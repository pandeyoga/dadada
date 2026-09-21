"""Iteration 316: catalog family variants, R&D linkage, and security matrix checks."""
import os
import uuid
from typing import Dict, Any, Tuple

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
PASSWORD = "demo12345"


def _must_base_url() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not configured")
    return BASE_URL


@pytest.fixture(scope="session")
def api() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def login(api: requests.Session, email: str) -> str:
    base = _must_base_url()
    res = requests.post(f"{base}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert res.status_code == 200, f"login failed for {email}: {res.status_code} {res.text[:300]}"
    data = res.json()
    assert "token" in data and isinstance(data["token"], str) and data["token"]
    return data["token"]


def h(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def build_axes() -> list:
    return [
        {"key": "color", "label": "Warna", "options": [
            {"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"},
            {"code": "BLU", "label": "Biru", "value": "BLU", "hex": "#0000FF"},
        ]},
        {"key": "size", "label": "Ukuran", "options": [
            {"code": "S", "label": "Small", "value": "S"},
            {"code": "L", "label": "Large", "value": "L"},
        ]},
        {"key": "material", "label": "Material", "options": [
            {"code": "CTN", "label": "Cotton", "value": "CTN"},
            {"code": "LIN", "label": "Linen", "value": "LIN"},
        ]},
    ]


def create_template(api: requests.Session, token: str, prefix: str, axes=None) -> Dict[str, Any]:
    base = _must_base_url()
    payload = {
        "name": f"TEST_catalog_family_{prefix}",
        "category": "Kain",
        "fabric_type": "woven",
        "stage": "finished",
        "base_unit": "meter",
        "base_price": 12000,
        "gramasi": 120,
        "lebar": 1.2,
        "sku_prefix": f"T{prefix[-6:].upper()}",
        "axes": axes if axes is not None else build_axes(),
    }
    res = api.post(f"{base}/api/product-templates", json=payload, headers=h(token), timeout=40)
    assert res.status_code == 200, res.text[:300]
    return res.json()


def generate_variants(api: requests.Session, token: str, template_id: str) -> Dict[str, Any]:
    base = _must_base_url()
    res = api.post(
        f"{base}/api/product-templates/{template_id}/generate-variants",
        json={},
        headers=h(token),
        timeout=60,
    )
    assert res.status_code == 200, res.text[:400]
    return res.json()


@pytest.fixture(scope="module")
def auth(api: requests.Session) -> Dict[str, str]:
    return {
        "admin": login(api, "admin@kainnusantara.id"),
        "manager": login(api, "manager@kainnusantara.id"),
        "sales": login(api, "sales@kainnusantara.id"),
        "md": login(api, "md@kainnusantara.id"),
    }


# Catalog meta and auth/security gate checks
def test_meta_gemini_disabled(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    r = api.get(f"{base}/api/product-catalog/meta", headers=h(auth["admin"]), timeout=30)
    assert r.status_code == 200
    ai = r.json().get("ai", {})
    assert ai.get("configured") is False
    assert ai.get("enabled") is False


def test_anonymous_catalog_endpoints_denied(api: requests.Session):
    base = _must_base_url()
    r = requests.get(f"{base}/api/products", timeout=30)
    assert r.status_code in (401, 403)


# Family creation + generator/idempotency + duplicate prevention
def test_create_family_generate_8_and_readback(api: requests.Session, auth: Dict[str, str]):
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    assert len(t.get("axes", [])) == 3
    assert t["axes"][0]["options"][0]["hex"] == "#FF0000"

    gen = generate_variants(api, auth["admin"], t["id"])
    assert gen["created"] == 8
    assert gen["total_combinations"] == 8
    skus = [v["sku"] for v in gen["variants"]]
    keys = [v["variant_key"] for v in gen["variants"]]
    assert len(set(skus)) == 8
    assert len(set(keys)) == 8

    base = _must_base_url()
    detail = api.get(f"{base}/api/product-templates/{t['id']}", headers=h(auth["admin"]), timeout=30)
    assert detail.status_code == 200
    body = detail.json()
    assert body.get("variant_count") == 8
    assert len(body.get("variants", [])) == 8


def test_generate_idempotent_repeat_skips_existing(api: requests.Session, auth: Dict[str, str]):
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    first = generate_variants(api, auth["admin"], t["id"])
    second = generate_variants(api, auth["admin"], t["id"])
    assert first["created"] == 8
    assert second["created"] == 0
    assert second["skipped"] == 8


def test_duplicate_combination_with_other_sku_denied(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    gen = generate_variants(api, auth["admin"], t["id"])
    v1, v2 = gen["variants"][0], gen["variants"][1]
    payload = {
        "data": {
            "variant_attrs": v1["variant_attrs"],
            "variant_options": v1["variant_options"],
        }
    }
    r = api.patch(f"{base}/api/products/{v2['id']}", json=payload, headers=h(auth["admin"]), timeout=30)
    assert r.status_code == 409
    assert "Kombinasi" in r.text or "kombinasi" in r.text


# Validation and patch error code behavior
def test_invalid_axes_empty_option_and_duplicate_code_return_400(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    p1 = {
        "name": f"TEST_catalog_bad_{uuid.uuid4().hex[:6]}",
        "category": "Kain",
        "fabric_type": "woven",
        "stage": "finished",
        "axes": [{"key": "color", "label": "Warna", "options": []}],
    }
    r1 = api.post(f"{base}/api/product-templates", json=p1, headers=h(auth["admin"]), timeout=30)
    assert r1.status_code == 400

    p2 = {
        "name": f"TEST_catalog_baddup_{uuid.uuid4().hex[:6]}",
        "category": "Kain",
        "fabric_type": "woven",
        "stage": "finished",
        "axes": [{"key": "size", "label": "Ukuran", "options": [
            {"code": "DUP", "label": "S"}, {"code": "DUP", "label": "L"}
        ]}],
    }
    r2 = api.post(f"{base}/api/product-templates", json=p2, headers=h(auth["admin"]), timeout=30)
    assert r2.status_code == 400


def test_over_200_combinations_rejected_without_partial_writes(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    prefix = f"OVR{uuid.uuid4().hex[:4].upper()}"
    axes = []
    for key in ("color", "size", "material"):
        axes.append({
            "key": key,
            "label": key,
            "options": [{"code": f"{key[:1].upper()}{i}", "label": f"{key}-{i}"} for i in range(1, 7)],
        })
    t = create_template(api, auth["admin"], prefix, axes=axes)

    pre = api.get(f"{base}/api/products", headers=h(auth["admin"]), timeout=30).json()
    pre_count = len([p for p in pre if str(p.get("sku", "")).startswith(t["sku_prefix"])])
    res = api.post(f"{base}/api/product-templates/{t['id']}/generate-variants", json={}, headers=h(auth["admin"]), timeout=40)
    assert res.status_code == 400
    post = api.get(f"{base}/api/products", headers=h(auth["admin"]), timeout=30).json()
    post_count = len([p for p in post if str(p.get("sku", "")).startswith(t["sku_prefix"])])
    assert post_count == pre_count


def test_patch_nan_or_inf_returns_400_not_500(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    gen = generate_variants(api, auth["admin"], t["id"])
    target = gen["variants"][0]
    payload = {"data": {"price": "NaN"}}
    r = api.patch(f"{base}/api/products/{target['id']}", json=payload, headers=h(auth["admin"]), timeout=30)
    assert r.status_code == 400


# R&D family linkage + cm->meter + idempotent approve
def test_rnd_spec_approve_links_template_and_cm_to_meter(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    spec_payload = {
        "title": f"TEST_catalog_spec_{uuid.uuid4().hex[:6]}",
        "category": "Kain",
        "base_unit": "meter",
        "template_id": t["id"],
        "variant_attrs": {"color": "Merah", "size": "Small", "material": "Cotton"},
        "variant_options": {"color": "RED", "size": "S", "material": "CTN"},
        "sample_type_hint": "labdip",
        "target": {"stage": "finished", "fabric_type": "woven", "gramasi": 130, "lebar": 150, "grade": "A"},
        "notes": "TEST",
    }
    c = api.post(f"{base}/api/rnd/specs", json=spec_payload, headers=h(auth["admin"]), timeout=40)
    assert c.status_code == 200, c.text[:300]
    spec = c.json()
    sid = spec["id"]

    s = api.post(f"{base}/api/rnd/specs/{sid}/submit", json={}, headers=h(auth["admin"]), timeout=30)
    assert s.status_code == 200

    approve_payload = {"sku": f"TEST_RND_{uuid.uuid4().hex[:6].upper()}", "name": "TEST RND Product", "price": 15000, "note": "ok"}
    a1 = api.post(f"{base}/api/rnd/specs/{sid}/approve", json=approve_payload, headers=h(auth["manager"]), timeout=50)
    assert a1.status_code == 200, a1.text[:400]
    body1 = a1.json()
    product = body1["product"]
    assert body1["spec"]["status"] == "approved"
    assert body1["spec"]["lifecycle"] == "disetujui"
    assert product["template_id"] == t["id"]
    assert product["variant_options"]["material"] == "CTN"
    assert abs(float(product.get("lebar") or 0) - 1.5) < 0.0001

    a2 = api.post(f"{base}/api/rnd/specs/{sid}/approve", json=approve_payload, headers=h(auth["manager"]), timeout=30)
    assert a2.status_code == 200
    assert a2.json()["product"]["id"] == product["id"]


def test_rnd_target_product_id_rejects_released_sku(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])

    # create + approve + release one product first
    sp = {
        "title": f"TEST_catalog_spec_release_{uuid.uuid4().hex[:6]}",
        "category": "Kain",
        "base_unit": "meter",
        "template_id": t["id"],
        "variant_attrs": {"color": "Merah", "size": "Small", "material": "Cotton"},
        "variant_options": {"color": "RED", "size": "S", "material": "CTN"},
        "sample_type_hint": "labdip",
        "target": {"stage": "finished", "fabric_type": "woven", "gramasi": 120, "lebar": 150, "grade": "A"},
    }
    c = api.post(f"{base}/api/rnd/specs", json=sp, headers=h(auth["admin"]), timeout=40)
    assert c.status_code == 200
    sid = c.json()["id"]
    assert api.post(f"{base}/api/rnd/specs/{sid}/submit", json={}, headers=h(auth["admin"]), timeout=30).status_code == 200
    ap = api.post(
        f"{base}/api/rnd/specs/{sid}/approve",
        json={"sku": f"TEST_REL_{uuid.uuid4().hex[:6].upper()}", "name": "REL", "price": 10000},
        headers=h(auth["manager"]),
        timeout=40,
    )
    assert ap.status_code == 200
    product_id = ap.json()["product"]["id"]
    rel = api.post(f"{base}/api/rnd/specs/{sid}/release-product", json={"reason": "oke"}, headers=h(auth["manager"]), timeout=40)
    assert rel.status_code == 200

    # reusing released SKU as target product must fail
    sp2 = {
        "title": f"TEST_catalog_spec_reuse_{uuid.uuid4().hex[:6]}",
        "category": "Kain",
        "base_unit": "meter",
        "template_id": t["id"],
        "target_product_id": product_id,
        "variant_attrs": {"color": "Merah", "size": "Small", "material": "Cotton"},
        "variant_options": {"color": "RED", "size": "S", "material": "CTN"},
        "sample_type_hint": "labdip",
        "target": {"stage": "finished", "fabric_type": "woven", "gramasi": 120, "lebar": 150, "grade": "A"},
    }
    c2 = api.post(f"{base}/api/rnd/specs", json=sp2, headers=h(auth["admin"]), timeout=40)
    assert c2.status_code == 409


# RBAC/sanitization checks
def test_md_role_can_create_template_not_admin_only(api: requests.Session, auth: Dict[str, str]):
    t = create_template(api, auth["md"], uuid.uuid4().hex[:8])
    assert t["id"].startswith("ptpl_")


def test_sales_cannot_mutate_and_cost_fields_hidden(api: requests.Session, auth: Dict[str, str]):
    base = _must_base_url()
    t = create_template(api, auth["admin"], uuid.uuid4().hex[:8])
    gen = generate_variants(api, auth["admin"], t["id"])
    variant = gen["variants"][0]

    patch = api.patch(
        f"{base}/api/products/{variant['id']}",
        json={"data": {"name": "FORBIDDEN_UPDATE"}},
        headers=h(auth["sales"]),
        timeout=30,
    )
    assert patch.status_code == 403

    tpl_list = api.get(f"{base}/api/product-templates", headers=h(auth["sales"]), timeout=30)
    assert tpl_list.status_code == 200
    items = tpl_list.json() if isinstance(tpl_list.json(), list) else tpl_list.json().get("items", [])
    if items:
        sample = items[0]
        assert "harga_pokok" not in sample
        if sample.get("cover_product"):
            assert "harga_pokok" not in sample["cover_product"]

    detail = api.get(f"{base}/api/product-templates/{t['id']}", headers=h(auth["sales"]), timeout=30)
    assert detail.status_code == 200
    body = detail.json()
    for v in body.get("variants", []):
        assert "harga_pokok" not in v
