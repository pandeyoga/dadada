"""PERAN KUSTOM & TINGKAT AKSES — aturan bisnis untuk layar "Peran & Hak Akses".

Sumber kebenaran izin tetap `permission_settings.matrix` (dibaca `dependencies.permission_matrix`).
Berkas ini menerjemahkan 3 tingkat per modul (none/view/manage) ke matriks aksi, dan menjaga
registry peran (`role_registry.ROLES`) tetap memuat peran kustom yang tersimpan di basis data.
"""
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from access_modules import LEVELS, apply_levels, clean_permissions, levels_of, nav_allowed_for_perms, nav_for_levels
from core_utils import now_iso
from db import db
from permissions_config import DEFAULT_PERMISSIONS
import role_registry as reg

LOCKED_ROLES = {"admin"}


async def list_custom() -> List[Dict[str, Any]]:
    return await db.custom_roles.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)


async def sync_registry() -> None:
    reg.register_custom_roles(await list_custom())


async def _matrix() -> Dict[str, Dict[str, List[str]]]:
    record = await db.permission_settings.find_one({"id": "default"}, {"_id": 0})
    return deepcopy(record.get("matrix") if record and record.get("matrix") else DEFAULT_PERMISSIONS)


async def _save_matrix(matrix: Dict[str, Any]) -> None:
    await db.permission_settings.update_one(
        {"id": "default"}, {"$set": {"matrix": matrix, "updated_at": now_iso()}}, upsert=True)


async def _users_by_role() -> Dict[str, int]:
    rows = await db.users.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$role", "n": {"$sum": 1}}},
    ]).to_list(200)
    return {r["_id"]: r["n"] for r in rows if r.get("_id")}


