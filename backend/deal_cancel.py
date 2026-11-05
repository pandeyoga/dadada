"""Pembatalan RESERVASI/BOOKING satu klik dari profil lead (tab Unit & SPR).

Aturan:
  * DP (booking fee) BELUM dibayar → sales pemegang lead boleh membatalkan sendiri.
  * DP SUDAH dibayar → wajib admin (sales_manager / finance / finance_manager / owner /
    super_admin) dan memilih perlakuan uang: refund penuh / refund sebagian / hangus.
  * Sudah ada pembayaran TERMIN (AR) → arahkan ke pembatalan kontrak formal (Kontrak & Legal).
Efek: unit kembali `available`, tagihan BF/AR yang belum dibayar ditutup, kontrak draft
dibatalkan, kupon dilepas, tugas terkait ditutup, tahap lead mundur ke nurturing.
"""
import booking_fee as bf
import lead_lifecycle as lc
import stage_clock as clock
from core_utils import now_iso
from db import db
from engine import add_activity, dispatch_pending, emit
from finance_engine import get_deposit, notify_finance
from idempotency import Conflict
from rbac import can, has_role

ADMIN_ROLES = ("sales_manager", "finance", "finance_manager", "owner", "super_admin")
REFUND_MODES = ("full", "partial", "forfeit")


async def is_admin(user: dict) -> bool:
    return has_role(user, *ADMIN_ROLES) or await can(user.get("role"), "finance", "approve")


async def preview(org: str, deal: dict, user: dict) -> dict:
    inv = await bf.get_invoice(org, deal["id"])
    paid = int((inv or {}).get("paid") or 0)
    refundable = max(0, paid - int((inv or {}).get("refunded_total") or 0)
                     - int((inv or {}).get("forfeited_total") or 0))
    ar = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal["id"]},
                                       {"_id": 0, "id": 1, "paid": 1, "status": 1})
    ar_paid = int((ar or {}).get("paid") or 0)
    contract = await db.contracts.find_one({"org_id": org, "deal_id": deal["id"]},
                                           {"_id": 0, "id": 1, "no": 1, "state": 1})
    admin = await is_admin(user)
    requires_admin = refundable > 0
    blocked = None
    if deal.get("status") not in ("reserved", "booked"):
        blocked = f"Deal berstatus '{deal.get('status')}' tidak bisa dibatalkan dari sini."
    elif ar_paid > 0 and not contract:
        # KT-12: pesan dulu saling merujuk (di sini "pakai Pembatalan Kontrak formal", di sana
        # "kontrak belum ada, batalkan dari daftar deal"). Jalan keluarnya satu-satunya: deal
        # harus punya kontrak lebih dulu supaya potongan & utang refund bisa dihitung formal.
        rp = f"{ar_paid:,}".replace(",", ".")
        blocked = (f"Tagihan deal ini sudah menerima Rp {rp} (booking fee yang dibayar "
                   "otomatis dialihkan ke piutang termin), sehingga pembatalan satu klik tidak "
                   "tersedia. Deal belum punya kontrak: klik 'Jadikan Pembeli' lebih dulu, lalu "
                   "ajukan Pembatalan Kontrak formal di Kontrak & Legal agar potongan & utang "
                   "refund dihitung.")
    elif ar_paid > 0:
        blocked = ("Sudah ada pembayaran termin (DP/cicilan) yang diterima. Gunakan Pembatalan "
                   "Kontrak formal di Kontrak & Legal agar potongan & utang refund dihitung.")
    elif requires_admin and not admin:
        blocked = ("Booking fee sudah dibayar — pembatalan memerlukan admin (Sales Manager / "
                   "Finance) untuk memutuskan refund atau hangus.")
    return {
        "deal_id": deal["id"], "deal_status": deal.get("status"), "unit_code": deal.get("unit_code"),
        "booking_fee": {"invoice_no": (inv or {}).get("no"), "amount": int((inv or {}).get("amount") or 0),
                        "paid": paid, "refundable": refundable, "status": (inv or {}).get("status")},
        "deposit_balance": int((await get_deposit(org, deal["id"])).get("balance") or 0),
        "ar_paid": ar_paid,
        "contract": contract,
        "requires_admin": requires_admin, "is_admin": admin,
        "refund_modes": list(REFUND_MODES) if refundable > 0 else [],
        "can_cancel": blocked is None, "blocked_reason": blocked,
    }


