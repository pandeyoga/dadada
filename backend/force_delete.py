"""HAPUS PAKSA transaksi (deal) beserta seluruh turunannya — hanya peran akses penuh, wajib alasan.

Berbeda dengan `master_delete` (menolak bila ada jejak transaksi), modul ini MENGHAPUS jejaknya:
deal → AR + kuitansi + jurnal + bukti kas (BKM/BKK), booking fee (tagihan/kuitansi/titipan), invoice & kuitansi biaya
all-in, penyaluran, beban AP, kontrak + dokumen, komisi, marketing fee, pajak, KPR, giro, penawaran, komplain & klaim
garansi, kupon dilepas, peristiwa/tugas/notifikasi; unit dikembalikan `available`, lead dilepas dari unit.
Setiap pemanggilan tercatat di audit log oleh router.

Dikerjakan di bawah mutex per-deal (`deal_money`) yang sama dengan penerimaan/void kuitansi (FZ-07), dan daftar
koleksi anak dijaga tes yang menghitung yatim setelah hapus-paksa (PK3-09/FZ-04).
"""
import asyncio
import re

from core_utils import now_iso
from db import db
from idempotency import Conflict
from rbac import FULL_ACCESS_ROLES


def may_force(user: dict) -> bool:
    return (user or {}).get("role") in FULL_ACCESS_ROLES


# Koleksi yang berkunci `deal_id`. PK3-09/FZ-04: `pdc_cheques` salah nama (koleksi nyata `pdc_instruments`) dan
# komplain, klaim garansi, marketing fee, faktur pajak, peristiwa konversi dulu terlewat → yatim (fee yatim bahkan
# masih bisa DISETUJUI → akrual utang fiktif).
DEAL_CHILD_COLLECTIONS = (
    "ar_invoices", "receipts", "booking_fee_invoices", "customer_deposits", "contract_liabilities",
    "revenue_recognitions", "tax_records", "commissions", "financing_apps", "payment_intakes",
    "cost_invoices", "cost_receipts", "cost_disbursements", "cost_expenses", "allin_amendments",
    "kpr_disbursements", "cancellations", "late_fees", "warning_letters", "coupon_redemptions",
    "unit_handovers", "refund_debts", "pdc_instruments",
    "complaints", "warranty_claims", "marketing_fees", "faktur_pajak", "conversion_events", "documents",
)
CONTRACT_CHILD_COLLECTIONS = ("doc_submissions", "doc_shares", "wa_doc_shares", "kpr_stages", "contract_documents")
# Koleksi uang yang disapu ULANG di akhir (penulis yang tak lewat `deal_money`, mis. titipan/booking fee).
_SWEEP_AGAIN = ("receipts", "customer_deposits", "contract_liabilities", "payment_intakes", "booking_fee_invoices")


async def _ids(coll: str, q: dict) -> list:
    try:
        return [r["id"] for r in await db[coll].find(q, {"_id": 0, "id": 1}).to_list(5000) if r.get("id")]
    except Exception:  # noqa: BLE001
        return []


async def _del(coll: str, q: dict, removed: dict) -> None:
    try:
        n = (await db[coll].delete_many(q)).deleted_count
    except Exception:  # noqa: BLE001
        return
    if n:
        removed[coll] = removed.get(coll, 0) + n


def _journal_q(deal_id: str, source_ids: list) -> dict:
    ors = [{"source_deal_id": deal_id}, {"source_event": {"$regex": re.escape(deal_id)}}]
    if source_ids:
        ors.append({"source_id": {"$in": source_ids}})
    return {"$or": ors}


async def _sweep_wa_reminders(org: str, did: str, removed: dict) -> None:
    """Log pengingat WhatsApp (`wa_reminders`) tidak berkunci `deal_id`: ia menunjuk dokumen turunan (tagihan AR, tagihan
    booking fee, BAST) lewat `entity_type`+`entity_id`, dan `dedup_key` peringatan tunggakan memuat id deal. Dibersihkan
    SEBELUM dokumen-dokumen itu dihapus (id-nya masih dibutuhkan)."""
    ors = [{"dedup_key": {"$regex": "^arrears_warning:" + re.escape(did) + ":"}}]
    for etype, coll in (("ar_invoice", "ar_invoices"), ("booking_fee_invoice", "booking_fee_invoices"),
                        ("unit_handover", "unit_handovers")):
        ids = await _ids(coll, {"org_id": org, "deal_id": did})
        if ids:
            ors.append({"entity_type": etype, "entity_id": {"$in": ids}})
    await _del("wa_reminders", {"org_id": org, "$or": ors}, removed)


