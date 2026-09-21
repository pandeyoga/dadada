"""FB-02 — Modul Logistik (koleksi `logistics_deliveries`, SCOPED, nomor LG-).

Satu pengiriman mengangkut ≥1 Surat Jalan (`shipments`) satu pesanan/entitas.
Moda: ekspedisi (resi + biaya) · armada sendiri (kendaraan master + sopir) · diambil pelanggan
(kode pickup + identitas pengambil — TANPA alamat kirim, sopir, kendaraan).
Tahapan kirim: prepared → loaded (WAJIB foto muat) → in_transit (posisi) → delivered
(WAJIB foto POD + nama penerima) → completed; loaded/in_transit → failed (alasan).
Tahapan ambil sendiri: prepared (menunggu diambil) → delivered (serah terima tervalidasi) → completed.
"""
import logging
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from db import db
from core_utils import new_id, now_iso, safe_doc, next_doc_number
from services import storage_service as storage
from services import fleet_service as fleet
logger = logging.getLogger(__name__)


COLL = "logistics_deliveries"
MODES = {"expedition": "Ekspedisi", "own_fleet": "Armada sendiri", "self_pickup": "Diambil pelanggan"}
STATUSES = ["prepared", "loaded", "in_transit", "delivered", "completed", "failed"]
STATUS_LABEL = {"prepared": "Disiapkan", "loaded": "Dimuat", "in_transit": "Dalam perjalanan",
                "delivered": "Terkirim", "completed": "Selesai", "failed": "Gagal kirim"}
PICKUP_STATUS_LABEL = {"prepared": "Menunggu diambil", "delivered": "Diserahkan", "completed": "Selesai"}
PHOTO_KINDS = {"load": "Foto muat", "pod": "Bukti terima (POD)", "other": "Lainnya"}
TRANSITIONS = {
    "prepared": {"loaded"},
    "loaded": {"in_transit", "failed", "prepared"},   # P1-3: salah tekan "Dimuat" → bongkar (manage, alasan)
    "in_transit": {"delivered", "failed"},
    "delivered": {"completed"},
    "failed": {"prepared"},
    "completed": set(),
}
PICKUP_TRANSITIONS = {"prepared": set(), "delivered": {"completed"}, "completed": set()}

ACTIVE_STATUSES = ("prepared", "loaded", "in_transit")
HISTORY_STATUSES = ("delivered", "completed", "failed")
SHIPMENT_DISPATCHABLE = {"dispatched"}   # L-8: hanya SJ yang sudah keluar gudang boleh diangkut
WIB = ZoneInfo("Asia/Jakarta")
PICKUP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # tanpa 0/O/1/I agar tidak rancu saat dibaca
# Peran yang TIDAK boleh melihat kode pickup (mereka yang memverifikasi) — kode dibagikan
# ke pelanggan oleh sales/admin; petugas gudang hanya mencocokkan kode yang disebut pengambil.
PICKUP_CODE_HIDDEN_ROLES = {"warehouse", "driver"}


def today_wib() -> str:
    """L-1 — 'hari ini' operasional = tanggal Asia/Jakarta, bukan UTC."""
    return datetime.now(WIB).strftime("%Y-%m-%d")


def meta() -> Dict[str, Any]:
    return {"modes": MODES, "statuses": STATUSES, "status_label": STATUS_LABEL,
            "pickup_status_label": PICKUP_STATUS_LABEL, "photo_kinds": PHOTO_KINDS,
            "transitions": {k: sorted(v) for k, v in TRANSITIONS.items()},
            "vehicle_types": fleet.VEHICLE_TYPES}


def _event(action: str, by: str, note: str = "", **extra) -> Dict[str, Any]:
    return {"id": new_id("evt"), "action": action, "by": by, "at": now_iso(), "note": note, **extra}


