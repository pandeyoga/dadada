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


def wait_until(cond, timeout=25.0, step=0.5):
    """Tunggu kondisi benar (jurnal event diposting dispatcher tiap ≤ 8 dtk)."""
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(step)
    return False


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


# ---------------------------------------------------------------- pembantu lanjutan
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002"
    "0001e221bc330000000049454e44ae426082")


def upload(user, owner_type, owner_id=None):
    """Unggah satu berkas bukti (PNG mungil) lewat API sungguhan → id berkas."""
    data = {"owner_type": owner_type, "optimize": "false"}
    if owner_id:
        data["owner_id"] = owner_id
    r = requests.post(f"{API}/files/upload", headers={"Authorization": "Bearer " + tok(user)},
                      files={"file": (f"{uniq('bukti')}.png", PNG, "image/png")}, data=data, timeout=60)
    assert r.status_code in (200, 201), (r.status_code, r.text[:200])
    return r.json()["data"]["id"]


def ensure_finlead():
    """Manajer Keuangan (finance_manager) — tidak ada di akun demo; dibuat lewat API Super Admin."""
    LOGINS["p0finlead"] = ("p0-finlead@sipro.co.id", PW)
    if "p0finlead" not in _TOK:
        call("superadmin", "POST", "/admin/users", {"name": "P0 Finlead", "email": "p0-finlead@sipro.co.id",
                                                    "password": PW, "role": "finance_manager"})
    return "p0finlead"


def project_id():
    s, j = call("finance", "GET", "/projects")
    return j["data"][0]["id"]


def fund(account_name, amount):
    """Isi rekening/kas lewat transfer internal dari Rekening Operasional (dibuat finance, disetujui owner)."""
    accs = accounts()
    s, j = call("finance", "POST", "/cash-bank/transfers",
                {"kind": "transfer", "from_account_id": accs["Rekening Operasional"]["id"],
                 "to_account_id": accs[account_name]["id"], "amount": amount, "fee": 0,
                 "note": "P0 isi kas uji"})
    assert s == 200, (s, j)
    s, j = call("owner", "POST", f"/cash-bank/transfers/{j['data']['id']}/approve")
    assert s == 200, (s, j)


