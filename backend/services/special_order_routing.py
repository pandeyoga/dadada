"""
special_order_routing.py — Fase 1 Special Order (OD) terstruktur:
intake tipe permintaan + spesifikasi + referensi pelanggan, lalu ROUTING otomatis saat disetujui:
  printing → Permintaan Desain (Desainer) [+ sample proofing dibuat MD setelah desain ACC]
  labdip / handfeel → Permintaan Sample R&D dengan spesifikasi diwarisi.
Rantai dokumen (OD ↔ Permintaan Desain ↔ Sample ↔ SKU ↔ PR/PO ↔ SO) dibaca lewat `chain_of`.
"""
from __future__ import annotations
import logging

from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso
from services import storage_service as storage
from services import design_request_service as dreq
from services import rnd_sample_service as smp
from services import rnd_spec_service as spec_svc
logger = logging.getLogger(__name__)


REQUEST_TYPES = ("printing", "labdip", "handfeel", "proofing")
PHASES = [
    ("draft", "Draft"), ("pending_approval", "Menunggu persetujuan"), ("approved", "Disetujui"),
    ("design", "Desain berjalan"), ("sampling", "Sampling berjalan"), ("sample_ready", "Sample siap"),
    ("customer_review", "Menunggu ACC pelanggan"), ("pricing", "Harga final"), ("confirmed", "Confirmed"),
    ("in_production", "Produksi"), ("ready", "Siap"), ("shipped", "Dikirim"), ("done", "Selesai"),
]


def _label(od: Dict[str, Any]) -> str:
    return f"Pesanan khusus {od.get('number')} · {od.get('customer_name', '')}"


