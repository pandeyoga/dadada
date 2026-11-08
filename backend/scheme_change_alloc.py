"""Pemetaan alokasi kuitansi → termin BARU saat skema diganti sesudah ada pembayaran (docs/audit/12 keputusan #9, IN-14).

Ganti skema membangun ulang seluruh termin dengan id baru, sedangkan kuitansi lama menyimpan `allocations[].item_id` ke termin
lama. Tanpa pemetaan yang disepakati, uang pembeli bisa terpasang ke termin yang salah (atau tautannya putus). Modul ini adalah
HITUNGAN MURNI + validasi pemetaan; siklus permintaannya ada di `scheme_change.py`.

Satuan: `alloc` = {receipt_id: [(indeks_termin_baru 0-based, nominal)]}. Di API/dokumen permintaan, termin baru dirujuk dengan
`no` (1-based, urutan jadwal baru) — id termin baru baru lahir saat jadwal disimpan, jadi tidak bisa dipakai di pratinjau.

Aturan validasi (semuanya ditolak dengan pesan yang menyebut kuitansi/termin terkait):
  * SETIAP kuitansi aktif harus dipetakan dan Σ alokasi per kuitansi = nominal yang ia alokasikan (`applied`) — sehingga
    Σ seluruhnya = total dibayar; ubah alokasi TIDAK mengubah kas, hanya penempatannya;
  * tiap alokasi bilangan bulat positif, `no` ada pada jadwal baru, kumulatif per termin <= nilai termin;
  * kuitansi pencairan KPR (`method=kpr`) hanya ke porsi bank dan tidak ke baris `kpr_excluded`; setoran lain ke luar porsi bank.
"""
import hashlib
import json

from db import db


def payer_of(receipt: dict) -> str:
    """Pencairan KPR = bank; selain itu pembeli (termasuk pemakaian titipan/booking fee)."""
    return "bank" if str(receipt.get("method") or "").lower() == "kpr" else "buyer"


def _is_bank(item: dict) -> bool:
    return item.get("payer") == "bank" and not item.get("kpr_excluded")


def eligible(receipt: dict, item: dict) -> bool:
    if payer_of(receipt) == "bank":
        return _is_bank(item) and not item.get("kpr_excluded")
    return not _is_bank(item)


async def mappable_receipts(org: str, deal_id: str) -> list:
    """Kuitansi aktif yang mengalokasikan uang ke AR (urut waktu) — inilah yang harus dipetakan."""
    rows = await db.receipts.find({"org_id": org, "deal_id": deal_id, "status": {"$ne": "void"},
                                   "applied": {"$gt": 0}}, {"_id": 0}).to_list(2000)
    rows.sort(key=lambda r: (r.get("created_at") or "", r.get("id") or ""))
    return rows


def schedule_hash(items: list) -> str:
    """Sidik jadwal baru (label, nilai, penanggung) — dipakai memastikan jadwal saat diterapkan = yang dipratinjau."""
    basis = [[str(i.get("label")), int(i.get("amount") or 0), "bank" if _is_bank(i) else "buyer"] for i in items]
    return hashlib.sha1(json.dumps(basis, ensure_ascii=False).encode()).hexdigest()[:16]


def summarize(items: list) -> list:
    return [{"no": n, "label": i.get("label"), "amount": int(i.get("amount") or 0), "due_date": i.get("due_date"),
             "payer": "bank" if _is_bank(i) else "buyer", "kpr_excluded": bool(i.get("kpr_excluded"))}
            for n, i in enumerate(items, 1)]


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


def check_old_ar(inv: dict, receipts: list) -> None:
    """Prasyarat pemetaan: AR konsisten dengan kuitansi, tanpa denda yang sudah dibayar."""
    for i in inv.get("items") or []:
        if i.get("is_penalty") and int(i.get("paid_amount") or 0) > 0:
            raise ValueError(f"Denda '{i.get('label')}' sudah dibayar sebagian/penuh — pembayaran denda tidak bisa "
                             "dipetakan ke termin skema baru (jurnalnya berbeda). Selesaikan/void denda itu dulu.")
    total = sum(int(r.get("applied") or 0) for r in receipts)
    if total != int(inv.get("paid") or 0):
        raise ValueError(f"AR mencatat dibayar {_rp(inv.get('paid'))} tetapi kuitansi aktif mengalokasikan {_rp(total)} "
                         f"(selisih {_rp(abs(total - int(inv.get('paid') or 0)))}). Rekonsiliasi dulu (periksa kuitansi/"
                         "void) sebelum menyusun ulang jadwal.")


# ------------------------------------------------------------------ penghitungan otomatis
def _by_due(items: list, idxs: list) -> list:
    return sorted(idxs, key=lambda j: (items[j].get("due_date") or "", j))


def _fill(receipts: list, items: list, order: list, cap: dict, alloc: dict) -> None:
    """Isi `order` (indeks termin) berurutan dengan kuitansi (kronologis); `cap` = sisa kapasitas per termin."""
    for r in receipts:
        left = int(r.get("applied") or 0)
        for j in order:
            if left <= 0:
                break
            take = min(left, cap[j])
            if take > 0:
                alloc.setdefault(r["id"], []).append((j, take))
                cap[j] -= take
                left -= take
        if left > 0:
            raise ValueError(f"Kuitansi {r.get('receipt_no')} tidak muat pada jadwal baru (sisa {_rp(left)}).")


