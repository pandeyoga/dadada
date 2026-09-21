"""FASE R0 — Router lokasi gudang (sites) + seed blueprint peta gudang user."""
from services.wilayah_service import normalize_location, LOCATION_KEYS
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from dependencies import require_permission, audit
from services import warehouse_profile_service as whp
from db import db

router = APIRouter(prefix="/api")


class SitePayload(BaseModel):
    name: str
    city: Optional[str] = ""
    province: Optional[str] = ""
    province_code: Optional[str] = ""
    city_code: Optional[str] = ""
    district: Optional[str] = ""
    district_code: Optional[str] = ""
    postal_code: Optional[str] = ""


class SitePatch(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    province_code: Optional[str] = None
    city_code: Optional[str] = None
    district: Optional[str] = None
    district_code: Optional[str] = None
    postal_code: Optional[str] = None


@router.get("/warehouse-sites")
async def get_sites(request: Request) -> Dict[str, Any]:
    await require_permission(request, "warehouse", "view")
    return {"sites": await whp.list_sites()}


@router.post("/warehouse-sites")
async def post_site(payload: SitePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "create")
    site = await whp.create_site(payload.name, payload.city or "", actor["name"],
                                 location=normalize_location(payload.model_dump()))
    await audit(actor["name"], "warehouse_site_created", "warehouse_site", site["id"], site)
    return site


@router.patch("/warehouse-sites/{site_id}")
async def patch_site(site_id: str, payload: SitePatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "update")
    patch = payload.model_dump(exclude_none=True)
    if any(k in patch for k in LOCATION_KEYS):
        _ex = await db.warehouse_sites.find_one({"id": site_id}, {"_id": 0}) or {}
        patch.update(normalize_location({**{k: _ex.get(k, "") for k in LOCATION_KEYS}, **patch}))
    site = await whp.update_site(site_id, patch)
    await audit(actor["name"], "warehouse_site_updated", "warehouse_site", site_id, site)
    return site


@router.delete("/warehouse-sites/{site_id}")
async def del_site(site_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "delete")
    res = await whp.delete_site(site_id)
    await audit(actor["name"], "warehouse_site_deleted", "warehouse_site", site_id, {})
    return res


@router.post("/warehouse-sites/seed-blueprint")
async def post_seed_blueprint(request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "warehouse", "create")
    res = await whp.seed_blueprint(actor["name"])
    await audit(actor["name"], "warehouse_blueprint_seeded", "warehouse_site", "blueprint", res)
    return res
