"""Iter 47 — Special Order FASE 3:
Auto PR/PO on lock-price, warehouse default, status→in_production, convert-to-so
with final locked price, printing OD design category fallback + explicit,
submit endpoint (draft→pending_approval).
"""
import io
import os
import uuid

import pytest
import requests


def _read_backend_url():
    env = os.environ.get("REACT_APP_BACKEND_URL")
    if env:
        return env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


BASE = _read_backend_url().rstrip("/")
ENTITY = "ent_ksc"


def _login(email, pwd="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(email):
    return {"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def admin_h():
    return _h("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager_h():
    return _h("manager@kainnusantara.id")


def _tiny_png():
    return bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
    )


def _get(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _get_od(oid, headers):
    return _get(f"{BASE}/api/special-orders/{oid}", headers)


# ─── (A) VERIFIKASI baseline sord_dab2dcbc0de9 ───────────────────────────────
class TestBaselineSord:
    OID = "sord_dab2dcbc0de9"

    def test_baseline(self, admin_h):
        od = _get_od(self.OID, admin_h)
        assert od["status"] == "in_production", od["status"]
        assert od.get("linked_pr_number") == "PR-00010", od.get("linked_pr_number")
        assert od.get("linked_po_number") == "KSC/PO-00016", od.get("linked_po_number")
        chain = od.get("chain") or {}
        pos = chain.get("po") or []
        assert pos and pos[0].get("supplier_name") == "Solo Weave", pos
        so = chain.get("so") or {}
        assert (so.get("order_number") or so.get("number")) == "KSC/SO-00016", so

    def test_baseline_so_uses_locked_price(self, admin_h):
        od = _get_od(self.OID, admin_h)
        so_id = ((od.get("chain") or {}).get("so") or {}).get("id")
        assert so_id, "chain.so.id missing"
        so = _get(f"{BASE}/api/sales-orders/{so_id}", admin_h)
        items = so.get("items") or []
        assert items and float(items[0]["price"]) == 49400.0, items
        assert items[0].get("special_order_price") is True
        assert float(items[0].get("cost_price") or 0) == 38000.0
        assert float(items[0].get("margin_pct") or 0) == 30.0

    def test_baseline_po_items(self, admin_h):
        po = _get(f"{BASE}/api/purchase-orders/po_648175665dd5", admin_h)
        it = (po.get("items") or [])[0]
        assert float(it.get("unit_price") or it.get("price") or 0) == 38000.0
        assert po.get("special_order_number", "").startswith("SORD-")


# ─── (B) Alur baru penuh ─────────────────────────────────────────────────────
class TestNewODFullFlow:
    """Buat OD → submit → approve → sampling → decide → customer ACC →
    lock-price auto_po → PR/PO → convert-to-so → unlock 400 / re-convert 400."""

    state = {}

    def test_01_create_and_submit(self, admin_h):
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": "cust_textile_medan",
            "title": f"Uji F3 {uuid.uuid4().hex[:6]}",
            "request_types": ["labdip"],
            "detail_level": "full",
            "spec": {"fabric_type": "woven", "gramasi": 150, "lebar": 150},
            "custom_item": {"description": "Uji F3", "quantity": 120, "unit": "meter", "target_price": 50000},
            "expected_delivery": "2026-12-20",
            "submit_for_approval": True,
        })
        assert r.status_code == 200, r.text
        od = r.json()
        assert od["status"] == "pending_approval", od
        TestNewODFullFlow.state["oid"] = od["id"]

    def test_02_manager_approve(self, manager_h):
        oid = TestNewODFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/approve", headers=manager_h,
                          json={"notes": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get_od(oid, manager_h)
        assert od["status"] == "confirmed", od["status"]
        assert od.get("sample_ids"), od
        TestNewODFullFlow.state["sample_id"] = od["sample_ids"][0]

    def test_03_send_supplier(self, manager_h):
        sid = TestNewODFullFlow.state["sample_id"]
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/send", headers=manager_h,
                          json={"supplier_ids": ["sup_343fce6af69e"], "type_codes": ["labdip"]}, timeout=30)
        assert r.status_code == 200, r.text
        # Fetch rounds
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", manager_h)
        rounds = []
        for r_ in smp.get("rounds") or []:
            rounds.append(r_)
        assert rounds, "No rounds after send"
        # Pick the round created for sup_343fce6af69e / labdip
        target = next((rr for rr in rounds if rr.get("supplier_id") == "sup_343fce6af69e" and (rr.get("type_code") == "labdip" or "labdip" in (rr.get("type_codes") or []))), rounds[0])
        TestNewODFullFlow.state["rid"] = target["id"]

    def test_04_upload_submit_assess(self, manager_h):
        sid = TestNewODFullFlow.state["sample_id"]
        rid = TestNewODFullFlow.state["rid"]
        # Upload PNG attachment
        files = {"file": ("swatch.png", _tiny_png(), "image/png")}
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/attachments",
                          headers={"Authorization": manager_h["Authorization"], "X-Entity-Id": ENTITY},
                          files=files, timeout=30)
        assert r.status_code in (200, 201), r.text
        # Submit result
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/submit", headers=manager_h,
                          json={"note": "ok",
                                "measurements": {"delta_e": 0.5, "colorfastness_wash": 4, "colorfastness_rub": 4}},
                          timeout=30)
        assert r.status_code == 200, r.text
        # Assess
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/assess", headers=manager_h,
                          json={"result": "acc", "score": 90}, timeout=30)
        assert r.status_code == 200, r.text

    def test_05_decide_by_admin(self, admin_h):
        sid = TestNewODFullFlow.state["sample_id"]
        sku = f"OD-F3-{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/decide", headers=admin_h,
                          json={"supplier_id": "sup_343fce6af69e", "reason_code": "warna_paling_dekat",
                                "price": 40000, "supplier_color_name": "X", "supplier_color_code": "X1",
                                "approve_spec": True, "product_sku": sku, "product_name": "Kain F3"}, timeout=30)
        assert r.status_code == 200, r.text
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", admin_h)
        dec = smp.get("decision") or {}
        assert dec.get("product_id"), dec
        TestNewODFullFlow.state["product_id"] = dec["product_id"]

    def test_06_customer_decision_acc(self, admin_h):
        oid = TestNewODFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/customer-decision", headers=admin_h,
                          json={"decision": "acc", "note": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get_od(oid, admin_h)
        chain = od.get("chain") or {}
        assert chain.get("phase") == "pricing", chain.get("phase")

    def test_07_get_warehouse(self, admin_h):
        r = requests.get(f"{BASE}/api/warehouses", headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        rows = r.json() if isinstance(r.json(), list) else r.json().get("items") or r.json().get("warehouses") or []
        assert rows, r.text
        TestNewODFullFlow.state["wh"] = rows[0]["id"]

    def test_08_lock_price_auto_po(self, admin_h):
        oid = TestNewODFullFlow.state["oid"]
        wh = TestNewODFullFlow.state["wh"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/lock-price", headers=admin_h,
                          json={"margin_pct": 25, "warehouse_id": wh, "auto_po": True}, timeout=30)
        assert r.status_code == 200, r.text
        pricing = r.json().get("pricing") or {}
        proc = pricing.get("procurement") or {}
        assert proc.get("po_number"), pricing
        assert not pricing.get("procurement_error"), pricing.get("procurement_error")
        TestNewODFullFlow.state["po_id"] = proc.get("po_id")
        TestNewODFullFlow.state["po_number"] = proc.get("po_number")
        # Verify OD state
        od = _get_od(oid, admin_h)
        assert od["status"] == "in_production", od["status"]
        chain = od.get("chain") or {}
        pos = chain.get("po") or []
        assert pos and pos[0].get("supplier_name") == "Solo Weave", pos
        assert pos[0].get("expected_delivery_date") == "2026-12-20", pos[0]

    def test_09_verify_po(self, admin_h):
        po_id = TestNewODFullFlow.state["po_id"]
        wh = TestNewODFullFlow.state["wh"]
        pid = TestNewODFullFlow.state["product_id"]
        po = _get(f"{BASE}/api/purchase-orders/{po_id}", admin_h)
        it = (po.get("items") or [])[0]
        assert it.get("product_id") == pid, it
        assert float(it["quantity"]) == 120.0
        assert po.get("warehouse_id") == wh, po.get("warehouse_id")
        price = float(it.get("unit_price") or it.get("price") or 0)
        # SPEC: PO unit_price must equal winner sample contract price (Rp 40.000).
        # BUG (iter47): PR→PO conversion picks the FIRST active supplier contract
        # regardless of product_id, so PO uses a stale contract price (38.000 from
        # KSC/SCT-00025) instead of the just-created winner contract (40.000, KSC/SCT-00027).
        assert price == 40000.0, (
            f"PO price {price} != winner contract 40000 — auto_procure picked wrong contract "
            f"(contract_id={it.get('contract_id')}, contract_number={it.get('contract_number')}). "
            "Expected the SCT- created by /decide (approve_spec+price=40000)."
        )

    def test_10_product_lifecycle_exclusive(self, admin_h):
        pid = TestNewODFullFlow.state["product_id"]
        # products list — filter by scope not needed, will search full list
        r = requests.get(f"{BASE}/api/products", headers=admin_h, timeout=30, params={"limit": 2000})
        assert r.status_code == 200, r.text
        rows = r.json() if isinstance(r.json(), list) else (r.json().get("items") or r.json().get("products") or [])
        p = next((x for x in rows if x.get("id") == pid), None)
        assert p is not None, f"Product {pid} not in list"
        assert p.get("lifecycle") == "produksi", p.get("lifecycle")
        assert p.get("exclusive_customer_id") == "cust_textile_medan", p.get("exclusive_customer_id")

    def test_11_unlock_price_400(self, admin_h):
        oid = TestNewODFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/unlock-price", headers=admin_h,
                          json={"reason": "coba buka"}, timeout=30)
        # PR/PO already exist → 400 (linked_pr_id/linked_po_id set)
        assert r.status_code == 400, r.text

    def test_12_convert_to_so(self, admin_h):
        oid = TestNewODFullFlow.state["oid"]
        pid = TestNewODFullFlow.state["product_id"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/convert-to-so", headers=admin_h,
                          json={}, timeout=30)
        assert r.status_code == 200, r.text
        so = r.json().get("sales_order") or {}
        items = so.get("items") or []
        assert items and items[0].get("product_id") == pid, items
        assert float(items[0]["price"]) == 50000.0, items[0]  # 40000 * 1.25
        assert items[0].get("special_order_price") is True
        assert float(items[0].get("margin_pct") or 0) == 25.0
        od = _get_od(oid, admin_h)
        assert od.get("linked_sales_order_id"), od

    def test_13_reconvert_400(self, admin_h):
        oid = TestNewODFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/convert-to-so", headers=admin_h,
                          json={}, timeout=30)
        assert r.status_code == 400, r.text


