"""Pelacakan biaya & anggaran AI. Tarif USD per juta token."""
import logging
from datetime import datetime, timezone

import settings_store as ss
from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("estora.ai.budget")

# model -> (input, output, cache_read) USD/MTok. Cache write = 1.25x input (5 menit).
PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 0.10),  # model fallback sisi server
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
WARN_PCT, STOP_PCT = 80.0, 100.0
WEB_SEARCH_USD_PER_1000 = 10.0


def cost_usd(model: str, usage: dict) -> float:
    if model not in PRICES:
        logger.warning("Model %r tak dikenal; memakai tarif Opus", model)
    p_in, p_out, p_cr = PRICES.get(model) or PRICES["claude-opus-5-5"]
    u = usage or {}
    web = ((u.get("server_tool_use") or {}).get("web_search_requests") or 0)
    inp = u.get("input_tokens") or 0
    out = u.get("output_tokens") or 0
    cr = u.get("cache_read_input_tokens") or 0
    cw = u.get("cache_creation_input_tokens") or 0
    return (inp * p_in + out * p_out + cr * p_cr + cw * p_in * 1.25) / 1_000_000 + web * WEB_SEARCH_USD_PER_1000 / 1000


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def record_usage(org_id: str, *, model: str, usage: dict, context: dict) -> dict:
    rate = await ss.get("ai.usd_idr", org_id=org_id)
    usd = cost_usd(model, usage)
    u = usage or {}
    doc = {"id": new_id(), "org_id": org_id, "model": model, "month": _month(),
           "input_tokens": u.get("input_tokens") or 0, "output_tokens": u.get("output_tokens") or 0,
           "cache_read_tokens": u.get("cache_read_input_tokens") or 0,
           "cache_write_tokens": u.get("cache_creation_input_tokens") or 0,
           "cost_usd": usd, "cost_idr": round(usd * rate), "at": now_iso(), "context": context or {}}
    await db.ai_usage.insert_one(dict(doc))
    doc.pop("_id", None)
    await _maybe_warn(org_id)
    return doc


async def month_spend_idr(org_id: str = ORG_ID) -> int:
    rows = await db.ai_usage.aggregate([
        {"$match": {"org_id": org_id, "month": _month()}},
        {"$group": {"_id": None, "t": {"$sum": "$cost_idr"}}}]).to_list(1)
    return int(rows[0]["t"]) if rows else 0


async def budget_state(org_id: str = ORG_ID) -> dict:
    limit = int(await ss.get("ai.budget_idr_month", org_id=org_id))
    spent = await month_spend_idr(org_id)
    pct = (spent / limit * 100.0) if limit > 0 else 100.0
    state = "stop" if pct >= STOP_PCT else "warn" if pct >= WARN_PCT else "ok"
    return {"state": state, "spent_idr": spent, "limit_idr": limit, "pct": round(pct, 2)}


async def _maybe_warn(org_id: str) -> None:
    st = await budget_state(org_id)
    if st["state"] == "ok":
        return
    month = _month()
    # Klaim atomik: hanya satu pemanggil yang berhasil menyisipkan per org per bulan.
    res = await db.ai_budget_alerts.update_one(
        {"org_id": org_id, "month": month}, {"$setOnInsert": {"id": new_id(), "at": now_iso()}}, upsert=True)
    if res.upserted_id is None:
        return
    from engine import create_notification
    body = (f"Pemakaian AI bulan ini Rp{st['spent_idr']:,} dari anggaran Rp{st['limit_idr']:,} "
            f"({st['pct']:.0f}%).").replace(",", ".")
    async for u in db.users.find({"org_id": org_id, "role": {"$in": ["super_admin", "owner"]},
                                  "is_active": {"$ne": False}}, {"_id": 0, "email": 1}):
        await create_notification(user_email=u["email"], title="Anggaran Estora AI hampir habis",
                                  body=body, type="warning", related_entity_type="ai_budget",
                                  related_entity_id=month, org_id=org_id)
