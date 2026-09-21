"""Probe runtime sesi 9: klaim ship-to-supplier · simulate-payment · closing reopen/reclose;
riwayat sampel di 360 pelanggan; inbound complete mengembalikan created_rolls.
Jalankan: python scripts/probe_sesi9.py"""
import asyncio
import os
import pathlib
import sys
import uuid

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
FAILS = []
LOCK = {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}


def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {info}" if info else ""))
    if not ok:
        FAILS.append(name)


async def login(email, pw="demo12345"):
    c = httpx.AsyncClient(base_url=API, timeout=60)
    r = await c.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    c.headers["X-Entity-Id"] = "ent_ksc"
    return c


async def main():
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    admin = await login("admin@kainnusantara.id")

    # ── simulate-payment: kunci → 409; balapan → satu 200; paid_total tepat 1× ──
    so = db.sales_orders.find_one({"entity_id": "ent_ksc", "status": {"$in": ["confirmed", "shipped", "done", "delivered"]}, "payment_status": {"$ne": "paid"},
                                   "saga_lock": {"$exists": False}, "order_type": {"$ne": "sample"}}, {"_id": 0})
    check("ada SO KSC belum lunas untuk uji", bool(so))
    if so:
        gt = float(so.get("grand_total") or 0); paid = float(so.get("paid_total") or 0); amt = round(min(1000.0, max(gt - paid, 1.0)), 2)
        db.sales_orders.update_one({"id": so["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/sales-orders/{so['id']}/simulate-payment", json={"amount": amt, "method": "transfer", "created_by": "probe"})
        check("simulate-payment saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
        await admin.post(f"/saga-locks/sales_orders/{so['id']}/release")
        rs = await asyncio.gather(*[admin.post(f"/sales-orders/{so['id']}/simulate-payment", json={"amount": amt, "method": "transfer", "created_by": "probe"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0, "paid_total": 1, "saga_lock": 1})
        check("2× simulate-payment bersamaan → satu 200 + satu 409; paid_total naik tepat 1×", codes == [200, 409] and round(float(after["paid_total"]) - paid, 2) == amt and "saga_lock" not in after, f"{codes} paid {paid}→{after['paid_total']}")

    # ── ship-to-supplier: kunci → 409/400 ──
    pret = db.purchase_returns.find_one({"supplier_flow": True}, {"_id": 0, "id": 1}) or db.purchase_returns.find_one({}, {"_id": 0, "id": 1})
    if pret:
        db.purchase_returns.update_one({"id": pret["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/purchase-returns/{pret['id']}/ship-to-supplier", json={"notes": "probe", "carrier": "", "tracking_no": ""})
        check("ship-to-supplier saat terkunci → 409 atau 400 transisi-dulu", r.status_code in (400, 409), f"{r.status_code} {r.text[:100]}")
        db.purchase_returns.update_one({"id": pret["id"]}, {"$unset": {"saga_lock": ""}})

    # ── closing reopen / reclose: dokumen sintetis status closed tanpa JE ──
    cid = f"cls_probe9_{uuid.uuid4().hex[:8]}"
    db.period_closings.insert_one({"id": cid, "entity_id": "ent_ksc", "period_type": "month", "period_key": "2020-01", "start_date": "2020-01-01", "end_date": "2020-01-31",
                                   "status": "closed", "journal_entry_id": None, "net_income": 0, "created_at": "2026-09-05T00:00:00+00:00"})
    db.period_closings.update_one({"id": cid}, {"$set": {"saga_lock": LOCK}})
    r = await admin.post(f"/finance/closing/{cid}/reopen")
    check("closing reopen saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
    locks = (await admin.get("/saga-locks")).json()
    check("kunci period_closings tampil di /saga-locks", any(l["collection"] == "period_closings" and l["id"] == cid for l in locks))
    await admin.post(f"/saga-locks/period_closings/{cid}/release")
    rs = await asyncio.gather(admin.post(f"/finance/closing/{cid}/reopen"), admin.post(f"/finance/closing/{cid}/reclose"))
    codes = sorted(x.status_code for x in rs)
    doc = db.period_closings.find_one({"id": cid}, {"_id": 0})
    check("reopen & reclose bersamaan → tepat satu 200, satu 4xx; tanpa saga_lock", codes.count(200) == 1 and all(c < 500 for c in codes) and "saga_lock" not in doc, f"{codes} status={doc.get('status')}")
    db.journal_entries.delete_many({"source_id": cid}); db.period_closings.delete_one({"id": cid})

    # ── 360 pelanggan: riwayat sampel ──
    smp = db.sample_requests.find_one({"status": "done"}, {"_id": 0, "customer_id": 1, "id": 1})
    if smp:
        r = await admin.get(f"/customers/{smp['customer_id']}/360")
        j = r.json() if r.status_code == 200 else {}
        check("GET /customers/{id}/360 memuat sample_history + stats.samples_cut", r.status_code == 200 and any(s["id"] == smp["id"] for s in j.get("sample_history", [])) and (j.get("stats") or {}).get("samples_cut", 0) >= 1, f"{r.status_code} n={len(j.get('sample_history', []))}")
    else:
        check("ada sampel done untuk uji 360", False)

    # ── inbound complete → created_rolls ──
    prod = db.products.find_one({"stage": {"$ne": "yarn"}}, {"_id": 0, "id": 1, "base_unit": 1, "name": 1})
    tid = f"task_probe9_{uuid.uuid4().hex[:8]}"
    db.wms_tasks.insert_one({"id": tid, "flow_type": "inbound", "status": "qc_check", "entity_id": "ent_ksc", "owner_entity_id": "ent_ksc", "product_id": prod["id"], "product_name": prod["name"],
                             "warehouse_id": "wh_jakarta", "quantity": 3.0, "received_qty": 3.0, "expected_qty": 3.0, "unit": prod.get("base_unit") or "meter", "created_at": "2026-09-05T00:00:00+00:00", "updated_at": "2026-09-05T00:00:00+00:00"})
    wh = await login("wh.admin@kainnusantara.id")
    r = await wh.post(f"/inbound/tasks/{tid}/complete", json={"supplier_lot": "LOT-P9", "dye_lot": "DYE-P9"})
    rolls = (r.json() if r.status_code == 200 else {}).get("created_rolls") or []
    check("inbound complete → 200 dengan created_rolls[roll_no,length,grade,lot]", r.status_code == 200 and rolls and all(k in rolls[0] for k in ("roll_no", "length", "grade", "lot")), f"{r.status_code} {str(rolls)[:120] or r.text[:120]}")
    for x in rolls:
        db.inventory_movements.delete_many({"roll_id": x["id"]}); db.inventory_rolls.delete_one({"id": x["id"]})
    db.wms_tasks.delete_one({"id": tid}); db.inspection_orders.delete_many({"source_task_id": tid}) if "inspection_orders" in db.list_collection_names() else None
    sys.path.insert(0, str(ROOT / "backend")); from dotenv import load_dotenv; load_dotenv(ROOT / "backend/.env")
    from services.roll_service import rebuild_balance
    await rebuild_balance(prod["id"], "wh_jakarta", "ent_ksc")

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
