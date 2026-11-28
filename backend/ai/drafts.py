"""Draf balasan AI (`ai_drafts`): pembuatan, pengiriman (manual/otomatis), tulis ulang, buang, label & tampilan Inbox."""
import logging

import wa_channels
import wa_gateway as gw
from ai import accuracy, budget, config, consent, identity, prompts, triage
from ai.client import ClaudeError, get_claude
from core_utils import new_id, now_iso
from db import db

logger = logging.getLogger("estora.ai.drafts")
OFFICIAL = ("cloud", "coexistence")
OPEN_STATES = ("ready", "edited", "rewritten")
WINDOW_CLOSED = "Sesi 24 jam tertutup. Gunakan template WA (pra-approved) untuk memulai percakapan."


class DraftError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


# ---------------------------------------------------------------- label percakapan
async def set_label(conv_id: str, status: str, detail: str = "") -> None:
    """status: auto_replied | draft_ready | needs_sales (None = hapus label)."""
    val = {"status": status, "detail": detail, "at": now_iso()} if status else None
    await db.conversations.update_one({"id": conv_id}, {"$set": {"ai_label": val}})


async def labels_for(org_id: str, ids: list, owner: str = None) -> dict:
    q = {"org_id": org_id, "id": {"$in": ids[:200]}}
    if owner:
        q["owner"] = owner
    rows = await db.conversations.find(q, {"_id": 0, "id": 1, "ai_label": 1}).to_list(200)
    return {r["id"]: r["ai_label"] for r in rows if r.get("ai_label")}


async def last_inbound_channel(conv_id: str) -> str:
    m = await db.messages.find_one({"conversation_id": conv_id, "direction": "in"}, {"_id": 0, "channel": 1},
                                   sort=[("created_at", -1)])
    return (m or {}).get("channel") or "simulation"


# ---------------------------------------------------------------- buat & kirim
async def create(org_id: str, conv: dict, *, category: str, mode: str, text: str, basis: list, flags: list = None,
                 with_notice: bool = False, channel: str = "simulation", ai_conversation_id: str = None,
                 source_message_id: str = None) -> dict:
    # draf lama yang belum diputuskan diganti draf baru (tidak dihitung dalam akurasi)
    await db.ai_drafts.update_many({"conversation_id": conv["id"], "status": "ready"}, {"$set": {"status": "superseded"}})
    d = {"id": new_id(), "org_id": org_id, "conversation_id": conv["id"], "lead_id": conv.get("lead_id"),
         "phone": conv.get("contact_phone"), "category": category, "mode": mode, "text": text, "original_text": text,
         "basis": basis, "flags": flags or [], "status": "ready", "final_text": None, "similarity": None,
         "sampled": False, "sample_review": None, "correct": None, "outcome_at": None, "with_notice": with_notice,
         "channel": channel, "ai_conversation_id": ai_conversation_id, "source_message_id": source_message_id, "at": now_iso()}
    await db.ai_drafts.insert_one(dict(d))
    return d


async def dispatch(org_id: str, conv_id: str, text: str, *, actor: str, with_notice: bool = False) -> dict:
    """Kirim satu balasan. Otomatis (`ai-auto`) HANYA lewat kanal resmi; kanal tidak resmi hanya untuk manusia."""
    conv = await db.conversations.find_one({"id": conv_id, "org_id": org_id}, {"_id": 0})
    if not conv:
        raise DraftError(404, "Percakapan tidak ditemukan.")
    channel = await last_inbound_channel(conv_id)
    if channel == "unofficial":
        if actor == "ai-auto":
            raise DraftError(409, "Balasan otomatis tidak boleh lewat kanal tidak resmi.")
        msg = await wa_channels.send_unofficial(org_id, conv["contact_phone"], text, actor=actor, ai_generated=False,
                                                kind="inbox", conversation_id=conv_id)
    else:
        if not gw.window_open(conv):
            raise DraftError(400, WINDOW_CLOSED)
        msg = await gw.send(org_id, conv["contact_phone"], kind="inbox", body=text, conversation_id=conv_id,
                            actor=actor, category="service")
    if msg.get("status") in ("failed", "blocked", "rate_limited"):
        raise DraftError(424, f"Kirim WA gagal ({msg.get('error_code')}): {msg.get('error_detail') or ''}".strip())
    ts = now_iso()
    await db.conversations.update_one({"id": conv_id}, {"$set": {"last_message_at": ts, "last_direction": "out",
                                                                  "status": "active", "updated_at": ts}})
    if with_notice:
        await consent.mark_noticed(org_id, conv["contact_phone"])
    return msg


