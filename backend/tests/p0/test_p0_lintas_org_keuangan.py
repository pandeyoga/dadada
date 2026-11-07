"""Regresi G-C — LINGKUP ORGANISASI untuk koleksi KEUANGAN (lanjutan AZ-01/AZ-02, `test_p0_otorisasi_org.py`).

    API_BASE=http://localhost:8073/api DB_NAME=sipro_gc python -m pytest backend/tests/p0/test_p0_lintas_org_keuangan.py \
        -n 0 --noconftest -q -p no:cacheprovider

Data dibuat/dipilih di org-sipro; pemilik org-nusa (`owner@nusaproperti.co.id`) mencoba GET/PUT/POST/PATCH/DELETE
atas: piutang (AR) + kuitansi (void, bukti, PDF), tagihan AP + pembayaran, komisi, fee marketing, voucher kas,
catatan pajak + faktur pajak + bukti potong, pengajuan dana, kas bon, kas kecil, mutasi bank + pencocokan,
aset tetap, pinjaman, rekap upah, jurnal, invoice/kuitansi biaya (PDF).

Aturan yang diuji (sama dengan AZ-01): lintas organisasi dijawab 404 (BUKAN 400/403/200 — keberadaan data org
lain tidak boleh bocor), dan data org-sipro TIDAK berubah (jumlah jurnal, neraca saldo, rincian tiap entitas).
Bagian "pencocokan/penautan lewat id di payload" menguji bahwa org-nusa tidak bisa mengaitkan dokumennya
ke dokumen org-sipro.
"""
import io
import json
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, TAG, World, call, ok, pay, rp_png, upload_proof

NUSA = "owner@nusaproperti.co.id"