async def _get(delivery_id: str) -> Dict[str, Any]:
    doc = await db[COLL].find_one({"id": delivery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Pengiriman tidak ditemukan.")
    return doc


def _is_pickup_order(so: Optional[Dict[str, Any]]) -> bool:
    return ((so or {}).get("fulfillment_method") or "kirim").strip().lower() == "ambil"


async def unassigned_shipments(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Surat Jalan yang belum diangkut pengiriman logistik mana pun.
    Pesanan AMBIL SENDIRI: alamat kirim TIDAK dibocorkan; moda disarankan `self_pickup`."""
    q = {**scope, "logistics_id": {"$in": [None, ""]}}
    rows = await db.shipments.find(q, {"_id": 0, "rolls": 0}).sort("created_at", -1).to_list(500)
    out = []
    for r in rows:
        so = await db.sales_orders.find_one({"id": r.get("order_id")},
                                            {"_id": 0, "customer_name": 1, "shipping_address": 1,
                                             "customer_id": 1, "fulfillment_method": 1, "pickup_date": 1,
                                             "delivery_date": 1})
        pickup = _is_pickup_order(so)
        r["customer_name"] = (so or {}).get("customer_name", "")
        r["fulfillment_method"] = "ambil" if pickup else "kirim"
        r["suggested_mode"] = "self_pickup" if pickup else "expedition"
        r["pickup_date"] = (so or {}).get("pickup_date", "") if pickup else ""
        r["delivery_date"] = "" if pickup else (so or {}).get("delivery_date", "")
        r["shipping_address"] = "" if pickup else _addr_text((so or {}).get("shipping_address"))
        out.append(safe_doc(r))
    return out


def _addr_text(v: Any) -> str:
    """`shipping_address` SO bisa dict {recipient_name, address, city, ...} → satu baris teks."""
    if isinstance(v, dict):
        return ", ".join(str(v[k]) for k in ("recipient_name", "address", "city", "province", "postal_code")
                         if v.get(k))
    return str(v or "")


def _receiver_contact(so: Dict[str, Any], customer: Optional[Dict[str, Any]], pickup: bool) -> Dict[str, str]:
    """Nama & telepon penerima: alamat kirim SO → kontak utama pelanggan → telepon pelanggan.
    Pesanan ambil sendiri melompati alamat kirim (tidak relevan & tidak boleh bocor)."""
    addr = so.get("shipping_address") if (not pickup and isinstance(so.get("shipping_address"), dict)) else {}
    name, phone = addr.get("recipient_name", ""), addr.get("phone", "")
    if not phone and customer:
        primary = next((c for c in (customer.get("contacts") or []) if c.get("is_primary")), None) \
            or next(iter(customer.get("contacts") or []), None)
        if primary:
            name, phone = name or primary.get("name", ""), primary.get("phone", "")
        phone = phone or customer.get("phone", "")
    return {"receiver_name_hint": str(name or ""), "receiver_phone": str(phone or "")}


def _validate_mode_fields(doc: Dict[str, Any]) -> None:
    if doc.get("mode") not in MODES:
        raise ValueError(f"Mode harus salah satu: {', '.join(MODES)}.")
    eta = doc.get("eta") or ""
    if eta:
        import re
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", eta):
            raise ValueError("ETA harus berformat tanggal YYYY-MM-DD.")


def _gen_pickup_code() -> str:
    return "".join(secrets.choice(PICKUP_ALPHABET) for _ in range(6))


async def _assert_driver_free(driver_user_id: str, exclude_delivery: str = "") -> None:
    if not driver_user_id:
        return
    busy = await db[COLL].find_one({"driver_user_id": driver_user_id, "status": "in_transit",
                                    "id": {"$ne": exclude_delivery}}, {"_id": 0, "number": 1})
    if busy:
        raise ValueError(f"Sopir sedang dalam perjalanan ({busy.get('number')}) — pilih sopir lain.")


async def create_delivery(payload: Dict[str, Any], actor: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
    ids = [s for s in (payload.get("shipment_ids") or []) if s]
    if not ids:
        raise ValueError("Pilih minimal 1 Surat Jalan.")
    ships = await db.shipments.find({"id": {"$in": ids}}, {"_id": 0, "rolls": 0}).to_list(100)
    if len(ships) != len(set(ids)):
        raise ValueError("Ada Surat Jalan yang tidak ditemukan.")
    for s in ships:
        if s.get("entity_id") and s["entity_id"] != entity_id:
            raise ValueError(f"Surat Jalan {s.get('shipment_no')} milik badan usaha lain.")
        if s.get("logistics_id"):
            raise ValueError(f"Surat Jalan {s.get('shipment_no')} sudah diangkut pengiriman lain.")
        if (s.get("status") or "") not in SHIPMENT_DISPATCHABLE:
            raise ValueError(f"Surat Jalan {s.get('shipment_no')} berstatus '{s.get('status') or '-'}' — "
                             f"hanya SJ yang sudah dispatch gudang yang bisa diangkut.")
    orders = {s.get("order_id") for s in ships}
    if len(orders) > 1:
        raise ValueError("Satu pengiriman hanya untuk Surat Jalan dari SATU pesanan.")
    order_id = next(iter(orders))
    so = await db.sales_orders.find_one({"id": order_id}, {"_id": 0, "order_number": 1, "number": 1,
                                                          "customer_name": 1, "customer_id": 1,
                                                          "shipping_address": 1, "fulfillment_method": 1,
                                                          "pickup_date": 1}) or {}
    pickup_order = _is_pickup_order(so)
    mode = (payload.get("mode") or "expedition").strip()
    if mode not in MODES:
        raise ValueError(f"Mode harus salah satu: {', '.join(MODES)}.")
    # VALIDASI AMBIL SENDIRI: pesanan 'ambil' WAJIB moda self_pickup (tidak boleh dikirim
    # diam-diam), dan pesanan 'kirim' TIDAK boleh diubah jadi ambil sendiri di logistik
    # (perubahan metode adalah keputusan sales di pesanan, bukan gudang).
    if pickup_order and mode != "self_pickup":
        raise ValueError("Pesanan ini adalah ORDER PENGAMBILAN (pelanggan ambil sendiri) — moda harus 'Diambil pelanggan'.")
    if not pickup_order and mode == "self_pickup":
        raise ValueError("Pesanan ini bermetode KIRIM — tidak bisa dibuat sebagai 'Diambil pelanggan'. Ubah metode pemenuhan di pesanan bila pelanggan ingin ambil sendiri.")
    customer = await db.customers.find_one({"id": so.get("customer_id")}, {"_id": 0, "phone": 1, "contacts": 1})
    contact = _receiver_contact(so, customer, pickup_order)
    is_pickup = mode == "self_pickup"
    vehicle_id = (payload.get("vehicle_id") or "").strip() if mode == "own_fleet" else ""
    vehicle_plate = (payload.get("vehicle_plate") or "").strip().upper() if mode == "own_fleet" else ""
    if vehicle_id:
        v = await fleet.assert_assignable(vehicle_id, entity_id)
        vehicle_plate = v["plate"]
    driver_user_id = (payload.get("driver_user_id") or "").strip() if mode == "own_fleet" else ""
    await _assert_driver_free(driver_user_id)
    doc = {
        "id": new_id("lgs"), "number": await next_doc_number(COLL, "number", "LG-", entity_id=entity_id),
        "entity_id": entity_id, "order_id": order_id,
        "order_number": so.get("order_number") or so.get("number") or ships[0].get("order_number", ""),
        "customer_id": so.get("customer_id", ""), "customer_name": so.get("customer_name", ""),
        "shipment_ids": ids, "shipment_nos": [s.get("shipment_no", "") for s in ships],
        "mode": mode, "fulfillment_method": "ambil" if pickup_order else "kirim",
        "courier_name": (payload.get("courier_name") or "").strip() if mode == "expedition" else "",
        "service_level": (payload.get("service_level") or "").strip() if mode == "expedition" else "",
        "tracking_no": (payload.get("tracking_no") or "").strip() if mode == "expedition" else "",
        "shipping_cost": round(float(payload.get("shipping_cost") or 0), 2) if mode == "expedition" else 0,
        "vehicle_id": vehicle_id, "vehicle_plate": vehicle_plate,
        "driver_name": (payload.get("driver_name") or "").strip() if mode == "own_fleet" else "",
        "driver_user_id": driver_user_id,
        "eta": (payload.get("eta") or "").strip() or ((so.get("pickup_date") or "") if is_pickup else ""),
        # Ambil sendiri: TIDAK ada alamat tujuan (barang tidak dikirim ke mana pun).
        "destination": "" if is_pickup else (payload.get("destination") or _addr_text(so.get("shipping_address"))).strip(),
        "receiver_phone": (payload.get("receiver_phone") or contact["receiver_phone"]).strip(),
        "receiver_name_hint": contact["receiver_name_hint"],
        "pickup_code": _gen_pickup_code() if is_pickup else "",
        "pickup_date": (so.get("pickup_date") or "") if is_pickup else "",
        "pickup_attempts": 0,
        "notes": (payload.get("notes") or "").strip(),
        "status": "prepared", "photos": [], "positions": [], "pod": None, "fail_reason": "",
        "timeline": [_event("created", actor.get("name", ""),
                            "Menunggu diambil pelanggan (kode pickup dibuat)" if is_pickup else "Pengiriman disiapkan")],
        "created_by": actor.get("name", ""), "created_at": now_iso(), "updated_at": now_iso(),
    }
    _validate_mode_fields(doc)
    await db[COLL].insert_one(dict(doc))
    await db.shipments.update_many({"id": {"$in": ids}}, {"$set": {
        "logistics_id": doc["id"], "logistics_number": doc["number"], "logistics_status": "prepared",
        "logistics_mode": mode}})
    return _enrich(safe_doc(doc))


def _status_label(doc: Dict[str, Any]) -> str:
    st = doc.get("status")
    if doc.get("mode") == "self_pickup":
        return PICKUP_STATUS_LABEL.get(st, STATUS_LABEL.get(st, st))
    return STATUS_LABEL.get(st, st)


def _enrich(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["status_label"] = _status_label(doc)
    doc["mode_label"] = MODES.get(doc.get("mode"), doc.get("mode"))
    pos = doc.get("positions") or []
    doc["last_position"] = pos[-1] if pos else None
    photos = doc.get("photos") or []
    doc["photo_counts"] = {k: sum(1 for p in photos if p.get("kind") == k) for k in PHOTO_KINDS}
    doc["is_late"] = bool(doc.get("eta")) and doc["eta"] < today_wib() and doc.get("status") in ACTIVE_STATUSES
    return doc


def redact_for(doc: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    """Kode pickup disembunyikan dari peran pemverifikasi (gudang/sopir) — mereka
    mencocokkan kode yang DISEBUT pengambil, bukan membacanya dari layar."""
    if doc and doc.get("pickup_code") and (actor or {}).get("role") in PICKUP_CODE_HIDDEN_ROLES:
        doc = {**doc, "pickup_code": "", "pickup_code_hidden": True}
    return doc


async def list_deliveries(scope: Dict[str, Any], status: str = "", q: str = "",
                          order_id: str = "", driver_user_id: str = "", mode: str = "",
                          active_only: bool = False) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = dict(scope or {})
    if status:
        sts = [s for s in status.split(",") if s]
        query["status"] = sts[0] if len(sts) == 1 else {"$in": sts}
    elif active_only:
        query["status"] = {"$in": list(ACTIVE_STATUSES)}
    if mode:
        query["mode"] = mode
    if order_id:
        query["order_id"] = order_id
    if driver_user_id:
        query["driver_user_id"] = driver_user_id
    rows = await db[COLL].find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    if driver_user_id:
        # Tugas sopir: urutan rute manual dulu (route_order), lalu ETA terdekat, lalu terbaru.
        rows.sort(key=lambda r: (r.get("route_order") or 9999, r.get("eta") or "9999-12-31", r.get("created_at") or ""))
    if q:
        s = q.lower()
        rows = [r for r in rows if any(s in str(r.get(k, "")).lower() for k in
                ("number", "order_number", "customer_name", "tracking_no", "courier_name",
                 "vehicle_plate", "driver_name")) or any(s in str(n).lower() for n in r.get("shipment_nos", []))]
    return [_enrich(safe_doc(r)) for r in rows]


async def get_delivery(delivery_id: str) -> Optional[Dict[str, Any]]:
    doc = await db[COLL].find_one({"id": delivery_id}, {"_id": 0})
    return _enrich(safe_doc(doc)) if doc else None


async def summary(scope: Dict[str, Any]) -> Dict[str, Any]:
    counts = {s: 0 for s in STATUSES}
    by_mode = {m: 0 for m in MODES}
    async for r in db[COLL].find(scope, {"_id": 0, "status": 1, "eta": 1, "mode": 1}):
        counts[r.get("status", "prepared")] = counts.get(r.get("status", "prepared"), 0) + 1
        by_mode[r.get("mode", "expedition")] = by_mode.get(r.get("mode", "expedition"), 0) + 1
    today = today_wib()
    late = await db[COLL].count_documents({**scope, "status": {"$in": list(ACTIVE_STATUSES)},
                                           "eta": {"$ne": "", "$lt": today}})
    return {"counts": counts, "by_mode": by_mode, "late": late, "total": sum(counts.values()), "today": today}


def _compact(d: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("id", "number", "order_id", "order_number", "customer_name", "mode", "mode_label", "status",
            "status_label", "eta", "is_late", "shipment_nos", "courier_name", "tracking_no", "vehicle_plate",
            "driver_name", "driver_user_id", "pickup_date", "last_position", "photo_counts", "created_at",
            "delivered_at", "completed_at", "fail_reason", "shipping_cost", "loaded_at", "departed_at", "pod")
    return {k: d.get(k) for k in keys}


async def dashboard(scope: Dict[str, Any], shipment_scope: Dict[str, Any], entity_id: Optional[str]) -> Dict[str, Any]:
    """Satu panggilan untuk Dasbor Pengiriman: angka, visual status/moda, antrean aksi cepat,
    armada, dan yang baru selesai."""
    sm = await summary(scope)
    today = sm["today"]
    active = [_compact(d) for d in await list_deliveries(scope, active_only=True)]
    active.sort(key=lambda r: (not r["is_late"], r.get("eta") or "9999-12-31", r.get("created_at") or ""))
    unassigned = await unassigned_shipments(shipment_scope)
    recent_rows = await db[COLL].find({**scope, "status": {"$in": list(HISTORY_STATUSES)}},
                                      {"_id": 0, "photos": 0, "timeline": 0, "positions": 0}) \
        .sort("updated_at", -1).to_list(8)
    fl = await fleet.availability(scope, entity_id)
    by_mode_active = {m: sum(1 for r in active if r["mode"] == m) for m in MODES}
    from datetime import timezone as _tz
    day_start_utc = datetime.fromisoformat(f"{today}T00:00:00").replace(tzinfo=WIB).astimezone(_tz.utc).isoformat()
    return {
        "today": today, "counts": sm["counts"], "by_mode": sm["by_mode"], "by_mode_active": by_mode_active,
        "total": sm["total"], "late": sm["late"],
        "kpi": {
            "active": len(active),
            "unassigned_sj": len(unassigned),
            "waiting_pickup": sum(1 for r in active if r["mode"] == "self_pickup"),
            "in_transit": sm["counts"].get("in_transit", 0),
            "eta_today": sum(1 for r in active if r.get("eta") == today),
            "late": sm["late"],
            "delivered_today": await db[COLL].count_documents({**scope, "delivered_at": {"$gte": day_start_utc}}),
            "failed_open": sm["counts"].get("failed", 0),
        },
        "active": active,
        "unassigned": unassigned[:12],
        "recent": [_compact(_enrich(safe_doc(r))) for r in recent_rows],
        "fleet": {"vehicle_summary": fl["vehicle_summary"], "driver_summary": fl["driver_summary"],
                  "vehicles": fl["vehicles"], "drivers": fl["drivers"]},
    }


async def history(scope: Dict[str, Any], date_from: str = "", date_to: str = "", mode: str = "",
                  status: str = "", q: str = "", page: int = 1, size: int = 25) -> Dict[str, Any]:
    """Riwayat pengiriman (terkirim / selesai / gagal) — saring tanggal, moda, kata kunci."""
    query: Dict[str, Any] = {**scope, "status": {"$in": [status] if status in HISTORY_STATUSES else list(HISTORY_STATUSES)}}
    if mode:
        query["mode"] = mode
    rows = await db[COLL].find(query, {"_id": 0, "photos": 0, "timeline": 0, "positions": 0}).sort("updated_at", -1).to_list(3000)

    def _when(r: Dict[str, Any]) -> str:
        return str(r.get("completed_at") or r.get("delivered_at") or r.get("updated_at") or "")[:10]
    if date_from:
        rows = [r for r in rows if _when(r) >= date_from]
    if date_to:
        rows = [r for r in rows if _when(r) <= date_to]
    if q:
        s = q.lower()
        rows = [r for r in rows if any(s in str(r.get(k, "")).lower() for k in
                ("number", "order_number", "customer_name", "tracking_no", "courier_name", "vehicle_plate", "driver_name"))
                or any(s in str(n).lower() for n in r.get("shipment_nos", []))]
    rows.sort(key=lambda r: str(r.get("completed_at") or r.get("delivered_at") or r.get("updated_at") or ""), reverse=True)
    total = len(rows)
    delivered = [r for r in rows if r.get("status") in ("delivered", "completed")]
    lead: List[float] = []
    for r in delivered:
        try:
            a = datetime.fromisoformat(str(r["created_at"]).replace("Z", "+00:00"))
            b = datetime.fromisoformat(str(r.get("delivered_at") or r.get("completed_at")).replace("Z", "+00:00"))
            lead.append(max((b - a).total_seconds() / 86400, 0))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[_when] efek samping gagal diabaikan: %s", exc)  # KN-C10
    stats = {"total": total, "delivered": len(delivered), "failed": sum(1 for r in rows if r.get("status") == "failed"),
             "avg_lead_days": round(sum(lead) / len(lead), 1) if lead else None,
             "shipping_cost_total": round(sum(float(r.get("shipping_cost") or 0) for r in rows), 2),
             "by_mode": {m: sum(1 for r in rows if r.get("mode") == m) for m in MODES}}
    start = max(page - 1, 0) * size
    return {"rows": [_compact(_enrich(safe_doc(r))) for r in rows[start:start + size]],
            "total": total, "page": page, "size": size, "stats": stats}


UPDATABLE = ("mode", "courier_name", "service_level", "tracking_no", "vehicle_plate",
             "driver_name", "driver_user_id", "eta", "destination", "notes", "receiver_phone",
             "shipping_cost", "vehicle_id")


async def update_delivery(delivery_id: str, patch: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    doc = await _get(delivery_id)
    if doc.get("status") in ("delivered", "completed"):
        raise ValueError("Pengiriman yang sudah terkirim tidak bisa diubah datanya.")
    if doc.get("mode") == "self_pickup" and patch.get("mode") not in (None, "self_pickup"):
        raise ValueError("Pengiriman ambil sendiri tidak bisa diubah menjadi dikirim di sini.")
    if patch.get("mode") == "self_pickup" and doc.get("mode") != "self_pickup":
        raise ValueError("Ubah metode pemenuhan di pesanan bila pelanggan ingin ambil sendiri.")
    upd: Dict[str, Any] = {}
    for k, v in patch.items():
        if k not in UPDATABLE or v is None:
            continue
        if k == "shipping_cost":
            upd[k] = round(float(v or 0), 2)
        elif k == "vehicle_plate":
            upd[k] = str(v).strip().upper()
        else:
            upd[k] = str(v).strip()
    if doc.get("mode") == "self_pickup":
        for k in ("destination", "vehicle_id", "vehicle_plate", "driver_name", "driver_user_id", "courier_name", "tracking_no"):
            upd.pop(k, None)
    if not upd:
        raise ValueError("Tidak ada perubahan.")
    if upd.get("vehicle_id") and upd["vehicle_id"] != doc.get("vehicle_id"):
        v = await fleet.assert_assignable(upd["vehicle_id"], doc.get("entity_id", ""))
        upd["vehicle_plate"] = v["plate"]
    if upd.get("driver_user_id") and upd["driver_user_id"] != doc.get("driver_user_id"):
        await _assert_driver_free(upd["driver_user_id"], delivery_id)
    _validate_mode_fields({**doc, **upd})
    upd["updated_at"] = now_iso()
    await db[COLL].update_one({"id": delivery_id}, {
        "$set": upd, "$push": {"timeline": _event("updated", actor_name, ", ".join(k for k in upd if k != "updated_at"))}})
    return await get_delivery(delivery_id)


async def add_photo(delivery_id: str, kind: str, filename: str, content_type: str,
                    data: bytes, note: str, actor_name: str) -> Dict[str, Any]:
    doc = await _get(delivery_id)
    if kind not in PHOTO_KINDS:
        raise ValueError(f"Jenis foto harus salah satu: {', '.join(PHOTO_KINDS)}.")
    if doc.get("status") == "completed":
        raise ValueError("Pengiriman sudah selesai — foto tidak bisa ditambah.")
    if doc.get("mode") == "self_pickup" and kind == "load":
        raise ValueError("Pengiriman ambil sendiri tidak memakai foto muat — gunakan foto bukti serah terima (POD).")
    ct = storage.validate_upload(filename, content_type, len(data))
    if not ct.startswith("image/"):
        raise ValueError("Foto harus berupa gambar (JPG/PNG/WEBP).")
    path = storage.build_path("logistics", storage.ext_of(filename))
    await storage.put_object(path, data, ct)
    photo = {"id": new_id("pho"), "kind": kind, "filename": filename, "path": path,
             "content_type": ct, "size": len(data), "note": (note or "").strip(),
             "by": actor_name, "at": now_iso()}
    await db[COLL].update_one({"id": delivery_id}, {
        "$push": {"photos": photo, "timeline": _event("photo", actor_name, PHOTO_KINDS[kind], kind=kind)},
        "$set": {"updated_at": now_iso()}})
    return safe_doc(photo)


async def get_photo_bytes(delivery_id: str, photo_id: str):
    doc = await _get(delivery_id)
    p = next((x for x in (doc.get("photos") or []) if x.get("id") == photo_id), None)
    if not p:
        raise ValueError("Foto tidak ditemukan.")
    data, ct = await storage.get_object(p["path"])
    return data, p.get("content_type") or ct


async def delete_photo(delivery_id: str, photo_id: str, actor_name: str) -> Dict[str, Any]:
    doc = await _get(delivery_id)
    if doc.get("status") in ("delivered", "completed"):
        raise ValueError("Foto pengiriman yang sudah terkirim tidak bisa dihapus (bukti).")
    if not any(x.get("id") == photo_id for x in (doc.get("photos") or [])):
        raise ValueError("Foto tidak ditemukan.")
    await db[COLL].update_one({"id": delivery_id}, {"$pull": {"photos": {"id": photo_id}},
                                                    "$set": {"updated_at": now_iso()}})
    return {"id": photo_id, "deleted": True}


async def add_position(delivery_id: str, payload: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    doc = await _get(delivery_id)
    if doc.get("mode") == "self_pickup":
        raise ValueError("Pengiriman ambil sendiri tidak punya posisi perjalanan.")
    if doc.get("status") not in ("loaded", "in_transit"):
        raise ValueError("Posisi hanya bisa dicatat saat barang sudah dimuat / dalam perjalanan.")
    lat, lng = payload.get("lat"), payload.get("lng")
    if (lat is None) != (lng is None):
        raise ValueError("Koordinat harus lengkap: lat dan lng bersama-sama.")
    if lat is not None and not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
        raise ValueError("Koordinat di luar rentang (lat -90..90, lng -180..180).")
    pos = {"id": new_id("pos"), "location": payload["location"].strip(), "note": (payload.get("note") or "").strip(),
           "lat": lat, "lng": lng, "by": actor_name, "at": now_iso()}
    await db[COLL].update_one({"id": delivery_id}, {
        "$push": {"positions": pos, "timeline": _event("position", actor_name, pos["location"])},
        "$set": {"updated_at": now_iso()}})
    return await get_delivery(delivery_id)


async def delete_position(delivery_id: str, pos_id: str, actor_name: str) -> Dict[str, Any]:
    """L-2 — koreksi posisi salah (manage). Tercatat di riwayat."""
    doc = await _get(delivery_id)
    p = next((x for x in (doc.get("positions") or []) if x.get("id") == pos_id), None)
    if not p:
        raise ValueError("Posisi tidak ditemukan.")
    await db[COLL].update_one({"id": delivery_id}, {
        "$pull": {"positions": {"id": pos_id}},
        "$push": {"timeline": _event("position_deleted", actor_name, p.get("location", ""))},
        "$set": {"updated_at": now_iso()}})
    return {"id": pos_id, "deleted": True}


async def transition(delivery_id: str, payload: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    doc = await _get(delivery_id)
    cur, to = doc.get("status"), (payload.get("to") or "").strip()
    is_pickup = doc.get("mode") == "self_pickup"
    allowed = PICKUP_TRANSITIONS if is_pickup else TRANSITIONS
    if to not in allowed.get(cur, set()):
        if is_pickup and cur == "prepared":
            raise ValueError("Pengiriman ambil sendiri hanya bisa diselesaikan lewat SERAH TERIMA (kode pickup + identitas pengambil).")
        raise ValueError(f"Dari '{_status_label(doc)}' tidak bisa ke '{STATUS_LABEL.get(to, to)}'.")
    photos = doc.get("photos") or []
    upd: Dict[str, Any] = {"status": to, "updated_at": now_iso()}
    note = (payload.get("note") or "").strip()
    if to == "loaded":
        if not any(p.get("kind") == "load" for p in photos):
            raise ValueError("Wajib unggah FOTO MUAT (barang naik kendaraan) sebelum menandai Dimuat.")
        upd["loaded_at"] = now_iso()
    elif to == "in_transit":
        if doc.get("mode") == "expedition" and not doc.get("tracking_no"):
            raise ValueError("Isi NOMOR RESI ekspedisi sebelum berangkat.")
        if doc.get("mode") == "own_fleet" and not (doc.get("vehicle_plate") and doc.get("driver_name")):
            raise ValueError("Isi PLAT KENDARAAN & NAMA SOPIR sebelum berangkat.")
        if doc.get("mode") == "own_fleet":
            if doc.get("vehicle_id"):
                await fleet.assert_assignable(doc["vehicle_id"], doc.get("entity_id", ""))
            await _assert_driver_free(doc.get("driver_user_id", ""), delivery_id)
        upd["departed_at"] = now_iso()
    elif to == "delivered":
        # L-4 — satu pesan lengkap: sebut SEMUA yang kurang.
        missing = []
        if not any(p.get("kind") == "pod" for p in photos):
            missing.append("FOTO BUKTI TERIMA (POD)")
        receiver = (payload.get("receiver_name") or "").strip()
        if not receiver:
            missing.append("NAMA PENERIMA")
        if missing:
            raise ValueError(f"Sebelum menandai Terkirim wajib: {' + '.join(missing)}.")
        upd["pod"] = {"receiver_name": receiver, "received_at": (payload.get("received_at") or now_iso()),
                      "note": note, "by": actor_name, "at": now_iso()}
        upd["delivered_at"] = now_iso()
    elif to == "failed":
        reason = (payload.get("reason") or "").strip()
        if len(reason) < 3:
            raise ValueError("Alasan gagal kirim wajib diisi.")
        upd["fail_reason"] = reason
        note = reason
    elif to == "completed":
        upd["completed_at"] = now_iso()
    elif to == "prepared" and cur == "loaded":
        reason = (payload.get("reason") or note or "").strip()
        if len(reason) < 3:
            raise ValueError("Alasan bongkar muatan (kembali ke Disiapkan) wajib diisi.")
        upd["loaded_at"] = None
        note = f"Dibongkar / kembali ke Disiapkan: {reason}"
    elif to == "prepared":
        upd["fail_reason"] = ""
        note = note or "Dijadwalkan ulang setelah gagal kirim"
    await db[COLL].update_one({"id": delivery_id}, {
        "$set": upd, "$push": {"timeline": _event("status", actor_name, note, from_status=cur, to_status=to)}})
    await db.shipments.update_many({"id": {"$in": doc.get("shipment_ids") or []}},
                                   {"$set": {"logistics_status": to}})
    # Armada: kendaraan otomatis 'dalam perjalanan' saat berangkat, dilepas saat tiba/gagal/selesai.
    if doc.get("vehicle_id"):
        if to == "in_transit":
            await fleet.mark_on_trip(doc["vehicle_id"], delivery_id)
        elif to in ("delivered", "failed", "completed", "prepared"):
            await fleet.release(doc["vehicle_id"], delivery_id)
    if to in ("delivered", "failed"):
        await _notify_sales(doc, to, note, actor_name)
    if to == "delivered" and doc.get("order_id"):
        try:
            from services import special_order_phase2 as _p2
            await _p2.on_delivered(doc["order_id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[transition] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return await get_delivery(delivery_id)


async def pickup_handover(delivery_id: str, payload: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    """Serah terima ke pelanggan yang ambil sendiri: kode pickup HARUS cocok + identitas pengambil."""
    doc = await _get(delivery_id)
    if doc.get("mode") != "self_pickup":
        raise ValueError("Serah terima hanya untuk pengiriman 'Diambil pelanggan'.")
    if doc.get("status") != "prepared":
        raise ValueError(f"Barang sudah berstatus '{_status_label(doc)}'.")
    code = (payload.get("pickup_code") or "").strip().upper().replace(" ", "").replace("-", "")
    picker = (payload.get("picker_name") or "").strip()
    id_no = (payload.get("picker_id_no") or "").strip()
    if code != (doc.get("pickup_code") or ""):
        await db[COLL].update_one({"id": delivery_id}, {
            "$inc": {"pickup_attempts": 1}, "$set": {"updated_at": now_iso()},
            "$push": {"timeline": _event("pickup_code_rejected", actor_name, f"Kode salah oleh pengambil '{picker or '-'}'")}})
        raise ValueError("KODE PICKUP SALAH — barang tidak boleh diserahkan. Minta pelanggan menunjukkan kode dari sales/konfirmasi pesanan.")
    if len(picker) < 2:
        raise ValueError("Nama pengambil wajib diisi.")
    pod = {"receiver_name": picker, "id_no": id_no, "received_at": now_iso(), "note": (payload.get("note") or "").strip(),
           "by": actor_name, "at": now_iso(), "verified_by_code": True}
    await db[COLL].update_one({"id": delivery_id}, {
        "$set": {"status": "delivered", "delivered_at": now_iso(), "pod": pod, "updated_at": now_iso()},
        "$push": {"timeline": _event("status", actor_name,
                                     f"Diserahkan ke {picker}" + (f" (ID {id_no})" if id_no else "") + " — kode pickup tervalidasi",
                                     from_status="prepared", to_status="delivered")}})
    await db.shipments.update_many({"id": {"$in": doc.get("shipment_ids") or []}}, {"$set": {"logistics_status": "delivered"}})
    await _notify_sales(doc, "delivered", f"diambil oleh {picker}", actor_name)
    return await get_delivery(delivery_id)


async def _notify_sales(doc: Dict[str, Any], to: str, note: str, actor_name: str) -> None:
    """L-9 — sales / admin sales tahu saat kiriman TERKIRIM atau GAGAL tanpa membuka Logistik."""
    try:
        from services import notification_service as notif
        label = ("DISERAHKAN" if doc.get("mode") == "self_pickup" else "TERKIRIM") if to == "delivered" else "GAGAL KIRIM"
        body = (f"{doc.get('number')} · {doc.get('order_number')} · {doc.get('customer_name')}"
                + (f" — {note}" if note else "") + f" (oleh {actor_name})")
        await notif.create_addressed(
            roles=("sales", "sales_admin"), entity_id=doc.get("entity_id"),
            notif_type=f"logistics_{to}", title=f"Pengiriman {label}: {doc.get('order_number')}",
            body=body, severity="success" if to == "delivered" else "warning",
            link="orders", ref=f"{doc.get('id')}:{to}")
    except Exception as exc:  # noqa: BLE001
        print(f"[logistics] notifikasi {to} gagal: {exc}")


async def set_my_route(ids: List[str], actor_id: str) -> int:
    """Sopir menyusun urutan tujuan miliknya sendiri: route_order = 1..n sesuai daftar."""
    n = 0
    for i, did in enumerate([x for x in ids if x], start=1):
        # L-3 — hanya pengiriman AKTIF; data mati (terkirim/selesai) tidak disentuh.
        res = await db[COLL].update_one({"id": did, "driver_user_id": actor_id,
                                         "status": {"$in": list(ACTIVE_STATUSES)}},
                                        {"$set": {"route_order": i, "updated_at": now_iso()}})
        n += res.matched_count
    return n


async def list_drivers(entity_id: str) -> List[Dict[str, Any]]:
    q = {"role": "driver", "status": {"$ne": "inactive"},
         "$or": [{"allowed_entity_ids": entity_id}, {"allowed_entity_ids": {"$in": [None, []]}}]}
    rows = await db.users.find(q, {"_id": 0, "id": 1, "name": 1, "phone": 1}).sort("name", 1).to_list(200)
    return [safe_doc(r) for r in rows]


async def for_order(order_id: str) -> List[Dict[str, Any]]:
    """Ringkasan pelacakan untuk Perjalanan Pesanan (read-only)."""
    rows = await db[COLL].find({"order_id": order_id}, {"_id": 0, "photos": 0, "timeline": 0}) \
        .sort("created_at", 1).to_list(50)
    return [_enrich(safe_doc(r)) for r in rows]
