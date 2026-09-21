"""FB-02 router — Modul Logistik (pengiriman: ekspedisi / armada sendiri, foto muat & POD, posisi).

RBAC modul `logistics`: view (lihat), manage (buat/ubah/hapus — gudang, admin, manajer),
update (foto, posisi, tahapan — termasuk peran `driver`).
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from dependencies import require_permission, audit
from db import db
from entity_scope import assert_entity_access, entity_ctx, resolve_list_scope
from schemas_logistics import (DeliveryCreateIn, DeliveryUpdateIn, MyRouteIn, PickupHandoverIn, PositionIn,
                               TransitionIn, VehicleIn, VehicleStatusIn, VehicleUpdateIn)
from services import logistics_service as lg
from services import fleet_service as fleet

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


async def _guard(delivery_id: str, ctx) -> Dict[str, Any]:
    doc = await lg.get_delivery(delivery_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Pengiriman tidak ditemukan.")
    assert_entity_access(doc, lg.COLL, ctx)
    return doc


def _guard_driver_write(doc: Dict[str, Any], actor: Dict[str, Any]) -> None:
    """P1-1 — sopir hanya boleh MENULIS (foto/posisi/tahapan) pada pengiriman yang ditugaskan padanya.
    Melihat daftar & detail tetap seluas entitas (keputusan pemilik 2026-09-02)."""
    if actor.get("role") == "driver" and doc.get("driver_user_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Pengiriman ini bukan tugas Anda — hanya sopir yang ditugaskan yang boleh mengubahnya.")


@router.get("/meta")
async def logistics_meta(request: Request) -> Dict[str, Any]:
    await require_permission(request, "logistics", "view")
    return lg.meta()


@router.get("/summary")
async def logistics_summary(request: Request, entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    return await lg.summary(resolve_list_scope(lg.COLL, {}, ctx, entity_id))


@router.get("/dashboard")
async def logistics_dashboard(request: Request, entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Dasbor Pengiriman: KPI, visual status/moda, antrean aksi cepat, armada, riwayat singkat."""
    actor = await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    data = await lg.dashboard(resolve_list_scope(lg.COLL, {}, ctx, entity_id),
                              resolve_list_scope("shipments", {}, ctx, entity_id),
                              entity_id or ctx.active_entity_id)
    data["active"] = [lg.redact_for(r, actor) for r in data["active"]]
    return data


@router.get("/history")
async def logistics_history(request: Request, entity_id: Optional[str] = Query(None),
                            date_from: str = Query(""), date_to: str = Query(""), mode: str = Query(""),
                            status: str = Query(""), q: str = Query(""),
                            page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=200)) -> Dict[str, Any]:
    await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    return await lg.history(resolve_list_scope(lg.COLL, {}, ctx, entity_id), date_from, date_to, mode, status, q, page, size)


