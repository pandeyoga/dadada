"""Tests for payment proof on fund requests (iter152).

Covers:
- disburse accepts proof_ids and stores payment_proofs with filename
- /payment-proof appends proofs (approve-only; 400 if not disbursed; 403 for requester)
- requester (sales) sees payment_proofs via GET /{id} and can download via /files/{fid}?auth=token
"""
import os
import pathlib
import time

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PASS = "Sipro#2026"
FIXT = pathlib.Path("/app/tests/fixtures")


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PASS}, timeout=15)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _upload(tok, path, owner_id):
    with open(path, "rb") as f:
        r = requests.post(
            f"{BASE}/files/upload",
            headers=_h(tok),
            files={"file": (path.name, f, "image/jpeg")},
            data={"owner_type": "fund_request_payment", "owner_id": owner_id},
            timeout=30,
        )
    assert r.status_code in (200, 201), f"upload -> {r.status_code} {r.text}"
    j = r.json()
    return j.get("id") or j.get("data", {}).get("id")


@pytest.fixture(scope="module")
def tokens():
    return {
        "sales": _login("sales@sipro.co.id"),
        "finance": _login("finance@sipro.co.id"),
    }


@pytest.fixture(scope="module")
def created_ids():
    return {"fund_requests": [], "files": []}


def _create_fr(tok, title):
    payload = {
        "type": "expense", "title": title, "amount": 150000,
        "category": "lainnya", "urgency": "normal",
        "items": [{"description": "Beli ATK", "qty": 1, "unit_price": 150000}],
        "note": "iter152 test",
    }
    r = requests.post(f"{BASE}/fund-requests", json=payload, headers=_h(tok), timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()["data"]


def test_full_disburse_flow(tokens, created_ids):
    # 1. sales creates
    fr = _create_fr(tokens["sales"], f"TEST_iter152 proof {int(time.time())}")
    rid = fr["id"]
    created_ids["fund_requests"].append(rid)
    assert fr["status"] == "submitted"

    # 2. finance approves
    r = requests.post(f"{BASE}/fund-requests/{rid}/approve", json={}, headers=_h(tokens["finance"]), timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "approved"

    # 3. upload proof file (as finance)
    fid = _upload(tokens["finance"], FIXT / "bukti_offline_1.jpg", rid)
    created_ids["files"].append(fid)

    # 4. disburse with proof_ids
    r = requests.post(f"{BASE}/fund-requests/{rid}/disburse",
                      json={"source": "bank", "proof_ids": [fid], "note": "paid"},
                      headers=_h(tokens["finance"]), timeout=20)
    assert r.status_code == 200, r.text
    doc = r.json()["data"]
    assert doc["status"] == "settled"  # expense -> settled
    assert isinstance(doc.get("payment_proofs"), list) and len(doc["payment_proofs"]) == 1
    pp = doc["payment_proofs"][0]
    assert pp["id"] == fid
    assert pp.get("filename"), f"filename must be set: {pp}"
    assert pp.get("content_type", "").startswith("image/")

    # 5. finance can append another proof
    fid2 = _upload(tokens["finance"], FIXT / "bukti_offline_2.jpg", rid)
    created_ids["files"].append(fid2)
    r = requests.post(f"{BASE}/fund-requests/{rid}/payment-proof",
                      json={"proof_ids": [fid2]}, headers=_h(tokens["finance"]), timeout=15)
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]["payment_proofs"]) == 2

    # 6. sales (requester) can GET detail & see proofs
    r = requests.get(f"{BASE}/fund-requests/{rid}", headers=_h(tokens["sales"]), timeout=15)
    assert r.status_code == 200, r.text
    sales_doc = r.json()["data"]
    assert len(sales_doc.get("payment_proofs") or []) == 2
    first_fid = sales_doc["payment_proofs"][0]["id"]

    # 7. sales can download the image via files endpoint using auth query token
    r = requests.get(f"{BASE}/files/{first_fid}?auth={tokens['sales']}", timeout=15,
                     allow_redirects=True)
    assert r.status_code == 200, f"download {r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("image/") or len(r.content) > 100

    # 8. sales POST /payment-proof -> 403
    r = requests.post(f"{BASE}/fund-requests/{rid}/payment-proof",
                      json={"proof_ids": [fid]}, headers=_h(tokens["sales"]), timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


def test_payment_proof_requires_disbursed(tokens, created_ids):
    # New request in submitted state
    fr = _create_fr(tokens["sales"], f"TEST_iter152 nodisburse {int(time.time())}")
    rid = fr["id"]
    created_ids["fund_requests"].append(rid)

    # finance tries to add proof on NOT disbursed -> 400
    fid = _upload(tokens["finance"], FIXT / "bukti_offline_3.jpg", rid)
    created_ids["files"].append(fid)
    r = requests.post(f"{BASE}/fund-requests/{rid}/payment-proof",
                      json={"proof_ids": [fid]}, headers=_h(tokens["finance"]), timeout=15)
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"


def test_cleanup(tokens, created_ids):
    """Delete test fund_requests + related docs (journals, cash vouchers, events, activities, audit, files)."""
    try:
        from pymongo import MongoClient
    except Exception:
        pytest.skip("pymongo not available for cleanup")
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME not set")
    client = MongoClient(mongo_url)
    db = client[db_name]
    rids = created_ids["fund_requests"]
    fids = created_ids["files"]
    if rids:
        db.fund_requests.delete_many({"id": {"$in": rids}})
        db.journal_entries.delete_many({"source_id": {"$in": rids}})
        db.cash_vouchers.delete_many({"source_id": {"$in": rids}})
        db.events.delete_many({"entity_id": {"$in": rids}})
        db.activities.delete_many({"entity_id": {"$in": rids}})
        db.audit_logs.delete_many({"entity_id": {"$in": rids}})
        db.files.delete_many({"owner_id": {"$in": rids}})
    if fids:
        db.files.delete_many({"id": {"$in": fids}})
    client.close()
