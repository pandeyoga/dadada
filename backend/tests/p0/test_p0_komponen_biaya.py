"""Regresi G-C — MASTER KOMPONEN BIAYA & SKEMA ALL-IN divalidasi di API (audit FN-02, FN-12c).

    API_BASE=http://localhost:8073/api DB_NAME=sipro_gc python -m pytest backend/tests/p0/test_p0_komponen_biaya.py \
        -n 0 --noconftest -q -p no:cacheprovider

Sebelum perbaikan: `POST /cost-components` menerima nominal -5 jt, persen 500, akun "9-9999", cara hitung "xyz";
skema menerima butir yang merujuk komponen yang tidak ada / nonaktif / nominal terkunci negatif; komponen
NONAKTIF tetap ikut snapshot reservasi baru; skema pencairan KPR menerima tahap -50% + 150%; pajak -5% / 500%.

Semua komponen uji dibuat dengan `sync_schemes=false` + nominal 0 supaya tidak menempel ke skema bersama
(ALLIN_STD/EXCLUDE) yang dipakai tes lain. Kode komponen/skema unik per jalan (TAG).
"""
import random
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, World, call, ok

TAG = uuid.uuid4().hex[:6].upper()
NUSA = "owner@nusaproperti.co.id"
# Bank khusus tes ini: skema pencairan KPR yang dibuat di sini TIDAK boleh menjadi skema bawaan pengajuan bank
# lain (tes KPR lain memakai BTN; skema 70/30 uji ini pernah membuat pencairan 500 jt hanya 350 jt).
BANK_UJI = f"Bank Uji GC {TAG}"
_n = [0]


def kode(prefix="GC"):
    _n[0] += 1
    return f"{prefix}{TAG}{_n[0]}"


def komp(code=None, **kw):
    body = {"code": kode() if code is None else code, "name": "Komponen uji G-C", "calc_method": "nominal_tetap",
            "default_treatment": "customer_pass_through", "amount": 0, "pct": 0, "sync_schemes": False}
    body.update(kw)
    return body


def buat_komp(actor=OWNER, **kw):
    return ok(call(actor, "POST", "/cost-components", json=komp(**kw)))["data"]


def semua_komp(actor=OWNER):
    return ok(call(actor, "GET", "/cost-components", params={"include_inactive": True}))["data"]


def skema_body(items, **kw):
    code = kode("SK")
    body = {"code": code, "name": f"Skema uji {code}", "items": items}
    body.update(kw)
    return body


def item(code, tr="customer_pass_through", ov=None):
    return {"component_code": code, "treatment": tr, "override_amount": ov}


def sebab(r):
    try:
        return r.json().get("detail")
    except Exception:  # noqa: BLE001
        return r.text[:200]


# ------------------------------------------------------------------ master komponen: nilai
@pytest.mark.parametrize("ubah", [
    {"calc_method": "nominal_tetap", "amount": -5_000_000},
    {"calc_method": "persen_harga", "pct": 500},
    {"calc_method": "persen_harga", "pct": -10},
    {"calc_method": "rumus_bphtb", "pct": 100.5},
    {"calc_method": "xyz"},
    {"default_treatment": "foo"},
    {"amount": 10 ** 15},
])
def test_komponen_nilai_tak_wajar_ditolak_dan_tidak_tersimpan(ubah):
    body = komp(**ubah)
    r = call(OWNER, "POST", "/cost-components", json=body)
    assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"
    assert body["code"] not in {c["code"] for c in semua_komp()}, "komponen cacat tetap tersimpan"


def test_komponen_kode_dan_nama_wajib_sah():
    for ubah in ({"code": ""}, {"code": "a b"}, {"code": "X"}, {"code": "TAK BOLEH SPASI"}, {"name": "   "}):
        r = call(OWNER, "POST", "/cost-components", json=komp(**ubah))
        assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"


