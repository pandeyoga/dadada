"""Regresi W2-C — SATU master komponen biaya (keputusan #16 / FN-01): katalog `price_components` = SUMBER, kebijakan All-in = ATURAN.

    API_BASE=http://localhost:8083/api DB_NAME=sipro_w2c MONGO_URL=<url> python -m pytest backend/tests/p0/test_w2c_katalog_aturan.py \
        -n 0 --noconftest -q -p no:cacheprovider

Dipakai org KEDUA (`owner@nusaproperti.co.id`; katalognya kosong dan hanya tes ini yang menyentuh master biayanya) supaya mode/migrasi tidak
mengganggu org lain di suite penuh. Semua komponen/skema uji berkode unik per jalan (TAG). Pengaturan mode SELALU dikembalikan di `finally`.

Cakupan: selisih NYATA katalog↔aturan (akun 2-1450 vs 2-1470, cara hitung, nama), migrasi idempoten, bayangan tidak mengubah tagihan,
penyelarasan, `katalog_sumber` hanya sah bila selisih = 0 + ekuivalensi tagihan + tulis tembus + All-in ditolak mengubah, mode per proyek,
validasi blok biaya katalog; bagian "murni" (`cost_master` dipanggil langsung) = pembanding, turunan, rujukan putus.
Merah di kode lama: seluruh bagian HTTP (endpoint /cost-master & kunci cost.master_mode belum ada).
"""
import json
import uuid

import pytest

import aio
from test_p0_masuk import call, ok

NUSA = "owner@nusaproperti.co.id"
TAG = uuid.uuid4().hex[:5].upper()
KEY = "cost.master_mode"
_n = [0]
HARGA = (1, 100_000_000, 850_000_000)
JENIS = ("kpr", "cash_keras")


def kode(prefix="KA"):
    _n[0] += 1
    return f"{prefix}{TAG}{_n[0]}"


def sebab(r):
    try:
        return str(r.json().get("detail"))
    except Exception:  # noqa: BLE001
        return r.text[:300]


def diff(probe=False):
    return ok(call(NUSA, "GET", "/cost-master/diff", params={"probe": str(bool(probe)).lower()}))["data"]


def baris(d, code):
    return next((r for r in d["rows"] if r["code"] == code), None)


def aturan():
    return ok(call(NUSA, "GET", "/cost-components", params={"include_inactive": True}))["data"]


def katalog():
    return ok(call(NUSA, "GET", "/catalog/price-components"))["data"]


def buat_aturan(amount=7_500_000, **kw):
    body = {"code": kode(), "name": "Komponen uji W2-C", "calc_method": "nominal_tetap", "amount": amount, "pct": 0,
            "default_treatment": "customer_pass_through", "sync_schemes": False}
    body.update(kw)
    return ok(call(NUSA, "POST", "/cost-components", json=body))["data"]


def buat_skema(codes, **kw):
    body = {"code": kode("SK"), "name": "Skema uji W2-C",
            "items": [{"component_code": c, "treatment": "customer_pass_through", "override_amount": None} for c in codes]}
    body.update(kw)
    return ok(call(NUSA, "POST", "/allin-schemes", json=body))["data"]


def rapikan():
    """Kondisi nol selisih: migrasi + selaraskan (alasan wajib) lalu verifikasi."""
    ok(call(NUSA, "POST", "/cost-master/migrate"))
    ok(call(NUSA, "POST", "/cost-master/sync", json={"reason": "rapikan master untuk uji W2-C"}))
    d = diff()
    assert d["summary"]["nol"], [r for r in d["rows"] if r["blocking"]]
    return d


