"""Notifikasi "giliran Anda" — setiap dokumen berpindah tahap, peran yang harus bertindak
berikutnya diberi tahu di lonceng (dalam aplikasi), dan pemberitahuan tahap sebelumnya ditutup.

Cakupan tahap 1 (keputusan pemilik 2026-09): Sales Order, Purchase Order, Retur Penjualan,
Retur Pembelian, Permintaan Sampel.

Mekanisme (tahan terhadap jalur transisi yang tersebar):
  * `after_audit()` — dipanggil dari `dependencies.audit()` (fire-and-forget) → cek 1 dokumen seketika.
  * `scan()` — job terjadwal (tiap 5 menit) menyapu semua dokumen; menangkap transisi yang
    tidak lewat audit. Tanda "sudah diberi tahu" disimpan di `turn_marks` (doc, status).
"""
import asyncio
import logging
from typing import Any, Dict, List

from db import db
from core_utils import now_iso, rupiah
logger = logging.getLogger(__name__)


log = logging.getLogger("turn")

# (peran penerima, judul giliran, tautan view) per koleksi × status. Status yang tidak ada
# di peta = tidak ada "giliran" (terminal / menunggu pihak luar).
TURN_MAP: Dict[str, Dict[str, Dict[str, Any]]] = {
    "sales_orders": {
        "waiting_approval": {"roles": ("manager",), "permission": ("order", "approve"), "title": "Setujui pesanan", "link": "approvals"},
        "waiting_stock":    {"roles": ("md", "warehouse_admin"), "permission": ("purchase_requisition", "create"), "title": "Stok kurang — atur pemenuhan", "link": "orders"},
        "approved":         {"roles": ("sales_admin",), "permission": ("order", "confirm"), "owner": True, "title": "Konfirmasi pesanan ke pelanggan", "link": "orders"},
        "confirmed":        {"roles": ("warehouse", "warehouse_admin"), "permission": ("wms", "scan"), "title": "Siapkan barang (pengambilan)", "link": "operations"},
        "picked":           {"roles": ("warehouse", "warehouse_admin"), "permission": ("wms", "scan"), "title": "Kirim pesanan", "link": "operations"},
        "partially_shipped": {"roles": ("warehouse", "warehouse_admin"), "permission": ("wms", "scan"), "title": "Lanjutkan pengiriman sisa", "link": "operations"},
        "shipped":          {"roles": ("finance",), "permission": ("tax_invoice", "create"), "title": "Terbitkan faktur & tagih", "link": "finance"},
        "cancelled":        {"owner": True, "title": "Pesanan dibatalkan", "link": "orders", "severity": "warning"},
    },
    "purchase_orders": {
        # waiting_approval sudah punya notifikasi aksi khusus (notify_po_awaiting_approval).
        "pending":   {"roles": ("warehouse", "warehouse_admin"), "permission": ("wms", "scan"), "title": "PO disetujui — siapkan penerimaan barang", "link": "operations"},
        "receiving": {"roles": ("warehouse", "warehouse_admin"), "permission": ("wms", "scan"), "title": "Lanjutkan penerimaan barang PO", "link": "operations"},
        "partial":   {"roles": ("md",), "permission": ("purchase_order", "update"), "owner": True, "title": "PO diterima sebagian — tindak lanjut ke pemasok", "link": "purchase-orders"},
        "completed": {"roles": ("finance",), "permission": ("vendor_bill", "create"), "title": "PO lengkap — cocokkan tagihan pemasok", "link": "finance"},
        "rejected":  {"owner": True, "title": "PO ditolak", "link": "purchase-orders", "severity": "warning"},
    },
    "sales_returns": {
        "pending_approval": {"roles": ("manager",), "permission": ("sales_return", "approve"), "title": "Setujui retur penjualan", "link": "approvals"},
        "approved":         {"roles": ("warehouse", "warehouse_admin"), "permission": ("inspection", "inspect"), "title": "Terima barang retur & mulai inspeksi", "link": "returns"},
        "inspecting":       {"roles": ("warehouse_admin",), "permission": ("inspection", "decide"), "title": "Selesaikan inspeksi retur", "link": "returns"},
        "inspected":        {"roles": ("finance", "sales_admin"), "permission": ("sales_return", "update"), "title": "Putuskan penyelesaian retur (pengembalian dana/kredit/nego)", "link": "returns"},
        "refund_settled":   {"owner": True, "title": "Retur selesai — pengembalian dana", "link": "returns"},
        "credit_settled":   {"owner": True, "title": "Retur selesai — store credit", "link": "returns"},
        "nego_settled":     {"owner": True, "title": "Retur selesai — nego", "link": "returns"},
        "rejected":         {"owner": True, "title": "Retur ditolak", "link": "returns", "severity": "warning"},
    },
    "purchase_returns": {
        "pending_approval": {"roles": ("manager",), "permission": ("purchase_return", "approve"), "title": "Setujui retur pembelian", "link": "approvals"},
        "approved":         {"roles": ("warehouse", "warehouse_admin"), "permission": ("purchase_return", "create"), "title": "Kirim barang retur ke pemasok", "link": "purchase-returns"},
        "rejected":         {"owner": True, "title": "Retur pembelian ditolak", "link": "purchase-returns", "severity": "warning"},
    },
}
# PERAN & HAK AKSES — `roles` = niat desain semula (dokumentasi + peran bawaan yang masih memegang
# izinnya); `permission` = GERBANG yang sebenarnya. Penerima = peran (bawaan maupun kustom) yang
# memegang izin itu menurut matriks yang berlaku, minus admin (admin bukan pelaksana giliran).


