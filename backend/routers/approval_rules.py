"""Approval Rules Router — CRUD matriks ambang persetujuan (`approval_rules`).

Skema TUNGGAL = skema yang dibaca mesin (`config_service.evaluate_approval`):
{doc_type, entity_id, min_amount, max_amount, required_role, sort, active, is_percent}.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from db import db
from dependencies import require_permission, current_user
from entity_scope import assert_entity_access, entity_ctx, resolve_scope_ids
from services import approval_service

router = APIRouter(prefix="/api")

VALID_DOC_TYPES = ["sales_order", "purchase_order", "purchase_requisition", "discount"]
VALID_ROLES = ["", "manager", "admin", "owner"]


class ApprovalRuleCreate(BaseModel):
    doc_type: str = Field(..., description="Jenis dokumen (sales_order, purchase_order, purchase_requisition, discount)")
    min_amount: float = Field(0, ge=0, description="Batas bawah rentang (inklusif)")
    max_amount: Optional[float] = Field(None, description="Batas atas rentang (eksklusif); kosong = tanpa batas")
    required_role: str = Field("", description="Peran penyetuju; '' = tanpa persetujuan (lolos otomatis)")
    sort: int = Field(default=1, ge=1, description="Urutan evaluasi (kecil = lebih dulu)")
    active: bool = Field(default=True)
    description: str = Field(default="")
    entity_id: str = Field(default="all", description="'all' = berlaku semua entitas (warisan grup)")


class ApprovalRuleUpdate(BaseModel):
    doc_type: Optional[str] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = None
    required_role: Optional[str] = None
    sort: Optional[int] = Field(None, ge=1)
    active: Optional[bool] = None
    description: Optional[str] = None
    entity_id: Optional[str] = None


def _validate(doc_type: Optional[str], required_role: Optional[str],
              min_amount: Optional[float], max_amount: Optional[float]):
    if doc_type is not None and doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400,
                            detail=f"doc_type tidak sah. Pilihan: {', '.join(VALID_DOC_TYPES)}")
    if required_role is not None and required_role not in VALID_ROLES:
        raise HTTPException(status_code=400,
                            detail="required_role tidak sah. Pilihan: kosong (tanpa persetujuan), manager, admin, owner")
    if max_amount is not None and min_amount is not None and max_amount <= min_amount:
        raise HTTPException(status_code=400, detail="max_amount harus lebih besar dari min_amount")


@router.get("/approval-rules")
async def list_approval_rules(
    request: Request,
    doc_type: Optional[str] = None,
    active: Optional[bool] = None
) -> List[Dict[str, Any]]:
    await require_permission(request, "settings", "view")
    ctx = await entity_ctx(request)
    return await approval_service.get_approval_rules(
        doc_type=doc_type, active=active,
        entity_ids=resolve_scope_ids(ctx),
    )


def _assert_rule_entity_allowed(entity_id: Optional[str], ctx) -> None:
    """Aturan ber-cakupan entitas hanya boleh menunjuk entitas dalam wewenang pengguna."""
    if entity_id in (None, "", "all"):
        return
    if entity_id not in ctx.allowed_entity_ids:
        raise HTTPException(status_code=403, detail="Tidak berwenang atas entitas ini")


@router.post("/approval-rules")
async def create_approval_rule(payload: ApprovalRuleCreate, request: Request) -> Dict[str, Any]:
    await require_permission(request, "settings", "manage")
    user = await current_user(request)
    _validate(payload.doc_type, payload.required_role, payload.min_amount, payload.max_amount)
    _assert_rule_entity_allowed(payload.entity_id, await entity_ctx(request))
    return await approval_service.create_approval_rule(
        doc_type=payload.doc_type,
        min_amount=payload.min_amount,
        max_amount=payload.max_amount,
        required_role=payload.required_role,
        sort=payload.sort,
        active=payload.active,
        description=payload.description,
        created_by=user["email"],
        entity_id=payload.entity_id or "all",
        is_percent=payload.doc_type == "discount",
    )


@router.get("/approval-rules/{rule_id}")
async def get_approval_rule(rule_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "settings", "view")
    rule = await db.approval_rules.find_one({"id": rule_id}, {"_id": 0})
    if not rule:
        raise HTTPException(status_code=404, detail="Approval rule tidak ditemukan")
    if rule.get("entity_id") not in (None, "", "all"):
        assert_entity_access(rule, "approval_rules", await entity_ctx(request))
    return rule


@router.patch("/approval-rules/{rule_id}")
async def update_approval_rule(rule_id: str, payload: ApprovalRuleUpdate, request: Request) -> Dict[str, Any]:
    await require_permission(request, "settings", "manage")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada field untuk diubah")
    existing = await db.approval_rules.find_one({"id": rule_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Approval rule tidak ditemukan")
    # Nilai efektif pasca-PATCH: field yang dikirim menang, sisanya dari dokumen lama.
    merged_min = updates.get("min_amount", existing.get("min_amount", 0))
    merged_max = updates["max_amount"] if "max_amount" in updates else existing.get("max_amount")
    _validate(updates.get("doc_type"), updates.get("required_role"), merged_min, merged_max)
    if "entity_id" in updates:
        _assert_rule_entity_allowed(updates["entity_id"], await entity_ctx(request))
        updates["entity_id"] = updates["entity_id"] or "all"
    if "doc_type" in updates:
        updates["is_percent"] = updates["doc_type"] == "discount"
    try:
        return await approval_service.update_approval_rule(rule_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/approval-rules/{rule_id}")
async def delete_approval_rule(rule_id: str, request: Request) -> Dict[str, str]:
    """Soft delete (set active=False) — mesin approval berhenti membaca aturan ini."""
    await require_permission(request, "settings", "manage")
    success = await approval_service.delete_approval_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Approval rule tidak ditemukan")
    return {"message": "Aturan persetujuan dinonaktifkan"}
