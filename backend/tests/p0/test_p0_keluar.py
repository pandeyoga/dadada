"""Regresi P0 — PEMBAYARAN KELUAR (audit PK-01 … PK-15).

Tes ini menembak server HIDUP (bukan mock): dua request PARALEL pada dokumen yang sama harus
menghasilkan TEPAT SATU efek uang (subledger + kas/bank + jurnal), alur sekuensial normal tetap
berhasil, dan kasus terlarang (saldo kurang, pemisahan tugas, retensi 150%, ...) ditolak.

Menjalankan (dari folder backend/, server + MongoDB hidup; seed demo sudah berjalan):

    API_BASE=http://localhost:8013/api REACT_APP_BACKEND_URL=http://localhost:8013 \
        python -m pytest -n 0 tests/p0 -v

Berkas: `p0_common.py` (pembantu HTTP/pabrik data), `test_p0_keluar.py` (AP, pengadaan, pengajuan,
kas bon, kas kecil, komisi) dan `test_p0_keluar_lanjutan.py` (fee, titipan, refund, pinjaman, pajak,
aset, upah, subkon). Setiap tes membuat datanya sendiri (awalan `P0-`) dan mengukur SELISIH
(sebelum → sesudah), jadi aman dijalankan berulang pada database yang sama.
"""
from p0_common import *  # noqa: F401,F403
from p0_common import _TOK  # noqa: F401


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
