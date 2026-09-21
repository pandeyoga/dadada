# Laporan Sesi 12 — 2026-09-06

## Permintaan
1. Ratchet: scan-pick, dispatch, qc-decision.
2. Pindai roll saran FIFO → tugas potong sampel muncul.
3. Cetak massal label roll dari lot / PO (desktop).

## Yang dikerjakan
### Ratchet INV-ATOMIC-01: 41 → 38
- `outbound scan-pick`: CAS `find_one_and_update` berprasyarat status hidup + `picked_qty` sama seperti saat dibaca → 409 `STATE_CHANGED` bila kalah. Probe: 6 pick bersamaan (qty 10) → `[200,200,400,409,409,409]`, picked_qty 8 = 2×4, scan_log 2 (tak ada tulisan hilang/ganda).
- `shipment_service.dispatch_task`: klaim `wms_tasks` (status dispatchable) sesudah validasi qty, release bila `ship_order_rolls` gagal, `finish_set` pada tulisan akhir.
- `qc_service.process_qc_decision`: klaim `wms_tasks` (status qc_pending) sesudah validasi, body dipisah ke `_apply_qc_decision` (mengembalikan `set_fields`), `mark_failed` bila gagal, `finish_set` di akhir. Router meneruskan 409.
- Guard 48 cek PASS, self-test hijau, `BASELINE_UNREVIEWED = 38`.

### Pindai → tugas sampel
- `GET /rfid/lookup` sudah memuat tugas `sample_cut` via `suggested_roll_id`; kini ikut `customer_name`; HP menampilkan "Potong · produk · pelanggan · SMP-xxxx" → klik membuka kartu di tab Sampel.

### Cetak massal label
- `GET /rfid/labels?po_id|lot_id|task_id` (hanya-baca, scope entitas) → roll + product_name + po_number.
- `printRollLabelsBulk` (`utils/rollLabels.js`, dikelompokkan per produk). Lot detail: tombol `lot-action-print-roll-labels` ("Label N roll"). PO detail (status receiving/partial/completed): `…print-roll-labels` "Cetak Label Semua Roll" + info jumlah.

## Verifikasi
- `scripts/probe_sesi12.py` SEMUA PASS · guard + gate quick hijau · testing agent: lihat iteration terbaru.
