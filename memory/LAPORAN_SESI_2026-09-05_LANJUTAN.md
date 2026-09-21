# LAPORAN SESI LANJUTAN 2026-09-05 — 4 Next Action Items audit 2026-09

Repo `pandeyoga/kn123` @65a3c9a di-clone ke `/app`, lingkungan dipulihkan (`.restore_env.sh`).
**Temuan lingkungan:** backend template datang dengan `CORS_ORIGINS="*"` → T-02 (gagal berisik) menolak start.
Diperbaiki di `backend/.env` (asal preview + localhost, `SESSION_COOKIE_SECURE=true`). `.env` di-.gitignore — kontainer baru
WAJIB mengisinya (lihat komentar T-02 di `server.py`).

## 1. T-01 Atomisitas — KEPUTUSAN: **Opsi B (saga / klaim atomik), tanpa replica set**
Alasan: replica set mengubah `MONGO_URL` di semua lingkungan (preview/CI/prod) dan 82 endpoint tetap harus di-refactor
satu per satu untuk memakai sesi transaksi — biaya infra + refactor; saga memberi jaminan yang dibutuhkan (satu pemenang,
kegagalan di tengah TERLIHAT) tanpa perubahan infra, dan bisa ditegakkan statik.

- `backend/services/atomic_claim.py`: `claim(coll, id, action, precondition)` = `find_one_and_update` berprasyarat status +
  `saga_lock` belum ada → pemenang tunggal, kalah 409 (`SAGA_IN_PROGRESS` bila terkunci, `STATE_CHANGED` bila status berubah);
  `finish_set()` = `$set` akhir + `$unset saga_lock`; `release()`; `mark_failed()`.
- `backend/routers/saga_locks.py`: `GET /api/saga-locks` (admin) daftar kunci menggantung; `POST /api/saga-locks/{coll}/{id}/release`.
- Diterapkan (klaim): inbound complete · SO cancel · SO release-reservation · SO approval decide · transfers approve/reject/status ·
  cycle-count approve. CAS berprasyarat status: PO close · PO cancel · **`so_transition`** (semua transisi SO kini CAS `status $in expected_from`
  + `$unset saga_lock`). Pra-eksisting diakui: vendor-bills pay, resolve-escalation.
- Guard baru **INV-ATOMIC-01** `scripts/guardrails/verify_atomic_claim.py` (+ self-test 10 kasus) dipasang di `gate.sh`:
  `REVIEWED` (mekanisme+alasan per endpoint, diverifikasi terhadap sumber fungsi), ratchet `BASELINE_UNREVIEWED=67` (hanya turun).
  Inventaris `memory/INVENTARIS_MULTI_KOLEKSI_2026-09.md` kini membaca `REVIEWED` (16 AMAN · 67 BELUM DITINJAU · 4 tidak relevan).
- Bukti runtime: 2× cancel SO bersamaan → 200 + 409, `saga_lock` tidak tersisa; 2× cancel PO bersamaan → 200 + 400/409;
  kunci disuntik manual → cancel 409 `SAGA_IN_PROGRESS`, tampil di `/api/saga-locks`, release 200.

## 2. T-05 Korpus uji — `memory/TRIASE_KORPUS_2026-09_TINDAK_LANJUT.md`
- `scripts/codemod_env_url.py` mengubah 63+4 berkas: literal URL preview → `os.environ["REACT_APP_BACKEND_URL"]`.
- 51 skrip direct dijalankan ulang: **21 LULUS penuh** (sebelumnya 0 — semua 404), 19 lulus-sebagian ≥70% (asersi lama vs aturan
  yang berevolusi; dipertahankan, alasan per skrip di dokumen), **11 dihapus** (9 rasio ≤50%/premis hilang + 2 UJI BASI SoD).
  Korpus 220 → 210. Bukti: `coverage_data/corpus_converted_2026-09-05.json`.

## 3. Seed demo — `seed_realistic.py`
- `clear_collections()` kini mengosongkan SEMUA koleksi selain `KEEP_MASTER` (design_gallery, amendment_reasons,
  expense_categories, uom_conversion_rules, bank_statement_formats, rnd_person_divisions) — 42 koleksi sisa tidak lagi bocor.
