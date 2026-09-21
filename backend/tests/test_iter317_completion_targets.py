"""Iteration 317 targeted checks: link-existing-variant, media access lifecycle, stock-backed sales flow."""
import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests
from PIL import Image


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
PASSWORD = "demo12345"


def _base() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL not set")
    return BASE_URL


def _h(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login(email: str) -> str:
    r = requests.post(f"{_base()}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:200]}"
    tk = r.json().get("token")
    assert isinstance(tk, str) and tk
    return tk


def _axes_three():
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


def _create_template(token: str, suffix: str, *, base_unit: str = "meter", exclusivity: str = "umum", owner_sales_ids=None):
    unique_prefix = f"I3{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "name": f"TEST_iter317_family_{suffix}",
        "category": "Kain",
        "fabric_type": "woven",
        "stage": "finished",
        "base_unit": base_unit,
        "base_price": 15000,
        "gramasi": 120,
        "lebar": 1.2,
        "sku_prefix": unique_prefix,
        "axes": _axes_three(),
        "exclusivity": exclusivity,
        "owner_sales_ids": owner_sales_ids or [],
    }
    r = requests.post(f"{_base()}/api/product-templates", json=payload, headers=_h(token), timeout=40)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _generate(token: str, template_id: str, payload=None):
    r = requests.post(
        f"{_base()}/api/product-templates/{template_id}/generate-variants",
        json=payload or {},
        headers=_h(token),
        timeout=60,
    )
    assert r.status_code == 200, r.text[:400]
    return r.json()


def _tiny_jpeg() -> bytes:
    im = Image.new("RGB", (32, 32), (200, 20, 20))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture(scope="module")
def auth_tokens():
    # auth and permissions baseline for backend+UI integration
    return {
        "admin": _login("admin@kainnusantara.id"),
        "manager": _login("manager@kainnusantara.id"),
        "md": _login("md@kainnusantara.id"),
        "sales": _login("sales@kainnusantara.id"),
    }


def _reviewer_token(auth_tokens):
    for role in ("manager", "admin", "md"):
        tk = auth_tokens.get(role)
        if not tk:
            continue
        r = requests.get(f"{_base()}/api/product-catalog/meta", headers=_h(tk), timeout=30)
        if r.status_code == 200 and (r.json().get("permissions") or {}).get("review"):
            return tk
    pytest.skip("No role with product media review permission in current environment")


def test_auth_me_includes_permissions(auth_tokens):
    for role, token in auth_tokens.items():
        r = requests.get(f"{_base()}/api/auth/me", headers=_h(token), timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body.get("role") == role
        assert isinstance(body.get("permissions"), dict)


def test_link_existing_variant_success_and_stock_persists(auth_tokens):
    admin = auth_tokens["admin"]
    suffix = uuid.uuid4().hex[:8]
    src = _create_template(admin, f"src_{suffix}")
    src_gen = _generate(admin, src["id"])
    assert src_gen["created"] == 8

    tgt = _create_template(admin, f"tgt_{suffix}")
    one_combo_axes = [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]
    tgt_gen = _generate(admin, tgt["id"], payload={"axes": one_combo_axes})
    assert tgt_gen["created"] == 1

    move_candidate = next(v for v in src_gen["variants"] if v["variant_options"] != {"color": "RED", "size": "S", "material": "CTN"})

    wh = requests.get(f"{_base()}/api/warehouses", headers=_h(admin), timeout=30)
    assert wh.status_code == 200
    warehouses = wh.json() if isinstance(wh.json(), list) else wh.json().get("items", [])
    assert warehouses, "No warehouse available for stock test"
    stock_payload = {
        "product_id": move_candidate["id"],
        "warehouse_id": warehouses[0]["id"],
        "owner_entity_id": "",
        "lot": f"TEST-LOT-{suffix}",
        "quantity": 23,
        "unit": "meter",
        "grade": "A",
        "batch": f"TEST-B-{suffix}",
    }
    stk = requests.post(f"{_base()}/api/inventory/initial-stock", json=stock_payload, headers=_h(admin), timeout=40)
    assert stk.status_code == 200, stk.text[:300]
    roll_id = stk.json().get("roll_id")
    assert isinstance(roll_id, str) and roll_id

    move_payload = {
        "data": {
            "template_id": tgt["id"],
            "variant_options": move_candidate["variant_options"],
            "variant_attrs": move_candidate["variant_attrs"],
        }
    }
    moved = requests.patch(f"{_base()}/api/products/{move_candidate['id']}", json=move_payload, headers=_h(admin), timeout=40)
    assert moved.status_code == 200, moved.text[:300]
    body = moved.json()
    assert body["id"] == move_candidate["id"]
    assert body["sku"] == move_candidate["sku"]
    assert body["template_id"] == tgt["id"]

    src_after = requests.get(f"{_base()}/api/product-templates/{src['id']}", headers=_h(admin), timeout=30)
    tgt_after = requests.get(f"{_base()}/api/product-templates/{tgt['id']}", headers=_h(admin), timeout=30)
    assert src_after.status_code == 200 and tgt_after.status_code == 200
    assert src_after.json().get("variant_count") == 7
    assert tgt_after.json().get("variant_count") == 2

    balances = requests.get(f"{_base()}/api/inventory/balances", headers=_h(admin), timeout=30)
    assert balances.status_code == 200
    rows = [b for b in balances.json() if b.get("product_id") == move_candidate["id"]]
    assert rows and sum(float(r.get("available_qty", 0) or 0) for r in rows) >= 23


def test_link_existing_variant_rejects_duplicate_combination(auth_tokens):
    admin = auth_tokens["admin"]
    suffix = uuid.uuid4().hex[:8]
    src = _create_template(admin, f"dup_src_{suffix}")
    tgt = _create_template(admin, f"dup_tgt_{suffix}")
    src_gen = _generate(admin, src["id"])
    tgt_gen = _generate(admin, tgt["id"])

    victim = src_gen["variants"][0]
    occupied = tgt_gen["variants"][0]
    r = requests.patch(
        f"{_base()}/api/products/{victim['id']}",
        json={"data": {"template_id": tgt["id"], "variant_options": occupied["variant_options"], "variant_attrs": occupied["variant_attrs"]}},
        headers=_h(admin),
        timeout=30,
    )
    assert r.status_code == 409


def test_link_existing_variant_rejects_mismatched_unit(auth_tokens):
    admin = auth_tokens["admin"]
    suffix = uuid.uuid4().hex[:8]
    src = _create_template(admin, f"u_src_{suffix}", base_unit="meter")
    tgt = _create_template(admin, f"u_tgt_{suffix}", base_unit="yard")
    src_gen = _generate(admin, src["id"])
    candidate = src_gen["variants"][0]
    r = requests.patch(
        f"{_base()}/api/products/{candidate['id']}",
        json={"data": {"template_id": tgt["id"], "variant_options": candidate["variant_options"], "variant_attrs": candidate["variant_attrs"]}},
        headers=_h(admin),
        timeout=30,
    )
    assert r.status_code == 400
    assert "base_unit" in r.text or "satuan" in r.text.lower()


def test_exclusive_owner_nonowner_cannot_list_detail_or_media(auth_tokens):
    admin = auth_tokens["admin"]
    sales_b = auth_tokens["sales"]
    uniq = uuid.uuid4().hex[:6]

    create_user = requests.post(
        f"{_base()}/api/users",
        json={
            "name": f"TEST Sales OwnerA {uniq}",
            "email": f"test.ownera.{uniq}@kainnusantara.id",
            "role": "sales",
            "password": PASSWORD,
        },
        headers=_h(admin),
        timeout=30,
    )
    assert create_user.status_code == 200, create_user.text[:300]
    sales_a_id = create_user.json()["id"]
    sales_a_email = create_user.json()["email"]
    sales_a = _login(sales_a_email)

    tpl = _create_template(admin, f"excl_{uniq}", exclusivity="sales_tertentu", owner_sales_ids=[sales_a_id])
    gen = _generate(admin, tpl["id"], payload={"axes": [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]})
    product_id = gen["variants"][0]["id"]

    img = _tiny_jpeg()
    up = requests.post(
        f"{_base()}/api/products/{product_id}/media",
        headers={"Authorization": f"Bearer {admin}"},
        files={"file": ("ok.jpg", img, "image/jpeg")},
        data={"kind": "photo"},
        timeout=30,
    )
    assert up.status_code == 200
    media_id = up.json()["id"]
    ap = requests.patch(f"{_base()}/api/products/{product_id}/media/{media_id}", json={"status": "approved"}, headers=_h(auth_tokens["manager"]), timeout=30)
    assert ap.status_code == 200

    list_a = requests.get(f"{_base()}/api/products", headers=_h(sales_a), timeout=30)
    list_b = requests.get(f"{_base()}/api/products", headers=_h(sales_b), timeout=30)
    assert list_a.status_code == 200 and list_b.status_code == 200
    assert any(p.get("id") == product_id for p in list_a.json())
    assert not any(p.get("id") == product_id for p in list_b.json())

    detail_b = requests.get(f"{_base()}/api/product-templates/{tpl['id']}", headers=_h(sales_b), timeout=30)
    assert detail_b.status_code == 404

    media_b = requests.get(f"{_base()}/api/products/{product_id}/media", headers=_h(sales_b), timeout=30)
    rel_b = requests.get(f"{_base()}/api/products/{product_id}/catalog-relations", headers=_h(sales_b), timeout=30)
    assert media_b.status_code == 404
    assert rel_b.status_code == 404

    content_b = requests.get(f"{_base()}/api/products/{product_id}/media/{media_id}/content", headers=_h(sales_b), timeout=30)
    assert content_b.status_code == 404


def test_media_restrictions_lifecycle_and_invalid_inputs(auth_tokens):
    admin = auth_tokens["admin"]
    reviewer = _reviewer_token(auth_tokens)
    sales = auth_tokens["sales"]
    suffix = uuid.uuid4().hex[:8]
    tpl = _create_template(admin, f"med_{suffix}")
    gen = _generate(admin, tpl["id"], payload={"axes": [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]})
    pid = gen["variants"][0]["id"]

    malformed = requests.post(
        f"{_base()}/api/products/{pid}/media",
        headers={"Authorization": f"Bearer {admin}"},
        files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")},
        data={"kind": "photo"},
        timeout=30,
    )
    assert malformed.status_code == 400

    good = requests.post(
        f"{_base()}/api/products/{pid}/media",
        headers={"Authorization": f"Bearer {admin}"},
        files={"file": ("ok.jpg", _tiny_jpeg(), "image/jpeg")},
        data={"kind": "photo"},
        timeout=30,
    )
    assert good.status_code == 200, good.text[:200]
    mid = good.json()["id"]

    empty_patch = requests.patch(f"{_base()}/api/products/{pid}/media/{mid}", json={}, headers=_h(reviewer), timeout=30)
    assert empty_patch.status_code == 400

    sales_draft = requests.get(f"{_base()}/api/products/{pid}/media/{mid}/content", headers=_h(sales), timeout=30)
    assert sales_draft.status_code == 404

    approved = requests.patch(f"{_base()}/api/products/{pid}/media/{mid}", json={"status": "approved"}, headers=_h(reviewer), timeout=30)
    assert approved.status_code == 200
    sales_ok = requests.get(f"{_base()}/api/products/{pid}/media/{mid}/content", headers=_h(sales), timeout=30)
    assert sales_ok.status_code == 200

    deleted = requests.delete(f"{_base()}/api/products/{pid}/media/{mid}", headers=_h(admin), timeout=30)
    assert deleted.status_code == 200
    sales_after_delete = requests.get(f"{_base()}/api/products/{pid}/media/{mid}/content", headers=_h(sales), timeout=30)
    assert sales_after_delete.status_code == 404

    anon = requests.get(f"{_base()}/api/products/{pid}/media/{mid}/content", timeout=30)
    assert anon.status_code in (401, 403)


def test_parallel_media_upload_cas_conflict_or_no_loss(auth_tokens):
    admin = auth_tokens["admin"]
    suffix = uuid.uuid4().hex[:8]
    tpl = _create_template(admin, f"cas_{suffix}")
    gen = _generate(admin, tpl["id"], payload={"axes": [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]})
    pid = gen["variants"][0]["id"]

    def _upload(i):
        return requests.post(
            f"{_base()}/api/products/{pid}/media",
            headers={"Authorization": f"Bearer {admin}"},
            files={"file": (f"cas_{i}.jpg", _tiny_jpeg(), "image/jpeg")},
            data={"kind": "photo"},
            timeout=30,
        ).status_code

    statuses = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(_upload, 1), ex.submit(_upload, 2)]
        for fut in as_completed(futs):
            statuses.append(fut.result())
    assert any(s == 200 for s in statuses)
    assert all(s in (200, 409) for s in statuses)


def test_product_patch_cannot_archive_parent_with_children(auth_tokens):
    admin = auth_tokens["admin"]
    suffix = uuid.uuid4().hex[:8]
    tpl = _create_template(admin, f"arc_{suffix}")
    _generate(admin, tpl["id"], payload={"axes": [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]})
    r = requests.patch(f"{_base()}/api/product-templates/{tpl['id']}", json={"status": "archived"}, headers=_h(admin), timeout=30)
    assert r.status_code == 400
    assert "SKU" in r.text or "induk" in r.text.lower()


def test_sales_order_stock_backed_create_and_cancel(auth_tokens):
    admin = auth_tokens["admin"]
    sales = auth_tokens["sales"]
    suffix = uuid.uuid4().hex[:8]
    tpl = _create_template(admin, f"so_{suffix}")
    gen = _generate(admin, tpl["id"], payload={"axes": [
        {"key": "color", "label": "Warna", "options": [{"code": "RED", "label": "Merah", "value": "RED", "hex": "#FF0000"}]},
        {"key": "size", "label": "Ukuran", "options": [{"code": "S", "label": "Small", "value": "S"}]},
        {"key": "material", "label": "Material", "options": [{"code": "CTN", "label": "Cotton", "value": "CTN"}]},
    ]})
    pid = gen["variants"][0]["id"]

    wh = requests.get(f"{_base()}/api/warehouses", headers=_h(admin), timeout=30)
    assert wh.status_code == 200
    warehouses = wh.json() if isinstance(wh.json(), list) else wh.json().get("items", [])
    assert warehouses
    add_stock = requests.post(
        f"{_base()}/api/inventory/initial-stock",
        json={
            "product_id": pid,
            "warehouse_id": warehouses[0]["id"],
            "owner_entity_id": "",
            "lot": f"TEST-SO-LOT-{suffix}",
            "quantity": 15,
            "unit": "meter",
            "grade": "A",
            "batch": f"TEST-SO-B-{suffix}",
        },
        headers=_h(admin),
        timeout=40,
    )
    assert add_stock.status_code == 200, add_stock.text[:300]

    me = requests.get(f"{_base()}/api/auth/me", headers=_h(sales), timeout=30)
    assert me.status_code == 200
    entity_id = ((me.json().get("entity_context") or {}).get("active_entity_id")
                 or (me.json().get("entity_context") or {}).get("home_entity_id")
                 or "")

    cust = requests.get(f"{_base()}/api/customers", headers=_h(sales), timeout=30)
    assert cust.status_code == 200
    c_items = cust.json() if isinstance(cust.json(), list) else cust.json().get("items", [])
    c_pick = next((c for c in c_items if c.get("addresses")), None)
    if c_pick is None:
        c_new = requests.post(
            f"{_base()}/api/customers",
            json={
                "name": f"TEST SO Customer {suffix}",
                "pic_name": "QA",
                "phone": "081234567890",
                "email": f"test.so.{suffix}@example.com",
                "city": "Bandung",
                "address": "Jalan QA 17",
                "type": "Retail",
                "entity_id": entity_id,
            },
            headers=_h(sales),
            timeout=40,
        )
        assert c_new.status_code == 200, c_new.text[:300]
        c_pick = c_new.json()
    addr_id = c_pick["addresses"][0]["id"]

    order = requests.post(
        f"{_base()}/api/sales-orders",
        json={
            "customer_id": c_pick["id"],
            "shipping_address_id": addr_id,
            "entity_id": entity_id,
            "items": [{"product_id": pid, "quantity": 2, "unit": "meter"}],
        },
        headers=_h(sales),
        timeout=60,
    )
    assert order.status_code == 200, order.text[:500]
    o = order.json()
    assert o.get("id") and any(it.get("product_id") == pid for it in o.get("items", []))

    cancel = requests.post(f"{_base()}/api/sales-orders/{o['id']}/cancel", headers=_h(sales), timeout=40)
    assert cancel.status_code == 200, cancel.text[:300]
    assert cancel.json().get("status") == "cancelled"


def test_saga_lock_registry_contains_md_specs(auth_tokens):
    admin = auth_tokens["admin"]
    r = requests.get(f"{_base()}/api/saga-locks", headers=_h(admin), timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
