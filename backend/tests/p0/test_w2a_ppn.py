"""Regresi W2-A — PPN TERKONFIGURASI per proyek (docs/audit/12 keputusan #1): `tax.ppn.mode` (eksklusif · inklusif · bebas_ppn) + `tax.ppn.rate`.

    API_BASE=http://localhost:8080/api DB_NAME=sipro_w2a MONGO_URL=... python -m pytest backend/tests/p0/test_w2a_ppn.py -n 0 --noconftest -q

Bawaan = perilaku sistem sebelum pengaturan ada (EKSKLUSIF: DPP = harga, PPN = harga × tarif; tidak ditambahkan ke tagihan pembeli).
Mengganti mode/tarif berlaku KE DEPAN: dokumen yang sudah lahir membekukan mode+tarif saat lahir. Semua penimpaan memakai tingkat PROYEK
milik tes ini dan di-reset di `finally` (suite penuh memakai organisasi yang sama).
"""
import os
import sys
import time

import pytest

import aio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, OWNER, SALES, TAG, World, call, ok  # noqa: E402

FINLEAD = "finlead@sipro.co.id"
K_MODE, K_RATE = "tax.ppn.mode", "tax.ppn.rate"
ALASAN = "uji W2-A PPN terkonfigurasi"
HARGA = 500_000_000


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world_b():
    return World()


def _put(key, value, project_id, who=FINLEAD, reason=ALASAN):
    return call(who, "PUT", f"/settings/{key}", json={"value": value, "reason": reason, "scope": "project", "scope_id": project_id})


def _reset(key, project_id):
    call(OWNER, "POST", f"/settings/{key}/reset", params={"scope": "project", "scope_id": project_id})


def _deal(world, book=True, scheme="Cash Bertahap (3x)"):
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji PPN {TAG} {world.next_unit}",
                                                  "phone": "+62812" + str(int(time.time() * 1000))[-9:], "source": "manual"}))["data"]
    deal = ok(call(SALES, "POST", "/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
                                                          "scheme_id": world.scheme[scheme]}))["data"]
    if book:
        ok(call(SALES, "POST", f"/deals/{deal['id']}/book", json={}))
    return {"deal_id": deal["id"], "unit_id": unit["id"]}


def _ar(deal_id):
    return ok(call(FINANCE, "GET", f"/finance/ar/{deal_id}"))["data"]


def _recs(deal_id):
    rows = ok(call(FINANCE, "GET", "/tax/records", params={"limit": 500}))["data"]
    return {r["type"]: r for r in rows if r.get("deal_id") == deal_id}


def _faktur(deal_id):
    return call(FINANCE, "POST", "/tax/faktur", json={"deal_id": deal_id, "buyer_npwp": "00.000.000.0-000.000"})


def _reconcile_ok(timeout=30):
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"]
        time.sleep(1.5)


def _lama(price, rate):
    """Rumus LAMA persis (sebelum W2-A): `round(price * ppn_rate / 100)`."""
    return round(price * rate / 100)


# ================================================================== bawaan identik dengan perilaku lama
@pytest.mark.parametrize("price", [0, 1, 79_999_999, 80_000_000, 500_000_000, 850_000_001, 10 ** 12])
@pytest.mark.parametrize("rate", [0.0, 11.0, 12.0, 12.5])
def test_eksklusif_identik_dengan_rumus_lama_untuk_banyak_harga(price, rate):
    import finance_engine as fe
    import tax_master as tm
    s = tm.ppn_split(price, "eksklusif", rate)
    assert (s["ppn"], s["dpp"], s["rate"]) == (_lama(price, rate), price, rate)
    cfg = {"ppn_rate": rate, "bphtb_rate": 5.0, "pph_rate": 2.5, "npoptkp": 80_000_000}   # tanpa ppn_mode = bentuk lama
    t = fe.compute_taxes(price, cfg)
    base = max(0, price - 80_000_000)
    assert (t["ppn"], t["ppn_rate"], t["bphtb"], t["bphtb_base"], t["pph"]) == (
        _lama(price, rate), rate, round(base * 5.0 / 100), base, round(price * 2.5 / 100))


@pytest.mark.parametrize("price,rate", [(500_000_000, 12.0), (1, 12.0), (850_000_001, 11.0), (999_999, 0.0)])
def test_inklusif_dpp_ditambah_ppn_sama_dengan_harga(price, rate):
    import tax_master as tm
    s = tm.ppn_split(price, "inklusif", rate)
    assert s["dpp"] + s["ppn"] == price and s["dpp"] == (round(price * 100 / (100 + rate)) if rate else price)
    b = tm.ppn_split(price, "bebas_ppn", rate)
    assert (b["ppn"], b["rate"], b["dpp"]) == (0, 0.0, price)
    with pytest.raises(ValueError):
        tm.ppn_split(price, "ngawur", rate)


