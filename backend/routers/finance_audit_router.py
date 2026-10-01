"""Audit keuangan: tie-out GL (lampu merah dasbor) + laporan HPP RAB vs realisasi per unit."""
from fastapi import APIRouter, Depends, HTTPException

import finance_audit as fa
from db import ORG_ID, db
from rbac import require_permission, assert_project_access

router = APIRouter(prefix="/finance", tags=["finance-audit"])


@router.get("/reconcile")
async def reconcile(user: dict = Depends(require_permission("finance", "view"))):
    return {"data": await fa.reconcile(user.get("org_id", ORG_ID))}


@router.get("/hpp-unit")
async def hpp_unit(project_id: str, user: dict = Depends(require_permission("finance", "view"))):
    org = user.get("org_id", ORG_ID)
    if not await db.projects.find_one({"id": project_id, "org_id": org}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    await assert_project_access(project_id, user)
    return {"data": await fa.hpp_per_unit(org, project_id)}
