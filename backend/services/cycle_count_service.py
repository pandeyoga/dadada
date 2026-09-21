"""CYCLE COUNT RFID — stock opname kilat via sweep handheld.

Expected = seluruh tag aktif roll fisik di gudang → scan handheld → rekonsiliasi:
found / missing (ada di sistem, tak terbaca) / extra (terbaca tapi milik gudang
lain atau EPC asing). LAPORAN SAJA — RFID tidak mengubah kuantitas (Roll-as-SSOT);
selisih ditindaklanjuti manual/insiden.
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, next_doc_number, safe_doc
from services.rfid_service import PHYSICAL_STATUSES


async def start(warehouse_id: str, scope_ids: List[str], actor_name: str) -> Dict[str, Any]:
    wh = await db.warehouses.find_one({"id": warehouse_id}, {"_id": 0, "name": 1})
    if not wh:
        raise HTTPException(status_code=404, detail="Gudang tidak ditemukan")
    existing = await db.rfid_verify_sessions.find_one(
        {"kind": "cycle_count", "warehouse_id": warehouse_id, "status": "open"}, {"_id": 0})
    if existing:
        return safe_doc(existing)
    rolls = await db.inventory_rolls.find({
        "warehouse_id": warehouse_id, "owner_entity_id": {"$in": scope_ids},
        "status": {"$in": PHYSICAL_STATUSES}, "length_remaining": {"$gt": 0},
        "rfid_tag_id": {"$nin": [None, ""]},
    }, {"_id": 0, "id": 1, "roll_no": 1, "rfid_tag_id": 1}).to_list(20000)
    if not rolls:
        raise HTTPException(status_code=400, detail="Tidak ada roll ber-tag di gudang ini.")
    tags = {t["id"]: t for t in await db.rfid_tags.find(
        {"id": {"$in": [r["rfid_tag_id"] for r in rolls]}, "status": "active"},
        {"_id": 0, "id": 1, "epc": 1, "sku": 1, "product_name": 1}).to_list(20000)}
    expected = []
    for r in rolls:
        t = tags.get(r["rfid_tag_id"])
        if t:
            expected.append({"epc": t["epc"], "roll_id": r["id"], "roll_no": r.get("roll_no", ""),
                             "sku": t.get("sku", ""), "product_name": t.get("product_name", "")})
    sess = {
        "id": new_id("rvs"), "kind": "cycle_count", "print_job_id": None,
        "warehouse_id": warehouse_id, "warehouse_name": wh.get("name", ""),
        "owner_entity_id": scope_ids[0] if len(scope_ids) == 1 else None,
        "expected": expected, "scanned_epcs": [], "missing": [], "extra": [],
        "status": "open", "created_at": now_iso(), "created_by": actor_name,
        "completed_at": None,
    }
    await db.rfid_verify_sessions.insert_one(dict(sess))
    return safe_doc(sess)


async def complete(session_id: str, actor_name: str) -> Dict[str, Any]:
    sess = await db.rfid_verify_sessions.find_one({"id": session_id}, {"_id": 0})
    if not sess or sess.get("kind") != "cycle_count":
        raise HTTPException(status_code=404, detail="Sesi cycle count tidak ditemukan")
    if sess["status"] != "open":
        raise HTTPException(status_code=400, detail="Sesi sudah selesai")
    # Sesi 14 — klaim saga sesi (status open) sesudah validasi; klik ganda/balapan → 409, satu CC saja.
    from services import atomic_claim as _saga
    await _saga.claim("rfid_verify_sessions", session_id, "cycle_count_complete", actor=actor_name,
                      precondition={"status": "open"})
    expected = {e["epc"]: e for e in sess.get("expected", [])}
    scanned = set(sess.get("scanned_epcs") or [])
    missing = [expected[e] for e in expected if e not in scanned]
    extra_epcs = sorted(scanned - set(expected))
    extra_items = []
    for epc in extra_epcs:
        tag = await db.rfid_tags.find_one({"epc": epc, "status": "active"}, {"_id": 0})
        if not tag:
            extra_items.append({"epc": epc, "kind": "unknown", "note": "EPC asing (tak terdaftar)"})
            continue
        roll = await db.inventory_rolls.find_one({"id": tag["roll_id"]},
                                                 {"_id": 0, "roll_no": 1, "warehouse_id": 1})
        wh = await db.warehouses.find_one({"id": (roll or {}).get("warehouse_id")},
                                          {"_id": 0, "name": 1}) or {}
        extra_items.append({"epc": epc, "kind": "misplaced", "roll_no": (roll or {}).get("roll_no"),
                            "sku": tag.get("sku"), "note": f"Terdaftar di {wh.get('name', 'gudang lain')} — salah lokasi"})
    found = len(expected) - len(missing)
    accuracy = round(found / len(expected) * 100, 1) if expected else 100.0
    now = now_iso()
    cc = {
        "id": new_id("rcc"),
        "cc_number": await next_doc_number("rfid_cycle_counts", "cc_number", "CC"),
        "session_id": session_id, "warehouse_id": sess["warehouse_id"],
        "warehouse_name": sess.get("warehouse_name", ""),
        "expected_count": len(expected), "found_count": found,
        "missing_count": len(missing), "extra_count": len(extra_items),
        "accuracy_pct": accuracy,
        "missing_items": [safe_doc(m) for m in missing][:500],
        "extra_items": extra_items[:500],
        "created_at": now, "created_by": actor_name,
    }
    await db.rfid_cycle_counts.insert_one(dict(cc))
    await db.rfid_verify_sessions.update_one({"id": session_id}, _saga.finish_set({
        "status": "completed", "result": "clean" if not missing and not extra_items else "with_issues",
        "missing": [m["epc"] for m in missing], "extra": extra_epcs,
        "completed_at": now, "cycle_count_id": cc["id"]}))
    return safe_doc(cc)


async def list_counts(warehouse_id: Optional[str], limit: int = 30) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if warehouse_id:
        q["warehouse_id"] = warehouse_id
    rows = await db.rfid_cycle_counts.find(q, {"_id": 0, "missing_items": 0, "extra_items": 0}) \
        .sort("created_at", -1).to_list(limit)
    return [safe_doc(r) for r in rows]


async def get_count(cc_id: str) -> Dict[str, Any]:
    cc = await db.rfid_cycle_counts.find_one({"id": cc_id}, {"_id": 0})
    if not cc:
        raise HTTPException(status_code=404, detail="Cycle count tidak ditemukan")
    return safe_doc(cc)
