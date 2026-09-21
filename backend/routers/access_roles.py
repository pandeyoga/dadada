"""Router PERAN & HAK AKSES (`/api/access/...`) — dipakai tab "Peran & Hak Akses"
di layar Badan Usaha & Akses. Aturan di `services/custom_role_service.py`."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from access_modules import ACTION_LABEL, LEVEL_LABEL, RESOURCE_LABEL, public_catalog
from dependencies import audit, require_permission
from services import custom_role_service as svc

router = APIRouter(prefix="/api/access", tags=["access-roles"])


class RoleCreate(BaseModel):
    label: str
    description: str = ""
    base_role: str = ""
    levels: Dict[str, str] = {}
    permissions: Optional[Dict[str, List[str]]] = None


class RolePatch(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    levels: Optional[Dict[str, str]] = None
    permissions: Optional[Dict[str, List[str]]] = None


class RolePreview(BaseModel):
    role_id: str = ""
    base_role: str = ""
    levels: Dict[str, str] = {}
    permissions: Optional[Dict[str, List[str]]] = None


class RoleMoveUsers(BaseModel):
    to_role: str


@router.post("/roles/preview")
async def preview_role(payload: RolePreview, request: Request) -> Dict[str, Any]:
    await require_permission(request, "permission", "view")
    return await svc.preview_role(payload.model_dump())


@router.post("/roles/{rid}/move-users")
async def move_role_users(rid: str, payload: RoleMoveUsers, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "permission", "update")
    out = await svc.move_users(rid, payload.to_role)
    await audit(actor["name"], "role_users_moved", "custom_role", rid, out)
    return out


@router.get("/modules")
async def list_modules(request: Request) -> Dict[str, Any]:
    await require_permission(request, "permission", "view")
    return {"modules": public_catalog(), "levels": LEVEL_LABEL,
            "resource_labels": RESOURCE_LABEL, "action_labels": ACTION_LABEL}


@router.get("/roles")
async def list_roles(request: Request) -> Dict[str, Any]:
    await require_permission(request, "permission", "view")
    return {"roles": await svc.all_roles()}


@router.get("/roles/{rid}")
async def get_role(rid: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "permission", "view")
    return await svc.get_role(rid)


@router.post("/roles")
async def create_role(payload: RoleCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "permission", "update")
    out = await svc.create_custom(payload.model_dump())
    await audit(actor["name"], "custom_role_created", "custom_role", out["id"],
                {"label": out["label"], "base_role": out["base_role"], "levels": out["levels"]})
    return out


@router.patch("/roles/{rid}")
async def patch_role(rid: str, payload: RolePatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "permission", "update")
    out = await svc.update_role(rid, payload.model_dump(exclude_none=True))
    await audit(actor["name"], "role_access_updated", "custom_role", rid,
                {"label": out["label"], "changes": out.get("changes", {}), "users": out["users"]})
    return out


@router.post("/roles/{rid}/reset")
async def reset_role(rid: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "permission", "update")
    out = await svc.reset_builtin(rid)
    await audit(actor["name"], "role_access_reset", "custom_role", rid, {"label": out["label"]})
    return out


@router.delete("/roles/{rid}")
async def delete_role(rid: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "permission", "update")
    out = await svc.delete_custom(rid)
    await audit(actor["name"], "custom_role_deleted", "custom_role", rid, out)
    return out
