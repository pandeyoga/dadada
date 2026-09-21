"""Extra coverage untuk fitur Jual Sampel POS (iterasi tester).

Cakupan tambahan di luar test_sample_pos_flow.py:
- GET /sample-quote punya `source` & `suggested_roll`
- /sample-requests LAMA harus 404 (dihapus)
- Mixed cart (roll biasa + sampel) -> SO 200 & has_sample true
- Tanpa sample_price -> harga ikut quote (source harga_daftar / master_sampel)
- cut-sample: TAG_UNKNOWN & REASON_REQUIRED
- Master harga sampel: GET /sample-prices, PUT lalu quote -> source master_sampel
"""
import os
import pytest
import requests
from pymongo import MongoClient

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/") + "/api"
db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "demo12345"}, timeout=15)
    r.raise_for_status()
    tok = r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def ctx():
    admin = _login("admin@kainnusantara.id")
    wh = _login("warehouse@kainnusantara.id")
    roll = db.inventory_rolls.find_one({"status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 20}}, {"_id": 0})
    if not roll:
        pytest.skip("butuh roll available ent_ksc")
    prod = db.products.find_one({"id": roll["product_id"]}, {"_id": 0})
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0}) or db.customers.find_one({}, {"_id": 0})
    return {"admin": admin, "wh": wh, "roll": roll, "prod": prod, "cust": cust}


# --- /sample-quote structure ---
def test_sample_quote_has_source_and_suggested_roll(ctx):
    r = requests.get(f"{BASE}/sample-quote", params={"product_id": ctx["prod"]["id"], "length": 1.5}, headers=ctx["admin"], timeout=15)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["price_per_unit"] > 0
    assert "source" in j
    assert j["source"] in ("master_sampel", "harga_daftar", "harga_daftar_default", "manual_sampel")
    # suggested_roll FIFO
    assert "suggested_roll" in j and j["suggested_roll"] is not None
    assert j["suggested_roll"].get("id")


# --- /sample-requests dihapus ---
def test_legacy_sample_requests_removed(ctx):
    r1 = requests.get(f"{BASE}/sample-requests", headers=ctx["admin"], timeout=10)
    r2 = requests.post(f"{BASE}/sample-requests", json={}, headers=ctx["admin"], timeout=10)
    assert r1.status_code == 404, f"GET expected 404, got {r1.status_code}"
    assert r2.status_code == 404, f"POST expected 404, got {r2.status_code}"


# --- Mixed cart & auto-price via quote ---
def test_mixed_cart_and_price_from_quote(ctx):
    prod, cust, roll = ctx["prod"], ctx["cust"], ctx["roll"]
    q = requests.get(f"{BASE}/sample-quote", params={"product_id": prod["id"], "length": 1.5}, headers=ctx["admin"], timeout=15).json()
    payload = {
        "customer_id": cust["id"],
        "shipping_address_id": cust["addresses"][0]["id"],
        "entity_id": "ent_ksc",
        "items": [
            {"product_id": prod["id"], "quantity": 5.0, "unit": prod["base_unit"]},
            {"product_id": prod["id"], "quantity": 1.5, "unit": prod["base_unit"], "is_sample": True},
        ],
    }
    r = requests.post(f"{BASE}/sales-orders", headers=ctx["admin"], json=payload, timeout=30)
    assert r.status_code == 200, r.text
    so = r.json()
    assert so["has_sample"] is True
    sample_line = next(it for it in so["items"] if it.get("is_sample"))
    regular_line = next(it for it in so["items"] if not it.get("is_sample"))
    assert sample_line["fulfillment_mode"] == "sample_cut"
    assert regular_line.get("fulfillment_mode") != "sample_cut"
    # Harga sampel ikut quote (source non-manual)
    assert sample_line["price_source"] in ("master_sampel", "harga_daftar", "harga_daftar_default")
    assert abs(float(sample_line["price"]) - float(q["price_per_unit"])) < 0.01