async def footprint(org: str, deal_id: str) -> dict:
    """Berapa banyak data turunan yang akan ikut terhapus — ditampilkan sebelum konfirmasi."""
    out = {}
    for coll in DEAL_CHILD_COLLECTIONS:
        try:
            n = await db[coll].count_documents({"org_id": org, "deal_id": deal_id})
        except Exception:  # noqa: BLE001
            n = 0
        if n:
            out[coll] = n
    n = await db.contracts.count_documents({"org_id": org, "deal_id": deal_id})
    if n:
        out["contracts"] = n
    n = await db.journal_entries.count_documents({"org_id": org, **_journal_q(deal_id, [])})
    if n:
        out["journal_entries"] = n
    return out


async def _settle_events(ids: list, wait: float = 3.0) -> None:
    """Tunggu event yang SEDANG diproses dispatcher untuk dokumen-dokumen ini selesai (jurnal terbit lebih dulu),
    supaya penyapuan jurnal berikutnya menangkapnya — bukan menyisakan jurnal yatim (FZ-07b)."""
    loop = asyncio.get_event_loop()
    end = loop.time() + wait
    while loop.time() < end:
        if not await db.events.count_documents({"entity_id": {"$in": ids}, "status": "processing"}):
            return
        await asyncio.sleep(0.1)


async def _sweep_journals(org: str, did: str, source_ids: list, removed: dict) -> None:
    """Hapus jurnal turunan + bukti kas (BKM/BKK) milik jurnal itu (FZ-04: dulu bukti kas tersisa yatim)."""
    q = {"org_id": org, **_journal_q(did, source_ids)}
    jids = [j["id"] async for j in db.journal_entries.find(q, {"_id": 0, "id": 1})]
    if jids:
        await _del("cash_vouchers", {"org_id": org, "journal_id": {"$in": jids}}, removed)
    await _del("journal_entries", q, removed)


async def delete_deal_cascade(org: str, deal: dict, actor: str) -> dict:
    """Hapus deal + turunannya di bawah mutex per-deal (FZ-07): penerimaan/void kuitansi yang bersamaan menunggu,
    lalu melihat deal/AR-nya sudah tiada — tidak ada lagi uang masuk tanpa jurnal atau jurnal yatim."""
    from deal_money import deal_money
    async with deal_money(org, deal["id"]):
        if not await db.deals.find_one({"id": deal["id"], "org_id": org}, {"_id": 1}):
            raise Conflict("Deal ini baru saja dihapus oleh proses lain.")
        return await _cascade_locked(org, deal, actor)