def set_mode(value, scope="org", scope_id=None):
    body = {"value": value, "reason": "uji sumber master W2-C", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    return call(NUSA, "PUT", f"/settings/{KEY}", json=body)


def reset_mode(scope="org", scope_id=None):
    params = {"scope": scope}
    if scope_id:
        params["scope_id"] = scope_id
    call(NUSA, "POST", f"/settings/{KEY}/reset", params=params)


def pratinjau(project_id=None):
    """{(kode skema, harga, jenis): komponen} untuk SEMUA skema aktif — dasar perbandingan 'tagihan sebelum/sesudah'."""
    out = {}
    for s in ok(call(NUSA, "GET", "/allin-schemes"))["data"]:
        for harga in HARGA:
            for jenis in JENIS:
                params = {"price": harga, "scheme": jenis, "booking_fee": 5_000_000}
                if project_id:
                    params["project_id"] = project_id
                snap = ok(call(NUSA, "GET", f"/allin-schemes/{s['id']}/preview", params=params))["data"]
                out[(s["code"], harga, jenis)] = snap
    return out


def inti(snap):
    """Tanpa penanda mode (`master_mode`, `catalog_code`): sisanya = angka/akun yang membentuk tagihan & jurnal."""
    s = {k: v for k, v in snap.items() if k != "master_mode"}
    s["components"] = [{k: v for k, v in c.items() if k != "catalog_code"} for c in s["components"]]
    return s


def semua_inti(pv):
    return {k: inti(v) for k, v in pv.items()}


@pytest.fixture(autouse=True)
def mode_bersih():
    reset_mode()
    yield
    reset_mode()


# ------------------------------------------------------------------ (a)+(c) selisih nyata & laporan
def test_selisih_nyata_sebelum_migrasi_dan_peta_field():
    code = kode()
    buat_aturan(7_500_000, code=code)
    ok(call(NUSA, "POST", "/catalog/price-components", json={
        "code": code, "label": "Komponen uji W2-C", "group": "biaya", "finance_treatment": "pass_through",
        "gl_account": "2-1450", "calc": "manual", "value": 0, "applies_schemes": []}))
    d = diff()
    r = baris(d, code)
    assert r["status"] == "belum_dimigrasi" and r["blocking"], r
    f = {x["field"]: x for x in r["diffs"]}
    assert f["gl_account"]["katalog"] == "2-1450" and f["gl_account"]["aturan"] == "2-1470", f   # akun katalog salah dibanding jurnal sebenarnya
    assert "calc" in f and "7.500.000" in str(f["calc"]["aturan"]), f
    assert d["summary"]["nol"] is False and d["summary"]["baris_selisih"] >= 1
    # peta field: kedua sisi + pembawa otoritatif
    peta = {x["katalog"] for x in d["field_map"]}
    assert any("gl_account" in k for k in peta) and any("cost.calc_method" in k for k in peta), peta
    assert {x["pembawa"] for x in d["field_map"]} == {"katalog", "aturan"}
    # opsi katalog_sumber TIDAK tersedia selama ada selisih: ditolak server + ditandai di daftar pengaturan dengan alasan jujur
    rr = set_mode("katalog_sumber")
    assert rr.status_code == 400 and "belum tersedia" in sebab(rr) and "berselisih" in sebab(rr), (rr.status_code, sebab(rr))
    spec = next(s for s in ok(call(NUSA, "GET", "/settings", params={"group": "kebijakan", "q": KEY}))["data"] if s["key"] == KEY)
    assert "katalog_sumber" in spec["unavailable"] and "berselisih" in spec["unavailable"]["katalog_sumber"], spec["unavailable"]
    assert d["katalog_sumber"]["tersedia"] is False and d["mode"]["value"] == "bayangan"


# ------------------------------------------------------------------ (b) migrasi idempoten, tagihan tidak berubah
def test_migrasi_idempoten_dan_tagihan_tidak_berubah():
    c = buat_aturan(7_500_000)
    buat_skema([c["code"]])
    sebelum = pratinjau()
    m1 = ok(call(NUSA, "POST", "/cost-master/migrate"))["data"]
    assert m1["katalog_dibuat"] >= 1 and m1["sudah_selaras"] is False, m1
    sesudah = pratinjau()
    assert sesudah == sebelum, "migrasi tidak boleh mengubah satu pun angka/akun tagihan"
    rujukan = {x["code"]: x.get("catalog_code") for x in aturan()}
    assert rujukan[c["code"]] == c["code"] and all(rujukan.values()), rujukan     # All-in MEREFERENSI kode katalog
    k = next(x for x in katalog() if x["code"] == c["code"])
    assert k["cost"]["amount"] == 7_500_000 and k["cost"]["gl_liability"] == "2-1470", k
    m2 = ok(call(NUSA, "POST", "/cost-master/migrate"))["data"]
    assert m2 == {"katalog_dibuat": 0, "blok_biaya_diisi": 0, "rujukan_dipasang": 0, "aturan_didaftarkan": 0, "sudah_selaras": True}, m2
    assert pratinjau() == sebelum


def test_migrasi_tidak_menimpa_nilai_katalog_yang_berbeda_selisih_tetap_dilaporkan():
    code = kode()
    buat_aturan(7_500_000, code=code)
    ok(call(NUSA, "POST", "/catalog/price-components", json={
        "code": code, "label": "Nama lain di katalog", "group": "biaya", "finance_treatment": "pass_through",
        "gl_account": "2-1450", "calc": "manual", "value": 0, "applies_schemes": []}))
    ok(call(NUSA, "POST", "/cost-master/migrate"))
    k = next(x for x in katalog() if x["code"] == code)
    assert k["label"] == "Nama lain di katalog" and k["gl_account"] == "2-1450", "migrasi tidak merusak: kolom lama tidak ditimpa"
    r = baris(diff(), code)
    assert r["status"] == "beda"
    assert {x["field"] for x in r["diffs"]} >= {"name", "gl_account"}, r["diffs"]


# ------------------------------------------------------------------ penyelarasan → nol selisih; bayangan tidak mengubah tagihan
def test_selaraskan_nol_selisih_wajib_alasan_dan_tagihan_tetap():
    c = buat_aturan(6_000_000)
    buat_skema([c["code"]])
    sebelum = pratinjau()
    r = call(NUSA, "POST", "/cost-master/sync", json={"reason": "pendek"})
    assert r.status_code == 400 and "alasan" in sebab(r).lower(), (r.status_code, sebab(r))
    res = ok(call(NUSA, "POST", "/cost-master/sync", json={"reason": "samakan katalog dengan aturan berjalan"}))["data"]
    assert res["diselaraskan"] >= 0 and "migrasi" in res
    d = diff(probe=True)
    assert d["summary"]["nol"] is True and d["katalog_sumber"]["tersedia"] is True, [r for r in d["rows"] if r["blocking"]]
    assert d["probe"]["identik"] is True and d["probe"]["beda"] == 0 and d["probe"]["diperiksa"] >= 6
    assert pratinjau() == sebelum, "menyelaraskan KATALOG tidak boleh mengubah tagihan (All-in tetap sumber)"
    again = ok(call(NUSA, "POST", "/cost-master/sync", json={"reason": "ulangi penyelarasan yang sama"}))["data"]
    assert again["diselaraskan"] == 0, again


def test_bayangan_katalog_diubah_dilaporkan_tapi_tagihan_tetap_dari_allin():
    c = buat_aturan(7_500_000)
    buat_skema([c["code"]])
    rapikan()
    sebelum = pratinjau()
    k = next(x for x in katalog() if x["code"] == c["code"])
    ok(call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": {"amount": 9_000_000}}))
    assert pratinjau() == sebelum, "mode bayangan: tagihan TETAP dari All-in walau katalog diubah"
    d = diff()
    r = baris(d, c["code"])
    assert r["status"] == "beda" and any(x["field"] == "amount" and x["katalog"] == 9_000_000 and x["aturan"] == 7_500_000
                                         for x in r["diffs"]), r
    assert set_mode("katalog_sumber").status_code == 400            # selisih ≠ 0 → opsi belum sah
    ok(call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": {"amount": 7_500_000}}))
    assert diff()["summary"]["nol"] is True


# ------------------------------------------------------------------ (d) katalog_sumber: ekuivalen, tulis tembus, All-in ditolak
def test_katalog_sumber_ekuivalen_tulis_tembus_dan_allin_ditolak_mengubah():
    c = buat_aturan(7_500_000)
    sk = buat_skema([c["code"]])
    rapikan()
    bayangan = pratinjau()
    try:
        assert set_mode("katalog_sumber").status_code == 200
        kat = pratinjau()
        assert semua_inti(kat) == semua_inti(bayangan), "tes ekuivalensi: tagihan identik di kedua sumber"
        assert all(v.get("master_mode") == "katalog_sumber" for v in kat.values()), "snapshot menandai sumbernya"
        assert all("master_mode" not in v for v in bayangan.values()), "bayangan = bentuk lama persis (tanpa penanda)"
        # tulis tembus: ubah di KATALOG → master All-in ikut, tagihan baru memakai nilai baru
        k = next(x for x in katalog() if x["code"] == c["code"])
        ok(call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": {"amount": 9_000_000}}))
        assert next(x for x in aturan() if x["code"] == c["code"])["amount"] == 9_000_000
        snap = ok(call(NUSA, "GET", f"/allin-schemes/{sk['id']}/preview", params={"price": 850_000_000, "scheme": "kpr"}))["data"]
        assert [x["amount"] for x in snap["components"] if x["code"] == c["code"]] == [9_000_000]
        assert diff()["summary"]["nol"] is True, "tulis tembus menjaga selisih tetap 0"
        # definisi dimiliki katalog: mengubah di tab Biaya All-in ditolak; mengirim ulang nilai yang sama tidak dianggap perubahan
        rr = call(NUSA, "PUT", f"/cost-components/{c['id']}", json={"amount": 1_000_000})
        assert rr.status_code == 400 and "KATALOG" in sebab(rr), (rr.status_code, sebab(rr))
        assert call(NUSA, "PUT", f"/cost-components/{c['id']}", json={"name": c["name"], "amount": 9_000_000}).status_code == 200
        # komponen All-in BARU otomatis terdaftar di katalog (tetap satu master, selisih 0)
        baru = buat_aturan(2_000_000)
        assert any(x["code"] == baru["code"] and x.get("cost") for x in katalog())
        assert diff()["summary"]["nol"] is True
        # kembali ke bayangan aman: All-in sudah sama dengan katalog → tagihan tidak melonjak/berubah
        reset_mode()
        snap = ok(call(NUSA, "GET", f"/allin-schemes/{sk['id']}/preview", params={"price": 850_000_000, "scheme": "kpr"}))["data"]
        assert [x["amount"] for x in snap["components"] if x["code"] == c["code"]] == [9_000_000]
        assert "master_mode" not in snap and diff()["summary"]["nol"] is True
    finally:
        reset_mode()


def test_arah_penyelarasan_dijaga_menurut_mode():
    c = buat_aturan(7_500_000)
    buat_skema([c["code"]])
    rapikan()
    # bayangan: All-in = sumber → arah sebaliknya ditolak
    r = call(NUSA, "POST", "/cost-master/sync", json={"reason": "salin katalog ke aturan", "direction": "aturan_ikut_katalog"})
    assert r.status_code == 400 and "bayangan" in sebab(r), (r.status_code, sebab(r))
    assert call(NUSA, "POST", "/cost-master/sync", json={"reason": "arah tidak dikenal", "direction": "ngawur"}).status_code == 400
    try:
        assert set_mode("katalog_sumber").status_code == 200
        # katalog = sumber: menimpa katalog dengan aturan (bukan sumber) ditolak; arah katalog → aturan boleh dan beralasan
        r = call(NUSA, "POST", "/cost-master/sync", json={"reason": "samakan katalog dengan aturan lagi"})
        assert r.status_code == 400 and "sumber" in sebab(r), (r.status_code, sebab(r))
        r = call(NUSA, "POST", "/cost-master/sync", json={"reason": "pendek", "direction": "aturan_ikut_katalog"})
        assert r.status_code == 400 and "alasan" in sebab(r).lower()
        r = ok(call(NUSA, "POST", "/cost-master/sync", json={"reason": "perbaiki simpangan aturan dari katalog", "direction": "aturan_ikut_katalog"}))
        assert r["data"]["diselaraskan"] == 0, r
    finally:
        reset_mode()


def test_edit_nama_atau_aktif_baris_biaya_tidak_memvalidasi_ulang_blok_biaya():
    c = buat_aturan(1_000_000)
    rapikan()
    k = next(x for x in katalog() if x["code"] == c["code"])
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"label": "Nama katalog baru", "note": "catatan"})
    assert r.status_code == 200, (r.status_code, sebab(r))
    k2 = next(x for x in katalog() if x["code"] == c["code"])
    assert k2["cost"] == k["cost"] and k2["label"] == "Nama katalog baru" and k2["gl_account"] == k["gl_account"]
    f = {x["field"] for x in baris(diff(), c["code"])["diffs"]}
    assert f == {"name"}, f      # hanya nama yang berbeda → dilaporkan sebagai selisih (bayangan)
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"finance_treatment": "revenue"})
    assert r.status_code == 400 and "pass_through" in sebab(r), (r.status_code, sebab(r))


