"""Smoke 2026-09 sesi 3: K-8 entitas, giliran Anda, Kebersihan Data. Jalankan: python backend/tests/smoke_turn_hygiene_entities.py"""
import sys, time, uuid, requests

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

# ── K-8 entitas ──────────────────────────────────────────────────────────────
ents = admin.get(f"{API}/entities", headers={"X-Entity-Id": "all"}).json()
ents = ents if isinstance(ents, list) else ents.get("items", [])
by_id = {e["id"]: e for e in ents}
ok(by_id["ent_ksc"]["legal_name"] == "Sukacita Textile", f"ent_ksc → Sukacita Textile: {by_id['ent_ksc']['legal_name']!r}")
ok(by_id["ent_kanda"]["legal_name"] == "Kanda Fabric", f"ent_kanda → Kanda Fabric: {by_id['ent_kanda']['legal_name']!r}")
cst = [e for e in ents if e.get("doc_prefix") == "CST"]
ok(len(cst) == 1 and cst[0]["legal_name"] == "CV Cipta Sandang Textile" and cst[0]["default_tax_mode"] == "ppn",
   f"CV Cipta Sandang Textile ada (PKP, prefix CST): {[(e['legal_name'], e['default_tax_mode']) for e in cst]}")
ok(by_id["ent_ksc"]["doc_prefix"] == "KSC" and by_id["ent_kanda"]["doc_prefix"] == "KANDA", "kode dokumen lama dipertahankan")

# ── Giliran Anda ─────────────────────────────────────────────────────────────
wh = sess("warehouse@kainnusantara.id")
before = {n["id"] for n in wh.get(f"{API}/notifications", params={"limit": 200}).json() if n.get("type") == "turn"} if isinstance(wh.get(f"{API}/notifications").json(), list) else set()
r = admin.post(f"{API}/sample-requests", json={"customer_id": "cust_toko_kain", "product_id": "prod_batik_mega", "length": 0.5, "notes": f"TEST_turn_{tag}", "entity_id": "ent_ksc"})
ok(r.status_code == 200, f"buat permintaan sampel: {r.status_code}")
smp = r.json()
time.sleep(2)
notes = wh.get(f"{API}/notifications", params={"limit": 200}).json()
notes = notes if isinstance(notes, list) else notes.get("items", [])
mine = [n for n in notes if n.get("type") == "turn" and smp["number"] in n.get("title", "")]
ok(len(mine) == 1 and "Giliran Anda" in mine[0]["title"] and not mine[0]["read"], f"gudang menerima 'Giliran Anda' untuk {smp['number']}: {[m['title'] for m in mine]}")
ok(mine[0].get("link") == "operations", f"tautan mengarah ke operasi gudang: {mine[0].get('link')}")
admin.post(f"{API}/sample-requests/{smp['id']}/cancel", json={"reason": "TEST"})
# scan terjadwal (dipanggil langsung lewat job scheduler API bila ada, else tunggu after_audit)
run = admin.post(f"{API}/scheduler/jobs/turn_scan/run")
print("   scheduler run:", run.status_code, run.text[:120])
time.sleep(1)
notes = wh.get(f"{API}/notifications", params={"limit": 200, "include_read": "true"}).json()
notes = notes if isinstance(notes, list) else notes.get("items", [])
mine_after = [n for n in notes if n.get("type") == "turn" and smp["number"] in n.get("title", "")]
resolved = [n for n in mine_after if n.get("resolution")]
ok(len(resolved) >= 1 or all(n.get("read") for n in mine_after) or not mine_after,
   f"giliran gudang ditutup setelah dibatalkan: {[(n['read'], n.get('resolution')) for n in mine_after]}")
tmap = admin.get(f"{API}/turn-notifications/map").json()
ok(any(t["collection"] == "sales_orders" and t["status"] == "waiting_approval" and "manager" in t["roles"] for t in tmap), "peta giliran memuat SO waiting_approval → manager")

# ── Kebersihan Data ──────────────────────────────────────────────────────────
s = admin.get(f"{API}/data-hygiene/summary").json()
ok(s["total"] >= 1 and "customers" in s["rules"], f"ringkasan kebersihan data: total={s['total']} aktif={s['active']}")
log = admin.get(f"{API}/data-hygiene/log", params={"collection": "customers", "limit": 50}).json()
ok(log["total"] >= 1 and all(l["collection"] == "customers" for l in log["items"]), f"log pelanggan: {log['total']} catatan")
entry = next((l for l in log["items"] if not l["reverted"] and l.get("trigger") != "location_fix"), None)
ok(entry is not None, "ada catatan yang bisa dikembalikan")
from pymongo import MongoClient
_db = MongoClient("mongodb://localhost:27017")["test_database"]
getc = lambda: _db[entry["collection"]].find_one({"id": entry["doc_id"]}, {"_id": 0})
rv = admin.post(f"{API}/data-hygiene/log/{entry['id']}/revert")
ok(rv.status_code == 200 and rv.json()["reverted"], f"kembalikan per-record: {rv.status_code}")
cust_after = getc()
first = entry["changes"][0]
ok(cust_after.get(first["field"]) == first["before"], f"nilai '{first['field']}' kembali ke sebelum: {str(cust_after.get(first['field']))[:40]}")
again = admin.post(f"{API}/data-hygiene/log/{entry['id']}/revert")
ok(again.status_code == 409, f"kembalikan dua kali ditolak 409: {again.status_code}")
run2 = admin.post(f"{API}/data-hygiene/run").json()
still = getc()
ok(still.get(first["field"]) == first["before"], "record yang dikembalikan DIKUNCI dari perapian ulang")
ul = admin.post(f"{API}/data-hygiene/{entry['collection']}/{entry['doc_id']}/unlock")
ok(ul.status_code == 200, f"buka kunci: {ul.status_code}")
run3 = admin.post(f"{API}/data-hygiene/run", params={"collection": "customers"}).json()
fixed = getc()
ok(fixed.get(first["field"]) == first["after"], f"setelah buka kunci, perapian ulang menerapkan lagi ({run3['changed']} record)")
pv = admin.get(f"{API}/data-hygiene/preview").json()
ok(isinstance(pv, list), f"pratinjau tersedia ({len(pv)} record masih akan berubah)")
mgr = sess("manager@kainnusantara.id")
ok(mgr.get(f"{API}/data-hygiene/summary").status_code == 200, "manajer boleh melihat ringkasan")
ok(mgr.post(f"{API}/data-hygiene/run").status_code == 403, "manajer tidak boleh menjalankan perapian (403)")
print("ALL PASS")
