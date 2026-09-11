"""Kosakata modul PENGAJUAN keuangan (fund requests): jenis, status, sumber pembayaran."""
from reference_groups import _o

GROUPS_P101 = {
    "fund_request_type": {
        "label": "Jenis Pengajuan Keuangan", "strict": True, "options": [
            _o("expense", "Pengajuan Biaya Operasional"),
            _o("reimbursement", "Reimbursement (sudah dibayar pribadi)"),
            _o("purchase", "Pembelian Barang / Jasa"),
            _o("vendor_payment", "Pembayaran Vendor / Tagihan"),
            _o("advance", "Kas Bon / Uang Muka (wajib pertanggungjawaban)"),
        ],
    },
    "fund_request_status": {
        "label": "Status Pengajuan Keuangan", "strict": True, "options": [
            _o("submitted", "Diajukan"), _o("approved", "Disetujui"),
            _o("disbursed", "Dicairkan"), _o("settled", "Dipertanggungjawabkan"),
            _o("rejected", "Ditolak"), _o("cancelled", "Dibatalkan"),
        ],
    },
    "fund_request_urgency": {
        "label": "Urgensi Pengajuan", "strict": True, "options": [
            _o("normal", "Normal"), _o("urgent", "Mendesak"),
        ],
    },
}
