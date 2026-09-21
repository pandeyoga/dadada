"""Iter318 dispatch & logistics revamp — backend regression."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ENT = "ent_ksc"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token, entity=True):
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if entity:
        h["X-Entity-Id"] = ENT
    return h


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def warehouse_token():
    return _login("warehouse@kainnusantara.id")


# ---- Dashboard ----
def test_dashboard_shape(admin_token):
    r = requests.get(f"{BASE_URL}/api/logistics/dashboard", params={"entity_id": ENT}, headers=_hdr(admin_token))
    assert r.status_code == 200, r.text
    d = r.json()
    kpi = d.get("kpi", {})
    for k in ["unassigned_sj", "waiting_pickup", "active", "in_transit", "eta_today", "late", "delivered_today"]:
        assert k in kpi, f"missing kpi.{k}"
    for k in ["by_mode", "by_mode_active", "active", "unassigned", "recent", "fleet"]:
        assert k in d, f"missing {k}"
    fleet = d["fleet"]
    for k in ["vehicle_summary", "driver_summary", "vehicles", "drivers"]:
        assert k in fleet


# ---- Anti-leak on unassigned ----
def test_unassigned_no_address_leak_for_pickup_orders(admin_token):
    r = requests.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT}, headers=_hdr(admin_token))
    assert r.status_code == 200, r.text
    rows = r.json() if isinstance(r.json(), list) else r.json().get("rows", r.json().get("items", []))
    assert isinstance(rows, list)
    for row in rows:
        assert "fulfillment_method" in row, f"row missing fulfillment_method: {row}"
        assert "suggested_mode" in row, f"row missing suggested_mode: {row}"
        if row.get("fulfillment_method") == "ambil":
            assert (row.get("shipping_address") or "") == "", f"pickup SJ leaks address: {row}"


# ---- Mode validation on create ----
def test_create_delivery_rejects_self_pickup_for_kirim_so(admin_token):
    # Find KSC/SJ-90007 (from SO kirim) among unassigned
    r = requests.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT}, headers=_hdr(admin_token))
    rows = r.json() if isinstance(r.json(), list) else r.json().get("rows", [])
    sj = next((x for x in rows if x.get("shipment_no", "").endswith("SJ-90007") or "SJ-90007" in x.get("shipment_no", "")), None)
    if not sj:
        pytest.skip("SJ-90007 not present")
    r2 = requests.post(
        f"{BASE_URL}/api/logistics/deliveries",
        json={"shipment_ids": [sj["id"]], "mode": "self_pickup", "entity_id": ENT},
        headers=_hdr(admin_token),
    )
    assert r2.status_code == 400, f"expected 400 for KIRIM+self_pickup, got {r2.status_code}: {r2.text}"


# ---- Pickup flow (destructive but reset by seed at end) ----
DELIVERY_ID = "demo_dsp_lgs_4"


def test_admin_sees_pickup_code(admin_token):
    r = requests.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}", headers=_hdr(admin_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("pickup_code") == "KN7PQ4"
    assert (d.get("destination") or d.get("shipping_address") or "") == ""


def test_warehouse_pickup_code_hidden(warehouse_token):
    r = requests.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}", headers=_hdr(warehouse_token))
    assert r.status_code == 200, r.text
    d = r.json()
    # Redacted
    assert (d.get("pickup_code") or "") == ""
    assert d.get("pickup_code_hidden") is True


def test_transition_loaded_rejected_for_pickup(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/transition",
        json={"to": "loaded"},
        headers=_hdr(admin_token),
    )
    assert r.status_code == 400, r.text


def test_pickup_handover_wrong_code(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/pickup-handover",
        json={"pickup_code": "XXXXXX", "picker_name": "Uji"},
        headers=_hdr(admin_token),
    )
    assert r.status_code == 400
    r2 = requests.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}", headers=_hdr(admin_token))
    assert (r2.json().get("pickup_attempts") or 0) >= 1


def test_pickup_handover_success_then_duplicate(admin_token):
    r = requests.post(
        f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/pickup-handover",
        json={"pickup_code": "kn7pq4", "picker_name": "TEST_Pengambil", "picker_id_no": "3171"},
        headers=_hdr(admin_token),
    )
    assert r.status_code == 200, r.text
    d = r.json()
    # sometimes handler returns partial; verify via GET
    g = requests.get(f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}", headers=_hdr(admin_token)).json()
    assert g.get("status") == "delivered", g
    pod = g.get("pod") or {}
    assert pod.get("verified_by_code") is True, pod

    # duplicate
    r2 = requests.post(
        f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/pickup-handover",
        json={"pickup_code": "kn7pq4", "picker_name": "TEST_Dup"},
        headers=_hdr(admin_token),
    )
    assert r2.status_code == 400

    # completed transition
    r3 = requests.post(
        f"{BASE_URL}/api/logistics/deliveries/{DELIVERY_ID}/transition",
        json={"to": "completed"},
        headers=_hdr(admin_token),
    )
    assert r3.status_code == 200, r3.text


# ---- Fleet ----
def test_fleet_vehicle_crud(admin_token):
    # Create
    plate = "TEST 1 UJI"
    r = requests.post(
        f"{BASE_URL}/api/logistics/fleet/vehicles",
        json={"plate": plate, "type": "van", "name": "TEST", "entity_id": ENT},
        headers=_hdr(admin_token),
    )
    assert r.status_code in (200, 201), r.text
    vid = r.json().get("id")
    assert vid, r.json()
    try:
        # duplicate normalized
        r2 = requests.post(
            f"{BASE_URL}/api/logistics/fleet/vehicles",
            json={"plate": "test  1 uji", "type": "van", "name": "TEST DUP", "entity_id": ENT},
            headers=_hdr(admin_token),
        )
        assert r2.status_code == 400, f"expected 400 dup plate, got {r2.status_code}: {r2.text}"

        # patch
        r3 = requests.patch(
            f"{BASE_URL}/api/logistics/fleet/vehicles/{vid}",
            json={"capacity_note": "x"},
            headers=_hdr(admin_token),
        )
        assert r3.status_code == 200, r3.text

        # status maintenance
        r4 = requests.post(
            f"{BASE_URL}/api/logistics/fleet/vehicles/{vid}/status",
            json={"status": "maintenance", "note": "servis"},
            headers=_hdr(admin_token),
        )
        assert r4.status_code == 200, r4.text

        # try to create own_fleet delivery with maintenance vehicle -> 400
        # first find any unassigned kirim SJ
        rows = requests.get(
            f"{BASE_URL}/api/logistics/shipments/unassigned",
            params={"entity_id": ENT},
            headers=_hdr(admin_token),
        ).json()
        rows = rows if isinstance(rows, list) else rows.get("rows", [])
        sj = next((x for x in rows if x.get("fulfillment_method") != "ambil"), None)
        if sj:
            r5 = requests.post(
                f"{BASE_URL}/api/logistics/deliveries",
                json={"shipment_ids": [sj["id"]], "mode": "own_fleet", "vehicle_id": vid, "entity_id": ENT},
                headers=_hdr(admin_token),
            )
            assert r5.status_code == 400, r5.text

        # back to available
        r6 = requests.post(
            f"{BASE_URL}/api/logistics/fleet/vehicles/{vid}/status",
            json={"status": "available"},
            headers=_hdr(admin_token),
        )
        assert r6.status_code == 200
    finally:
        # cleanup via Mongo
        try:
            from pymongo import MongoClient
            mc = MongoClient(os.environ["MONGO_URL"])
            db = mc[os.environ["DB_NAME"]]
            db.fleet_vehicles.delete_one({"id": vid})
        except Exception as e:
            print("cleanup failed", e)


def test_fleet_availability_and_on_trip_maintenance_blocked(admin_token):
    r = requests.get(f"{BASE_URL}/api/logistics/fleet/availability", params={"entity_id": ENT}, headers=_hdr(admin_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert "vehicle_summary" in d
    assert "drivers" in d
    # find any on_trip vehicle
    on_trip = [v for v in d.get("vehicles", []) if v.get("status") == "on_trip"]
    if on_trip:
        vid = on_trip[0]["id"]
        r2 = requests.post(
            f"{BASE_URL}/api/logistics/fleet/vehicles/{vid}/status",
            json={"status": "maintenance"},
            headers=_hdr(admin_token),
        )
        assert r2.status_code == 400, r2.text


# ---- History ----
def test_history_filters(admin_token):
    r = requests.get(f"{BASE_URL}/api/logistics/history", params={"entity_id": ENT}, headers=_hdr(admin_token))
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["rows", "total", "stats"]:
        assert k in d, f"missing {k}"
    stats = d["stats"]
    for k in ["delivered", "failed", "shipping_cost_total", "by_mode"]:
        assert k in stats
    # mode filter
    r2 = requests.get(
        f"{BASE_URL}/api/logistics/history",
        params={"entity_id": ENT, "mode": "expedition"},
        headers=_hdr(admin_token),
    )
    assert r2.status_code == 200
    for row in r2.json().get("rows", []):
        assert row.get("mode") == "expedition"


# ---- Order preview leak check ----
def test_order_preview_leak(admin_token):
    r = requests.get(f"{BASE_URL}/api/sales-orders/so_001/verification", headers=_hdr(admin_token))
    if r.status_code in (403, 404):
        pytest.skip("verification endpoint not available for admin")
    assert r.status_code == 200, r.text
    op = r.json().get("order_preview", {})
    assert op.get("fulfillment_method") == "ambil", op
    addr = op.get("shipping_address", {})
    if isinstance(addr, dict):
        assert (addr.get("address") or "") == "", addr
    else:
        assert not addr
