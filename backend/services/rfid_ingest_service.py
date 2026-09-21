"""FASE R3 — Device Ingest API (kontrak hardware: gate Chainway UR300 / handheld /
printer RFID via middleware Kotlin).

Autentikasi: header `X-Device-Key` per device (bukan login user). Keputusan gate
kini SADAR-DOKUMEN: gate-in memvalidasi Putaway Order tujuan, gate-out memvalidasi
dokumen keluar (SO/transfer/PA). RFID tetap tidak mengubah stok — hanya mencatat
`rfid_reads` dan menjawab green/red agar middleware membunyikan lampu/alarm.
"""
import secrets
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, safe_doc

from services.rfid_service import GREEN_OUT as GREEN_OUT_STATUSES  # KN-C03 — satu daftar bersama


async def ensure_api_key(device_id: str, regenerate: bool = False) -> Dict[str, Any]:
    dev = await db.rfid_devices.find_one({"id": device_id}, {"_id": 0})
    if not dev:
        raise HTTPException(status_code=404, detail="Device tidak ditemukan")
    if dev.get("api_key") and not regenerate:
        return {"device_id": device_id, "api_key": dev["api_key"]}
    key = f"dk_{secrets.token_hex(16)}"
    await db.rfid_devices.update_one({"id": device_id}, {"$set": {
        "api_key": key, "api_key_at": now_iso()}})
    return {"device_id": device_id, "api_key": key}


async def authenticate(device_key: Optional[str]) -> Dict[str, Any]:
    if not device_key:
        raise HTTPException(status_code=401, detail="Header X-Device-Key wajib")
    dev = await db.rfid_devices.find_one({"api_key": device_key}, {"_id": 0})
    if not dev:
        raise HTTPException(status_code=401, detail="Device key tidak dikenal")
    return dev


async def heartbeat(device: Dict[str, Any]) -> Dict[str, Any]:
    await db.rfid_devices.update_one({"id": device["id"]}, {"$set": {
        "status": "online", "last_heartbeat": now_iso()}})
    return {"ok": True, "device_id": device["id"], "server_time": now_iso()}


async def _doc_gate_decision(device: Dict[str, Any], roll: Dict[str, Any]) -> Dict[str, str]:
    """Keputusan SADAR-DOKUMEN. direction=in: cocokkan PA/transfer tujuan gudang ini.
    direction=out: harus ada dokumen keluar (PA/SO/transfer)."""
    direction = device.get("direction") or "out"
    wh_id = device.get("warehouse_id")
    status = roll.get("status", "?")
    journey = roll.get("journey") or {}
    pa_id = journey.get("putaway_order_id")
    pa = await db.putaway_orders.find_one({"id": pa_id}, {"_id": 0, "pa_number": 1,
        "to_warehouse_id": 1, "from_warehouse_id": 1, "to_warehouse_name": 1,
        "status": 1}) if pa_id else None

    if direction == "in":
        if pa and pa.get("status") in ("open", "in_transit"):
            if pa["to_warehouse_id"] == wh_id:
                return {"result": "green", "reason": f"Sesuai {pa['pa_number']} — tujuan gudang ini."}
            return {"result": "red", "reason": (
                f"SALAH GUDANG — {pa['pa_number']} menuju {pa.get('to_warehouse_name', '?')}, bukan gudang ini.")}
        if status in ("in_transit_transfer", "in_transit_sales"):
            return {"result": "green", "reason": f"Barang transit diterima (status: {status})."}
        if roll.get("warehouse_id") == wh_id:
            return {"result": "info", "reason": "Roll milik gudang ini terbaca di gate masuk."}
        return {"result": "red", "reason": "Tidak ada dokumen tujuan (PA/transfer) ke gudang ini."}

    # direction == out
    if journey.get("stage") == "putaway_in_transit" and pa and pa.get("from_warehouse_id") == wh_id:
        return {"result": "green", "reason": f"Keluar untuk putaway {pa['pa_number']}."}
    if status == "quarantine":
        return {"result": "red", "reason": "Roll KARANTINA (QC hold) — dilarang keluar."}
    if status == "available":
        return {"result": "red", "reason": "Roll masih AVAILABLE — tidak ada dokumen keluar (SO/transfer/PA). Keluar tak sah."}
    if status in GREEN_OUT_STATUSES:
        ref = roll.get("reserved_ref") or {}
        so = ""
        if isinstance(ref, dict) and ref.get("type") == "sales_order" and ref.get("id"):
            so_doc = await db.sales_orders.find_one({"id": ref["id"]}, {"_id": 0, "number": 1})
            so = f" untuk SO {so_doc.get('number', ref['id'])}" if so_doc else ""
        return {"result": "green", "reason": f"Keluar ter-otorisasi (status: {status}){so}."}
    return {"result": "red", "reason": f"Status tak dikenal untuk keluar: {status}."}


