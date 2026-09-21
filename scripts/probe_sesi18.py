"""Probe runtime sesi 18 (ratchet INV-ATOMIC-01 → 0): setiap endpoint yang baru diklaim ditolak 409
SAGA_IN_PROGRESS saat dokumen induk terkunci, validasi 4xx tidak meninggalkan kunci, jalur sukses
melepas kunci, dan balapan (2× bersamaan) hanya melahirkan satu tulisan turunan.
Jalankan: python scripts/probe_sesi18.py"""
import asyncio
import os
import pathlib
import uuid

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
    c = httpx.AsyncClient(base_url=API, timeout=90)
    r = await c.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    c.headers["X-Entity-Id"] = "ent_ksc"
    return c


def locked(db, coll, _id):
    return "saga_lock" in (db[coll].find_one({"id": _id}, {"_id": 0, "saga_lock": 1}) or {})


async def expect_409_when_locked(db, client, name, coll, doc_id, method, path, json=None):
    db[coll].update_one({"id": doc_id}, {"$set": {"saga_lock": LOCK}})
    r = await client.request(method, path, json=json)
    db[coll].update_one({"id": doc_id}, {"$unset": {"saga_lock": ""}})
    check(f"{name} saat {coll} terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text,
          f"{r.status_code} {r.text[:90]}")


