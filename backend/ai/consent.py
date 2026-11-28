"""Persetujuan WhatsApp untuk Estora AI: pemberitahuan, kata kunci STOP/manusia/YA, opt-in per jenis.

Satu sumber kebenaran: koleksi `ai_consents` {org_id, phone, noticed_at, stopped, pending_optin, optins{unofficial, documents}}.
STOP juga mendaftarkan opt-out yang sudah ada (`wa_compliance.register_opt_out`), tidak membuat mekanisme kedua.
"""
import re

import settings_store as ss
import wa_compliance
from core_utils import new_id, normalize_phone_e164, now_iso
from db import db, ORG_ID

OPTIN_KINDS = ("unofficial", "documents")
HUMAN_WORDS = frozenset({"manusia", "sales", "cs", "staf", "staff"})
YES_WORDS = frozenset({"ya", "iya", "yes", "setuju", "ok", "oke"})
_WORD = re.compile(r"[a-zA-Z]+")


def _variants(phone: str) -> list:
    return list({phone, normalize_phone_e164(phone) or phone})


async def _doc(org_id: str, phone: str) -> dict:
    return await db.ai_consents.find_one({"org_id": org_id, "phone": {"$in": _variants(phone)}}, {"_id": 0}) or {}


async def state(org_id: str, phone: str) -> dict:
    d = await _doc(org_id, phone)
    o = d.get("optins") or {}
    stopped = bool(d.get("stopped")) or bool(await wa_compliance.is_opted_out(org_id, d.get("phone") or phone))
    return {"noticed_at": d.get("noticed_at"), "stopped": stopped, "pending_optin": d.get("pending_optin"),
            "optins": {"unofficial": bool(o.get("unofficial")), "documents": bool(o.get("documents"))}}


async def _set(org_id: str, phone: str, fields: dict) -> None:
    key = (await _doc(org_id, phone)).get("phone") or phone
    await db.ai_consents.update_one(
        {"org_id": org_id, "phone": key}, {"$set": {**fields, "updated_at": now_iso()},
                                          "$setOnInsert": {"id": new_id(), "created_at": now_iso()}}, upsert=True)


async def notice_text(org_id: str = ORG_ID) -> str:
    return await ss.get("ai.privacy_notice", org_id=org_id)


async def mark_noticed(org_id: str, phone: str) -> None:
    await _set(org_id, phone, {"noticed_at": now_iso()})


async def ask_optin(org_id: str, phone: str, kind: str) -> None:
    """Catat bahwa AI baru menanyakan opt-in `kind`; balasan 'YA' berikutnya berlaku untuk jenis itu."""
    if kind not in OPTIN_KINDS:
        raise ValueError("Jenis opt-in tidak dikenal.")
    await _set(org_id, phone, {"pending_optin": kind})


async def resume(org_id: str, phone: str) -> None:
    """Staf mencabut penghentian AI untuk nomor ini."""
    await _set(org_id, phone, {"stopped": False})


async def handle_keyword(org_id: str, phone: str, text: str):
    """-> "stop" | "human" | "yes" | None."""
    if wa_compliance.detect_opt_out(text):
        await wa_compliance.register_opt_out(org_id, phone, source="ai_keyword")
        await _set(org_id, phone, {"stopped": True, "pending_optin": None})
        return "stop"
    words = [w.lower() for w in _WORD.findall(text or "")]
    if words and len(words) <= 4 and set(words) & HUMAN_WORDS:
        return "human"
    if words and len(words) <= 2 and words[0] in YES_WORDS:
        d = await _doc(org_id, phone)
        kind = d.get("pending_optin")
        if kind in OPTIN_KINDS:
            await _set(org_id, phone, {"optins": {**(d.get("optins") or {}), kind: True}, "pending_optin": None})
            return "yes"
    return None
