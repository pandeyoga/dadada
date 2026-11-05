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


# ================================================================== GL-15 — tanggal & periode
def _wib_now():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=7)))


def _days_ago(n):
    from datetime import timedelta
    return (_wib_now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _period_info():
    """(bulan_lalu, bulan_berjalan, tanggal_terakhir_bulan_lalu, bulan_depan) menurut WIB."""
    from datetime import timedelta
    now = _wib_now()
    first = now.replace(day=1)
    prev_last = first - timedelta(days=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return (prev_last.strftime("%Y-%m"), now.strftime("%Y-%m"), prev_last.strftime("%Y-%m-%d"),
            nxt.strftime("%Y-%m"))


def _manual_journal(date):
    return call(FINANCE, "POST", "/gl/journals", json={
        "memo": "Uji GL-15 " + TAG, "date": date,
        "lines": [{"account_code": "6-1300", "debit": 1000, "credit": 0},
                  {"account_code": "4-1200", "debit": 0, "credit": 1000}]})


def _pl_expense(date_from, date_to):
    d = ok(call(FINANCE, "GET", "/gl/reports/income-statement", params={"date_from": date_from, "date_to": date_to}))
    return int(d["data"]["total_expense"])


def test_gl15_tanggal_bayar_nyata_kuitansi_dan_pembayaran_ap(world):
    day = _days_ago(3)
    d = world.new_deal()["deal_id"]
    rid = ok(pay(d, 10_000_000, value_date=day))["data"]["receipt"]["id"]
    assert ok(call(FINANCE, "GET", f"/finance/ar/{d}"))["receipts"][0]["value_date"] == day
    je = _wait(lambda: [j for j in _journals(source_type="receipt", source_id=rid) if j["source_id"] == rid])
    assert je and je[0]["date"].startswith(day), je and je[0]["date"]
    # pembayaran AP
    b = _bill(6_000_000)
    ok(_pay_bill(b["id"], 6_000_000, value_date=day))
    pj = [j for j in _detail(b["id"])["journals"] if j["source_type"] == "ap_bill" and "Pembayaran" in j["memo"]]
    assert pj and pj[0]["date"].startswith(day)
    # tanpa value_date = sekarang (perilaku lama)
    b2 = _bill(1_000_000)
    ok(_pay_bill(b2["id"], 1_000_000))
    pj2 = [j for j in _detail(b2["id"])["journals"] if j["source_type"] == "ap_bill" and "Pembayaran" in j["memo"]]
    assert pj2 and pj2[0]["date"][:10] in (_days_ago(0), _days_ago(1))
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]


def test_gl15_tanggal_bayar_ditolak_bila_masa_depan_atau_rusak(world):
    d = world.new_deal()["deal_id"]
    for bad in ("2099-01-01", "bukan-tanggal", _days_ago(-3)):
        r = pay(d, 1_000_000, value_date=bad)
        assert r.status_code == 400 and "anggal bayar" in r.text, (bad, r.status_code, r.text[:160])
    assert len(ar(d)["receipts"]) == 0, "tidak ada kuitansi yang lahir dari permintaan ditolak"
    b = _bill(2_000_000)
    r = _pay_bill(b["id"], 2_000_000, value_date="2099-01-01")
    assert r.status_code == 400 and _detail(b["id"])["bill"]["paid"] == 0


def test_gl15_batas_zona_waktu_periode_tertutup_dan_tak_menutup_masa_depan(world):
    prev, cur, last_day, nxt = _period_info()
    r = call(SUPER, "POST", "/gl/periods/close", json={"period": prev, "override": True,
                                                         "override_reason": "uji GL-15 batas zona waktu"})
    if r.status_code != 200 and "sudah ditutup" not in r.text:
        pytest.skip(f"tidak bisa menutup {prev} untuk uji: {r.text[:120]}")
    try:
        before = _pl_expense(f"{prev}-01", last_day)
        # 20:00 UTC hari terakhir = 03:00 WIB tanggal 1 bulan berjalan → periode berjalan (terbuka), BUKAN bulan lalu
        r = _manual_journal(f"{last_day}T20:00:00+00:00")
        if _wib_now().strftime("%Y-%m-%d") == f"{cur}-01" and _wib_now().hour < 3:
            pytest.skip("belum lewat 03:00 WIB tanggal 1 — jurnal itu masih di masa depan")
        je = ok(r)["data"]
        assert je["date"].startswith(f"{cur}-01"), je["date"]
        assert _pl_expense(f"{prev}-01", last_day) == before, "Laba Rugi periode tertutup tidak boleh berubah"
        # 10:00 UTC hari terakhir = 17:00 WIB hari terakhir → periode tertutup → ditolak
        r = _manual_journal(f"{last_day}T10:00:00+00:00")
        assert r.status_code == 400 and "tertutup" in r.text, r.text[:200]
        # tanggal bayar nyata di periode tertutup ditolak
        d = world.new_deal()["deal_id"]
        r = pay(d, 1_000_000, value_date=f"{prev}-15")
        assert r.status_code == 400 and "DITUTUP" in r.text, r.text[:200]
        # periode yang belum berakhir tidak boleh ditutup (dulu sampai 2027-01-01 setelah Nov–Des ditutup lebih awal)
        for p in (cur, nxt):
            r = call(SUPER, "POST", "/gl/periods/close", json={"period": p, "override": True,
                                                                 "override_reason": "uji GL-15 tutup dini"})
            assert r.status_code == 400 and "belum berakhir" in r.text, (p, r.status_code, r.text[:160])
    finally:
        call(SUPER, "POST", "/gl/periods/reopen", json={"period": prev})
        for p in (cur, nxt):    # kode lama menerima penutupan dini → bersihkan bila sempat tertutup
            call(SUPER, "POST", "/gl/periods/reopen", json={"period": p})


def test_gl15_jurnal_penutup_tahun_tetap_bertanggal_31_des_dan_tutup_ulang_berjurnal():
    """Kanonisasi tanggal ke WIB tidak boleh menggeser jurnal penutup (23:59 UTC 31 Des = 1 Jan WIB) ke tahun
    berikutnya; tutup → buka → tutup lagi tetap menghasilkan jurnal penutup BARU (GL-03)."""
    year = "2025"
    ok(_manual_journal(f"{year}-06-15"))                       # ada aktivitas laba-rugi di tahun uji
    rows = ok(call(SUPER, "GET", "/gl/periods", params={"limit": 60}))["data"]
    to_close = [r["period"] for r in rows if r["period"].startswith(year) and r["status"] == "open" and r["journals"]]
    closed_here = []
    try:
        for p in to_close:
            ok(call(SUPER, "POST", "/gl/periods/close", json={"period": p, "override": True,
                                                              "override_reason": "uji tutup tahun GL-15"}))
            closed_here.append(p)
        first = ok(call(SUPER, "POST", "/gl/year/close", json={"year": year}))["data"]
        je = ok(call(SUPER, "GET", f"/gl/journals/{first['entry_id']}"))["data"]
        assert je["date"][:10] == f"{year}-12-31", je["date"]
        ok(call(SUPER, "POST", "/gl/year/reopen", json={"year": year, "reason": "uji buka kembali tahun buku"}))
        # jurnal pembalik bertanggal 31 Des membuat Desember bertransaksi → tutup lagi sebelum tutup tahun ulang
        for r in ok(call(SUPER, "GET", "/gl/periods", params={"limit": 60}))["data"]:
            if r["period"].startswith(year) and r["status"] == "open" and r["journals"]:
                ok(call(SUPER, "POST", "/gl/periods/close", json={"period": r["period"], "override": True,
                                                                  "override_reason": "uji tutup tahun ulang"}))
                closed_here.append(r["period"])
        again = ok(call(SUPER, "POST", "/gl/year/close", json={"year": year}))["data"]
        assert again["entry_no"] != first["entry_no"] and not again.get("idempotent"), (first["entry_no"], again)
    finally:
        call(SUPER, "POST", "/gl/year/reopen", json={"year": year, "reason": "bersihkan sesudah uji tahun buku"})
        for p in closed_here:
            call(SUPER, "POST", "/gl/periods/reopen", json={"period": p})


def test_gl15_posting_otomatis_digeser_ke_periode_terbuka_terdekat_bukan_masa_depan_jauh():
    """Murni (tanpa server): bulan berjalan tertutup → hari pertama bulan DEPAN (bukan 2027-01-01);
    bulan lalu tertutup tapi bulan berjalan terbuka → SEKARANG; manual selalu ditolak."""
    import asyncio
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
    os.environ.setdefault("DB_NAME", "sipro_unit_dummy")
    import gl_periods as glp
    from core_utils import period_of
    prev, cur, _last, nxt = _period_info()
    months = [f"2026-{m:02d}" for m in range(1, 13)]
    asli = glp.closed_periods

    async def tutup_sampai_berjalan(_org):
        return {m for m in months if m <= cur}

    async def tutup_bulan_lalu(_org):
        return {prev}
    try:
        glp.closed_periods = tutup_sampai_berjalan
        d, dari = asyncio.run(glp.resolve_post_date("o", "2026-03-15", True))
        assert dari == "2026-03" and period_of(d) == nxt, (d, nxt)
        glp.closed_periods = tutup_bulan_lalu
        d, dari = asyncio.run(glp.resolve_post_date("o", f"{prev}-10", True))
        assert dari == prev and period_of(d) == cur and d[:10] <= _days_ago(0), d
        with pytest.raises(ValueError):
            asyncio.run(glp.resolve_post_date("o", f"{prev}-10", False))
    finally:
        glp.closed_periods = asli


# ================================================================== GL-21 — jurnal manual ke akun kendali
def _mj(email, lines, memo="Uji GL-21 " + TAG, **extra):
    return call(email, "POST", "/gl/journals", json={"memo": memo, "lines": lines, **extra})


def test_gl21_jurnal_manual_akun_kendali_butuh_izin_dan_alasan():
    ctl = [{"account_code": "2-1100", "debit": 1000, "credit": 0}, {"account_code": "4-1200", "debit": 0, "credit": 1000}]
    r = _mj(FINANCE, ctl)                                  # staf keuangan biasa: tidak berizin
    assert r.status_code == 403 and "akun kendali" in r.text, (r.status_code, r.text[:200])
    r = _mj(FINLEAD, ctl)                                  # berizin tetapi tanpa alasan
    assert r.status_code == 400 and "control_reason" in r.text, (r.status_code, r.text[:200])
    r = _mj(FINLEAD, ctl, control_reason="pendek")
    assert r.status_code == 400
    je = ok(_mj(FINLEAD, ctl, control_reason="koreksi saldo awal utang vendor hasil audit"))["data"]
    assert "akun kendali" in je["memo"], "alasan melekat pada jurnal"


def test_gl21_induk_kas_baris_dua_sisi_dan_memo_kosong_ditolak():
    ok_lines = [{"account_code": "6-1300", "debit": 500, "credit": 0}, {"account_code": "4-1200", "debit": 0, "credit": 500}]
    head = [{"account_code": "6-1300", "debit": 500, "credit": 0}, {"account_code": "1-1200", "debit": 0, "credit": 500}]
    for who in (FINANCE, FINLEAD, SUPER):
        r = _mj(who, head)
        assert r.status_code == 400 and "induk" in r.text, (who, r.status_code, r.text[:160])
    both = [{"account_code": "6-1300", "debit": 1000, "credit": 1000}, {"account_code": "4-1200", "debit": 0, "credit": 0}]
    assert _mj(FINANCE, both).status_code == 400
    assert _mj(FINANCE, ok_lines, memo="  ").status_code in (400, 422)
    ok(_mj(FINANCE, ok_lines))                              # jurnal biasa tetap jalan


# ================================================================== IN-17 / IN-16 — bukti bayar
def test_in17_bukti_bayar_staf_divalidasi_dan_tidak_dipakai_ulang(world):
    d1, d2 = world.new_deal()["deal_id"], world.new_deal()["deal_id"]

    def rc(deal, proofs, amount=2_000_000, who=FINANCE):
        return call(who, "POST", "/finance/ar/receipts",
                    json={"deal_id": deal, "amount": amount, "method": "transfer", "proof_file_ids": proofs})
    r = rc(d1, ["x"])
    assert r.status_code == 400 and "tidak ditemukan" in r.text, r.text[:200]
    proof = upload_proof()
    ok(rc(d1, [proof]))
    r = rc(d2, [proof])                                      # berkas yang sama untuk deal lain
    assert r.status_code == 400 and "sudah dipakai" in r.text, r.text[:200]
    r = rc(d2, [upload_proof(OWNER)])                        # diunggah orang lain
    assert r.status_code == 400 and "pengguna lain" in r.text, r.text[:200]
    assert len(ar(d2)["receipts"]) == 0
    ok(rc(d2, [upload_proof()], amount=3_000_000))           # berkas sendiri & baru → lolos


def test_in16_bukti_portal_tanggal_nominal_dan_isi_berkas(world):
    import io
    import requests
    from test_p0_masuk import API, rp_png
    from test_p0_masuk_2 import portal_token
    deal = world.new_deal()
    h = {"Authorization": f"Bearer {portal_token(deal['phone'])}"}
    bad = requests.post(f"{API}/portal/payments/proof/upload", headers=h, timeout=60, data={"deal_id": deal["deal_id"]},
                        files={"file": ("b.png", io.BytesIO(b"<html><script>alert(1)</script></html>"), "image/png")})
    assert bad.status_code == 400 and "Isi berkas" in bad.text, bad.text[:200]
    up = requests.post(f"{API}/portal/payments/proof/upload", headers=h, timeout=60, data={"deal_id": deal["deal_id"]},
                       files={"file": ("b.png", io.BytesIO(rp_png(int(time.time()) % 90000 + 7)), "image/png")})
    assert up.status_code == 200, up.text[:200]
    fid = up.json()["data"]["id"]
    for kw in ({"transfer_date": "abcdefghij"}, {"transfer_date": "2099-12-31"}, {"amount": 999_999_999_999}):
        body = {"deal_id": deal["deal_id"], "amount": 1_000_000, "transfer_date": _days_ago(0), "file_ids": [fid], **kw}
        r = requests.post(f"{API}/portal/payments/proof", headers=h, json=body, timeout=60)
        assert r.status_code == 400, (kw, r.status_code, r.text[:200])
    good = {"deal_id": deal["deal_id"], "amount": 1_000_000, "transfer_date": _days_ago(0), "file_ids": [fid]}
    assert requests.post(f"{API}/portal/payments/proof", headers=h, json=good, timeout=60).status_code == 200


# ================================================================== IN-20 — kuitansi void di laporan/PDF/portal
def test_in20_kuitansi_void_keluar_dari_total_laporan_dan_portal(world):
    import requests
    from test_p0_masuk import API
    from test_p0_masuk_2 import portal_token
    deal = world.new_deal()
    d = deal["deal_id"]
    t0 = ok(call(FINANCE, "GET", "/finance/reports/receipts"))["data"]["totals"]
    rid = ok(pay(d, 9_000_000))["data"]["receipt"]["id"]
    t1 = ok(call(FINANCE, "GET", "/finance/reports/receipts"))["data"]["totals"]
    assert t1["amount"] - t0["amount"] == 9_000_000
    ok(call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": "uji kuitansi dibatalkan IN-20"}))
    rep = ok(call(FINANCE, "GET", "/finance/reports/receipts"))["data"]
    assert rep["totals"]["amount"] == t0["amount"], "kuitansi void tidak boleh dihitung"
    assert rep["totals"]["void_count"] >= 1
    row = [r for r in rep["rows"] if r["id"] == rid][0]
    assert row["status"] == "void", "tetap tampil sebagai jejak, ditandai batal"
    h = {"Authorization": f"Bearer {portal_token(deal['phone'])}"}
    ids = [r["id"] for r in requests.get(f"{API}/portal/receipts", headers=h, timeout=30).json()["data"]]
    assert rid not in ids, "pembeli tidak melihat kuitansi yang dibatalkan"
    assert requests.get(f"{API}/portal/receipts/{rid}/pdf", headers=h, timeout=30).status_code == 404
    assert call(FINANCE, "GET", f"/finance/ar/receipts/{rid}/pdf").status_code == 200   # staf tetap bisa cetak (bertanda batal)


# ================================================================== GL-16 / PK-21 — tie-out kas bon gabungan
def test_gl16_tieout_kas_bon_menjumlahkan_dua_modul():
    from test_p0_keluar import call as kc, disburse_body, make_advance, make_fr

    def row():
        return [c for c in ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["checks"] if c["code"] == "1-1500"][0]
    r0 = row()
    assert r0["ok"], r0
    a = make_advance(amount=2_000_000)                                  # modul Kas Bon
    s, j = kc("finance", "POST", f"/petty-cash/advances/{a['id']}/disburse", {"source": "bank"})
    assert s == 200, (s, j)
    fr = make_fr(amount=1_500_000, typ="advance")                       # Pengajuan Dana jenis kas bon
    s, j = kc("finance", "POST", f"/fund-requests/{fr['id']}/disburse", disburse_body(fr["id"]))
    assert s == 200, (s, j)
    r1 = row()
    assert r1["ok"], r1
    assert r1["sources"]["cash_advances"] - r0["sources"]["cash_advances"] == 2_000_000
    assert r1["sources"]["fund_requests"] - r0["sources"]["fund_requests"] == 1_500_000
    assert r1["gl"] - r0["gl"] == 3_500_000 and "Pengajuan Dana" in r1["label"]


# ================================================================== GL-17 — pilihan rekening di alur uang
def _new_bank(opening=50_000_000):
    body = {"kind": "bank", "name": f"Rek GL17 {_uniq('R')}", "bank_name": "Bank Uji",
            "account_no": _uniq("NO").replace("-", ""), "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def _accounts():
    return {a["id"]: a for a in ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"]}


def test_gl17_booking_fee_tunai_masuk_kas_dan_rekening_bisa_dipilih(world):
    d = world.new_deal(booking_fee=5_000_000, book=False)["deal_id"]
    accs = _accounts()
    kas = next(a for a in accs.values() if a["kind"] == "cash" and a["is_default"])
    bank = next(a for a in accs.values() if a["kind"] == "bank" and a["is_default"])
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay", json={
        "amount": 2_000_000, "method": "cash", "proof_file_ids": [upload_proof()]}))
    after = _wait(lambda: (_accounts()[kas["id"]]["balance"] - kas["balance"]) == 2_000_000 and _accounts() or None)
    assert after, "setoran tunai booking fee harus masuk Kas, bukan bank"
    assert after[bank["id"]]["balance"] == bank["balance"]
    # rekening bank lain dipilih eksplisit
    rek = _new_bank(0)
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay", json={
        "amount": 1_000_000, "method": "transfer", "proof_file_ids": [upload_proof()], "cash_account_id": rek["id"]}))
    assert _wait(lambda: _accounts()[rek["id"]]["balance"] == 1_000_000), "uang harus mendarat di rekening pilihan"
    bad = call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay", json={
        "amount": 500_000, "method": "transfer", "proof_file_ids": [upload_proof()], "cash_account_id": "tidak-ada"})
    assert bad.status_code == 400, bad.text[:200]