def test_katalog_sumber_per_proyek_tidak_menyentuh_proyek_lain():
    c = buat_aturan(7_500_000)
    sk = buat_skema([c["code"]])
    rapikan()
    pid = ok(call(NUSA, "POST", "/projects", json={"name": f"Proyek W2C {TAG}", "location": "uji"}))["data"]["id"]
    try:
        assert set_mode("katalog_sumber", "project", pid).status_code == 200
        dgn = ok(call(NUSA, "GET", f"/allin-schemes/{sk['id']}/preview", params={"price": 850_000_000, "project_id": pid}))["data"]
        tanpa = ok(call(NUSA, "GET", f"/allin-schemes/{sk['id']}/preview", params={"price": 850_000_000}))["data"]
        assert dgn.get("master_mode") == "katalog_sumber" and "master_mode" not in tanpa, (dgn.get("master_mode"), tanpa.get("master_mode"))
        assert inti(dgn) == inti(tanpa)
    finally:
        reset_mode("project", pid)


def test_hanya_katalog_biaya_didaftarkan_ke_aturan_oleh_migrasi_tanpa_menyentuh_skema():
    code = kode()
    ok(call(NUSA, "POST", "/catalog/price-components", json={
        "code": code, "label": "Komponen katalog saja", "group": "biaya", "finance_treatment": "pass_through",
        "cost": {"calc_method": "nominal_tetap", "amount": 1_500_000, "default_treatment": "customer_pass_through"}}))
    r = baris(diff(), code)
    assert r["status"] == "hanya_katalog_biaya" and r["blocking"] is False, r
    skema_sebelum = ok(call(NUSA, "GET", "/allin-schemes", params={"include_inactive": True}))["data"]
    m = ok(call(NUSA, "POST", "/cost-master/migrate"))["data"]
    assert m["aturan_didaftarkan"] >= 1, m
    row = next(x for x in aturan() if x["code"] == code)
    assert row["amount"] == 1_500_000 and row["catalog_code"] == code
    assert ok(call(NUSA, "GET", "/allin-schemes", params={"include_inactive": True}))["data"] == skema_sebelum, "skema tidak disentuh"