# ─── Armada internal ──────────────────────────────────────────────────────────
@router.get("/fleet/availability")
async def fleet_availability(request: Request, entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    return await fleet.availability(resolve_list_scope(fleet.COLL, {}, ctx, entity_id), entity_id or ctx.active_entity_id)


@router.get("/fleet/vehicles")
async def list_vehicles(request: Request, entity_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    return await fleet.list_vehicles(resolve_list_scope(fleet.COLL, {}, ctx, entity_id))


@router.post("/fleet/vehicles")
async def create_vehicle(payload: VehicleIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    try:
        doc = await fleet.create_vehicle(payload.model_dump(), actor["name"], ctx.active_entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "fleet_vehicle_create", fleet.COLL, doc["id"], {"plate": doc["plate"]})
    return doc


@router.patch("/fleet/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id: str, payload: VehicleUpdateIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    cur = await db.fleet_vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not cur:
        raise HTTPException(status_code=404, detail="Kendaraan tidak ditemukan.")
    assert_entity_access(cur, fleet.COLL, ctx)
    try:
        doc = await fleet.update_vehicle(vehicle_id, payload.model_dump(exclude_unset=True), actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "fleet_vehicle_update", fleet.COLL, vehicle_id, payload.model_dump(exclude_unset=True))
    return doc


@router.post("/fleet/vehicles/{vehicle_id}/status")
async def set_vehicle_status(vehicle_id: str, payload: VehicleStatusIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    cur = await db.fleet_vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not cur:
        raise HTTPException(status_code=404, detail="Kendaraan tidak ditemukan.")
    assert_entity_access(cur, fleet.COLL, ctx)
    try:
        doc = await fleet.set_vehicle_status(vehicle_id, payload.status, payload.note, actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "fleet_vehicle_status", fleet.COLL, vehicle_id, {"status": payload.status}, reason=payload.note)
    return doc


@router.get("/shipments/unassigned")
async def unassigned_shipments(request: Request, entity_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    return await lg.unassigned_shipments(resolve_list_scope("shipments", {}, ctx, entity_id))


@router.get("/drivers")
async def list_drivers(request: Request, entity_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Daftar akun sopir (peran `driver`) untuk ditugaskan ke pengiriman."""
    await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    return await lg.list_drivers(entity_id or ctx.active_entity_id)


@router.post("/my-route")
async def set_my_route(payload: MyRouteIn, request: Request) -> Dict[str, Any]:
    """Sopir menyusun urutan tujuan pengiriman miliknya (route_order)."""
    actor = await require_permission(request, "logistics", "update")
    n = await lg.set_my_route(payload.ids, actor.get("id", ""))
    if n == 0:
        raise HTTPException(status_code=400, detail="Tidak ada pengiriman milik Anda dalam daftar.")
    await audit(actor["name"], "logistics_route", lg.COLL, "-", {"ids": payload.ids})
    return {"updated": n}


@router.get("/deliveries")
async def list_deliveries(request: Request, entity_id: Optional[str] = Query(None),
                          status: str = Query(""), q: str = Query(""), mode: str = Query(""),
                          order_id: str = Query(""), mine: bool = Query(False),
                          active_only: bool = Query(False)) -> List[Dict[str, Any]]:
    actor = await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    scope = resolve_list_scope(lg.COLL, {}, ctx, entity_id)
    rows = await lg.list_deliveries(scope, status, q, order_id,
                                    driver_user_id=actor.get("id") if mine else "",
                                    mode=mode, active_only=active_only)
    return [lg.redact_for(r, actor) for r in rows]


@router.post("/deliveries")
async def create_delivery(payload: DeliveryCreateIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    try:
        doc = await lg.create_delivery(payload.model_dump(), actor, ctx.active_entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_create", lg.COLL, doc["id"],
                {"number": doc["number"], "shipments": doc["shipment_nos"], "mode": doc["mode"]})
    return lg.redact_for(doc, actor)


@router.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    return lg.redact_for(await _guard(delivery_id, ctx), actor)


@router.post("/deliveries/{delivery_id}/pickup-handover")
async def pickup_handover(delivery_id: str, payload: PickupHandoverIn, request: Request) -> Dict[str, Any]:
    """Serah terima barang ke pelanggan yang ambil sendiri — WAJIB kode pickup cocok + nama/ID pengambil."""
    actor = await require_permission(request, "logistics", "update")
    ctx = await entity_ctx(request)
    before = await _guard(delivery_id, ctx)
    try:
        doc = await lg.pickup_handover(delivery_id, payload.model_dump(), actor["name"])
    except ValueError as e:
        await audit(actor["name"], "logistics_pickup_rejected", lg.COLL, delivery_id,
                    {"picker_name": payload.picker_name}, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_pickup_handover", lg.COLL, delivery_id,
                {"from": before.get("status"), "picker_name": payload.picker_name, "picker_id_no": payload.picker_id_no})
    return lg.redact_for(doc, actor)


@router.patch("/deliveries/{delivery_id}")
async def update_delivery(delivery_id: str, payload: DeliveryUpdateIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    await _guard(delivery_id, ctx)
    try:
        doc = await lg.update_delivery(delivery_id, payload.model_dump(exclude_unset=True), actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_update", lg.COLL, delivery_id, payload.model_dump(exclude_unset=True))
    return doc


@router.post("/deliveries/{delivery_id}/photos")
async def upload_photo(delivery_id: str, request: Request, kind: str = Form("other"),
                       note: str = Form(""), file: UploadFile = File(...)) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "update")
    ctx = await entity_ctx(request)
    _guard_driver_write(await _guard(delivery_id, ctx), actor)
    data = await file.read()
    try:
        photo = await lg.add_photo(delivery_id, kind, file.filename or "foto.jpg",
                                   file.content_type or "", data, note, actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_photo", lg.COLL, delivery_id, {"kind": kind, "photo_id": photo["id"]})
    return photo


@router.get("/deliveries/{delivery_id}/photos/{photo_id}")
async def get_photo(delivery_id: str, photo_id: str, request: Request):
    await require_permission(request, "logistics", "view")
    ctx = await entity_ctx(request)
    await _guard(delivery_id, ctx)
    try:
        data, ct = await lg.get_photo_bytes(delivery_id, photo_id)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e) or "Foto tidak ditemukan.")
    return Response(content=data, media_type=ct, headers={"Cache-Control": "private, max-age=300"})


@router.delete("/deliveries/{delivery_id}/photos/{photo_id}")
async def delete_photo(delivery_id: str, photo_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "update")
    ctx = await entity_ctx(request)
    _guard_driver_write(await _guard(delivery_id, ctx), actor)
    try:
        res = await lg.delete_photo(delivery_id, photo_id, actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_photo_delete", lg.COLL, delivery_id, {"photo_id": photo_id})
    return res


@router.post("/deliveries/{delivery_id}/positions")
async def add_position(delivery_id: str, payload: PositionIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "update")
    ctx = await entity_ctx(request)
    _guard_driver_write(await _guard(delivery_id, ctx), actor)
    try:
        doc = await lg.add_position(delivery_id, payload.model_dump(), actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_position", lg.COLL, delivery_id, {"location": payload.location})
    return doc


@router.delete("/deliveries/{delivery_id}/positions/{pos_id}")
async def delete_position(delivery_id: str, pos_id: str, request: Request) -> Dict[str, Any]:
    """L-2 — hapus/koreksi posisi salah (manage)."""
    actor = await require_permission(request, "logistics", "manage")
    ctx = await entity_ctx(request)
    await _guard(delivery_id, ctx)
    try:
        res = await lg.delete_position(delivery_id, pos_id, actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_position_delete", lg.COLL, delivery_id, {"pos_id": pos_id})
    return res


@router.post("/deliveries/{delivery_id}/transition")
async def transition(delivery_id: str, payload: TransitionIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "logistics", "update")
    ctx = await entity_ctx(request)
    before = await _guard(delivery_id, ctx)
    _guard_driver_write(before, actor)
    if payload.to == "prepared" and before.get("status") == "loaded":
        await require_permission(request, "logistics", "manage")   # P1-3: bongkar hanya gudang/manajer/admin
    try:
        doc = await lg.transition(delivery_id, payload.model_dump(), actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "logistics_status", lg.COLL, delivery_id,
                {"from": before.get("status"), "to": payload.to}, reason=payload.reason or payload.note or "")
    return doc
