"""Special Orders Router - Sub-fase 1.12

Handles custom product orders (products not yet in catalog).
Status flow aligned with sales_orders for consistency.
"""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from db import db
from dependencies import require_permission, audit, current_user
from core_utils import new_id, now_iso, safe_doc
from entity_scope import entity_ctx, resolve_list_scope, assert_entity_access
from services.special_order_service import (
    generate_special_order_number,
    can_approve_special_order,
    approve_special_order,
    reject_special_order,
    transition_special_order_status,
    create_sku_from_special_order,
    APPROVAL_THRESHOLD
)
from services import purchase_requisition_service as pr_svc
from services import approval_matrix_service as amx  # PS-20 — PO Custom 2 tingkat (Manager → Direksi)
from services import special_order_routing as routing
from services import special_order_phase2 as p2
from fastapi import UploadFile, File, Form
from fastapi.responses import Response
from services.rnd_spec_service import RndError
from schemas import (
    PurchaseRequisitionCreate, PurchaseRequisitionItem, SpecialOrderToPR,
    SalesOrderCreate, SalesOrderItemIn,
)
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CustomItemSpec(BaseModel):
    """Custom item specification"""
    description: str = Field(..., description="Item description")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Custom specs (size, color, material, etc)")
    quantity: float = Field(..., gt=0, description="Quantity")
    unit: str = Field(..., description="Unit of measure")
    target_price: float = Field(..., ge=0, description="Target price per unit (IDR)")
    notes: str = Field(default="", description="Additional notes")


class SpecialOrderSpec(BaseModel):
    """Spesifikasi terstruktur (opsional bila pelanggan hanya memberi referensi)."""
    template_id: str = ""
    fabric_type: str = ""
    gramasi: Optional[float] = None
    lebar: Optional[float] = None
    color_id: str = ""
    color_new_note: str = ""
    sku_hint: str = ""
    notes: str = ""


class SpecialOrderCreate(BaseModel):
    """Create special order request"""
    customer_id: str = Field(..., description="Customer ID")
    title: str = ""
    request_types: list = Field(default_factory=list, description="printing | labdip | handfeel | proofing")
    detail_level: str = "reference"   # reference | full
    reference_notes: str = ""
    spec: Optional[SpecialOrderSpec] = None
    pattern_category_code: str = ""
    design_category_code: str = ""
    entity_id: str = Field(default="", description="Selling entity ID")
    custom_item: CustomItemSpec = Field(..., description="Custom item details")
    expected_delivery: str = Field(..., description="Expected delivery date (ISO format)")
    shipping_address_id: str = Field(default="", description="Shipping address ID")
    notes: str = Field(default="", description="Order notes")
    submit_for_approval: bool = Field(default=False, description="Auto-submit if needs approval")


class SpecialOrderApprove(BaseModel):
    """Approve special order"""
    notes: str = Field(default="", description="Approval notes")


class SpecialOrderReject(BaseModel):
    """Reject special order"""
    reason: str = Field(..., min_length=1, description="Rejection reason")


class SpecialOrderStatusUpdate(BaseModel):
    """Update special order status"""
    status: str = Field(..., description="New status")
    notes: str = Field(default="", description="Update notes")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/special-orders")
async def list_special_orders(
    request: Request,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    entity_id: Optional[str] = None
) -> Dict[str, Any]:
    """List special orders with optional filters.
    
    Query params:
    - status: Filter by status
    - customer_id: Filter by customer
    - entity_id: Filter by entity
    """
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    
    query = {}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    query = resolve_list_scope("special_orders", query, ctx, entity_id)
    
    special_orders = await db.special_orders.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # Aggregate stats (ter-scope entitas, lepas dari filter status/customer)
    stats_match = resolve_list_scope("special_orders", {}, ctx, entity_id)
    pipeline = [
        {"$match": stats_match},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$total_amount"}
        }}
    ]
    
    status_counts = {}
    async for doc in db.special_orders.aggregate(pipeline):
        status_counts[doc["_id"]] = {
            "count": doc["count"],
            "total_amount": doc["total_amount"]
        }
    
    return {
        "items": special_orders,
        "count": len(special_orders),
        "by_status": status_counts,
        "approval_threshold": APPROVAL_THRESHOLD
    }


