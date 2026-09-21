"""Backend tests for:
 (1) allocation.roll_pick_sales toggle guard at POST /api/sales-orders
 (2) POST /api/sales-orders/{order_id}/items/{product_id}/reallocate (manual reallocate)

Ensures cleanup: allocation.roll_pick_sales is reset to default at end of run.
"""
import os
import pytest
import requests
from pathlib import Path


def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    envf = Path("/app/frontend/.env")
    if envf.exists():
        for line in envf.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    return ""


BASE_URL = _load_url()
ENTITY = "ent_ksc"
KEY = "allocation.roll_pick_sales"

CREATED_SO_IDS = []


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


def _hdr(token, entity=ENTITY):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": entity,
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {
        "admin": _login("admin@kainnusantara.id"),
        "sales": _login("sales@kainnusantara.id"),
        "sadm":  _login("salesadmin@kainnusantara.id"),
    }


def _set_roll_pick(token, value):
    body = {"items": [{"key": KEY, "value": value, "scope_type": "global",
                       "scope_id": "", "reason": "test toggle"}]}
    r = requests.put(f"{BASE_URL}/api/config/values", json=body, headers=_hdr(token), timeout=30)
    return r


def _reset_roll_pick(token):
    body = {"key": KEY, "scope_type": "global", "scope_id": "", "reason": "cleanup"}
    return requests.post(f"{BASE_URL}/api/config/values/reset",
                         json=body, headers=_hdr(token), timeout=30)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(tokens):
    yield
    # Restore default
    _reset_roll_pick(tokens["admin"])
    print("Reset roll_pick_sales to default. Test SOs created:", CREATED_SO_IDS)


# ---------- Registry ----------
def test_registry_contains_roll_pick_sales_true(tokens):
    r = requests.get(f"{BASE_URL}/api/config/registry?q=roll_pick",
                     headers=_hdr(tokens["admin"]), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    entries = data.get("entries") or data.get("items") or []
    keys = {e.get("key"): e for e in entries}
    assert KEY in keys, f"Registry missing {KEY}: {list(keys)[:20]}"
    entry = keys[KEY]
    assert entry.get("default") is True


# ---------- Helper: pick customer + product with rolls ----------
def _pick_customer(token):
    r = requests.get(f"{BASE_URL}/api/customers", headers=_hdr(token), timeout=30)
    assert r.status_code == 200
    for c in r.json():
        if c.get("entity_id") == ENTITY:
            addrs = c.get("addresses") or []
            if addrs:
                return c["id"], addrs[0]["id"]
    pytest.skip("No customer with address for ent_ksc")


def _find_product_with_rolls(token, min_rolls=2):
    """Find a product that has >= min_rolls AVAILABLE rolls in ent_ksc."""
    r = requests.get(f"{BASE_URL}/api/products", headers=_hdr(token), timeout=30)
    assert r.status_code == 200
    products = r.json()[:200] if isinstance(r.json(), list) else r.json().get("items", [])[:200]
    for p in products:
        rr = requests.get(
            f"{BASE_URL}/api/inventory/rolls/available?product_id={p['id']}&entity_id={ENTITY}",
            headers=_hdr(token), timeout=30)
        if rr.status_code != 200:
            continue
        rolls = rr.json() if isinstance(rr.json(), list) else rr.json().get("items", [])
        if len(rolls) >= min_rolls:
            return p, rolls
    pytest.skip(f"No product with >= {min_rolls} available rolls in ent_ksc")


# ---------- Toggle True: sales qty mode OK ----------
def test_sales_qty_mode_with_toggle_true(tokens):
    _reset_roll_pick(tokens["admin"])
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=1)
    cust_id, addr_id = _pick_customer(tokens["admin"])
    body = {
        "customer_id": cust_id, "shipping_address_id": addr_id,
        "items": [{"product_id": prod["id"], "quantity": 5, "unit": prod.get("base_unit", "meter"),
                   "purchase_mode": "qty"}],
        "confirm_mixed_lot": True, "allow_backorder": True,
    }
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body,
                      headers=_hdr(tokens["sales"]), timeout=60)
    assert r.status_code == 200, r.text
    CREATED_SO_IDS.append(r.json()["id"])


