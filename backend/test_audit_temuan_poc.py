"""POC audit temuan 2026-09-02 (P1-1..P1-3, L-*, G-*, X-5). Jalankan: python backend/test_audit_temuan_poc.py
Mutasi ringan pada data seed (pengiriman uji dibuat baru; dibersihkan di akhir)."""
import io
import os
import sys

import requests
from pymongo import MongoClient

API = os.environ.get("API_URL", "http://localhost:8001").rstrip("/") + "/api"
db = MongoClient("mongodb://localhost:27017")["test_database"]
PW = "demo12345"
R = {"pass": 0, "fail": 0}


def ok(name, cond, detail=""):
    R["pass" if cond else "fail"] += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def login(email, entity="ent_ksc"):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}); r.raise_for_status()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": entity})
    return s, r.json()["user"]


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (40, 40), (200, 30, 30)).save(b, format="PNG"); return b.getvalue()


admin, _ = login("admin@kainnusantara.id")
driver_email = db.users.find_one({"role": "driver"}, {"email": 1})["email"]
driver, drv = login(driver_email)
sales, _ = login("sales@kainnusantara.id")

print("\n== L-8: SJ non-dispatched tidak bisa diangkut ==")
ship = db.shipments.find_one({"logistics_id": {"$in": [None, ""]}, "status": "dispatched", "entity_id": "ent_ksc"}, {"_id": 0, "id": 1, "shipment_no": 1})
db.shipments.update_one({"id": ship["id"]}, {"$set": {"status": "cancelled_test"}})
r = admin.post(f"{API}/logistics/deliveries", json={"shipment_ids": [ship["id"]], "mode": "own_fleet"})
ok("SJ status bukan dispatched → 400", r.status_code == 400 and "dispatch" in r.text.lower(), r.text[:120])
db.shipments.update_one({"id": ship["id"]}, {"$set": {"status": "dispatched"}})

print("\n== Buat pengiriman uji (armada sendiri, sopir ditugaskan) ==")
r = admin.post(f"{API}/logistics/deliveries", json={"shipment_ids": [ship["id"]], "mode": "own_fleet", "vehicle_plate": "B 1 TEST",
                                                     "driver_name": drv["name"], "driver_user_id": drv["id"], "eta": "2026-01-01"})
ok("create 200", r.status_code == 200, r.text[:120]); D = r.json(); did = D["id"]
r = admin.post(f"{API}/logistics/deliveries", json={"shipment_ids": [db.shipments.find_one({"logistics_id": {"$in": [None, ""]}, "status": "dispatched", "entity_id": "ent_ksc", "id": {"$ne": ship['id']}}, {"id": 1})["id"]], "mode": "expedition", "courier_name": "JNE"})
ok("create pengiriman ke-2 (tanpa sopir) 200", r.status_code == 200, r.text[:120]); D2 = r.json(); did2 = D2["id"]

print("\n== P1-1: sopir hanya menulis pada pengirimannya ==")
r = driver.post(f"{API}/logistics/deliveries/{did2}/photos", files={"file": ("a.png", png(), "image/png")}, data={"kind": "load"})
ok("foto pada pengiriman BUKAN tugasnya → 403", r.status_code == 403, f"{r.status_code} {r.text[:100]}")
r = driver.post(f"{API}/logistics/deliveries/{did2}/transition", json={"to": "loaded"})
ok("transisi pada pengiriman bukan tugasnya → 403", r.status_code == 403, str(r.status_code))
r = driver.get(f"{API}/logistics/deliveries/{did2}")
ok("detail pengiriman lain tetap bisa dilihat (keputusan pemilik)", r.status_code == 200, str(r.status_code))
r = driver.post(f"{API}/logistics/deliveries/{did}/photos", files={"file": ("a.png", png(), "image/png")}, data={"kind": "load"})
ok("foto pada pengiriman miliknya → 200", r.status_code == 200, r.text[:100])

print("\n== L-10/P1-3: Dimuat → bongkar kembali ke Disiapkan (manage + alasan) ==")
r = driver.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "loaded"})
ok("sopir tandai Dimuat → 200", r.status_code == 200 and r.json()["status"] == "loaded", r.text[:100])
r = driver.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "prepared", "reason": "salah tekan"})
ok("sopir bongkar → 403 (hanya manage)", r.status_code == 403, str(r.status_code))
r = admin.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "prepared"})
ok("admin bongkar tanpa alasan → 400", r.status_code == 400, r.text[:100])
r = admin.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "prepared", "reason": "salah tekan tombol"})
ok("admin bongkar dengan alasan → prepared", r.status_code == 200 and r.json()["status"] == "prepared", r.text[:100])
ok("riwayat mencatat alasan bongkar", any("salah tekan tombol" in (t.get("note") or "") for t in r.json()["timeline"]))
r = admin.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "loaded"})
ok("Dimuat lagi → 200", r.status_code == 200)

print("\n== L-2: validasi koordinat + hapus posisi ==")
r = driver.post(f"{API}/logistics/deliveries/{did}/positions", json={"location": "Cikampek", "lat": 999, "lng": -999})
ok("lat 999 → 422", r.status_code == 422, str(r.status_code))
r = driver.post(f"{API}/logistics/deliveries/{did}/positions", json={"location": "Cikampek", "lat": -6.4, "lng": 107.4})
ok("posisi valid → 200", r.status_code == 200, r.text[:100]); pos_id = r.json()["positions"][-1]["id"]
r = driver.delete(f"{API}/logistics/deliveries/{did}/positions/{pos_id}")
ok("sopir hapus posisi → 403 (manage)", r.status_code == 403, str(r.status_code))
r = admin.delete(f"{API}/logistics/deliveries/{did}/positions/{pos_id}")
ok("admin hapus posisi → 200", r.status_code == 200, r.text[:100])

