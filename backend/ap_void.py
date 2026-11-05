"""Pembatalan RESMI pembayaran tagihan AP (audit PK-09 / GL-10).

Sebelumnya TIDAK ADA jalan membetulkan pembayaran vendor yang salah/ganda: tidak ada void, nota kredit,
maupun pembayaran-balik. Akibatnya kesalahan input dibetulkan lewat jurnal manual ke akun kendali
2-1100 atau hapus-paksa — dua-duanya membuat subledger dan buku besar menyimpang.

`void_payment()` membatalkan SATU pembayaran (baris `payments_out`) secara atomik:
  * baris pembayaran ditandai `void` (jejak tetap ada; TIDAK dihapus) — dijaga CAS + kunci per pembayaran;
  * subledger tagihan dikembalikan PERSIS sebesar pembayaran itu (`paid`, `outstanding`, `status`,
    `withheld_total`), juga dengan CAS atas (paid, status) yang dibaca;
  * jurnal PEMBALIK terbit (Dr kas/bank + Dr 2-1300 bila ada potongan PPh / Cr 2-1100) — jurnal asli
    TIDAK diubah; kunci idempoten `ap.void:<payment_id>`;
  * bukti potong PPh yang terbit untuk pembayaran itu dibatalkan; pencocokan mutasi bank yang melahirkan
    pembayaran itu dilepas (mutasi kembali "belum cocok");
  * gagal di tengah jalan -> semua klaim dikembalikan (`reserved`), tidak ada separuh-batal.
Pemisahan tugas (pembayar != pembatal) dan izin dijaga di router; alasan minimal 10 huruf.
"""
import logging

import gl_engine as gl
from core_utils import now_iso
from db import db
from engine import add_activity, dispatch_pending
from idempotency import expect_of, reserved
from money_lock import locked

logger = logging.getLogger("sipro.ap_void")
MIN_REASON = 10


async def _original_journal(org: str, bill_id: str, pay: dict) -> dict:
    """Jurnal pembayaran asli yang belum pernah dibalik (cocokkan nominal dr 2-1100). None bila belum terbit."""
    already = {p.get("void_orig_journal_id") for p in await db.payments_out.find(
        {"org_id": org, "bill_id": bill_id, "status": "void"}, {"_id": 0, "void_orig_journal_id": 1}).to_list(500)}
    rows = await db.journal_entries.find(
        {"org_id": org, "source_type": "ap_bill", "source_id": bill_id, "memo": "Pembayaran tagihan AP",
         "lines": {"$elemMatch": {"account_code": "2-1100", "debit": int(pay.get("amount") or 0)}}},
        {"_id": 0}).sort("created_at", 1).to_list(200)
    return next((j for j in rows if j["id"] not in already), None)


async def _release_bank_match(org: str, bill_id: str, amount: int, actor: str, reason: str):
    """Pembayaran lahir dari pencocokan mutasi bank -> lepas pencocokannya (mutasi kembali belum cocok)."""
    m = await db.bank_matches.find_one(
        {"org_id": org, "kind": "ap_bill", "target_id": bill_id, "state": "matched", "amount": int(amount)},
        {"_id": 0}, sort=[("created_at", -1)])
    if not m:
        return None
    ts = now_iso()
    await db.bank_matches.update_one({"id": m["id"]}, {"$set": {
        "state": "reversed", "reversed_at": ts, "reversed_by": actor,
        "reverse_reason": f"Pembayaran vendor dibatalkan: {reason}", "reverse_detail": {"via": "ap_void"}}})
    await db.bank_transactions.update_one({"id": m["txn_id"]}, {"$set": {
        "match_state": "unmatched", "match_id": None, "match_kind": None, "matched_at": None,
        "matched_by": None, "updated_at": ts},
        "$push": {"history": {"at": ts, "by": actor, "action": "unmatch", "reason": reason, "kind": "ap_bill"}}})
    return m["id"]


async def void_payment(org: str, payment_id: str, actor: str, reason: str) -> dict:
    """Diserialkan PER TAGIHAN: dua pembatalan bersamaan (pembayaran sama ATAU dua pembayaran bernominal
    sama pada tagihan yang sama) tidak boleh memilih jurnal asli yang sama untuk dibalik."""
    pay = await db.payments_out.find_one({"id": payment_id, "org_id": org}, {"_id": 0, "bill_id": 1})
    if not pay:
        raise ValueError("Pembayaran tidak ditemukan.")
    async with locked("ap.void_payment", pay.get("bill_id") or payment_id,
                      what="Pembatalan pembayaran vendor pada tagihan ini"):
        return await _void_locked(org, payment_id, actor, (reason or "").strip())


