"""Iter 44: two-color (internal + supplier) sync on product master.

Verifies:
1. Existing TST-TWL-NVY-01 product has color_ref (KN-BLU-01), supplier_colors entry
   for sup_a05908473e52 (Palembang Silk House / Navy 07 / NV-07), and rnd_supplier
   with contract_number containing 'SCT'.
2. Regression: new labdip sample decide flow (manager) → sync_product_colors created
   product with color_ref KN-BLU-01, supplier_colors containing the deciding
   supplier group id with supplier_color_name 'Merah 12', and rnd_supplier.id equal
   to that supplier group id.
"""
import os
import io
import time
import uuid
import requests
import pytest

def _base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL"):
                v = line.split("=", 1)[1].strip()
                break
    return v.rstrip("/")

BASE = _base()
ENT = "ent_ksc"


def _login(email: str, password: str = "demo12345") -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"] if "access_token" in r.json() else r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    tok = _login("admin@kainnusantara.id")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT}


@pytest.fixture(scope="module")
def manager_headers():
    tok = _login("manager@kainnusantara.id")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT}


# ---- 1. Existing product verification ----------------------------------------------
def test_existing_product_two_color(admin_headers):
    r = requests.get(f"{BASE}/api/products", headers=admin_headers, params={"entity_id": ENT}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    prod = next((p for p in items if p.get("sku") == "TST-TWL-NVY-01"), None)
    assert prod is not None, "TST-TWL-NVY-01 not found in /api/products"

    color_ref = prod.get("color_ref") or {}
    assert color_ref.get("code") == "KN-BLU-01", f"color_ref.code={color_ref}"
    assert color_ref.get("name") == "Biru Indigo", f"color_ref.name={color_ref}"
    assert color_ref.get("hex"), f"missing hex in color_ref: {color_ref}"

    sup_colors = prod.get("supplier_colors") or []
    assert len(sup_colors) >= 1, f"supplier_colors empty: {sup_colors}"
    sc0 = next((s for s in sup_colors if s.get("supplier_id") == "sup_a05908473e52"), None)
    assert sc0 is not None, f"no supplier_colors entry for sup_a05908473e52: {sup_colors}"
    assert sc0.get("supplier_name") == "Palembang Silk House"
    assert sc0.get("supplier_color_name") == "Navy 07"
    assert sc0.get("supplier_color_code") == "NV-07"

    rnd_sup = prod.get("rnd_supplier") or {}
    assert rnd_sup.get("name") == "Palembang Silk House", f"rnd_supplier={rnd_sup}"
    assert "SCT" in (rnd_sup.get("contract_number") or ""), f"contract_number missing SCT: {rnd_sup}"


# ---- 2. Regression: create sample → send → submit → assess → decide -----------------
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000"
    "000d4944415478da63f8ffff3f0300050001019cd7b3f30000000049454e44ae426082"
)


def test_decide_syncs_two_color_to_new_product(admin_headers, manager_headers):
    uniq = uuid.uuid4().hex[:6].upper()
    sku = f"TST-2C-{uniq}"
    sup_group_id = "sup_grp_ksc_527ac628fd3b"

    # Create labdip sample
    spec = {
        "title": f"Labdip 2C {uniq}",
        "base_unit": "meter",
        "sku_hint": sku,
        "sample_type_hint": "labdip",
        "target": {"fabric_type": "woven", "gramasi": 200, "lebar": 150},
        "color_target": {"color_id": "col_kn_blu_01"},
    }
    payload = {
        "sample_types": ["labdip"],
        "title": f"Labdip 2C {uniq}",
        "brief": "regresi dua warna",
        "color_target": {"color_id": "col_kn_blu_01"},
        "qty_requested": 1,
        "unit": "meter",
        "spec": spec,
    }
    r = requests.post(f"{BASE}/api/rnd/samples", headers={**admin_headers, "Content-Type": "application/json"}, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    smp = r.json()
    sid = smp["id"]

    # Send to supplier group
    r = requests.post(
        f"{BASE}/api/rnd/samples/{sid}/send",
        headers={**admin_headers, "Content-Type": "application/json"},
        json={"supplier_ids": [sup_group_id], "type_codes": ["labdip"], "note": "uji"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    smp = r.json()
    round_id = smp["rounds"][0]["id"]

    # Upload PNG
    r = requests.post(
        f"{BASE}/api/rnd/samples/{sid}/rounds/{round_id}/attachments",
        headers=admin_headers,
        files={"file": ("swatch.png", PNG_1x1, "image/png")},
        timeout=30,
    )
    assert r.status_code == 200, r.text

    # Get measurement fields
    meta = requests.get(f"{BASE}/api/rnd/meta", headers=admin_headers, params={"entity_id": ENT}, timeout=30).json()
    fields = next((t.get("measurement_fields", []) for t in meta.get("sample_types", []) if t["value"] == "labdip"), [])
    meas = {f: 1 for f in fields}

    # Submit
    r = requests.post(
        f"{BASE}/api/rnd/samples/{sid}/rounds/{round_id}/submit",
        headers={**admin_headers, "Content-Type": "application/json"},
        json={"note": "ok", "measurements": meas, "cost": 50000},
        timeout=30,
    )
    assert r.status_code == 200, r.text

    # Assess acc 88
    r = requests.post(
        f"{BASE}/api/rnd/samples/{sid}/rounds/{round_id}/assess",
        headers={**admin_headers, "Content-Type": "application/json"},
        json={"result": "acc", "score": 88, "note": "ACC uji"},
        timeout=30,
    )
    assert r.status_code == 200, r.text

    # Decide by MANAGER
    reason = meta["reasons"][0]["value"]
    r = requests.post(
        f"{BASE}/api/rnd/samples/{sid}/decide",
        headers={**manager_headers, "Content-Type": "application/json"},
        json={
            "supplier_id": sup_group_id,
            "reason_code": reason,
            "price": 42500,
            "supplier_color_name": "Merah 12",
            "supplier_color_code": "MR-12",
            "approve_spec": True,
            "product_sku": sku,
            "product_name": f"Katun 2C Test {uniq}",
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    dec = r.json().get("decision") or {}
    assert dec.get("color_synced") is True or dec.get("product_sku") == sku, f"decision={dec}"

    # Give backend a moment
    time.sleep(1)

    # Fetch products, find sku
    r = requests.get(f"{BASE}/api/products", headers=admin_headers, params={"entity_id": ENT}, timeout=30)
    assert r.status_code == 200
    items = r.json()
    items = items if isinstance(items, list) else items.get("items", [])
    prod = next((p for p in items if p.get("sku") == sku), None)
    assert prod is not None, f"Product {sku} not in /api/products after decide"

    color_ref = prod.get("color_ref") or {}
    assert color_ref.get("code") == "KN-BLU-01", f"color_ref={color_ref}"

    sup_colors = prod.get("supplier_colors") or []
    sc = next((s for s in sup_colors if s.get("supplier_id") == sup_group_id), None)
    assert sc is not None, f"supplier_colors missing {sup_group_id}: {sup_colors}"
    assert sc.get("supplier_color_name") == "Merah 12", f"supplier_color_name mismatch: {sc}"
    assert sc.get("supplier_color_code") == "MR-12", f"supplier_color_code mismatch: {sc}"

    rnd_sup = prod.get("rnd_supplier") or {}
    assert rnd_sup.get("id") == sup_group_id, f"rnd_supplier.id != {sup_group_id}: {rnd_sup}"
