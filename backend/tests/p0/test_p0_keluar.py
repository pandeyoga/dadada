"""Regresi P0 — PEMBAYARAN KELUAR (audit PK-01 … PK-15).

Tes ini menembak server HIDUP (bukan mock): dua request PARALEL pada dokumen yang sama harus
menghasilkan TEPAT SATU efek uang (subledger + kas/bank + jurnal), alur sekuensial normal tetap
berhasil, dan kasus terlarang (saldo kurang, pemisahan tugas, retensi 150%, ...) ditolak.

Menjalankan (dari folder backend/, server + MongoDB hidup; seed demo sudah berjalan):

    API_BASE=http://localhost:8013/api REACT_APP_BACKEND_URL=http://localhost:8013 \
        python -m pytest -n 0 tests/p0/test_p0_keluar.py -v

Setiap tes membuat datanya sendiri (awalan `P0-`) dan mengukur SELISIH (sebelum → sesudah),
jadi aman dijalankan berulang pada database yang sama.
"""
import os
import threading
import time
import uuid

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8013/api").rstrip("/")
PW = "Sipro#2026"
LOGINS = {"superadmin": ("superadmin@estora.id", "test1234")}
_TOK = {}


def _email(u):
    return LOGINS.get(u, (f"{u}@sipro.co.id", PW))[0]


def tok(u):
    if u not in _TOK:
        email, pw = LOGINS.get(u, (f"{u}@sipro.co.id", PW))
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
        if r.status_code != 200:
            pytest.skip(f"login {email} gagal: {r.status_code}")
        _TOK[u] = r.json()["access_token"]
    return _TOK[u]


def call(u, method, path, body=None, params=None):
    r = requests.request(method, API + path, headers={"Authorization": "Bearer " + tok(u)},
                         json=body, params=params, timeout=120)
    try:
        j = r.json()
    except Exception:  # noqa: BLE001
        j = {"raw": r.text[:300]}
    return r.status_code, j


