"""KEB-PDPT (Sesi #090) — Laporan Uang Muka Pelanggan.

Saldo 2-1400 per pelanggan dari dua sumber:
* **Uang muka pesanan** — pembayaran ber-`gl_bucket=advance` yang belum direklas ke Piutang
  (barang belum keluar), per pesanan, dengan umur sejak kwitansi tertua.
* **Deposit / kelebihan bayar** — `customers.deposit_balance` (kas tak teralokasi, FASE G-3).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db import db
from core_utils import now_iso, safe_doc
from services import gl_service as _gl

EPS = 0.01


def _age_days(iso: str) -> int:
    if not iso:
        return 0
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - d).days)
    except Exception:  # noqa: BLE001
        return 0


def _bucket(days: int) -> str:
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


async def advance_report(entity_id: Optional[Any] = None, q: str = "") -> Dict[str, Any]:
    flt: Dict[str, Any] = {"payments.gl_bucket": _gl.ADVANCE_BUCKET,
                           "status": {"$nin": list(_gl.DEAD_STATUSES)}}
    if entity_id and entity_id != "all":
        flt["entity_id"] = entity_id
    orders = await db.sales_orders.find(flt, {"_id": 0, "items": 0}).to_list(5000)

    per_cust: Dict[str, Dict[str, Any]] = {}
    for o in orders:
        tertahan = await _gl.order_advance_unrecognized(o)
        if tertahan <= EPS:
            continue
        adv_pay = [p for p in (o.get("payments") or []) if p.get("gl_bucket") == _gl.ADVANCE_BUCKET]
        oldest = min((p.get("date") or p.get("created_at") or "" for p in adv_pay), default="")
        age = _age_days(oldest)
        rec = await _gl.order_revenue_recognized(o["id"])
        grand = float(o.get("grand_total") or o.get("total_amount") or 0)
        row = {
            "order_id": o["id"], "order_number": o.get("number", ""), "status": o.get("status", ""),
            "entity_id": o.get("entity_id", ""), "grand_total": round(grand, 2),
            "paid_total": round(float(o.get("paid_total") or 0), 2),
            "advance_total": _gl.order_advance_total(o), "advance_unrecognized": tertahan,
            "revenue_recognized_pct": round(100.0 * rec["ar"] / grand, 1) if grand > 0 else 0.0,
            "oldest_receipt_date": oldest, "age_days": age, "bucket": _bucket(age),
            "receipts": [{"receipt_number": p.get("receipt_number", ""), "amount": p.get("amount"),
                          "date": p.get("date") or p.get("created_at", "")} for p in adv_pay],
        }
        cid = o.get("customer_id", "")
        c = per_cust.setdefault(cid, {
            "customer_id": cid, "customer_name": o.get("customer_name", "—"),
            "advance_orders": 0.0, "deposit_balance": 0.0, "total": 0.0,
            "oldest_days": 0, "orders": []})
        c["orders"].append(row)
        c["advance_orders"] = round(c["advance_orders"] + tertahan, 2)
        c["oldest_days"] = max(c["oldest_days"], age)

    # deposit / kelebihan bayar (tak terikat pesanan)
    dep_flt: Dict[str, Any] = {"deposit_balance": {"$gt": EPS}}
    if entity_id and entity_id != "all":
        dep_flt["entity_id"] = entity_id
    async for cst in db.customers.find(dep_flt, {"_id": 0, "id": 1, "name": 1, "deposit_balance": 1}):
        c = per_cust.setdefault(cst["id"], {
            "customer_id": cst["id"], "customer_name": cst.get("name", "—"),
            "advance_orders": 0.0, "deposit_balance": 0.0, "total": 0.0, "oldest_days": 0, "orders": []})
        c["deposit_balance"] = round(float(cst.get("deposit_balance") or 0), 2)

    rows: List[Dict[str, Any]] = []
    ql = (q or "").strip().lower()
    for c in per_cust.values():
        c["total"] = round(c["advance_orders"] + c["deposit_balance"], 2)
        c["orders"].sort(key=lambda r: -r["age_days"])
        if ql and ql not in (c["customer_name"] or "").lower() and not any(
                ql in (r["order_number"] or "").lower() for r in c["orders"]):
            continue
        rows.append(c)
    rows.sort(key=lambda c: (-c["total"], -c["oldest_days"]))
    # Ringkasan mengikuti hasil filter supaya kartu metrik konsisten dengan tabel.
    tot_adv = round(sum(c["advance_orders"] for c in rows), 2)
    tot_dep = round(sum(c["deposit_balance"] for c in rows), 2)
    buckets = {k: 0.0 for k in ("0_30", "31_60", "61_90", "90_plus")}
    for c in rows:
        for r in c["orders"]:
            buckets[r["bucket"]] = round(buckets[r["bucket"]] + r["advance_unrecognized"], 2)
    return safe_doc({
        "generated_at": now_iso(),
        "filtered": bool(ql),
        "totals": {"advance_orders": tot_adv, "deposit_balance": tot_dep,
                   "liability": round(tot_adv + tot_dep, 2),
                   "customers": len(rows), "orders": sum(len(c["orders"]) for c in rows),
                   "buckets": buckets},
        "rows": rows,
    })
