"""Audit keuangan: tie-out GL (lampu merah dasbor) + laporan HPP RAB vs realisasi per unit."""
from fastapi import APIRouter, Depends, HTTPException

import event_retry as er
import finance_audit as fa
from db import ORG_ID, db
from rbac import audit_log, can, require_permission, assert_project_access

router = APIRouter(prefix="/finance", tags=["finance-audit"])


@router.get("/reconcile")
async def reconcile(user: dict = Depends(require_permission("finance", "view"))):
    data = await fa.reconcile(user.get("org_id", ORG_ID))
    data["can_retry_events"] = await can(user.get("role"), "finance", "approve")
    return {"data": data}


# ---------------------------------------------------------------- event pembukuan gagal (GL-09)
@router.get("/events/failed")
async def failed_events(status: str = "failed", limit: int = 100,
                        user: dict = Depends(require_permission("finance", "view"))):
    """Event pembukuan yang tidak berhasil diposting. `status`: failed (bawaan) | retrying | all."""
    rows = await er.list_problems(user.get("org_id", ORG_ID), status, limit)
    return {"data": rows, "total": len(rows)}


async def _retry_one(org: str, event_id: str, user: dict) -> dict:
    from engine import dispatch_pending
    try:
        await er.requeue(org, event_id, user.get("email"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await dispatch_pending()
    ev = await db.events.find_one({"id": event_id, "org_id": org},
                                  {"_id": 0, "id": 1, "type": 1, "status": 1, "last_error": 1,
                                   "next_retry_at": 1})
    await audit_log(user, "event_retry", "events", event_id, {"status": ev and ev.get("status")})
    return ev


@router.post("/events/{event_id}/retry")
async def retry_event(event_id: str, user: dict = Depends(require_permission("finance", "approve"))):
    """Proses ulang satu event pembukuan yang gagal — setelah penyebabnya dibetulkan. Jurnal yang sudah
    ada tidak diubah (handler idempoten per source_event)."""
    return {"data": await _retry_one(user.get("org_id", ORG_ID), event_id, user)}


@router.post("/events/retry-failed")
async def retry_all_failed(user: dict = Depends(require_permission("finance", "approve"))):
    """Proses ulang SEMUA event yang gagal permanen (maks 200). Mengembalikan status akhir tiap event."""
    org = user.get("org_id", ORG_ID)
    out = []
    for r in await er.list_problems(org, "failed", 200):
        out.append(await _retry_one(org, r["id"], user))
    return {"data": out, "total": len(out),
            "still_failed": sum(1 for e in out if e and e.get("status") != "dispatched")}


@router.get("/hpp-unit")
async def hpp_unit(project_id: str, user: dict = Depends(require_permission("finance", "view"))):
    org = user.get("org_id", ORG_ID)
    if not await db.projects.find_one({"id": project_id, "org_id": org}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    await assert_project_access(project_id, user)
    return {"data": await fa.hpp_per_unit(org, project_id)}