# ---------- Set False → sales cannot pick rolls ----------
def test_sales_roll_mode_blocked_when_toggle_false(tokens):
    r = _set_roll_pick(tokens["admin"], False)
    assert r.status_code == 200, r.text
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=1)
    cust_id, addr_id = _pick_customer(tokens["admin"])
    roll = rolls[0]
    body = {
        "customer_id": cust_id, "shipping_address_id": addr_id,
        "items": [{"product_id": prod["id"],
                   "quantity": float(roll.get("length_remaining") or roll.get("length_initial") or 5),
                   "unit": prod.get("base_unit", "meter"),
                   "purchase_mode": "roll",
                   "roll_lines": [{"roll_id": roll["id"], "take_qty": 0}]}],
        "confirm_mixed_lot": True, "allow_backorder": True,
    }
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body,
                      headers=_hdr(tokens["sales"]), timeout=30)
    assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"
    assert "roll" in r.text.lower()


def test_sales_qty_mode_still_ok_when_toggle_false(tokens):
    prod, _ = _find_product_with_rolls(tokens["admin"], min_rolls=1)
    cust_id, addr_id = _pick_customer(tokens["admin"])
    body = {
        "customer_id": cust_id, "shipping_address_id": addr_id,
        "items": [{"product_id": prod["id"], "quantity": 3, "unit": prod.get("base_unit", "meter"),
                   "purchase_mode": "qty"}],
        "confirm_mixed_lot": True, "allow_backorder": True,
    }
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body,
                      headers=_hdr(tokens["sales"]), timeout=60)
    assert r.status_code == 200, r.text
    order = r.json()
    CREATED_SO_IDS.append(order["id"])
    # Auto-reserve FEFO expected
    assert order.get("allocations"), "expected allocations for qty mode"


def test_admin_roll_mode_still_ok_when_toggle_false(tokens):
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=1)
    cust_id, addr_id = _pick_customer(tokens["admin"])
    roll = rolls[0]
    body = {
        "customer_id": cust_id, "shipping_address_id": addr_id,
        "items": [{"product_id": prod["id"],
                   "quantity": float(roll.get("length_remaining") or 5),
                   "unit": prod.get("base_unit", "meter"),
                   "purchase_mode": "roll",
                   "roll_lines": [{"roll_id": roll["id"], "take_qty": 0}]}],
        "confirm_mixed_lot": True, "allow_backorder": True,
    }
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body,
                      headers=_hdr(tokens["sadm"]), timeout=60)
    assert r.status_code == 200, f"Admin sales should still be able to pick rolls: {r.text}"
    CREATED_SO_IDS.append(r.json()["id"])
    # Reset toggle for reallocate tests
    _reset_roll_pick(tokens["admin"])


# ---------- Reallocate ----------
@pytest.fixture(scope="module")
def qty_so(tokens):
    """Create qty-mode SO with allocations, as admin. Product must have >=2 rolls."""
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=2)
    cust_id, addr_id = _pick_customer(tokens["admin"])
    take_len = float(rolls[0].get("length_remaining") or 20)
    body = {
        "customer_id": cust_id, "shipping_address_id": addr_id,
        "items": [{"product_id": prod["id"], "quantity": take_len,
                   "unit": prod.get("base_unit", "meter"), "purchase_mode": "qty"}],
        "confirm_mixed_lot": True, "allow_backorder": True,
    }
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body,
                      headers=_hdr(tokens["sadm"]), timeout=60)
    assert r.status_code == 200, r.text
    order = r.json()
    CREATED_SO_IDS.append(order["id"])
    return {"order": order, "product": prod, "rolls": rolls}


