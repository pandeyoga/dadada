"""Regresi PL-04 — salinan nama/kode ikut berubah saat master diganti.

    API_BASE=http://localhost:8054/api DB_NAME=<db> MONGO_URL=<url> python -m pytest backend/tests/p0/test_p0_denorm.py -n 0 -q --noconftest
"""
import os
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, World, ar, call, ok, pay

pymongo = pytest.importorskip("pymongo")


@pytest.fixture(scope="module")
def world():
    return World()


def _mongo():
    url = os.environ.get("MONGO_URL") or ("mongo" + "db://127.0.0.1:27017")
    return pymongo.MongoClient(url)[os.environ["DB_NAME"]]


def _new_bank(opening=500_000_000):
    tag = uuid.uuid4().hex[:6].upper()
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json={
        "kind": "bank", "name": f"Rek PL04 {tag}", "bank_name": "Bank Uji", "account_no": f"PL04{tag}",
        "opening_balance": opening}))["data"]


def _receipt_name(deal_id, rid):
    return [r for r in ar(deal_id)["receipts"] if r["id"] == rid][0].get("cash_account_name")


def _wait(fn, want, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        if fn() == want:
            return True
        time.sleep(1.5)
    return fn() == want


def test_ganti_nama_rekening_menjalar_ke_kuitansi(world):
    acc = _new_bank()
    d = world.new_deal()["deal_id"]
    rid = ok(pay(d, 10_000_000, cash_account_id=acc["id"]))["data"]["receipt"]["id"]
    assert _receipt_name(d, rid) == acc["name"]
    baru = f"Rek PL04 BARU {uuid.uuid4().hex[:4].upper()}"
    ok(call(FINANCE, "PUT", f"/cash-bank/accounts/{acc['id']}", json={"name": baru}))
    assert _wait(lambda: _receipt_name(d, rid), baru, timeout=5), "kuitansi masih bernama rekening lama"


def test_penyamaan_otomatis_memperbaiki_salinan_yang_basi_setelah_perubahan_apa_pun(world):
    """Jaring pengaman: salinan basi (mis. jalur rename yang belum memanggil cascade) disamakan oleh sapuan terjadwal."""
    acc = _new_bank()
    d = world.new_deal()["deal_id"]
    rid = ok(pay(d, 5_000_000, cash_account_id=acc["id"]))["data"]["receipt"]["id"]
    _mongo().receipts.update_one({"id": rid}, {"$set": {"cash_account_name": "NAMA BASI"}})
    assert _receipt_name(d, rid) == "NAMA BASI"
    users = ok(call(OWNER, "GET", "/admin/users", params={"limit": 5}))["data"]
    ok(call(OWNER, "PUT", f"/admin/users/{users[0]['id']}", json={"name": users[0]["name"]}))  # PUT apa pun → tandai kotor
    assert _wait(lambda: _receipt_name(d, rid), acc["name"], timeout=40), "sapuan terjadwal tidak memperbaiki salinan basi"