async def _cascade_locked(org: str, deal: dict, actor: str) -> dict:
    from engine import dispatch_pending
    import bank_match
    did = deal["id"]
    removed = {}
    ts = now_iso()
    # Kosongkan antrean event lebih dulu: jurnal penerimaan yang masih antre terbit SEKARANG (lalu ikut terhapus),
    # bukan di tengah penghapusan (jurnal yatim).
    await dispatch_pending()
    # Jurnal: semua yang bersumber dari dokumen turunan deal ini (kuitansi, titipan, biaya, AP, komisi, fee, giro).
    source_ids = [did]
    for coll in ("receipts", "cost_receipts", "cost_disbursements", "cost_expenses", "commissions",
                 "booking_fee_invoices", "customer_deposits", "ar_invoices", "cost_invoices", "kpr_disbursements",
                 "revenue_recognitions", "late_fees", "cancellations", "marketing_fees", "pdc_instruments"):
        source_ids += await _ids(coll, {"org_id": org, "deal_id": did})
    exp = await db.cost_expenses.find({"org_id": org, "deal_id": did}, {"_id": 0, "ap_bill_id": 1}).to_list(100)
    ap_ids = [e["ap_bill_id"] for e in exp if e.get("ap_bill_id")]
    source_ids += ap_ids
    # Pembayaran fee marketing (payments_out) → jurnalnya bersumber dari id pembayaran itu.
    fee_ids = await _ids("marketing_fees", {"org_id": org, "deal_id": did})
    fee_pay_ids = await _ids("payments_out", {"org_id": org, "marketing_fee_id": {"$in": fee_ids}}) if fee_ids else []
    source_ids += fee_pay_ids
    # Semua id dokumen turunan (deal, kontrak, anak kontrak, anak deal): notifikasi/aktivitas/tugas/peristiwa yang
    # menunjuknya lewat `related_entity_id`/`entity_id` (mis. notifikasi "Pengajuan marketing fee") disapu di bawah —
    # ditemukan tes pemindai SEMUA koleksi (sisa PK3-09): dulu hanya yang bertipe `deal` yang ikut terhapus.
    child_ids = set(source_ids)
    cids0 = await _ids("contracts", {"org_id": org, "deal_id": did})
    child_ids.update(cids0)
    for coll in DEAL_CHILD_COLLECTIONS:
        child_ids.update(await _ids(coll, {"org_id": org, "deal_id": did}))
    for coll in CONTRACT_CHILD_COLLECTIONS:
        if cids0:
            child_ids.update(await _ids(coll, {"org_id": org, "contract_id": {"$in": cids0}}))
    child_ids = sorted(child_ids)
    # PK3-12: mutasi bank yang tercocokkan ke kuitansi deal ini dilepas (kembali "belum cocok"), bukan tertinggal.
    for rid in await _ids("receipts", {"org_id": org, "deal_id": did}):
        await bank_match.release_match_for_receipt(org, rid, actor, "deal dihapus-paksa")
    await _del("events", {"entity_id": {"$in": source_ids}}, removed)
    await _sweep_wa_reminders(org, did, removed)
    await _sweep_journals(org, did, source_ids, removed)
    if ap_ids:
        await _del("ap_invoices", {"org_id": org, "id": {"$in": ap_ids}}, removed)
        await _del("payments_out", {"org_id": org, "ap_invoice_id": {"$in": ap_ids}}, removed)
    if fee_pay_ids:
        await _del("payments_out", {"org_id": org, "id": {"$in": fee_pay_ids}}, removed)
    # Kupon: kuota dikembalikan sebelum jejaknya dihapus.
    async for r in db.coupon_redemptions.find({"org_id": org, "ref_type": "deal", "ref_id": did, "state": "used"}):
        await db.coupons.update_one({"id": r["coupon_id"], "used_count": {"$gt": 0}}, {"$inc": {"used_count": -1}})
    await _del("coupon_redemptions", {"org_id": org, "ref_type": "deal", "ref_id": did}, removed)
    # Kontrak + turunannya (+ tugas yang menempel pada kontrak: isi komponen biaya, dst.).
    contract_ids = await _ids("contracts", {"org_id": org, "deal_id": did})
    for cid in contract_ids:
        for coll in CONTRACT_CHILD_COLLECTIONS:
            await _del(coll, {"org_id": org, "contract_id": cid}, removed)
        await _del("documents", {"org_id": org, "contract_id": cid}, removed)
    if contract_ids:
        await _del("tasks", {"org_id": org, "related_entity_type": "contract",
                             "related_entity_id": {"$in": contract_ids}}, removed)
    await _del("contracts", {"org_id": org, "deal_id": did}, removed)
    for coll in DEAL_CHILD_COLLECTIONS:
        await _del(coll, {"org_id": org, "deal_id": did}, removed)
    await _del("quotations", {"org_id": org, "converted_deal_id": did}, removed)
    for coll, f1, f2 in (("activities", "entity_type", "entity_id"), ("tasks", "related_entity_type", "related_entity_id"),
                         ("notifications", "related_entity_type", "related_entity_id")):
        await _del(coll, {"org_id": org, f1: "deal", f2: did}, removed)
        await _del(coll, {"org_id": org, f2: {"$in": child_ids}}, removed)
    # Unit kembali tersedia; ikatan ke deal/lead/pembeli/kontrak dilepas — HANYA bila unit itu memang dipegang
    # deal ini (PK3-04: dulu hapus-paksa deal lama melepas unit yang sudah direservasi deal BARU).
    await db.units.update_one({"id": deal.get("unit_id"), "org_id": org, "$or": [
        {"reserved_by_deal": did}, {"booked_by_deal": did}, {"sold_by_deal": did}, {"deal_id": did}]}, {
        "$set": {"status": "available", "payment_status": "none", "reserved_by_deal": None,
                 "booked_by_deal": None, "sold_by_deal": None, "updated_at": ts},
        "$unset": {"deal_id": "", "lead_id": "", "lead_name": "", "customer_id": "", "contract_id": "", "sold_at": ""}})
    await db.build_schedules.update_many({"org_id": org, "unit_id": deal.get("unit_id")},
                                         {"$unset": {"deal_id": "", "lead_id": "", "customer_id": ""}})
    await db.leads.update_one({"id": deal.get("lead_id"), "org_id": org},
                              {"$unset": {"unit_id": "", "deal_id": ""}, "$set": {"updated_at": ts}})
    # PK3-09: customers.deal_id (dan jejak asal `converted_from_deal`) tidak boleh menunjuk deal yang hilang.
    await db.customers.update_many({"org_id": org, "$or": [{"deal_id": did}, {"converted_from_deal": did}]},
                                   {"$unset": {"deal_id": "", "converted_from_deal": ""}})
    await db.deals.delete_one({"id": did, "org_id": org})
    removed["deals"] = 1
    # Penyapuan akhir: jurnal yang baru terbit dari event yang sedang diproses + uang yang masuk lewat penulis
    # yang tidak memegang mutex deal (titipan, booking fee) — keduanya tidak boleh tersisa sebagai yatim.
    await _settle_events(source_ids)
    await _del("events", {"entity_id": {"$in": child_ids}}, removed)
    await _sweep_journals(org, did, source_ids, removed)
    for coll in _SWEEP_AGAIN:
        await _del(coll, {"org_id": org, "deal_id": did}, removed)
    return {"id": did, "unit_code": deal.get("unit_code"), "deleted": True, "removed": removed,
            "deleted_by": actor, "deleted_at": ts}