async def add_reference(od: Dict[str, Any], actor: str, filename: str, content_type: str,
                        data: bytes, caption: str = "") -> Dict[str, Any]:
    ct = storage.validate_upload(filename, content_type, len(data))
    path = storage.build_path("special_orders", storage.ext_of(filename))
    await storage.put_object(path, data, ct)
    meta = {"id": new_id("odref"), "filename": filename, "content_type": ct, "size": len(data),
            "path": path, "caption": caption, "uploaded_by": actor, "uploaded_at": now_iso()}
    await db.special_orders.update_one({"id": od["id"]}, {"$push": {"references": meta}, "$set": {"updated_at": now_iso()}})
    # referensi menyusul → ikut ke permintaan desain yang sudah lahir
    if od.get("design_request_id"):
        try:
            await dreq.add_reference(od["design_request_id"], {"name": actor}, filename, ct, data, caption or _label(od))
        except Exception as exc:  # noqa: BLE001 — referensi OD tetap tersimpan walau salin gagal
            logger.warning("[add_reference] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return meta


async def reference_bytes(od: Dict[str, Any], file_id: str):
    meta = next((r for r in od.get("references") or [] if r.get("id") == file_id), None)
    if not meta:
        raise ValueError("Referensi tidak ditemukan.")
    data = await storage.get_object(meta["path"])
    if isinstance(data, tuple):
        data = data[0]
    return data, meta.get("content_type", "application/octet-stream"), meta.get("filename", file_id)


def _spec_from_od(od: Dict[str, Any], types: List[str]) -> Dict[str, Any]:
    sp = od.get("spec") or {}
    item = od.get("custom_item") or {}
    body = {
        "title": od.get("title") or item.get("description") or od.get("number"),
        "base_unit": item.get("unit") or "meter", "customer_id": od.get("customer_id", ""),
        "template_id": sp.get("template_id") or "", "sku_hint": sp.get("sku_hint") or "",
        "sample_type_hint": types[0] if types else "labdip",
        "target": {"fabric_type": sp.get("fabric_type") or "woven", "gramasi": sp.get("gramasi"), "lebar": sp.get("lebar")},
        "color_target": {"color_id": sp["color_id"]} if sp.get("color_id") else {},
        "target_price": item.get("target_price") or 0,
        "notes": " · ".join(x for x in [sp.get("color_new_note"), sp.get("notes"), f"Sumber: {_label(od)}"] if x),
        "exclusive_customer_id": od.get("customer_id", ""),
    }
    return body


async def route_on_approve(od: Dict[str, Any], actor: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
    """Dipanggil sekali saat OD disetujui penuh. Idempoten (tidak menggandakan dokumen turunan)."""
    types = [t for t in (od.get("request_types") or []) if t in REQUEST_TYPES]
    links: Dict[str, Any] = {}
    if "printing" in types and not od.get("design_request_id"):
        sp = od.get("spec") or {}
        from services import design_studio_service as _studio
        cat = (od.get("pattern_category_code") or "").strip().upper()
        dcat = (od.get("design_category_code") or "").strip().upper()
        if not cat:
            rows = await _studio.list_categories("pattern")
            cat = (rows[0] or {}).get("code", "") if rows else ""
        if not dcat:
            rows = await _studio.list_categories("design")
            dcat = (rows[0] or {}).get("code", "") if rows else ""
        payload = {"source": "customer", "customer_id": od.get("customer_id", ""),
                   "category_code": cat, "design_category_code": dcat,
                   "brief": f"{_label(od)}\n{od.get('reference_notes') or ''}\n{(od.get('custom_item') or {}).get('description', '')}".strip(),
                   "due_date": od.get("expected_delivery", ""), "submit_now": True,
                   "color_targets": [{"color_id": sp["color_id"]}] if sp.get("color_id") else [],
                   "special_order_id": od["id"], "special_order_number": od.get("number", "")}
        try:
            req = await dreq.create(payload, actor, entity_id)
            await db.design_requests.update_one({"id": req["id"]}, {"$set": {
                "special_order_id": od["id"], "special_order_number": od.get("number", ""),
                "exclusive_customer_id": od.get("customer_id", ""), "exclusive_customer_name": od.get("customer_name", "")}})
            links["design_request_id"] = req["id"]
            links["design_request_number"] = req.get("number", "")
            for r in od.get("references") or []:
                try:
                    data = await storage.get_object(r["path"])
                    if isinstance(data, tuple):
                        data = data[0]
                    await dreq.add_reference(req["id"], actor, r["filename"], r["content_type"], data, r.get("caption") or _label(od))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[route_on_approve] efek samping gagal diabaikan: %s", exc)  # KN-C10
        except Exception as exc:  # noqa: BLE001
            links["routing_errors"] = (links.get("routing_errors") or []) + [f"Permintaan desain: {exc}"]
    rnd_types = [t for t in types if t in ("labdip", "handfeel")]
    if rnd_types and not od.get("sample_ids"):
        try:
            spec_doc = await spec_svc.create_spec(_spec_from_od(od, rnd_types), entity_id=entity_id, actor=actor.get("name", ""))
            item = od.get("custom_item") or {}
            sample = await smp.create_sample({
                "spec_id": spec_doc["id"], "sample_types": rnd_types,
                "title": f"{od.get('title') or item.get('description') or 'Sample'} — {od.get('customer_name', '')}",
                "brief": f"{_label(od)}. {od.get('reference_notes') or ''} {item.get('notes') or ''}".strip(),
                "color_target": {"color_id": (od.get("spec") or {}).get("color_id")} if (od.get("spec") or {}).get("color_id") else {},
                "customer_id": od.get("customer_id", ""), "special_order_id": od["id"], "special_order_number": od.get("number", ""),
                "target_date": od.get("expected_delivery", ""), "qty_requested": 3, "unit": item.get("unit") or "meter",
            }, entity_id=entity_id, actor=actor.get("name", ""))
            await db.md_samples.update_one({"id": sample["id"]}, {"$set": {
                "special_order_id": od["id"], "special_order_number": od.get("number", ""),
                "customer_name": od.get("customer_name", ""), "exclusive_customer_id": od.get("customer_id", "")}})
            links["sample_ids"] = [sample["id"]]
            links["sample_numbers"] = [sample.get("number", "")]
            links["spec_id"] = spec_doc["id"]
        except Exception as exc:  # noqa: BLE001
            links["routing_errors"] = (links.get("routing_errors") or []) + [f"Permintaan sample: {exc}"]
    if links:
        links["routed_at"] = now_iso()
        await db.special_orders.update_one({"id": od["id"]}, {"$set": links})
    return links


async def chain_of(od: Dict[str, Any]) -> Dict[str, Any]:
    """Rantai dokumen untuk rincian OD + fase turunan."""
    out: Dict[str, Any] = {"design_request": None, "design": None, "samples": [], "products": [], "pr": None, "po": [], "so": None}
    if od.get("design_request_id"):
        req = await db.design_requests.find_one({"id": od["design_request_id"]}, {"_id": 0, "id": 1, "number": 1, "status": 1, "design_id": 1, "assigned_to_name": 1})
        out["design_request"] = req
        if req and req.get("design_id"):
            out["design"] = await db.design_gallery.find_one({"id": req["design_id"]}, {"_id": 0, "id": 1, "code": 1, "title": 1, "status": 1, "version": 1})
    if od.get("sample_ids"):
        out["samples"] = await db.md_samples.find({"id": {"$in": od["sample_ids"]}},
                                                  {"_id": 0, "id": 1, "number": 1, "title": 1, "status": 1, "sample_types": 1,
                                                   "decision.supplier_name": 1, "decision.product_sku": 1, "decision.product_id": 1, "decision.price": 1,
                                                   "revision_of_sample_id": 1, "design_code": 1, "created_at": 1,
                                                   "finished_at": 1, "delivered_to": 1, "delivered_at": 1}).to_list(20)
        out["samples"].sort(key=lambda s: s.get("created_at") or "")
        pids = [((s.get("decision") or {}).get("product_id")) for s in out["samples"] if (s.get("decision") or {}).get("product_id")]
        if pids:
            out["products"] = await db.products.find({"id": {"$in": pids}}, {"_id": 0, "id": 1, "sku": 1, "name": 1, "lifecycle": 1, "color_ref": 1, "supplier_colors": 1, "rnd_supplier": 1, "exclusive_customer_name": 1, "price": 1}).to_list(20)
    if od.get("pr_id"):
        out["pr"] = await db.purchase_requisitions.find_one({"id": od["pr_id"]}, {"_id": 0, "id": 1, "number": 1, "status": 1})
    if od.get("so_id") or od.get("sales_order_id"):
        out["so"] = await db.sales_orders.find_one({"id": od.get("so_id") or od.get("sales_order_id")}, {"_id": 0, "id": 1, "order_number": 1, "number": 1, "status": 1})
    if od.get("linked_pr_id") and not out["pr"]:
        out["pr"] = await db.purchase_requisitions.find_one({"id": od["linked_pr_id"]}, {"_id": 0, "id": 1, "number": 1, "status": 1})
    if od.get("linked_sales_order_id") and not out["so"]:
        out["so"] = await db.sales_orders.find_one({"id": od["linked_sales_order_id"]}, {"_id": 0, "id": 1, "order_number": 1, "number": 1, "status": 1})
    if od.get("linked_po_id"):
        out["po"] = await db.purchase_orders.find(
            {"id": od["linked_po_id"]}, {"_id": 0, "id": 1, "po_number": 1, "status": 1, "supplier_name": 1, "expected_delivery_date": 1, "grand_total": 1}).to_list(1)
    if od.get("linked_product_id") and not out["products"]:
        p = await db.products.find_one({"id": od["linked_product_id"]}, {"_id": 0, "id": 1, "sku": 1, "name": 1, "lifecycle": 1, "color_ref": 1, "supplier_colors": 1, "rnd_supplier": 1, "exclusive_customer_name": 1})
        out["products"] = [p] if p else []
    from services import special_order_phase2 as p2
    out["review"] = await p2.review_ready(od)
    out["pricing"] = await p2.pricing_preview(od)
    out["phase"] = _phase(od, out)
    if od.get("linked_sales_order_id"):
        out["outbound_tasks"] = await db.wms_tasks.find({"order_id": od["linked_sales_order_id"], "flow_type": "outbound"},
                                                        {"_id": 0, "id": 1, "status": 1, "quantity": 1, "shipped_qty": 1, "warehouse_name": 1}).to_list(20)
        out["shipments"] = await db.shipments.find({"order_id": od["linked_sales_order_id"]}, {"_id": 0, "id": 1, "shipment_no": 1, "status": 1, "logistics_status": 1, "created_at": 1}).to_list(20)
    types = od.get("request_types") or []
    out["phases"] = [p for p in PHASES if p[0] != "design" or "printing" in types]
    return out


def _phase(od: Dict[str, Any], chain: Dict[str, Any]) -> str:
    st = od.get("status", "draft")
    if st in ("draft", "pending_approval", "cancelled"):
        return st
    if st in ("in_production", "ready", "shipped", "done"):
        return st
    if (od.get("pricing") or {}).get("locked"):
        return "confirmed"
    if od.get("customer_decision") == "acc":
        return "pricing"
    samples = chain.get("samples") or []
    live = [s for s in samples if s.get("status") != "cancelled"]
    if live and all(s.get("status") == "decided" for s in live):
        return "customer_review" if any(s.get("delivered_at") for s in live) else "sample_ready"
    if live:
        return "sampling"
    dr = chain.get("design_request")
    if dr and dr.get("status") not in ("approved", "done", "delivered", "closed"):
        return "design"
    if chain.get("design") and chain["design"].get("status") in ("approved", "final_submitted", "active"):
        return "customer_review"
    return "approved" if st in ("approved", "confirmed") else st
