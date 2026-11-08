"""Regresi W2-B #3 — BPHTB DIPILIH PER KONTRAK: `bphtb.borne_by` (pembeli · developer · dibagi) + `bphtb.developer_share_pct`.

    API_BASE=http://localhost:8086/api DB_NAME=sipro_w2b MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w2b_bphtb.py -n 0 --noconftest -q -p no:cacheprovider

Yang dibuktikan per opsi: angka komponen, invoice biaya, titipan 2-1470 (kuitansi → penyaluran), beban developer (jurnal 6-1700/2-1100), catatan pajak,
rekonsiliasi hijau, pembatalan (hanya bagian pembeli yang direfund), amandemen skema (keputusan kontrak terbawa), urutan kontrak > proyek > organisasi.
NILAI BAWAAN = perilaku lama: tanpa pilihan eksplisit perlakuan BPHTB mengikuti skema all-in (Exclude → pembeli, All-in Standar → developer).
Harga unit World = Rp 500 jt → BPHTB 5% × (500 jt − 80 jt) = Rp 21.000.000; notaris Rp 7.500.000.
Penimpaan pengaturan dipasang di TINGKAT PROYEK `World` tes (satu tes organisasi mereset di `finally`).

Merah-di-kode-lama: bagian HTTP (kunci/endpoint belum ada). Tes murni (`split_amount`/`apply_to_components`) memanggil modul worktree ini.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, OWNER, World, call, ok  # noqa: E402
from test_p0_siklus_deal import mdb  # noqa: E402
from w2b_common import (ALASAN, BPHTB_500JT, DEVELOPER, DIBAGI, FINLEAD, K_BY, K_PCT, NOTARIS, PEMBELI, allin_id, bayar_invoice,  # noqa: E402
                        comps, contract, delete, journals, ledger, lines_of, live_invoices, new_contract, policy_of, put,
                        reconcile_ok, row, settings, wait_until)

ORG = "org-sipro"
SPS = "/cancel-cost-settlements"


@pytest.fixture(scope="module")
def world():
    return World()


def _items(cid):
    return {i["code"]: i["amount"] for i in live_invoices(cid)[0]["items"]} if live_invoices(cid) else {}


def _green():
    green, bad = reconcile_ok()
    assert green, f"rekonsiliasi merah: {[(c['code'], c['diff']) for c in bad]}"


# ================================================================== aritmetika murni (satu fungsi pembagi)
@pytest.mark.parametrize("total", [0, 1, 7, 999, 21_000_000, 38_500_001, 10 ** 12 + 7])
@pytest.mark.parametrize("pct", [0, 0.01, 25, 33.33, 50, 66.67, 99.99, 100])
def test_split_amount_selalu_menjumlah_ke_total(total, pct):
    import bphtb_policy as bp
    for by in (PEMBELI, DEVELOPER, DIBAGI):
        sp = bp.split_amount(total, by, pct)
        assert sp["total"] == total and sp["buyer"] + sp["developer"] == total and sp["buyer"] >= 0 and sp["developer"] >= 0, (by, sp)
    assert bp.split_amount(total, PEMBELI, pct) == {"total": total, "buyer": total, "developer": 0}
    assert bp.split_amount(total, DEVELOPER, pct) == {"total": total, "buyer": 0, "developer": total}
    dev = bp.split_amount(total, DIBAGI, pct)["developer"]
    assert dev == int(round(total * pct / 100))


def test_split_amount_menolak_masukan_tak_sah():
    import bphtb_policy as bp
    for bad in (-0.01, 100.01, "abc"):
        with pytest.raises(ValueError):
            bp.split_amount(1000, DIBAGI, bad)
    with pytest.raises(ValueError):
        bp.split_amount(1000, "ngawur", 50)


def _komp(treatment="customer_pass_through", amount=BPHTB_500JT, **kw):
    return {"code": "BPHTB", "name": "BPHTB", "amount": amount, "treatment": treatment, "calc_method": "rumus_bphtb",
            "formula": "5% × (harga − NPOPTKP Rp 80.000.000)", "source": "scheme", "discount": 0, **kw}


def test_apply_to_components_tiap_opsi_dan_idempoten():
    import bphtb_policy as bp
    notaris = {"code": "NOTARY_FEE", "name": "Notaris", "amount": NOTARIS, "treatment": "customer_pass_through"}
    base = [_komp(), notaris]
    dev = bp.apply_to_components(base, DEVELOPER, 50, "project")
    assert [(c["code"], c["treatment"], c["amount"]) for c in dev] == [("BPHTB", "developer_borne", BPHTB_500JT), ("NOTARY_FEE", "customer_pass_through", NOTARIS)]
    div = bp.apply_to_components(base, DIBAGI, 40, "contract")
    assert [(c["code"], c["treatment"], c["amount"]) for c in div] == [
        ("BPHTB", "customer_pass_through", 12_600_000), ("BPHTB_DEV", "developer_borne", 8_400_000), ("NOTARY_FEE", "customer_pass_through", NOTARIS)]
    assert div[0]["bphtb_policy"] == {"borne_by": DIBAGI, "share_pct": 40.0, "origin": "contract", "scheme_treatment": "customer_pass_through"}
    assert base[0]["treatment"] == "customer_pass_through" and "bphtb_policy" not in base[0], "masukan tidak diubah"
    # menerapkan ulang pada hasilnya menghasilkan keadaan ekonomis yang sama (dan bisa pindah ke opsi lain tanpa kehilangan total)
    again = bp.apply_to_components(div, DIBAGI, 40, "contract")
    assert bp._signature(again) == bp._signature(div)
    back = bp.apply_to_components(div, PEMBELI, 40, "contract")
    assert [(c["code"], c["treatment"], c["amount"]) for c in back][:1] == [("BPHTB", "customer_pass_through", BPHTB_500JT)] and len(back) == 2
    # dibagi dengan porsi 100% / 0% runtuh menjadi satu baris
    assert [(c["code"], c["treatment"]) for c in bp.apply_to_components(base, DIBAGI, 100, "org")][:1] == [("BPHTB", "developer_borne")]
    assert [(c["code"], c["treatment"]) for c in bp.apply_to_components(base, DIBAGI, 0, "org")][:2] == [("BPHTB", "customer_pass_through"), ("NOTARY_FEE", "customer_pass_through")]
    # skema tanpa BPHTB: tak ada yang diatur
    assert bp.apply_to_components([notaris], DEVELOPER, 50, "org") == [notaris]


def test_apply_to_components_teks_rumus_tidak_menumpuk_saat_diterapkan_berulang():
    import bphtb_policy as bp
    comps_ = [_komp()]
    for pct in (50, 70, 30):
        comps_ = bp.apply_to_components(comps_, DIBAGI, pct, "contract")
    by = {c["code"]: c["formula"] for c in comps_}
    assert by["BPHTB"] == "5% × (harga − NPOPTKP Rp 80.000.000) · bagian pembeli 70%", by["BPHTB"]
    assert by["BPHTB_DEV"] == "5% × (harga − NPOPTKP Rp 80.000.000) · bagian developer 30%", by["BPHTB_DEV"]
    assert bp.apply_to_components(comps_, PEMBELI, 30, "contract")[0]["formula"] == "5% × (harga − NPOPTKP Rp 80.000.000)"


def test_apply_to_components_memutar_ulang_potongan_promo_pada_bagian_pembeli():
    import bphtb_policy as bp
    promo = {"code": "PROMO-X", "name": "Promo BPHTB", "amount": 5_000_000, "source": "promo"}
    base = [_komp(amount=BPHTB_500JT - 5_000_000, discount=5_000_000, discount_lines=[promo],
                  formula="5% × (harga − NPOPTKP Rp 80.000.000) − potongan PROMO-X Rp 5.000.000")]
    div = bp.apply_to_components(base, DIBAGI, 40, "org")
    by = {c["code"]: c for c in div}
    assert by["BPHTB"]["amount"] == 12_600_000 - 5_000_000 and by["BPHTB"]["discount"] == 5_000_000 and by["BPHTB_DEV"]["amount"] == 8_400_000
    assert bp.derive(div)["total"] == BPHTB_500JT and bp.derive(div)["discount"] == 5_000_000
    # promo lebih besar dari bagian pembeli → dibatasi pada nilai bagian pembeli
    big = [_komp(amount=0, discount=BPHTB_500JT, discount_lines=[{**promo, "amount": BPHTB_500JT}])]
    capped = {c["code"]: c for c in bp.apply_to_components(big, DIBAGI, 40, "org")}
    assert capped["BPHTB"]["amount"] == 0 and capped["BPHTB"]["discount"] == 12_600_000 and capped["BPHTB_DEV"]["amount"] == 8_400_000


def test_derive_membaca_snapshot_komponen():
    import bphtb_policy as bp
    assert bp.derive([{"code": "NOTARY_FEE", "amount": 1}]) is None
    assert bp.derive([_komp()])["borne_by"] == PEMBELI and bp.derive([_komp("developer_borne")])["borne_by"] == DEVELOPER
    d = bp.derive(bp.apply_to_components([_komp()], DIBAGI, 25, "org"))
    assert (d["total"], d["buyer"], d["developer"], d["borne_by"], d["share_pct"], d["origin"]) == (BPHTB_500JT, 15_750_000, 5_250_000, DIBAGI, 25.0, "org")
    legacy = bp.derive(None, {"bphtb": 9_000_000, "all_in_by_developer": True})
    assert (legacy["borne_by"], legacy["developer"], legacy["origin"]) == (DEVELOPER, 9_000_000, "legacy")


# ================================================================== BAWAAN = perilaku lama
def test_bawaan_exclude_identik_perilaku_lama(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    rc = {c["code"]: c for c in d["reserve_costs"]["components"]}
    assert "BPHTB_DEV" not in rc and "bphtb_policy" not in rc["BPHTB"], "tanpa pilihan eksplisit komponen reservasi TIDAK disentuh"
    assert comps(cid)["BPHTB"] == ("customer_pass_through", BPHTB_500JT) and comps(cid)["NOTARY_FEE"] == ("customer_pass_through", NOTARIS)
    inv = live_invoices(cid)
    assert len(inv) == 1 and inv[0]["total"] == BPHTB_500JT + NOTARIS and _items(cid) == {"BPHTB": BPHTB_500JT, "NOTARY_FEE": NOTARIS}
    led = ledger(cid)
    assert led["pass_through_total"] == BPHTB_500JT + NOTARIS and led["developer_borne_total"] == 0
    assert led["bphtb"]["borne_by"] == PEMBELI and led["bphtb"]["buyer"] == BPHTB_500JT and led["bphtb"]["origin"] == "skema"
    # uang: kuitansi → titipan 2-1470 (bukan pendapatan) → penyaluran
    rcpt = ok(bayar_invoice(inv[0]))["data"]["receipt"]
    je = [j for j in wait_until(lambda: journals("cost_receipt", rcpt["id"])) or []][0]
    assert lines_of(je)["2-1470"] == (0, BPHTB_500JT + NOTARIS)
    ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-disbursements", json={"component_code": "BPHTB", "amount": BPHTB_500JT, "payee": "BPN Uji W2B"}))
    assert ledger(cid)["titipan_balance"] == NOTARIS


def test_bawaan_all_in_standar_identik_perilaku_lama(world):
    d = new_contract(world, "ALLIN_STD")
    cid = d["contract_id"]
    assert comps(cid)["BPHTB"] == ("developer_borne", BPHTB_500JT) and comps(cid)["NOTARY_FEE"] == ("developer_borne", NOTARIS)
    assert not live_invoices(cid), "semua biaya ditanggung developer → tak ada invoice biaya"
    out = ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB", "amount": BPHTB_500JT, "vendor": "KPP Uji W2B"}))["data"]
    je = [j for j in wait_until(lambda: journals("ap_bill", out["ap_bill"]["id"])) or []][0]
    assert lines_of(je) == {"6-1700": (BPHTB_500JT, 0), "2-1100": (0, BPHTB_500JT)}


# ================================================================== tiap opsi — tingkat PROYEK (kontrak baru)
def test_opsi_pembeli_eksplisit_menimpa_skema_all_in_standar(world):
    with settings(world.project_id, **{K_BY: PEMBELI}):
        d = new_contract(world, "ALLIN_STD")
    cid = d["contract_id"]
    assert comps(cid)["BPHTB"] == ("customer_pass_through", BPHTB_500JT), "pilihan eksplisit menang atas skema"
    assert comps(cid)["NOTARY_FEE"] == ("developer_borne", NOTARIS), "komponen lain tetap mengikuti skema"
    assert _items(cid) == {"BPHTB": BPHTB_500JT}
    r = row(cid)
    assert (r["value"], r["origin"]) == (PEMBELI, "project") and r["snapshot"]["origin"] == "project"


def test_opsi_developer_tidak_ditagih_dan_menjadi_beban_developer(world):
    with settings(world.project_id, **{K_BY: DEVELOPER}):
        d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    assert comps(cid)["BPHTB"] == ("developer_borne", BPHTB_500JT) and "BPHTB_DEV" not in comps(cid)
    assert _items(cid) == {"NOTARY_FEE": NOTARIS}, "BPHTB tidak ditagihkan ke pembeli"
    led = ledger(cid)
    assert led["pass_through_total"] == NOTARIS and led["developer_borne_total"] == BPHTB_500JT
    assert (led["bphtb"]["total"], led["bphtb"]["buyer"], led["bphtb"]["developer"]) == (BPHTB_500JT, 0, BPHTB_500JT)
    # titipan hanya dari bagian pembeli; BPHTB developer dicatat lewat jalur beban developer yang SUDAH ada (akun yang sudah ada)
    ok(bayar_invoice(live_invoices(cid)[0]))
    assert ledger(cid)["titipan_balance"] == NOTARIS
    out = ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB", "amount": BPHTB_500JT, "vendor": "KPP Uji W2B"}))["data"]
    assert out["expense"]["amount"] == BPHTB_500JT
    je = [j for j in wait_until(lambda: journals("ap_bill", out["ap_bill"]["id"])) or []][0]
    assert lines_of(je) == {"6-1700": (BPHTB_500JT, 0), "2-1100": (0, BPHTB_500JT)}
    _green()


def test_opsi_dibagi_dua_baris_angka_tagihan_titipan_dan_beban(world):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 40}):
        d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    buyer, dev = 12_600_000, 8_400_000
    assert comps(cid)["BPHTB"] == ("customer_pass_through", buyer) and comps(cid)["BPHTB_DEV"] == ("developer_borne", dev)
    assert _items(cid) == {"BPHTB": buyer, "NOTARY_FEE": NOTARIS}
    led = ledger(cid)
    assert (led["bphtb"]["total"], led["bphtb"]["buyer"], led["bphtb"]["developer"], led["bphtb"]["share_pct"]) == (BPHTB_500JT, buyer, dev, 40.0)
    assert led["pass_through_total"] == buyer + NOTARIS and led["developer_borne_total"] == dev
    # panel kontrak: ringkasan dan rincian harga membaca baris yang sama (BPHTB pembeli + porsi developer)
    p = policy_of(cid)
    assert (p["summary"]["bphtb"]["buyer"], p["summary"]["bphtb"]["developer"]) == (buyer, dev)
    assert {r["key"]: r["value"] for r in p["keys"]} == {K_BY: DIBAGI, K_PCT: 40.0}
    rows = {r["code"]: r for r in contract(cid)["breakdown"]["rows"]}
    assert rows["BPHTB"]["amount"] == buyer and rows["BPHTB_DEV"]["amount"] == dev and rows["BPHTB_DEV"]["finance_treatment"] == "developer_borne"
    # titipan: pembeli membayar bagiannya (+ notaris) → 2-1470; BPHTB disalurkan sebesar bagian pembeli
    rcpt = ok(bayar_invoice(live_invoices(cid)[0]))["data"]["receipt"]
    je = [j for j in wait_until(lambda: journals("cost_receipt", rcpt["id"])) or []][0]
    assert lines_of(je)["2-1470"] == (0, buyer + NOTARIS)
    ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-disbursements", json={"component_code": "BPHTB", "amount": buyer, "payee": "BPN Uji W2B"}))
    assert ledger(cid)["titipan_balance"] == NOTARIS
    # beban developer untuk porsinya (kode BPHTB_DEV) lewat jalur yang sama dengan komponen ditanggung developer lain
    out = ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB_DEV", "amount": dev, "vendor": "KPP Uji W2B"}))["data"]
    je = [j for j in wait_until(lambda: journals("ap_bill", out["ap_bill"]["id"])) or []][0]
    assert lines_of(je) == {"6-1700": (dev, 0), "2-1100": (0, dev)}
    assert call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB", "amount": 1_000_000}).status_code == 400, \
        "bagian pembeli bukan beban developer"
    _green()


@pytest.mark.parametrize("pct,dev_expected", [(33.33, 6_999_300), (0.01, 2_100), (99.99, 20_997_900)])
def test_dibagi_pembulatan_tidak_menghilangkan_rupiah(world, pct, dev_expected):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: pct}):
        d = new_contract(world, "EXCLUDE")
    c = comps(d["contract_id"])
    assert c["BPHTB_DEV"][1] == dev_expected and c["BPHTB"][1] + c["BPHTB_DEV"][1] == BPHTB_500JT


def test_dibagi_porsi_100_dan_0_runtuh_ke_satu_baris(world):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 100}):
        a = new_contract(world, "EXCLUDE")
    assert comps(a["contract_id"])["BPHTB"] == ("developer_borne", BPHTB_500JT) and "BPHTB_DEV" not in comps(a["contract_id"])
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 0}):
        b = new_contract(world, "EXCLUDE")
    assert comps(b["contract_id"])["BPHTB"] == ("customer_pass_through", BPHTB_500JT) and "BPHTB_DEV" not in comps(b["contract_id"])


# ================================================================== urutan kontrak > proyek > organisasi
def test_urutan_proyek_menang_atas_organisasi_dan_kontrak_menang_atas_proyek(world):
    try:
        ok(call(FINLEAD, "PUT", f"/settings/{K_BY}", json={"value": DEVELOPER, "reason": ALASAN, "scope": "org"}))
        org_only = new_contract(world, "EXCLUDE")
        assert comps(org_only["contract_id"])["BPHTB"][0] == "developer_borne" and row(org_only["contract_id"])["origin"] == "org"
        with settings(world.project_id, **{K_BY: PEMBELI}):
            proj = new_contract(world, "EXCLUDE")
            assert comps(proj["contract_id"])["BPHTB"][0] == "customer_pass_through" and row(proj["contract_id"])["origin"] == "project"
            ok(put(proj["contract_id"], K_BY, DIBAGI))
            r = row(proj["contract_id"])
            assert (r["value"], r["origin"]) == (DIBAGI, "contract")
            assert r["inherited"]["value"] == PEMBELI and r["inherited"]["origin"] == "project"
            assert comps(proj["contract_id"])["BPHTB_DEV"][0] == "developer_borne"
    finally:
        call(OWNER, "POST", f"/settings/{K_BY}/reset", params={"scope": "org"})


def test_pratinjau_skema_mengikuti_pilihan_proyek(world):
    sid = allin_id("EXCLUDE")
    base = ok(call(OWNER, "GET", f"/allin-schemes/{sid}/preview", params={"price": 500_000_000, "project_id": world.project_id}))["data"]
    assert [c["code"] for c in base["components"]][:2] == ["BPHTB", "NOTARY_FEE"] and "bphtb_policy" not in base["components"][0]
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 25}):
        pv = ok(call(OWNER, "GET", f"/allin-schemes/{sid}/preview", params={"price": 500_000_000, "project_id": world.project_id}))["data"]
    by = {c["code"]: (c["treatment"], c["amount"]) for c in pv["components"]}
    assert by["BPHTB"] == ("customer_pass_through", 15_750_000) and by["BPHTB_DEV"] == ("developer_borne", 5_250_000)


def test_promo_bersasaran_bphtb_memotong_bagian_pembeli_saja_pada_dibagi(world):
    """PROMO-BPHTB (potongan 100% komponen BPHTB) menempel pada baris BPHTB = bagian PEMBELI; porsi developer tidak dipotong."""
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 40}):
        d = new_contract(world, "EXCLUDE", promo="PROMO-BPHTB")
    cid = d["contract_id"]
    rows = {c["code"]: c for c in contract(cid)["costs"]["components"]}
    assert rows["BPHTB"]["amount"] == 0 and rows["BPHTB"]["discount"] == 12_600_000
    assert rows["BPHTB_DEV"]["amount"] == 8_400_000 and not rows["BPHTB_DEV"].get("discount")
    assert _items(cid) == {"NOTARY_FEE": NOTARIS}, "bagian pembeli lunas oleh promo; invoice hanya notaris"
    s = ledger(cid)["bphtb"]
    assert (s["total"], s["buyer"], s["developer"], s["discount"]) == (BPHTB_500JT, 0, 8_400_000, 12_600_000)
    # ubah porsi pada kontrak: potongan promo diputar ulang pada bagian pembeli yang baru
    ok(put(cid, K_PCT, 60, "porsi developer dinaikkan menjadi 60 persen"))
    rows = {c["code"]: c for c in contract(cid)["costs"]["components"]}
    assert rows["BPHTB"]["amount"] == 0 and rows["BPHTB"]["discount"] == 8_400_000 and rows["BPHTB_DEV"]["amount"] == 12_600_000


def test_penawaran_dan_reservasi_baru_memakai_pilihan_eksplisit_tapi_tidak_mengubah_yang_lama(world):
    lama = new_contract(world, "EXCLUDE")
    with settings(world.project_id, **{K_BY: DEVELOPER}):
        baru = new_contract(world, "EXCLUDE")
    assert comps(lama["contract_id"])["BPHTB"][0] == "customer_pass_through"
    assert comps(baru["contract_id"])["BPHTB"][0] == "developer_borne"
    assert comps(lama["contract_id"])["BPHTB"][0] == "customer_pass_through"


# ================================================================== per kontrak: perubahan menjadi uang yang benar
def test_per_kontrak_pembeli_ke_dibagi_membatalkan_invoice_lama_dan_menerbitkan_ulang(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    lama = live_invoices(cid)[0]
    ok(put(cid, K_PCT, 30, "porsi developer disepakati 30 persen"))
    assert comps(cid)["BPHTB"][1] == BPHTB_500JT, "porsi saja tidak mengubah komponen selama penanggungnya belum 'dibagi'"
    out = ok(put(cid, K_BY, DIBAGI, "BPHTB dibagi 70/30 sesuai kesepakatan tertulis"))["data"]
    assert out["after"]["voided"] == 1 and out["after"]["reissued"]
    inv = live_invoices(cid)
    assert len(inv) == 1 and inv[0]["id"] != lama["id"] and inv[0]["total"] == 14_700_000 + NOTARIS
    assert [i["status"] for i in ledger(cid)["invoices"] if i["id"] == lama["id"]] == ["void"]
    assert comps(cid)["BPHTB"] == ("customer_pass_through", 14_700_000) and comps(cid)["BPHTB_DEV"] == ("developer_borne", 6_300_000)
    # ubah porsi → komponen dihitung ulang
    ok(put(cid, K_PCT, 60, "porsi developer dinaikkan jadi 60 persen"))
    assert comps(cid)["BPHTB"][1] == 8_400_000 and comps(cid)["BPHTB_DEV"][1] == 12_600_000
    assert live_invoices(cid)[0]["total"] == 8_400_000 + NOTARIS
    # agregat biaya kontrak ikut: pembeli = invoice
    c = contract(cid)
    assert int(c["costs"].get("buyer_total", 8_400_000 + NOTARIS)) == 8_400_000 + NOTARIS
    assert c["breakdown"]["costs_total"] == 8_400_000 + NOTARIS and c["breakdown"]["developer_borne_total"] == 12_600_000
    # deal ikut disinkronkan supaya deal.costs bukan sumber kedua yang basi
    assert {x["code"]: x["amount"] for x in mdb().deals.find_one({"id": d["deal_id"]})["costs"]["components"]}["BPHTB_DEV"] == 12_600_000


def test_per_kontrak_developer_tanpa_biaya_pembeli_lain_tidak_ada_invoice_baru(world):
    d = new_contract(world, "ALLIN_STD")        # BPHTB & notaris developer; tak ada invoice
    cid = d["contract_id"]
    out = ok(put(cid, K_BY, PEMBELI, "kesepakatan baru: BPHTB ditanggung pembeli"))["data"]
    assert out["after"]["voided"] == 0 and out["after"]["reissued"]
    assert _items(cid) == {"BPHTB": BPHTB_500JT}
    out = ok(delete(cid, K_BY, "kembali mengikuti skema All-in Standar"))["data"]
    assert out["after"]["voided"] == 1 and out["after"]["reissued"] is None, "tak ada lagi yang ditagih ke pembeli"
    assert comps(cid)["BPHTB"] == ("developer_borne", BPHTB_500JT) and not live_invoices(cid)
    assert row(cid)["origin"] == "skema"


def test_per_kontrak_mengubah_dari_dibagi_ke_pembeli_mengembalikan_total_utuh(world):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 50}):
        d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    ok(put(cid, K_BY, PEMBELI, "pembeli sepakat menanggung seluruh BPHTB"))
    assert comps(cid)["BPHTB"] == ("customer_pass_through", BPHTB_500JT) and "BPHTB_DEV" not in comps(cid)
    assert live_invoices(cid)[0]["total"] == BPHTB_500JT + NOTARIS
    assert ledger(cid)["bphtb"]["developer"] == 0


# ================================================================== catatan pajak
def test_catatan_pajak_bphtb_menampilkan_penanggung_dari_satu_fungsi_pembagi(world):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 40}):
        d = new_contract(world, "EXCLUDE")
    recs = ok(call(FINANCE, "GET", "/tax/records", params={"type": "bphtb", "limit": 500}))["data"]
    r = next(x for x in recs if x["deal_id"] == d["deal_id"])
    assert r["amount"] == BPHTB_500JT, "jumlah catatan pajak = total BPHTB (kewajiban ke negara tidak berubah oleh siapa penanggungnya)"
    assert r["bphtb_split"] == {"borne_by": DIBAGI, "buyer": 12_600_000, "developer": 8_400_000, "share_pct": 40.0, "origin": "project"}
    e = new_contract(world, "EXCLUDE")
    recs = ok(call(FINANCE, "GET", "/tax/records", params={"type": "bphtb", "limit": 500}))["data"]
    r2 = next(x for x in recs if x["deal_id"] == e["deal_id"])
    assert r2["bphtb_split"]["borne_by"] == PEMBELI and r2["bphtb_split"]["buyer"] == BPHTB_500JT and r2["amount"] == BPHTB_500JT


# ================================================================== amandemen skema biaya membawa keputusan kontrak
def _amend(cid, scheme_code):
    am = ok(call(FINANCE, "POST", f"/contracts/{cid}/allin-amendments", json={"scheme_id": allin_id(scheme_code),
                                                                                "reason": "uji W2-B amandemen skema biaya"}))["data"]
    return am


def test_amandemen_membawa_pilihan_eksplisit_kontrak_dan_skema_tanpa_pilihan_mengikuti_skema_baru(world):
    # (a) kontrak TANPA pilihan eksplisit: pindah ke All-in Standar → BPHTB mengikuti skema baru (developer)
    a = new_contract(world, "EXCLUDE")
    am = _amend(a["contract_id"], "ALLIN_STD")
    assert {c["code"]: c["treatment"] for c in am["to"]["components"]}["BPHTB"] == "developer_borne"
    ok(call(FINLEAD, "POST", f"/allin-amendments/{am['id']}/decide", json={"approve": True, "note": "setuju uji"}))
    assert comps(a["contract_id"])["BPHTB"] == ("developer_borne", BPHTB_500JT)
    # (b) kontrak DENGAN pilihan eksplisit 'dibagi': pindah skema tidak mengubah keputusan itu
    b = new_contract(world, "EXCLUDE")
    ok(put(b["contract_id"], K_BY, DIBAGI, "BPHTB dibagi sesuai kesepakatan khusus"))
    ok(put(b["contract_id"], K_PCT, 20, "porsi developer 20 persen"))
    am = _amend(b["contract_id"], "ALLIN_STD")
    by = {c["code"]: (c["treatment"], c["amount"]) for c in am["to"]["components"]}
    assert by["BPHTB"] == ("customer_pass_through", 16_800_000) and by["BPHTB_DEV"] == ("developer_borne", 4_200_000)
    ok(call(FINLEAD, "POST", f"/allin-amendments/{am['id']}/decide", json={"approve": True, "note": "setuju uji"}))
    assert comps(b["contract_id"])["BPHTB_DEV"] == ("developer_borne", 4_200_000)
    assert row(b["contract_id"])["origin"] == "contract", "penimpaan kontrak tetap berlaku sesudah amandemen"


# ================================================================== pembatalan: hanya bagian pembeli yang direfund
def test_pembatalan_dengan_bphtb_dibagi_refund_hanya_bagian_pembeli_dan_rekonsiliasi_hijau(world):
    with settings(world.project_id, **{K_BY: DIBAGI, K_PCT: 40}):
        d = new_contract(world, "EXCLUDE")
    cid, did = d["contract_id"], d["deal_id"]
    buyer, dev = 12_600_000, 8_400_000
    inv = live_invoices(cid)[0]
    ok(bayar_invoice(inv))                                   # pembeli membayar bagiannya + notaris (20,1 jt) → titipan 2-1470
    ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB_DEV", "amount": dev, "vendor": "KPP Uji W2B"}))   # developer membayar porsinya
    assert ledger(cid)["titipan_balance"] == buyer + NOTARIS
    ok(call(OWNER, "POST", f"/deals/{did}/cancel", json={"reason": "uji W2-B batal dengan BPHTB dibagi"}))
    s = mdb().cost_deposit_settlements.find_one({"deal_id": did})
    assert s and s["state"] == "diajukan"
    assert s["snapshot"]["titipan_balance"] == buyer + NOTARIS, "yang direfund = titipan pembeli saja; porsi developer bukan uang pembeli"
    ok(call(FINLEAD, "POST", f"{SPS}/{s['id']}/decision", json={"approved": True, "note": "setuju refund titipan biaya pembeli"}))
    s = mdb().cost_deposit_settlements.find_one({"id": s["id"]})
    assert s["state"] == "disetujui" and int(s["settlement"]["refund_amount"]) == buyer + NOTARIS
    je = wait_until(lambda: journals("cost_settlement", s["id"]))
    assert je and lines_of(je[0])["2-1470"][0] == buyer + NOTARIS and lines_of(je[0])["2-1460"][1] == buyer + NOTARIS
    assert ledger(cid)["titipan_balance"] == 0
    _green()
