"""Permintaan ganti skema yang DITAHAN menunggu pemetaan alokasi Keuangan (W1-B #9, docs/audit/12; lihat `scheme_change.py`).

Permintaan lahir otomatis (HTTP 202) dari `POST /finance/ar/{deal}/schedule`, `POST /payment-schemes/contracts/{id}` dan
`POST /contracts/{id}/scheme` bila deal sudah punya uang nyata. Di sini Keuangan melihat pratinjau, menyerahkan pemetaan
(mode `manual_keuangan`) atau mengonfirmasi hitungan sistem (`urut_termin_tertua`/`proporsional`), atau membatalkannya.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import scheme_change as sc
from core_utils import serialize_doc
from db import ORG_ID
from idempotency import Conflict
from rbac import audit_log, require_permission

router = APIRouter(prefix="/finance/scheme-changes", tags=["finance-scheme-change"])


class MapAlloc(BaseModel):
    no: int
    amount: int


class MapRow(BaseModel):
    receipt_id: str
    allocations: List[MapAlloc] = Field(default_factory=list)


class ApplyIn(BaseModel):
    reason: str
    mapping: Optional[List[MapRow]] = None
    confirm: bool = False


class CancelIn(BaseModel):
    reason: str


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


@router.get("")
async def list_requests(deal_id: str = None, status: str = None,
                        user: dict = Depends(require_permission("finance", "view"))):
    rows = await sc.list_requests(_org(user), deal_id, status)
    return {"data": serialize_doc(rows), "total": len(rows)}


@router.get("/{rid}")
async def get_request(rid: str, user: dict = Depends(require_permission("finance", "view"))):
    try:
        return {"data": serialize_doc(await sc.get_request(_org(user), rid))}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{rid}/apply")
async def apply_request(rid: str, payload: ApplyIn, user: dict = Depends(require_permission("finance", "approve"))):
    """Terapkan: manual → `mapping` wajib; mode hitung sistem → `confirm: true`. Alasan wajib, tercatat."""
    mapping = [m.model_dump() for m in payload.mapping] if payload.mapping is not None else None
    try:
        doc = await sc.apply(_org(user), rid, user, mapping=mapping, reason=payload.reason, confirm=payload.confirm)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Conflict:
        raise
    except sc.Held as h:   # tidak seharusnya: jalur terapkan tidak membuka permintaan baru
        raise HTTPException(status_code=409, detail=h.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "approve", "scheme_change_request", rid,
                    {"op": doc.get("op"), "deal_id": doc.get("deal_id"), "reason": payload.reason,
                     "mode": doc.get("mode"), "mapping": doc.get("applied_mapping")})
    return {"data": serialize_doc(doc), "message": "Skema diganti dan alokasi kuitansi dipetakan ke termin baru."}


@router.post("/{rid}/cancel")
async def cancel_request(rid: str, payload: CancelIn, user: dict = Depends(require_permission("finance", "update"))):
    try:
        doc = await sc.cancel(_org(user), rid, user.get("email"), payload.reason)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "reject", "scheme_change_request", rid, {"reason": payload.reason})
    return {"data": serialize_doc(doc)}
