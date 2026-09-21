"""KN-D11 (audit 2026-09-21) — SATU definisi ATP (Available-to-Promise) untuk seluruh sistem.

Sebelumnya ada tiga rumus berlabel "ATP":
  • roll_service.rebuild_balance      : available + incoming (horizon penuh, tanpa kurang demand)
  • fulfillment_service (wizard)      : available + incoming (tanpa interco, tanpa demand)
  • stock_bucket_service.atp_detail   : available + incoming(≤14 hari) − backorder

Definisi tunggal (dipakai ketiganya):
    ATP = available + incoming_dalam_horizon − permintaan_backorder_aktif
  - available        : bucket `available_qty` (reservasi sudah keluar)
  - incoming         : in_transit_inbound + PO terbuka (OPEN_PO_STATUSES) + pembelian antar-PT,
                       hanya yang ETA ≤ ATP_HORIZON_DAYS (ETA kosong dianggap dalam horizon,
                       karena PO tanpa tanggal tetap pasokan nyata yang sedang berjalan)
  - permintaan       : Σ `backorders[].backorder_qty` aktif (status ≠ fulfilled) pesanan
                       ber-`has_backorder` yang belum terpenuhi (ACTIVE_BACKORDER_STATUSES)
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

from db import db

ATP_HORIZON_DAYS = 14
ACTIVE_BACKORDER_STATUSES = ["waiting_stock", "reserved", "waiting_approval", "approved",
                             "confirmed", "partially_picked", "partially_shipped"]


def compute_atp(available: float, incoming_in_horizon: float, pending_demand: float) -> float:
    return round(float(available or 0) + float(incoming_in_horizon or 0) - float(pending_demand or 0), 2)


def within_horizon(eta: Optional[str], now: Optional[datetime] = None,
                   horizon_days: int = ATP_HORIZON_DAYS) -> bool:
    """ETA kosong/tak terbaca = dalam horizon (pasokan nyata tanpa tanggal)."""
    if not eta:
        return True
    try:
        dt = datetime.fromisoformat(str(eta).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return True
    now = now or datetime.now(timezone.utc)
    return dt <= now + timedelta(days=max(1, int(horizon_days or ATP_HORIZON_DAYS)))


async def pending_backorder_qty(product_id: str, owner_entity_id: str,
                                warehouse_id: Optional[str] = None) -> float:
    """Σ backorder aktif product×entitas (opsional ×gudang) dalam satuan dasar."""
    q: Dict[str, Any] = {"has_backorder": True, "backorders.product_id": product_id,
                         "status": {"$in": ACTIVE_BACKORDER_STATUSES}}
    if owner_entity_id:
        q["entity_id"] = owner_entity_id
    total = 0.0
    async for so in db.sales_orders.find(q, {"_id": 0, "backorders": 1, "warehouse_id": 1}):
        for bo in so.get("backorders", []) or []:
            if bo.get("product_id") != product_id or bo.get("status") == "fulfilled":
                continue
            if warehouse_id and (bo.get("warehouse_id") or so.get("warehouse_id")) not in (None, "", warehouse_id):
                continue
            total += float(bo.get("backorder_qty", 0) or 0)
    return round(total, 2)


def sum_incoming_in_horizon(rows: Iterable[Dict[str, Any]], horizon_days: int = ATP_HORIZON_DAYS) -> float:
    now = datetime.now(timezone.utc)
    return round(sum(float(r.get("qty", 0) or 0) for r in rows if within_horizon(r.get("eta"), now, horizon_days)), 2)
