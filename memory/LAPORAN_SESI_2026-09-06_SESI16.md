# Laporan Sesi 16 — 2026-09-06

## Permintaan
Mobile sales native (Pelanggan, Retur, Pesanan Khusus, Daftar Harga) · Piutang & kwitansi di HP sales · Pesanan tertunda offline · Ratchet entities/impact-apply.

## Mobile sales native (menggantikan komponen desktop yang terpotong di "Lainnya")
- `MobileCustomers.jsx`: daftar kartu + cari; detail 360 satu layar (piutang terbuka, jatuh tempo, tab Tagihan/Pesanan/Kwitansi/Sampel) dari `GET /customers/{id}/360` (kini memuat `payments` = kwitansi pelanggan).
- `MobileArReceipt.jsx`: catat pembayaran dari HP — alokasi FIFO otomatis ke `GET /ar-receipts/open-orders` (bisa diubah), metode, catatan, kelebihan → titipan; `offlinePost` (Idempotency-Key). **Kebijakan**: peran `sales` kini diberi `ar_receipt.create` (bootstrap GRANT idempoten) — keputusan user; sebelumnya E8.2 memindahkan ke finance.
- `MobileSalesNative.jsx`: `MobileReturns` (daftar + detail + buat retur dari pesanan terkirim, alasan dari master `complaint-reasons`, `quantity_returned`), `MobileSpecialOrders` (daftar + form ringkas `custom_item`), `MobilePricelist` (harga efektif per pelanggan dari `GET /customer-prices` dengan badge sumber).
- `MobilePendingQueue.jsx`: daftar aksi/pesanan yang masih antre di HP (tab Pesanan & Lainnya) + batalkan sebelum terkirim (`askConfirm`) + "Kirim sekarang".
- Idempotency prefixes + `/ar-receipts`, `/sales-returns`, `/special-orders`. `audit_create_modal`: `INLINE_DIBOLEHKAN` untuk sub-halaman HP (form menukar layar).

## Ratchet INV-ATOMIC-01: 30 → 26
- `entity_lifecycle.archive_entity`: CAS `status ≠ archived` → 409 (`service_cas`, dipakai POST archive & DELETE).
- `config_impact_service.apply`: klaim `products` sesudah validasi; body ke `_apply_plan`; `mark_failed` bila gagal; `release` di `finally`.
- `POST /entities` ditinjau `service` (id baru, seed idempoten). Guard 64 cek PASS.

## Verifikasi
- `scripts/probe_sesi16.py` SEMUA PASS. Testing agent iteration_331 → 2 temuan diperbaiki (KNSelect `onValueChange`; payload special-order sesuai `CustomItemSpec` + kolom harga target) → retest 332/333 PASS.
- Catatan data demo: `sales@` hanya punya 1 pelanggan tanpa pesanan terkirim → alur buat retur di HP baru bisa diuji sampai pemilihan (tombol disabled benar); backend `POST /sales-returns` lolos probe.
