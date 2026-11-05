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


# ================================================================== GL-09 — event pembukuan gagal
def test_gl09_logika_percobaan_ulang_berjeda_lalu_gagal_permanen():
    """Murni (tanpa server): gagal → dijadwalkan ulang berjeda; setelah MAX_ATTEMPTS → failed permanen."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import event_retry as er
    first = er.failure_set({"retries": 0}, "Akun 2-1200 NONAKTIF")
    assert first["status"] == "pending" and first["next_retry_at"], "percobaan pertama gagal -> jadwal ulang"
    due = er.due_filter("2000-01-01T00:00:00+00:00")["$or"]
    assert {"next_retry_at": None} in due and {"next_retry_at": {"$lte": "2000-01-01T00:00:00+00:00"}} in due
    last = er.failure_set({"retries": er.MAX_ATTEMPTS - 1}, "x" * 900)
    assert last["status"] == "failed" and last["next_retry_at"] is None and len(last["last_error"]) == 500
    mid = [er.failure_set({"retries": n}, "x")["status"] for n in range(er.MAX_ATTEMPTS - 1)]
    assert set(mid) == {"pending"}


def test_gl09_health_dan_tieout_menampilkan_event_gagal():
    import requests
    from test_p0_masuk import API
    h = requests.get(f"{API}/health", timeout=30).json()
    assert "events_failed" in h and "events_retrying" in h, h
    rc = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
    assert {"events_failed", "events_retrying", "failed_events", "can_retry_events"} <= set(rc), sorted(rc)
    assert rc["can_retry_events"] is True


def test_gl09_proses_ulang_butuh_izin_dan_event_yang_ada():
    assert call("sales@sipro.co.id", "POST", "/finance/events/apa-saja/retry").status_code == 403
    assert call("sales@sipro.co.id", "POST", "/finance/events/retry-failed").status_code == 403
    r = call(FINLEAD, "POST", "/finance/events/tidak-ada-event/retry")
    assert r.status_code == 400 and "tidak ditemukan" in r.text, r.text[:200]
    lst = ok(call(FINANCE, "GET", "/finance/events/failed", params={"status": "all"}))
    assert isinstance(lst["data"], list)
    done = ok(call(FINLEAD, "POST", "/finance/events/retry-failed"))
    assert done["total"] == len(done["data"]) and "still_failed" in done


# ================================================================== GL-13 — CoA mengikat posting
def _new_code(prefix="6"):
    """Kode akun unik 4 digit (tes bisa diulang di database yang sama)."""
    import random
    existing = {a["code"] for a in ok(call(FINANCE, "GET", "/gl/accounts"))["data"]}
    for _ in range(60):
        code = f"{prefix}-{random.randint(2000, 9999)}"
        if code not in existing:
            return code
    raise AssertionError("tidak menemukan kode akun kosong")


def test_gl13_kode_akun_baru_divalidasi():
    bad = [("ABC", "expense", None), ("2-1400 ", "liability", None), (" 6-1999", "expense", None),
           ("4-9998", "asset", None), ("6-19", "expense", None), ("1-1299", "asset", "1-1200"),
           ("1-1199", "asset", "1-1100")]
    for code, typ, parent in bad:
        r = call(FINANCE, "POST", "/gl/accounts", json={"code": code, "name": "Uji " + TAG, "type": typ,
                                                         "parent_code": parent})
        assert r.status_code == 400, f"{code!r}: {r.status_code} {r.text[:160]}"
    code = _new_code("6")
    d = ok(call(FINANCE, "POST", "/gl/accounts", json={"code": code, "name": "Beban Uji " + TAG, "type": "expense"}))
    assert d["data"]["code"] == code


def test_gl13_akun_nonaktif_tidak_menerima_posting_dan_akun_sistem_terkunci():
    code = _new_code("6")
    ok(call(FINANCE, "POST", "/gl/accounts", json={"code": code, "name": "Beban Uji " + TAG, "type": "expense"}))
    lines = [{"account_code": code, "debit": 1000, "credit": 0}, {"account_code": "4-1200", "debit": 0, "credit": 1000}]
    ok(call(FINANCE, "POST", "/gl/journals", json={"memo": "Uji akun aktif " + TAG, "lines": lines}))
    ok(call(FINANCE, "PUT", f"/gl/accounts/{code}", json={"is_active": False}))
    r = call(FINANCE, "POST", "/gl/journals", json={"memo": "Uji akun nonaktif " + TAG, "lines": lines})
    assert r.status_code == 400 and "NONAKTIF" in r.text, r.text[:200]
    # akun yang dipakai jurnal otomatis tidak boleh dimatikan (dulu penerimaan baru tetap memposting ke sana)
    r = call(FINANCE, "PUT", "/gl/accounts/2-1400", json={"is_active": False})
    assert r.status_code == 400, r.text[:200]
    r = call(FINANCE, "PUT", "/gl/accounts/1-1300", json={"type": "revenue"})
    assert r.status_code == 400, r.text[:200]
    # sub-akun kas milik rekening aktif tidak boleh dimatikan dari Bagan Akun
    a = ok(call(FINANCE, "POST", "/bank/accounts", json=_bank_body()))["data"]
    r = call(FINANCE, "PUT", f"/gl/accounts/{a['gl_account_code']}", json={"is_active": False})
    assert r.status_code == 400 and "rekening" in r.text, r.text[:200]


# ================================================================== PK-09 — batalkan pembayaran AP
def _bill(claimed=10_000_000, retention=0):
    b = ok(call(FINANCE, "POST", "/finance/ap/bills", json={
        "vendor": f"Vendor Uji {_uniq('V')}", "claimed": claimed, "retention_pct": retention}))["data"]
    ok(call(OWNER, "POST", f"/finance/ap/bills/{b['id']}/approve"))
    return b


def _pay_bill(bill_id, amount, **extra):
    return call(FINANCE, "POST", f"/finance/ap/bills/{bill_id}/pay", json={"amount": amount, **extra})


def _detail(bill_id):
    return ok(call(FINANCE, "GET", f"/finance/ap/bills/{bill_id}"))["data"]


def _void_pay(email, pid, reason="uji pembatalan pembayaran vendor"):
    return call(email, "POST", f"/finance/ap/payments/{pid}/void", json={"reason": reason})


def _paid_journal_ready(bill_id):
    return _wait(lambda: any(j["source_type"] == "ap_bill" and "Pembayaran" in j["memo"]
                             for j in _detail(bill_id)["journals"]))


def test_pk09_batal_bayar_ap_membalik_jurnal_dan_subledger():
    b = _bill(10_000_000)
    ok(_pay_bill(b["id"], 10_000_000))
    d = _detail(b["id"])
    pid = d["payments"][0]["id"]
    cash_code = d["payments"][0]["cash_account_code"]
    assert d["bill"]["status"] == "paid"
    assert _paid_journal_ready(b["id"])
    before = _tb()
    res = ok(_void_pay(FINLEAD, pid))["data"]
    assert res["reversed"] == 10_000_000 and res["bill"]["status"] == "approved"
    d2 = _detail(b["id"])
    assert d2["bill"]["paid"] == 0 and d2["bill"]["outstanding"] == 10_000_000 and d2["bill"]["status"] == "approved"
    assert d2["payments"][0]["status"] == "void", "pembayaran tetap ada sebagai jejak"
    assert d2["summary"]["paid"] == 0 and d2["summary"]["paid_consistent"]
    after = _tb()
    assert after.get("2-1100", 0) - before.get("2-1100", 0) == -10_000_000   # utang usaha kembali (kredit +10 jt)
    assert after.get(cash_code, 0) - before.get(cash_code, 0) == 10_000_000   # kas kembali
    assert any(j["source_type"] == "ap_payment_void" for j in d2["journals"])
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]
    # tagihan bisa dibayar lagi (nominal berbeda dari yang pertama supaya lolos kunci klik-ganda 15 dtk)
    ok(_pay_bill(b["id"], 4_000_000))
    ok(_pay_bill(b["id"], 6_000_000))
    assert _detail(b["id"])["bill"]["status"] == "paid"


def test_pk09_batal_bayar_ap_aturan_izin_alasan_dan_ganda():
    b = _bill(8_000_000)
    ok(_pay_bill(b["id"], 8_000_000))
    pid = _detail(b["id"])["payments"][0]["id"]
    assert _paid_journal_ready(b["id"])
    r = _void_pay(FINANCE, pid)                                   # pembayar sendiri
    assert r.status_code == 400 and "Pemisahan tugas" in r.text, r.text[:200]
    assert _void_pay(FINLEAD, pid, reason="pendek").status_code in (400, 422)
    assert call("sales@sipro.co.id", "POST", f"/finance/ap/payments/{pid}/void",
                json={"reason": "uji pembatalan tanpa izin"}).status_code == 403
    rs = race([lambda: _void_pay(FINLEAD, pid) for _ in range(3)])
    assert sorted(r.status_code for r in rs).count(200) == 1, [(r.status_code, r.text[:100]) for r in rs]
    assert _void_pay(FINLEAD, pid).status_code == 400            # sudah dibatalkan
    d = _detail(b["id"])
    assert d["summary"]["paid_recorded"] == 0
    assert len([j for j in d["journals"] if j["source_type"] == "ap_payment_void"]) == 1, "hanya satu jurnal pembalik"
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]


def test_pk09_batal_bayar_dengan_pph_membatalkan_bukti_potong():
    b = _bill(10_000_000)
    ok(call(FINANCE, "POST", f"/finance/ap/bills/{b['id']}/pay-withholding",
            json={"bill_id": b["id"], "amount": 4_000_000, "kind": "pph23", "rate": 2}))
    d = _detail(b["id"])
    pid = d["payments"][0]["id"]
    assert len(d["withholding"]) == 1 and d["withholding"][0]["state"] != "cancelled"
    assert _paid_journal_ready(b["id"])
    before = _tb()
    res = ok(_void_pay(FINLEAD, pid))["data"]
    assert res["withheld_reversed"] == 80_000
    d2 = _detail(b["id"])
    assert d2["withholding"][0]["state"] == "cancelled"
    after = _tb()
    assert after.get("2-1300", 0) - before.get("2-1300", 0) == 80_000   # utang pajak (kredit) turun 80 rb
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]


# ================================================================== PK-09 — status pajak tak boleh mundur
def test_pk09_status_pajak_tidak_bisa_dimundurkan():
    recs = ok(call(FINANCE, "GET", "/tax/records", params={"limit": 200}))["data"]
    rec = next((r for r in recs if r["status"] == "pending" and int(r.get("amount") or 0) > 0), None)
    if not rec:
        pytest.skip("tidak ada catatan pajak berstatus pending untuk diuji")
    ok(call(FINANCE, "PUT", f"/tax/records/{rec['id']}", json={"status": "reported"}))
    r = call(FINANCE, "PUT", f"/tax/records/{rec['id']}", json={"status": "pending"})
    assert r.status_code == 400 and "dimundurkan" in r.text, r.text[:200]
    cur = [x for x in ok(call(FINANCE, "GET", "/tax/records", params={"limit": 200}))["data"] if x["id"] == rec["id"]][0]
    assert cur["status"] == "reported"
