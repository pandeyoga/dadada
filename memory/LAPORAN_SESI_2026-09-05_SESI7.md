# LAPORAN SESI 2026-09-05 — SESI 7: SISA PLAN GELOMBANG (satu run)

## Keputusan pemilik (jual sampel)
Harga **per satuan roll (yard/meter) × panjang** dari **master harga sampel terpisah per INDUK** (fallback harga daftar varian) ·
potong = **SO jenis `sample` + kwitansi kas/transfer saat itu juga** · **sales mengajukan** (mobile/desktop), **gudang memotong** lewat tugas WMS `sample_cut`.
Tanpa batas, tanpa persetujuan, saran roll **FIFO**, roll lain **boleh dengan alasan**, sisa induk < 2 satuan → `is_remnant`.

## 1. Modul Jual Sampel (§3-C) — SELESAI
- Backend `services/sample_sale_service.py` + `routers/sample_sales.py`:
  `GET/PUT /sample-prices[/{template_id}]` (admin/manager) · `GET /sample-requests/quote` (harga × panjang + saran FIFO) ·
  `POST /sample-requests` (sales → dokumen `sample_requests` + `wms_tasks{flow_type:'sample_cut'}`) · `POST /sample-requests/{id}/cut` (gudang) · `/cancel` (CAS).
- `cut`: validasi roll (produk sama, `available`, cukup panjang; EPC tak dikenal → 404 `TAG_UNKNOWN`; bukan saran tanpa alasan → 400 `REASON_REQUIRED`) →
  **klaim atomik** `sample_requests` → CAS potong induk → `insert_child_roll` (**P-1: potongan lahir tanpa tag**, status `sold`) → mutasi `sample_sale` →
  SO `order_type:'sample'` status `done` → `ar_receipt_service.create_receipt` (kas/transfer, alokasi penuh) → `gl_service.post_sales_order` → tugas `completed` → `finish_set`.
  Bukti balapan: 2× potong bersamaan → `[200, 409]`.
- Pelajaran: SO sampel memakai `payment_profile_method:'transfer'` (metode kas asli disimpan di `sample_payment_method`) supaya kwitansi tidak dianggap "tanpa pesanan terbuka" oleh mesin selisih bayar (NON_AR_METHODS).
- Frontend: `features/samples/SampleRequestForm.jsx` (satu form: mobile "Jual Sampel" & desktop), `SampleSalesView.jsx` (tab **Jual Sampel** di hub Penjualan; daftar + master harga), `SamplePriceMaster.jsx`.
- Mobile gudang: tab **Sampel** → kartu tugas → "Potong roll saran" / roll lain (EPC atau ID + alasan) → hasil DIPOTONG · induk → anak · SO · kwitansi.
- Panel Kunci Saga mengenal `sample_requests` ("Permintaan sampel"). INV-ATOMIC-01: kedua endpoint tercatat REVIEWED (33 cek PASS, baseline 54 tetap).

## 2. Bersihkan field warna (§D lanjutan) — SELESAI
- `product_variant_service.canonical_color()` = SATU sumber (`variant_attrs.color` ← `color` ← `color_name` ← `variant`); `color_fields()` menulis turunan `color`/`color_name`/`color_code` dari sumber itu (PDF/label tetap jalan).
- `color_code_for()` ("Biru Tua"→`BIT`) + `variant_sku(parent, warna, grade)` = **prefix induk + kode warna** (+grade bila ≠ A). Jalur template `generate_variants` sudah memakai prefix+kode.
- Migrasi `resolve_orphans()` diperluas (menyamakan warna) → 19 produk dirapikan; probe: semua produk `color == color_name == variant_attrs.color`.

## 3. Aksi tugas gudang di mobile (Tahap 2) — SELESAI
- `features/mobile/MobileTaskActions.jsx`: Masuk → **Terima** (`scan-receive` qty) & **Selesai** (`complete` + lot/dye lot; pagar lot 400 ditampilkan apa adanya) · Keluar → **Ambil** (`scan-pick`) & **Berangkatkan** (`dispatch`) · Sampel → **Potong**.
- Kartu tugas ketuk-untuk-buka; hasil = notice ikon+teks.

## 4. Bukti
- `scripts/probe_sesi7_sampel.py` **23/23 PASS** · `verify_atomic_claim` 33 PASS · `verify_data_integrity` 246/0 (3 WARN: AR drift pra-eksisting, 1 titipan bank pra-eksisting, 1 kwitansi selisih dari probe sebelum perbaikan → sudah ditandai selesai) · `ux_audit --strict` 0 ERROR · gate `--quick` lihat `.gate_quick.log`.
- Testing agent: `test_reports/iteration_318.json`.

## 5. Belum / catatan jujur
- Peta lacak lapangan belum memakai paginasi `/hr/field-tracks?page=` (backend siap).
- HPP/COGS potongan sampel mengikuti mekanisme jurnal SO yang ada (`post_sales_order`); COGS per surat jalan tidak berlaku karena tak ada shipment — bila kebijakan menuntut COGS eksplisit per potongan, perlu jurnal tambahan.
- Mobile sales "PIN/persetujuan" tidak dibangun: sales tidak punya wewenang menyetujui; keputusan tetap di desktop manajer.
