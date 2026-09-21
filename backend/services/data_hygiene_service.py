"""Kebersihan Data (K-1/K-2 otomatis) — normalisasi EYD nama & nomor telepon pada data LAMA.

Berjalan otomatis saat boot (idempoten) dan bisa dijalankan ulang dari layar Kebersihan Data.
Setiap perubahan dicatat per-record di `data_hygiene_log` (sebelum/sesudah) dan bisa
dikembalikan; record yang dikembalikan diberi `hygiene_locked=True` agar tidak disentuh lagi.
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso
from services.text_normalize import nama_orang, nama_usaha, phone_id

# koleksi → {field: jenis}. Jenis: usaha | orang | phone. Kunci bertitik = field di dalam array.
RULES: Dict[str, Dict[str, str]] = {
    "customers": {"name": "usaha", "pic_name": "orang", "phone": "phone",
                  "addresses.recipient_name": "orang", "addresses.phone": "phone",
                  "contacts.name": "orang", "contacts.phone": "phone"},
    "suppliers": {"name": "usaha", "pic_name": "orang", "phone": "phone"},
    "users":     {"name": "orang", "phone": "phone"},
    "hr_employees": {"name": "orang", "full_name": "orang", "phone": "phone"},
    "makloons":  {"name": "usaha", "pic_name": "orang", "phone": "phone"},
}
LABEL = {"customers": "Pelanggan", "suppliers": "Pemasok", "users": "Pengguna", "hr_employees": "Karyawan", "makloons": "Mitra makloon"}


def _norm(kind: str, value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    if kind == "usaha":
        return nama_usaha(value)
    if kind == "orang":
        return nama_orang(value)
    try:
        return phone_id(value)
    except ValueError:
        return value          # nomor lama yang tidak bisa dibaca dibiarkan (dilaporkan sebagai 'skipped')


def compute_changes(coll: str, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Daftar {field, before, after}. Untuk array, 1 entri per field array (before/after = seluruh array)."""
    changes: List[Dict[str, Any]] = []
    array_subs: Dict[str, Dict[str, str]] = {}
    for path, kind in RULES[coll].items():
        if "." in path:
            arr_key, sub = path.split(".", 1)
            array_subs.setdefault(arr_key, {})[sub] = kind
            continue
        before = doc.get(path)
        after = _norm(kind, before)
        if after != before:
            changes.append({"field": path, "before": before, "after": after})
    for arr_key, subs in array_subs.items():
        arr = doc.get(arr_key)
        if not isinstance(arr, list):
            continue
        new_arr = [{**it, **{s: _norm(k, it.get(s)) for s, k in subs.items()}} if isinstance(it, dict) else it for it in arr]
        if new_arr != arr:
            changes.append({"field": arr_key, "before": arr, "after": new_arr})
    return changes


def _label_of(doc: Dict[str, Any]) -> str:
    return str(doc.get("name") or doc.get("full_name") or doc.get("email") or doc.get("id") or "")


