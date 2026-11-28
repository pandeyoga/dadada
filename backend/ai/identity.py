"""Verifikasi identitas pembeli di WhatsApp: nomor pengirim = nomor pembeli terdaftar + 4 digit terakhir NIK.

NIK tidak pernah dicatat/dikembalikan. Status di `ai_identity`. 3 jawaban salah -> kunci 24 jam + notifikasi CS.
"""
import hmac
import logging
from datetime import datetime, timedelta, timezone

import settings_store as ss
from core_utils import new_id, normalize_nik, normalize_phone_e164, now_iso
from db import db

logger = logging.getLogger("estora.ai.identity")
MAX_FAILS = 3
LOCK_HOURS = 24
QUESTION = "Untuk melindungi data Anda, mohon sebutkan 4 digit terakhir NIK (KTP) pembeli yang terdaftar."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _phones(phone: str) -> list:
    e = normalize_phone_e164(phone) or phone
    digits = "".join(c for c in e if c.isdigit())
    return list({phone, e, digits, "0" + digits[2:] if digits.startswith("62") else digits})


async def _buyer(org_id: str, phone: str):
    """Pembeli terdaftar dengan nomor ini (yang punya NIK). Mengandung NIK: jangan dikembalikan ke luar modul."""
    return await db.customers.find_one({"org_id": org_id, "phone": {"$in": _phones(phone)}, "nik": {"$nin": [None, ""]}},
                                       {"_id": 0, "id": 1, "nik": 1})


async def _row(org_id: str, phone: str) -> dict:
    return await db.ai_identity.find_one({"org_id": org_id, "phone": normalize_phone_e164(phone) or phone}, {"_id": 0}) or {}


async def _save(org_id: str, phone: str, fields: dict) -> None:
    p = normalize_phone_e164(phone) or phone
    await db.ai_identity.update_one({"org_id": org_id, "phone": p}, {"$set": {**fields, "updated_at": now_iso()},
                                    "$setOnInsert": {"id": new_id(), "created_at": now_iso()}}, upsert=True)


def _parse(ts):
    try:
        return datetime.fromisoformat(ts) if ts else None
    except ValueError:
        return None


async def is_locked(org_id: str, phone: str) -> bool:
    until = _parse((await _row(org_id, phone)).get("locked_until"))
    return bool(until and until > _now())


async def is_verified(org_id: str, phone: str) -> bool:
    exp = _parse((await _row(org_id, phone)).get("expires_at"))
    return bool(exp and exp > _now())


async def verified_customer_id(org_id: str, phone: str):
    """customer_id pembeli bila nomor ini terverifikasi (untuk `ToolContext.contact["buyer_customer_id"]`)."""
    return (await _row(org_id, phone)).get("customer_id") if await is_verified(org_id, phone) else None


async def start(org_id: str, phone: str) -> dict:
    if await is_locked(org_id, phone):
        return {"question": "Verifikasi dikunci sementara karena terlalu banyak jawaban salah. Staf kami akan membantu Anda."}
    return {"question": QUESTION}


async def _notify_cs(org_id: str, phone: str) -> None:
    try:
        from wa_inbound import _notify_admins
        await _notify_admins(org_id, "Verifikasi identitas WhatsApp terkunci",
                             f"3 jawaban salah dari nomor ...{phone[-4:]}. Terkunci {LOCK_HOURS} jam; mohon hubungi pembeli.")
    except Exception:  # noqa: BLE001
        logger.exception("Gagal mengirim notifikasi kunci verifikasi")


async def check(org_id: str, phone: str, answer: str) -> bool:
    if await is_locked(org_id, phone):
        return False
    buyer = await _buyer(org_id, phone)
    if not buyer:
        return False  # nomor tak terdaftar: tanpa penghitung percobaan (tidak membocorkan keberadaan nomor)
    nik = normalize_nik(buyer.get("nik") or "")
    given = normalize_nik(answer or "")
    ok = len(given) == 4 and len(nik) >= 4 and hmac.compare_digest(given, nik[-4:])
    if ok:
        ttl = int(await ss.get("ai.verification_ttl_days", org_id=org_id) or 30)
        await _save(org_id, phone, {"verified_at": now_iso(), "expires_at": (_now() + timedelta(days=ttl)).isoformat(),
                                    "customer_id": buyer["id"], "fails": 0, "locked_until": None})
        return True
    fails = int((await _row(org_id, phone)).get("fails") or 0) + 1
    if fails >= MAX_FAILS:
        await _save(org_id, phone, {"fails": 0, "locked_until": (_now() + timedelta(hours=LOCK_HOURS)).isoformat()})
        await _notify_cs(org_id, phone)
    else:
        await _save(org_id, phone, {"fails": fails})
    return False
