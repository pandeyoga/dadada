"""Regresi P0 — PEMBAYARAN KELUAR (lanjutan) (audit PK-01 … PK-15).

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
        """Sakelar Pusat Konfigurasi `cash.allow_negative`: bawaan MATI (ditolak); bila dinyalakan, saldo minus diizinkan."""
        key = "cash.allow_negative"
        s, j = call("owner", "GET", "/settings", params={"q": key})
        row = next((r for r in (j.get("data") or []) if r.get("key") == key), None)
        assert row is not None, "kunci cash.allow_negative tidak terdaftar"
        assert row["value"] is False                                    # bawaan MATI
        acc = accounts()["Kas Kecil Site"]
        amount = max(acc["balance"], 0) + 1_000_000
        b = approved_bill(amount, 0)
        s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": amount, "cash_account_id": acc["id"]})
        assert s == 400 and "tidak cukup" in detail((s, j)), (s, j)
        s, j = call("owner", "PUT", f"/settings/{key}", {"value": True, "reason": "P0 uji sakelar saldo negatif"})
        assert s == 200, (s, j)
        try:
            s, j = call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay",
                        {"amount": amount, "cash_account_id": acc["id"]})
            assert s == 200, (s, j)                                      # sakelar menyala → diizinkan
        finally:
            call("owner", "POST", f"/settings/{key}/reset")
        s, j = call("owner", "GET", "/settings", params={"q": key})
        assert next(r for r in j["data"] if r["key"] == key)["value"] is False


class TestPenyaluranTitipan:
    def test_penyaluran_tanpa_titipan_atau_tanpa_penerima_ditolak(self):
        """Jalur penyaluran titipan biaya (notaris/BPN): validasi tetap bekerja setelah dibungkus kunci + mutex."""
        s, j = call("finance", "GET", "/contracts", params={"limit": 5})
        if s != 200 or not j.get("data"):
            pytest.skip("tidak ada kontrak")
        cid = j["data"][0]["id"]
        s, j = call("finance", "POST", f"/contracts/{cid}/cost-disbursements",
                    {"component_code": "bphtb", "amount": 1_000, "payee": "Notaris Uji"})
        assert s == 400 and "melebihi sisa titipan" in detail((s, j)), (s, j)
        s, j = call("finance", "POST", f"/contracts/{cid}/cost-disbursements",
                    {"component_code": "bphtb", "amount": 0, "payee": "Notaris Uji"})
        assert s == 400, (s, j)
        s, j = call("finance", "POST", f"/contracts/{cid}/cost-disbursements",
                    {"component_code": "bphtb", "amount": 1_000, "payee": "  "})
        assert s == 400 and "Penerima" in detail((s, j)), (s, j)


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