def test_komponen_kode_unik_per_org_dan_boleh_sama_di_org_lain():
    c = buat_komp()
    r = call(OWNER, "POST", "/cost-components", json=komp(c["code"]))
    assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
    # kode sama di org lain = komponen lain (unik per organisasi)
    r2 = call(NUSA, "POST", "/cost-components", json=komp(c["code"]))
    assert r2.status_code == 200, f"{r2.status_code} {r2.text[:200]}"
    assert ok(call(OWNER, "GET", "/cost-components", params={"include_inactive": True}))["data"]
    ids = {x["id"] for x in semua_komp() if x["code"] == c["code"]}
    assert ids == {c["id"]}, "komponen org lain tidak boleh tampak di org ini"


def test_komponen_kode_sama_paralel_hanya_satu_lahir():
    from test_p0_masuk import race
    code = kode("PAR")
    rs = race([lambda: call(OWNER, "POST", "/cost-components", json=komp(code)) for _ in range(4)])
    assert sorted(r.status_code for r in rs).count(200) == 1, [r.status_code for r in rs]
    assert len([x for x in semua_komp() if x["code"] == code]) == 1


# ------------------------------------------------------------------ master komponen: akun GL
@pytest.mark.parametrize("ubah,potongan", [
    ({"gl_expense": "9-9999"}, "tidak ada"),
    ({"gl_expense": "XYZ"}, "tidak valid"),
    ({"gl_expense": "2-1100"}, "bertipe"),         # akun utang dipakai sebagai akun beban
    ({"gl_liability": "6-1700"}, "bertipe"),       # akun beban dipakai sebagai akun titipan
    ({"gl_liability": "2-1400"}, "kendali"),       # akun kendali kewajiban kontrak
    ({"gl_ap": "2-1300"}, "2-1100"),               # pembayaran AP selalu mendebet 2-1100
    ({"gl_ap": "1-1300"}, "bertipe"),
])
def test_komponen_akun_gl_harus_nyata_aktif_dan_bertipe_sesuai(ubah, potongan):
    r = call(OWNER, "POST", "/cost-components", json=komp(**ubah))
    assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"
    assert potongan in str(sebab(r)), sebab(r)


def test_komponen_akun_gl_nonaktif_ditolak():
    kodea = f"6-{random.randint(5000, 9998)}"
    r = call(OWNER, "POST", "/gl/accounts", json={"code": kodea, "name": f"Beban uji G-C {TAG}", "type": "expense"})
    if r.status_code != 200:
        pytest.skip(f"tidak bisa membuat akun uji: {r.status_code} {r.text[:120]}")
    ok(call(OWNER, "PUT", f"/gl/accounts/{kodea}", json={"is_active": False}))
    r = call(OWNER, "POST", "/cost-components", json=komp(gl_expense=kodea))
    assert r.status_code == 400 and "NONAKTIF" in str(sebab(r)), f"{r.status_code} {r.text[:200]}"


def test_komponen_akun_gl_sah_diterima_dan_kosong_memakai_bawaan():
    c = buat_komp(gl_expense="6-1700", gl_liability="2-1470", gl_ap="2-1100")
    assert (c["gl_expense"], c["gl_liability"], c["gl_ap"]) == ("6-1700", "2-1470", "2-1100")
    d = buat_komp()
    assert (d["gl_expense"], d["gl_liability"], d["gl_ap"]) == ("6-1700", "2-1470", "2-1100")


# ------------------------------------------------------------------ update komponen
@pytest.mark.parametrize("ubah", [
    {"calc_method": "xyz"}, {"default_treatment": "foo"}, {"pct": -3}, {"pct": 101}, {"amount": -1},
    {"gl_expense": "9-9999"}, {"gl_ap": "2-1300"}, {"name": "   "},
])
def test_update_komponen_nilai_cacat_ditolak_dan_data_tidak_berubah(ubah):
    c = buat_komp(amount=1000, pct=2)
    r = call(OWNER, "PUT", f"/cost-components/{c['id']}", json=ubah)
    assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"
    now = [x for x in semua_komp() if x["id"] == c["id"]][0]
    for k in ("calc_method", "default_treatment", "pct", "amount", "gl_expense", "gl_ap", "name"):
        assert now[k] == c[k], f"{k} berubah: {c[k]!r} -> {now[k]!r}"


