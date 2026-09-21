"""RFID router (Fase 5 — SIMULATOR).

Endpoint prefix /api. Perizinan:
- GET (baca)            → wms:view
- encode/retire/scan    → wms:scan  (warehouse/manager/admin)
- device write & seed   → role admin (infra)
"""
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core_utils import safe_doc, new_id, now_iso
from db import db
from dependencies import require_permission, require_role, audit
from entity_scope import entity_ctx, resolve_scope_ids, assert_entity_access
import services.rfid_service as rfid

router = APIRouter(prefix="/api")


# ─── Payloads ────────────────────────────────────────────────────────────────
class EncodePayload(BaseModel):
    roll_id: str
    epc: Optional[str] = None


class AutoEncodePayload(BaseModel):
    warehouse_id: Optional[str] = None


class DevicePayload(BaseModel):
    code: Optional[str] = None
    name: str
    type: str                      # gate | fixed_reader | handheld
    direction: Optional[str] = None  # in | out (gate saja)
    warehouse_id: str
    location: Optional[str] = None
    status: Optional[str] = None


class DevicePatch(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    direction: Optional[str] = None
    type: Optional[str] = None


class GateSimPayload(BaseModel):
    device_id: str
    roll_id: str


class ReaderScanPayload(BaseModel):
    device_id: str


class PrintJobPayload(BaseModel):
    roll_ids: list[str]
    kind: str = "rfid_tag"      # rfid_tag (encode EPC) | qr_label (QR nomor roll, tanpa encode)
    source: str = ""


class RollScanPayload(BaseModel):
    code: str
    warehouse_id: Optional[str] = None
    bin_id: Optional[str] = None
    scanned_at: Optional[str] = None   # diisi HP saat offline (waktu pindai asli)


class VerifyScanPayload(BaseModel):
    epcs: list[str]


class RoutingPayload(BaseModel):
    roll_ids: list[str]
    routing: str  # store | cross_dock


# ─── Summary ─────────────────────────────────────────────────────────────────
@router.get("/rfid/summary")
async def get_summary(request: Request, warehouse_id: Optional[str] = None,
                      entity_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, entity_id)
    return await rfid.rfid_summary(scope, warehouse_id)


# ─── Tags ────────────────────────────────────────────────────────────────────
@router.get("/rfid/tags")
async def get_tags(request: Request, warehouse_id: Optional[str] = None,
                   status: Optional[str] = None, entity_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, entity_id)
    tags = await rfid.list_tags(scope, warehouse_id, status)
    return {"count": len(tags), "tags": tags}


@router.get("/rfid/lookup")
async def lookup_code(request: Request, code: str = Query(..., min_length=1),
                      record: bool = Query(True), warehouse_id: Optional[str] = Query(None),
                      bin_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Pindai label (QR = nomor roll) ATAU tag EPC → satu roll. Untuk HP gudang tanpa RFID.
    `record=true` (bawaan) mencatat jejak pindai ke `roll_scans` (append-only) + `last_scan` di roll."""
    actor = await require_permission(request, "wms", "view")
    code = code.strip()
    tag = await db.rfid_tags.find_one({"epc": code}, {"_id": 0})
    roll = await db.inventory_rolls.find_one({"id": tag["roll_id"]}, {"_id": 0}) if tag else None
    via = "rfid" if roll else "label"
    if not roll:
        roll = await db.inventory_rolls.find_one({"$or": [{"roll_no": code}, {"id": code}]}, {"_id": 0})
    if not roll:
        raise HTTPException(status_code=404, detail={"code": "CODE_UNKNOWN", "message": "Kode tidak dikenal (bukan EPC tag maupun nomor roll)."})
    ctx = await entity_ctx(request)
    assert_entity_access({"entity_id": roll.get("owner_entity_id")}, "inventory_rolls", ctx)
    product = await db.products.find_one({"id": roll.get("product_id")}, {"_id": 0, "name": 1, "sku": 1})
    # Sesi 11 — pindai → aksi: tugas WMS terbuka yang menyentuh roll ini (ambil / terima / potong).
    ors: list = [{"roll_id": roll["id"]}, {"suggested_roll_id": roll["id"]}, {"roll_ids": roll["id"]}, {"roll_id": roll.get("roll_no")}]
    ref = roll.get("reserved_ref") or roll.get("earmarked_for") or {}
    if isinstance(ref, dict) and ref.get("id"):
        # roll dicadangkan untuk SO/transfer → tugas ambil (outbound) atas dokumen itu & produk yang sama
        ors.append({"order_id": ref["id"], "product_id": roll.get("product_id")})
        ors.append({"transfer_id": ref["id"], "product_id": roll.get("product_id")})
    open_tasks = await db.wms_tasks.find(
        {"status": {"$nin": ["completed", "shipped", "dispatched", "cancelled", "done"]}, "$or": ors},
        {"_id": 0, "id": 1, "flow_type": 1, "status": 1, "product_name": 1, "product_id": 1, "customer_name": 1,
         "order_number": 1, "po_number": 1, "task_subtype": 1, "quantity": 1, "unit": 1}).sort("created_at", -1).to_list(5)
    last_scan = roll.get("last_scan")
    if record:
        scan = {"id": new_id("rscan"), "roll_id": roll["id"], "roll_no": roll.get("roll_no"), "code": code, "via": via,
                "owner_entity_id": roll.get("owner_entity_id"),
                "by": actor.get("name", ""), "by_user_id": actor.get("id"), "warehouse_id": warehouse_id or roll.get("warehouse_id"),
                "bin_id": (bin_id or "").strip() or None,
                "roll_warehouse_id": roll.get("warehouse_id"), "roll_status": roll.get("status"), "at": now_iso()}
        await db.roll_scans.insert_one(dict(scan))
        last_scan = {k: scan[k] for k in ("at", "by", "via", "warehouse_id", "bin_id")}
        await db.inventory_rolls.update_one({"id": roll["id"]}, {"$set": {"last_scan": last_scan}})
    return {"via": via, "roll": safe_doc(roll), "product_name": (product or {}).get("name"), "sku": (product or {}).get("sku"),
            "tagged": bool(roll.get("rfid_tag_id")), "open_tasks": open_tasks, "last_scan": last_scan}


@router.post("/rfid/roll-scans")
async def post_roll_scan(payload: RollScanPayload, request: Request) -> Dict[str, Any]:
    """Catat jejak pindai (dipakai antrean offline HP; online memakai GET /rfid/lookup)."""
    actor = await require_permission(request, "wms", "view")
    code = payload.code.strip()
    roll = await db.inventory_rolls.find_one({"$or": [{"roll_no": code}, {"id": code}]}, {"_id": 0})
    via = "label"
    if not roll:
        tag = await db.rfid_tags.find_one({"epc": code.upper(), "status": "active"}, {"_id": 0})
        roll = await db.inventory_rolls.find_one({"id": tag["roll_id"]}, {"_id": 0}) if tag else None
        via = "rfid"
    if not roll:
        raise HTTPException(status_code=404, detail={"code": "CODE_UNKNOWN", "message": f"Kode '{code}' tidak dikenal"})
    ctx = await entity_ctx(request)
    assert_entity_access({"entity_id": roll.get("owner_entity_id")}, "inventory_rolls", ctx)
    if payload.warehouse_id:
        from services import warehouse_scope_service as whscope
        # E4.1 — pindai di gudang khusus badan usaha lain tidak boleh dicatat sebagai lokasi
        await whscope.assert_usable(payload.warehouse_id, ctx.active_entity_id, action="mencatat pindai roll di gudang ini")
    at = payload.scanned_at or now_iso()
    scan = {"id": new_id("rscan"), "roll_id": roll["id"], "roll_no": roll.get("roll_no"), "code": code, "via": via,
            "owner_entity_id": roll.get("owner_entity_id"), "by": actor.get("name", ""), "by_user_id": actor.get("id"),
            "warehouse_id": payload.warehouse_id or roll.get("warehouse_id"), "bin_id": (payload.bin_id or "").strip() or None,
            "roll_warehouse_id": roll.get("warehouse_id"), "roll_status": roll.get("status"), "at": at, "offline": bool(payload.scanned_at)}
    await db.roll_scans.insert_one(dict(scan))
    last = {k: scan[k] for k in ("at", "by", "via", "warehouse_id", "bin_id")}
    # last_scan hanya maju (pindai offline lama tidak menimpa pindai yang lebih baru)
    await db.inventory_rolls.update_one({"id": roll["id"], "$or": [{"last_scan": None}, {"last_scan.at": {"$lt": at}}]}, {"$set": {"last_scan": last}})
    return {"ok": True, "roll_no": roll.get("roll_no"), "scan_id": scan["id"], "message": f"Pindai {roll.get('roll_no')} tercatat"}


@router.get("/rfid/roll-scans/{roll_id}")
async def get_roll_scans(roll_id: str, request: Request, limit: int = Query(15, ge=1, le=100)) -> Dict[str, Any]:
    """Riwayat pindai QR/RFID satu roll dari HP gudang (terbaru dulu)."""
    await require_permission(request, "wms", "view")
    roll = await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0, "owner_entity_id": 1, "last_scan": 1})
    if not roll:
        raise HTTPException(status_code=404, detail="Roll tidak ditemukan")
    assert_entity_access({"entity_id": roll.get("owner_entity_id")}, "inventory_rolls", await entity_ctx(request))
    rows = await db.roll_scans.find({"roll_id": roll_id}, {"_id": 0}).sort("at", -1).to_list(limit)
    return {"count": len(rows), "scans": rows, "last_scan": roll.get("last_scan")}


@router.get("/rfid/printer-status")
async def printer_status(request: Request, warehouse_id: Optional[str] = None) -> Dict[str, Any]:
    """Status printer label per gudang: online/offline (heartbeat ≤ 5 menit), label menunggu, job tertua."""
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    q_dev: Dict[str, Any] = {"type": "printer"}
    if warehouse_id:
        q_dev["warehouse_id"] = warehouse_id
    devices = await db.rfid_devices.find(q_dev, {"_id": 0, "api_key": 0}).to_list(200)
    q_job: Dict[str, Any] = {"status": "queued"}
    if scope:
        q_job["owner_entity_id"] = {"$in": scope}
    if warehouse_id:
        q_job["warehouse_id"] = warehouse_id
    queued = await db.rfid_print_jobs.find(q_job, {"_id": 0, "id": 1, "job_number": 1, "kind": 1, "item_count": 1,
                                                   "warehouse_id": 1, "warehouse_name": 1, "created_at": 1}).sort("created_at", 1).to_list(500)
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=5)).isoformat()
    by_wh: Dict[str, Dict[str, Any]] = {}
    for d in devices:
        w = by_wh.setdefault(d.get("warehouse_id") or "-", {"warehouse_id": d.get("warehouse_id"), "printers": [], "queued_jobs": 0, "queued_labels": 0, "oldest_queued_at": None})
        hb = d.get("last_heartbeat") or ""
        w["printers"].append({"id": d["id"], "code": d.get("code"), "name": d.get("name"), "last_heartbeat": hb or None,
                              "online": bool(hb) and hb >= cutoff})
    for j in queued:
        w = by_wh.setdefault(j.get("warehouse_id") or "-", {"warehouse_id": j.get("warehouse_id"), "printers": [], "queued_jobs": 0, "queued_labels": 0, "oldest_queued_at": None})
        w["queued_jobs"] += 1
        w["queued_labels"] += int(j.get("item_count") or 0)
        if not w["oldest_queued_at"] or j["created_at"] < w["oldest_queued_at"]:
            w["oldest_queued_at"] = j["created_at"]
    names = {x["id"]: x.get("name") for x in await db.warehouses.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(200)}
    rows = []
    for w in by_wh.values():
        online = any(p["online"] for p in w["printers"])
        w["warehouse_name"] = names.get(w["warehouse_id"], w["warehouse_id"])
        w["online_printers"] = sum(1 for p in w["printers"] if p["online"])
        w["stuck"] = w["queued_jobs"] > 0 and not online       # label menunggu tapi tak ada printer hidup
        rows.append(w)
    rows.sort(key=lambda r: (not r["stuck"], -r["queued_labels"]))
    return {"count": len(rows), "warehouses": rows, "total_queued_labels": sum(r["queued_labels"] for r in rows),
            "stuck_warehouses": sum(1 for r in rows if r["stuck"]), "as_of": now_iso()}


@router.get("/rfid/labels")
async def labels_for_document(request: Request, po_id: Optional[str] = None, lot_id: Optional[str] = None,
                              task_id: Optional[str] = None) -> Dict[str, Any]:
    """Cetak massal label QR: semua roll satu PO / lot / tugas penerimaan (hanya-baca)."""
    await require_permission(request, "wms", "view")
    if not (po_id or lot_id or task_id):
        raise HTTPException(status_code=400, detail="Sebutkan po_id, lot_id, atau task_id")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    q: Dict[str, Any] = {"owner_entity_id": {"$in": scope}} if scope else {}
    if po_id:
        q["po_id"] = po_id
    if lot_id:
        q["lot_id"] = lot_id
    if task_id:
        q["$or"] = [{"acquired.ref_id": task_id}, {"inbound_task_id": task_id}, {"qc_task_id": task_id}]
    rolls = await db.inventory_rolls.find(q, {"_id": 0, "id": 1, "roll_no": 1, "product_id": 1, "length_initial": 1, "length_remaining": 1,
                                             "unit": 1, "grade": 1, "lot": 1, "supplier_lot": 1, "dye_lot": 1, "warehouse_id": 1, "status": 1}).sort("roll_no", 1).to_list(500)
    pids = list({r.get("product_id") for r in rolls})
    names = {p["id"]: p.get("name") for p in await db.products.find({"id": {"$in": pids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(pids) or 1)}
    po = await db.purchase_orders.find_one({"id": po_id}, {"_id": 0, "po_number": 1}) if po_id else None
    for r in rolls:
        r["product_name"] = names.get(r.get("product_id"))
        r["length"] = r.get("length_remaining", r.get("length_initial"))
        r["lot"] = r.get("lot") or r.get("supplier_lot")
    return {"count": len(rolls), "rolls": rolls, "po_number": (po or {}).get("po_number")}


@router.get("/rfid/untagged-rolls")
async def get_untagged(request: Request, warehouse_id: Optional[str] = None,
                       entity_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, entity_id)
    rolls = await rfid.untagged_rolls(scope, warehouse_id)
    return {"count": len(rolls), "rolls": rolls}


@router.post("/rfid/tags/encode")
async def post_encode(payload: EncodePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    tag = await rfid.encode_tag(payload.roll_id, scope, payload.epc, actor["name"])
    await audit(actor["name"], "rfid_tag_encoded", "rfid_tag", tag["id"],
                {"epc": tag["epc"], "roll_id": payload.roll_id})
    return tag


@router.post("/rfid/tags/auto-encode")
async def post_auto_encode(payload: AutoEncodePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    res = await rfid.auto_encode(scope, payload.warehouse_id, actor["name"])
    await audit(actor["name"], "rfid_auto_encode", "rfid_tag", "batch", {"encoded": res["encoded"]})
    return res


@router.delete("/rfid/tags/{tag_id}")
async def delete_tag(tag_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    res = await rfid.retire_tag(tag_id, scope)
    await audit(actor["name"], "rfid_tag_retired", "rfid_tag", tag_id, {})
    return res


# ─── Devices ─────────────────────────────────────────────────────────────────
@router.get("/rfid/devices")
async def get_devices(request: Request, warehouse_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    devs = await rfid.list_devices(warehouse_id)
    return {"count": len(devs), "devices": devs}


@router.post("/rfid/devices")
async def post_device(payload: DevicePayload, request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    dev = await rfid.create_device(payload.model_dump(), actor["name"])
    await audit(actor["name"], "rfid_device_created", "rfid_device", dev["id"], {"code": dev["code"]})
    return dev


@router.patch("/rfid/devices/{device_id}")
async def patch_device(device_id: str, payload: DevicePatch, request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    dev = await rfid.update_device(device_id, payload.model_dump(exclude_none=True))
    await audit(actor["name"], "rfid_device_updated", "rfid_device", device_id, {})
    return dev


@router.delete("/rfid/devices/{device_id}")
async def del_device(device_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    res = await rfid.delete_device(device_id)
    await audit(actor["name"], "rfid_device_deleted", "rfid_device", device_id, {})
    return res


@router.post("/rfid/devices/seed-defaults")
async def post_seed_devices(request: Request) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    res = await rfid.seed_default_devices(actor["name"])
    await audit(actor["name"], "rfid_devices_seeded", "rfid_device", "batch", {"created": res["created"]})
    return res


# ─── Reads / Gate / Scan ─────────────────────────────────────────────────────
@router.get("/rfid/reads")
async def get_reads(request: Request, device_id: Optional[str] = None, result: Optional[str] = None,
                    read_type: Optional[str] = None, warehouse_id: Optional[str] = None,
                    limit: int = 100) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    reads = await rfid.list_reads(device_id, result, read_type, warehouse_id, min(limit, 300))
    return {"count": len(reads), "reads": reads}


@router.post("/rfid/gate/simulate")
async def post_gate_simulate(payload: GateSimPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    read = await rfid.gate_simulate(payload.device_id, payload.roll_id, scope)
    if read.get("result") == "red":
        await audit(actor["name"], "rfid_gate_alert", "rfid_read", read["id"],
                    {"reason": read.get("reason"), "roll_id": payload.roll_id})
    return read


@router.post("/rfid/reader/scan")
async def post_reader_scan(payload: ReaderScanPayload, request: Request) -> Dict[str, Any]:
    await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, None)
    return await rfid.reader_scan(payload.device_id, scope)


# ─── Locations ───────────────────────────────────────────────────────────────
@router.get("/rfid/locations")
async def get_locations(request: Request, warehouse_id: Optional[str] = None,
                        entity_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    scope = resolve_scope_ids(ctx, entity_id)
    items = await rfid.rfid_locations(scope, warehouse_id)
    return {"count": len(items), "items": items}


# ─── FASE R1 — Print Jobs & Verifikasi ───────────────────────────────────────
@router.get("/rfid/print-jobs")
async def get_print_jobs(request: Request, warehouse_id: Optional[str] = None,
                         status: Optional[str] = None, entity_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    jobs = await rps.list_print_jobs(resolve_scope_ids(ctx, entity_id), warehouse_id, status)
    return {"count": len(jobs), "jobs": jobs}


@router.post("/rfid/print-jobs")
async def post_print_job(payload: PrintJobPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    if payload.kind == "qr_label":
        job = await rps.create_qr_label_job(payload.roll_ids, resolve_scope_ids(ctx, None), actor["name"], source=payload.source)
    else:
        job = await rps.create_print_job(payload.roll_ids, resolve_scope_ids(ctx, None), actor["name"])
    await audit(actor["name"], "rfid_print_job_created", "rfid_print_job", job["id"],
                {"job_number": job["job_number"], "items": job["item_count"], "kind": job.get("kind")})
    return job


@router.get("/rfid/print-jobs/{job_id}")
async def get_print_job(job_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    return await rps.get_print_job(job_id, resolve_scope_ids(ctx, None))


@router.get("/rfid/print-jobs/{job_id}/zpl")
async def get_print_job_zpl(job_id: str, request: Request):
    await require_permission(request, "wms", "view")
    ctx = await entity_ctx(request)
    from fastapi.responses import PlainTextResponse
    from services import rfid_print_service as rps
    job = await rps.get_print_job(job_id, resolve_scope_ids(ctx, None))
    return PlainTextResponse(rps.job_zpl(job), headers={
        "Content-Disposition": f"attachment; filename={job.get('job_number', job_id)}.zpl"})


@router.post("/rfid/print-jobs/{job_id}/mark-printed")
async def post_mark_printed(job_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    job = await rps.mark_printed(job_id, resolve_scope_ids(ctx, None))
    await audit(actor["name"], "rfid_print_job_printed", "rfid_print_job", job_id, {})
    return job


@router.post("/rfid/print-jobs/{job_id}/verify/start")
async def post_verify_start(job_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    return await rps.start_verify(job_id, resolve_scope_ids(ctx, None), actor["name"])


@router.post("/rfid/verify-sessions/{session_id}/scan")
async def post_verify_scan(session_id: str, payload: VerifyScanPayload, request: Request) -> Dict[str, Any]:
    await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    return await rps.scan_verify(session_id, payload.epcs, resolve_scope_ids(ctx, None))


@router.post("/rfid/verify-sessions/{session_id}/complete")
async def post_verify_complete(session_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    sess = await rps.complete_verify(session_id, resolve_scope_ids(ctx, None))
    await audit(actor["name"], "rfid_verify_completed", "rfid_verify_session", session_id,
                {"result": sess.get("result"), "missing": len(sess.get("missing", [])),
                 "extra": len(sess.get("extra", []))})
    return sess


@router.post("/rfid/rolls/set-routing")
async def post_set_routing(payload: RoutingPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    ctx = await entity_ctx(request)
    from services import rfid_print_service as rps
    res = await rps.set_routing(payload.roll_ids, payload.routing,
                                resolve_scope_ids(ctx, None), actor["name"])
    await audit(actor["name"], "roll_routing_set", "inventory_roll", "bulk",
                {"routing": payload.routing, "rolls": len(payload.roll_ids)})
    return res


# ─── FASE R3 — Device Ingest API (middleware Kotlin / Chainway) ──────────────
class IngestPayload(BaseModel):
    epcs: list[str]


@router.post("/rfid/devices/{device_id}/api-key")
async def post_device_api_key(device_id: str, request: Request,
                              regenerate: bool = False) -> Dict[str, Any]:
    actor = await require_role(request, ["admin"])
    from services import rfid_ingest_service as ing
    res = await ing.ensure_api_key(device_id, regenerate)
    await audit(actor["name"], "rfid_device_key_issued", "rfid_device", device_id,
                {"regenerate": regenerate})
    return res


@router.post("/rfid/ingest")
async def post_ingest(payload: IngestPayload, request: Request) -> Dict[str, Any]:
    """Device fisik (gate/handheld) kirim batch EPC. Auth: header X-Device-Key."""
    from services import rfid_ingest_service as ing
    device = await ing.authenticate(request.headers.get("X-Device-Key"))
    return await ing.ingest(device, payload.epcs)


@router.post("/rfid/heartbeat")
async def post_heartbeat(request: Request) -> Dict[str, Any]:
    from services import rfid_ingest_service as ing
    device = await ing.authenticate(request.headers.get("X-Device-Key"))
    return await ing.heartbeat(device)


@router.get("/rfid/device-jobs/pending")
async def get_device_jobs(request: Request) -> Dict[str, Any]:
    """Printer RFID (middleware) menarik antrean ZPL. Auth: X-Device-Key."""
    from services import rfid_ingest_service as ing
    device = await ing.authenticate(request.headers.get("X-Device-Key"))
    return await ing.pending_jobs_for_device(device)


@router.post("/rfid/device-jobs/{job_id}/ack")
async def post_device_job_ack(job_id: str, request: Request) -> Dict[str, Any]:
    from services import rfid_ingest_service as ing
    device = await ing.authenticate(request.headers.get("X-Device-Key"))
    return await ing.ack_job_printed(device, job_id)


# ─── FASE R6 — Insiden (alarm gate merah), shrinkage, kesehatan device ───────
class IncidentNotePayload(BaseModel):
    note: str = ""


@router.get("/rfid/incidents")
async def get_incidents(request: Request, status: Optional[str] = None,
                        warehouse_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    from services import rfid_incident_service as inc
    rows = await inc.list_incidents(status, warehouse_id, limit)
    return {"count": len(rows), "incidents": rows}


@router.post("/rfid/incidents/{incident_id}/acknowledge")
async def post_incident_ack(incident_id: str, payload: IncidentNotePayload,
                            request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    from services import rfid_incident_service as inc
    row = await inc.acknowledge(incident_id, actor["name"], payload.note)
    await audit(actor["name"], "rfid_incident_ack", "rfid_incident", incident_id, {})
    return row


@router.post("/rfid/incidents/{incident_id}/resolve")
async def post_incident_resolve(incident_id: str, payload: IncidentNotePayload,
                                request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "update")
    from services import rfid_incident_service as inc
    row = await inc.resolve(incident_id, actor["name"], payload.note)
    await audit(actor["name"], "rfid_incident_resolved", "rfid_incident", incident_id, {})
    return row


@router.get("/rfid/shrinkage-report")
async def get_shrinkage(request: Request, days: int = 30) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    from services import rfid_incident_service as inc
    return await inc.shrinkage_report(days)


@router.get("/rfid/device-health")
async def get_device_health(request: Request) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    from services import rfid_incident_service as inc
    return await inc.device_health()


# ─── CYCLE COUNT RFID — stock opname kilat via sweep handheld ────────────────
class CycleCountStartPayload(BaseModel):
    warehouse_id: str


@router.post("/rfid/cycle-count/start")
async def post_cc_start(payload: CycleCountStartPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    ctx = await entity_ctx(request)
    from services import cycle_count_service as cc
    from services import warehouse_scope_service as whscope
    # E4.1 — opname RFID di gudang khusus badan usaha lain = menghitung barang orang.
    await whscope.assert_usable(payload.warehouse_id, ctx.active_entity_id,
                                action="melakukan stock opname RFID di sini")
    return await cc.start(payload.warehouse_id, resolve_scope_ids(ctx, None), actor["name"])


@router.post("/rfid/cycle-count/{session_id}/complete")
async def post_cc_complete(session_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "wms", "scan")
    from services import cycle_count_service as cc
    res = await cc.complete(session_id, actor["name"])
    await audit(actor["name"], "rfid_cycle_count_completed", "rfid_cycle_count", res["id"],
                {"cc_number": res["cc_number"], "accuracy": res["accuracy_pct"]})
    return res


@router.get("/rfid/cycle-counts")
async def get_cc_list(request: Request, warehouse_id: Optional[str] = None) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    from services import cycle_count_service as cc
    rows = await cc.list_counts(warehouse_id)
    return {"count": len(rows), "counts": rows}


@router.get("/rfid/cycle-counts/{cc_id}")
async def get_cc_detail(cc_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "wms", "view")
    from services import cycle_count_service as cc
    return await cc.get_count(cc_id)
