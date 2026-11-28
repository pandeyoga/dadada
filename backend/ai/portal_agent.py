"""Agen CS pembeli di portal ("Tanya Estora", peran `buyer_cs`, kanal `portal`).

Urutan satu pesan (`handle_message`): nonaktif -> berhenti -> kuota harian (`$inc` atomik `ai_portal_quota`) -> minta staf
(kata manusia/staf/cs, <= 4 kata, atau frasa "bicara/hubungi/minta ... CS/staf": tiket tanpa model; tidak memakan anggaran
AI) -> anggaran `stop` -> pemilah (Haiku) -> topik terkunci (diskon/nego, janji/komitmen, pembatalan/refund, menurut
pemilah ATAU penahan kata kunci: tiket ke Manajer Penjualan tanpa memanggil model jawaban) -> selain itu `agent.run_turn`
dengan token portal pembeli (tanpa token staf / `ai_agent`). Galat berorientasi staf diganti teks untuk pembeli.
Privasi (UU PDP): pemberitahuan & "berhenti" dicatat di `ai_consents` (kunci `phone = "portal:<portal_user_id>"`,
`channel: "portal"`) supaya tidak bertabrakan dengan indeks unik nomor WA.
"""
import logging
import re
from typing import AsyncIterator

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ai import agent, api_views, budget, config, conversations, portal_handoff, triage
from ai.tools.registry import ToolContext
from complaint_intake import CHAT_KIND
from core_utils import WIB, new_id, now, now_iso
from db import db, ORG_ID

logger = logging.getLogger("estora.ai.portal")

SENSITIVE = ("diskon_nego", "janji_komitmen", "pembatalan_refund")
TOPIC = {"diskon_nego": "diskon atau negosiasi harga", "janji_komitmen": "janji atau komitmen",
         "pembatalan_refund": "pembatalan atau pengembalian dana"}
DISABLED_MSG = "Asisten Tanya Estora belum tersedia. Silakan hubungi CS kami lewat menu Komplain."
STOPPED_MSG = "Anda sudah berhenti memakai asisten. Pilih \"Aktifkan lagi\" di menu bila ingin memakainya kembali."
BUYER_ERR = "Asisten sedang tidak bisa menjawab saat ini. Tekan \"Bicara dengan CS\" agar tim kami menghubungi Anda."
_STAFF_ERR = re.compile(r"admin|pemilik|anggaran|kunci api|putaran alat", re.I)  # teks galat untuk staf, bukan pembeli
_WORD = re.compile(r"[a-zA-Z]+")
# Portal: tanpa "sales" ("Siapa sales saya?" adalah pertanyaan, bukan minta staf); frasa panjang lewat _HUMAN_PHRASE.
HUMAN_WORDS = frozenset({"manusia", "staf", "staff", "cs"})
_HUMAN_PHRASE = re.compile(r"(?:bicara|hubungi|sambungkan|minta).{0,20}\b(?:cs|staf|staff|manusia|admin|petugas)\b", re.I)
# Penahan setelah pemilah: pemilah bisa ragu (< 0,6), menolak karena pola injeksi, atau salah kelas. Topik sensitif
# tetap ke Manajer Penjualan (§9.1) tanpa model jawaban. Awalan kata (\b) + akhiran bebas: "dibatalkan", "bernego".
SENSITIVE_RX = (
    ("pembatalan_refund", re.compile(r"\b(?:di|mem|pem)?batal|\brefund|\buang\s+kembali", re.I)),
    ("diskon_nego", re.compile(r"\bdiskon|\b(?:ber)?nego|\bpotongan", re.I)),
    ("janji_komitmen", re.compile(r"\b(?:di|men)?(?:janji|jamin)", re.I)),
)


def _org(pu: dict) -> str:
    return pu.get("org_id", ORG_ID)


def _key(pu: dict) -> str:
    return f"portal:{pu['id']}"


def _day() -> str:
    return now().astimezone(WIB).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- privasi (ai_consents kanal portal)
async def _consent(pu: dict) -> dict:
    return await db.ai_consents.find_one({"org_id": _org(pu), "phone": _key(pu)}, {"_id": 0}) or {}


async def _set_consent(pu: dict, fields: dict) -> None:
    await db.ai_consents.update_one(
        {"org_id": _org(pu), "phone": _key(pu)},
        {"$set": {**fields, "channel": "portal", "portal_user_id": pu["id"], "updated_at": now_iso()},
         "$setOnInsert": {"id": new_id(), "created_at": now_iso()}}, upsert=True)


async def mark_noticed(pu: dict) -> None:
    await _set_consent(pu, {"noticed_at": now_iso()})


async def stop(pu: dict) -> None:
    await _set_consent(pu, {"stopped": True, "stopped_at": now_iso()})