def test_update_komponen_sah_dan_nonaktifkan_komponen_selalu_bisa():
    c = buat_komp(amount=1000)
    d = ok(call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 2500, "pct": 1.5}))["data"]
    assert d["amount"] == 2500 and d["pct"] == 1.5
    # komponen yang SUDAH rusak (data lama, ditanam lewat DB) tetap dapat dinonaktifkan tanpa membereskan semuanya
    from pymongo import MongoClient
    import os
    db_name = os.environ.get("DB_NAME")
    if db_name:
        url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"
        MongoClient(url)[db_name].cost_components.update_one({"id": c["id"]}, {"$set": {"pct": 500}})
        ok(call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"is_active": False}))
        assert [x for x in semua_komp() if x["id"] == c["id"]][0]["is_active"] is False


def test_komponen_booking_nominal_tetap_terkunci():
    b = [x for x in semua_komp() if x["code"] == "BOOKING"][0]
    ok(call(OWNER, "PUT", f"/cost-components/{b['id']}", json={"amount": 999_999, "pct": 50}))
    now = [x for x in semua_komp() if x["id"] == b["id"]][0]
    assert now["amount"] == b["amount"] and now["pct"] == b["pct"]


def test_komponen_org_lain_tidak_bisa_diubah():
    c = buat_komp()
    r = call(NUSA, "PUT", f"/cost-components/{c['id']}", json={"name": "dibajak"})
    assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"


def test_sinkron_ke_skema_dapat_dimatikan():
    """`sync_schemes=false` (opsi baru): komponen baru TIDAK menempel ke skema yang sedang dijual."""
    c = buat_komp()
    skema = ok(call(OWNER, "GET", "/allin-schemes", params={"include_inactive": True}))["data"]
    assert all(c["code"] not in [i["component_code"] for i in s["items"]] for s in skema)


# ------------------------------------------------------------------ skema all-in: butir
@pytest.fixture(scope="module")
def komp_aktif():
    return buat_komp()


def test_skema_butir_komponen_tak_ada_ditolak(komp_aktif):
    body = skema_body([item(komp_aktif["code"]), item("TIDAK_ADA_" + TAG)])
    r = call(OWNER, "POST", "/allin-schemes", json=body)
    assert r.status_code == 400 and "tidak ada" in str(sebab(r)), f"{r.status_code} {r.text[:200]}"
    kodes = {s["code"] for s in ok(call(OWNER, "GET", "/allin-schemes", params={"include_inactive": True}))["data"]}
    assert body["code"] not in kodes


@pytest.mark.parametrize("ov", [-7_500_000, 10 ** 15])
def test_skema_nominal_terkunci_tak_wajar_ditolak(komp_aktif, ov):
    r = call(OWNER, "POST", "/allin-schemes", json=skema_body([item(komp_aktif["code"], ov=ov)]))
    assert r.status_code == 400, f"{ov}: {r.status_code} {r.text[:200]}"


def test_skema_butir_ganda_perlakuan_salah_dan_kosong_ditolak(komp_aktif):
    c = komp_aktif["code"]
    for items in ([item(c), item(c)], [item(c, tr="foo")], [], [{"treatment": "customer_pass_through"}]):
        r = call(OWNER, "POST", "/allin-schemes", json=skema_body(items))
        assert r.status_code == 400, f"{items}: {r.status_code} {r.text[:200]}"


def test_skema_proyek_tak_ada_ditolak(komp_aktif):
    r = call(OWNER, "POST", "/allin-schemes", json=skema_body([item(komp_aktif["code"])], project_ids=["bukan-proyek"]))
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


