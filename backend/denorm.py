"""Sinkronisasi field denormalisasi (SSOT guard).

Masalah yang diperbaiki (audit forensik): 48 pasangan field kopi
(project_name, unit_code, lead_name, subcontractor_name, spk_number, po_number,
phase_name, scheme_name, customer_name) disimpan ulang di koleksi anak TANPA mekanisme
sinkronisasi. Akibatnya:
- Data sudah basi sekarang: commissions.unit_code = 'A-02'/'A-03' padahal unit_id -> 'A-01'.
- Rename master (mis. nama subkontraktor via PUT) membuat semua dokumen anak salah nama.

DIPAKAI DI DUA TITIK:
1. cascade_master_change(...) dipanggil setiap master di-update/rename.
2. resync_all() dijalankan saat startup (migrasi idempoten) + bisa dipanggil manual.
"""
import logging

from db import db

logger = logging.getLogger("sipro.denorm")

# master -> [(koleksi anak, field FK, field kopi di anak, field sumber di master)]
DENORM_MAP: dict = {
    "projects": [
        ("boq_items", "project_id", "project_name", "name"),
        ("permits", "project_id", "project_name", "name"),
        ("punch_items", "project_id", "project_name", "name"),
        ("site_diaries", "project_id", "project_name", "name"),
        ("spk", "project_id", "project_name", "name"),
        ("progress_claims", "project_id", "project_name", "name"),
        ("change_orders", "project_id", "project_name", "name"),
        ("purchase_orders", "project_id", "project_name", "name"),
        ("material_requisitions", "project_id", "project_name", "name"),
        ("inspections", "project_id", "project_name", "name"),
        ("materials", "project_id", "project_name", "name"),
    ],
    "units": [
        ("deals", "unit_id", "unit_code", "code"),
        ("ar_invoices", "unit_id", "unit_code", "code"),
        ("commissions", "unit_id", "unit_code", "code"),
        ("complaints", "unit_id", "unit_code", "code"),
    ],
    "leads": [
        ("ar_invoices", "lead_id", "lead_name", "name"),
        ("appointments", "lead_id", "lead_name", "name"),
        ("surveys", "lead_id", "lead_name", "name"),
        # KT-15: salinan nama lead yang dulu tidak ikut tersinkron saat kontak diedit setelah konversi.
        ("deals", "lead_id", "lead_name", "name"),
        ("units", "lead_id", "lead_name", "name"),
        ("booking_fee_invoices", "lead_id", "lead_name", "name"),
    ],
    "subcontractors": [
        ("spk", "subcontractor_id", "subcontractor_name", "name"),
        ("progress_claims", "subcontractor_id", "subcontractor_name", "name"),
        ("change_orders", "subcontractor_id", "subcontractor_name", "name"),
        ("purchase_orders", "subcontractor_id", "subcontractor_name", "name"),
    ],
    "spk": [
        ("progress_claims", "spk_id", "spk_number", "spk_number"),
        ("change_orders", "spk_id", "spk_number", "spk_number"),
    ],
    "purchase_orders": [
        ("grns", "po_id", "po_number", "po_number"),
    ],
    "construction_phases": [
        ("material_requisitions", "phase_id", "phase_name", "name"),
    ],
    "commission_schemes": [
        ("commissions", "scheme_id", "scheme_name", "name"),
    ],
    "payment_schemes": [
        ("ar_invoices", "scheme_id", "scheme_name", "name"),
    ],
    "customers": [
        ("complaints", "customer_id", "customer_name", "name"),
        ("financing_apps", "customer_id", "customer_name", "name"),
        # KT-15: nama pembeli di kontrak/deal ikut berubah (dulu GET /contracts?q=<nama baru> = 0 hasil).
        ("contracts", "customer_id", "customer_name", "name"),
        ("deals", "customer_id", "customer_name", "name"),
    ],
}


def _merge_extra() -> None:
    """Gabungkan `denorm_map_extra.EXTRA_PAIRS` (PL-04) ke DENORM_MAP tanpa menggandakan pasangan."""
    from denorm_map_extra import EXTRA_PAIRS
    for master, pairs in EXTRA_PAIRS.items():
        cur = DENORM_MAP.setdefault(master, [])
        have = {(c, fk, cf) for c, fk, cf, _ in cur}
        cur.extend(p for p in pairs if (p[0], p[1], p[2]) not in have)


_merge_extra()

# ---- Sinkronisasi otomatis (PL-04) ---------------------------------------------------------------------
# Dulu `cascade_master_change` hanya dipanggil dari 6 router; mengganti nama rekening, vendor, mitra, pekerja, dst.
# membuat 31+ dokumen tetap bernama lama. Sekarang: (a) setiap PUT/PATCH yang berhasil menandai "kotor" (middleware di
# server.py), (b) penjadwal menjalankan `sync_if_dirty` tiap beberapa detik dan `resync_stale` penuh tiap jam. Menyapu
# SEMUA pasangan sekaligus berarti jalur rename baru di masa depan otomatis tercakup tanpa harus mengingat memanggil cascade.
import time as _time

_dirty = False
_last_run = 0.0
MIN_INTERVAL_S = 10.0


def mark_dirty() -> None:
    global _dirty
    _dirty = True