def test_gl17_titipan_terima_dan_kembali_memakai_rekening_pilihan(world):
    d = world.new_deal()["deal_id"]
    rek = _new_bank(50_000_000)
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit", json={
        "amount": 4_000_000, "proof_file_ids": [upload_proof()], "cash_account_id": rek["id"]}))
    assert _wait(lambda: _accounts()[rek["id"]]["balance"] == 54_000_000), "titipan masuk ke rekening pilihan"
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit/refund", json={"amount": 1_500_000, "cash_account_id": rek["id"]}))
    assert _wait(lambda: _accounts()[rek["id"]]["balance"] == 52_500_000), "pengembalian keluar dari rekening pilihan"
    r = call(FINANCE, "POST", f"/finance/ar/{d}/deposit", json={
        "amount": 1_000, "proof_file_ids": [upload_proof()], "cash_account_id": "tidak-ada"})
    assert r.status_code == 400


def test_gl17_angsuran_pinjaman_dari_rekening_pilihan():
    import random
    rek = _new_bank(20_000_000)
    act = [x for x in ok(call(FINANCE, "GET", "/corp-financing/loans"))["data"] if x["status"] == "active"]
    if not act:
        pytest.skip("tidak ada pinjaman aktif untuk diuji")
    lid = act[0]["id"]
    sched = ok(call(FINANCE, "GET", f"/corp-financing/loans/{lid}"))["data"]["schedule"]
    item = next((r for r in sched if r["status"] != "paid" and r["amount_due"] > 2_000_000), None)
    if not item:
        pytest.skip("tidak ada angsuran terbuka yang cukup besar")
    amt = 1_000 + random.randint(1, 800)
    bad = call(FINANCE, "POST", f"/corp-financing/loans/{lid}/pay",
               json={"installment_no": item["no"], "amount": amt, "source": "bank", "cash_account_id": "tidak-ada"})
    assert bad.status_code == 400, bad.text[:200]
    ok(call(FINANCE, "POST", f"/corp-financing/loans/{lid}/pay",
            json={"installment_no": item["no"], "amount": amt, "source": "bank", "cash_account_id": rek["id"]}))
    assert _wait(lambda: _accounts()[rek["id"]]["balance"] == 20_000_000 - amt), "angsuran harus keluar dari rekening pilihan"