- `_replant_bootstrap()` di akhir `main()` menjalankan `bootstrap.run_bootstrap()` (idempoten): akun md@/wh.admin@, COA, hr_*,
  config ditanam ulang **tanpa restart backend**. Bukti: sesudah seed, login md@/wh.admin@/admin → 200; fondasi 8/75/18.

## 4. Lencana eskalasi menggantung
- `POST /api/outbound/tasks/{id}/reopen-escalation` (wms.approve): `resolving` → `pending_review` (+`reopened_by/at`), 409 bila tidak menggantung.
- `EscalationManagement.jsx`: badge "N Menggantung", label "MENGGANTUNG (resolving)", panel penjelasan (waktu klaim, peringatan roll),
  tombol "Buka Kembali Eskalasi (lepas klaim)" menggantikan Resolve pada kartu menggantung.

## Verifikasi
- `verify_atomic_claim.py --self-test` HIJAU; `gate.sh --quick`: 5 merah = persis pra-eksisting (modal_dismiss, escape_layers ×2,
  ux_audit, audit_i18n_id) — nol regresi; 2 gate baru hijau.
- Testing agent iteration_314: semua PASS (backend saga/CAS/stuck-lock/reopen + frontend badge & reopen).

## Tindak lanjut 2026-09-05 (sesi 3)
- **Ratchet turun 67 → 62**: klaim atomik dipasang di service `purchase_return_service.reverse_settlement`,
  `return_service.reverse_settlement`, `putaway_order_service.confirm_arrival` (klaim sesudah guard, `finish_set` di tulisan
  akhir); `POST /sales-orders` diakui **compensate** (id baru per permintaan; roll dilepas di `except`). Guard INV-ATOMIC-01
  kini memverifikasi mekanisme `service` (sumber fungsi service wajib berisi claim+finish) dan `compensate` (`except → await
  release_…`); self-test 16 kasus. `saga_locks.LOCKED_COLLECTIONS` +purchase_returns, sales_returns, putaway_orders.
- **Dua skrip ragu selesai**: `fase_f_write_flows` LULUS penuh di seed bersih (roll 800→50 = residu urutan korpus, bukan bug);
  `po_timeline_approval` = asersi basi (`po_00009` vs id seed `po_009`) → dibetulkan, 11/11.
- `.restore_env.sh` langkah [3b]: menolak lanjut bila `CORS_ORIGINS` kosong/`*` + berhenti bila `/api/` bukan 200 (tail log).
- **Panel "Kunci Saga"** di Pusat Pengaturan (tab admin-only): daftar kunci menggantung + alasan gagal + tombol lepas
  (konfirmasi via `askConfirm`, INV-UI-06). Testing agent iteration_315 semua PASS; gate `--quick` merah = 5 pra-eksisting.

## Terbuka / keputusan berikutnya
- 55 endpoint multi-koleksi masih BELUM DITINJAU (ratchet). Empat target sesi 5 sudah ditutup (lihat bawah).

## Tindak lanjut 2026-09-05 (sesi 5) — ratchet 58 → 55 + T-03 Lapis 4
- **Klaim retur jual**: `return_service.reverse_writeoff` klaim `sales_returns` SESUDAH target roll scrap ditentukan (400 "tanpa target" tidak pernah menyentuh kunci), `finish_set` di akhir; `relocate_return_rolls` klaim sesudah roll karantina ditentukan, tulisan akhir `finish_set` + `$push relocation_legs`. Bukti: kunci disuntik → 409; 2× relocate bersamaan → `[200, 400]`, kaki relokasi tepat 1.
- **Klaim void kwitansi AR**: `ar_receipt_service.void_receipt` klaim `ar_receipts` (`status != void`) sebelum keputusan selisih/payments SO/kas/deposit dibalik; bila `reverse_decision` gagal → `release()` lalu 400/409; status `void` lewat `finish_set`. `LOCKED_COLLECTIONS` + `ar_receipts` (panel: "Kwitansi pembayaran"). Bukti: 2× void bersamaan → `[200, 409]`, jurnal void kas tepat 1, `paid_total` 0.
- **Stok awal (kompensasi)**: mutasi + rebuild di `try`; `except → rollback_initial_stock` menghapus roll & mutasi yang lahir.
- **Inbound resolve-escalation (CAS)**: `find_one_and_update` berprasyarat `escalation.status != resolved` → 409 bila kalah (pola outbound). Bukti: 2× bersamaan → `[200, 409]`, ulang → 409.
- **Guard**: `validation_after_claim` mengabaikan raise 4xx yang didahului `_saga.release(` (≤3 baris); self-test 19 kasus.
- **T-03 Lapis 4**: paginasi opt-in `/hr/attendance`, `/hr/visits`, `/hr/field-tracks` (envelope bila `?page=`, array bila tidak); `purchase-history` proyeksi terbatas + `events_page`.
- Probe: `scripts/probe_sesi5_saga.py` 27/27 PASS (self-cleanup: roll/task sintetis dihapus, SO probe dibatalkan, lot yatim + balance dipulihkan). `verify_data_integrity` 247/0; `gate.sh --quick` 52 PASS, 5 merah pra-eksisting.

