"""FASE R6 — Insiden gate MERAH: alarm → acknowledge operator → resolve,
laporan shrinkage, dan kesehatan device (heartbeat monitor).

Insiden dibuat otomatis dari pembacaan gate berhasil-MERAH (ingest & simulasi).
Dedupe: EPC+device yang sama dalam 10 menit → hitungan `hits` bertambah,
tidak membanjiri daftar alarm.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, safe_doc

DEDUPE_MINUTES = 10
HEARTBEAT_STALE_SECONDS = 300


async def create_from_read(read: Dict[str, Any]) -> None:
    """Panggil untuk setiap pembacaan gate MERAH."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=DEDUPE_MINUTES)).isoformat()
    dup = await db.rfid_incidents.find_one({
        "epc": read.get("epc"), "device_id": read.get("device_id"),
        "status": "open", "last_at": {"$gte": cutoff}}, {"_id": 0, "id": 1})
    if dup:
        await db.rfid_incidents.update_one({"id": dup["id"]}, {
            "$inc": {"hits": 1}, "$set": {"last_at": now_iso(), "reason": read.get("reason", "")}})
        return
    inc_id = new_id("rinc")
    await db.rfid_incidents.insert_one({
        "id": inc_id, "read_id": read.get("id"), "epc": read.get("epc"),
        "roll_id": read.get("roll_id"), "roll_no": read.get("roll_no"),
        "sku": read.get("sku"), "product_name": read.get("product_name"),
        "device_id": read.get("device_id"), "device_name": read.get("device_name"),
        "read_type": read.get("read_type"), "warehouse_id": read.get("warehouse_id"),
        "owner_entity_id": read.get("owner_entity_id"),
        "reason": read.get("reason", ""), "severity": "high" if read.get("roll_id") else "medium",
        "status": "open", "hits": 1,
        "created_at": now_iso(), "last_at": now_iso(),
        "ack_by": None, "ack_at": None, "resolved_by": None, "resolved_at": None,
        "notes": [],
    })
    # NOTIFIKASI REAL-TIME kepala gudang (best-effort — alarm tak boleh gagal karenanya)
    try:
        from services.notification_service import create_notification
        wh = await db.warehouses.find_one({"id": read.get("warehouse_id")},
                                          {"_id": 0, "name": 1}) or {}
        await create_notification(
            notif_type="rfid_gate_alarm",
            title=f"🔴 ALARM GATE MERAH — {wh.get('name', 'Gudang')}",
            body=(f"{read.get('roll_no') or read.get('epc')} ditahan di "
                  f"{read.get('device_name', 'gate')}: {read.get('reason', '')} "
                  f"Segera acknowledge di layar Alarm & Keamanan."),
            severity="critical", link="cs-rfid-gate",
            entity_id=read.get("owner_entity_id"),
            recipient_role="warehouse", ref=inc_id, dedupe=True,
        )
    except Exception:
        pass


async def list_incidents(status: Optional[str], warehouse_id: Optional[str],
                         limit: int = 100) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    if warehouse_id:
        q["warehouse_id"] = warehouse_id
    rows = await db.rfid_incidents.find(q, {"_id": 0}).sort("last_at", -1).to_list(limit)
    return [safe_doc(r) for r in rows]


async def _transition(incident_id: str, to_status: str, actor: str, note: str) -> Dict[str, Any]:
    inc = await db.rfid_incidents.find_one({"id": incident_id}, {"_id": 0})
    if not inc:
        raise HTTPException(status_code=404, detail="Insiden tidak ditemukan")
    allowed = {"acknowledged": ["open"], "resolved": ["open", "acknowledged"]}
    if inc["status"] not in allowed[to_status]:
        raise HTTPException(status_code=400, detail=f"Insiden berstatus {inc['status']}")
    now = now_iso()
    upd: Dict[str, Any] = {"status": to_status}
    if to_status == "acknowledged":
        upd.update({"ack_by": actor, "ack_at": now})
    else:
        upd.update({"resolved_by": actor, "resolved_at": now})
    op: Dict[str, Any] = {"$set": upd}
    if note:
        op["$push"] = {"notes": {"by": actor, "at": now, "text": note.strip()}}
    await db.rfid_incidents.update_one({"id": incident_id}, op)
    return safe_doc(await db.rfid_incidents.find_one({"id": incident_id}, {"_id": 0}))


