"""EPIC 1.7 + Fase 43 — Conversion API (CAPI) feedback loop, siap-live & jujur.

Saat lead/deal mencapai tonggak konversi, event-nya dikirim BALIK ke platform iklan
(Meta CAPI / Google Enhanced Conversions / TikTok Events API) supaya model optimasi mereka
belajar dari hasil nyata di hilir. Sumber non-iklan (walk-in, referral, manual) dilewati —
tidak ada loop yang perlu ditutup.

APA YANG DITAMBAHKAN FASE 43 (spec `docs/v2/30_MARKETING_INTEGRATION_SPEC.md` §6):

1. **`event_id` deduplikasi.** Platform membuang event kembar berdasarkan `event_id`. Tanpa
   ini, dispatcher yang mengulang event (retry) atau dua event bisnis yang terbit bersamaan
   (`deal.ajb` + `deal.sold`) akan membuat konversi dihitung DUA KALI — dan angka ROAS di
   layar ikut salah karena `conversion_events` juga sumber laporan atribusi. `event_id`
   dihitung deterministik dari (org, event, lead, deal), lalu dijaga index unik.
2. **`user_data` ter-hash SHA-256.** Nomor telepon dinormalkan E.164 lalu di-hash; email
   dihuruf-kecilkan lalu di-hash. Yang tersimpan di `conversion_events` hanya hash-nya, jadi
   dokumen ini boleh dibaca lebih banyak peran tanpa membocorkan data pribadi, DAN payload
   sudah berbentuk final yang diminta platform saat kredensial dinyalakan.
3. **`SubmitApplication`** saat SPR ditandatangani (sinyal lebih awal daripada booking).
5. **Conversions API for Business Messaging (CTWA).** Lead yang berasal dari iklan Click-to-WhatsApp
   (punya `ctwa_clid` hasil tangkapan webhook, lihat `ctwa.py`) TIDAK dikirim sebagai event Pixel
   `system_generated`, melainkan sebagai event percakapan: `action_source: "business_messaging"`,
   `messaging_channel: "whatsapp"`, `user_data` = {`whatsapp_business_account_id`, `ctwa_clid`}. Format
   yang salah membuat Meta tidak dapat mengaitkan penjualan ke iklan (audit 09 §4 celah 5). `event_id`
   deterministik dari (org, nama event Meta, `ctwa_clid`, deal) -> pengiriman ulang tidak dihitung dua
   kali. Tanpa token/dataset: simulasi — payload final dicatat di baris + log, tidak ada paket keluar.
4. **Status yang tidak berbohong.** Tanpa kredensial, event TIDAK dikirim ke mana pun, jadi
   statusnya `simulated` — bukan `sent`. Dulu semua baris berstatus "Terkirim" padahal tidak
   ada satu pun paket keluar; itu membuat layar audit tidak bisa dipercaya.
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from pymongo.errors import DuplicateKeyError

import ctwa as ctwa_mod
import wa_gateway as gw
from core_utils import new_id, normalize_phone_e164, now_iso
from db import db, ORG_ID

logger = logging.getLogger("sipro.capi")

# lead.source -> ad platform that should receive the feedback event.
PLATFORM_BY_SOURCE = {
    "meta_ads": "meta",
    "whatsapp": "meta",        # WhatsApp click-to-chat ads also report to Meta.
    "google_lead": "google",
    "tiktok_lead": "tiktok",
    "tiktok_ads": "tiktok",
    "website": "web_pixel",
}

# platform -> env var whose presence flips transport to LIVE (else simulation).
LIVE_ENV_BY_PLATFORM = {
    "meta": "META_CAPI_TOKEN",
    "google": "GOOGLE_ADS_CONV_TOKEN",
    "tiktok": "TIKTOK_EVENTS_TOKEN",
    "web_pixel": "WEB_PIXEL_TOKEN",
}

# Nama event SIPRO -> nama event Meta untuk percakapan WhatsApp (audit 09 §6 butir 10: lead -> Lead,
# lead berkualitas -> QualifiedLead, akad -> Purchase). ASUMSI: nama selain ketiganya dikirim apa adanya
# (event standar Meta); sesuaikan di sini bila dokumentasi Meta berubah — kontrak penyimpanan tidak berubah.
BM_EVENT_MAP = {"Lead": "Lead", "SubmitApplication": "QualifiedLead",
                "InitiateCheckout": "InitiateCheckout", "Purchase": "Purchase"}
BM_ACTION_SOURCE, BM_CHANNEL = "business_messaging", "whatsapp"

PLATFORM_LABEL = {
    "meta": "Meta (Conversions API)",
    "google": "Google (Enhanced Conversions)",
    "tiktok": "TikTok (Events API)",
    "web_pixel": "Web Pixel",
}

from meta_api import GRAPH_BASE as GRAPH  # noqa: E402 — satu konstanta versi (Fase 94B)
TIMEOUT = 10.0


def platform_for_source(source):
    return PLATFORM_BY_SOURCE.get((source or "").lower())


def _live(platform: str) -> bool:
    env = LIVE_ENV_BY_PLATFORM.get(platform)
    return bool(env and os.environ.get(env))


def sha256_of(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def hash_phone(phone: str) -> str:
    """E.164 tanpa '+' lalu SHA-256 — bentuk yang diminta Meta/Google."""
    if not phone:
        return None
    return sha256_of(normalize_phone_e164(phone).lstrip("+"))


def hash_email(email: str) -> str:
    if not email:
        return None
    return sha256_of(str(email).strip().lower())


def user_data_for(lead: dict) -> dict:
    """Payload identitas TER-HASH (kunci `ph`/`em` sesuai kontrak platform)."""
    out = {}
    ph = hash_phone((lead or {}).get("phone"))
    em = hash_email((lead or {}).get("email"))
    if ph:
        out["ph"] = ph
    if em:
        out["em"] = em
    return out


def event_id_for(*, org_id: str, event_name: str, lead_id: str = None,
                 deal_id: str = None) -> str:
    """ID event deterministik: peristiwa bisnis yang SAMA selalu menghasilkan ID yang sama,
    sehingga percobaan kedua (retry / event kembar) tidak dihitung dua kali."""
    raw = f"{org_id}|{event_name}|{lead_id or ''}|{deal_id or ''}"
    return sha256_of(raw)[:32]


def bm_event_id(*, org_id: str, platform_event: str, ctwa_clid: str, deal_id: str = None) -> str:
    """ID event Business Messaging: peristiwa & klik iklan yang SAMA selalu menghasilkan ID yang sama."""
    return sha256_of(f"{org_id}|bm|{platform_event}|{ctwa_clid}|{deal_id or ''}")[:32]


def build_bm_event(doc: dict) -> dict:
    """Satu objek `data[]` Conversions API for Business Messaging (fungsi murni; dipakai kirim & catatan simulasi)."""
    ud = doc.get("user_data") or {}
    name = doc.get("platform_event_name") or BM_EVENT_MAP.get(doc.get("event_name"), doc.get("event_name"))
    event = {
        "event_name": name, "event_time": int(doc.get("event_time") or time.time()),
        "event_id": doc["event_id"], "action_source": BM_ACTION_SOURCE, "messaging_channel": BM_CHANNEL,
        "user_data": {"whatsapp_business_account_id": ud.get("whatsapp_business_account_id"),
                      "ctwa_clid": ud.get("ctwa_clid")},
    }
    if name == "Purchase" or int(doc.get("value") or 0) > 0:
        event["custom_data"] = {"value": int(doc.get("value") or 0), "currency": doc.get("currency") or "IDR"}
    return event


def _bm_dataset() -> str:
    return os.environ.get("META_CAPI_DATASET_ID") or os.environ.get("META_PIXEL_ID") or ""


async def _post_json(url: str, payload: dict, token: str) -> tuple:
    """SATU-SATUNYA pintu jaringan keluar CAPI. -> (status_http, json|teks). Token lewat header (bukan
    query string) supaya tidak tercetak oleh log httpx. Tes mengganti fungsi ini dengan pengirim palsu."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    try:
        return res.status_code, res.json()
    except ValueError:
        return res.status_code, res.text[:200]


