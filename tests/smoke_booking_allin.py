"""Smoke test: booking fee → komponen BOOKING all-in (Fase lanjutan)."""
import json
import os
import sys

import requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL")][0] + "/api"
S = requests.Session()
tok = S.post(f"{API}/auth/login", json={"email": "superadmin@sipro.co.id", "password": "Sipro#2026"}).json()["access_token"]
S.headers["Authorization"] = f"Bearer {tok}"


def ok(r, label):
    if r.status_code >= 300:
        print("FAIL", label, r.status_code, r.text[:400]); sys.exit(1)
    print("OK  ", label, r.status_code)
    return r.json()


# 1. skema all-in dengan komponen BOOKING
schemes = ok(S.get(f"{API}/allin-schemes?include_inactive=true"), "list schemes")["data"]
sch = next((s for s in schemes if s["code"] == "ALLIN_BOOKING_TEST"), None)
if not sch:
    sch = ok(S.post(f"{API}/allin-schemes", json={
        "code": "ALLIN_BOOKING_TEST", "name": "All-in + BOOKING (uji)",
        "items": [{"component_code": "NOTARY_FEE", "treatment": "customer_pass_through"},
                  {"component_code": "BOOKING", "treatment": "customer_pass_through"}]}), "create scheme")["data"]
print("scheme", sch["id"])

# 2. preview
pv = ok(S.get(f"{API}/allin-schemes/{sch['id']}/preview", params={"price": 850000000, "booking_fee": 5000000}), "preview")["data"]
print("  components:", [(c["code"], c["amount"], c["formula"]) for c in pv["components"]])
assert any(c["code"] == "BOOKING" and c["amount"] == 5000000 for c in pv["components"])

# 3. reservasi
units = ok(S.get(f"{API}/units", params={"status": "available", "limit": 5}), "units")["data"]
leads = ok(S.get(f"{API}/leads", params={"limit": 5}), "leads")["data"]
unit, lead = units[0], leads[-1]
deal = ok(S.post(f"{API}/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 5000000,
                                               "allin_scheme_id": sch["id"],
                                               "limit_override_reason": "Uji otomatis komponen BOOKING all-in"}), "reserve")["data"]
print("  deal", deal["id"], "costs:", [(c["code"], c["amount"]) for c in (deal.get("costs") or {}).get("components", [])])

# 4. bayar booking fee tanpa bukti → harus ditolak; dengan bukti → ok
r = S.post(f"{API}/booking-fee/deals/{deal['id']}/pay", json={"amount": 5000000, "method": "transfer", "proof_file_ids": []})
assert r.status_code in (400, 422), r.text
print("OK   pay tanpa bukti ditolak (422)")
up = ok(S.post(f"{API}/files/upload", files={"file": ("bukti.txt", b"bukti transfer dummy", "text/plain")},
               data={"owner_type": "receipt_proof", "optimize": "false"}), "upload")["data"]
pay = ok(S.post(f"{API}/booking-fee/deals/{deal['id']}/pay",
                json={"amount": 5000000, "method": "transfer", "proof_file_ids": [up["id"]]}), "pay booking fee")["data"]
print("  receipt", pay["receipt"]["receipt_no"], "deposit balance", pay["deposit"]["balance"])

# 5. konfirmasi booking → AR lahir → booking fee dialihkan ke komponen BOOKING (bukan termin)
ok(S.post(f"{API}/deals/{deal['id']}/book", json={}), "book")
import time; time.sleep(3)
ar = ok(S.get(f"{API}/finance/ar/{deal['id']}"), "ar")["data"]
print("  AR total", ar["total"], "paid", ar["paid"], "(harus 0 — booking fee tidak ke termin)")
contracts = ok(S.get(f"{API}/contracts", params={"limit": 200}), "contracts")["data"]
c = next((x for x in contracts if x["deal_id"] == deal["id"]), None)
if c:
    led = ok(S.get(f"{API}/contracts/{c['id']}/costs-ledger"), "ledger")["data"]
else:
    led = None
    # tanpa kontrak: cek langsung koleksi via endpoint invoice
print("  ledger:", json.dumps({k: led[k] for k in ("received", "invoiced", "titipan_balance")} if led else None))
if led:
    print("  receipts:", [(r["receipt_no"], r["amount"], r["method"], r.get("funding")) for r in led["receipts"]])
dep = ok(S.get(f"{API}/finance/ar/deposits"), "deposits")["data"]
d = next((x for x in dep if x["deal_id"] == deal["id"]), {})
print("  deposit entries:", [(e["type"], e["amount"]) for e in d.get("entries", [])], "balance", d.get("balance"))
assert ar["paid"] == 0 and d.get("balance") == 0
print("ALL GOOD")