async def main():
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    admin = await login("admin@kainnusantara.id")
    tag = "P18-" + uuid.uuid4().hex[:4]

    # ── product-templates DELETE ──
    tid = "tpl_probe18_" + uuid.uuid4().hex[:4]
    db.product_templates.insert_one({"id": tid, "name": f"Tpl {tag}", "code": tag, "created_at": "2026-09-06T00:00:00+00:00"})
    pid = "prd_probe18_" + uuid.uuid4().hex[:4]
    db.products.insert_one({"id": pid, "name": f"Var {tag}", "sku": tag, "template_id": tid, "price": 1, "status": "active"})
    await expect_409_when_locked(db, admin, "hapus template", "product_templates", tid, "DELETE", f"/product-templates/{tid}")
    r = await admin.delete(f"/product-templates/{tid}")
    check("hapus template → varian dilepas, template hilang", r.status_code == 200 and db.products.find_one({"id": pid})["template_id"] == "" and not db.product_templates.find_one({"id": tid}), f"{r.status_code}")
    db.products.delete_one({"id": pid})

    # ── input-tax create/cancel ──
    bill = db.vendor_bills.find_one({"status": {"$in": ["posted", "paid"]}, "ppn_amount": {"$gt": 0},
                                     "input_faktur_status": {"$nin": ["recorded", "reported", "credited"]}}, {"_id": 0, "id": 1})
    if bill:
        body = {"vendor_bill_id": bill["id"], "nsfp": "010." + uuid.uuid4().hex[:3] + "-26.9" + str(uuid.uuid4().int)[:7]}
        await expect_409_when_locked(db, admin, "catat faktur masukan", "vendor_bills", bill["id"], "POST", "/input-tax-invoices", body)
        rs = await asyncio.gather(*[admin.post("/input-tax-invoices", json=body) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        n = db.tax_invoices_in.count_documents({"vendor_bill_id": bill["id"], "status": "recorded"})
        check("catat faktur 2× bersamaan → satu faktur, kunci lepas", n == 1 and 200 in codes and not locked(db, "vendor_bills", bill["id"]), f"{codes} n={n}")
        fpm = db.tax_invoices_in.find_one({"vendor_bill_id": bill["id"], "status": "recorded"}, {"_id": 0, "id": 1})
        if fpm:
            await expect_409_when_locked(db, admin, "batal faktur masukan", "tax_invoices_in", fpm["id"], "POST", f"/input-tax-invoices/{fpm['id']}/cancel", {"reason": "probe"})
            r = await admin.post(f"/input-tax-invoices/{fpm['id']}/cancel", json={"reason": ""})
            check("batal faktur alasan kosong → 400 tanpa kunci", r.status_code == 400 and not locked(db, "tax_invoices_in", fpm["id"]), f"{r.status_code}")
            r = await admin.post(f"/input-tax-invoices/{fpm['id']}/cancel", json={"reason": "probe"})
            b = db.vendor_bills.find_one({"id": bill["id"]}, {"_id": 0, "input_faktur_status": 1, "saga_lock": 1})
            check("batal faktur → bill dilepas, kunci lepas", r.status_code == 200 and b.get("input_faktur_status") == "cancelled" and not locked(db, "tax_invoices_in", fpm["id"]), f"{r.status_code} {b}")
            db.tax_invoices_in.delete_many({"vendor_bill_id": bill["id"], "nsfp": body["nsfp"]})
            db.vendor_bills.update_one({"id": bill["id"]}, {"$unset": {"input_faktur_status": "", "input_faktur_id": "", "input_faktur_number": "", "input_faktur_nsfp": ""}})
    else:
        print("SKIP input-tax (tidak ada bill posted ber-PPN tanpa faktur)")

    # ── landed cost approve/pay: terkunci → 409 (tanpa mengubah data) ──
    lc = db.landed_cost_vouchers.find_one({"status": "pending_approval"}, {"_id": 0, "id": 1})
    if lc:
        await expect_409_when_locked(db, admin, "approve landed cost", "landed_cost_vouchers", lc["id"], "POST", f"/landed-costs/{lc['id']}/approve")
    lcp = db.landed_cost_vouchers.find_one({"status": "applied"}, {"_id": 0, "id": 1})
    if lcp:
        await expect_409_when_locked(db, admin, "bayar landed cost", "landed_cost_vouchers", lcp["id"], "POST", f"/landed-costs/{lcp['id']}/pay",
                                     {"amount": 1000, "method": "transfer", "cash_type": "kas_besar"})
    if not lc and not lcp:
        print("SKIP landed cost (tidak ada voucher pending/applied)")

    # ── special order create-pr / create-sku: terkunci → 409 ──
    so = db.special_orders.find_one({"status": {"$in": ["confirmed", "in_production"]}}, {"_id": 0, "id": 1, "linked_product_id": 1})
    if so:
        if not so.get("linked_product_id"):
            await expect_409_when_locked(db, admin, "create-sku special order", "special_orders", so["id"], "POST", f"/special-orders/{so['id']}/create-sku")
        else:
            db.special_orders.update_one({"id": so["id"]}, {"$set": {"saga_lock": LOCK}})
            r = await admin.post(f"/special-orders/{so['id']}/create-sku")
            db.special_orders.update_one({"id": so["id"]}, {"$unset": {"saga_lock": ""}})
            check("create-sku idempoten (SKU sudah ada) → 200 tanpa menyentuh kunci", r.status_code == 200 and r.json()["product"]["id"] == so["linked_product_id"], f"{r.status_code}")
        await expect_409_when_locked(db, admin, "create-pr special order", "special_orders", so["id"], "POST", f"/special-orders/{so['id']}/create-pr", {"warehouse_id": "", "notes": "probe"})
    else:
        print("SKIP special order create-pr/sku")

    # ── request-credit-approval: SO draft terkunci → 409; sukses → kunci lepas ──
    order = db.sales_orders.find_one({"status": "draft", "pending_approvals": {"$not": {"$elemMatch": {"type": "kredit", "status": "pending"}}}}, {"_id": 0, "id": 1, "pending_approvals": 1, "credit_hold": 1})
    if order:
        await expect_409_when_locked(db, admin, "minta approval kredit", "sales_orders", order["id"], "POST", f"/sales-orders/{order['id']}/request-credit-approval", {"reason": "probe"})
        r = await admin.post(f"/sales-orders/{order['id']}/request-credit-approval", json={"reason": "probe"})
        check("minta approval kredit → 200, kunci lepas", r.status_code == 200 and not locked(db, "sales_orders", order["id"]), f"{r.status_code} {r.text[:80]}")
        db.credit_overrides.delete_many({"order_id": order["id"], "reason": "probe"})
        db.sales_orders.update_one({"id": order["id"]}, {"$set": {"pending_approvals": order.get("pending_approvals", []), "credit_hold": order.get("credit_hold", False)}})
    else:
        print("SKIP request-credit-approval (tidak ada SO draft)")

    # ── RFQ award: terkunci → 409 ──
    rfq = db.rfqs.find_one({"status": "open"}, {"_id": 0, "id": 1, "suppliers": 1})
    if rfq:
        sid = (rfq.get("suppliers") or [{}])[0].get("supplier_id", "")
        await expect_409_when_locked(db, admin, "award RFQ", "rfqs", rfq["id"], "POST", f"/rfqs/{rfq['id']}/award", {"mode": "full", "full_supplier_id": sid})
    else:
        print("SKIP rfq award")

    # ── loading-check complete: sesi open terkunci → 409 ──
    sess = db.rfid_verify_sessions.find_one({"kind": "loading_check", "status": "open"}, {"_id": 0, "id": 1})
    if sess:
        await expect_409_when_locked(db, admin, "loading check complete", "rfid_verify_sessions", sess["id"], "POST", f"/outbound/loading-check/{sess['id']}/complete")
    else:
        print("SKIP loading-check")

    # ── esign verify: request pending terkunci (OTP salah harus 400 dulu → kunci tidak dicek); pakai OTP simulated ──
    src = db.sales_orders.find_one({}, {"_id": 0, "id": 1, "entity_id": 1})
    r = await admin.post("/esign/request", json={"doc_type": "sales_order", "source_id": src["id"], "entity_id": src.get("entity_id"), "signer_name": f"Probe {tag}", "signer_role": "pelanggan", "signer_contact": "0812", "channel": "simulated"})
    if r.status_code == 200 and r.json().get("reveal_code"):
        rid, otp = r.json()["request_id"], r.json()["reveal_code"]
        await expect_409_when_locked(db, admin, "esign verify", "esign_requests", rid, "POST", "/esign/verify", {"request_id": rid, "otp": otp, "signature_b64": "data:image/png;base64,AAAA"})
        rs = await asyncio.gather(*[admin.post("/esign/verify", json={"request_id": rid, "otp": otp, "signature_b64": "data:image/png;base64,AAAA"}) for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        n = db.document_signatures.count_documents({"request_id": rid})
        check("esign verify 2× bersamaan → satu signature, kunci lepas", n == 1 and 200 in codes and not locked(db, "esign_requests", rid), f"{codes} n={n}")
        db.document_signatures.delete_many({"request_id": rid})
        db.esign_requests.delete_one({"id": rid})
    else:
        print("SKIP esign:", r.status_code, r.text[:100])

    # ── payroll run 2× bersamaan → satu run ──
    ent = "ent_ksc"
    period = "2031-01"
    db.hr_payroll_runs.delete_many({"entity_id": ent, "period": period})
    rs = await asyncio.gather(*[admin.post("/hr/payroll/runs", json={"entity_id": ent, "period": period}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    n = db.hr_payroll_runs.count_documents({"entity_id": ent, "period": period})
    if 400 in codes and n == 0:
        print("SKIP payroll (tidak ada karyawan aktif):", rs[0].text[:80])
    else:
        ids = {x.json().get("id") for x in rs if x.status_code == 200}
        check("payroll run 2× bersamaan → satu run, id sama, tanpa slip yatim", n == 1 and len(ids) == 1 and db.hr_payslips.count_documents({"run_id": {"$nin": [d["id"] for d in db.hr_payroll_runs.find({}, {"id": 1})]}}) == 0, f"{codes} n={n} ids={ids}")
    for run in db.hr_payroll_runs.find({"entity_id": ent, "period": period}, {"id": 1}):
        db.hr_payslips.delete_many({"run_id": run["id"]})
    db.hr_payroll_runs.delete_many({"entity_id": ent, "period": period})

    # ── run-depreciation 2× bersamaan → entri per aset per periode tunggal ──
    fa = db.fin_fixed_assets.find_one({"status": "active"}, {"_id": 0, "id": 1, "entity_id": 1})
    if fa:
        period = "2030-06"
        before = dict(db.fin_fixed_assets.find_one({"id": fa["id"]}, {"_id": 0}))
        rs = await asyncio.gather(*[admin.post("/fixed-assets/run-depreciation", json={"period": period, "asset_id": fa["id"], "entity_id": fa.get("entity_id")}) for _ in range(2)])
        n = db.fin_depreciation_entries.count_documents({"asset_id": fa["id"], "period": period})
        check("run-depreciation 2× bersamaan → entri tunggal per aset+periode", n <= 1 and all(x.status_code in (200, 400) for x in rs), f"{[x.status_code for x in rs]} n={n}")
        for e in db.fin_depreciation_entries.find({"asset_id": fa["id"], "period": period}, {"je_id": 1}):
            if e.get("je_id"):
                db.journal_entries.delete_one({"id": e["je_id"]})
        db.fin_depreciation_entries.delete_many({"asset_id": fa["id"], "period": period})
        db.fin_fixed_assets.replace_one({"id": fa["id"]}, before)
    else:
        print("SKIP run-depreciation (tidak ada aset aktif)")

    # ── tidak ada kunci tertinggal ──
    leftovers = {c: db[c].count_documents({"saga_lock": {"$exists": True}}) for c in
                 ["product_templates", "vendor_bills", "tax_invoices_in", "landed_cost_vouchers", "special_orders", "sales_orders", "rfqs", "rfid_verify_sessions", "esign_requests", "makloon_orders", "sales_returns"]}
    check("tidak ada saga_lock tertinggal", not any(leftovers.values()), str({k: v for k, v in leftovers.items() if v}))

    print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAIL: {FAILS}"))
    await admin.aclose()


asyncio.run(main())
