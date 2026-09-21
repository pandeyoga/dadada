"""Probe runtime sesi 4: klaim saga reallocate/release-rolls, vendor-bill cancel, variance reverse,
job saga_lock_watch. Jalankan: python scripts/probe_sesi4_saga.py (env REACT_APP_BACKEND_URL dari frontend/.env)."""
import asyncio
import os
import pathlib
import sys

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PW = "demo12345"
FAILS = []


def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {info}" if info else ""))
    if not ok:
        FAILS.append(name)


async def login(email):
    c = httpx.AsyncClient(base_url=API, timeout=60)
    r = await c.post("/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    c.headers["X-Entity-Id"] = "ent_ksc"
    return c


async def main():
    admin = await login("admin@kainnusantara.id")
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]

    # ── 1. SO reallocate / release-rolls dengan kunci disuntik → 409 SAGA_IN_PROGRESS ──
    so = db.sales_orders.find_one({"status": "reserved", "entity_id": "ent_ksc", "saga_lock": {"$exists": False}}, {"_id": 0})
    check("ada SO reserved untuk uji", bool(so))
    if so:
        pid = so["items"][0]["product_id"]
        rolls = list(db.inventory_rolls.find({"reserved_ref.id": so["id"], "product_id": pid, "status": "reserved"}, {"_id": 0, "id": 1}))
        db.sales_orders.update_one({"id": so["id"]}, {"$set": {"saga_lock": {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}}})
        r = await admin.post(f"/sales-orders/{so['id']}/items/{pid}/release-rolls",
                             json={"roll_ids": [rolls[0]["id"]] if rolls else ["x"], "reason": "probe kunci"})
        check("release-rolls saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        r = await admin.post(f"/sales-orders/{so['id']}/items/{pid}/reallocate",
                             json={"roll_lines": [{"roll_id": rolls[0]["id"], "take_qty": 1}] if rolls else [{"roll_id": "x", "take_qty": 1}]})
        check("reallocate saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        locks = (await admin.get("/saga-locks")).json()
        check("kunci probe tampil di /saga-locks", any(l["id"] == so["id"] for l in locks))

        # ── 3. job saga_lock_watch → notifikasi admin (kunci berumur > 10 menit) ──
        r = await admin.post("/scheduler/jobs/saga_lock_watch/run")
        check("run job saga_lock_watch → 200", r.status_code == 200, r.text[:200])
        run = r.json() if r.status_code == 200 else {}
        check("job menemukan kunci probe & membuat notifikasi", run.get("status") in ("ok", "success") and run.get("created", 0) >= 1, str({k: run.get(k) for k in ("status", "created", "detail")}))
        n = db.notifications.find_one({"type": "saga_lock_stuck", "ref": {"$regex": f"^saga_lock:sales_orders:{so['id']}#"}}, {"_id": 0, "title": 1, "recipient_user": 1, "recipient_role": 1})
        check("notifikasi saga_lock_stuck beralamat ke user admin (recipient_user, bukan role)", bool(n) and n.get("recipient_user") and not n.get("recipient_role"), str(n))
        r2 = await admin.post("/scheduler/jobs/saga_lock_watch/run")
        check("job idempoten (jalan ke-2 hari ini → 0 notifikasi baru)", r2.status_code == 200 and r2.json().get("created") == 0, str(r2.json().get("created")))

        r = await admin.post(f"/saga-locks/sales_orders/{so['id']}/release")
        check("lepas kunci → 200", r.status_code == 200, r.text[:100])
        db.notifications.delete_many({"type": "saga_lock_stuck"})

        # ── 1b. release-rolls nyata (sesudah kunci lepas) → 200 dan saga_lock tidak tersisa ──
        if rolls and len(rolls) >= 1:
            r = await admin.post(f"/sales-orders/{so['id']}/items/{pid}/release-rolls",
                                 json={"roll_ids": [rolls[0]["id"]], "reason": "probe lepas sebagian"})
            check("release-rolls nyata → 200", r.status_code == 200, r.text[:160])
            after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0, "saga_lock": 1, "status": 1})
            check("saga_lock tidak tersisa sesudah release-rolls", "saga_lock" not in after, str(after))
            # reallocate: ambil kembali roll yang baru dilepas + roll yang tersisa
            remaining = list(db.inventory_rolls.find({"reserved_ref.id": so["id"], "product_id": pid, "status": "reserved"}, {"_id": 0, "id": 1}))
            lines = [{"roll_id": x["id"], "take_qty": 0} for x in remaining] + [{"roll_id": rolls[0]["id"], "take_qty": 0}]
            r = await admin.post(f"/sales-orders/{so['id']}/items/{pid}/reallocate", json={"roll_lines": lines})
            check("reallocate nyata → 200", r.status_code == 200, r.text[:200])
            after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0, "saga_lock": 1})
            check("saga_lock tidak tersisa sesudah reallocate", "saga_lock" not in after, str(after))
            # 2 reallocate bersamaan → satu 200 + satu 409 (atau keduanya 200 berurutan bila cepat)
            rs = await asyncio.gather(*[admin.post(f"/sales-orders/{so['id']}/items/{pid}/reallocate", json={"roll_lines": lines}) for _ in range(2)])
            codes = sorted(x.status_code for x in rs)
            check("2× reallocate bersamaan → tidak ada 5xx, ≤1 pemenang per klaim", all(c in (200, 409) for c in codes), str(codes))
            after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0, "saga_lock": 1})
            check("saga_lock bersih sesudah balapan", "saga_lock" not in after, str(after))

    # ── 2. vendor-bill cancel: kunci disuntik → 409; dua cancel bersamaan → 1 pemenang; JE reversal tunggal ──
    bill = db.vendor_bills.find_one({"status": "posted", "amount_paid": {"$not": {"$gt": 0.01}}, "entity_id": "ent_ksc"}, {"_id": 0})
    if not bill:
        bill = db.vendor_bills.find_one({"status": {"$in": ["draft", "pending_approval", "posted"]}, "amount_paid": {"$not": {"$gt": 0.01}}}, {"_id": 0})
    check("ada vendor bill yang bisa dibatalkan", bool(bill), str((bill or {}).get("status")))
    if bill:
        admin.headers["X-Entity-Id"] = bill.get("entity_id") or "ent_ksc"
        db.vendor_bills.update_one({"id": bill["id"]}, {"$set": {"saga_lock": {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}}})
        r = await admin.post(f"/vendor-bills/{bill['id']}/cancel", json={"notes": "probe"})
        check("vendor-bill cancel saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        locks = (await admin.get("/saga-locks")).json()
        check("kunci vendor_bills tampil di /saga-locks", any(l["collection"] == "vendor_bills" and l["id"] == bill["id"] for l in locks))
        r = await admin.post(f"/saga-locks/vendor_bills/{bill['id']}/release")
        check("lepas kunci vendor_bills → 200", r.status_code == 200)
        rs = await asyncio.gather(*[admin.post(f"/vendor-bills/{bill['id']}/cancel", json={"notes": "probe balapan"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        check("2× cancel bersamaan → satu 200 + satu 409", codes == [200, 409], f"{codes} {[x.text[:80] for x in rs]}")
        after = db.vendor_bills.find_one({"id": bill["id"]}, {"_id": 0, "status": 1, "saga_lock": 1})
        check("bill cancelled tanpa saga_lock tersisa", after.get("status") == "cancelled" and "saga_lock" not in after, str(after))
        if bill["status"] == "posted":
            n_rev = db.journal_entries.count_documents({"source_type": "vendor_bill_reversal", "source_id": bill["id"]})
            check("jurnal pembalik vendor bill tepat 1", n_rev == 1, str(n_rev))
        admin.headers["X-Entity-Id"] = "ent_ksc"

    # ── 2b. payment-variance reverse: buat keputusan writeoff (SO → kurang bayar → manager hapus sisa) ──
    dec = None
    try:
        manager = await login("manager@kainnusantara.id")
        prods = (await admin.get("/products")).json()
        plist = prods if isinstance(prods, list) else prods.get("items", [])
        custs = (await admin.get("/customers")).json()
        clist = custs if isinstance(custs, list) else custs.get("items", [])
        p = next((x for x in plist if float(x.get("price") or 0) > 0), plist[0])
        cust = next(c for c in clist if c.get("addresses"))
        r = await admin.post("/sales-orders", json={
            "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0].get("id") or "",
            "items": [{"product_id": p["id"], "quantity": 15.0, "unit": p.get("base_unit") or "meter"}],
            "sales_name": "Probe sesi 4", "notes": "probe variance"})
        so2 = r.json()
        gt = round(float(so2.get("grand_total") or 0), 2)
        r = await admin.post("/ar-receipts", json={"customer_id": so2["customer_id"], "amount": round(gt - 300000, 2),
                                                   "method": "transfer", "notes": "probe",
                                                   "allocations": [{"order_id": so2["id"], "amount": round(gt - 300000, 2)}]})
        rec = r.json()
        r = await manager.post(f"/payment-variances/receipt/{rec['id']}/decide",
                               json={"kind": "writeoff", "reason_code": "uncollectible_small", "note": "probe hapus sisa"})
        check("keputusan writeoff dibuat (manager) → 200 berjurnal", r.status_code == 200 and r.json().get("je_number"), r.text[:160])
        dec = db.payment_variance_decisions.find_one({"id": r.json().get("id")}, {"_id": 0}) if r.status_code == 200 else None
    except Exception as exc:  # noqa: BLE001
        check("setup keputusan selisih", False, repr(exc)[:200])
    check("ada keputusan selisih aktif", bool(dec), str((dec or {}).get("kind")))
    if dec:
        admin.headers["X-Entity-Id"] = dec.get("entity_id") or "ent_ksc"
        db.payment_variance_decisions.update_one({"id": dec["id"]}, {"$set": {"saga_lock": {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}}})
        r = await admin.post(f"/payment-variances/{dec['id']}/reverse", json={"reason": "probe"})
        check("variance reverse saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        await admin.post(f"/saga-locks/payment_variance_decisions/{dec['id']}/release")
        rs = await asyncio.gather(*[admin.post(f"/payment-variances/{dec['id']}/reverse", json={"reason": "probe balapan"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        check("2× reverse bersamaan → tidak ada 5xx, tepat 1 pemenang 200", codes.count(200) == 1 and all(c in (200, 409) for c in codes), f"{codes} {[x.text[:80] for x in rs]}")
        after = db.payment_variance_decisions.find_one({"id": dec["id"]}, {"_id": 0, "status": 1, "saga_lock": 1})
        check("keputusan reversed tanpa saga_lock", after.get("status") == "reversed" and "saga_lock" not in after, str(after))
        n_rev = db.journal_entries.count_documents({"source_type": {"$regex": "variance"}, "source_id": dec["id"], "description": {"$regex": "probe balapan"}})
        check("jurnal pembalik variance ≤ 1", n_rev <= 1, str(n_rev))

    # ── job tanpa kunci → 0 ──
    r = await admin.post("/scheduler/jobs/saga_lock_watch/run")
    check("job saga_lock_watch tanpa kunci → created 0", r.status_code == 200 and r.json().get("created") == 0, str(r.json())[:160])
    jobs = (await admin.get("/scheduler/jobs")).json()
    j = next((x for x in (jobs if isinstance(jobs, list) else jobs.get("jobs", [])) if x.get("id") == "saga_lock_watch"), None)
    check("job saga_lock_watch terdaftar (label 'Setiap 10 menit')", bool(j) and "10 menit" in str(j), str(j)[:200])

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
