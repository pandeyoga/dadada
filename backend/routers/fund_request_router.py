"""Pengajuan keuangan: siapa pun mengajukan; finance/owner menyetujui & mencairkan (SoD)."""
from fastapi import APIRouter, Depends, HTTPException

import fund_requests as fr
from core_utils import parse_pagination, serialize_doc
from db import ORG_ID, db
from models_fund_request import (FundRequestCreate, FundRequestDecision, FundRequestDisburse,
                                 FundRequestSettle)
from rbac import audit_log, can, require_permission

router = APIRouter(prefix="/fund-requests", tags=["fund-requests"])
RES = "fund_request"


async def _scope(user: dict, q: dict) -> dict:
    q = dict(q)
    q["org_id"] = user.get("org_id", ORG_ID)
    if not await can(user.get("role"), RES, "view_all"):
        q["requested_by"] = user.get("email")
    return q


def _err(e):
    return HTTPException(status_code=400, detail=str(e))


@router.get("")
async def listing(status: str = None, type: str = None, q: str = None, skip: int = 0,
                  limit: int = 50, user: dict = Depends(require_permission(RES, "view"))):
    skip, limit = parse_pagination(skip, limit)
    query = await _scope(user, {})
    if status:
        query["status"] = {"$in": status.split(",")}
    if type:
        query["type"] = type
    if q:
        query["$or"] = [{"no": {"$regex": q, "$options": "i"}},
                        {"title": {"$regex": q, "$options": "i"}},
                        {"requester_name": {"$regex": q, "$options": "i"}}]
    total = await db[fr.COLL].count_documents(query)
    rows = await db[fr.COLL].find(query, {"_id": 0}).sort("created_at", -1) \
        .skip(skip).limit(limit).to_list(limit)
    return {"data": serialize_doc(rows), "total": total,
            "can_approve": await can(user.get("role"), RES, "approve")}


@router.get("/summary")
async def summary(user: dict = Depends(require_permission(RES, "view"))):
    own = None if await can(user.get("role"), RES, "view_all") else user.get("email")
    return {"data": await fr.summary(user.get("org_id", ORG_ID), own)}


@router.get("/{rid}")
async def detail(rid: str, user: dict = Depends(require_permission(RES, "view"))):
    doc = await db[fr.COLL].find_one(await _scope(user, {"id": rid}), {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pengajuan tidak ditemukan.")
    return {"data": serialize_doc(doc)}


@router.post("")
async def create(payload: FundRequestCreate,
                 user: dict = Depends(require_permission(RES, "create"))):
    try:
        doc = await fr.create(payload, user.get("email"), user.get("name"),
                              user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    await audit_log(user, "create", RES, doc["id"], {"amount": doc["amount"], "type": doc["type"]})
    return {"data": serialize_doc(doc)}


@router.post("/{rid}/approve")
async def approve(rid: str, payload: FundRequestDecision,
                  user: dict = Depends(require_permission(RES, "approve"))):
    try:
        doc = await fr.approve(rid, user.get("email"), payload.note, payload.approved_amount,
                               user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    await audit_log(user, "approve", RES, rid, {"approved_amount": doc.get("approved_amount")})
    return {"data": serialize_doc(doc)}


@router.post("/{rid}/reject")
async def reject(rid: str, payload: FundRequestDecision,
                 user: dict = Depends(require_permission(RES, "approve"))):
    try:
        doc = await fr.reject(rid, user.get("email"), payload.note, user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    await audit_log(user, "reject", RES, rid, {"reason": payload.note})
    return {"data": serialize_doc(doc)}


async def _own_or_approver(rid: str, user: dict) -> dict:
    org = user.get("org_id", ORG_ID)
    doc = await db[fr.COLL].find_one({"id": rid, "org_id": org}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pengajuan tidak ditemukan.")
    if doc.get("requested_by") != user.get("email") and not await can(user.get("role"), RES, "approve"):
        raise HTTPException(status_code=403, detail="Hanya pemohon atau finance yang boleh melakukan ini.")
    return doc


@router.post("/{rid}/cancel")
async def cancel(rid: str, user: dict = Depends(require_permission(RES, "update"))):
    await _own_or_approver(rid, user)
    try:
        doc = await fr.cancel(rid, user.get("email"), user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    return {"data": serialize_doc(doc)}


@router.post("/{rid}/disburse")
async def disburse(rid: str, payload: FundRequestDisburse,
                   user: dict = Depends(require_permission(RES, "approve"))):
    try:
        doc = await fr.disburse(rid, payload, user.get("email"), user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    await audit_log(user, "disburse", RES, rid, {"amount": doc.get("disbursed_amount")})
    return {"data": serialize_doc(doc)}


@router.post("/{rid}/settle")
async def settle(rid: str, payload: FundRequestSettle,
                 user: dict = Depends(require_permission(RES, "update"))):
    await _own_or_approver(rid, user)
    try:
        doc = await fr.settle(rid, payload, user.get("email"), user.get("org_id", ORG_ID))
    except ValueError as e:
        raise _err(e)
    await audit_log(user, "settle", RES, rid, {"expense_total": doc.get("expense_total")})
    return {"data": serialize_doc(doc)}