async def resume(pu: dict) -> None:
    await _set_consent(pu, {"stopped": False})


# ---------------------------------------------------------------- status & kuota
async def enabled(org_id: str):
    """-> (aktif?, pengaturan AI). Aktif = saklar `ai.portal_enabled` menyala dan mode AI bukan `off`."""
    s = await config.get_ai_settings(org_id)
    return bool(s.get("portal_enabled")) and s.get("effective_mode") != "off", s


def _qkey(pu: dict) -> dict:
    return {"org_id": _org(pu), "portal_user_id": pu["id"], "day": _day()}


async def _used(pu: dict) -> int:
    d = await db.ai_portal_quota.find_one(_qkey(pu), {"_id": 0, "count": 1})
    return int((d or {}).get("count") or 0)


async def _take_quota(pu: dict, limit: int) -> bool:
    """Klaim satu jatah pesan secara atomik; melewati batas -> dikembalikan dan False."""
    q = _qkey(pu)
    upd = {"$inc": {"count": 1}, "$set": {"updated_at": now_iso()}}
    try:
        doc = await db.ai_portal_quota.find_one_and_update(q, upd, upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:  # dua upsert serentak untuk hari baru: ulangi sekali (dokumen sudah ada)
        doc = await db.ai_portal_quota.find_one_and_update(q, upd, return_document=ReturnDocument.AFTER)
    if int(doc["count"]) > limit:
        await db.ai_portal_quota.update_one(q, {"$inc": {"count": -1}})
        return False
    return True


async def _release_quota(pu: dict) -> None:
    await db.ai_portal_quota.update_one({**_qkey(pu), "count": {"$gt": 0}}, {"$inc": {"count": -1}})


async def status(portal_user: dict) -> dict:
    pu, org = portal_user, _org(portal_user)
    on, s = await enabled(org)
    c = await _consent(pu)
    return {"enabled": on, "effective_mode": s.get("effective_mode"),
            "budget_state": (await budget.budget_state(org))["state"],
            "quota": {"used": await _used(pu), "limit": int(s.get("portal_daily_limit") or 0)},
            "notice_text": s.get("portal_notice"), "noticed": bool(c.get("noticed_at")), "stopped": bool(c.get("stopped"))}


# ---------------------------------------------------------------- tampilan
def action_view(a: dict) -> dict:
    """Kartu konfirmasi untuk pembeli: tanpa payload/izin/penyetuju internal."""
    if not a:
        return a
    p = a.get("preview") or {}
    st = a.get("status")
    return {"id": a["id"], "tool": a.get("tool"), "status": st,
            "preview": {"title": p.get("title"), "changes": p.get("changes") or [], "checks": p.get("checks") or []},
            "summary": a.get("summary") or (p.get("title") if st == "pending" else None), "error": a.get("error"),
            "editable": [], "created_at": a.get("created_at"), "updated_at": a.get("updated_at")}


async def conversation_view(conv_id: str, pu: dict) -> dict:
    """Percakapan milik pembeli ini (LookupError bila bukan). Pesan = bentuk Copilot (`ui_messages`) + `ticket`."""
    c = await conversations.get(conv_id, pu["id"])
    if c.get("channel") != "portal":
        raise LookupError("Percakapan tidak ditemukan.")
    raw = c.pop("messages")
    tickets = {m["id"]: m["ticket"] for m in raw if m.get("ticket")}
    msgs = await api_views.ui_messages(raw)
    for m in msgs:
        if m.get("actions"):
            m["actions"] = [action_view(a) for a in m["actions"]]
        if m["id"] in tickets:
            m["ticket"] = tickets[m["id"]]
    return {**{k: c.get(k) for k in ("id", "title", "created_at", "updated_at")}, "messages": msgs}


# ---------------------------------------------------------------- serah ke CS deterministik
def _wants_human(text: str) -> bool:
    words = [w.lower() for w in _WORD.findall(text or "")]
    return (bool(words) and len(words) <= 4 and bool(set(words) & HUMAN_WORDS)) or bool(_HUMAN_PHRASE.search(text or ""))


def _sensitive_topic(text: str):
    return next((cat for cat, rx in SENSITIVE_RX if rx.search(text or "")), None)


def _buyer_error(msg: str) -> str:
    return BUYER_ERR if not msg or _STAFF_ERR.search(msg) else msg


async def _recent(conv_id: str, n: int = 10) -> list:
    rows = await db.ai_messages.find({"conversation_id": conv_id}, {"_id": 0, "role": 1, "content": 1}) \
        .sort("seq", -1).to_list(n * 3)
    out = []
    for m in reversed(rows):
        c = m.get("content")
        blocks = c if isinstance(c, list) else [{"type": "text", "text": c or ""}]
        text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        if text and text != "Lanjutkan.":
            out.append({"role": m["role"], "text": text})
    return out[-n:]


def _summary(hist: list, text: str) -> str:
    lines = [f"{'Pembeli' if h['role'] == 'user' else 'Asisten'}: {h['text'][:300]}" for h in hist[-8:]]
    return "\n".join(lines + [f"Pembeli (pesan terakhir): {text[:500]}"])


def _handoff_text(t: dict, sensitive: bool, reason: str) -> str:
    due = portal_handoff.due_text(t["due_at"])
    if sensitive:
        who = "Manajer Penjualan kami" if t.get("assigned_role") == "sales_manager" else "pimpinan penjualan kami"
        return (f"Pertanyaan tentang {TOPIC.get(reason, 'hal ini')} perlu dijawab langsung oleh tim kami, jadi saya tidak "
                f"bisa memberi kepastian di sini. Saya sudah meneruskannya ke {who} sebagai tiket No. {t['number']}. "
                f"Tim kami akan menghubungi Anda paling lambat {due}.")
    return (f"Baik, saya teruskan ke tim CS kami sebagai tiket No. {t['number']}. "
            f"Tim kami akan menghubungi Anda paling lambat {due}.")


async def _handoff(ctx: ToolContext, text: str, hist: list, *, sensitive: bool, reason: str) -> AsyncIterator[dict]:
    t = await portal_handoff.create_ticket(ctx, reason=reason, question=text, summary=_summary(hist, text),
                                           sensitive=sensitive, deal_id=None)
    conv_id = ctx.conversation_id
    await conversations.append(conv_id, {"role": "user", "content": [{"type": "text", "text": text}]})
    await conversations.set_title_if_new(conv_id, text)
    msg = _handoff_text(t, sensitive, reason)
    m = await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": msg}],
                                             "ticket": t, "handoff": reason})
    yield {"type": "handoff", "ticket": t}
    yield {"type": "text_delta", "text": msg, "saved": True}  # sudah tersimpan: router tidak menyimpannya lagi sebagai parsial
    yield {"type": "done", "message_id": m["id"], "usage": {}, "stop": "ok"}


