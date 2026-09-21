"""Smoke feedback klien 2026-09 (K-1, K-2, K-4, K-5) — jalankan: python backend/tests/smoke_feedback_klien_2026_09.py"""
import sys, uuid, requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
PW = "demo12345"


def sess(email, entity="ent_ksc"):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}); r.raise_for_status()
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": entity})
    return s


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


admin = sess("admin@kainnusantara.id")
tag = uuid.uuid4().hex[:6].upper()
sales = [u for u in admin.get(f"{API}/sales-users").json()]
ok(len(sales) >= 3, f"ada ≥3 akun sales: {len(sales)}")
s1, s2, s3 = sales[0]["id"], sales[1]["id"], sales[2]["id"]

# ── K-1 + K-2: nama EYD otomatis & nomor WA dinormalisasi ────────────────────
body = {"name": f"pt TEST_klien {tag.lower()} tbk", "pic_name": "BUDI santoso, s.e.", "phone": "0812-3456-7890",
        "city": "Bandung", "address": "Jl. Mawar 1", "type": "Retail", "assigned_sales_id": s1, "entity_id": "ent_ksc"}
r = admin.post(f"{API}/customers", json=body)
ok(r.status_code == 200, f"buat pelanggan: {r.status_code} {r.text[:150]}")
c = r.json()
ok(c["name"] == f"PT Test_klien {tag.lower().capitalize()} Tbk" or c["name"].startswith("PT Test_klien"), f"K-1 nama usaha EYD: {c['name']!r}")
ok(c["pic_name"] == "Budi Santoso, S.E.", f"K-1 nama orang EYD: {c['pic_name']!r}")
ok(c["phone"] == "6281234567890", f"K-2 nomor WA dinormalisasi: {c['phone']!r}")
bad = admin.post(f"{API}/customers", json={**body, "name": f"TEST_bad {tag}", "phone": "0812abc"})
ok(bad.status_code == 422, f"K-2 nomor WA berhuruf ditolak: {bad.status_code}")
bad2 = admin.post(f"{API}/customers", json={**body, "name": f"TEST_bad2 {tag}", "phone": "12345"})
ok(bad2.status_code == 422, f"K-2 nomor terlalu pendek ditolak: {bad2.status_code}")
patch = admin.patch(f"{API}/customers/{c['id']}", json={"data": {"pic_name": "siti AMINAH", "phone": "+62 813 1111 2222"}})
ok(patch.status_code == 200 and patch.json()["pic_name"] == "Siti Aminah" and patch.json()["phone"] == "6281311112222",
   f"K-1/K-2 saat PATCH: {patch.status_code} {patch.json().get('pic_name')!r} {patch.json().get('phone')!r}")
patch_bad = admin.patch(f"{API}/customers/{c['id']}", json={"data": {"phone": "telp kantor"}})
ok(patch_bad.status_code == 400, f"K-2 PATCH nomor tidak valid ditolak 400: {patch_bad.status_code}")
addr = admin.post(f"{API}/customers/{c['id']}/addresses", json={"label": "Gudang", "recipient_name": "andi WIJAYA", "phone": "08561234567", "city": "Cimahi", "address": "Jl. Melati 2"})
ok(addr.status_code == 200, f"tambah alamat: {addr.status_code}")
a = [x for x in addr.json()["addresses"] if x["label"] == "Gudang"][0]
ok(a["recipient_name"] == "Andi Wijaya" and a["phone"] == "628561234567", f"K-1/K-2 alamat: {a['recipient_name']!r} {a['phone']!r}")

# ── K-4: termin CBD / NET60 / NET90 ada ───────────────────────────────────────
terms = admin.get(f"{API}/payment-terms").json()
terms = terms if isinstance(terms, list) else terms.get("items", [])
codes = {t["code"]: t for t in terms}
ok({"CBD", "NET60", "NET90"} <= set(codes), f"K-4 termin baru tersedia: {sorted(set(codes) & {'CBD', 'NET60', 'NET90'})}")
ok(codes["NET60"]["net_days"] == 60 and codes["NET90"]["net_days"] == 90, "K-4 NET60=60 hari, NET90=90 hari")

# ── K-5: group sales maks 2 + split otomatis 50-50 ───────────────────────────
r3 = admin.patch(f"{API}/customers/{c['id']}", json={"data": {"sales_team": [
    {"sales_id": s1, "role": "pic", "split_pct": 40}, {"sales_id": s2, "role": "co", "split_pct": 30}, {"sales_id": s3, "role": "co", "split_pct": 30}]}})
ok(r3.status_code == 400 and "maksimal 2" in r3.text.lower(), f"K-5 tim 3 orang ditolak: {r3.status_code} {r3.text[:100]}")
r2 = admin.patch(f"{API}/customers/{c['id']}", json={"data": {"sales_team": [
    {"sales_id": s1, "role": "pic", "split_pct": 0}, {"sales_id": s2, "role": "co", "split_pct": 0}]}})
ok(r2.status_code == 200, f"K-5 tim 2 orang split kosong diterima: {r2.status_code} {r2.text[:120]}")
team = r2.json()["sales_team"]
ok(sorted(m["split_pct"] for m in team) == [50.0, 50.0], f"K-5 split otomatis 50-50: {[m['split_pct'] for m in team]}")

# bersihkan
admin.delete(f"{API}/customers/{c['id']}")
print("ALL PASS")