async def acknowledge(incident_id: str, actor: str, note: str = "") -> Dict[str, Any]:
    return await _transition(incident_id, "acknowledged", actor, note)


async def resolve(incident_id: str, actor: str, note: str = "") -> Dict[str, Any]:
    return await _transition(incident_id, "resolved", actor, note)


async def shrinkage_report(days: int = 30) -> Dict[str, Any]:
    """Rekap keamanan: red reads, insiden, roll gate_exception, akurasi cycle count."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    wh_names = {w["id"]: w.get("name", w["id"]) async for w in
                db.warehouses.find({}, {"_id": 0, "id": 1, "name": 1})}
    per_wh: Dict[str, Dict[str, Any]] = {}

    def bucket(wid: Optional[str]) -> Dict[str, Any]:
        key = wid or "-"
        return per_wh.setdefault(key, {
            "warehouse_id": wid, "warehouse_name": wh_names.get(wid, "—"),
            "red_reads": 0, "incidents_open": 0, "incidents_ack": 0,
            "incidents_resolved": 0, "gate_exception_rolls": 0})

    async for r in db.rfid_reads.aggregate([
        {"$match": {"result": "red", "timestamp": {"$gte": cutoff},
                    "read_type": {"$in": ["gate_in", "gate_out"]}}},
        {"$group": {"_id": "$warehouse_id", "n": {"$sum": 1}}}]):
        bucket(r["_id"])["red_reads"] = r["n"]
    async for r in db.rfid_incidents.aggregate([
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": {"w": "$warehouse_id", "s": "$status"}, "n": {"$sum": 1}}}]):
        b = bucket(r["_id"]["w"])
        key = {"open": "incidents_open", "acknowledged": "incidents_ack",
               "resolved": "incidents_resolved"}.get(r["_id"]["s"])
        if key:
            b[key] = r["n"]
    async for r in db.inventory_rolls.aggregate([
        {"$match": {"journey.stage": "gate_exception"}},
        {"$group": {"_id": "$warehouse_id", "n": {"$sum": 1}}}]):
        bucket(r["_id"])["gate_exception_rolls"] = r["n"]

    ccs = await db.rfid_cycle_counts.find({"created_at": {"$gte": cutoff}},
                                          {"_id": 0, "warehouse_id": 1, "warehouse_name": 1,
                                           "cc_number": 1, "accuracy_pct": 1, "missing_count": 1,
                                           "created_at": 1}).sort("created_at", -1).to_list(10)
    rows = sorted(per_wh.values(), key=lambda x: -(x["red_reads"] + x["incidents_open"]))
    return {
        "days": days,
        "totals": {
            "red_reads": sum(r["red_reads"] for r in rows),
            "incidents_open": sum(r["incidents_open"] for r in rows),
            "gate_exception_rolls": sum(r["gate_exception_rolls"] for r in rows),
        },
        "per_warehouse": rows,
        "recent_cycle_counts": [safe_doc(c) for c in ccs],
    }


async def device_health() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    devices = await db.rfid_devices.find({}, {"_id": 0, "api_key": 0}).to_list(200)
    out = []
    for d in devices:
        hb = d.get("last_heartbeat")
        age = None
        if hb:
            try:
                age = int((now - datetime.fromisoformat(hb.replace("Z", "+00:00"))).total_seconds())
            except ValueError:
                age = None
        effective = "online" if (age is not None and age <= HEARTBEAT_STALE_SECONDS) else \
            ("stale" if d.get("status") == "online" else "offline")
        out.append({**safe_doc(d), "heartbeat_age_sec": age, "effective_status": effective})
    out.sort(key=lambda x: (x["effective_status"] != "stale", x["effective_status"] != "offline"))
    return {"count": len(out), "devices": out,
            "stale_count": sum(1 for d in out if d["effective_status"] == "stale")}
