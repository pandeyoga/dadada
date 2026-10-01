"""Probe: SP3K → skema pencairan otomatis → pencairan hanya lewat tahapan → AR & jurnal."""
import io, sys, requests
BASE = "http://localhost:8001/api"
PW = "Sipro#2026"
cid = sys.argv[1]

def login(e):
    return {"Authorization": "Bearer " + requests.post(f"{BASE}/auth/login", json={"email": e, "password": PW}).json()["access_token"]}

def ok(c, m):
    print("PASS" if c else "FAIL", m)
    if not c: sys.exit(1)

h = login("superadmin@sipro.co.id")
fin = login("finance@sipro.co.id")
c = requests.get(f"{BASE}/contracts/{cid}", headers=h).json()["data"]
kv = requests.get(f"{BASE}/contracts/{cid}/kpr", headers=h).json()["data"]
print("stage", kv.get("stage"), "next", kv.get("next_stage"))
if kv.get("next_stage") == "sp3k":
    up = requests.post(f"{BASE}/files/upload", headers=h, files={"file": ("sp3k.pdf", io.BytesIO(b"%PDF-1.4 demo"), "application/pdf")},
                       data={"owner_type": "contract", "owner_id": cid, "optimize": "false"})
    fid = up.json()["data"]["id"] if up.status_code == 200 else None
    bd = c.get("breakdown") or {}
    plafon = int(bd.get("nett_price") or bd.get("gross_price") or c.get("net_price") or c.get("price") or 0) - 50_000_000
    r = requests.post(f"{BASE}/contracts/{cid}/kpr/stage/sp3k", headers=h,
                      json={"file_id": fid, "plafon": plafon, "tenor_months": 180, "rate": 7.5, "number": "SP3K/DEMO/1"})
    ok(r.status_code == 200, f"sp3k: {r.status_code} {r.text[:120]}")
kv = requests.get(f"{BASE}/contracts/{cid}/kpr", headers=h).json()["data"]
app = kv["application"]
ok(app.get("tranches") and app.get("disbursement_scheme_auto"), f"skema pencairan otomatis terpasang: {app.get('disbursement_scheme_name')} tahap={[(t['code'], t['amount'], t['condition']) for t in app['tranches']]}")
# akad
if kv.get("next_stage") == "akad_kredit":
    r = requests.post(f"{BASE}/contracts/{cid}/kpr/stage/akad_kredit", headers=h, json={"notary": "Notaris Demo", "place": "Jakarta"})
    ok(r.status_code == 200, f"akad: {r.status_code} {r.text[:120]}")
# AR before
ar = requests.get(f"{BASE}/finance/ar", headers=fin, params={"deal_id": c["deal_id"]}).json()
inv = next((i for i in ar.get("data", []) if i.get("deal_id") == c["deal_id"]), None)
print("AR sebelum: total", inv and inv.get("total"), "paid", inv and inv.get("paid"), "outstanding", inv and inv.get("outstanding"))
# free amount must be rejected
r = requests.post(f"{BASE}/contracts/{cid}/kpr/disbursements", headers=fin, json={"amount": 12345678})
ok(r.status_code == 400 and "tahap" in r.text.lower(), f"nominal bebas ditolak: {r.json().get('detail','')[:100]}")
# tranche disbursement
t = app["tranches"][0]
r = requests.post(f"{BASE}/contracts/{cid}/kpr/disbursements", headers=fin, json={"tranche_code": t["code"], "note": "Bank cair T1"})
print("disburse", r.status_code, r.text[:200])
ok(r.status_code == 200, "pencairan tahap T1 tercatat")
app2 = r.json()["data"]
d = [x for x in app2["disbursements"] if x["status"] != "dibatalkan"][-1]
print("kuitansi", d["receipt_no"], "amount", d["amount"], "deposit_excess", d["deposit_excess"])
ar = requests.get(f"{BASE}/finance/ar", headers=fin, params={"deal_id": c["deal_id"]}).json()
inv2 = next((i for i in ar.get("data", []) if i.get("deal_id") == c["deal_id"]), None)
print("AR sesudah: paid", inv2.get("paid"), "outstanding", inv2.get("outstanding"), "status", inv2.get("status"))
ok(inv2["paid"] - (inv["paid"] if inv else 0) == d["amount"] - d["deposit_excess"], "piutang berkurang sebesar pencairan (tanpa titipan)")
# journals
r = requests.get(f"{BASE}/gl/journals", headers=fin, params={"q": d["receipt_no"], "limit": 20})
print("journals", r.status_code, r.text[:600])
print("ALL PASS")
