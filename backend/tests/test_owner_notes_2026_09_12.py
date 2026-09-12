"""Sesi 2026-09-12 — 5 catatan owner (backend).

1. Harga unit per skema (units.scheme_prices → quotation simulate & contract breakdown)
2. Override gerbang akad (kelebihan tanah belum lunas) dengan alasan manajer + setting off → warning
3. Bukti bayar pada kuitansi (proof_file_ids: buat, PATCH lampirkan, laporan receipts)
4. Add-on terpisah: item AR basis addon punya addon_code (dipakai kotak Add-on UI)
5. Daftar customer: kolom/filter tahap legal + legal_counts; deals.akad_at; KPR summary akad_done
"""
import asyncio
import io
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


def _set(sa, key, value):
    r = requests.put(f"{BASE}/settings/{key}", json={"value": value, "reason": "uji owner notes"}, headers=sa)
    assert r.status_code == 200, r.text


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PW}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin@sipro.co.id")


@pytest.fixture(scope="module")
def mgr():
    return _login("manager@sipro.co.id")


@pytest.fixture(scope="module")
def kpr_contract(sa):
    """Kontrak KPR demo: paksa SP3K lengkap + add-on kelebihan tanah belum lunas → gerbang akad
    hanya tertahan 'kelebihan_tanah_belum_lunas' (overridable)."""
    r = requests.get(f"{BASE}/contracts", params={"scheme": "kpr", "limit": 5}, headers=sa)
    rows = r.json()["data"]
    assert rows, "tidak ada kontrak KPR demo"
    c = rows[0]
    org = c["org_id"]
    # idempoten: cabut akad hasil run sebelumnya
    _db.contracts.update_one({"id": c["id"]}, {"$unset": {"legal.akad_kredit": ""}, "$set": {"legal_stage": "belum"}})
    _db.deals.update_one({"id": c["deal_id"]}, {"$unset": {"akad_at": ""}})
    _db.financing_apps.update_one(
        {"org_id": org, "deal_id": c["deal_id"]},
        {"$set": {"approved_plafon": 500_000_000, "sp3k": {"file_id": "test-sp3k", "plafon": 500_000_000}}},
        upsert=True)
    _db.deals.update_one({"id": c["deal_id"]}, {"$set": {"addons": [
        {"code": "KT", "name": "Kelebihan tanah 10 m2", "category": "kelebihan_tanah",
         "amount": 50_000_000, "qty": 10, "uom": "m2", "unit_price": 5_000_000,
         "finance_treatment": "revenue"}]}})
    _set(sa, "addon.require_spkt_for_excess_land", False)
    _db.ar_invoices.update_one({"org_id": org, "deal_id": c["deal_id"]}, {"$set": {"paid": 0}})
    return c


def _gate(sa, cid):
    d = requests.get(f"{BASE}/contracts/{cid}", headers=sa).json()["data"]
    return d["gates"]["akad_kredit"], d


# ------------------------------------------------------------------ 2. override akad
def test_akad_gate_overridable_and_setting(sa, kpr_contract):
    _set(sa, "addon.excess_land_must_be_paid_before_akad", True)
    g, _ = _gate(sa, kpr_contract["id"])
    codes = [b["code"] for b in g["blocks"]]
    assert "kelebihan_tanah_belum_lunas" in codes, g
    assert g["ok"] is False and g["overridable"] is True, g
    # setting dimatikan → hanya peringatan
    _set(sa, "addon.excess_land_must_be_paid_before_akad", False)
    g2, _ = _gate(sa, kpr_contract["id"])
    assert g2["ok"] is True and [w["code"] for w in g2["warnings"]] == ["kelebihan_tanah_belum_lunas"], g2
    _set(sa, "addon.excess_land_must_be_paid_before_akad", True)


def test_akad_override_requires_reason_then_records(mgr, sa, kpr_contract):
    cid = kpr_contract["id"]
    r = requests.post(f"{BASE}/contracts/{cid}/legal/akad_kredit", json={}, headers=mgr)
    assert r.status_code == 400 and "PENGECUALIAN" in r.text, r.text
    r = requests.post(f"{BASE}/contracts/{cid}/legal/akad_kredit", json={"override_reason": "ok"}, headers=mgr)
    assert r.status_code == 400, r.text
    r = requests.post(f"{BASE}/contracts/{cid}/legal/akad_kredit",
                      json={"override_reason": "Bank sudah jadwalkan akad, KT dibayar dari tahap 1"}, headers=mgr)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    ent = d["legal"]["akad_kredit"]
    assert ent["override"]["reason"].startswith("Bank sudah") and ent["override"]["blocks"] == ["kelebihan_tanah_belum_lunas"]
    assert d["legal_stage"] == "akad_kredit"
    deal = _db.deals.find_one({"id": kpr_contract["deal_id"]}, {"_id": 0, "akad_at": 1, "legal_stage": 1})
    assert deal["akad_at"] == ent["date"]
    assert deal.get("legal_stage") != "akad_kredit"  # cermin deals tetap ppjb/ajb saja


# ------------------------------------------------------------------ 5. sudah akad
def test_customers_legal_column_filter_counts(sa, kpr_contract):
    r = requests.get(f"{BASE}/customers", params={"legal_stage": "akad_kredit"}, headers=sa)
    assert r.status_code == 200
    d = r.json()
    ids = [c["id"] for c in d["data"]]
    assert kpr_contract["customer_id"] in ids, d
    row = next(c for c in d["data"] if c["id"] == kpr_contract["customer_id"])
    assert row["legal"]["stage"] == "akad_kredit" and row["legal"]["akad_date"] and row["legal"]["akad_override"] is True
    assert d["legal_counts"]["akad_done"] >= 1
    r2 = requests.get(f"{BASE}/customers", params={"legal_stage": "belum"}, headers=sa).json()
    assert kpr_contract["customer_id"] not in [c["id"] for c in r2["data"]]
    s = requests.get(f"{BASE}/kpr/disbursement-summary", headers=sa).json()["data"]["totals"]
    assert s["akad_done"] >= 1 and "akad_pending" in s


