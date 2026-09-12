"""E2E verification for iteration 37: KPR plafon reconcile & Quotation with all-in."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"

CID = "9c31c6bc-6ab7-4116-b034-713f34d5ffea"
DEAL = "0dac1579-8a58-476a-a15b-59a350157a38"
LEAD = "7e9e5203-9b35-47eb-a21e-152404904c0c"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": "superadmin@sipro.co.id", "password": "Sipro#2026"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def H(token):
    return {"Authorization": f"Bearer {token}"}


# --- plafon-check ---
def _unwrap(j):
    return j.get("data") if isinstance(j, dict) and "data" in j else j


def test_plafon_check_shortfall(H):
    r = requests.get(f"{API}/contracts/{CID}/kpr/plafon-check", params={"plafon": 200000000}, headers=H)
    assert r.status_code == 200, r.text
    d = _unwrap(r.json())
    assert d["kind"] == "shortfall"
    assert d["shortfall"] == 55000000
    assert d["requires_due_date"] is True
    assert d["bank_portion"] == 255000000


def test_plafon_check_excess(H):
    r = requests.get(f"{API}/contracts/{CID}/kpr/plafon-check", params={"plafon": 300000000}, headers=H)
    assert r.status_code == 200
    d = _unwrap(r.json())
    assert d["kind"] == "excess"
    assert d["excess"] == 45000000


def test_plafon_check_match(H):
    r = requests.get(f"{API}/contracts/{CID}/kpr/plafon-check", params={"plafon": 255000000}, headers=H)
    assert r.status_code == 200
    d = _unwrap(r.json())
    assert d["kind"] == "match"


# --- quotation create with allin + booking fee ---
def test_quotation_create_and_pdf(H):
    # options
    opts = _unwrap(requests.get(f"{API}/quotations/options", headers=H).json())
    units = opts.get("units", [])
    assert units, "No units in options"
    unit_id = units[0]["id"]

    schemes = requests.get(f"{API}/allin-schemes", headers=H).json()
    schemes = _unwrap(schemes)
    if isinstance(schemes, dict):
        schemes = schemes.get("items") or schemes.get("data") or []
    assert schemes, "No allin schemes"
    scheme_id = schemes[0]["id"]

    payload = {
        "unit_id": unit_id,
        "lead_id": LEAD,
        "booking_fee": 7500000,
        "allin_scheme_id": scheme_id,
        "valid_days": 7,
    }
    r = requests.post(f"{API}/quotations", json=payload, headers=H)
    assert r.status_code == 200, r.text
    q = r.json()
    qid = q.get("id") or q.get("_id") or (q.get("data") or {}).get("id")
    data = q.get("data") or q
    assert data.get("booking_fee_gross") == 7500000 or data.get("booking_fee") == 7500000, f"booking fee missing: {data}"
    assert data.get("allin_scheme_id") == scheme_id
    costs = data.get("costs") or {}
    assert costs.get("components") or data.get("payment_breakdown"), f"no components/breakdown: {data}"

    # PDF
    if qid:
        p = requests.get(f"{API}/quotations/{qid}/pdf", headers=H)
        assert p.status_code == 200
        assert p.headers.get("content-type", "").startswith("application/pdf")

    # cleanup: delete from mongo directly via API if exists, else via mongo
    if qid:
        import pymongo
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        cli = pymongo.MongoClient(os.environ["MONGO_URL"])
        db = cli[os.environ["DB_NAME"]]
        db.quotations.delete_one({"id": qid})


# --- receipt on kpr_shortfall item (requires SP3K to have been staged; check if item already exists) ---
def test_receipt_on_kpr_shortfall_if_present(H):
    ar = requests.get(f"{API}/finance/ar/{DEAL}", headers=H).json()
    items = ar.get("items") or ar.get("data", {}).get("items") or []
    shortfall_items = [i for i in items if i.get("kind") == "kpr_shortfall"]
    if not shortfall_items:
        pytest.skip("no kpr_shortfall item present (SP3K not staged)")
    item_id = shortfall_items[0]["id"]
    r = requests.post(f"{API}/finance/ar/receipts", json={
        "deal_id": DEAL,
        "amount": 5000000,
        "method": "transfer",
        "allocations": [{"item_id": item_id, "amount": 5000000}],
    }, headers=H)
    assert r.status_code == 200, r.text
    rid = (r.json().get("data") or r.json()).get("id") or r.json().get("id")
    # cleanup
    if rid:
        requests.delete(f"{API}/finance/ar/receipts/{rid}", params={"reason": "pembersihan data uji otomatis"}, headers=H)
