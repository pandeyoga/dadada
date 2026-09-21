"""Iterasi 268 — `order_preview` pada dialog Verifikasi & Pemenuhan (Meja Admin Sales).

Cakupan:
* GET /api/sales-orders/{id}/verification → order_preview lengkap
* GET /api/sales-admin/orders/{id}/fulfillment → order_preview sama
* REGRESI: POST /api/sales-orders/{id}/verify (sukses & 409 bergap)
"""
import os

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
ENT = "ent_ksc"


def _login(email, password="demo12345"):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} gagal: {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("salesadmin@kainnusantara.id")


@pytest.fixture(scope="module")
def desk(sa):
    r = sa.get(f"{BASE_URL}/api/sales-admin/desk", params={"entity_id": ENT}, timeout=60)
    assert r.status_code == 200, f"desk gagal: {r.status_code} {r.text[:300]}"
    return r.json()


def _rows(desk, kind):
    out = []
    for q in desk.get("queues") or []:
        for row in q.get("rows") or []:
            if row.get("action_kind") == kind:
                out.append(row)
    return out


def _assert_preview_shape(p, label=""):
    assert isinstance(p, dict), f"{label}: order_preview bukan objek"
    for key in ("customer_name", "shipping_address", "payment_term", "sales_name",
                "items", "backorders", "totals", "created_at", "status"):
        assert key in p, f"{label}: field '{key}' hilang dari order_preview"
    addr = p["shipping_address"]
    for key in ("recipient_name", "phone", "address", "city"):
        assert key in addr, f"{label}: shipping_address.{key} hilang"
    t = p["totals"]
    for key in ("net_subtotal", "ppn_amount", "ppn_rate", "grand_total", "is_pkp"):
        assert key in t, f"{label}: totals.{key} hilang"
        if key != "is_pkp":
            assert isinstance(t[key], (int, float)), f"{label}: totals.{key} bukan angka"
    for it in p["items"]:
        for key in ("product_id", "product_name", "quantity", "price", "line_total",
                    "available_qty", "stock_ok"):
            assert key in it, f"{label}: items[].{key} hilang"
        assert isinstance(it["stock_ok"], bool)
        assert isinstance(it["available_qty"], (int, float))
    assert "_id" not in p, f"{label}: ada _id mongo di payload"
    for it in p["items"]:
        assert "_id" not in it, f"{label}: ada _id mongo di items[]"


class TestVerificationPreview:
    """GET /api/sales-orders/{id}/verification"""

    def test_desk_has_verify_rows(self, desk):
        rows = _rows(desk, "verify")
        assert rows, "tidak ada baris antrean 'Perlu diverifikasi' di meja admin sales"

    def test_preview_shape_for_order_with_items(self, sa, desk):
        rows = _rows(desk, "verify")
        assert rows
        checked = 0
        for row in rows[:6]:
            oid = row.get("ref_id") or row.get("id")
            r = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
            assert r.status_code == 200, f"{oid}: {r.status_code} {r.text[:300]}"
            data = r.json()
            assert "order_preview" in data, f"{oid}: order_preview tidak ada"
            _assert_preview_shape(data["order_preview"], oid)
            assert "checks" in data and data["checks"]
            if data["order_preview"]["items"]:
                checked += 1
                p = data["order_preview"]
                assert p["customer_name"], f"{oid}: customer_name kosong"
                assert p["totals"]["grand_total"] > 0, f"{oid}: grand_total nol padahal ada item"
        assert checked > 0, "tidak ada order antrean verify yang punya items — cek data demo"

    def test_so_008_preview(self, sa):
        r = sa.get(f"{BASE_URL}/api/sales-orders/so_008/verification", timeout=30)
        if r.status_code == 404:
            pytest.skip("so_008 tidak ada di data demo")
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        p = r.json().get("order_preview")
        _assert_preview_shape(p, "so_008")
        assert p["items"], "so_008 seharusnya punya items"
        assert p["totals"]["grand_total"] > 0
        print("so_008 grand_total =", p["totals"]["grand_total"],
              "customer =", p["customer_name"], "sales =", p["sales_name"])

    def test_backorder_only_order_preview(self, sa):
        """SO-0009 murni backorder → backorders[] terisi, items[] kosong."""
        r = sa.get(f"{BASE_URL}/api/sales-orders", params={"entity_id": ENT, "limit": 200},
                   timeout=60)
        assert r.status_code == 200, f"list SO gagal: {r.status_code} {r.text[:200]}"
        body = r.json()
        orders = body if isinstance(body, list) else (body.get("items") or body.get("orders") or [])
        target = next((o for o in orders if str(o.get("number", "")).endswith("SO-0009")
                       or o.get("number") == "SO-0009"), None)
        if not target:
            pytest.skip("SO-0009 tidak ditemukan")
        oid = target["id"]
        r = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        p = data["order_preview"]
        _assert_preview_shape(p, "SO-0009")
        assert p["backorders"], "SO-0009 murni backorder tetapi backorders[] kosong"
        for b in p["backorders"]:
            assert b["backorder_qty"] > 0
            assert b["product_name"] or b["sku"]
        print("SO-0009 backorders:", p["backorders"], "items:", len(p["items"]))


class TestFulfillmentPreview:
    """GET /api/sales-admin/orders/{id}/fulfillment"""

    def test_fulfillment_options_include_preview(self, sa, desk):
        rows = _rows(desk, "fulfill")
        if not rows:
            pytest.skip("tidak ada baris antrean 'Perlu dipenuhi'")
        ok = 0
        for row in rows[:4]:
            oid = row.get("ref_id") or row.get("id")
            r = sa.get(f"{BASE_URL}/api/sales-admin/orders/{oid}/fulfillment", timeout=30)
            assert r.status_code == 200, f"{oid}: {r.status_code} {r.text[:300]}"
            data = r.json()
            assert "order_preview" in data, f"{oid}: order_preview tidak ada di fulfillment"
            _assert_preview_shape(data["order_preview"], oid)
            assert "options" in data or "modes" in data, f"{oid}: opsi pemenuhan hilang: {list(data)}"
            ok += 1
        assert ok > 0

    def test_preview_consistent_between_endpoints(self, sa, desk):
        rows = _rows(desk, "fulfill")
        if not rows:
            pytest.skip("tidak ada baris fulfill")
        oid = rows[0].get("ref_id") or rows[0].get("id")
        a = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
        b = sa.get(f"{BASE_URL}/api/sales-admin/orders/{oid}/fulfillment", timeout=30)
        if a.status_code != 200 or b.status_code != 200:
            pytest.skip(f"salah satu endpoint tak 200 ({a.status_code}/{b.status_code})")
        assert a.json()["order_preview"] == b.json()["order_preview"], \
            "order_preview beda antara endpoint verification dan fulfillment"


class TestVerifyRegression:
    """POST /api/sales-orders/{id}/verify — hanya SATU order diverifikasi."""

    def test_verify_ready_order_succeeds(self, sa, desk):
        rows = _rows(desk, "verify")
        target = None
        for row in rows:
            oid = row.get("ref_id") or row.get("id")
            r = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
            if r.status_code == 200 and r.json().get("ready") and not (r.json().get("verification")):
                target = oid
                break
        if not target:
            pytest.skip("tidak ada order siap-verifikasi yang belum terverifikasi")
        r = sa.post(f"{BASE_URL}/api/sales-orders/{target}/verify",
                    json={"note": "TEST_iter268 verifikasi otomatis"}, timeout=30)
        assert r.status_code == 200, f"{target}: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("verification", {}).get("status") == "verified"
        # persistensi
        r2 = sa.get(f"{BASE_URL}/api/sales-orders/{target}/verification", timeout=30)
        assert r2.status_code == 200
        assert (r2.json().get("verification") or {}).get("status") == "verified"

    def test_verify_incomplete_order_returns_409(self, sa, desk):
        rows = _rows(desk, "verify")
        target = None
        for row in rows:
            oid = row.get("ref_id") or row.get("id")
            r = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
            if r.status_code == 200 and not r.json().get("ready"):
                target = oid
                break
        if not target:
            pytest.skip("tidak ada order cacat di antrean")
        r = sa.post(f"{BASE_URL}/api/sales-orders/{target}/verify", json={"note": ""}, timeout=30)
        assert r.status_code == 409, f"harusnya 409, dapat {r.status_code} {r.text[:300]}"
        det = r.json().get("detail")
        assert isinstance(det, dict) and det.get("checks"), f"detail 409 tak berisi checks: {det}"

    def test_verify_synthetic_defective_order_409(self, sa):
        """Order cacat buatan (tanpa alamat/termin/item) → 409 + daftar gap."""
        from pymongo import MongoClient
        be = dotenv_values("/app/backend/.env")
        cli = MongoClient(be.get("MONGO_URL"))
        col = cli[be.get("DB_NAME")].sales_orders
        oid = "t1_iter268_defect"
        col.delete_many({"id": oid})
        col.insert_one({"id": oid, "number": "TEST_SO-DEFECT", "entity_id": ENT,
                        "status": "draft", "items": [], "backorders": [],
                        "customer_name": "TEST_Pelanggan", "shipping_address": {},
                        "total_amount": 0, "_t1_probe": True})
        try:
            pre = sa.get(f"{BASE_URL}/api/sales-orders/{oid}/verification", timeout=30)
            assert pre.status_code == 200, f"{pre.status_code} {pre.text[:300]}"
            body = pre.json()
            assert body.get("ready") is False
            assert "order_preview" in body
            _assert_preview_shape(body["order_preview"], "synthetic")
            r = sa.post(f"{BASE_URL}/api/sales-orders/{oid}/verify", json={"note": ""}, timeout=30)
            assert r.status_code == 409, f"harusnya 409, dapat {r.status_code} {r.text[:300]}"
            det = r.json().get("detail")
            assert isinstance(det, dict) and det.get("checks"), f"detail 409: {det}"
            assert "Alamat" in det.get("message", "") or det.get("message")
        finally:
            col.delete_many({"id": oid})
            cli.close()