# ------------------------------------------------------------------ 3. bukti bayar
def _upload(sa):
    files = {"file": ("bukti.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), "image/png")}
    r = requests.post(f"{BASE}/files/upload", files=files, data={"owner_type": "receipt_proof", "optimize": "false"}, headers=sa)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_receipt_with_proof_and_attach_later(sa, kpr_contract):
    fid = _upload(sa)
    deal_id = kpr_contract["deal_id"]
    inv = requests.get(f"{BASE}/finance/ar/{deal_id}", headers=sa).json()["data"]
    open_items = [i for i in inv["items"] if int(i["amount"]) > int(i.get("paid_amount") or 0)]
    assert open_items
    it = open_items[0]
    r = requests.post(f"{BASE}/finance/ar/receipts", headers=sa, json={
        "deal_id": deal_id, "amount": 1000, "method": "transfer", "proof_file_ids": [fid],
        "allocations": [{"item_id": it["id"], "amount": 1000}]})
    assert r.status_code == 200, r.text
    rc = r.json()["data"]["receipt"]
    assert rc["proof_file_ids"] == [fid]
    fid2 = _upload(sa)
    r = requests.patch(f"{BASE}/finance/ar/receipts/{rc['id']}/proof", json={"proof_file_ids": [fid2]}, headers=sa)
    assert r.status_code == 200, r.text
    assert set(r.json()["data"]["proof_file_ids"]) == {fid, fid2}
    r = requests.patch(f"{BASE}/finance/ar/receipts/{rc['id']}/proof", json={"proof_file_ids": ["nope"]}, headers=sa)
    assert r.status_code == 400
    rep = requests.get(f"{BASE}/finance/reports/receipts", headers=sa).json()["data"]
    row = next(x for x in rep["rows"] if x["id"] == rc["id"])
    assert row["has_proof"] and len(row["proof_file_ids"]) == 2
    assert rep["totals"]["with_proof"] >= 1
    assert requests.get(f"{BASE}/finance/reports/receipts/pdf", headers=sa).status_code == 200
    pdf = requests.get(f"{BASE}/finance/ar/receipts/{rc['id']}/pdf", headers=sa)
    assert pdf.status_code == 200


# ------------------------------------------------------------------ 4. add-on terpisah
def test_addon_items_flagged(sa):
    inv = _db.ar_invoices.find_one({"items.basis": "addon"}, {"_id": 0, "items": 1})
    if not inv:
        pytest.skip("tidak ada AR dengan add-on di seed")
    add = [i for i in inv["items"] if i.get("basis") == "addon"]
    assert all(i.get("kpr_excluded") and i.get("addon_code") for i in add)


# ------------------------------------------------------------------ 1. harga per skema
def test_unit_scheme_prices_flow(sa):
    u = _db.units.find_one({"status": "available", "price": {"$gt": 0}}, {"_id": 0})
    assert u, "tidak ada unit available"
    base = int(u["price"])
    r = requests.patch(f"{BASE}/masterplan/units/{u['id']}", headers=sa,
                       json={"scheme_prices": {"kpr": base + 25_000_000, "cash_keras": base - 10_000_000, "cash_bertahap": 0}})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["scheme_prices"] == {"kpr": base + 25_000_000, "cash_keras": base - 10_000_000}
    r = requests.patch(f"{BASE}/masterplan/units/{u['id']}", headers=sa, json={"scheme_prices": {"xx": 1}})
    assert r.status_code == 400
    schemes = _db.payment_schemes.find({"org_id": u["org_id"]}, {"_id": 0, "id": 1, "kind": 1, "type": 1})
    by_kind = {}
    for s in schemes:
        by_kind.setdefault(s.get("kind") or s.get("type"), s["id"])
    assert "kpr" in by_kind and "cash_keras" in by_kind, by_kind
    sim_kpr = requests.post(f"{BASE}/quotations/simulate", headers=sa,
                            json={"unit_id": u["id"], "scheme_id": by_kind["kpr"]})
    assert sim_kpr.status_code == 200, sim_kpr.text
    ck = sim_kpr.json()["data"]
    assert ck["base_price"] == base + 25_000_000 and ck["price_source"] == "skema"
    sim_ck = requests.post(f"{BASE}/quotations/simulate", headers=sa,
                           json={"unit_id": u["id"], "scheme_id": by_kind["cash_keras"]}).json()["data"]
    assert sim_ck["base_price"] == base - 10_000_000
    if "cash_bertahap" in by_kind:
        sim_cb = requests.post(f"{BASE}/quotations/simulate", headers=sa,
                               json={"unit_id": u["id"], "scheme_id": by_kind["cash_bertahap"]}).json()["data"]
        assert sim_cb["base_price"] == base and sim_cb["price_source"] == "dasar"
    row = next(x for x in ck["breakdown"]["rows"] if x["code"] == "UNIT_PRICE") if "breakdown" in ck else None
    if row:
        assert "harga skema" in (row.get("hint") or "")
    # bersihkan
    requests.patch(f"{BASE}/masterplan/units/{u['id']}", headers=sa, json={"scheme_prices": {}})
