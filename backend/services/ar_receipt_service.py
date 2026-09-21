"""AR Receipt service (EPIC3B) — Penerimaan pembayaran customer + aplikasi ke SO.

Mencatat penerimaan kas dari customer lalu meng-apply-nya ke sales_orders
(`payments[]`, `paid_total`, `payment_status`). Karena credit gate &
Collection Worklist sudah membaca `payments[]`/`payment_status`, AR otomatis
ter-update tanpa perubahan lapisan lain (lihat customer_service.compute_customer_credit).

Integrasi tambahan (audit fix):
  - P0-1: setiap penerimaan KAS (amount > 0) di-posting ke `cash_transactions`
    (direction=in, ref_type=ar_receipt). Routing: tunai → kas_kecil (per entitas),
    transfer/giro/qris → kas_besar (bank gabungan).
  - P2-5: kelebihan bayar (unapplied) → `customers.deposit_balance`; deposit dapat
    dipakai mendanai alokasi via `use_deposit_amount`.
  - P2-6: void/reversal — membalik payments[], void cash, dan koreksi deposit.

Alokasi:
  - Eksplisit: payload.allocations = [{order_id, amount}].
  - Otomatis (default): FIFO ke order terbuka tertua sampai dana habis.

Idempotensi nomor: AR-##### via next_doc_number (deletion-safe).
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pymongo import ReturnDocument

from db import db
from core_utils import new_id, now_iso, next_doc_number, safe_doc, DEFAULT_ENTITY_ID, rupiah

# Re-use kontrak AR yang sama dengan engine kredit (SSOT tunggal — hindari drift).
from services.customer_service import (
    _order_grand_total as order_grand_total,
    _order_paid as order_paid,
    order_payment_method,
    DEAD_STATUSES,
    NON_AR_METHODS,
)
from request_context import active_entity_or
logger = logging.getLogger(__name__)


EPS = 0.01
CASH_METHODS = {"cash", "tunai", "kontan"}


def _payment_status(grand_total: float, paid: float) -> str:
    if paid >= grand_total - EPS:
        return "paid"
    if paid > EPS:
        return "partial"
    return "unpaid"


# ─── Cash posting (P0-1) ─────────────────────────────────────────────────────
def _cash_routing(method: str) -> tuple:
    """(cash_type, force_all_entity) berdasar metode pembayaran (P0-1/P3-9).

    Tunai/kontan → kas_kecil (per entitas). Transfer/giro/qris → kas_besar (bank).

    FASE E-7 (E7.4): elemen kedua **selalu False** sekarang. `kas_besar` berarti
    "buku bank", BUKAN "milik grup" — uangnya tetap milik badan usaha penerbit
    kwitansi. Sebelum ini penerimaan `KSC/AR-0000x` tercatat `entity_id="all"`
    sehingga kas PT Kain Suka Cita terlihat kosong padahal uangnya masuk.
    """
    if (method or "").lower() in CASH_METHODS:
        return "kas_kecil", False
    return "kas_besar", False


async def _post_cash_in(receipt: Dict[str, Any], actor: Dict[str, Any]) -> Optional[str]:
    """Posting kas masuk untuk penerimaan AR. Mengembalikan id cash_transaction."""
    amt = round(float(receipt.get("amount", 0) or 0), 2)
    if amt <= EPS:
        return None
    cash_type, force_all = _cash_routing(receipt.get("method", ""))
    # E7.4 — pemilik uang = badan usaha kwitansinya (tidak ada lagi kas grup).
    from services.cash_entity_service import resolve_owner
    entity_id = resolve_owner(receipt.get("entity_id"), DEFAULT_ENTITY_ID,
                              what="Kas masuk kwitansi")
    number = await next_doc_number("cash_transactions", "number", "CASH-", entity_id=entity_id)
    cdoc = {
        "id": new_id("cash"),
        "number": number,
        "cash_type": cash_type,
        "direction": "in",
        "amount": amt,
        "category": "penagihan",
        "description": f"Penerimaan {receipt.get('number')} — {receipt.get('customer_name', '')}",
        "entity_id": entity_id,
        "ref_type": "ar_receipt",
        "ref_id": receipt["id"],
        "txn_date": receipt.get("receipt_date") or now_iso(),
        "status": "posted",
        "created_by": actor.get("name", "system"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.cash_transactions.insert_one(cdoc)
    # KN-G3: jurnal kas diposting SEKARANG (bukan menunggu backfill saat startup) supaya
    # saldo Piutang & Uang Muka Pelanggan langsung benar — penting sejak keputusan selisih
    # pembayaran (FASE G-3) bisa menjurnal di detik yang sama. Idempotent.
    try:
        from services import gl_service as _gl
        await _gl.post_cash_transaction(cdoc)
    except Exception as exc:  # noqa: BLE001 — kwitansi tetap sah; backfill akan menyusul
        logger.warning("[_post_cash_in] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return cdoc["id"]


# ─── Deposit (P2-5) ──────────────────────────────────────────────────────────
async def get_deposit_balance(customer_id: str) -> float:
    c = await db.customers.find_one({"id": customer_id}, {"_id": 0, "deposit_balance": 1})
    return round(float((c or {}).get("deposit_balance", 0) or 0), 2)


async def _adjust_deposit(customer_id: str, delta: float) -> None:
    if abs(delta) < EPS:
        return
    pred: Dict[str, Any] = {"id": customer_id}
    if delta < 0:
        # KN-B08 — pemakaian deposit berprasyarat saldo cukup (CAS): dua pemakaian
        # bersamaan tidak bisa membuat deposit negatif.
        pred["deposit_balance"] = {"$gte": round(-delta, 2) - EPS}
    res = await db.customers.update_one(
        pred, {"$inc": {"deposit_balance": round(delta, 2)}, "$set": {"updated_at": now_iso()}})
    if res.matched_count == 0 and delta < 0:
        raise HTTPException(status_code=409, detail="Deposit pelanggan tidak cukup (baru saja terpakai proses lain).")


async def adjust_deposit(customer_id: str, delta: float) -> None:
    """FASE G-3 — penyesuaian deposit dari keputusan selisih pembayaran (publik)."""
    await _adjust_deposit(customer_id, delta)


async def apply_from_deposit(order_id: str, amount: float, decision_id: str,
                            decision_number: str, receipt_number: str,
                            actor: Dict[str, Any]) -> Dict[str, Any]:
    """FASE G-3 — pakai kelebihan bayar (deposit) untuk melunasi pesanan LAIN.

    Sama seperti alokasi kwitansi biasa (guard $expr anti-dobel), hanya sumber dananya
    deposit — bukan kas baru. Jurnalnya diposting oleh keputusan selisih
    (`Dr 2-1400 / Cr 1-1200`), bukan oleh kwitansi.
    """
    res = await _apply_to_order(order_id, amount, decision_id,
                               f"{decision_number} (dari kelebihan bayar {receipt_number})",
                               "deposit", now_iso())
    try:
        from services import payment_plan_service as _plans
        await _plans.recompute_for_doc("sales_order", order_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[apply_from_deposit] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return res


async def apply_from_bank_holding(order_id: str, amount: float, line_id: str,
                                  cash_number: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    """FASE G-8 — pakai **titipan dana** (dana masuk yang baru teridentifikasi) untuk
    melunasi pesanan.

    Pola sama dengan `apply_from_deposit` (G-3): outstanding pesanan berkurang, tetapi
    TIDAK ada kas baru — kasnya sudah diakui saat dana dititipkan (Dr Bank / Cr 2-1950).
    Jurnal alokasinya (`Dr 2-1950 / Cr 1-1200`) diposting oleh modul rekonsiliasi bank,
    bukan oleh kwitansi, supaya uang yang sama tidak pernah terhitung dua kali.
    """
    res = await _apply_to_order(order_id, amount, line_id,
                               f"{cash_number or line_id} (titipan dana bank)",
                               "bank_holding", now_iso())
    try:
        from services import payment_plan_service as _plans
        await _plans.recompute_for_doc("sales_order", order_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[apply_from_bank_holding] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return res


async def apply_from_case(order_id: str, amount: float, case_id: str,
                          case_number: str, method: str = "finance_case") -> Dict[str, Any]:
    """FASE G-9 — pelunasan pesanan dari **penyelesaian kasus keuangan**.

    Pola sama dengan `apply_from_deposit` (G-3) & `apply_from_bank_holding` (G-8):
    outstanding pesanan berkurang, tetapi TIDAK ada kas baru — kas/jurnalnya diurus
    playbook kasus (mis. `Dr 1-1280 Piutang Titipan Karyawan / Cr 1-1200 Piutang`).
    Dipisah supaya sumber uang selalu terbaca di riwayat pembayaran pesanan.
    """
    res = await _apply_to_order(order_id, amount, case_id,
                               f"{case_number or case_id} (kasus keuangan)", method, now_iso())
    try:
        from services import payment_plan_service as _plans
        await _plans.recompute_for_doc("sales_order", order_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[apply_from_case] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return res


async def unapply_for_case(order_id: str, amount: float, case_id: str,
                           case_number: str) -> Dict[str, Any]:
    """FASE G-9 — TARIK alokasi pembayaran dari pesanan yang salah (append-only).

    Kwitansi tidak dibatalkan dan baris pembayaran lama tidak dihapus: ditambahkan
    baris **pengurang bernilai negatif** yang menyebut kasusnya, sehingga auditor
    membaca dua kejadian (salah tempel, lalu dipindahkan) — bukan sejarah yang berubah.
    """
    o = await db.sales_orders.find_one({"id": order_id}, {"_id": 0})
    if not o:
        raise HTTPException(status_code=404, detail=f"Order {order_id} tidak ditemukan")
    amt = round(float(amount or 0), 2)
    paid = round(order_paid(o), 2)
    if amt <= 0:
        raise HTTPException(status_code=400, detail="Nominal harus lebih dari 0")
    if amt > paid + EPS:
        raise HTTPException(
            status_code=400,
            detail=(f"Penarikan {rupiah(amt)} melebihi yang sudah dibayar di pesanan "
                    f"{o.get('number')} ({rupiah(paid)})"))
    entry = {"id": new_id("pay"), "amount": -amt, "receipt_id": case_id,
             "receipt_number": f"{case_number or case_id} (dipindahkan lewat kasus)",
             "method": "realokasi", "date": now_iso(), "created_at": now_iso()}
    updated = await db.sales_orders.find_one_and_update(
        {"id": order_id,
         "$expr": {"$gte": [{"$add": [{"$sum": "$payments.amount"}, -amt]}, -EPS]}},
        {"$push": {"payments": entry}, "$inc": {"paid_total": -amt},
         "$set": {"updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        raise HTTPException(
            status_code=409,
            detail=(f"Penarikan alokasi pesanan {o.get('number')} gagal — nilai terbayar "
                    "berubah. Muat ulang lalu coba lagi."))
    gt = order_grand_total(updated)
    new_paid = round(order_paid(updated), 2)
    status = _payment_status(gt, new_paid)
    if updated.get("payment_status") != status:
        await db.sales_orders.update_one({"id": order_id}, {"$set": {"payment_status": status}})
    try:
        from services import payment_plan_service as _plans
        await _plans.recompute_for_doc("sales_order", order_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[unapply_for_case] efek samping gagal diabaikan: %s", exc)  # KN-C10
    return {"order_id": order_id, "order_number": o.get("number", order_id),
            "unapplied": amt, "outstanding_after": round(gt - new_paid, 2),
            "payment_status": status, "entity_id": o.get("entity_id", "")}


async def list_open_orders(customer_id: str) -> List[Dict[str, Any]]:
    """Order AR terbuka (ada outstanding) untuk customer, tertua dulu (FIFO)."""
    orders = await db.sales_orders.find({"customer_id": customer_id}, {"_id": 0}).to_list(2000)
    rows = []
    for o in orders:
        if o.get("status") in DEAD_STATUSES:
            continue
        if order_payment_method(o) in NON_AR_METHODS:
            continue
        gt = order_grand_total(o)
        paid = order_paid(o)
        outstanding = round(gt - paid, 2)
        if outstanding <= EPS:
            continue
        rows.append({
            "order_id": o["id"],
            "entity_id": o.get("entity_id", ""),
            "number": o.get("number", o["id"]),
            "grand_total": round(gt, 2),
            "paid_total": round(paid, 2),
            "outstanding": outstanding,
            "payment_status": o.get("payment_status") or _payment_status(gt, paid),
            "created_at": o.get("created_at"),
        })
    rows.sort(key=lambda r: str(r.get("created_at") or ""))
    return rows


async def _validate_allocation_target(order_id: str, amount: float, *,
                                      customer_id: str, entity_id: str) -> Dict[str, Any]:
    """F-05/F-06 — periksa order tujuan TANPA menulis: ada, milik pelanggan & badan usaha
    kwitansi, dan tidak melebihi outstanding. Dipanggil untuk SEMUA alokasi sebelum
    satu pun order dimutasi, supaya kegagalan alokasi ke-2 tidak meninggalkan
    pembayaran yatim di order ke-1."""
    o = await db.sales_orders.find_one({"id": order_id}, {"_id": 0})
    if not o:
        raise HTTPException(status_code=404, detail=f"Order {order_id} tidak ditemukan")
    if customer_id and o.get("customer_id") and o["customer_id"] != customer_id:
        raise HTTPException(
            status_code=400,
            detail=(f"Order {o.get('number', order_id)} milik pelanggan lain — kwitansi hanya "
                    f"boleh dialokasikan ke pesanan pelanggan yang sama."))
    if entity_id and entity_id != "all" and o.get("entity_id") and o["entity_id"] != entity_id:
        raise HTTPException(
            status_code=403,
            detail=(f"Order {o.get('number', order_id)} milik badan usaha lain — piutangnya "
                    f"tidak boleh dilunasi lewat kwitansi badan usaha ini."))
    gt = order_grand_total(o)
    outstanding = round(gt - order_paid(o), 2)
    if amount > outstanding + EPS:
        raise HTTPException(
            status_code=400,
            detail=f"Alokasi {rupiah(amount)} melebihi outstanding order {o.get('number')} ({rupiah(outstanding)})",
        )
    return o


async def _unapply_receipt(receipt_id: str, applied: List[Dict[str, Any]]) -> None:
    """F-06 — kompensasi: cabut payments[] ber-receipt_id ini dari order yang sudah dimutasi."""
    for a in applied:
        await db.sales_orders.update_one(
            {"id": a["order_id"]},
            {"$pull": {"payments": {"receipt_id": receipt_id}},
             "$inc": {"paid_total": -float(a.get("applied") or 0)},
             "$set": {"updated_at": now_iso()}})
        o = await db.sales_orders.find_one({"id": a["order_id"]}, {"_id": 0})
        if o:
            await db.sales_orders.update_one(
                {"id": a["order_id"]},
                {"$set": {"payment_status": _payment_status(order_grand_total(o), order_paid(o))}})


async def _apply_to_order(order_id: str, amount: float, receipt_id: str,
                          receipt_number: str, method: str, receipt_date: str,
                          plan_line_seq: int = 0, customer_id: str = "",
                          entity_id: str = "") -> Dict[str, Any]:
    o = await _validate_allocation_target(order_id, amount, customer_id=customer_id,
                                          entity_id=entity_id)
    gt = order_grand_total(o)
    amt = round(float(amount), 2)
    payment = {
        "id": new_id("pay"),
        "amount": amt,
        "receipt_id": receipt_id,
        "receipt_number": receipt_number,
        "method": method,
        "date": receipt_date,
        "created_at": receipt_date,
    }
    # FASE G-3 — pembayaran bisa MENYEBUT baris jadwal tujuan ("ini untuk cicilan ke-3").
    if int(plan_line_seq or 0) > 0:
        payment["plan_line_seq"] = int(plan_line_seq)
    # INV-CONC-01 (KN-077-RACE-AR-RECEIPT P1): $push ATOMIK + guard $expr, JANGAN $set seluruh
    # array (lost-update/clobber). SSOT `paid` = Σ payments[].amount (lihat _order_paid), maka
    # guard membandingkan (Σ payments + amount) <= grand_total. K receipt-penuh paralel utk satu
    # outstanding → hanya 1 lolos; sisanya no-match → 409 (tak ada penerimaan yang hilang/dobel).
    updated = await db.sales_orders.find_one_and_update(
        {"id": order_id,
         "$expr": {"$lte": [{"$add": [{"$sum": "$payments.amount"}, amt]}, gt + EPS]}},
        {"$push": {"payments": payment},
         "$inc": {"paid_total": amt},
         "$set": {"updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        raise HTTPException(
            status_code=409,
            detail=(f"Alokasi ke order {o.get('number')} gagal — outstanding berubah "
                    f"(kemungkinan penerimaan paralel). Muat ulang lalu coba lagi."))
    new_paid = round(order_paid(updated), 2)   # SSOT: Σ payments[].amount
    status = _payment_status(gt, new_paid)
    if updated.get("payment_status") != status:
        await db.sales_orders.update_one({"id": order_id}, {"$set": {"payment_status": status}})
    return {"order_id": order_id, "order_number": o.get("number", order_id),
            "applied": amt, "outstanding_after": round(gt - new_paid, 2),
            "payment_status": status,
            "entity_id": o.get("entity_id", ""),
            "plan_line_seq": int(plan_line_seq or 0)}


async def create_receipt(payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    customer = await db.customers.find_one({"id": payload.get("customer_id")}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")

    amount = round(float(payload.get("amount", 0) or 0), 2)              # kas baru diterima
    use_deposit_amount = round(float(payload.get("use_deposit_amount", 0) or 0), 2)  # dana dari deposit (P2-5)
    if amount < 0 or use_deposit_amount < 0:
        raise HTTPException(status_code=400, detail="Jumlah pembayaran tidak valid")

    deposit_avail = await get_deposit_balance(customer["id"])
    if use_deposit_amount > deposit_avail + EPS:
        raise HTTPException(
            status_code=400,
            detail=f"Deposit tidak cukup (tersedia {rupiah(deposit_avail)})")

    total_funds = round(amount + use_deposit_amount, 2)
    if total_funds <= EPS:
        raise HTTPException(status_code=400, detail="Jumlah pembayaran harus > 0")

    method = (payload.get("method") or "transfer").strip().lower()
    receipt_date = payload.get("receipt_date") or now_iso()
    # FASE E-1 (E1.10) — kwitansi milik badan usaha pelanggan/konteks, bukan default.
    entity_id = (payload.get("entity_id") or customer.get("entity_id")
                 or active_entity_or(DEFAULT_ENTITY_ID))

    receipt_id = new_id("arc")
    number = await next_doc_number("ar_receipts", "number", "AR-", entity_id=entity_id)

    # FASE G-3 — hitung SELISIH PEMBAYARAN sebelum alokasi mengubah outstanding.
    # `expected` selalu dihitung server-side dari tagihan yang jatuh tempo, sehingga
    # sisi klien tidak bisa mengarang angka "seharusnya".
    from services import payment_variance_service as pvs
    explicit = payload.get("allocations") or []
    assessment = await pvs.pre_assess(customer["id"], total_funds, explicit,
                                      as_of=receipt_date, entity_id=entity_id)

    # Tentukan alokasi (dibatasi total dana = kas baru + deposit dipakai)
    allocations: List[Dict[str, Any]] = []
    if explicit:
        total_alloc = round(sum(float(a.get("amount", 0) or 0) for a in explicit), 2)
        if total_alloc > total_funds + EPS:
            raise HTTPException(status_code=400, detail="Total alokasi melebihi dana (kas + deposit)")
        # F-05/F-06 — validasi SEMUA target dulu (pemilik, entitas, outstanding) tanpa menulis.
        planned = [(a["order_id"], round(float(a.get("amount", 0) or 0), 2),
                    int(a.get("plan_line_seq") or 0)) for a in explicit
                   if round(float(a.get("amount", 0) or 0), 2) > 0]
        seen_amounts: Dict[str, float] = {}
        for oid, amt, _seq in planned:
            seen_amounts[oid] = round(seen_amounts.get(oid, 0.0) + amt, 2)
        for oid, amt_total in seen_amounts.items():
            await _validate_allocation_target(oid, amt_total, customer_id=customer["id"],
                                              entity_id=entity_id)
        for oid, amt, seq in planned:
            try:
                allocations.append(await _apply_to_order(
                    oid, amt, receipt_id, number, method, receipt_date,
                    plan_line_seq=seq, customer_id=customer["id"], entity_id=entity_id))
            except HTTPException:
                # F-06 — alokasi tengah gagal (mis. balapan 409): cabut yang sudah tertulis
                # supaya tidak ada pembayaran yatim tanpa kwitansi.
                await _unapply_receipt(receipt_id, allocations)
                raise
    else:
        remaining = total_funds
        for oo in await list_open_orders(customer["id"]):
            if remaining <= EPS:
                break
            if entity_id and entity_id != "all" and oo.get("entity_id") \
                    and oo["entity_id"] != entity_id:
                continue
            take = min(remaining, oo["outstanding"])
            if take <= EPS:
                continue
            try:
                allocations.append(await _apply_to_order(
                    oo["order_id"], take, receipt_id, number, method, receipt_date,
                    customer_id=customer["id"], entity_id=entity_id))
            except HTTPException:
                await _unapply_receipt(receipt_id, allocations)
                raise
            remaining = round(remaining - take, 2)

    applied_total = round(sum(a["applied"] for a in allocations), 2)
    unapplied = round(total_funds - applied_total, 2)
    # Perubahan deposit: deposit terpakai berkurang, sisa tak teralokasi masuk deposit (P2-5).
    deposit_delta = round(unapplied - use_deposit_amount, 2)

    doc = {
        "id": receipt_id,
        "number": number,
        "customer_id": customer["id"],
        "customer_name": customer.get("name", ""),
        "entity_id": entity_id,
        "receipt_date": receipt_date,
        "method": method,
        "amount": amount,
        "used_deposit": use_deposit_amount,
        "total_funds": total_funds,
        "applied_total": applied_total,
        "unapplied_amount": unapplied,
        "deposit_delta": deposit_delta,
        "allocations": allocations,
        "notes": payload.get("notes", ""),
        "status": "posted",
        # FASE G-3 — catatan selisih pembayaran (bahan antrean keputusan & INV-VAR).
        "variance": pvs.variance_block(assessment),
        "created_by": actor.get("id"),
        "created_by_name": actor.get("name", ""),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.ar_receipts.insert_one(doc)
    # FASE G-4 — kwitansi menaut ke SETIAP pesanan yang dilunasinya (dua arah).
    from services import doc_refs_service as _refs
    for _al in allocations or []:
        if _al.get("order_id"):
            await _refs.safe_link(("ar_receipt", receipt_id), ("sales_order", _al["order_id"]),
                                  "settles", note="pembayaran dialokasikan ke pesanan")
            # FASE G-2 — jadwal pembayaran (rencana) ikut diperbarui: total terbayar
            # dialokasikan berurutan ke barisnya. Turunan, jadi kegagalan tak boleh
            # menggagalkan kwitansi.
            try:
                from services import payment_plan_service as _plans
                await _plans.recompute_for_doc("sales_order", _al["order_id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("[create_receipt] efek samping gagal diabaikan: %s", exc)  # KN-C10

    # P0-1 — posting kas masuk (hanya untuk kas baru; deposit bukan kas baru).
    cash_txn_id = await _post_cash_in(doc, actor)
    if cash_txn_id:
        doc["cash_txn_id"] = cash_txn_id
        await db.ar_receipts.update_one({"id": receipt_id}, {"$set": {"cash_txn_id": cash_txn_id}})

    # F-01 (audit 2026-09-02) — order yang menjadi berpendapatan karena pembayaran ini
    # (kebijakan `_revenue_eligible`) dijurnal SEKARANG, bukan menunggu restart.
    for _al in allocations or []:
        try:
            from services import gl_service as _gl
            await _gl.post_order_revenue_and_cogs(_al["order_id"])
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger("ar_receipt").error(
                "GL pendapatan order %s gagal setelah kwitansi %s: %s",
                _al.get("order_id"), number, exc)

    # P2-5 — sesuaikan saldo deposit customer.
    await _adjust_deposit(customer["id"], deposit_delta)

    # ── FASE G-3 — selesaikan selisih pembayaran ────────────────────────────
    # Di dalam toleransi → diputus OTOMATIS (tetap berlabel, tetap bisa diaudit).
    # Di luar toleransi → keputusan eksplisit bila petugas sudah memilih di dialog,
    # kalau belum: kwitansi masuk antrean "Selisih Bayar" (tidak ada yang senyap).
    decision = None
    v = doc.get("variance") or {}
    try:
        if v.get("direction") == pvs.DIR_ROUNDING:
            decision = await pvs.auto_resolve_receipt(doc, actor)
        elif v.get("needs_decision") and (payload.get("variance") or {}).get("kind"):
            decision = await pvs.decide_receipt(receipt_id, payload["variance"], actor)
    except pvs.VarianceError as exc:
        # Keputusan gagal (mis. wewenang kurang) TIDAK boleh membatalkan uang yang sudah
        # masuk — kwitansi tetap sah dan selisihnya menunggu di antrean, lengkap dg sebab.
        await db.ar_receipts.update_one({"id": receipt_id}, {"$set": {
            "variance.decision_error": str(exc), "updated_at": now_iso()}})
    fresh = await db.ar_receipts.find_one({"id": receipt_id}, {"_id": 0})
    out = safe_doc(fresh or doc)
    if decision:
        out["variance_decision"] = decision
    return out


async def void_receipt(receipt_id: str, actor: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """Batalkan penerimaan AR (P2-6): balik payments[], void kas, koreksi deposit.

    `reason` (FASE P5) disimpan sebagai `voided_reason` — pembatalan ini membalik uang
    yang sudah tercatat masuk, jadi sebabnya bagian dari dokumennya, bukan catatan lisan.
    """
    r = await db.ar_receipts.find_one({"id": receipt_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Receipt tidak ditemukan")
    if r.get("status") == "void":
        raise HTTPException(status_code=409, detail="Receipt sudah di-void")

    # INV-ATOMIC-01 (T-01 Opsi B) — klaim kwitansi SEBELUM payments SO / kas / deposit dibalik:
    # dua void bersamaan (tombol ganda / layar lain) tidak boleh membalik uang dua kali.
    from services import atomic_claim as _saga
    await _saga.claim("ar_receipts", receipt_id, "ar_receipt_void",
                      precondition={"status": {"$ne": "void"}}, actor=actor.get("name", ""))

    # FASE G-3 — keputusan selisih pembayaran yang sudah dijalankan HARUS dibalik lebih
    # dulu, kalau tidak akan ada piutang "terhapus" / dana "dikembalikan" atas uang yang
    # ternyata tidak pernah ada. Jejak keputusannya tetap tersimpan (append-only).
    _decision_id = ((r.get("variance") or {}).get("decision_id") or "").strip()
    if _decision_id:
        from services import payment_variance_service as _pvs
        try:
            await _pvs.reverse_decision(
                _decision_id, f"kwitansi {r.get('number', '')} dibatalkan", actor)
        except HTTPException:
            await _saga.release("ar_receipts", receipt_id)
            raise
        except _pvs.VarianceError as exc:
            await _saga.release("ar_receipts", receipt_id)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        r = await db.ar_receipts.find_one({"id": receipt_id}, {"_id": 0}) or r

    # 1) Balik payments[] tiap order yang terdampak → recompute paid_total/status.
    reversed_orders: List[Dict[str, Any]] = []
    for alloc in (r.get("allocations") or []):
        oid = alloc.get("order_id")
        o = await db.sales_orders.find_one({"id": oid}, {"_id": 0})
        if not o:
            continue
        # KEB-PDPT — bila uang muka kwitansi ini sudah direklas ke Piutang (pesanan sudah
        # dikirim), porsinya dikembalikan dulu supaya jurnal void kas menutup dengan benar.
        _adv = round(sum(float(p.get("amount") or 0) for p in (o.get("payments") or [])
                         if p.get("receipt_id") == receipt_id
                         and p.get("gl_bucket") == "advance"), 2)
        if _adv > EPS:
            try:
                from services import gl_service as _gl
                await _gl.post_advance_reclass_reversal(o, receipt_id, _adv,
                                                        label=f"void {r.get('number', '')}")
            except Exception as exc:  # noqa: BLE001 — kwitansi tetap di-void; jejak untuk audit
                import logging
                logging.getLogger("ar_receipt").error(
                    "Pembalik reklas uang muka %s untuk order %s gagal: %s", receipt_id, oid, exc)
        payments = [p for p in (o.get("payments") or []) if p.get("receipt_id") != receipt_id]
        # KN-B25 — baris NEGATIF hasil realokasi kasus (bertanda id kasus, method
        # 'realokasi') tertinggal saat kwitansi asalnya di-void → piutang melebihi nilai
        # pesanan. Bila sisa pembayaran menjadi negatif, baris realokasi ikut dinetralkan
        # (tercatat di hasil void) sehingga paid_total tidak pernah < 0.
        _dropped_realloc: List[Dict[str, Any]] = []
        while round(sum(float(p.get("amount", 0) or 0) for p in payments), 2) < -EPS:
            neg = [p for p in payments if float(p.get("amount", 0) or 0) < 0 and p.get("method") == "realokasi"]
            if not neg:
                break
            payments.remove(neg[0])
            _dropped_realloc.append(neg[0])
        gt = order_grand_total(o)
        paid = round(sum(float(p.get("amount", 0) or 0) for p in payments), 2)
        status = _payment_status(gt, paid)
        await db.sales_orders.update_one(
            {"id": oid},
            {"$set": {"payments": payments, "paid_total": paid,
                      "payment_status": status, "updated_at": now_iso()}},
        )
        reversed_orders.append({"order_id": oid, "outstanding_after": round(gt - paid, 2),
                                "payment_status": status,
                                "reallocation_rows_neutralized": len(_dropped_realloc)})
        # FASE G-2/G-3 — jadwal pembayaran ikut disegarkan supaya baris cicilan tidak
        # tetap "lunas" padahal kwitansinya dibatalkan.
        try:
            from services import payment_plan_service as _plans
            await _plans.recompute_for_doc("sales_order", oid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[void_receipt] efek samping gagal diabaikan: %s", exc)  # KN-C10

    # 2) Void cash_transaction terkait (saldo kas tak lagi menghitungnya) + jurnal PEMBALIK
    #    supaya buku besar ikut kembali (Dr Piutang / Cr Kas), bukan hanya buku kas.
    _cash_ids = [c["id"] async for c in db.cash_transactions.find(
        {"ref_type": "ar_receipt", "ref_id": receipt_id, "status": {"$ne": "void"}},
        {"_id": 0, "id": 1})]
    await db.cash_transactions.update_many(
        {"ref_type": "ar_receipt", "ref_id": receipt_id, "status": {"$ne": "void"}},
        {"$set": {"status": "void", "updated_at": now_iso()}},
    )
    for _cid in _cash_ids:
        try:
            from services import gl_service as _gl
            await _gl.post_cash_void(_cid, label=f"void {r.get('number', '')}",
                                     created_by=actor.get("name", "system"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[void_receipt] efek samping gagal diabaikan: %s", exc)  # KN-C10

    # 3) Koreksi deposit (balik deposit_delta yang sempat diterapkan).
    delta = round(float(r.get("deposit_delta", 0) or 0), 2)
    if abs(delta) > EPS:
        await _adjust_deposit(r["customer_id"], -delta)

    await db.ar_receipts.update_one(
        {"id": receipt_id},
        _saga.finish_set({"status": "void", "voided_by": actor.get("name", ""),
                          "voided_at": now_iso(), "voided_reason": (reason or "").strip(),
                          "updated_at": now_iso(),
                          "variance.needs_decision": False,
                          "variance.resolved": True,
                          "reversed_orders": reversed_orders}),
    )
    return safe_doc(await db.ar_receipts.find_one({"id": receipt_id}, {"_id": 0}))


async def list_receipts(customer_id: Optional[str] = None,
                        scope: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = dict(scope or {})
    if customer_id:
        query["customer_id"] = customer_id
    rows = await db.ar_receipts.find(query, {"_id": 0}).to_list(2000)
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return [safe_doc(r) for r in rows]


async def get_receipt(receipt_id: str) -> Optional[Dict[str, Any]]:
    return safe_doc(await db.ar_receipts.find_one({"id": receipt_id}, {"_id": 0}))