async def run(trigger: str = "boot", actor: str = "sistem", collections: Optional[List[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"trigger": trigger, "changed": 0, "scanned": 0, "per_collection": {}}
    for coll in (collections or list(RULES)):
        if coll not in RULES:
            continue
        n_changed = 0
        async for doc in db[coll].find({"hygiene_locked": {"$ne": True}}, {"_id": 0}):
            out["scanned"] += 1
            changes = compute_changes(coll, doc)
            if not changes:
                continue
            await db[coll].update_one({"id": doc["id"]}, {"$set": {**{c["field"]: c["after"] for c in changes},
                                                                   "hygiene_applied_at": now_iso()}})
            await db.data_hygiene_log.insert_one({
                "id": new_id("hyg"), "collection": coll, "doc_id": doc["id"], "doc_label": _label_of(doc),
                "entity_id": doc.get("entity_id"), "changes": changes, "trigger": trigger, "actor": actor,
                "applied_at": now_iso(), "reverted": False})
            n_changed += 1
        out["per_collection"][coll] = n_changed
        out["changed"] += n_changed
    if out["changed"]:
        await db.data_hygiene_runs.insert_one({"id": new_id("hygrun"), **out, "at": now_iso()})
    return out


async def revert(log_id: str, actor: str) -> Dict[str, Any]:
    entry = await db.data_hygiene_log.find_one({"id": log_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Catatan kebersihan data tidak ditemukan.")
    if entry.get("reverted"):
        raise HTTPException(status_code=409, detail="Catatan ini sudah dikembalikan.")
    coll = entry["collection"]
    res = await db[coll].update_one(
        {"id": entry["doc_id"]},
        {"$set": {**{c["field"]: c["before"] for c in entry["changes"]}, "hygiene_locked": True,
                  "hygiene_reverted_at": now_iso()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Dokumen asal sudah tidak ada.")
    await db.data_hygiene_log.update_one({"id": log_id}, {"$set": {"reverted": True, "reverted_at": now_iso(), "reverted_by": actor}})
    return {**entry, "reverted": True, "reverted_at": now_iso(), "reverted_by": actor}


async def unlock(coll: str, doc_id: str) -> Dict[str, Any]:
    if coll not in RULES:
        raise HTTPException(status_code=404, detail="Koleksi tidak dikenal.")
    await db[coll].update_one({"id": doc_id}, {"$unset": {"hygiene_locked": ""}})
    return {"collection": coll, "doc_id": doc_id, "locked": False}


async def summary() -> Dict[str, Any]:
    total = await db.data_hygiene_log.count_documents({})
    reverted = await db.data_hygiene_log.count_documents({"reverted": True})
    locked = {c: await db[c].count_documents({"hygiene_locked": True}) for c in RULES}
    last = await db.data_hygiene_runs.find_one({}, {"_id": 0}, sort=[("at", -1)])
    per = {}
    async for row in db.data_hygiene_log.aggregate([{"$group": {"_id": "$collection", "n": {"$sum": 1}}}]):
        per[row["_id"]] = row["n"]
    return {"total": total, "reverted": reverted, "active": total - reverted, "locked": locked,
            "per_collection": per, "last_run": last, "labels": LABEL, "rules": RULES}


async def preview(collections: Optional[List[str]] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Apa yang AKAN diubah bila dijalankan sekarang (tanpa menulis)."""
    rows: List[Dict[str, Any]] = []
    for coll in (collections or list(RULES)):
        if coll not in RULES:
            continue
        async for doc in db[coll].find({"hygiene_locked": {"$ne": True}}, {"_id": 0}):
            ch = compute_changes(coll, doc)
            if ch:
                rows.append({"collection": coll, "doc_id": doc["id"], "doc_label": _label_of(doc), "changes": ch})
                if len(rows) >= limit:
                    return rows
    return rows


# ── Alamat belum terverifikasi (2026-09) ─────────────────────────────────────
LOCATION_COLLECTIONS = {
    "customers": "Pelanggan", "suppliers": "Pemasok", "makloons": "Mitra makloon",
    "warehouses": "Gudang", "warehouse_sites": "Lokasi gudang", "business_entities": "Badan usaha", "hr_employees": "Karyawan",
}


def _loc_status(doc: Dict[str, Any]) -> str:
    """Status lokasi: pakai yang tersimpan; data lama tanpa status dinilai leniently (tanpa menulis)."""
    from services.wilayah_service import normalize_location
    st = doc.get("location_status")
    if st == "foreign" or (st == "verified" and doc.get("postal_code")):
        return st
    try:
        return normalize_location({k: doc.get(k, "") for k in ("country", "country_code", "province", "province_code", "city",
                                                                "city_code", "district", "district_code", "postal_code")}).get("location_status", "unverified")
    except Exception:  # noqa: BLE001 — nilai lama yang tidak konsisten
        return "unverified"


async def unverified_locations(collection: Optional[str] = None, limit: int = 300) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for coll, label in LOCATION_COLLECTIONS.items():
        if collection and coll != collection:
            continue
        n = 0
        async for doc in db[coll].find({"location_status": {"$nin": ["verified", "foreign"]}}, {"_id": 0}):
            st = _loc_status(doc)
            if st in ("verified", "foreign"):
                continue
            n += 1
            if len(rows) < limit:
                rows.append({"collection": coll, "label": label, "doc_id": doc["id"],
                             "doc_label": doc.get("name") or doc.get("legal_name") or doc.get("full_name") or doc["id"],
                             "entity_id": doc.get("entity_id"), "status": st, "address": doc.get("address", ""),
                             **{k: doc.get(k, "") for k in ("country", "country_code", "province", "province_code", "city",
                                                            "city_code", "district", "district_code", "postal_code")}})
        counts[coll] = n
    return {"items": rows, "counts": counts, "total": sum(counts.values()), "labels": LOCATION_COLLECTIONS}


async def fix_location(collection: str, doc_id: str, data: Dict[str, Any], actor: str) -> Dict[str, Any]:
    """Lengkapi lokasi satu record dari layar Kebersihan Data (wajib lengkap & konsisten)."""
    from services.wilayah_service import normalize_location
    if collection not in LOCATION_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Koleksi tidak dikenal.")
    doc = await db[collection].find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    loc = normalize_location(data, require=True)
    await db[collection].update_one({"id": doc_id}, {"$set": {**loc, "updated_at": now_iso()}})
    if collection == "customers" and isinstance(doc.get("addresses"), list) and data.get("apply_to_primary", True):
        addrs = [{**a, **loc} if a.get("is_primary") and (not a.get("postal_code") or _loc_status(a) not in ("verified", "foreign")) else a
                 for a in doc["addresses"]]
        await db.customers.update_one({"id": doc_id}, {"$set": {"addresses": addrs}})
    await db.data_hygiene_log.insert_one({
        "id": new_id("hyg"), "collection": collection, "doc_id": doc_id, "doc_label": doc.get("name") or doc.get("legal_name") or doc_id,
        "entity_id": doc.get("entity_id"), "trigger": "location_fix", "actor": actor, "applied_at": now_iso(), "reverted": False,
        "changes": [{"field": k, "before": doc.get(k, ""), "after": v} for k, v in loc.items() if doc.get(k, "") != v]})
    return {"collection": collection, "doc_id": doc_id, **loc}