async def ingest(device: Dict[str, Any], epcs: List[str]) -> Dict[str, Any]:
    """Batch pembacaan dari device fisik → keputusan per EPC + catat rfid_reads."""
    if device.get("type") not in ("gate", "fixed_reader", "handheld"):
        raise HTTPException(status_code=400, detail="Tipe device ini tidak menerima pembacaan EPC")
    await db.rfid_devices.update_one({"id": device["id"]}, {"$set": {
        "status": "online", "last_heartbeat": now_iso()}})
    read_type = ("gate_in" if device.get("direction") == "in" else "gate_out") \
        if device.get("type") == "gate" else "inventory"
    results, reads = [], []
    now = now_iso()
    for raw in list(dict.fromkeys(e.strip().upper() for e in epcs if e and e.strip()))[:500]:
        tag = await db.rfid_tags.find_one({"epc": raw, "status": "active"}, {"_id": 0})
        roll = await db.inventory_rolls.find_one({"id": tag["roll_id"]}, {"_id": 0}) if tag else None
        if not tag or not roll:
            decision = {"result": "red", "reason": "EPC tidak dikenal / tag tidak aktif."}
            results.append({"epc": raw, **decision, "roll_no": None, "sku": None})
            reads.append({"id": new_id("rread"), "epc": raw, "tag_id": None, "roll_id": None,
                          "sku": None, "product_name": None, "roll_no": None,
                          "device_id": device["id"], "device_name": device.get("name"),
                          "device_type": device.get("type"), "read_type": read_type,
                          "warehouse_id": device.get("warehouse_id"), "location": device.get("location"),
                          "owner_entity_id": None, "result": "red",
                          "reason": decision["reason"], "timestamp": now})
            continue
        if device.get("type") == "gate":
            decision = await _doc_gate_decision(device, roll)
        else:
            decision = {"result": "info", "reason": "Pembacaan inventori (handheld/fixed reader)."}
        results.append({"epc": raw, **decision, "roll_no": roll.get("roll_no"),
                        "sku": tag.get("sku"), "product_name": tag.get("product_name")})
        reads.append({"id": new_id("rread"), "epc": raw, "tag_id": tag["id"], "roll_id": roll["id"],
                      "sku": tag.get("sku"), "product_name": tag.get("product_name"),
                      "roll_no": roll.get("roll_no"), "device_id": device["id"],
                      "device_name": device.get("name"), "device_type": device.get("type"),
                      "read_type": read_type, "warehouse_id": device.get("warehouse_id"),
                      "location": device.get("location"), "owner_entity_id": roll.get("owner_entity_id"),
                      "result": decision["result"], "reason": decision["reason"], "timestamp": now})
        await db.rfid_tags.update_one({"id": tag["id"]}, {"$set": {
            "last_seen_at": now, "last_seen_device_id": device["id"],
            "last_seen_device_name": device.get("name"),
            "last_seen_location": device.get("location"),
            "last_seen_warehouse_id": device.get("warehouse_id")}})
    if reads:
        await db.rfid_reads.insert_many(reads)
        # FASE R6 — pembacaan gate MERAH otomatis menjadi insiden (alarm operator)
        from services import rfid_incident_service as inc
        for r in reads:
            if r["result"] == "red" and r["read_type"] in ("gate_in", "gate_out"):
                await inc.create_from_read(r)
    greens = sum(1 for r in results if r["result"] == "green")
    reds = sum(1 for r in results if r["result"] == "red")
    return {"device": {"id": device["id"], "code": device.get("code"), "direction": device.get("direction")},
            "count": len(results), "green": greens, "red": reds, "results": results}


# ─── Printer pull (middleware ambil antrean ZPL) ────────────────────────────
async def pending_jobs_for_device(device: Dict[str, Any]) -> Dict[str, Any]:
    if device.get("type") != "printer":
        raise HTTPException(status_code=400, detail="Device bukan printer")
    jobs = await db.rfid_print_jobs.find(
        {"warehouse_id": device.get("warehouse_id"), "status": "queued"},
        {"_id": 0}).sort("created_at", 1).to_list(20)
    return {"count": len(jobs), "jobs": [safe_doc(j) for j in jobs]}


async def ack_job_printed(device: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    job = await db.rfid_print_jobs.find_one({"id": job_id}, {"_id": 0, "items.zpl": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Print job tidak ditemukan")
    if job.get("warehouse_id") != device.get("warehouse_id"):
        raise HTTPException(status_code=403, detail="Job bukan milik gudang device ini")
    if job.get("status") != "queued":
        return {"ok": True, "status": job["status"]}
    await db.rfid_print_jobs.update_one({"id": job_id}, {"$set": {
        "status": "printed", "printed_at": now_iso(), "printed_by_device": device["id"]}})
    return {"ok": True, "status": "printed"}