def test_skema_komponen_nonaktif_ditolak_baik_buat_maupun_ubah(komp_aktif):
    mati = buat_komp()
    ok(call(OWNER, "PUT", f"/cost-components/{mati['id']}", json={"is_active": False}))
    r = call(OWNER, "POST", "/allin-schemes", json=skema_body([item(mati["code"])]))
    assert r.status_code == 400 and "NONAKTIF" in str(sebab(r)), f"{r.status_code} {r.text[:200]}"
    s = ok(call(OWNER, "POST", "/allin-schemes", json=skema_body([item(komp_aktif["code"])])))["data"]
    r = call(OWNER, "PUT", f"/allin-schemes/{s['id']}", json={"items": [item(komp_aktif["code"]), item(mati["code"])]})
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
    now = [x for x in ok(call(OWNER, "GET", "/allin-schemes"))["data"] if x["id"] == s["id"]][0]
    assert [i["component_code"] for i in now["items"]] == [komp_aktif["code"]]


def test_skema_sah_diterima_dan_butir_lama_nonaktif_tidak_memblokir_simpan_ulang(komp_aktif):
    c2 = buat_komp()
    s = ok(call(OWNER, "POST", "/allin-schemes", json=skema_body(
        [item(komp_aktif["code"], ov=1_000_000), item(c2["code"], tr="developer_borne")])))["data"]
    assert [i["override_amount"] for i in s["items"]] == [1_000_000, None]
    ok(call(OWNER, "PUT", f"/cost-components/{c2['id']}", json={"is_active": False}))
    # simpan ulang dengan butir lama yang kini nonaktif (UI selalu mengirim seluruh daftar) tetap boleh
    ok(call(OWNER, "PUT", f"/allin-schemes/{s['id']}", json={"note": "diubah", "items": s["items"]}))


def test_skema_kode_unik_dan_org_lain(komp_aktif):
    body = skema_body([item(komp_aktif["code"])])
    ok(call(OWNER, "POST", "/allin-schemes", json=body))
    assert call(OWNER, "POST", "/allin-schemes", json=body).status_code == 409
    # org lain tidak melihat komponen org ini -> 400 (komponen tidak ada di master org itu)
    r = call(NUSA, "POST", "/allin-schemes", json=skema_body([item(komp_aktif["code"])]))
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


def test_pratinjau_harga_negatif_ditolak():
    s = [x for x in ok(call(OWNER, "GET", "/allin-schemes"))["data"] if x["code"] == "EXCLUDE"][0]
    assert call(OWNER, "GET", f"/allin-schemes/{s['id']}/preview", params={"price": -5}).status_code == 400
    assert call(OWNER, "GET", f"/allin-schemes/{s['id']}/preview", params={"price": 0}).status_code == 200


# ------------------------------------------------------------------ nonaktif tidak ditagihkan
def test_komponen_nonaktif_tidak_ikut_snapshot_baru_pratinjau_dan_reservasi():
    c = buat_komp(calc_method="nominal_tetap", amount=0)
    pakai = buat_komp()
    s = ok(call(OWNER, "POST", "/allin-schemes", json=skema_body([item(c["code"]), item(pakai["code"])])))["data"]

    def kodes_pratinjau():
        d = ok(call(OWNER, "GET", f"/allin-schemes/{s['id']}/preview", params={"price": 500_000_000}))["data"]
        return [x["code"] for x in d["components"]]

    assert set(kodes_pratinjau()) == {c["code"], pakai["code"]}
    ok(call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"is_active": False}))
    assert kodes_pratinjau() == [pakai["code"]], "komponen nonaktif tetap ikut pratinjau/snapshot"
    # reservasi baru memakai skema yang sama: snapshot biaya deal juga tanpa komponen nonaktif
    w = World()
    unit = w.units[0]
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"GC nonaktif {TAG}", "source": "manual",
                                                  "phone": "+62812" + str(int(time.time() * 1000))[-9:]}))["data"]
    deal = ok(call(SALES, "POST", "/deals/reserve", json={
        "unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
        "scheme_id": w.scheme["Cash Bertahap (3x)"], "allin_scheme_id": s["id"]}))["data"]
    got = ok(call(OWNER, "GET", f"/deals/{deal['id']}"))["data"]
    kode_deal = [x["code"] for x in (got.get("costs") or {}).get("components") or []]
    assert c["code"] not in kode_deal and pakai["code"] in kode_deal, kode_deal


