"""Iterasi 305 (S#096) — HPP tidak boleh diinput manual.

Modul: routers/products.py (list enrich hpp/hpp_source; PATCH tanpa harga_pokok;
POST memaksa harga_pokok=0) + services/costing_service.wac_for_product.
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


def _products(sess):
    r = sess.get(f"{BASE_URL}/api/products", timeout=90)
    assert r.status_code == 200, f"GET /api/products → {r.status_code} {r.text[:300]}"
    return r.json()


def _find(products, key, val):
    for p in products:
        if p.get(key) == val:
            return p
    return None


# ── (1) enrich hpp + hpp_source ──────────────────────────────────────────
class TestHppEnrich:
    def test_every_product_has_hpp_and_source(self, admin):
        products = _products(admin)
        assert isinstance(products, list) and len(products) > 0
        allowed = {"roll", "roll_partial", "harga_pokok", "price", "none"}
        bad = []
        for p in products:
            if "hpp" not in p or "hpp_source" not in p:
                bad.append((p.get("sku"), "field hilang"))
            elif not isinstance(p["hpp"], (int, float)):
                bad.append((p.get("sku"), f"hpp bukan angka: {p['hpp']!r}"))
            elif p["hpp_source"] not in allowed:
                bad.append((p.get("sku"), f"source tak dikenal: {p['hpp_source']!r}"))
        assert not bad, f"produk bermasalah: {bad[:10]}"

    def test_btk_mega_hpp_from_roll(self, admin):
        p = _find(_products(admin), "sku", "BTK-MEGA-001")
        assert p, "BTK-MEGA-001 tidak ditemukan"
        assert p["hpp_source"] == "roll", f"hpp_source={p['hpp_source']}"
        assert abs(float(p["hpp"]) - 122387) < 50, f"hpp={p['hpp']} (harap ≈122387)"

    def test_no_mongo_id_leak(self, admin):
        assert all("_id" not in p for p in _products(admin))


# ── (2) PATCH harga_pokok diabaikan ──────────────────────────────────────
class TestPatchIgnoresHargaPokok:
    def test_patch_harga_pokok_ignored(self, admin):
        before = _find(_products(admin), "id", TARGET)
        assert before, f"{TARGET} tidak ditemukan"
        hp_before = float(before.get("harga_pokok") or 0)
        hpp_before = float(before.get("hpp") or 0)

        r = admin.patch(f"{BASE_URL}/api/products/{TARGET}",
                        json={"data": {"harga_pokok": 999}}, timeout=60)
        assert r.status_code == 200, f"PATCH → {r.status_code} {r.text[:300]}"
        assert float(r.json().get("harga_pokok") or 0) == hp_before, \
            f"respons PATCH mengubah harga_pokok → {r.json().get('harga_pokok')}"

        after = _find(_products(admin), "id", TARGET)
        assert float(after.get("harga_pokok") or 0) == hp_before, \
            f"harga_pokok berubah: {hp_before} → {after.get('harga_pokok')}"
        assert after["hpp_source"] == "roll"
        assert abs(float(after["hpp"]) - hpp_before) < 1


# ── (3) POST memaksa harga_pokok = 0 ─────────────────────────────────────
class TestCreateForcesZero:
    def test_create_forces_harga_pokok_zero(self, admin):
        import time as _t
        sku = f"TEST_HPP_305_{int(_t.time())}"
        payload = {"sku": sku, "name": "TEST_ HPP Guard 305", "category": "Kain",
                   "price": 100000, "harga_pokok": 555, "base_unit": "meter",
                   "stage": "finished", "fabric_type": "woven", "grade": "A",
                   "gramasi": 120, "lebar": 115}
        r = admin.post(f"{BASE_URL}/api/products", json=payload, timeout=60)
        if r.status_code == 409:
            existing = _find(_products(admin), "sku", sku)
            pid = existing["id"]
        else:
            assert r.status_code in (200, 201), f"POST → {r.status_code} {r.text[:400]}"
            body = r.json()
            assert float(body.get("harga_pokok") or 0) == 0.0, \
                f"harga_pokok tidak dipaksa 0: {body.get('harga_pokok')}"
            pid = body["id"]
        # verifikasi persisten
        got = _find(_products(admin), "id", pid)
        assert got, "produk uji tidak muncul di GET /api/products"
        assert float(got.get("harga_pokok") or 0) == 0.0
        assert got.get("hpp_source") in ("none", "price", "roll", "harga_pokok")
        # bersihkan (nonaktifkan)
        d = admin.delete(f"{BASE_URL}/api/products/{pid}", timeout=60)
        assert d.status_code in (200, 204), f"DELETE → {d.status_code} {d.text[:200]}"
        assert d.json().get("status") == "inactive"


# ── (3b) sumber data layar Master Produk: GET /api/dashboard ─────────────
class TestDashboardProductsCarryHpp:
    """Master Produk (AdminView) memakai `data.products` dari GET /api/dashboard,
    BUKAN GET /api/products — jadi field hpp/hpp_source harus ikut di sana."""

    def test_dashboard_products_include_hpp(self, admin):
        r = admin.get(f"{BASE_URL}/api/dashboard?entity_id={ENT}", timeout=90)
        assert r.status_code == 200, f"GET /api/dashboard → {r.status_code}"
        products = r.json().get("products") or []
        assert products, "dashboard tidak mengembalikan produk"
        p = _find(products, "id", TARGET)
        assert p, f"{TARGET} tidak ada di dashboard.products"
        assert "hpp" in p and "hpp_source" in p, \
            "dashboard.products TIDAK membawa hpp/hpp_source → layar Master Produk selalu " \
            "menampilkan 'Belum ada penerimaan PO'"
        assert abs(float(p["hpp"]) - 122387) < 50, f"hpp dashboard={p.get('hpp')}"


# ── (4) strip_cost_fields untuk sales ────────────────────────────────────
class TestSalesCostRedaction:
    def test_sales_cannot_see_cost(self, sales):
        products = _products(sales)
        assert len(products) > 0
        leaks = [p.get("sku") for p in products
                 if "hpp" in p or "harga_pokok" in p or "wac" in p]
        assert not leaks, f"HPP bocor ke sales: {leaks[:10]}"
