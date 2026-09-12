"""
Iteration 33 - SIPRO tests:
  (A) GET /api/kpr/disbursement-summary (bank dashboard) - RBAC + data shape + consistency
  (B) POST /api/contracts/{cid}/cost-invoices - issue all-in cost invoice + RBAC
  (C) GET /api/contracts/{cid}/costs-ledger - verify unpaid invoice recorded
  (D) GET /api/cost-invoices/{iid}/pdf - PDF generation
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "Sipro#2026"

DEMO_CUSTOMER = "2ccf0ccb-e100-4c78-9f31-f0cfc2689c22"
DEMO_CONTRACT = "ee3005c4-0a99-4b32-a579-fa21e635cf69"


def _login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def token_super():
    return _login("superadmin@sipro.co.id")


@pytest.fixture(scope="module")
def token_finance():
    return _login("finance@sipro.co.id")


@pytest.fixture(scope="module")
def token_sales():
    return _login("sales@sipro.co.id")


@pytest.fixture(scope="module")
def token_site():
    return _login("site@sipro.co.id")


def _hdr(t): return {"Authorization": f"Bearer {t}"}


# ---------------------------- A) KPR bank summary ----------------------------
class TestKprDisbursementSummary:
    def test_forbidden_for_site_engineer(self, token_site):
        r = requests.get(f"{API}/kpr/disbursement-summary", headers=_hdr(token_site), timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    def test_finance_can_access(self, token_finance):
        r = requests.get(f"{API}/kpr/disbursement-summary", headers=_hdr(token_finance), timeout=15)
        assert r.status_code == 200, r.text

    def test_shape_and_consistency(self, token_super):
        r = requests.get(f"{API}/kpr/disbursement-summary", headers=_hdr(token_super), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        # totals shape
        totals = data["totals"]
        for k in ("plafon", "disbursed", "ready_amount", "waiting_amount",
                  "ready", "waiting", "no_scheme"):
            assert k in totals, f"missing totals.{k}"

        # banks[] shape
        banks = data["banks"]
        assert isinstance(banks, list) and len(banks) > 0, "banks empty"
        for b in banks:
            for k in ("bank", "apps", "plafon", "disbursed", "outstanding",
                      "ready", "ready_amount", "waiting", "waiting_amount", "no_scheme", "done"):
                assert k in b, f"missing banks[].{k}"

        # consistency: totals.plafon == sum(banks.plafon)
        sum_plafon = sum(b["plafon"] for b in banks)
        assert sum_plafon == totals["plafon"], f"plafon mismatch: totals={totals['plafon']} sum={sum_plafon}"

        # held[] shape + consistency
        held = data.get("held", [])
        assert isinstance(held, list)
        for h in held:
            for k in ("bank", "customer_name", "unit_code", "contract_no",
                      "tranche_code", "tranche_name", "amount", "condition", "ready", "days_since_akad"):
                assert k in h, f"missing held[].{k}"

        sum_ready_amt = sum(h["amount"] for h in held if h.get("ready"))
        assert sum_ready_amt == totals["ready_amount"], (
            f"ready_amount mismatch: sum_held_ready={sum_ready_amt} totals={totals['ready_amount']}"
        )

        # BTN demo checks
        btn = next((b for b in banks if b["bank"] == "BTN"), None)
        assert btn is not None, "BTN bank not found"
        assert btn["plafon"] >= 800_000_000, f"BTN plafon {btn['plafon']} < 800M"

        # Demo contract held tranches:
        demo_held = [h for h in held if h.get("contract_no") and h.get("bank") == "BTN"]
        # T2 must exist and be NOT ready (sertifikat unmet); T4/T5 ready
        t2 = [h for h in demo_held if h["tranche_code"] == "T2"]
        t4 = [h for h in demo_held if h["tranche_code"] == "T4"]
        t5 = [h for h in demo_held if h["tranche_code"] == "T5"]
        if t2:
            assert all(h["ready"] is False for h in t2), "T2 should not be ready (syarat sertifikat)"
        if t4:
            assert all(h["ready"] is True for h in t4), "T4 should be ready"
        if t5:
            assert all(h["ready"] is True for h in t5), "T5 should be ready"

        # no_scheme[] shape
        assert isinstance(data.get("no_scheme", []), list)


# ---------------------------- B) Cost invoice issuance ----------------------------
class TestCostInvoice:
    def test_sales_forbidden(self, token_sales):
        r = requests.post(f"{API}/contracts/{DEMO_CONTRACT}/cost-invoices",
                          headers=_hdr(token_sales), timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    def test_issue_or_conflict_then_ledger_and_pdf(self, token_finance, token_super):
        # First try issuing (may 200 or already have an open invoice → 400/409)
        r = requests.post(f"{API}/contracts/{DEMO_CONTRACT}/cost-invoices",
                          headers=_hdr(token_finance), timeout=30)
        assert r.status_code in (200, 400, 409), f"unexpected: {r.status_code} {r.text[:200]}"

        issued_first = r.status_code == 200
        if issued_first:
            body = r.json().get("data", {})
            num = body.get("number") or body.get("invoice_no") or body.get("no")
            assert num and str(num).startswith("INB"), f"invoice number missing/format: {body}"
            total = body.get("total") or body.get("amount")
            assert total == 11_500_000, f"expected total 11.500.000, got {total}"

            # Duplicate issue must be rejected
            r2 = requests.post(f"{API}/contracts/{DEMO_CONTRACT}/cost-invoices",
                               headers=_hdr(token_finance), timeout=15)
            assert r2.status_code in (400, 409), f"duplicate issue should be rejected: {r2.status_code} {r2.text[:200]}"

        # Ledger check
        r = requests.get(f"{API}/contracts/{DEMO_CONTRACT}/costs-ledger",
                         headers=_hdr(token_super), timeout=15)
        assert r.status_code == 200, r.text
        ledger = r.json()["data"]
        invoices = ledger.get("invoices", [])
        assert len(invoices) >= 1, "expected at least 1 cost invoice in ledger"
        inv = invoices[0]
        assert inv.get("status") in ("unpaid", "partial", "paid"), f"unexpected status {inv.get('status')}"
        # invoiced total = 11.5jt
        invoiced = inv.get("total") or inv.get("amount") or inv.get("invoiced")
        assert invoiced == 11_500_000, f"invoiced amount mismatch: {invoiced}"

        inv_id = inv.get("id") or inv.get("_id") or inv.get("invoice_id")
        assert inv_id, f"invoice id missing in {inv}"

        # PDF
        r = requests.get(f"{API}/cost-invoices/{inv_id}/pdf",
                         headers=_hdr(token_finance), timeout=30)
        assert r.status_code == 200, f"pdf status {r.status_code}: {r.text[:200]}"
        ctype = r.headers.get("content-type", "")
        assert "application/pdf" in ctype, f"unexpected content-type: {ctype}"
        assert r.content[:4] == b"%PDF", "content is not PDF"
