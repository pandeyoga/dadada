"""Regresi W2-C — batas wajar NOMINAL komponen biaya sebagai PENGATURAN `cost.component_max_amount` (dulu pagar Rp 1 triliun di kode).

    API_BASE=http://localhost:8083/api DB_NAME=sipro_w2c MONGO_URL=<url> python -m pytest backend/tests/p0/test_w2c_batas_nominal.py \
        -n 0 --noconftest -q -p no:cacheprovider

Bawaan Rp 10.000.000.000 per komponen, tingkat organisasi + proyek, sensitif. Dibaca di SEMUA jalur input komponen: master All-in,
nominal terkunci skema, komponen manual saat reservasi, isian bebas biaya kontrak, beban developer, nilai bawaan katalog.
Nilai yang sudah tersimpan di atas batas tidak diubah, tetapi tidak bisa diedit NAIK.

Tes mengubah pengaturan org/proyek → SELALU dikembalikan di `finally` (suite penuh memakai org yang sama). Tes HTTP merah di kode lama
(pagar 1 triliun, kunci pengaturan belum ada).
"""
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, SUPER, World, call, ok
from test_p0_masuk_2 import convert

KEY = "cost.component_max_amount"
TAG = uuid.uuid4().hex[:5].upper()
_n = [0]
FINLEAD = "finlead@sipro.co.id"
M10 = 10_000_000_000


def kode(prefix="BT"):
    _n[0] += 1
    return f"{prefix}{TAG}{_n[0]}"


def put_limit(value, scope="org", scope_id=None, who=OWNER):
    body = {"value": value, "reason": "uji batas nominal W2-C", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    return call(who, "PUT", f"/settings/{KEY}", json=body)


def reset_limit(scope="org", scope_id=None):
    params = {"scope": scope}
    if scope_id:
        params["scope_id"] = scope_id
    call(OWNER, "POST", f"/settings/{KEY}/reset", params=params)


def komp(amount, **kw):
    body = {"code": kode(), "name": "Komponen uji batas W2-C", "calc_method": "nominal_tetap", "amount": amount,
            "default_treatment": "customer_pass_through", "sync_schemes": False}
    body.update(kw)
    return body


def sebab(r):
    try:
        return str(r.json().get("detail"))
    except Exception:  # noqa: BLE001
        return r.text[:300]


@pytest.fixture(scope="module")
def world():
    return World()


# ------------------------------------------------------------------ bawaan & validasi kunci
def test_bawaan_10_miliar_per_komponen_dan_kunci_sah():
    eff = ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY}))["data"]
    assert eff[KEY] == M10, eff
    spec = next(s for s in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan", "q": KEY}))["data"] if s["key"] == KEY)
    assert spec["type"] == "money" and spec["sensitive"] is True and set(spec["levels"]) == {"org", "project"}
    # sensitif: alasan wajib; rentang sah 1 juta .. 1 triliun
    r = call(OWNER, "PUT", f"/settings/{KEY}", json={"value": 20_000_000_000, "scope": "org"})
    assert r.status_code == 400 and "alasan" in sebab(r).lower(), (r.status_code, sebab(r))
    for bad in (999_999, 1_000_000_000_001):
        r = put_limit(bad)
        assert r.status_code == 400, (bad, r.status_code, sebab(r))


# ------------------------------------------------------------------ master komponen All-in
def test_komponen_di_atas_batas_ditolak_di_batas_diterima():
    r = call(OWNER, "POST", "/cost-components", json=komp(M10 + 1))
    assert r.status_code == 400 and "batas" in sebab(r).lower() and "10.000.000.000" in sebab(r), (r.status_code, sebab(r))
    assert call(OWNER, "POST", "/cost-components", json=komp(M10)).status_code == 200
    # skema: nominal terkunci memakai batas yang sama
    c = ok(call(OWNER, "POST", "/cost-components", json=komp(1_000_000)))["data"]
    sk = {"code": kode("SK"), "name": "Skema uji batas", "items": [{"component_code": c["code"], "treatment": "customer_pass_through",
                                                                   "override_amount": M10 + 1}]}
    r = call(OWNER, "POST", "/allin-schemes", json=sk)
    assert r.status_code == 400 and "batas" in sebab(r).lower(), (r.status_code, sebab(r))
    sk["items"][0]["override_amount"] = M10
    assert call(OWNER, "POST", "/allin-schemes", json=sk).status_code == 200


def test_batas_org_bisa_dinaikkan_dan_diturunkan_dan_dikembalikan():
    try:
        ok(put_limit(20_000_000_000))
        assert call(OWNER, "POST", "/cost-components", json=komp(15_000_000_000)).status_code == 200
        ok(put_limit(5_000_000))
        r = call(OWNER, "POST", "/cost-components", json=komp(6_000_000))
        assert r.status_code == 400 and "5.000.000" in sebab(r), (r.status_code, sebab(r))
        assert call(OWNER, "POST", "/cost-components", json=komp(5_000_000)).status_code == 200
    finally:
        reset_limit()
    assert ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY}))["data"][KEY] == M10