async def _waba_for(org_id: str, ctwa_doc: dict = None) -> str:
    """WABA ID: kredensial WhatsApp terkonfigurasi dulu, lalu ID dari entri webhook (bukan 'SIM-...')."""
    cfg = await gw.get_config(org_id)
    waba = cfg["creds"].get("waba_id") or ""
    if not waba:
        seen = str((ctwa_doc or {}).get("waba_id") or "")
        waba = seen if seen and not seen.upper().startswith("SIM") else ""
    return waba


async def _send_bm(doc: dict) -> tuple:
    dataset = _bm_dataset()
    if not dataset:
        return "pending", ("META_CAPI_TOKEN terisi tetapi META_CAPI_DATASET_ID (atau META_PIXEL_ID) belum — "
                           "Meta tidak tahu dataset WABA mana yang harus menerima event percakapan ini.")
    ud = doc.setdefault("user_data", {})
    if not ud.get("whatsapp_business_account_id"):
        ud["whatsapp_business_account_id"] = await _waba_for(doc.get("org_id", ORG_ID))
    if not ud.get("whatsapp_business_account_id") or not ud.get("ctwa_clid"):
        return "pending", ("whatsapp_business_account_id / ctwa_clid belum lengkap — isi WABA ID di "
                           "Pengaturan > WhatsApp lalu kirim ulang.")
    payload = {"data": [build_bm_event(doc)]}
    doc["payload"] = payload
    try:
        code, body = await _post_json(f"{GRAPH}/{dataset}/events", payload, os.environ["META_CAPI_TOKEN"])
    except Exception as exc:  # noqa: BLE001 — jaringan: laporkan apa adanya
        return "failed", f"Gagal menghubungi Meta: {exc}"
    if code == 200:
        return "sent", "Diterima Meta Conversions API (Business Messaging)."
    detail = ((body or {}).get("error") or {}).get("message") if isinstance(body, dict) else str(body)[:200]
    return "failed", f"Meta menolak event (HTTP {code}): {detail}"


