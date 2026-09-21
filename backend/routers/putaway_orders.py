"""FASE R2 — Router Putaway Order (PA) + BTG. Prefix /api."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from dependencies import require_permission, audit
from entity_scope import entity_ctx, resolve_scope_ids
from services import warehouse_scope_service as whscope
from services import putaway_order_service as pa

router = APIRouter(prefix="/api")


class PACreatePayload(BaseModel):
    from_warehouse_id: str
    to_warehouse_id: str
    roll_ids: List[str]


class PAConfirmPayload(BaseModel):
    scanned_epcs: Optional[List[str]] = None


class PAResolvePayload(BaseModel):
    roll_ids: List[str]
    action: str  # accept | return_transit


async def _scope(request: Request) -> List[str]:
    ctx = await entity_ctx(request)
    return resolve_scope_ids(ctx)


@router.get("/putaway-orders/suggest")
async def get_suggest(request: Request, from_warehouse_id: str) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    return await pa.suggest(from_warehouse_id, await _scope(request))


@router.get("/putaway-orders")
async def get_orders(request: Request, warehouse_id: Optional[str] = None,
                     status: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    return {"orders": await pa.list_orders(await _scope(request), warehouse_id, status, limit)}


@router.post("/putaway-orders")
async def post_order(payload: PACreatePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    ctx = await entity_ctx(request)
    # E4.1 — gudang asal & tujuan harus boleh dipakai badan usaha aktif.
    await whscope.assert_many_usable([payload.from_warehouse_id, payload.to_warehouse_id],
                                     ctx.active_entity_id, action="memindahkan roll ke rak di sini")
    order = await pa.create_order(payload.from_warehouse_id, payload.to_warehouse_id,
                                  payload.roll_ids, resolve_scope_ids(ctx), actor["name"])
    await audit(actor["name"], "putaway_order_created", "putaway_order", order["id"],
                {"pa_number": order["pa_number"], "items": order["item_count"]})
    return order


@router.post("/putaway-orders/{order_id}/dispatch")
async def post_dispatch(order_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    order = await pa.dispatch(order_id, await _scope(request))
    await audit(actor["name"], "putaway_order_dispatched", "putaway_order", order_id, {})
    return order


@router.post("/putaway-orders/{order_id}/confirm-arrival")
async def post_confirm(order_id: str, payload: PAConfirmPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    order = await pa.confirm_arrival(order_id, payload.scanned_epcs,
                                     await _scope(request), actor["name"])
    await audit(actor["name"], "putaway_order_confirmed", "putaway_order", order_id,
                {"btg": order.get("btg_number"), "exceptions": order.get("exception_count", 0)})
    return order


@router.post("/putaway-orders/{order_id}/resolve-exception")
async def post_resolve(order_id: str, payload: PAResolvePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    order = await pa.resolve_exception(order_id, payload.roll_ids, payload.action,
                                       await _scope(request), actor["name"])
    await audit(actor["name"], "putaway_exception_resolved", "putaway_order", order_id,
                {"action": payload.action, "rolls": len(payload.roll_ids)})
    return order


@router.get("/wms/health-dashboard")
async def get_wms_health(request: Request) -> Dict[str, Any]:
    """DASHBOARD KESEHATAN GUDANG — insiden, opname, antrean putaway, device."""
    await require_permission(request, "wms", "view")
    from services.wms_health_service import health_dashboard
    return await health_dashboard(await _scope(request))