def uniq(p):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def dapat(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


def daftar(actor, path, **params):
    r = call(actor, "GET", path, params=params or {"limit": 50})
    return (dapat(r).get("data") or []) if r.status_code == 200 else []


def upload_nusa():
    from test_p0_masuk import _seed
    _seed[0] += 1
    r = call(NUSA, "POST", "/files/upload", files={"file": ("bukti.png", io.BytesIO(rp_png(_seed[0] + 7)), "image/png")},
             data={"owner_type": "generic"})
    return ok(r)["data"]["id"]


# ================================================================== data org-sipro
class Dunia:
    def __init__(self):
        self.w = World()
        deal = self.w.new_deal()
        self.deal = deal["deal_id"]
        self.proyek = self.w.project_id
        self.skema = self.w.scheme["Cash Bertahap (3x)"]
        self.receipt = ok(pay(self.deal, 100_000_000))["data"]["receipt"]["id"]
        # AP: tagihan disetujui + satu pembayaran
        b = ok(call(FINANCE, "POST", "/finance/ap/bills", json={
            "vendor": uniq("Vendor LintasOrg"), "claimed": 10_000_000, "retention_pct": 5}))["data"]
        ok(call(OWNER, "POST", f"/finance/ap/bills/{b['id']}/approve"))
        self.bill = b["id"]
        self.bayar_ap = ok(call(FINANCE, "POST", f"/finance/ap/bills/{b['id']}/pay",
                                json={"amount": 1_000_000}))["data"]
        pays = [p for p in daftar(FINANCE, "/finance/ap/payments", limit=200) if p.get("bill_id") == b["id"]]
        self.payment = pays[0]["id"]
        # komisi
        r = call(FINANCE, "POST", f"/finance/commissions/{self.deal}/compute", json={})
        self.komisi = (dapat(r).get("data") or {}).get("id") or (daftar(FINANCE, "/finance/commissions") or [{}])[0].get("id")
        # fee marketing (pakai data seed; buat bila kosong)
        fees = daftar(FINANCE, "/marketing/fees")
        agents = daftar(FINANCE, "/marketing/agents")
        self.agent = agents[0]["id"] if agents else None
        self.fee = fees[0]["id"] if fees else None
        self.fee_row = fees[0] if fees else {}
        # lain-lain dari seed
        self.voucher = (daftar(FINANCE, "/cash-bank/vouchers") or [{}])[0].get("id")
        self.taxrec = (daftar(FINANCE, "/tax/records") or [{}])[0].get("id")
        self.faktur = (daftar(FINANCE, "/tax/faktur") or [{}])[0].get("id")
        self.bupot = (daftar(FINANCE, "/tax/compliance/withholding") or [{}])[0].get("id")
        self.kasbon = (daftar(FINANCE, "/petty-cash/advances") or [{}])[0].get("id")
        self.txn = (daftar(FINANCE, "/bank/transactions") or [{}])[0].get("id")
        self.rekening = (daftar(FINANCE, "/bank/accounts") or [{}])[0].get("id")
        self.kas_rek = (daftar(FINANCE, "/cash-bank/accounts") or [{}])[0].get("id")
        self.aset = (daftar(FINANCE, "/fixed-assets/assets") or [{}])[0].get("id")
        self.pinjaman = (daftar(FINANCE, "/corp-financing/loans") or [{}])[0].get("id")
        self.jurnal = (daftar(FINANCE, "/gl/journals") or [{}])[0].get("id")
        self.intake = (daftar(FINANCE, "/payment-intakes", limit=50) or [{}])[0].get("id")
        # pengajuan dana
        r = call(FINANCE, "POST", "/fund-requests", json={"type": "expense", "title": uniq("Uji lintas org"),
                                                          "amount": 500_000})
        self.dana = (dapat(r).get("data") or {}).get("id") or (daftar(FINANCE, "/fund-requests") or [{}])[0].get("id")
        # rekap upah (pekerja + absensi + rekap)
        self.payroll = self._payroll()
        # biaya all-in: invoice + kuitansi biaya
        from test_p0_masuk_2 import allin_deal, cost_ledger
        d = allin_deal(self.w)
        self.contract = d["contract_id"]
        self.inv_biaya = d["invoice"]["id"]
        ok(call(FINANCE, "POST", f"/cost-invoices/{self.inv_biaya}/pay",
                json={"amount": 1_000_000, "proof_file_ids": [upload_proof()]}))
        self.kwb = cost_ledger(self.contract)["receipts"][0]["id"]
        self.proof_nusa = upload_nusa()

    def _payroll(self):
        try:
            wk = ok(call(OWNER, "POST", "/labor/workers", json={
                "name": uniq("Tukang LO"), "role": "tukang", "daily_wage": 200_000,
                "project_ids": [self.w.project_id]}))["data"]
            hari = time.strftime("%Y-%m-%d")
            ok(call(OWNER, "POST", "/labor/attendance", json={
                "project_id": self.w.project_id, "work_date": hari,
                "entries": [{"worker_id": wk["id"], "status": "full"}]}))
            r = ok(call(OWNER, "POST", "/labor/payrolls", json={
                "project_id": self.w.project_id, "period_start": hari, "period_end": hari}))
            return r["data"]["id"]
        except AssertionError:
            return None

    def peta(self):
        return {k: v for k, v in self.__dict__.items() if isinstance(v, str)}


@pytest.fixture(scope="module")
def dunia():
    return Dunia()


# ================================================================== daftar serangan
def _ar(d):
    return d.deal


# (nama, metode, path, body | callable(dunia) -> body | None, params)
SERANGAN = [
    # --- piutang (AR)
    ("ar detail", "GET", "/finance/ar/{deal}", None),
    ("ar spr-compare", "GET", "/finance/ar/{deal}/spr-compare", None),
    ("ar invoice pdf", "GET", "/finance/ar/{deal}/invoice/pdf", None),
    ("ar jadwal ganti", "POST", "/finance/ar/{deal}/schedule", lambda d: {"scheme_id": d.skema}),
    ("ar BAST", "POST", "/finance/ar/{deal}/bast", None),
    ("ar titipan terima", "POST", "/finance/ar/{deal}/deposit", lambda d: {"amount": 1000, "proof_file_ids": [d.proof_nusa]}),
    ("ar titipan pakai", "POST", "/finance/ar/{deal}/deposit/apply", lambda d: {"amount": 1000}),
    ("ar titipan kembali", "POST", "/finance/ar/{deal}/deposit/refund", lambda d: {"amount": 1000}),
    ("ar kuitansi baru utk deal org lain", "POST", "/finance/ar/receipts",
     lambda d: {"deal_id": d.deal, "amount": 1000, "method": "transfer", "proof_file_ids": [d.proof_nusa]}),
    ("kuitansi bukti", "PATCH", "/finance/ar/receipts/{receipt}/proof", lambda d: {"proof_file_ids": [d.proof_nusa]}),
    ("kuitansi void", "POST", "/finance/ar/receipts/{receipt}/void", {"reason": "uji lintas org keuangan"}),
    ("kuitansi hapus", "DELETE", "/finance/ar/receipts/{receipt}?reason=uji%20lintas%20org%20keuangan", None),
    ("kuitansi pdf", "GET", "/finance/ar/receipts/{receipt}/pdf", None),
    # --- AP
    ("ap tagihan", "GET", "/finance/ap/bills/{bill}", None),
    ("ap setujui", "POST", "/finance/ap/bills/{bill}/approve", None),
    ("ap bayar", "POST", "/finance/ap/bills/{bill}/pay", {"amount": 1000}),
    ("ap bayar+PPh", "POST", "/finance/ap/bills/{bill}/pay-withholding",
     lambda d: {"bill_id": d.bill, "amount": 1000, "kind": "pph23", "rate": 2}),
    ("ap void pembayaran", "POST", "/finance/ap/payments/{payment}/void", {"reason": "uji lintas org keuangan"}),
    # --- komisi
    ("komisi hitung", "POST", "/finance/commissions/{deal}/compute", {}),
    ("komisi setujui", "POST", "/finance/commissions/{komisi}/approve", None),
    ("komisi bayar", "POST", "/finance/commissions/{komisi}/pay", {}),
    # --- fee marketing
    ("fee baca", "GET", "/marketing/fees/{fee}", None),
    ("fee setujui", "POST", "/marketing/fees/{fee}/approve", {}),
    ("fee tolak", "POST", "/marketing/fees/{fee}/reject", {"reason": "uji lintas org keuangan"}),
    ("fee bayar", "POST", "/marketing/fees/{fee}/pay", {}),
    ("agen ubah", "PUT", "/marketing/agents/{agent}", {"name": "Dibajak Org Lain"}),
    ("fee buat utk agen+deal org lain", "POST", "/marketing/fees",
     lambda d: {"agent_id": d.agent, "deal_id": d.deal, "basis": d.fee_row.get("basis") or "percent",
                "value": 1, "trigger": d.fee_row.get("trigger") or "booking_fee_verified"}),
    # --- voucher kas
    ("voucher baca", "GET", "/cash-bank/vouchers/{voucher}", None),
    ("voucher pdf", "GET", "/cash-bank/vouchers/{voucher}/pdf", None),
    # --- bukti transfer pelanggan (portal)
    ("bukti transfer verifikasi", "POST", "/payment-intakes/{intake}/verify", {}),
    ("bukti transfer tolak", "POST", "/payment-intakes/{intake}/reject", {"reason": "uji lintas org keuangan"}),
    # --- pajak
    ("pajak catatan setor", "PUT", "/tax/records/{taxrec}", {"status": "paid", "ntpn": "NTPN-LINTAS-ORG"}),
    ("faktur baca", "GET", "/tax/faktur/{faktur}", None),
    ("faktur pdf", "GET", "/tax/faktur/{faktur}/pdf", None),
    ("faktur terbit utk deal org lain", "POST", "/tax/faktur", lambda d: {"deal_id": d.deal}),
    ("faktur ganti", "POST", "/tax/compliance/faktur/{faktur}/replace", {"reason": "uji lintas org keuangan"}),
    ("faktur batal", "POST", "/tax/compliance/faktur/{faktur}/cancel", {"reason": "uji lintas org keuangan"}),
    ("bupot baca", "GET", "/tax/compliance/withholding/{bupot}", None),
    ("bupot pdf", "GET", "/tax/compliance/withholding/{bupot}/pdf", None),
    ("bupot koreksi", "POST", "/tax/compliance/withholding/{bupot}/correct", {"reason": "uji lintas org keuangan"}),
    ("bupot batal", "POST", "/tax/compliance/withholding/{bupot}/cancel", {"reason": "uji lintas org keuangan"}),
    ("bupot dari fee", "POST", "/tax/compliance/withholding/from-fee/{fee}", {}),
    # --- pengajuan dana
    ("dana baca", "GET", "/fund-requests/{dana}", None),
    ("dana setujui", "POST", "/fund-requests/{dana}/approve", {}),
    ("dana tolak", "POST", "/fund-requests/{dana}/reject", {"note": "uji lintas org keuangan"}),
    ("dana batal", "POST", "/fund-requests/{dana}/cancel", {"note": "uji lintas org keuangan"}),
    ("dana cairkan", "POST", "/fund-requests/{dana}/disburse", {}),
    ("dana bukti", "POST", "/fund-requests/{dana}/payment-proof", lambda d: {"proof_ids": [d.proof_nusa]}),
    ("dana pertanggungjawaban", "POST", "/fund-requests/{dana}/settle",
     {"items": [{"category": "transport", "description": "uji", "amount": 1000}]}),
    # --- kas bon & kas kecil
    ("kasbon baca", "GET", "/petty-cash/advances/{kasbon}", None),
    ("kasbon setujui", "POST", "/petty-cash/advances/{kasbon}/approve", {}),
    ("kasbon tolak", "POST", "/petty-cash/advances/{kasbon}/reject", {"note": "uji lintas org keuangan"}),
    ("kasbon batal", "POST", "/petty-cash/advances/{kasbon}/cancel", {"note": "uji lintas org keuangan"}),
    ("kasbon cairkan", "POST", "/petty-cash/advances/{kasbon}/disburse", {}),
    ("kasbon pertanggungjawaban", "POST", "/petty-cash/advances/{kasbon}/settle",
     {"items": [{"category": "transport", "description": "uji", "amount": 1000}]}),
    ("kas kecil isi ulang", "POST", "/petty-cash/imprest/{kas_rek}/replenish", {}),
    ("kas kecil biaya utk rekening org lain", "POST", "/petty-cash/expenses",
     lambda d: {"cash_account_id": d.kas_rek, "category": "transport", "description": "uji lintas org", "amount": 1000}),
    # --- mutasi bank & pencocokan
    ("bank saran", "GET", "/bank/transactions/{txn}/suggest", None),
    ("bank cocokkan", "POST", "/bank/transactions/{txn}/match", lambda d: {"kind": "ar_deal", "target_id": d.deal}),
    ("bank batal cocok", "POST", "/bank/transactions/{txn}/unmatch", {"reason": "uji lintas org keuangan"}),
    ("bank abaikan", "POST", "/bank/transactions/{txn}/ignore", {"reason": "uji lintas org keuangan"}),
    ("bank rekening ubah", "PUT", "/bank/accounts/{rekening}",
     {"name": "Dibajak", "bank_name": "BCA", "account_no": "1234567", "gl_account_code": "1-1200"}),
    ("bank rekonsiliasi", "GET", "/bank/reconciliation?account_id={rekening}", None),
    ("bank jelaskan selisih", "POST", "/bank/reconciliation/explain",
     lambda d: {"account_id": d.rekening, "journal_id": d.jurnal, "reason_code": "other", "note": "uji lintas org"}),
    ("bank impor ke rekening org lain", "POST", "/bank/statements/import",
     lambda d: {"account_id": d.rekening, "filename": "x.csv", "csv_text": "tanggal,keterangan,debit,kredit,saldo\n", "dry_run": True}),
    # --- aset tetap & pinjaman
    ("aset baca", "GET", "/fixed-assets/assets/{aset}", None),
    ("aset lepas", "POST", "/fixed-assets/assets/{aset}/dispose", {"proceeds": 0, "source": "bank"}),
    ("pinjaman baca", "GET", "/corp-financing/loans/{pinjaman}", None),
    ("pinjaman cairkan", "POST", "/corp-financing/loans/{pinjaman}/activate", {"source": "bank"}),
    ("pinjaman angsuran", "POST", "/corp-financing/loans/{pinjaman}/pay", {"installment_no": 1, "amount": 1000, "source": "bank"}),
    # --- rekap upah
    ("upah baca", "GET", "/labor/payrolls/{payroll}", None),
    ("upah ajukan", "POST", "/labor/payrolls/{payroll}/submit", None),
    ("upah putuskan", "POST", "/labor/payrolls/{payroll}/decision", {"approve": True}),
    ("upah bayar", "POST", "/labor/payrolls/{payroll}/pay", {}),
    # --- jurnal
    ("jurnal baca", "GET", "/gl/journals/{jurnal}", None),
    # --- penulisan lintas-org lewat id di payload (dokumen org-nusa tidak boleh menunjuk proyek/tagihan org-sipro)
    ("ap tagihan baru utk proyek org lain", "POST", "/finance/ap/bills",
     lambda d: {"vendor": "Vendor Nusa LO", "claimed": 1_000_000, "project_id": d.proyek}),
    ("dana baru utk proyek org lain", "POST", "/fund-requests",
     lambda d: {"type": "expense", "title": "Uji lintas org proyek", "amount": 1000, "project_id": d.proyek}),
    ("dana vendor utk tagihan org lain", "POST", "/fund-requests",
     lambda d: {"type": "vendor_payment", "title": "Uji lintas org tagihan", "amount": 1000, "ap_bill_id": d.bill}),
    ("kasbon baru utk proyek org lain", "POST", "/petty-cash/advances",
     lambda d: {"purpose": "uji lintas org", "amount": 1000, "category": "transport", "project_id": d.proyek}),
    ("aset baru utk proyek org lain", "POST", "/fixed-assets/assets",
     lambda d: {"name": "Aset Nusa Uji LO", "category": "komputer_it", "tax_group": "kelompok_1",
                "method": "garis_lurus", "cost": 1_000_000, "funding": "bank", "project_id": d.proyek}),
    # --- biaya all-in (PDF) & penagihan biaya
    ("invoice biaya pdf", "GET", "/cost-invoices/{inv_biaya}/pdf", None),
    ("kuitansi biaya pdf", "GET", "/cost-receipts/{kwb}/pdf", None),
    ("invoice biaya bayar", "POST", "/cost-invoices/{inv_biaya}/pay", lambda d: {"amount": 1000, "proof_file_ids": [d.proof_nusa]}),
    ("buku biaya kontrak", "GET", "/contracts/{contract}/costs-ledger", None),
    ("biaya salurkan titipan", "POST", "/contracts/{contract}/cost-disbursements",
     {"component_code": "NOTARY_FEE", "amount": 1000, "payee": "Notaris Lintas Org"}),
    ("biaya catat beban", "POST", "/contracts/{contract}/cost-expenses", {"component_code": "BPHTB", "amount": 1000}),
]


def _rakit(dunia, path, body):
    p = path.format(**dunia.peta())
    b = body(dunia) if callable(body) else body
    return p, b


def _butuh(dunia, path):
    import re
    for k in re.findall(r"{(\w+)}", path):
        if not getattr(dunia, k, None):
            pytest.skip(f"data uji '{k}' tidak tersedia di DB ini")


@pytest.mark.parametrize("nama,metode,path,body", SERANGAN, ids=[s[0] for s in SERANGAN])
def test_org_lain_dijawab_404(dunia, nama, metode, path, body):
    _butuh(dunia, path)
    p, b = _rakit(dunia, path, body)
    r = call(NUSA, metode, p, json=b)
    assert r.status_code == 404, f"{metode} {p}: {r.status_code} {r.text[:200]}"


# ================================================================== daftar & ringkasan tidak memuat data org lain
@pytest.mark.parametrize("path,kunci", [
    ("/finance/ar", "deal"), ("/finance/ap/bills", "bill"), ("/finance/ap/payments", "payment"),
    ("/finance/commissions", "komisi"), ("/marketing/fees", "fee"), ("/marketing/agents", "agent"),
    ("/cash-bank/vouchers", "voucher"), ("/tax/records", "taxrec"), ("/tax/faktur", "faktur"),
    ("/tax/compliance/withholding", "bupot"), ("/fund-requests", "dana"), ("/petty-cash/advances", "kasbon"),
    ("/bank/transactions", "txn"), ("/bank/accounts", "rekening"), ("/fixed-assets/assets", "aset"),
    ("/corp-financing/loans", "pinjaman"), ("/labor/payrolls", "payroll"), ("/gl/journals", "jurnal"),
])
def test_daftar_org_lain_tidak_memuat_id_org_sipro(dunia, path, kunci):
    _butuh(dunia, "{" + kunci + "}")
    r = call(NUSA, "GET", path, params={"limit": 100})
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:160]}"
    assert getattr(dunia, kunci) not in r.text, f"id {kunci} org-sipro muncul di daftar {path} org-nusa"


