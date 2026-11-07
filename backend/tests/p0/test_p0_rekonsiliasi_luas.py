"""Regresi G-C (G3) — REKONSILIASI LUAS `/finance/reconcile`: dari 7 menjadi 12 pemeriksaan.

    API_BASE=http://localhost:8073/api DB_NAME=sipro_gc python -m pytest backend/tests/p0/test_p0_rekonsiliasi_luas.py \
        -n 0 --noconftest -q -p no:cacheprovider

Pemeriksaan baru (tanpa keputusan akuntansi baru): 1-1300 piutang usaha, 2-1470 titipan biaya, 1-2100 aset tetap,
1-2200 akumulasi penyusutan, 2-2100 utang bank. Dua kelompok tes:

 A. Alur NYATA di org-sipro (aset, pinjaman, deal+BAST+denda, biaya all-in) -> tiap pemeriksaan baru ADA, berlabel,
    HIJAU, dan angka subledger-nya naik tepat sebesar transaksi (selisih terhadap garis dasar, bukan saldo mutlak).
 B. KORUPSI subledger lewat pymongo -> pemeriksaan jadi MERAH dengan selisih terukur, lalu dipulihkan. Dilakukan
    di org-nusa (organisasi KHUSUS tes; `reconcile` dihitung per organisasi), sehingga rekonsiliasi org-sipro yang
    dibaca tes lain tidak pernah ikut merah. Wajib `DB_NAME` (+ opsional `MONGO_URL`) menunjuk DB backend yang diuji.
"""
import os
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, TAG, World, ar, call, ok, pay, upload_proof
from test_p0_masuk_2 import allin_deal, cost_ledger

NUSA = "owner@nusaproperti.co.id"
BARU = ("1-1300", "2-1470", "1-2100", "1-2200", "2-2100")


def uniq(p):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def recon(actor=FINANCE):
    return {c["code"]: c for c in ok(call(actor, "GET", "/finance/reconcile"))["data"]["checks"]}


def tunggu_hijau(kode, actor=FINANCE, timeout=40):
    """Jurnal lahir dari event (dispatcher ±8 dtk): ulangi pembacaan sampai pemeriksaan ini hijau."""
    end, c = time.time() + timeout, None
    while time.time() < end:
        c = recon(actor)[kode]
        if c["ok"]:
            return c
        time.sleep(1.5)
    return c


@pytest.fixture(scope="module")
def world():
    return World()


# ================================================================== A. kehadiran & label
def test_dua_belas_pemeriksaan_dengan_label_indonesia_dan_bentuk_sama():
    d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
    kode = [c["code"] for c in d["checks"]]
    assert len(kode) == len(set(kode)) >= 12, kode
    for k in BARU:
        c = next((c for c in d["checks"] if c["code"] == k), None)
        assert c, f"pemeriksaan {k} belum ada (ada: {kode})"
        assert " vs " in c["label"] and c["hint"], c
        assert set(("gl", "subledger", "diff", "ok")) <= set(c)
        assert c["diff"] == c["gl"] - c["subledger"]


def test_semua_pemeriksaan_baru_hijau_pada_data_bersama():
    for k in BARU:
        c = tunggu_hijau(k)
        assert c["ok"], f"{k} merah pada data suite: GL {c['gl']} vs subledger {c['subledger']} (Δ {c['diff']}) {c.get('sources')}"


# ================================================================== A. alur nyata -> angka bergerak tepat
def test_piutang_usaha_pasca_bast_dan_denda_ikut_terukur(world):
    awal = tunggu_hijau("1-1300")["sources"]
    d = world.new_deal()["deal_id"]                      # Cash Bertahap 3x, harga unit Rp 500 jt
    ok(pay(d, 100_000_000))
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/bast"))
    ok(pay(d, 150_000_000))                              # sesudah BAST: melunasi piutang
    unit = int(ar(d)["data"]["unit_total"])
    c = tunggu_hijau("1-1300")
    assert c["ok"], c
    assert c["sources"]["sisa_unit_pasca_bast"] - awal["sisa_unit_pasca_bast"] == unit - 250_000_000
    assert c["gl"] == c["subledger"]

    # denda ditagihkan (Dr 1-1300 / Cr 4-1400) -> piutang denda belum lunas ikut terukur
    sname = f"G3 denda {TAG}"
    sid = ok(call(OWNER, "POST", "/payment-schemes", json={
        "name": sname, "kind": "cash_bertahap", "code": f"g3-{TAG.lower()}", "active": True,
        "terms": [{"label": "Termin lampau", "basis": "percent", "value": 100, "due_offset_days": -90}]}))["data"]["id"]
    world.scheme[sname] = sid
    d2 = world.new_deal(scheme=sname)["deal_id"]
    fee = ok(call(OWNER, "POST", f"/finance/late-fees/{d2}/apply", json={}))["created"][0]["amount"]
    c2 = tunggu_hijau("1-1300")
    assert c2["ok"], c2
    assert c2["sources"]["denda_belum_lunas"] - c["sources"]["denda_belum_lunas"] == fee


