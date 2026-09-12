"""E2E: reserve with chosen scheme -> book -> convert -> contract/AR must match scheme."""
import json, sys, requests

API = "http://localhost:8001/api"
tok = requests.post(f"{API}/auth/login", json={"email": "superadmin@sipro.co.id", "password": "Sipro#2026"}).json()
TOKEN = tok.get("token") or tok.get("access_token")
H = {"Authorization": f"Bearer {TOKEN}"}
scheme_name = sys.argv[1] if len(sys.argv) > 1 else "Cash Bertahap (3x)"

opts = requests.get(f"{API}/quotations/options", headers=H).json()["data"]
scheme = next(s for s in opts["schemes"] if s["name"] == scheme_name)
unit = opts["units"][-1]
lead = requests.post(f"{API}/leads", json={"name": f"Uji Skema {scheme_name[:8]}", "phone": f"+62812{abs(hash(scheme_name)) % 10**7:07d}", "source": "manual"}, headers=H).json()["data"]
print("lead", lead["id"][:8], "unit", unit["code"], "scheme", scheme["name"], scheme.get("kind"))

r = requests.post(f"{API}/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 5000000,
                                                "scheme_id": scheme["id"], "addons": [], "kpr": {}}, headers=H)
print("reserve", r.status_code, r.text[:200] if r.status_code != 200 else "")
deal = r.json()["data"]
print("deal.scheme_id", deal.get("scheme_id", "")[:8], "explicit", deal.get("scheme_explicit"), "terms", [(t.get("label"), t.get("amount")) for t in (deal.get("pricing") or {}).get("terms", [])][:6])

up = requests.post(f"{API}/files/upload", files={"file": ("bukti.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")}, headers=H)
fid = (up.json().get("data") or up.json()).get("id") or (up.json().get("data") or {}).get("file_id")
r = requests.post(f"{API}/booking-fee/deals/{deal['id']}/pay", json={"amount": 5000000, "proof_file_ids": [fid]}, headers=H)
print("pay bf", r.status_code, r.text[:200] if r.status_code != 200 else "")
r = requests.post(f"{API}/deals/{deal['id']}/book", json={}, headers=H)
print("book", r.status_code, r.text[:200] if r.status_code != 200 else "")
pv = requests.get(f"{API}/deals/{deal['id']}/convert-preview", headers=H).json()["data"]
print("preview suggested", pv.get("suggested_scheme"), "deal_scheme", pv.get("deal_scheme"), pv.get("deal_scheme_name"), "blocks", [b.get("code") for b in pv.get("blocks", [])])
r = requests.post(f"{API}/deals/{deal['id']}/convert", json={}, headers=H)
print("convert", r.status_code, r.text[:300] if r.status_code != 200 else "")
out = r.json()["data"]
cid = out["contract"]["id"]
c = requests.get(f"{API}/contracts/{cid}", headers=H).json()["data"]
print("contract scheme", c["scheme"], c.get("payment_scheme_name"), "state", c["state"])
plan = c.get("payment_plan", {})
print("plan", plan.get("state"), plan.get("reason"), "scheme", plan.get("scheme"), [(t.get("label"), t.get("amount")) for t in plan.get("terms", [])])
if c["state"] == "draft":
    r = requests.post(f"{API}/contracts/{cid}/activate", headers=H)
    print("activate", r.status_code, r.text[:300] if r.status_code != 200 else "")
    c = requests.get(f"{API}/contracts/{cid}", headers=H).json()["data"]
    plan = c.get("payment_plan", {})
    print("plan after activate", plan.get("state"), plan.get("scheme"), [(t.get("label"), t.get("amount")) for t in plan.get("terms", [])])
inv = requests.get(f"{API}/finance/ar", params={"deal_id": deal["id"]}, headers=H)
print("AR", inv.status_code, json.dumps(inv.json())[:600])
print("customer", out["customer"]["id"])