async def delete_deals_of(org: str, q: dict, actor: str) -> dict:
    """Hapus paksa semua deal yang cocok (dipakai hapus paksa lead/customer/unit/proyek)."""
    removed = {}
    for d in await db.deals.find({"org_id": org, **q}, {"_id": 0}).to_list(5000):
        try:
            out = await delete_deal_cascade(org, d, actor)
        except Conflict:
            continue   # sudah dihapus proses lain
        for k, v in out["removed"].items():
            removed[k] = removed.get(k, 0) + v
    return removed


async def delete_receipt(org: str, receipt: dict, actor: str) -> dict:
    """Hapus SATU pembayaran (kuitansi) beserta jurnalnya; alokasi termin & titipan dibalik.

    PK3-11/FZ-07: diserialkan dengan kunci yang SAMA dengan void kuitansi (`receipt.void`) + mutex per-deal, dan
    kuitansi dibaca ULANG di bawah kunci — penghapusan kedua yang bersamaan/menyusul tidak membalik efek dua kali
    (dulu kewajiban kontrak −Rp 170 jt) tetapi mendapat 409."""
    from deal_money import deal_money
    from money_lock import locked
    rid = receipt["id"]
    async with locked("receipt.void", rid, what="Penghapusan/pembatalan kuitansi ini"):
        async with deal_money(org, receipt.get("deal_id")):
            return await _delete_receipt_locked(org, rid, actor)


