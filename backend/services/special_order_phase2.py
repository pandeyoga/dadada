"""
special_order_phase2.py — Fase 2 Special Order (OD):
  * ACC PELANGGAN atas sample (acc / revisi / tolak + catatan, tanggal, bukti) — riwayat lengkap.
    revisi → sample R&D baru otomatis (spesifikasi diwarisi), OD kembali ke fase Sampling.
  * HARGA FINAL: harga kontrak supplier pemenang + margin (default 30%, bisa diubah Sales) → kunci → Confirmed.
  * PROOFING OTOMATIS: desain dari OD printing di-ACC → Permintaan Sample proofing lahir + notifikasi MD.
Eksklusivitas SKU ditegakkan di `assert_customer_allowed` (dipanggil pembuat SO/POS).
"""
from __future__ import annotations
import logging

from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import new_id, now_iso, parse_decimal, rupiah
from services import storage_service as storage
from services import rnd_sample_service as smp
from services import rnd_spec_service as spec_svc
from services import special_order_routing as routing
logger = logging.getLogger(__name__)


DECISIONS = ("acc", "revisi", "tolak")
DEFAULT_MARGIN_PCT = 30.0
SETTINGS_SCOPE = "special_order"


class ODError(ValueError):
    pass


def _label(od: Dict[str, Any]) -> str:
    return f"Pesanan khusus {od.get('number')} · {od.get('customer_name', '')}"


async def default_margin_pct() -> float:
    doc = await db.system_settings.find_one({"scope": SETTINGS_SCOPE}, {"_id": 0, "default_margin_pct": 1}) or {}
    try:
        return float(doc.get("default_margin_pct") if doc.get("default_margin_pct") is not None else DEFAULT_MARGIN_PCT)
    except (TypeError, ValueError):
        return DEFAULT_MARGIN_PCT


