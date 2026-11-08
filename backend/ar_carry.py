"""Penggantian JADWAL TAGIHAN (AR) tidak boleh mengacak pembayaran yang sudah diterima (audit KT-06).

`finance_engine.create_ar_for_deal(replace=True)` membangun ulang seluruh item termin dengan id
baru. Dulu uang yang sudah masuk dialokasikan ulang secara FIFO (jatuh tempo terlama dulu) —
akibatnya pembayaran yang oleh kasir DIALOKASIKAN ke "Termin 40%" muncul di AR sebagai DP,
sementara kuitansinya tetap menyebut Termin 40%: kuitansi ≠ AR, umur piutang per termin salah,
dan pembeli ditagih ulang termin yang sudah ia bayar.

Aturan di sini:
  * pembayaran dipindahkan ke termin baru yang BERLABEL SAMA (alokasi yang tercatat dipertahankan),
    dan alokasi pada kuitansi ikut diarahkan ke id termin baru (supaya pembatalan kuitansi tetap
    mengurangi termin yang benar);
  * sisa yang tak punya termin pasangan boleh dialokasikan FIFO HANYA bila itu uang titipan/booking
    fee (dialihkan sistem, bukan alokasi pilihan kasir) — alur normal "booking fee ikut ke DP baru";
  * uang NYATA (kuitansi kas/KPR) yang tidak punya termin pasangan DITOLAK: jadwal baru tidak
    memuat termin yang sudah dibayar pembeli, jadi harus lewat adendum, bukan ditimpa diam-diam.
"""
from core_utils import now_iso
from db import db
from idempotency import Conflict


async def default_base_date(org: str, deal: dict) -> str:
    """Dasar tanggal jatuh tempo termin (KT-11).

    Teks skema/SPR berbunyi "N hari setelah kontrak DIAKTIFKAN", jadi sesudah kontrak aktif dasarnya
    `activated_at`. Sebelum itu jadwal masih sementara dan memakai tanggal booking/reservasi.
    """
    k = await db.contracts.find_one({"org_id": org, "deal_id": deal["id"]},
                                    {"_id": 0, "activated_at": 1}) or {}
    return k.get("activated_at") or deal.get("booked_at") or deal.get("reserved_at") or now_iso()


def _key(label) -> str:
    return " ".join(str(label or "").lower().split())


def _mark(item: dict) -> None:
    item["status"] = "paid" if item["paid_amount"] >= item["amount"] else (
        "partial" if item["paid_amount"] > 0 else "unpaid")


async def _cash_by_item(org: str, deal_id: str) -> dict:
    """Uang NYATA (bukan pemakaian titipan) per id termin lama, dari alokasi kuitansi tercatat."""
    out = {}
    rows = await db.receipts.find(
        {"org_id": org, "deal_id": deal_id, "status": {"$ne": "void"},
         "funding": {"$ne": "deposit"}}, {"_id": 0, "allocations": 1}).to_list(1000)
    for r in rows:
        for a in r.get("allocations") or []:
            if a.get("item_id"):
                out[a["item_id"]] = out.get(a["item_id"], 0) + int(a.get("amount") or 0)
    return out


async def carry_mapped(org: str, deal_id: str, existing: dict, items: list, approved: dict) -> dict:
    """Pindahkan pembayaran ke `items` baru memakai PEMETAAN yang sudah dikonfirmasi Keuangan (W1-B #9, IN-14).

    `approved` = {"alloc": {receipt_id: [(indeks, nominal)]}, "schedule_hash", "request_id", "by", "reason"} (dari
    `scheme_change.apply`). Divalidasi ULANG terhadap kuitansi & jadwal saat ini — bukan percaya hasil pratinjau lama.
    """
    import scheme_change_alloc as sca
    if sca.schedule_hash(items) != approved["schedule_hash"]:
        raise ValueError("Jadwal skema baru berubah sejak pratinjau (harga/skema/diskon deal berubah) — pemetaan tidak "
                         "berlaku lagi. Batalkan permintaan ini lalu ajukan ulang.")
    receipts = await sca.mappable_receipts(org, deal_id)
    sca.check_old_ar(existing, receipts)
    alloc = sca.normalize(sca.to_api(approved["alloc"]), receipts, items)
    sca.apply_to_items(items, alloc)
    return {"_mapped": True, "alloc": alloc, "items": items, "request_id": approved.get("request_id"),
            "by": approved.get("by"), "reason": approved.get("reason")}


