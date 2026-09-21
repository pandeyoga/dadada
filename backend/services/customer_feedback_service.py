"""FEEDBACK / KOMPLAIN PELANGGAN per Sales Order (2026-09, sesi #075).

Satu catatan = satu masukan pelanggan atas satu SO: kategori, tingkat, uraian, PENANGGUNG
JAWAB (assignee), tenggat, status tindak lanjut (open → in_progress → resolved → closed),
jejak `timeline[]`. Koleksi `customer_feedbacks` SCOPED per badan usaha (warisan entitas SO).
"""
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc, timeline_entry

COLL = "customer_feedbacks"
CATEGORIES = ["kualitas", "pengiriman", "layanan", "harga", "dokumen", "lainnya"]
SEVERITIES = ["rendah", "sedang", "tinggi"]
STATUSES = ["open", "in_progress", "resolved", "closed"]
STATUS_LABEL = {"open": "Baru", "in_progress": "Ditindak", "resolved": "Selesai", "closed": "Ditutup"}
CATEGORY_LABEL = {"kualitas": "Kualitas kain", "pengiriman": "Pengiriman", "layanan": "Layanan",
                  "harga": "Harga / tagihan", "dokumen": "Dokumen", "lainnya": "Lainnya"}
_NEXT = {"open": {"in_progress", "resolved", "closed"}, "in_progress": {"resolved", "closed", "open"},
         "resolved": {"closed", "in_progress"}, "closed": set()}


class FeedbackError(Exception):
    """Pelanggaran aturan feedback (→ HTTP 400 di router)."""


async def _next_number(entity_id: str) -> str:
    from core_utils import next_doc_number
    return await next_doc_number(COLL, "number", "CF-", entity_id=entity_id or None)


