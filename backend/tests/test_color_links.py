"""Tests for color library supplier-variants & links endpoints (iter 42)."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://kn-workflow-system.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"},
                      timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_supplier_variants_contains_target_row(headers):
    r = requests.get(f"{BASE_URL}/api/color-library/supplier-variants",
                     headers=headers, params={"entity_id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list) and len(data) > 0
    match = [
        row for row in data
        if row.get("color_id") == "col_kn_blu_01" and row.get("supplier_id") == "sup_a05908473e52"
    ]
    assert match, f"Target row not found. Sample keys: {list(data[0].keys()) if data else 'empty'}"
    row = match[0]
    assert row.get("supplier_name") == "Palembang Silk House"
    assert row.get("supplier_color_name") == "Navy 07"
    assert row.get("supplier_color_code") == "NV-07"
    assert row.get("color_code") == "KN-BLU-01"
    assert row.get("hex")
    assert row.get("sample_number")
    assert isinstance(row.get("products", []), list)
    assert row.get("color_products_count", 0) >= 3


def test_color_links_returns_full_structure(headers):
    r = requests.get(f"{BASE_URL}/api/color-library/col_kn_blu_01/links",
                     headers=headers, params={"entity_id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("color", {}).get("code") == "KN-BLU-01"
    sv = body.get("supplier_variants") or []
    assert len(sv) >= 1
    with_products = [v for v in sv if v.get("products")]
    assert with_products, "Expected at least one supplier_variant with products"
    products = body.get("products") or []
    assert len(products) >= 3
    for p in products:
        assert p.get("sku")
        assert p.get("lifecycle") is not None
        assert p.get("spec_number")
    samples = body.get("samples") or []
    assert len(samples) >= 3


def test_color_links_404(headers):
    r = requests.get(f"{BASE_URL}/api/color-library/tidak-ada/links",
                     headers=headers, params={"entity_id": "ent_ksc"}, timeout=30)
    assert r.status_code == 404
