"""Kebersihan Data — riwayat normalisasi otomatis (EYD + nomor telepon) & pengembalian per-record."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from db import db
from dependencies import require_role, audit
from services import data_hygiene_service as svc
from services.turn_notification_service import turn_map_public

router = APIRouter(prefix="/api")
ROLES = ["admin", "manager"]


@router.get("/data-hygiene/summary")
async def hygiene_summary(request: Request) -> Dict[str, Any]:
    await require_role(request, ROLES)
    return await svc.summary()


@router.get("/data-hygiene/log")
async def hygiene_log(request: Request, collection: Optional[str] = None, reverted: Optional[bool] = None,
                      q: str = "", limit: int = 100, skip: int = 0) -> Dict[str, Any]:
    await require_role(request, ROLES)
    query: Dict[str, Any] = {}
    if collection:
        query["collection"] = collection
    if reverted is not None:
        query["reverted"] = reverted
    if q.strip():
        query["doc_label"] = {"$regex": q.strip(), "$options": "i"}
    total = await db.data_hygiene_log.count_documents(query)
    items = await db.data_hygiene_log.find(query, {"_id": 0}).sort("applied_at", -1).skip(max(0, skip)).limit(max(1, min(limit, 500))).to_list(500)
    return {"items": items, "total": total}


@router.get("/data-hygiene/preview")
async def hygiene_preview(request: Request, collection: Optional[str] = None) -> List[Dict[str, Any]]:
    await require_role(request, ROLES)
    return await svc.preview([collection] if collection else None)


@router.post("/data-hygiene/run")
async def hygiene_run(request: Request, collection: Optional[str] = None) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    res = await svc.run(trigger="manual", actor=actor["name"], collections=[collection] if collection else None)
    await audit(actor["name"], "data_hygiene_run", "data_hygiene", "run", res)
    return res


@router.post("/data-hygiene/log/{log_id}/revert")
async def hygiene_revert(log_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    res = await svc.revert(log_id, actor["name"])
    await audit(actor["name"], "data_hygiene_reverted", res["collection"], res["doc_id"], {"log_id": log_id})
    return res


@router.post("/data-hygiene/{collection}/{doc_id}/unlock")
async def hygiene_unlock(collection: str, doc_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    res = await svc.unlock(collection, doc_id)
    await audit(actor["name"], "data_hygiene_unlocked", collection, doc_id, res)
    return res


@router.get("/turn-notifications/map")
async def turn_map(request: Request) -> List[Dict[str, Any]]:
    await require_role(request, ROLES)
    return turn_map_public()


@router.get("/data-hygiene/unverified-locations")
async def unverified_locations(request: Request, collection: Optional[str] = None) -> Dict[str, Any]:
    await require_role(request, ROLES)
    return await svc.unverified_locations(collection)


@router.post("/data-hygiene/location/{collection}/{doc_id}")
async def fix_location(collection: str, doc_id: str, body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ROLES)
    res = await svc.fix_location(collection, doc_id, body or {}, actor["name"])
    await audit(actor["name"], "location_fixed", collection, doc_id, res)
    return res