async def _void_locked(org: str, payment_id: str, actor: str, reason: str) -> dict:
    if len(reason) < MIN_REASON:
        raise ValueError(f"Alasan pembatalan minimal {MIN_REASON} huruf.")
    await dispatch_pending()  # jurnal pembayaran asli lahir dari event; kosongkan antrean dulu
    pay = await db.payments_out.find_one({"id": payment_id, "org_id": org}, {"_id": 0})
    if not pay:
        raise ValueError("Pembayaran tidak ditemukan.")
    if pay.get("status") == "void":
        raise ValueError("Pembayaran ini sudah dibatalkan.")
    bill_id = pay.get("bill_id")
    if not bill_id or pay.get("kind"):
        raise ValueError("Hanya pembayaran TAGIHAN AP yang bisa dibatalkan dari sini (bukan refund / fee / "
                         "uang muka / pelepasan retensi).")
    fr = await db.fund_requests.find_one({"org_id": org, "ap_payment_id": payment_id}, {"_id": 0, "no": 1})
    if fr:
        raise ValueError(f"Pembayaran ini berasal dari pencairan Pengajuan Dana {fr['no']} — batalkan lewat "
                         "pengajuannya agar dua dokumen tidak saling bertentangan.")
    bill = await db.ap_invoices.find_one({"id": bill_id, "org_id": org}, {"_id": 0})
    if not bill:
        raise ValueError("Tagihan AP untuk pembayaran ini tidak ditemukan.")
    amount = int(pay.get("amount") or 0)
    withheld = int(pay.get("withheld_amount") or 0)
    if amount <= 0 or int(bill.get("paid") or 0) < amount:
        raise ValueError("Saldo terbayar tagihan lebih kecil dari pembayaran ini — data tidak konsisten; "
                         "periksa dulu riwayat pembayaran tagihan.")
    orig = await _original_journal(org, bill_id, pay)
    if not orig:
        raise ValueError("Jurnal pembayaran asli belum terbit (event pembukuan antre/gagal). Proses ulang "
                         "jurnalnya dulu (banner tie-out → Proses ulang), baru batalkan pembayarannya.")
    cash_code = pay.get("cash_account_code") or next(
        (ln["account_code"] for ln in orig["lines"] if ln["credit"] and ln["account_code"] not in ("2-1100", "2-1300")),
        "1-1200")
    paid_after = int(bill.get("paid") or 0) - amount
    ts = now_iso()
    new_status = "partial" if paid_after > 0 else "approved"
    async with reserved(
            "payments_out", {"id": payment_id, "org_id": org}, {"status": {"$ne": "void"}},
            {"$set": {"status": "void", "void_reason": reason, "void_by": actor, "void_at": ts,
                      "void_orig_journal_id": orig["id"]}},
            undo={"$unset": {"status": "", "void_reason": "", "void_by": "", "void_at": "",
                             "void_orig_journal_id": ""}}, what="Pembayaran vendor"):
        async with reserved(
                "ap_invoices", {"id": bill_id, "org_id": org}, expect_of(bill, "paid", "status"),
                {"$set": {"paid": paid_after, "outstanding": int(bill.get("net") or 0) - paid_after,
                          "status": new_status, "updated_at": ts},
                 "$inc": {"withheld_total": -withheld}},
                undo={"$set": {"paid": int(bill.get("paid") or 0), "status": bill.get("status"),
                               "outstanding": int(bill.get("outstanding") or 0)},
                      "$inc": {"withheld_total": withheld}}, what="Tagihan AP"):
            lines = [{"account_code": cash_code, "debit": amount - withheld, "credit": 0,
                      "memo": "Pembatalan pembayaran"},
                     {"account_code": "2-1100", "debit": 0, "credit": amount}]
            if withheld > 0:
                lines.append({"account_code": "2-1300", "debit": withheld, "credit": 0,
                              "memo": "Pembatalan potongan PPh"})
            je = await gl.post_journal(
                org, f"Pembatalan pembayaran AP — {pay.get('vendor')} — {reason[:70]}", lines,
                source_type="ap_payment_void", source_id=bill_id, source_event=f"ap.void:{payment_id}",
                posted_by=actor, auto=False)
    await db.payments_out.update_one({"id": payment_id}, {"$set": {
        "void_journal_id": je["id"], "void_journal_no": je["entry_no"]}})
    if withheld > 0:
        try:
            import withholding_engine as wh
            for d in await db.withholding_docs.find(
                    {"org_id": org, "basis": "ap_payment", "ref_id": payment_id,
                     "state": {"$ne": wh.CANCELLED}}, {"_id": 0, "id": 1}).to_list(10):
                await wh.cancel(org, d["id"], actor, f"Pembayaran dibatalkan: {reason}")
        except Exception:  # noqa: BLE001 — jurnal sudah benar; bukti potong bisa dibatalkan manual
            logger.exception("Bukti potong pembayaran %s gagal dibatalkan otomatis", payment_id)
    match_id = await _release_bank_match(org, bill_id, amount, actor, reason)
    await add_activity(entity_type="ap_bill", entity_id=bill_id, type="finance", actor=actor, org_id=org,
                       body=f"Pembayaran Rp {amount:,} ke {pay.get('vendor')} DIBATALKAN — {reason}")
    return {"payment_id": payment_id, "bill_id": bill_id, "reversed": amount, "withheld_reversed": withheld,
            "journal_no": je["entry_no"], "bank_match_released": match_id,
            "bill": {"paid": paid_after, "outstanding": int(bill.get("net") or 0) - paid_after,
                     "status": new_status}}