# ─── Sample pemenang / desain ACC ─────────────────────────────────────────────
async def _decided_samples(od: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Sample yang sudah diputus — HANYA bila sample TERAKHIR (revisi terbaru) juga sudah diputus."""
    ids = od.get("sample_ids") or []
    if not ids:
        return []
    rows = await db.md_samples.find({"id": {"$in": ids}, "status": {"$ne": "cancelled"}},
                                    {"_id": 0, "id": 1, "number": 1, "status": 1, "sample_types": 1,
                                     "decision": 1, "delivered_at": 1, "created_at": 1}).to_list(50)
    rows.sort(key=lambda r: r.get("created_at") or "")
    if rows and rows[-1].get("status") != "decided":
        return []
    return [r for r in rows if r.get("status") == "decided"]


async def _design_of(od: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not od.get("design_request_id"):
        return None
    req = await db.design_requests.find_one({"id": od["design_request_id"]}, {"_id": 0, "design_id": 1})
    if not req or not req.get("design_id"):
        return None
    return await db.design_gallery.find_one({"id": req["design_id"]}, {"_id": 0, "id": 1, "code": 1, "status": 1, "version": 1, "approved_at": 1})


async def review_ready(od: Dict[str, Any]) -> Dict[str, Any]:
    """Apakah OD sudah punya hasil yang bisa dimintakan ACC pelanggan + dasar keputusannya."""
    decided = await _decided_samples(od)
    design = await _design_of(od)
    design_ok = bool(design and design.get("status") in ("approved", "final_submitted", "active"))
    latest = decided[-1] if decided else None
    return {"ready": bool(decided) or design_ok, "sample": latest, "design": design if design_ok else None,
            "samples_decided": len(decided)}


# ─── Keputusan pelanggan ──────────────────────────────────────────────────────
async def customer_decide(od: Dict[str, Any], payload: Dict[str, Any], actor: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
    decision = str(payload.get("decision") or "").strip().lower()
    if decision not in DECISIONS:
        raise ODError("Keputusan pelanggan harus salah satu: acc / revisi / tolak.")
    if od.get("status") in ("draft", "pending_approval", "cancelled"):
        raise ODError("OD belum disetujui internal — belum ada sample untuk dimintakan ACC pelanggan.")
    if (od.get("pricing") or {}).get("locked"):
        raise ODError("Harga sudah dikunci — keputusan pelanggan tidak bisa diubah lagi (buka kunci oleh admin dulu).")
    ready = await review_ready(od)
    if not ready["ready"]:
        raise ODError("Belum ada sample yang diputus (pemenang) atau desain ACC — pelanggan belum bisa memberi keputusan.")
    note = (payload.get("note") or "").strip()
    if decision in ("revisi", "tolak") and not note:
        raise ODError("Catatan pelanggan wajib diisi untuk revisi / tolak (apa yang kurang).")
    at = (str(payload.get("decided_at") or "")[:10]) or now_iso()[:10]
    entry = {
        "id": new_id("odcd"), "decision": decision, "note": note, "decided_at": at,
        "recorded_by": actor.get("name", ""), "recorded_at": now_iso(),
        "sample_id": (ready["sample"] or {}).get("id", ""), "sample_number": (ready["sample"] or {}).get("number", ""),
        "design_id": (ready["design"] or {}).get("id", ""), "design_code": (ready["design"] or {}).get("code", ""),
        "evidence": [], "contact_name": (payload.get("contact_name") or "").strip(),
    }
    sets: Dict[str, Any] = {"customer_decision": decision, "customer_decision_at": at, "customer_decision_note": note,
                            "updated_at": now_iso()}
    history_note = f"Pelanggan {decision.upper()} sample" + (f" — {note}" if note else "")
    if decision == "revisi":
        new_sample = await _spawn_revision_sample(od, actor, entity_id, note, ready)
        entry["revision_sample_id"] = new_sample.get("id", "")
        entry["revision_sample_number"] = new_sample.get("number", "")
        sets["customer_decision"] = ""   # OD kembali ke sampling; keputusan hidup hanya di riwayat
        await db.special_orders.update_one({"id": od["id"]}, {"$push": {"sample_ids": new_sample["id"], "sample_numbers": new_sample.get("number", "")}})
    if decision == "tolak":
        sets.update({"status": "cancelled", "cancelled_at": now_iso(), "cancelled_by": actor.get("email", actor.get("name", "")),
                     "reject_reason": f"Ditolak pelanggan: {note}"})
    await db.special_orders.update_one({"id": od["id"]}, {
        "$set": sets,
        "$push": {"customer_decisions": entry,
                  "status_history": {"status": sets.get("status", od.get("status")), "timestamp": now_iso(),
                                     "user": actor.get("email", ""), "note": history_note}}})
    return entry


async def _spawn_revision_sample(od: Dict[str, Any], actor: Dict[str, Any], entity_id: str, note: str,
                                 ready: Dict[str, Any]) -> Dict[str, Any]:
    prev = ready.get("sample") or {}
    types = [t for t in (prev.get("sample_types") or []) if t] or \
            [t for t in (od.get("request_types") or []) if t in ("labdip", "handfeel")] or ["labdip"]
    spec_id = od.get("spec_id") or ""
    if not spec_id and prev.get("id"):
        row = await db.md_samples.find_one({"id": prev["id"]}, {"_id": 0, "spec_id": 1})
        spec_id = (row or {}).get("spec_id") or ""
    if not spec_id:
        spec_doc = await spec_svc.create_spec(routing._spec_from_od(od, types), entity_id=entity_id, actor=actor.get("name", ""))  # noqa: SLF001
        spec_id = spec_doc["id"]
        await db.special_orders.update_one({"id": od["id"]}, {"$set": {"spec_id": spec_id}})
    item = od.get("custom_item") or {}
    rev_no = len([d for d in (od.get("customer_decisions") or []) if d.get("decision") == "revisi"]) + 1
    design = ready.get("design") or {}
    sample = await smp.create_sample({
        "spec_id": spec_id, "sample_types": types,
        "title": f"{od.get('title') or item.get('description') or 'Sample'} — revisi pelanggan #{rev_no}",
        "brief": f"REVISI PELANGGAN #{rev_no} atas {prev.get('number') or 'sample'}: {note}. {_label(od)}",
        "color_target": {"color_id": (od.get("spec") or {}).get("color_id")} if (od.get("spec") or {}).get("color_id") else {},
        "customer_id": od.get("customer_id", ""), "target_date": od.get("expected_delivery", ""),
        "qty_requested": 3, "unit": item.get("unit") or "meter",
        **({"design_id": design.get("id"), "design_version": design.get("version")} if design.get("id") else {}),
    }, entity_id=entity_id, actor=actor.get("name", ""))
    await db.md_samples.update_one({"id": sample["id"]}, {"$set": {
        "special_order_id": od["id"], "special_order_number": od.get("number", ""),
        "customer_name": od.get("customer_name", ""), "exclusive_customer_id": od.get("customer_id", ""),
        "revision_of_sample_id": prev.get("id", ""), "customer_revision_note": note}})
    try:
        from services import notification_service as notif
        await notif.create_addressed(roles=("md", "manager"), entity_id=entity_id, notif_type="special_order_revision",
                                     title=f"Revisi pelanggan · {od.get('number')} → sample {sample.get('number')}",
                                     body=note[:200], severity="warning", link="rnd-samples", ref=sample["id"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[_spawn_revision_sample] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return sample


async def add_evidence(od: Dict[str, Any], decision_id: str, actor: str, filename: str, content_type: str, data: bytes,
                       caption: str = "") -> Dict[str, Any]:
    entries = od.get("customer_decisions") or []
    target = next((d for d in entries if d.get("id") == decision_id), None) if decision_id else (entries[-1] if entries else None)
    if not target:
        raise ODError("Belum ada keputusan pelanggan yang bisa dilampiri bukti.")
    ct = storage.validate_upload(filename, content_type, len(data))
    path = storage.build_path("special_orders", storage.ext_of(filename))
    await storage.put_object(path, data, ct)
    meta = {"id": new_id("odev"), "filename": filename, "content_type": ct, "size": len(data), "path": path,
            "caption": caption, "uploaded_by": actor, "uploaded_at": now_iso()}
    await db.special_orders.update_one({"id": od["id"], "customer_decisions.id": target["id"]},
                                       {"$push": {"customer_decisions.$.evidence": meta}, "$set": {"updated_at": now_iso()}})
    return meta


async def evidence_bytes(od: Dict[str, Any], file_id: str):
    for d in od.get("customer_decisions") or []:
        for f in d.get("evidence") or []:
            if f.get("id") == file_id:
                data = await storage.get_object(f["path"])
                if isinstance(data, tuple):
                    data = data[0]
                return data, f.get("content_type", "application/octet-stream")
    raise ODError("Bukti tidak ditemukan.")


# ─── Harga final ──────────────────────────────────────────────────────────────
async def pricing_preview(od: Dict[str, Any], margin_pct: Optional[float] = None) -> Dict[str, Any]:
    decided = await _decided_samples(od)
    winner = decided[-1] if decided else None
    dec = (winner or {}).get("decision") or {}
    cost = float(dec.get("price") or 0)
    saved = od.get("pricing") or {}
    if saved.get("locked"):
        return {**saved, "target_price": float((od.get("custom_item") or {}).get("target_price") or 0),
                "default_margin_pct": await default_margin_pct(), "customer_decision": od.get("customer_decision", "")}
    margin = float(margin_pct) if margin_pct is not None else float(saved.get("margin_pct") if saved.get("margin_pct") is not None else await default_margin_pct())
    qty = float((od.get("custom_item") or {}).get("quantity") or 0)
    unit = round(cost * (1 + margin / 100.0), 2) if cost else 0.0
    return {"cost_price": cost, "margin_pct": margin, "final_unit_price": unit, "quantity": qty,
            "unit": (od.get("custom_item") or {}).get("unit", "meter"), "total": round(unit * qty, 2),
            "target_price": float((od.get("custom_item") or {}).get("target_price") or 0),
            "supplier_id": dec.get("supplier_id", ""), "supplier_name": dec.get("supplier_name", ""),
            "contract_number": dec.get("contract_number", ""), "sample_number": (winner or {}).get("number", ""),
            "product_id": dec.get("product_id", ""), "product_sku": dec.get("product_sku", ""),
            "default_margin_pct": await default_margin_pct(), "locked": bool(saved.get("locked")),
            "locked_by": saved.get("locked_by", ""), "locked_at": saved.get("locked_at", ""),
            "unlocked_by": saved.get("unlocked_by", ""), "unlocked_at": saved.get("unlocked_at", ""),
            "customer_decision": od.get("customer_decision", "")}


async def lock_price(od: Dict[str, Any], payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    if (od.get("pricing") or {}).get("locked"):
        raise ODError("Harga OD ini sudah dikunci.")
    if od.get("customer_decision") != "acc":
        raise ODError("Harga final hanya bisa dikunci setelah pelanggan ACC sample.")
    margin = payload.get("margin_pct")
    margin = float(parse_decimal(margin, 2)) if margin not in (None, "") else None
    if margin is not None and (margin < 0 or margin > 500):
        raise ODError("Margin harus 0–500%.")
    pv = await pricing_preview(od, margin)
    if pv["cost_price"] <= 0:
        raise ODError("Harga kontrak supplier pemenang belum ada — putuskan pemenang sample dengan harga dulu.")
    pricing = {**{k: pv[k] for k in ("cost_price", "margin_pct", "final_unit_price", "quantity", "unit", "total",
                                     "supplier_id", "supplier_name", "contract_number", "sample_number", "product_id", "product_sku")},
               "locked": True, "locked_by": actor.get("name", ""), "locked_at": now_iso(), "note": (payload.get("note") or "").strip()}
    # INV-ATOMIC-01 — klaim atomik OD (harga BELUM terkunci) sebelum produk/spec disentuh;
    # tulisan akhir finish_set mencabut kunci; dua kunci paralel → satu 409.
    from services import atomic_claim as _saga
    await _saga.claim("special_orders", od["id"], "lock_price",
                      precondition={"price_locked": {"$ne": True}}, actor=actor.get("name", ""))
    _res = await db.special_orders.update_one({"id": od["id"], "price_locked": {"$ne": True}}, {
        **_saga.finish_set({"pricing": pricing, "final_price": pricing["final_unit_price"], "total_amount": pricing["total"],
                 "price_locked": True, "updated_at": now_iso(),
                 **({"linked_product_id": pv["product_id"], "linked_product_sku": pv["product_sku"]} if pv["product_id"] else {})}),
        "$push": {"status_history": {"status": od.get("status"), "timestamp": now_iso(), "user": actor.get("email", ""),
                                     "note": f"Harga final dikunci: {rupiah(pricing['final_unit_price'])}/{pricing['unit']} (kontrak {rupiah(pricing['cost_price'])} + margin {pricing['margin_pct']:g}%)"}}})
    if _res.matched_count == 0:
        raise ODError("Harga OD ini baru saja dikunci oleh pihak lain. Muat ulang.")
    pid_final = pv["product_id"] or od.get("linked_product_id") or ""
    if pid_final:
        await db.products.update_one({"id": pid_final}, {"$set": {
            "price": pricing["final_unit_price"], "harga_pokok": pricing["cost_price"],
            "exclusive_customer_id": od.get("customer_id", ""), "exclusive_customer_name": od.get("customer_name", ""),
            "special_order_id": od["id"], "special_order_number": od.get("number", ""), "updated_at": now_iso()}})
    if payload.get("auto_po", True):
        fresh = await db.special_orders.find_one({"id": od["id"]}, {"_id": 0})
        try:
            pricing["procurement"] = await auto_procure(fresh, actor, payload.get("warehouse_id") or "")
        except Exception as exc:  # noqa: BLE001 — harga tetap terkunci; pengadaan bisa diulang manual
            pricing["procurement_error"] = str(exc)
            await db.special_orders.update_one({"id": od["id"]}, {"$set": {"procurement_error": str(exc)}})
    return pricing


async def default_warehouse_id(entity_id: str) -> str:
    from services import warehouse_scope_service as whs
    rows = await whs.list_for_entity(entity_id, only_active=True)
    return (rows[0] or {}).get("id", "") if rows else ""


async def auto_procure(od: Dict[str, Any], actor: Dict[str, Any], warehouse_id: str = "") -> Dict[str, Any]:
    """PR (source special_order) → approve → PO ke supplier pemenang (harga kontrak, tenggat OD). Idempoten."""
    if od.get("linked_po_id"):
        return {"pr_number": od.get("linked_pr_number"), "po_number": od.get("linked_po_number"), "skipped": "sudah ada PO"}
    pricing = od.get("pricing") or {}
    if not pricing.get("locked"):
        raise ODError("Harga final belum dikunci.")
    product_id = pricing.get("product_id") or od.get("linked_product_id") or ""
    if not product_id:
        raise ODError("SKU eksklusif belum lahir (ACC spesifikasi di keputusan sample) — PO butuh produk katalog.")
    supplier_id = pricing.get("supplier_id") or ""
    if not supplier_id:
        raise ODError("Supplier pemenang tidak diketahui.")
    entity_id = od.get("entity_id", "")
    # Harga terkunci = konfirmasi final → SKU eksklusif dirilis ke produksi agar boleh masuk PR/PO & SO.
    prod = await db.products.find_one({"id": product_id}, {"_id": 0, "lifecycle": 1, "spec_id": 1})
    if prod and prod.get("lifecycle") not in (None, "", "produksi"):
        released = False
        if prod.get("spec_id"):
            try:
                await spec_svc.release_product(prod["spec_id"], actor, note=f"Otomatis — harga {_label(od)} dikunci")
                released = True
            except Exception:  # noqa: BLE001
                released = False
        if not released:
            await db.products.update_one({"id": product_id}, {"$set": {"lifecycle": "produksi", "updated_at": now_iso()}})
            if prod.get("spec_id"):
                await db.md_specs.update_one({"id": prod["spec_id"]}, {"$set": {"lifecycle": "produksi", "released_by": actor.get("name", ""), "released_at": now_iso()}})
    wh = warehouse_id or await default_warehouse_id(entity_id)
    if not wh:
        raise ODError("Tidak ada gudang aktif untuk badan usaha ini — pilih gudang tujuan.")
    from services import warehouse_scope_service as whs
    await whs.assert_usable(wh, entity_id, action="menerima barang di sini", field_label="Gudang tujuan")
    from services import purchase_requisition_service as pr_svc
    from schemas import PurchaseRequisitionCreate, PurchaseRequisitionItem
    item = od.get("custom_item") or {}
    out: Dict[str, Any] = {}
    pr_id = od.get("linked_pr_id") or ""
    if not pr_id:
        pr = await pr_svc.create_requisition(PurchaseRequisitionCreate(
            items=[PurchaseRequisitionItem(product_id=product_id, description=od.get("title") or item.get("description", ""),
                                           quantity=float(pricing.get("quantity") or item.get("quantity") or 1), unit=pricing.get("unit") or item.get("unit", "meter"),
                                           est_price=float(pricing.get("cost_price") or 0), note=f"Kontrak {pricing.get('contract_number') or '-'} · sample {pricing.get('sample_number') or '-'}")],
            warehouse_id=wh, entity_id=entity_id,
            reason=f"Pengadaan otomatis {_label(od)} — supplier pemenang {pricing.get('supplier_name')}",
            needed_by_date=od.get("expected_delivery", ""), source="special_order", source_ref_id=od["id"],
            notes=f"Harga final pelanggan {rupiah(float(pricing.get('final_unit_price') or 0))} (margin {float(pricing.get('margin_pct') or 0):g}%)",
            submit_now=True), created_by="Sistem (OD)")
        pr_id = pr["id"]
        await db.special_orders.update_one({"id": od["id"]}, {"$set": {"linked_pr_id": pr_id, "linked_pr_number": pr["number"], "pr_id": pr_id}})
        out.update({"pr_id": pr_id, "pr_number": pr["number"]})
    pr_doc = await db.purchase_requisitions.find_one({"id": pr_id}, {"_id": 0, "status": 1, "number": 1})
    if pr_doc and pr_doc.get("status") in ("draft", "pending_approval"):
        try:
            await pr_svc.approve_requisition(pr_id, actor, notes="Otomatis — harga OD dikunci")
        except ValueError as exc:
            raise ODError(f"PR {pr_doc.get('number')} belum bisa disetujui otomatis: {exc}") from exc
    res = await pr_svc.convert_to_po(pr_id, supplier_id, actor, warehouse_id=wh,
                                     expected_delivery_date=od.get("expected_delivery", ""),
                                     notes=f"Otomatis dari {_label(od)} · kontrak {pricing.get('contract_number') or '-'}")
    po = res.get("po") or {}
    # Jaminan harga PO = harga kontrak pemenang yang dikunci (bukan kontrak lain supplier yang sama).
    cost = float(pricing.get("cost_price") or 0)
    po_doc = await db.purchase_orders.find_one({"id": po.get("id")}, {"_id": 0, "items": 1}) or {}
    if cost > 0 and po_doc.get("items"):
        items = po_doc["items"]
        changed = False
        for it in items:
            if it.get("product_id") == product_id and abs(float(it.get("price") or it.get("unit_price") or 0) - cost) > 0.009:
                q = float(it.get("quantity") or 0)
                it.update({"price": cost, "unit_price": cost, "subtotal": round(cost * q, 2),
                           "contract_id": pricing.get("contract_id", "") or it.get("contract_id", ""),
                           "contract_number": pricing.get("contract_number") or it.get("contract_number", ""),
                           "price_source": "special_order_contract"})
                changed = True
        if changed:
            from services.config_service import compute_order_pricing
            raw = [{k: v for k, v in i.items()} for i in items]
            pr_ = await compute_order_pricing(raw, entity_id, 0.0, cfg_section="purchasing")
            await db.purchase_orders.update_one({"id": po.get("id")}, {"$set": {
                "items": pr_["items"], "total_amount": pr_["total_amount"], "net_subtotal": pr_["net_subtotal"], "dpp": pr_["dpp"],
                "ppn_amount": pr_["ppn_amount"], "grand_total": pr_["grand_total"], "outstanding": round(float(pr_["grand_total"]), 2),
                "approval_amount": pr_["total_amount"], "updated_at": now_iso()}})
    await db.purchase_orders.update_one({"id": po.get("id")}, {"$set": {"special_order_id": od["id"], "special_order_number": od.get("number", ""),
                                                                      "exclusive_customer_id": od.get("customer_id", ""), "exclusive_customer_name": od.get("customer_name", "")}})
    await db.special_orders.update_one({"id": od["id"]}, {
        "$set": {"linked_po_id": po.get("id", ""), "linked_po_number": po.get("po_number", ""), "procurement_warehouse_id": wh,
                 "procurement_error": "", "updated_at": now_iso()},
        "$push": {"status_history": {"status": od.get("status"), "timestamp": now_iso(), "user": actor.get("email", ""),
                                     "note": f"PR {out.get('pr_number') or pr_doc.get('number')} → PO {po.get('po_number')} ke {pricing.get('supplier_name')} (otomatis)"}}})
    if od.get("status") == "confirmed":
        from services.special_order_service import transition_special_order_status
        try:
            await transition_special_order_status(od["id"], "in_production", actor.get("email", ""))
        except ValueError as exc:
            logger.warning("[auto_procure] efek samping gagal diabaikan: %s", exc)  # KN-C10
    out.update({"po_id": po.get("id", ""), "po_number": po.get("po_number", ""), "warehouse_id": wh})
    return out


async def unlock_price(od: Dict[str, Any], actor: Dict[str, Any], reason: str) -> None:
    if not (od.get("pricing") or {}).get("locked"):
        raise ODError("Harga belum dikunci.")
    if actor.get("role") != "admin":
        raise ODError("Hanya admin yang boleh membuka kunci harga.")
    if not (reason or "").strip():
        raise ODError("Alasan buka kunci wajib diisi.")
    if od.get("linked_pr_id") or od.get("linked_sales_order_id") or od.get("linked_po_id"):
        raise ODError("PR/PO/SO sudah lahir dari harga ini — tidak bisa dibuka lagi.")
    await db.special_orders.update_one({"id": od["id"]}, {
        "$set": {"pricing.locked": False, "pricing.unlocked_by": actor.get("name", ""), "pricing.unlocked_at": now_iso(),
                 "pricing.unlock_reason": reason.strip(), "price_locked": False, "updated_at": now_iso()},
        "$push": {"status_history": {"status": od.get("status"), "timestamp": now_iso(), "user": actor.get("email", ""),
                                     "note": f"Kunci harga dibuka: {reason.strip()}"}}})


# ─── Fase 4 — Pengiriman OD otomatis ─────────────────────────────────────────
async def _od_of_so(so_id: str) -> Optional[Dict[str, Any]]:
    return await db.special_orders.find_one({"$or": [{"linked_sales_order_id": so_id}, {"so_id": so_id}]}, {"_id": 0})


async def on_goods_received(od_id: str) -> Dict[str, Any]:
    """PO OD diterima gudang: stok → SO OD direservasi, tugas outbound (Surat Jalan) lahir otomatis."""
    od = await db.special_orders.find_one({"id": od_id}, {"_id": 0})
    if not od:
        return {}
    so_id = od.get("linked_sales_order_id") or ""
    if not so_id:
        raise ODError("SO hasil OD belum ada — konversi ke Pesanan Penjualan dulu, lalu tekan 'Siapkan pengiriman'.")
    so = await db.sales_orders.find_one({"id": so_id}, {"_id": 0})
    if not so or so.get("status") in ("cancelled", "done", "shipped"):
        return {"skipped": (so or {}).get("status")}
    from services.backorder_service import auto_fulfill_backorders
    from services.fulfillment_status import create_outbound_tasks_for_order, recompute_so_status
    pid = (od.get("pricing") or {}).get("product_id") or od.get("linked_product_id") or ""
    if pid and so.get("has_backorder"):
        await auto_fulfill_backorders(pid, so.get("entity_id") or od.get("entity_id", ""))
    so = await db.sales_orders.find_one({"id": so_id}, {"_id": 0})
    if not (so.get("allocations") or []):
        raise ODError("Stok hasil PO belum bisa direservasi ke SO (mungkin masih karantina QC). Ulangi 'Siapkan pengiriman' setelah QC.")
    tasks = await create_outbound_tasks_for_order(so_id, "Sistem (OD)")
    if tasks:
        await db.sales_orders.update_one({"id": so_id}, {"$set": {"status": "confirmed", "confirmed_at": now_iso(), "confirmed_by": "Sistem (OD)",
                                                                  "admin_verified": True, "updated_at": now_iso()},
                                                         "$push": {"timeline": {"id": new_id("tl"), "event": "confirmed", "label": "Dikonfirmasi otomatis — barang pesanan khusus diterima gudang",
                                                                                "by": "Sistem (OD)", "at": now_iso()}}})
    await recompute_so_status(so_id)
    await db.special_orders.update_one({"id": od_id}, {"$set": {"shipping_error": "", "outbound_task_ids": [t["id"] for t in tasks], "updated_at": now_iso()},
                                                       "$push": {"status_history": {"status": od.get("status"), "timestamp": now_iso(), "user": "Sistem (OD)",
                                                                                    "note": f"Barang diterima → {len(tasks)} tugas Surat Jalan lahir otomatis untuk SO {so.get('number')}"}}})
    return {"tasks": len(tasks), "so_number": so.get("number")}


async def on_shipment_dispatched(so_id: str) -> None:
    od = await _od_of_so(so_id)
    if not od or od.get("status") not in ("in_production", "ready"):
        return
    open_tasks = await db.wms_tasks.count_documents({"order_id": so_id, "flow_type": "outbound", "status": {"$nin": ["dispatched", "cancelled"]}})
    if open_tasks:
        return
    from services.special_order_service import transition_special_order_status
    for st in ("ready", "shipped"):
        try:
            await transition_special_order_status(od["id"], st, "Sistem (Surat Jalan)")
        except ValueError as exc:
            logger.warning("[on_shipment_dispatched] efek samping gagal diabaikan: %s", exc)  # KN-C10


async def on_delivered(so_id: str) -> None:
    od = await _od_of_so(so_id)
    if not od or od.get("status") != "shipped":
        return
    from services.special_order_service import transition_special_order_status
    try:
        await transition_special_order_status(od["id"], "done", "Sistem (Terkirim)")
    except ValueError as exc:
        logger.warning("[on_delivered] efek samping gagal diabaikan: %s", exc)  # KN-C10


async def desk_rows(scope: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Antrean OD untuk Meja Admin Sales: menunggu ACC pelanggan · perlu kunci harga · siap dikirim."""
    rows = await db.special_orders.find({**scope, "status": {"$in": ["confirmed", "approved", "in_production", "ready"]}, "request_types.0": {"$exists": True}},
                                        {"_id": 0}).sort("updated_at", -1).to_list(300)
    out: Dict[str, List[Dict[str, Any]]] = {"acc_pelanggan": [], "kunci_harga": [], "siap_kirim": []}
    for od in rows:
        chain = await routing.chain_of(od)
        ph = chain.get("phase")
        if ph in ("sample_ready", "customer_review"):
            out["acc_pelanggan"].append({**od, "phase": ph, "basis": chain.get("review") or {}})
        elif ph == "pricing":
            out["kunci_harga"].append({**od, "phase": ph, "pricing_preview": chain.get("pricing") or {}})
        elif od.get("status") == "ready" and not od.get("outbound_task_ids"):
            out["siap_kirim"].append({**od, "phase": ph})
    return out
def assert_customer_allowed(product: Dict[str, Any], customer_id: str, where: str = "Pesanan") -> None:
    owner = (product or {}).get("exclusive_customer_id") or ""
    if not owner:
        return
    if owner != (customer_id or ""):
        name = product.get("name") or product.get("sku") or "produk ini"
        raise HTTPException(status_code=400, detail=(
            f"{where}: produk '{name}' ({product.get('sku', '')}) EKSKLUSIF untuk pelanggan "
            f"{product.get('exclusive_customer_name') or owner} (hasil pesanan khusus {product.get('special_order_number') or ''}). "
            "Tidak boleh dijual ke pelanggan lain / walk-in — pilih pelanggan pemiliknya."))


# ─── Proofing otomatis saat desain OD di-ACC ─────────────────────────────────
async def on_design_approved(design: Dict[str, Any], actor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    req_id = (design.get("request_id") or "").strip()
    if not req_id:
        return None
    req = await db.design_requests.find_one({"id": req_id}, {"_id": 0, "special_order_id": 1})
    od_id = (req or {}).get("special_order_id") or ""
    if not od_id:
        return None
    od = await db.special_orders.find_one({"id": od_id}, {"_id": 0})
    if not od or od.get("status") == "cancelled":
        return None
    exists = await db.md_samples.find_one({"special_order_id": od_id, "design_id": design["id"], "sample_types": "proofing",
                                           "status": {"$ne": "cancelled"}}, {"_id": 0, "id": 1})
    if exists:
        return None
    entity_id = od.get("entity_id", "")
    spec_id = od.get("spec_id") or ""
    if not spec_id:
        spec_doc = await spec_svc.create_spec(routing._spec_from_od(od, ["proofing"]), entity_id=entity_id, actor=actor.get("name", ""))  # noqa: SLF001
        spec_id = spec_doc["id"]
    item = od.get("custom_item") or {}
    sample = await smp.create_sample({
        "spec_id": spec_id, "sample_types": ["proofing"], "design_id": design["id"], "design_version": design.get("version"),
        "title": f"Proofing {design.get('code') or ''} — {od.get('customer_name', '')}",
        "brief": f"Otomatis: desain {design.get('code')} di-ACC. {_label(od)}. {od.get('reference_notes') or ''}".strip(),
        "customer_id": od.get("customer_id", ""), "target_date": od.get("expected_delivery", ""),
        "qty_requested": 3, "unit": item.get("unit") or "meter",
    }, entity_id=entity_id, actor=actor.get("name", ""))
    await db.md_samples.update_one({"id": sample["id"]}, {"$set": {
        "special_order_id": od_id, "special_order_number": od.get("number", ""),
        "customer_name": od.get("customer_name", ""), "exclusive_customer_id": od.get("customer_id", "")}})
    await db.special_orders.update_one({"id": od_id}, {
        "$set": {"spec_id": spec_id, "updated_at": now_iso()},
        "$push": {"sample_ids": sample["id"], "sample_numbers": sample.get("number", ""),
                  "status_history": {"status": od.get("status"), "timestamp": now_iso(), "user": actor.get("email", ""),
                                     "note": f"Desain {design.get('code')} ACC → proofing {sample.get('number')} dibuat otomatis"}}})
    try:
        from services import notification_service as notif
        await notif.create_addressed(roles=("md", "manager"), entity_id=entity_id, notif_type="special_order_proofing",
                                     title=f"Proofing otomatis {sample.get('number')} · {od.get('number')}",
                                     body=f"Desain {design.get('code')} di-ACC. Kirim proofing ke supplier untuk {od.get('customer_name', '')}.",
                                     severity="info", link="rnd-proofing", ref=sample["id"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[on_design_approved] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return sample
