"""FASE R0 — Profil gudang: site (lokasi), peran gedung, rules penyimpanan, gate config.

`warehouses` = GEDUNG (koleksi existing, SSOT stok tidak berubah).
`warehouse_sites` = lokasi fisik (Rancamalang, Soreang, Jakarta) — koleksi kecil SHARED.
Semua configurable oleh user (keputusan pemilik: fungsionalitas gudang bisa berubah).
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, safe_doc

VALID_ROLES = {"transit", "storage", "return", "staging", "central_inbound"}
VALID_RULE_MODES = {"none", "category", "grade"}
ROLE_LABEL = {
    "transit": "Transit", "storage": "Penyimpanan", "return": "Retur",
    "staging": "Staging", "central_inbound": "Penerimaan Pusat",
}


def validate_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validasi + normalisasi field profil (roles, storage_rules, gate_config, site_id)."""
    out: Dict[str, Any] = {}
    if "roles" in data:
        roles = [str(r).strip().lower() for r in (data.get("roles") or [])]
        bad = [r for r in roles if r not in VALID_ROLES]
        if bad:
            raise HTTPException(status_code=400, detail=f"Peran gudang tidak valid: {', '.join(bad)}")
        out["roles"] = sorted(set(roles))
    if "storage_rules" in data:
        rules = data.get("storage_rules") or {}
        mode = str(rules.get("mode") or "none").strip().lower()
        if mode not in VALID_RULE_MODES:
            raise HTTPException(status_code=400, detail=f"Mode rules tidak valid: {mode}")
        out["storage_rules"] = {
            "mode": mode,
            "categories": [str(c).strip() for c in (rules.get("categories") or []) if str(c).strip()],
            "grades": [str(g).strip().upper() for g in (rules.get("grades") or []) if str(g).strip()],
        }
    if "gate_config" in data:
        gc = data.get("gate_config") or {}
        out["gate_config"] = {"physical_gate": bool(gc.get("physical_gate", False))}
    if "site_id" in data:
        out["site_id"] = data.get("site_id") or ""
    return out


async def assert_site_exists(site_id: str) -> None:
    if site_id and not await db.warehouse_sites.find_one({"id": site_id}):
        raise HTTPException(status_code=400, detail="Lokasi (site) tidak ditemukan")


def check_storage_rules(warehouse: Dict[str, Any], category: str, grade: str) -> Dict[str, Any]:
    """Apakah roll (kategori, grade) boleh disimpan di gedung ini? → {ok, reason}."""
    rules = warehouse.get("storage_rules") or {}
    mode = rules.get("mode") or "none"
    if mode == "category":
        allowed = rules.get("categories") or []
        if allowed and category not in allowed:
            return {"ok": False, "reason": (
                f"Kategori '{category or '—'}' tidak diizinkan di {warehouse.get('name', '')} "
                f"(hanya: {', '.join(allowed)}).")}
    elif mode == "grade":
        allowed = rules.get("grades") or []
        if allowed and (grade or "").upper() not in allowed:
            return {"ok": False, "reason": (
                f"Grade '{grade or '—'}' tidak diizinkan di {warehouse.get('name', '')} "
                f"(hanya grade: {', '.join(allowed)}).")}
    return {"ok": True, "reason": ""}


# ─── Sites ───────────────────────────────────────────────────────────────────
async def list_sites() -> List[Dict[str, Any]]:
    sites = await db.warehouse_sites.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    counts: Dict[str, int] = {}
    async for w in db.warehouses.find({"site_id": {"$nin": [None, ""]}}, {"_id": 0, "site_id": 1}):
        counts[w["site_id"]] = counts.get(w["site_id"], 0) + 1
    for s in sites:
        s["warehouse_count"] = counts.get(s["id"], 0)
    return [safe_doc(s) for s in sites]


async def create_site(name: str, city: str, actor_name: str, location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nama lokasi wajib diisi")
    if await db.warehouse_sites.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}):
        raise HTTPException(status_code=409, detail="Nama lokasi sudah ada")
    site = {"id": new_id("site"), "name": name, "city": (city or "").strip(), **(location or {}),
            "created_at": now_iso(), "created_by": actor_name}
    await db.warehouse_sites.insert_one(dict(site))
    return safe_doc(site)


