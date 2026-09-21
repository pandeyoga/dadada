# Laporan Sesi 14 — 2026-09-06

## Permintaan
Offline HP gudang · Ratchet verify/cycle-count/interco · Status printer gudang · Lokasi terakhir roll.

## Yang dikerjakan
### Offline HP gudang (tanpa dobel)
- Backend `idempotency.py` (middleware): header `Idempotency-Key` pada POST/PUT/PATCH/DELETE ke `/api/inbound/*`, `/api/outbound/*`, `/api/sample-requests/*`, `/api/wms/tasks/*`, `/api/rfid/roll-scans`, `/api/rfid/print-jobs`. Kunci diikat ke path + identitas; insert `in_progress` dulu (kunci bersamaan → 409 `IDEMPOTENT_IN_PROGRESS`), balasan (kode + body, termasuk 4xx) disimpan 7 hari (TTL index) dan di-replay dengan header `X-Idempotent-Replay: true`. 5xx tidak disimpan.
- `POST /rfid/roll-scans` — catat jejak pindai dari antrean offline (waktu pindai asli `scanned_at`, `bin_id`, `offline: true`); `last_scan` hanya maju (pindai offline lama tidak menimpa yang lebih baru); pagar gudang E4.1.
- HP: `utils/offlineQueue.js` (antrean localStorage FIFO, `offlinePost` dengan kunci unik, `syncQueue` saat `online`), `OfflineBanner` (status offline / N aksi menunggu / hasil sinkron: berhasil · sudah tercatat (replay) · ditolak server). Aksi terima/selesai/ambil/berangkatkan/potong dan pindai memakai jalur ini.

### Ratchet INV-ATOMIC-01: 36 → 34
- `complete_verify` & `cycle_count.complete`: klaim `rfid_verify_sessions` (status open) sesudah validasi; `finish_set` di tulisan akhir; balapan → satu CC.
- `POST /transfers/inter-company`: seluruh reservasi + validasi interco + insert dalam satu `try`, `except → release_transfer_rolls` (endpoint satu-koleksi menurut inventaris → tidak mengubah angka, tetapi kompensasi kini menutup insert gagal).
- `POST /rfid/roll-scans` ditinjau `service` (append-only + CAS hanya-maju). Guard 55 cek PASS, baseline 34.

### Status printer gudang
- `GET /rfid/printer-status` → per gudang: printer (online = heartbeat ≤ 5 mnt), label/job menunggu, job tertua, `stuck` (label menunggu tanpa printer hidup). `PrinterStatusWidget` di Operasi Gudang › Kesehatan dan HP gudang › Pindai (ringkas).

### Lokasi terakhir roll
- HP Pindai: kolom "Bin / lokasi saya" (diingat di HP) → `bin_id` ikut tercatat. Tampil di hasil pindai HP, tabel roll Lot (kolom "Terakhir dipindai"), Jejak Barang (`last_scan` + event timeline "· bin …").

## Verifikasi
- `scripts/probe_sesi14.py` 14/14 PASS · guard/ux/i18n/warehouse_scope hijau · testing agent: iteration terbaru.
