"""Satu master komponen biaya (W2-C #16): laporan selisih katalog↔aturan All-in, migrasi idempoten, penyelarasan katalog.

Lihat `cost_master.py` untuk rancangan. Semua endpoint organisasi-sadar (`user.org_id`).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import allin_engine as ae
import cost_master as cm
from core_utils import serialize_doc
from db import ORG_ID
from idempotency import Conflict
from rbac import audit_log, require_permission

router = APIRouter(prefix="/cost-master", tags=["cost-master"])


class SyncIn(BaseModel):
    reason: str
    direction: Optional[str] = "katalog_ikut_aturan"   # atau "aturan_ikut_katalog" (hanya mode katalog_sumber)


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


@router.get("/diff")
async def diff(usage: bool = False, probe: bool = False, user: dict = Depends(require_permission("catalog", "view"))):
    """Laporan selisih 'katalog vs aturan': peta field, baris per komponen (sama/beda/belum dimigrasi/hanya satu sisi/rujukan putus),
    mode berlaku, dan apakah opsi `katalog_sumber` sah dipilih (beserta alasannya). `usage` = kode pada snapshot deal/kontrak;
    `probe` = uji ekuivalensi hitung-ulang skema aktif di kedua mode."""
    org = _org(user)
    await ae.ensure_defaults(org)
    d = await cm.diff(org, usage=usage, probe=probe)
    mode, origin = await cm.policy.resolve_with_origin(cm.KEY_MODE, org_id=org)
    sebab = cm.reason_of(d, probe)   # tanpa probe: hanya selisih kolom; uji ekuivalensi dijalankan penuh saat opsi dipilih
    d["mode"] = {"value": mode, "origin": origin}
    d["katalog_sumber"] = {"tersedia": sebab is None, "alasan": sebab}
    return {"data": serialize_doc(d)}


@router.post("/migrate")
async def migrate(user: dict = Depends(require_permission("finance", "manage"))):
    """Migrasi IDEMPOTEN (tidak merusak): buat baris katalog yang belum ada, isi blok biaya, pasang rujukan `catalog_code` di master
    All-in. Tidak menyentuh skema, snapshot, tagihan, atau jurnal. Memanggil ulang = tidak ada perubahan."""
    org = _org(user)
    await ae.ensure_defaults(org)
    try:
        res = await cm.migrate(org, user.get("email"))
    except Conflict:
        raise
    await audit_log(user, "migrate", "cost_master", None, res)
    return {"data": res}


@router.post("/sync")
async def sync(p: SyncIn, user: dict = Depends(require_permission("finance", "manage"))):
    """'Selaraskan': `katalog_ikut_aturan` (bawaan; tagihan TIDAK berubah) menyamakan katalog dengan aturan All-in yang berjalan;
    `aturan_ikut_katalog` hanya pada mode katalog_sumber (perbaikan simpangan)."""
    org = _org(user)
    await ae.ensure_defaults(org)
    try:
        if p.direction == "aturan_ikut_katalog":
            res = await cm.sync_to_rules(org, user.get("email"), p.reason)
        elif p.direction in (None, "katalog_ikut_aturan"):
            res = await cm.sync_to_catalog(org, user.get("email"), p.reason)
        else:
            raise ValueError("direction harus 'katalog_ikut_aturan' atau 'aturan_ikut_katalog'.")
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "sync", "cost_master", None, {"direction": p.direction, "reason": p.reason,
                                                         "diselaraskan": res.get("diselaraskan")})
    return {"data": serialize_doc(res)}