# ------------------------------------------------------------------ validasi blok biaya katalog (FN-02 versi katalog)
@pytest.mark.parametrize("cost,potongan", [
    ({"calc_method": "xyz"}, "tidak dikenal"),
    ({"pct": 500}, "di antara"),
    ({"gl_expense": "9-9999"}, "tidak ada"),
    ({"gl_liability": "1-1100"}, "bertipe"),
    ({"amount": 10_000_000_001}, "batas"),
    ({"bukan_field": 1}, "tidak dikenal"),
])
def test_blok_biaya_katalog_divalidasi_seperti_master_allin(cost, potongan):
    c = buat_aturan(1_000_000)
    rapikan()
    k = next(x for x in katalog() if x["code"] == c["code"])
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": cost})
    assert r.status_code == 400 and potongan in sebab(r), (cost, r.status_code, sebab(r))
    assert next(x for x in katalog() if x["code"] == c["code"])["cost"] == k["cost"], "ditolak = tidak tersimpan"


def test_kolom_turunan_tidak_bisa_bertentangan_dengan_blok_biaya():
    c = buat_aturan(1_000_000)
    rapikan()
    k = next(x for x in katalog() if x["code"] == c["code"])
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"gl_account": "2-1450"})
    assert r.status_code == 400 and "diturunkan" in sebab(r), (r.status_code, sebab(r))
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": {"default_treatment": "developer_borne"}, "finance_treatment": "pass_through"})
    assert r.status_code == 200
    k2 = next(x for x in katalog() if x["code"] == c["code"])
    assert k2["gl_account"] == "6-1700", "ditalangi developer → akun turunan = akun beban"
    r = call(NUSA, "PUT", f"/catalog/price-components/{k['id']}", json={"cost": {"default_treatment": "customer_pass_through"}})
    assert r.status_code == 200 and next(x for x in katalog() if x["code"] == c["code"])["gl_account"] == "2-1470"


