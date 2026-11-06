"""Regresi F3 — saldo kas/bank tidak boleh jebol lewat jalur persetujuan & balapan (audit PL-01, PL-02, PL-03).

    API_BASE=http://localhost:8054/api python -m pytest backend/tests/p0/test_p0_dana_kas.py -n 0 -q --noconftest

Tiap tes memakai rekening bank BARU (saldo awal Rp 10 jt) sehingga tidak bergantung pada saldo bersama.
"""
import uuid

import pytest

from test_p0_masuk import FINANCE, race, call, ok

FINLEAD = "finlead@sipro.co.id"
PM = "pm@sipro.co.id"


def _uniq(p):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


def new_bank(opening=10_000_000):
    body = {"kind": "bank", "name": f"Rek F3 {_uniq('R')}", "bank_name": "Bank Uji",
            "account_no": _uniq("NO"), "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def balance(acc_id):
    rows = ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"]
    return int([a for a in rows if a["id"] == acc_id][0]["balance"])


def new_transfer(src, dst, amount):
    r = call(FINANCE, "POST", "/cash-bank/transfers", json={
        "kind": "transfer", "from_account_id": src["id"], "to_account_id": dst["id"],
        "amount": amount, "fee": 0, "reference": _uniq("F3")})
    return ok(r)["data"]["id"]


def get_transfer(tid):
    rows = ok(call(FINANCE, "GET", "/cash-bank/transfers", params={"limit": 200}))["data"]
    return [t for t in rows if t["id"] == tid][0]


def approve(tid):
    return call(FINLEAD, "POST", f"/cash-bank/transfers/{tid}/approve")


def reject(tid):
    return call(FINLEAD, "POST", f"/cash-bank/transfers/{tid}/reject", json={"reason": "uji tolak bersamaan F3"})


# ------------------------------------------------------------------ PL-01
def test_transfer_dicek_dana_saat_disetujui_bukan_hanya_saat_dibuat():
    src, dst = new_bank(10_000_000), new_bank(0)
    ids = [new_transfer(src, dst, 6_000_000) for _ in range(3)]  # tiap-tiap lolos saat dibuat
    res = [approve(t) for t in ids]
    assert [r.status_code for r in res].count(200) == 1, [(r.status_code, r.text[:100]) for r in res]
    assert all(r.status_code in (200, 400) for r in res)
    assert balance(src["id"]) == 4_000_000, "saldo asal tidak boleh minus"
    assert balance(dst["id"]) == 6_000_000


def test_transfer_disetujui_paralel_hanya_yang_dananya_cukup():
    src, dst = new_bank(10_000_000), new_bank(0)
    ids = [new_transfer(src, dst, 6_000_000) for _ in range(3)]
    rs = race([lambda t=t: approve(t) for t in ids])
    assert sorted(r.status_code for r in rs).count(200) == 1, [(r.status_code, r.text[:100]) for r in rs]
    assert balance(src["id"]) == 4_000_000


# ------------------------------------------------------------------ PL-02
@pytest.mark.parametrize("ronde", range(4))
def test_setuju_dan_tolak_bersamaan_tepat_satu_menang(ronde):
    src, dst = new_bank(10_000_000), new_bank(0)
    tid = new_transfer(src, dst, 1_000_000)
    a, r = race([lambda: approve(tid), lambda: reject(tid)])
    assert sorted([a.status_code, r.status_code]) in ([200, 400], [200, 409]), (a.status_code, a.text[:80], r.status_code, r.text[:80])
    t = get_transfer(tid)
    if a.status_code == 200:
        assert t["status"] == "posted" and t.get("journal_no") and not t.get("reject_reason")
        assert balance(src["id"]) == 9_000_000
    else:
        assert t["status"] == "rejected" and not t.get("journal_no")
        assert balance(src["id"]) == 10_000_000


def test_setuju_dua_kali_tidak_menjurnal_ganda():
    src, dst = new_bank(10_000_000), new_bank(0)
    tid = new_transfer(src, dst, 2_000_000)
    rs = race([lambda: approve(tid), lambda: approve(tid)])
    assert [r.status_code for r in rs].count(200) == 1, [(r.status_code, r.text[:80]) for r in rs]
    assert balance(src["id"]) == 8_000_000


# ------------------------------------------------------------------ PL-03 (kas bon dari rekening yang sama)
def _advance(amount):
    r = call(PM, "POST", "/petty-cash/advances", json={"purpose": _uniq("F3 kas bon"), "amount": amount,
                                                     "category": "transport"})
    aid = ok(r)["data"]["id"]
    ok(call(FINANCE, "POST", f"/petty-cash/advances/{aid}/approve", json={}))
    return aid


def test_dua_kas_bon_berbeda_dari_rekening_sama_tidak_menjebol_saldo():
    acc = new_bank(10_000_000)
    ids = [_advance(6_000_000), _advance(6_000_000)]
    rs = race([lambda a=a: call(FINANCE, "POST", f"/petty-cash/advances/{a}/disburse",
                                json={"source": "bank", "cash_account_id": acc["id"]}) for a in ids])
    oks = [r for r in rs if r.status_code == 200]
    assert len(oks) == 1, [(r.status_code, r.text[:100]) for r in rs]
    assert balance(acc["id"]) == 4_000_000, "saldo tidak boleh minus"
