"""§3-C (2026-09-16) — Jual sampel = baris SO ber-`is_sample` + tugas potong gudang (sample_cut).

Alur: POS checkout (is_sample, harga manual) → approve/verify/confirm → tugas outbound
bersubtipe sample_cut → gudang pindai EPC roll induk + panjang aktual → roll anak reserved,
induk berkurang, SO ter-reprice → dispatch → shipped.
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
    admin, mgr, wh = _login("admin@kainnusantara.id"), _login("manager@kainnusantara.id"), _login("warehouse@kainnusantara.id")
    roll = db.inventory_rolls.find_one({"status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 20}}, {"_id": 0})
    tag = db.rfid_tags.find_one({"roll_id": roll["id"]}, {"_id": 0})
    if not roll or not tag:
        pytest.skip("butuh roll available ber-tag RFID milik ent_ksc")
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0}) or db.customers.find_one({}, {"_id": 0})
    prod = db.products.find_one({"id": roll["product_id"]}, {"_id": 0})
    return {"admin": admin, "mgr": mgr, "wh": wh, "roll": roll, "epc": tag["epc"], "cust": cust, "prod": prod}


def test_sample_line_end_to_end(ctx):
    prod, cust, roll = ctx["prod"], ctx["cust"], ctx["roll"]
    q = requests.get(f"{BASE}/sample-quote", params={"product_id": prod["id"], "length": 1.5}, headers=ctx["admin"], timeout=15)
    assert q.status_code == 200 and q.json()["price_per_unit"] > 0

    r = requests.post(f"{BASE}/sales-orders", headers=ctx["admin"], timeout=30, json={
        "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"], "entity_id": "ent_ksc",
        "items": [{"product_id": prod["id"], "quantity": 1.5, "unit": prod["base_unit"], "is_sample": True, "sample_price": 12345}]})
    assert r.status_code == 200, r.text
    so = r.json()
    oid = so["id"]
    it = so["items"][0]
    assert so["has_sample"] and it["is_sample"] and it["price"] == 12345 and it["price_source"] == "manual_sampel"
    assert it["reserved_qty"] == 0 and it["fulfillment_mode"] == "sample_cut" and so["status"] == "reserved"

    requests.post(f"{BASE}/sales-orders/{oid}/submit-for-approval", headers=ctx["admin"], timeout=15)
    for pa in db.sales_orders.find_one({"id": oid}, {"_id": 0}).get("pending_approvals", []):
        if pa.get("status") != "approved":
            requests.post(f"{BASE}/sales-orders/{oid}/approvals/{pa['id']}/decide", json={"decision": "approve", "note": "uji"}, headers=ctx["mgr"], timeout=15)
    requests.post(f"{BASE}/sales-orders/{oid}/verify", json={"note": "uji"}, headers=ctx["admin"], timeout=15)
    assert requests.post(f"{BASE}/sales-orders/{oid}/approve", headers=ctx["mgr"], timeout=15).status_code == 200
    assert requests.post(f"{BASE}/sales-orders/{oid}/confirm", headers=ctx["admin"], timeout=30).status_code == 200

    task = db.wms_tasks.find_one({"order_id": oid}, {"_id": 0})
    assert task and task["flow_type"] == "outbound" and task["task_subtype"] == "sample_cut" and task["status"] == "created"
    tid = task["id"]

    other = db.inventory_rolls.find_one({"status": "available", "product_id": {"$ne": prod["id"]}}, {"_id": 0})
    r = requests.post(f"{BASE}/outbound/tasks/{tid}/cut-sample", json={"roll_id": other["id"], "reason": "x"}, headers=ctx["wh"], timeout=15)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "ROLL_WRONG_PRODUCT"

    before = float(roll["length_remaining"])
    r = requests.post(f"{BASE}/outbound/tasks/{tid}/cut-sample", json={"epc": ctx["epc"], "actual_length": 1.4, "reason": "uji"}, headers=ctx["wh"], timeout=30)
    assert r.status_code == 200, r.text
    cut = r.json()["cut"]
    assert cut["length"] == 1.4 and cut["child_roll_no"].startswith(roll["roll_no"])
    parent = db.inventory_rolls.find_one({"id": roll["id"]}, {"_id": 0})
    assert abs(float(parent["length_remaining"]) - (before - 1.4)) < 0.01
    child = db.inventory_rolls.find_one({"id": cut["child_roll_id"]}, {"_id": 0})
    assert child["status"] == "reserved" and child["reserved_ref"]["id"] == oid and child["rfid_tag_id"] is None
    so2 = db.sales_orders.find_one({"id": oid}, {"_id": 0})
    assert so2["items"][0]["quantity"] == 1.4 and so2["items"][0]["sample_cut_status"] == "cut" and so2["grand_total"] < so["grand_total"]
    assert requests.post(f"{BASE}/outbound/tasks/{tid}/cut-sample", json={"epc": ctx["epc"]}, headers=ctx["wh"], timeout=15).status_code == 409

    r = requests.post(f"{BASE}/outbound/tasks/{tid}/dispatch", headers=ctx["wh"], timeout=30)
    assert r.status_code == 200, r.text
    assert db.sales_orders.find_one({"id": oid}, {"_id": 0, "status": 1})["status"] == "shipped"
    assert db.inventory_rolls.find_one({"id": cut["child_roll_id"]}, {"_id": 0, "status": 1})["status"] == "in_transit_sales"