# ---------------------------------------------------------------- satu pesan pembeli
async def handle_message(portal_user: dict, token: str, conv_id: str, text: str) -> AsyncIterator[dict]:
    pu, org = portal_user, _org(portal_user)
    on, s = await enabled(org)
    if not on:
        yield {"type": "error", "message": DISABLED_MSG}
        return
    if (await _consent(pu)).get("stopped"):
        yield {"type": "error", "message": STOPPED_MSG}
        return
    limit = int(s.get("portal_daily_limit") or 0)
    if not await _take_quota(pu, limit):
        yield {"type": "error", "message": f"Batas {limit} pesan hari ini tercapai. Coba lagi besok, atau sampaikan "
                                           "keluhan Anda lewat menu Komplain di portal."}
        return
    ctx = ToolContext(org_id=org, user=pu, token=token, channel="portal", conversation_id=conv_id,
                      verified=True, role="buyer_cs")
    hist = await _recent(conv_id)
    if _wants_human(text):  # tanpa model: tidak memakan anggaran AI
        async for ev in _handoff(ctx, text, hist, sensitive=False, reason="minta_staf"):
            yield ev
        return
    if (await budget.budget_state(org))["state"] == "stop":
        await _release_quota(pu)
        yield {"type": "error", "message": BUYER_ERR}
        return
    tri = await triage.classify(org, text, hist, channel="portal")
    topic = tri["category"] if tri["category"] in SENSITIVE else _sensitive_topic(text)
    if topic:
        async for ev in _handoff(ctx, text, hist, sensitive=True, reason=topic):
            yield ev
        return
    handoff_steps, ticket = set(), None
    async for ev in agent.run_turn(ctx, conv_id, [{"type": "text", "text": text}]):
        kind = ev.get("type")
        if kind == "step_started" and ev.get("tool") == "serahkan_ke_cs":
            handoff_steps.add(ev.get("id"))
        elif kind == "action_proposed":
            ev = {**ev, "action": action_view(ev.get("action"))}
        elif kind == "error":
            ev = {**ev, "message": _buyer_error(ev.get("message"))}
        elif kind == "done" and ticket and ev.get("message_id"):
            await db.ai_messages.update_one({"id": ev["message_id"]}, {"$set": {"ticket": ticket}})
        yield ev
        if kind == "step_done" and ev.get("ok") and ev.get("id") in handoff_steps:
            doc = await db.complaints.find_one({"org_id": org, "kind": CHAT_KIND, "ai_conversation_id": conv_id},
                                               {"_id": 0}, sort=[("created_at", -1)])
            if doc:
                ticket = portal_handoff.ticket_view(doc)
                yield {"type": "handoff", "ticket": ticket}
