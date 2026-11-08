"""Posting Profile (Fase 1–2) — katalog peristiwa, dry-run, dan laporan resolver BAYANGAN. SEMUA READ-ONLY.

Endpoints (RBAC resource `gl`, aksi `view`):
  GET  /gl/posting-profile/catalog          — katalog peristiwa + peran akun (status di CoA) + cakupan jujur
  POST /gl/posting-profile/dry-run          — {event, inputs} → jurnal hasil + cek seimbang/akun/tipe/peringatan (tidak menulis)
  GET  /gl/posting-profile/shadow-report    — ringkasan selisih resolver bayangan per peristiwa (+ selisih terbaru)
  GET  /gl/posting-profile/verify/{jid}     — bandingkan SATU jurnal tersimpan dengan profil v0

Profil v0 hidup di kode (`posting_profile_v0.py`) dan TIDAK bisa diubah lewat API pada fase ini: tidak ada rute
tulis, sehingga metode lain di path ini dijawab 405. Perubahan profil menunggu fase maker-checker (docs/audit/03_..._5).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import posting_profile as pp
import posting_shadow as ps
from db import ORG_ID
from rbac import require_permission

router = APIRouter(prefix="/gl/posting-profile", tags=["posting-profile"])


class DryRunBody(BaseModel):
    event: str = Field(..., min_length=1, max_length=64, description="Kunci peristiwa katalog, mis. sales.receipt")
    inputs: dict = Field(default_factory=dict, description="Variabel peristiwa {nama: nilai}")


@router.get("/catalog")
async def get_catalog(user: dict = Depends(require_permission("gl", "view"))):
    return {"data": await pp.catalog(user.get("org_id", ORG_ID))}


@router.post("/dry-run")
async def dry_run(body: DryRunBody, user: dict = Depends(require_permission("gl", "view"))):
    if len(body.inputs) > 40 or any(isinstance(v, (dict, list)) for v in body.inputs.values()):
        raise HTTPException(status_code=400, detail="'inputs' harus objek datar {variabel: angka/teks} (maks 40 isian).")
    if body.event not in pp.EVENTS:
        raise HTTPException(status_code=404, detail=f"Peristiwa '{body.event[:64]}' tidak ada di katalog posting profile.")
    return {"data": await pp.dry_run(user.get("org_id", ORG_ID), body.event, body.inputs)}


@router.get("/shadow-report")
async def shadow_report(limit: int = 20, days: int = 30, user: dict = Depends(require_permission("gl", "view"))):
    return {"data": await ps.report(user.get("org_id", ORG_ID), limit=limit, days=days)}


@router.get("/verify/{jid}")
async def verify(jid: str, user: dict = Depends(require_permission("gl", "view"))):
    res = await ps.verify_journal(user.get("org_id", ORG_ID), jid)
    if not res.get("found"):
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    return {"data": res}
