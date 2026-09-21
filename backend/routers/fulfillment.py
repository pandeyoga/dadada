"""FASE R7 — Router Fulfillment Wizard. Prefix /api."""
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from pydantic import BaseModel

from dependencies import require_permission, audit
from entity_scope import entity_ctx, resolve_scope_ids
from services import fulfillment_wizard_service as wiz

router = APIRouter(prefix="/api")


class WizIntercoPayload(BaseModel):
    seller_entity_id: str
    items: List[Dict[str, Any]]


class WizPRPayload(BaseModel):
    items: List[Dict[str, Any]]


async def _scope(request: Request) -> List[str]:
    return resolve_scope_ids(await entity_ctx(request))


@router.get("/fulfillment/wizard/{so_id}")
async def get_wizard(so_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "order", "view")
    return await wiz.analyze(so_id, await _scope(request))


@router.post("/fulfillment/wizard/{so_id}/create-interco")
async def post_wizard_interco(so_id: str, payload: WizIntercoPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "create")
    doc = await wiz.create_interco_draft(so_id, payload.seller_entity_id, payload.items,
                                         await _scope(request), actor)
    await audit(actor["name"], "wizard_interco_created", "interco", doc.get("id", ""),
                {"so_id": so_id, "seller": payload.seller_entity_id})
    return doc


@router.post("/fulfillment/wizard/{so_id}/create-pr")
async def post_wizard_pr(so_id: str, payload: WizPRPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "order", "create")
    doc = await wiz.create_pr_draft(so_id, payload.items, await _scope(request), actor)
    await audit(actor["name"], "wizard_pr_created", "purchase_requisition", doc.get("id", ""),
                {"so_id": so_id, "items": len(payload.items)})
    return doc