async def _release_unit(org: str, deal: dict, actor: str, reason: str, only_deal: bool = False) -> None:
    ts = now_iso()
    filt = {"id": deal["unit_id"], "org_id": org}
    if only_deal:  # sweeper: jangan melepas unit yang kini dipegang deal LAIN
        filt["$or"] = [{"reserved_by_deal": deal["id"]}, {"deal_id": deal["id"]}]
    await db.units.update_one(
        filt,
        {"$set": {"status": "available", "reserved_by_deal": None, "booked_by_deal": None,
                  "deal_id": None, "lead_id": None, "lead_name": None, "customer_id": None,
                  "contract_id": None, "payment_status": "none", "updated_at": ts},
         "$push": {"status_history": {"status": "available", "at": ts, "actor": actor,
                                      "note": f"Reservasi dibatalkan: {reason}"}}})
    import build_engine as be
    try:
        await be.sync_unit_binding(org, deal["unit_id"])
    except Exception:  # noqa: BLE001
        pass


async def _close_tasks_and_rewind_lead(org: str, deal: dict, actor: str, ts: str, outcome: str,
                                       lead_reason: str, source: str) -> None:
    """Tugas terkait deal ditutup; lead yang tadinya `booking` mundur ke nurturing bila tak ada deal hidup."""
    await db.tasks.update_many(
        {"org_id": org, "related_entity_type": "deal", "related_entity_id": deal["id"],
         "status": {"$nin": ["done", "cancelled"]}},
        {"$set": {"status": "cancelled", "outcome": outcome, "updated_at": ts}})
    lead = await db.leads.find_one({"id": deal.get("lead_id"), "org_id": org}, {"_id": 0})
    if lead and lead.get("stage") == "booking":
        other = await db.deals.find_one({"org_id": org, "lead_id": lead["id"],
                                         "status": {"$in": ["reserved", "booked", "completed"]}},
                                        {"_id": 1})
        if not other:
            await lc.record(lead, "nurturing", actor=actor, source=source, reason=lead_reason)


async def expire(org: str, deal: dict, actor: str = "scheduler") -> bool:
    """Reservasi KEDALUWARSA (sweeper) — pelepasan SAMA dengan pembatalan (audit KT-25).

    Dulu sweeper hanya mengubah status deal + status unit: tautan basi tertinggal di unit
    (`reserved_by_deal`, `deal_id`, `lead_id`, `payment_status`), lead tetap `booking`, kupon tetap
    terpakai, dan tugas "Konfirmasi booking fee" tetap terbuka. Klaim status bersifat atomik, jadi
    reservasi yang di saat yang sama di-booking/dibatalkan tidak ikut dilepas. True bila dilepas.
    """
    ts = now_iso()
    claimed = await db.deals.update_one(
        {"id": deal["id"], "org_id": org, "status": {"$in": ["draft", "reserved"]}},
        {"$set": {"status": "expired", "expired_at": ts, "updated_at": ts}})
    if claimed.matched_count != 1:
        return False
    if deal.get("unit_id"):
        await _release_unit(org, deal, actor, "Reservasi kedaluwarsa", only_deal=True)
    import pricing_engine as pe
    await pe.release_coupon(org, ref_type="deal", ref_id=deal["id"], actor=actor)
    await bf.cancel(org, deal["id"], actor)
    await _close_tasks_and_rewind_lead(org, deal, actor, ts, "Reservasi kedaluwarsa",
                                       f"Reservasi unit {deal.get('unit_code')} kedaluwarsa", "deal_expired")
    await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system", actor=actor,
                       org_id=org, body=f"Reservasi unit {deal.get('unit_code')} KEDALUWARSA — unit dilepas ke stok.")
    await emit("deal.expired", "deal", deal["id"], {"unit_id": deal.get("unit_id")}, org_id=org)
    return True


async def _void_ar(org: str, deal_id: str, reason: str) -> None:
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal_id}, {"_id": 0})
    if not inv:
        return
    ts = now_iso()
    items = [{**it, "status": "cancelled", "cancelled_at": ts, "cancel_note": reason}
             if int(it.get("paid_amount") or 0) < int(it.get("amount") or 0) else it
             for it in inv.get("items") or []]
    await db.ar_invoices.update_one({"id": inv["id"]}, {"$set": {
        "items": items, "status": "cancelled", "outstanding": 0, "cancelled_at": ts,
        "cancel_reason": reason, "updated_at": ts}})