def test_titipan_biaya_kuitansi_dan_penyaluran_terukur(world):
    awal = tunggu_hijau("2-1470")["sources"]
    d = allin_deal(world)
    iid, total = d["invoice"]["id"], int(d["invoice"]["total"])
    bayar = total // 2
    ok(call(FINANCE, "POST", f"/cost-invoices/{iid}/pay", json={"amount": bayar, "proof_file_ids": [upload_proof()]}))
    salur = min(1_000_000, bayar)
    ok(call(FINANCE, "POST", f"/contracts/{d['contract_id']}/cost-disbursements",
            json={"component_code": "NOTARY_FEE", "amount": salur, "payee": "Notaris Uji G3"}))
    assert cost_ledger(d["contract_id"])["titipan_balance"] == bayar - salur
    c = tunggu_hijau("2-1470")
    assert c["ok"], c
    assert c["sources"]["kuitansi_biaya"] - awal["kuitansi_biaya"] == bayar
    assert c["sources"]["penyaluran"] - awal["penyaluran"] == salur
    assert c["gl"] == c["subledger"]


def test_aset_tetap_perolehan_dan_penyusutan_terukur():
    a0, d0 = tunggu_hijau("1-2100"), tunggu_hijau("1-2200")
    body = {"name": uniq("G3 Laptop"), "category": "komputer_it", "tax_group": "kelompok_1",
            "method": "garis_lurus", "cost": 12_000_000, "funding": "bank"}
    ok(call(FINANCE, "POST", "/fixed-assets/assets", json=body))
    periode = time.strftime("%Y-%m")
    run = ok(call(OWNER, "POST", "/fixed-assets/depreciation/run", json={"period": periode}))["data"]
    a1, d1 = tunggu_hijau("1-2100"), tunggu_hijau("1-2200")
    assert a1["ok"] and d1["ok"], (a1, d1)
    assert a1["subledger"] - a0["subledger"] == 12_000_000
    assert d1["subledger"] - d0["subledger"] == int(run["total_amount"]) > 0


def test_utang_bank_pencairan_dan_angsuran_terukur():
    awal = tunggu_hijau("2-2100")
    loan = ok(call(FINANCE, "POST", "/corp-financing/loans", json={
        "lender": "Bank Uji G3", "lender_type": "bank", "loan_type": "kredit_modal_kerja",
        "principal": 120_000_000, "interest_rate_pct": 10, "tenor_months": 12,
        "amortization_method": "anuitas", "provision_fee": 0}))["data"]
    ok(call(OWNER, "POST", f"/corp-financing/loans/{loan['id']}/activate", json={"source": "bank"}))
    assert tunggu_hijau("2-2100")["subledger"] - awal["subledger"] == 120_000_000
    sched = ok(call(FINANCE, "GET", f"/corp-financing/loans/{loan['id']}"))["data"]["schedule"]
    ang = ok(call(OWNER, "POST", f"/corp-financing/loans/{loan['id']}/pay", json={
        "installment_no": 1, "amount": int(sched[0]["total"]), "source": "bank"}))["data"]
    pokok = sum(int(r.get("paid_principal") or 0) for r in ang["schedule"])
    assert pokok > 0
    c = tunggu_hijau("2-2100")
    assert c["ok"], c
    assert c["subledger"] - awal["subledger"] == 120_000_000 - pokok


# ================================================================== B. korupsi subledger -> MERAH, lalu pulih
def _koleksi():
    from pymongo import MongoClient
    nama = os.environ.get("DB_NAME")
    if not nama:
        pytest.skip("set DB_NAME = DB backend yang diuji (korupsi subledger lewat pymongo)")
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"
    return MongoClient(url)[nama]