async def _draft_for(draft_id: str, org_id: str) -> dict:
    d = await db.ai_drafts.find_one({"id": draft_id, "org_id": org_id}, {"_id": 0})
    if not d:
        raise DraftError(404, "Draf tidak ditemukan.")
    return d


async def send(draft_id: str, org_id: str, user: dict, text: str = None) -> dict:
    d = await _draft_for(draft_id, org_id)
    if d["status"] not in OPEN_STATES:
        raise DraftError(409, "Draf ini sudah diproses.")
    final = (text if text is not None else d["text"]).strip()
    if not final:
        raise DraftError(400, "Teks balasan kosong.")
    # Klaim atomik (terbuka -> sending): dua sales/klik ganda tidak bisa mengirim draf yang sama dua kali.
    if not await db.ai_drafts.find_one_and_update({"id": draft_id, "status": d["status"]}, {"$set": {"status": "sending"}}):
        raise DraftError(409, "Draf ini sudah diproses.")
    try:
        msg = await dispatch(org_id, d["conversation_id"], final, actor=user.get("email"), with_notice=d.get("with_notice", False))
    except Exception:
        await db.ai_drafts.update_one({"id": draft_id, "status": "sending"}, {"$set": {"status": d["status"]}})
        raise
    from routers.inbox_router import log_lead_activity  # jalur yang sama dengan balasan Inbox biasa
    conv = await db.conversations.find_one({"id": d["conversation_id"]}, {"_id": 0})
    await log_lead_activity(conv, msg, final, "out", user.get("email"), org_id)
    out = await accuracy.record_outcome(draft_id, final, status="sent" if final == d["text"] else "edited")
    await set_label(d["conversation_id"], None)
    return out


async def discard(draft_id: str, org_id: str) -> dict:
    d = await _draft_for(draft_id, org_id)
    if d["status"] not in OPEN_STATES:
        raise DraftError(409, "Draf ini sudah diproses.")
    out = await accuracy.record_outcome(draft_id, None, status="discarded")
    await set_label(d["conversation_id"], "needs_sales", "Draf dibuang, balas manual")
    return out


async def rewrite(draft_id: str, org_id: str, instruction: str) -> dict:
    d = await _draft_for(draft_id, org_id)
    if d["status"] not in OPEN_STATES:
        raise DraftError(409, "Draf ini sudah diproses.")
    if (await budget.budget_state(org_id))["state"] == "stop":
        raise DraftError(429, "Anggaran AI bulan ini habis.")
    s = await config.get_ai_settings(org_id)
    prompt = (f"Draf balasan saat ini:\n{d['text']}\n\nInstruksi staf: {instruction}\n\n"
              "Tulis ulang draf sesuai instruksi. Keluarkan HANYA teks balasan. Jangan menambah janji, diskon, atau data baru.")
    try:
        claude = await get_claude(org_id)
        resp = await claude.turn(model=s["model_main"], system=prompts.system_for("sales", None),
                                 messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}], tools=[],
                                 effort=s["effort_wa"], max_tokens=1500, on_text=None,
                                 context={"purpose": "rewrite", "draft_id": draft_id})
    except ClaudeError:
        raise DraftError(502, "Layanan AI sedang bermasalah. Coba lagi.")
    new = "".join(b.get("text", "") for b in resp.get("content") or [] if b.get("type") == "text").strip()
    if not new:
        raise DraftError(502, "AI tidak menghasilkan teks. Coba instruksi lain.")
    if d.get("with_notice") and not new.startswith((await consent.notice_text(org_id))[:30]):
        new = f"{await consent.notice_text(org_id)}\n\n{new}"
    upd = {"text": new, "status": "rewritten", "correct": False, "similarity": accuracy.similarity(d["original_text"], new)}
    if d["status"] != "rewritten":
        upd["outcome_at"] = now_iso()  # ditulis ulang = salah (sekali saja)
    await db.ai_drafts.update_one({"id": draft_id}, {"$set": upd})
    return {**d, **upd}


