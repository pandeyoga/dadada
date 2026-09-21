"""ITER-270 — supplementary coverage for manual reallocate (Ganti Roll):
 - keep old roll (take_qty=0) + add new roll → old stays reserved, no double count
 - confirmed SO → 409
 - partial reallocate (rolls < need) → backorder_qty > 0, backorders[], has_backorder
 - other-entity roll → 400 (uses a roll owned by another entity, any product)
Cleanup: restores allocation.roll_pick_sales default.
"""
import os
from pathlib import Path

import pytest
import requests


def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    envf = Path("/app/frontend/.env")
    for line in envf.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


BASE_URL = _load_url()
ENTITY = "ent_ksc"
CREATED_SO = []


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


def _hdr(token, entity=ENTITY):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": entity, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {"admin": _login("admin@kainnusantara.id"),
            "sadm": _login("salesadmin@kainnusantara.id"),
            "sales": _login("sales@kainnusantara.id")}


def _pick_customer(token):
    r = requests.get(f"{BASE_URL}/api/customers", headers=_hdr(token), timeout=30)
    assert r.status_code == 200
    for c in r.json():
        if c.get("entity_id") == ENTITY and (c.get("addresses") or []):
            if "Sejahtera" in (c.get("name") or ""):
                continue  # credit-blocked demo customer
            return c["id"], c["addresses"][0]["id"]
    pytest.skip("No usable customer")


def _avail(token, product_id):
    r = requests.get(f"{BASE_URL}/api/inventory/rolls/available?product_id={product_id}&entity_id={ENTITY}",
                     headers=_hdr(token), timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    return j if isinstance(j, list) else j.get("items", [])


def _find_product_with_rolls(token, min_rolls=3):
    r = requests.get(f"{BASE_URL}/api/products", headers=_hdr(token), timeout=30)
    assert r.status_code == 200
    j = r.json()
    products = j if isinstance(j, list) else j.get("items", [])
    for p in products[:200]:
        rolls = _avail(token, p["id"])
        if len(rolls) >= min_rolls:
            return p, rolls
    pytest.skip(f"No product with >= {min_rolls} available rolls")


def _create_qty_so(token, product, qty):
    cust_id, addr_id = _pick_customer(token)
    body = {"customer_id": cust_id, "shipping_address_id": addr_id,
            "items": [{"product_id": product["id"], "quantity": qty,
                       "unit": product.get("base_unit", "meter"), "purchase_mode": "qty"}],
            "confirm_mixed_lot": True, "allow_backorder": True}
    r = requests.post(f"{BASE_URL}/api/sales-orders", json=body, headers=_hdr(token), timeout=60)
    assert r.status_code == 200, r.text
    order = r.json()
    CREATED_SO.append(order["id"])
    return order


def _reserved_roll_ids(order, product_id=None):
    ids = set()
    for a in order.get("allocations", []):
        if product_id and a.get("product_id") != product_id:
            continue
        for rr in (a.get("rolls") or []):
            if rr.get("roll_id"):
                ids.add(rr["roll_id"])
    return ids


def _roll_map(token, product_id):
    """GET /api/inventory/rolls/{id} does NOT exist (404) — use the list endpoint."""
    r = requests.get(f"{BASE_URL}/api/inventory/rolls?product_id={product_id}&limit=500",
                     headers=_hdr(token), timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    items = j if isinstance(j, list) else j.get("items", [])
    return {x["id"]: x for x in items}


def _reallocate(token, order_id, product_id, roll_lines):
    return requests.post(f"{BASE_URL}/api/sales-orders/{order_id}/items/{product_id}/reallocate",
                         json={"roll_lines": roll_lines}, headers=_hdr(token), timeout=40)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(tokens):
    yield
    requests.post(f"{BASE_URL}/api/config/values/reset",
                  json={"key": "allocation.roll_pick_sales", "scope_type": "global",
                        "scope_id": "", "reason": "cleanup iter270"},
                  headers=_hdr(tokens["admin"]), timeout=30)
    print("ITER270 created SOs:", CREATED_SO)


# ---------- keep old roll + add new roll ----------
def test_reallocate_keeps_old_roll_and_adds_new(tokens):
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=3)
    take = float(rolls[0].get("length_remaining") or 20)
    order = _create_qty_so(tokens["sadm"], prod, take)
    old_ids = _reserved_roll_ids(order, prod["id"])
    assert old_ids, "qty mode should auto-reserve rolls"
    avail = [x for x in _avail(tokens["admin"], prod["id"]) if x["id"] not in old_ids]
    if not avail:
        pytest.skip("no spare roll")
    new_roll = avail[0]
    lines = [{"roll_id": rid, "take_qty": 0} for rid in old_ids] + \
            [{"roll_id": new_roll["id"], "take_qty": 0}]
    r = _reallocate(tokens["sadm"], order["id"], prod["id"], lines)
    assert r.status_code == 200, r.text
    updated = r.json()
    final_ids = _reserved_roll_ids(updated, prod["id"])
    assert old_ids <= final_ids, f"old rolls should be kept: {old_ids} vs {final_ids}"
    assert new_roll["id"] in final_ids
    # no duplicate roll entries
    flat = [rr["roll_id"] for a in updated["allocations"] if a.get("product_id") == prod["id"]
            for rr in (a.get("rolls") or []) if rr.get("roll_id")]
    assert len(flat) == len(set(flat)), f"duplicate rolls in allocations: {flat}"
    item = next(i for i in updated["items"] if i["product_id"] == prod["id"])
    assert float(item["reserved_qty"]) > 0
    # old roll still reserved to this order in DB; new roll reserved too
    rolls_db = _roll_map(tokens["admin"], prod["id"])
    for rid in old_ids:
        assert rolls_db[rid]["status"] == "reserved", rolls_db[rid]
        assert (rolls_db[rid].get("reserved_ref") or {}).get("id") == order["id"]
    assert rolls_db[new_roll["id"]]["status"] == "reserved"
    assert (rolls_db[new_roll["id"]].get("reserved_ref") or {}).get("id") == order["id"]
    # reservation movement recorded
    mv = requests.get(f"{BASE_URL}/api/inventory/movements?product_id={prod['id']}&movement_type=reservation",
                      headers=_hdr(tokens["admin"]), timeout=30)
    assert mv.status_code == 200, mv.text
    mj = mv.json()
    movs = mj if isinstance(mj, list) else mj.get("items", [])
    assert any(order["id"] in str(m.get("source_document", "")) or order["id"] in str(m.get("reference_id", ""))
               or order["id"] in str(m) for m in movs), "no reservation movement for this order"


# ---------- partial reallocate → backorder ----------
def test_reallocate_partial_creates_backorder(tokens):
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=3)
    # need more than one roll can supply
    big_qty = round(sum(float(x.get("length_remaining") or 0) for x in rolls[:3]), 2)
    if big_qty <= 0:
        pytest.skip("no roll lengths")
    order = _create_qty_so(tokens["sadm"], prod, big_qty)
    old_ids = _reserved_roll_ids(order, prod["id"])
    # keep only ONE roll → shortfall
    keep = sorted(old_ids)[:1]
    if not keep:
        pytest.skip("no reserved rolls")
    r = _reallocate(tokens["sadm"], order["id"], prod["id"], [{"roll_id": keep[0], "take_qty": 0}])
    assert r.status_code == 200, r.text
    up = r.json()
    item = next(i for i in up["items"] if i["product_id"] == prod["id"])
    assert float(item["backorder_qty"]) > 0.01, f"expected backorder, got {item}"
    assert up.get("has_backorder") is True
    bos = [b for b in up.get("backorders", []) if b.get("product_id") == prod["id"]]
    assert bos, "backorders[] should have entry"
    assert round(float(item["reserved_qty"]) + float(item["backorder_qty"]), 1) == round(
        float(item.get("base_quantity") or item.get("quantity")), 1)
    # persisted?
    g = requests.get(f"{BASE_URL}/api/sales-orders/{order['id']}", headers=_hdr(tokens["sadm"]), timeout=30)
    assert g.status_code == 200
    gi = next(i for i in g.json()["items"] if i["product_id"] == prod["id"])
    assert float(gi["backorder_qty"]) > 0.01
    # dropped rolls released back to available
    rolls_db = _roll_map(tokens["admin"], prod["id"])
    for rid in old_ids - set(keep):
        assert rolls_db[rid]["status"] == "available", f"{rid} not released: {rolls_db[rid]['status']}"