def test_reallocate_success_swap_rolls(tokens, qty_so):
    order = qty_so["order"]
    prod = qty_so["product"]
    # Refresh order to see current reserved rolls
    r = requests.get(f"{BASE_URL}/api/sales-orders/{order['id']}",
                     headers=_hdr(tokens["sadm"]), timeout=30)
    assert r.status_code == 200
    order = r.json()
    reserved_roll_ids = set()
    for a in order.get("allocations", []):
        for rr_ in (a.get("rolls") or []):
            if rr_.get("roll_id"):
                reserved_roll_ids.add(rr_["roll_id"])
    # Find replacement rolls (available, same entity, not currently reserved)
    rr = requests.get(
        f"{BASE_URL}/api/inventory/rolls/available?product_id={prod['id']}&entity_id={ENTITY}",
        headers=_hdr(tokens["admin"]), timeout=30)
    assert rr.status_code == 200
    avail = rr.json() if isinstance(rr.json(), list) else rr.json().get("items", [])
    replacements = [x for x in avail if x["id"] not in reserved_roll_ids]
    if not replacements:
        pytest.skip("No replacement rolls available for swap")
    new_roll = replacements[0]
    body = {"roll_lines": [{"roll_id": new_roll["id"], "take_qty": 0}]}
    r = requests.post(
        f"{BASE_URL}/api/sales-orders/{order['id']}/items/{prod['id']}/reallocate",
        json=body, headers=_hdr(tokens["sadm"]), timeout=30)
    assert r.status_code == 200, r.text
    updated = r.json()
    new_alloc_roll_ids = set()
    for a in updated.get("allocations", []):
        if a.get("product_id") != prod["id"]:
            continue
        for rr_ in (a.get("rolls") or []):
            if rr_.get("roll_id"):
                new_alloc_roll_ids.add(rr_["roll_id"])
    assert new_roll["id"] in new_alloc_roll_ids
    # Old rolls should NOT be reserved anymore
    assert not (reserved_roll_ids & new_alloc_roll_ids), "old rolls should be released"
    # Explanation contains "MANUAL"
    manual = any("MANUAL" in (a.get("allocation_explanation") or "")
                 for a in updated.get("allocations", []) if a.get("product_id") == prod["id"])
    assert manual
    # Roll DB status: old rolls -> available
    for rid in reserved_roll_ids:
        d = requests.get(f"{BASE_URL}/api/inventory/rolls/{rid}",
                         headers=_hdr(tokens["admin"]), timeout=15)
        if d.status_code == 200:
            assert d.json().get("status") == "available"


def test_reallocate_denied_for_sales(tokens, qty_so):
    order = qty_so["order"]
    prod = qty_so["product"]
    body = {"roll_lines": [{"roll_id": "rl_dummy", "take_qty": 0}]}
    r = requests.post(
        f"{BASE_URL}/api/sales-orders/{order['id']}/items/{prod['id']}/reallocate",
        json=body, headers=_hdr(tokens["sales"]), timeout=15)
    assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"


def test_reallocate_empty_roll_lines(tokens, qty_so):
    order = qty_so["order"]
    prod = qty_so["product"]
    r = requests.post(
        f"{BASE_URL}/api/sales-orders/{order['id']}/items/{prod['id']}/reallocate",
        json={"roll_lines": []}, headers=_hdr(tokens["sadm"]), timeout=15)
    assert r.status_code == 400, r.text


def test_reallocate_other_entity_roll_denied(tokens, qty_so):
    order = qty_so["order"]
    prod = qty_so["product"]
    # Look for a roll in different entity for same product
    all_rolls = requests.get(
        f"{BASE_URL}/api/inventory/rolls/available?product_id={prod['id']}",
        headers={"Authorization": f"Bearer {tokens['admin']}", "X-Entity-Id": "all",
                 "Content-Type": "application/json"}, timeout=30)
    if all_rolls.status_code != 200:
        pytest.skip("Cannot query all entities")
    rolls = all_rolls.json() if isinstance(all_rolls.json(), list) else all_rolls.json().get("items", [])
    other = next((x for x in rolls if x.get("owner_entity_id") and x["owner_entity_id"] != ENTITY), None)
    if not other:
        pytest.skip("No other-entity roll for this product")
    body = {"roll_lines": [{"roll_id": other["id"], "take_qty": 0}]}
    r = requests.post(
        f"{BASE_URL}/api/sales-orders/{order['id']}/items/{prod['id']}/reallocate",
        json=body, headers=_hdr(tokens["sadm"]), timeout=15)
    assert r.status_code == 400, r.text
    assert "entitas lain" in r.text.lower() or "entity" in r.text.lower()