async def update_site(site_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    _keys = {"name", "city", "country", "country_code", "province", "province_code", "city_code", "district", "district_code", "postal_code", "location_status"}
    data = {k: str(v).strip() for k, v in patch.items() if k in _keys and v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan")
    data["updated_at"] = now_iso()
    await db.warehouse_sites.update_one({"id": site_id}, {"$set": data})
    site = await db.warehouse_sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
    return safe_doc(site)


async def delete_site(site_id: str) -> Dict[str, Any]:
    used = await db.warehouses.count_documents({"site_id": site_id})
    if used:
        raise HTTPException(status_code=409,
                            detail=f"Lokasi masih dipakai {used} gedung — lepaskan dulu dari gedungnya.")
    res = await db.warehouse_sites.delete_one({"id": site_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
    return {"ok": True}


# ─── Seed blueprint (idempotent) — peta gudang nyata user ────────────────────
BLUEPRINT_SITES = [
    {"key": "rancamalang", "name": "Rancamalang", "city": "Bandung"},
    {"key": "soreang", "name": "Soreang", "city": "Bandung"},
    {"key": "jakarta", "name": "Jakarta", "city": "Jakarta"},
]
BLUEPRINT_WH = [
    {"site": "rancamalang", "code": "RCM-TRANSIT", "name": "Gedung Transit (Central)",
     "roles": ["transit", "central_inbound", "staging"], "gate": False,
     "rules": {"mode": "none", "categories": [], "grades": []}},
    {"site": "rancamalang", "code": "RCM-WOVEN", "name": "Gedung Woven",
     "roles": ["storage"], "gate": True, "rules": {"mode": "category", "categories": [], "grades": []}},
    {"site": "rancamalang", "code": "RCM-KNITTING", "name": "Gedung Knitting",
     "roles": ["storage"], "gate": True, "rules": {"mode": "category", "categories": [], "grades": []}},
    {"site": "rancamalang", "code": "RCM-PRINTING", "name": "Gedung Printing",
     "roles": ["storage"], "gate": True, "rules": {"mode": "category", "categories": [], "grades": []}},
    {"site": "rancamalang", "code": "RCM-RETUR", "name": "Gedung Retur",
     "roles": ["return", "storage"], "gate": True,
     "rules": {"mode": "grade", "categories": [], "grades": ["B", "C", "BS"]}},
    {"site": "soreang", "code": "SRG-01", "name": "Gedung Soreang",
     "roles": ["storage"], "gate": True, "rules": {"mode": "none", "categories": [], "grades": []}},
]


async def seed_blueprint(actor_name: str) -> Dict[str, Any]:
    """Buat 3 site + gedung sesuai peta user. Idempotent; gudang existing tidak diubah
    kecuali wh_jakarta yang dipetakan ke site Jakarta (handheld-only)."""
    site_ids: Dict[str, str] = {}
    created_sites = 0
    for s in BLUEPRINT_SITES:
        cur = await db.warehouse_sites.find_one({"name": s["name"]}, {"_id": 0})
        if cur:
            site_ids[s["key"]] = cur["id"]
            continue
        doc = {"id": new_id("site"), "name": s["name"], "city": s["city"],
               "created_at": now_iso(), "created_by": actor_name}
        await db.warehouse_sites.insert_one(doc)
        site_ids[s["key"]] = doc["id"]
        created_sites += 1

    created_wh = 0
    for spec in BLUEPRINT_WH:
        if await db.warehouses.find_one({"code": spec["code"]}):
            continue
        wid = new_id("wh")
        await db.warehouses.insert_one({
            "id": wid, "code": spec["code"], "name": spec["name"],
            "city": next(s["city"] for s in BLUEPRINT_SITES if s["key"] == spec["site"]),
            "site_id": site_ids[spec["site"]],
            "roles": spec["roles"], "storage_rules": spec["rules"],
            "gate_config": {"physical_gate": spec["gate"]},
            "sharing_mode": "shared", "entity_ids": [],
            "zones": [{"id": new_id("zone"), "name": "Zone A", "racks": [
                {"id": new_id("rack"), "name": "Rack A1",
                 "bins": [{"id": new_id("bin"), "code": "A1-01", "capacity": 5000.0}]}]}],
            "active": True, "created_at": now_iso(),
        })
        created_wh += 1

    # Gudang Jakarta existing → site Jakarta, storage, handheld-only (tanpa gate fisik)
    jkt = await db.warehouses.find_one({"id": "wh_jakarta"}, {"_id": 0})
    if jkt and not jkt.get("site_id"):
        await db.warehouses.update_one({"id": "wh_jakarta"}, {"$set": {
            "site_id": site_ids["jakarta"], "roles": ["storage"],
            "storage_rules": jkt.get("storage_rules") or {"mode": "none", "categories": [], "grades": []},
            "gate_config": {"physical_gate": False}, "updated_at": now_iso()}})

    return {"created_sites": created_sites, "created_warehouses": created_wh,
            "sites": await list_sites()}