@router.post("/special-orders")
async def create_special_order(payload: SpecialOrderCreate, request: Request) -> Dict[str, Any]:
    """Create new special order for custom product.
    
    Flow:
    1. Validate customer exists
    2. Calculate total amount
    3. Generate order number
    4. Check approval requirement (amount > threshold)
    5. Create order document
    6. Return created order
    """
    await require_permission(request, "order", "create")
    user = await current_user(request)
    ctx = await entity_ctx(request)
    
    # Validate customer
    customer = await db.customers.find_one({"id": payload.customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")
    
    # Get shipping address
    address = {}
    if payload.shipping_address_id:
        address = next(
            (a for a in customer.get("addresses", []) if a["id"] == payload.shipping_address_id),
            customer.get("addresses", [{}])[0] if customer.get("addresses") else {}
        )
    else:
        address = customer.get("addresses", [{}])[0] if customer.get("addresses") else {}
    
    # Calculate total amount
    total_amount = payload.custom_item.target_price * payload.custom_item.quantity
    
    # Generate order ID and number
    order_id = new_id("sord")
    order_number = await generate_special_order_number()
    
    # Determine initial status
    initial_status = "draft"
    if payload.submit_for_approval:
        initial_status = "pending_approval"   # OD selalu lewat persetujuan (routing ke Desainer/R&D terjadi saat disetujui)
    
    # Create special order document
    special_order = {
        "id": order_id,
        "number": order_number,
        "status": initial_status,
        "type": "special_order",
        "title": payload.title.strip() or payload.custom_item.description,
        "request_types": [t for t in payload.request_types if t in routing.REQUEST_TYPES],
        "detail_level": payload.detail_level, "reference_notes": payload.reference_notes,
        "spec": payload.spec.model_dump() if payload.spec else {}, "references": [],
        "pattern_category_code": payload.pattern_category_code.strip().upper(),
        "design_category_code": payload.design_category_code.strip().upper(),
        
        # Customer info
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_email": customer.get("email", ""),
        "customer_phone": customer.get("phone", ""),
        
        # Shipping
        "shipping_address": address,
        
        # Custom item
        "custom_item": {
            "description": payload.custom_item.description,
            "specifications": payload.custom_item.specifications,
            "quantity": payload.custom_item.quantity,
            "unit": payload.custom_item.unit,
            "target_price": payload.custom_item.target_price,
            "notes": payload.custom_item.notes
        },
        
        # Financial
        "total_amount": total_amount,
        "requires_approval": total_amount > APPROVAL_THRESHOLD,
        "approval_threshold": APPROVAL_THRESHOLD,
        
        # Timeline
        "expected_delivery": payload.expected_delivery,
        
        # Entity
        "entity_id": payload.entity_id or customer.get("entity_id") or ctx.active_entity_id,
        
        # Notes
        "notes": payload.notes,
        
        # Status tracking
        "status_history": [{
            "status": initial_status,
            "timestamp": now_iso(),
            "user": user["email"]
        }],
        
        # Metadata
        "created_at": now_iso(),
        "created_by": user["email"],
        "updated_at": now_iso()
    }

    # PS-20 — cap rantai persetujuan sejak awal supaya pembuat dokumen langsung
    # melihat berapa tingkat yang dibutuhkan (Manager, dan Direksi bila nilainya besar).
    if initial_status == "pending_approval":
        # B1 DIBAYAR (2026-08-25) — KAPAN dokumen ini MULAI menunggu keputusan ditulis
        # di dokumen, bukan ditebak. Sebelum ini `AGING_META["special_order"].since`
        # menyebut `submitted_at`/`approval_requested_at` yang TIDAK PERNAH diisi
        # siapa pun, sehingga umur tunggu di Papan PO Custom & pengingat harian selalu
        # jatuh ke `created_at` — dokumen yang lama berstatus draf dilaporkan jauh
        # lebih tua daripada kenyataan, tanpa satu pun galat.
        special_order["approval_requested_at"] = now_iso()
        _chain, _cfg = await amx.special_order_chain(special_order,
                                                     special_order.get("entity_id", ""))
        special_order["approval_chain"] = _chain
        special_order["approval_level_current"] = (_chain[0]["level"] if _chain else 0)
        special_order["required_approval_role"] = (
            (_chain[0].get("roles") or ["manager"])[0] if _chain else "")
        special_order["approval_status"] = "pending"

    from services import line_scope as _lines            # FASE L
    await _lines.stamp_doc(db, special_order)
    await db.special_orders.insert_one(special_order)
    special_order.pop("_id", None)

    # FASE N butir 3 — PO CUSTOM YANG DIAJUKAN HARUS TERLIHAT. Terukur 2026-08-24:
    # 3 dokumen `special_orders` di data demo dan **0** notifikasi. Artinya pesanan
    # custom yang menunggu keputusan hanya ketahuan oleh orang yang kebetulan membuka
    # layarnya — padahal justru dokumen inilah yang paling mahal bila terlambat
    # (kain dipesan khusus, tidak bisa dijual ke pelanggan lain).
    # Alamatnya BUKAN "manager" yang diketik di sini, melainkan peran yang memang
    # diminta rantai persetujuan dokumen ini (`required_approval_role`, hasil
    # `approval_matrix_service.special_order_chain` — nilai besar bisa menuntut
    # Direksi). Ditambah pemegang `order.approve` supaya tidak pernah ada dokumen
    # menunggu tanpa satu pun penerima.
    #
    # A1 DIBAYAR (2026-08-25): pesannya TIDAK lagi disusun di sini. Judul, isi, tautan,
    # dan tingkat keparahan dulu diketik DUA KALI (di sini saat dokumen LAHIR, dan di
    # `notification_service._notify_pending_special_orders()` saat KEADAAN masih
    # menunggu) — dan keduanya sudah tidak identik: versi endpoint menyebut "Diajukan
    # oleh …", versi job tidak. Sekarang keduanya memanggil SATU penyusun pesan
    # (`notification_service.notify_special_order_waiting`), dan penjaga INV-NOTIF-02
    # aturan K3 melarang `notif_type="special_order_approval"` disusun di tempat lain.
    if initial_status == "pending_approval":
        try:
            from services.notification_service import notify_special_order_waiting
            await notify_special_order_waiting(special_order,
                                               actor_name=user.get("name", ""))
        except Exception:  # noqa: BLE001
            # Notifikasi TIDAK boleh menggagalkan pembuatan dokumen — pesanannya
            # sudah tersimpan dan sah; pemberitahuan adalah lapisan di atasnya.
            pass
    
    # Audit log
    await audit(
        user.get("name", ""),
        "special_order_created",
        "special_order",
        order_id,
        {"number": order_number, "customer_id": payload.customer_id, "total_amount": total_amount}
    )
    
    return special_order


@router.get("/special-orders/{order_id}")
async def get_special_order(order_id: str, request: Request) -> Dict[str, Any]:
    """Get special order detail by ID."""
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    
    special_order = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not special_order:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    assert_entity_access(special_order, "special_orders", ctx)
    special_order["chain"] = await routing.chain_of(special_order)
    return special_order


@router.post("/special-orders/{order_id}/references")
async def upload_od_reference(order_id: str, request: Request, file: UploadFile = File(...), caption: str = Form("")) -> Dict[str, Any]:
    """Referensi pelanggan (foto swatch / pattern / kain fisik) — ikut ke Permintaan Desain bila sudah lahir."""
    user = await require_permission(request, "order", "create")
    od = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not od:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    data = await file.read()
    try:
        meta = await routing.add_reference(od, user.get("name", ""), file.filename or "referensi", file.content_type or "", data, caption)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return meta


@router.get("/special-orders/{order_id}/references/{file_id}")
async def get_od_reference(order_id: str, file_id: str, request: Request):
    await require_permission(request, "order", "view")
    od = await db.special_orders.find_one({"id": order_id}, {"_id": 0, "references": 1})
    if not od:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    try:
        data, ctype, fname = await routing.reference_bytes(od, file_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})


@router.post("/special-orders/{order_id}/route")
async def route_od_now(order_id: str, request: Request) -> Dict[str, Any]:
    """Jalankan/ulangi routing ke Desainer & R&D (untuk OD lama yang disetujui sebelum fitur ini)."""
    user = await require_permission(request, "order", "approve")
    od = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not od:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    if od.get("status") in ("draft", "pending_approval", "cancelled"):
        raise HTTPException(status_code=400, detail="OD harus sudah disetujui sebelum diteruskan ke Desainer/R&D.")
    await routing.route_on_approve(od, user, od.get("entity_id", ""))
    fresh = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))
    fresh["chain"] = await routing.chain_of(fresh)
    return fresh