async def sync_if_dirty() -> dict:
    """Dijalankan penjadwal: sapu hanya bila ada perubahan sejak sapuan terakhir (dan tidak lebih sering dari MIN_INTERVAL_S)."""
    global _dirty, _last_run
    if not _dirty or _time.monotonic() - _last_run < MIN_INTERVAL_S:
        return {}
    _dirty = False
    _last_run = _time.monotonic()
    try:
        return await resync_stale()
    except Exception:  # noqa: BLE001 — sapuan gagal jangan mematikan penjadwal; tandai kotor lagi agar dicoba ulang
        logger.exception("denorm: sapuan otomatis gagal")
        _dirty = True
        return {}


async def resync_stale(batch: int = 1000) -> dict:
    """Samakan SEMUA salinan yang basi dengan satu agregasi per pasangan ($lookup), bukan satu `update_many` per master.

    Biaya ~ jumlah dokumen anak (bukan master × pasangan); idempoten; hanya menulis dokumen yang memang berbeda."""
    from pymongo import UpdateOne
    fixed = {}
    existing = set(await db.list_collection_names())
    for master, pairs in DENORM_MAP.items():
        if master not in existing:
            continue
        for child, fk, copy_field, src_field in pairs:
            if child not in existing:
                continue
            want = {"$arrayElemAt": [f"$_m.{src_field}", 0]}
            pipe = [
                {"$match": {fk: {"$type": "string"}}},
                {"$lookup": {"from": master, "localField": fk, "foreignField": "id", "as": "_m"}},
                {"$match": {"$expr": {"$and": [{"$gt": [{"$size": "$_m"}, 0]},
                                               {"$eq": [{"$type": want}, "string"]},
                                               {"$ne": [f"${copy_field}", want]}]}}},
                {"$project": {"_id": 1, "want": want}},
            ]
            ops, n = [], 0
            async for r in db[child].aggregate(pipe):
                ops.append(UpdateOne({"_id": r["_id"]}, {"$set": {copy_field: r["want"]}}))
                if len(ops) >= batch:
                    n += (await db[child].bulk_write(ops, ordered=False)).modified_count
                    ops = []
            if ops:
                n += (await db[child].bulk_write(ops, ordered=False)).modified_count
            if n:
                fixed[f"{child}.{copy_field}<-{master}.{src_field}"] = n
    if fixed:
        logger.info("denorm resync_stale: %s", fixed)
    return fixed


def register(scheduler) -> None:
    """Pola `scheduler_*.register`: sapuan bila kotor (tiap 10 dtk) + sapuan penuh tiap jam sebagai jaring pengaman."""
    scheduler.add_job(sync_if_dirty, "interval", seconds=10, id="denorm_sync_if_dirty",
                      max_instances=1, coalesce=True)
    scheduler.add_job(resync_stale, "interval", seconds=3600, id="denorm_resync_hourly",
                      max_instances=1, coalesce=True)


async def cascade_master_change(master: str, master_id: str, master_doc: dict) -> int:
    """Setelah master di-update, samakan semua field kopi di koleksi anak."""
    total = 0
    for child, fk, copy_field, src_field in DENORM_MAP.get(master, []):
        if src_field not in master_doc:
            continue
        res = await db[child].update_many(
            {fk: master_id, copy_field: {"$ne": master_doc[src_field]}},
            {"$set": {copy_field: master_doc[src_field]}},
        )
        total += res.modified_count
    if total:
        logger.info("denorm cascade %s/%s -> %s dokumen anak disamakan", master, master_id, total)
    return total


async def resync_all(limit_per_master: int = 5000) -> dict:
    """Perbaiki SEMUA field kopi yang basi. Idempoten; kembalikan jumlah per pasangan."""
    fixed = {}
    existing = set(await db.list_collection_names())
    for master, pairs in DENORM_MAP.items():
        if master not in existing:
            continue
        src_fields = sorted({p[3] for p in pairs})
        proj = {"_id": 0, "id": 1}
        for f in src_fields:
            proj[f] = 1
        masters = await db[master].find({}, proj).to_list(limit_per_master)
        mmap = {m["id"]: m for m in masters if m.get("id")}
        for child, fk, copy_field, src_field in pairs:
            if child not in existing:
                continue
            n = 0
            for mid, mdoc in mmap.items():
                want = mdoc.get(src_field)
                if want is None:
                    continue
                res = await db[child].update_many(
                    {fk: mid, copy_field: {"$ne": want}}, {"$set": {copy_field: want}})
                n += res.modified_count
            if n:
                fixed[f"{child}.{copy_field}<-{master}.{src_field}"] = n
    return fixed


async def audit_stale(limit_per_master: int = 5000) -> list:
    """Laporan (read-only) semua field kopi yang tidak sama dengan master."""
    out = []
    existing = set(await db.list_collection_names())
    for master, pairs in DENORM_MAP.items():
        if master not in existing:
            continue
        for child, fk, copy_field, src_field in pairs:
            if child not in existing:
                continue
            masters = await db[master].find({}, {"_id": 0, "id": 1, src_field: 1}).to_list(limit_per_master)
            mmap = {m["id"]: m.get(src_field) for m in masters if m.get("id")}
            rows = await db[child].find({fk: {"$ne": None}},
                                        {"_id": 0, "id": 1, fk: 1, copy_field: 1}).to_list(limit_per_master)
            for r in rows:
                want = mmap.get(r.get(fk))
                if want is not None and r.get(copy_field) != want:
                    out.append({"collection": child, "id": r.get("id"), "field": copy_field,
                                "stored": r.get(copy_field), "master": want})
    return out
