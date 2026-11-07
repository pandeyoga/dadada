"""Rekonsiliasi LUAS (G3): akun kendali tambahan yang buku besarnya BISA dibuktikan dari subledger.

`finance_audit.reconcile()` semula hanya menjaga 7 akun (2-1100, 2-1200, 2-1400, 2-1450, 2-1600, 1-1500,
neraca saldo). Akun lain yang digerakkan jurnal otomatis tidak punya penjaga: selisihnya baru ketahuan
saat audit manual. Berkas ini menambah pemeriksaan yang murni PEMBUKTIAN (tanpa keputusan akuntansi baru):

  1-1300  Piutang Usaha          vs  sisa tagih AR yang sudah diakui (pasca-BAST) + denda yang belum lunas
  2-1470  Titipan Biaya Customer vs  Σ kuitansi biaya − Σ penyaluran titipan
  1-2100  Aset Tetap             vs  Σ harga perolehan aset yang belum dilepas
  1-2200  Akumulasi Penyusutan   vs  Σ riwayat penyusutan aset yang belum dilepas
  2-2100  Utang Bank / Leasing   vs  Σ (pokok − pokok terbayar menurut jadwal) fasilitas aktif/lunas

Saldo tiap sub-akun kas/bank sengaja TIDAK diperiksa: saldonya dihitung dari jurnal itu sendiri
(`cash_bank.account_balance`), jadi tidak ada subledger kedua yang bisa berselisih.

Bentuk tiap pemeriksaan sama dengan `finance_audit.reconcile`. Bila sebuah pemeriksaan ditandai
`indicator=True` ia TIDAK menggagalkan `ok` (hanya peringatan) — dipakai untuk angka yang secara
akuntansi memang bisa berbeda tanpa ada yang salah (lihat catatan di tiap fungsi).
"""
import allin_engine as ae
import fixed_assets as fa
import late_fee_engine as lf
import loans as ln
from db import db
from revrec_cogs import account_balance


def _i(v) -> int:
    return int(v or 0)


async def _check(org: str, code: str, label: str, expected: int, hint: str, *, credit_normal: bool,
                 indicator: bool = False, sources: dict = None) -> dict:
    bal = await account_balance(org, code)     # debit − kredit
    gl_bal = -bal if credit_normal else bal
    out = {"code": code, "label": label, "gl": gl_bal, "subledger": int(expected), "diff": gl_bal - int(expected),
           "ok": gl_bal == int(expected), "hint": hint}
    if indicator:
        out["indicator"] = True
    if sources:
        out["sources"] = sources
    return out


async def piutang_usaha(org: str) -> dict:
    """1-1300 = sisa tagih unit yang SUDAH diakui pendapatannya (BAST) + denda keterlambatan yang belum lunas.

    * Sebelum BAST sisa tagih unit TIDAK ada di buku (model kewajiban kontrak: hanya uang yang sudah masuk
      yang dibukukan, ke 2-1400) — jadi tidak dihitung. Sesudah BAST: Dr 1-1300 = pendapatan − uang yang
      sudah dikliringkan; pembayaran sesudahnya mengkredit 1-1300 (`finance_engine.gl_split`).
    * Denda dibukukan Dr 1-1300 / Cr 4-1400 saat ditagihkan (sebelum maupun sesudah BAST) dan dikreditkan
      saat dibayar/diringankan; denda yang belum lunas tetap piutang walau kontraknya kemudian dibatalkan
      (termin dibatalkan tetapi jurnal denda tidak dibalik) — jumlahnya dilaporkan di `sources`.
    """
    recognized = {r["deal_id"] async for r in db.revenue_recognitions.find({"org_id": org}, {"_id": 0, "deal_id": 1})}
    unit_open = penalty_open = penalty_cancelled = 0
    async for inv in db.ar_invoices.find({"org_id": org}, {"_id": 0, "deal_id": 1, "items": 1}):
        after_bast = inv.get("deal_id") in recognized
        for it in inv.get("items") or []:
            out = _i(it.get("amount")) - _i(it.get("paid_amount"))
            if it.get("is_penalty"):
                penalty_open += out
                if it.get("status") == "cancelled":
                    penalty_cancelled += out
            elif after_bast and it.get("status") != "cancelled":
                unit_open += out
    return await _check(
        org, lf.AKUN_PIUTANG, "Piutang Usaha vs Σ sisa tagih AR pasca-BAST + denda belum lunas", unit_open + penalty_open,
        "Pendapatan BAST/pelunasan piutang/denda dibukukan tanpa subledger (atau sebaliknya), atau jurnal "
        "manual langsung ke 1-1300.", credit_normal=False,
        sources={"sisa_unit_pasca_bast": unit_open, "denda_belum_lunas": penalty_open,
                 "denda_dari_kontrak_batal": penalty_cancelled})


