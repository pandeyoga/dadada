"""Bukti runtime T-01 Langkah 1 (audit 2026-09): resolve-escalation aman diulang.
Panggil endpoint dua kali dengan adjusted_qty sama; panggilan kedua WAJIB 409 dan roll
yang dilepas TIDAK bertambah. Snapshot/restore EKSAK koleksi yang disentuh (nol residu).
Pakai: python3 backend/tests/iter313_t01_resolve_escalation_probe.py
"""
import os
import sys

import requests
from pymongo import MongoClient

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/") + "/api"
db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
COLS = ["wms_tasks", "sales_orders", "inventory_rolls", "inventory_balances", "inventory_movements", "audit_logs"]


def login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "demo12345"}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "all"}


def roll_state(order_id, product_id, wh):
    held = list(db.inventory_rolls.find({"reserved_ref.id": order_id, "product_id": product_id, "warehouse_id": wh},
                                        {"_id": 0, "length_remaining": 1}))
    avail = list(db.inventory_rolls.find({"product_id": product_id, "warehouse_id": wh, "status": "available"},
                                         {"_id": 0, "length_remaining": 1}))
    return {"held_qty": sum(r["length_remaining"] for r in held), "held_n": len(held),
            "avail_qty": sum(r["length_remaining"] for r in avail), "avail_n": len(avail)}


def main():
    task = db.wms_tasks.find_one({"flow_type": "outbound", "status": "created", "allocation_id": {"$exists": True},
                                  "picked_qty": 0}, {"_id": 0})
    if not task:
        print("RALAT: tidak ada task outbound 'created' ber-allocation_id di data demo")
        return 2
    order = db.sales_orders.find_one({"id": task["order_id"]}, {"_id": 0, "number": 1, "payments": 1, "status": 1})
    print(f"task {task['id']} qty={task['quantity']} order={order['number']} ({order['status']}, payments={len(order.get('payments') or [])})")
    snap = {c: list(db[c].find({})) for c in COLS}
    fails = 0
    try:
        wh, mg = login("warehouse@kainnusantara.id"), login("manager@kainnusantara.id")
        r = requests.post(f"{BASE}/outbound/tasks/{task['id']}/escalate", headers=wh, params={"reason": "probe T-01"}, timeout=30)
        print("escalate:", r.status_code, r.json().get("status"), (r.json().get("escalation") or {}).get("status"))
        s0 = roll_state(task["order_id"], task["product_id"], task["warehouse_id"])
        adj = round(float(task["quantity"]) - 5, 2)
        r1 = requests.post(f"{BASE}/outbound/tasks/{task['id']}/resolve-escalation", headers=mg,
                           params={"adjusted_qty": adj, "resolution_notes": "probe 1"}, timeout=60)
        s1 = roll_state(task["order_id"], task["product_id"], task["warehouse_id"])
        r2 = requests.post(f"{BASE}/outbound/tasks/{task['id']}/resolve-escalation", headers=mg,
                           params={"adjusted_qty": adj, "resolution_notes": "probe 2 (ulang-jalan)"}, timeout=60)
        s2 = roll_state(task["order_id"], task["product_id"], task["warehouse_id"])
        t_after = db.wms_tasks.find_one({"id": task["id"]}, {"_id": 0, "status": 1, "quantity": 1, "escalation.status": 1})
        print(f"sebelum        : {s0}")
        print(f"panggilan 1    : HTTP {r1.status_code} → {s1}")
        print(f"panggilan 2    : HTTP {r2.status_code} {r2.text[:110]} → {s2}")
        print(f"task sesudah   : {t_after}")
        chk = [
            ("panggilan 1 = 200", r1.status_code == 200),
            ("roll dilepas tepat 5 pada panggilan 1", abs((s0["held_qty"] - s1["held_qty"]) - 5) < 0.01),
            ("panggilan 2 = 409", r2.status_code == 409),
            ("roll TIDAK dilepas lagi pada panggilan 2", abs(s1["held_qty"] - s2["held_qty"]) < 0.01 and s1["avail_qty"] == s2["avail_qty"]),
            ("escalation.status = resolved & task packing", (t_after.get("escalation") or {}).get("status") == "resolved" and t_after.get("status") == "packing"),
        ]
        for name, ok in chk:
            fails += 0 if ok else 1
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    finally:
        for c, docs in snap.items():
            db[c].delete_many({})
            if docs:
                db[c].insert_many(docs)
        print("restore: koleksi", COLS, "dipulihkan eksak")
    print("HASIL:", "PASS" if not fails else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
