"""Armada internal — master kendaraan (`fleet_vehicles`, SCOPED) + ketersediaan sopir.

Status kendaraan: available | on_trip | maintenance. `on_trip` diset OTOMATIS saat
pengiriman armada sendiri berangkat (in_transit) dan dilepas saat terkirim/gagal/selesai.
Status sopir DITURUNKAN dari pengiriman aktif (tidak disimpan)."""
import re
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc

COLL = "fleet_vehicles"
VEHICLE_STATUSES = {"available": "Tersedia", "on_trip": "Dalam perjalanan", "maintenance": "Perawatan"}
VEHICLE_TYPES = {"pickup": "Pick-up", "box": "Truk box", "cde": "CDE", "cdd": "CDD", "van": "Van/Blindvan", "motor": "Motor", "other": "Lainnya"}
DRIVER_BUSY = ("loaded", "in_transit")


def _norm_plate(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


async def list_vehicles(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = await db[COLL].find(scope, {"_id": 0}).sort("plate", 1).to_list(500)
    return [_enrich(safe_doc(r)) for r in rows]


def _enrich(v: Dict[str, Any]) -> Dict[str, Any]:
    v["status_label"] = VEHICLE_STATUSES.get(v.get("status"), v.get("status"))
    v["type_label"] = VEHICLE_TYPES.get(v.get("type"), v.get("type") or "—")
    return v


async def create_vehicle(payload: Dict[str, Any], actor_name: str, entity_id: str) -> Dict[str, Any]:
    plate = _norm_plate(payload.get("plate"))
    if len(plate) < 3:
        raise ValueError("Plat kendaraan wajib diisi.")
    if await db[COLL].find_one({"entity_id": entity_id, "plate": plate}, {"_id": 1}):
        raise ValueError(f"Kendaraan {plate} sudah terdaftar.")
    vtype = (payload.get("type") or "other").strip()
    if vtype not in VEHICLE_TYPES:
        raise ValueError("Jenis kendaraan tidak dikenal.")
    doc = {"id": new_id("veh"), "entity_id": entity_id, "plate": plate, "type": vtype,
           "name": (payload.get("name") or "").strip(), "capacity_note": (payload.get("capacity_note") or "").strip(),
           "default_driver_user_id": (payload.get("default_driver_user_id") or "").strip(),
           "notes": (payload.get("notes") or "").strip(), "status": "available", "current_delivery_id": "",
           "status_note": "", "created_by": actor_name, "created_at": now_iso(), "updated_at": now_iso()}
    await db[COLL].insert_one(dict(doc))
    return _enrich(safe_doc(doc))


async def update_vehicle(vehicle_id: str, patch: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    doc = await db[COLL].find_one({"id": vehicle_id}, {"_id": 0})
    if not doc:
        raise ValueError("Kendaraan tidak ditemukan.")
    upd: Dict[str, Any] = {}
    for k in ("name", "capacity_note", "default_driver_user_id", "notes", "type"):
        if patch.get(k) is not None:
            upd[k] = str(patch[k]).strip()
    if patch.get("plate") is not None:
        plate = _norm_plate(patch["plate"])
        if len(plate) < 3:
            raise ValueError("Plat kendaraan wajib diisi.")
        dup = await db[COLL].find_one({"entity_id": doc["entity_id"], "plate": plate, "id": {"$ne": vehicle_id}}, {"_id": 1})
        if dup:
            raise ValueError(f"Kendaraan {plate} sudah terdaftar.")
        upd["plate"] = plate
    if "type" in upd and upd["type"] not in VEHICLE_TYPES:
        raise ValueError("Jenis kendaraan tidak dikenal.")
    if not upd:
        raise ValueError("Tidak ada perubahan.")
    upd["updated_at"] = now_iso()
    await db[COLL].update_one({"id": vehicle_id}, {"$set": upd})
    return _enrich(safe_doc(await db[COLL].find_one({"id": vehicle_id}, {"_id": 0})))


async def set_vehicle_status(vehicle_id: str, status: str, note: str, actor_name: str) -> Dict[str, Any]:
    """Manual: available ⇄ maintenance. `on_trip` hanya diset oleh mesin pengiriman."""
    doc = await db[COLL].find_one({"id": vehicle_id}, {"_id": 0})
    if not doc:
        raise ValueError("Kendaraan tidak ditemukan.")
    if status not in ("available", "maintenance"):
        raise ValueError("Status manual hanya: available / maintenance.")
    if doc.get("status") == "on_trip":
        raise ValueError(f"Kendaraan sedang dalam perjalanan ({doc.get('current_delivery_id')}) — selesaikan pengirimannya dulu.")
    await db[COLL].update_one({"id": vehicle_id}, {"$set": {
        "status": status, "status_note": (note or "").strip(), "updated_at": now_iso(), "status_by": actor_name}})
    return _enrich(safe_doc(await db[COLL].find_one({"id": vehicle_id}, {"_id": 0})))


async def assert_assignable(vehicle_id: str, entity_id: str) -> Dict[str, Any]:
    v = await db[COLL].find_one({"id": vehicle_id}, {"_id": 0})
    if not v:
        raise ValueError("Kendaraan tidak ditemukan.")
    if v.get("entity_id") and entity_id and v["entity_id"] != entity_id:
        raise ValueError("Kendaraan milik badan usaha lain.")
    if v.get("status") == "maintenance":
        raise ValueError(f"Kendaraan {v['plate']} sedang perawatan — pilih kendaraan lain.")
    if v.get("status") == "on_trip":
        raise ValueError(f"Kendaraan {v['plate']} sedang dalam perjalanan — pilih kendaraan lain.")
    return v


async def mark_on_trip(vehicle_id: str, delivery_id: str) -> None:
    if vehicle_id:
        await db[COLL].update_one({"id": vehicle_id}, {"$set": {
            "status": "on_trip", "current_delivery_id": delivery_id, "updated_at": now_iso()}})


async def release(vehicle_id: str, delivery_id: str) -> None:
    if vehicle_id:
        await db[COLL].update_one({"id": vehicle_id, "current_delivery_id": delivery_id}, {"$set": {
            "status": "available", "current_delivery_id": "", "updated_at": now_iso()}})


async def driver_status_map(scope: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """driver_user_id → pengiriman aktif yang sedang ia tangani (loaded/in_transit)."""
    out: Dict[str, Dict[str, Any]] = {}
    async for d in db.logistics_deliveries.find({**scope, "status": {"$in": list(DRIVER_BUSY)}, "driver_user_id": {"$ne": ""}},
                                                {"_id": 0, "id": 1, "number": 1, "driver_user_id": 1, "status": 1}):
        out.setdefault(d["driver_user_id"], d)
    return out


async def availability(scope: Dict[str, Any], entity_id: Optional[str]) -> Dict[str, Any]:
    from services.logistics_service import list_drivers
    vehicles = await list_vehicles(scope)
    busy = await driver_status_map(scope)
    drivers = []
    for u in await list_drivers(entity_id or ""):
        b = busy.get(u["id"])
        drivers.append({**u, "status": "on_trip" if b else "available",
                        "status_label": "Dalam perjalanan" if b else "Tersedia",
                        "current_delivery_id": (b or {}).get("id", ""), "current_delivery_no": (b or {}).get("number", "")})
    vsum = {s: sum(1 for v in vehicles if v.get("status") == s) for s in VEHICLE_STATUSES}
    dsum = {"available": sum(1 for d in drivers if d["status"] == "available"), "on_trip": sum(1 for d in drivers if d["status"] == "on_trip")}
    return {"vehicles": vehicles, "drivers": drivers, "vehicle_summary": vsum, "driver_summary": dsum,
            "vehicle_statuses": VEHICLE_STATUSES, "vehicle_types": VEHICLE_TYPES}
