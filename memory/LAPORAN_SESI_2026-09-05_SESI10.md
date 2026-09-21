# LAPORAN SESI 2026-09-05 — SESI 10: QR label + pindai tanpa RFID · ratchet 49 → 48

## 1. Pindai label roll (QR) tanpa RFID
- Label potongan sampel & label roll inbound kini memuat **QR berisi NOMOR ROLL** (`qrcode` npm, data-URL offline; tata letak 58×40 mm: QR 22 mm + teks).
- Backend hanya-baca `GET /rfid/lookup?code=` (izin `wms.view`): EPC tag → roll (`via: rfid`), atau nomor roll / id → roll (`via: label`); 404 `CODE_UNKNOWN`; menghormati scope entitas.
- HP gudang tab **Pindai**: kotak input menerima nomor roll atau EPC (Enter = pindai), tombol **Kamera** (hanya bila `BarcodeDetector` tersedia — Chrome Android) memindai QR/Code-128 langsung; hasil besar COCOK / TERIKAT PESANAN / KODE TIDAK DIKENAL + keterangan "via label QR / via tag RFID · roll belum bertag".
- Potong sampel: `_resolve_roll()` menerima nomor roll dari QR (EPC tak dikenal → cari `roll_no`; `roll_id` juga bisa berupa `roll_no`).

## 2. Ratchet INV-ATOMIC-01 (49 → 48; 41 cek PASS)
| Endpoint | Klaim | Prasyarat | Bukti |
|---|---|---|---|
| `DELETE /transfers/{id}` (batal) | `warehouse_transfers` (router, `claim`) | `status ∉ {completed, rejected, cancelled}` — SEBELUM roll dilepas | kunci → 409; 2× bersamaan → satu 200 + satu 4xx, tanpa `saga_lock` |
- **Belum ditinjau (jujur)**: `POST /rfid/ingest` (log bacaan + `last_seen` — sifatnya append/idempoten, kandidat mekanisme `log_only`), `POST /sales-returns/{id}/rolls/{roll}/transfer-ownership` (sudah CAS `update_one` berprasyarat di service — perlu dipindah ke `find_one_and_update` agar terbaca guard), `POST /transfers` & `POST /wms/tasks` (pembuatan dokumen baru — kandidat `compensate`). Sisa anggaran sesi tidak cukup untuk empat sekaligus; angka 48.

## 3. Bukti
- Gate `--quick` 57 PASS / 0 merah; probe cepat transfer cancel (kunci → 409; balapan `[200, 400]`); testing agent `test_reports/iteration_324.json` **SEMUA PASS** (backend 12/12 + frontend pindai label & QR di popup).
