"""Router FEEDBACK / KOMPLAIN PELANGGAN per SO — izin `order.view` (lihat) & `order.update` (catat/tindak)."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from db import db
from dependencies import audit, require_permission
from entity_scope import assert_entity_access, entity_ctx, resolve_list_scope
from services import customer_feedback_service as svc

router = APIRouter(prefix="/api", tags=["customer-feedback"])


class FeedbackCreate(BaseModel):
    order_id: str
    title: str = Field(..., min_length=5)
    category: str = "lainnya"
    severity: str = "sedang"
    description: str = ""
    assignee_id: str = ""
    assignee_name: str = ""
    due_date: str = ""


class FeedbackUpdate(BaseModel):
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[str] = None
    severity: Optional[str] = None
    resolution: Optional[str] = None
    note: str = ""


@router.get("/customer-feedback/meta")
async def feedback_meta(request: Request) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    return {
        "categories": [{"value": c, "label": svc.CATEGORY_LABEL[c]} for c in svc.CATEGORIES],
        "severities": [{"value": s, "label": s.capitalize()} for s in svc.SEVERITIES],
        "statuses": [{"value": s, "label": svc.STATUS_LABEL[s]} for s in svc.STATUSES],
    }


@router.get("/customer-feedback/summary")
async def feedback_summary(request: Request, entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    return await svc.summary(resolve_list_scope(svc.COLL, {}, ctx, entity_id))


@router.get("/customer-feedback")
async def list_feedback(request: Request, entity_id: Optional[str] = Query(None),
                        order_id: str = Query(""), status: str = Query(""),
                        customer_id: str = Query(""), assignee_id: str = Query("")) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    scope = resolve_list_scope(svc.COLL, {}, ctx, entity_id)
    rows = await svc.list_feedback(scope, order_id=order_id, status=status,
                                   customer_id=customer_id, assignee_id=assignee_id)
    return {"count": len(rows), "items": rows}


@router.post("/customer-feedback")
async def create_feedback(payload: FeedbackCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "update")
    order = await db.sales_orders.find_one({"id": payload.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan (SO) tidak ditemukan.")
    assert_entity_access(order, "sales_orders", await entity_ctx(request))
    try:
        doc = await svc.create_feedback(payload.model_dump(), actor)
    except svc.FeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(actor.get("name", ""), "customer_feedback_created", "customer_feedback", doc["id"],
                {"order_id": payload.order_id, "category": doc["category"], "severity": doc["severity"]})
    return doc


@router.patch("/customer-feedback/{fb_id}")
async def update_feedback(fb_id: str, payload: FeedbackUpdate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "update")
    doc = await db[svc.COLL].find_one({"id": fb_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Feedback tidak ditemukan.")
    assert_entity_access(doc, svc.COLL, await entity_ctx(request))
    try:
        updated = await svc.update_feedback(fb_id, payload.model_dump(exclude_none=True) | {"note": payload.note}, actor)
    except svc.FeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(actor.get("name", ""), "customer_feedback_updated", "customer_feedback", fb_id,
                {k: v for k, v in payload.model_dump(exclude_none=True).items() if k != "note"},
                reason=payload.note)
    return updated
