"""Verifikasi runtime temuan audit 2026-09-02 (F-01, F-02, F-03, F-05, F-06, F-07, F-08, E-01, E-02, U-02).
Jalankan dari /app: python backend/test_audit_2026_09_02_poc.py
Memakai DB seed (seed_reset.sh). Tidak merusak: memakai SO seed yang belum dikirim + rollback manual.
"""
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
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW})
    r.raise_for_status()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": entity})
    return s


admin = login("admin@kainnusantara.id")
kanda = login("sales3@kainnusantara.id", "ent_kanda")
admin_kanda = login("admin@kainnusantara.id", "ent_kanda")

print("\n== F-03: tagihan jasa makloon tidak dijurnal dua kali (sync ulang) ==")
r = admin.post(f"{API}/gl/sync")
ok("POST /gl/sync 200", r.status_code == 200, r.text[:120])
ok("sync tidak memposting vendor_bills makloon lagi", r.json().get("vendor_bills", 0) == 0, str(r.json()))
dups = list(db.journal_entries.aggregate([
    {"$match": {"status": {"$ne": "void"}, "reversed": {"$ne": True},
                "source_type": {"$in": ["vendor_bill", "subcon_service"]}}},
    {"$group": {"_id": "$source_id", "n": {"$sum": 1}}}, {"$match": {"n": {"$gt": 1}}}]))
ok("tidak ada bill dengan JE vendor_bill + subcon_service aktif", not dups, str(dups[:3]))

print("\n== F-05: alokasi kwitansi ke order pelanggan lain / badan usaha lain ditolak ==")
so8 = db.sales_orders.find_one({"id": "so_008"}, {"_id": 0, "customer_id": 1, "entity_id": 1, "payments": 1})
before_pay = len(so8.get("payments") or [])
r = admin.post(f"{API}/ar-receipts", json={"customer_id": "cust_toko_kain", "amount": 100000, "method": "transfer",
                                            "allocations": [{"order_id": "so_008", "amount": 100000}]})