async def _send_live(doc: dict) -> tuple:
    """Kirim event ke platform. -> (status, pesan). Hanya dipanggil saat kredensial ada."""
    platform = doc["platform"]
    if doc.get("action_source") == BM_ACTION_SOURCE:
        return await _send_bm(doc)
    if platform != "meta":
        return "pending", (f"Kredensial {PLATFORM_LABEL.get(platform, platform)} terpasang, "
                           "tetapi transport live untuk platform ini belum dipasang — event "
                           "tersimpan dan bisa dikirim ulang tanpa mengubah kontrak.")
    pixel = os.environ.get("META_PIXEL_ID")
    if not pixel:
        return "pending", ("META_CAPI_TOKEN terisi tetapi META_PIXEL_ID belum — Meta tidak "
                           "tahu ke pixel mana event ini harus masuk.")
    payload = {"data": [{
        "event_name": doc["event_name"],
        "event_time": int(datetime.now(timezone.utc).timestamp()),
        "event_id": doc["event_id"], "action_source": "system_generated",
        "user_data": doc.get("user_data") or {},
        "custom_data": {"value": doc.get("value") or 0,
                        "currency": doc.get("currency") or "IDR"},
    }]}
    try:
        code, body = await _post_json(f"{GRAPH}/{pixel}/events", payload, os.environ["META_CAPI_TOKEN"])
        if code == 200:
            return "sent", "Diterima Meta Conversions API."
        detail = ((body or {}).get("error") or {}).get("message") if isinstance(body, dict) else str(body)[:200]
        return "failed", f"Meta menolak event (HTTP {code}): {detail}"
    except Exception as exc:  # noqa: BLE001 — jaringan: laporkan apa adanya
        return "failed", f"Gagal menghubungi Meta: {exc}"


