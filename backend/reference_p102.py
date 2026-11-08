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
}
