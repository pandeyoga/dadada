"""Reservasi KEDALUWARSA dengan booking fee SUDAH dibayar (keputusan pemilik #13, docs/audit/12).

Masalah: sweeper melepas unit begitu `reserved_until` lewat — walau pembeli sudah membayar booking fee. Uangnya tertinggal di
titipan 2-1450 tanpa tugas untuk siapa pun. Kini sweeper memanggil `handle()` yang memilih perlakuan menurut kebijakan
`reservation.expiry.paid_booking_fee` (org/proyek):

  * `perpanjang` (bawaan) — unit TIDAK dilepas; `reserved_until` ditambah `extend_days`, dihitung dari yang lebih akhir antara
    jatuh tempo lama dan sekarang (supaya putaran sweeper berikutnya tidak memperpanjang lagi untuk jatuh tempo yang sama).
    Hitungan perpanjangan disimpan di deal (`reservation_extensions` + `reservation_extension_log`); dicatat dengan CAS pada
    `reserved_until` yang tadi dibaca, jadi dua putaran / dua worker tidak bisa memperpanjang dua kali. Sales + Keuangan diberi
    notifikasi dan tugas. Setelah `max_extensions` habis unit TIDAK dilepas diam-diam: tugas tindak lanjut dibuat SEKALI
    (penanda `expiry_hold` pada deal) dan unit tetap ditahan sampai manusia memutuskan (batal lewat jalur batal yang ada).
  * `antrean_refund` — unit dilepas lewat jalur yang sama (`deal_cancel.expire` → penutup bersama
    `deal_cancel_cleanup.close_deal_dependents`); uang TETAP titipan 2-1450 (tanpa jurnal baru) dan Keuangan diberi tugas +
    notifikasi untuk mengembalikannya lewat refund booking fee yang sudah ada (`POST /booking-fee/deals/{id}/refund`).
  * `hangus` — unit dilepas; sisa booking fee diakui hangus lewat jalur yang SUDAH ada (`booking_fee.refund(finalize=True)`:
    Dr 2-1450 / Cr 4-1200, idempoten lewat `source_event`). Bila langkah hangus gagal, uang tetap titipan dan Keuangan diberi tugas.

Reservasi TANPA booking fee terbayar kedaluwarsa dan dilepas seperti sebelumnya (tidak berubah). "Terbayar" dihitung dari
KUITANSI (`receipts` kind booking_fee yang bukan void) dikurangi yang sudah dikembalikan/hangus — bukan dari penanda salinan
di deal (`booking_fee_status`).
"""
import logging
from datetime import datetime, timedelta, timezone

import booking_fee as bf
import deal_cancel as dc
import policy
from core_utils import now, now_iso
from db import db
from engine import add_activity, auto_create_task, emit
from idempotency import Conflict, expect_of, transition

logger = logging.getLogger("sipro.reservation_expiry")

MODE_KEY = "reservation.expiry.paid_booking_fee"
DAYS_KEY = "reservation.expiry.extend_days"
MAX_KEY = "reservation.expiry.max_extensions"
KEYS = (MODE_KEY, DAYS_KEY, MAX_KEY)
EXTEND_SRC = "deal.expiry_extend:"
HOLD_SRC = "deal.expiry_hold:"
REFUND_SRC = "deal.expiry_refund:"
SWEEP_STATUS = ["draft", "reserved"]


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def booking_fee_held(org: str, deal_id: str) -> dict:
    """Booking fee yang MASIH di tangan perusahaan untuk deal ini, dari kuitansi (SSOT), bukan flag salinan."""
    paid = back = 0
    async for r in db.receipts.find({"org_id": org, "deal_id": deal_id,
                                     "kind": {"$in": ["booking_fee", "booking_fee_refund"]}},
                                    {"_id": 0, "kind": 1, "amount": 1, "forfeited": 1, "status": 1}):
        if r.get("kind") == "booking_fee":
            if r.get("status") != "void":
                paid += int(r.get("amount") or 0)
        else:
            back += int(r.get("amount") or 0) + int(r.get("forfeited") or 0)
    return {"paid": paid, "returned": back, "held": max(0, paid - back)}


def _parse(value) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return now()
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _overdue(deal: dict) -> bool:
    ru = deal.get("reserved_until")
    return bool(ru) and str(ru) < now_iso()


async def _tell(org: str, deal: dict, title: str, body: str, *, finance_task: tuple = None, sales_task: tuple = None,
                priority: str = "high", due: str = None) -> None:
    """Notifikasi (sales pemilik deal + Keuangan/owner) dan tugas (sales, Keuangan) — idempoten lewat `source_event`."""
    from finance_engine import notify_finance
    did, sales = deal["id"], deal.get("assigned_to")
    await notify_finance(org, title, body, "finance", "deal", did, extra_emails=[sales])
    for who, spec in ((sales, sales_task), (None, finance_task)):
        if spec:
            await auto_create_task(source_event=spec[0], title=spec[1], type="follow_up", related_entity_type="deal",
                                   related_entity_id=did, assigned_to=who, description=body, priority=priority,
                                   due_date=due, org_id=org)


