# Laporan Sesi 15 — 2026-09-06

## Permintaan
Bug harga khusus tidak terpakai di pesanan HP sales · offline sales · peringatan label tertahan · service worker · ratchet rekonsiliasi bank.

## Bug: harga khusus disetujui tidak terpakai di pesanan HP sales
- Akar: `MobileCart` tidak memanggil `useEffectivePrices` → `special_prices` kosong → `price_approval_id` tidak dikirim → server memakai harga list.
- Fix: `MobileCart` memakai `useEffectivePrices` (sama dengan desktop `CheckoutDrawer`), harga efektif per baris + badge sumber ("Harga khusus"/"Harga pelanggan"), list price dicoret, subtotal efektif, `special_prices` dikirim ke `submitOrder`.

## Offline sales lapangan
- `Idempotency-Key` diperluas ke `/api/sales-orders`, `/api/hr/visits`, `/api/price-approvals`.
- Check-in/out kunjungan & kirim pesanan lewat `offlinePost` (antrean localStorage yang sama dengan gudang); `OfflineBanner` di app sales.

## Peringatan label tertahan
- `services/printer_stuck_watch.py` + job scheduler `printer_stuck_watch` (interval 10 menit): label queued > 30 menit di gudang tanpa printer online (heartbeat > 5 menit) → notifikasi `printer_stuck` ke `warehouse_admin` (+ manager), dedupe per gudang selama belum dibaca.

## Service worker (buka app tanpa sinyal)
- `public/sw.js`: app shell cache-first; data GET (tugas, roll, dashboard, produk, pelanggan, kunjungan) network-first → fallback cache dengan header `X-From-Cache`; aksi tulis tidak pernah di-cache (antrean offline). `TaskList` HP menampilkan banner "menampilkan daftar tugas terakhir". Registrasi hanya production build.

## Ratchet INV-ATOMIC-01: 34 → 30
- `bank_recon_service`: klaim `bank_statement_lines` pada `book_charge`, `to_holding`, `allocate_holding`, `cancel_holding` (sesudah validasi, `mark_failed` bila gagal, `finish_set` di akhir). `role-reality apply` ditinjau (dua tulisan idempoten). Guard 60 cek PASS.

## Verifikasi
- `scripts/probe_sesi15.py` SEMUA PASS (409 saat terkunci ×4 endpoint, 400 tanpa kunci, effective price + SO memakai harga khusus, idempotency kunjungan, job label tertahan + dedupe). Gate quick hijau. Testing agent: iteration terbaru.
