# Laporan Sesi 11 — 2026-09-06

## Permintaan
1. Ratchet klaim atomik: rfid ingest, transfer-ownership retur, POST /transfers, POST /wms/tasks.
2. Cetak ulang label QR roll (desktop + HP gudang).
3. Pindai → Aksi di HP gudang (hasil pindai langsung membuka tugas terkait).

## Yang dikerjakan
### Ratchet INV-ATOMIC-01: 48 → 41
- `return_service.transfer_return_roll_ownership`: klaim `sales_returns` sesudah semua validasi (roll, entitas, E9.3), release bila CAS roll kalah/engine gagal, `finish_set` + `$push ownership_transfers`. Router meneruskan 409 dari klaim.
- `transfers.create_transfer`: reservasi roll + insert dokumen dalam satu `try`, `except → release_wh_transfer_rolls` (kompensasi). Dokumen dibangun via `_build_transfer_doc`.
- `wms.create_task`: inbound manual → `create_inbound_roll` dalam `try`, `except → rollback_task_shell` (safe_unlink_all + hapus tugas cangkang).
- `rfid/ingest`: ditinjau → `service` (append-only rfid_reads, last_seen idempoten; tak butuh kunci).
- Guard: 45 cek PASS, self-test hijau, `BASELINE_UNREVIEWED = 41`.

### Cetak ulang label
- `frontend/src/utils/rollLabels.js` (sumber tunggal QR label 58×40; `reprintRollLabel`). `MobileTaskActions` re-export + `ReprintRollButton` pada kartu inbound/outbound (bila `roll_id`).
- HP: panel Pindai `mw-scan-reprint`. Desktop: RFID Tags (`rfid-reprint-{tag}`, `rfid-untagged-reprint-{roll}`), Lot detail tab Roll (`lot-roll-reprint-{roll}`). Data roll segar dari `GET /rfid/lookup`.

### Pindai → Aksi
- `GET /rfid/lookup` mengembalikan `open_tasks` (roll_id/suggested_roll_id/roll_ids, + outbound task `order_id == roll.reserved_ref.id` & produk sama).
- `MobileWarehouseApp`: tombol `mw-scan-task-{id}` → pindah tab + `TaskList` menerima `focusTaskId` (kartu terbuka, ring biru, scrollIntoView).

## Verifikasi
- `scripts/probe_sesi11.py`: SEMUA PASS (409 saat terkunci via fixture sintetis non-antar-PT, 400 sebelum klaim tanpa kunci tertinggal, kompensasi transfers, wms task+roll, lookup open_tasks inbound & outbound).
- `gate.sh --quick`: hijau (perbaikan INV-REF-04 pada rollback_task_shell).
- Screenshot mobile: pindai RL-00025 → tugas SO-0005 → kartu terbuka di tab Keluar.
- Testing agent: lihat iteration terbaru di /app/test_reports.
