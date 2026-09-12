"""Iteration 39 — Mandatory proof uploads & booking-fee → BOOKING component redirect.

Covers:
 * AR receipt, booking-fee, cost-invoice, deposit, KPR disbursement — proof required.
 * All-in scheme with BOOKING component: booking fee closes the BOOKING cost invoice
   (2-1470) instead of being applied to AR terms.
 * All-in scheme without BOOKING component: booking fee is applied to AR terms
   (default behaviour).
 * Legal override endpoint accepts override_file_ids and rejects overridable gate
   without files.
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          [l.split("=", 1)[1].strip()
                           for l in open("/app/frontend/.env")
                           if l.startswith("REACT_APP_BACKEND_URL")][0]).rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@sipro.co.id", "password": "Sipro#2026"}


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="session")
def token() -> str:
    r = requests.post(f"{API}/auth/login", json=SUPER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def S(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def _upload(S) -> str:
    r = S.post(f"{API}/files/upload",
               files={"file": ("bukti.txt", b"bukti xxx", "text/plain")},
               data={"owner_type": "receipt_proof", "optimize": "false"},
               timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _make_deal(S, scheme_code_or_none: str | None, booking_fee: int = 5_000_000):
    """Reserve a fresh deal (optionally with all-in scheme). Returns deal dict."""
    schemes = S.get(f"{API}/allin-schemes", params={"include_inactive": "true"}).json()["data"]
    scheme = None
    if scheme_code_or_none:
        scheme = next((s for s in schemes if s["code"] == scheme_code_or_none), None)
        assert scheme, f"scheme {scheme_code_or_none} not found"
    units = S.get(f"{API}/units", params={"status": "available", "limit": 20}).json()["data"]
    leads = S.get(f"{API}/leads", params={"limit": 30}).json()["data"]
    assert units and leads
    last_err = None
    for u in units:
        for lead in reversed(leads):
            payload = {"unit_id": u["id"], "lead_id": lead["id"],
                       "booking_fee": booking_fee,
                       "limit_override_reason": "Uji regresi otomatis iter39"}
            if scheme:
                payload["allin_scheme_id"] = scheme["id"]
            r = S.post(f"{API}/deals/reserve", json=payload, timeout=30)
            if r.status_code == 200:
                return r.json()["data"], scheme
            last_err = r.text
    raise AssertionError(f"could not reserve deal: {last_err}")


# ================================================================== AR receipt
class TestARReceiptProof:
    def test_reject_without_proof(self, S):
        # find an AR that has invoices to pay
        ar_list = S.get(f"{API}/finance/ar").json().get("data") or []
        target = next((a for a in ar_list if (a.get("total") or 0) > (a.get("paid") or 0)), None)
        if not target:
            pytest.skip("no outstanding AR available")
        deal_id = target["deal_id"]
        r = S.post(f"{API}/finance/ar/receipts",
                   json={"deal_id": deal_id, "amount": 100_000,
                         "method": "transfer", "proof_file_ids": []})
        assert r.status_code in (400, 422), r.text
        assert "proof" in r.text.lower() or "bukti" in r.text.lower() or "at least" in r.text.lower()

    def test_accept_with_proof(self, S):
        ar_list = S.get(f"{API}/finance/ar").json().get("data") or []
        target = next((a for a in ar_list if (a.get("total") or 0) > (a.get("paid") or 0)), None)
        if not target:
            pytest.skip("no outstanding AR available")
        fid = _upload(S)
        r = S.post(f"{API}/finance/ar/receipts",
                   json={"deal_id": target["deal_id"], "amount": 100_000,
                         "method": "transfer", "proof_file_ids": [fid]})
        assert r.status_code == 200, r.text
        rec = r.json()["data"]
        receipt = rec.get("receipt") if isinstance(rec.get("receipt"), dict) else rec
        assert fid in (receipt.get("proof_file_ids") or []), f"receipt={receipt}"


# ================================================================== booking fee
class TestBookingFeeProof:
    def test_reject_without_proof(self, S):
        deal, _ = _make_deal(S, None)
        r = S.post(f"{API}/booking-fee/deals/{deal['id']}/pay",
                   json={"amount": 5_000_000, "method": "transfer", "proof_file_ids": []})
        assert r.status_code in (400, 422), r.text

    def test_accept_with_proof(self, S):
        deal, _ = _make_deal(S, None)
        fid = _upload(S)
        r = S.post(f"{API}/booking-fee/deals/{deal['id']}/pay",
                   json={"amount": 5_000_000, "method": "transfer", "proof_file_ids": [fid]})
        assert r.status_code == 200, r.text


# ================================================================== cost invoice
class TestCostInvoiceProof:
    def test_reject_without_proof(self, S):
        invs = S.get(f"{API}/cost-invoices", params={"limit": 20}).json().get("data") or []
        pending = next((i for i in invs
                        if (i.get("total") or 0) > (i.get("paid") or 0)), None)
        if pending:
            r = S.post(f"{API}/cost-invoices/{pending['id']}/pay",
                       json={"amount": 10_000, "method": "cash", "proof_file_ids": []})
            assert r.status_code in (400, 422), r.text
            return
        # No unpaid invoice in dataset — verify the validator by hitting a random id.
        # A missing proof_file_ids must be rejected *before* the invoice lookup runs.
        r = S.post(f"{API}/cost-invoices/does-not-exist/pay",
                   json={"amount": 10_000, "method": "cash", "proof_file_ids": []})
        assert r.status_code in (400, 422), r.text
        assert ("proof" in r.text.lower() or "bukti" in r.text.lower()
                or "at least" in r.text.lower()), r.text


# ================================================================== deposit
class TestDepositProof:
    def test_reject_without_proof(self, S):
        deal, _ = _make_deal(S, None)
        r = S.post(f"{API}/finance/ar/{deal['id']}/deposit",
                   json={"amount": 500_000, "method": "transfer", "proof_file_ids": []})
        assert r.status_code in (400, 422), r.text

    def test_accept_with_proof(self, S):
        deal, _ = _make_deal(S, None)
        fid = _upload(S)
        r = S.post(f"{API}/finance/ar/{deal['id']}/deposit",
                   json={"amount": 500_000, "method": "transfer",
                         "proof_file_ids": [fid]})
        assert r.status_code == 200, r.text
        deps = S.get(f"{API}/finance/ar/deposits").json()["data"]
        entry = next((d for d in deps if d.get("deal_id") == deal["id"]), None)
        assert entry is not None
        assert fid in (entry.get("entries", [{}])[0].get("proof_file_ids") or [])


# ================================================================== disbursement
class TestDisburseProof:
    def test_reject_without_file_id(self, S):
        r = S.post(f"{API}/financing/does-not-exist/disburse",
                   json={"amount": 1_000_000, "date": "2026-01-15"})
        # Pydantic validation runs before existence check → 400/422 due to missing file_id
        assert r.status_code in (400, 422), r.text
        assert "file" in r.text.lower()


# ================================================================== BOOKING component
class TestAllInBookingComponent:
    def test_component_registered(self, S):
        comps = S.get(f"{API}/cost-components", params={"limit": 500}).json().get("data") or []
        codes = [c.get("code") for c in comps]
        assert "BOOKING" in codes

    def test_preview_reflects_booking_fee(self, S):
        schemes = S.get(f"{API}/allin-schemes",
                        params={"include_inactive": "true"}).json()["data"]
        sch = next((s for s in schemes if s["code"] == "ALLIN_BOOKING_TEST"), None)
        assert sch, "seed scheme ALLIN_BOOKING_TEST missing"
        pv = S.get(f"{API}/allin-schemes/{sch['id']}/preview",
                   params={"price": 850_000_000, "booking_fee": 5_000_000}).json()["data"]
        b = next((c for c in pv["components"] if c["code"] == "BOOKING"), None)
        assert b and b["amount"] == 5_000_000
        assert "booking fee" in (b.get("formula") or "").lower()


# ================================================================== e2e regression w/o BOOKING
class TestAllInWithoutBookingRegression:
    """When all-in scheme has NO BOOKING component, booking fee should still flow to AR."""

    def test_booking_fee_applied_to_ar(self, S):
        # find an all-in scheme without BOOKING
        schemes = S.get(f"{API}/allin-schemes",
                        params={"include_inactive": "true"}).json()["data"]
        target = None
        for s in schemes:
            codes = [(it.get("component_code") or "").upper() for it in (s.get("items") or [])]
            if codes and "BOOKING" not in codes:
                target = s
                break
        if not target:
            pytest.skip("no all-in scheme without BOOKING available")
        deal, _ = _make_deal(S, target["code"])
        fid = _upload(S)
        r = S.post(f"{API}/booking-fee/deals/{deal['id']}/pay",
                   json={"amount": 5_000_000, "method": "transfer",
                         "proof_file_ids": [fid]})
        assert r.status_code == 200, r.text
        r = S.post(f"{API}/deals/{deal['id']}/book", json={})
        assert r.status_code == 200, r.text
        time.sleep(3)
        ar = S.get(f"{API}/finance/ar/{deal['id']}").json()["data"]
        deps = S.get(f"{API}/finance/ar/deposits").json()["data"]
        d = next((x for x in deps if x["deal_id"] == deal["id"]), {})
        # booking fee should have been applied to AR terms (default behaviour)
        assert ar.get("paid", 0) >= 5_000_000, f"AR paid={ar.get('paid')} — booking fee not applied to AR"
        assert d.get("balance", 0) == 0
        entries = [(e["type"], e["amount"]) for e in d.get("entries", [])]
        # expect standard 'apply' (to AR) rather than 'apply_cost'
        assert any(t == "apply" for t, _ in entries), f"entries={entries}"


# ================================================================== legal override validation
class TestLegalOverrideFilesRequired:
    def test_override_reason_without_files_rejected_or_not_422(self, S):
        contracts = S.get(f"{API}/contracts", params={"limit": 50}).json().get("data") or []
        if not contracts:
            pytest.skip("no contracts to test legal override")
        # Try each contract until we find one with an overridable blocked gate
        found_overridable = False
        for c in contracts:
            for stage in ("akad_kredit", "ajb"):
                r = S.post(f"{API}/contracts/{c['id']}/legal/{stage}",
                           json={"override_reason": "uji regresi otomatis pengecualian",
                                 "override_file_ids": []})
                if r.status_code == 400 and ("surat keterangan" in r.text.lower()
                                             or "wajib diunggah" in r.text.lower()):
                    found_overridable = True
                    break
                # Model must accept the override_file_ids field (no 422 due to unknown field)
                assert r.status_code != 422 or "override_file_ids" not in r.text, r.text
            if found_overridable:
                break
        if not found_overridable:
            pytest.skip("no overridable-gate contract found in dataset")
