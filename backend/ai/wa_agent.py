"""Agen penjualan WhatsApp: antrean `ai_jobs` -> pemilah -> draf (atau balasan otomatis bertahap) -> ringkasan lead.

Aturan keselamatan (urutan penting):
STOP/manusia dihormati -> anggaran `stop` menghentikan semuanya -> kategori terkunci = serahkan ke sales (tanpa draf) ->
data pribadi hanya setelah verifikasi -> kirim otomatis HANYA bila mode `auto`, kanal resmi, jendela 24 jam terbuka,
gerbang akurasi masih lolos, dan tidak ada usulan aksi/penanda risiko.
Isi pesan pelanggan selalu data tak tepercaya (dibungkus `prompts`/agen); alat WA tidak punya akses data kontak lain.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import settings_store as ss
import wa_gateway as gw
from ai import accuracy, budget, config, consent, conversations, drafts, identity, insights, triage
from ai.agent import run_turn
from ai.tools import internal_api
from ai.tools.registry import ToolContext
from core_utils import new_id, now_iso
from db import db

logger = logging.getLogger("estora.ai.wa_agent")
PERSONAL = ("tagihan_pembayaran", "progres_serah_terima")  # butuh verifikasi identitas
STALE_MIN = 10
MAX_ATTEMPTS = 3
RISKY = re.compile(r"\b(diskon|potongan harga|cashback|gratis|bebas biaya|refund|pengembalian dana|dijamin|pasti disetujui|harga khusus)\b", re.I)
LONG_DIGITS = re.compile(r"\d{12,}")
DEFAULT_ANSWER_FAIL = ("Verifikasi belum berhasil. Mohon kirim 4 digit terakhir NIK pembeli yang terdaftar, "
                       "atau balas HUBUNGI STAF agar dibantu tim kami.")


# ---------------------------------------------------------------- antrean
async def enqueue(org_id: str, conversation_id: str, message_id: str, *, phone: str, lead_id: str = None) -> dict:
    job = {"id": new_id(), "org_id": org_id, "conversation_id": conversation_id, "message_id": message_id,
           "phone": phone, "lead_id": lead_id, "status": "queued", "attempts": 0, "created_at": now_iso()}
    await db.ai_jobs.insert_one(dict(job))
    return job


async def _claim():
    stale = (datetime.now(timezone.utc) - timedelta(minutes=STALE_MIN)).isoformat()
    return await db.ai_jobs.find_one_and_update(
        {"$or": [{"status": "queued"}, {"status": "processing", "locked_at": {"$lt": stale}}], "attempts": {"$lt": MAX_ATTEMPTS}},
        {"$set": {"status": "processing", "locked_at": now_iso()}, "$inc": {"attempts": 1}},
        sort=[("created_at", 1)], projection={"_id": 0}, return_document=True)


async def tick() -> int:
    """Satu putaran worker: proses semua job yang antre. Dipanggil penjadwal tiap 5 detik."""
    n = 0
    while (job := await _claim()):
        try:
            res = await process_job(job)
            await db.ai_jobs.update_one({"id": job["id"]}, {"$set": {"status": "done", "result": res, "done_at": now_iso()}})
        except Exception as e:  # noqa: BLE001
            logger.exception("Job AI %s gagal", job["id"])
            await db.ai_jobs.update_one({"id": job["id"]}, {"$set": {"status": "failed" if job["attempts"] >= MAX_ATTEMPTS else "queued",
                                                                      "error": type(e).__name__}})
        n += 1
    return n


def register(scheduler) -> list:
    scheduler.add_job(tick, "interval", seconds=5, id="ai_jobs_worker", max_instances=1, coalesce=True)
    return ["ai_jobs_worker"]


# ---------------------------------------------------------------- bantu
async def _notify_owner(org_id: str, conv: dict, title: str, body: str) -> None:
    if not conv.get("owner"):
        return
    from engine import create_notification
    await create_notification(user_email=conv["owner"], title=title, body=body, type="info",
                              related_entity_type="conversation", related_entity_id=conv["id"], org_id=org_id)


async def _handoff(org_id: str, conv: dict, category: str, reason: str) -> dict:
    label = triage.CATEGORY_INFO.get(category, (category,))[0]
    await drafts.set_label(conv["id"], "needs_sales", reason or label)
    await _notify_owner(org_id, conv, "Percakapan WhatsApp butuh sales", f"{conv.get('contact_name') or conv.get('contact_phone')}: {reason or label}")
    return {"status": "handoff", "category": category, "reason": reason}


async def _ai_conversation(org_id: str, conv: dict, svc_user: dict) -> dict:
    c = await db.ai_conversations.find_one({"org_id": org_id, "channel": "wa", "contact.phone": conv["contact_phone"]}, {"_id": 0})
    return c or await conversations.create(org_id, svc_user["id"], role="sales", channel="wa", title=conv.get("contact_name"),
                                           contact={"phone": conv["contact_phone"], "lead_id": conv.get("lead_id"),
                                                    "conversation_id": conv["id"]})


def _risky(text: str, phone: str) -> list:
    flags = []
    if RISKY.search(text or ""):
        flags.append("janji_atau_diskon")
    if any(d not in re.sub(r"\D", "", phone or "") for d in LONG_DIGITS.findall(text or "")):
        flags.append("angka_panjang_mirip_data_pribadi")
    return flags


async def _generate(ctx: ToolContext, ai_conv_id: str, text: str) -> dict:
    """Jalankan agen peran `sales`; kembalikan {text, basis, actions, error}."""
    basis, actions, err, msg_id, deltas = [], [], None, None, []
    async for ev in run_turn(ctx, ai_conv_id, [{"type": "text", "text": text}]):
        t = ev["type"]
        if t == "step_started" and ev["label"] not in basis:
            basis.append(ev["label"])
        elif t == "action_proposed":
            actions.append(ev["action"]["id"])
        elif t == "text_delta":
            deltas.append(ev["text"])
        elif t == "done":
            msg_id = ev["message_id"]
        elif t == "error":
            err = ev["message"]
    out = ""
    if msg_id:
        m = await db.ai_messages.find_one({"id": msg_id}, {"_id": 0})
        out = "".join(b.get("text", "") for b in (m or {}).get("content") or [] if b.get("type") == "text").strip()
    return {"text": out or ("".join(deltas).strip() if not err else ""), "basis": basis, "actions": actions, "error": err}


async def _auto_allowed(org_id: str, conv_id: str, category: str, mode: str, flags: list, actions: list) -> tuple:
    if mode != "auto":
        return False, "mode bukan otomatis"
    if flags or actions:
        return False, "ada penanda risiko/usulan aksi"
    ch = await drafts.last_inbound_channel(conv_id)
    if ch not in drafts.OFFICIAL:
        return False, "kanal bukan resmi"
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not gw.window_open(conv):
        return False, "jendela 24 jam tertutup"
    if (await budget.budget_state(org_id))["state"] == "stop":
        return False, "anggaran habis"
    ok, why = await accuracy.can_enable_auto(org_id, category)
    return (True, "") if ok else (False, why)


async def _finish(org_id: str, conv: dict, tri: dict, mode: str, text: str, *, basis, flags, actions, with_notice, ai_conv_id) -> dict:
    cat = tri["category"]
    channel = await drafts.last_inbound_channel(conv["id"])
    flags = list(flags) + (["ada_usulan_aksi"] if actions else [])
    d = await drafts.create(org_id, conv, category=cat, mode=mode, text=text, basis=basis, flags=flags,
                            with_notice=with_notice, channel=channel, ai_conversation_id=ai_conv_id)
    ok, why = await _auto_allowed(org_id, conv["id"], cat, mode, flags, actions)
    if ok:
        try:
            await drafts.dispatch(org_id, conv["id"], text, actor="ai-auto", with_notice=with_notice)
        except drafts.DraftError as e:
            ok, why = False, e.message
    if ok:
        sampled = await accuracy.maybe_sample(d)
        await db.ai_drafts.update_one({"id": d["id"]}, {"$set": {"status": "auto_sent", "sampled": sampled, "final_text": text,
                                                                  "sent_at": now_iso()}})
        await drafts.set_label(conv["id"], "auto_replied", triage.CATEGORY_INFO[cat][0])
        return {"status": "auto_sent", "draft_id": d["id"], "category": cat, "sampled": sampled}
    await drafts.set_label(conv["id"], "draft_ready", triage.CATEGORY_INFO[cat][0])
    return {"status": "draft", "draft_id": d["id"], "category": cat, "auto_blocked": why}


# ---------------------------------------------------------------- inti
async def process_job(job: dict) -> dict:
    org = job["org_id"]
    conv = await db.conversations.find_one({"id": job["conversation_id"], "org_id": org}, {"_id": 0})
    if not conv:
        return {"status": "skipped", "reason": "percakapan tidak ada"}
    phone = conv["contact_phone"]
    msg = await db.messages.find_one({"id": job.get("message_id")}, {"_id": 0}) or {}
    text = job.get("text") or msg.get("body") or ""
    if (await config.get_ai_settings(org))["effective_mode"] == "off":
        return {"status": "off"}
    if (await consent.state(org, phone))["stopped"]:
        return {"status": "stopped"}  # STOP: tidak ada AI sama sekali
    if (await budget.budget_state(org))["state"] == "stop":
        await drafts.set_label(conv["id"], "needs_sales", "Anggaran AI habis")
        return {"status": "budget_stop"}

    lead_id = job.get("lead_id") or conv.get("lead_id")
    pending = conv.get("ai_pending_verify")
    if pending and re.fullmatch(r"\s*\d{4}\s*", text):  # jawaban verifikasi: 4 digit tidak dikirim ke model
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {"ai_pending_verify": None}})
        if await identity.check(org, phone, text):
            text, tri = pending["text"], {"category": pending["category"], "intent": "", "objections": [], "sentiment": "netral", "confidence": 1.0}
        elif await identity.is_locked(org, phone):
            return await _handoff(org, conv, "tagihan_pembayaran", "Verifikasi identitas terkunci")
        else:
            await db.conversations.update_one({"id": conv["id"]}, {"$set": {"ai_pending_verify": pending}})
            tri = {"category": pending["category"], "intent": "", "objections": [], "sentiment": "netral", "confidence": 1.0}
            modes = await ss.get("ai.category_modes", org_id=org)
            return await _finish(org, conv, tri, (modes or {}).get(tri["category"], "draft"), DEFAULT_ANSWER_FAIL,
                                 basis=["Verifikasi identitas"], flags=[], actions=[], with_notice=False, ai_conv_id=None)
    else:
        hist = await db.messages.find({"conversation_id": conv["id"], "id": {"$ne": job.get("message_id")}}, {"_id": 0, "direction": 1, "body": 1}) \
            .sort("created_at", -1).limit(8).to_list(8)
        tri = await triage.classify(org, text, list(reversed(hist)))

    cat = tri["category"]
    await insights.update(org, lead_id, tri, conv)
    if tri["sentiment"] == "negatif":  # sinyal negatif setelah balasan otomatis -> turunkan kategorinya
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        prev = await db.ai_drafts.find_one({"conversation_id": conv["id"], "status": "auto_sent", "at": {"$gte": since}},
                                           {"_id": 0}, sort=[("at", -1)])
        if prev:
            await accuracy.check_demote(org, prev["category"], negative_signal=True)
    if cat in triage.LOCKED:
        return await _handoff(org, conv, cat, triage.CATEGORY_INFO[cat][0])
    mode = ((await ss.get("ai.category_modes", org_id=org)) or {}).get(cat, "draft")
    if mode == "off":
        return {"status": "off_category", "category": cat}

    verified = await identity.is_verified(org, phone)
    svc = await internal_api.service_user(org)
    ai_conv = await _ai_conversation(org, conv, svc)
    notice = None if (await consent.state(org, phone))["noticed_at"] else await consent.notice_text(org)

    def prefixed(t: str) -> str:
        return f"{notice}\n\n{t}" if notice else t

    if cat in PERSONAL and not verified:  # tawarkan verifikasi; jangan sentuh data pribadi
        if await identity.is_locked(org, phone):
            return await _handoff(org, conv, cat, "Verifikasi identitas terkunci")
        q = (await identity.start(org, phone))["question"]
        await db.conversations.update_one({"id": conv["id"]}, {"$set": {"ai_pending_verify": {"category": cat, "text": text}}})
        return await _finish(org, conv, tri, mode, prefixed(f"Untuk menjaga keamanan data Anda, kami perlu verifikasi dulu. {q}"),
                             basis=["Verifikasi identitas"], flags=[], actions=[], with_notice=bool(notice), ai_conv_id=ai_conv["id"])

    ctx = ToolContext(org_id=org, user=svc, token=await internal_api.service_token(org), channel="wa", conversation_id=ai_conv["id"],
                      contact={"phone": phone, "lead_id": lead_id, "buyer_customer_id": await identity.verified_customer_id(org, phone)},
                      verified=verified, role="sales")
    gen = await _generate(ctx, ai_conv["id"], text)
    if not gen["text"]:
        await drafts.set_label(conv["id"], "needs_sales", "AI belum bisa membuat draf")
        return {"status": "error", "category": cat, "error": gen["error"]}
    return await _finish(org, conv, tri, mode, prefixed(gen["text"]), basis=gen["basis"], flags=_risky(gen["text"], phone),
                         actions=gen["actions"], with_notice=bool(notice), ai_conv_id=ai_conv["id"])