def test_batas_proyek_menimpa_organisasi_untuk_skema_proyek(world):
    pid = world.project_id
    c = ok(call(OWNER, "POST", "/cost-components", json=komp(1_000_000)))["data"]

    def skema(override, project_ids):
        return {"code": kode("SK"), "name": "Skema batas proyek", "project_ids": project_ids,
                "items": [{"component_code": c["code"], "treatment": "customer_pass_through", "override_amount": override}]}
    try:
        ok(put_limit(3_000_000, "project", pid))
        # skema untuk proyek itu memakai batas proyek (3 jt); skema tanpa proyek memakai batas org (10 M)
        r = call(OWNER, "POST", "/allin-schemes", json=skema(5_000_000, [pid]))
        assert r.status_code == 400 and "3.000.000" in sebab(r), (r.status_code, sebab(r))
        assert call(OWNER, "POST", "/allin-schemes", json=skema(2_000_000, [pid])).status_code == 200
        assert call(OWNER, "POST", "/allin-schemes", json=skema(5_000_000, [])).status_code == 200
        # proyek boleh MENAIKKAN batas di atas organisasi
        ok(put_limit(50_000_000_000, "project", pid))
        assert call(OWNER, "POST", "/allin-schemes", json=skema(20_000_000_000, [pid])).status_code == 200
        assert call(OWNER, "POST", "/allin-schemes", json=skema(20_000_000_000, [])).status_code == 400
    finally:
        reset_limit("project", pid)


def test_nilai_tersimpan_di_atas_batas_tidak_diubah_tetapi_tidak_bisa_naik():
    c = ok(call(OWNER, "POST", "/cost-components", json=komp(8_000_000)))["data"]
    try:
        ok(put_limit(5_000_000))
        # tidak diubah diam-diam
        row = next(x for x in ok(call(OWNER, "GET", "/cost-components", params={"include_inactive": True}))["data"] if x["id"] == c["id"])
        assert row["amount"] == 8_000_000
        # formulir yang mengirim ulang nilai yang sama (ganti nama saja) tetap boleh
        assert call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"name": "Nama baru", "amount": 8_000_000}).status_code == 200
        # naik ditolak, turun (walau masih di atas batas) diterima, di bawah batas diterima
        r = call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 9_000_000})
        assert r.status_code == 400 and "dinaikkan" in sebab(r), (r.status_code, sebab(r))
        assert call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 6_000_000}).status_code == 200
        assert call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 4_000_000}).status_code == 200
        assert call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 5_000_000}).status_code == 200
        assert call(OWNER, "PUT", f"/cost-components/{c['id']}", json={"amount": 5_000_001}).status_code == 400
    finally:
        reset_limit()


def test_nominal_terkunci_skema_tersimpan_di_atas_batas_tidak_bisa_naik():
    c = ok(call(OWNER, "POST", "/cost-components", json=komp(1_000_000)))["data"]
    sk = ok(call(OWNER, "POST", "/allin-schemes", json={
        "code": kode("SK"), "name": "Skema nominal tersimpan", "items": [
            {"component_code": c["code"], "treatment": "customer_pass_through", "override_amount": 8_000_000}]}))["data"]
    try:
        ok(put_limit(5_000_000))

        def ubah(nominal):
            return call(OWNER, "PUT", f"/allin-schemes/{sk['id']}", json={
                "items": [{"component_code": c["code"], "treatment": "customer_pass_through", "override_amount": nominal}]})
        assert ubah(8_000_000).status_code == 200      # tidak berubah
        assert ubah(9_000_000).status_code == 400      # naik
        assert ubah(6_000_000).status_code == 200      # turun
    finally:
        reset_limit()


