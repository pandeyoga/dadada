"""Sesi 2026-09-12 #4 — plafon SP3K vs porsi bank (kpr_plafon) + penawaran ≡ reservasi.

- plafon < porsi bank → termin "Selisih Plafon KPR" (payer buyer, jatuh tempo wajib), porsi bank turun,
  total AR tetap; setoran pembeli boleh melunasinya; pencairan tidak menyentuhnya.
- plafon > porsi bank → porsi bank naik, termin pembeli turun.
- /kpr/plafon-check memberi pratinjau.
- Penawaran menyimpan allin_scheme_id/costs/booking_fee; konversi membawa costs ke deal.
Uji ini MENGEMBALIKAN state (financing_app & AR) di akhir modul.
"""
import copy
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
SNAP = {}


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@sipro.co.id", "password": PW}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def kpr_contract(sa):
    r = requests.get(f"{BASE}/contracts", params={"scheme": "kpr", "limit": 5}, headers=sa)
    rows = [c for c in r.json()["data"] if _db.ar_invoices.find_one({"deal_id": c["deal_id"], "items.payer": "bank"})]
    assert rows, "tidak ada kontrak KPR demo dengan porsi bank pada AR"
    c = rows[0]
    app_before = _db.financing_apps.find_one({"deal_id": c["deal_id"]}, {"_id": 0})
    inv_before = _db.ar_invoices.find_one({"deal_id": c["deal_id"]}, {"_id": 0})
    SNAP["inv"] = inv_before
    contract_before = _db.contracts.find_one({"id": c["id"]}, {"_id": 0, "costs": 1, "legal": 1})
    yield c
    # pulihkan
    _db.receipts.delete_many({"deal_id": c["deal_id"], "note": {"$regex": "UJI-PLAFON"}})
    _db.ar_invoices.replace_one({"id": inv_before["id"]}, copy.deepcopy(inv_before))
    _db.financing_apps.delete_many({"deal_id": c["deal_id"]})
    if app_before:
        _db.financing_apps.insert_one(dict(app_before))
    _db.contracts.update_one({"id": c["id"]}, {"$set": {"costs": contract_before.get("costs") or {},
                                                        "legal": contract_before.get("legal") or {}}})


