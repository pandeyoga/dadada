"""Skenario AS-02 (qty PR fleksibel) + AS-03 (lepas reservasi sebagian) — jalankan manual:
   python backend/tests/iter283_as02_as03_scenario.py   (butuh seed_realistic; data uji dibersihkan)"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
PWD = "demo12345"
FAILS = []


def chk(label, cond, info=""):
    print(("  [PASS] " if cond else "  [FAIL] ") + label + ("" if cond else f"  → {str(info)[:300]}"))
    if not cond:
        FAILS.append(label)


def login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}


admin, sadmin, sales = login("admin@kainnusantara.id"), login("salesadmin@kainnusantara.id"), login("sales@kainnusantara.id")

custs = requests.get(f"{BASE}/api/customers?limit=100", headers=admin, timeout=30).json()
custs = custs.get("items", custs) if isinstance(custs, dict) else custs
cust = next(c for c in custs if c.get("entity_id") == "ent_ksc" and c.get("addresses"))
addr = cust["addresses"][0].get("id")
prods = requests.get(f"{BASE}/api/products?limit=300", headers=admin, timeout=30).json()
prods = prods.get("items", prods) if isinstance(prods, dict) else prods

# pilih produk dengan >= 2 roll tersedia di KSC
pick = None
for p in prods:
    if float(p.get("price") or 0) <= 0:
        continue
    r = requests.get(f"{BASE}/api/inventory/rolls/available", headers=admin, timeout=30,
                     params={"product_id": p["id"], "entity_id": "ent_ksc", "sort": "fefo", "limit": 10})
    rolls = (r.json() or {}).get("items", []) if r.ok else []
    if len(rolls) >= 2:
        pick = (p, rolls)
        break
chk("ada produk dengan >= 2 roll tersedia", pick is not None)
p, rolls = pick
qty = round(sum(float(x.get("length_remaining") or 0) for x in rolls[:2]), 2)

print("\n[AS-03] SO baru ter-reserve 2 roll → lepas 1 roll")
r = requests.post(f"{BASE}/api/sales-orders", headers=sales, timeout=60, json={
    "customer_id": cust["id"], "shipping_address_id": addr,
    "items": [{"product_id": p["id"], "quantity": qty, "unit": p.get("base_unit") or "meter"}],
    "sales_name": "Ayu Permatasari", "entity_id": "ent_ksc", "allow_backorder": True, "confirm_mixed_lot": True})
chk("POST /sales-orders", r.status_code in (200, 201), r.text)
so = r.json().get("order") or r.json()
so_id = so["id"]
alloc_rolls = [rr for a in so.get("allocations", []) for rr in a.get("rolls", [])]
chk("SO punya roll ter-reserve", len(alloc_rolls) >= 1, so.get("allocations"))
item0 = so["items"][0]
before_res = float(item0.get("reserved_qty") or 0)

r = requests.post(f"{BASE}/api/sales-orders/{so_id}/items/{p['id']}/release-rolls", headers=sales, timeout=60,
                  json={"roll_ids": [alloc_rolls[0]["roll_id"]], "reason": "pelanggan menunda pengiriman"})
chk("sales biasa DITOLAK 403 (izin inventory.pegging)", r.status_code == 403, r.text)
r = requests.post(f"{BASE}/api/sales-orders/{so_id}/items/{p['id']}/release-rolls", headers=sadmin, timeout=60,
                  json={"roll_ids": [alloc_rolls[0]["roll_id"]], "reason": "abc"})
chk("alasan pendek → 422", r.status_code == 422, r.text)
r = requests.post(f"{BASE}/api/sales-orders/{so_id}/items/{p['id']}/release-rolls", headers=sadmin, timeout=60,
                  json={"roll_ids": ["roll_tidak_ada"], "reason": "roll tidak ada di baris"})
chk("roll bukan milik baris → 400", r.status_code == 400, r.text)
r = requests.post(f"{BASE}/api/sales-orders/{so_id}/items/{p['id']}/release-rolls", headers=sadmin, timeout=60,
                  json={"roll_ids": [alloc_rolls[0]["roll_id"]], "reason": "pelanggan menunda pengiriman"})
chk("Admin Sales lepas 1 roll → 200", r.status_code == 200, r.text)
after = r.json()
it = after["items"][0]
chk("status SO TETAP", after["status"] == so["status"], (so["status"], after["status"]))
chk("reserved_qty turun", float(it.get("reserved_qty") or 0) < before_res, (before_res, it.get("reserved_qty")))
chk("backorder_qty > 0", float(it.get("backorder_qty") or 0) > 0, it.get("backorder_qty"))
rel = after.get("reservation_releases") or []
chk("jejak reservation_releases: siapa/kapan/alasan", rel and rel[-1]["by"] and rel[-1]["at"]
    and rel[-1]["reason"] == "pelanggan menunda pengiriman", rel)
r = requests.get(f"{BASE}/api/inventory/rolls/available", headers=admin, timeout=30,
                 params={"product_id": p["id"], "entity_id": "ent_ksc", "limit": 50})
ids = {x["id"] for x in (r.json() or {}).get("items", [])}
chk("roll yang dilepas kembali available", alloc_rolls[0]["roll_id"] in ids)

print("\n[AS-02] PR lahir dari SO (repeat-restock) → qty boleh NAIK, tidak boleh TURUN")
r = requests.post(f"{BASE}/api/sales-orders/{so_id}/repeat-restock", headers=sadmin, timeout=60, json={
    "items": [{"product_id": p["id"], "quantity": 100, "unit": p.get("base_unit") or "meter"}],
    "reason": "uji AS-02", "submit_now": False})
chk("repeat-restock → PR", r.status_code in (200, 201), r.text)
pr = r.json().get("requisition") or r.json().get("pr") or r.json()
pr_id = pr.get("id") or pr.get("pr_id")
prdoc = requests.get(f"{BASE}/api/purchase-requisitions/{pr_id}", headers=admin, timeout=30).json()
chk("PR source so_repeat", prdoc.get("source") == "so_repeat", prdoc.get("source"))
line_no = prdoc["items"][0].get("line_no") or 1
r = requests.patch(f"{BASE}/api/purchase-requisitions/{pr_id}/lines/{line_no}", headers=admin, timeout=30,
                   json={"quantity": 80, "reason": "coba turunkan di bawah pesanan"})
chk("turun di bawah kebutuhan pesanan → 400", r.status_code == 400 and "kebutuhan pesanan" in r.text, r.text)
r = requests.patch(f"{BASE}/api/purchase-requisitions/{pr_id}/lines/{line_no}", headers=admin, timeout=30,
                   json={"quantity": 150, "reason": "MOQ supplier 150 m, sisa jadi stok"})
chk("naik 100 → 150 → 200", r.status_code == 200, r.text)
d = r.json()
li = d["items"][0]
chk("order_qty=100 · extra_qty=50 · quantity=150",
    li.get("order_qty") == 100 and li.get("extra_qty") == 50 and li.get("quantity") == 150, li)
chk("qty_history tercatat", (li.get("qty_history") or [{}])[-1].get("reason", "").startswith("MOQ"), li.get("qty_history"))
chk("total_est_amount ikut naik", float(d.get("total_est_amount") or 0) > float(prdoc.get("total_est_amount") or 0),
    (prdoc.get("total_est_amount"), d.get("total_est_amount")))
r = requests.patch(f"{BASE}/api/purchase-requisitions/{pr_id}/lines/{line_no}", headers=sales, timeout=30,
                   json={"quantity": 160, "reason": "sales coba ubah qty"})
chk("sales tanpa izin PR → 403", r.status_code == 403, r.text)

print("\n[CLEANUP]")
requests.post(f"{BASE}/api/purchase-requisitions/{pr_id}/cancel", headers=admin, timeout=30)
r = requests.post(f"{BASE}/api/sales-orders/{so_id}/cancel", headers=admin, timeout=60)
chk("SO uji dibatalkan (roll kembali)", r.status_code == 200, r.text)
print(f"\nHASIL: {len(FAILS)} FAIL")
sys.exit(1 if FAILS else 0)
