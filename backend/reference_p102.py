"""Kosakata Fase 102 — pilihan enum kebijakan akuntansi/pembatalan terkonfigurasi (docs/audit/12)."""
from reference_groups import _o

GROUPS_P102 = {
    "deposit_cancelled_deal_policy": {
        "label": "Penerimaan Titipan pada Deal Batal", "strict": True,
        "help": "Setting `deposit.on_cancelled_deal`.",
        "options": [
            _o("bebas", "Boleh bebas (keuangan menangani manual)"),
            _o("wajib_alasan_dan_antrean_refund", "Boleh, alasan wajib + otomatis jadi tugas refund Keuangan"),
            _o("tolak", "Ditolak (catat lewat jalur lain)"),
        ],
    },
    "reservation_expiry_paid_fee_policy": {
        "label": "Reservasi Kedaluwarsa, Booking Fee Sudah Dibayar", "strict": True,
        "help": "Setting `reservation.expiry.paid_booking_fee` (keputusan #13).",
        "options": [
            _o("perpanjang", "Perpanjang reservasi — unit TIDAK dilepas (berbatas, lalu tugas tindak lanjut)"),
            _o("antrean_refund", "Lepas unit + booking fee masuk antrean refund Keuangan"),
            _o("hangus", "Lepas unit + booking fee diakui hangus"),
        ],
    },
    # ---------------- W1-C: deal batal — akrual komisi/fee/pajak (keputusan #11) ----------------
    "cancel_accrual_reversal_mode": {
        "label": "Pembalikan Akrual pada Deal Batal", "strict": True,
        "help": "Settings `cancel.accrual_reversal.commission|marketing_fee|tax`.",
        "options": [
            _o("manual_keuangan", "Manual oleh Keuangan (ditandai + tugas, tanpa jurnal balik)"),
            _o("balik_otomatis_yang_belum_dibayar", "Balik otomatis yang disetujui tapi belum dibayar"),
            _o("balik_otomatis_semua", "Balik otomatis termasuk yang sudah dibayar (tagih balik ke penerima)"),
        ],
    },
    # ---------------- W1-C: deal batal — titipan biaya 2-1470 & invoice biaya terbuka (keputusan #12) ----------------
    "cancel_cost_deposit_policy": {
        "label": "Titipan Biaya pada Deal Batal", "strict": True,
        "help": "Setting `cancel.cost_deposit.policy`.",
        "options": [
            _o("refund_dan_batalkan_invoice", "Refund titipan ke pembeli + batalkan invoice biaya terbuka"),
            _o("manual_dengan_pengakuan", "Manual: pembatalan wajib mengakui titipan/invoice biaya (tanpa jurnal)"),
            _o("hangus_sebagian", "Sebagian titipan hangus (ditahan developer), sisanya direfund"),
        ],
    },
    "cost_settlement_state": {
        "label": "Keadaan Permohonan Refund Titipan Biaya", "strict": True,
        "help": "Permohonan refund titipan biaya & pembatalan invoice biaya pada deal batal (W1-C).",
        "options": [
            _o("diajukan", "Menunggu persetujuan Keuangan"),
            _o("disetujui", "Disetujui — refund belum dibayar"),
            _o("refund_sebagian", "Refund dibayar sebagian"),
            _o("selesai", "Selesai"),
            _o("ditolak", "Ditolak (ditangani manual)"),
        ],
    },
    # ---- W1-B: persetujuan diskon bertingkat, alokasi saat ganti skema, ganti skema ke KPR ----
    "discount_approval_mode": {
        "label": "Mode Persetujuan Diskon", "strict": True,
        "help": "Setting `discount.approval_mode`.",
        "options": [
            _o("satu_level", "Satu level (semua pemegang izin persetujuan harga setara)"),
            _o("bertingkat", "Bertingkat menurut nilai (peran penyetuju ditentukan tabel tingkat)"),
        ],
    },
    "payment_scheme_change_allocation": {
        "label": "Alokasi Pembayaran saat Ganti Skema", "strict": True,
        "help": "Setting `payment.scheme_change.allocation`.",
        "options": [
            _o("manual_keuangan", "Manual oleh Keuangan (Keuangan menyerahkan pemetaan per kuitansi)"),
            _o("urut_termin_tertua", "Urut termin tertua (sistem menghitung, Keuangan mengonfirmasi)"),
            _o("proporsional", "Proporsional terhadap nilai termin (sistem menghitung, Keuangan mengonfirmasi)"),
        ],
    },
    "contract_scheme_change_to_kpr": {
        "label": "Ganti Skema Kontrak ke KPR", "strict": True,
        "help": "Setting `contract.scheme_change_to_kpr`.",
        "options": [
            _o("tolak_buat_baru", "Tolak — batalkan lalu buat kontrak baru berskema KPR"),
            _o("hitung_ulang_dengan_persetujuan", "Hitung ulang komponen KPR + persetujuan Keuangan"),
            _o("izinkan_manual", "Izinkan (perilaku lama, komponen KPR diurus manual)"),
        ],
    },
}


# ===== W2-A — kosakata PPN terkonfigurasi (keputusan #1) =====
GROUPS_P102["ppn_mode"] = {
    "label": "Perlakuan Harga Jual terhadap PPN", "strict": True,
    "help": "Setting `tax.ppn.mode`.",
    "options": [
        _o("eksklusif", "Eksklusif — harga belum termasuk PPN (DPP = harga; perilaku sebelum pengaturan ini ada)"),
        _o("inklusif", "Inklusif — harga sudah termasuk PPN (DPP = harga × 100/(100+tarif))"),
        _o("bebas_ppn", "Bebas PPN — tarif efektif 0 (mis. rumah subsidi), tanpa catatan PPN"),
    ],
}
