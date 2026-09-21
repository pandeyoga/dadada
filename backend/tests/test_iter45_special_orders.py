"""Iter 45 — Special Order Fase 1: intake terstruktur + routing otomatis + referensi."""
import io
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ENTITY = "ent_ksc"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login('admin@kainnusantara.id')}",
            "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def manager_headers():
    return {"Authorization": f"Bearer {_login('manager@kainnusantara.id')}",
            "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def customer_id(admin_headers):
    r = requests.get(f"{BASE_URL}/api/customers?entity_id={ENTITY}",
                     headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        items = body.get("items") or body.get("customers") or []
    else:
        items = []
    assert items, "No customers"
    return items[0]["id"]


def _tiny_png():
    # 1x1 transparent PNG
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )


def _create_od(headers, customer_id, request_types, detail_level="full", spec_extra=None):
    uniq = uuid.uuid4().hex[:8]
    spec = {"fabric_type": "woven", "gramasi": 200, "lebar": 150,
            "color_id": "col_kn_blu_01", "sku_hint": f"ODT-{uniq}"}
    if spec_extra is not None:
        spec = spec_extra
    body = {
        "customer_id": customer_id,
        "entity_id": ENTITY,
        "title": f"Uji OD {request_types[0]} {uniq}",
        "request_types": request_types,
        "detail_level": detail_level,
        "reference_notes": "swatch fisik",
        "spec": spec,
        "custom_item": {"description": "Uji OD", "specifications": {},
                        "quantity": 300, "unit": "meter",
                        "target_price": 45000, "notes": ""},
        "expected_delivery": "2026-12-01", "notes": "",
        "submit_for_approval": True,
    }
    r = requests.post(f"{BASE_URL}/api/special-orders", json=body,
                      headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ── Test 1: create OD labdip ────────────────────────────────────────────────
def test_create_od_labdip(admin_headers, customer_id):
    od = _create_od(admin_headers, customer_id, ["labdip"])
    assert od["status"] == "pending_approval"
    assert od["request_types"] == ["labdip"]
    assert od["spec"]["gramasi"] == 200
    pytest.od_labdip = od  # stash


# ── Test 2: upload + fetch reference ────────────────────────────────────────
def test_od_reference_upload_and_fetch(admin_headers):
    od = pytest.od_labdip
    files = {"file": ("swatch.png", _tiny_png(), "image/png")}
    r = requests.post(f"{BASE_URL}/api/special-orders/{od['id']}/references",
                      files=files, data={"caption": "swatch"},
                      headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    meta = r.json()
    assert meta["id"].startswith("odref_"), meta
    fid = meta["id"]
    r2 = requests.get(f"{BASE_URL}/api/special-orders/{od['id']}/references/{fid}",
                      headers=admin_headers, timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("image/png")


# ── Test 3: approve labdip → sample created, no design ─────────────────────
def test_approve_labdip_routes_to_sample(manager_headers, admin_headers):
    od = pytest.od_labdip
    r = requests.post(f"{BASE_URL}/api/special-orders/{od['id']}/approve",
                      json={"notes": "ok"}, headers=manager_headers, timeout=60)
    assert r.status_code == 200, r.text
    time.sleep(0.5)
    detail = requests.get(f"{BASE_URL}/api/special-orders/{od['id']}",
                          headers=admin_headers, timeout=30).json()
    sample_ids = detail.get("sample_ids") or []
    sample_numbers = detail.get("sample_numbers") or []
    assert len(sample_ids) == 1, detail
    assert sample_numbers and sample_numbers[0].startswith("KSC/SMP-"), sample_numbers
    assert not detail.get("routing_errors"), detail.get("routing_errors")
    chain = detail["chain"]
    assert chain["samples"], chain
    assert chain["samples"][0]["status"] == "draft"
    assert chain["phase"] == "sampling"
    phase_codes = [p[0] if isinstance(p, list) else p for p in chain["phases"]]
    assert "design" not in phase_codes, phase_codes
    # verify sample doc
    sid = sample_ids[0]
    smp = requests.get(f"{BASE_URL}/api/rnd/samples/{sid}",
                       headers=admin_headers, timeout=30).json()
    assert smp["special_order_id"] == od["id"]
    assert smp["spec"]["target"]["gramasi"] == 200
    assert smp["spec"]["color_target"]["color_id"] == "col_kn_blu_01"


# ── Test 4: printing OD → design_request created with references ───────────
def test_create_od_printing_routes_to_design(admin_headers, manager_headers, customer_id):
    # spec without gramasi for reference-level detail
    spec = {"fabric_type": "", "gramasi": None, "lebar": None,
            "color_id": "col_kn_blu_01", "sku_hint": ""}
    od = _create_od(admin_headers, customer_id, ["printing"],
                    detail_level="reference", spec_extra=spec)
    # upload one reference
    files = {"file": ("ref.png", _tiny_png(), "image/png")}
    r = requests.post(f"{BASE_URL}/api/special-orders/{od['id']}/references",
                      files=files, data={"caption": "ref"},
                      headers=admin_headers, timeout=30)
    assert r.status_code == 200

    r = requests.post(f"{BASE_URL}/api/special-orders/{od['id']}/approve",
                      json={"notes": "ok"}, headers=manager_headers, timeout=60)
    assert r.status_code == 200, r.text
    time.sleep(0.5)
    detail = requests.get(f"{BASE_URL}/api/special-orders/{od['id']}",
                          headers=admin_headers, timeout=30).json()
    drid = detail.get("design_request_id")
    assert drid, detail
    dr = requests.get(f"{BASE_URL}/api/design-requests/{drid}",
                      headers=admin_headers, timeout=30).json()
    assert dr.get("special_order_id") == od["id"]
    assert dr.get("source") == "customer"
    # references list only asserted if endpoint returns them
    if "references" in dr:
        refs = dr.get("references") or []
        assert len(refs) >= 1, dr
    chain = detail["chain"]
    assert chain["phase"] == "design"
    phase_codes = [p[0] if isinstance(p, list) else p for p in chain["phases"]]
    assert "design" in phase_codes
    pytest.od_printing = od


# ── Test 5: re-route idempotent; route on pending_approval → 400 ───────────
def test_reroute_idempotent(admin_headers, manager_headers):
    od = pytest.od_labdip
    r = requests.post(f"{BASE_URL}/api/special-orders/{od['id']}/route",
                      headers=manager_headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body.get("sample_ids") or []) == 1

    # Create a new pending od → route should 400
    uniq = uuid.uuid4().hex[:8]
    r2 = requests.post(f"{BASE_URL}/api/special-orders", json={
        "customer_id": od["customer_id"], "entity_id": ENTITY,
        "title": f"Pending OD {uniq}", "request_types": ["labdip"],
        "detail_level": "reference", "reference_notes": "",
        "spec": {"color_id": "col_kn_blu_01"},
        "custom_item": {"description": "x", "specifications": {}, "quantity": 300,
                        "unit": "meter", "target_price": 45000, "notes": ""},
        "expected_delivery": "2026-12-01", "notes": "", "submit_for_approval": True,
    }, headers=admin_headers, timeout=30).json()
    r3 = requests.post(f"{BASE_URL}/api/special-orders/{r2['id']}/route",
                       headers=manager_headers, timeout=30)
    assert r3.status_code == 400, r3.text
