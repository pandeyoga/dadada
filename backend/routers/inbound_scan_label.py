"""FASE SL — Penerimaan berbasis SCAN LABEL SUPPLIER (Scan – Konfirmasi – Tempel – Bin).

Prinsip: manusia hanya mengonfirmasi/mengoreksi PENGUKURAN FISIK; semua IDENTITAS
(nomor roll supplier, lot, kode barang, warna, produk, bin) datang dari scan + master.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pymongo import ReturnDocument

from core_utils import DEFAULT_ENTITY_ID, new_id, now_iso, safe_doc
from db import db
from dependencies import audit, require_permission
from entity_scope import assert_entity_access, entity_ctx, resolve_scope_ids
from schemas_scan_label import (ConfirmMeasureIn, LabelPatternIn, LabelPatternTestIn,
                                PutawayIn, ScanLabelIn, TagRfidIn)
from services import label_decoder_service as ldec

router = APIRouter(prefix="/api")

_LEN_FACTOR = {"meter": 1.0, "m": 1.0, "yard": 0.9144, "yd": 0.9144}


def _to_meter(qty: float, unit: str) -> float:
    return float(qty or 0) * _LEN_FACTOR.get((unit or "meter").lower(), 1.0)


def _from_meter(qty_m: float, unit: str) -> float:
    return float(qty_m or 0) / _LEN_FACTOR.get((unit or "meter").lower(), 1.0)


async def _tolerance_pct(entity_id: str) -> float:
    from services.config_service import get_effective_settings
    s = await get_effective_settings(entity_id or None)
    return float((s.get("receiving", {}) or {}).get("label_variance_tolerance_percent", 2.0) or 0)


async def _load_task(task_id: str, request: Request, perm: str = "update") -> Dict[str, Any]:
    await require_permission(request, "wms", perm)
    task = safe_doc(await db.wms_tasks.find_one({"id": task_id}, {"_id": 0}))
    if not task:
        raise HTTPException(status_code=404, detail="Inbound task tidak ditemukan")
    assert_entity_access(task, "wms_tasks", await entity_ctx(request))
    if task.get("flow_type") != "inbound":
        raise HTTPException(status_code=400, detail="Task ini bukan inbound task")
    return task


def _roll_view(r: Dict[str, Any]) -> Dict[str, Any]:
    unit = r.get("unit") or "meter"
    length = float(r.get("length_initial") or 0)
    length_m = _to_meter(length, unit)
    r["length_m"] = round(length_m, 2)
    r["length_yd"] = round(_from_meter(length_m, "yard"), 2)
    return safe_doc(r)


async def _attach_epc(rolls: List[Dict[str, Any]]) -> None:
    ids = [r.get("rfid_tag_id") for r in rolls if r.get("rfid_tag_id")]
    tags = {t["id"]: t.get("epc", "") for t in await db.rfid_tags.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "epc": 1}).to_list(len(ids) or 1)} if ids else {}
    for r in rolls:
        r["rfid_epc"] = tags.get(r.get("rfid_tag_id") or "", "")


# ═══════════════════════════════════════════════════════════════════════════
# POLA LABEL SUPPLIER (master)
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/suppliers/{supplier_id}/label-pattern")
async def get_label_pattern(supplier_id: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "supplier", "view")
    sup = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0, "label_pattern": 1, "name": 1})
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
    return {"supplier_id": supplier_id, "supplier_name": sup.get("name", ""),
            "pattern": ldec.normalize_pattern(sup.get("label_pattern")),
            "formats": list(ldec.FORMATS), "fields": list(ldec.FIELDS),
            "default_gs1_ai_map": ldec.DEFAULT_GS1_MAP}


@router.put("/suppliers/{supplier_id}/label-pattern")
async def put_label_pattern(supplier_id: str, payload: LabelPatternIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "supplier", "update")
    if not await db.suppliers.find_one({"id": supplier_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
    pattern = ldec.normalize_pattern(payload.model_dump())
    await db.suppliers.update_one({"id": supplier_id},
                                  {"$set": {"label_pattern": pattern, "updated_at": now_iso()}})
    await audit(actor["name"], "supplier_label_pattern_updated", "supplier", supplier_id, pattern)
    return {"supplier_id": supplier_id, "pattern": pattern}


@router.post("/suppliers/label-pattern/test")
async def test_label_pattern(payload: LabelPatternTestIn, request: Request) -> Dict[str, Any]:
    """Uji 'scan contoh' — murni decoder, tidak menulis apa pun."""
    await require_permission(request, "supplier", "view")
    try:
        decoded = ldec.decode(payload.raw, payload.pattern.model_dump() if payload.pattern else None)
    except ldec.LabelDecodeError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "decoded": decoded}


# ═══════════════════════════════════════════════════════════════════════════
# SCAN LABEL → roll `receiving`
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/inbound/tasks/{task_id}/scanned-rolls")
async def list_scanned_rolls(task_id: str, request: Request) -> Dict[str, Any]:
    task = await _load_task(task_id, request, "view")
    rolls = await db.inventory_rolls.find({"grn_task_id": task_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    po = await db.purchase_orders.find_one({"id": task.get("po_id")}, {"_id": 0, "supplier_id": 1, "entity_id": 1}) or {}
    sup = await db.suppliers.find_one({"id": po.get("supplier_id", "")}, {"_id": 0, "label_pattern": 1, "name": 1}) or {}
    wh = await db.warehouses.find_one({"id": task.get("warehouse_id")}, {"_id": 0, "zones": 1}) or {}
    bins = [{"id": b["id"], "code": b.get("code", ""), "rack": rk.get("name", ""), "zone": z.get("name", "")}
            for z in wh.get("zones", []) for rk in z.get("racks", []) for b in rk.get("bins", [])]
    scanned = [r for r in rolls if r.get("status") == "receiving" or r.get("scan_source")]
    await _attach_epc(scanned)
    product = await db.products.find_one({"id": task.get("product_id")}, {"_id": 0, "name": 1, "sku": 1}) or {}
    from services import supplier_item_service as sis
    pattern_items = await sis.label_pattern_candidates(
        supplier_id=po.get("supplier_id", ""), product_id=task.get("product_id", ""),
        entity_id=po.get("entity_id") or task.get("entity_id") or "")
    return {
        "task_id": task_id, "rolls": [_roll_view(r) for r in scanned],
        "product_name": product.get("name", ""), "sku": product.get("sku", ""),
        "count": len(scanned),
        "sum_task_qty": round(sum(float(r.get("declared_task_qty") or 0) if not r.get("measure_confirmed")
                                  else float(r.get("actual_task_qty") or r.get("declared_task_qty") or 0)
                                  for r in scanned), 2),
        "tolerance_pct": await _tolerance_pct(po.get("entity_id") or task.get("entity_id") or ""),
        "label_pattern": ldec.normalize_pattern(sup.get("label_pattern")),
        # FASE SL — pola khusus per Barang Supplier (dicoba lebih dulu saat scan)
        "item_label_patterns": [{"supplier_item_id": it["id"], "supplier_sku": it["supplier_sku"],
                                 "format": (it.get("label_pattern") or {}).get("format", "auto")}
                                for it in pattern_items],
            "supplier_name": sup.get("name", ""), "supplier_id": po.get("supplier_id", ""), "bins": bins,
    }


@router.post("/inbound/tasks/{task_id}/scan-label")
async def scan_label(task_id: str, payload: ScanLabelIn, request: Request) -> Dict[str, Any]:
    """Decode label → cocokkan Supplier Item → validasi PO → roll `receiving` (idempoten)."""
    actor = await require_permission(request, "wms", "update")
    task = await _load_task(task_id, request)
    if task["status"] in ("completed", "cancelled", "qc_pending"):
        raise HTTPException(status_code=400, detail="Task sudah selesai / sedang QC — tidak bisa scan lagi.")
    po = safe_doc(await db.purchase_orders.find_one({"id": task.get("po_id")}, {"_id": 0})) or {}
    supplier_id = po.get("supplier_id", "") or task.get("supplier_id", "")
    sup = safe_doc(await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})) or {}
    product = safe_doc(await db.products.find_one({"id": task["product_id"]}, {"_id": 0})) or {}
    base_unit = product.get("base_unit") or "meter"
    task_unit = task.get("unit") or base_unit
    owner_entity_id = po.get("entity_id") or task.get("entity_id") or DEFAULT_ENTITY_ID

    from services import supplier_item_service as sis
    manual = payload.manual
    if manual:
        decoded = {"supplier_sku": "", "gtin": "", "lot": manual.lot.strip(),
                   "roll_no": manual.supplier_roll_no.strip(), "length": manual.declared_length or None,
                   "length_unit": "meter" if manual.length_unit.lower().startswith("m") else "yard",
                   "weight_kg": manual.declared_weight_kg or None, "color_code": manual.color_code.strip(),
                   "format": "manual", "raw": payload.raw or ""}
        sitem = await sis.get_item(manual.supplier_item_id) if manual.supplier_item_id else None
        if sitem is None:
            sitem = await sis.resolve_for_product(supplier_id=supplier_id, product_id=task["product_id"],
                                                  entity_id=owner_entity_id) or {}
    else:
        # FASE SL — pola per Barang Supplier dicoba lebih dulu (supplier campur-label), lalu pola supplier.
        pattern_items = await sis.label_pattern_candidates(
            supplier_id=supplier_id, product_id=task["product_id"], entity_id=owner_entity_id)
        candidates = [(f"item:{it['supplier_sku']}", it["label_pattern"]) for it in pattern_items]
        candidates.append(("supplier", sup.get("label_pattern")))
        try:
            decoded = ldec.decode_first(payload.raw, candidates)
        except ldec.LabelDecodeError as exc:
            raise HTTPException(status_code=400, detail={"code": "UNDECODABLE", "message": str(exc)}) from exc
        sitem = None
        if decoded.get("supplier_sku"):
            sitem = await sis.lookup(supplier_sku=decoded["supplier_sku"], supplier_id=supplier_id,
                                     entity_id=owner_entity_id)
        if sitem is None and decoded.get("gtin"):
            flt: Dict[str, Any] = {"barcode": decoded["gtin"]}
            if supplier_id:
                flt["supplier_id"] = supplier_id
            sitem = safe_doc(await db.supplier_items.find_one(flt, {"_id": 0}))
        if sitem is None and not decoded.get("supplier_sku") and not decoded.get("gtin") \
                and str(decoded.get("pattern_source", "")).startswith("item:"):
            # Label tanpa kode barang tetapi cocok pola khusus barang → barang tersirat dari polanya.
            sitem = next((it for it in pattern_items
                          if f"item:{it['supplier_sku']}" == decoded["pattern_source"]), None)
            if sitem:
                decoded["supplier_sku"] = sitem["supplier_sku"]
        if sitem is None:
            other = await sis.lookup(supplier_sku=decoded["supplier_sku"], entity_id=owner_entity_id) \
                if decoded.get("supplier_sku") else None
            if other:
                raise HTTPException(status_code=400, detail={
                    "code": "NOT_IN_TASK",
                    "message": (f"Kode '{decoded['supplier_sku']}' adalah barang '{other.get('supplier_item_name') or other.get('sku')}' "
                                f"dari supplier {other.get('supplier_name') or 'lain'} — bukan barang PO ini "
                                f"({task.get('sku')}). Pilih tugas penerimaan yang sesuai atau eskalasi."),
                    "decoded": decoded})
            raise HTTPException(status_code=400, detail={
                "code": "UNMAPPED",
                "message": (f"Barang '{decoded.get('supplier_sku') or decoded.get('gtin') or '?'}' tidak ada di PO / "
                            f"belum dipetakan ke produk kami. Eskalasi ke purchasing untuk memetakan "
                            f"kode supplier ini di master Barang Supplier."),
                "decoded": decoded})
    sitem = sitem or {}
    if sitem and sitem.get("product_id") != task["product_id"]:
        raise HTTPException(status_code=400, detail={
            "code": "NOT_IN_TASK",
            "message": (f"Label ini barang '{sitem.get('supplier_item_name') or sitem.get('supplier_sku')}' "
                        f"({sitem.get('sku')}), bukan barang tugas ini ({task.get('sku')}). "
                        f"Pilih tugas penerimaan yang sesuai atau eskalasi."),
            "decoded": decoded})

    supplier_roll_no = (decoded.get("roll_no") or "").strip()
    if not supplier_roll_no:
        raise HTTPException(status_code=400, detail={
            "code": "NO_ROLL_NO",
            "message": "Label tidak memuat nomor roll supplier. Gunakan 'Label tidak terbaca' dan "
                       "masukkan nomor roll dari label fisik.", "decoded": decoded})
    dup = await db.inventory_rolls.find_one(
        {"supplier_id": supplier_id, "supplier_roll_no": supplier_roll_no}, {"_id": 0, "roll_no": 1, "status": 1})
    if dup:
        raise HTTPException(status_code=409, detail={
            "code": "DUPLICATE", "message": (f"Roll supplier {supplier_roll_no} sudah diterima sebagai "
                                            f"{dup.get('roll_no')} (status {dup.get('status')}).")})

    # ── qty deklarasi (label) → satuan task & base unit ────────────────────
    length_label = float(decoded.get("length") or 0)
    label_unit = decoded.get("length_unit") or "yard"
    weight_kg = float(decoded.get("weight_kg") or 0)
    from services.uom_service import kg_per_base_unit, load_fixed_factors
    factors = await load_fixed_factors()
    kgpb = kg_per_base_unit(product, factors)
    length_m = _to_meter(length_label, label_unit)
    if length_m <= 0 and weight_kg > 0 and kgpb > 0:
        length_m = _to_meter(weight_kg / kgpb, base_unit)
    if length_m <= 0 and weight_kg <= 0:
        conv = float(sitem.get("conv_factor") or 0)
        if conv > 0 and (sitem.get("supplier_uom") or "").lower() in ("roll", "rol", "rll", "gulung"):
            length_m = _to_meter(conv, base_unit)
    if length_m <= 0 and weight_kg <= 0:
        raise HTTPException(status_code=400, detail={
            "code": "NO_QTY", "message": "Label tidak memuat panjang/berat. Gunakan 'Label tidak terbaca' "
                                         "dan isi panjang dari label fisik.", "decoded": decoded})
    length_base = round(_from_meter(length_m, base_unit), 2)
    if weight_kg <= 0 and kgpb > 0:
        weight_kg = round(length_base * kgpb, 3)
    task_qty = round(weight_kg if task_unit.lower() == "kg" else _from_meter(length_m, task_unit), 2)

    # ── pagar PO: qty belum lewat (toleransi kedatangan) ───────────────────
    from services.config_service import get_effective_settings
    settings = await get_effective_settings(owner_entity_id)
    tol_recv = float((settings.get("purchasing", {}) or {}).get("receive_tolerance_percent", 2.0) or 0)
    block_over = bool((settings.get("receiving", {}) or {}).get("block_over_remaining", True))
    expected = float(task.get("expected_qty") or 0)
    new_received = round(float(task.get("received_qty") or 0) + task_qty, 2)
    over = expected > 0 and new_received > expected * (1 + tol_recv / 100)
    if over and block_over:
        raise HTTPException(status_code=400, detail={
            "code": "OVER_PO", "message": (f"Roll ini membuat total {new_received:g} {task_unit} melebihi PO "
                                          f"{expected:g} {task_unit} + toleransi {tol_recv:g}%. Eskalasi ke "
                                          f"manajer bila kiriman memang lebih."), "decoded": decoded})

    from services.roll_service import next_roll_no
    import domain_registry as _dr
    supplier_lot = (decoded.get("lot") or "").strip()
    roll_doc = {
        "id": new_id("roll"), "roll_no": await next_roll_no(),
        "product_id": task["product_id"], "owner_entity_id": owner_entity_id,
        "ownership_type": "internal", "consignor_ref": None,
        "warehouse_id": task["warehouse_id"], "bin_id": None, "bin_code": "",
        "lot": supplier_lot or task.get("lot") or "", "lot_id": "",
        "supplier_lot": supplier_lot, "dye_lot": supplier_lot or task.get("dye_lot") or "",
        "batch": task.get("batch") or "",
        "length_initial": length_base, "length_remaining": length_base, "unit": base_unit,
        "weight_kg": round(weight_kg, 3), "weight_unit": "kg",
        "secondary_measures": {"kg": round(weight_kg, 3)} if weight_kg > 0 else None,
        "grade": sitem.get("expected_grade") or "A", "defects": [],
        **_dr.roll_domain_snapshot(product),
        "status": "receiving", "qc_task_id": None, "tracking_mode": "barcode",
        "earmarked_for": None, "location_type": "warehouse_bin", "reserved_ref": None,
        "unit_cost": None, "base_unit_cost": None, "landed_cost_total": 0.0, "landed_cost_refs": [],
        "acquired": {"via": "inbound", "ref_id": task.get("po_id") or task_id, "date": now_iso()},
        "supplier_id": supplier_id, "supplier_name": po.get("supplier_name") or sup.get("name", ""),
        "po_id": task.get("po_id") or "", "po_number": task.get("po_number", ""),
        "grn_task_id": task_id, "received_date": now_iso(),
        "vendor_bill_id": "", "supplier_invoice_no": "", "rfid_tag_id": None, "is_remnant": False,
        # ── alias supplier (telusur balik dye lot / komplain warna) ───────────
        "supplier_roll_no": supplier_roll_no,
        "supplier_sku": sitem.get("supplier_sku") or decoded.get("supplier_sku") or "",
        "supplier_item_name": sitem.get("supplier_item_name") or "",
        "supplier_color_code": (decoded.get("color_code") or sitem.get("supplier_color_code") or ""),
        "supplier_item_id": sitem.get("id") or "",
        # ── deklarasi label vs aktual ───────────────────────────────────────────
        "declared_length": length_base, "declared_length_label": length_label or None,
        "declared_length_unit": label_unit, "declared_weight_kg": round(weight_kg, 3),
        "declared_task_qty": task_qty, "actual_task_qty": None,
        "measure_confirmed": False, "label_variance": None,
        "scan_source": decoded.get("format", "manual"), "raw_label": decoded.get("raw", ""),
        "manual_override": ({"reason": manual.reason, "note": manual.reason_note, "by": actor["name"],
                             "at": now_iso()} if manual else None),
        "journey": {"stage": "receiving", "routing": "store", "updated_at": now_iso()},
        "created_at": now_iso(), "updated_at": now_iso(),
        "created_by": actor.get("id") or "system", "created_by_name": actor["name"],
    }
    await db.inventory_rolls.insert_one(dict(roll_doc))

    # FASE SL — RFID Auto-Tag: EPC lahir bersama roll (best-effort; gagal → petugas tag manual).
    roll_doc["rfid_epc"] = ""
    if bool((settings.get("receiving", {}) or {}).get("auto_rfid_on_scan", True)):
        try:
            from services import rfid_service as _rfid
            _tag = await _rfid.encode_tag(roll_doc["id"], [owner_entity_id], actor_name=actor["name"])
            roll_doc["rfid_tag_id"], roll_doc["tracking_mode"], roll_doc["rfid_epc"] = _tag["id"], "rfid", _tag["epc"]
        except HTTPException as exc:
            import logging
            logging.getLogger(__name__).warning("Auto-RFID roll %s gagal: %s", roll_doc["roll_no"], exc.detail)

    tol_close = tol_recv
    # INV-ATOMIC-01 — received_qty & qty_rolls_scanned di-$inc (bukan $set nilai yang dibaca
    # tadi) supaya dua pemindai pada satu tugas tidak saling menimpa; status berprasyarat hidup.
    upd: Dict[str, Any] = {
        "updated_at": now_iso(),
        "over_receipt": bool(over), "receive_within_tolerance": not over,
        "receive_mode": "scan_label",
    }
    _inc: Dict[str, Any] = {"received_qty": task_qty, "qty_rolls_scanned": 1}
    if not task.get("supplier_lot") and supplier_lot:
        upd["supplier_lot"] = supplier_lot
    if task["status"] == "waiting_goods":
        upd["status"] = "receiving"
    if expected > 0 and new_received >= expected * (1 - tol_close / 100):
        upd["status"] = "qc_check"
        upd["quantity"] = new_received
    scan_entry = {"id": new_id("scan"), "scan_type": "label", "actual_qty": task_qty,
                  "lot": supplier_lot, "roll_id": roll_doc["id"], "roll_no": roll_doc["roll_no"],
                  "supplier_roll_no": supplier_roll_no, "format": roll_doc["scan_source"],
                  "manual": bool(manual), "actor": actor["name"], "timestamp": now_iso()}
    upd.pop("quantity", None)
    updated = await db.wms_tasks.find_one_and_update(
        {"id": task_id, "status": {"$in": ["waiting_goods", "receiving", "qc_check"]}},
        {"$set": upd, "$inc": _inc, "$push": {"scan_log": scan_entry}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        await db.inventory_rolls.delete_one({"id": roll_doc["id"]})   # kompensasi saga
        raise HTTPException(status_code=409, detail="Tugas penerimaan sudah selesai/berubah — pindaian dibatalkan. Muat ulang.")
    if updated.get("status") == "qc_check" and float(updated.get("quantity") or 0) != float(updated.get("received_qty") or 0):
        await db.wms_tasks.update_one({"id": task_id}, {"$set": {"quantity": updated.get("received_qty")}})
    await audit(actor["name"], "inbound_scan_label", "wms_task", task_id, {
        "roll_no": roll_doc["roll_no"], "supplier_roll_no": supplier_roll_no, "supplier_lot": supplier_lot,
        "task_qty": task_qty, "format": roll_doc["scan_source"], "manual": bool(manual)})
    return {"roll": _roll_view(roll_doc), "task": safe_doc(updated), "decoded": decoded}


@router.post("/inbound/rolls/{roll_id}/confirm-measure")
async def confirm_measure(roll_id: str, payload: ConfirmMeasureIn, request: Request) -> Dict[str, Any]:
    """Hanya panjang/berat AKTUAL & grade; selisih vs deklarasi > toleransi → flag QC."""
    actor = await require_permission(request, "wms", "update")
    roll = safe_doc(await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}))
    if not roll or not roll.get("grn_task_id"):
        raise HTTPException(status_code=404, detail="Roll hasil scan tidak ditemukan")
    task = await _load_task(roll["grn_task_id"], request)
    if roll.get("status") != "receiving":
        raise HTTPException(status_code=400, detail="Roll sudah masuk stok — ukuran dikoreksi lewat penyesuaian stok.")
    if payload.grade and payload.grade not in ("A", "A+", "A1", "A2", "B", "C", "BS"):
        raise HTTPException(status_code=400, detail="Grade tidak dikenal (A, A+, B, C, BS).")
    tol = await _tolerance_pct(roll.get("owner_entity_id") or "")
    base_unit = roll.get("unit") or "meter"
    task_unit = task.get("unit") or base_unit
    decl_len = float(roll.get("declared_length") or 0)
    decl_wt = float(roll.get("declared_weight_kg") or 0)
    act_len = decl_len if payload.actual_length is None else float(payload.actual_length)
    act_wt = decl_wt if payload.actual_weight_kg is None else float(payload.actual_weight_kg)
    if act_len <= 0 and act_wt <= 0:
        raise HTTPException(status_code=400, detail="Panjang atau berat aktual harus lebih dari 0.")

    def _pct(a: float, d: float) -> Optional[float]:
        return None if d <= 0 else round(abs(a - d) / d * 100, 2)

    var_len, var_wt = _pct(act_len, decl_len), _pct(act_wt, decl_wt)
    worst = max([v for v in (var_len, var_wt) if v is not None] or [0.0])
    flagged = worst > tol
    variance = {"length_declared": decl_len, "length_actual": act_len, "length_pct": var_len,
                "weight_declared": decl_wt, "weight_actual": act_wt, "weight_pct": var_wt,
                "tolerance_pct": tol, "flagged": flagged,
                "message": (f"Selisih label vs aktual {worst:g}% > toleransi {tol:g}% — masuk QC."
                            if flagged else "Dalam toleransi."), "confirmed_by": actor["name"],
                "confirmed_at": now_iso()}
    new_task_qty = round(act_wt if task_unit.lower() == "kg" else _from_meter(_to_meter(act_len, base_unit), task_unit), 2)
    prev_task_qty = float(roll.get("actual_task_qty") if roll.get("actual_task_qty") is not None
                          else roll.get("declared_task_qty") or 0)
    upd = {"length_initial": round(act_len, 2), "length_remaining": round(act_len, 2),
           "weight_kg": round(act_wt, 3), "secondary_measures": {"kg": round(act_wt, 3)} if act_wt > 0 else None,
           "grade": payload.grade or roll.get("grade") or "A", "defects": list(payload.defects or []),
           "measure_confirmed": True, "label_variance": variance, "needs_qc": flagged,
           "actual_task_qty": new_task_qty, "updated_at": now_iso()}
    # INV-ATOMIC-01 — CAS: roll wajib masih 'receiving' & ukuran aktual seperti yang dibaca;
    # selisih ke tugas ditulis $inc (bukan $set hasil baca) supaya konfirmasi paralel tak saling timpa.
    updated = await db.inventory_rolls.find_one_and_update(
        {"id": roll_id, "status": "receiving", "actual_task_qty": roll.get("actual_task_qty")},
        {"$set": upd}, projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        raise HTTPException(status_code=409, detail="Roll sudah dikonfirmasi/berubah oleh proses lain. Muat ulang.")
    await _attach_epc([updated])
    delta = round(new_task_qty - prev_task_qty, 2)
    t_upd: Dict[str, Any] = {"updated_at": now_iso()}
    t_inc: Dict[str, Any] = {}
    if delta:
        new_recv = round(float(task.get("received_qty") or 0) + delta, 2)
        t_inc["received_qty"] = delta
        from services.config_service import get_effective_settings
        _s = await get_effective_settings(roll.get("owner_entity_id") or None)
        _tol_recv = float((_s.get("purchasing", {}) or {}).get("receive_tolerance_percent", 2.0) or 0)
        _exp = float(task.get("expected_qty") or 0)
        if _exp > 0 and new_recv >= _exp * (1 - _tol_recv / 100):
            t_upd["status"], t_upd["quantity"] = "qc_check", new_recv
        elif task.get("status") == "qc_check":
            t_upd["status"] = "receiving"
    if flagged:
        t_upd["needs_review"] = True
        t_upd["label_variance_flagged"] = int(task.get("label_variance_flagged") or 0) + 1
    _t_ops: Dict[str, Any] = {"$set": t_upd}
    if t_inc:
        _t_ops["$inc"] = t_inc
    task_after = await db.wms_tasks.find_one_and_update(
        {"id": task["id"], "status": {"$in": ["waiting_goods", "receiving", "qc_check"]}}, _t_ops,
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    await audit(actor["name"], "inbound_confirm_measure", "inventory_roll", roll_id, variance,
                "FASE SL — konfirmasi ukuran aktual vs label supplier")
    return {"roll": _roll_view(updated), "task": safe_doc(task_after)}


@router.post("/inbound/rolls/{roll_id}/putaway")
async def putaway_scanned_roll(roll_id: str, payload: PutawayIn, request: Request) -> Dict[str, Any]:
    """Scan bin tujuan (dari master zona/rak/bin) — bukan ketik."""
    actor = await require_permission(request, "wms", "update")
    roll = safe_doc(await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}))
    if not roll or not roll.get("grn_task_id"):
        raise HTTPException(status_code=404, detail="Roll hasil scan tidak ditemukan")
    task = await _load_task(roll["grn_task_id"], request)
    wh = await db.warehouses.find_one({"id": task["warehouse_id"]}, {"_id": 0}) or {}
    code = (payload.bin_code or "").strip().lower()
    found = None
    for z in wh.get("zones", []):
        for rk in z.get("racks", []):
            for b in rk.get("bins", []):
                if (payload.bin_id and b.get("id") == payload.bin_id) or (code and (b.get("code", "").lower() == code or b.get("id", "").lower() == code)):
                    found = {**b, "zone": z.get("name", ""), "rack": rk.get("name", "")}
    if not found:
        raise HTTPException(status_code=400, detail=(
            f"Bin '{payload.bin_code or payload.bin_id}' tidak ada di master gudang {wh.get('name', task['warehouse_id'])}. "
            f"Scan label bin yang terpasang di rak."))
    updated = await db.inventory_rolls.find_one_and_update(
        {"id": roll_id, "status": "receiving"},   # INV-ATOMIC-01 — CAS: roll masih tahap terima
        {"$set": {"bin_id": found["id"], "bin_code": found.get("code", ""),
                                   "journey.stage": "putaway", "journey.updated_at": now_iso(),
                                   "updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    await _attach_epc([updated])
    if not updated:
        raise HTTPException(status_code=409, detail="Roll sudah bukan tahap penerimaan — tidak bisa dialokasikan bin.")
    await db.wms_tasks.update_one({"id": task["id"]}, {"$set": {"bin_id": found["id"], "updated_at": now_iso()}})
    await audit(actor["name"], "inbound_putaway_bin", "inventory_roll", roll_id,
                {"bin_id": found["id"], "bin_code": found.get("code", "")})
    return {"roll": _roll_view(updated), "bin": found}


@router.post("/inbound/rolls/{roll_id}/tag")
async def tag_scanned_roll(roll_id: str, payload: TagRfidIn, request: Request) -> Dict[str, Any]:
    """Tautkan EPC RFID ke roll hasil scan (EPC sistem, atau EPC yang dibaca handheld/printer)."""
    actor = await require_permission(request, "wms", "scan")
    roll = safe_doc(await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}))
    if not roll or not roll.get("grn_task_id"):
        raise HTTPException(status_code=404, detail="Roll hasil scan tidak ditemukan")
    ctx = await entity_ctx(request)
    from services import rfid_service as _rfid
    tag = await _rfid.encode_tag(roll_id, resolve_scope_ids(ctx, None), payload.epc or None, actor["name"])
    await audit(actor["name"], "rfid_tag_encoded", "rfid_tag", tag["id"],
                {"epc": tag["epc"], "roll_id": roll_id, "source": "inbound_scan_label"})
    updated = safe_doc(await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}))
    updated["rfid_epc"] = tag["epc"]
    return {"roll": _roll_view(updated), "tag": tag}


@router.delete("/inbound/rolls/{roll_id}/scan")
async def undo_scan(roll_id: str, request: Request) -> Dict[str, Any]:
    """Batalkan scan yang salah (hanya roll `receiving`, sebelum GR ditutup)."""
    actor = await require_permission(request, "wms", "update")
    roll = safe_doc(await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}))
    if not roll or roll.get("status") != "receiving":
        raise HTTPException(status_code=400, detail="Hanya roll yang masih 'receiving' yang bisa dibatalkan.")
    task = await _load_task(roll["grn_task_id"], request)
    qty = float(roll.get("actual_task_qty") if roll.get("actual_task_qty") is not None else roll.get("declared_task_qty") or 0)
    # INV-ATOMIC-01 — hapus berprasyarat status (dua "batalkan" bersamaan → satu yang menang
    # dan hanya satu yang mengurangi received_qty lewat $inc).
    _del = await db.inventory_rolls.delete_one({"id": roll_id, "status": "receiving"})
    if _del.deleted_count == 0:
        raise HTTPException(status_code=409, detail="Roll sudah dibatalkan/berubah oleh proses lain.")
    new_recv = max(0.0, round(float(task.get("received_qty") or 0) - qty, 2))
    upd = {"updated_at": now_iso()}
    if task.get("status") == "qc_check" and new_recv < float(task.get("expected_qty") or 0):
        upd["status"] = "receiving"
    t = await db.wms_tasks.find_one_and_update(
        {"status": {"$in": ["waiting_goods", "receiving", "qc_check"]}, "id": task["id"]},
        {"$set": upd, "$inc": {"received_qty": -qty, "qty_rolls_scanned": -1}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if t and (float(t.get("received_qty") or 0) < 0 or int(t.get("qty_rolls_scanned") or 0) < 0):
        await db.wms_tasks.update_one({"id": task["id"]}, {"$set": {
            "received_qty": max(0.0, float(t.get("received_qty") or 0)),
            "qty_rolls_scanned": max(0, int(t.get("qty_rolls_scanned") or 0))}})
    await audit(actor["name"], "inbound_scan_undone", "wms_task", task["id"],
                {"roll_no": roll.get("roll_no"), "supplier_roll_no": roll.get("supplier_roll_no")})
    return {"task": safe_doc(t)}


@router.get("/inbound/scan-label/stats")
async def scan_label_stats(request: Request, supplier_id: str = "") -> List[Dict[str, Any]]:
    """% roll yang labelnya tidak terbaca (manual override) & selisih label vs aktual per supplier."""
    await require_permission(request, "wms", "view")
    match: Dict[str, Any] = {"scan_source": {"$exists": True, "$ne": None}}
    if supplier_id:
        match["supplier_id"] = supplier_id
    rows = await db.inventory_rolls.aggregate([
        {"$match": match},
        {"$group": {"_id": {"supplier_id": "$supplier_id", "supplier_name": "$supplier_name"},
                    "total": {"$sum": 1},
                    "manual": {"$sum": {"$cond": [{"$ifNull": ["$manual_override", False]}, 1, 0]}},
                    "flagged": {"$sum": {"$cond": [{"$eq": ["$label_variance.flagged", True]}, 1, 0]}},
                    "confirmed": {"$sum": {"$cond": [{"$eq": ["$measure_confirmed", True]}, 1, 0]}}}},
        {"$sort": {"total": -1}},
    ]).to_list(200)
    return [{"supplier_id": r["_id"].get("supplier_id", ""), "supplier_name": r["_id"].get("supplier_name", ""),
             "total_rolls": r["total"], "manual_override": r["manual"],
             "manual_pct": round(r["manual"] / r["total"] * 100, 1) if r["total"] else 0,
             "variance_flagged": r["flagged"],
             "variance_pct": round(r["flagged"] / r["total"] * 100, 1) if r["total"] else 0,
             "confirmed": r["confirmed"]} for r in rows]
