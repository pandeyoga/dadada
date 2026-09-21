"""Coverage tambahan untuk fitur lokasi tervalidasi (2026-09) — endpoint countries,
POST /api/wilayah/validate, PATCH supplier, POST makloon dengan lokasi.
Dijalankan langsung: `python backend/tests/test_wilayah_extra.py` (tanpa pytest).
"""
import sys
import uuid
import requests

with open("/app/frontend/.env") as f:
    BASE = [l.split("=", 1)[1].strip() for l in f if l.startswith("REACT_APP_BACKEND_URL=")][0]
API = BASE.rstrip("/") + "/api"

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
r.raise_for_status()
s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": "ent_ksc"})
tag = uuid.uuid4().hex[:6].upper()

failed = []

def check(cond, name, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        failed.append(name)

# --- 1) GET /api/wilayah/countries (Indonesia pertama) ---
c = s.get(f"{API}/wilayah/countries")
check(c.status_code == 200, "GET /wilayah/countries 200", f"status={c.status_code}")
countries = c.json() if c.status_code == 200 else []
check(len(countries) > 0 and (countries[0].get("code") == "ID" or countries[0].get("name") == "Indonesia"),
      "Indonesia berada di posisi pertama", detail=str(countries[:2]))

# --- 2) POST /api/wilayah/validate valid ---
v = s.post(f"{API}/wilayah/validate", json={"city": "Bandung", "postal_code": "40115"})
check(v.status_code == 200, "POST /wilayah/validate {city:Bandung, postal:40115} 200", f"status={v.status_code} body={v.text[:120]}")
vd = v.json() if v.status_code == 200 else {}
check(vd.get("valid") is True and vd.get("city") == "Kota Bandung" and vd.get("location_status") == "verified",
      "validate → valid, Kota Bandung, verified", detail=str(vd))

# --- 3) POST /api/wilayah/validate inkonsisten ---
v2 = s.post(f"{API}/wilayah/validate", json={"province": "Jawa Barat", "city": "Kota Bandung", "postal_code": "10110"})
check(v2.status_code == 400 and "bukan kode pos wilayah Kota Bandung" in v2.text,
      "validate {Jabar,Bandung,10110} → 400 pesan menuntun", detail=f"{v2.status_code} {v2.text[:120]}")

# --- 4) Pelanggan kode pos 4 angka ---
base = {"name": f"TEST_LOKX {tag}", "pic_name": "Tester", "phone": "081200001111", "address": "Jl. Uji",
        "type": "Retail", "assigned_sales_id": "user_sales_01", "entity_id": "ent_ksc"}
bad = s.post(f"{API}/customers", json={**base, "postal_code": "1234"})
check(bad.status_code == 400 and "5 angka" in bad.text, "Pelanggan postal '1234' → 400 pesan '5 angka'",
      detail=f"{bad.status_code} {bad.text[:120]}")

# --- 5) Supplier PATCH lokasi tidak konsisten ---
sup_ok = s.post(f"{API}/suppliers", json={"name": f"TEST_SUP_BDG {tag}", "country_code": "ID",
                                          "province_code": "32", "city_code": "32.73", "postal_code": "40115"})
check(sup_ok.status_code == 200, "Buat supplier Bandung valid", f"{sup_ok.status_code} {sup_ok.text[:120]}")
sup_id = sup_ok.json().get("id") if sup_ok.status_code == 200 else None

if sup_id:
    pp = s.patch(f"{API}/suppliers/{sup_id}", json={"data": {"postal_code": "10110"}})
    check(pp.status_code == 400, "PATCH supplier Bandung ganti kode pos Jakarta → 400",
          detail=f"{pp.status_code} {pp.text[:120]}")

# --- 6) Makloon dengan lokasi valid ---
mk = s.post(f"{API}/makloons", json={"name": f"TEST_MAK {tag}", "phone": "081200003333",
                                     "country_code": "ID", "province_code": "32", "city_code": "32.73",
                                     "district_code": "32.73.09", "postal_code": "40115",
                                     "process_types": ["tenun"], "entity_id": "ent_ksc"})
check(mk.status_code == 200, "Buat makloon Bandung valid → 200", f"{mk.status_code} {mk.text[:200]}")
if mk.status_code == 200:
    mj = mk.json()
    check(mj.get("location_status") == "verified" and mj.get("city") == "Kota Bandung"
          and mj.get("district") == "Bandung Wetan",
          "Makloon dokumen tersimpan verified + kota/kecamatan lengkap", detail=str({k: mj.get(k) for k in ("city","district","province","location_status")}))
    mk_id = mj.get("id")
else:
    mk_id = None

# --- Cleanup ---
if sup_id:
    s.delete(f"{API}/suppliers/{sup_id}")
if mk_id:
    s.delete(f"{API}/makloons/{mk_id}")

print("\n" + ("ALL PASS" if not failed else f"FAIL {len(failed)}: {failed}"))
sys.exit(0 if not failed else 1)
