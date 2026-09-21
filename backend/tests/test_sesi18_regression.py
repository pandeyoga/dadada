"""Regresi Sesi 18 (INV-ATOMIC-01) — jalur SUKSES + sampling saga_lock 409 + audit
leftover locks. Menguji ratchet 24 → 0: multi-koleksi endpoint memakai atomic claim /
CAS / kompensasi. Fixture WAJIB dibersihkan (lihat teardown).

Jalankan:
    pytest /app/backend/tests/test_sesi18_regression.py -v --tb=short \
        --junitxml=/app/test_reports/pytest/sesi18_regression.xml
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import uuid

import httpx
import pytest
from pymongo import MongoClient

# ── env bootstrap (ambil dari .env kalau belum di lingkungan) ───────────────────
ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p, _keys in [(ROOT / "frontend/.env", ("REACT_APP_BACKEND_URL",)),
                  (ROOT / "backend/.env", ("MONGO_URL", "DB_NAME"))]:
    if _p.exists():
        for line in _p.read_text().splitlines():
            k, _, v = line.partition("=")
            if k in _keys and not os.environ.get(k):
                os.environ[k] = v.strip().strip('"')

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
LOCK = {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}


# ── fixtures ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="session")
def admin_token():
    with httpx.Client(base_url=API, timeout=60) as c:
        r = c.post("/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
        assert r.status_code == 200, r.text
        return r.json().get("access_token") or r.json().get("token")


@pytest.fixture()
def admin(admin_token):
    c = httpx.Client(base_url=API, timeout=90)
    c.headers["X-Entity-Id"] = "ent_ksc"
    # some backends want cookie session, but Authorization Bearer is expected here
    c.headers["Authorization"] = f"Bearer {admin_token}"
    yield c
    c.close()


@pytest.fixture()
def sales(admin_token):
    with httpx.Client(base_url=API, timeout=60) as c:
        r = c.post("/auth/login", json={"email": "sales@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    c = httpx.Client(base_url=API, timeout=90)
    c.headers["X-Entity-Id"] = "ent_ksc"
    c.headers["Authorization"] = f"Bearer {tok}"
    yield c
    c.close()


def _locked(db, coll, _id):
    return "saga_lock" in (db[coll].find_one({"id": _id}, {"_id": 0, "saga_lock": 1}) or {})


# ── (1) POST /api/users + PATCH /api/users/{id} ────────────────────────────────
class TestUsersSuccess:
    def test_create_and_patch_user_success(self, admin, db):
        email = f"test_sesi18_{uuid.uuid4().hex[:6]}@example.com"
        payload = {"name": "TEST Sesi18", "email": email, "role": "sales"}
        r = admin.post("/users", json=payload)
        assert r.status_code == 200, r.text
        user = r.json()
        uid = user["id"]
        assert user["email"] == email
        # PATCH nama
        r2 = admin.patch(f"/users/{uid}", json={"data": {"name": "TEST Sesi18 Updated"}})
        assert r2.status_code == 200, r2.text
        assert r2.json().get("name") == "TEST Sesi18 Updated"
        # cleanup
        db.users.delete_one({"id": uid})


# ── (2) permintaan sampel kini baris SO ber-is_sample (lihat test_sample_pos_flow) ──

# ── (3) Payroll runs 2× bersamaan → satu run id ────────────────────────────────
class TestPayrollRaceSingleRun:
    def test_two_parallel_runs_yield_one(self, admin_token, db):
        ent, period = "ent_ksc", "2032-02"
        db.hr_payroll_runs.delete_many({"entity_id": ent, "period": period})

        async def _go():
            async with httpx.AsyncClient(base_url=API, timeout=90) as c:
                c.headers["X-Entity-Id"] = "ent_ksc"
                c.headers["Authorization"] = f"Bearer {admin_token}"
                return await asyncio.gather(*[
                    c.post("/hr/payroll/runs", json={"entity_id": ent, "period": period})
                    for _ in range(2)
                ])

        rs = asyncio.run(_go())
        codes = sorted(x.status_code for x in rs)
        n = db.hr_payroll_runs.count_documents({"entity_id": ent, "period": period})
        if 400 in codes and n == 0:
            pytest.skip(f"payroll skip (no active employees): {rs[0].text[:100]}")
        ids = {x.json().get("id") for x in rs if x.status_code == 200}
        assert n == 1, f"expected 1 run got {n} codes={codes}"
        assert len(ids) == 1, f"expected identical id, got {ids}"
        # cleanup
        for run in db.hr_payroll_runs.find({"entity_id": ent, "period": period}, {"id": 1}):
            db.hr_payslips.delete_many({"run_id": run["id"]})
        db.hr_payroll_runs.delete_many({"entity_id": ent, "period": period})


# ── (4) run-depreciation success + idempotent (posted 0 pada ulangan) ──────────
class TestRunDepreciationSuccess:
    def test_run_depreciation_and_idempotent(self, admin, db):
        fa = db.fin_fixed_assets.find_one({"status": "active"}, {"_id": 0})
        if not fa:
            pytest.skip("no active fixed asset")
        aid, period = fa["id"], "2030-07"
        before = dict(fa)
        # jaga kebersihan: hapus entri periode ini kalau ada
        for e in db.fin_depreciation_entries.find({"asset_id": aid, "period": period}, {"je_id": 1}):
            if e.get("je_id"):
                db.journal_entries.delete_one({"id": e["je_id"]})
        db.fin_depreciation_entries.delete_many({"asset_id": aid, "period": period})

        r1 = admin.post("/fixed-assets/run-depreciation",
                        json={"period": period, "asset_id": aid, "entity_id": fa.get("entity_id", "")})
        assert r1.status_code == 200, r1.text
        j1 = r1.json()
        # ulangi → aset dilewati (posted 0)
        r2 = admin.post("/fixed-assets/run-depreciation",
                        json={"period": period, "asset_id": aid, "entity_id": fa.get("entity_id", "")})
        assert r2.status_code == 200, r2.text
        assert r2.json().get("posted", 0) == 0, r2.text

        # cleanup: hapus entri+JE + kembalikan field aset
        for e in db.fin_depreciation_entries.find({"asset_id": aid, "period": period}, {"je_id": 1}):
            if e.get("je_id"):
                db.journal_entries.delete_one({"id": e["je_id"]})
        db.fin_depreciation_entries.delete_many({"asset_id": aid, "period": period})
        # restore fields
        db.fin_fixed_assets.replace_one({"id": aid}, before)
        assert j1.get("period") == period


# ── (5) input-tax create + cancel; bill kembali eligible ───────────────────────
class TestInputTaxInvoiceSuccess:
    def test_create_and_cancel_input_tax(self, admin, db):
        bill = db.vendor_bills.find_one(
            {"status": {"$in": ["posted", "paid"]}, "ppn_amount": {"$gt": 0},
             "input_faktur_status": {"$nin": ["recorded", "reported", "credited"]}},
            {"_id": 0, "id": 1})
        if not bill:
            pytest.skip("no eligible vendor bill")
        body = {"vendor_bill_id": bill["id"],
                "nsfp": "010." + uuid.uuid4().hex[:3] + "-26.9" + str(uuid.uuid4().int)[:7]}
        r = admin.post("/input-tax-invoices", json=body)
        assert r.status_code == 200, r.text
        fpm = db.tax_invoices_in.find_one(
            {"vendor_bill_id": bill["id"], "status": "recorded"}, {"_id": 0, "id": 1})
        assert fpm, "tax invoice not created"
        # cancel
        rc = admin.post(f"/input-tax-invoices/{fpm['id']}/cancel", json={"reason": "TEST sesi18"})
        assert rc.status_code == 200, rc.text
        # bill kembali eligible: input_faktur_status = cancelled
        b = db.vendor_bills.find_one({"id": bill["id"]}, {"_id": 0, "input_faktur_status": 1, "saga_lock": 1})
        assert b.get("input_faktur_status") == "cancelled"
        assert "saga_lock" not in b
        # cleanup
        db.tax_invoices_in.delete_many({"vendor_bill_id": bill["id"], "nsfp": body["nsfp"]})
        db.vendor_bills.update_one({"id": bill["id"]},
                                   {"$unset": {"input_faktur_status": "", "input_faktur_id": "",
                                               "input_faktur_number": "", "input_faktur_nsfp": ""}})


# ── (6) DELETE product-templates: varian template_id "" ────────────────────────
class TestDeleteProductTemplate:
    def test_delete_synthetic_template(self, admin, db):
        tag = "P18-" + uuid.uuid4().hex[:4]
        tid = "tpl_test18_" + uuid.uuid4().hex[:4]
        pid = "prd_test18_" + uuid.uuid4().hex[:4]
        db.product_templates.insert_one({"id": tid, "name": f"Tpl {tag}", "code": tag,
                                          "created_at": "2026-09-06T00:00:00+00:00"})
        db.products.insert_one({"id": pid, "name": f"Var {tag}", "sku": tag,
                                "template_id": tid, "price": 1, "status": "active"})
        r = admin.delete(f"/product-templates/{tid}")
        assert r.status_code == 200, r.text
        assert db.product_templates.find_one({"id": tid}) is None
        assert db.products.find_one({"id": pid})["template_id"] == ""
        # cleanup
        db.products.delete_one({"id": pid})


# ── (7) esign request+verify; verify ulang → 400 ──────────────────────────────
class TestEsignVerifyIdempotent:
    def test_verify_twice_second_400(self, admin, db):
        so = db.sales_orders.find_one({}, {"_id": 0, "id": 1, "entity_id": 1})
        if not so:
            pytest.skip("no sales order")
        r = admin.post("/esign/request", json={
            "doc_type": "sales_order", "source_id": so["id"],
            "entity_id": so.get("entity_id") or "ent_ksc",
            "signer_name": "TEST sesi18", "signer_role": "pelanggan",
            "signer_contact": "0812", "channel": "simulated"})
        if r.status_code != 200 or not r.json().get("reveal_code"):
            pytest.skip(f"esign request failed: {r.status_code} {r.text[:150]}")
        rid, otp = r.json()["request_id"], r.json()["reveal_code"]
        body = {"request_id": rid, "otp": otp, "signature_b64": "data:image/png;base64,AAAA"}
        r1 = admin.post("/esign/verify", json=body)
        assert r1.status_code == 200, r1.text
        r2 = admin.post("/esign/verify", json=body)
        assert r2.status_code == 400, r2.text
        assert "selesai" in r2.text.lower() or "sudah" in r2.text.lower()
        # cleanup
        db.document_signatures.delete_many({"request_id": rid})
        db.esign_requests.delete_one({"id": rid})


# ── (8) POST inventory/putaway roll ke bin valid → 200 ─────────────────────────
class TestPutawaySuccess:
    def test_putaway_roll_to_bin(self, admin, db):
        q = admin.get("/inventory/putaway/queue")
        if q.status_code != 200:
            pytest.skip(f"queue not accessible: {q.status_code}")
        rolls = (q.json() or {}).get("rolls") or []
        if not rolls:
            pytest.skip("no putaway candidate")
        candidate = rolls[0]
        wh = db.warehouses.find_one({"id": candidate["warehouse_id"]}, {"_id": 0})
        # Kumpulkan bin_id (nested zones→racks→bins)
        bin_id = None
        for z in (wh or {}).get("zones", []) or []:
            for rack in z.get("racks", []) or []:
                for b in rack.get("bins", []) or []:
                    if b.get("id"):
                        bin_id = b["id"]
                        break
                if bin_id:
                    break
            if bin_id:
                break
        if not bin_id:
            pytest.skip("no bin in warehouse")
        original_bin = db.inventory_rolls.find_one({"id": candidate["id"]}, {"_id": 0, "bin_id": 1}).get("bin_id")
        r = admin.post("/inventory/putaway",
                       json={"roll_id": candidate["id"], "bin_id": bin_id})
        assert r.status_code == 200, r.text
        after = db.inventory_rolls.find_one({"id": candidate["id"]}, {"_id": 0, "bin_id": 1})
        assert after["bin_id"] == bin_id
        # restore
        db.inventory_rolls.update_one({"id": candidate["id"]}, {"$set": {"bin_id": original_bin}})


# ── (9) Sampling 3-4 saga_lock 409 checks ──────────────────────────────────────
class TestSagaLockSampling:
    """Sampling: probe internal sudah lolos, cukup 3-4 endpoint di sini."""

    def _lock_then_call(self, admin, db, coll, doc_id, method, path, json=None):
        db[coll].update_one({"id": doc_id}, {"$set": {"saga_lock": LOCK}})
        try:
            r = admin.request(method, path, json=json)
        finally:
            db[coll].update_one({"id": doc_id}, {"$unset": {"saga_lock": ""}})
        return r

    def test_product_template_delete_locked_409(self, admin, db):
        tid = "tpl_lock18_" + uuid.uuid4().hex[:4]
        db.product_templates.insert_one({"id": tid, "name": "Lock", "code": tid,
                                          "created_at": "2026-09-06T00:00:00+00:00"})
        try:
            r = self._lock_then_call(admin, db, "product_templates", tid,
                                     "DELETE", f"/product-templates/{tid}")
            assert r.status_code == 409, f"{r.status_code} {r.text[:120]}"
            assert "SAGA_IN_PROGRESS" in r.text
        finally:
            db.product_templates.delete_one({"id": tid})

    def test_rfq_award_locked_409(self, admin, db):
        rfq = db.rfqs.find_one({"status": "open"}, {"_id": 0, "id": 1, "suppliers": 1})
        if not rfq:
            pytest.skip("no open RFQ")
        sid = (rfq.get("suppliers") or [{}])[0].get("supplier_id", "")
        r = self._lock_then_call(admin, db, "rfqs", rfq["id"], "POST",
                                 f"/rfqs/{rfq['id']}/award",
                                 {"mode": "full", "full_supplier_id": sid})
        assert r.status_code == 409, r.text[:120]
        assert "SAGA_IN_PROGRESS" in r.text

    def test_input_tax_locked_409(self, admin, db):
        bill = db.vendor_bills.find_one(
            {"status": {"$in": ["posted", "paid"]}, "ppn_amount": {"$gt": 0},
             "input_faktur_status": {"$nin": ["recorded", "reported", "credited"]}},
            {"_id": 0, "id": 1})
        if not bill:
            pytest.skip("no eligible vendor bill")
        body = {"vendor_bill_id": bill["id"],
                "nsfp": "010." + uuid.uuid4().hex[:3] + "-26.9" + str(uuid.uuid4().int)[:7]}
        r = self._lock_then_call(admin, db, "vendor_bills", bill["id"], "POST",
                                 "/input-tax-invoices", body)
        assert r.status_code == 409, r.text[:120]
        assert "SAGA_IN_PROGRESS" in r.text

    def test_special_order_create_pr_locked_409(self, admin, db):
        so = db.special_orders.find_one({"status": {"$in": ["confirmed", "in_production"]}},
                                        {"_id": 0, "id": 1})
        if not so:
            pytest.skip("no special order")
        r = self._lock_then_call(admin, db, "special_orders", so["id"], "POST",
                                 f"/special-orders/{so['id']}/create-pr",
                                 {"warehouse_id": "", "notes": "TEST"})
        assert r.status_code == 409, r.text[:120]
        assert "SAGA_IN_PROGRESS" in r.text


# ── (10) Tidak ada saga_lock tertinggal di koleksi yang dilindungi ─────────────
class TestNoLeftoverSagaLocks:
    def test_no_leftover_saga_locks(self, db):
        colls = ["product_templates", "vendor_bills", "tax_invoices_in", "landed_cost_vouchers",
                 "special_orders", "sales_orders", "rfqs", "rfid_verify_sessions",
                 "esign_requests", "makloon_orders", "sales_returns", "product_categories"]
        # abaikan kunci sengaja-tanam dari test lain (by=probe) — hanya tangkap kunci REAL leftover
        left = {c: db[c].count_documents({"saga_lock": {"$exists": True},
                                          "saga_lock.by": {"$ne": "probe"}}) for c in colls}
        stray = {k: v for k, v in left.items() if v}
        assert not stray, f"stray saga_lock: {stray}"


# ── (11) GET /api/saga-locks (admin) mencakup koleksi baru ─────────────────────
class TestSagaLocksEndpoint:
    def test_get_saga_locks_lists_new_collections(self, admin, db):
        # inject one saga_lock on product_categories & special_orders & rfqs to prove listing works
        cats = list(db.product_categories.find({}, {"_id": 0, "id": 1}).limit(1))
        sos = list(db.special_orders.find({}, {"_id": 0, "id": 1}).limit(1))
        rfqs = list(db.rfqs.find({}, {"_id": 0, "id": 1}).limit(1))
        injected = []
        if cats:
            db.product_categories.update_one({"id": cats[0]["id"]}, {"$set": {"saga_lock": LOCK}})
            injected.append(("product_categories", cats[0]["id"]))
        if sos:
            db.special_orders.update_one({"id": sos[0]["id"]}, {"$set": {"saga_lock": LOCK}})
            injected.append(("special_orders", sos[0]["id"]))
        if rfqs:
            db.rfqs.update_one({"id": rfqs[0]["id"]}, {"$set": {"saga_lock": LOCK}})
            injected.append(("rfqs", rfqs[0]["id"]))
        try:
            r = admin.get("/saga-locks")
            assert r.status_code == 200, r.text
            listed = {(x.get("collection"), x.get("id")) for x in r.json()}
            for pair in injected:
                assert pair in listed, f"missing {pair} in listing"
            # koleksi tercantum di response harus mencakup yang di-inject
            colls_in_resp = {x.get("collection") for x in r.json()}
            for c, _ in injected:
                assert c in colls_in_resp
        finally:
            for coll, _id in injected:
                db[coll].update_one({"id": _id}, {"$unset": {"saga_lock": ""}})