# --- cut-sample error cases ---
def test_cut_sample_tag_unknown_and_reason_required(ctx):
    prod, cust, roll = ctx["prod"], ctx["cust"], ctx["roll"]
    # Buat SO sampel & bawa ke confirmed
    mgr = _login("manager@kainnusantara.id")
    r = requests.post(f"{BASE}/sales-orders", headers=ctx["admin"], json={
        "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"], "entity_id": "ent_ksc",
        "items": [{"product_id": prod["id"], "quantity": 1.5, "unit": prod["base_unit"], "is_sample": True, "sample_price": 9999}],
    }, timeout=30)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    requests.post(f"{BASE}/sales-orders/{oid}/submit-for-approval", headers=ctx["admin"], timeout=15)
    for pa in db.sales_orders.find_one({"id": oid}, {"_id": 0}).get("pending_approvals", []):
        if pa.get("status") != "approved":
            requests.post(f"{BASE}/sales-orders/{oid}/approvals/{pa['id']}/decide",
                          json={"decision": "approve", "note": "uji"}, headers=mgr, timeout=15)
    requests.post(f"{BASE}/sales-orders/{oid}/verify", json={"note": "uji"}, headers=ctx["admin"], timeout=15)
    requests.post(f"{BASE}/sales-orders/{oid}/approve", headers=mgr, timeout=15)
    requests.post(f"{BASE}/sales-orders/{oid}/confirm", headers=ctx["admin"], timeout=30)

    task = db.wms_tasks.find_one({"order_id": oid, "task_subtype": "sample_cut"}, {"_id": 0})
    assert task, "sample_cut task belum dibuat"
    tid = task["id"]

    # TAG_UNKNOWN
    r = requests.post(f"{BASE}/outbound/tasks/{tid}/cut-sample",
                      json={"epc": "FAKE-EPC-DOES-NOT-EXIST-TEST", "actual_length": 1.4, "reason": "uji"},
                      headers=ctx["wh"], timeout=15)
    assert r.status_code == 404, r.text
    assert r.json().get("detail", {}).get("code") == "TAG_UNKNOWN"

    # REASON_REQUIRED: pilih roll produk yang sama tapi bukan roll saran; tanpa reason
    other_same = db.inventory_rolls.find_one(
        {"status": "available", "product_id": prod["id"], "owner_entity_id": "ent_ksc", "id": {"$ne": task.get("suggested_roll_id")}},
        {"_id": 0},
    )
    if other_same:
        r = requests.post(f"{BASE}/outbound/tasks/{tid}/cut-sample",
                          json={"roll_id": other_same["id"], "actual_length": 1.4},
                          headers=ctx["wh"], timeout=15)
        assert r.status_code == 400, r.text
        assert r.json().get("detail", {}).get("code") == "REASON_REQUIRED"


# --- Master harga sampel ---
def test_sample_prices_admin_and_master_source(ctx):
    r = requests.get(f"{BASE}/sample-prices", headers=ctx["admin"], timeout=15)
    assert r.status_code == 200, r.text
    lst = r.json()
    assert isinstance(lst, list)
    # Cari template terkait product parent kita
    prod = ctx["prod"]
    parent_id = prod.get("parent_id") or prod["id"]
    matches = [t for t in lst if t.get("product_id") in (parent_id, prod["id"])]
    if not matches:
        pytest.skip("belum ada template sample-price untuk produk uji")
    tpl = matches[0]
    new_price = 54321
    up = requests.put(f"{BASE}/sample-prices/{tpl['id']}", headers=ctx["admin"],
                      json={"price_per_unit": new_price}, timeout=15)
    assert up.status_code == 200, up.text

    q = requests.get(f"{BASE}/sample-quote",
                     params={"product_id": prod["id"], "length": 1.0},
                     headers=ctx["admin"], timeout=15).json()
    assert q["source"] == "master_sampel"
    assert abs(float(q["price_per_unit"]) - new_price) < 0.01