def _proportional_targets(total: int, items: list, idxs: list) -> dict:
    """Bagi `total` ke termin `idxs` sebanding nilainya (metode sisa terbesar), tak melebihi nilai termin."""
    base = sum(int(items[j]["amount"]) for j in idxs)
    if total > base:
        raise ValueError(f"Total dibayar {_rp(total)} melebihi nilai termin pada jadwal baru ({_rp(base)}).")
    if total == 0 or base == 0:
        return {j: 0 for j in idxs}
    raw = {j: total * int(items[j]["amount"]) / base for j in idxs}
    tgt = {j: int(raw[j]) for j in idxs}
    sisa = total - sum(tgt.values())
    for j in sorted(idxs, key=lambda k: (raw[k] - tgt[k]), reverse=True):
        if sisa <= 0:
            break
        if tgt[j] < int(items[j]["amount"]):
            tgt[j] += 1
            sisa -= 1
    return tgt


def distribute(receipts: list, items: list, mode: str) -> dict:
    """Pemetaan otomatis: `urut_termin_tertua` (isi termin jatuh tempo terlama dulu) atau `proporsional`
    (tiap termin terisi sebanding nilainya). Bank dan pembeli dihitung terpisah. ValueError bila tak muat."""
    alloc, rows = {}, [(r, payer_of(r)) for r in receipts]
    for who in ("bank", "buyer"):
        rs = [r for r, p in rows if p == who]
        if not rs:
            continue
        idxs = [j for j, it in enumerate(items) if (_is_bank(it) if who == "bank" else not _is_bank(it))
                and not (who == "bank" and it.get("kpr_excluded"))]
        order = _by_due(items, idxs)
        if mode == "proporsional":
            cap = _proportional_targets(sum(int(r.get("applied") or 0) for r in rs), items, order)
        else:
            cap = {j: int(items[j]["amount"]) for j in order}
        _fill(rs, items, order, cap, alloc)
    return alloc


# ------------------------------------------------------------------ validasi pemetaan yang diserahkan
def normalize(mapping, receipts: list, items: list) -> dict:
    """`mapping` (API) = [{receipt_id, allocations:[{no, amount}]}] → {receipt_id: [(indeks, nominal)]} tervalidasi."""
    if not isinstance(mapping, list) or not mapping:
        raise ValueError("Pemetaan alokasi kosong — sebutkan alokasi tiap kuitansi ke termin baru.")
    by_id = {r["id"]: r for r in receipts}
    alloc, used = {}, [0] * len(items)
    for row in mapping:
        rid = (row or {}).get("receipt_id")
        if rid not in by_id:
            raise ValueError(f"Kuitansi '{rid}' bukan kuitansi aktif deal ini (atau sudah tidak mengalokasikan uang).")
        if rid in alloc:
            raise ValueError(f"Kuitansi {by_id[rid].get('receipt_no')} muncul dua kali pada pemetaan.")
        lst = []
        for a in (row.get("allocations") or []):
            try:
                no, amt = int(a.get("no")), int(a.get("amount"))
            except (TypeError, ValueError, AttributeError):
                raise ValueError(f"Alokasi kuitansi {by_id[rid].get('receipt_no')}: `no` dan `amount` harus bilangan bulat.")
            if not 1 <= no <= len(items):
                raise ValueError(f"Alokasi kuitansi {by_id[rid].get('receipt_no')}: termin no {no} tidak ada pada jadwal baru "
                                 f"(1..{len(items)}).")
            if amt < 0:
                raise ValueError(f"Alokasi kuitansi {by_id[rid].get('receipt_no')} ke termin no {no} negatif ({_rp(amt)}).")
            if amt == 0:
                continue
            it = items[no - 1]
            if not eligible(by_id[rid], it):
                raise ValueError(f"Kuitansi {by_id[rid].get('receipt_no')} ({'pencairan KPR' if payer_of(by_id[rid]) == 'bank' else 'setoran pembeli'}) "
                                 f"tidak boleh dialokasikan ke termin '{it.get('label')}' "
                                 f"({'porsi bank' if _is_bank(it) else 'bukan porsi bank'}).")
            used[no - 1] += amt
            lst.append((no - 1, amt))
        got = sum(a for _, a in lst)
        want = int(by_id[rid].get("applied") or 0)
        if got != want:
            raise ValueError(f"Kuitansi {by_id[rid].get('receipt_no')}: jumlah alokasi {_rp(got)} harus tepat sama dengan "
                             f"yang dialokasikan kuitansi ({_rp(want)}), selisih {_rp(abs(got - want))}.")
        alloc[rid] = lst
    missing = [r.get("receipt_no") for r in receipts if r["id"] not in alloc]
    if missing:
        raise ValueError("Kuitansi berikut belum dipetakan: " + ", ".join(str(m) for m in missing) + ".")
    for j, u in enumerate(used):
        if u > int(items[j]["amount"]):
            raise ValueError(f"Termin no {j + 1} '{items[j].get('label')}' (nilai {_rp(items[j]['amount'])}) kelebihan "
                             f"alokasi {_rp(u - int(items[j]['amount']))}.")
    return alloc


def to_api(alloc: dict) -> list:
    return [{"receipt_id": rid, "allocations": [{"no": j + 1, "amount": a} for j, a in lst]} for rid, lst in alloc.items()]


def apply_to_items(items: list, alloc: dict) -> None:
    """Tuliskan hasil pemetaan ke `paid_amount` termin baru (di tempat)."""
    for lst in alloc.values():
        for j, a in lst:
            items[j]["paid_amount"] = int(items[j].get("paid_amount") or 0) + a
    for it in items:
        it["status"] = "paid" if it.get("paid_amount", 0) >= it["amount"] else ("partial" if it.get("paid_amount", 0) > 0 else "unpaid")
