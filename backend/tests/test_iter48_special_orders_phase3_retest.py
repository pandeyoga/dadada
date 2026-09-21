"""Iter 48 — Special Order FASE 3 retest bug HIGH iter47:
Auto PO on lock-price must use the WINNING supplier contract price
(pricing.cost_price, pricing.contract_number), not a stale contract
from the same supplier.

Also verify existing PO po_bb6ee82dee6b matches KSC/SCT-00029 at Rp 41.000.
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
SUPPLIER = "sup_343fce6af69e"
CUSTOMER = "cust_textile_medan"
PRICE = 43000
QTY = 80
MARGIN = 20


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


# ─── (A) Verify pre-existing PO po_bb6ee82dee6b ──────────────────────────────
class TestExistingPO:
    def test_po_bb6ee82dee6b(self, admin_h):
        po = _get(f"{BASE}/api/purchase-orders/po_bb6ee82dee6b", admin_h)
        items = po.get("items") or []
        assert items, po
        it = items[0]
        price = float(it.get("unit_price") or it.get("price") or 0)
        assert price == 41000.0, f"price={price} expected 41000. item={it}"
        assert it.get("contract_number") == "KSC/SCT-00029", (
            f"contract_number={it.get('contract_number')} expected KSC/SCT-00029"
        )


# ─── (B) Full retest flow ─────────────────────────────────────────────────────
class TestRetestFullFlow:
    state = {}

    def test_01_create_and_submit(self, admin_h):
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": CUSTOMER,
            "title": f"Retest F3 {uuid.uuid4().hex[:6]}",
            "request_types": ["labdip"],
            "detail_level": "full",
            "spec": {"fabric_type": "woven", "gramasi": 150, "lebar": 150},
            "custom_item": {"description": "Retest", "quantity": QTY, "unit": "meter", "target_price": 50000},
            "expected_delivery": "2026-12-22",
            "submit_for_approval": True,
        })
        assert r.status_code == 200, r.text
        od = r.json()
        assert od["status"] == "pending_approval", od
        TestRetestFullFlow.state["oid"] = od["id"]

    def test_02_manager_approve(self, manager_h):
        oid = TestRetestFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/approve", headers=manager_h,
                          json={"notes": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get(f"{BASE}/api/special-orders/{oid}", manager_h)
        assert od["status"] == "confirmed", od["status"]
        assert od.get("sample_ids"), od
        TestRetestFullFlow.state["sample_id"] = od["sample_ids"][0]

    def test_03_send_supplier(self, manager_h):
        sid = TestRetestFullFlow.state["sample_id"]
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/send", headers=manager_h,
                          json={"supplier_ids": [SUPPLIER], "type_codes": ["labdip"]}, timeout=30)
        assert r.status_code == 200, r.text
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", manager_h)
        rounds = smp.get("rounds") or []
        target = next((rr for rr in rounds if rr.get("supplier_id") == SUPPLIER
                       and (rr.get("type_code") == "labdip")), rounds[0] if rounds else None)
        assert target, rounds
        TestRetestFullFlow.state["rid"] = target["id"]

    def test_04_upload_submit_assess(self, manager_h):
        sid = TestRetestFullFlow.state["sample_id"]
        rid = TestRetestFullFlow.state["rid"]
        files = {"file": ("swatch.png", _tiny_png(), "image/png")}
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/attachments",
                          headers={"Authorization": manager_h["Authorization"], "X-Entity-Id": ENTITY},
                          files=files, timeout=30)
        assert r.status_code in (200, 201), r.text
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/submit", headers=manager_h,
                          json={"note": "ok",
                                "measurements": {"delta_e": 0.5, "colorfastness_wash": 4, "colorfastness_rub": 4}},
                          timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/assess", headers=manager_h,
                          json={"result": "acc", "score": 90}, timeout=30)
        assert r.status_code == 200, r.text

    def test_05_decide_by_admin(self, admin_h):
        sid = TestRetestFullFlow.state["sample_id"]
        sku = f"OD-RT-{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/decide", headers=admin_h,
                          json={"supplier_id": SUPPLIER, "reason_code": "warna_paling_dekat",
                                "price": PRICE, "supplier_color_name": "Y", "supplier_color_code": "Y1",
                                "approve_spec": True, "product_sku": sku, "product_name": "Retest"}, timeout=30)
        assert r.status_code == 200, r.text
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", admin_h)
        dec = smp.get("decision") or {}
        assert dec.get("product_id"), dec
        assert dec.get("contract_number"), dec
        assert float(dec.get("price") or 0) == float(PRICE), dec
        TestRetestFullFlow.state["product_id"] = dec["product_id"]
        TestRetestFullFlow.state["contract_number"] = dec["contract_number"]
        TestRetestFullFlow.state["contract_id"] = dec.get("contract_id", "")

    def test_06_customer_decision_acc(self, admin_h):
        oid = TestRetestFullFlow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/customer-decision", headers=admin_h,
                          json={"decision": "acc", "note": "ok"}, timeout=30)
        assert r.status_code == 200, r.text

    def test_07_lock_price_auto_po(self, admin_h):
        oid = TestRetestFullFlow.state["oid"]
        # Fetch a warehouse
        r = requests.get(f"{BASE}/api/warehouses", headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        rows = r.json() if isinstance(r.json(), list) else r.json().get("items") or r.json().get("warehouses") or []
        assert rows, r.text
        wh = rows[0]["id"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/lock-price", headers=admin_h,
                          json={"margin_pct": MARGIN, "warehouse_id": wh, "auto_po": True}, timeout=30)
        assert r.status_code == 200, r.text
        pricing = r.json().get("pricing") or {}
        proc = pricing.get("procurement") or {}
        assert proc.get("po_number"), pricing
        assert not pricing.get("procurement_error"), pricing.get("procurement_error")
        TestRetestFullFlow.state["po_id"] = proc.get("po_id")

    def test_08_verify_po_uses_winner_contract(self, admin_h):
        """CORE ASSERT of iter48 retest — bug fixed if this passes."""
        po_id = TestRetestFullFlow.state["po_id"]
        pid = TestRetestFullFlow.state["product_id"]
        exp_cn = TestRetestFullFlow.state["contract_number"]
        po = _get(f"{BASE}/api/purchase-orders/{po_id}", admin_h)
        it = (po.get("items") or [])[0]
        assert it.get("product_id") == pid, it
        assert float(it["quantity"]) == float(QTY), it
        price = float(it.get("unit_price") or it.get("price") or 0)
        assert price == float(PRICE), (
            f"PO items[0].price={price} != winner cost_price {PRICE} — "
            f"contract_number={it.get('contract_number')}, expected {exp_cn}"
        )
        assert it.get("contract_number") == exp_cn, (
            f"PO items[0].contract_number={it.get('contract_number')} != decision.contract_number {exp_cn}"
        )

    def test_09_convert_to_so(self, admin_h):
        oid = TestRetestFullFlow.state["oid"]
        pid = TestRetestFullFlow.state["product_id"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/convert-to-so", headers=admin_h,
                          json={}, timeout=30)
        assert r.status_code == 200, r.text
        so = r.json().get("sales_order") or {}
        items = so.get("items") or []
        assert items and items[0].get("product_id") == pid, items
        assert float(items[0]["price"]) == 51600.0, items[0]  # 43000 * 1.20
        assert float(items[0].get("cost_price") or 0) == float(PRICE), items[0]
        assert float(items[0].get("margin_pct") or 0) == float(MARGIN), items[0]
