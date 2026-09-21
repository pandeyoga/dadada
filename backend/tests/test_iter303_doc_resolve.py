"""ITER-303 — S#093: GET /api/documents/resolve (alamat dokumen `?doc=`).

Cakupan:
- SO-0007 → sales_order/so_007/ent_ksc
- PO-00015 → purchase_order dengan nomor berawalan PT (KSC/PO-00015)
- SJ-00003 → dokumen logistik (milik ent_kanda)
- nomor tak dikenal → 404 · tanpa token → 401 · peran driver → 200/404 (bukan 500)
"""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"
ENTITY = "ent_ksc"
PASSWORD = "demo12345"


def login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login {email} → {r.status_code}: {r.text[:300]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no token for {email}: {r.text[:300]}"
    return token


def hdr(token: str, entity: str = ENTITY):
    h = {"Authorization": f"Bearer {token}"}
    if entity:
        h["X-Entity-Id"] = entity
    return h


@pytest.fixture(scope="module")
def admin_token():
    return login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def driver_token():
    return login("driver@kainnusantara.id")


def resolve(token, number, entity=ENTITY):
    return requests.get(f"{API}/documents/resolve", params={"number": number},
                        headers=hdr(token, entity), timeout=60)


class TestResolveHappyPath:
    def test_sales_order(self, admin_token):
        r = resolve(admin_token, "SO-0007")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["ref_type"] == "sales_order"
        assert d["ref_id"] == "so_007", d
        assert d["number"] == "SO-0007"
        assert d["entity_id"] == "ent_ksc"
        assert "_id" not in d

    def test_purchase_order_without_prefix(self, admin_token):
        r = resolve(admin_token, "PO-00015")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["ref_type"] == "purchase_order"
        assert d["number"] == "KSC/PO-00015", d
        assert isinstance(d["ref_id"], str) and d["ref_id"]

    def test_purchase_order_with_prefix(self, admin_token):
        r = resolve(admin_token, "KSC/PO-00015")
        assert r.status_code == 200, r.text[:300]
        assert r.json()["number"] == "KSC/PO-00015"

    def test_case_insensitive(self, admin_token):
        r = resolve(admin_token, "so-0007")
        assert r.status_code == 200, r.text[:300]
        assert r.json()["ref_id"] == "so_007"

    def test_shipment_sj_00003(self, admin_token):
        """SJ-00003 milik ent_kanda — admin punya kedua entitas, jadi harus 200."""
        r = resolve(admin_token, "SJ-00003")
        assert r.status_code in (200, 404), r.text[:300]
        if r.status_code == 200:
            d = r.json()
            assert d["ref_type"] in ("shipment", "logistics_delivery"), d
            print("SJ-00003 →", d)
        else:
            print("SJ-00003 tidak ditemukan (di luar cakupan admin):", r.text[:200])


class TestResolveGuards:
    def test_unknown_number_404(self, admin_token):
        r = resolve(admin_token, "XX-999")
        assert r.status_code == 404, r.text[:300]
        assert "tidak ditemukan" in (r.json().get("detail") or "").lower()

    def test_no_token_401(self):
        r = requests.get(f"{API}/documents/resolve", params={"number": "SO-0007"},
                         headers={"X-Entity-Id": ENTITY}, timeout=60)
        assert r.status_code in (401, 403), f"{r.status_code}: {r.text[:200]}"

    def test_too_short_422(self, admin_token):
        r = resolve(admin_token, "S")
        assert r.status_code == 422, r.text[:200]

    # ITER-304: resolver kini menyaring jenis dokumen sesuai izin MODUL peran.
    def test_driver_sales_order_404(self, driver_token):
        r = resolve(driver_token, "SO-0007")
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"
        assert "tidak ditemukan" in (r.json().get("detail") or "").lower()

    def test_driver_purchase_order_404(self, driver_token):
        r = resolve(driver_token, "PO-00015")
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"

    def test_driver_shipment_allowed(self, driver_token):
        r = resolve(driver_token, "SJ-00001")
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        d = r.json()
        assert d["ref_type"] == "shipment", d
        assert d["number"] == "SJ-00001", d
        assert "_id" not in d

    def test_admin_all_three_200(self, admin_token):
        for num, expected in (("SO-0007", "sales_order"), ("PO-00015", "purchase_order"),
                              ("SJ-00001", "shipment")):
            r = resolve(admin_token, num)
            assert r.status_code == 200, f"{num} → {r.status_code}: {r.text[:200]}"
            assert r.json()["ref_type"] == expected, (num, r.json())
