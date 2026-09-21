"""Smoke lokasi tervalidasi (2026-09): python backend/tests/smoke_wilayah.py"""
import sys, uuid, requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"}); r.raise_for_status()
s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": "ent_ksc"})
tag = uuid.uuid4().hex[:6].upper()


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        sys.exit(1)


prov = s.get(f"{API}/wilayah/provinces").json()
ok(len(prov) == 38, f"38 provinsi: {len(prov)}")
jb = next(p for p in prov if p["name"] == "Jawa Barat")
reg = s.get(f"{API}/wilayah/regencies", params={"province_code": jb["code"]}).json()
bdg = next(r for r in reg if r["name"] == "Kota Bandung")
ok(len(reg) == 27, f"Jawa Barat 27 kab/kota: {len(reg)}")
dis = s.get(f"{API}/wilayah/districts", params={"regency_code": bdg["code"]}).json()
ok(len(dis) == 30 and all(d["postal_codes"] for d in dis), f"Kota Bandung 30 kecamatan berkode pos: {len(dis)}")
hit = s.get(f"{API}/wilayah/postal-code/40115").json()
ok(hit and hit[0]["city"] == "Kota Bandung" and hit[0]["district"] == "Bandung Wetan", f"kode pos 40115 → {hit[0]['district']}, {hit[0]['city']}")
ok(s.get(f"{API}/wilayah/postal-code/99999").json() == [], "kode pos 99999 tidak ada")
sr = s.get(f"{API}/wilayah/search", params={"q": "surakarta"}).json()
ok(any(x["name"] == "Kota Surakarta" for x in sr), "pencarian 'surakarta' menemukan Kota Surakarta")

