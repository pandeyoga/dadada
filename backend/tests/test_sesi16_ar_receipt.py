"""Sesi 16: sales@ can POST /api/ar-receipts (idempotent), admin can void it."""
import os, uuid, requests
from pathlib import Path

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v: return v.rstrip("/")
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE = _load_url()
ENT = {"X-Entity-Id": "ent_ksc"}


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "demo12345"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_sales_can_create_ar_receipt_and_admin_can_void():
    sales_tok = _login("sales@kainnusantara.id")
    admin_tok = _login("admin@kainnusantara.id")

    sh = {"Authorization": f"Bearer {sales_tok}", **ENT}
    ah = {"Authorization": f"Bearer {admin_tok}", **ENT}

    # Get customers, find one with open orders
    rc = requests.get(f"{BASE}/api/customers", headers=sh)
    assert rc.status_code == 200, rc.text
    customers = rc.json()
    if isinstance(customers, dict):
        customers = customers.get("items", [])
    order = None
    customer_id = None
    for c in customers[:20]:
        cid = c.get("id") or c.get("_id")
        r = requests.get(f"{BASE}/api/ar-receipts/open-orders",
                         headers=sh, params={"customer_id": cid})
        if r.status_code == 200 and r.json():
            order = r.json()[0]
            customer_id = cid
            break
    assert order, "no customer with open orders found"
    order_id = order["order_id"]
    outstanding = float(order.get("outstanding") or order.get("grand_total") or 0)
    amount = min(1000.0, outstanding)
    assert amount > 0

    idem = f"test-sesi16-{uuid.uuid4().hex[:10]}"
    payload = {
        "customer_id": customer_id,
        "amount": amount,
        "method": "cash",
        "allocations": [{"order_id": order_id, "amount": amount}],
    }
    idem_headers = {**sh, "Idempotency-Key": idem}
    r1 = requests.post(f"{BASE}/api/ar-receipts", headers=idem_headers, json=payload)
    assert r1.status_code == 200, f"sales POST /api/ar-receipts failed: {r1.status_code} {r1.text}"
    receipt = r1.json()
    rid = receipt["id"]

    # Idempotent replay
    r2 = requests.post(f"{BASE}/api/ar-receipts", headers=idem_headers, json=payload)
    assert r2.status_code == 200 and r2.json()["id"] == rid, "replay should return same receipt"

    # Admin void
    rv = requests.post(f"{BASE}/api/ar-receipts/{rid}/void",
                       headers=ah, json={"reason": "test cleanup sesi16"})
    assert rv.status_code in (200, 204), f"void failed: {rv.status_code} {rv.text}"
