"""Regresi P1-a — model kewajiban kontrak pasca-BAST & denda (audit GL-01, GL-02).

    API_BASE=http://localhost:8020/api python -m pytest backend/tests/p0/test_p0_gl_bast.py -n 0 -q --noconftest

Memakai helper tes uang masuk (World/pay/ar). Jurnal GL lahir dari event (dispatcher 8 dtk), jadi
tes menunggu jurnal muncul.
"""
import time

import pytest

from test_p0_masuk import FINANCE, OWNER, TAG, World, ar, call, ok, pay  # noqa: F401


@pytest.fixture(scope="module")
def world():
    return World()


def _journals(deal_id, source_type=None, want=1, timeout=25):
    end = time.time() + timeout
    rows = []
    while time.time() < end:
        params = {"source_id": deal_id, "limit": 100}
        if source_type:
            params["source_type"] = source_type
        rows = ok(call(FINANCE, "GET", "/gl/journals", params=params))["data"]
        if len(rows) >= want:
            return rows
        time.sleep(1)
    return rows


def _credits(entry):
    return {l["account_code"]: l["credit"] for l in entry["lines"] if l["credit"]}


def _receipt_id(resp):
    return (resp.get("data") or resp)["receipt"]["id"]


def test_gl01_penerimaan_pasca_bast_mengurangi_piutang_bukan_kewajiban_kontrak(world):
    d = world.new_deal()["deal_id"]
    pre = _receipt_id(ok(pay(d, 100_000_000)))
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/bast"))
    post = _receipt_id(ok(pay(d, 200_000_000)))
    rows = {e["source_id"]: e for e in _journals(d, "receipt", want=2)}
    assert set(rows) >= {pre, post}, "jurnal kedua penerimaan harus terbit"
    # sebelum BAST: uang muka penjualan (kewajiban kontrak)
    assert _credits(rows[pre]) == {"2-1400": 100_000_000}
    # sesudah BAST: pelunasan PIUTANG; kewajiban kontrak tidak boleh bertambah lagi
    assert _credits(rows[post]) == {"1-1300": 200_000_000}
    liab = ar(d).get("contract_liability") or {}
    assert int(liab.get("balance") or 0) == 0, "kewajiban kontrak pasca-BAST harus tetap nol"
    chk = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
    assert chk["ok"], [c for c in chk["checks"] if not c.get("ok")]


def test_gl02_denda_tidak_terhitung_dua_kali_sebagai_pendapatan(world):
    sname = f"P0 GL02 {TAG}"
    r = call(OWNER, "POST", "/payment-schemes", json={
        "name": sname, "kind": "cash_bertahap", "code": f"p0-gl2-{TAG.lower()}", "active": True,
        "terms": [{"label": "Termin lampau", "basis": "percent", "value": 100, "due_offset_days": -90}]})
    world.scheme[sname] = ok(r)["data"]["id"]
    d = world.new_deal(scheme=sname)["deal_id"]
    fee = ok(call(OWNER, "POST", f"/finance/late-fees/{d}/apply", json={}))["created"][0]["amount"]
    inv = ar(d)["data"]
    unit_price = int(inv["unit_total"])
    assert int(inv["outstanding"]) == unit_price + fee
    rid = _receipt_id(ok(pay(d, int(inv["outstanding"]))))
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/bast"))
    rows = {e["source_id"]: e for e in _journals(d, "receipt", want=1)}
    # pelunasan denda mengkredit PIUTANG denda (1-1300), bukan kewajiban kontrak
    assert _credits(rows[rid]) == {"2-1400": unit_price, "1-1300": fee}
    # pendapatan unit saat BAST = harga unit saja (denda sudah pendapatan 4-1400 saat ditagihkan)
    rev = ar(d)["revenue_recognition"]
    assert int(rev["revenue"]) == unit_price
    chk = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
    assert chk["ok"], [c for c in chk["checks"] if not c.get("ok")]
