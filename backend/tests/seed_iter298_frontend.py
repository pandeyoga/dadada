"""Seed uji frontend iterasi 298 (KEB-PDPT) — 1 SO belum dikirim + uang muka 30%.

Jalankan: cd /app && python backend/tests/seed_iter298_frontend.py
Dokumen ditandai `_test_kebpdpt_fe: true` (SO + kwitansi) agar mudah dihapus.
Hapus: python backend/tests/seed_iter298_frontend.py --purge
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


def hdr():
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT,
            "Content-Type": "application/json"}


def purge():
    oids = [d["id"] for d in db.sales_orders.find({"_test_kebpdpt_fe": True}, {"_id": 0, "id": 1})]
    rids = [d["id"] for d in db.ar_receipts.find({"_test_kebpdpt_fe": True}, {"_id": 0, "id": 1})]
    cids = [c["id"] for c in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                        "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
    db.journal_entries.delete_many({"source_id": {"$in": oids + rids + cids}})
    db.tax_invoices.delete_many({"order_id": {"$in": oids}})
    db.sales_orders.delete_many({"_test_kebpdpt_fe": True})
    db.ar_receipts.delete_many({"_test_kebpdpt_fe": True})
    db.cash_transactions.delete_many({"id": {"$in": cids}})
    print("purged", oids, rids)
    import subprocess, sys as _sys
    subprocess.run([_sys.executable, "/app/backend/tests/iter299_restore_orphan_rolls.py"],
                   check=False, capture_output=True, timeout=120)


def seed():
    h = hdr()
    payload = {"customer_id": "cust_butik_bali", "shipping_address_id": "addr_002",
               "entity_id": ENT, "sales_name": "Ayu Permatasari",
               "items": [{"product_id": "prod_endek_bali", "quantity": 15.0, "unit": "yard",
                          "base_quantity": 15.0}]}
    r = requests.post(f"{BASE}/sales-orders", headers=h, json=payload, timeout=120)
    r.raise_for_status()
    o = r.json()
    oid = o["id"]
    db.sales_orders.update_one({"id": oid}, {"$set": {"notes": "TEST KEB-PDPT (frontend)",
                                                      "_test_kebpdpt_fe": True}})
    for p in (f"/sales-orders/{oid}/verify", f"/sales-orders/{oid}/confirm"):
        rr = requests.post(f"{BASE}{p}", headers=h, json={}, timeout=120)
        rr.raise_for_status()
    adv = round(float(o["grand_total"]) * 0.30, 2)
    rr = requests.post(f"{BASE}/ar-receipts", headers=h, json={
        "customer_id": "cust_butik_bali", "amount": adv, "method": "transfer", "entity_id": ENT,
        "notes": "TEST KEB-PDPT (frontend)",
        "allocations": [{"order_id": oid, "amount": adv}]}, timeout=120)
    rr.raise_for_status()
    db.ar_receipts.update_one({"id": rr.json()["id"]}, {"$set": {"_test_kebpdpt_fe": True}})
    print("SEEDED order", oid, o["number"], "grand_total", o["grand_total"], "advance", adv,
          "receipt", rr.json()["number"])


if __name__ == "__main__":
    if "--purge" in sys.argv:
        purge()
    else:
        seed()
