"""FASE R1 — Print job tag RFID (bulk dari GR/roll transit) + sesi verifikasi handheld.

Prinsip:
- Print job TIDAK mengubah stok. Ia meng-encode tag (via rfid_service — SSOT tag)
  dan membawa payload ZPL untuk printer RFID (Chainway, emulasi ZPL: ^RFW).
- Verifikasi = expected (EPC di job) vs scanned (EPC dari handheld). Missing/extra
  ter-highlight; roll yang cocok naik journey → tag_verified.
- Journey roll: field `inventory_rolls.journey` {stage, routing} — TIDAK menyentuh
  bucket status stok (Roll-as-SSOT aman).
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, next_doc_number, safe_doc
from services import rfid_service

JOURNEY_STAGES = [
    "received_transit", "tag_printed", "tag_verified", "cross_dock_ready",
    "putaway_assigned", "putaway_in_transit", "stored", "gate_exception",
]
STAGE_LABEL = {
    "received_transit": "Diterima di Transit", "tag_printed": "Tag Dicetak",
    "tag_verified": "Tag Terverifikasi", "cross_dock_ready": "Cross-Dock (Langsung Kirim)",
    "putaway_assigned": "Masuk Putaway Order", "putaway_in_transit": "Menuju Gudang Simpan",
    "stored": "Tersimpan", "gate_exception": "Exception Gate",
}


async def set_journey(roll_ids: List[str], stage: str, extra: Optional[Dict[str, Any]] = None) -> None:
    upd = {"journey.stage": stage, "journey.updated_at": now_iso(), "updated_at": now_iso()}
    for k, v in (extra or {}).items():
        upd[f"journey.{k}"] = v
    op: Dict[str, Any] = {"$set": upd}
    if stage in ("stored", "tag_verified"):  # bersihkan sisa exception dari siklus sebelumnya
        op["$unset"] = {"journey.exception_reason": ""}
    await db.inventory_rolls.update_many({"id": {"$in": roll_ids}}, op)


def generate_rfid_zpl(epc: str, roll: Dict[str, Any], tag: Dict[str, Any]) -> str:
    """ZPL label 4x2" (203dpi) dengan tulis EPC ke chip RFID (^RFW,H)."""
    epc_hex = epc.replace("-", "")[:24]
    sku = (tag.get("sku") or "")[:28]
    name = (tag.get("product_name") or "")[:40]
    roll_no = roll.get("roll_no", "")
    lot = roll.get("lot", "")
    qty = f"{float(roll.get('length_remaining') or 0):g} {roll.get('unit', 'm')}"
    return (
        "^XA\n^RS8\n"
        f"^RFW,H^FD{epc_hex}^FS\n"
        f"^FO20,15^A0N,28,28^FD{name}^FS\n"
        f"^FO20,50^A0N,24,24^FDSKU: {sku}^FS\n"
        f"^FO20,80^A0N,24,24^FDRoll: {roll_no}  Lot: {lot}^FS\n"
        f"^FO20,110^A0N,24,24^FDQty: {qty}^FS\n"
        f"^FO20,140^BY2^BCN,50,Y,N,N^FD{roll_no or epc_hex}^FS\n"
        f"^FO20,196^A0N,18,18^FDEPC {epc}^FS\n"
        "^XZ"
    )


def generate_qr_zpl(roll: Dict[str, Any], product_name: str = "") -> str:
    """ZPL label 58×40 mm (203dpi ≈ 464×320 dot) dengan QR NOMOR ROLL (tanpa encode RFID) —
    isi QR sama dengan label browser, jadi HP gudang memindainya lewat GET /rfid/lookup."""
    roll_no = roll.get("roll_no", "")
    name = (product_name or roll.get("product_name") or "")[:30]
    qty = f"{float(roll.get('length_remaining') or roll.get('length') or 0):g} {roll.get('unit', 'm')}"
    lot = roll.get("lot") or roll.get("supplier_lot") or "-"
    return (
        "^XA\n^PW464\n^LL320\n"
        f"^FO16,16^BQN,2,6^FDQA,{roll_no}^FS\n"
        f"^FO200,20^A0N,34,34^FD{roll_no}^FS\n"
        f"^FO200,64^A0N,22,22^FD{name}^FS\n"
        f"^FO200,96^A0N,24,24^FD{qty}  Grade {roll.get('grade') or 'A'}^FS\n"
        f"^FO200,128^A0N,22,22^FDLot {lot}^FS\n"
        "^XZ"
    )