class CustomerDecisionBody(BaseModel):
    decision: str
    note: str = ""
    decided_at: str = ""
    contact_name: str = ""


class LockPriceBody(BaseModel):
    margin_pct: Optional[float] = None
    note: str = ""
    warehouse_id: str = ""
    auto_po: bool = True


class ProcureBody(BaseModel):
    warehouse_id: str = ""


async def _od_or_404(order_id: str, request: Request) -> Dict[str, Any]:
    ctx = await entity_ctx(request)
    od = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not od:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    assert_entity_access(od, "special_orders", ctx)
    return od


async def _fresh(order_id: str) -> Dict[str, Any]:
    od = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))
    od["chain"] = await routing.chain_of(od)
    return od


@router.post("/special-orders/{order_id}/submit")
async def submit_special_order(order_id: str, request: Request) -> Dict[str, Any]:
    """Ajukan OD draft ke persetujuan (Manager → Direksi bila nilai besar)."""
    user = await require_permission(request, "order", "create")
    od = await _od_or_404(order_id, request)
    if od.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Hanya OD draft yang bisa diajukan.")
    chain, _cfg = await amx.special_order_chain(od, od.get("entity_id", ""))
    await db.special_orders.update_one({"id": order_id}, {
        "$set": {"status": "pending_approval", "approval_requested_at": now_iso(), "approval_chain": chain,
                 "approval_level_current": (chain[0]["level"] if chain else 0),
                 "required_approval_role": ((chain[0].get("roles") or ["manager"])[0] if chain else ""),
                 "approval_status": "pending", "updated_at": now_iso()},
        "$push": {"status_history": {"status": "pending_approval", "timestamp": now_iso(), "user": user.get("email", ""), "note": "Diajukan"}}})
    fresh = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))
    try:
        from services.notification_service import notify_special_order_waiting
        await notify_special_order_waiting(fresh, actor_name=user.get("name", ""))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[submit_special_order] efek samping gagal diabaikan: %s", exc)  # KN-C10
    fresh["chain"] = await routing.chain_of(fresh)
    return fresh


