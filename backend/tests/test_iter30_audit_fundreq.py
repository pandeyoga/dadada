"""Iter30 backend tests: finance reconcile (lampu merah), HPP per unit, fund_request vendor_payment↔AP."""
import os
import time
import uuid
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PW = "Sipro#2026"


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PW}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def h_finance():
    return _login("finance@sipro.co.id")


@pytest.fixture(scope="module")
def h_pm():
    return _login("pm@sipro.co.id")


@pytest.fixture(scope="module")
def h_super():
    return _login("superadmin@sipro.co.id")


# ---------- Reconcile ----------
def test_reconcile_shape_and_ok(h_finance):
    r = requests.get(f"{BASE}/finance/reconcile", headers=h_finance, timeout=15)
    assert r.status_code == 200
    d = r.json()["data"]
    codes = {c["code"] for c in d["checks"]}
    for c in ("2-1100", "2-1200", "2-1400", "2-1450", "2-1600", "TB"):
        assert c in codes, f"missing {c}"
    for c in d["checks"]:
        for k in ("gl", "subledger", "diff", "ok", "hint"):
            assert k in c
    assert "events_pending" in d and "events_failed" in d
    assert d["ok"] is True, [c for c in d["checks"] if not c["ok"]]


def test_reconcile_detects_mismatch_and_recovers(h_finance):
    """Insert probe journal with imbalanced subledger effect for 2-1100 then remove."""
    from db import ORG_ID
    mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    jid = f"TEST_probe_{uuid.uuid4().hex[:8]}"
    entry_no = f"TEST-PROBE-{uuid.uuid4().hex[:6]}"
    doc = {
        "id": jid, "org_id": ORG_ID, "entry_no": entry_no,
        "source_type": "probe", "source_id": jid,
        "date": "2026-01-01", "memo": "TEST_probe mismatch",
        "lines": [
            {"account_code": "6-1300", "debit": 1000, "credit": 0},
            {"account_code": "2-1100", "debit": 0, "credit": 1000},
        ],
        "total_debit": 1000, "total_credit": 1000, "status": "posted",
    }

    async def _run():
        await mongo.journal_entries.insert_one(doc)
        try:
            r = requests.get(f"{BASE}/finance/reconcile", headers=h_finance, timeout=15)
            d = r.json()["data"]
            row = next(c for c in d["checks"] if c["code"] == "2-1100")
            assert row["ok"] is False, row
            assert row["diff"] == 1000, row
            assert d["ok"] is False
        finally:
            await mongo.journal_entries.delete_one({"id": jid})
        r2 = requests.get(f"{BASE}/finance/reconcile", headers=h_finance, timeout=15)
        d2 = r2.json()["data"]
        row2 = next(c for c in d2["checks"] if c["code"] == "2-1100")
        assert row2["ok"] is True, row2

    asyncio.get_event_loop().run_until_complete(_run())


# ---------- HPP per unit ----------
def test_hpp_unit_404(h_finance):
    r = requests.get(f"{BASE}/finance/hpp-unit?project_id=does-not-exist", headers=h_finance, timeout=15)
    assert r.status_code == 404


