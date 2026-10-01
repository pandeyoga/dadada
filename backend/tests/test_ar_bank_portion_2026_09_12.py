"""Sesi 2026-09-12 #3 — piutang: porsi bank vs porsi pembeli.

- Setoran pembeli TIDAK melunasi termin porsi bank (menunggu pencairan KPR) → pencairan tetap bisa.
- Nominal bebas (tidak harus FULL); kelebihan atas porsi pembeli ditolak dengan hint porsi bank.
- Alokasi eksplisit ke porsi bank hanya dengan allow_bank_portion.
- Pencairan (method kpr) melunasi porsi bank lebih dulu.
- Detail AR memuat rincian komponen all-in dari kontrak (live_breakdown).
"""
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from pymongo import MongoClient  # noqa: E402

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
PW = "Sipro#2026"
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@sipro.co.id", "password": PW}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def kpr_deal(sa):
    r = requests.get(f"{BASE}/contracts", params={"scheme": "kpr", "limit": 5}, headers=sa)
    rows = r.json()["data"]
    assert rows, "tidak ada kontrak KPR demo"
    return rows[0]


def _ar(sa, deal_id):
    r = requests.get(f"{BASE}/finance/ar/{deal_id}", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _receipt(sa, body):
    return requests.post(f"{BASE}/finance/ar/receipts", headers=sa, json=body)


def _delete_receipt(sa, rid):
    r = requests.delete(f"{BASE}/finance/ar/receipts/{rid}", headers=sa,
                        params={"reason": "pembersihan data uji otomatis"})
    assert r.status_code == 200, r.text


def test_ar_has_bank_portion_split(sa, kpr_deal):
    inv = _ar(sa, kpr_deal["deal_id"])
    bank = [i for i in inv["items"] if i.get("payer") == "bank"]
    assert bank, inv["items"]
    assert inv["bank_total"] == sum(i["amount"] for i in bank)
    assert inv["buyer_outstanding"] + inv["bank_outstanding"] == inv["outstanding"]
    assert inv["kpr_outstanding"] == inv["bank_outstanding"]
    assert inv["bank_outstanding"] > 0


def test_full_payment_rejected_with_bank_hint(sa, kpr_deal):
    inv = _ar(sa, kpr_deal["deal_id"])
    r = _receipt(sa, {"deal_id": kpr_deal["deal_id"], "amount": inv["outstanding"], "method": "transfer"})
    assert r.status_code == 400, r.text
    assert "Porsi bank" in r.text and "pencairan KPR" in r.text


def test_partial_buyer_payment_skips_bank_items(sa, kpr_deal):
    inv = _ar(sa, kpr_deal["deal_id"])
    bank_before = inv["bank_outstanding"]
    r = _receipt(sa, {"deal_id": kpr_deal["deal_id"], "amount": 1500, "method": "transfer"})
    assert r.status_code == 200, r.text
    rc = r.json()["data"]["receipt"]
    bank_ids = {i["id"] for i in inv["items"] if i.get("payer") == "bank"}
    assert all(a["item_id"] not in bank_ids for a in rc["allocations"])
    after = _ar(sa, kpr_deal["deal_id"])
    assert after["bank_outstanding"] == bank_before
    assert after["kpr_outstanding"] == bank_before  # pencairan tetap bisa
    _delete_receipt(sa, rc["id"])


def test_explicit_bank_allocation_requires_opt_in(sa, kpr_deal):
    inv = _ar(sa, kpr_deal["deal_id"])
    bank_item = next(i for i in inv["items"] if i.get("payer") == "bank")
    body = {"deal_id": kpr_deal["deal_id"], "amount": 1000, "method": "transfer",
            "allocations": [{"item_id": bank_item["id"], "amount": 1000}]}
    r = _receipt(sa, body)
    assert r.status_code == 400 and "PORSI BANK" in r.text, r.text
    r = _receipt(sa, {**body, "allow_bank_portion": True})
    assert r.status_code == 200, r.text
    rc = r.json()["data"]["receipt"]
    assert rc["allocations"][0]["item_id"] == bank_item["id"]
    _delete_receipt(sa, rc["id"])
    assert _ar(sa, kpr_deal["deal_id"])["bank_outstanding"] == inv["bank_outstanding"]


def test_kpr_method_pays_bank_portion_first(sa, kpr_deal):
    inv = _ar(sa, kpr_deal["deal_id"])
    bank_ids = {i["id"] for i in inv["items"] if i.get("payer") == "bank"}
    r = _receipt(sa, {"deal_id": kpr_deal["deal_id"], "amount": 2000, "method": "kpr"})
    assert r.status_code == 200, r.text
    rc = r.json()["data"]["receipt"]
    assert rc["allocations"] and all(a["item_id"] in bank_ids for a in rc["allocations"])
    after = _ar(sa, kpr_deal["deal_id"])
    assert after["bank_outstanding"] == inv["bank_outstanding"] - 2000
    assert after["buyer_outstanding"] == inv["buyer_outstanding"]
    _delete_receipt(sa, rc["id"])


def test_scheme_terms_accept_payer(sa):
    r = requests.get(f"{BASE}/payment-schemes", headers=sa)
    assert r.status_code == 200, r.text
    body = {"name": "Uji KPR porsi bank", "kind": "kpr", "code": "uji-kpr-porsi-bank", "active": True,
            "terms": [{"label": "DP 10%", "basis": "percent", "value": 10},
                      {"label": "Pencairan bank 90%", "basis": "percent", "value": 90, "payer": "bank",
                       "due_offset_days": 45}]}
    r = requests.post(f"{BASE}/payment-schemes", headers=sa, json=body)
    assert r.status_code in (200, 201), r.text
    doc = r.json()["data"]
    assert [t["payer"] for t in doc["items"]] == ["buyer", "bank"]
    sim = requests.post(f"{BASE}/payment-schemes/simulate", headers=sa,
                        json={"terms": body["terms"], "price": 500_000_000})
    if sim.status_code == 200:
        rows = sim.json()["data"]["rows"]
        assert rows[1]["payer"] == "bank"
    _db.payment_schemes.delete_one({"id": doc["id"]})


def test_live_breakdown_follows_contract_costs(sa, kpr_deal):
    """Komponen all-in yang dipilih di KONTRAK (bukan saat reservasi) tampil di piutang."""
    org = kpr_deal["org_id"]
    c = _db.contracts.find_one({"id": kpr_deal["id"]}, {"_id": 0, "costs": 1})
    old = c.get("costs")
    comps = [{"code": "BPHTB", "name": "BPHTB", "amount": 25_000_000, "treatment": "customer_pass_through"},
             {"code": "NOTARY_FEE", "name": "Biaya notaris", "amount": 5_000_000, "treatment": "developer_borne"}]
    _db.contracts.update_one({"id": kpr_deal["id"]},
                             {"$set": {"costs": {**(old or {}), "components": comps, "scheme_name": "Exclude uji"}}})
    try:
        inv = _ar(sa, kpr_deal["deal_id"])
        bd = inv["breakdown"]
        codes = {x["code"]: x for x in bd["cost_components"]}
        assert codes["BPHTB"]["treatment"] == "customer_pass_through"
        assert bd["cost_total"] == 25_000_000 and bd["developer_cost_total"] == 5_000_000
        assert bd["allin_scheme_name"] == "Exclude uji"
        assert bd["buyer_total"] == bd["net_price"] + 25_000_000 + (bd.get("addon_net_total") or 0)
        pb = bd.get("payment_breakdown")
        if pb:
            pcodes = [r["code"] for r in pb["rows"]]
            assert "COST:BPHTB" in pcodes and "COST_TOTAL" in pcodes
    finally:
        _db.contracts.update_one({"id": kpr_deal["id"]},
                                 {"$set": {"costs": old}} if old is not None else {"$unset": {"costs": ""}})
    assert org