# ------------------------------------------------------------------ izin & laporan
def test_migrasi_dan_penyelarasan_butuh_izin_keuangan_laporan_untuk_pemegang_katalog():
    r = call("sales@sipro.co.id", "POST", "/cost-master/migrate")
    assert r.status_code == 403, r.status_code
    r = call("sales@sipro.co.id", "POST", "/cost-master/sync", json={"reason": "tidak berwenang untuk ini"})
    assert r.status_code == 403, r.status_code
    d = ok(call(NUSA, "GET", "/cost-master/diff", params={"usage": "true"}))["data"]
    assert "snapshot_kode" in d and isinstance(d["snapshot_kode"], list)


# ------------------------------------------------------------------ bagian murni (memanggil kode backend langsung)
def test_murni_turunan_dan_pembanding():
    import cost_master as cm
    cost = {"calc_method": "nominal_tetap", "pct": 0, "amount": 7_500_000, "default_treatment": "customer_pass_through",
            "gl_expense": "6-1700", "gl_liability": "2-1470", "gl_ap": "2-1100", "kpr_only": True}
    assert cm.derive_legacy(cost) == {"gl_account": "2-1470", "applies_schemes": ["kpr"], "value": 7_500_000}
    assert cm.derive_legacy({**cost, "default_treatment": "developer_borne", "kpr_only": False, "calc_method": "persen_harga"}) == \
        {"gl_account": "6-1700", "applies_schemes": [], "value": 0}
    # "semua skema" ditulis eksplisit ≡ kosong; ["kpr"] ≡ hanya KPR
    assert cm.kpr_only_of(["cash_keras", "cash_bertahap", "kpr"]) is False and cm.kpr_only_of([]) is False
    assert cm.kpr_only_of(["kpr"]) is True
    a = {"code": "X1", "name": "Uji", "is_active": True, **cost}
    k = {"code": "X1", "label": "Uji", "active": True, "cost": dict(cost), "gl_account": "2-1470", "value": 7_500_000,
         "applies_schemes": ["kpr"], "finance_treatment": "pass_through"}
    assert cm.compare(a, k) == []
    # blok biaya katalog menyimpang → selisih nominal DAN kolom lama 'value' (turunan blok itu) yang kini tak konsisten
    assert [d["field"] for d in cm.compare(a, {**k, "cost": {**cost, "amount": 1}})] == ["amount", "value"]
    assert [d["field"] for d in cm.compare(a, {**k, "gl_account": "2-1450"})] == ["gl_account"]
    assert [d["field"] for d in cm.compare(a, {**k, "label": "Lain", "active": False})] == ["name", "is_active"]