@router.post("/special-orders/{order_id}/customer-decision")
async def customer_decision(order_id: str, payload: CustomerDecisionBody, request: Request) -> Dict[str, Any]:
    """Fase 2 — ACC / revisi / tolak PELANGGAN atas sample (revisi → sample R&D baru otomatis)."""
    user = await require_permission(request, "order", "update")
    od = await _od_or_404(order_id, request)
    try:
        entry = await p2.customer_decide(od, payload.model_dump(), user, od.get("entity_id", ""))
    except (p2.ODError, RndError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(user.get("name", ""), f"special_order_customer_{payload.decision}", "special_order", order_id,
                {"number": od.get("number"), "decision_id": entry["id"]}, reason=payload.note or "")
    return {"decision": entry, "special_order": await _fresh(order_id)}


@router.post("/special-orders/{order_id}/customer-decision/evidence")
async def customer_decision_evidence(order_id: str, request: Request, file: UploadFile = File(...),
                                     decision_id: str = Form(""), caption: str = Form("")) -> Dict[str, Any]:
    user = await require_permission(request, "order", "update")
    od = await _od_or_404(order_id, request)
    data = await file.read()
    try:
        meta = await p2.add_evidence(od, decision_id, user.get("name", ""), file.filename or "bukti", file.content_type or "", data, caption)
    except (p2.ODError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"evidence": meta, "special_order": await _fresh(order_id)}


@router.get("/special-orders/{order_id}/customer-decision/evidence/{file_id}")
async def customer_decision_evidence_file(order_id: str, file_id: str, request: Request):
    await require_permission(request, "order", "view")
    od = await _od_or_404(order_id, request)
    try:
        data, ctype = await p2.evidence_bytes(od, file_id)
    except (p2.ODError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})


@router.get("/special-orders/{order_id}/pricing")
async def pricing_preview(order_id: str, request: Request, margin_pct: Optional[float] = None) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    od = await _od_or_404(order_id, request)
    return await p2.pricing_preview(od, margin_pct)