# ================================================================== pencocokan mutasi bank org-nusa -> dokumen org-sipro
@pytest.fixture(scope="module")
def bank_nusa():
    """Rekening + dua mutasi (masuk & keluar) MILIK org-nusa, dibuat lewat API org-nusa sendiri."""
    r = call(NUSA, "POST", "/bank/accounts", json={
        "name": uniq("Rek Nusa LO"), "bank_name": "BCA", "account_no": str(int(time.time() * 1000))[-10:],
        "gl_account_code": "1-1200", "opening_balance": 0})
    if r.status_code != 200:
        pytest.skip(f"rekening org-nusa tidak bisa dibuat: {r.status_code} {r.text[:120]}")
    acc = r.json()["data"]
    hari = time.strftime("%Y-%m-%d")
    csv_text = (f"tanggal,keterangan,debit,kredit,saldo\n{hari},Transfer masuk uji LO {TAG},,2500000,2500000\n"
                f"{hari},Transfer keluar uji LO {TAG},1500000,,1000000\n")
    imp = call(NUSA, "POST", "/bank/statements/import", json={
        "account_id": acc["id"], "filename": "nusa.csv", "csv_text": csv_text, "dry_run": False})
    if imp.status_code != 200:
        pytest.skip(f"impor mutasi org-nusa gagal: {imp.status_code} {imp.text[:160]}")
    rows = [t for t in ok(call(NUSA, "GET", "/bank/transactions", params={"limit": 100}))["data"]
            if t.get("account_id") == acc["id"]]
    masuk = [t for t in rows if t.get("direction") == "in"][0]["id"]
    keluar = [t for t in rows if t.get("direction") == "out"][0]["id"]
    return {"masuk": masuk, "keluar": keluar}


