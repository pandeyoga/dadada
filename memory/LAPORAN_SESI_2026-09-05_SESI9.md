# LAPORAN SESI 2026-09-05 — SESI 9: ratchet 51 → 49 · riwayat sampel di 360 · label roll inbound

## 1. Ratchet INV-ATOMIC-01 (51 → 49; 4 endpoint ditinjau, 40 cek PASS)
| Endpoint | Klaim | Prasyarat | Bukti |
|---|---|---|---|
| `POST /purchase-returns/{id}/ship-to-supplier` | `purchase_returns` (service) | `supplier_status != shipped` sesudah `assert_transition` | kunci → 400 transisi-dulu / 409 |
| `POST /sales-orders/{id}/simulate-payment` | `sales_orders` (router, mekanisme `claim`) | sesudah validasi outstanding, sebelum `invoices` ditulis; `finish_set` + `$inc paid_total` + `$push payments` dalam SATU update | kunci → 409; 2× bersamaan → `[200, 409]`, **paid_total naik tepat 1×** |
| `POST /finance/closing/{id}/reopen` | `period_closings` (service) | `status == closed` | kunci → 409; reopen ∥ reclose → tepat satu 200 |
| `POST /finance/closing/{id}/reclose` | `period_closings` (service) | `status == closed` | (sama; dua jurnal penutup tidak mungkin lahir bersamaan) |
- `LOCKED_COLLECTIONS` + `period_closings` (panel: "Tutup buku periode"). Angka BELUM DITINJAU 49 (dua endpoint closing tidak dihitung terpisah oleh inventaris).

## 2. Riwayat sampel pelanggan (kartu CRM 360)
- `customer_service.customer_360()` + `sample_history` (nomor, produk·SKU, panjang, nilai, status, roll anak, tanggal potong) + `stats.samples_cut`.
- `Customer360Panel` tab **Sampel** (testid `customer-360-tab-samples`, baris `customer-360-sample-{id}`).

## 3. Label roll baru inbound (HP gudang)
- `POST /inbound/tasks/{id}/complete` kini mengembalikan `created_rolls[{id, roll_no, length, unit, grade, lot, dye_lot}]`.
- Mobile: sesudah **Selesai** muncul banner `mw-inbound-done-{task}` (SELESAI · n roll baru) + tombol **Cetak label n roll** (`mw-inbound-print-{task}`) → satu halaman 58×40 mm per roll (nomor roll besar, produk, panjang, grade, lot/dye, PO, gudang, tanggal). Pola sama dengan label potongan sampel (banner diangkat ke daftar agar bertahan setelah refresh).

## 4. Bukti
- `scripts/probe_sesi9.py` **9/9 PASS** (self-clean). Testing agent `iteration_321`: 7/9 — 2 temuan "2× bersamaan → 200/200" pada simulate-payment & reopen∥reclose.
  Analisis: klaim saga (Opsi B) menutup permintaan yang **tumpang-tindih**; bila permintaan pertama selesai sebelum klaim kedua (jalur berurutan-cepat), keduanya sah secara bisnis (dua pembayaran berbeda / reclose lalu reopen). Untuk pembayaran ditambah **pagar klik-ganda** yang dimasukkan ke **PRASYARAT klaim** (atomik di Mongo: `payments $not $elemMatch {amount, method, created_at ≥ now-10s}`) → dua permintaan yang membaca snapshot lama pun hanya satu yang menang (409 `STATE_CHANGED`/`DUPLICATE_PAYMENT`). Retest: `iteration_322.json` (frontend 3/3, closing PASS) → perbaikan prasyarat → `iteration_323.json`.
- Insiden: `sed -i` gagal mengosongkan `MobileTaskActions.jsx` → dipulihkan dari commit HEAD lalu ditambah fungsi baru; pelajaran: pakai `search_replace`, bukan sed, untuk berkas JSX.
