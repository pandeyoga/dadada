"""Iteration 288 — FB-02 increment: GPS lat/lng on delivery positions."""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
PWD = "demo12345"
DELIVERY_ID = "lgs_3e0a57edeaf7"


def login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def driver():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('driver@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def sales():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('sales@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"})
    return s


class TestPositionGps:
    def test_delivery_precondition(self, driver):
        r = driver.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["status"] == "in_transit"
        assert "_id" not in d
        gps = [p for p in d.get("positions", []) if p.get("lat") is not None]
        assert len(gps) >= 2, f"expected >=2 GPS positions, got {len(gps)}"

    def test_post_position_with_latlng(self, driver):
        payload = {"location": "TEST_GPS Cikampek", "note": "uji pytest", "lat": -6.4123456, "lng": 107.4567891}
        r = driver.post(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/positions", json=payload)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        last = d.get("last_position") or {}
        assert last.get("location") == payload["location"]
        assert last.get("lat") == pytest.approx(payload["lat"], abs=1e-6)
        assert last.get("lng") == pytest.approx(payload["lng"], abs=1e-6)
        # persistence via GET
        g = driver.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}").json()
        p = g["positions"][-1]
        assert p["location"] == payload["location"]
        assert p["lat"] == pytest.approx(payload["lat"], abs=1e-6)
        assert p["lng"] == pytest.approx(payload["lng"], abs=1e-6)
        assert p.get("by")

    def test_post_position_without_latlng(self, driver):
        r = driver.post(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/positions",
                        json={"location": "TEST_GPS Tanpa Koordinat"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        p = (r.json().get("last_position") or {})
        assert p.get("location") == "TEST_GPS Tanpa Koordinat"
        assert p.get("lat") is None and p.get("lng") is None

    def test_post_position_invalid_lat(self, driver):
        r = driver.post(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/positions",
                        json={"location": "TEST_GPS Invalid", "lat": "utara", "lng": 106.8})
        assert r.status_code == 422, f"expected 422, got {r.status_code} {r.text[:300]}"

    def test_post_position_short_location(self, driver):
        r = driver.post(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/positions", json={"location": "X"})
        assert r.status_code == 422, f"expected 422, got {r.status_code}"


class TestSalesReadOnly:
    def test_sales_can_list(self, sales):
        r = sales.get(f"{BASE_URL}/api/logistics/deliveries", params={"entity_id": "ent_ksc"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert isinstance(r.json(), list)

    def test_sales_can_read_detail(self, sales):
        r = sales.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}")
        assert r.status_code == 200, r.text[:300]
        assert r.json()["number"]

    def test_sales_summary(self, sales):
        r = sales.get(f"{BASE_URL}/api/logistics/summary", params={"entity_id": "ent_ksc"})
        assert r.status_code == 200, r.text[:300]
        assert "total" in r.json()

    def test_sales_cannot_add_position(self, sales):
        r = sales.post(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/positions",
                       json={"location": "TEST_GPS sales tolak", "lat": -6.2, "lng": 106.8})
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:300]}"

    def test_sales_cannot_create_delivery(self, sales):
        r = sales.post(f"{BASE_URL}/api/logistics/deliveries", json={"shipment_ids": ["x"]})
        assert r.status_code in (403, 422), f"got {r.status_code} {r.text[:300]}"