# ---------------------------------------------------------------- tampilan Inbox
def public(d: dict) -> dict:
    keys = ("id", "conversation_id", "lead_id", "category", "mode", "text", "basis", "status", "final_text", "similarity",
            "sampled", "sample_review", "flags", "at")
    out = {k: d.get(k) for k in keys}
    out["category_label"] = triage.CATEGORY_INFO.get(d.get("category"), (d.get("category"),))[0]
    return out


async def latest_visible(org_id: str, conv_id: str):
    d = await db.ai_drafts.find_one({"org_id": org_id, "conversation_id": conv_id, "status": {"$in": list(OPEN_STATES) + ["auto_sent"]}},
                                    {"_id": 0}, sort=[("at", -1)])
    if d and d["status"] == "auto_sent" and not (d.get("sampled") and not d.get("sample_review")):
        return None
    return d


async def inbox_view(org_id: str, conv: dict) -> dict:
    d = await latest_visible(org_id, conv["id"])
    ins = None
    if conv.get("lead_id"):
        ins = await db.ai_lead_insights.find_one({"org_id": org_id, "lead_id": conv["lead_id"]}, {"_id": 0})
        lead = await db.leads.find_one({"id": conv["lead_id"], "org_id": org_id}, {"_id": 0, "score": 1, "stage": 1}) or {}
        if ins:
            ins = {**ins, "score": lead.get("score"), "stage": lead.get("stage"),
                   "next_step_prompt": f"Bantu saya menyiapkan langkah berikutnya untuk lead ini: {ins.get('next_step')}"}
    phone = conv.get("contact_phone")
    label = conv.get("ai_label")
    cs = await consent.state(org_id, phone) if phone else None
    return {"draft": public(d) if d else None, "label": label, "insights": ins,
            "channel": await last_inbound_channel(conv["id"]), "window_open": gw.window_open(conv),
            "verified": bool(phone) and await identity.is_verified(org_id, phone),
            "actions": await pending_actions(org_id, phone),
            "optin_unofficial": (cs or {}).get("optins", {}).get("unofficial", False),
            "optin_pending": (cs or {}).get("pending_optin") == "unofficial",
            "unofficial_enabled": bool((await db.channel_accounts.find_one(
                {"org_id": org_id, "code": wa_channels.UNOFFICIAL_CODE}, {"_id": 0, "enabled": 1}) or {}).get("enabled"))}


async def pending_actions(org_id: str, phone: str) -> list:
    """Usulan aksi agen WA untuk kontak ini (percakapan AI milik akun layanan) — disetujui/ditolak dari Inbox."""
    if not phone:
        return []
    from ai.api_views import action_view
    ai_conv = await db.ai_conversations.find_one({"org_id": org_id, "channel": "wa", "contact.phone": phone}, {"_id": 0, "id": 1})
    if not ai_conv:
        return []
    rows = await db.ai_actions.find({"org_id": org_id, "conversation_id": ai_conv["id"], "status": "pending"},
                                    {"_id": 0}).sort("created_at", -1).to_list(20)
    return [action_view(a) for a in rows]