def test_hpp_unit_shape(h_finance):
    projects = requests.get(f"{BASE}/projects?limit=5", headers=h_finance, timeout=15).json().get("data", [])
    assert projects, "need a project"
    pid = projects[0]["id"]
    r = requests.get(f"{BASE}/finance/hpp-unit?project_id={pid}", headers=h_finance, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    for k in ("rows", "totals", "project_ap_total", "project_ap_unallocated",
              "gl_wip", "gl_accrual", "units_over_rab"):
        assert k in d, k
    if d["rows"]:
        r0 = d["rows"][0]
        for k in ("unit_code", "hpp", "contracted", "verified", "billed", "variance",
                  "realized_pct", "over_rab", "recognized"):
            assert k in r0


# ---------- fund_request vendor_payment ↔ AP ----------
def _create_bill(h, project_id, claimed=12_000_000):
    payload = {"vendor": f"TEST_vendor_{uuid.uuid4().hex[:6]}", "project_id": project_id,
               "claimed": claimed, "retention_pct": 0, "note": "TEST_iter30"}
    r = requests.post(f"{BASE}/finance/ap/bills", headers=h, json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    j = r.json()
    return j.get("data") if isinstance(j, dict) and "data" in j else j


def _cleanup_bill(bill_id):
    async def _run():
        mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        await mongo.fund_requests.delete_many({"ap_bill_id": bill_id})
        await mongo.payments_out.delete_many({"ap_invoice_id": bill_id})
        await mongo.journal_entries.delete_many({"source_type": "ap_payment", "source_id": bill_id})
        await mongo.journal_entries.delete_many({"source_type": "ap_invoice", "source_id": bill_id})
        await mongo.ap_invoices.delete_one({"id": bill_id})
    asyncio.get_event_loop().run_until_complete(_run())


def test_vendor_payment_flow_end_to_end(h_finance, h_pm):
    projects = requests.get(f"{BASE}/projects?limit=5", headers=h_finance, timeout=15).json().get("data", [])
    pid = projects[0]["id"]
    bill = _create_bill(h_finance, pid, claimed=12_000_000)
    bid = bill["id"]
    try:
        # not approved yet -> pengajuan should reject
        r_pending = requests.post(f"{BASE}/fund-requests", headers=h_pm, json={
            "type": "vendor_payment", "title": "TEST_vp pending",
            "amount": 12_000_000, "ap_bill_id": bid, "category": "lainnya"
        }, timeout=15)
        assert r_pending.status_code == 400, r_pending.text

        # approve bill
        ra = requests.post(f"{BASE}/finance/ap/bills/{bid}/approve", headers=h_finance, timeout=15)
        assert ra.status_code in (200, 201), ra.text

        # non-vendor_payment type with ap_bill_id -> 400
        rbad = requests.post(f"{BASE}/fund-requests", headers=h_pm, json={
            "type": "expense", "title": "TEST_bad type", "amount": 1000,
            "ap_bill_id": bid, "category": "lainnya"
        }, timeout=15)
        assert rbad.status_code == 400, rbad.text

        # over amount -> 400
        rover = requests.post(f"{BASE}/fund-requests", headers=h_pm, json={
            "type": "vendor_payment", "title": "TEST_over", "amount": 99_999_999,
            "ap_bill_id": bid, "category": "lainnya"
        }, timeout=15)
        assert rover.status_code == 400, rover.text

        # good pengajuan
        rok = requests.post(f"{BASE}/fund-requests", headers=h_pm, json={
            "type": "vendor_payment", "title": "TEST_vp ok", "amount": 12_000_000,
            "ap_bill_id": bid, "category": "lainnya"
        }, timeout=15)
        assert rok.status_code in (200, 201), rok.text
        fr = rok.json().get("data", rok.json())
        assert fr.get("ap_bill_id") == bid
        assert fr.get("payee_name") and "TEST_vendor" in fr.get("payee_name", "")
        assert fr.get("project_id") == pid
        assert fr.get("ap_bill_outstanding") == 12_000_000

        # duplicate submission -> 400 "sudah diajukan"
        rdup = requests.post(f"{BASE}/fund-requests", headers=h_pm, json={
            "type": "vendor_payment", "title": "TEST_dup", "amount": 12_000_000,
            "ap_bill_id": bid, "category": "lainnya"
        }, timeout=15)
        assert rdup.status_code == 400, rdup.text
        assert "sudah" in rdup.text.lower() or "diajukan" in rdup.text.lower()

        fr_id = fr["id"]
        # approve fund request
        rapr = requests.post(f"{BASE}/fund-requests/{fr_id}/approve", headers=h_finance,
                             json={"note": "TEST_ok"}, timeout=15)
        assert rapr.status_code in (200, 201), rapr.text

        # capture 6-1300 balance before disburse
        async def _bal(code):
            from revrec_cogs import account_balance
            from db import ORG_ID
            return await account_balance(ORG_ID, code)
        bal_before = asyncio.get_event_loop().run_until_complete(_bal("6-1300"))

        # disburse
        rdis = requests.post(f"{BASE}/fund-requests/{fr_id}/disburse",
                             headers=h_finance, json={"source": "bank"}, timeout=20)
        assert rdis.status_code in (200, 201), rdis.text
        settled = rdis.json().get("data", rdis.json())
        assert settled.get("status") == "settled"
        assert settled.get("ap_payment_id")
        assert settled.get("ap_bill_status") in ("paid", "partial")
        assert settled.get("journal_ids")

        # confirm bill paid
        # verify via list endpoint
        rlist = requests.get(f"{BASE}/finance/ap/bills?status=paid&limit=200", headers=h_finance, timeout=15).json()
        rows = rlist.get("data", [])
        rget = next((b for b in rows if b["id"] == bid), None)
        assert rget is not None and rget.get("status") == "paid", rget
        assert rget.get("paid") == 12_000_000

        # 6-1300 unchanged (no expense re-recognition)
        bal_after = asyncio.get_event_loop().run_until_complete(_bal("6-1300"))
        assert bal_after == bal_before, f"6-1300 changed: {bal_before} -> {bal_after}"

        # no journal source_type='fund_request' for this fr
        async def _check_no_fr_je():
            mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
            cnt = await mongo.journal_entries.count_documents({"source_type": "fund_request", "source_id": fr_id})
            return cnt
        assert asyncio.get_event_loop().run_until_complete(_check_no_fr_je()) == 0
    finally:
        _cleanup_bill(bid)


def test_reconcile_still_ok_after_cleanup(h_finance):
    r = requests.get(f"{BASE}/finance/reconcile", headers=h_finance, timeout=15)
    d = r.json()["data"]
    assert d["ok"] is True, [c for c in d["checks"] if not c["ok"]]
