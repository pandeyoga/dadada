"""ai_inbox_router — draf AI di Inbox, tinjauan sampel, akurasi & mode per kategori (`/api/ai/...`)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_store as ss
import wa_channels
import wa_gateway as gw
from ai import accuracy, config, consent, drafts, triage
from core_utils import new_id, now_iso, serialize_doc
from db import db, ORG_ID
from rbac import audit_log, is_scoped_sales, require_permission
from routers.inbox_router import _get_conv_scoped, log_lead_activity

router = APIRouter(prefix="/ai", tags=["ai-inbox"])
_use = require_permission("ai_inbox", "use")
_manage = require_permission("ai_settings", "manage")


def _org(u: dict) -> str:
    return u.get("org_id", ORG_ID)


async def _conv(conv_id: str, user: dict) -> dict:
    """Percakapan Inbox milik org pengguna (dan milik sales itu sendiri bila perannya terbatas)."""
    conv = await _get_conv_scoped(conv_id, user)
    if conv.get("org_id", ORG_ID) != _org(user):
        raise HTTPException(404, "Percakapan tidak ditemukan")
    return conv


async def _guard(draft_id: str, user: dict) -> dict:
    d = await db.ai_drafts.find_one({"id": draft_id, "org_id": _org(user)}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Draf tidak ditemukan.")
    await _conv(d["conversation_id"], user)  # sales hanya percakapannya sendiri
    return d


async def _run(coro):
    try:
        return await coro
    except drafts.DraftError as e:
        raise HTTPException(e.status, e.message)
    except (LookupError, ValueError) as e:
        raise HTTPException(400 if isinstance(e, ValueError) else 404, str(e))


@router.get("/inbox/conversations/{conv_id}")
async def inbox_conversation(conv_id: str, user: dict = Depends(_use)):
    conv = await _conv(conv_id, user)
    return {"data": await drafts.inbox_view(_org(user), conv)}


@router.get("/inbox/labels")
async def inbox_labels(ids: str = "", user: dict = Depends(_use)):
    wanted = [i for i in ids.split(",") if i][:200]
    owner = user.get("email") if is_scoped_sales(user) else None  # sales: hanya label percakapannya sendiri
    return {"data": await drafts.labels_for(_org(user), wanted, owner=owner)}


# ---------------------------------------------------------------- opt-in kanal kedua & kirim WA lead (aksi AI)
OPTIN_QUESTION = ("Halo, tim Estora ingin juga bisa menghubungi Anda lewat nomor WhatsApp kedua kami{nomor}. "
                  "Balas YA bila Anda setuju. Abaikan pesan ini bila tidak setuju.")


@router.post("/inbox/conversations/{conv_id}/optin-unofficial")
async def request_unofficial_optin(conv_id: str, user: dict = Depends(_use)):
    """"Minta izin kanal kedua": tanyakan opt-in lewat kanal RESMI; balasan YA berikutnya mencatat persetujuan."""
    conv = await _conv(conv_id, user)
    org, phone = _org(user), conv.get("contact_phone")
    if not phone:
        raise HTTPException(400, "Percakapan ini tidak punya nomor kontak.")
    st = await consent.state(org, phone)
    if st["stopped"]:
        raise HTTPException(409, "Kontak ini sudah meminta berhenti (STOP); jangan dihubungi lewat kanal lain.")
    if st["optins"]["unofficial"]:
        raise HTTPException(409, "Kontak ini sudah memberi izin kanal kedua.")
    uo = await wa_channels.get_unofficial_config(org)
    if not uo["enabled"]:
        raise HTTPException(409, "Gateway WhatsApp tidak resmi belum diaktifkan di Pengaturan AI.")
    if not gw.window_open(conv):
        raise HTTPException(400, drafts.WINDOW_CLOSED)
    body = OPTIN_QUESTION.format(nomor=f" ({uo['phone']})" if uo.get("phone") else "")
    msg = await gw.send(org, phone, kind="inbox", body=body, conversation_id=conv_id,
                        actor=user.get("email"), category="service")
    if msg.get("status") == "failed":
        raise HTTPException(424, f"Kirim WA gagal ({msg.get('error_code')}): {msg.get('error_detail') or ''}".strip())
    await consent.ask_optin(org, phone, "unofficial")
    await audit_log(user, "request_optin", "ai_consents", conv_id, {"kind": "unofficial"})
    return {"data": {"pending_optin": "unofficial", "message_id": msg["id"]}}


class LeadWaIn(BaseModel):
    body: Optional[str] = ""
    template_code: Optional[str] = None


@router.post("/inbox/leads/{lead_id}/wa")
async def send_lead_wa(lead_id: str, payload: LeadWaIn, user: dict = Depends(require_permission("leads", "update"))):
    """Kirim WA ke lead lewat gateway RESMI atas nama pengguna (dipakai aksi AI `kirim_pesan_wa` setelah disetujui).

    Teks bebas hanya bila sesi 24 jam terbuka, selain itu wajib template. Kontak pertama/tahap lead hanya
    dicatat bila pengiriman berhasil.
    """
    from routers.leads_lifecycle_router import _lead
    lead = await _lead(lead_id, user)
    org = lead["org_id"]
    conv = await db.conversations.find_one({"org_id": org, "lead_id": lead_id}, {"_id": 0}, sort=[("last_message_at", -1)])
    template = None
    if payload.template_code:
        template = await db.wa_templates.find_one({"org_id": org, "code": payload.template_code}, {"_id": 0})
        if not template:
            raise HTTPException(404, "Template WA tidak ditemukan")
    elif not gw.window_open(conv):
        raise HTTPException(400, drafts.WINDOW_CLOSED)
    body = template["body"] if template else (payload.body or "").strip()
    if not body:
        raise HTTPException(400, "Isi pesan tidak boleh kosong.")
    if template:
        from engine import render_wa_body, wa_template_vars
        body = render_wa_body(body, await wa_template_vars(lead))
    if not conv:
        ts = now_iso()
        adapter, _cfg = await gw.adapter_for(org)
        conv = {"id": new_id(), "org_id": org, "channel": "whatsapp", "contact_phone": lead.get("phone"),
                "contact_name": lead.get("name"), "lead_id": lead_id, "owner": lead.get("assigned_to") or user.get("email"),
                "status": "active", "mode": adapter.mode, "unread": 0, "last_message_at": None, "last_direction": None,
                "window_expires_at": None, "created_at": ts, "updated_at": ts}
        await db.conversations.insert_one(dict(conv))
    msg = await gw.send(org, lead.get("phone"), kind="inbox", body=body, template=template, conversation_id=conv["id"],
                        actor=user.get("email"))
    if msg.get("status") in ("failed", "blocked", "rate_limited"):
        raise HTTPException(424, f"Kirim WA gagal ({msg.get('error_code')}): {msg.get('error_detail') or ''}".strip())
    await log_lead_activity(conv, msg, body, "out", user.get("email"), org)  # kontak pertama hanya bila terkirim
    msg.pop("_id", None)
    return {"data": serialize_doc(msg)}


class SendIn(BaseModel):
    text: Optional[str] = None


class RewriteIn(BaseModel):
    instruction: str


class ReviewIn(BaseModel):
    verdict: str


class ModeIn(BaseModel):
    mode: str


@router.post("/inbox/drafts/{draft_id}/send")
async def send_draft(draft_id: str, body: SendIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(drafts.send(draft_id, _org(user), user, body.text))
    await audit_log(user, "send", "ai_drafts", draft_id, {"edited": out["status"] == "sent_edited", "similarity": out["similarity"]})
    return {"data": drafts.public(out)}


@router.post("/inbox/drafts/{draft_id}/rewrite")
async def rewrite_draft(draft_id: str, body: RewriteIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    if not body.instruction.strip():
        raise HTTPException(400, "Instruksi tulis ulang kosong.")
    out = await _run(drafts.rewrite(draft_id, _org(user), body.instruction.strip()[:500]))
    return {"data": {**drafts.public(out), "draft": drafts.public(out)}}


@router.post("/inbox/drafts/{draft_id}/discard")
async def discard_draft(draft_id: str, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(drafts.discard(draft_id, _org(user)))
    await audit_log(user, "discard", "ai_drafts", draft_id, {})
    return {"data": drafts.public(out)}


@router.post("/inbox/samples/{draft_id}/review")
async def review_sample(draft_id: str, body: ReviewIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(accuracy.review_sample(draft_id, body.verdict, user))
    await audit_log(user, "review", "ai_drafts", draft_id, {"verdict": body.verdict})
    return {"data": drafts.public(out)}


# ---------------------------------------------------------------- akurasi & mode kategori
async def _row(org: str, cat: str, modes: dict) -> dict:
    label, desc = triage.CATEGORY_INFO[cat]
    if cat in triage.LOCKED:
        return {"category": cat, "label": label, "description": desc, "accuracy": None, "samples": 0, "mode": "handoff",
                "locked": True, "can_enable_auto": False, "reason": accuracy.LOCKED_REASON}
    st = await accuracy.stats(org, cat)
    ok, why = await accuracy.can_enable_auto(org, cat)
    return {"category": cat, "label": label, "description": desc, "accuracy": st["accuracy"], "samples": st["samples"],
            "mode": (modes or {}).get(cat, "draft"), "locked": False, "can_enable_auto": ok, "reason": why}


@router.get("/accuracy")
async def accuracy_table(user: dict = Depends(_manage)):
    org = _org(user)
    modes = await ss.get("ai.category_modes", org_id=org)
    return {"data": [await _row(org, c, modes) for c in triage.CATEGORY_INFO]}


@router.put("/categories/{cat}")
async def set_category(cat: str, body: ModeIn, user: dict = Depends(_manage)):
    org = _org(user)
    if cat not in triage.CATEGORY_INFO:
        raise HTTPException(404, "Kategori tidak dikenal.")
    if cat in triage.LOCKED:
        raise HTTPException(400, accuracy.LOCKED_REASON)
    if body.mode not in config.CATEGORY_MODES:
        raise HTTPException(400, "Mode harus auto, draft, atau off.")
    if body.mode == "auto":
        ok, why = await accuracy.can_enable_auto(org, cat)
        if not ok:
            raise HTTPException(400, f"Mode Otomatis belum bisa dipilih. {why}")
    try:
        modes = await config.set_category_mode(org, cat, body.mode, user.get("email"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    await audit_log(user, "update", "ai_category_mode", cat, {"mode": body.mode})
    return {"data": await _row(org, cat, modes)}