def _clean_levels(levels: Optional[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (levels or {}).items():
        lvl = v.get("level") if isinstance(v, dict) else v
        if lvl not in LEVELS:
            raise HTTPException(status_code=400,
                                detail=f"Tingkat akses “{lvl}” untuk modul “{k}” tidak dikenal "
                                       f"(pilihan: Tidak ada · Lihat saja · Kelola penuh).")
        out[k] = lvl
    return out


def _clean_perms(perms: Any) -> Dict[str, List[str]]:
    try:
        return clean_permissions(perms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _clean_perms(perms: Any) -> Dict[str, List[str]]:
    try:
        return clean_permissions(perms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _clean_label(label: str) -> str:
    clean = re.sub(r"\s+", " ", (label or "").strip())
    if len(clean) < 2 or len(clean) > 40:
        raise HTTPException(status_code=400, detail="Nama peran wajib 2–40 karakter.")
    return clean


async def _assert_label_unique(label: str, exclude_id: str = "") -> None:
    low = label.lower()
    for rid, r in reg.ROLES.items():
        if rid != exclude_id and (r["label"].lower() == low or r["long_label"].lower() == low):
            raise HTTPException(status_code=409,
                                detail=f"Nama peran “{label}” sudah dipakai. Pilih nama lain.")


def _role_view(rid: str, matrix: Dict[str, Any], users: Dict[str, int],
               custom_docs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    entry = reg.ROLES.get(rid) or {}
    perms = matrix.get(rid, {}) or {}
    custom = rid in custom_docs
    doc = custom_docs.get(rid, {})
    default = DEFAULT_PERMISSIONS.get(rid)
    return {
        "id": rid,
        "label": entry.get("label", rid),
        "long_label": entry.get("long_label", rid),
        "description": doc.get("description") if custom else entry.get("description", ""),
        "custom": custom,
        "base_role": doc.get("base_role", "") if custom else "",
        "base_role_label": reg.role_label(doc.get("base_role", "")) if custom and doc.get("base_role") else "",
        "rank": entry.get("rank", 0),
        "cross_entity": entry.get("cross_entity", False),
        "home_view": entry.get("home_view", ""),
        "users": users.get(rid, 0),
        "locked": rid in LOCKED_ROLES,
        "deletable": custom and users.get(rid, 0) == 0,
        "modified": (not custom) and default is not None and perms != default,
        "levels": levels_of(perms),
        "permissions": perms,
        "turn_alerts": _turn_alerts(perms),
        "updated_at": doc.get("updated_at", ""),
    }


def _turn_alerts(perms: Dict[str, List[str]]) -> List[str]:
    """Judul notifikasi "giliran" yang akan diterima pemegang izin ini (untuk pratinjau)."""
    from services.turn_notification_service import TURN_MAP
    out: List[str] = []
    for rules in TURN_MAP.values():
        for rule in rules.values():
            perm = rule.get("permission")
            if perm and perm[1] in (perms.get(perm[0]) or []):
                out.append(rule["title"])
    return out


async def all_roles() -> List[Dict[str, Any]]:
    await sync_registry()
    matrix, users, customs = await _matrix(), await _users_by_role(), await list_custom()
    cdocs = {c["id"]: c for c in customs}
    return [_role_view(rid, matrix, users, cdocs) for rid in reg.role_ids()]


async def get_role(rid: str) -> Dict[str, Any]:
    await sync_registry()
    if rid not in reg.ROLES:
        raise HTTPException(status_code=404, detail="Peran tidak ditemukan.")
    cdocs = {c["id"]: c for c in await list_custom()}
    out = _role_view(rid, await _matrix(), await _users_by_role(), cdocs)
    out["accounts"] = await _accounts_of_role(rid)
    return out


async def _accounts_of_role(rid: str) -> List[Dict[str, Any]]:
    rows = await db.users.find(
        {"role": rid}, {"_id": 0, "id": 1, "name": 1, "email": 1, "status": 1, "home_entity_id": 1},
    ).sort("name", 1).to_list(200)
    ents = {e["id"]: e for e in await db.business_entities.find(
        {}, {"_id": 0, "id": 1, "short_name": 1, "legal_name": 1}).to_list(200)}
    for r in rows:
        e = ents.get(r.get("home_entity_id") or "") or {}
        r["entity_name"] = e.get("short_name") or e.get("legal_name") or ""
    return rows


def _slug(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:24]
    return f"cr_{s or 'peran'}"


async def create_custom(payload: Dict[str, Any]) -> Dict[str, Any]:
    await sync_registry()
    label = _clean_label(payload.get("label", ""))
    await _assert_label_unique(label)
    base = (payload.get("base_role") or "").strip()
    if base and (base not in reg.ROLES):
        raise HTTPException(status_code=400, detail="Peran acuan (template) tidak dikenal.")
    if base in LOCKED_ROLES:
        raise HTTPException(status_code=400, detail="Peran Admin tidak bisa dijadikan template.")
    levels = _clean_levels(payload.get("levels"))
    rid = _slug(label)
    existing = {r["id"] for r in await list_custom()}
    n = 2
    while rid in existing or rid in reg.ROLES:
        rid = f"{_slug(label)}_{n}"
        n += 1
    matrix = await _matrix()
    perms = apply_levels(deepcopy(matrix.get(base, {})) if base else {}, levels)
    if payload.get("permissions") is not None:
        perms = _clean_perms(payload["permissions"])
    matrix[rid] = perms
    doc = {"id": rid, "label": label, "description": (payload.get("description") or "").strip()[:200],
           "base_role": base, "levels": {k: v["level"] for k, v in levels_of(perms).items()},
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.custom_roles.insert_one(dict(doc))
    await _save_matrix(matrix)
    await sync_registry()
    return await get_role(rid)


async def update_role(rid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    await sync_registry()
    if rid in LOCKED_ROLES:
        raise HTTPException(status_code=403,
                            detail="Peran Admin dikunci: hak aksesnya tidak bisa diubah supaya "
                                   "tidak ada yang terkunci keluar dari sistem.")
    if rid not in reg.ROLES:
        raise HTTPException(status_code=404, detail="Peran tidak ditemukan.")
    custom = bool(reg.ROLES[rid].get("custom"))
    matrix = await _matrix()
    changes: Dict[str, Any] = {}
    if "levels" in payload and payload["levels"] is not None:
        levels = _clean_levels(payload["levels"])
        current = matrix.get(rid)
        if current is None:
            current = DEFAULT_PERMISSIONS.get(rid, {})
        matrix[rid] = apply_levels(deepcopy(current), levels)
        changes["levels"] = levels
    if payload.get("permissions") is not None:
        before = matrix.get(rid) or DEFAULT_PERMISSIONS.get(rid, {})
        matrix[rid] = _clean_perms(payload["permissions"])
        changes["permissions"] = {
            r: sorted(matrix[rid].get(r, [])) for r in set(before) | set(matrix[rid])
            if sorted(before.get(r, [])) != sorted(matrix[rid].get(r, []))}
    if custom:
        patch: Dict[str, Any] = {"updated_at": now_iso()}
        if payload.get("label") is not None:
            label = _clean_label(payload["label"])
            await _assert_label_unique(label, exclude_id=rid)
            patch["label"] = label
            changes["label"] = label
        if payload.get("description") is not None:
            patch["description"] = str(payload["description"]).strip()[:200]
        patch["levels"] = {k: v["level"] for k, v in levels_of(matrix.get(rid, {})).items()}
        await db.custom_roles.update_one({"id": rid}, {"$set": patch})
    elif payload.get("label") is not None or payload.get("description") is not None:
        raise HTTPException(status_code=400,
                            detail="Nama & deskripsi peran bawaan sistem tidak bisa diubah; "
                                   "hanya hak aksesnya.")
    await _save_matrix(matrix)
    await sync_registry()
    out = await get_role(rid)
    out["changes"] = changes
    return out


async def reset_builtin(rid: str) -> Dict[str, Any]:
    await sync_registry()
    if rid in LOCKED_ROLES or rid not in DEFAULT_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Hanya peran bawaan (selain Admin) yang bisa dikembalikan ke bawaan.")
    matrix = await _matrix()
    matrix[rid] = deepcopy(DEFAULT_PERMISSIONS[rid])
    await _save_matrix(matrix)
    return await get_role(rid)


async def delete_custom(rid: str) -> Dict[str, Any]:
    await sync_registry()
    if rid not in reg.ROLES or not reg.ROLES[rid].get("custom"):
        raise HTTPException(status_code=400, detail="Peran bawaan sistem tidak bisa dihapus.")
    n = await db.users.count_documents({"role": rid})
    if n:
        inactive = await db.users.count_documents({"role": rid, "status": {"$ne": "active"}})
        extra = f" ({inactive} di antaranya nonaktif)" if inactive else ""
        raise HTTPException(
            status_code=409,
            detail=f"Peran ini masih dipakai {n} akun{extra}. Pindahkan akun tersebut ke peran lain "
                   f"dulu (layar Akun & Akses), baru hapus.")
    matrix = await _matrix()
    matrix.pop(rid, None)
    await _save_matrix(matrix)
    await db.custom_roles.delete_one({"id": rid})
    await sync_registry()
    return {"id": rid, "deleted": True}


async def preview_role(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pratinjau hak (tanpa menyimpan): notifikasi giliran & layar yang notifikasinya lolos."""
    await sync_registry()
    src = (payload.get("role_id") or payload.get("base_role") or "").strip()
    if src and src not in reg.ROLES:
        raise HTTPException(status_code=400, detail="Peran acuan tidak dikenal.")
    matrix = await _matrix()
    current = matrix.get(src) if src else {}
    if current is None:
        current = DEFAULT_PERMISSIONS.get(src, {})
    perms = apply_levels(deepcopy(current or {}), _clean_levels(payload.get("levels")))
    if payload.get("permissions") is not None:
        perms = _clean_perms(payload["permissions"])
    return {"turn_alerts": _turn_alerts(perms), "screens": sorted(nav_allowed_for_perms(perms)),
            "levels": levels_of(perms)}


async def move_users(rid: str, to_role: str) -> Dict[str, Any]:
    await sync_registry()
    if rid not in reg.ROLES or to_role not in reg.ROLES:
        raise HTTPException(status_code=404, detail="Peran tidak ditemukan.")
    if to_role == rid:
        raise HTTPException(status_code=400, detail="Peran tujuan sama dengan peran asal.")
    if to_role in LOCKED_ROLES:
        raise HTTPException(status_code=400, detail="Akun tidak bisa dipindahkan massal ke peran Admin.")
    ids = [u["id"] for u in await db.users.find({"role": rid}, {"_id": 0, "id": 1}).to_list(500)]
    if ids:
        await db.users.update_many({"role": rid}, {"$set": {"role": to_role, "updated_at": now_iso()}})
    return {"from_role": rid, "to_role": to_role, "to_role_label": reg.role_label(to_role),
            "moved": len(ids), "user_ids": ids}


async def assert_valid_role_async(role: str) -> str:
    await sync_registry()
    return reg.assert_valid_role(role)


def nav_of(levels: Dict[str, str]) -> Dict[str, List[str]]:
    return nav_for_levels(levels)
