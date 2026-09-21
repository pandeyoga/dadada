"""Iter 26 — REVISI KLIEN 17 Sep: validasi POST /api/customers (PIC toko wajib, alamat toko wajib,
role sales auto-assign, non-sales wajib memilih sales)."""
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://sample-tracker-25.preview.emergentagent.com"
ENTITY = "ent_ksc"

# Mongo (cleanup)
_mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
_db = _mongo[os.environ.get("DB_NAME", "test_database")]


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@kainnusantara.id", "demo12345")


@pytest.fixture(scope="module")
def sales_token():
    return _login("sales@kainnusantara.id", "demo12345")


@pytest.fixture(scope="module")
def sales_me(sales_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=_headers(sales_token), timeout=15)
    assert r.status_code == 200
    return r.json()


_created_ids = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    if _created_ids:
        _db.customers.delete_many({"id": {"$in": _created_ids}})
    # also purge any TEST_ prefix leftovers
    _db.customers.delete_many({"name": {"$regex": "^TEST_", "$options": "i"}})


def _base_payload(name_suffix, **over):
    b = {
        "name": f"TEST_{name_suffix}",
        "pic_name": "Ibu Rina",
        "phone": "081234567890",
        "city": "Kota Bandung",
        "address": "Jl. Merdeka No. 10",
        "entity_id": ENTITY,
        "type": "Retail",
        "segment": "Retail",
        "country": "ID", "country_code": "ID",
        "province": "Jawa Barat", "province_code": "32",
        "city_code": "32.73",
        "district": "Sumur Bandung", "district_code": "32.73.19",
        "postal_code": "40111",
    }
    b.update(over)
    return b


class TestAdminValidations:
    def test_a_admin_missing_assigned_sales(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token),
                          json=_base_payload("adm_no_sales"), timeout=15)
        assert r.status_code == 400, r.text
        assert "Sales penanggung jawab" in r.json().get("detail", "")

    def test_b_admin_missing_pic_name(self, admin_token):
        p = _base_payload("adm_no_pic", assigned_sales_id="user_sales_01", pic_name="")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token), json=p, timeout=15)
        assert r.status_code == 400, r.text
        assert "PIC toko" in r.json().get("detail", "")

    def test_c_admin_missing_phone(self, admin_token):
        p = _base_payload("adm_no_phone", assigned_sales_id="user_sales_01", phone="")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token), json=p, timeout=15)
        assert r.status_code == 400, r.text

    def test_d1_admin_address_dash(self, admin_token):
        p = _base_payload("adm_addr_dash", assigned_sales_id="user_sales_01", address="-")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token), json=p, timeout=15)
        assert r.status_code == 400, r.text
        assert "Alamat toko wajib diisi" in r.json().get("detail", "")

    def test_d2_admin_address_empty(self, admin_token):
        p = _base_payload("adm_addr_empty", assigned_sales_id="user_sales_01", address="")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token), json=p, timeout=15)
        assert r.status_code == 400, r.text
        assert "Alamat toko wajib diisi" in r.json().get("detail", "")

    def test_e_admin_full_ok(self, admin_token):
        p = _base_payload("adm_full", assigned_sales_id="user_sales_01")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(admin_token), json=p, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("assigned_sales_id") == "user_sales_01"
        _created_ids.append(data["id"])
        # verify persistence via list
        g = requests.get(f"{BASE_URL}/api/customers?entity_id={ENTITY}&with_credit=false", headers=_headers(admin_token), timeout=15)
        assert g.status_code == 200, g.text
        rows = g.json() if isinstance(g.json(), list) else g.json().get("items", [])
        assert any(c.get("id") == data["id"] for c in rows), "created customer not found in list"


class TestSalesAutoAssign:
    def test_f_sales_ignores_fake_assigned(self, sales_token, sales_me):
        p = _base_payload("sales_fake", assigned_sales_id="user_sales_99")
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(sales_token), json=p, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("assigned_sales_id") == sales_me["id"], f"expected {sales_me['id']} got {data.get('assigned_sales_id')}"
        assert data.get("assigned_sales_id") != "user_sales_99"
        _created_ids.append(data["id"])

    def test_g_sales_without_assigned_ok(self, sales_token, sales_me):
        p = _base_payload("sales_noassign")
        p.pop("assigned_sales_id", None)
        r = requests.post(f"{BASE_URL}/api/customers", headers=_headers(sales_token), json=p, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("assigned_sales_id") == sales_me["id"]
        _created_ids.append(data["id"])