def test_deal_bawaan_angka_pajak_ar_dan_faktur_sama_dengan_perilaku_lama(world):
    d = _deal(world)
    ar = _ar(d["deal_id"])
    t = ar["taxes"]
    assert (t["ppn"], t["ppn_rate"], t["ppn_mode"], t["dpp"]) == (_lama(HARGA, 12.0), 12.0, "eksklusif", HARGA)
    assert ar["total"] == HARGA, "PPN tidak ditambahkan ke tagihan pembeli (perilaku lama)"
    assert ar["policy_snapshot"]["tax.ppn.mode"] == {"value": "eksklusif", "origin": "default"}
    r = _recs(d["deal_id"])
    assert (r["ppn"]["base"], r["ppn"]["rate"], r["ppn"]["amount"]) == (HARGA, 12.0, _lama(HARGA, 12.0))
    assert r["bphtb"]["amount"] == round((HARGA - 80_000_000) * 5 / 100) and r["pph"]["amount"] == round(HARGA * 2.5 / 100)
    f = ok(_faktur(d["deal_id"]))["data"]
    assert (f["dpp"], f["ppn"], f["ppn_rate"]) == (HARGA, _lama(HARGA, 12.0), 12.0)
    deal = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]
    assert deal["pricing"]["taxes"]["ppn_mode"] == "eksklusif" and deal["pricing"]["policy_snapshot"]["tax.ppn.rate"]["value"] == 12.0


# ================================================================== inklusif
def test_mode_inklusif_per_proyek(world, world_b):
    try:
        ok(_put(K_MODE, "inklusif", world.project_id, reason="harga jual proyek A sudah termasuk PPN"))
        d = _deal(world)
        ar = _ar(d["deal_id"])
        dpp = round(HARGA * 100 / 112)
        t = ar["taxes"]
        assert (t["ppn_mode"], t["dpp"], t["ppn"], t["ppn_rate"]) == ("inklusif", dpp, HARGA - dpp, 12.0)
        assert ar["total"] == HARGA, "tagihan pembeli tetap = harga (PPN ada DI DALAM harga)"
        assert ar["policy_snapshot"]["tax.ppn.mode"] == {"value": "inklusif", "origin": "project"}
        r = _recs(d["deal_id"])
        assert (r["ppn"]["base"], r["ppn"]["amount"]) == (dpp, HARGA - dpp)
        assert r["pph"]["amount"] == round(HARGA * 2.5 / 100)   # PPh/BPHTB tidak terpengaruh mode PPN
        f = ok(_faktur(d["deal_id"]))["data"]
        assert (f["dpp"], f["ppn"], f["ppn_mode"]) == (dpp, HARGA - dpp, "inklusif") and f["dpp"] + f["ppn"] == HARGA
        # penawaran proyek yang sama membawa mode + snapshot; proyek lain tetap eksklusif
        unit = world.units[world.next_unit]
        q = ok(call(SALES, "POST", "/quotations/simulate", json={"unit_id": unit["id"]}))["data"]
        assert q["taxes"]["ppn_mode"] == "inklusif" and q["policy_snapshot"]["tax.ppn.mode"]["origin"] == "project"
        d_b = _deal(world_b)
        assert _ar(d_b["deal_id"])["taxes"]["ppn_mode"] == "eksklusif"
    finally:
        _reset(K_MODE, world.project_id)
    assert _ar(_deal(world)["deal_id"])["taxes"]["ppn_mode"] == "eksklusif"   # reset → kembali bawaan


# ================================================================== bebas PPN
def test_mode_bebas_ppn_tanpa_catatan_ppn_dan_tanpa_faktur(world):
    try:
        ok(_put(K_MODE, "bebas_ppn", world.project_id, reason="rumah subsidi — dibebaskan dari PPN"))
        d = _deal(world)
        ar = _ar(d["deal_id"])
        t = ar["taxes"]
        assert (t["ppn_mode"], t["ppn"], t["ppn_rate"]) == ("bebas_ppn", 0, 0.0) and ar["total"] == HARGA
        r = _recs(d["deal_id"])
        assert "ppn" not in r and "bphtb" in r and "pph" in r, "Bebas PPN → tidak ada catatan PPN"
        rf = _faktur(d["deal_id"])
        assert rf.status_code == 400 and "BEBAS PPN" in rf.text, (rf.status_code, rf.text[:200])
        cands = ok(call(FINANCE, "GET", "/tax/faktur-candidates"))["data"]
        assert d["deal_id"] not in {c["deal_id"] for c in cands}
        unit = world.units[world.next_unit]
        q = ok(call(SALES, "POST", "/quotations/simulate", json={"unit_id": unit["id"]}))["data"]
        assert (q["taxes"]["ppn_mode"], q["taxes"]["ppn"]) == ("bebas_ppn", 0)
    finally:
        _reset(K_MODE, world.project_id)