ok("pelanggan lain → 400", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
r = admin_kanda.post(f"{API}/ar-receipts", json={"customer_id": so8["customer_id"], "amount": 100000, "method": "transfer",
                                                  "entity_id": "ent_kanda",
                                                  "allocations": [{"order_id": "so_008", "amount": 100000}]})
ok("badan usaha lain → 403", r.status_code == 403, f"{r.status_code} {r.text[:100]}")
so8b = db.sales_orders.find_one({"id": "so_008"}, {"_id": 0, "payments": 1})
ok("F-06: tidak ada pembayaran yatim tertulis di so_008", len(so8b.get("payments") or []) == before_pay)

print("\n== F-06: alokasi ke-2 tidak valid → alokasi ke-1 dicabut (tidak yatim) ==")
so8 = db.sales_orders.find_one({"id": "so_008"}, {"_id": 0, "customer_id": 1, "grand_total": 1, "payments": 1})
r = admin.post(f"{API}/ar-receipts", json={"customer_id": so8["customer_id"], "amount": 99999999, "method": "transfer",
                                            "allocations": [{"order_id": "so_008", "amount": 1000},
                                                            {"order_id": "so_008", "amount": 99999000}]})
ok("melebihi outstanding → 400", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
so8c = db.sales_orders.find_one({"id": "so_008"}, {"_id": 0, "payments": 1})
ok("payments[] so_008 tidak bertambah", len(so8c.get("payments") or []) == len(so8.get("payments") or []))

print("\n== F-07: simulate-payment menolak lebih-bayar & sinkron paid_total ==")
r = admin.post(f"{API}/sales-orders/so_007/simulate-payment", json={"amount": 1000000, "method": "transfer"})
ok("order lunas → 400", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
so7 = db.sales_orders.find_one({"id": "so_007"}, {"_id": 0, "grand_total": 1, "payments": 1})
ok("Σpayments so_007 ≤ grand_total",
   sum(float(p.get("amount", 0) or 0) for p in so7["payments"]) <= float(so7["grand_total"]) + 0.01)

print("\n== F-08: netting melebihi piutang balik ditolak ==")
open_t = db.interco_transactions.find_one({"role": "seller", "seller_entity_id": "ent_kanda", "buyer_entity_id": "ent_ksc",
                                           "status": {"$in": ["confirmed", "invoiced", "received", "partially_settled"]}},
                                          {"_id": 0, "id": 1, "status": 1, "grand_total": 1})
if open_t:
    r = admin.post(f"{API}/interco/settlements", json={"payer_entity_id": "ent_ksc", "payee_entity_id": "ent_kanda",
                                                       "method": "netting", "transactions": [{"interco_id": open_t["id"]}]})
    ok("netting 4,44jt > piutang balik KSC→Kanda (522rb) → 4xx", 400 <= r.status_code < 500, f"{r.status_code} {r.text[:140]}")
    r = admin.post(f"{API}/interco/settlements", json={"payer_entity_id": "ent_ksc", "payee_entity_id": "ent_kanda",
                                                       "method": "transfer", "transactions": [{"interco_id": open_t["id"], "applied_amount": 1000}]})
    ok("metode transfer tetap boleh", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
else:
    print("  [SKIP] tidak ada transaksi interco terbuka Kanda→KSC")

print("\n== E-01: stock-breakdown tidak membocorkan SO PT lain ==")
r = kanda.get(f"{API}/products/prod_batik_mega/stock-breakdown")
ok("200 untuk sales Kanda", r.status_code == 200, r.text[:100])
res = r.json().get("reservations", []) if r.status_code == 200 else []
ok("reservations hanya ent_kanda", all(x.get("entity_id") == "ent_kanda" for x in res), str([x.get("number") for x in res]))
ok("reservations tanpa field sensitif", all("grand_total" not in x and "shipping_address" not in x for x in res))

print("\n== E-02: cycle-count/sessions ber-scope entitas ==")
r = admin_kanda.get(f"{API}/cycle-count/sessions")
ok("Kanda tidak melihat sesi KSC", r.status_code == 200 and all(s.get("entity_id") != "ent_ksc" for s in r.json()),
   str([s.get("id") for s in r.json()]) if r.status_code == 200 else r.text[:80])
r = admin_kanda.get(f"{API}/cycle-count/sessions/cc_seed_001")
ok("detail sesi KSC dari konteks Kanda → 404", r.status_code == 404, str(r.status_code))
r = admin.get(f"{API}/cycle-count/sessions")
ok("KSC tetap melihat sesinya", r.status_code == 200 and len(r.json()) >= 2)

print("\n== U-02: /documents/{id}/print ada ==")
r = admin.post(f"{API}/documents/generate", json={"document_type": "invoice", "source_id": "so_001"})
ok("generate 200", r.status_code == 200, r.text[:100])
if r.status_code == 200:
    r2 = admin.get(f"{API}/documents/{r.json()['id']}/print")
    ok("print 200 + HTML", r2.status_code == 200 and "<" in r2.text, str(r2.status_code))

print("\n== F-01: pendapatan diposting SAAT dispatch (bukan menunggu restart) ==")
so6 = db.sales_orders.find_one({"id": "so_006"}, {"_id": 0, "status": 1, "grand_total": 1})
print("  so_006 status awal:", so6.get("status"))
if so6.get("status") == "reserved":
    for step in ("verify", "confirm"):
        r = admin.post(f"{API}/sales-orders/so_006/{step}", json={})
        print(f"  {step}: {r.status_code} {r.text[:80] if r.status_code >= 400 else ''}")
    r = admin.post(f"{API}/wms/tasks/outbound-from-order/so_006", json={})
    print("  outbound tasks:", r.status_code, r.text[:100] if r.status_code >= 400 else "")
    tasks = list(db.wms_tasks.find({"order_id": "so_006", "flow_type": "outbound"}, {"_id": 0, "id": 1, "quantity": 1, "status": 1}))
    for t in tasks:
        r = admin.post(f"{API}/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": t["quantity"]})
        r2 = admin.post(f"{API}/outbound/tasks/{t['id']}/dispatch")
        print(f"  task {t['id']}: pick {r.status_code} dispatch {r2.status_code} {r2.text[:100] if r2.status_code >= 400 else ''}")
    so6 = db.sales_orders.find_one({"id": "so_006"}, {"_id": 0, "status": 1})
    je = db.journal_entries.find_one({"source_type": "sales_order", "source_id": "so_006", "status": {"$ne": "void"}}, {"_id": 0, "number": 1})
    ok(f"so_006 status={so6.get('status')} → JE pendapatan langsung ada", so6.get("status") in ("shipped", "partially_shipped") and je is not None,
       str(je))
    cogs = db.journal_entries.find_one({"source_type": "sales_cogs", "source_id": "so_006", "status": {"$ne": "void"}}, {"_id": 0, "number": 1})
    ok("JE HPP so_006 langsung ada", cogs is not None, str(cogs))
else:
    print("  [SKIP] so_006 bukan reserved")

print("\n== F-02: /gl/sync tetap 200 walau ada periode tertutup ==")
r = admin.post(f"{API}/gl/sync")
ok("POST /gl/sync 200 & mengembalikan skipped_closed/errors", r.status_code == 200 and "skipped_closed" in r.json(), r.text[:160])

print(f"\nPASS {R['pass']} | FAIL {R['fail']}")
sys.exit(1 if R["fail"] else 0)
