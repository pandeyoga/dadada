"""§3-C Jual Sampel — SATU alur dengan pesanan roll (keputusan pemilik 2026-09-16).

Baris SO ber-`is_sample=true`: harga dari master harga sampel per INDUK produk (fallback
harga daftar) atau harga manual sales; TIDAK direservasi FEFO saat checkout — gudang
menerima tugas outbound bersubtipe `sample_cut` (permintaan potong) yang dipenuhi dengan
memindai roll induk (RFID/QR), memotong, dan mencatat panjang aktual. Potongan lahir
sebagai roll anak ber-`reserved_ref` SO sehingga packing → staging → dispatch → delivered
berjalan identik dengan baris roll biasa.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pymongo import ReturnDocument

from core_utils import new_id, now_iso, safe_doc
from db import db
from services import atomic_claim as _saga
from services.roll_service import insert_child_roll, rebuild_balance

REMNANT_THRESHOLD = 2.0   # sisa induk < 2 satuan → ditandai is_remnant

# REVISI SAMPEL (klien 17 Sep): woven maks 5 yard · knitting maks 2 kg per baris sampel.
SAMPLE_LIMITS = {"woven": {"max_qty": 5.0, "unit": "yard", "label": "woven"},
                 "knit": {"max_qty": 2.0, "unit": "kg", "label": "knitting"}}
SAMPLE_BILLINGS = ("free", "paid")
SAMPLE_PAYMENT_APPROVERS = ("finance", "sample_admin", "manager", "admin")


def sample_limit_for(product: Dict[str, Any]) -> Dict[str, Any]:
    ft = str(product.get("fabric_type") or "woven").strip().lower()
    rule = SAMPLE_LIMITS.get(ft) or SAMPLE_LIMITS["woven"]
    return {"fabric_type": ft, "fabric_label": rule["label"], "max_qty": rule["max_qty"],
            "limit_unit": rule["unit"], "base_unit": product.get("base_unit") or "yard"}


def assert_sample_qty(product: Dict[str, Any], base_qty: float) -> None:
    lim = sample_limit_for(product)
    if base_qty <= 0:
        raise HTTPException(status_code=400, detail=f"Sampel {product.get('name')}: panjang/berat harus > 0.")
    if base_qty > lim["max_qty"] + 0.0001:
        raise HTTPException(status_code=400, detail={
            "code": "SAMPLE_LIMIT", "product_id": product.get("id"), "max_qty": lim["max_qty"],
            "message": f"Sampel {product.get('name')}: maks {lim['max_qty']:g} {lim['limit_unit']} untuk kain {lim['fabric_label']} (diminta {base_qty:g} {lim['base_unit']})."})


async def sample_price_for(product: Dict[str, Any]) -> Dict[str, Any]:
    master = await db.sample_price_master.find_one({"template_id": product.get("template_id")}, {"_id": 0}) if product.get("template_id") else None
    if master and float(master.get("price_per_unit") or 0) > 0:
        return {"price_per_unit": float(master["price_per_unit"]), "source": "master_sampel", "unit": product.get("base_unit") or "yard"}
    return {"price_per_unit": float(product.get("price") or 0), "source": "harga_daftar", "unit": product.get("base_unit") or "yard"}


async def suggest_roll(product_id: str, length: float, entity_ids: List[str]) -> Optional[Dict[str, Any]]:
    """FIFO: roll available tertua yang cukup panjang (sisa ≥ panjang)."""
    q: Dict[str, Any] = {"product_id": product_id, "status": "available", "length_remaining": {"$gte": length}}
    if entity_ids:
        q["owner_entity_id"] = {"$in": entity_ids}
    return await db.inventory_rolls.find_one(q, {"_id": 0}, sort=[("created_at", 1)])


async def resolve_sample_price(product: Dict[str, Any], manual_price: Optional[float]) -> Dict[str, Any]:
    """Harga per satuan dasar untuk baris sampel: manual sales (>0) menang, lalu master, lalu daftar."""
    if manual_price is not None and float(manual_price) > 0:
        return {"price_per_unit": round(float(manual_price), 2), "source": "manual_sampel", "unit": product.get("base_unit") or "yard"}
    return await sample_price_for(product)


async def annotate_sample_line(item: Dict[str, Any], entity_id: str) -> None:
    """Tandai baris SO sebagai permintaan potong: tanpa reservasi, saran roll FIFO dicatat."""
    sug = await suggest_roll(item["product_id"], float(item.get("base_quantity") or 0), [entity_id] if entity_id else [])
    item.update({
        "is_sample": True, "fulfillment_mode": "sample_cut",
        "reserved_qty": 0.0, "backorder_qty": 0.0, "sample_cut_status": "requested",
        "suggested_roll_id": (sug or {}).get("id"), "suggested_roll_no": (sug or {}).get("roll_no"),
        "suggested_warehouse_id": (sug or {}).get("warehouse_id"),
    })


async def _fallback_warehouse(product_id: str, entity_id: str) -> Optional[str]:
    any_roll = await db.inventory_rolls.find_one(
        {"product_id": product_id, "owner_entity_id": entity_id, "status": "available"}, {"_id": 0, "warehouse_id": 1})
    if any_roll:
        return any_roll.get("warehouse_id")
    wh = await db.warehouses.find_one({}, {"_id": 0, "id": 1})
    return (wh or {}).get("id")


async def create_sample_cut_tasks(order: Dict[str, Any], actor_name: str, init_status: str, stages: List[str],
                                  warehouses: Dict[str, Any], method: str, hold_until: str) -> List[Dict[str, Any]]:
    """Tugas outbound bersubtipe `sample_cut` per baris sampel (dipanggil saat SO confirmed)."""
    created: List[Dict[str, Any]] = []
    for item in order.get("items", []):
        if not item.get("is_sample"):
            continue
        wid = item.get("suggested_warehouse_id") or await _fallback_warehouse(item["product_id"], order.get("entity_id", ""))
        wh = warehouses.get(wid, {})
        now = now_iso()
        task = {
            "id": new_id("wms"), "entity_id": order.get("entity_id"),
            "flow_type": "outbound", "source_type": "sales_order", "task_subtype": "sample_cut",
            "order_type": order.get("order_type") or "regular", "sample_billing": order.get("sample_billing") or "",
            "order_id": order["id"], "order_number": order["number"], "customer_name": order.get("customer_name"),
            "allocation_id": None, "line_product_id": item["product_id"],
            "product_id": item["product_id"], "product_name": item.get("product_name", ""), "sku": item.get("sku", ""),
            "quantity": round(float(item.get("base_quantity") or item.get("quantity") or 0), 2),
            "picked_qty": 0.0, "shipped_qty": 0.0, "unit": item.get("base_unit") or item.get("unit") or "meter",
            "warehouse_id": wid, "warehouse_name": wh.get("name", ""), "warehouse_city": wh.get("city", ""),
            "suggested_roll_id": item.get("suggested_roll_id"), "suggested_roll_no": item.get("suggested_roll_no"),
            "bin_id": "", "batch": "", "lot": "", "roll_id": "",
            "status": init_status, "stages": stages, "scan_log": [],
            "fulfillment_method": method, "hold_until": hold_until,
            "created_by": actor_name, "created_at": now, "updated_at": now,
        }
        await db.wms_tasks.insert_one(task)
        from services import doc_refs_service as _refs
        await _refs.safe_link(("picking_task", task["id"]), ("sales_order", order["id"]), "parent", note="permintaan potong sampel untuk SO")
        created.append(safe_doc(task))
    return created


async def _resolve_roll(product_id: str, sku: str, take: float, unit: str, roll_id: str, epc: str,
                        entity_id: str = "") -> Dict[str, Any]:
    if epc and not roll_id:
        tag = await db.rfid_tags.find_one({"epc": epc.strip()}, {"_id": 0})
        if tag:
            roll_id = tag.get("roll_id")
        else:   # label QR berisi NOMOR ROLL (tanpa RFID) → cari roll_no
            by_no = await db.inventory_rolls.find_one({"roll_no": epc.strip()}, {"_id": 0, "id": 1})
            if not by_no:
                raise HTTPException(status_code=404, detail={"code": "TAG_UNKNOWN", "message": "Kode tidak dikenal (bukan EPC tag maupun nomor roll) — periksa label atau pilih roll manual."})
            roll_id = by_no["id"]
    roll = await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0}) if roll_id else None
    if not roll and roll_id:
        roll = await db.inventory_rolls.find_one({"roll_no": roll_id}, {"_id": 0})
    if not roll:
        raise HTTPException(status_code=404, detail="Roll tidak ditemukan")
    if roll.get("product_id") != product_id:
        raise HTTPException(status_code=400, detail={"code": "ROLL_WRONG_PRODUCT", "message": f"Roll {roll.get('roll_no')} bukan produk {sku} — ambil roll produk yang benar."})
    if roll.get("status") != "available":
        raise HTTPException(status_code=409, detail={"code": "ROLL_NOT_AVAILABLE", "message": f"Roll {roll.get('roll_no')} berstatus {roll.get('status')} (terikat pesanan) — tidak boleh dipotong untuk sampel."})
    if entity_id and roll.get("owner_entity_id") and roll.get("owner_entity_id") != entity_id:
        raise HTTPException(status_code=400, detail={"code": "ROLL_WRONG_ENTITY", "message": f"Roll {roll.get('roll_no')} milik badan usaha lain — pesanan sampel ini milik {entity_id}."})
    if float(roll.get("length_remaining") or 0) < take:
        raise HTTPException(status_code=400, detail={"code": "ROLL_TOO_SHORT", "message": f"Sisa roll {roll.get('length_remaining')} < {take} {unit}."})
    return roll


async def _reprice_order_line(order: Dict[str, Any], product_id: str, take: float, actor_name: str, note: str) -> None:
    """Panjang aktual ≠ permintaan → qty baris & total pesanan dihitung ulang (pola eskalasi gudang)."""
    items = [dict(i) for i in order.get("items", [])]
    for it in items:
        if it.get("product_id") == product_id and it.get("is_sample"):
            it["quantity"] = take
            it["base_quantity"] = take
            break
    from services.config_service import compute_order_pricing
    pricing = await compute_order_pricing(items, order.get("entity_id"), 0,
                                          tax_override=(order.get("tax_override") or "").strip().lower() or None)
    await db.sales_orders.update_one({"id": order["id"]}, {"$set": {
        "items": pricing["items"], "total_amount": pricing["total_amount"],
        "items_discount_total": pricing["items_discount_total"], "order_discount_amount": pricing["order_discount_amount"],
        "discount_total": pricing["discount_total"], "net_subtotal": pricing["net_subtotal"],
        "dpp": pricing["dpp"], "dpp_nilai_lain": pricing.get("dpp_nilai_lain", False),
        "effective_rate": pricing.get("effective_rate", pricing["ppn_rate"]), "ppn_amount": pricing["ppn_amount"],
        "grand_total": pricing["grand_total"], "approval_amount": pricing["grand_total"], "updated_at": now_iso()},
        "$push": {"timeline": {"event": "qty_adjusted", "label": "Panjang sampel disesuaikan saat potong",
                               "actor": actor_name, "at": now_iso(), "note": note}}})


async def cut_sample_task(task_id: str, payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    task = await db.wms_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
    if task.get("task_subtype") != "sample_cut":
        raise HTTPException(status_code=400, detail="Tugas ini bukan permintaan potong sampel")
    if task.get("status") == "scheduled":
        raise HTTPException(status_code=400, detail="Tugas pengambilan masih di-hold (terjadwal). Rilis dulu sebelum memotong.")
    if task.get("status") not in ("created", "picking") or float(task.get("picked_qty") or 0) > 0:
        raise HTTPException(status_code=409, detail=f"Sampel sudah dipotong / tugas berstatus {task.get('status')}")
    order = await db.sales_orders.find_one({"id": task.get("order_id")}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan")
    requested = round(float(task.get("quantity") or 0), 2)
    take = round(float(payload.get("actual_length") or requested), 2)
    if take <= 0:
        raise HTTPException(status_code=400, detail="Panjang aktual potongan harus > 0")
    unit = task.get("unit") or "meter"
    roll = await _resolve_roll(task["product_id"], task.get("sku", ""), take, unit,
                               (payload.get("roll_id") or "").strip(), (payload.get("epc") or "").strip(),
                               entity_id=order.get("entity_id") or "")
    reason = (payload.get("reason") or "").strip()
    off_suggestion = bool(task.get("suggested_roll_id")) and roll["id"] != task.get("suggested_roll_id")
    if off_suggestion and not reason:
        raise HTTPException(status_code=400, detail={"code": "REASON_REQUIRED",
                            "message": f"Roll ini bukan saran FIFO ({task.get('suggested_roll_no')}). Isi alasan mengapa roll lain dipotong."})
    # INV-ATOMIC-01 — klaim tugas SEBELUM roll dipotong / SO ditulis.
    await _saga.claim("wms_tasks", task_id, "sample_cut", precondition={"status": {"$in": ["created", "picking"]}}, actor=actor.get("name", ""))
    parent = await db.inventory_rolls.find_one_and_update(
        {"id": roll["id"], "status": "available", "length_remaining": {"$gte": take - 0.001}},
        {"$inc": {"length_remaining": -take, "length_initial": -take}, "$set": {"updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not parent:
        await _saga.release("wms_tasks", task_id)
        raise HTTPException(status_code=409, detail="Roll baru saja dipakai proses lain — pindai ulang.")
    rem = round(float(parent.get("length_remaining") or 0), 2)
    await db.inventory_rolls.update_one({"id": roll["id"]}, {"$set": {
        "length_remaining": rem, "length_initial": round(float(parent.get("length_initial") or 0), 2),
        "is_remnant": bool(0 < rem < REMNANT_THRESHOLD)}})
    now = now_iso()
    child = dict(roll)
    child.update({"id": new_id("roll"), "length_initial": take, "length_remaining": take, "status": "reserved",
                  "reserved_ref": {"type": "sales_order", "id": order["id"]}, "earmarked_for": None,
                  "is_remnant": False, "is_sample_cut": True, "parent_roll_id": roll["id"], "parent_roll_no": roll.get("roll_no"),
                  "created_at": now, "updated_at": now})
    child = await insert_child_roll(child, roll)   # P-1: potongan lahir TANPA tag
    await db.inventory_movements.insert_one({
        "id": new_id("mov"), "product_id": roll["product_id"], "warehouse_id": roll["warehouse_id"],
        "owner_entity_id": roll.get("owner_entity_id"), "movement_type": "sample_cut", "quantity": 0.0,
        "cut_length": take, "unit": unit, "roll_id": child["id"], "parent_roll_id": roll["id"], "qty_rolls": 1,
        "source_document": order["number"], "reference_id": order["id"], "timestamp": now, "created_by": actor.get("name", "")})
    await rebuild_balance(roll["product_id"], roll["warehouse_id"], roll.get("owner_entity_id") or order.get("entity_id"))

    if abs(take - requested) > 0.005:
        await _reprice_order_line(order, task["product_id"], take, actor.get("name", ""),
                                  f"{task.get('product_name')}: {requested:g} → {take:g} {unit} (roll {roll.get('roll_no')})")
    alloc = {"id": new_id("alloc"), "product_id": roll["product_id"], "warehouse_id": roll["warehouse_id"],
             "quantity": take, "roll_ids": [child["id"]], "lots": [roll.get("lot")] if roll.get("lot") else [],
             "lot": roll.get("lot"), "source": "sample_cut"}
    await db.sales_orders.update_one({"id": order["id"]}, {"$push": {"allocations": alloc}})
    await db.sales_orders.update_one(
        {"id": order["id"], "items": {"$elemMatch": {"product_id": task["product_id"], "is_sample": True}}},
        {"$set": {"items.$.reserved_qty": take, "items.$.sample_cut_status": "cut", "items.$.cut_roll_id": roll["id"],
                  "items.$.cut_roll_no": roll.get("roll_no"), "items.$.child_roll_id": child["id"], "items.$.child_roll_no": child.get("roll_no"),
                  "items.$.cut_by": actor.get("name", ""), "items.$.cut_at": now,
                  "items.$.off_suggestion_reason": reason if off_suggestion else "", "updated_at": now}})
    updated = await db.wms_tasks.find_one_and_update(
        {"id": task_id},
        {**_saga.finish_set({"status": "packing", "picked_qty": take, "quantity": take, "roll_id": child["id"],
                             "allocation_id": alloc["id"], "warehouse_id": roll["warehouse_id"], "lot": roll.get("lot") or "",
                             "parent_roll_id": roll["id"], "parent_roll_no": roll.get("roll_no"), "child_roll_no": child.get("roll_no"),
                             "off_suggestion_reason": reason if off_suggestion else "",
                             "cut_by": actor.get("name", ""), "cut_at": now, "updated_at": now}),
         "$push": {"scan_log": {"id": new_id("scan"), "scan_type": "cut", "actual_qty": take, "epc": (payload.get("epc") or "").strip(),
                                "roll_id": roll["id"], "roll_no": roll.get("roll_no"), "actor": actor.get("name", ""), "timestamp": now}}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    from services.fulfillment_status import recompute_so_status
    await recompute_so_status(order["id"])
    return {"task": safe_doc(updated), "cut": {
        "cut_roll_no": roll.get("roll_no"), "child_roll_no": child.get("roll_no"), "child_roll_id": child["id"],
        "length": take, "unit": unit, "requested_length": requested, "customer_name": order.get("customer_name"),
        "product_name": task.get("product_name"), "sku": task.get("sku"), "sales_order_number": order.get("number"),
        "parent_remaining": rem}}
