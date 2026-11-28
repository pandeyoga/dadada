"""Serah ke CS dari chat portal: tiket "Pertanyaan dari chat" di modul Komplain (kode sistem, bukan isian bebas AI).

Arah tiket (keputusan pemilik §9): pertanyaan biasa / minta staf -> sales pemegang unit; topik sensitif (diskon/nego,
janji/komitmen, pembatalan/refund) -> pengguna aktif ber-peran `sales_manager` pertama di org, bila tidak ada -> `owner`.
Tenggat 24 jam, tugas SM-09 + notifikasi staf, TANPA WA ke pembeli (nomor tiket sudah tampil di chat).
"""
from datetime import timedelta

import complaint_intake as ci
from core_utils import WIB, now, now_iso
from db import db

SLA_HOURS = 24
DEDUPE_MINUTES = 10  # tombol "Bicara dengan CS" ditekan dua kali -> tiket yang sama, bukan dua tiket
REASON_LABEL = {"diskon_nego": "Diskon & nego", "janji_komitmen": "Janji & komitmen",
                "pembatalan_refund": "Pembatalan & refund", "minta_staf": "Minta dihubungi CS"}


def ticket_view(doc: dict) -> dict:
    return {"id": doc["id"], "number": doc["id"][:8].upper(), "subject": doc.get("subject"),
            "assigned_role": doc.get("assigned_role"), "due_at": doc.get("sla_due_at")}


def due_text(iso: str) -> str:
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso).astimezone(WIB).strftime("%d/%m/%Y %H.%M WIB")
    except (TypeError, ValueError):
        return "1x24 jam"


async def _manager(org_id: str):
    for role in ("sales_manager", "owner"):
        u = await db.users.find_one({"org_id": org_id, "role": role, "is_active": {"$ne": False}},
                                    {"_id": 0, "email": 1}, sort=[("created_at", 1)])
        if u:
            return u["email"], role
    return None, "owner"


async def _route(org_id: str, deal: dict, deals: list, sensitive: bool):
    """-> (assigned_to, assigned_role)."""
    if not sensitive:
        if deal and deal.get("assigned_to"):
            return deal["assigned_to"], "sales"
        holders = {d.get("assigned_to") for d in deals if d.get("assigned_to")}
        if len(holders) == 1:  # semua unit pembeli dipegang sales yang sama: tidak ambigu
            return holders.pop(), "sales"
    return await _manager(org_id)


async def create_ticket(ctx, *, reason: str, question: str, summary: str, sensitive: bool,
                        deal_id: str = None) -> dict:
    """-> {"id","number","subject","assigned_role","due_at"}. `deal_id` di luar milik pembeli diabaikan."""
    pu, org = ctx.user, ctx.org_id
    q = " ".join(str(question or "").split())
    deals = await ci.buyer_deals(pu, await ci.buyer_customer(pu))
    deal = next((d for d in deals if d["id"] == deal_id), None) if deal_id else (deals[0] if len(deals) == 1 else None)
    since = (now() - timedelta(minutes=DEDUPE_MINUTES)).isoformat()
    if ctx.conversation_id:
        dup = await db.complaints.find_one({"org_id": org, "kind": ci.CHAT_KIND, "ai_conversation_id": ctx.conversation_id,
                                            "status": "open", "sensitive": bool(sensitive), "created_at": {"$gte": since}},
                                           {"_id": 0}, sort=[("created_at", -1)])
        if dup:
            if q and q not in (dup.get("message") or ""):  # pertanyaan tambahan tetap sampai ke CS, tanpa tiket kedua
                await db.complaints.update_one({"id": dup["id"]}, {"$set": {
                    "message": f"{dup.get('message') or ''}\n\nPertanyaan tambahan lewat chat: {q[:500]}", "updated_at": now_iso()}})
            return ticket_view(dup)
    assignee, role = await _route(org, deal, deals, sensitive)
    label = REASON_LABEL.get(reason) or (str(reason or "").strip()[:60] or "Pertanyaan ke CS")
    label = label[:1].upper() + label[1:]
    subject = f"{label}: {q[:80]}" if q else label
    message = (f"Pertanyaan pembeli lewat chat Tanya Estora:\n{q or '-'}\n\nAlasan diteruskan: {label}\n\n"
               f"Ringkasan percakapan:\n{(summary or '-').strip()[:2000]}")
    doc = await ci.create_complaint(
        org_id=org, portal_user=pu, deal=deal, category="layanan", subject=subject, message=message,
        priority="high" if sensitive else "medium", sla_hours=SLA_HOURS, assigned_to=assignee,
        extra={"kind": ci.CHAT_KIND, "source": "ai_portal", "ai_conversation_id": ctx.conversation_id,
               "handoff_reason": reason, "sensitive": bool(sensitive), "assigned_role": role,
               "portal_user_id": pu.get("id")},  # tiket tanpa deal/customer tetap terlihat oleh pembeli ini (portal_scope)
        notify_buyer_wa=False)
    return ticket_view(doc)
