"""Probe runtime sesi 15: klaim rekonsiliasi bank (book-charge/holding/allocate/cancel → 409 saat terkunci,
kunci lepas sesudah 400), harga khusus efektif untuk HP (endpoint effective + SO menghormati price_approval_id),
job printer_stuck_watch (notifikasi label tertahan), Idempotency-Key pada /sales-orders & /hr/visits.
Jalankan: python scripts/probe_sesi15.py"""
import asyncio
import os
import pathlib
import uuid
from datetime import datetime, timedelta, timezone

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
for line in (ROOT / "backend/.env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k in ("MONGO_URL", "DB_NAME") and not os.environ.get(k):
        os.environ[k] = v.strip().strip('"')
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
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    admin = await login("admin@kainnusantara.id")
    tag = "PROBE15-" + uuid.uuid4().hex[:4]

    # ── rekonsiliasi bank: kunci → 409 pada 4 endpoint; 400 validasi tak meninggalkan kunci ──
    line = db.bank_statement_lines.find_one({"status": {"$nin": ["matched", "holding"]}}, {"_id": 0, "id": 1, "entity_id": 1, "direction": 1, "amount": 1})
    hold = db.bank_statement_lines.find_one({"status": "holding"}, {"_id": 0, "id": 1, "entity_id": 1})
    if line:
        admin.headers["X-Entity-Id"] = line.get("entity_id") or "ent_ksc"
        db.bank_statement_lines.update_one({"id": line["id"]}, {"$set": {"saga_lock": LOCK}})
        r1 = await admin.post(f"/bank-reconciliation/lines/{line['id']}/book-charge", json={"kind": "interest" if (line.get("direction") or "in") == "in" else "charge", "note": "probe"})
        r2 = await admin.post(f"/bank-reconciliation/lines/{line['id']}/holding", json={"note": "probe"})
        db.bank_statement_lines.update_one({"id": line["id"]}, {"$unset": {"saga_lock": ""}})
        check("book-charge & holding saat terkunci → 409 SAGA_IN_PROGRESS", all(x.status_code == 409 and "SAGA_IN_PROGRESS" in x.text for x in (r1, r2)), f"{r1.status_code}/{r2.status_code} {r1.text[:80]}")
        rb = await admin.post(f"/bank-reconciliation/lines/{line['id']}/book-charge", json={"kind": "salah", "note": ""})
        cur = db.bank_statement_lines.find_one({"id": line["id"]}, {"_id": 0, "saga_lock": 1})
        check("book-charge jenis salah → 400 tanpa kunci tertinggal", rb.status_code == 400 and "saga_lock" not in cur, f"{rb.status_code}")
        rc = await admin.post(f"/bank-reconciliation/lines/{line['id']}/holding/cancel")
        check("holding/cancel pada baris bukan titipan → 400 (validasi sebelum klaim)", rc.status_code == 400 and "saga_lock" not in db.bank_statement_lines.find_one({"id": line["id"]}, {"_id": 0, "saga_lock": 1}), f"{rc.status_code}")
    else:
        print("SKIP  tidak ada baris koran unmatched")
    if hold:
        admin.headers["X-Entity-Id"] = hold.get("entity_id") or "ent_ksc"
        db.bank_statement_lines.update_one({"id": hold["id"]}, {"$set": {"saga_lock": LOCK}})
        ra = await admin.post(f"/bank-reconciliation/lines/{hold['id']}/holding/allocate", json={"allocations": [{"order_id": "x", "amount": 1}], "reason_code": "probe"})
        rk = await admin.post(f"/bank-reconciliation/lines/{hold['id']}/holding/cancel")
        db.bank_statement_lines.update_one({"id": hold["id"]}, {"$unset": {"saga_lock": ""}})
        check("holding/allocate & cancel saat terkunci → 409", all(x.status_code == 409 for x in (ra, rk)), f"{ra.status_code}/{rk.status_code}")
    else:
        print("SKIP  tidak ada baris titipan (holding)")
    admin.headers["X-Entity-Id"] = "ent_ksc"

    # ── harga khusus efektif untuk HP: approval approved → effective has_special → SO memakai harga itu ──
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0}) or db.customers.find_one({}, {"_id": 0})
    prod = db.products.find_one({"price": {"$gt": 1000}}, {"_id": 0})
    eid = cust.get("entity_id") or "ent_ksc"
    admin.headers["X-Entity-Id"] = eid
    special = round(float(prod["price"]) * 0.9, 2)
    appr = {"id": "pa_probe15_" + uuid.uuid4().hex[:6], "entity_id": eid, "customer_id": cust["id"], "customer_name": cust.get("name"),
            "product_id": prod["id"], "product_name": prod.get("name"), "normal_price": float(prod["price"]), "requested_price": special,
            "min_quantity": 1, "status": "approved", "approved_at": datetime.now(timezone.utc).isoformat(),
            "valid_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "scope": "standing", "created_at": datetime.now(timezone.utc).isoformat(), "notes": tag}
    db.price_approvals.insert_one(dict(appr))
    eff = await admin.get("/price-approvals/effective", params={"customer_id": cust["id"], "product_id": prod["id"], "entity_id": eid, "quantity": 2})
    ok_eff = eff.status_code == 200 and eff.json().get("has_special") and eff.json().get("price_approval_id") == appr["id"]
    check("GET /price-approvals/effective (yang dipakai keranjang HP) → has_special + id approval", ok_eff, f"{eff.status_code} {eff.text[:120]}")
    addr_id = ((cust.get("addresses") or [{}])[0]).get("id", "")
    so = await admin.post("/sales-orders", json={"customer_id": cust["id"], "shipping_address_id": addr_id, "items": [{"product_id": prod["id"], "quantity": 2, "unit": prod.get("unit", "yard"), "discount_percent": 0, "price_approval_id": appr["id"]}]},
                          headers={"Idempotency-Key": "idem15-" + uuid.uuid4().hex})
    so_ok = so.status_code == 200
    line_price = (so.json().get("items") or [{}])[0].get("price") if so_ok else None
    check("POST /sales-orders dgn price_approval_id → harga baris = harga khusus (bukan list)", so_ok and abs(float(line_price or 0) - special) < 0.01, f"{so.status_code} unit_price={line_price} khusus={special} {so.text[:100] if not so_ok else ''}")
    if so_ok:
        so_id = so.json()["id"]
        # bersihkan SO probe (dan reservasi)
        try:
            await admin.post(f"/sales-orders/{so_id}/cancel", json={"reason": "probe"})
        except Exception:
            pass
        db.sales_orders.delete_one({"id": so_id})
        db.inventory_rolls.update_many({"reserved_ref.id": so_id}, {"$set": {"status": "available", "reserved_ref": None}})
    db.price_approvals.delete_one({"id": appr["id"]})
    admin.headers["X-Entity-Id"] = "ent_ksc"

    # ── Idempotency pada kunjungan: check-in 2× kunci sama → 1 kunjungan ──
    sales = await login("sales@kainnusantara.id")
    k = "idem15-" + uuid.uuid4().hex
    before = db.hr_visits.count_documents({}) if "hr_visits" in db.list_collection_names() else None
    v1 = await sales.post("/hr/visits/check-in", json={"customer_name": tag, "notes": "probe"}, headers={"Idempotency-Key": k})
    v2 = await sales.post("/hr/visits/check-in", json={"customer_name": tag, "notes": "probe"}, headers={"Idempotency-Key": k})
    coll = next((c for c in db.list_collection_names() if "visit" in c), None)
    n = db[coll].count_documents({"customer_name": tag}) if coll else -1
    check("check-in kunjungan 2× kunci sama → replay, 1 kunjungan", v1.status_code in (200, 201) and v2.status_code == v1.status_code and v2.headers.get("x-idempotent-replay") == "true" and n == 1, f"{v1.status_code}/{v2.status_code} n={n} {v1.text[:80]}")
    if coll:
        db[coll].delete_many({"customer_name": tag})

    # ── printer_stuck_watch: job antre lama tanpa printer online → notifikasi warehouse_admin + manager ──
    wh = db.warehouses.find_one({}, {"_id": 0, "id": 1, "name": 1})
    db.rfid_devices.update_many({"type": "printer", "warehouse_id": wh["id"]}, {"$set": {"last_heartbeat": "2026-01-01T00:00:00+00:00"}})
    old = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    job = {"id": "rpj_probe15_" + uuid.uuid4().hex[:6], "kind": "qr_label", "job_number": "PJ-PROBE15", "warehouse_id": wh["id"], "warehouse_name": wh.get("name"),
           "owner_entity_id": "ent_ksc", "status": "queued", "items": [], "item_count": 3, "created_at": old, "created_by": "probe"}
    db.rfid_print_jobs.insert_one(dict(job))
    db.notifications.delete_many({"ref": {"$regex": f"^printer_stuck:{wh['id']}"}})
    run = await admin.post("/scheduler/jobs/printer_stuck_watch/run")
    notif = db.notifications.find_one({"ref": f"printer_stuck:{wh['id']}", "recipient_role": "warehouse_admin"}, {"_id": 0})
    notif_m = db.notifications.find_one({"ref": f"printer_stuck:{wh['id']}:manager"}, {"_id": 0})
    check("job printer_stuck_watch → notifikasi 'Label tertahan' ke warehouse_admin & manager (3 label, >30 menit)",
          run.status_code == 200 and notif and "3 label" in notif["body"] and notif_m is not None, f"{run.status_code} {run.text[:120]} notif={bool(notif)}")
    run2 = await admin.post("/scheduler/jobs/printer_stuck_watch/run")
    cnt = db.notifications.count_documents({"ref": f"printer_stuck:{wh['id']}"})
    check("job dijalankan lagi → tidak ada notifikasi ganda (dedupe unread)", run2.status_code == 200 and cnt == 1, f"cnt={cnt}")
    db.rfid_print_jobs.delete_one({"id": job["id"]}); db.notifications.delete_many({"ref": {"$regex": f"^printer_stuck:{wh['id']}"}})
    check("jejak probe bersih", db.price_approvals.count_documents({"notes": tag}) == 0 and db.rfid_print_jobs.count_documents({"job_number": "PJ-PROBE15"}) == 0)

    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