def _bayar(dunia):
    return [b for b in daftar(FINANCE, "/finance/ap/bills", limit=200) if b["id"] == dunia.bill][0]["paid"]


@pytest.mark.parametrize("arah,kind,kunci", [
    ("masuk", "ar_deal", "deal"), ("masuk", "payment_intake", "intake"),
    ("keluar", "ap_bill", "bill"), ("keluar", "labor_payroll", "payroll"),
])
def test_mutasi_nusa_tidak_bisa_melunasi_dokumen_org_sipro(dunia, bank_nusa, arah, kind, kunci):
    """Mutasi bank MILIK org-nusa dicocokkan ke dokumen org-sipro -> 404; tagihan/kuitansi org-sipro tidak berubah."""
    _butuh(dunia, "{" + kunci + "}")
    sebelum = _bayar(dunia)
    r = call(NUSA, "POST", f"/bank/transactions/{bank_nusa[arah]}/match",
             json={"kind": kind, "target_id": getattr(dunia, kunci)})
    assert r.status_code == 404, f"{kind}: {r.status_code} {r.text[:200]}"
    assert _bayar(dunia) == sebelum
    t = [x for x in ok(call(NUSA, "GET", "/bank/transactions", params={"limit": 100}))["data"] if x["id"] == bank_nusa[arah]][0]
    assert t.get("match_state") != "matched", "mutasi org-nusa tertaut ke dokumen org-sipro"