async def create_qr_label_job(roll_ids: List[str], scope_ids: List[str], actor_name: str,
                              source: str = "") -> Dict[str, Any]:
    """Antrean label QR (kind=qr_label) — satu antrean printer bersama dengan tag RFID, tanpa encode."""
    if not roll_ids:
        raise HTTPException(status_code=400, detail="Pilih minimal satu roll")
    rolls = await db.inventory_rolls.find({"id": {"$in": roll_ids}}, {"_id": 0}).to_list(len(roll_ids) + 5)
    if len(rolls) != len(set(roll_ids)):
        raise HTTPException(status_code=404, detail="Sebagian roll tidak ditemukan")
    wh_id = rolls[0].get("warehouse_id")
    for roll in rolls:
        if roll.get("owner_entity_id") not in scope_ids:
            raise HTTPException(status_code=403, detail=f"Roll {roll.get('roll_no')} di luar entitas Anda")
        if roll.get("warehouse_id") != wh_id:
            raise HTTPException(status_code=400, detail="Semua roll dalam satu job harus di gudang yang sama")
    pids = list({r.get("product_id") for r in rolls})
    names = {p["id"]: p.get("name", "") for p in await db.products.find({"id": {"$in": pids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(pids) or 1)}
    items = [{"roll_id": r["id"], "roll_no": r.get("roll_no", ""), "tag_id": None, "epc": None,
              "sku": r.get("sku", ""), "product_name": names.get(r.get("product_id"), ""),
              "lot": r.get("lot", ""), "qty": float(r.get("length_remaining") or 0), "unit": r.get("unit", "meter"),
              "zpl": generate_qr_zpl(r, names.get(r.get("product_id"), ""))} for r in rolls]
    wh = await db.warehouses.find_one({"id": wh_id}, {"_id": 0, "name": 1}) or {}
    job = {
        "id": new_id("rpj"), "kind": "qr_label", "source": source,
        "job_number": await next_doc_number("rfid_print_jobs", "job_number", "PJ"),
        "warehouse_id": wh_id, "warehouse_name": wh.get("name", ""),
        "owner_entity_id": rolls[0].get("owner_entity_id"), "status": "queued",
        "items": items, "item_count": len(items),
        "created_at": now_iso(), "created_by": actor_name, "printed_at": None, "verified_at": None,
    }
    await db.rfid_print_jobs.insert_one(dict(job))
    return safe_doc(job)


async def create_print_job(roll_ids: List[str], scope_ids: List[str],
                           actor_name: str) -> Dict[str, Any]:
    if not roll_ids:
        raise HTTPException(status_code=400, detail="Pilih minimal satu roll")
    rolls = await db.inventory_rolls.find({"id": {"$in": roll_ids}}, {"_id": 0}).to_list(len(roll_ids) + 5)
    if len(rolls) != len(set(roll_ids)):
        raise HTTPException(status_code=404, detail="Sebagian roll tidak ditemukan")
    items, wh_id, owner = [], None, None
    for roll in rolls:
        if roll.get("owner_entity_id") not in scope_ids:
            raise HTTPException(status_code=403, detail=f"Roll {roll.get('roll_no')} di luar entitas Anda")
        wh_id = wh_id or roll.get("warehouse_id")
        owner = owner or roll.get("owner_entity_id")
        if roll.get("warehouse_id") != wh_id:
            raise HTTPException(status_code=400, detail="Semua roll dalam satu job harus di gudang yang sama")
        tag = None
        if roll.get("rfid_tag_id"):
            tag = await db.rfid_tags.find_one({"id": roll["rfid_tag_id"], "status": "active"}, {"_id": 0})
        if not tag:
            tag = await rfid_service.encode_tag(roll["id"], scope_ids, actor_name=actor_name)
        items.append({
            "roll_id": roll["id"], "roll_no": roll.get("roll_no", ""), "tag_id": tag["id"],
            "epc": tag["epc"], "sku": tag.get("sku", ""), "product_name": tag.get("product_name", ""),
            "lot": roll.get("lot", ""), "qty": float(roll.get("length_remaining") or 0),
            "unit": roll.get("unit", "meter"),
            "zpl": generate_rfid_zpl(tag["epc"], roll, tag),
        })
    wh = await db.warehouses.find_one({"id": wh_id}, {"_id": 0, "name": 1}) or {}
    job = {
        "id": new_id("rpj"), "kind": "rfid_tag",
        "job_number": await next_doc_number("rfid_print_jobs", "job_number", "PJ"),
        "warehouse_id": wh_id, "warehouse_name": wh.get("name", ""),
        "owner_entity_id": owner, "status": "queued",
        "items": items, "item_count": len(items),
        "created_at": now_iso(), "created_by": actor_name,
        "printed_at": None, "verified_at": None,
    }
    await db.rfid_print_jobs.insert_one(dict(job))
    await set_journey([i["roll_id"] for i in items], "tag_printed", {"print_job_id": job["id"]})
    return safe_doc(job)


async def list_print_jobs(scope_ids: List[str], warehouse_id: Optional[str],
                          status: Optional[str], limit: int = 100) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"owner_entity_id": {"$in": scope_ids}}
    if warehouse_id:
        q["warehouse_id"] = warehouse_id
    if status:
        q["status"] = status
    jobs = await db.rfid_print_jobs.find(q, {"_id": 0, "items.zpl": 0}).sort("created_at", -1).to_list(limit)
    return [safe_doc(j) for j in jobs]


async def get_print_job(job_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    job = await db.rfid_print_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Print job tidak ditemukan")
    if job.get("owner_entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="Print job di luar entitas Anda")
    return safe_doc(job)


async def mark_printed(job_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    job = await get_print_job(job_id, scope_ids)
    if job["status"] != "queued":
        raise HTTPException(status_code=400, detail=f"Job sudah berstatus {job['status']}")
    await db.rfid_print_jobs.update_one({"id": job_id}, {"$set": {
        "status": "printed", "printed_at": now_iso(), "updated_at": now_iso()}})
    return await get_print_job(job_id, scope_ids)


def job_zpl(job: Dict[str, Any]) -> str:
    return "\n".join(i.get("zpl", "") for i in job.get("items", []))


# ─── Verifikasi (expected vs scanned) ────────────────────────────────────────
async def start_verify(job_id: str, scope_ids: List[str], actor_name: str) -> Dict[str, Any]:
    job = await get_print_job(job_id, scope_ids)
    if job["status"] not in ("printed", "queued"):
        raise HTTPException(status_code=400, detail=f"Job berstatus {job['status']} — tidak bisa diverifikasi ulang")
    existing = await db.rfid_verify_sessions.find_one(
        {"print_job_id": job_id, "status": "open"}, {"_id": 0})
    if existing:
        return safe_doc(existing)
    sess = {
        "id": new_id("rvs"), "print_job_id": job_id, "job_number": job.get("job_number", ""),
        "warehouse_id": job.get("warehouse_id"), "owner_entity_id": job.get("owner_entity_id"),
        "expected": [{"epc": i["epc"], "roll_id": i["roll_id"], "roll_no": i["roll_no"],
                      "sku": i["sku"], "product_name": i["product_name"]} for i in job["items"]],
        "scanned_epcs": [], "missing": [], "extra": [],
        "status": "open", "created_at": now_iso(), "created_by": actor_name,
        "completed_at": None,
    }
    await db.rfid_verify_sessions.insert_one(dict(sess))
    return safe_doc(sess)


async def scan_verify(session_id: str, epcs: List[str], scope_ids: List[str]) -> Dict[str, Any]:
    sess = await db.rfid_verify_sessions.find_one({"id": session_id}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Sesi verifikasi tidak ditemukan")
    if sess.get("owner_entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="Sesi di luar entitas Anda")
    if sess["status"] != "open":
        raise HTTPException(status_code=400, detail="Sesi sudah selesai")
    clean = {e.strip().upper() for e in epcs if e and e.strip()}
    merged = sorted(set(sess.get("scanned_epcs") or []) | clean)
    await db.rfid_verify_sessions.update_one({"id": session_id}, {"$set": {
        "scanned_epcs": merged, "updated_at": now_iso()}})
    return await _verify_progress(session_id)


async def _verify_progress(session_id: str) -> Dict[str, Any]:
    sess = await db.rfid_verify_sessions.find_one({"id": session_id}, {"_id": 0})
    expected = {e["epc"] for e in sess.get("expected", [])}
    scanned = set(sess.get("scanned_epcs") or [])
    sess["matched_count"] = len(expected & scanned)
    sess["expected_count"] = len(expected)
    sess["missing"] = sorted(expected - scanned)
    sess["extra"] = sorted(scanned - expected)
    return safe_doc(sess)


async def complete_verify(session_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    prog = await _verify_progress(session_id)
    if prog.get("owner_entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="Sesi di luar entitas Anda")
    if prog["status"] != "open":
        raise HTTPException(status_code=400, detail="Sesi sudah selesai")
    clean = "clean" if not prog["missing"] and not prog["extra"] else "with_issues"
    matched_rolls = [e["roll_id"] for e in prog["expected"] if e["epc"] in set(prog["scanned_epcs"])]
    # Sesi 14 — klaim saga sesi verifikasi (status open) sesudah validasi, sebelum job/journey ditulis.
    from services import atomic_claim as _saga
    await _saga.claim("rfid_verify_sessions", session_id, "verify_complete", actor="", precondition={"status": "open"})
    try:
        await db.rfid_print_jobs.update_one({"id": prog["print_job_id"]}, {"$set": {
            "status": "verified" if clean == "clean" else "verified_with_issues",
            "verified_at": now_iso(), "updated_at": now_iso()}})
        if matched_rolls:
            await set_journey(matched_rolls, "tag_verified", {"verify_session_id": session_id})
    except Exception as e:
        await _saga.mark_failed("rfid_verify_sessions", session_id, str(e))
        raise
    await db.rfid_verify_sessions.update_one({"id": session_id}, _saga.finish_set({
        "status": "completed", "result": clean, "missing": prog["missing"], "extra": prog["extra"],
        "completed_at": now_iso()}))
    return await _verify_progress(session_id)


async def set_routing(roll_ids: List[str], routing: str, scope_ids: List[str],
                      actor_name: str) -> Dict[str, Any]:
    """Keputusan admin: store (putaway) vs cross_dock (langsung kirim, tetap di transit)."""
    if routing not in ("store", "cross_dock"):
        raise HTTPException(status_code=400, detail="Routing harus 'store' atau 'cross_dock'")
    rolls = await db.inventory_rolls.find(
        {"id": {"$in": roll_ids}, "owner_entity_id": {"$in": scope_ids}},
        {"_id": 0, "id": 1, "journey": 1}).to_list(len(roll_ids) + 5)
    if len(rolls) != len(set(roll_ids)):
        raise HTTPException(status_code=403, detail="Sebagian roll tidak ditemukan / di luar entitas")
    now = now_iso()
    for r in rolls:
        stage = (r.get("journey") or {}).get("stage") or "received_transit"
        if routing == "cross_dock" and stage in ("tag_verified", "cross_dock_ready"):
            stage = "cross_dock_ready"
        elif routing == "store" and stage == "cross_dock_ready":
            stage = "tag_verified"
        await db.inventory_rolls.update_one({"id": r["id"]}, {"$set": {
            "journey.routing": routing, "journey.stage": stage,
            "journey.routing_by": actor_name, "journey.updated_at": now, "updated_at": now}})
    return {"updated": len(rolls), "routing": routing}