async def cancel(org: str, deal: dict, user: dict, *, reason: str, refund_mode: str = None,
                 refund_amount: int = None, method: str = "transfer", note: str = None) -> dict:
    pv = await preview(org, deal, user)
    if not pv["can_cancel"]:
        raise ValueError(pv["blocked_reason"])
    refundable = pv["booking_fee"]["refundable"]
    if refundable > 0:
        if refund_mode not in REFUND_MODES:
            raise ValueError("Pilih perlakuan booking fee: refund penuh, refund sebagian, atau hangus.")
        if refund_mode == "partial":
            amt = int(refund_amount or 0)
            if amt <= 0 or amt >= refundable:
                raise ValueError(f"Nominal refund sebagian harus antara Rp 1 dan Rp {refundable - 1:,}."
                                 .replace(",", "."))
    actor = user.get("email")
    ts = now_iso()
    # Audit IN-12 (pemisahan tugas): refund booking fee = KAS KELUAR. Yang boleh mengeksekusinya
    # hanya pemegang `finance:approve`. Admin lain (mis. sales_manager) tetap boleh membatalkan dan
    # memilih perlakuan uangnya, tetapi refund-nya DITUNDA untuk dieksekusi Keuangan.
    pays_cash = refundable > 0 and refund_mode in ("full", "partial")
    defer_refund = pays_cash and not await can(user.get("role"), "finance", "approve")
    # Audit IN-04: pembatalan DIKLAIM secara atomik lewat perubahan status itu sendiri. Dua permintaan
    # bersamaan (dua tab/dua staf) yang sama-sama lolos preview dulu sama-sama menjalankan refund —
    # booking fee keluar dua kali dan titipan menjadi negatif. Yang kalah mendapat 409 tanpa efek.
    claimed = await db.deals.update_one(
        {"id": deal["id"], "org_id": org, "status": {"$in": ["reserved", "booked"]}},
        {"$set": {
            "status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": reason,
            "cancel_refund_mode": refund_mode if refundable > 0 else None, "updated_at": ts,
            **({"cancel_refund_request": {"mode": refund_mode, "amount": int(refund_amount or 0),
                                          "method": method or "transfer", "requested_by": actor,
                                          "requested_at": ts}} if defer_refund else {}),
            **await clock.patch_for("deal", "cancelled", org_id=org, at=ts)}})
    if claimed.matched_count != 1:
        raise Conflict("Reservasi ini baru saja dibatalkan oleh pengguna lain. Tidak ada refund ganda "
                       "yang dibuat — muat ulang halaman untuk melihat hasilnya.")
    await _release_unit(org, deal, actor, reason)
    await _void_ar(org, deal["id"], f"Reservasi dibatalkan: {reason}")
    if pv["contract"]:
        await db.contracts.update_one({"id": pv["contract"]["id"]}, {"$set": {
            "state": "cancelled", "cancelled_at": ts, "cancelled_by": actor,
            "cancel_reason": reason, "updated_at": ts}})
    import pricing_engine as pe
    await pe.release_coupon(org, ref_type="deal", ref_id=deal["id"], actor=actor)
    refund = None
    if defer_refund:
        await notify_finance(
            org, "Refund booking fee menunggu eksekusi Keuangan",
            (f"Reservasi unit {deal.get('unit_code') or '-'} dibatalkan oleh {actor} dengan "
             f"{'refund penuh' if refund_mode == 'full' else 'refund sebagian'} booking fee "
             f"Rp {refundable:,}. Proses refund dari rincian booking fee deal ini.").replace(",", "."),
            "finance", "deal", deal["id"])
    elif refundable > 0:
        amount = {"full": refundable, "partial": int(refund_amount or 0), "forfeit": 0}[refund_mode]
        out = await bf.refund(org, deal["id"], amount=amount, method=method or "transfer",
                              note=note or f"Pembatalan reservasi: {reason}", actor=actor,
                              finalize=True)
        refund = out["refund"]
    else:
        await bf.cancel(org, deal["id"], actor)
    await _close_tasks_and_rewind_lead(org, deal, actor, ts, f"Reservasi dibatalkan: {reason}",
                                       f"Reservasi unit {deal.get('unit_code')} dibatalkan", "deal_cancel")
    mode_label = {"full": "booking fee direfund penuh", "partial": "booking fee direfund sebagian",
                  "forfeit": "booking fee hangus"}.get(refund_mode) if refundable > 0 else None
    await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system",
                       actor=actor, org_id=org,
                       body=(f"Reservasi unit {deal.get('unit_code')} DIBATALKAN: {reason}. "
                             f"Unit dilepas ke stok" + (f"; {mode_label}" if mode_label else "") + "."))
    await emit("deal.cancelled", "deal", deal["id"],
               {"unit_id": deal.get("unit_id"), "reason": reason, "refund_mode": refund_mode},
               org_id=org)
    await dispatch_pending()
    fresh = await db.deals.find_one({"id": deal["id"]}, {"_id": 0})
    return {"deal": fresh, "refund": refund, "refund_mode": refund_mode if refundable > 0 else None,
            "refund_deferred": bool(defer_refund)}