@router.post("/special-orders/{order_id}/lock-price")
async def lock_price(order_id: str, payload: LockPriceBody, request: Request) -> Dict[str, Any]:
    """Fase 2 — harga final = kontrak supplier pemenang + margin → dikunci, OD Confirmed."""
    user = await require_permission(request, "order", "update")
    if user.get("role") not in ("sales", "sales_admin", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Hanya Sales / manager / admin yang boleh mengunci harga final.")
    od = await _od_or_404(order_id, request)
    try:
        pricing = await p2.lock_price(od, payload.model_dump(), user)
    except p2.ODError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(user.get("name", ""), "special_order_price_locked", "special_order", order_id,
                {"number": od.get("number"), "final_unit_price": pricing["final_unit_price"], "margin_pct": pricing["margin_pct"]})
    # Fase 4 — SO hasil OD lahir otomatis (harga final) agar barang PO nanti langsung direservasi & Surat Jalan lahir.
    if payload.auto_po and pricing.get("procurement") and not pricing.get("procurement_error"):
        try:
            await convert_special_order_to_so(order_id, request)
        except HTTPException as exc:
            await db.special_orders.update_one({"id": order_id}, {"$set": {"shipping_error": f"SO otomatis gagal: {exc.detail}"}})
    return {"pricing": pricing, "special_order": await _fresh(order_id)}


@router.post("/special-orders/{order_id}/procure")
async def procure_now(order_id: str, payload: ProcureBody, request: Request) -> Dict[str, Any]:
    """Fase 3 — ulangi PR→PO otomatis ke supplier pemenang (bila saat kunci harga gagal / dimatikan)."""
    user = await require_permission(request, "purchase_requisition", "create")
    od = await _od_or_404(order_id, request)
    if payload.warehouse_id:   # E4.1 — gudang tujuan wajib boleh dipakai badan usaha OD
        from services import warehouse_scope_service as whscope
        await whscope.assert_usable(payload.warehouse_id, od.get("entity_id"), action="menerima PO special order")
    try:
        res = await p2.auto_procure(od, user, payload.warehouse_id)
    except (p2.ODError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"procurement": res, "special_order": await _fresh(order_id)}


@router.post("/special-orders/{order_id}/prepare-shipment")
async def prepare_shipment(order_id: str, request: Request) -> Dict[str, Any]:
    """Fase 4 — ulangi otomatisasi pengiriman: reservasi stok SO OD + tugas Surat Jalan."""
    user = await require_permission(request, "order", "update")
    await _od_or_404(order_id, request)
    try:
        res = await p2.on_goods_received(order_id)
    except p2.ODError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(user.get("name", ""), "special_order_prepare_shipment", "special_order", order_id, res)
    return {"result": res, "special_order": await _fresh(order_id)}


@router.post("/special-orders/{order_id}/unlock-price")
async def unlock_price(order_id: str, payload: SpecialOrderReject, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "order", "update")
    od = await _od_or_404(order_id, request)
    try:
        await p2.unlock_price(od, user, payload.reason)
    except p2.ODError as exc:
        raise HTTPException(status_code=400 if user.get("role") == "admin" else 403, detail=str(exc)) from exc
    await audit(user.get("name", ""), "special_order_price_unlocked", "special_order", order_id,
                {"number": od.get("number")}, reason=payload.reason)
    return await _fresh(order_id)


@router.post("/special-orders/{order_id}/approve")

async def approve_special_order_endpoint(
    order_id: str,
    payload: SpecialOrderApprove,
    request: Request
) -> Dict[str, Any]:
    """Approve special order (PO Custom) — PS-20: BERJENJANG sesuai matriks divisi.

    Tingkat 1 = Manager (admin juga boleh). Bila nilai pesanan ≥ ambang
    `approval.po_custom_direksi_min`, dibutuhkan tingkat 2 = **Direksi (admin)**.
    Transisi: pending_approval → (tingkat 2 menunggu) → confirmed.
    """
    await require_permission(request, "order", "approve")
    user = await current_user(request)

    special_order = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))
    if not special_order:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")

    if not await can_approve_special_order(special_order, user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Hanya manager/admin yang dapat approve special order dengan status pending_approval"
        )

    entity_id = special_order.get("entity_id", "")
    chain, _cfg = await amx.special_order_chain(special_order, entity_id)
    level = amx.pending_level(chain)
    if level is None:
        raise HTTPException(status_code=409, detail="Semua tingkat persetujuan sudah terpenuhi.")
    # Matriks persetujuan divisi (peran per tingkat + pemisahan tugas) — MENGIKAT.
    ev = await amx.guard("po_custom", user, special_order, entity_id,
                         amount=special_order.get("total_amount"), level=level,
                         action="approve")

    level["status"] = "approved"
    level["approved_by"] = user.get("name", "")
    level["approved_by_id"] = user.get("id", "")
    level["approved_at"] = now_iso()
    nxt = amx.pending_level(chain)

    if nxt is not None:
        # Masih butuh tingkat berikutnya (Direksi) → tetap menunggu persetujuan.
        # INV-ATOMIC-01 — CAS: tingkat berjalan harus masih seperti yang dibaca (dua penyetuju paralel → satu menang).
        _cas_res = await db.special_orders.find_one_and_update(
            {"status": "pending_approval", "id": order_id,
             "approval_level_current": special_order.get("approval_level_current", level["level"])},
            {"$set": {"approval_chain": chain,
                      "approval_level_current": nxt["level"],
                      "required_approval_role": (nxt.get("roles") or ["admin"])[0],
                      "updated_at": now_iso()},
             "$push": {"status_history": {
                 "status": "pending_approval",
                 "timestamp": now_iso(), "user": user.get("email", ""),
                 "note": (f"Disetujui tingkat {level['level']} ({level.get('label', '')}) — "
                          f"lanjut ke {nxt.get('label', '')}")}}})
        if not _cas_res:
            raise HTTPException(status_code=409, detail="Tingkat persetujuan sudah diputus pihak lain. Muat ulang.")
        await amx.record(stage="po_custom", action="approve", actor=user, doc=special_order,
                         entity_id=entity_id, level=level["level"],
                         level_label=level.get("label", ""),
                         outcome=f"disetujui tingkat {level['level']} — menunggu {nxt.get('label', '')}",
                         note=payload.notes or "", enforced=ev.get("enforced", True))
        await audit(user.get("name", ""), "special_order_approved_level", "special_order",
                    order_id, {"number": special_order.get("number"),
                               "level": level["level"], "next": nxt.get("label", "")},
                    reason=payload.notes or "")
        return safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))

    try:
        updated = await approve_special_order(order_id, user["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.special_orders.update_one(
        {"id": order_id},
        {"$set": {"approval_chain": chain, "approval_level_current": 0,
                  "approval_status": "approved"}})
    await amx.record(stage="po_custom", action="approve", actor=user, doc=special_order,
                     entity_id=entity_id, level=level["level"],
                     level_label=level.get("label", ""),
                     outcome=f"disetujui penuh ({len(chain)} tingkat)",
                     note=payload.notes or "", enforced=ev.get("enforced", True))
    await audit(user.get("name", ""), "special_order_approved", "special_order", order_id,
                {"number": special_order.get("number"), "levels": len(chain)},
                reason=payload.notes or "")
    fresh = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0})) or updated
    # ROUTING: printing → Permintaan Desain; labdip/handfeel → Permintaan Sample R&D (spesifikasi diwarisi)
    await routing.route_on_approve(fresh, user, entity_id)
    return safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0})) or fresh


