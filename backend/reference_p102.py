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
}