## Tindak lanjut 2026-09-05 (sesi 4) — 4 Next Action Items
- **Klaim Realokasi Roll**: `POST /sales-orders/{id}/items/{pid}/reallocate` (klaim sesudah validasi; `release()` bila
  `reserve_specific_rolls` gagal; `finish_set`) dan `/release-rolls` (klaim sebelum roll dilepas + mutasi; `finish_set`
  + `$push reservation_releases`). Bukti: kunci disuntik → 409 `SAGA_IN_PROGRESS`; 2× reallocate bersamaan → tanpa 5xx,
  `saga_lock` bersih.
- **Klaim Pembatalan Tagihan**: `POST /vendor-bills/{id}/cancel` klaim berprasyarat `status` + `amount_paid ≤ 0.01`
  sebelum `reverse_vendor_bill`; gagal reversal → `mark_failed` (alasan tampil di Kunci Saga); status `cancelled` lewat
  `finish_set`. `payment_variance_service.reverse_decision` klaim `status != reversed` (dipanggil tombol Anulir DAN
  `void_receipt`). Bukti: 2× cancel bersamaan → `[200, 409]`, jurnal pembalik tepat 1; 2× reverse → 1 pemenang.
  `saga_locks.LOCKED_COLLECTIONS` + `vendor_bills`, `payment_variance_decisions` (label di panel). Ratchet **62 → 58**.
- **Notifikasi Kunci Menggantung**: `services/saga_lock_watch.py` + job scheduler `saga_lock_watch` (interval **10 menit**
  — scheduler kini mendukung `interval_minutes`), ambang `saga.stuck_lock_minutes` (config catalog, bawaan 10) →
  `create_addressed(roles=("admin",))`, severity `critical` bila ada `error`, dedupe per hari per kunci, link
  `settings-config`. Job TIDAK melepas kunci. Bukti: kunci umur 1000 menit → 1 notifikasi ke `user_admin_01`
  (`recipient_user`, bukan role), jalan ke-2 → 0; tanpa kunci → 0.
- **Guard baru INV-ATOMIC-01**: validasi 4xx SESUDAH klaim = MERAH (`validation_after_claim`, self-test 18 kasus). Lahir
  dari bug nyata yang ditemukan korpus: `inbound complete` pagar lot mode `block` di bawah klaim → kunci tertinggal →
  GR ulang 409. Diperbaiki (pagar dipindah ke atas klaim); `test_fase_c_lot_poc` kini rc=0.
- **Triase 76 skrip TIDAK TAHU** → `memory/TRIASE_TIDAK_TAHU_2026-09-05.md`: 6 LULUS · 1 BUG DIPERBAIKI · 9 BASI→DIBETULKAN
  · 19 ASERSI BASI · 12 UJI BASI · 27 LINGKUNGAN · 2 REGISTRY GAP (P2). Nol TIDAK TAHU tersisa.
- Skrip bantu: `scripts/probe_sesi4_saga.py` (probe runtime 4 item, semua PASS), `scripts/run_corpus_subset.py`.
