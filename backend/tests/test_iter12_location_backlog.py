"""Iter12 — Backlog alamat & lokasi tervalidasi untuk gudang/site/karyawan.

Pola: pakai pelanggan uji sendiri untuk skenario 'Lengkapi' agar data seed tak berubah.
Jalankan: pytest -n0 backend/tests/test_iter12_location_backlog.py
"""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
API = BASE + "/api"
TAG = uuid.uuid4().hex[:6].upper()
DB = MongoClient("mongodb://localhost:27017")["test_database"]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    r.raise_for_status()
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def cleanup():
    ids = {"warehouses": [], "warehouse_sites": [], "hr_employees": [], "customers": []}
    yield ids
    for coll, id_list in ids.items():
        for _id in id_list:
            DB[coll].delete_one({"id": _id})


# ── Backend gudang ────────────────────────────────────────────────────────────
def test_warehouse_reject_postal_mismatch(admin):
    r = admin.post(f"{API}/warehouses", json={"code": f"TEST-WH-A-{TAG}", "name": f"TEST_WH A {TAG}", "city": "Kota Bandung", "postal_code": "60111"})
    assert r.status_code == 400, r.text


def test_warehouse_create_verified(admin, cleanup):
    r = admin.post(f"{API}/warehouses", json={"code": f"TEST-WH-B-{TAG}", "name": f"TEST_WH B {TAG}", "city_code": "32.73", "district_code": "32.73.09", "postal_code": "40115"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["location_status"] == "verified"
    assert d["city"] == "Kota Bandung"
    assert d["province"] == "Jawa Barat"
    cleanup["warehouses"].append(d["id"])


def test_warehouse_patch_reject_and_accept(admin, cleanup):
    r = admin.post(f"{API}/warehouses", json={"code": f"TEST-WH-C-{TAG}", "name": f"TEST_WH C {TAG}", "city_code": "32.73", "district_code": "32.73.09", "postal_code": "40115"})
    assert r.status_code == 200
    wid = r.json()["id"]
    cleanup["warehouses"].append(wid)
    bad = admin.patch(f"{API}/warehouses/{wid}", json={"data": {"postal_code": "10110"}})
    assert bad.status_code == 400
    good = admin.patch(f"{API}/warehouses/{wid}", json={"data": {"district_code": "32.73.01", "postal_code": "40151"}})
    assert good.status_code == 200, good.text
    assert good.json().get("district") == "Sukasari"


# ── Backend site ──────────────────────────────────────────────────────────────
def test_warehouse_site(admin, cleanup):
    r = admin.post(f"{API}/warehouse-sites", json={"name": f"TEST_SITE {TAG}", "city_code": "33.72", "postal_code": "57111"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["location_status"] == "verified"
    assert d["province"] == "Jawa Tengah"
    cleanup["warehouse_sites"].append(d["id"])
    bad = admin.patch(f"{API}/warehouse-sites/{d['id']}", json={"postal_code": "40115"})
    assert bad.status_code == 400


# ── Backend karyawan ──────────────────────────────────────────────────────────
def test_hr_employee_location(admin, cleanup):
    r = admin.post(f"{API}/hr/employees", json={"name": f"TEST_EMP {TAG}", "nik": f"NIK{TAG}", "phone": "081200009999", "address": "Jl. K", "city_code": "32.73", "postal_code": "40115", "entity_id": "ent_ksc"})
    assert r.status_code == 200, r.text
    emp = r.json()
    assert emp["location_status"] == "verified"
    cleanup["hr_employees"].append(emp["id"])
    bad = admin.patch(f"{API}/hr/employees/{emp['id']}", json={"data": {"postal_code": "10110"}})
    assert bad.status_code == 400
    good = admin.patch(f"{API}/hr/employees/{emp['id']}", json={"data": {"postal_code": "40111"}})
    assert good.status_code == 200, good.text
    assert good.json().get("city") == "Kota Bandung"


# ── Backend backlog alamat ────────────────────────────────────────────────────
def test_backlog_list_shape(admin):
    r = admin.get(f"{API}/data-hygiene/unverified-locations")
    assert r.status_code == 200
    j = r.json()
    for key in ("items", "counts", "total", "labels"):
        assert key in j
    for coll in ("customers", "suppliers", "makloons", "warehouses", "warehouse_sites", "business_entities", "hr_employees"):
        assert coll in j["counts"]


def test_backlog_filter_by_collection(admin, cleanup):
    # buat pelanggan uji dengan city saja → partial/unverified
    r = admin.post(f"{API}/customers", json={
        "name": f"TEST_BACKLOG {TAG}", "pic_name": "T", "phone": "081200001234", "address": "Jl. Uji",
        "type": "Retail", "assigned_sales_id": "user_sales_01", "entity_id": "ent_ksc",
        "city": "Bandung",
    })
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    cleanup["customers"].append(cid)
    # muncul di backlog?
    lst = admin.get(f"{API}/data-hygiene/unverified-locations", params={"collection": "customers"}).json()
    assert all(x["collection"] == "customers" for x in lst["items"])
    assert any(x["doc_id"] == cid for x in lst["items"]), "pelanggan uji ada di backlog"


def test_backlog_fix_customer(admin, cleanup):
    r = admin.post(f"{API}/customers", json={
        "name": f"TEST_FIX {TAG}", "pic_name": "T", "phone": "081200001235", "address": "Jl. Uji",
        "type": "Retail", "assigned_sales_id": "user_sales_01", "entity_id": "ent_ksc",
        "city": "Bandung",
    })
    assert r.status_code == 200
    cid = r.json()["id"]
    cleanup["customers"].append(cid)

    # tanpa kode pos → 400
    bad = admin.post(f"{API}/data-hygiene/location/customers/{cid}", json={"province_code": "32", "city_code": "32.73"})
    assert bad.status_code == 400
    assert "kode pos" in bad.text.lower()

    # kirim lokasi valid Jakarta Pusat
    fx = admin.post(f"{API}/data-hygiene/location/customers/{cid}", json={"province_code": "31", "city_code": "31.71", "postal_code": "10110"})
    assert fx.status_code == 200, fx.text
    dj = fx.json()
    assert dj["location_status"] == "verified"
    assert "Jakarta Pusat" in dj["city"]

    # backlog tidak lagi memuat record ini
    lst = admin.get(f"{API}/data-hygiene/unverified-locations", params={"collection": "customers"}).json()
    assert all(x["doc_id"] != cid for x in lst["items"]), "record hilang dari backlog"

    # doc di Mongo — alamat utama harus ikut membawa postal_code
    cust = DB.customers.find_one({"id": cid}, {"_id": 0})
    assert cust["postal_code"] == "10110"
    primary = next((a for a in cust.get("addresses", []) if a.get("is_primary")), None)
    assert primary is not None, "harus ada primary address"
    assert primary.get("postal_code") == "10110", f"primary address ikut membawa postal_code, dapat: {primary}"

    # ada catatan location_fix di log
    log = admin.get(f"{API}/data-hygiene/log", params={"collection": "customers", "limit": 20}).json()
    assert any(l["trigger"] == "location_fix" and l["doc_id"] == cid for l in log["items"]), "log location_fix ada"


def test_backlog_unknown_collection(admin):
    r = admin.post(f"{API}/data-hygiene/location/nomor_lucu/xxx", json={"postal_code": "40115"})
    assert r.status_code == 404