async def _extend(org: str, deal: dict, fee: dict, snap: dict) -> str:
    n, mx = int(deal.get("reservation_extensions") or 0), int(snap[MAX_KEY]["value"])
    if n >= mx:
        return await _hold(org, deal, fee, n, mx, snap)
    days, ts = int(snap[DAYS_KEY]["value"]), now_iso()
    old = deal["reserved_until"]
    new = (max(_parse(old), now()) + timedelta(days=days)).isoformat()
    entry = {"n": n + 1, "of": mx, "from": old, "to": new, "days": days, "at": ts, "by": "scheduler",
             "booking_fee_held": fee["held"], "policy_snapshot": snap}
    try:   # CAS: hanya SATU pemroses per jatuh tempo (status, reserved_until, hitungan harus masih seperti yang dibaca)
        await transition("deals", {"id": deal["id"], "org_id": org},
                         {"status": {"$in": SWEEP_STATUS}, "reserved_until": old, **expect_of(deal, "reservation_extensions")},
                         {"$set": {"reserved_until": new, "reservation_extensions": n + 1, "last_extended_at": ts, "updated_at": ts},
                          "$unset": {"expiry_hold": ""}, "$push": {"reservation_extension_log": entry}},
                         what="Reservasi ini")
    except Conflict:
        return "skipped"
    unit, lead = deal.get("unit_code") or "-", deal.get("lead_name") or "pembeli"
    body = (f"Masa keep unit {unit} ({lead}) habis, tetapi booking fee {_rp(fee['held'])} SUDAH dibayar — unit TIDAK dilepas. "
            f"Masa keep diperpanjang {days} hari sampai {new[:10]} (perpanjangan {n + 1} dari maks. {mx}). Segera konfirmasi "
            "booking, atau batalkan reservasi bila pembeli mundur (Keuangan memutuskan refund/hangus booking fee).")
    try:
        await _tell(org, deal, f"Reservasi unit {unit} diperpanjang ({n + 1}/{mx}) — booking fee sudah dibayar", body,
                    sales_task=(f"{EXTEND_SRC}{deal['id']}:{n + 1}", f"Konfirmasi booking unit {unit}: reservasi diperpanjang ({n + 1}/{mx})"),
                    finance_task=(f"{EXTEND_SRC}fin:{deal['id']}:{n + 1}", f"Pantau reservasi unit {unit}: booking fee {_rp(fee['held'])} tertahan"),
                    due=new)
        await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system", actor="scheduler", org_id=org,
                           body=f"Reservasi unit {unit} DIPERPANJANG {days} hari (booking fee sudah dibayar) sampai {new[:10]}.")
        await emit("deal.reservation_extended", "deal", deal["id"], {"n": n + 1, "to": new}, org_id=org)
    except Exception:  # noqa: BLE001 — perpanjangan sudah tercatat; pemberitahuan yang gagal tidak boleh membatalkannya
        logger.exception("Pemberitahuan perpanjangan reservasi %s gagal", deal["id"])
    return "extended"


async def _hold(org: str, deal: dict, fee: dict, n: int, mx: int, snap: dict) -> str:
    """Perpanjangan habis: JANGAN lepas diam-diam. Tugas tindak lanjut SEKALI (CAS pada penanda `expiry_hold`)."""
    ts = now_iso()
    flagged = await db.deals.update_one(
        {"id": deal["id"], "org_id": org, "status": {"$in": SWEEP_STATUS}, "expiry_hold": {"$exists": False}},
        {"$set": {"expiry_hold": {"at": ts, "extensions": n, "max": mx, "booking_fee_held": fee["held"],
                                  "policy_snapshot": snap}, "updated_at": ts}})
    if flagged.matched_count != 1:
        return "held"
    unit = deal.get("unit_code") or "-"
    body = (f"Reservasi unit {unit} ({deal.get('lead_name') or 'pembeli'}) sudah diperpanjang {n}× (batas {mx}) dan booking fee "
            f"{_rp(fee['held'])} sudah dibayar. Unit TETAP DITAHAN — tidak dilepas otomatis. Putuskan: konfirmasi booking, atau "
            "batalkan reservasi (Keuangan memutuskan refund/hangus booking fee) lewat 'Batalkan Reservasi'.")
    try:
        await _tell(org, deal, f"Reservasi unit {unit}: perpanjangan habis — perlu keputusan", body,
                    sales_task=(f"{HOLD_SRC}{deal['id']}", f"Putuskan reservasi unit {unit}: perpanjangan habis, booking fee sudah dibayar"),
                    finance_task=(f"{HOLD_SRC}fin:{deal['id']}", f"Putuskan booking fee {_rp(fee['held'])} unit {unit}: reservasi tak dikonfirmasi"))
        await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system", actor="scheduler", org_id=org,
                           body=f"Perpanjangan reservasi unit {unit} habis ({n}×); unit tetap ditahan menunggu keputusan manusia.")
    except Exception:  # noqa: BLE001
        logger.exception("Tugas tindak lanjut reservasi %s gagal dibuat", deal["id"])
    return "held"


