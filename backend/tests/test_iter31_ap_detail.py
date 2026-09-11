"""Iter31 — GET /api/finance/ap/bills/{bill_id} detail (read-only).

Covers three real bills:
  (a) termin from TRM/DEMO51/CAIR → CV Taman Hijau (claim+spk+retention + 1 journal)
  (b) CV Sumber Beton Sejahtera (partial, withholding)
  (c) PO TB Sumber Bangunan (po filled, status paid)
Plus 404 and RBAC/summary invariants.
"""
import os
import pytest
import requests
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
PASS = "Sipro#2026"

TERMIN_ID = "6000799f-b56e-494f-9752-a87872539001"      # CV Taman Hijau
BETON_ID  = "82874735-b3ed-400f-a2f5-2f630e995486"      # CV Sumber Beton Sejahtera (partial)
PO_ID     = "4d84f2de-b855-4216-a2dd-b9a1f048cb37"      # TB Sumber Bangunan (paid, po)


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PASS}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def finance_headers():
    return {"Authorization": f"Bearer {_login('finance@sipro.co.id')}"}


@pytest.fixture(scope="module")
def super_headers():
    return {"Authorization": f"Bearer {_login('superadmin@sipro.co.id')}"}


def _get(bill_id, headers):
    return requests.get(f"{BASE}/api/finance/ap/bills/{bill_id}", headers=headers, timeout=15)


# ── 404 branch ─────────────────────────────────────────────────────────────
def test_unknown_id_returns_404(finance_headers):
    r = _get("no-such-id-xxx", finance_headers)
    assert r.status_code == 404
    assert "tidak ditemukan" in r.json()["detail"].lower()


def test_both_roles_can_view(finance_headers, super_headers):
    for h in (finance_headers, super_headers):
        r = _get(TERMIN_ID, h)
        assert r.status_code == 200, r.text


# ── (a) termin TRM/DEMO51/CAIR ─────────────────────────────────────────────
def test_termin_bill_detail_shape(finance_headers):
    r = _get(TERMIN_ID, finance_headers)
    assert r.status_code == 200
    d = r.json()["data"]
    # top-level keys
    for k in ("bill", "project", "payments", "withholding", "retention",
              "source_retention", "release_bill", "claim", "spk", "po",
              "fund_requests", "journals", "summary"):
        assert k in d, f"missing key: {k}"
    assert d["bill"]["id"] == TERMIN_ID
    # from termin → claim + spk + retention present
    assert d["claim"] is not None, "claim harus terisi untuk tagihan dari termin"
    assert d["spk"] is not None, "spk harus terisi (via claim.spk_id)"
    assert d["retention"] is not None, "retention subcon harus terisi"
    assert d["retention"]["retention_number"].startswith("RET/"), d["retention"]["retention_number"]
    # journals: at least 1 (Dr 1-1600 / Cr 2-1100 / Cr 2-1200)
    assert len(d["journals"]) >= 1
    j0 = d["journals"][0]
    codes = {(l["account_code"], "d" if l.get("debit") else "c") for l in j0["lines"]}
    assert ("1-1600", "d") in codes
    assert ("2-1100", "c") in codes
    assert ("2-1200", "c") in codes
    # summary invariants
    s = d["summary"]
    assert s["paid"] == sum(int(p.get("amount", 0)) for p in d["payments"])
    assert s["paid_consistent"] is (s["paid"] == s["paid_recorded"])
    assert s["outstanding"] == s["net"] - s["paid_recorded"]
    assert s["claimed"] == int(d["bill"]["claimed"])
    assert s["retention_held"] == int(d["bill"]["retention_held"])


# ── (b) CV Sumber Beton Sejahtera partial with withholding ────────────────
def test_beton_partial_with_withholding(finance_headers):
    r = _get(BETON_ID, finance_headers)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["bill"]["status"] == "partial"
    # at least one payment, at least one withholding doc
    assert len(d["payments"]) >= 1
    # payment.amount matches bill.paid
    assert sum(int(p.get("amount", 0)) for p in d["payments"]) == int(d["bill"]["paid"])
    assert d["summary"]["paid_consistent"] is True
    # withholding doc(s) present because "1 pembayaran dengan potong PPh"
    assert len(d["withholding"]) >= 1, "harus ada bukti potong PPh"
    # journals: at least 2
    assert len(d["journals"]) >= 2
    # journal_debit ≥ paid + something
    assert d["summary"]["journal_debit"] > 0


# ── (c) PO TB Sumber Bangunan (paid) ──────────────────────────────────────
def test_po_bill_paid(finance_headers):
    r = _get(PO_ID, finance_headers)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["bill"]["status"] == "paid"
    assert d["po"] is not None, "po harus terisi"
    assert d["po"]["id"] == d["bill"].get("po_id")
    assert "po_number" in d["po"] and "po_type" in d["po"]
    # sum payments == bill.paid == bill.net
    assert d["summary"]["paid_consistent"] is True
    assert d["summary"]["outstanding"] == 0


# ── invariant: journals scoped to bill / retentions only ─────────────────
def test_journals_source_scope(finance_headers):
    r = _get(TERMIN_ID, finance_headers)
    d = r.json()["data"]
    allowed = {TERMIN_ID}
    if d["retention"]:
        allowed.add(d["retention"]["id"])
    if d["source_retention"]:
        allowed.add(d["source_retention"]["id"])
    for j in d["journals"]:
        assert j["source_id"] in allowed, f"journal source_id {j['source_id']} escapes scope"