async def carry(org: str, deal_id: str, existing: dict, items: list, allocate, approved: dict = None) -> dict:
    """Pindahkan pembayaran AR `existing` ke `items` baru (diubah di tempat).

    `approved` (pemetaan dikonfirmasi Keuangan) menggantikan seluruh pemetaan otomatis di bawah ini.

    `allocate` = `finance_engine._allocate` (disuntik supaya tidak ada impor melingkar).
    Mengembalikan pemetaan {id termin lama: termin baru} untuk `remap_receipts`.
    Raise `ValueError` bila uang nyata tak bisa dipetakan, atau jadwal baru lebih kecil dari
    pembayaran yang sudah masuk.
    """
    if approved:
        return await carry_mapped(org, deal_id, existing, items, approved)
    cash = await _cash_by_item(org, deal_id)
    free = list(range(len(items)))
    mapping, pool, cash_pool = {}, 0, 0
    for old in existing.get("items") or []:
        paid = int(old.get("paid_amount") or 0)
        if paid <= 0:
            continue
        k, pen = _key(old.get("label")), bool(old.get("is_penalty"))
        j = next((i for i in free if _key(items[i].get("label")) == k
                  and bool(items[i].get("is_penalty")) == pen), None)
        real = min(paid, cash.get(old.get("id"), 0))
        if j is None:
            pool += paid
            cash_pool += real
            continue
        free.remove(j)
        new = items[j]
        take = min(paid, int(new["amount"]))
        new["paid_amount"] = take
        _mark(new)
        mapping[old["id"]] = new
        sisa = paid - take
        if sisa > 0:
            pool += sisa
            cash_pool += max(0, sisa - (paid - real))  # titipan terpakai lebih dulu dari sisa
    if cash_pool > 0:
        rp = f"{cash_pool:,}".replace(",", ".")
        raise ValueError(
            f"Rp {rp} yang sudah diterima dialokasikan ke termin yang TIDAK ADA lagi pada "
            "jadwal baru. Jadwal tagihan yang sudah dibayar pembeli tidak boleh disusun ulang "
            "diam-diam (kuitansi dan piutang akan berbeda). Ajukan penggantian skema lewat jalur pemetaan Keuangan "
            "(Keuangan menetapkan alokasi tiap kuitansi ke termin baru), atau kembalikan uangnya sebagai titipan/refund dulu.")
    if pool > 0:
        _, sisa = allocate(items, pool)
        if sisa > 0:
            total = sum(int(i["amount"]) for i in items)
            raise ValueError(
                f"Skema baru bernilai Rp {total:,}, lebih kecil dari pembayaran yang sudah diterima "
                f"Rp {int(existing.get('paid') or 0):,}. Kembalikan kelebihan sebagai titipan/refund dulu.")
    return mapping


async def remap_receipts(org: str, deal_id: str, mapping: dict) -> int:
    """Arahkan alokasi kuitansi dari id termin lama ke id termin baru (setelah AR tersimpan)."""
    if not mapping:
        return 0
    n = 0
    rows = await db.receipts.find({"org_id": org, "deal_id": deal_id},
                                  {"_id": 0, "id": 1, "allocations": 1}).to_list(1000)
    for r in rows:
        allocs, changed = [], False
        for a in r.get("allocations") or []:
            new = mapping.get(a.get("item_id"))
            if new:
                a = {**a, "item_id": new["id"], "label": new.get("label")}
                changed = True
            allocs.append(a)
        if changed:
            await db.receipts.update_one({"id": r["id"]}, {"$set": {"allocations": allocs}})
            n += 1
    return n


async def remap_receipts_mapped(org: str, deal_id: str, carried: dict) -> int:
    """Tulis ulang `allocations` kuitansi sesuai pemetaan Keuangan; alokasi LAMA disimpan di `allocation_history`
    (kuitansi, nominal, nomor, dan jurnal kas TIDAK berubah — hanya penempatannya ke termin)."""
    ts = now_iso()
    n = 0
    items = carried["items"]
    for rid, lst in carried["alloc"].items():
        rec = await db.receipts.find_one({"id": rid, "org_id": org, "deal_id": deal_id}, {"_id": 0, "allocations": 1})
        if rec is None:
            continue
        baru = [{"item_id": items[j]["id"], "label": items[j].get("label"), "amount": a, "remapped": True}
                for j, a in lst]
        # CAS pada alokasi yang tadi dibaca: kuitansi yang berubah di sela-sela (tidak mungkin di bawah `deal_money`)
        # ditolak, bukan ditimpa.
        res = await db.receipts.update_one(
            {"id": rid, "org_id": org, "deal_id": deal_id, "allocations": rec.get("allocations")},
            {"$set": {"allocations": baru}, "$push": {"allocation_history": {
                "at": ts, "by": carried.get("by"), "request_id": carried.get("request_id"),
                "reason": carried.get("reason"), "previous": rec.get("allocations") or []}}})
        if res.matched_count != 1:
            raise Conflict("Kuitansi berubah saat alokasinya dipetakan — tidak ditimpa. Muat ulang lalu ulangi.")
        n += 1
    return n


async def replace_invoice(org: str, deal_id: str, inv: dict, existing: dict, carried: dict) -> None:
    """Tulis AR hasil susun-ulang dengan CAS, lalu arahkan alokasi kuitansi ke termin baru.

    CAS: pembayaran yang masuk SELAMA jadwal disusun ulang tidak boleh tertimpa diam-diam.
    """
    expect = {k: existing[k] for k in ("updated_at", "paid") if k in existing}
    res = await db.ar_invoices.update_one({"id": inv["id"], **expect}, {"$set": inv})
    if res.matched_count != 1:
        raise Conflict("Tagihan (AR) deal ini berubah saat jadwal disusun ulang (ada pembayaran/"
                       "penyesuaian lain). Tidak ada yang diubah — muat ulang lalu ulangi.")
    if carried.get("_mapped"):
        await remap_receipts_mapped(org, deal_id, carried)
        return
    await remap_receipts(org, deal_id, carried)
