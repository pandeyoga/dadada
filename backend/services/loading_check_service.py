"""FASE R4 — FINAL LOADING CHECK: sweep handheld vs manifest SO sebelum naik mobil.

Memakai koleksi `rfid_verify_sessions` yang sama (kind="loading_check") agar tidak
ada mesin kembar. Hasil terakhir disimpan di `sales_orders.loading_check`; dispatch
DIBLOKIR bila ada sesi terbuka atau hasil terakhir tidak bersih.
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, safe_doc

EXPECTED_STATUSES = ["reserved", "committed", "picked", "packed", "allocated"]


async def _expected_rolls(order_id: str) -> List[Dict[str, Any]]:
    rolls = await db.inventory_rolls.find({
        "reserved_ref.type": "sales_order", "reserved_ref.id": order_id,
        "status": {"$in": EXPECTED_STATUSES}, "length_remaining": {"$gt": 0},
    }, {"_id": 0, "id": 1, "roll_no": 1, "rfid_tag_id": 1, "product_id": 1, "status": 1}).to_list(2000)
    return rolls


async def start(order_id: str, scope_ids: List[str], actor_name: str) -> Dict[str, Any]:
    so = await db.sales_orders.find_one({"id": order_id}, {"_id": 0, "id": 1, "number": 1,
                                                           "entity_id": 1})
    if not so:
        raise HTTPException(status_code=404, detail="SO tidak ditemukan")
    if so.get("entity_id") and so["entity_id"] not in scope_ids:
        raise HTTPException(status_code=403, detail="SO di luar entitas Anda")
    existing = await db.rfid_verify_sessions.find_one(
        {"kind": "loading_check", "order_id": order_id, "status": "open"}, {"_id": 0})
    if existing:
        return safe_doc(existing)
    rolls = await _expected_rolls(order_id)
    if not rolls:
        raise HTTPException(status_code=400, detail="Tidak ada roll ter-alokasi untuk SO ini (pick dulu).")
    tag_ids = [r["rfid_tag_id"] for r in rolls if r.get("rfid_tag_id")]
    tags = {t["id"]: t for t in await db.rfid_tags.find(
        {"id": {"$in": tag_ids}, "status": "active"}, {"_id": 0}).to_list(2000)}
    expected = []
    for r in rolls:
        t = tags.get(r.get("rfid_tag_id"))
        if t:
            expected.append({"epc": t["epc"], "roll_id": r["id"], "roll_no": r.get("roll_no", ""),
                             "sku": t.get("sku", ""), "product_name": t.get("product_name", "")})
    if not expected:
        raise HTTPException(status_code=400,
                            detail="Roll SO ini belum ber-tag RFID — print & verifikasi tag dulu.")
    sess = {
        "id": new_id("rvs"), "kind": "loading_check", "order_id": order_id,
        "so_number": so.get("number", ""), "print_job_id": None,
        "owner_entity_id": so.get("entity_id"), "warehouse_id": None,
        "expected": expected, "scanned_epcs": [], "missing": [], "extra": [],
        "untagged_count": len(rolls) - len(expected),
        # Peringatan dini: roll expected yang BELUM committed akan lolos check tapi
        # tertahan saat dispatch (ship_order_rolls hanya kirim roll committed).
        "not_committed_count": sum(1 for r in rolls
                                   if r.get("status") in ("reserved", "allocated")),
        "status": "open", "created_at": now_iso(), "created_by": actor_name,
        "completed_at": None,
    }
    await db.rfid_verify_sessions.insert_one(dict(sess))
    return safe_doc(sess)


async def complete(session_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    from services.rfid_print_service import _verify_progress
    prog = await _verify_progress(session_id)
    if prog.get("kind") != "loading_check":
        raise HTTPException(status_code=400, detail="Bukan sesi loading check")
    if prog.get("owner_entity_id") and prog["owner_entity_id"] not in scope_ids:
        raise HTTPException(status_code=403, detail="Sesi di luar entitas Anda")
    if prog["status"] != "open":
        raise HTTPException(status_code=400, detail="Sesi sudah selesai")
    clean = "clean" if not prog["missing"] and not prog["extra"] else "with_issues"
    now = now_iso()
    # INV-ATOMIC-01 — klaim sesi (status open) SESUDAH validasi, sebelum SO ditulis; finish_set.
    from services import atomic_claim as _saga
    await _saga.claim("rfid_verify_sessions", session_id, "loading_check_complete",
                      precondition={"status": "open"})
    await db.sales_orders.update_one({"id": prog["order_id"]}, {"$set": {"loading_check": {
        "session_id": session_id, "result": clean,
        "matched": prog["matched_count"], "expected": prog["expected_count"],
        "missing": prog["missing"], "extra": prog["extra"], "checked_at": now}}})
    await db.rfid_verify_sessions.update_one({"id": session_id}, _saga.finish_set({
        "status": "completed", "result": clean, "missing": prog["missing"],
        "extra": prog["extra"], "completed_at": now}))
    return await _verify_progress(session_id)


async def dispatch_guard(order_id: Optional[str]) -> None:
    """Blokir dispatch bila loading check terbuka / hasil terakhir tidak bersih."""
    if not order_id:
        return
    open_sess = await db.rfid_verify_sessions.find_one(
        {"kind": "loading_check", "order_id": order_id, "status": "open"}, {"_id": 0, "id": 1})
    if open_sess:
        raise HTTPException(status_code=400, detail=(
            "Final Loading Check masih BERJALAN untuk SO ini — selesaikan dulu sebelum dispatch."))
    so = await db.sales_orders.find_one({"id": order_id}, {"_id": 0, "loading_check": 1})
    lc = (so or {}).get("loading_check")
    if lc and lc.get("result") != "clean":
        raise HTTPException(status_code=400, detail=(
            f"Final Loading Check TIDAK BERSIH (missing {len(lc.get('missing') or [])}, "
            f"extra {len(lc.get('extra') or [])}) — ulangi check atau bereskan selisih sebelum dispatch."))


async def status_for_order(order_id: str) -> Dict[str, Any]:
    open_sess = await db.rfid_verify_sessions.find_one(
        {"kind": "loading_check", "order_id": order_id, "status": "open"}, {"_id": 0})
    so = await db.sales_orders.find_one({"id": order_id}, {"_id": 0, "loading_check": 1})
    return {"open_session": safe_doc(open_sess) if open_sess else None,
            "last_result": (so or {}).get("loading_check")}
