"""Regresi GELOMBANG 2 akuntansi/keuangan (audit GL-08, GL-09, PK-09, GL-15, GL-16/PK-21, GL-17, GL-21,
IN-20, IN-21, IN-16/17, GL-13, GL-14).

    API_BASE=http://localhost:8032/api python -m pytest backend/tests/p0/test_p0_akuntansi2.py -n 0 -q --noconftest

Memakai helper tes uang masuk (World/pay/ar/call/ok). Tiap tes membuat DATA SENDIRI. Jurnal GL lahir dari
event (dispatcher 8 dtk / dipanggil langsung oleh endpoint), jadi tes menunggu jurnal muncul.
"""
import time
import uuid

import pytest

from test_p0_masuk import (FINANCE, OWNER, SUPER, TAG, World, ar, call, cl_balance, ok, pay,  # noqa: F401
                           race, upload_proof)

FINLEAD = "finlead@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


def _uniq(prefix="UJI"):
    return f"{prefix}-{TAG}-{uuid.uuid4().hex[:6].upper()}"


def _wait(fn, timeout=25, step=1.0):
    """Ulangi `fn()` sampai truthy (jurnal lahir dari event)."""
    end = time.time() + timeout
    val = fn()
    while not val and time.time() < end:
        time.sleep(step)
        val = fn()
    return val


def _journals(**params):
    params.setdefault("limit", 100)
    return ok(call(FINANCE, "GET", "/gl/journals", params=params))["data"]


def _tb(email=FINANCE):
    """{kode_akun: debit − kredit} dari neraca saldo."""
    rows = ok(call(email, "GET", "/gl/trial-balance"))["data"]["rows"]
    return {r["code"]: int(r["debit"]) - int(r["credit"]) for r in rows}


def _bal(code, email=FINANCE):
    """Saldo (debit − kredit) satu akun dari neraca saldo."""
    return _tb(email).get(code, 0)


# ================================================================== GL-08 — rekening bank & akun GL
def _bank_body(**over):
    body = {"name": f"Rek Uji {_uniq('R')}", "bank_name": "Bank Uji", "account_no": _uniq("NO").replace("-", ""),
            "gl_account_code": "1-1200", "opening_balance": 0}
    body.update(over)
    return body


def test_gl08_akun_non_kas_ditolak_sebagai_rekening_bank():
    for code in ("1-1300", "1-1600", "1-1400", "1-1100", "2-1100", "TIDAK-ADA"):
        r = call(FINANCE, "POST", "/bank/accounts", json=_bank_body(gl_account_code=code))
        assert r.status_code == 400, f"{code}: {r.status_code} {r.text[:200]}"


def test_gl08_akun_kembar_ditolak_dan_induk_membuat_subakun_baru():
    a = ok(call(FINANCE, "POST", "/bank/accounts", json=_bank_body()))["data"]
    assert a["gl_account_code"] not in ("1-1200", "1-1100"), "induk tidak boleh jadi akun rekening"
    r = call(FINANCE, "POST", "/bank/accounts", json=_bank_body(gl_account_code=a["gl_account_code"]))
    assert r.status_code == 400 and "sudah dipakai" in r.text, r.text[:200]
    # sub-akun rekening yang sudah dipakai tidak ditawarkan lagi di dropdown
    codes = [o["code"] for o in ok(call(FINANCE, "GET", "/bank/accounts/gl-options"))["data"]]
    assert a["gl_account_code"] not in codes
    assert "1-1200" in codes and "1-1300" not in codes and "1-1600" not in codes


def test_gl08_pindah_akun_gl_lewat_put_ditolak():
    a = ok(call(FINANCE, "POST", "/bank/accounts", json=_bank_body()))["data"]
    for target in ("1-1300", "1-1201"):
        body = _bank_body(name=a["name"], account_no=a["account_no"], gl_account_code=target)
        r = call(FINANCE, "PUT", f"/bank/accounts/{a['id']}", json=body)
        assert r.status_code == 400, f"{target}: {r.status_code} {r.text[:160]}"
    # ubah data biasa tetap jalan, akun GL tidak berubah
    body = _bank_body(name=a["name"] + " X", account_no=a["account_no"], gl_account_code=a["gl_account_code"])
    d = ok(call(FINANCE, "PUT", f"/bank/accounts/{a['id']}", json=body))["data"]
    assert d["gl_account_code"] == a["gl_account_code"] and d["name"].endswith(" X")


def test_gl08_saldo_kas_posisi_sama_dengan_neraca():
    ok(call(FINANCE, "POST", "/bank/accounts", json=_bank_body()))
    pos = ok(call(FINANCE, "GET", "/cash-bank/position"))["data"]
    tb = _tb()
    gl_total = sum(tb.get(r["gl_account_code"], 0) for r in pos["accounts"] if r["is_active"])
    assert pos["total"] == gl_total
