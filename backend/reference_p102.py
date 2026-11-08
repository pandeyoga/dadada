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
}
