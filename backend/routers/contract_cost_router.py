"""Permohonan isian bebas biaya kontrak (W2-C #6): daftar, putusan Keuangan, pembatalan oleh pemohon.

Permohonan lahir dari `POST /contracts/{id}/costs` bila model biaya kontrak mewajibkan persetujuan (lihat `contract_cost_model`).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import contract_cost_model as ccm
import contracts_engine as ce
from core_utils import serialize_doc
from db import ORG_ID
from idempotency import Conflict
from rbac import audit_log, is_scoped_sales, require_permission

router = APIRouter(tags=["contract-cost-requests"])


class DecideIn(BaseModel):
    approve: bool
    note: Optional[str] = None


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


def _err(e: Exception):
    if isinstance(e, PermissionError):
        return HTTPException(status_code=403, detail=str(e))
    if isinstance(e, LookupError):
        return HTTPException(status_code=404, detail=str(e))
    return HTTPException(status_code=400, detail=str(e))


@router.get("/contracts/{cid}/cost-requests")
async def list_requests(cid: str, user: dict = Depends(require_permission("contracts", "view_own"))):
    try:
        c = await ce.get_raw(_org(user), cid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if is_scoped_sales(user) and c.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan kontrak Anda")
    return {"data": serialize_doc(await ccm.list_for_contract(_org(user), cid))}


@router.get("/cost-requests")
async def pending_requests(user: dict = Depends(require_permission("finance", "approve"))):
    """Antrean Keuangan: permohonan isian biaya kontrak yang menunggu keputusan."""
    return {"data": serialize_doc(await ccm.list_pending(_org(user)))}


@router.post("/cost-requests/{rid}/decide")
async def decide(rid: str, p: DecideIn, user: dict = Depends(require_permission("finance", "approve"))):
    try:
        doc = await ccm.decide(_org(user), rid, p.approve, p.note, user)
    except Conflict:
        raise
    except (ValueError, LookupError, PermissionError) as e:
        raise _err(e)
    await audit_log(user, "approve" if p.approve else "reject", "contract_cost_requests", rid, {"note": p.note})
    return {"data": serialize_doc(doc)}


@router.post("/cost-requests/{rid}/cancel")
async def cancel(rid: str, user: dict = Depends(require_permission("contracts", "update"))):
    try:
        doc = await ccm.cancel(_org(user), rid, user)
    except Conflict:
        raise
    except (ValueError, LookupError, PermissionError) as e:
        raise _err(e)
    await audit_log(user, "cancel", "contract_cost_requests", rid, {})
    return {"data": serialize_doc(doc)}