async def turn_roles(rule: Dict[str, Any]) -> tuple:
    perm = rule.get("permission")
    if not perm:
        return tuple(rule.get("roles") or ())
    from services.notification_audience import roles_with_permission
    holders = set(await roles_with_permission(perm[0], perm[1]))
    # Peran pengawas (admin/manajer) memegang hampir semua izin — mereka bukan pelaksana giliran,
    # kecuali rule memang menyebutnya (mis. persetujuan).
    for oversight in ("admin", "manager"):
        if oversight not in (rule.get("roles") or ()):
            holders.discard(oversight)
    return tuple(sorted(holders))
ALIASES = {"sales_order": "sales_orders", "purchase_order": "purchase_orders", "sales_return": "sales_returns",
           "purchase_return": "purchase_returns"}
STALE_DAYS = 7   # sapuan terjadwal: dokumen yang tidak bergerak > 7 hari tidak dinotifikasi ulang
OWNER_FIELDS = ("created_by", "requested_by", "sales_id", "sales_user_id", "requested_by_id")


def _number(doc: Dict[str, Any]) -> str:
    return str(doc.get("number") or doc.get("po_number") or doc.get("code") or doc.get("id") or "")


def _party(doc: Dict[str, Any]) -> str:
    return str(doc.get("customer_name") or doc.get("supplier_name") or "")


async def _owner_user_id(doc: Dict[str, Any]) -> str:
    """created_by di data lama bisa berisi id / email / nama — cari yang cocok."""
    for f in OWNER_FIELDS:
        v = str(doc.get(f) or "").strip()
        if not v:
            continue
        u = await db.users.find_one({"$or": [{"id": v}, {"email": v}, {"name": v}]}, {"_id": 0, "id": 1})
        if u:
            return u["id"]
    return ""


async def _mark(coll: str, doc_id: str, status: str) -> bool:
    """True bila (doc, status) BELUM pernah diberi tahu (dan kini ditandai)."""
    res = await db.turn_marks.update_one(
        {"collection": coll, "doc_id": doc_id, "status": status},
        {"$setOnInsert": {"created_at": now_iso()}}, upsert=True)
    return res.upserted_id is not None