# ---------- confirmed SO → 409 ----------
def test_reallocate_confirmed_order_conflict(tokens):
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=2)
    take = float(rolls[0].get("length_remaining") or 10)
    order = _create_qty_so(tokens["sadm"], prod, take)
    oid = order["id"]
    for path in ("submit-for-approval", "approve", "confirm"):
        rr = requests.post(f"{BASE_URL}/api/sales-orders/{oid}/{path}",
                           json={}, headers=_hdr(tokens["admin"]), timeout=40)
        print(path, rr.status_code, rr.text[:200])
    g = requests.get(f"{BASE_URL}/api/sales-orders/{oid}", headers=_hdr(tokens["admin"]), timeout=30)
    status = g.json().get("status")
    if status not in ("confirmed", "partially_picked", "picked", "shipped"):
        pytest.skip(f"could not confirm order (status={status})")
    r = _reallocate(tokens["sadm"], oid, prod["id"], [{"roll_id": rolls[-1]["id"], "take_qty": 0}])
    assert r.status_code == 409, f"Expected 409 got {r.status_code}: {r.text}"


# ---------- other-entity roll → 400 ----------
def test_reallocate_other_entity_roll_denied_any_product(tokens):
    prod, rolls = _find_product_with_rolls(tokens["admin"], min_rolls=2)
    take = float(rolls[0].get("length_remaining") or 10)
    order = _create_qty_so(tokens["sadm"], prod, take)
    # find any roll owned by another entity
    r = requests.get(f"{BASE_URL}/api/inventory/rolls?limit=500",
                     headers=_hdr(tokens["admin"], entity="all"), timeout=30)
    if r.status_code != 200:
        pytest.skip(f"rolls list unavailable: {r.status_code}")
    j = r.json()
    items = j if isinstance(j, list) else j.get("items", [])
    other = next((x for x in items if x.get("owner_entity_id") and x["owner_entity_id"] != ENTITY), None)
    if not other:
        pytest.skip("no other-entity roll in DB")
    resp = _reallocate(tokens["sadm"], order["id"], prod["id"],
                       [{"roll_id": other["id"], "take_qty": 0}])
    assert resp.status_code == 400, f"Expected 400 got {resp.status_code}: {resp.text}"
    assert "entitas lain" in resp.text.lower()