async def _queue_refund(org: str, deal: dict, fee: dict, why: str = "") -> None:
    """Uang tetap titipan 2-1450 (tanpa jurnal baru) — Keuangan diberi tugas + notifikasi untuk mengembalikannya."""
    unit = deal.get("unit_code") or "-"
    body = (f"Reservasi unit {unit} ({deal.get('lead_name') or 'pembeli'}) KEDALUWARSA dan unit dilepas; booking fee "
            f"{_rp(fee['held'])} sudah dibayar. Kembalikan ke pembeli lewat rincian booking fee deal ini "
            f"(Refund booking fee).{(' ' + why) if why else ''}")
    await _tell(org, deal, f"Booking fee {_rp(fee['held'])} menunggu refund — reservasi {unit} kedaluwarsa", body,
                finance_task=(f"{REFUND_SRC}{deal['id']}", f"Refund booking fee {_rp(fee['held'])} · unit {unit} (reservasi kedaluwarsa)"))


async def _forfeit(org: str, deal: dict, fee: dict) -> None:
    """Hangus lewat jalur yang sudah ada; idempoten (sisa refundable 0 → tidak ada yang diakui lagi)."""
    unit = deal.get("unit_code") or "-"
    out = await bf.refund(org, deal["id"], amount=0, method="transfer", actor="scheduler", finalize=True,
                          note=f"Reservasi kedaluwarsa — booking fee hangus (kebijakan {MODE_KEY}=hangus)")
    body = (f"Reservasi unit {unit} ({deal.get('lead_name') or 'pembeli'}) KEDALUWARSA; booking fee {_rp(fee['held'])} diakui "
            f"HANGUS otomatis sesuai kebijakan ({out['refund'].get('receipt_no')}).")
    await _tell(org, deal, f"Booking fee {_rp(fee['held'])} unit {unit} hangus — reservasi kedaluwarsa", body)


async def _release(org: str, deal: dict, fee: dict, mode: str, snap: dict) -> str:
    if not await dc.expire(org, deal, "scheduler"):
        return "skipped"
    outcome = mode
    try:
        if mode == "hangus":
            await _forfeit(org, deal, fee)
        else:
            await _queue_refund(org, deal, fee)
    except Exception as e:  # noqa: BLE001 — unit sudah dilepas; uang TETAP titipan dan Keuangan wajib tahu
        logger.exception("Perlakuan booking fee (%s) deal %s gagal", mode, deal["id"])
        outcome = "antrean_refund"
        await _queue_refund(org, deal, fee, f"(Langkah '{mode}' otomatis gagal: {str(e)[:150]} — putuskan manual.)")
    await db.deals.update_one({"id": deal["id"]}, {"$set": {"expiry_paid_fee": {
        "mode": mode, "outcome": outcome, "held": fee["held"], "at": now_iso(), "policy_snapshot": snap}}})
    return "released"


async def handle(org: str, deal: dict) -> str:
    """Satu deal `draft/reserved` yang lewat batas keep → 'released' | 'extended' | 'held' | 'skipped'.

    Di bawah mutex uang per-deal (sama dengan bayar/batal/refund booking fee), jadi keputusan "booking fee terbayar?"
    tidak bisa berselisih dengan pembayaran yang masuk di saat yang sama; status dibaca ulang di dalam kunci.
    """
    from deal_money import deal_money
    async with deal_money(org, deal["id"]):
        deal = await db.deals.find_one({"id": deal["id"], "org_id": org}, {"_id": 0})
        if not deal or deal.get("status") not in SWEEP_STATUS or not _overdue(deal):
            return "skipped"   # sudah dibooking/dibatalkan/diperpanjang pemroses lain
        fee = await booking_fee_held(org, deal["id"])
        if fee["held"] <= 0:   # tanpa booking fee terbayar: kedaluwarsa & dilepas seperti sebelumnya
            return "released" if await dc.expire(org, deal) else "skipped"
        snap = await policy.snapshot(KEYS, org_id=org, project_id=deal.get("project_id"))
        mode = snap[MODE_KEY]["value"]
        if mode == "perpanjang":
            return await _extend(org, deal, fee, snap)
        return await _release(org, deal, fee, mode, snap)
