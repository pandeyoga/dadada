"""Konfigurasi Estora AI: setting, kunci API terenkripsi, mode per kategori."""
import logging

import settings_store as ss
from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("estora.ai.config")

ACCOUNT_CODE = "anthropic"
CATEGORY_MODES = ("auto", "draft", "off")
_SIMPLE = ("mode", "model_main", "model_triage", "effort_copilot", "effort_wa", "effort_triage",
           "budget_idr_month", "usd_idr", "accuracy_threshold", "accuracy_min_samples",
           "accuracy_window_days", "auto_sample_rate", "kpr_max_installment_ratio",
           "web_research_enabled", "privacy_notice", "verification_ttl_days", "category_modes",
           "portal_enabled", "portal_daily_limit", "portal_notice")

# Dihubungkan di Task 10: async (org_id, category) -> bool (ai.accuracy.can_enable_auto).
_auto_validator = None


def set_auto_validator(fn) -> None:
    global _auto_validator
    _auto_validator = fn


async def get_api_key(org_id: str = ORG_ID):
    from wa_gateway import decrypt
    row = await db.channel_accounts.find_one({"org_id": org_id, "code": ACCOUNT_CODE}, {"_id": 0})
    enc = (row or {}).get("api_key_enc")
    return (decrypt(enc) or None) if enc else None


async def save_api_key(org_id: str, key: str, actor: str) -> None:
    from wa_gateway import encrypt
    key = (key or "").strip()
    if not key:
        raise ValueError("Kunci API kosong.")
    ts = now_iso()
    res = await db.channel_accounts.update_one(
        {"org_id": org_id, "code": ACCOUNT_CODE},
        {"$set": {"api_key_enc": encrypt(key), "updated_by": actor, "updated_at": ts, "key_last4": key[-4:]},
         "$setOnInsert": {"id": new_id(), "org_id": org_id, "code": ACCOUNT_CODE, "created_at": ts}},
        upsert=True)
    logger.info("Kunci API Anthropic disimpan oleh %s (%s)", actor, "baru" if res.upserted_id else "ganti")


async def get_ai_settings(org_id: str = ORG_ID) -> dict:
    out = {}
    for k in _SIMPLE:
        out[k] = await ss.get(f"ai.{k}", org_id=org_id)
    mode = out["mode"]
    has_key = bool(await get_api_key(org_id))
    out["has_api_key"] = has_key
    if mode == "off":
        out["effective_mode"] = "off"
    elif mode == "live" and has_key:
        out["effective_mode"] = "live"
    else:
        out["effective_mode"] = "simulation"
    return out


async def set_category_mode(org_id: str, category: str, mode: str, actor: str) -> dict:
    if mode not in CATEGORY_MODES:
        raise ValueError(f"Mode kategori tidak valid: {mode}")
    cur = dict(await ss.get("ai.category_modes", org_id=org_id))
    if mode == "auto" and cur.get(category) != "auto":
        ok = await _auto_validator(org_id, category) if _auto_validator else False
        if not ok:
            raise ValueError("Mode auto belum boleh diaktifkan: akurasi belum memenuhi ambang.")
    cur[category] = mode
    await ss.set_value("ai.category_modes", cur, actor=actor, reason=f"{category}={mode}", org_id=org_id)
    return cur