base = {"name": f"TEST_LOK {tag}", "pic_name": "Tester", "phone": "081200001111", "address": "Jl. Uji 1", "type": "Retail", "assigned_sales_id": "user_sales_01", "entity_id": "ent_ksc"}
# STRICT — kode pos tidak konsisten dengan kota
bad = s.post(f"{API}/customers", json={**base, "province": "Jawa Barat", "city": "Kota Bandung", "postal_code": "10110"})
ok(bad.status_code == 400 and "bukan kode pos wilayah Kota Bandung" in bad.text, f"kode pos Jakarta untuk Bandung ditolak: {bad.status_code} {bad.text[:90]}")
bad2 = s.post(f"{API}/customers", json={**base, "province": "Jawa Barat", "city": "Kota Ngawur", "postal_code": "40115"})
ok(bad2.status_code == 400 and "tidak dikenal" in bad2.text, f"kota tak dikenal ditolak: {bad2.status_code}")
bad3 = s.post(f"{API}/customers", json={**base, "province_code": "33", "city_code": "32.73", "postal_code": "40115"})
ok(bad3.status_code == 400 and "tidak berada di provinsi" in bad3.text, f"kota bukan di provinsinya ditolak: {bad3.status_code}")
bad4 = s.post(f"{API}/customers", json={**base, "city_code": "32.73", "district_code": "32.73.09", "postal_code": "40111"})
ok(bad4.status_code == 400 and "bukan kode pos kecamatan" in bad4.text, f"kode pos bukan milik kecamatan ditolak: {bad4.status_code}")
good = s.post(f"{API}/customers", json={**base, "province_code": "32", "city_code": "32.73", "district_code": "32.73.09", "postal_code": "40115", "city": "Kota Bandung"})
ok(good.status_code == 200, f"alamat valid diterima: {good.status_code} {good.text[:80]}")
c = good.json()
ok(c["location_status"] == "verified" and c["province"] == "Jawa Barat" and c["district"] == "Bandung Wetan" and c["country_code"] == "ID", f"dokumen tersimpan lengkap: {c['province']}/{c['city']}/{c['district']}/{c['postal_code']} {c['location_status']}")
ok(c["addresses"][0]["postal_code"] == "40115" and c["addresses"][0]["province_code"] == "32", "alamat utama ikut membawa lokasi")
# kode pos → isi otomatis
auto = s.post(f"{API}/customers", json={**base, "name": f"TEST_LOK2 {tag}", "postal_code": "57111"})
ok(auto.status_code == 200 and auto.json()["city"] == "Kota Surakarta" and auto.json()["province"] == "Jawa Tengah", f"kode pos saja → kota/provinsi terisi: {auto.json().get('city')}")
# LENIENT — klien lama hanya kirim city
old = s.post(f"{API}/customers", json={**base, "name": f"TEST_LOK3 {tag}", "city": "Solo"})
ok(old.status_code == 200 and old.json()["city"] == "Kota Surakarta" and old.json()["location_status"] == "partial", f"klien lama city='Solo' → {old.json().get('city')} ({old.json().get('location_status')})")
old2 = s.post(f"{API}/customers", json={**base, "name": f"TEST_LOK4 {tag}", "city": "QA City"})
ok(old2.status_code == 200 and old2.json()["location_status"] == "unverified", "klien lama kota asing tidak ditolak, ditandai unverified")
# PATCH lokasi
p = s.patch(f"{API}/customers/{c['id']}", json={"data": {"postal_code": "40111"}})
ok(p.status_code == 400, f"PATCH kode pos yang bukan milik kecamatan tersimpan ditolak: {p.status_code}")
p2 = s.patch(f"{API}/customers/{c['id']}", json={"data": {"district_code": "32.73.01", "postal_code": "40151"}})
ok(p2.status_code == 200 and p2.json()["district"] and p2.json()["postal_code"] == "40151", f"PATCH kecamatan+kode pos konsisten diterima: {p2.json().get('district')}")
# alamat tambahan wajib konsisten
a_bad = s.post(f"{API}/customers/{c['id']}/addresses", json={"label": "Gudang", "recipient_name": "Andi", "city": "Kota Bandung", "address": "Jl. X", "postal_code": "60111"})
ok(a_bad.status_code == 400, f"alamat tambahan kode pos Surabaya untuk Bandung ditolak: {a_bad.status_code}")
# supplier & luar negeri
sup = s.post(f"{API}/suppliers", json={"name": f"TEST_SUP {tag}", "country": "Tiongkok", "country_code": "CN", "city": "Shaoxing", "postal_code": "312000", "origin_type": "import"})
ok(sup.status_code == 200 and sup.json()["location_status"] == "foreign", f"pemasok luar negeri: {sup.status_code} {sup.json().get('location_status')}")
sup_bad = s.post(f"{API}/suppliers", json={"name": f"TEST_SUP2 {tag}", "city": "Kota Bandung", "postal_code": "1234"})
ok(sup_bad.status_code == 400 and "5 angka" in sup_bad.text, f"pemasok kode pos 4 angka ditolak: {sup_bad.status_code}")
for cid in (c["id"], auto.json()["id"], old.json()["id"], old2.json()["id"]):
    s.delete(f"{API}/customers/{cid}")
s.delete(f"{API}/suppliers/{sup.json()['id']}")
print("ALL PASS")

