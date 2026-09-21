"""Iter-284 — PB-01 (Blanket PO termin/PPN + call-off), MD-02 (yarn), MD-08 (supplier_codes), lencana labdip telat."""
import os
import pytest
import requests

def _base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        # baca frontend/.env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        return line.split("=", 1)[1].strip().rstrip("/")
        except Exception:
            pass
    return (v or "").rstrip("/")


BASE = _base()
ENT = "ent_ksc"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT, "Content-Type": "application/json"})
    return s


# --- PB-01 ---------------------------------------------------------------
def _mk_blanket_payload(**over):
    body = {
        "supplier_id": "sup_cbd71be5aff2",
        "warehouse_id": "wh_bandung",
        "items": [{"product_id": "prod_batik_mega", "contract_qty": 300, "contract_price": 100000, "unit": "yard"}],
        "payment_term_code": "NET14",
        "tax_mode": "ppn",
        "price_includes_ppn": False,
        "entity_id": ENT,
    }
    body.update(over)
    return body


@pytest.fixture(scope="module")
def cleanup_ids():
    return {"blanket_ids": [], "po_ids": []}


def test_pb01_blanket_create_ok(admin, cleanup_ids):
    r = admin.post(f"{BASE}/api/purchase-orders/blanket", json=_mk_blanket_payload())
    assert r.status_code == 200, r.text
    doc = r.json()
    assert (doc.get("payment_term") or {}).get("code") == "NET14"
    assert (doc.get("payment_term") or {}).get("net_days") == 14
    assert doc.get("payment_term_code") == "NET14"
    assert doc.get("tax_mode") == "ppn"
    assert doc.get("price_includes_ppn") is False
    cleanup_ids["blanket_ids"].append(doc["id"])


def test_pb01_blanket_inherits_supplier_term_when_missing(admin, cleanup_ids):
    body = _mk_blanket_payload()
    body.pop("payment_term_code")
    r = admin.post(f"{BASE}/api/purchase-orders/blanket", json=body)
    assert r.status_code == 200, r.text
    doc = r.json()
    # supplier Palembang Silk House = NET30
    assert doc.get("payment_term_code") == "NET30", doc.get("payment_term")
    assert (doc.get("payment_term") or {}).get("net_days") == 30
    cleanup_ids["blanket_ids"].append(doc["id"])


def test_pb01_blanket_invalid_term_code(admin):
    r = admin.post(f"{BASE}/api/purchase-orders/blanket", json=_mk_blanket_payload(payment_term_code="NET99"))
    assert r.status_code == 400
    assert "tidak ada di master" in r.text.lower() or "master" in r.text.lower()


def test_pb01_blanket_invalid_tax_mode(admin):
    r = admin.post(f"{BASE}/api/purchase-orders/blanket", json=_mk_blanket_payload(tax_mode="xyz"))
    assert r.status_code == 400


def test_pb01_call_off_excluded(admin, cleanup_ids):
    # kontrak baru harga excl ppn
    b = admin.post(f"{BASE}/api/purchase-orders/blanket", json=_mk_blanket_payload()).json()
    cleanup_ids["blanket_ids"].append(b["id"])
    r = admin.post(
        f"{BASE}/api/purchase-orders/{b['id']}/call-off",
        json={
            "items": [{"product_id": "prod_batik_mega", "quantity": 50, "unit": "yard"}],
            "expected_delivery_date": "2026-09-20",
        },
    )
    assert r.status_code == 200, r.text
    child = r.json()
    cleanup_ids["po_ids"].append(child["id"])
    assert child.get("payment_term_code") == "NET14"
    # NET14 → 2026-09-20 + 14 = 2026-10-04
    assert (child.get("payment_due_date") or "").startswith("2026-10-04")
    assert child.get("price_includes_ppn") is False
    assert child.get("ppn_mode") == "excluded"
    gt = float(child.get("grand_total") or 0)
    ta = float(child.get("total_amount") or 0)
    dpp = float(child.get("dpp_total") or child.get("dpp") or 0)
    # excluded → grand_total = total + PPN → grand > total
    assert gt > ta > 0, child


def test_pb01_call_off_included(admin, cleanup_ids):
    b = admin.post(f"{BASE}/api/purchase-orders/blanket", json=_mk_blanket_payload(price_includes_ppn=True)).json()
    assert b.get("price_includes_ppn") is True
    cleanup_ids["blanket_ids"].append(b["id"])
    r = admin.post(
        f"{BASE}/api/purchase-orders/{b['id']}/call-off",
        json={
            "items": [{"product_id": "prod_batik_mega", "quantity": 40, "unit": "yard"}],
            "expected_delivery_date": "2026-09-20",
        },
    )
    assert r.status_code == 200, r.text
    child = r.json()
    cleanup_ids["po_ids"].append(child["id"])
    assert child.get("ppn_mode") == "included"
    assert child.get("price_includes_ppn") is True
    gt = float(child.get("grand_total") or 0)
    ta = float(child.get("total_amount") or 0)
    dpp = float(child.get("dpp_total") or child.get("dpp") or 0)
    assert abs(gt - ta) < 1, (gt, ta)  # included → gt == total
    assert dpp > 0 and dpp < ta, (dpp, ta)


