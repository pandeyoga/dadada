"""Riwayat dokumen terbit per lead/customer (Fase 91)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import customer_scope as cs
import doc_history
import wa_docs
from db import ORG_ID, db
from org_scope import get_in_org
from rbac import audit_log, is_scoped_sales, require_permission


class SendWaIn(BaseModel):
    entity_type: str
    entity_id: str
    pdf_url: str
    label: str
    number: Optional[str] = None
    caption: Optional[str] = None

router = APIRouter(prefix="/doc-history", tags=["doc-history"])


async def _assert_entity_access(user: dict, entity_type: str, entity_id: str, *, owned: bool = True) -> None:
    """AZ-06: entitas tujuan harus ada di organisasi pemanggil (404 bila tidak) dan — bila `owned` —
    untuk sales ber-scope "own" harus milik sales itu (lead.assigned_to / lingkup pembeli)."""
    if entity_type == "lead":
        lead = await get_in_org(db.leads, entity_id, user, projection={"_id": 0, "assigned_to": 1}, name="Lead")
        if owned and is_scoped_sales(user) and lead.get("assigned_to") != user.get("email"):
            raise HTTPException(status_code=403, detail="Akses ditolak: bukan lead Anda")
    else:
        await get_in_org(db.customers, entity_id, user, projection={"_id": 1}, name="Customer")
        if owned:
            await cs.assert_access(user, entity_id)


@router.post("/send-wa")
async def send_document_wa(p: SendWaIn, request: Request,
                           user: dict = Depends(require_permission("documents", "view"))):
    """Fase 98D — kirim PDF dokumen terbit ke WhatsApp pembeli (render lewat jalur tombol PDF yang sama)."""
    if p.entity_type not in ("lead", "customer"):
        raise HTTPException(status_code=400, detail="entity_type harus lead atau customer.")
    await _assert_entity_access(user, p.entity_type, p.entity_id)
    res = await wa_docs.send_document(user.get("org_id", ORG_ID), app=request.app, headers=dict(request.headers),
                                      entity_type=p.entity_type, entity_id=p.entity_id, pdf_url=p.pdf_url,
                                      label=p.label, number=p.number, caption=p.caption, actor=user.get("email"))
    await audit_log(user, "send_wa", "doc_share", res["share"]["id"], {"pdf_url": p.pdf_url, "status": res["message"]["status"]})
    if res["message"]["status"] == "failed":
        raise HTTPException(status_code=424, detail=f"Kirim WA gagal ({res['message'].get('error_code')}): "
                                                    f"{res['message'].get('error_detail')}")
    return {"data": res}


@router.get("/{entity_type}/{entity_id}")
async def issued_documents(entity_type: str, entity_id: str,
                           user: dict = Depends(require_permission("documents", "view"))):
    if entity_type not in ("lead", "customer"):
        raise HTTPException(status_code=400, detail="entity_type harus lead atau customer.")
    await _assert_entity_access(user, entity_type, entity_id, owned=False)   # riwayat: cukup se-organisasi
    return {"data": await doc_history.history(user.get("org_id", ORG_ID), entity_type, entity_id)}