@router.post("/special-orders/{order_id}/reject")

async def reject_special_order_endpoint(
    order_id: str,
    payload: SpecialOrderReject,
    request: Request
) -> Dict[str, Any]:
    """Reject special order (manager/admin only) — PS-20: dijaga matriks divisi.
    
    Transitions: pending_approval → cancelled
    """
    await require_permission(request, "order", "approve")
    user = await current_user(request)
    
    # Check if user can reject
    special_order = safe_doc(await db.special_orders.find_one({"id": order_id}, {"_id": 0}))
    if not special_order:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    
    if not await can_approve_special_order(special_order, user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Hanya manager/admin yang dapat reject special order dengan status pending_approval"
        )
    entity_id = special_order.get("entity_id", "")
    chain, _cfg = await amx.special_order_chain(special_order, entity_id)
    level = amx.pending_level(chain) or (chain[0] if chain else None)
    ev = await amx.guard("po_custom", user, special_order, entity_id,
                         amount=special_order.get("total_amount"), level=level,
                         action="reject")
    try:
        updated = await reject_special_order(order_id, user["email"], payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await amx.record(stage="po_custom", action="reject", actor=user, doc=special_order,
                     entity_id=entity_id, level=(level or {}).get("level", 1),
                     level_label=(level or {}).get("label", ""), outcome="ditolak",
                     note=payload.reason or "", enforced=ev.get("enforced", True))
    await audit(user.get("name", ""), "special_order_rejected", "special_order", order_id,
                {"number": special_order.get("number")}, reason=payload.reason or "")
    return updated


@router.post("/special-orders/{order_id}/status")

async def update_special_order_status(
    order_id: str,
    payload: SpecialOrderStatusUpdate,
    request: Request
) -> Dict[str, Any]:
    """Update special order status.
    
    Valid transitions:
    - confirmed → in_production (purchasing started)
    - in_production → ready (item produced/received)
    - ready → shipped (dispatched to customer)
    - shipped → done (delivered)
    """
    await require_permission(request, "order", "update")
    user = await current_user(request)
    
    try:
        updated = await transition_special_order_status(
            order_id,
            payload.status,
            user["email"]
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/special-orders/{order_id}/create-pr")
async def create_pr_from_special_order(
    order_id: str,
    payload: SpecialOrderToPR,
    request: Request
) -> Dict[str, Any]:
    """Depth #2c — Jembatan Special Order → Purchase Requisition (pengadaan).

    Membuat PR (source=special_order) untuk item custom, lalu menggerakkan
    special order: confirmed → in_production (purchasing started).
    """
    await require_permission(request, "purchase_requisition", "create")
    user = await current_user(request)

    so = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not so:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    if so.get("linked_pr_id"):
        raise HTTPException(status_code=400, detail=f"Special order sudah punya PR ({so.get('linked_pr_number')})")
    if so["status"] not in ("confirmed", "in_production"):
        raise HTTPException(status_code=400,
                            detail="PR hanya bisa dibuat untuk special order yang sudah confirmed")
    if so.get("request_types") and not (so.get("pricing") or {}).get("locked"):
        raise HTTPException(status_code=400, detail="Kunci harga final (ACC pelanggan + margin) dulu sebelum membuat PR ke supplier.")

    ci = so.get("custom_item", {})
    pr_price_locked = float((so.get("pricing") or {}).get("cost_price") or 0)
    if payload.warehouse_id:   # E4.1 — gudang tujuan pengadaan harus boleh dipakai
        from services import warehouse_scope_service as whscope
        await whscope.assert_usable(payload.warehouse_id, so.get("entity_id", ""),
                                   action="menerima barang di sini",
                                   field_label="Gudang tujuan")
    est_price = payload.est_price if payload.est_price > 0 else (pr_price_locked or float(ci.get("target_price", 0) or 0))
    pr_payload = PurchaseRequisitionCreate(
        items=[PurchaseRequisitionItem(
            product_id=so.get("linked_product_id") or (so.get("pricing") or {}).get("product_id") or "",
            description=ci.get("description", f"Custom item {so.get('number')}"),
            quantity=float(ci.get("quantity", 1) or 1),
            unit=ci.get("unit", "meter"),
            est_price=est_price,
            note=ci.get("notes", ""),
        )],
        warehouse_id=payload.warehouse_id,
        entity_id=so.get("entity_id", ""),
        reason=f"Pengadaan untuk Special Order {so.get('number')} — {so.get('customer_name','')}"
               + (f" · supplier pemenang {(so.get('pricing') or {}).get('supplier_name')} (kontrak {(so.get('pricing') or {}).get('contract_number') or '-'})" if (so.get("pricing") or {}).get("supplier_name") else ""),
        needed_by_date=payload.needed_by_date or so.get("expected_delivery", ""),
        source="special_order",
        source_ref_id=order_id,
        notes=payload.notes,
        submit_now=payload.submit_now,
    )
    # INV-ATOMIC-01 — klaim special order (belum punya PR) SESUDAH validasi, sebelum PR lahir.
    from services import atomic_claim as _saga
    await _saga.claim("special_orders", order_id, "special_order_create_pr",
                      precondition={"linked_pr_id": {"$in": [None, ""]}}, actor=user.get("name", ""))
    try:
        pr = await pr_svc.create_requisition(pr_payload, created_by=user.get("name", "Admin"))
    except ValueError as e:
        await _saga.release("special_orders", order_id)   # PR belum lahir → aman dilepas
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await _saga.release("special_orders", order_id)
        raise

    await db.special_orders.update_one({"id": order_id}, _saga.finish_set({
        "linked_pr_id": pr["id"], "linked_pr_number": pr["number"], "updated_at": now_iso()}))

    # Gerakkan ke in_production (purchasing started) bila masih confirmed
    if so["status"] == "confirmed":
        try:
            await transition_special_order_status(order_id, "in_production", user["email"])
        except ValueError as exc:
            logger.warning("[create_pr_from_special_order] efek samping gagal diabaikan: %s", exc)  # KN-C10

    await audit(user.get("name", ""), "special_order_pr_created", "special_order", order_id,
                {"pr_number": pr["number"], "pr_id": pr["id"]})

    so_updated = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    return {"pr": pr, "special_order": safe_doc(so_updated)}


@router.post("/special-orders/{order_id}/create-sku")
async def create_sku_endpoint(order_id: str, request: Request) -> Dict[str, Any]:
    """F3 (2.a) — Materialisasi Product SKU dari Special Order MTO (idempotent).

    Otomatis dijalankan saat approve; endpoint ini adalah fallback manual
    (mis. special order lama yang dibuat sebelum fitur auto-create).
    """
    await require_permission(request, "order", "approve")
    user = await current_user(request)
    ctx = await entity_ctx(request)

    so = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not so:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    assert_entity_access(so, "special_orders", ctx)

    try:
        product = await create_sku_from_special_order(
            order_id, created_by=user.get("email", user.get("name", "system")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await audit(user.get("name", ""), "special_order_sku_created", "special_order", order_id,
                {"product_id": product["id"], "sku": product["sku"]})
    so_updated = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    return {"product": product, "special_order": safe_doc(so_updated)}


@router.post("/special-orders/{order_id}/convert-to-so")
async def convert_special_order_to_so(order_id: str, request: Request) -> Dict[str, Any]:
    """F3 — Konversi Special Order (MTO) menjadi Sales Order standar.

    Menutup loop MTO: produk custom yang sudah punya SKU dimasukkan ke jalur
    fulfillment standar. Reuse penuh logika `create_order` (pricing/reservasi/
    credit gate). `allow_backorder=True` agar tidak gagal bila stok MTO belum
    tersedia. Idempotent: tolak bila sudah pernah dikonversi.
    """
    await require_permission(request, "order", "create")
    user = await current_user(request)
    ctx = await entity_ctx(request)

    so = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not so:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    assert_entity_access(so, "special_orders", ctx)

    if so.get("linked_sales_order_id"):
        raise HTTPException(
            status_code=400,
            detail=f"Special order sudah dikonversi ke SO {so.get('linked_sales_order_number')}")
    if so.get("status") not in ("confirmed", "in_production", "ready"):
        raise HTTPException(
            status_code=400,
            detail="Konversi hanya untuk special order yang sudah disetujui (confirmed/in_production/ready).")
    if so.get("request_types") and not (so.get("pricing") or {}).get("locked"):
        raise HTTPException(status_code=400, detail="Kunci harga final (ACC pelanggan + margin) dulu sebelum konversi ke SO.")

    # Pastikan SKU sudah ada (auto-create bila belum — mis. order lama sebelum fitur 2.a).
    # OD terstruktur: SKU eksklusif hasil R&D (pricing.product_id) MENANG atas SKU ad hoc lama.
    _pp = (so.get("pricing") or {}).get("product_id")
    if _pp and so.get("linked_product_id") != _pp:
        await db.special_orders.update_one({"id": order_id}, {"$set": {"linked_product_id": _pp, "linked_product_sku": so["pricing"].get("product_sku", "")}})
        so = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not so.get("linked_product_id"):
        try:
            await create_sku_from_special_order(
                order_id, created_by=user.get("email", "system"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        so = await db.special_orders.find_one({"id": order_id}, {"_id": 0})

    ci = so.get("custom_item", {}) or {}
    addr = so.get("shipping_address", {}) or {}
    so_payload = SalesOrderCreate(
        customer_id=so["customer_id"],
        shipping_address_id=addr.get("id", ""),
        items=[SalesOrderItemIn(
            product_id=so["linked_product_id"],
            quantity=float(ci.get("quantity", 1) or 1),
            unit=ci.get("unit", "meter"),
        )],
        entity_id=so.get("entity_id", ""),
        allow_backorder=True,         # MTO: stok mungkin belum tersedia → backorder
        confirm_mixed_lot=True,       # item custom tunggal — lewati gate mixed-lot
        source_special_order_id=order_id,
        sales_name=so.get("created_by", "Sales"),
    )

    # Klaim atomik SESUDAH semua validasi: special_orders (belum tertaut SO) sebelum SO lahir.
    # Klik ganda / balapan → 409, bukan dua SO dari satu pesanan khusus.
    from services import atomic_claim as _saga
    await _saga.claim("special_orders", order_id, "special_order_convert_to_so",
                      precondition={"linked_sales_order_id": {"$in": [None, ""]}},
                      actor=user.get("name", ""))
    # Reuse penuh create_order (local import → hindari circular import).
    from routers.sales_orders import create_order as _create_sales_order
    try:
        sales_order = await _create_sales_order(so_payload, request)
    except Exception:
        await _saga.release("special_orders", order_id)   # SO belum lahir → aman dilepas
        raise

    await db.special_orders.update_one(
        {"id": order_id},
        _saga.finish_set({
            "linked_sales_order_id": sales_order["id"],
            "linked_sales_order_number": sales_order["number"],
            "converted_at": now_iso(),
            "converted_by": user.get("email", user.get("name", "")),
            "updated_at": now_iso(),
        }))
    await audit(user.get("name", ""), "special_order_converted_to_so", "special_order", order_id,
                {"so_id": sales_order["id"], "so_number": sales_order["number"]})

    so_updated = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    return {"special_order": safe_doc(so_updated), "sales_order": sales_order}


@router.patch("/special-orders/{order_id}")

async def patch_special_order(
    order_id: str,
    payload: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Partial update special order (draft only).
    
    Allowed fields: notes, expected_delivery, custom_item fields
    """
    await require_permission(request, "order", "update")
    user = await current_user(request)
    
    ctx = await entity_ctx(request)
    special_order = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not special_order:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    assert_entity_access(special_order, "special_orders", ctx)  # S#074 IDOR
    if special_order["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail="Hanya special order dengan status draft yang dapat diedit"
        )
    
    # Allowed updates
    allowed_fields = ["notes", "expected_delivery"]
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada field yang dapat diupdate")
    
    updates["updated_at"] = now_iso()
    updates["updated_by"] = user["email"]
    
    result = await db.special_orders.find_one_and_update(
        {"id": order_id},
        {"$set": updates},
        return_document=True
    )
    
    result.pop("_id", None)
    return result


@router.delete("/special-orders/{order_id}")

async def delete_special_order(
    order_id: str,
    request: Request
) -> Dict[str, Any]:
    """Soft delete special order (draft only)."""
    await require_permission(request, "order", "delete")
    user = await current_user(request)
    
    special_order = await db.special_orders.find_one({"id": order_id}, {"_id": 0})
    if not special_order:
        raise HTTPException(status_code=404, detail="Special order tidak ditemukan")
    
    if special_order["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail="Hanya special order dengan status draft yang dapat dihapus"
        )
    
    result = await db.special_orders.find_one_and_update(
        {"id": order_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now_iso(),
                "cancelled_by": user["email"],
                "updated_at": now_iso()
            }
        },
        return_document=True
    )
    
    result.pop("_id", None)
    return result
