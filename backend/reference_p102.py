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
