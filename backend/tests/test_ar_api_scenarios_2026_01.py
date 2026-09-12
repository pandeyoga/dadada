"""API scenarios for review: AR detail split & receipt rules on deal A-01."""
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
PW = "Sipro#2026"
DEAL = "5a6ef161-2889-4f97-9519-ea6221ad6666"


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@sipro.co.id", "password": PW}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def _ar(sa):
    r = requests.get(f"{BASE}/finance/ar/{DEAL}", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_ar_detail_split(sa):
    d = _ar(sa)
    assert d["bank_outstanding"] == 255_000_000
    assert d["kpr_outstanding"] == d["bank_outstanding"]
    assert d["buyer_outstanding"] + d["bank_outstanding"] == d["outstanding"]
    # third item should be KPR bank
    bank_items = [it for it in d["items"] if it.get("payer") == "bank"]
    assert bank_items, "no bank payer items"
    assert any("KPR" in it.get("label", "") or "Pelunasan" in it.get("label", "") for it in bank_items)


def test_receipt_full_rejected(sa):
    d = _ar(sa)
    body = {"deal_id": DEAL, "amount": d["outstanding"], "method": "transfer", "date": "2026-01-15"}
    r = requests.post(f"{BASE}/finance/ar/receipts", headers=sa, json=body)
    assert r.status_code == 400
    assert "porsi bank" in r.text.lower() or "kpr" in r.text.lower()


def test_receipt_small_ok_and_cleanup(sa):
    d0 = _ar(sa)
    body = {"deal_id": DEAL, "amount": 2000, "method": "transfer", "date": "2026-01-15"}
    r = requests.post(f"{BASE}/finance/ar/receipts", headers=sa, json=body)
    assert r.status_code == 200, r.text
    rid = r.json()["data"]["receipt"]["id"]
    d1 = _ar(sa)
    assert d1["bank_outstanding"] == d0["bank_outstanding"]
    assert d1["buyer_outstanding"] == d0["buyer_outstanding"] - 2000
    # cleanup
    dr = requests.delete(
        f"{BASE}/finance/ar/receipts/{rid}",
        headers=sa,
        params={"reason": "cleanup uji otomatis pytest"},
    )
    assert dr.status_code in (200, 204), dr.text
    d2 = _ar(sa)
    assert d2["buyer_outstanding"] == d0["buyer_outstanding"]