# =============================================================== B. Pengadaan (PO → GRN → tagihan)
class TestProcurement:
    def _po(self, creator="pm", qty=100, price=70_000):
        s, j = call(creator, "POST", "/procurement/pos", {
            "project_id": project_id(), "po_type": "general", "vendor": uniq("P0-Vendor-PO"),
            "items": [{"description": "Semen uji", "uom": "sak", "qty": qty, "unit_price": price}]})
        assert s == 200, (s, j)
        return j["data"]

    def test_po_sod_pembuat_tidak_boleh_menyetujui(self):
        po = self._po("finance")
        s, j = call("finance", "POST", f"/procurement/pos/{po['id']}/approve", {})
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)
        s, j = call("owner", "POST", f"/procurement/pos/{po['id']}/approve", {})
        assert s == 200, (s, j)

    def test_rantai_p2p_satu_akun_terputus(self):
        """PK-07: finance buat PO → (tak bisa setujui sendiri); tagihan AP buatannya tak bisa disetujui sendiri."""
        po = self._po("finance", qty=10, price=100_000)
        s, j = call("owner", "POST", f"/procurement/pos/{po['id']}/approve", {})
        assert s == 200
        s, j = call("finance", "POST", "/procurement/grns",
                    {"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 10}]})
        assert s == 200, (s, j)
        s, j = call("finance", "POST", "/procurement/bills", {"po_id": po["id"], "claimed": 1_000_000, "retention_pct": 0})
        assert s == 200, (s, j)
        bid = j["data"]["id"]
        s, j = call("finance", "POST", f"/finance/ap/bills/{bid}/approve")
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)

    def test_grn_paralel_stok_dan_po_sekali(self):
        po = self._po("pm", qty=100)
        call("owner", "POST", f"/procurement/pos/{po['id']}/approve", {})
        body = {"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 100}]}
        res = same(3, lambda: call("pm", "POST", "/procurement/grns", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("pm", "GET", f"/procurement/pos/{po['id']}")
        assert len(j["grns"]) == 1
        assert j["data"]["status"] == "received" and j["data"]["received_value"] == 100 * 70_000

    def test_tagihan_po_paralel_satu_tagihan(self):
        po = self._po("pm", qty=100, price=70_000)   # PO 7 jt
        call("owner", "POST", f"/procurement/pos/{po['id']}/approve", {})
        call("pm", "POST", "/procurement/grns", {"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 100}]})
        body = {"po_id": po["id"], "claimed": 7_000_000, "retention_pct": 0}
        res = same(3, lambda: call("finance", "POST", "/procurement/bills", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("pm", "GET", f"/procurement/pos/{po['id']}")
        assert len(j["bills"]) == 1 and j["data"]["billed_value"] == 7_000_000

    def test_retensi_150_persen_tagihan_po_ditolak(self):
        po = self._po("pm")
        call("owner", "POST", f"/procurement/pos/{po['id']}/approve", {})
        call("pm", "POST", "/procurement/grns", {"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 100}]})
        s, j = call("finance", "POST", "/procurement/bills", {"po_id": po["id"], "claimed": 1_000_000, "retention_pct": 150})
        assert s == 400, (s, j)


# =============================================================== C. Pengajuan keuangan (fund requests)
def make_fr(creator="pm", amount=500_000, typ="expense", approve_by="finance", **extra):
    body = {"type": typ, "title": uniq("P0 pengajuan"), "amount": amount, "category": "lainnya"}
    body.update(extra)
    s, j = call(creator, "POST", "/fund-requests", body)
    assert s == 200, (s, j)
    fr = j["data"]
    if approve_by:
        s, j = call(approve_by, "POST", f"/fund-requests/{fr['id']}/approve", {})
        assert s == 200, (s, j)
        fr = j["data"]
    return fr


def disburse_body(rid, user="finance", **extra):
    body = {"source": "bank", "proof_ids": [upload(user, "fund_request_payment", rid)]}
    body.update(extra)
    return body


class TestFundRequest:
    def test_cairkan_paralel_satu_efek(self):
        """PK-02: 3 pencairan bersamaan → kas keluar sekali, riwayat 'disbursed' sekali."""
        fr = make_fr(amount=500_000)
        body = disburse_body(fr["id"])
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert all(r[0] in (200, 400, 409) for r in res)
        s, j = call("finance", "GET", f"/fund-requests/{fr['id']}")
        d = j["data"]
        assert d["status"] == "settled" and d["disbursed_amount"] == 500_000
        assert len([h for h in d["history"] if h["action"] == "disbursed"]) == 1
        assert len(d["journal_ids"]) == 1
        assert before - bank() == 500_000

    def test_sekuensial_normal_dan_cairkan_dua_kali_ditolak(self):
        fr = make_fr(amount=300_000)
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", disburse_body(fr["id"]))
        assert s == 200 and j["data"]["status"] == "settled", (s, j)
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", disburse_body(fr["id"]))
        assert s == 400, (s, j)

    def test_pemohon_tidak_boleh_mencairkan_sendiri(self):
        """PK-07 (API): finance mengajukan, owner menyetujui, finance TIDAK boleh mencairkan miliknya sendiri."""
        fr = make_fr("finance", amount=200_000, approve_by="owner")
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", disburse_body(fr["id"]))
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)
        s, j = call("owner", "POST", f"/fund-requests/{fr['id']}/disburse", disburse_body(fr["id"], "owner"))
        assert s == 200, (s, j)

    def test_bukti_pencairan_wajib_di_api(self):
        fr = make_fr(amount=200_000)
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", {"source": "bank"})
        assert s == 400 and "bukti" in detail((s, j)).lower(), (s, j)
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse",
                    {"source": "bank", "proof_ids": ["FAKE-FILE-ID"]})
        assert s == 400 and "tidak ditemukan" in detail((s, j)), (s, j)
        s, j = call("finance", "GET", f"/fund-requests/{fr['id']}")
        assert j["data"]["status"] == "approved"

    def test_bukti_tidak_boleh_dipakai_ulang(self):
        fr1 = make_fr(amount=100_000)
        fr2 = make_fr(amount=100_000)
        shared = upload("finance", "generic")
        s, j = call("finance", "POST", f"/fund-requests/{fr1['id']}/disburse", {"source": "bank", "proof_ids": [shared]})
        assert s == 200, (s, j)
        s, j = call("finance", "POST", f"/fund-requests/{fr2['id']}/disburse", {"source": "bank", "proof_ids": [shared]})
        assert s == 400 and "sudah dipakai" in detail((s, j)), (s, j)
        # berkas terikat ke pengajuan LAIN (owner_id) juga ditolak
        other = upload("finance", "fund_request_payment", fr1["id"])
        s, j = call("finance", "POST", f"/fund-requests/{fr2['id']}/disburse", {"source": "bank", "proof_ids": [other]})
        assert s == 400, (s, j)

    def test_bukti_milik_orang_lain_ditolak(self):
        fr = make_fr(amount=100_000)
        pm_file = upload("pm", "fund_request_payment", fr["id"])
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", {"source": "bank", "proof_ids": [pm_file]})
        assert s == 400 and "pengguna lain" in detail((s, j)), (s, j)

    def test_reimbursement_lampiran_palsu_ditolak(self):
        s, j = call("pm", "POST", "/fund-requests", {
            "type": "reimbursement", "title": uniq("P0 reimb"), "amount": 100_000, "category": "lainnya",
            "attachment_ids": ["fake-id-123"]})
        assert s == 400 and "tidak ditemukan" in detail((s, j)), (s, j)
        real = upload("pm", "fund_request")
        s, j = call("pm", "POST", "/fund-requests", {
            "type": "reimbursement", "title": uniq("P0 reimb"), "amount": 100_000, "category": "lainnya",
            "attachment_ids": [real]})
        assert s == 200 and len(j["data"]["attachments"]) == 1, (s, j)
        # berkas yang sama tidak boleh menjadi nota pengajuan kedua
        s, j = call("pm", "POST", "/fund-requests", {
            "type": "reimbursement", "title": uniq("P0 reimb"), "amount": 100_000, "category": "lainnya",
            "attachment_ids": [real]})
        assert s == 400 and "sudah dipakai" in detail((s, j)), (s, j)

    def test_vendor_payment_ke_tagihan_ap_paralel_satu_pembayaran(self):
        b = approved_bill(4_000_000, 0)
        fr = make_fr("pm", amount=4_000_000, typ="vendor_payment", ap_bill_id=b["id"])
        body = disburse_body(fr["id"])
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        d = bill_detail(b["id"])
        assert d["bill"]["paid"] == 4_000_000 and len(d["payments"]) == 1 and d["summary"]["paid_consistent"]
        assert before - bank() == 4_000_000

    def test_cairkan_saldo_kas_kurang_ditolak(self):
        fr = make_fr(amount=7_000_000)
        acc = accounts()["Kas Kecil Site"]
        body = disburse_body(fr["id"], cash_account_id=acc["id"], source="kas")
        s, j = call("finance", "POST", f"/fund-requests/{fr['id']}/disburse", body)
        assert s == 400 and "Kas Kecil Site" in detail((s, j)) and "tidak cukup" in detail((s, j)), (s, j)
        s, j = call("finance", "GET", f"/fund-requests/{fr['id']}")
        assert j["data"]["status"] == "approved"


# =============================================================== D. Kas bon (modul KB)
def make_advance(creator="pm", amount=1_000_000):
    s, j = call(creator, "POST", "/petty-cash/advances",
                {"purpose": uniq("P0 kas bon"), "amount": amount, "category": "transport"})
    assert s == 200, (s, j)
    s2, j2 = call("finance", "POST", f"/petty-cash/advances/{j['data']['id']}/approve", {})
    assert s2 == 200, (s2, j2)
    return j2["data"]


class TestKasBon:
    def test_cairkan_paralel_satu_efek(self):
        a = make_advance(amount=3_000_000)
        before = bank()
        body = {"source": "bank"}
        res = same(3, lambda: call("finance", "POST", f"/petty-cash/advances/{a['id']}/disburse", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/petty-cash/advances/{a['id']}")
        d = j["data"]
        assert d["status"] == "disbursed" and d["outstanding"] == 3_000_000 and len(d["journal_ids"]) == 1
        assert before - bank() == 3_000_000

    def test_settle_paralel_satu_jurnal(self):
        a = make_advance(amount=3_000_000)
        s, j = call("finance", "POST", f"/petty-cash/advances/{a['id']}/disburse", {"source": "bank"})
        assert s == 200
        body = {"items": [{"category": "transport", "description": "Ongkos", "amount": 2_000_000}]}
        before = bank()
        res = same(3, lambda: call("pm", "POST", f"/petty-cash/advances/{a['id']}/settle", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/petty-cash/advances/{a['id']}")
        d = j["data"]
        assert d["status"] == "settled" and d["returned_amount"] == 1_000_000
        assert len(d["journal_ids"]) == 2        # 1 cair + 1 pertanggungjawaban
        assert bank() - before == 1_000_000       # sisa dikembalikan masuk kas SEKALI

    def test_pemohon_tidak_boleh_mencairkan_sendiri(self):
        s, j = call("finance", "POST", "/petty-cash/advances",
                    {"purpose": uniq("P0 kas bon"), "amount": 500_000, "category": "transport"})
        assert s == 200
        aid = j["data"]["id"]
        s, j = call("owner", "POST", f"/petty-cash/advances/{aid}/approve", {})
        assert s == 200
        s, j = call("finance", "POST", f"/petty-cash/advances/{aid}/disburse", {"source": "bank"})
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)

    def test_saldo_kas_kurang_ditolak(self):
        a = make_advance(amount=900_000_000_000)
        s, j = call("finance", "POST", f"/petty-cash/advances/{a['id']}/disburse", {"source": "bank"})
        assert s == 400 and "tidak cukup" in detail((s, j)), (s, j)


# =============================================================== E. Kas kecil (imprest)
class TestKasKecil:
    def _expense(self, acc_id, amount, file_ids=None, user="finance"):
        return call(user, "POST", "/petty-cash/expenses", {
            "cash_account_id": acc_id, "amount": amount, "category": "transport", "description": uniq("P0 beli"),
            "file_ids": file_ids if file_ids is not None else [upload(user, "petty_expense")]})

    def test_pengeluaran_paralel_tidak_menembus_saldo_dan_void_sekali(self):
        accs = accounts()
        kk = accs["Kas Kecil Site"]
        if kk["balance"] != 1_000_000:       # bawa saldo kas kecil tepat ke Rp 1 jt (saldo awal bisa berbeda)
            if kk["balance"] < 1_000_000:
                fund("Kas Kecil Site", 1_000_000 - kk["balance"])
        base = accounts()["Kas Kecil Site"]["balance"]
        assert base >= 1_000_000
        files = [upload("finance", "petty_expense") for _ in range(4)]
        res = par([lambda f=f: self._expense(kk["id"], base - 400_000, [f]) for f in files])
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert accounts()["Kas Kecil Site"]["balance"] == 400_000
        # void paralel oleh owner (bukan pencatat) → kas kembali sekali
        exp = ok(res)[0][1]["data"]
        res = same(3, lambda: call("owner", "POST", f"/petty-cash/expenses/{exp['id']}/void", {"reason": "P0 uji batal ganda"}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert accounts()["Kas Kecil Site"]["balance"] == base

    def test_bukti_palsu_atau_dipakai_ulang_ditolak(self):
        kk = accounts()["Kas Besar"]
        s, j = self._expense(kk["id"], 10_000, ["FAKE-FILE-ID"])
        assert s == 400 and "tidak ditemukan" in detail((s, j)), (s, j)
        s, j = self._expense(kk["id"], 10_000, [])
        assert s == 400 and "wajib" in detail((s, j)), (s, j)
        f = upload("finance", "petty_expense")
        s, j = self._expense(kk["id"], 10_000, [f])
        assert s == 200, (s, j)
        s, j = self._expense(kk["id"], 10_000, [f])
        assert s == 400, (s, j)


# =============================================================== F. Komisi & fee
class TestKomisi:
    def _by_status(self, status):
        s, j = call("finance", "GET", "/finance/commissions", params={"limit": 100})
        return [c for c in j["data"] if c["status"] == status]

    def test_approve_pada_komisi_paid_ditolak(self):
        """PK-03: approve pada komisi 'paid' tidak boleh memundurkan status / menerbitkan akrual baru."""
        paid = self._by_status("paid")
        if not paid:
            pytest.skip("tidak ada komisi berstatus paid pada data ini")
        c = paid[0]
        before = gl_balance("6-1100")
        s, j = call("owner", "POST", f"/finance/commissions/{c['id']}/approve")
        assert s == 400 and "tidak dapat disetujui" in detail((s, j)), (s, j)
        assert gl_balance("6-1100") == before
        s, j = call("owner", "GET", "/finance/commissions", params={"limit": 100})
        assert next(x for x in j["data"] if x["id"] == c["id"])["status"] == "paid"

    def test_approve_paralel_satu_akrual(self):
        pend = self._by_status("pending")
        if not pend:
            pytest.skip("tidak ada komisi pending pada data ini (sudah terpakai uji sebelumnya)")
        c = pend[0]
        before6 = gl_balance("6-1100")
        res = same(3, lambda: call("owner", "POST", f"/finance/commissions/{c['id']}/approve"))
        assert len(ok(res)) >= 1 and all(r[0] in (200, 409) for r in res), [(r[0], detail(r)) for r in res]
        # jurnal komisi diposting oleh dispatcher (≤ 8 dtk) — tunggu, lalu pastikan akrual SEKALI saja
        wait_until(lambda: gl_balance("6-1100") - before6 >= c["amount"])
        time.sleep(9)   # lewati satu tick lagi: bila ada event ganda, akrual kedua akan muncul di sini
        assert gl_balance("6-1100") - before6 == c["amount"]

    def test_bayar_paralel_satu_efek_dan_tidak_bisa_dibayar_ulang(self):
        approved = self._by_status("approved")
        if not approved:
            pytest.skip("tidak ada komisi approved pada data ini (sudah terpakai uji sebelumnya)")
        c = approved[0]
        by = (c.get("approved_by") or "").split("@")[0]
        payer = "owner" if by == "finance" else "finance"
        if by == payer:
            pytest.skip("penyetuju dan pembayar sama")
        before_bank = bank()
        before6 = gl_balance("6-1100")
        res = same(3, lambda: call(payer, "POST", f"/finance/commissions/{c['id']}/pay", {}))
        assert 200 in codes(res) and all(r[0] in (200, 409) for r in res), [(r[0], detail(r)) for r in res]
        wait_until(lambda: before_bank - bank() >= c["amount"])
        time.sleep(9)
        assert before_bank - bank() == c["amount"]                    # bank keluar SEKALI
        # approve lagi pada komisi paid → ditolak (PK-03), tanpa akrual baru
        s, j = call("owner", "POST", f"/finance/commissions/{c['id']}/approve")
        assert s == 400, (s, j)
        s, j = call(payer, "POST", f"/finance/commissions/{c['id']}/pay", {})
        assert s == 200                                                # pay ulang idempoten
        time.sleep(9)
        assert before_bank - bank() == c["amount"] and gl_balance("6-1100") == before6

    def test_penyetuju_tidak_boleh_membayar(self):
        approved = self._by_status("approved")
        if not approved:
            pytest.skip("tidak ada komisi approved")
        c = approved[0]
        s, j = call("finance", "GET", "/finance/commissions", params={"limit": 100})
        by = next(x for x in j["data"] if x["id"] == c["id"]).get("approved_by")
        if not by or by.split("@")[0] not in ("owner", "finance"):
            pytest.skip("penyetuju komisi seed bukan akun demo")
        payer = by.split("@")[0]
        s, j = call(payer, "POST", f"/finance/commissions/{c['id']}/pay", {})
        assert s == 400 and "Pemisahan tugas" in detail((s, j)), (s, j)


def a_booked_deal():
    s, j = call("finance", "GET", "/deals", params={"limit": 20})
    rows = [d for d in j["data"] if d.get("status") == "booked"]
    assert rows, "tidak ada deal booked"
    return rows[0]


class TestMarketingFee:
    def _fee(self, deal_id, value=10_000_000):
        s, j = call("marketing", "POST", "/marketing/agents",
                    {"name": uniq("P0 Agen"), "agent_type": "referral_pembeli"})
        assert s == 200, (s, j)
        s, j = call("marketing", "POST", "/marketing/fees",
                    {"agent_id": j["data"]["id"], "deal_id": deal_id, "basis": "fixed", "value": value,
                     "trigger": "booking", "pph_pct": 0})
        return s, j

    def test_bayar_paralel_satu_efek(self):
        s, j = self._fee(a_booked_deal()["id"], 9_000_000)
        assert s == 200, (s, j)
        fid = j["data"]["id"]
        s, j = call("owner", "POST", f"/marketing/fees/{fid}/approve", {})
        assert s == 200, (s, j)
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/marketing/fees/{fid}/pay", {"source": "bank"}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/marketing/fees/{fid}")
        d = j["data"]
        assert d["status"] == "paid" and d["paid_amount"] == 9_000_000
        assert before - bank() == 9_000_000
        s, j = call("finance", "GET", "/finance/ap/payments", params={"limit": 200})
        assert len([p for p in j["data"] if p.get("marketing_fee_id") == fid]) == 1

    def test_approve_paralel_satu_jurnal(self):
        s, j = self._fee(a_booked_deal()["id"], 1_000_000)
        assert s == 200
        fid = j["data"]["id"]
        res = same(3, lambda: call("owner", "POST", f"/marketing/fees/{fid}/approve", {}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/marketing/fees/{fid}")
        assert len(j["data"]["journal_ids"]) == 1

    def test_saldo_kurang_ditolak(self):
        s, j = self._fee(a_booked_deal()["id"], 20_000_000)
        fid = j["data"]["id"]
        call("owner", "POST", f"/marketing/fees/{fid}/approve", {})
        # sumber 'kas' → Kas Besar (default); fee > saldo kas besar
        s, j = call("finance", "POST", f"/marketing/fees/{fid}/pay", {"amount": 20_000_000, "source": "kas"})
        if accounts()["Kas Besar"]["balance"] >= 20_000_000:
            pytest.skip("Kas Besar cukup untuk uji ini")
        assert s == 400 and "tidak cukup" in detail((s, j)), (s, j)


# =============================================================== G. Titipan pembeli (refund deposit)
class TestDeposit:
    def test_refund_titipan_paralel_satu_efek_saldo_tidak_negatif(self):
        deal = a_booked_deal()
        fid = upload("finance", "receipt_proof")
        s, j = call("finance", "POST", f"/finance/ar/{deal['id']}/deposit", {"amount": 2_000_000, "proof_file_ids": [fid],
                                                                      "note": "P0 titipan uji"})
        assert s == 200, (s, j)
        bal0 = j["data"]["deposit"]["balance"]
        refunded0 = j["data"]["deposit"].get("refunded_total", 0)
        res = same(3, lambda: call("finance", "POST", f"/finance/ar/{deal['id']}/deposit/refund", {"amount": bal0}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/finance/ar/{deal['id']}")
        dep = j.get("deposit") or {}
        # PK-02: saldo titipan tidak boleh negatif (dulu −Rp 2 jt) dan pengembalian tercatat sekali
        assert dep.get("balance", 0) == 0 and dep.get("refunded_total", 0) - refunded0 == bal0
        s, j = call("finance", "POST", f"/finance/ar/{deal['id']}/deposit/refund", {"amount": 1})
        assert s == 400, (s, j)    # saldo habis → sekuensial tetap ditolak dengan pesan biasa


# =============================================================== H. Refund pembatalan
class TestRefundPembatalan:
    def _ready(self):
        lead = ensure_finlead()
        s, j = call(lead, "GET", "/cancellations")
        rows = j.get("data", [])
        c = next((x for x in rows if x["state"] in ("disetujui", "refund_sebagian")), None)
        if c is None:
            c = next((x for x in rows if x["state"] == "diajukan"), None)
            if c is None:
                pytest.skip("tidak ada pembatalan yang bisa dibayar refund-nya")
            s, j = call(lead, "POST", f"/cancellations/{c['id']}/decision",
                        {"approved": True, "note": "P0 uji setujui pembatalan"})
            assert s == 200, (s, j)
            c = j["data"]
        assert c.get("refund_outstanding", 0) > 5_000_000, c.get("refund_outstanding")
        return lead, c

    def _body(self, **kw):
        body = {"method": "transfer", "amount": 1_000_000, "override": True,
                "override_reason": "P0 uji: abaikan penahanan penjualan ulang"}
        body.update(kw)
        return body

    def test_refund_paralel_dengan_client_ref_sama_satu_pembayaran(self):
        lead, c = self._ready()
        ref = uniq("ref-refund")
        before = bank()
        res = same(4, lambda: call(lead, "POST", f"/cancellations/{c['id']}/refund", self._body(client_ref=ref)))
        assert all(r[0] == 200 for r in res), [(r[0], detail(r)) for r in res]   # replay → 200 semua
        assert len([r for r in res if not r[1].get("replay")]) == 1
        wait_until(lambda: before - bank() >= 1_000_000)
        time.sleep(1)
        assert before - bank() == 1_000_000
        s, j = call(lead, "GET", f"/cancellations/{c['id']}")
        pays = [p for p in j["data"]["refund_payments"] if p.get("client_ref") == ref]
        assert len(pays) == 1 and pays[0]["journal_id"]

    def test_refund_paralel_tanpa_client_ref_satu_pembayaran(self):
        lead, c = self._ready()
        before = bank()
        res = same(4, lambda: call(lead, "POST", f"/cancellations/{c['id']}/refund", self._body(amount=1_000_001)))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert before - bank() == 1_000_001

    def test_refund_melebihi_sisa_ditolak_dan_saldo_kurang(self):
        lead, c = self._ready()
        s, j = call(lead, "POST", f"/cancellations/{c['id']}/refund", self._body(amount=c["refund_outstanding"] + 1))
        assert s == 400 and "melebihi" in detail((s, j)), (s, j)
        if c["refund_outstanding"] > bank():
            s, j = call(lead, "POST", f"/cancellations/{c['id']}/refund", self._body(amount=c["refund_outstanding"]))
            assert s == 400 and "tidak cukup" in detail((s, j)), (s, j)


# =============================================================== I. Pinjaman, pajak, aset, upah
class TestPinjaman:
    def _loan(self):
        s, j = call("finance", "GET", "/corp-financing/loans")
        act = [x for x in j["data"] if x["status"] == "active"]
        assert act, "tidak ada pinjaman aktif"
        s, j = call("finance", "GET", f"/corp-financing/loans/{act[0]['id']}")
        sched = j["data"]["schedule"]
        item = next(r for r in sched if r["status"] != "paid" and r["amount_due"] > 1_000_000)
        return act[0]["id"], item["no"]

    def test_angsuran_paralel_satu_efek(self):
        lid, no = self._loan()
        amt = 1_000 + int(uuid.uuid4().int % 900)
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/corp-financing/loans/{lid}/pay",
                                   {"installment_no": no, "amount": amt, "source": "bank"}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert before - bank() == amt
        s, j = call("finance", "GET", "/corp-financing/payments", params={"loan_id": lid})
        assert len([p for p in j["data"] if p["amount"] == amt]) == 1

    def test_tanggal_sembarang_ditolak_tanpa_jurnal(self):
        """PK-14: tanggal tak valid / masa depan ditolak SEBELUM jurnal; kas tidak berubah."""
        lid, no = self._loan()
        before = bank()
        for bad in ("garbage-date", "2035-01-01"):
            s, j = call("finance", "POST", f"/corp-financing/loans/{lid}/pay",
                        {"installment_no": no, "amount": 1000, "source": "bank", "date": bad})
            assert s == 400, (bad, s, j)
        assert bank() == before

    def test_angsuran_saldo_kurang_ditolak(self):
        lid, no = self._loan()
        s, j = call("finance", "GET", f"/corp-financing/loans/{lid}")
        item = next(r for r in j["data"]["schedule"] if r["no"] == no)
        accs = accounts()
        # sumber 'kas' (Kas Besar Rp 17,5 jt) tidak cukup untuk angsuran > saldonya
        if item["amount_due"] <= accs["Kas Besar"]["balance"]:
            pytest.skip("angsuran lebih kecil dari saldo Kas Besar")
        s, j = call("finance", "POST", f"/corp-financing/loans/{lid}/pay",
                    {"installment_no": no, "amount": item["amount_due"], "source": "kas"})
        assert s == 400 and "tidak cukup" in detail((s, j)), (s, j)


class TestPajak:
    def test_setor_paralel_satu_jurnal(self):
        s, j = call("finance", "GET", "/tax/records", params={"status": "pending", "limit": 100})
        rows = [r for r in j["data"] if r["type"] == "pph"]
        if not rows:
            pytest.skip("tidak ada catatan pajak PPh pending")
        r = rows[0]
        before = bank("Rekening Escrow")
        body = {"status": "paid", "ntpn": uniq("NTPN"), "paid_date": "2026-11-01",
                "cash_account_id": accounts()["Rekening Escrow"]["id"]}
        res = same(3, lambda: call("finance", "PUT", f"/tax/records/{r['id']}", body))
        assert 200 in codes(res) and all(x[0] in (200, 409) for x in res), [(x[0], detail(x)) for x in res]
        s, j = call("finance", "GET", "/tax/records", params={"limit": 200})
        rec = next(x for x in j["data"] if x["id"] == r["id"])
        assert rec["status"] == "paid" and rec.get("gl_setor_entry_no")
        assert before - bank("Rekening Escrow") == r["amount"]       # keluar SEKALI

    def test_tanggal_setor_tidak_valid_ditolak(self):
        s, j = call("finance", "GET", "/tax/records", params={"status": "pending", "limit": 100})
        if not j["data"]:
            pytest.skip("tidak ada catatan pajak pending")
        rid = j["data"][0]["id"]
        s, j = call("finance", "PUT", f"/tax/records/{rid}", {"status": "paid", "ntpn": "X1", "paid_date": "2035-01-01"})
        assert s == 400, (s, j)

    def test_setor_saldo_kas_kurang_ditolak(self):
        s, j = call("finance", "GET", "/tax/records", params={"status": "pending", "limit": 100})
        acc = accounts()["Kas Kecil Site"]
        big = [r for r in j["data"] if r["amount"] > acc["balance"]]
        if not big:
            pytest.skip("tidak ada catatan pajak pending yang melebihi saldo Kas Kecil Site")
        s, j = call("finance", "PUT", f"/tax/records/{big[0]['id']}",
                    {"status": "paid", "ntpn": uniq("NTPN"), "cash_account_id": acc["id"]})
        assert s == 400 and "Kas Kecil Site" in detail((s, j)) and "tidak cukup" in detail((s, j)), (s, j)
        s, j = call("finance", "GET", "/tax/records", params={"limit": 200})
        assert next(x for x in j["data"] if x["id"] == big[0]["id"])["status"] == "pending"


class TestAsetTetap:
    def _asset(self, cost, name=None):
        return {"name": name or uniq("P0 Laptop"), "category": "perabot_kantor", "tax_group": "kelompok_1",
                "method": "garis_lurus", "cost": cost, "funding": "bank"}

    def test_pembuatan_identik_paralel_satu_aset(self):
        body = self._asset(15_000_000, uniq("P0 Aset Kembar"))
        before = bank()
        res = same(3, lambda: call("finance", "POST", "/fixed-assets/assets", body))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert before - bank() == 15_000_000

    def test_aset_melebihi_saldo_bank_ditolak(self):
        s, j = call("finance", "POST", "/fixed-assets/assets", self._asset(99_000_000_000))
        assert s == 400 and "tidak cukup" in detail((s, j)) and "Rekening Operasional" in detail((s, j)), (s, j)

    def test_sakelar_izinkan_saldo_negatif(self):
        """Sakelar Pusat Konfigurasi `cash.allow_negative` (bawaan mati) mengizinkan saldo minus bila dinyalakan."""
        s, j = call("finance", "GET", "/settings", params={"q": "cash.allow_negative"})
        if s != 200:
            pytest.skip(f"/settings tidak tersedia: {s}")
        rows = j.get("data") or []
        row = next((r for r in rows if r.get("key") == "cash.allow_negative"), None)
        assert row is not None, "kunci cash.allow_negative tidak terdaftar"
        assert row["value"] is False                                    # bawaan MATI


class TestUpah:
    def test_bayar_upah_paralel_satu_efek(self):
        pid = project_id()
        s, j = call("pm", "POST", "/labor/workers", {"name": uniq("P0 Tukang"), "role": "tukang", "daily_wage": 150_000,
                                                    "project_ids": [pid]})
        if s != 200:
            pytest.skip(f"master pekerja: {s} {j}")
        wid = j["data"]["id"]
        # tanggal unik per jalankan (rekap tidak boleh bertumpang)
        day = time.strftime("%Y-%m-%d", time.gmtime(1_500_000_000 + (uuid.uuid4().int % 700) * 86400))
        s, j = call("pm", "POST", "/labor/attendance", {"project_id": pid, "work_date": day,
                                                       "entries": [{"worker_id": wid, "status": "full"}]})
        if s != 200:
            pytest.skip(f"absensi: {s} {j}")
        s, j = call("pm", "POST", "/labor/payrolls", {"project_id": pid, "period_start": day, "period_end": day})
        assert s == 200, (s, j)
        prid = j["data"]["id"]
        total = j["data"]["total"]
        assert call("pm", "POST", f"/labor/payrolls/{prid}/submit")[0] == 200
        assert call("finance", "POST", f"/labor/payrolls/{prid}/decision", {"approve": True})[0] == 200
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/labor/payrolls/{prid}/pay", {}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert before - bank() == total
        s, j = call("finance", "GET", f"/labor/payrolls/{prid}")
        assert len([h for h in j["data"]["history"] if h["action"] == "pay"]) == 1


# =============================================================== J. Subkon: uang muka, potongan, termin, retensi, SPK
REASON = "P0 uji otomatis — alasan lengkap untuk kontrol keuangan subkon"


def make_spk(contract=100_000_000, retention=5, creator="pm"):
    s, j = call("pm", "GET", "/subcon/subcontractors")
    sub = j["data"][0]["id"]
    s, j = call(creator, "POST", "/subcon/spk", {
        "subcontractor_id": sub, "project_id": project_id(), "title": uniq("P0 SPK"),
        "contract_value": contract, "retention_pct": retention, "maintenance_days": 90})
    assert s == 200, (s, j)
    return j["data"]


def paid_advance(spk, amount=20_000_000):
    lead = ensure_finlead()
    s, j = call("pm", "POST", "/subcon/advances", {"spk_id": spk["id"], "amount": amount, "reason": REASON})
    assert s == 200, (s, j)
    aid = j["data"]["id"]
    s, j = call(lead, "POST", f"/subcon/advances/{aid}/decision", {"approve": True, "reason": REASON})
    assert s == 200, (s, j)
    s, j = call("finance", "POST", f"/subcon/advances/{aid}/pay", {})
    assert s == 200, (s, j)
    return j["data"]


def submitted_claim(spk, pct=50):
    s, j = call("site", "POST", "/subcon/claims", {"spk_id": spk["id"], "progress_pct": pct})
    assert s == 200, (s, j)
    cid = j["data"]["id"]
    s, j = call("pm", "POST", f"/subcon/claims/{cid}/verify", {"verified_pct": pct})
    assert s == 200, (s, j)
    return j["data"]


class TestSubkon:
    def test_uang_muka_dibayar_paralel_satu_efek(self):
        lead = ensure_finlead()
        spk = make_spk()
        s, j = call("pm", "POST", "/subcon/advances", {"spk_id": spk["id"], "amount": 20_000_000, "reason": REASON})
        aid = j["data"]["id"]
        s, j = call(lead, "POST", f"/subcon/advances/{aid}/decision", {"approve": True, "reason": REASON})
        assert s == 200
        before = bank()
        res = same(3, lambda: call("finance", "POST", f"/subcon/advances/{aid}/pay", {}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        assert before - bank() == 20_000_000
        s, j = call("finance", "GET", "/finance/ap/payments", params={"limit": 500})
        assert len([p for p in j["data"] if p.get("advance_id") == aid]) == 1

    def test_keputusan_uang_muka_paralel_sekali(self):
        lead = ensure_finlead()
        spk = make_spk()
        s, j = call("pm", "POST", "/subcon/advances", {"spk_id": spk["id"], "amount": 10_000_000, "reason": REASON})
        aid = j["data"]["id"]
        res = same(3, lambda: call(lead, "POST", f"/subcon/advances/{aid}/decision", {"approve": True, "reason": REASON}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]

    def test_batas_30_persen_paralel(self):
        spk = make_spk(100_000_000)
        res = same(5, lambda: call("pm", "POST", "/subcon/advances",
                                   {"spk_id": spk["id"], "amount": 10_000_000, "reason": REASON}))
        assert len(ok(res)) == 3, [(r[0], detail(r)) for r in res]    # 3 × 10 jt = tepat 30%

    def test_potongan_uang_muka_tidak_melebihi_sisa(self):
        """PK-10: dua potongan @ sisa uang muka → yang kedua ditolak (sekuensial maupun paralel)."""
        spk = make_spk()
        adv = paid_advance(spk, 20_000_000)
        body = {"spk_id": spk["id"], "kind": "advance", "amount": 20_000_000, "reason": REASON, "advance_id": adv["id"]}
        s, j = call("pm", "POST", "/subcon/deductions", body)
        assert s == 200, (s, j)
        s, j = call("pm", "POST", "/subcon/deductions", body)
        assert s == 400 and "melebihi" in detail((s, j)), (s, j)
        spk2 = make_spk()
        adv2 = paid_advance(spk2, 20_000_000)
        body2 = {**body, "spk_id": spk2["id"], "advance_id": adv2["id"]}
        res = same(3, lambda: call("pm", "POST", "/subcon/deductions", body2))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]

    def test_termin_approve_paralel_satu_tagihan_satu_retensi(self):
        spk = make_spk(100_000_000, 5)
        claim = submitted_claim(spk, 50)
        res = same(3, lambda: call("finance", "POST", f"/subcon/claims/{claim['id']}/approve"))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", f"/subcon/claims/{claim['id']}")
        c = j["data"]
        assert c["status"] == "approved" and c["gross"] == 50_000_000 and c["ap_bill_id"]
        s, j = call("finance", "GET", "/finance/ap/bills", params={"limit": 500})
        mine = [b for b in j["data"] if (b.get("note") or "").startswith(f"Termin {c['claim_number']}")]
        assert len(mine) == 1 and mine[0]["status"] == "approved"
        s, j = call("finance", "GET", "/subcon/retentions", params={"spk_id": spk["id"]})
        assert len(j["data"]) == 1 and j["data"][0]["amount"] == 2_500_000

    def test_release_retensi_paralel_tanpa_client_ref_satu_tagihan(self):
        lead = ensure_finlead()
        spk = make_spk(100_000_000, 5)
        claim = submitted_claim(spk, 50)
        assert call("finance", "POST", f"/subcon/claims/{claim['id']}/approve")[0] == 200
        s, j = call("finance", "GET", "/subcon/retentions", params={"spk_id": spk["id"]})
        ret = j["data"][0]
        blocks = [b["code"] for b in ret["gate"]["blocks"]]
        waivable = [c for c in blocks if c in ("maintenance_active", "punch_open", "warranty_claim_active")]
        if waivable:
            s, j = call(lead, "POST", f"/subcon/retentions/{ret['id']}/waive",
                        {"codes": waivable, "reason": "P0 uji: abaikan penahanan untuk menguji pencairan"})
            assert s == 200, (s, j)
        s, j = call("pm", "POST", f"/subcon/retentions/{ret['id']}/request-release", {"reason": REASON})
        assert s == 200, (s, j)
        res = same(3, lambda: call(lead, "POST", f"/subcon/retentions/{ret['id']}/release", {"reason": "P0 cairkan uji"}))
        assert len(ok(res)) == 1, [(r[0], detail(r)) for r in res]
        s, j = call("finance", "GET", "/finance/ap/bills", params={"limit": 500})
        rel = [b for b in j["data"] if b.get("retention_id") == ret["id"]]
        assert len(rel) == 1 and rel[0]["net"] == 2_500_000
        s, j = call(lead, "POST", f"/subcon/retentions/{ret['id']}/release", {"reason": "P0 cairkan uji"})
        assert s == 400, (s, j)   # sudah dicairkan: pesan biasa

    def test_pm_tidak_boleh_ubah_nilai_kontrak_progres_setelah_termin(self):
        """PK-11."""
        spk = make_spk(100_000_000, 5)
        claim = submitted_claim(spk, 50)
        assert call("finance", "POST", f"/subcon/claims/{claim['id']}/approve")[0] == 200
        s, j = call("pm", "PUT", f"/subcon/spk/{spk['id']}", {"contract_value": 1_000_000_000})
        assert s == 403 and "Change Order" in detail((s, j)), (s, j)
        s, j = call("pm", "PUT", f"/subcon/spk/{spk['id']}", {"progress_pct": 0})
        assert s == 400, (s, j)
        s, j = call("pm", "PUT", f"/subcon/spk/{spk['id']}", {"retention_pct": 0})
        assert s == 403, (s, j)
        s, j = call("pm", "PUT", f"/subcon/spk/{spk['id']}", {"title": "judul baru boleh"})
        assert s == 200, (s, j)
        # nilai kontrak tidak boleh di bawah yang sudah ditagih (juga untuk Keuangan/Owner)
        s, j = call("owner", "PUT", f"/subcon/spk/{spk['id']}", {"contract_value": 10_000_000})
        assert s == 400 and "lebih kecil" in detail((s, j)), (s, j)

    def test_retensi_spk_di_luar_0_100_ditolak(self):
        s, j = call("pm", "GET", "/subcon/subcontractors")
        sub = j["data"][0]["id"]
        for pct in (150, -10):
            s, j = call("pm", "POST", "/subcon/spk", {"subcontractor_id": sub, "project_id": project_id(),
                                                     "title": uniq("P0 SPK"), "contract_value": 1_000_000,
                                                     "retention_pct": pct})
            assert s == 400, (pct, s, j)
        spk = make_spk()
        s, j = call("pm", "PUT", f"/subcon/spk/{spk['id']}", {"retention_pct": 150})
        assert s == 400, (s, j)


# ==== END ====
