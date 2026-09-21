#!/usr/bin/env python3
"""Create a sample request as sales user, return wms_task_id + suggested_roll_id + child info."""
import os, sys, json, requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://vendor-bills-wms.preview.emergentagent.com").rstrip("/")
API = BASE + "/api"
ENT = "ent_ksc"

s = requests.Session()
s.headers.update({"X-Entity-Id": ENT})

# Login as sales
r = s.post(f"{API}/auth/login", json={"email":"sales@kainnusantara.id","password":"demo12345"})
print("login", r.status_code)
assert r.status_code == 200, r.text

# Pick a customer
rc = s.get(f"{API}/customers", params={"limit":50})
customers = rc.json()
if isinstance(customers, dict):
    customers = customers.get("items", [])
cust = next((c for c in customers if c.get("owner_entity_id")==ENT or True), None)
assert cust, "no customer"
customer_id = cust["id"]
print("customer_id", customer_id, cust.get("name"))

# Find a product with available roll
rp = s.get(f"{API}/products", params={"limit":100})
products = rp.json()
if isinstance(products, dict):
    products = products.get("items", [])

# Get rolls that are available with sisa >= 1
rr = s.get(f"{API}/rolls", params={"status":"available","limit":200})
rolls = rr.json()
if isinstance(rolls, dict):
    rolls = rolls.get("items", [])

roll = None
for rl in rolls:
    sisa = rl.get("remaining_length") or rl.get("length") or rl.get("sisa") or 0
    if float(sisa) >= 1:
        roll = rl
        break

if not roll:
    # try any roll
    for rl in rolls:
        roll = rl; break

assert roll, "no roll available"
print("roll", roll.get("id"), roll.get("roll_no"), "product", roll.get("product_id"))
product_id = roll["product_id"]

# Create sample request
payload = {"customer_id": customer_id, "product_id": product_id, "length": 1, "payment_method":"cash"}
r2 = s.post(f"{API}/sample-requests", json=payload)
print("sample-req", r2.status_code)
print(r2.text[:600])
assert r2.status_code in (200,201), r2.text
data = r2.json()

out = {
    "sample_request_id": data.get("id"),
    "wms_task_id": data.get("wms_task_id"),
    "suggested_roll_id": data.get("suggested_roll_id"),
    "customer_id": customer_id,
    "customer_name": cust.get("name"),
    "product_id": product_id,
}
print(json.dumps(out, indent=2))
with open("/tmp/sample_req.json","w") as f:
    json.dump(out, f)
