"""Seed uji frontend iterasi 299 — (A) SO dikirim PARSIAL 8/20 + uang muka 50%
(untuk `journey-revenue-prorata`), (B) SO belum dikirim + uang muka 40% (untuk
layar Laporan Uang Muka Pelanggan).

Jalankan: cd /app && python backend/tests/seed_iter299_frontend.py
Hapus   : cd /app && python backend/tests/seed_iter299_frontend.py --purge
Dokumen ditandai `_test_iter299_fe: true`.
"""
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
db = MongoClient(be.get("MONGO_URL"))[be.get("DB_NAME")]
ENT = "ent_ksc"
CUST = "cust_butik_bali"


def hdr():
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT,
            "Content-Type": "application/json"}


def purge():
    oids = [d["id"] for d in db.sales_orders.find({"_test_iter299_fe": True}, {"_id": 0, "id": 1})]
    rids = [d["id"] for d in db.ar_receipts.find({"_test_iter299_fe": True}, {"_id": 0, "id": 1})]
    cids = [c["id"] for c in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                        "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
    shids = [d["id"] for d in db.shipments.find({"order_id": {"$in": oids}}, {"_id": 0, "id": 1})]
    db.journal_entries.delete_many({"$or": [{"source_id": {"$in": oids + rids + cids + shids}},
                                            {"ref.order_id": {"$in": oids}}]
                                    + [{"source_id": {"$regex": f"^{o}:"}} for o in oids]})
    db.tax_invoices.delete_many({"order_id": {"$in": oids}})
    db.sales_orders.delete_many({"_test_iter299_fe": True})
    db.ar_receipts.delete_many({"_test_iter299_fe": True})
    db.cash_transactions.delete_many({"id": {"$in": cids}})
    db.wms_tasks.delete_many({"order_id": {"$in": oids}})
    db.shipments.delete_many({"order_id": {"$in": oids}})
    print("purged orders", oids, "receipts", rids, "shipments", shids)
    import subprocess, sys as _sys
    subprocess.run([_sys.executable, "/app/backend/tests/iter299_restore_orphan_rolls.py"],
                   check=False, capture_output=True, timeout=120)


def make_order(h, qty, pct, note):
    payload = {"customer_id": CUST, "shipping_address_id": "addr_002", "entity_id": ENT,
               "sales_name": "Ayu Permatasari",
               "items": [{"product_id": "prod_endek_bali", "quantity": qty, "unit": "yard",
                          "base_quantity": qty}]}
    r = requests.post(f"{BASE}/sales-orders", headers=h, json=payload, timeout=120)
    r.raise_for_status()
    o = r.json()
    oid = o["id"]
    db.sales_orders.update_one({"id": oid}, {"$set": {"notes": note, "_test_iter299_fe": True}})
    for p in (f"/sales-orders/{oid}/verify", f"/sales-orders/{oid}/confirm"):
        requests.post(f"{BASE}{p}", headers=h, json={}, timeout=120).raise_for_status()
    adv = round(float(o["grand_total"]) * pct, 2)
    rr = requests.post(f"{BASE}/ar-receipts", headers=h, json={
        "customer_id": CUST, "amount": adv, "method": "transfer", "entity_id": ENT,
        "notes": note, "allocations": [{"order_id": oid, "amount": adv}]}, timeout=120)
    rr.raise_for_status()
    rid = rr.json().get("id") or rr.json().get("receipt", {}).get("id")
    db.ar_receipts.update_one({"id": rid}, {"$set": {"_test_iter299_fe": True}})
    print(f"SO {o['number']} ({oid}) grand={o['grand_total']} uang muka={adv}")
    return oid, o["number"]


def seed():
    h = hdr()
    # (A) dikirim parsial 8 dari 20 yard
    oid_a, num_a = make_order(h, 20.0, 0.5, "TEST PRORATA 299 (frontend · parsial)")
    requests.post(f"{BASE}/wms/tasks/outbound-from-order/{oid_a}", headers=h,
                  json={}, timeout=120).raise_for_status()
    for t in db.wms_tasks.find({"order_id": oid_a, "flow_type": "outbound"},
                               {"_id": 0, "id": 1, "quantity": 1}):
        requests.post(f"{BASE}/outbound/tasks/{t['id']}/scan-pick", headers=h,
                      params={"actual_qty": t["quantity"]}, json={}, timeout=120).raise_for_status()
        r = requests.post(f"{BASE}/outbound/tasks/{t['id']}/dispatch", headers=h,
                          params={"ship_qty": 8.0}, json={}, timeout=120)
        r.raise_for_status()
    st = db.sales_orders.find_one({"id": oid_a}, {"_id": 0, "status": 1})["status"]
    print(f"A parsial: {num_a} status={st}")

    # (B) belum dikirim (laporan uang muka)
    oid_b, num_b = make_order(h, 12.0, 0.4, "TEST PRORATA 299 (frontend · belum kirim)")
    print(f"B belum kirim: {num_b} ({oid_b})")
    print("SEED_A", oid_a, num_a, "SEED_B", oid_b, num_b)


if __name__ == "__main__":
    if "--purge" in sys.argv:
        purge()
    else:
        seed()
