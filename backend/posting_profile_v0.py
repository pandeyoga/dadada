"""Profil posting VERSI 0 — salinan PERSIS perilaku pembukuan otomatis hari ini sebagai DATA deklaratif.

Rancangan: docs/audit/03_AKUNTANSI_5_KEBUTUHAN_KONFIGURASI.md (§2 kebutuhan, §3 tabel pemetaan awal, §2.8 fase).
Fase 1–2 (berkas ini + `posting_profile.py` + `posting_shadow.py`): katalog, dry-run, dan resolver BAYANGAN.
Profil ini TIDAK dipakai untuk memposting apa pun — jurnal tetap dibentuk kode lama (`gl_engine._gl_*`, dst.);
profil hanya DIBANDINGKAN dengan jurnal yang benar-benar terbit (`posting_shadow`) dan diuji ekuivalen lewat API.

Aturan menulis profil v0 (agar tidak menyalin cacat secara diam-diam):
  * Cacat yang diketahui (GL-xx) TETAP disalin apa adanya — v0 harus sama dengan kode supaya saldo historis
    tidak berubah; perbaikannya adalah profil koreksi (versi 2) di fase berikutnya. Cacat ditandai di `defects`.
  * Peristiwa yang belum diuji ekuivalen berstatus `covered: False` dan TIDAK punya `lines` (tidak ada klaim palsu).
  * Kode akun HANYA ada di tabel peran (`ROLE_TABLE`); baris peristiwa memakai NAMA PERAN. Tabel ditulis sebagai teks
    kolom (bukan literal bertanda kutip per kode) — itu bentuk yang kelak dimigrasi ke koleksi `account_roles`.
  * Ekspresi nilai/kondisi hanya memakai variabel yang dideklarasikan peristiwa (`vars`) + fungsi min/max/abs —
    dievaluasi oleh pengurai AST terbatas (tanpa eval), lihat `posting_profile.py`.
"""

# peran         kode    tipe       label
ROLE_TABLE = """
CASH_DEFAULT          1-1100  asset      Kas (induk; jurnal dialihkan ke kas default / yang dipilih)
BANK_DEFAULT          1-1200  asset      Bank (induk; jurnal dialihkan ke rekening default / yang dipilih)
AR_UNIT               1-1300  asset      Piutang Usaha (termasuk piutang denda)
PDC_ASSET             1-1350  asset      Giro / Cek Belum Cair
INVENTORY             1-1400  asset      Persediaan Material
STAFF_ADVANCE         1-1500  asset      Uang Muka Karyawan (Kas Bon)
WIP                   1-1600  asset      Aset Proyek dalam Penyelesaian (WIP)
RETENTION_RECEIVABLE  1-1700  asset      Piutang Retensi (belum dipakai kode mana pun)
SUBCON_ADVANCE        1-1800  asset      Uang Muka Subkontraktor & Vendor
FIXED_ASSET           1-2100  asset      Aset Tetap
ACCUM_DEPR            1-2200  asset      Akumulasi Penyusutan
AP_TRADE              2-1100  liability  Utang Usaha
RETENTION_PAYABLE     2-1200  liability  Utang Retensi
TAX_PAYABLE           2-1300  liability  Utang Pajak
CONTRACT_LIABILITY    2-1400  liability  Uang Muka Penjualan (Kewajiban Kontrak)
CUSTOMER_DEPOSIT      2-1450  liability  Titipan Pelanggan (Kelebihan Bayar)
REFUND_PAYABLE        2-1460  liability  Utang Refund Pembatalan
CUSTOMER_COST_TRUST   2-1470  liability  Titipan Biaya Customer (BPHTB/Notaris)
PDC_CONTRA            2-1480  liability  Giro Diterima Belum Cair (Kontra)
MKT_FEE_PAYABLE       2-1500  liability  Utang Marketing Fee
COMMISSION_PAYABLE    2-1600  liability  Utang Komisi
COGS_ACCRUAL          2-1700  liability  Utang Biaya Konstruksi Ditaksir (Akrual HPP)
LOAN_PAYABLE          2-2100  liability  Utang Bank / Leasing
PAID_IN_CAPITAL       3-1100  equity     Modal Disetor
RETAINED_EARNINGS     3-1900  equity     Laba Ditahan
OPENING_EQUITY        3-1950  equity     Saldo Awal Kas & Bank
REVENUE_UNIT          4-1100  revenue    Pendapatan Penjualan Unit
REVENUE_OTHER         4-1200  revenue    Pendapatan Lain-lain
GAIN_DISPOSAL         4-1300  revenue    Laba Pelepasan Aset Tetap
REVENUE_PENALTY       4-1400  revenue    Pendapatan Denda Keterlambatan
COGS                  5-1100  expense    Beban Pokok Penjualan
COMMISSION_EXPENSE    6-1100  expense    Beban Komisi
MKT_FEE_EXPENSE       6-1200  expense    Beban Pemasaran
GENERAL_EXPENSE       6-1300  expense    Beban Umum & Administrasi
TAX_EXPENSE           6-1400  expense    Beban Pajak
DEPR_EXPENSE          6-1500  expense    Beban Penyusutan
INTEREST_EXPENSE      6-1600  expense    Beban Bunga, Provisi & Biaya Bank
SALES_COST_EXPENSE    6-1700  expense    Beban Penjualan (Biaya All-in Developer)
LOSS_DISPOSAL         6-1800  expense    Kerugian Pelepasan Aset Tetap
"""

