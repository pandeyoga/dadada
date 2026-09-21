"""Iterasi 281 — skenario AS-01: SO bernilai besar TIDAK butuh persetujuan nilai manajer.

Jalankan: cd /app/backend/tests && python iter281_as01_scenario.py
"""
import os
import json
import requests

def _env():
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    return ""

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env()).rstrip("/")
PWD = "demo12345"
OK = FAIL = 0

def chk(label, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  PASS · {label}")
    else:
        FAIL += 1
        print(f"  FAIL · {label} {extra}")

def hdr(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}

admin = hdr("admin@kainnusantara.id")
sales = hdr("sales@kainnusantara.id")
sadmin = hdr("salesadmin@kainnusantara.id")

print("\n[BE-1] aturan ambang sales_order = satu baris 0..∞ tanpa peran")
r = requests.get(f"{BASE}/api/approval-rules?doc_type=sales_order", headers=admin, timeout=30)
chk("GET /api/approval-rules 200", r.status_code == 200, r.text[:200])
rules = r.json()
rules = rules.get("items", rules) if isinstance(rules, dict) else rules
so_rules = [x for x in rules if x.get("doc_type") == "sales_order"]
chk("hanya 1 baris sales_order", len(so_rules) == 1, json.dumps(so_rules)[:400])
if so_rules:
    rl = so_rules[0]
    chk("min_amount 0", float(rl.get("min_amount") or 0) == 0, rl)
    chk("max_amount null/kosong", rl.get("max_amount") in (None, "", 0) or rl.get("max_amount") is None, rl)
    chk("role kosong", not (rl.get("approver_role") or rl.get("role") or ""), rl)

print("\n[BE-2] pelanggan berlimit kredit besar + produk berstok")
custs = requests.get(f"{BASE}/api/customers?limit=100", headers=admin, timeout=30).json()
custs = custs.get("items", custs) if isinstance(custs, dict) else custs
cands = [c for c in custs if (c.get("credit") or {}).get("status") == "active"]
cands.sort(key=lambda c: -float((c.get("credit") or {}).get("available_credit") or 0))
print("   kandidat:", [(c["name"], (c.get("credit") or {}).get("available_credit")) for c in cands][:5])
chk("ada pelanggan limit >= 60jt aktif",
    bool(cands) and float((cands[0].get("credit") or {}).get("available_credit") or 0) >= 60_000_000)
cust = cands[0]
addr = ((cust.get("shipping_addresses") or cust.get("addresses")) or [{}])[0].get("id", "")
chk("pelanggan punya alamat kirim", bool(addr), cust.get("addresses"))
CREDIT = float((cust.get("credit") or {}).get("available_credit") or 0)

prods = requests.get(f"{BASE}/api/products?limit=300", headers=admin, timeout=30).json()
prods = prods.get("items", prods) if isinstance(prods, dict) else prods
avail = []
for p in prods:
    price = float(p.get("price") or p.get("selling_price") or 0)
    stock = float(p.get("available_qty") or p.get("stock_qty") or p.get("total_stock") or 0)
    if price > 0:
        avail.append((p, price, stock))
avail.sort(key=lambda t: -t[1])
print("   produk teratas:", [(p["name"], pr, st) for p, pr, st in avail[:5]])

# target total 60jt-150jt tapi <= 250jt limit
line = None
for p, price, stock in avail:
    qty = round(65_000_000 / price, 2)
    if 60_000_000 <= qty * price <= CREDIT * 0.9:
        line = {"product_id": p["id"], "quantity": round(qty, 2), "unit": p.get("unit") or "meter"}
        print(f"   pilih {p['name']} qty={line['quantity']} harga={price} ≈ Rp {qty*price:,.0f}")
        break
chk("bisa menyusun baris >= Rp 60 jt dari stok", line is not None)

print("\n[BE-3] sales membuat SO bernilai besar")
so = None
if line and addr:
    r = requests.post(f"{BASE}/api/sales-orders", headers=sales, timeout=60, json={
        "customer_id": cust["id"], "shipping_address_id": addr, "items": [line],
        "sales_name": "Ayu Permatasari", "entity_id": "ent_ksc", "allow_backorder": True,
        "confirm_mixed_lot": True})
    chk("POST /api/sales-orders 200", r.status_code in (200, 201), r.text[:500])
    if r.status_code in (200, 201):
        so = r.json().get("order") or r.json()
        print("   nomor:", so.get("number"), "status:", so.get("status"),
              "grand_total:", so.get("grand_total"),
              "approval_required:", so.get("approval_required"),
              "pending:", so.get("pending_approvals"))
        chk("grand_total >= 50jt", float(so.get("grand_total") or 0) >= 50_000_000, so.get("grand_total"))
        chk("approval_required False", so.get("approval_required") in (False, None), so.get("approval_required"))
        pend = so.get("pending_approvals") or []
        kinds = [p.get("kind") or p.get("type") or p for p in pend] if isinstance(pend, list) else pend
        chk("tidak ada pending 'nilai'/'value'", not any(str(k) in ("nilai", "value", "amount") for k in kinds), kinds)

print("\n[BE-4] salesadmin verify → confirm tanpa manajer")
if so:
    sid = so["id"]
    r = requests.post(f"{BASE}/api/sales-orders/{sid}/verify", headers=sadmin, timeout=60, json={"note": "QA iter281"})
    chk("POST verify 200", r.status_code == 200, r.text[:400])
    r = requests.post(f"{BASE}/api/sales-orders/{sid}/confirm", headers=sadmin, timeout=60, json={})
    chk("POST confirm 200", r.status_code == 200, r.text[:400])
    d = requests.get(f"{BASE}/api/sales-orders/{sid}", headers=sadmin, timeout=30).json()
    d = d.get("order") or d
    print("   status akhir:", d.get("status"))
    chk("status confirmed", d.get("status") == "confirmed", d.get("status"))

print("\n[BE-5] kontrol negatif: SO melebihi limit kredit tetap butuh persetujuan kredit")
blocked = next((c for c in custs if (c.get("credit_limit") or 0) > 0 and (c.get("credit_limit") or 0) < 60_000_000), None)
if blocked and line:
    a2 = ((blocked.get("shipping_addresses") or blocked.get("addresses")) or [{}])[0].get("id", "")
    print("   pelanggan:", blocked.get("name"), "limit:", blocked.get("credit_limit"))
    if a2:
        r = requests.post(f"{BASE}/api/sales-orders", headers=sales, timeout=60, json={
            "customer_id": blocked["id"], "shipping_address_id": a2, "items": [line],
            "sales_name": "Ayu Permatasari", "entity_id": "ent_ksc", "allow_backorder": True,
            "confirm_mixed_lot": True})
        print("   status:", r.status_code, str(r.text)[:300])
        if r.status_code in (200, 201):
            o2 = r.json().get("order") or r.json()
            pend = o2.get("pending_approvals") or []
            print("   pending:", pend, "approval_required:", o2.get("approval_required"))
            chk("SO melebihi kredit → butuh persetujuan kredit",
                bool(pend) or o2.get("approval_required") is True, o2)
        else:
            chk("SO melebihi kredit ditolak/ditahan (409 juga sah)", r.status_code in (400, 409), r.status_code)
else:
    print("   (dilewati: tidak ada pelanggan limit kecil)")

print(f"\n=== AS-01 SELESAI · PASS {OK} · FAIL {FAIL} ===")