def _is_stale(doc: Dict[str, Any], days: int) -> bool:
    ts = str(doc.get("updated_at") or doc.get("created_at") or "")
    if not ts:
        return False
    try:
        from datetime import datetime, timedelta, timezone
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - t > timedelta(days=days)
    except ValueError:
        return False


async def notify_turn(coll: str, doc: Dict[str, Any], *, stale_days: int = 0) -> int:
    from services.notification_service import create_addressed, resolve_action
    status = str(doc.get("status") or "")
    rule = TURN_MAP.get(coll, {}).get(status)
    if not rule or not doc.get("id"):
        return 0
    if not await _mark(coll, doc["id"], status):
        return 0
    if stale_days and _is_stale(doc, stale_days):
        return 0   # dokumen lama saat sapuan pertama: ditandai diam-diam, tidak membanjiri lonceng
    # Tutup pemberitahuan giliran tahap sebelumnya untuk dokumen ini.
    await resolve_action("turn", f"{coll}:{doc['id']}", outcome=f"tahap → {status}", actor="sistem")
    owner = await _owner_user_id(doc) if rule.get("owner") else ""
    total = doc.get("grand_total") or doc.get("total_amount")
    body = " · ".join(x for x in [_party(doc), rupiah(float(total)) if total else "", f"tahap: {status}"] if x)
    made = await create_addressed(
        roles=await turn_roles(rule), also_users=(owner,) if owner else (),
        notif_type="turn", ref=f"turn:{coll}:{doc['id']}:{status}",
        title=f"Giliran Anda — {rule['title']}: {_number(doc)}",
        body=body, severity=rule.get("severity", "info"), link=rule.get("link", ""),
        entity_id=doc.get("entity_id"), dedupe_scope="ever",
        action_type="turn", action_id=f"{coll}:{doc['id']}")
    return len(made)


async def check_doc(coll: str, doc_id: str) -> int:
    coll = ALIASES.get(coll, coll)
    if coll not in TURN_MAP:
        return 0
    doc = await db[coll].find_one({"id": doc_id}, {"_id": 0})
    return await notify_turn(coll, doc) if doc else 0


def after_audit(entity_type: str, entity_id: str) -> None:
    """Dipanggil dari audit(): fire-and-forget, tidak pernah menggagalkan aksi bisnis."""
    coll = ALIASES.get(entity_type, entity_type)
    if coll not in TURN_MAP or not entity_id:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_safe_check(coll, entity_id))
    except RuntimeError as exc:
        logger.warning("[after_audit] efek samping gagal diabaikan: %s", exc)  # KN-C10


async def _safe_check(coll: str, doc_id: str) -> None:
    try:
        await asyncio.sleep(0.3)   # beri waktu tulisan status yang menyusul audit
        await check_doc(coll, doc_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[turn] cek %s/%s gagal: %s", coll, doc_id, exc)


async def scan(limit_per_coll: int = 500) -> Dict[str, Any]:
    created, scanned = 0, 0
    for coll, rules in TURN_MAP.items():
        cur = db[coll].find({"status": {"$in": list(rules)}}, {"_id": 0}).sort("updated_at", -1).limit(limit_per_coll)
        async for doc in cur:
            scanned += 1
            created += await notify_turn(coll, doc, stale_days=STALE_DAYS)
    return {"scanned": scanned, "created": created}


async def job_turn_scan() -> Dict[str, Any]:
    res = await scan()
    return {**res, "detail": f"{res['created']} pemberitahuan giliran baru dari {res['scanned']} dokumen"}


def turn_map_public() -> List[Dict[str, Any]]:
    return [{"collection": c, "status": s, "roles": list(r.get("roles") or ()),
             "permission": list(r.get("permission") or ()), "owner": bool(r.get("owner")), "title": r["title"]}
            for c, m in TURN_MAP.items() for s, r in m.items()]
