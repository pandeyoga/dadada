"""Bukti runtime T-09 (audit 2026-09): saran reorder menghormati rnd.lifecycle_enforcement.
Membuat 1 produk uji labdip + 1 produk produksi (ROP terpenuhi), menguji 3 mode, lalu
membersihkan. Pakai: python3 backend/tests/iter313_t09_reorder_lifecycle_probe.py
"""
import json
import os
import sys

import requests
from pymongo import MongoClient

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/") + "/api"
db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]


def login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "demo12345"}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "all"}


def cfg_set(h, value):
    r = requests.put(f"{BASE}/config/values", headers=h, timeout=30, json={"items": [
        {"key": "rnd.lifecycle_enforcement", "value": value, "scope_type": "global", "scope_id": "",
         "reason": "probe T-09"}]})
    assert r.status_code == 200, r.text


PRODS = [
    {"id": "prod_t09_labdip", "sku": "T09-LABDIP", "name": "Uji T-09 labdip", "status": "active",
     "lifecycle": "labdip", "reorder_point": 500, "reorder_qty": 100, "base_unit": "meter", "price": 1000},
    {"id": "prod_t09_produksi", "sku": "T09-PROD", "name": "Uji T-09 produksi", "status": "active",
     "lifecycle": "produksi", "reorder_point": 500, "reorder_qty": 100, "base_unit": "meter", "price": 1000},
]


def main():
    h = login("admin@kainnusantara.id")
    db.products.delete_many({"id": {"$in": [p["id"] for p in PRODS]}})
    db.products.insert_many([dict(p) for p in PRODS])
    before = db.config_values.find_one({"key": "rnd.lifecycle_enforcement", "scope_type": "global"}, {"_id": 0, "value": 1})
    fails = 0
    try:
        for mode, expect_labdip, expect_warn in (("block", False, None), ("warn", True, True), ("off", True, False)):
            cfg_set(h, mode)
            r = requests.get(f"{BASE}/purchase-requisitions/reorder-suggestions", headers=h, timeout=60)
            rows = {x["product_id"]: x for x in r.json().get("items", [])}
            lab, prod = rows.get("prod_t09_labdip"), rows.get("prod_t09_produksi")
            ok1 = (lab is not None) == expect_labdip
            ok2 = prod is not None and not prod.get("lifecycle_warning")
            ok3 = expect_warn is None or (lab or {}).get("lifecycle_warning") == expect_warn
            fails += (not ok1) + (not ok2) + (not ok3)
            print(f"mode={mode:5s} HTTP {r.status_code} labdip_muncul={lab is not None} (harap {expect_labdip}) "
                  f"warning={(lab or {}).get('lifecycle_warning')} (harap {expect_warn}) "
                  f"produksi_muncul={prod is not None} produksi_warning={(prod or {}).get('lifecycle_warning')} "
                  f"→ {'PASS' if ok1 and ok2 and ok3 else 'FAIL'}")
            if mode == "warn" and lab:
                print("   baris labdip:", json.dumps({k: lab[k] for k in ("product_id", "lifecycle", "lifecycle_warning", "suggested_qty")}))
    finally:
        cfg_set(h, (before or {}).get("value") or "block")
        db.products.delete_many({"id": {"$in": [p["id"] for p in PRODS]}})
        print("cleanup: produk uji dihapus, mode dikembalikan ke", (before or {}).get("value") or "block")
    print("HASIL:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