# ================================================================== GL-14 — klasifikasi arus kas
def test_gl14_klasifikasi_arus_kas_per_akun():
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
    os.environ.setdefault("DB_NAME", "sipro_unit_dummy")
    import gl_reports as glr
    expect = {"2-2100": "financing", "3-1900": "financing", "3-1950": "financing",     # utang bank (dulu operasi) & ekuitas
              "1-1800": "operating", "2-1500": "operating", "2-1700": "operating",      # dulu investasi / pendanaan
              "1-2100": "investing", "1-2200": "investing", "1-1300": "operating",
              "2-1400": "operating", "4-1100": "operating", "6-1300": "operating"}
    assert {c: glr._cash_category(c) for c in expect} == expect


# ================================================================== IN-21 — nomor giro varian
def test_in21_nomor_giro_varian_huruf_spasi_ditolak(world):
    d = world.new_deal()["deal_id"]
    no = f"BG-{TAG}-{uuid.uuid4().hex[:5].upper()}"
    base = {"kind": "bg", "bank_name": "BCA", "instrument_no": no, "amount": 7_000_000,
            "due_date": f"{_wib_now().year + 1}-01-15", "deal_id": d}
    ok(call(FINANCE, "POST", "/pdc", json=base))
    for inst, bank in ((no, "BCA"), (no.lower(), "BCA"), (" " + no + " ", "bca "), (no.replace("-", " "), "B C A"),
                       (no.replace("-", ""), "Bca")):
        r = call(FINANCE, "POST", "/pdc", json={**base, "instrument_no": inst, "bank_name": bank})
        assert r.status_code == 400 and "sudah tercatat" in r.text, (inst, bank, r.status_code, r.text[:160])
    # nomor yang benar-benar berbeda tetap boleh
    ok(call(FINANCE, "POST", "/pdc", json={**base, "instrument_no": no + "9"}))