async def titipan_biaya(org: str) -> dict:
    """2-1470 = Σ kuitansi biaya (termasuk booking fee yang dialihkan) − Σ penyaluran titipan ke notaris/BPN."""
    received = paid_out = 0
    async for r in db.cost_receipts.find({"org_id": org, "status": {"$ne": "void"}}, {"_id": 0, "amount": 1}):
        received += _i(r.get("amount"))
    async for d in db.cost_disbursements.find({"org_id": org}, {"_id": 0, "amount": 1}):
        paid_out += _i(d.get("amount"))
    return await _check(
        org, ae.GL_TITIPAN_BIAYA, "Titipan Biaya Customer vs Σ kuitansi biaya − Σ penyaluran", received - paid_out,
        "Kuitansi biaya/penyaluran titipan tanpa jurnal (atau jurnal tanpa catatan), atau data biaya dihapus "
        "tanpa membalik jurnalnya.", credit_normal=True,
        sources={"kuitansi_biaya": received, "penyaluran": paid_out})


async def aset_tetap(org: str) -> list:
    """1-2100 = Σ harga perolehan aset belum dilepas; 1-2200 = Σ penyusutan tercatat aset belum dilepas."""
    live, cost = set(), 0
    async for a in db.fixed_assets.find({"org_id": org, "status": {"$ne": "disposed"}}, {"_id": 0, "id": 1, "cost": 1}):
        live.add(a["id"])
        cost += _i(a.get("cost"))
    depr = 0
    async for d in db.asset_depreciations.find({"org_id": org}, {"_id": 0, "asset_id": 1, "amount": 1}):
        if d.get("asset_id") in live:
            depr += _i(d.get("amount"))
    return [
        await _check(org, fa.ASSET_ACC, "Aset Tetap vs Σ harga perolehan aset belum dilepas", cost,
                     "Perolehan/pelepasan aset tanpa jurnal, atau jurnal manual langsung ke 1-2100.",
                     credit_normal=False),
        await _check(org, fa.ACCUM_ACC, "Akumulasi Penyusutan vs Σ riwayat penyusutan aset belum dilepas", depr,
                     "Penyusutan diposting tanpa catatan riwayat (atau sebaliknya), atau pelepasan aset tidak "
                     "menghapus akumulasinya.", credit_normal=True),
    ]


async def utang_bank(org: str) -> dict:
    """2-2100 = Σ (pokok − pokok terbayar menurut JADWAL) fasilitas yang sudah dicairkan (aktif/lunas)."""
    total = 0
    async for fas in db.loans.find({"org_id": org, "status": {"$in": ["active", "paid_off"]}},
                                   {"_id": 0, "principal": 1, "schedule": 1}):
        total += _i(fas.get("principal")) - sum(_i(r.get("paid_principal")) for r in fas.get("schedule") or [])
    return await _check(
        org, ln.LOAN_ACC, "Utang Bank / Leasing vs Σ pokok belum terbayar menurut jadwal", total,
        "Pencairan/angsuran pembiayaan dibukukan tanpa mengubah jadwal (atau sebaliknya).", credit_normal=True)


async def extra_checks(org: str) -> list:
    out = [await piutang_usaha(org), await titipan_biaya(org)]
    out += await aset_tetap(org)
    out.append(await utang_bank(org))
    return out