VERSION = "v0"
MODULES = ("Penjualan & Piutang", "Pembatalan", "Utang Usaha (AP)", "Komisi & Marketing Fee", "Pajak",
           "Kas Bon & Dana", "Aset Tetap & Pembiayaan", "Kas & Bank", "All-in & Giro", "Tutup Buku & Manual")


# ----------------------------------------------------------------------------------- pembangun ringkas
def I(label, default=0, required=False):   # noqa: E743 — variabel bilangan bulat Rupiah
    return {"type": "int", "label": label, "default": default, "required": required}


def S(label, default=None, choices=None):
    return {"type": "str", "label": label, "default": default, "choices": choices}


def L(side, account, amount, when=None, memo=None):
    """Satu baris profil: side D/K; account `role:NAMA` atau `cash` (rekening kas/bank menurut konteks)."""
    return {"side": side, "account": account, "amount": amount, "when": when, "memo": memo}


def E(key, label, module, trigger, *, sources, covered=False, vars=None, let=None, cash_rule=None, lines=None,
      derive=None, defects=(), evidence=None, why_not=None, note=None):
    return {"key": key, "label": label, "module": module, "trigger": trigger, "sources": sources,
            "covered": covered, "vars": vars or {}, "let": let or {}, "cash_rule": cash_rule,
            "lines": lines, "derive": derive or {}, "defects": list(defects), "evidence": evidence,
            "why_not": why_not, "note": note}


BANK = {"fixed": "bank"}
SPLIT_VARS = {"split_ar": I("Bagian ke piutang pasca-BAST (split.ar)"),
              "split_penalty": I("Bagian pelunasan denda (split.penalty)")}
# Rumus kolektif penerimaan pembeli: bagian piutang = ar + denda; sisanya (termasuk selisih bulat) = kewajiban kontrak.
SPLIT_LET = {"ar": "split_ar + split_penalty"}
T = "tests/p0/test_p0_posting_profile.py"


def _uncovered(key, label, module, trigger, sources, why, defects=()):
    return E(key, label, module, trigger, sources=sources, covered=False, why_not=why, defects=defects)