print("\n== L-3: my-route hanya pengiriman aktif ==")
r = driver.post(f"{API}/logistics/my-route", json={"ids": [did]})
ok("my-route aktif → 200", r.status_code == 200, r.text[:100])

print("\n== L-4 + L-9: pesan gabungan & notifikasi sales ==")
r = admin.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "in_transit"})
ok("berangkat → 200", r.status_code == 200, r.text[:120])
r = driver.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "delivered"})
ok("terkirim tanpa POD & nama → satu pesan menyebut keduanya", r.status_code == 400 and "POD" in r.text and "NAMA PENERIMA" in r.text, r.text[:160])
n_before = db.notifications.count_documents({"type": "logistics_delivered"})
driver.post(f"{API}/logistics/deliveries/{did}/photos", files={"file": ("p.png", png(), "image/png")}, data={"kind": "pod"})
r = driver.post(f"{API}/logistics/deliveries/{did}/transition", json={"to": "delivered", "receiver_name": "Bu Ani"})
ok("terkirim → 200", r.status_code == 200, r.text[:100])
n_after = db.notifications.count_documents({"type": "logistics_delivered"})
ok("notifikasi 'logistics_delivered' ke sales/admin sales dibuat", n_after > n_before, f"{n_before}→{n_after}")
r = driver.post(f"{API}/logistics/my-route", json={"ids": [did]})
ok("L-3: my-route pada pengiriman terkirim → 400", r.status_code == 400, str(r.status_code))
r = admin.get(f"{API}/logistics/summary")
ok("L-1: summary.today ada (WIB)", r.status_code == 200 and "today" in r.json(), str(r.json().get("today")))

print("\n== P1-2: SJ menyimpan logistics_number/status (chip) ==")
sj = db.shipments.find_one({"id": ship["id"]}, {"_id": 0, "logistics_number": 1, "logistics_status": 1})
ok("shipments.logistics_status = delivered", sj.get("logistics_status") == "delivered" and sj.get("logistics_number"), str(sj))

print("\n== G-3/G-8: status AI & uji koneksi ==")
r = admin.get(f"{API}/design-gallery-ai/status")
ok("status mengandung verified/daily_limit/cost", r.status_code == 200 and {"verified", "daily_limit", "cost_per_image_usd"} <= set(r.json()), r.text[:160])
r = admin.post(f"{API}/admin/integrations/gemini/test")
ok("uji koneksi tanpa key → 400", r.status_code == 400, r.text[:100])
r = admin.put(f"{API}/admin/integrations", json={"gemini_daily_limit": 1})
ok("set batas harian 1 → 200", r.status_code == 200 and r.json()["gemini"]["daily_limit"] == 1, r.text[:120])
g = db.design_gallery.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "id": 1})
r1 = admin.post(f"{API}/design-gallery/{g['id']}/ai-illustrate", json={"mode": "mockup", "prompt": "uji batas harian"})
r2 = admin.post(f"{API}/design-gallery/{g['id']}/ai-illustrate", json={"mode": "mockup", "prompt": "uji batas harian 2"})
ok("ilustrasi ke-1 200, ke-2 ditolak (batas 1/hari)", r1.status_code == 200 and r2.status_code == 400 and "Batas" in r2.text, f"{r1.status_code}/{r2.status_code} {r2.text[:100]}")
admin.put(f"{API}/admin/integrations", json={"gemini_daily_limit": 10})

print("\n== G-6: komentar → notifikasi desainer; hapus komentar sendiri ==")
fid = r1.json()["id"] if r1.status_code == 200 else None
if fid:
    nb = db.notifications.count_documents({"type": "design_ai_comment"})
    r = admin.post(f"{API}/design-gallery/{g['id']}/files/{fid}/comments", json={"text": "Perbesar motif"})
    ok("komentar admin → 200", r.status_code == 200, r.text[:100]); cid = r.json()["id"]
    ok("notifikasi desainer dibuat", db.notifications.count_documents({"type": "design_ai_comment"}) > nb)
    d_email = db.users.find_one({"role": "designer"}, {"email": 1})["email"]
    designer, _ = login(d_email)
    r = designer.delete(f"{API}/design-gallery/{g['id']}/files/{fid}/comments/{cid}")
    ok("desainer hapus komentar admin → 400", r.status_code == 400, f"{r.status_code} {r.text[:80]}")
    r = admin.delete(f"{API}/design-gallery/{g['id']}/files/{fid}/comments/{cid}")
    ok("admin hapus komentarnya → 200", r.status_code == 200, r.text[:80])
    admin.delete(f"{API}/design-gallery/{g['id']}/files/{fid}")

print("\n== X-5: divisi Logistik ==")
r = admin.get(f"{API}/rnd/divisions")
ok("divisi 'logistics' ada", r.status_code == 200 and any(d.get("id") == "logistics" for d in (r.json() if isinstance(r.json(), list) else r.json().get("divisions", r.json().get("items", [])))), r.text[:120])

# bersihkan pengiriman uji
db.logistics_deliveries.delete_many({"id": {"$in": [did, did2]}})
db.shipments.update_many({"logistics_id": {"$in": [did, did2]}}, {"$set": {"logistics_id": "", "logistics_number": "", "logistics_status": ""}})
db.notifications.delete_many({"type": {"$in": ["logistics_delivered", "design_ai_comment"]}})
print(f"\nPASS {R['pass']} | FAIL {R['fail']}")
sys.exit(1 if R["fail"] else 0)