def par(fns):
    """Jalankan beberapa callable SERENTAK (pagar thread) dan kembalikan hasilnya berurutan."""
    res = [None] * len(fns)
    bar = threading.Barrier(len(fns))

    def w(i, fn):
        bar.wait()
        try:
            res[i] = fn()
        except Exception as e:  # noqa: BLE001
            res[i] = ("EXC", str(e))
    ts = [threading.Thread(target=w, args=(i, f)) for i, f in enumerate(fns)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return res


def same(n, fn):
    return par([fn] * n)


def codes(results):
    return sorted(r[0] for r in results)


def ok(results):
    return [r for r in results if r[0] == 200]


def detail(r):
    d = r[1]
    return d.get("detail") if isinstance(d, dict) else d


def uniq(prefix="P0"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------- pembaca keadaan
def accounts():
    s, j = call("finance", "GET", "/cash-bank/position")
    assert s == 200, j
    return {a["name"]: a for a in j["data"]["accounts"]}


def bank(name="Rekening Operasional"):
    return accounts()[name]["balance"]


def gl_balance(code):
    s, j = call("finance", "GET", "/gl/trial-balance")
    assert s == 200, j
    for r in j["data"]["rows"]:
        if r["code"] == code:
            return r["balance"]
    return 0


def gl_cash_out(delta_bank):
    return -delta_bank


# ---------------------------------------------------------------- pabrik data
def make_bill(claimed=10_000_000, ret=5, vendor=None, creator="finance", **extra):
    body = {"vendor": vendor or uniq("P0-Vendor"), "claimed": claimed, "retention_pct": ret}
    body.update(extra)
    s, j = call(creator, "POST", "/finance/ap/bills", body)
    assert s == 200, (s, j)
    return j["data"]


def approved_bill(claimed=10_000_000, ret=5, **kw):
    b = make_bill(claimed, ret, **kw)
    s, j = call("owner", "POST", f"/finance/ap/bills/{b['id']}/approve")
    assert s == 200, (s, j)
    return j["data"]


def bill_detail(bid):
    s, j = call("finance", "GET", f"/finance/ap/bills/{bid}")
    assert s == 200, j
    return j["data"]


# =============================================================================== A. AP
class TestAP:
    def test_bayar_paralel_satu_efek(self):
        """PK-01/02: 2 request bayar bersamaan → bank berkurang sekali, 1 payments_out, 1 jurnal bayar."""
        b = approved_bill(10_000_000, 5)           # net 9,5 jt
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay",
                                   {"amount": 9_500_000}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert all(r[0] in (200, 409) for r in res), [(r[0], detail(r)) for r in res]
        d = bill_detail(b["id"])
        assert d["bill"]["paid"] == 9_500_000 and d["bill"]["status"] == "paid"
        assert len(d["payments"]) == 1
        assert d["summary"]["paid_consistent"] is True
        pay_journals = [j for j in d["journals"] if str(j.get("memo", "")).startswith("Pembayaran")]
        assert len(pay_journals) == 1, [j["memo"] for j in d["journals"]]
        assert before - bank() == 9_500_000

    def test_bayar_beda_nominal_paralel_tidak_melebihi_sisa(self):
        """Dua pembayaran parsial berbeda bersamaan: total tidak boleh melebihi net."""
        b = approved_bill(10_000_000, 0)
        res = par([lambda: call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 6_000_000}),
                   lambda: call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 7_000_000})])
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        d = bill_detail(b["id"])
        assert d["bill"]["paid"] in (6_000_000, 7_000_000)
        assert len(d["payments"]) == 1 and d["summary"]["paid_consistent"]

    def test_bayar_dengan_pph_paralel_satu_efek(self):
        b = approved_bill(10_000_000, 0)
        body = {"bill_id": b["id"], "amount": 4_000_000, "kind": "pph23", "rate": 2}
        before = bank()
        res = same(2, lambda: call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay-withholding", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        d = bill_detail(b["id"])
        assert len(d["payments"]) == 1 and d["bill"]["paid"] == 4_000_000
        assert len(d["withholding"]) == 1
        assert before - bank() == 4_000_000 - 80_000

    def test_approve_paralel_satu_jurnal(self):
        """PK-02: approve bersamaan → ap.approved diterbitkan sekali (1 jurnal akrual)."""
        b = make_bill(3_000_000, 0)
        before = gl_balance("2-1100")
        res = same(3, lambda: call("owner", "POST", f"/finance/ap/bills/{b['id']}/approve"))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        d = bill_detail(b["id"])
        assert d["bill"]["status"] == "approved"
        assert len([j for j in d["journals"]]) == 1
        assert gl_balance("2-1100") - before == 3_000_000

    def test_sekuensial_normal_tetap_berhasil(self):
        """Alur normal: buat → setujui (orang lain) → bayar sebagian → bayar sisa; sisa lebih ditolak."""
        b = approved_bill(10_000_000, 5)
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 4_000_000})
        assert s == 200 and j["data"]["status"] == "partial", (s, j)
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 5_500_001})
        assert s == 400 and "melebihi sisa" in detail((s, j)), (s, j)
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 5_500_000})
        assert s == 200 and j["data"]["status"] == "paid"
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 1})
        assert s == 400, (s, j)   # sudah lunas: pesan status biasa, bukan 409 generik

    def test_client_ref_retry_tidak_membayar_dua_kali(self):
        b = approved_bill(10_000_000, 0)
        ref = uniq("ref")
        s1, j1 = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 2_000_000, "client_ref": ref})
        assert s1 == 200
        s2, j2 = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 2_000_000, "client_ref": ref})
        assert s2 == 409, (s2, j2)
        assert bill_detail(b["id"])["bill"]["paid"] == 2_000_000

    def test_saldo_kas_tidak_cukup_ditolak(self):
        """PK-06: bayar dari 'Kas Kecil Site' (saldo 0) ditolak dengan nama rekening, saldo, kebutuhan."""
        b = approved_bill(3_333_333, 0)
        acc = accounts()["Kas Kecil Site"]
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay",
                    {"amount": 3_333_333, "cash_account_id": acc["id"]})
        assert s == 400, (s, j)
        msg = detail((s, j))
        assert "Kas Kecil Site" in msg and "tidak cukup" in msg and "3,333,333" in msg, msg
        d = bill_detail(b["id"])
        assert d["bill"]["paid"] == 0 and len(d["payments"]) == 0
        assert accounts()["Kas Kecil Site"]["balance"] == acc["balance"]

    def test_retensi_di_luar_0_100_ditolak(self):
        """PK-08."""
        for pct in (150, -50, 100.5):
            s, j = call("finance", "POST", "/finance/ap/bills",
                        {"vendor": uniq("P0-Ret"), "claimed": 1_000_000, "retention_pct": pct})
            assert s == 400, (pct, s, j)
        # batas sah: 0 dan 100
        for pct in (0, 100):
            s, j = call("finance", "POST", "/finance/ap/bills",
                        {"vendor": uniq("P0-Ret"), "claimed": 1_000_000, "retention_pct": pct})
            assert s == 200, (pct, s, j)
            assert j["data"]["net"] >= 0

    def test_sod_pembuat_tidak_boleh_menyetujui_sendiri(self):
        """PK-07: finance membuat lalu menyetujui tagihannya sendiri → ditolak; owner boleh."""
        b = make_bill(2_000_000, 0, creator="finance")
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/approve")
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)
        s, j = call("owner", "POST", f"/finance/ap/bills/{b['id']}/approve")
        assert s == 200

    def test_sod_penyetuju_tidak_boleh_membayar(self):
        """PK-07: owner membuat dan finance menyetujui... penyetuju yang sama tidak boleh membayar."""
        b = make_bill(2_000_000, 0, creator="finance")
        s, j = call("owner", "POST", f"/finance/ap/bills/{b['id']}/approve")
        assert s == 200
        s, j = call("owner", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 2_000_000})
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 2_000_000})
        assert s == 200

    def test_nomor_faktur_vendor_kembar_ditolak(self):
        """PK-15: nomor faktur sama dari vendor sama ditolak; vendor lain atau tanpa nomor boleh."""
        v = uniq("P0-Vendor")
        no = uniq("INV")
        s, j = call("finance", "POST", "/finance/ap/bills",
                    {"vendor": v, "claimed": 1_000_000, "retention_pct": 0, "vendor_invoice_no": no})
        assert s == 200, (s, j)
        s, j = call("finance", "POST", "/finance/ap/bills",
                    {"vendor": v, "claimed": 1_000_000, "retention_pct": 0, "vendor_invoice_no": no})
        assert s == 400 and "sudah pernah dicatat" in detail((s, j)), (s, j)
        s, j = call("finance", "POST", "/finance/ap/bills",
                    {"vendor": uniq("P0-Lain"), "claimed": 1_000_000, "retention_pct": 0, "vendor_invoice_no": no})
        assert s == 200
        for _ in range(2):
            s, j = call("finance", "POST", "/finance/ap/bills",
                        {"vendor": v, "claimed": 1_000_000, "retention_pct": 0})
            assert s == 200
        # paralel: hanya satu yang lolos
        no2 = uniq("INV")
        res = same(3, lambda: call("finance", "POST", "/finance/ap/bills",
                                   {"vendor": v, "claimed": 1_000_000, "retention_pct": 0, "vendor_invoice_no": no2}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]


# ==== END ====