def test_murni_baris_laporan_rujukan_putus_dan_alasan():
    import cost_master as cm
    rules = [{"code": "A1", "name": "A", "is_active": True, "calc_method": "nominal_tetap", "amount": 1, "pct": 0,
              "default_treatment": "customer_pass_through", "gl_expense": "6-1700", "gl_liability": "2-1470", "gl_ap": "2-1100"}]
    cat = [{"code": "UNIT_PRICE", "label": "Harga", "active": True}]
    schemes = [{"code": "S1", "items": [{"component_code": "A1"}, {"component_code": "HILANG"}]}]
    rows = {(r["code"], r["status"]): r for r in cm._rows(rules, cat, schemes)}
    assert rows[("A1", "hanya_aturan")]["blocking"] is True
    assert rows[("UNIT_PRICE", "hanya_katalog")]["blocking"] is False
    assert rows[("HILANG", "rujukan_putus")]["blocking"] is True
    assert "berselisih" in cm.reason_of({"summary": {"nol": False, "baris_selisih": 2}, "rows": [{"blocking": True, "code": "A1"}]})
    assert cm.reason_of({"summary": {"nol": True}, "probe": {"lengkap": True, "identik": True}}, True) is None
    assert "ekuivalensi" in cm.reason_of({"summary": {"nol": True}, "probe": {"lengkap": True, "identik": False, "beda": 1,
                                                                             "diperiksa": 3, "contoh": [{"skema": "S1"}]}}, True)
    assert "tidak bisa dibuktikan" in cm.reason_of({"summary": {"nol": True}, "probe": {"lengkap": False, "skema_aktif": 999}}, True)
    assert aio.run(cm.mode_for("org-nusa")) in ("bayangan", "katalog_sumber")


def test_rekonsiliasi_hijau_setelah_uji_master():
    import time
    end = time.time() + 40
    while True:
        d = ok(call("finance@sipro.co.id", "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            break
        time.sleep(1.5)
    assert d["ok"], [c for c in d["checks"] if not c.get("ok")]
