"""Batas wajar NOMINAL satu komponen biaya — pengaturan `cost.component_max_amount` (W2-C).

Dulu pagar Rp 1 triliun dikunci di `cost_master_rules.MAX_NOMINAL`. Pemilik menyetujui: batas menjadi PENGATURAN di Pusat
Konfigurasi (bawaan Rp 10.000.000.000 per komponen; tingkat organisasi + proyek, sensitif). Satu pembaca untuk SEMUA jalur
yang menerima nominal komponen:

  * master komponen All-in (`POST/PUT /cost-components`)            → batas tingkat organisasi
  * butir skema All-in (`override_amount`)                           → batas TERKETAT dari proyek-proyek skema itu
    (skema tanpa proyek berlaku untuk semua proyek → batas organisasi)
  * komponen manual reservasi / amandemen (`manual_components`)      → batas proyek deal
  * isian bebas biaya kontrak (`POST /contracts/{id}/costs`)         → batas proyek kontrak
  * beban developer (`cost-expenses`)                                → batas proyek kontrak
  * nilai bawaan katalog (`/catalog/price-components`)               → batas tingkat organisasi

Aturan nilai yang SUDAH tersimpan di atas batas baru: tidak diubah (tidak ada migrasi diam-diam), tetapi tidak bisa
DIEDIT NAIK — penyuntingan hanya boleh bila nilai baru ≤ batas ATAU ≤ nilai tersimpan (menurunkan selalu boleh).
Batas teknis lain (tahap pencairan KPR, NPOPTKP) tetap `cost_master_rules.MAX_NOMINAL` karena bukan nominal komponen.
"""
import policy
from db import db

KEY = "cost.component_max_amount"


def fmt(v) -> str:
    return f"Rp {int(v):,}".replace(",", ".")


async def max_amount(org: str, project_id: str = None) -> int:
    """Batas efektif: proyek → organisasi → bawaan kode."""
    return int(await policy.resolve(KEY, org_id=org, project_id=project_id))


async def limit_for_projects(org: str, project_ids) -> int:
    """Batas TERKETAT dari daftar proyek; daftar kosong = berlaku untuk semua proyek → batas organisasi."""
    ids = [p for p in (project_ids or []) if p]
    if not ids:
        return await max_amount(org)
    return min([await max_amount(org, p) for p in ids])


async def project_of_deal(org: str, deal_id: str = None) -> str:
    if not deal_id:
        return None
    d = await db.deals.find_one({"org_id": org, "id": deal_id}, {"_id": 0, "project_id": 1})
    return (d or {}).get("project_id")


async def project_of_contract(org: str, contract: dict) -> str:
    """Proyek sebuah kontrak = proyek deal-nya (kontrak tidak menyimpan proyek sendiri)."""
    return await project_of_deal(org, (contract or {}).get("deal_id"))


def check(value, limit: int, label: str, stored=None) -> None:
    """Tolak nominal di atas `limit` (ValueError → HTTP 400). `stored` = nilai yang sudah tersimpan: nilai yang sudah di
    atas batas boleh DITURUNKAN (atau dibiarkan) tetapi tidak boleh dinaikkan."""
    if value is None:
        return
    v = int(value)
    if v <= int(limit):
        return
    if stored is not None and v <= int(stored):
        return
    extra = (f" Nilai yang tersimpan {fmt(stored)} sudah di atas batas — boleh diturunkan, tidak boleh dinaikkan."
             if stored is not None and int(stored) > int(limit) else "")
    raise ValueError(f"{label} {fmt(v)} melebihi batas nominal per komponen {fmt(limit)} — angka tidak wajar, periksa "
                     "kembali. Batas bisa diubah di Pusat Konfigurasi › Aturan Bisnis (kunci cost.component_max_amount)."
                     + extra)
