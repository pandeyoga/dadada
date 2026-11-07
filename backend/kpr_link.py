"""Satu pengajuan KPR aktif per deal + tautan ke kontrak + plafon tersinkron (audit KT-23).

Dulu `POST /financing` selalu menyisipkan pengajuan baru: dua klik / dua petugas menghasilkan dua
pengajuan untuk satu deal, dan karena tampilan kontrak (`kpr_engine.kpr_of`) mengambil pengajuan
TERBARU, pengajuan baru tanpa `contract_id`/`kpr_stage` MENIMPA tampilan — progres bank yang sudah
berjalan (berkas → diajukan → SP3K) hilang dari layar dan tahap berikutnya ditolak "tahap sebelumnya
belum selesai". Plafon yang diisi di komponen biaya kontrak tidak pernah sampai ke pengajuan.
"""
from core_utils import now_iso
from db import db

TERMINAL_STATUS = ("rejected", "cancelled")   # PK3-08: deal batal menutup pengajuan
TERMINAL_STAGE = ("ditolak", "batal")


def create_lock(deal_id: str):
    """Kunci pembuatan pengajuan KPR per deal (cek-lalu-sisip dijadikan satu langkah)."""
    from idempotency import mutex
    return mutex(f"kpr:app:{deal_id}", wait=10, ttl=30, what="Pengajuan KPR deal ini")


async def active_app(org: str, deal_id: str) -> dict:
    """Pengajuan KPR deal yang MASIH berjalan (bukan ditolak/dibatalkan), atau None."""
    async for a in db.financing_apps.find({"org_id": org, "deal_id": deal_id},
                                          {"_id": 0}).sort("created_at", -1):
        if a.get("status") not in TERMINAL_STATUS and a.get("kpr_stage") not in TERMINAL_STAGE:
            return a
    return None


def is_pristine(app: dict) -> bool:
    """Pengajuan otomatis kontrak KPR yang belum diisi siapa pun (tanpa bank, masih draft)."""
    return (app.get("status") == "draft" and not (app.get("bank_name") or "").strip()
            and app.get("kpr_stage") in (None, "", "berkas_lengkap"))


async def contract_fields(org: str, deal_id: str, actor: str) -> dict:
    """Bidang tambahan bagi pengajuan baru bila deal ini punya kontrak KPR (tautan + tahap awal)."""
    c = await db.contracts.find_one({"org_id": org, "deal_id": deal_id, "scheme": "kpr"},
                                    {"_id": 0, "id": 1, "customer_id": 1})
    if not c:
        return {}
    ts = now_iso()
    return {"contract_id": c["id"], "customer_id": c.get("customer_id"),
            "kpr_stage": "berkas_lengkap",
            "stage_history": [{"from": None, "to": "berkas_lengkap", "at": ts, "actor": actor,
                               "reason": "Pengajuan dibuat dari menu pembiayaan"}]}


async def sync_plafon(org: str, deal_id: str, old, new) -> None:
    """Plafon di komponen biaya kontrak → pengajuan KPR, selama belum disetujui bank dan belum
    disunting terpisah (plafon pengajuan masih kosong atau sama dengan nilai lama kontrak)."""
    if new is None:
        return
    app = await active_app(org, deal_id)
    if not app or int(app.get("approved_plafon") or 0) > 0:
        return
    if int(app.get("plafon") or 0) not in (0, int(old or 0)):
        return
    await db.financing_apps.update_one({"id": app["id"]}, {"$set": {
        "plafon": int(new), "requested_plafon": int(new), "updated_at": now_iso()}})