def _suntik_piutang(db, nilai):
    i = uniq("g3-ar")
    db.ar_invoices.insert_one({"id": i, "org_id": "org-nusa", "deal_id": uniq("g3-deal"), "status": "unpaid",
                               "items": [{"id": uniq("it"), "label": "Denda uji", "is_penalty": True,
                                          "amount": nilai + 100_000, "paid_amount": 100_000, "status": "partial"}]})
    return lambda: db.ar_invoices.delete_one({"id": i})


def _suntik_kuitansi_biaya(db, nilai):
    i = uniq("g3-kwb")
    db.cost_receipts.insert_one({"id": i, "org_id": "org-nusa", "amount": nilai, "status": "posted",
                                 "created_at": "2026-01-01T00:00:00+00:00"})
    return lambda: db.cost_receipts.delete_one({"id": i})


def _suntik_aset(db, nilai):
    i = uniq("g3-fa")
    db.fixed_assets.insert_one({"id": i, "org_id": "org-nusa", "code": i, "name": "Aset uji G3", "status": "active",
                                "cost": nilai, "accumulated_depreciation": 0})
    return lambda: db.fixed_assets.delete_one({"id": i})


def _suntik_penyusutan(db, nilai):
    a, i = uniq("g3-fa0"), uniq("g3-dep")
    db.fixed_assets.insert_one({"id": a, "org_id": "org-nusa", "code": a, "name": "Aset uji G3", "status": "active",
                                "cost": 0, "accumulated_depreciation": 0})
    db.asset_depreciations.insert_one({"id": i, "org_id": "org-nusa", "asset_id": a, "period": "2026-01",
                                       "amount": nilai})

    def pulih():
        db.asset_depreciations.delete_one({"id": i})
        db.fixed_assets.delete_one({"id": a})
    return pulih


def _suntik_pinjaman(db, nilai):
    i = uniq("g3-ln")
    db.loans.insert_one({"id": i, "org_id": "org-nusa", "no": i, "status": "active", "principal": nilai,
                         "schedule": [], "lender": "Bank Uji G3", "created_at": "2026-01-01T00:00:00+00:00"})
    return lambda: db.loans.delete_one({"id": i})


@pytest.mark.parametrize("kode,suntik,nilai", [
    ("1-1300", _suntik_piutang, 600_000),
    ("2-1470", _suntik_kuitansi_biaya, 5_000_000),
    ("1-2100", _suntik_aset, 9_000_000),
    ("1-2200", _suntik_penyusutan, 300_000),
    ("2-2100", _suntik_pinjaman, 50_000_000),
])
def test_korupsi_subledger_membuat_pemeriksaan_merah_lalu_pulih(kode, suntik, nilai):
    db = _koleksi()
    sebelum = recon(NUSA)[kode]
    sipro_sebelum = recon(FINANCE)[kode]["diff"]
    pulih = suntik(db, nilai)
    try:
        rusak = recon(NUSA)[kode]
        assert rusak["ok"] is False, f"{kode} tetap hijau padahal subledger dirusak: {rusak}"
        assert rusak["diff"] - sebelum["diff"] == -nilai, (sebelum, rusak)     # GL − subledger turun tepat sebesar suntikan
        d = ok(call(NUSA, "GET", "/finance/reconcile"))["data"]
        assert d["ok"] is False and d["failed"] >= 1
        # organisasi lain TIDAK ikut tercemar (reconcile per organisasi)
        assert recon(FINANCE)[kode]["diff"] == sipro_sebelum
    finally:
        pulih()
    pulih_c = recon(NUSA)[kode]
    assert pulih_c["diff"] == sebelum["diff"] and pulih_c["ok"] == sebelum["ok"]


def test_indikator_tidak_menggagalkan_ok_tetapi_tampil_di_rincian():
    """Pemeriksaan bertanda `indicator` hanya peringatan: `ok` global tidak jatuh, `indicators_off` menghitungnya."""
    d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
    assert "indicators_off" in d
    for c in d["checks"]:
        if c.get("indicator") and not c["ok"]:
            assert d["failed"] == len([x for x in d["checks"] if not x["ok"] and not x.get("indicator")])