# ── Gudang, lokasi gudang, karyawan, backlog alamat (sesi 5) ─────────────────
wh_bad = s.post(f"{API}/warehouses", json={"code": f"TEST-WH-{tag}", "name": f"TEST_WH {tag}", "city": "Kota Bandung", "postal_code": "60111"})
ok(wh_bad.status_code == 400, f"gudang kode pos Surabaya untuk Bandung ditolak: {wh_bad.status_code}")
wh_ok = s.post(f"{API}/warehouses", json={"code": f"TEST-WH-{tag}", "name": f"TEST_WH {tag}", "city_code": "32.73", "district_code": "32.73.09", "postal_code": "40115"})
ok(wh_ok.status_code == 200 and wh_ok.json().get("location_status") == "verified" and wh_ok.json().get("city") == "Kota Bandung", f"gudang valid: {wh_ok.status_code} {wh_ok.json().get('city')}")
site = s.post(f"{API}/warehouse-sites", json={"name": f"TEST_SITE {tag}", "city_code": "33.72", "postal_code": "57111"})
ok(site.status_code == 200 and site.json().get("location_status") == "verified" and site.json().get("province") == "Jawa Tengah", f"lokasi gudang valid: {site.status_code} {site.json().get('province')}")
site_bad = s.patch(f"{API}/warehouse-sites/{site.json()['id']}", json={"postal_code": "40115"})
ok(site_bad.status_code == 400, f"PATCH lokasi gudang kode pos lain kota ditolak: {site_bad.status_code}")
emp = s.post(f"{API}/hr/employees", json={"name": f"TEST_EMP {tag}", "nik": f"NIK{tag}", "phone": "081200009999", "address": "Jl. K", "city_code": "32.73", "postal_code": "40115", "entity_id": "ent_ksc"})
ok(emp.status_code == 200 and emp.json().get("location_status") == "verified", f"karyawan lokasi valid: {emp.status_code} {emp.text[:80]}")
emp_bad = s.patch(f"{API}/hr/employees/{emp.json()['id']}", json={"data": {"postal_code": "10110"}})
ok(emp_bad.status_code == 400, f"PATCH karyawan kode pos lain kota ditolak: {emp_bad.status_code}")
ub = s.get(f"{API}/data-hygiene/unverified-locations").json()
ok(ub["total"] >= 1 and "customers" in ub["counts"], f"backlog alamat belum terverifikasi: {ub['total']} ({ub['counts']})")
row = next((r for r in ub["items"] if r["collection"] == "customers"), None)
ok(row is not None, f"ada pelanggan lama belum terverifikasi: {row and row['doc_label']}")
fx_bad = s.post(f"{API}/data-hygiene/location/customers/{row['doc_id']}", json={"province_code": "32", "city_code": "32.73"})
ok(fx_bad.status_code == 400 and "kode pos" in fx_bad.text.lower(), f"lengkapi tanpa kode pos ditolak: {fx_bad.status_code}")
fx = s.post(f"{API}/data-hygiene/location/customers/{row['doc_id']}", json={"province_code": "31", "city_code": "31.71", "postal_code": "10110"})
ok(fx.status_code == 200 and fx.json()["location_status"] == "verified" and fx.json()["province"] == "Daerah Khusus Ibukota Jakarta" or "Jakarta" in fx.json()["province"], f"lengkapi alamat pelanggan lama: {fx.status_code} {fx.json().get('city')}")
ub2 = s.get(f"{API}/data-hygiene/unverified-locations", params={"collection": "customers"}).json()
ok(all(r["doc_id"] != row["doc_id"] for r in ub2["items"]), "pelanggan yang dilengkapi hilang dari backlog")
from pymongo import MongoClient
_db = MongoClient("mongodb://localhost:27017")["test_database"]
_c = _db.customers.find_one({"id": row["doc_id"]}, {"_id": 0, "addresses": 1, "location_status": 1})
ok(_c["location_status"] == "verified" and any(a.get("postal_code") == "10110" for a in _c.get("addresses", []) if a.get("is_primary")), "alamat utama pelanggan ikut dilengkapi")
# kembalikan pelanggan seed ke keadaan semula agar idempoten
_db.customers.update_one({"id": row["doc_id"]}, {"$set": {k: row.get(k, "") for k in ("country", "country_code", "province", "province_code", "city", "city_code", "district", "district_code", "postal_code")}, "$unset": {"location_status": ""}})
_db.customers.update_one({"id": row["doc_id"]}, {"$set": {"addresses": [{**a, **{k: "" for k in ("province", "province_code", "city_code", "district", "district_code", "postal_code")}, "city": row.get("city", "")} if a.get("is_primary") else a for a in _c.get("addresses", [])]}})
_db.warehouses.delete_one({"id": wh_ok.json()["id"]}); _db.warehouse_sites.delete_one({"id": site.json()["id"]}); _db.hr_employees.delete_one({"id": emp.json()["id"]})
print("ALL PASS (sesi 5)")