# ================================================================== berlaku KE DEPAN saja
def test_mengganti_mode_tidak_menghitung_ulang_dokumen_lama(world):
    lama = _deal(world)                       # lahir saat bawaan (eksklusif, 12%)
    belum_ar = _deal(world, book=False)       # reservasi lahir SEBELUM ganti mode; AR-nya lahir SESUDAH
    ar0 = _ar(lama["deal_id"])
    f_lama = None
    try:
        ok(_put(K_MODE, "inklusif", world.project_id, reason="mulai kuartal ini harga inklusif PPN"))
        ok(_put(K_RATE, 11.0, world.project_id, reason="tarif PPN efektif 11% — uji ke depan saja"))
        assert _ar(lama["deal_id"])["taxes"] == ar0["taxes"], "AR lama tidak berubah"
        # susun-ulang jadwal (ganti skema) JUGA tidak menghitung ulang PPN deal lama
        ok(call(FINANCE, "POST", f"/finance/ar/{lama['deal_id']}/schedule", json={"scheme_id": world.scheme["Cash Bertahap (3x)"]}))
        ar1 = _ar(lama["deal_id"])
        assert (ar1["taxes"]["ppn_mode"], ar1["taxes"]["ppn"], ar1["taxes"]["ppn_rate"]) == ("eksklusif", _lama(HARGA, 12.0), 12.0)
        assert ar1["policy_snapshot"]["tax.ppn.mode"]["value"] == "eksklusif"
        assert _recs(lama["deal_id"])["ppn"]["amount"] == _lama(HARGA, 12.0)
        # Faktur Pajak deal lama memakai mode+tarif yang dibekukan, bukan master hari ini
        f_lama = ok(_faktur(lama["deal_id"]))["data"]
        assert (f_lama["dpp"], f_lama["ppn"], f_lama["ppn_rate"]) == (HARGA, _lama(HARGA, 12.0), 12.0)
        # reservasi yang lahir sebelum ganti mode: AR yang terbit sesudahnya tetap memakai mode saat reservasi
        ok(call(SALES, "POST", f"/deals/{belum_ar['deal_id']}/book", json={}))
        ar2 = _ar(belum_ar["deal_id"])
        assert (ar2["taxes"]["ppn_mode"], ar2["taxes"]["ppn"]) == ("eksklusif", _lama(HARGA, 12.0))
        # deal BARU memakai mode + tarif baru
        baru = _ar(_deal(world)["deal_id"])
        dpp = round(HARGA * 100 / 111)
        assert (baru["taxes"]["ppn_mode"], baru["taxes"]["ppn_rate"], baru["taxes"]["dpp"], baru["taxes"]["ppn"]) == ("inklusif", 11.0, dpp, HARGA - dpp)
    finally:
        _reset(K_MODE, world.project_id)
        _reset(K_RATE, world.project_id)
    assert _ar(lama["deal_id"])["taxes"]["ppn_mode"] == "eksklusif"


def test_snapshot_deal_dan_penawaran_dipakai_pembaca(world):
    """Pembaca (dasar komisi 'nilai bersih', susun-ulang AR) memakai mode+tarif yang dibekukan saat lahir, bukan master."""
    import tax_master as tm
    eks = {"ppn_rate": 12.0, "ppn_mode": "eksklusif"}
    ar = {"policy_snapshot": {K_MODE: {"value": "inklusif", "origin": "project"}, K_RATE: {"value": 11.0, "origin": "org"}}}
    deal = {"pricing": {"taxes": eks}}
    assert tm._frozen_ppn(ar, deal)["mode"] == "inklusif"                       # AR menang atas deal
    assert tm._frozen_ppn(None, deal)["mode"] == "eksklusif" and tm._frozen_ppn(None, deal)["rate"] == 12.0
    assert tm._frozen_ppn({"taxes": {"ppn_rate": 11.0}}, None)["mode"] == "eksklusif"   # dokumen lama tanpa mode = eksklusif
    assert tm._frozen_ppn({"taxes": {}}, {"pricing": None}) is None and tm._frozen_ppn(None, None) is None
    # tanpa dokumen beku → master hari ini (kunci tambahan `policy_snapshot` ada)
    c = aio.run(tm.config_for_deal("org-sipro", {"project_id": None}, None))
    assert c["ppn_mode"] in tm.PPN_MODES and set(c["policy_snapshot"]) == {K_MODE, K_RATE}
    d = {"pricing": {"taxes": {"ppn_rate": 9.0, "ppn_mode": "inklusif"}}, "project_id": None}
    c2 = aio.run(tm.config_for_deal("org-sipro", d, None))
    assert (c2["ppn_mode"], c2["ppn_rate"]) == ("inklusif", 9.0)