async def _reverse_allocations(org: str, receipt: dict, kind: str) -> None:
    """Balikkan alokasi termin/titipan/booking fee yang dilakukan kuitansi ini (BELUM void)."""
    rid, did = receipt["id"], receipt.get("deal_id")
    if kind == "booking_fee":
        inv = await db.booking_fee_invoices.find_one({"org_id": org, "deal_id": did}, {"_id": 0})
        if inv:
            paid = max(0, int(inv.get("paid") or 0) - int(receipt.get("amount") or 0))
            await db.booking_fee_invoices.update_one({"id": inv["id"]}, {
                "$set": {"paid": paid, "outstanding": int(inv["amount"]) - paid,
                         "status": "paid" if paid >= int(inv["amount"]) else ("partial" if paid else "unpaid"),
                         "paid_at": None if paid < int(inv["amount"]) else inv.get("paid_at"), "updated_at": now_iso()},
                "$pull": {"receipt_ids": rid}})
            await db.deals.update_one({"id": did}, {"$set": {"booking_fee_status": "recorded" if paid else "unverified"}})
        await db.customer_deposits.update_one({"org_id": org, "deal_id": did}, {
            "$inc": {"balance": -int(receipt.get("deposit_amount") or receipt.get("amount") or 0),
                     "received_total": -int(receipt.get("amount") or 0)},
            "$pull": {"entries": {"receipt_id": rid}}})
        return
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": did}, {"_id": 0})
    if inv:
        items = inv.get("items") or []
        for al in receipt.get("allocations") or []:
            it = next((x for x in items if x.get("id") == al.get("item_id")), None)
            if it:
                it["paid_amount"] = max(0, int(it.get("paid_amount") or 0) - int(al.get("amount") or 0))
                it["status"] = "paid" if it["paid_amount"] >= int(it["amount"]) else ("partial" if it["paid_amount"] else "unpaid")
        paid = sum(int(i.get("paid_amount") or 0) for i in items)
        await db.ar_invoices.update_one({"id": inv["id"]}, {"$set": {
            "items": items, "paid": paid, "outstanding": int(inv["total"]) - paid,
            "status": "paid" if paid >= int(inv["total"]) else ("partial" if paid else "unpaid"),
            "updated_at": now_iso()}})
        await db.units.update_one({"id": inv.get("unit_id")}, {"$set": {
            "payment_status": "paid_off" if paid >= int(inv["total"]) else ("partial" if paid else "booking_fee")}})
    if int(receipt.get("deposit_amount") or 0) and receipt.get("funding") != "deposit":
        await db.customer_deposits.update_one({"org_id": org, "deal_id": did}, {
            "$inc": {"balance": -int(receipt["deposit_amount"])}, "$pull": {"entries": {"receipt_id": rid}}})
    if receipt.get("funding") == "deposit":
        await db.customer_deposits.update_one({"org_id": org, "deal_id": did}, {
            "$inc": {"balance": int(receipt.get("applied") or receipt.get("amount") or 0),
                     "applied_total": -int(receipt.get("applied") or receipt.get("amount") or 0)},
            "$pull": {"entries": {"receipt_id": rid}}})
    # Audit IN-05/GL-05: jurnal penerimaan ikut terhapus, jadi bagian "kewajiban kontrak" dari uang ini harus ikut
    # diturunkan di subledger (dulu tidak → tie-out 2-1400 merah).
    applied = int(receipt.get("applied") or 0)
    if applied > 0:
        split = receipt.get("gl_split")
        liab_part = int(split["liability"]) if split else applied
        if liab_part:
            await db.contract_liabilities.update_one({"org_id": org, "deal_id": did}, {"$inc": {"balance": -liab_part}})


async def _delete_receipt_locked(org: str, rid: str, actor: str) -> dict:
    from engine import dispatch_pending
    import bank_match
    receipt = await db.receipts.find_one({"id": rid, "org_id": org}, {"_id": 0})
    if not receipt:
        raise Conflict("Kuitansi ini sudah dihapus oleh proses lain.")
    await dispatch_pending()   # jurnal penerimaan yang masih antre terbit dulu → ikut terhapus di bawah
    removed = {}
    kind = receipt.get("kind") or "ar"
    # Kuitansi yang SUDAH dibatalkan (void): alokasinya sudah dibalik oleh void — membaliknya lagi akan mengurangi
    # alokasi kuitansi lain pada termin yang sama dan menurunkan kewajiban kontrak dua kali.
    if receipt.get("status") != "void":
        await _reverse_allocations(org, receipt, kind)
    # PK3-12: mutasi bank yang dicocokkan ke kuitansi ini dilepas (kembali "belum cocok"); dulu `matched` ke hantu.
    await bank_match.release_match_for_receipt(org, rid, actor, "kuitansi dihapus-paksa")
    # Bukti kas (BKM/BKK) milik jurnal yang dihapus tidak boleh tersisa yatim.
    jq = {"org_id": org, "$or": [{"source_id": rid}, {"source_event": {"$regex": re.escape(rid)}}]}
    jids = [j["id"] async for j in db.journal_entries.find(jq, {"_id": 0, "id": 1})]
    if jids:
        await _del("cash_vouchers", {"org_id": org, "journal_id": {"$in": jids}}, removed)
    await _del("journal_entries", jq, removed)
    await _del("payment_intakes", {"org_id": org, "receipt_id": rid}, removed)
    gone = await db.receipts.delete_one({"id": rid, "org_id": org})
    if gone.deleted_count != 1:   # CAS terakhir — tak mungkin di bawah kunci, tetapi jangan melapor sukses palsu
        raise Conflict("Kuitansi ini baru saja dihapus oleh proses lain.")
    removed["receipts"] = 1
    return {"id": rid, "receipt_no": receipt.get("receipt_no"), "deleted": True, "removed": removed, "deleted_by": actor}