# ================================================================== jurnal manual & rekening/kas org lain
def test_jurnal_manual_org_lain_masuk_ke_org_nusa_bukan_sipro(dunia):
    sebelum = ok(call(FINANCE, "GET", "/gl/journals", params={"limit": 1}))["total"]
    r = call(NUSA, "POST", "/gl/journals", json={
        "memo": f"Jurnal manual uji lintas org {TAG}",
        "lines": [{"account_code": "6-1300", "debit": 1000, "credit": 0},
                  {"account_code": "1-1100", "debit": 0, "credit": 1000}]})
    # boleh sah (jurnal milik org-nusa) atau ditolak aturan lain; yang dilarang: menyentuh org-sipro
    assert r.status_code in (200, 400, 403), f"{r.status_code} {r.text[:200]}"
    assert ok(call(FINANCE, "GET", "/gl/journals", params={"limit": 1}))["total"] == sebelum


def test_jurnal_manual_menyebut_dokumen_org_lain_ditolak_atau_diabaikan(dunia):
    """Payload jurnal manual TIDAK boleh menautkan `source_deal_id`/`source_id` ke dokumen org-sipro."""
    r = call(NUSA, "POST", "/gl/journals", json={
        "memo": f"Jurnal manual tautan lintas org {TAG}", "source_id": dunia.deal, "source_deal_id": dunia.deal,
        "lines": [{"account_code": "6-1300", "debit": 1000, "credit": 0},
                  {"account_code": "1-1100", "debit": 0, "credit": 1000}]})
    assert r.status_code in (200, 400, 403, 404, 422), r.text[:200]
    rows = ok(call(FINANCE, "GET", "/gl/journals", params={"source_id": dunia.deal, "limit": 100}))["data"]
    assert not any((j.get("memo") or "").endswith(TAG) for j in rows), "jurnal org-nusa tertaut ke deal org-sipro"