def _ar(sa, deal_id):
    r = requests.get(f"{BASE}/finance/ar/{deal_id}", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _stage(sa, cid, stage, body):
    return requests.post(f"{BASE}/contracts/{cid}/kpr/stage/{stage}", headers=sa, json=body)


def _to_sp3k_ready(sa, c):
    """Reset pengajuan ke tahap sebelum SP3K (idempoten untuk run ulang)."""
    _db.financing_apps.delete_many({"deal_id": c["deal_id"]})
    for st in ("berkas_lengkap", "diajukan_ke_bank"):
        r = _stage(sa, c["id"], st, {"bank": "BTN", "note": "uji plafon"})
        assert r.status_code == 200, r.text
    use_appraisal = requests.get(f"{BASE}/contracts/{c['id']}/kpr", headers=sa).json()["data"]
    if use_appraisal.get("next_stage") == "appraisal":
        assert _stage(sa, c["id"], "appraisal", {"amount": 1, "note": "uji"}).status_code == 200


def test_plafon_check_preview(sa, kpr_contract):
    inv = _ar(sa, kpr_contract["deal_id"])
    bank = inv["bank_outstanding"]
    r = requests.get(f"{BASE}/contracts/{kpr_contract['id']}/kpr/plafon-check",
                     params={"plafon": bank - 10_000_000}, headers=sa)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["kind"] == "shortfall" and d["shortfall"] == 10_000_000 and d["requires_due_date"]
    d2 = requests.get(f"{BASE}/contracts/{kpr_contract['id']}/kpr/plafon-check",
                      params={"plafon": bank + 5_000_000}, headers=sa).json()["data"]
    assert d2["kind"] == "excess" and d2["excess"] == 5_000_000 and d2["excess_ok"]


def test_sp3k_shortfall_requires_due_date_then_creates_buyer_item(sa, kpr_contract):
    c = kpr_contract
    _to_sp3k_ready(sa, c)
    inv0 = _ar(sa, c["deal_id"])
    bank0, buyer0, total0 = inv0["bank_outstanding"], inv0["buyer_outstanding"], inv0["total"]
    plafon = bank0 - 55_000_000
    body = {"number": "SP3K/UJI/1", "plafon": plafon, "tenor_months": 120, "rate": 7.5,
            "file_id": "uji-file-sp3k", "valid_until": "2027-12-31"}
    r = _stage(sa, c["id"], "sp3k", body)
    assert r.status_code == 400 and "JATUH TEMPO" in r.text, r.text
    r = _stage(sa, c["id"], "sp3k", {**body, "shortfall_due_date": "2027-01-15"})
    assert r.status_code == 200, r.text
    app = r.json()["data"]
    assert app["approved_plafon"] == plafon
    rec = app["plafon_reconcile"]
    assert rec["applied"] and rec["kind"] == "shortfall" and rec["shortfall"] == 55_000_000
    inv = _ar(sa, c["deal_id"])
    assert inv["total"] == total0
    assert inv["bank_outstanding"] == plafon == bank0 - 55_000_000
    assert inv["buyer_outstanding"] == buyer0 + 55_000_000
    sf = [i for i in inv["items"] if i.get("kind") == "kpr_shortfall"]
    assert len(sf) == 1 and sf[0]["amount"] == 55_000_000 and sf[0]["payer"] == "buyer"
    assert sf[0]["due_date"].startswith("2027-01-15")
    assert inv["kpr_outstanding"] == plafon
    contract = _db.contracts.find_one({"id": c["id"]}, {"_id": 0, "costs": 1})
    assert contract["costs"]["plafon_kredit"] == plafon


def test_buyer_receipt_can_pay_shortfall_item(sa, kpr_contract):
    c = kpr_contract
    inv = _ar(sa, c["deal_id"])
    sf = next(i for i in inv["items"] if i.get("kind") == "kpr_shortfall")
    r = requests.post(f"{BASE}/finance/ar/receipts", headers=sa, json={
        "deal_id": c["deal_id"], "amount": 5_000_000, "method": "transfer",
        "note": "UJI-PLAFON setoran selisih", "allocations": [{"item_id": sf["id"], "amount": 5_000_000}]})
    assert r.status_code == 200, r.text
    inv2 = _ar(sa, c["deal_id"])
    sf2 = next(i for i in inv2["items"] if i.get("kind") == "kpr_shortfall")
    assert sf2["paid_amount"] == 5_000_000 and sf2["status"] == "partial"
    assert inv2["bank_outstanding"] == inv["bank_outstanding"]


def test_sp3k_excess_raises_bank_portion(sa, kpr_contract):
    c = kpr_contract
    # reset AR ke snapshot awal & pengajuan ke sebelum SP3K
    _db.receipts.delete_many({"deal_id": c["deal_id"], "note": {"$regex": "UJI-PLAFON"}})
    _db.ar_invoices.replace_one({"id": SNAP["inv"]["id"]}, copy.deepcopy(SNAP["inv"]))
    _to_sp3k_ready(sa, c)
    inv0 = _ar(sa, c["deal_id"])
    bank0, buyer0, total0 = inv0["bank_outstanding"], inv0["buyer_outstanding"], inv0["total"]
    plafon = bank0 + 20_000_000
    r = _stage(sa, c["id"], "sp3k", {"number": "SP3K/UJI/2", "plafon": plafon, "tenor_months": 120,
                                     "rate": 7.5, "file_id": "uji-file-sp3k-2"})
    assert r.status_code == 200, r.text
    rec = r.json()["data"]["plafon_reconcile"]
    assert rec["kind"] == "excess" and rec["applied"]
    inv = _ar(sa, c["deal_id"])
    assert inv["total"] == total0
    assert inv["bank_outstanding"] == plafon
    assert inv["buyer_outstanding"] == buyer0 - 20_000_000


def test_quotation_stores_allin_and_booking_fee(sa):
    opts = requests.get(f"{BASE}/quotations/options", headers=sa).json()["data"]
    units = opts.get("units") or []
    if not units:
        pytest.skip("tidak ada unit tersedia")
    lead = _db.leads.find_one({"stage": {"$nin": ["closed_won", "lost"]}}, {"_id": 0, "id": 1})
    schemes = requests.get(f"{BASE}/allin-schemes", headers=sa).json().get("data") or []
    body = {"unit_id": units[0]["id"], "lead_id": lead["id"], "booking_fee": 7_500_000,
            "allin_scheme_id": schemes[0]["id"] if schemes else None, "valid_days": 7}
    r = requests.post(f"{BASE}/quotations", headers=sa, json=body)
    assert r.status_code == 200, r.text
    q = r.json()["data"]
    try:
        assert q["booking_fee_gross"] == 7_500_000
        assert q.get("payment_breakdown")
        if schemes:
            assert q["allin_scheme_id"] == schemes[0]["id"]
            assert q["costs"]["components"]
            assert q["buyer_total"] == q["net_price"] + (q.get("addon_net_total") or 0) + q["costs"]["buyer_total"]
    finally:
        _db.quotations.delete_one({"id": q["id"]})
