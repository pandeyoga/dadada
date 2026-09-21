"""Iteration 4 seed setup for browser E2E (R&D lifecycle + sales mobile/desktop)."""
import io
import json
import os
import uuid

import pytest
import requests
from PIL import Image


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
PASSWORD = "demo12345"
ENTITY_ID = "ent_ksc"
SEED_PATH = "/app/test_reports/iter4_seed.json"


def _base() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL not set")
    return BASE_URL


def _h(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Entity-Id": ENTITY_ID,
    }


def _login(email: str) -> str:
    r = requests.post(
        f"{_base()}/api/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=30,
        headers={"X-Entity-Id": ENTITY_ID},
    )
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:200]}"
    token = r.json().get("token")
    assert isinstance(token, str) and token
    return token


def _tiny_jpeg() -> bytes:
    im = Image.new("RGB", (40, 40), (40, 120, 210))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture(scope="module")
def tokens():
    # auth baseline used by browser-seed APIs
    return {
        "admin": _login("admin@kainnusantara.id"),
        "md": _login("md@kainnusantara.id"),
        "manager": _login("manager@kainnusantara.id"),
        "sales": _login("sales@kainnusantara.id"),
    }


def test_seed_rnd_and_sales_browser_data(tokens):
    admin = tokens["admin"]
    sales = tokens["sales"]
    uniq = uuid.uuid4().hex[:8]

    # catalog + color-library seed source for 4-axis template
    colors = requests.get(f"{_base()}/api/color-library", headers=_h(admin), timeout=30)
    assert colors.status_code == 200, colors.text[:300]
    color_items = colors.json() if isinstance(colors.json(), list) else colors.json().get("items", [])
    if len(color_items) < 2:
        for ix, (hexv, fam) in enumerate([("#1E88E5", "Biru"), ("#E53935", "Merah")], start=1):
            cp = requests.post(
                f"{_base()}/api/color-library",
                json={
                    "code": f"TESTI4C{uniq.upper()}{ix}",
                    "name": f"TEST Iter4 Color {ix}",
                    "hex": hexv,
                    "system": "KN",
                    "family": fam,
                },
                headers=_h(admin),
                timeout=30,
            )
            assert cp.status_code == 200, cp.text[:300]
        colors = requests.get(f"{_base()}/api/color-library", headers=_h(admin), timeout=30)
        assert colors.status_code == 200
        color_items = colors.json() if isinstance(colors.json(), list) else colors.json().get("items", [])
    assert len(color_items) >= 2, "Need >=2 colors in color_library"
    c1, c2 = color_items[0], color_items[1]

    axes = [
        {"key": "color", "label": "Warna", "options": [
            {"code": c1["code"], "label": c1.get("name") or c1["code"], "value": c1["code"], "hex": c1.get("hex")},
            {"code": c2["code"], "label": c2.get("name") or c2["code"], "value": c2["code"], "hex": c2.get("hex")},
        ]},
        {"key": "size", "label": "Ukuran", "options": [
            {"code": "S", "label": "Small", "value": "S"},
            {"code": "L", "label": "Large", "value": "L"},
        ]},
        {"key": "material", "label": "Material", "options": [
            {"code": "CTN", "label": "Cotton", "value": "CTN"},
            {"code": "LIN", "label": "Linen", "value": "LIN"},
        ]},
        {"key": "lebar", "label": "Lebar", "options": [
            {"code": "W110", "label": "110 cm", "value": "110"},
            {"code": "W120", "label": "120 cm", "value": "120"},
        ]},
    ]

    t_payload = {
        "name": f"TEST_iter4_family_{uniq}",
        "category": "Kain",
        "fabric_type": "woven",
        "stage": "finished",
        "base_unit": "meter",
        "base_price": 18000,
        "gramasi": 125,
        "lebar": 1.1,
        "sku_prefix": f"I4{uniq.upper()}",
        "axes": axes,
    }
    t = requests.post(f"{_base()}/api/product-templates", json=t_payload, headers=_h(admin), timeout=40)
    assert t.status_code == 200, t.text[:400]
    template = t.json()

    # create only 2 variants manually -> ensures missing cross-combinations exist in picker
    p1_payload = {
        "sku": f"{template['sku_prefix']}-001",
        "name": f"TEST_iter4_SKU_A_{uniq}",
        "category": "Kain",
        "color": c1.get("name") or c1["code"],
        "color_code": c1["code"],
        "color_name": c1.get("name") or c1["code"],
        "color_hex": c1.get("hex") or "#999999",
        "motif": "Polos",
        "grade": "A",
        "stage": "finished",
        "fabric_type": "woven",
        "supplier": "Internal",
        "base_unit": "meter",
        "price": 22000,
        "gramasi": 125,
        "lebar": 1.1,
        "template_id": template["id"],
        "variant_attrs": {"color": c1.get("name") or c1["code"], "size": "Small", "material": "Cotton", "lebar": "110 cm"},
        "variant_options": {"color": c1["code"], "size": "S", "material": "CTN", "lebar": "W110"},
    }
    p2_payload = {
        "sku": f"{template['sku_prefix']}-002",
        "name": f"TEST_iter4_SKU_B_{uniq}",
        "category": "Kain",
        "color": c2.get("name") or c2["code"],
        "color_code": c2["code"],
        "color_name": c2.get("name") or c2["code"],
        "color_hex": c2.get("hex") or "#777777",
        "motif": "Polos",
        "grade": "A",
        "stage": "finished",
        "fabric_type": "woven",
        "supplier": "Internal",
        "base_unit": "meter",
        "price": 24000,
        "gramasi": 125,
        "lebar": 1.2,
        "template_id": template["id"],
        "variant_attrs": {"color": c2.get("name") or c2["code"], "size": "Large", "material": "Linen", "lebar": "120 cm"},
        "variant_options": {"color": c2["code"], "size": "L", "material": "LIN", "lebar": "W120"},
    }
    p1 = requests.post(f"{_base()}/api/products", json=p1_payload, headers=_h(admin), timeout=40)
    p2 = requests.post(f"{_base()}/api/products", json=p2_payload, headers=_h(admin), timeout=40)
    assert p1.status_code == 200, p1.text[:400]
    assert p2.status_code == 200, p2.text[:400]
    prod1, prod2 = p1.json(), p2.json()

    wh = requests.get(f"{_base()}/api/warehouses", headers=_h(admin), timeout=30)
    assert wh.status_code == 200
    warehouses = wh.json() if isinstance(wh.json(), list) else wh.json().get("items", [])
    assert warehouses, "No warehouse found"
    wh_id = warehouses[0]["id"]

    # inventory + media seed for sales/mobile quickview checks
    for idx, pid in enumerate([prod1["id"], prod2["id"]], start=1):
        stk = requests.post(
            f"{_base()}/api/inventory/initial-stock",
            json={
                "product_id": pid,
                "warehouse_id": wh_id,
                "owner_entity_id": ENTITY_ID,
                "lot": f"TEST-I4-LOT-{uniq}-{idx}",
                "quantity": 35,
                "unit": "meter",
                "grade": "A",
                "batch": f"TEST-I4-B-{uniq}-{idx}",
            },
            headers=_h(admin),
            timeout=40,
        )
        assert stk.status_code == 200, stk.text[:300]

        media_ids = []
        for m in range(2):
            up = requests.post(
                f"{_base()}/api/products/{pid}/media",
                headers={"Authorization": f"Bearer {admin}", "X-Entity-Id": ENTITY_ID},
                files={"file": (f"iter4_{idx}_{m}.jpg", _tiny_jpeg(), "image/jpeg")},
                data={"kind": "photo"},
                timeout=30,
            )
            assert up.status_code == 200, up.text[:300]
            mid = up.json()["id"]
            media_ids.append(mid)
            ap = requests.patch(
                f"{_base()}/api/products/{pid}/media/{mid}",
                json={"status": "approved"},
                headers=_h(tokens["manager"]),
                timeout=30,
            )
            assert ap.status_code == 200, ap.text[:300]

    # ensure one customer with address is available for checkout
    custs = requests.get(f"{_base()}/api/customers", headers=_h(sales), timeout=30)
    assert custs.status_code == 200
    rows = custs.json() if isinstance(custs.json(), list) else custs.json().get("items", [])
    customer = next((c for c in rows if c.get("addresses")), None)
    if customer is None:
        c_new = requests.post(
            f"{_base()}/api/customers",
            json={
                "name": f"TEST_iter4_customer_{uniq}",
                "pic_name": "QA",
                "phone": "081234567890",
                "email": f"test.iter4.{uniq}@example.com",
                "city": "Bandung",
                "address": "Jalan QA Iter4",
                "type": "Retail",
                "entity_id": ENTITY_ID,
            },
            headers=_h(sales),
            timeout=40,
        )
        assert c_new.status_code == 200, c_new.text[:300]
        customer = c_new.json()

    out = {
        "template_id": template["id"],
        "template_name": template["name"],
        "sku_prefix": template["sku_prefix"],
        "products": [
            {"id": prod1["id"], "sku": prod1["sku"], "variant_options": prod1.get("variant_options", {})},
            {"id": prod2["id"], "sku": prod2["sku"], "variant_options": prod2.get("variant_options", {})},
        ],
        "missing_combo_example": {"color": c1["code"], "size": "L", "material": "CTN", "lebar": "W110"},
        "customer_id": customer["id"],
        "customer_address_id": (customer.get("addresses") or [{}])[0].get("id", ""),
        "entity_id": ENTITY_ID,
    }
    with open(SEED_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    assert out["template_id"].startswith("ptpl_")
    assert all(p["id"].startswith("prod_") for p in out["products"])