async def list_feedback(scope: Dict[str, Any], *, order_id: str = "", status: str = "",
                        customer_id: str = "", assignee_id: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    flt = dict(scope or {})
    if order_id:
        flt["order_id"] = order_id
    if status:
        flt["status"] = status
    if customer_id:
        flt["customer_id"] = customer_id
    if assignee_id:
        flt["assignee_id"] = assignee_id
    rows = await db[COLL].find(flt, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [safe_doc(r) for r in rows]


async def create_feedback(payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    order = await db.sales_orders.find_one({"id": payload.get("order_id", "")}, {"_id": 0})
    if not order:
        raise FeedbackError("Pesanan (SO) tidak ditemukan.")
    title = (payload.get("title") or "").strip()
    if len(title) < 5:
        raise FeedbackError("Judul feedback wajib (min. 5 huruf).")
    category = (payload.get("category") or "lainnya").strip().lower()
    if category not in CATEGORIES:
        raise FeedbackError(f"Kategori tidak dikenal. Pilihan: {', '.join(CATEGORIES)}.")
    severity = (payload.get("severity") or "sedang").strip().lower()
    if severity not in SEVERITIES:
        raise FeedbackError(f"Tingkat tidak dikenal. Pilihan: {', '.join(SEVERITIES)}.")
    assignee_id = (payload.get("assignee_id") or "").strip()
    assignee_name = (payload.get("assignee_name") or "").strip()
    if assignee_id and not assignee_name:
        u = await db.users.find_one({"id": assignee_id}, {"_id": 0, "name": 1})
        assignee_name = (u or {}).get("name", "")
    entity_id = order.get("entity_id") or ""
    doc = {
        "id": new_id("cf"), "number": await _next_number(entity_id), "entity_id": entity_id,
        "order_id": order["id"], "order_number": order.get("number", ""),
        "customer_id": order.get("customer_id", ""), "customer_name": order.get("customer_name", ""),
        "sales_name": order.get("sales_name", ""),
        "category": category, "severity": severity, "title": title,
        "description": (payload.get("description") or "").strip(),
        "status": "in_progress" if assignee_id or assignee_name else "open",
        "assignee_id": assignee_id, "assignee_name": assignee_name,
        "due_date": (payload.get("due_date") or "").strip(),
        "resolution": "", "resolved_at": "", "closed_at": "",
        "created_by": actor.get("name", ""), "created_by_id": actor.get("id", ""),
        "created_at": now_iso(), "updated_at": now_iso(),
        "timeline": [timeline_entry("created", f"Feedback dicatat ({CATEGORY_LABEL[category]}, {severity})",
                                    actor.get("name", ""), payload.get("description") or "")],
    }
    if assignee_name:
        doc["timeline"].append(timeline_entry("assigned", f"Penanggung jawab: {assignee_name}", actor.get("name", "")))
    await db[COLL].insert_one(dict(doc))
    await db.sales_orders.update_one({"id": order["id"]}, {"$inc": {"feedback_open_count": 1}})
    return safe_doc(doc)


async def update_feedback(fb_id: str, payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    doc = await db[COLL].find_one({"id": fb_id}, {"_id": 0})
    if not doc:
        raise FeedbackError("Feedback tidak ditemukan.")
    upd: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []
    note = (payload.get("note") or "").strip()
    new_status: Optional[str] = (payload.get("status") or "").strip().lower() or None
    assignee_id = payload.get("assignee_id")
    assignee_name = payload.get("assignee_name")
    if assignee_id is not None or assignee_name is not None:
        aid = (assignee_id or "").strip()
        aname = (assignee_name or "").strip()
        if aid and not aname:
            u = await db.users.find_one({"id": aid}, {"_id": 0, "name": 1})
            aname = (u or {}).get("name", "")
        upd.update({"assignee_id": aid, "assignee_name": aname})
        events.append(timeline_entry("assigned", f"Penanggung jawab: {aname or '— (dilepas)'}", actor.get("name", ""), note))
        if doc["status"] == "open" and aname and not new_status:
            new_status = "in_progress"
    if payload.get("due_date") is not None:
        upd["due_date"] = (payload.get("due_date") or "").strip()
    if payload.get("severity"):
        sev = payload["severity"].strip().lower()
        if sev not in SEVERITIES:
            raise FeedbackError("Tingkat tidak dikenal.")
        upd["severity"] = sev
    if new_status:
        if new_status not in STATUSES:
            raise FeedbackError("Status tidak dikenal.")
        if new_status != doc["status"] and new_status not in _NEXT[doc["status"]]:
            raise FeedbackError(f"Status '{STATUS_LABEL[doc['status']]}' tidak bisa langsung ke '{STATUS_LABEL[new_status]}'.")
        if new_status in ("resolved", "closed"):
            resolution = (payload.get("resolution") or doc.get("resolution") or "").strip()
            if len(resolution) < 5:
                raise FeedbackError("Uraian penyelesaian wajib (min. 5 huruf) saat menyelesaikan/menutup.")
            upd["resolution"] = resolution
            upd["resolved_at" if new_status == "resolved" else "closed_at"] = now_iso()
        if new_status != doc["status"]:
            upd["status"] = new_status
            events.append(timeline_entry("status", f"{STATUS_LABEL[doc['status']]} → {STATUS_LABEL[new_status]}",
                                         actor.get("name", ""), note or upd.get("resolution", "")))
    elif note:
        events.append(timeline_entry("note", "Catatan tindak lanjut", actor.get("name", ""), note))
    if not upd and not events:
        raise FeedbackError("Tidak ada perubahan.")
    upd["updated_at"] = now_iso()
    await db[COLL].update_one({"id": fb_id}, {"$set": upd, "$push": {"timeline": {"$each": events}}})
    was_open = doc["status"] in ("open", "in_progress")
    now_open = upd.get("status", doc["status"]) in ("open", "in_progress")
    if was_open != now_open:
        await db.sales_orders.update_one({"id": doc["order_id"]}, {"$inc": {"feedback_open_count": 1 if now_open else -1}})
    return safe_doc(await db[COLL].find_one({"id": fb_id}, {"_id": 0}))


async def summary(scope: Dict[str, Any]) -> Dict[str, Any]:
    rows = await db[COLL].find(dict(scope or {}), {"_id": 0, "status": 1, "severity": 1, "due_date": 1}).to_list(5000)
    today = now_iso()[:10]
    return {
        "total": len(rows),
        "open": sum(1 for r in rows if r["status"] in ("open", "in_progress")),
        "tinggi_open": sum(1 for r in rows if r["status"] in ("open", "in_progress") and r.get("severity") == "tinggi"),
        "overdue": sum(1 for r in rows if r["status"] in ("open", "in_progress") and r.get("due_date") and r["due_date"] < today),
        "resolved": sum(1 for r in rows if r["status"] in ("resolved", "closed")),
    }
