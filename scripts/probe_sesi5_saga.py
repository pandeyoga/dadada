"""Probe runtime sesi 5: klaim saga reverse-writeoff/relocate retur jual, void kwitansi AR,
kompensasi stok awal, CAS resolve-escalation inbound, paginasi opt-in T-03 Lapis 4.
Jalankan: python scripts/probe_sesi5_saga.py (env REACT_APP_BACKEND_URL dari frontend/.env)."""
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
PW = "demo12345"
FAILS = []
LOCK = {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}


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

    # ── 1. sales-returns reverse-writeoff / relocate ──
    ret = db.sales_returns.find_one({"entity_id": "ent_ksc", "saga_lock": {"$exists": False}}, {"_id": 0})
    check("ada retur jual KSC untuk uji", bool(ret))
    if ret:
        rid = ret["id"]
        r = await admin.post(f"/sales-returns/{rid}/reverse-writeoff", json={"reason": "probe tanpa target"})
        after = db.sales_returns.find_one({"id": rid}, {"_id": 0, "saga_lock": 1})
        check("reverse-writeoff tanpa roll scrap → 400 dan TIDAK meninggalkan saga_lock",
              r.status_code == 400 and "saga_lock" not in after, f"{r.status_code} {str(after)}")
        db.sales_returns.update_one({"id": rid}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/sales-returns/{rid}/reverse-writeoff", json={"reason": "probe kunci"})
        # validasi 'tanpa target' berjalan SEBELUM klaim → 400 tetap menang atas kunci (klaim sesudah validasi)
        check("reverse-writeoff saat terkunci: validasi dulu (400), kunci tidak disentuh",
              r.status_code == 400, f"{r.status_code} {r.text[:100]}")
        # roll karantina sintetis milik retur ini → relocate
        roll_id = f"roll_probe5_{uuid.uuid4().hex[:8]}"
        prod = db.products.find_one({}, {"_id": 0, "id": 1})
        db.inventory_rolls.insert_one({
            "id": roll_id, "product_id": prod["id"], "owner_entity_id": "ent_ksc", "warehouse_id": "wh_jakarta",
            "status": "quarantine", "length_initial": 5.0, "length_remaining": 5.0, "unit": "meter",
            "roll_no": "PROBE5", "acquired": {"via": "return", "ref_id": rid}, "return_id": rid, "origin_type": "return",
            "created_at": "2026-09-05T00:00:00+00:00", "updated_at": "2026-09-05T00:00:00+00:00"})
        r = await admin.post(f"/sales-returns/{rid}/relocate", json={"to_warehouse_id": "wh_bandung", "note": "probe kunci"})
        check("relocate saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        locks = (await admin.get("/saga-locks")).json()
        check("kunci sales_returns tampil di /saga-locks", any(l["collection"] == "sales_returns" and l["id"] == rid for l in locks))
        r = await admin.post(f"/saga-locks/sales_returns/{rid}/release")
        check("lepas kunci sales_returns → 200", r.status_code == 200)
        rs = await asyncio.gather(*[admin.post(f"/sales-returns/{rid}/relocate", json={"to_warehouse_id": "wh_bandung", "note": "probe balapan"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        check("2× relocate bersamaan → tepat 1 pemenang 200, sisanya 4xx (tanpa 5xx)",
              codes.count(200) == 1 and all(c in (200, 400, 409) for c in codes), f"{codes} {[x.text[:80] for x in rs]}")
        after = db.sales_returns.find_one({"id": rid}, {"_id": 0, "saga_lock": 1, "relocation_legs": 1})
        legs = [l for l in (after.get("relocation_legs") or []) if l.get("note") == "probe balapan"]
        check("kaki relokasi tepat 1 & saga_lock bersih", len(legs) == 1 and "saga_lock" not in after, f"legs={len(legs)} lock={'saga_lock' in after}")
        moved = db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0, "warehouse_id": 1})
        check("roll sintetis pindah ke wh_bandung", (moved or {}).get("warehouse_id") == "wh_bandung", str(moved))
        # bersihkan residu sintetis
        db.inventory_rolls.delete_one({"id": roll_id})
        db.inventory_movements.delete_many({"roll_id": roll_id})
        db.sales_returns.update_one({"id": rid}, {"$pull": {"relocation_legs": {"note": "probe balapan"}}})
        from_leg_ids = [l["id"] for l in legs]
        _ = from_leg_ids

    # ── 2. ar-receipts void: buat SO + kwitansi, kunci → 409, balapan → 1 pemenang ──
    rec = None
    so2 = None
    try:
        prods = (await admin.get("/products")).json()
        plist = prods if isinstance(prods, list) else prods.get("items", [])
        custs = (await admin.get("/customers")).json()
        clist = custs if isinstance(custs, list) else custs.get("items", [])
        p = next((x for x in plist if float(x.get("price") or 0) > 0), plist[0])
        cust = next(c for c in clist if c.get("addresses"))
        r = await admin.post("/sales-orders", json={
            "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0].get("id") or "",
            "items": [{"product_id": p["id"], "quantity": 15.0, "unit": p.get("base_unit") or "meter"}],
            "sales_name": "Probe sesi 5", "notes": "probe void kwitansi"})
        so2 = r.json()
        gt = round(float(so2.get("grand_total") or 0), 2)
        r = await admin.post("/ar-receipts", json={"customer_id": so2["customer_id"], "amount": round(gt / 2, 2),
                                                   "method": "transfer", "notes": "probe sesi 5",
                                                   "allocations": [{"order_id": so2["id"], "amount": round(gt / 2, 2)}]})
        check("kwitansi AR dibuat → 200", r.status_code == 200, r.text[:160])
        rec = r.json() if r.status_code == 200 else None
    except Exception as exc:  # noqa: BLE001
        check("setup kwitansi AR", False, repr(exc)[:200])
    if rec:
        db.ar_receipts.update_one({"id": rec["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/ar-receipts/{rec['id']}/void", params={"reason": "probe kunci"})
        check("void kwitansi saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
        locks = (await admin.get("/saga-locks")).json()
        check("kunci ar_receipts tampil di /saga-locks", any(l["collection"] == "ar_receipts" and l["id"] == rec["id"] for l in locks))
        r = await admin.post(f"/saga-locks/ar_receipts/{rec['id']}/release")
        check("lepas kunci ar_receipts → 200", r.status_code == 200)
        rs = await asyncio.gather(*[admin.post(f"/ar-receipts/{rec['id']}/void", params={"reason": "probe balapan"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        check("2× void bersamaan → satu 200 + satu 409", codes == [200, 409], f"{codes} {[x.text[:80] for x in rs]}")
        after = db.ar_receipts.find_one({"id": rec["id"]}, {"_id": 0, "status": 1, "saga_lock": 1})
        check("kwitansi void tanpa saga_lock tersisa", after.get("status") == "void" and "saga_lock" not in after, str(after))
        so_after = db.sales_orders.find_one({"id": so2["id"]}, {"_id": 0, "paid_total": 1, "payments": 1})
        check("payments SO dibalik (paid_total 0, tanpa payment kwitansi ini)",
              round(float(so_after.get("paid_total") or 0), 2) == 0 and not [x for x in (so_after.get("payments") or []) if x.get("receipt_id") == rec["id"]],
              str(so_after)[:160])
        n_void_je = db.journal_entries.count_documents({"description": {"$regex": f"void {rec.get('number', '')}"}}) if rec.get("number") else 0
        check("jurnal void kas ≤ 1 (tidak ganda)", n_void_je <= 1, str(n_void_je))
    if so2:
        r = await admin.post(f"/sales-orders/{so2['id']}/cancel", json={"reason": "probe sesi 5 selesai"})
        check("SO probe dibatalkan (bersih-bersih) → 200/409", r.status_code in (200, 409), f"{r.status_code} {r.text[:80]}")

    # ── 3. inventory initial-stock: kompensasi → sukses normal 200 + roll & mutasi lahir ──
    prod = db.products.find_one({}, {"_id": 0, "id": 1, "base_unit": 1})
    r = await admin.post("/inventory/initial-stock", json={
        "product_id": prod["id"], "warehouse_id": "wh_jakarta", "quantity": 3.0,
        "unit": prod.get("base_unit") or "meter", "lot": "LOT-PROBE5", "grade": "A"})
    check("initial-stock → 200", r.status_code == 200, r.text[:160])
    if r.status_code == 200:
        roll_id = r.json().get("roll_id")
        lot_id = r.json().get("lot_id")
        n_mov = db.inventory_movements.count_documents({"roll_id": roll_id, "movement_type": "initial_stock"})
        check("roll + tepat 1 mutasi initial_stock lahir", bool(db.inventory_rolls.find_one({"id": roll_id})) and n_mov == 1, f"mov={n_mov}")
        # bersih-bersih lewat kompensasi yang sama + lot yatim + rebuild balance
        db.inventory_movements.delete_many({"roll_id": roll_id})
        db.inventory_rolls.delete_one({"id": roll_id})
        if lot_id and not db.inventory_rolls.find_one({"lot_id": lot_id}):
            db.inventory_lots.delete_one({"id": lot_id})
        sys.path.insert(0, str(ROOT / "backend"))
        from dotenv import load_dotenv
        load_dotenv(ROOT / "backend/.env")
        from services.roll_service import rebuild_balance  # noqa: E402
        await rebuild_balance(prod["id"], "wh_jakarta", "ent_ksc")

    # ── 4. inbound resolve-escalation: CAS → dua manajer bersamaan = [200, 409] ──
    manager = await login("manager@kainnusantara.id")
    task_id = f"task_probe5_{uuid.uuid4().hex[:8]}"
    db.wms_tasks.insert_one({
        "id": task_id, "type": "inbound", "status": "escalated", "entity_id": "ent_ksc",
        "product_id": prod["id"], "warehouse_id": "wh_jakarta", "quantity": 10.0, "received_qty": 8.0, "expected_qty": 10.0,
        "escalation": {"escalated_by": "probe", "escalated_at": "2026-09-05T00:00:00+00:00", "reason": "probe",
                       "status": "pending_review", "resolved_by": None, "resolved_at": None, "resolution_notes": ""},
        "created_at": "2026-09-05T00:00:00+00:00", "updated_at": "2026-09-05T00:00:00+00:00"})
    rs = await asyncio.gather(*[manager.post(f"/inbound/tasks/{task_id}/resolve-escalation", params={"adjusted_qty": 8, "resolution_notes": "probe"}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    check("2× resolve-escalation inbound bersamaan → satu 200 + satu 409", codes == [200, 409], f"{codes} {[x.text[:80] for x in rs]}")
    t = db.wms_tasks.find_one({"id": task_id}, {"_id": 0, "status": 1, "escalation.status": 1})
    check("task → qc_check, eskalasi resolved", t.get("status") == "qc_check" and (t.get("escalation") or {}).get("status") == "resolved", str(t))
    r = await manager.post(f"/inbound/tasks/{task_id}/resolve-escalation", params={"resolution_notes": "probe ulang"})
    check("resolve ulang sesudah resolved → 409", r.status_code == 409, f"{r.status_code} {r.text[:80]}")
    db.wms_tasks.delete_one({"id": task_id})

    # ── 5. paginasi opt-in T-03 Lapis 4 ──
    for path in ("/hr/attendance?date_from=2020-01-01&date_to=2030-12-31", "/hr/visits?date_from=2020-01-01&date_to=2030-12-31",
                 "/hr/field-tracks?employee_id=none"):
        plain = await admin.get(path)
        paged = await admin.get(path + "&page=1&page_size=2")
        ok = plain.status_code == 200 and isinstance(plain.json(), list) and paged.status_code == 200 \
            and isinstance(paged.json(), dict) and set(paged.json()) >= {"items", "total", "page", "page_size", "has_more"} \
            and len(paged.json()["items"]) <= 2 and paged.json()["total"] == len(plain.json())
        check(f"paginasi opt-in {path.split('?')[0]}: array tanpa param, envelope dengan page", ok,
              f"{plain.status_code}/{paged.status_code} total={paged.json().get('total') if paged.status_code == 200 and isinstance(paged.json(), dict) else '?'} vs {len(plain.json()) if plain.status_code == 200 and isinstance(plain.json(), list) else '?'}")
    pid = prod["id"]
    plain = await admin.get(f"/products/{pid}/purchase-history")
    paged = await admin.get(f"/products/{pid}/purchase-history?page=1&page_size=1")
    ok = plain.status_code == 200 and "events_page" not in plain.json() and paged.status_code == 200 \
        and paged.json().get("events_page", {}).get("total") == len(plain.json().get("events", [])) \
        and len(paged.json()["events"]) <= 1 and paged.json()["summary"] == plain.json()["summary"]
    check("paginasi opt-in purchase-history: ringkasan utuh, events dipotong + events_page", ok,
          f"{plain.status_code}/{paged.status_code} {str(paged.json().get('events_page'))[:100]}")

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
