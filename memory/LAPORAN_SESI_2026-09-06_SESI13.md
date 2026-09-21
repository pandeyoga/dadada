# Laporan Sesi 13 — 2026-09-06

## Permintaan
Ratchet encode/DELETE tag & advance · label saat penerimaan (desktop) · riwayat pindai roll · antrean printer label (QR ikut antrean RFID). Offline HP gudang ditunda ke sesi berikutnya (persetujuan user).

## Yang dikerjakan
### Ratchet INV-ATOMIC-01: 38 → 36 (+ advance dikunci)
- `rfid_service.encode_tag`: CAS `inventory_rolls` (`rfid_tag_id` kosong → tag) via `find_one_and_update`; kalah → tag baru dihapus (kompensasi) + 409.
- `rfid_service.retire_tag`: `find_one_and_update` berprasyarat `status: active` → 409 bila sudah retired.
- `wms advance`: CAS `status == status saat dibaca` + `expected_status` opsional dari UI (status yang dilihat pengguna) → 409 `STATE_CHANGED`; klik ganda tidak lagi melompat dua tahap (temuan testing agent iteration_327, diperbaiki). Endpoint satu-koleksi → tidak mengubah baseline.
- Guard: mekanisme baru `service_cas` (CAS di service, diverifikasi RE_CAS pada sumber service) + 2 kasus self-test; `RE_CAS` mengenal `rfid_tag_id`. 51 cek PASS, baseline 36.

### Label saat penerimaan (desktop)
- `InboundScanInterface` banner hasil `complete` kini memuat `RollLabelActions` (`gr-labels-popup` cetak popup, `gr-labels-queue` kirim antrean) dari `created_rolls`.

### Riwayat pindai roll
- `GET /rfid/lookup` (bawaan `record=true`) mencatat `roll_scans` (append-only, `owner_entity_id` ter-scope) + `inventory_rolls.last_scan`; respons memuat `last_scan` sebelumnya. `record=false` untuk cetak ulang (tidak menambah jejak).
- `GET /rfid/roll-scans/{roll_id}`; timeline Jejak Barang (`journey-timeline`) menambah event `scan` + `roll.last_scan`; `RollJourneyPopup` menampilkan "Terakhir dipindai HP". HP: baris "Pindai ini tercatat · …".

### Antrean printer label
- `POST /rfid/print-jobs` `kind: "qr_label"` → `rfid_print_service.create_qr_label_job` (ZPL 58×40 `^BQN` nomor roll, tanpa `^RFW`); job RFID lama diberi `kind: "rfid_tag"`. Printer pull `device-jobs/pending` + `ack` melayani keduanya (antrean bersama).
- Tombol antrean: Lot detail (`lot-action-queue-roll-labels`), PO detail (`…queue-roll-labels`), banner inbound. Panel Print & Verify menandai job QR (badge, tanpa tombol verifikasi RFID).

## Verifikasi
- `scripts/probe_sesi13.py` 14/14 PASS (encode/retire/advance balapan, roll_scans, timeline, ZPL, printer pull+ack). Gate quick hijau. Testing agent: iteration terbaru.