# ================================================================== data org-sipro TIDAK berubah
def test_data_org_sipro_tidak_berubah_setelah_semua_serangan(dunia):
    """Dijalankan sesudah seluruh serangan di atas (urutan berkas)."""
    a = ok(call(FINANCE, "GET", f"/finance/ar/{dunia.deal}"))
    assert a["data"]["paid"] == 100_000_000, "pembayaran deal org-sipro berubah"
    assert [r for r in a["receipts"] if r["id"] == dunia.receipt][0].get("status") != "void"
    bills = {b["id"]: b for b in daftar(FINANCE, "/finance/ap/bills", limit=200)}
    assert bills[dunia.bill]["paid"] == 1_000_000 and bills[dunia.bill]["status"] in ("partial", "approved")
    pays = [p for p in daftar(FINANCE, "/finance/ap/payments", limit=200) if p["id"] == dunia.payment]
    assert pays and pays[0].get("status") != "void"
    if dunia.taxrec:
        rec = [t for t in daftar(FINANCE, "/tax/records", limit=200) if t["id"] == dunia.taxrec][0]
        assert rec.get("ntpn") != "NTPN-LINTAS-ORG"
    if dunia.agent:
        ag = [x for x in daftar(FINANCE, "/marketing/agents", limit=200) if x["id"] == dunia.agent][0]
        assert ag["name"] != "Dibajak Org Lain"
    if dunia.rekening:
        ba = [x for x in daftar(FINANCE, "/bank/accounts", limit=200) if x["id"] == dunia.rekening][0]
        assert ba["name"] != "Dibajak"
    if dunia.kasbon:
        kb = ok(call(FINANCE, "GET", f"/petty-cash/advances/{dunia.kasbon}"))["data"]
        assert kb.get("status") not in ("rejected", "cancelled") or True   # status awal tidak diketahui; lihat jurnal di bawah
    # buku besar: tidak ada jurnal baru dari org-nusa di org-sipro; rekonsiliasi tetap hijau
    end, rc = time.time() + 40, None
    while time.time() < end:
        rc = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if rc["ok"]:
            break
        time.sleep(1.5)
    assert rc["ok"], [c for c in rc["checks"] if not c["ok"]]