EVENTS = [
    # ====================================================================== Penjualan & Piutang
    E("sales.receipt", "Penerimaan pembayaran pembeli (DP/termin/pelunasan/KPR/denda)", MODULES[0],
      "finance_engine.apply_receipt → event payment.received → gl_engine._gl_payment_received",
      sources=[["receipt", "ev:"]], covered=True,
      vars={"amount": I("Nilai diterima (Rp)", required=True), **SPLIT_VARS,
            "method": S("Metode bayar (cash/tunai → kas; lainnya → bank)", "bank"),
            "cash_account_id": S("Rekening/kas tujuan (kosong = default jenis)")},
      let=SPLIT_LET, cash_rule={"var": "method", "cash_values": ["cash", "tunai"]},
      lines=[L("D", "cash", "amount"), L("K", "role:CONTRACT_LIABILITY", "amount - ar"),
             L("K", "role:AR_UNIT", "ar")],
      derive={"amount": "D_CASH + D_BANK", "split_ar": "K_AR_UNIT", "split_penalty": "0"},
      defects=["GL-01", "GL-02"], evidence=T,
      note="Pasca-BAST penerimaan dikredit ke piutang (split.ar) sebelum BAST ke kewajiban kontrak — keputusan sudah "
           "diambil kode (Fase 47/GL-01), bukan hasil profil."),
    E("sales.deposit_in", "Titipan pelanggan diterima (kelebihan bayar / titipan bebas / booking fee)", MODULES[0],
      "finance_engine._deposit_move → event deposit.received → gl_engine._gl_deposit_received",
      sources=[["deposit", "ev:"]], covered=True,
      vars={"amount": I("Nilai titipan (Rp)", required=True), "cash_account_id": S("Rekening/kas tujuan")},
      cash_rule=BANK, lines=[L("D", "cash", "amount"), L("K", "role:CUSTOMER_DEPOSIT", "amount")],
      derive={"amount": "K_CUSTOMER_DEPOSIT"}, defects=["GL-17"], evidence=T,
      note="Tanpa rekening dipilih, titipan masuk ke BANK default walau tunai (GL-17) — disalin apa adanya."),
    E("sales.deposit_apply", "Titipan dipakai untuk termin", MODULES[0],
      "finance_engine.apply_deposit → event deposit.applied → gl_engine._gl_deposit_applied",
      sources=[["deposit", "ev:"]], covered=True,
      vars={"amount": I("Nilai titipan dipakai (Rp)", required=True), **SPLIT_VARS}, let=SPLIT_LET,
      lines=[L("D", "role:CUSTOMER_DEPOSIT", "amount"), L("K", "role:CONTRACT_LIABILITY", "amount - ar"),
             L("K", "role:AR_UNIT", "ar")],
      derive={"amount": "D_CUSTOMER_DEPOSIT", "split_ar": "K_AR_UNIT", "split_penalty": "0"},
      defects=["GL-01"], evidence=T),
    E("sales.deposit_refund", "Titipan pelanggan dikembalikan", MODULES[0],
      "finance_engine.refund_deposit → event deposit.refunded → gl_engine._gl_deposit_refunded",
      sources=[["deposit", "ev:"]], covered=True,
      vars={"amount": I("Nilai refund titipan (Rp)", required=True), "cash_account_id": S("Rekening/kas sumber")},
      cash_rule=BANK, lines=[L("D", "role:CUSTOMER_DEPOSIT", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_CUSTOMER_DEPOSIT"}, defects=["GL-17"], evidence=T),
    E("sales.revrec", "Pengakuan pendapatan + HPP (BAST)", MODULES[0],
      "ar_router.bast → finance_engine.recognize_revenue → event revenue.recognized → gl_engine._gl_revenue_recognized",
      sources=[["revrec", "ev:"]], covered=True,
      vars={"revenue": I("Pendapatan diakui (Rp)", required=True), "cogs": I("HPP (Rp)"),
            "cleared": I("Kewajiban kontrak yang dibersihkan (Rp)"),
            "wip_balance": I("Saldo WIP org sebelum jurnal (Rp) — menentukan porsi 1-1600 vs akrual 2-1700")},
      let={"ar_part": "max(0, revenue - cleared)", "wip_used": "min(cogs, max(0, wip_balance))"},
      lines=[L("D", "role:CONTRACT_LIABILITY", "cleared"), L("D", "role:AR_UNIT", "ar_part"),
             L("K", "role:REVENUE_UNIT", "revenue"), L("K", "role:CUSTOMER_DEPOSIT", "max(0, cleared - revenue)"),
             L("D", "role:COGS", "cogs"), L("K", "role:WIP", "wip_used"), L("K", "role:COGS_ACCRUAL", "cogs - wip_used")],
      derive={"revenue": "K_REVENUE_UNIT", "cogs": "D_COGS", "cleared": "D_CONTRACT_LIABILITY",
              "wip_balance": "K_WIP"},
      defects=["GL-02", "GL-07", "GL-11"], evidence=T,
      note="WIP dihitung satu-org (bukan per proyek/unit) seperti kode hari ini (GL-11)."),
    E("sales.late_fee", "Denda keterlambatan ditagihkan", MODULES[0],
      "late_fee_engine.apply → gl.post_journal(source_type=late_fee)", sources=[["late_fee", "late_fee:"]],
      covered=True, vars={"amount": I("Denda ditagihkan (Rp)", required=True)},
      lines=[L("D", "role:AR_UNIT", "amount"), L("K", "role:REVENUE_PENALTY", "amount")],
      derive={"amount": "D_AR_UNIT"}, evidence=T),
    E("sales.late_fee_waive", "Keringanan denda (membalik jurnal denda)", MODULES[0],
      "late_fee_engine.waive → gl.post_journal(source_type=late_fee_waiver)",
      sources=[["late_fee_waiver", "late_fee_waive:"]], covered=True,
      vars={"amount": I("Denda diringankan (Rp)", required=True)},
      lines=[L("D", "role:REVENUE_PENALTY", "amount"), L("K", "role:AR_UNIT", "amount")],
      derive={"amount": "K_AR_UNIT"}, evidence=T),
    E("sales.receipt_void", "Pembatalan penerimaan (void kuitansi / revert pencocokan bank)", MODULES[0],
      "bank_match.void_receipt → gl.post_journal(source_type=receipt_void)",
      sources=[["receipt_void", "receipt.void:"]], covered=True,
      vars={"amount": I("Nilai penerimaan dibalik (Rp)", required=True), **SPLIT_VARS,
            "cash_account_id": S("Rekening/kas kuitansi asal")},
      let=SPLIT_LET, cash_rule=BANK,
      lines=[L("D", "role:CONTRACT_LIABILITY", "amount - ar"), L("D", "role:AR_UNIT", "ar"),
             L("K", "cash", "amount")],
      derive={"amount": "K_CASH + K_BANK", "split_ar": "D_AR_UNIT", "split_penalty": "0"},
      defects=["GL-01"], evidence=T),
    _uncovered("sales.booking_forfeit", "Booking fee hangus", MODULES[0], "booking_fee.forfeit",
               [["booking_fee_forfeit", "bf:"]], "belum ada skenario API ekuivalensi (Dr 2-1450 / Cr 4-1200)"),
    # ====================================================================== Pembatalan
    E("cancel.decision", "Keputusan pembatalan kontrak (kewajiban ke pembeli diselesaikan)", MODULES[1],
      "cancellation_engine._post_decision_journal", sources=[["cancellation", "cancel:"]], covered=True,
      vars={"received_total": I("Total uang muka diterima (Rp)"), "deposit_balance": I("Saldo titipan (Rp)"),
            "cut_amount": I("Potongan pembatalan (Rp)"), "payable_total": I("Utang refund (Rp)")},
      lines=[L("D", "role:CONTRACT_LIABILITY", "received_total"), L("D", "role:CUSTOMER_DEPOSIT", "deposit_balance"),
             L("K", "role:REVENUE_OTHER", "cut_amount"), L("K", "role:REFUND_PAYABLE", "payable_total")],
      derive={"received_total": "D_CONTRACT_LIABILITY", "deposit_balance": "D_CUSTOMER_DEPOSIT",
              "cut_amount": "K_REVENUE_OTHER", "payable_total": "K_REFUND_PAYABLE"},
      defects=["GL-23"], evidence=T,
      note="Komisi/fee/pajak atas deal batal tidak dibalik (GL-23) — perlakuan akuntansinya menunggu keputusan pemilik."),
    E("cancel.refund_pay", "Pembayaran refund pembatalan", MODULES[1],
      "cancellation_engine.pay_refund", sources=[["cancellation_refund", "cancel:"]], covered=True,
      vars={"amount": I("Nilai refund dibayar (Rp)", required=True),
            "method": S("Metode (tunai → kas; lainnya → bank)", "transfer"),
            "cash_account_id": S("Rekening/kas sumber")},
      cash_rule={"var": "method", "cash_values": ["tunai"]},
      lines=[L("D", "role:REFUND_PAYABLE", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_REFUND_PAYABLE"}, evidence=T),
    # W1-C (docs/audit/12 #11/#12): jurnal koreksi/penyelesaian deal batal. Belum diuji ekuivalen dengan profil → tidak `covered`
    # (tercatat di katalog supaya pagar anti-drift `source_type` tetap utuh).
    _uncovered("cancel.cost_settlement", "Titipan biaya deal batal → utang refund (± hangus ke pendapatan lain-lain)", MODULES[1],
               "cancel_cost_settlement.execute", [["cost_settlement", "costsettle:"]],
               "kebijakan terkonfigurasi baru (W1-C #12); belum ada skenario ekuivalensi profil (Dr 2-1470 / Cr 2-1460 [+ Cr 4-1200])"),
    _uncovered("cancel.cost_settlement_refund", "Pembayaran refund titipan biaya deal batal", MODULES[1],
               "cancel_cost_settlement.pay_refund", [["cost_settlement_refund", "costsettle:"]],
               "kebijakan terkonfigurasi baru (W1-C #12); belum ada skenario ekuivalensi profil (Dr 2-1460 / Cr kas|bank)"),
    _uncovered("commission.reverse", "Pembalikan akrual komisi pada deal batal", MODULES[3],
               "cancel_accrual_reversal.reverse_commissions", [["commission_reversal", "cancel.reverse:commission:"]],
               "kebijakan terkonfigurasi baru (W1-C #11); jurnal = cermin jurnal akrual asli (Dr utang komisi / Cr beban komisi)"),
    _uncovered("mktfee.reverse", "Pembalikan akrual marketing fee pada deal batal", MODULES[3],
               "cancel_accrual_reversal.reverse_fees", [["marketing_fee_reversal", "cancel.reverse:mfee:"]],
               "kebijakan terkonfigurasi baru (W1-C #11); jurnal = cermin jurnal akrual asli (Dr utang fee [+ Dr utang pajak] / Cr beban pemasaran)"),
    # ====================================================================== Utang Usaha (AP)
    E("ap.approve", "Tagihan AP disetujui (± retensi, ± potongan termin)", MODULES[2],
      "finance_ap.approve_ap_bill → event ap.approved → gl_engine._gl_ap_approved",
      sources=[["ap_bill", "ev:"]], covered=True,
      vars={"claimed": I("Nilai klaim (Rp)", required=True), "net": I("Neto utang usaha (Rp)", required=True),
            "retention": I("Retensi ditahan (Rp)"),
            "po_type": S("Tipe PO (material/general/subcon; kosong/lain = WIP)"),
            "accrual_balance": I("Saldo akrual HPP 2-1700 sebelum jurnal (Rp)"),
            "ded_advance": I("Potongan: angsuran uang muka (Rp)"), "ded_material": I("Potongan: bon material (Rp)"),
            "ded_penalty": I("Potongan: denda (Rp)"), "ded_other": I("Potongan: lainnya/jenis tak dikenal (Rp)")},
      let={"accrual_cleared": "min(claimed, max(0, accrual_balance))"},
      lines=[L("D", "role:INVENTORY", "claimed", when="po_type == 'material'"),
             L("D", "role:GENERAL_EXPENSE", "claimed", when="po_type == 'general'"),
             L("D", "role:COGS_ACCRUAL", "accrual_cleared", when="po_type not in ['material', 'general']"),
             L("D", "role:WIP", "claimed - accrual_cleared", when="po_type not in ['material', 'general']"),
             L("K", "role:AP_TRADE", "net"), L("K", "role:RETENTION_PAYABLE", "retention"),
             L("K", "role:SUBCON_ADVANCE", "ded_advance"), L("K", "role:INVENTORY", "ded_material"),
             L("K", "role:REVENUE_OTHER", "ded_penalty + ded_other")],
      derive={"claimed": "D_INVENTORY + D_GENERAL_EXPENSE + D_COGS_ACCRUAL + D_WIP", "net": "K_AP_TRADE",
              "retention": "K_RETENTION_PAYABLE", "accrual_balance": "D_COGS_ACCRUAL",
              "po_type": "'material' if D_INVENTORY > 0 else ('general' if D_GENERAL_EXPENSE > 0 else 'subcon')",
              "ded_advance": "K_SUBCON_ADVANCE", "ded_material": "K_INVENTORY", "ded_penalty": "0",
              "ded_other": "K_REVENUE_OTHER"},
      defects=["GL-11", "GL-12"], evidence=T,
      note="Potongan 'penalty' dan 'other' sama-sama ke pendapatan lain (4-1200) — disalin dari DEDUCTION_GL."),
    E("ap.pay", "Pembayaran tagihan AP (± potong PPh)", MODULES[2],
      "finance_ap.pay_ap_bill → event ap.paid → gl_engine._gl_ap_paid", sources=[["ap_bill", "ev:"]], covered=True,
      vars={"amount": I("Nilai dilunasi bruto (Rp)", required=True), "withheld": I("PPh dipotong (Rp)"),
            "cash_account_id": S("Rekening/kas sumber")},
      cash_rule=BANK,
      lines=[L("D", "role:AP_TRADE", "amount"), L("K", "cash", "amount - withheld"),
             L("K", "role:TAX_PAYABLE", "withheld")],
      derive={"amount": "D_AP_TRADE", "withheld": "K_TAX_PAYABLE"}, defects=["GL-18"], evidence=T),
    E("ap.pay_void", "Pembatalan pembayaran AP", MODULES[2], "ap_void.void_payment",
      sources=[["ap_payment_void", "ap.void:"]], covered=True,
      vars={"amount": I("Nilai pembayaran dibalik bruto (Rp)", required=True), "withheld": I("PPh dibalik (Rp)"),
            "cash_account_id": S("Rekening/kas pembayaran asal")},
      cash_rule=BANK,
      lines=[L("D", "cash", "amount - withheld"), L("K", "role:AP_TRADE", "amount"),
             L("D", "role:TAX_PAYABLE", "withheld")],
      derive={"amount": "K_AP_TRADE", "withheld": "D_TAX_PAYABLE"}, evidence=T),
    _uncovered("subcon.advance_pay", "Uang muka subkon dibayar", MODULES[2], "subcon_finance.pay_advance",
               [["subcon_advance", "subcon_advance_paid:"]], "belum ada skenario API ekuivalensi (alur SPK panjang)"),
    _uncovered("subcon.retention_release", "Pencairan retensi subkon", MODULES[2], "subcon_finance.release",
               [["subcon_retention", "retention_released:"]],
               "belum ada skenario API ekuivalensi (butuh SPK + termin + gerbang retensi)"),
    # ====================================================================== Komisi & Marketing Fee
    E("commission.approve", "Komisi disetujui (akrual)", MODULES[3],
      "finance_commission.approve_commission → event commission.approved → gl_engine._gl_commission_approved",
      sources=[["commission", "ev:"]], covered=True,
      vars={"amount": I("Nilai komisi (Rp)", required=True)},
      lines=[L("D", "role:COMMISSION_EXPENSE", "amount"), L("K", "role:COMMISSION_PAYABLE", "amount")],
      derive={"amount": "D_COMMISSION_EXPENSE"}, evidence=T,
      note="Kapitalisasi komisi (PSAK 72) belum diputuskan pemilik; v0 tetap beban langsung."),
    E("commission.pay", "Pembayaran komisi", MODULES[3],
      "finance_commission.pay_commission → event commission.paid → gl_engine._gl_commission_paid",
      sources=[["commission", "ev:"]], covered=True,
      vars={"amount": I("Nilai dibayar (Rp)", required=True), "cash_account_id": S("Rekening/kas sumber")},
      cash_rule=BANK, lines=[L("D", "role:COMMISSION_PAYABLE", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_COMMISSION_PAYABLE"}, evidence=T),
    E("mktfee.approve", "Marketing fee disetujui (akrual, ± PPh)", MODULES[3], "marketing_fee.approve_fee",
      sources=[["marketing_fee", "mfee.approve:"]], covered=True,
      vars={"gross": I("Fee bruto (Rp)", required=True), "net": I("Fee neto (Rp)", required=True),
            "pph": I("PPh dipotong (Rp)")},
      lines=[L("D", "role:MKT_FEE_EXPENSE", "gross"), L("K", "role:MKT_FEE_PAYABLE", "net"),
             L("K", "role:TAX_PAYABLE", "pph")],
      derive={"gross": "D_MKT_FEE_EXPENSE", "net": "K_MKT_FEE_PAYABLE", "pph": "K_TAX_PAYABLE"}, evidence=T),
    E("mktfee.pay", "Pembayaran marketing fee", MODULES[3], "marketing_fee.pay_fee",
      sources=[["marketing_fee_payment", "mfee.pay:"]], covered=True,
      vars={"amount": I("Nilai dibayar (Rp)", required=True), "source": S("Sumber (kas/bank)", "bank"),
            "cash_account_id": S("Rekening/kas sumber")},
      cash_rule={"var": "source", "cash_values": ["kas"]},
      lines=[L("D", "role:MKT_FEE_PAYABLE", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_MKT_FEE_PAYABLE"}, evidence=T),
    # ====================================================================== Pajak
    E("tax.accrue", "Akrual pajak (saat dilaporkan/disetor)", MODULES[4],
      "gl_engine.post_tax_accrual (dari tax_router)", sources=[["tax_accrual", "tax.accrue:"]], covered=True,
      vars={"amount": I("Nilai pajak (Rp)", required=True)},
      lines=[L("D", "role:TAX_EXPENSE", "amount"), L("K", "role:TAX_PAYABLE", "amount")],
      derive={"amount": "D_TAX_EXPENSE"}, defects=["GL-04"], evidence=T,
      note="SEMUA jenis pajak (PPN/PPh final/BPHTB) ke beban pajak — PPN keluaran belum dipisah (GL-04)."),
    E("tax.deposit", "Setoran pajak", MODULES[4], "gl_engine.post_tax_payment (dari tax_router)",
      sources=[["tax_setor", "tax.setor:"]], covered=True,
      vars={"amount": I("Nilai setoran (Rp)", required=True), "cash_account_id": S("Rekening/kas sumber")},
      cash_rule=BANK, lines=[L("D", "role:TAX_PAYABLE", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_TAX_PAYABLE"}, evidence=T),
    # ====================================================================== Kas Bon & Dana
    E("staff.advance_disburse", "Kas bon dicairkan", MODULES[5], "petty_cash.disburse_advance",
      sources=[["cash_advance", "cashbon.disburse:"]], covered=True,
      vars={"amount": I("Nilai dicairkan (Rp)", required=True), "source": S("Sumber (kas/bank)", "bank"),
            "cash_account_id": S("Rekening/kas sumber")},
      cash_rule={"var": "source", "cash_values": ["kas"]},
      lines=[L("D", "role:STAFF_ADVANCE", "amount"), L("K", "cash", "amount")],
      derive={"amount": "D_STAFF_ADVANCE"}, defects=["GL-16"], evidence=T),
    E("staff.advance_settle", "Kas bon dipertanggungjawabkan", MODULES[5], "petty_cash.settle_advance",
      sources=[["cash_advance", "cashbon.settle:"]], covered=True,
      vars={"disbursed": I("Nominal kas bon dicairkan (Rp)", required=True),
            "exp_general": I("Realisasi kategori beban umum (Rp) — transport/konsumsi/ATK/izin/perbaikan/lainnya"),
            "exp_wip": I("Realisasi kategori biaya proyek/upah harian → WIP (Rp)"),
            "exp_marketing": I("Realisasi kategori pemasaran/promosi (Rp)"),
            "source": S("Sumber kas bon (kas/bank)", "bank"), "cash_account_id": S("Rekening/kas kas bon")},
      let={"total": "exp_general + exp_wip + exp_marketing", "returned": "max(0, disbursed - total)",
           "reimburse": "max(0, total - disbursed)"},
      cash_rule={"var": "source", "cash_values": ["kas"]},
      lines=[L("D", "role:GENERAL_EXPENSE", "exp_general"), L("D", "role:WIP", "exp_wip"),
             L("D", "role:MKT_FEE_EXPENSE", "exp_marketing"), L("D", "cash", "returned"),
             L("K", "role:STAFF_ADVANCE", "disbursed"), L("K", "cash", "reimburse")],
      derive={"disbursed": "K_STAFF_ADVANCE", "exp_general": "D_GENERAL_EXPENSE", "exp_wip": "D_WIP",
              "exp_marketing": "D_MKT_FEE_EXPENSE"},
      defects=["GL-11", "GL-16"], evidence=T,
      note="Kategori → kelas akun (reference_p27.CASHBON_ACCOUNT): biaya_proyek & upah_harian → WIP; "
           "pemasaran_promosi → beban pemasaran; sisanya (termasuk kategori tak dikenal) → beban umum."),
    _uncovered("fund.disburse", "Pengajuan dana dicairkan (kas bon / beban kategori)", MODULES[5],
               "fund_requests.disburse", [["fund_request", "fund_request.disburse:"]],
               "belum ada skenario API ekuivalensi (jalur AP + non-AP bercabang)"),
    _uncovered("fund.settle", "Pengajuan dana (kas bon) dipertanggungjawabkan", MODULES[5], "fund_requests.settle",
               [["fund_request", "fund_request.settle:"]], "belum ada skenario API ekuivalensi"),
    _uncovered("petty.expense", "Kas kecil: pengeluaran", MODULES[5], "petty_expense.record",
               [["petty_expense", "petty.expense:"]], "belum ada skenario API; akun beban diambil dari dokumen"),
    _uncovered("petty.void", "Kas kecil: pembatalan pengeluaran", MODULES[5], "petty_expense.void",
               [["petty_expense", "petty.expense.void:"]], "belum ada skenario API"),
    _uncovered("labor.pay", "Upah harian dibayar", MODULES[5], "labor_engine.pay_payroll",
               [["labor_payroll", "labor.paid:"]], "belum ada skenario API (alur absensi panjang)"),
    # ====================================================================== Aset Tetap & Pembiayaan
    E("fixed_asset.acquire", "Perolehan aset tetap", MODULES[6], "fixed_assets._create_asset_locked",
      sources=[["fixed_asset", "asset.acquire:"]], covered=True,
      vars={"cost": I("Harga perolehan (Rp)", required=True),
            "funding": S("Pendanaan (kas/bank/utang_usaha)", "bank", ["kas", "bank", "utang_usaha"])},
      cash_rule={"var": "funding", "cash_values": ["kas"]},
      lines=[L("D", "role:FIXED_ASSET", "cost"),
             L("K", "cash", "cost", when="funding != 'utang_usaha'"),
             L("K", "role:AP_TRADE", "cost", when="funding == 'utang_usaha'")],
      derive={"cost": "D_FIXED_ASSET", "funding": "'utang_usaha' if K_AP_TRADE > 0 else ('kas' if K_CASH > 0 else 'bank')"},
      defects=["GL-24"], evidence=T,
      note="Semua kategori (termasuk tanah) ke satu akun aset tetap (GL-24)."),
    E("fixed_asset.depreciate", "Penyusutan bulanan", MODULES[6], "fixed_assets.run_depreciation",
      sources=[["asset_depreciation", "asset.depr:"]], covered=True,
      vars={"amount": I("Beban penyusutan periode (Rp)", required=True)},
      lines=[L("D", "role:DEPR_EXPENSE", "amount"), L("K", "role:ACCUM_DEPR", "amount")],
      derive={"amount": "D_DEPR_EXPENSE"}, defects=["GL-24"], evidence=T),
    E("fixed_asset.dispose", "Pelepasan aset tetap", MODULES[6], "fixed_assets.dispose_asset",
      sources=[["fixed_asset", "asset.dispose:"]], covered=True,
      vars={"cost": I("Harga perolehan (Rp)", required=True), "accum": I("Akumulasi penyusutan (Rp)"),
            "proceeds": I("Hasil pelepasan (Rp)"), "source": S("Sumber/tujuan kas (kas/bank)", "bank"),
            "cash_account_id": S("Rekening/kas penerima")},
      let={"gain": "proceeds - (cost - accum)"}, cash_rule={"var": "source", "cash_values": ["kas"]},
      lines=[L("D", "cash", "proceeds"), L("D", "role:ACCUM_DEPR", "accum"),
             L("D", "role:LOSS_DISPOSAL", "max(0, 0 - gain)"), L("K", "role:FIXED_ASSET", "cost"),
             L("K", "role:GAIN_DISPOSAL", "max(0, gain)")],
      derive={"cost": "K_FIXED_ASSET", "accum": "D_ACCUM_DEPR", "proceeds": "D_CASH + D_BANK"}, evidence=T),
    _uncovered("loan.disburse", "Pinjaman/pembiayaan dicairkan", MODULES[6], "loans.activate",
               [["loan", "loan.activate:"]], "belum ada skenario API ekuivalensi", ["GL-24"]),
    _uncovered("loan.installment", "Angsuran pinjaman", MODULES[6], "loans.pay_installment",
               [["loan_payment", "loan.pay:"]], "belum ada skenario API ekuivalensi", ["GL-24"]),
    # ====================================================================== Kas & Bank
    _uncovered("cash.transfer", "Transfer internal kas/bank (± biaya)", MODULES[7], "cash_bank.approve_transfer",
               [["cash_transfer", "cashbank.transfer:"]], "dua sisi kas dengan jenis berbeda; belum dimodelkan"),
    _uncovered("cash.opening", "Saldo awal rekening/kas", MODULES[7], "cash_bank._post_opening",
               [["cash_opening", "cashbank.opening:"]], "belum ada skenario API ekuivalensi"),
    _uncovered("bank.fee", "Biaya bank (rekonsiliasi)", MODULES[7], "bank_match (biaya bank)",
               [["bank_txn", "bank.fee:"]], "belum ada skenario API ekuivalensi"),
    _uncovered("bank.interest", "Jasa giro (rekonsiliasi)", MODULES[7], "bank_match (jasa giro)",
               [["bank_txn", "bank.interest:"]], "belum ada skenario API ekuivalensi"),
    _uncovered("bank.unmatch", "Pembalikan pencocokan bank (non-AR)", MODULES[7], "bank_match.unmatch",
               [["bank_txn_void", "bank.unmatch:"]], "jurnal cermin dari jurnal asal; bukan pemetaan tetap"),
    # ====================================================================== All-in & Giro
    _uncovered("allin.booking_to_cost_trust", "Booking fee dialihkan ke titipan biaya", MODULES[8],
               "allin_engine (cost_receipt)", [["cost_receipt", "cost_receipt:"]],
               "milik stream lain (allin_engine); akun kredit dari data komponen", ["GL-19"]),
    _uncovered("allin.cost_receipt", "Titipan biaya pembeli diterima", MODULES[8], "allin_engine.pay_cost_invoice",
               [["cost_receipt", "cost_receipt:"]], "milik stream lain (allin_engine)", ["GL-19"]),
    _uncovered("allin.cost_disburse", "Titipan biaya disalurkan", MODULES[8], "allin_engine (cost_disbursement)",
               [["cost_disbursement", "cost_disb:"]], "milik stream lain (allin_engine)", ["GL-19"]),
    _uncovered("allin.dev_expense", "Beban all-in ditanggung developer", MODULES[8], "allin_engine (ap.sales_cost)",
               [["ap_bill", "ap.sales_cost:"]], "milik stream lain; akun beban/AP dari data komponen", ["GL-19"]),
    _uncovered("pdc.receive", "Giro diterima", MODULES[8], "pdc_engine.receive", [["pdc", "pdc.receive:"]],
               "belum ada skenario API ekuivalensi", ["GL-26"]),
    _uncovered("pdc.reverse", "Giro kliring/tolak/batal (jurnal balik kontra)", MODULES[8], "pdc_engine._reverse_pair",
               [["pdc", "pdc."]], "belum ada skenario API ekuivalensi"),
    _uncovered("pdc.clear_no_deal", "Giro cair tanpa deal (rekening bank pilihan ← titipan)", MODULES[8],
               "pdc_engine.clear (tanpa deal)", [["pdc", "pdc.clear.cash:"]], "belum ada skenario API ekuivalensi"),
    # ====================================================================== Tutup Buku & Manual
    _uncovered("year.close", "Jurnal penutup tahun buku", MODULES[9], "closing_engine.close_year",
               [["year_closing", "year_close:"]], "jumlah baris dinamis (satu per akun pendapatan/beban)", ["GL-03"]),
    _uncovered("year.reopen", "Jurnal balik tahun buku", MODULES[9], "closing_engine.reopen_year",
               [["year_closing", "year_reopen:"]], "jumlah baris dinamis (cermin jurnal penutup)", ["GL-03"]),
    _uncovered("manual", "Jurnal manual", MODULES[9], "routers.gl_router.create_journal", [["manual", None]],
               "bebas oleh definisi — tidak ada pemetaan peristiwa → akun", ["GL-21"]),
]