# ─── (C) Kategori fallback + explicit untuk printing ─────────────────────────
class TestPrintingCategoryFallback:
    def test_fallback_first_active(self, admin_h, manager_h):
        # Create draft printing OD (no category)
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": "cust_textile_medan", "title": "Uji kat",
            "request_types": ["printing"], "detail_level": "reference",
            "custom_item": {"description": "k", "quantity": 50, "unit": "meter", "target_price": 60000},
            "expected_delivery": "2026-12-20", "submit_for_approval": False,
        })
        assert r.status_code == 200, r.text
        od = r.json()
        assert od["status"] == "draft", od
        oid = od["id"]
        # Submit
        r = requests.post(f"{BASE}/api/special-orders/{oid}/submit", headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "pending_approval"
        # Approve
        r = requests.post(f"{BASE}/api/special-orders/{oid}/approve", headers=manager_h,
                          json={"notes": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get_od(oid, admin_h)
        dr_id = od.get("design_request_id")
        assert dr_id, od
        # Fetch design request
        dr = _get(f"{BASE}/api/design-requests/{dr_id}", admin_h)
        assert dr.get("category_code") == "ABS", dr.get("category_code")
        assert dr.get("design_category_code") == "AO", dr.get("design_category_code")

    def test_explicit_categories(self, admin_h, manager_h):
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": "cust_textile_medan", "title": "Uji kat BGA",
            "request_types": ["printing"], "detail_level": "reference",
            "pattern_category_code": "BGA", "design_category_code": "PG",
            "custom_item": {"description": "k2", "quantity": 50, "unit": "meter", "target_price": 60000},
            "expected_delivery": "2026-12-20", "submit_for_approval": True,
        })
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/approve", headers=manager_h,
                          json={"notes": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get_od(oid, admin_h)
        dr_id = od.get("design_request_id")
        assert dr_id, od
        dr = _get(f"{BASE}/api/design-requests/{dr_id}", admin_h)
        assert dr.get("category_code") == "BGA", dr.get("category_code")
        assert dr.get("design_category_code") == "PG", dr.get("design_category_code")
