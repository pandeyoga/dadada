"""REVISI SAMPEL (klien 17 Sep) — Pesanan Sampel (SOS-) terpisah dari SO roll biasa.

Alur: POS (sales pilih "Order Sampel", gratis/berbayar) → berbayar: persetujuan pembayaran
Finance/Admin Sampel → Admin Sampel meneruskan ke gudang (confirm → tugas `sample_cut`)
→ gudang pindai roll RFID, potong, catat panjang → packing → kirim / diambil.
Dokumennya tetap di koleksi `sales_orders` (order_type="sample") supaya gudang, SJ, dan
riwayat pelanggan memakai mesin yang sama; yang berbeda: nomor, penyetuju, meja kerja.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core_utils import now_iso, safe_doc, strip_cost_fields
from db import db
from dependencies import audit, require_permission
from entity_scope import assert_active_entity_access, entity_ctx, resolve_list_scope
from services import sales_ownership, so_approvals
from services.fulfillment_status import create_outbound_tasks_for_order, recompute_so_status
from services.sales_order_helpers import norm_backorder, so_transition
from services.sample_sale_service import SAMPLE_LIMITS, SAMPLE_PAYMENT_APPROVERS
from services.work_desk_service import _age_days, _queue, _row

router = APIRouter(prefix="/api")

ACTIVE = ["waiting_approval", "approved", "confirmed", "partially_picked", "picked", "partially_shipped", "shipped"]


class NoteIn(BaseModel):
    note: str = ""


def _base_q(ctx, entity_id: Optional[str]) -> Dict[str, Any]:
    return resolve_list_scope("sales_orders", {"order_type": "sample"}, ctx, entity_id)


async def _load(order_id: str, request: Request) -> Dict[str, Any]:
    order = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan sampel tidak ditemukan")
    if order.get("order_type") != "sample":
        raise HTTPException(status_code=400, detail=f"{order.get('number')} bukan pesanan sampel — gunakan alur SO biasa.")
    # KN-A07 — kembali ke penjaga KETAT (aktif), seketat daftarnya (R-3a).
    assert_active_entity_access(order, "sales_orders", await entity_ctx(request))
    return order


@router.get("/sample-orders/limits")
async def sample_limits(request: Request) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    return SAMPLE_LIMITS


@router.get("/sample-orders")
async def list_sample_orders(request: Request, status: str = None, entity_id: str = None,
                             mine: Optional[bool] = None, customer_id: str = None) -> List[Dict[str, Any]]:
    actor = await require_permission(request, "sample_order", "view")
    q = _base_q(await entity_ctx(request), entity_id)
    if status:
        parts = [s.strip() for s in status.split(",") if s.strip()]
        q["status"] = parts[0] if len(parts) == 1 else {"$in": parts}
    if customer_id:
        q["customer_id"] = customer_id
    q = sales_ownership.apply_scope(q, actor, mine)
    rows = await db.sales_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(300)
    return strip_cost_fields([norm_backorder(safe_doc(o)) for o in rows], actor.get("role"))


@router.get("/sample-orders/stats/summary")
async def sample_stats(request: Request, entity_id: str = None, mine: Optional[bool] = None) -> Dict[str, Any]:
    actor = await require_permission(request, "sample_order", "view")
    q = sales_ownership.apply_scope(_base_q(await entity_ctx(request), entity_id), actor, mine)
    rows = await db.sales_orders.find(q, {"_id": 0, "status": 1, "sample_billing": 1, "grand_total": 1}).to_list(2000)
    by_status: Dict[str, int] = {}
    for r in rows:
        by_status[r.get("status", "")] = by_status.get(r.get("status", ""), 0) + 1
    return {"total": len(rows), "by_status": by_status,
            "free": sum(1 for r in rows if r.get("sample_billing") == "free"),
            "paid": sum(1 for r in rows if r.get("sample_billing") == "paid"),
            "paid_value": round(sum(float(r.get("grand_total") or 0) for r in rows if r.get("sample_billing") == "paid"), 2)}


def _rows(docs: List[Dict[str, Any]], action: str, kind: str) -> List[Dict[str, Any]]:
    out = []
    for o in docs:
        items = o.get("items") or []
        sub = " · ".join(f"{i.get('product_name')} {float(i.get('quantity') or 0):g} {i.get('base_unit') or i.get('unit') or ''}" for i in items[:3])
        cut = sum(1 for i in items if i.get("sample_cut_status") == "cut")
        out.append(_row(ref_type="sample_order", ref_id=o["id"], number=o.get("number", ""), title=o.get("customer_name", "—"),
                        subtitle=f"{'GRATIS' if o.get('sample_billing') == 'free' else 'BERBAYAR'} · {sub}" + (f" · dipotong {cut}/{len(items)}" if cut else ""),
                        value=float(o.get("grand_total") or 0), age_days=_age_days(o.get("updated_at") or o.get("created_at")),
                        badge=o.get("status", ""), action=action, action_kind=kind,
                        extra={"sales_name": o.get("sales_name"), "fulfillment_method": o.get("fulfillment_method"), "items": len(items)}))
    return out


@router.get("/sample-orders/desk")
async def sample_desk(request: Request, entity_id: str = None) -> Dict[str, Any]:
    """Meja Admin Sampel — antrean per tahap, satu tindakan per baris."""
    actor = await require_permission(request, "sample_order", "view")
    q = _base_q(await entity_ctx(request), entity_id)

    async def find(extra: Dict[str, Any]):
        return await db.sales_orders.find({**q, **extra}, {"_id": 0}).sort("created_at", 1).to_list(200)

    bayar = await find({"status": "waiting_approval", "sample_billing": "paid"})
    siap = await find({"status": "approved"})
    gudang = await find({"status": {"$in": ["confirmed", "partially_picked", "picked"]}})
    kirim = await find({"status": {"$in": ["partially_shipped", "shipped", "delivered"]}})
    selesai = await find({"status": "done", "updated_at": {"$gte": _days_ago(7)}})
    can_pay = actor.get("role") in SAMPLE_PAYMENT_APPROVERS
    return {
        "title": "Meja Admin Sampel", "role": actor.get("role"),
        "queues": [
            _queue("bayar_sampel", "Sampel berbayar — menunggu persetujuan pembayaran",
                   "Pastikan pembayaran/kesepakatan bayar sampel sudah ada, lalu setujui. Baru setelah itu masuk ke tim sampel.",
                   _rows(bayar, "Setujui Bayar" if can_pay else "Lihat", "approve_payment" if can_pay else "open"),
                   action_label="Setujui Bayar", owner="sample_admin"),
            _queue("siap_gudang", "Siap diteruskan ke gudang", "Gratis atau pembayaran sudah disetujui — teruskan agar gudang memotong dari roll (RFID).",
                   _rows(siap, "Teruskan ke Gudang", "confirm"), action_label="Teruskan ke Gudang", owner="sample_admin", value_kind="count", value_label="Pesanan"),
            _queue("di_gudang", "Sedang dipotong / disiapkan gudang", "Gudang memindai roll induk, memotong, mencatat panjang aktual, lalu packing.",
                   _rows(gudang, "Pantau", "open"), action_label="Pantau", owner="warehouse", value_kind="count", value_label="Pesanan"),
            _queue("kirim_ambil", "Dikirim / siap diambil", "Sampel sudah keluar gudang — pastikan sampai ke pelanggan.",
                   _rows(kirim, "Lihat", "open"), action_label="Lihat", owner="warehouse", value_kind="count", value_label="Pesanan"),
            _queue("selesai", "Selesai (7 hari)", "Sampel yang sudah diterima pelanggan.",
                   _rows(selesai, "Lihat", "open"), action_label="Lihat", owner="sample_admin", value_kind="count", value_label="Pesanan"),
        ],
        "not_my_desk": ["Pesanan roll/yard biasa (SO-) → Meja Admin Sales", "Uang masuk & faktur pajak → Meja Finance"],
    }


@router.post("/sample-orders/{order_id}/approve-payment")
async def approve_payment(order_id: str, payload: NoteIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "sample_order", "approve_payment")
    if actor.get("role") not in SAMPLE_PAYMENT_APPROVERS:
        raise HTTPException(status_code=403, detail="Persetujuan pembayaran sampel hanya oleh Finance atau Admin Sampel.")
    order = await _load(order_id, request)
    if order.get("sample_billing") != "paid":
        raise HTTPException(status_code=400, detail=f"{order['number']} sampel gratis — tidak ada pembayaran yang perlu disetujui.")
    if order.get("status") == "approved":
        return order
    if order.get("status") != "waiting_approval":
        raise HTTPException(status_code=409, detail=f"{order['number']} berstatus {order.get('status')} — bukan tahap persetujuan pembayaran.")
    pa = list(order.get("pending_approvals") or [])
    for p in pa:
        if p.get("type") == "pembayaran_sampel" and p.get("status") == "pending":
            p.update({"status": "approved", "decided_by": actor["name"], "decided_by_id": actor["id"],
                      "decided_at": now_iso(), "note": payload.note})
    await db.sales_orders.update_one({"id": order_id}, {"$set": {
        "pending_approvals": pa, "approval_required": False, "required_approval_role": "",
        "sample_payment_status": "approved", "sample_payment_approved_by": actor["name"],
        "sample_payment_approved_at": now_iso(), "updated_at": now_iso()}})
    result = await so_transition(order_id, ["waiting_approval"], "approved", actor["name"], "sample_payment_approved",
                                 {"approved_by": actor["name"], "note": payload.note})
    await audit(actor["name"], "sample_payment_approved", "sales_order", order_id, {"number": order["number"], "note": payload.note})
    return result


@router.post("/sample-orders/{order_id}/confirm")
async def confirm_sample(order_id: str, request: Request) -> Dict[str, Any]:
    """Admin Sampel meneruskan ke gudang: SO → confirmed, lahir tugas outbound `sample_cut`."""
    actor = await require_permission(request, "sample_order", "confirm")
    order = await _load(order_id, request)
    if order.get("status") == "confirmed":
        return order
    if order.get("sample_billing") == "paid" and order.get("sample_payment_status") != "approved":
        raise HTTPException(status_code=409, detail={"code": "SAMPLE_PAYMENT_PENDING",
                            "message": f"{order['number']} sampel berbayar — pembayaran belum disetujui Finance/Admin Sampel."})
    await so_transition(order_id, ["approved"], "confirmed", actor["name"], "sample_forwarded_to_warehouse",
                        {"forwarded_by": actor["name"]})
    tasks = await create_outbound_tasks_for_order(order_id, actor["name"])
    await recompute_so_status(order_id)
    await audit(actor["name"], "sample_forwarded_to_warehouse", "sales_order", order_id,
                {"number": order["number"], "tasks_count": len(tasks)})
    final = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    final["tasks_created"] = len(tasks)
    return final


@router.post("/sample-orders/{order_id}/cancel")
async def cancel_sample(order_id: str, payload: NoteIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "sample_order", "cancel")
    order = await _load(order_id, request)
    if actor.get("role") == "sales":
        sales_ownership.assert_may_open(order, actor)
    if order.get("status") not in ("waiting_approval", "approved"):
        raise HTTPException(status_code=409, detail=f"{order['number']} sudah diteruskan ke gudang ({order.get('status')}) — tidak bisa dibatalkan dari sini.")
    result = await so_transition(order_id, ["waiting_approval", "approved"], "cancelled", actor["name"], "sample_cancelled",
                                 {"cancelled_by": actor["name"], "reason": payload.note})
    await audit(actor["name"], "sample_cancelled", "sales_order", order_id, {"number": order["number"], "reason": payload.note})
    return result


def _days_ago(n: int) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()
