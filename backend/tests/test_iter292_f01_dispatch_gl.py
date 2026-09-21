"""Iteration 292 — F-01 MUTATING test: revenue + COGS JE posted at dispatch (no restart)."""
import os
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
db = MongoClient(be.get("MONGO_URL"))[be.get("DB_NAME")]

ORDER = "so_006"


@pytest.fixture(scope="module")
def hdr():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    assert r.status_code == 200, r.text[:300]
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc",
            "Content-Type": "application/json"}


def test_e01_reservations_visible_for_owning_entity(hdr):
    """Counter-check for E-01: the scoped endpoint still returns data for its own entity."""
    r = requests.get(f"{BASE}/products/prod_batik_mega/stock-breakdown", headers=hdr, timeout=60)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert "reservations" in body
    print("ent_ksc reservations count:", len(body.get("reservations") or []))
    for item in (body.get("reservations") or []):
        assert item.get("entity_id") == "ent_ksc"


def test_f01_dispatch_posts_revenue_and_cogs(hdr):
    so = db.sales_orders.find_one({"id": ORDER}, {"_id": 0, "status": 1})
    assert so, "so_006 missing"
    print("initial status:", so.get("status"))

    for path in [f"/sales-orders/{ORDER}/verify", f"/sales-orders/{ORDER}/confirm",
                 f"/wms/tasks/outbound-from-order/{ORDER}"]:
        if so.get("status") in ("shipped", "delivered", "closed"):
            print("already dispatched (re-run) — skipping mutation, asserting JE only")
            break
        r = requests.post(f"{BASE}{path}", headers=hdr, json={}, timeout=120)
        assert r.status_code in (200, 201), f"{path} -> {r.status_code}: {r.text[:400]}"
        print(path, "ok")

    if so.get("status") not in ("shipped", "delivered", "closed"):
        tasks = list(db.wms_tasks.find({"order_id": ORDER, "flow_type": "outbound"},
                                       {"_id": 0, "id": 1, "quantity": 1, "status": 1}))
        assert tasks, "no outbound wms_tasks created for so_006"
        print("tasks:", tasks)

        for t in tasks:
            qty = t.get("quantity")
            r = requests.post(f"{BASE}/outbound/tasks/{t['id']}/scan-pick?actual_qty={qty}",
                              headers=hdr, json={}, timeout=120)
            assert r.status_code == 200, f"scan-pick {t['id']} -> {r.status_code}: {r.text[:400]}"
            r = requests.post(f"{BASE}/outbound/tasks/{t['id']}/dispatch", headers=hdr, json={}, timeout=120)
            assert r.status_code == 200, f"dispatch {t['id']} -> {r.status_code}: {r.text[:400]}"
        print("all tasks dispatched")

    # No backend restart, no gl/sync: JE must already exist.
    # KEB-PDPT tahap 2 (pro-rata): pesanan BER-surat jalan diakui per surat jalan
    # (`shipment_revenue`/`shipment_cogs`, source_id = id surat jalan); jalur lama
    # tanpa surat jalan memakai `sales_order`/`sales_cogs` per pesanan.
    ship_ids = [s["id"] for s in db.shipments.find({"order_id": ORDER}, {"_id": 0, "id": 1})]
    for stype, alt in (("sales_order", "shipment_revenue"), ("sales_cogs", "shipment_cogs")):
        je = list(db.journal_entries.find({"$or": [
            {"source_type": stype, "source_id": ORDER},
            {"source_type": alt, "source_id": {"$in": ship_ids}}]},
            {"_id": 0, "id": 1, "status": 1, "lines": 1}))
        assert je, f"no journal entry with source_type={stype}/{alt} for {ORDER} right after dispatch"
        assert any(j.get("status") == "posted" for j in je), f"{stype} JE not posted: {je}"
        print(stype, "JE ok:", [j["id"] for j in je])

    # API surface must expose it too (per surat jalan → source=shipment_revenue)
    r = requests.get(f"{BASE}/gl/journal", headers=hdr,
                     params={"source": "shipment_revenue" if ship_ids else "sales_order"}, timeout=60)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", data.get("entries", []))
    wanted = set(ship_ids) or {ORDER}
    assert any(i.get("source_id") in wanted for i in items), \
        f"GET /gl/journal does not include JE pendapatan {ORDER} (got {len(items)} rows)"

    # No Mongo ObjectId leakage in API payload
    assert all("_id" not in i.keys() for i in items)
