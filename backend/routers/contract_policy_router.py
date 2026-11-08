"""KEBIJAKAN TINGKAT KONTRAK (W2-B) — baca nilai efektif, timpa per kontrak, kembali mengikuti proyek/organisasi.

  GET    /contracts/{id}/policy        nilai efektif + asal tiap kunci ber-level kontrak, opsi & label, boleh-diubah/terkunci, riwayat
  PUT    /contracts/{id}/policy/{key}  {value, reason} — menimpa untuk kontrak ini
  DELETE /contracts/{id}/policy/{key}  ?reason= — mencabut penimpaan (kembali mengikuti pengaturan proyek/organisasi SEKARANG)

Izin: `contracts:view` untuk membaca (sales hanya kontrak miliknya); mengubah = `contracts:update` DITAMBAH izin penulis kunci itu
(`writer` pada spesifikasi; kunci keuangan seperti BPHTB = `finance:manage` → Manajer Keuangan, owner, super admin). Lintas organisasi = 404.
Logika ada di `contract_policy.py`; di sini hanya pemetaan galat → HTTP (400 masukan/aturan, 403 izin, 404, 409 bentrok) dan audit log.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import contract_policy as cp
from core_utils import serialize_doc
from db import db
from idempotency import Conflict
from org_scope import get_in_org
from rbac import audit_log, can, is_scoped_sales, require_permission

router = APIRouter(tags=["contract-policy"])


class PolicyIn(BaseModel):
    value: Any
    reason: Optional[str] = None


async def _contract(contract_id: str, user: dict) -> dict:
    c = await get_in_org(db.contracts, contract_id, user, name="Kontrak")
    if is_scoped_sales(user) and c.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan kontrak Anda")
    return c


async def _may_write(user: dict, key: str) -> None:
    res, act = cp.writer_of(key)
    if not await can(user.get("role"), res, act):
        raise HTTPException(status_code=403, detail=f"Akses ditolak: mengubah kebijakan ini butuh izin '{act}' pada '{res}'")


@router.get("/contracts/{contract_id}/policy")
async def get_policy(contract_id: str, user: dict = Depends(require_permission("contracts", "view"))):
    c = await _contract(contract_id, user)
    return {"data": serialize_doc(await cp.view(c["org_id"], c))}


@router.put("/contracts/{contract_id}/policy/{key}")
async def put_policy(contract_id: str, key: str, payload: PolicyIn,
                     user: dict = Depends(require_permission("contracts", "update"))):
    c = await _contract(contract_id, user)
    await _may_write(user, key)
    try:
        res = await cp.set_override(c["org_id"], contract_id, key, payload.value, payload.reason, user.get("email"))
    except Conflict:
        raise   # 409 lewat penangan global (bentrok dengan permintaan lain)
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "contract_policy", contract_id,
                    {"key": key, "value": payload.value, "reason": payload.reason, "action": "set"})
    return {"data": serialize_doc({**res, "policy": await cp.view(c["org_id"], await _contract(contract_id, user))})}


@router.delete("/contracts/{contract_id}/policy/{key}")
async def delete_policy(contract_id: str, key: str, reason: Optional[str] = None,
                        user: dict = Depends(require_permission("contracts", "update"))):
    c = await _contract(contract_id, user)
    await _may_write(user, key)
    try:
        res = await cp.clear_override(c["org_id"], contract_id, key, reason, user.get("email"))
    except Conflict:
        raise
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "contract_policy", contract_id, {"key": key, "reason": reason, "action": "clear"})
    return {"data": serialize_doc({**res, "policy": await cp.view(c["org_id"], await _contract(contract_id, user))})}