async def record_conversion(*, event_name, lead=None, deal=None, value=0,
                            currency="IDR", org_id=ORG_ID):
    """Tulis satu baris `conversion_events` + kirim balik ke platform (bila live).

    `event_name` memakai taksonomi iklan: 'Lead', 'SubmitApplication', 'InitiateCheckout',
    'Purchase'. Mengembalikan dokumen tersimpan, atau None bila sumbernya tidak bisa
    dilacak ke platform iklan. Idempoten: peristiwa yang sama tidak pernah tersimpan dua kali.
    """
    lead = lead or {}
    source = lead.get("source")
    platform = platform_for_source(source)
    # Lead dari iklan Click-to-WhatsApp (punya ctwa_clid): umpan balik wajib berbentuk
    # Conversions API for Business Messaging, apa pun kolom `source`-nya.
    ctwa_doc = await ctwa_mod.resolve(lead, org_id) if lead.get("id") else None
    if ctwa_doc:
        platform = "meta"
    if not platform:
        return None  # organic / manual channel — no loop to close.
    if ctwa_doc:
        bm_name = BM_EVENT_MAP.get(event_name, event_name)
        event_id = bm_event_id(org_id=org_id, platform_event=bm_name, ctwa_clid=ctwa_doc["ctwa_clid"],
                               deal_id=(deal or {}).get("id"))
    else:
        event_id = event_id_for(org_id=org_id, event_name=event_name, lead_id=lead.get("id"),
                                deal_id=(deal or {}).get("id"))
    existing = await db.conversion_events.find_one({"org_id": org_id, "event_id": event_id},
                                                  {"_id": 0})
    if existing:
        logger.info("[CAPI dedup] event %s sudah ada (%s) — tidak dihitung dua kali",
                    event_name, event_id)
        return {**existing, "duplicate": True}
    ts = now_iso()
    attribution = lead.get("attribution") or {}
    live = _live(platform)
    doc = {
        "id": new_id(), "org_id": org_id, "platform": platform,
        "platform_label": PLATFORM_LABEL.get(platform, platform),
        "event_name": event_name, "event_id": event_id,
        "source": source, "campaign": lead.get("campaign"),
        "campaign_id": attribution.get("campaign_id"),
        "adset_id": attribution.get("adset_id"), "ad_id": attribution.get("ad_id"),
        "creative_id": attribution.get("creative_id"),
        "lead_id": lead.get("id"), "deal_id": (deal or {}).get("id"),
        "value": int(value or 0), "currency": currency,
        "transport": "live" if live else "simulation",
        "user_data": user_data_for(lead),
        "status": "sent" if not live else "pending",
        "message": None, "attempts": 0, "last_attempt_at": None,
        "sent_at": ts, "created_at": ts,
    }
    if ctwa_doc:
        doc.update({
            "action_source": BM_ACTION_SOURCE, "messaging_channel": BM_CHANNEL,
            "platform_event_name": bm_name, "event_time": int(time.time()),
            "ctwa_clid": ctwa_doc["ctwa_clid"], "ctwa_source_id": ctwa_doc.get("source_id"),
            "user_data": {"whatsapp_business_account_id": await _waba_for(org_id, ctwa_doc) or None,
                          "ctwa_clid": ctwa_doc["ctwa_clid"]}})
        doc["payload"] = {"data": [build_bm_event(doc)]}
    if not live:
        # Tanpa kredensial tidak ada paket yang keluar: katakan apa adanya.
        doc["status"] = "simulated"
        doc["message"] = ("Mode simulasi: event dicatat lengkap (termasuk hash identitas) dan "
                          "siap dikirim begitu kredensial platform diisi.")
        if ctwa_doc:
            doc["message"] = ("Mode simulasi (dry-run) Business Messaging: payload final dicatat di baris ini "
                              "dan di log; tidak ada paket keluar sampai META_CAPI_TOKEN + dataset diisi.")
            logger.info("[CAPI BM dry-run] %s", json.dumps(doc["payload"], ensure_ascii=False))
    try:
        # Sisipkan DULU (indeks unik org+event_id = pagar atomik), baru kirim: dua pemicu bersamaan
        # tidak bisa sama-sama mengirim; yang kalah mendapat baris pemenang sebagai duplikat.
        await db.conversion_events.insert_one(dict(doc))
    except DuplicateKeyError:
        won = await db.conversion_events.find_one({"org_id": org_id, "event_id": event_id}, {"_id": 0})
        return {**(won or doc), "duplicate": True}
    if live:
        status, message = await _send_live(doc)
        doc.update({"status": status, "message": message, "attempts": 1, "last_attempt_at": now_iso()})
        await db.conversion_events.update_one({"id": doc["id"]}, {"$set": {
            k: doc[k] for k in ("status", "message", "attempts", "last_attempt_at", "user_data", "payload")
            if k in doc}})
    doc.pop("_id", None)
    logger.info("[CAPI %s/%s] platform=%s event=%s value=%s campaign=%s lead=%s",
                doc["transport"], doc["status"], platform, event_name, value,
                doc.get("campaign"), lead.get("id"))
    return doc


async def resend_conversion(event_row_id: str, *, org_id=ORG_ID, actor="system"):
    """Kirim ulang satu event. Di mode simulasi tidak ada yang dikirim — dan itu dikatakan."""
    doc = await db.conversion_events.find_one({"id": event_row_id, "org_id": org_id},
                                              {"_id": 0})
    if not doc:
        raise ValueError("Event konversi tidak ditemukan.")
    platform = doc.get("platform")
    if not _live(platform):
        raise ValueError(
            f"{PLATFORM_LABEL.get(platform, platform)} masih mode simulasi "
            f"({LIVE_ENV_BY_PLATFORM.get(platform, 'token')} belum diisi) — tidak ada yang "
            "bisa dikirim ulang. Event tetap tersimpan dan akan bisa dikirim setelah "
            "kredensial dipasang.")
    doc.setdefault("user_data", {})
    status, message = await _send_live(doc)
    ts = now_iso()
    await db.conversion_events.update_one({"id": event_row_id}, {
        "$set": {"status": status, "message": message, "transport": "live",
                 "last_attempt_at": ts, "resent_by": actor,
                 **{k: doc[k] for k in ("user_data", "payload") if k in doc}},
        "$inc": {"attempts": 1}})
    return await db.conversion_events.find_one({"id": event_row_id}, {"_id": 0})