# ------------------------------------------------------------------ katalog
def test_nilai_bawaan_katalog_terkena_batas():
    rows = ok(call(OWNER, "GET", "/catalog/price-components"))["data"]
    row = next(r for r in rows if r["code"] == "UNIT_PRICE")
    r = call(OWNER, "PUT", f"/catalog/price-components/{row['id']}", json={"value": M10 + 1})
    assert r.status_code == 400 and "batas" in sebab(r).lower(), (r.status_code, sebab(r))
    assert call(OWNER, "PUT", f"/catalog/price-components/{row['id']}", json={"value": 0}).status_code == 200


# ------------------------------------------------------------------ jalur kontrak / reservasi / beban developer
def _contract(world):
    d = world.new_deal(booking_fee=0)
    return d, convert(d)


def test_isian_bebas_kontrak_terkena_batas_proyek_sebelum_ditahan(world):
    pid = world.project_id
    d, cid = _contract(world)
    try:
        ok(put_limit(5_000_000, "project", pid))
        r = call(FINANCE, "POST", f"/contracts/{cid}/costs", json={"bphtb": 6_000_000})
        assert r.status_code == 400 and "5.000.000" in sebab(r), (r.status_code, sebab(r))
        # di bawah batas lolos validasi (bawaan: ditahan menunggu persetujuan — lihat tes model biaya kontrak)
        assert call(FINANCE, "POST", f"/contracts/{cid}/costs", json={"bphtb": 4_000_000}).status_code in (200, 202)
    finally:
        reset_limit("project", pid)
        call(OWNER, "DELETE", f"/deals/{d['deal_id']}", params={"reason": "bersihkan data uji W2-C batas"})


def test_komponen_manual_reservasi_terkena_batas_proyek(world):
    pid = world.project_id
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(OWNER, "POST", "/leads", json={"name": f"Uji W2C manual {TAG}", "phone": "+62813" + str(time.time_ns())[-9:],
                                                  "source": "manual"}))["data"]

    def reserve(nominal):
        return call(OWNER, "POST", "/deals/reserve", json={
            "unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
            "scheme_id": world.scheme["Cash Bertahap (3x)"],
            "costs_manual": [{"code": "NOTARIS", "amount": nominal, "treatment": "customer_pass_through"}],
            "costs_manual_reason": "uji batas komponen manual W2-C"})
    try:
        ok(put_limit(3_000_000, "project", pid))
        r = reserve(5_000_000)
        assert r.status_code == 400 and "3.000.000" in sebab(r), (r.status_code, sebab(r))
        r = reserve(2_000_000)
        assert r.status_code == 200, (r.status_code, sebab(r))
        did = r.json()["data"]["id"]
        call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "bersihkan data uji W2-C batas"})
    finally:
        reset_limit("project", pid)


def test_beban_developer_terkena_batas(world):
    sch = next(s for s in ok(call(OWNER, "GET", "/allin-schemes"))["data"] if s["code"] == "ALLIN_STD")
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(OWNER, "POST", "/leads", json={"name": f"Uji W2C beban {TAG}", "phone": "+62814" + str(time.time_ns())[-9:],
                                                  "source": "manual"}))["data"]
    deal = ok(call(OWNER, "POST", "/deals/reserve", json={
        "unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0, "scheme_id": world.scheme["Cash Bertahap (3x)"],
        "allin_scheme_id": sch["id"]}))["data"]
    ok(call(OWNER, "POST", f"/deals/{deal['id']}/book", json={}))
    cid = ok(call(OWNER, "POST", f"/deals/{deal['id']}/convert", json={}))["data"]["contract"]["id"]
    try:
        r = call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={
            "component_code": "BPHTB", "amount": M10 + 1, "vendor": "KPP Uji W2C"})
        assert r.status_code == 400 and "batas" in sebab(r).lower(), (r.status_code, sebab(r))
    finally:
        call(OWNER, "DELETE", f"/deals/{deal['id']}", params={"reason": "bersihkan data uji W2-C batas"})


def test_rekonsiliasi_hijau_setelah_uji_batas():
    end = time.time() + 40
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            break
        time.sleep(1.5)
    assert d["ok"], [c for c in d["checks"] if not c.get("ok")]