def test_skema_nonaktif_tidak_bisa_dipakai_reservasi_baru():
    pakai = buat_komp()
    s = ok(call(OWNER, "POST", "/allin-schemes", json=skema_body([item(pakai["code"])])))["data"]
    ok(call(OWNER, "PUT", f"/allin-schemes/{s['id']}", json={"is_active": False}))
    r = call(OWNER, "GET", f"/allin-schemes/{s['id']}/preview", params={"price": 500_000_000})
    assert r.status_code == 400 and "nonaktif" in str(sebab(r)).lower(), f"{r.status_code} {r.text[:200]}"


# ------------------------------------------------------------------ skema pencairan KPR & pajak
def tahap(code, pct, amount=0, cond="akad"):
    return {"code": code, "name": f"Tahap {code}", "pct": pct, "amount": amount, "condition": cond}


@pytest.mark.parametrize("ubah", [
    {"tranches": [tahap("T1", -50), tahap("T2", 150)]},        # total 100% tetapi tiap tahap di luar 0–100
    {"tranches": [tahap("T1", 100, amount=-5_000_000)]},
    {"tolerance_pct": 500},
    {"tolerance_pct": -1},
    {"name": "   "},
])
def test_skema_pencairan_kpr_rentang_angka_ditolak(ubah):
    body = {"code": kode("KPR"), "bank": BANK_UJI, "name": "Skema KPR uji", "tolerance_pct": 1,
            "tranches": [tahap("T1", 100)]}
    body.update(ubah)
    r = call(OWNER, "POST", "/kpr-disbursement-schemes", json=body)
    assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"


def test_skema_pencairan_kpr_sah_dan_update_cacat_ditolak():
    body = {"code": kode("KPR"), "bank": BANK_UJI, "name": "Skema KPR uji", "tolerance_pct": 1,
            "tranches": [tahap("T1", 70), tahap("T2", 30, cond="serah_terima")]}
    s = ok(call(OWNER, "POST", "/kpr-disbursement-schemes", json=body))["data"]
    r = call(OWNER, "PUT", f"/kpr-disbursement-schemes/{s['id']}",
             json={"tranches": [tahap("T1", -20), tahap("T2", 120)]})
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
    now = [x for x in ok(call(OWNER, "GET", "/kpr-disbursement-schemes", params={"include_inactive": True}))["data"]
           if x["id"] == s["id"]][0]
    assert [t["pct"] for t in now["tranches"]] == [70, 30]
    ok(call(OWNER, "PUT", f"/kpr-disbursement-schemes/{s['id']}", json={"is_active": False}))   # bersih-bersih


@pytest.mark.parametrize("ubah", [{"ppn_rate": -5}, {"bphtb_rate": 500}, {"pph_rate": 999}, {"npoptkp": -1}])
def test_konfigurasi_pajak_rentang_ditolak_dan_tidak_tersimpan(ubah):
    awal = ok(call(FINANCE, "GET", "/finance/config/tax"))["data"]
    body = {"ppn_rate": awal["ppn_rate"], "bphtb_rate": awal["bphtb_rate"], "pph_rate": awal["pph_rate"],
            "npoptkp": awal["npoptkp"]}
    body.update(ubah)
    r = call(OWNER, "PUT", "/finance/config/tax", json=body)
    assert r.status_code == 400, f"{ubah}: {r.status_code} {r.text[:200]}"
    assert ok(call(FINANCE, "GET", "/finance/config/tax"))["data"]["bphtb_rate"] == awal["bphtb_rate"]