def test_dasar_komisi_nilai_bersih_mengikuti_mode_beku():
    import finance_engine as fe
    price = 500_000_000
    for mode, harapan in (("eksklusif", price - _lama(price, 12.0)), ("inklusif", round(price * 100 / 112)), ("bebas_ppn", price)):
        deal = {"pricing": {"taxes": {"ppn_rate": 12.0, "ppn_mode": mode}}}
        cfg = aio.run(fe.get_finance_config("org-sipro", deal=deal))
        assert price - fe.compute_taxes(price, cfg)["ppn"] == harapan, mode


# ================================================================== izin & jurnal & rekonsiliasi
def test_ubah_mode_ppn_khusus_manajer_keuangan_dan_owner(world):
    for who in (FINANCE, SALES):
        assert _put(K_MODE, "bebas_ppn", world.project_id, who=who).status_code == 403
        assert _put(K_RATE, 1, world.project_id, who=who).status_code == 403
    assert call(FINLEAD, "PUT", f"/settings/{K_MODE}", json={"value": "bebas_ppn", "scope": "project", "scope_id": world.project_id}).status_code == 400
    for who in (FINLEAD, OWNER):
        try:
            assert _put(K_MODE, "inklusif", world.project_id, who=who).status_code == 200
        finally:
            _reset(K_MODE, world.project_id)


def test_pajak_ppn_inklusif_dilaporkan_menjurnal_jumlah_catatan_dan_rekonsiliasi_hijau(world):
    import db as dbm
    try:
        ok(_put(K_MODE, "inklusif", world.project_id, reason="uji jurnal PPN inklusif"))
        d_in = _deal(world)
    finally:
        _reset(K_MODE, world.project_id)
    d_ek = _deal(world)
    for d, harapan in ((d_in, HARGA - round(HARGA * 100 / 112)), (d_ek, _lama(HARGA, 12.0))):
        rec = _recs(d["deal_id"])["ppn"]
        assert rec["amount"] == harapan
        ok(call(FINANCE, "PUT", f"/tax/records/{rec['id']}", json={"status": "reported"}))

        async def jurnal():
            return await dbm.db.journal_entries.find_one({"source_type": "tax_accrual", "source_id": rec["id"]}, {"_id": 0})
        t_end = time.time() + 30
        je = aio.run(jurnal())
        while not je and time.time() < t_end:
            time.sleep(1)
            je = aio.run(jurnal())
        assert je, "akrual PPN dilaporkan harus berjurnal"
        by = {ln["account_code"]: ln for ln in je["lines"]}
        assert by["6-1400"]["debit"] == harapan and by["2-1300"]["credit"] == harapan, "jurnal mengikuti jumlah catatan pajak (mode)"
    assert _reconcile_ok(), "rekonsiliasi GL/subledger harus tetap hijau"


def test_ppn_masukan_memakai_tarif_nominal_organisasi(world):
    """Mode Bebas PPN hanya untuk PENJUALAN: estimasi PPN masukan dari tagihan vendor tetap memakai tarif nominal."""
    try:
        ok(_put(K_MODE, "bebas_ppn", world.project_id, reason="uji PPN masukan tetap nominal"))
        d = ok(call(FINANCE, "GET", "/tax/ppn-input"))["data"]
        assert d["rate"] == 12.0
    finally:
        _reset(K_MODE, world.project_id)


def test_semua_opsi_mode_tersedia_tidak_ada_pengaturan_mati():
    row = [r for r in ok(call(OWNER, "GET", "/settings", params={"q": K_MODE}))["data"] if r["key"] == K_MODE][0]
    assert row["options"] == ["eksklusif", "inklusif", "bebas_ppn"] and row["unavailable"] == {}
    assert set(row["option_labels"]) == set(row["options"])
