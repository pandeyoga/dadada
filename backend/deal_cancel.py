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
from finance_engine import get_deposit
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


async def _release_unit(org: str, deal: dict, actor: str, reason: str) -> None:
    ts = now_iso()
    await db.units.update_one(
        {"id": deal["unit_id"], "org_id": org},
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
    await db.deals.update_one({"id": deal["id"]}, {"$set": {
        "status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": reason,
        "cancel_refund_mode": refund_mode if refundable > 0 else None, "updated_at": ts,
        **await clock.patch_for("deal", "cancelled", org_id=org, at=ts)}})
    await _release_unit(org, deal, actor, reason)
    await _void_ar(org, deal["id"], f"Reservasi dibatalkan: {reason}")
    if pv["contract"]:
        await db.contracts.update_one({"id": pv["contract"]["id"]}, {"$set": {
            "state": "cancelled", "cancelled_at": ts, "cancelled_by": actor,
            "cancel_reason": reason, "updated_at": ts}})
    import pricing_engine as pe
    await pe.release_coupon(org, ref_type="deal", ref_id=deal["id"], actor=actor)
    refund = None
    if refundable > 0:
        amount = {"full": refundable, "partial": int(refund_amount or 0), "forfeit": 0}[refund_mode]
        out = await bf.refund(org, deal["id"], amount=amount, method=method or "transfer",
                              note=note or f"Pembatalan reservasi: {reason}", actor=actor,
                              finalize=True)
        refund = out["refund"]
    else:
        await bf.cancel(org, deal["id"], actor)
    await db.tasks.update_many(
        {"org_id": org, "related_entity_type": "deal", "related_entity_id": deal["id"],
         "status": {"$nin": ["done", "cancelled"]}},
        {"$set": {"status": "cancelled", "outcome": f"Reservasi dibatalkan: {reason}",
                  "updated_at": ts}})
    lead = await db.leads.find_one({"id": deal.get("lead_id"), "org_id": org}, {"_id": 0})
    if lead and lead.get("stage") == "booking":
        other = await db.deals.find_one({"org_id": org, "lead_id": lead["id"],
                                         "status": {"$in": ["reserved", "booked", "completed"]}},
                                        {"_id": 1})
        if not other:
            await lc.record(lead, "nurturing", actor=actor, source="deal_cancel",
                            reason=f"Reservasi unit {deal.get('unit_code')} dibatalkan")
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
    return {"deal": fresh, "refund": refund, "refund_mode": refund_mode if refundable > 0 else None}
