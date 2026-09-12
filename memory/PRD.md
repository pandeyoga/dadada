# SIPRO — PRD (lanjutan development dari github.com/makidbeh/sipro)

## Problem statement (asli, Juni 2026)
Lanjutkan development repo sipro:
1. Menu override persyaratan akad (mis. SPKT / biaya all-in belum lunas) sudah ada → **tambahkan upload surat keterangan** saat override.
2. **Bukti pembayaran wajib dilampirkan** untuk semua tipe pembayaran (all-in, termin, booking fee, titipan, pencairan KPR — semua yang ada di detail leads & customer). Semua tipe file diizinkan.
3. Booking fee = uang titipan. Jika skema all-in memuat komponen **BOOKING**, booking fee otomatis melunasi komponen itu; jika tidak ada, tetap default (dialihkan ke termin unit).

## Arsitektur
- Backend FastAPI (`/app/backend`, prefix `/api`), MongoDB (motor), engine modular (`allin_engine`, `finance_engine`, `contracts_engine`, `booking_fee`, `kpr_disburse`).
- Frontend React 19 + CRACO + shadcn (`/app/frontend`), uploader bukti = `components/patterns/EvidenceUploader.js` → `POST /api/files/upload`.
- Env baru yang dibutuhkan backend: `JWT_SECRET`, `SEED_DEMO_USERS` (lihat `/app/backend/.env`). Kredensial: `/app/memory/test_credentials.md`.

## Implementasi (12 Jun 2026)
### 1. Surat keterangan pada override tahap legal
- `models_p53.LegalAdvanceIn.override_file_ids`; `contracts_engine.legal_advance` menolak override tanpa berkas (dan memverifikasi id berkas ada), menyimpan `legal.<stage>.override.file_ids`.
- `OVERRIDABLE` kini: `kelebihan_tanah_belum_lunas`, `spkt_belum_ada`.
- UI `LegalTimeline.js`: uploader "Surat keterangan / dasar pengecualian (wajib)" + tautan berkas di badge pengecualian.
### 2. Bukti pembayaran wajib (backend + UI)
- `POST /finance/ar/receipts` (`ReceiptCreate.proof_file_ids` min 1), `POST /cost-invoices/{id}/pay`, `POST /booking-fee/deals/{id}/pay`, `POST /finance/ar/{deal}/deposit` (baru: `proof_file_ids`, tersimpan di entri titipan), pencairan KPR (`DisbursementCreate.file_id` wajib + validasi `kpr_disburse`).
- UI: `ReceiptDialog`, `BookingFeePanel`, `CostBillingPanel`, `DepositPanel`, `FinancingDialogs` (uploader baru), `KprPanel` — tombol simpan nonaktif tanpa bukti; `EvidenceUploader` default menerima semua tipe file (`accept="*/*"`, prop `required`).
### 3. Booking fee → komponen BOOKING all-in
- `allin_engine.BOOKING_CODE="BOOKING"`; komponen master bawaan `BOOKING` ditambahkan; `resolve_scheme(..., booking_fee=)` → nominal komponen = booking fee deal (formula "= booking fee deal"). Dipanggil dari `quotation_engine` (reservasi), `allin_amend`, preview `/allin-schemes/{id}/preview?booking_fee=`.
- `allin_engine.apply_booking_deposit`: saat AR lahir (`finance_engine.create_ar_for_deal`), bila deal punya komponen BOOKING → terbitkan invoice biaya (jika belum), kuitansi biaya `KWB` funding `booking_deposit`, jurnal `2-1450 → 2-1470`, mutasi titipan `apply_cost`. Sisa titipan (jika ada) tetap ke termin. Tanpa komponen BOOKING → perilaku lama.
- Smoke test: `/app/tests/smoke_booking_allin.py` (lulus).
### Perbaikan lingkungan
- `ReferenceSelect.js`: fungsi `useCustom` → `applyCustom` (eslint rules-of-hooks memblokir build).

### Label komponen BOOKING (12 Jun 2026)
- Master komponen & skema all-in: badge "otomatis dari booking fee", cara hitung & nominal terkunci ("= booking fee deal"); `PUT /cost-components/{id}` mengabaikan `calc_method/amount/pct` untuk kode BOOKING.

## Backlog / catatan
- P1: Refund booking fee pada deal yang sudah mengalihkan titipan ke komponen BOOKING (saldo titipan 2-1450 = 0; refund harus dari titipan biaya 2-1470).
- P2: Laporan pembayaran: filter "tanpa bukti" untuk data lama (sebelum kewajiban bukti).

---
## Lanjutan dari github.com/bagatadaha/Sipro (Juni 2026) — 5 poin owner
Problem statement: (1) skema pembayaran yang dipilih saat reservasi harus sinkron ke Kontrak & Legal dan Finance AR; (2) form Tambah Lead manual tidak punya kolom PIC; (3) tab "Kontrak & Harga" datar & tidak berguna; (4) tab "Unit & Konstruksi" tidak update & minim fungsi; (5) komplain hanya dari portal — perlu input manual oleh manajemen.
Pilihan user: rincian lengkap harga+biaya komponen editable+skema+AR; semua user manajemen boleh input komplain; progres per tahapan/milestone/foto/BAST/link Pembangunan; kerjakan semua sekaligus.

### Implementasi
- **Backend baru** `routers/customer_hub_router.py`: `GET /customers/{cid}/contract-pricing` (per deal: skema pilihan reservasi, rincian harga, termin AR, kontrak + breakdown biaya, ringkasan AR, pemeriksaan **sync** deal↔kontrak↔AR) dan `GET /customers/{cid}/units-construction` (jadwal bangun, tahapan, milestone, foto bukti, BAST, kontrak, tautan).
- `POST /complaints` (komplain manual staf: customer_id, unit, kanal wa/telepon/walk_in/email, kategori, prioritas, PIC, notifikasi WA opsional) — SLA 48 jam + task SM-09 + notifikasi, `source=manual`.
- `GET /leads/assignees` (calon PIC: sales/sales_manager/marketing_admin; sales scoped → diri sendiri).
- `GET /quotations/options` kini memuat `kind`, `kind_label`, `items` skema; seed skema "Standar KPR (DP 20%)" diperbaiki → `kind: kpr` (dulu cash_bertahap → penyebab ketidaksinkronan).
- **Frontend**: `CustomerContractTab.js` (kartu per transaksi + tombol isi komponen biaya via CostsDialog), `CustomerRelatedTabs.js` (CustomerUnitsTab baru + CustomerComplaintsTab dengan tombol "Catat komplain"), `complaints/ManualComplaintDialog.js` (dipakai di profil pelanggan & halaman /complaints), `AddLeadDialog.js` (select PIC `lead-form-pic`), `PricingFields.js` (label jenis skema + pratinjau termin). TestIds: `constants/testIds/custHub.js` (CHUB).
- Env: `JWT_SECRET`, `SEED_DEMO_USERS=true` di backend/.env. Skrip verifikasi: `scripts/verify_scheme_sync.py "<nama skema>"`.
- Uji: test_reports/iteration_40.json — semua lulus (backend pytest 9/9 + Playwright UI).

### Backlog
- P1: validasi di Pusat Konfigurasi › Skema Pembayaran — tolak nama yang menyebut "KPR" bila `kind != kpr` (saat ini hanya ditandai di panel sync).
- P2: Filter "sumber = manual/portal" & kolom kanal di tabel /complaints.
- P2: Tab Unit & Konstruksi — tombol "bangkitkan jadwal" langsung dari profil pelanggan.