# --- MD-02 ---------------------------------------------------------------
@pytest.fixture(scope="module")
def yarn_products():
    return []


def test_md02_yarn_create_ok(admin, yarn_products):
    body = {
        "sku": "YRN-QA-01",
        "name": "Benang Katun 30s QA",
        "category": "Benang",
        "stage": "yarn",
        "fabric_type": "woven",
        "yarn_count": "30s",
        "yarn_count_system": "Ne",
        "yarn_material": "Katun",
        "yarn_ply": "2",
        "yarn_twist": "z",
        "yarn_dye_status": "raw",
        "base_unit": "kg",
        "price": 45000,
        "grade": "A",
        "entity_id": ENT,
    }
    r = admin.post(f"{BASE}/api/products", json=body)
    assert r.status_code == 200, r.text
    prod = r.json()
    yarn_products.append(prod["id"])
    assert prod.get("yarn_material") == "katun"
    assert prod.get("yarn_twist") == "Z"


def test_md02_yarn_invalid_material(admin):
    body = {
        "sku": "YRN-QA-BAD",
        "name": "Bad", "category": "Benang", "stage": "yarn",
        "yarn_count": "30s", "yarn_count_system": "Ne",
        "yarn_material": "kapas", "yarn_ply": "1", "yarn_twist": "z",
        "yarn_dye_status": "raw", "base_unit": "kg", "price": 1000, "grade": "A",
        "entity_id": ENT,
    }
    r = admin.post(f"{BASE}/api/products", json=body)
    assert r.status_code == 400
    assert "pilihan sah" in r.text.lower() or "pilihan" in r.text.lower()


def test_md02_enums(admin):
    r = admin.get(f"{BASE}/api/enums")
    assert r.status_code == 200
    e = r.json().get("enums") or r.json()
    assert "yarn_material" in e
    assert "yarn_twist" in e
    assert "yarn_dye_status" in e


# --- MD-08 supplier codes -------------------------------------------------
def test_md08_products_have_supplier_codes(admin):
    r = admin.get(f"{BASE}/api/products", params={"entity_id": ENT})
    assert r.status_code == 200
    products = r.json() if isinstance(r.json(), list) else r.json().get("items") or r.json().get("products") or []
    btk = next((p for p in products if p.get("sku") == "BTK-MEGA-001"), None)
    assert btk, "BTK-MEGA-001 tidak ditemukan"
    codes = btk.get("supplier_codes") or []
    assert codes and codes[0].get("supplier_sku") == "CBN-MEGA-PREM", codes


def test_md08_dashboard_has_supplier_codes(admin):
    r = admin.get(f"{BASE}/api/dashboard", params={"entity_id": ENT})
    assert r.status_code == 200
    d = r.json()
    products = d.get("products") or []
    btk = next((p for p in products if p.get("sku") == "BTK-MEGA-001"), None)
    assert btk, "dashboard.products tanpa BTK-MEGA-001"
    codes = btk.get("supplier_codes") or []
    assert codes, "dashboard product tidak membawa supplier_codes"


# --- Lencana labdip telat -------------------------------------------------
def test_color_library_labdip_overdue(admin):
    r = admin.get(f"{BASE}/api/color-library", params={"entity_id": ENT})
    assert r.status_code == 200
    body = r.json()
    colors = body if isinstance(body, list) else body.get("items") or body.get("colors") or []
    wht = next((c for c in colors if c.get("code") == "KN-WHT-01" or c.get("id") == "col_kn_wht_01"), None)
    assert wht, "warna KN-WHT-01 tidak ditemukan"
    assert (wht.get("labdip_overdue_count") or 0) >= 1, wht


# --- Cleanup at end (run last alphabetically prefix zzz) ------------------
def test_zzz_cleanup(admin, cleanup_ids, yarn_products):
    for pid in cleanup_ids["po_ids"]:
        admin.post(f"{BASE}/api/purchase-orders/{pid}/cancel", json={"reason": "iter284 cleanup"})
    for bid in cleanup_ids["blanket_ids"]:
        admin.post(f"{BASE}/api/purchase-orders/{bid}/close-contract", json={"reason": "iter284 cleanup"})
    for prod in yarn_products:
        r = admin.delete(f"{BASE}/api/products/{prod}")
        if r.status_code not in (200, 204):
            admin.patch(f"{BASE}/api/products/{prod}", json={"is_active": False})
    print("cleanup done", cleanup_ids, yarn_products)
