"""Iterasi 306 — RETEST temuan iter305.

Modul: routers/dashboard.py (enrich hpp/hpp_source + strip_cost_fields),
routers/products.py (redaksi + PATCH harga_pokok diabaikan),
bootstrap.backfill_costing_data (tidak lagi menulis products.harga_pokok).
"""
import os
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
base = os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")
if not base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base.rstrip("/")
ENT = "ent_ksc"
PWD = "demo12345"
TARGET = "prod_batik_mega"
COST_KEYS = {"hpp", "hpp_source", "harga_pokok", "unit_cost", "base_unit_cost",
             "landed_cost_total", "wac", "margin"}


def _login(email: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Entity-Id": ENT})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": f"{email}@kainnusantara.id", "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} gagal: {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("session_token")
    assert tok, f"tidak ada token untuk {email}: {r.text[:200]}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin")


@pytest.fixture(scope="module")
def sales():
    return _login("sales")


def _dashboard(sess):
    r = sess.get(f"{BASE_URL}/api/dashboard", params={"entity_id": ENT}, timeout=120)
    assert r.status_code == 200, f"GET /api/dashboard → {r.status_code} {r.text[:300]}"
    return r.json()


def _find(rows, key, val):
    return next((p for p in rows if p.get(key) == val), None)


# ── (1) dashboard membawa hpp untuk admin ────────────────────────────────
class TestDashboardHpp:
    def test_admin_dashboard_products_have_hpp(self, admin):
        data = _dashboard(admin)
        prods = data.get("products") or []
        assert prods, "dashboard tidak membawa products[]"
        p = _find(prods, "id", TARGET) or _find(prods, "sku", "BTK-MEGA-001")
        assert p, "BTK-MEGA-001 tidak ada di dashboard.products"
        assert "hpp" in p and "hpp_source" in p, f"hpp/hpp_source hilang: {sorted(p.keys())}"
        assert float(p["hpp"]) > 0, f"hpp harus > 0, dapat {p['hpp']}"
        assert p["hpp_source"] in ("roll", "harga_pokok", "po"), p["hpp_source"]
        assert abs(float(p["hpp"]) - 122387.0) < 1.0, f"hpp={p['hpp']} (harap ~122387)"

    def test_dashboard_hpp_matches_products_endpoint(self, admin):
        dash = _find(_dashboard(admin).get("products") or [], "id", TARGET)
        r = admin.get(f"{BASE_URL}/api/products", timeout=90)
        assert r.status_code == 200
        prod = _find(r.json(), "id", TARGET)
        assert prod and dash
        assert abs(float(dash["hpp"]) - float(prod["hpp"])) < 0.01
        assert dash["hpp_source"] == prod["hpp_source"]

    def test_no_mongo_id_leak(self, admin):
        data = _dashboard(admin)
        for p in data.get("products") or []:
            assert "_id" not in p


# ── (2) redaksi biaya untuk peran non admin/manager ──────────────────────
class TestRedaction:
    def test_sales_dashboard_products_have_no_cost_fields(self, sales):
        prods = _dashboard(sales).get("products") or []
        assert prods, "sales tidak menerima products[] di dashboard"
        leaks = {k for p in prods for k in p.keys() if k in COST_KEYS}
        assert not leaks, f"kebocoran biaya di dashboard untuk sales: {sorted(leaks)}"

    def test_sales_products_endpoint_has_no_cost_fields(self, sales):
        r = sales.get(f"{BASE_URL}/api/products", timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        rows = r.json()
        assert rows
        leaks = {k for p in rows for k in p.keys() if k in COST_KEYS}
        assert not leaks, f"kebocoran biaya di /api/products untuk sales: {sorted(leaks)}"


# ── (3) PATCH harga_pokok tetap diabaikan ────────────────────────────────
class TestPatchIgnoresHargaPokok:
    def test_patch_harga_pokok_ignored(self, admin):
        r0 = admin.get(f"{BASE_URL}/api/products", timeout=90)
        before = _find(r0.json(), "id", TARGET)
        assert before
        old = float(before.get("harga_pokok") or 0)
        r = admin.patch(f"{BASE_URL}/api/products/{TARGET}",
                        json={"data": {"harga_pokok": 999}}, timeout=60)
        assert r.status_code in (200, 400, 403, 422), f"{r.status_code} {r.text[:200]}"
        after = _find(admin.get(f"{BASE_URL}/api/products", timeout=90).json(), "id", TARGET)
        assert float(after.get("harga_pokok") or 0) == old, \
            f"harga_pokok berubah {old} → {after.get('harga_pokok')}"
        assert abs(float(after["hpp"]) - float(before["hpp"])) < 0.01
