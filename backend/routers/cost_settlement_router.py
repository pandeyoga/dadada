"""ROUTER PERMOHONAN REFUND TITIPAN BIAYA PADA DEAL BATAL (W1-C #12) — prefix `/cancel-cost-settlements`.

Permohonan lahir dari penutup deal batal (`cancel_cost_settlement.apply_policy`) menurut kebijakan `cancel.cost_deposit.*`.
Pemisahan tugas (memakai izin pembatalan yang sudah ada — tidak ada izin baru):
  * **melihat** = `cancellation:view` (sales hanya deal miliknya);
  * **memutuskan** (setujui/tolak) = `cancellation:approve` (Manajer Keuangan) — penyetuju HARUS orang lain dari pemohon (dijaga mesin);
  * **membayar refund** = `cancellation:update` (Keuangan) lewat `money_op` (anti klik-ganda → kunci deal → kunci rekening + cek dana).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import cancel_cost_settlement as ccs
from core_utils import serialize_doc
from db import ORG_ID
from idempotency import Conflict
from rbac import audit_log, is_scoped_sales, require_permission

router = APIRouter(prefix="/cancel-cost-settlements", tags=["cancel-cost-settlements"])


class DecisionIn(BaseModel):
    approved: bool
    note: Optional[str] = Field(default=None, max_length=500)


class RefundIn(BaseModel):
    method: str = Field(default="transfer", max_length=20)
    amount: Optional[int] = Field(default=None, ge=1)
    cash_account_id: Optional[str] = None
    client_ref: Optional[str] = Field(default=None, max_length=80)
    note: Optional[str] = Field(default=None, max_length=300)


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


def _scoped(user: dict, row: dict) -> None:
    if is_scoped_sales(user) and row.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan permohonan atas deal Anda")


@router.get("")
async def listing(state: str = None, deal_id: str = None, limit: int = 100,
                  user: dict = Depends(require_permission("cancellation", "view"))):
    out = await ccs.listing(_org(user), state=state, deal_id=deal_id, limit=limit)
    if is_scoped_sales(user):
        out["data"] = [r for r in out["data"] if r.get("assigned_to") == user.get("email")]
        out["outstanding"] = sum(r["refund_outstanding"] for r in out["data"])
    return {"data": serialize_doc(out["data"]), "counts": out["counts"], "outstanding": out["outstanding"]}


@router.get("/{sid}")
async def detail(sid: str, user: dict = Depends(require_permission("cancellation", "view"))):
    try:
        row = await ccs.get(_org(user), sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    _scoped(user, row)
    return {"data": serialize_doc(row)}


@router.post("/{sid}/decision")
async def decide(sid: str, payload: DecisionIn, user: dict = Depends(require_permission("cancellation", "approve"))):
    """Setujui (jurnal + pembatalan invoice berlaku) atau tolak (alasan wajib; ditangani manual)."""
    try:
        row = await ccs.decide(_org(user), sid, user.get("email"), payload.approved, payload.note)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404 if "tidak ditemukan" in str(e) else 400, detail=str(e))
    await audit_log(user, "approve" if payload.approved else "reject", "cancel_cost_settlement", sid,
                    {"note": payload.note, "number": row.get("number"),
                     "refund": (row.get("settlement") or {}).get("refund_amount")})
    return {"data": serialize_doc(ccs.enrich(row))}


@router.post("/{sid}/refund")
async def pay_refund(sid: str, payload: RefundIn, user: dict = Depends(require_permission("cancellation", "update"))):
    """Bayar refund titipan biaya (boleh bertahap) — uang keluar lewat `money_op`."""
    try:
        out = await ccs.pay_refund(_org(user), sid, user.get("email"), method=payload.method, amount=payload.amount,
                                   cash_account_id=payload.cash_account_id, client_ref=payload.client_ref,
                                   note=payload.note)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404 if "tidak ditemukan" in str(e) else 400, detail=str(e))
    await audit_log(user, "update", "cancel_cost_settlement", sid,
                    {"refund": out["payment"]["amount"], "method": payload.method})
    return {"data": serialize_doc(ccs.enrich(out["settlement"])), "payment": serialize_doc(out["payment"])}
