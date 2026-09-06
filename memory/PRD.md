# PRD — SIPRO Property Development OS (lanjutan dari repo pandeyoga/dadada)

## Sesi lanjutan 2026-09-06 — repo agavafayaja/sipro; editor dan re-verifikasi
### Permintaan pengguna sesi ini
Lanjutkan https://github.com/agavafayaja/sipro, cocokkan ulang AUDIT_SINTESIS_1.md dan plan lama dengan bukti valid; jangan asal mengubah. Tambahkan format naskah seperti Word (rata kiri/kanan/kanan-kiri) dan pengaturan posisi/urutan tabel; pastikan dokumen terkonfigurasi. Audit overlap all-in include/exclude, jarak hadap–Tenggara, popup, tabel, dan field. Pengguna menyetujui main/default branch serta mempertahankan desain.

### Persona dan kebutuhan tetap
- Owner/admin: konfigurasi dokumen/master tanpa mengubah kode, angka bisa ditelusuri, audit jujur.
- Sales: dokumen/peta unit terbaca dan kontrol yang sesuai hak akses.
- Keuangan: naskah resmi konsisten dengan nominal transaksi dan salinan pembeli.
- Pembeli: salinan dokumen yang sama, bukan versi cetak yang kehilangan tabel biaya.

### Implementasi dan keputusan arsitektur
- React/FastAPI/MongoDB dipertahankan; env platform tidak diganti. Tiptap untuk naskah berformat, PDF.js untuk menampilkan PDF backend.
- Naskah HTML tersanitasi di koleksi template existing, teks lama masih didukung; renderer ReportLab bersama untuk alignment/list/table. Nilai placeholder di-escape; token tabel diteruskan ke renderer.
- Tabel native bisa dipindah, baris/kolom diedit; posisi/lebar tabel terkonfigurasi. Ukuran cetak mengikuti margin/kertas.
- Naskah sistem KWITANSI/BKM/BKK/BAST/PENAWARAN/FAKTUR/BUPOT/LAPORAN dan INB tersambung ke penerbit; faktur/bupot ikut layout; konteks biaya salinan staf/portal dibagi lewat helper.
- Overlap all-in, kartu arah hadap/harga, input konfigurasi bertipe salah, dan beberapa warning notifikasi/grafik diperbaiki berdasarkan reproduksi.
- 48 tes terfokus lulus; 23 target preview PDF diuji. Laporan independen iteration_5 dan koreksinya dipisah dari hasil akhir. Rangkaian repo saat ini sebenarnya 70 gate, bukan 62.
- Bukti terperinci dan batas cakupan: `memory/VERIFIKASI_SIPRO_2026-09-06.md`; log di `memory/verification/`.

### Backlog terprioritas / langkah berikutnya
- P0: tutup regresi yang terbukti pada alur editor/PDF/UI sebelum penyerahan; hasil gate akhir dicatat di laporan verifikasi.
- P1: seluruh fixture legacy mandiri (sebagian masih tergantung seed), skip WA live yang jujur, audit GL/BI non-lead dan portal sampai sumber baris, matriks visual semua dialog/peran, lencana global data uji.
- P2: versi/diff naskah, tipografi lanjutan, pemisahan template turunan invoice/kwitansi bila diperlukan. Peran dinamis belum diputuskan pengguna.
- Tidak diklaim: seluruh audit akuntansi/keamanan/seluruh UI tuntas, atau WhatsApp live terbukti.

## Problem statement (asli, 2026-06)
Lanjutkan development repo. Temuan pemakai: kartu KPI Pipeline Lead salah (jumlah kartu melebihi total lead),
biaya all-in include/exclude & konfigurasi lain tidak ter-wiring ke fitur, template PDF tidak bisa mengatur posisi
tabel/urutan bagian, nomor surat SPR (3 jenis) harus bisa dikonfigurasi terpisah, banyak tabel master tanpa RBAC,
banyak input bebas yang seharusnya dropdown master (mis. CoA), latar site plan tidak tersimpan/tampil.

## Arsitektur
FastAPI (`/app/backend`, 100+ router) + React (CRA, shadcn) + MongoDB. Konfigurasi terpusat di `settings_store.py`
(Pusat Konfigurasi), penomoran `numbering_registry.py`, tampilan dokumen `doc_layout.py` + `pdf_layout.py`.
Env backend: `MONGO_URL, DB_NAME, JWT_SECRET, SEED_DEMO_USERS, BACKUP_DIR`.

## Temuan audit (2026-06-xx) → status
| # | Temuan | Status |
|---|---|---|
| 1 | KPI lead tumpang tindih (65 > 48); "Diam ≥7 hari" hitung lead baru; "Lewat SLA" query field tak tersimpan (`sla_state`) | ✅ kartu = partisi Total/Aktif/Menang/Daur ulang/Hilang; drilldown SLA pakai `stage_due_at`; idle syarat `created_at < cutoff`; count pakai `count_documents` |
| 2 | 12 kunci konfigurasi tidak pernah dibaca kode | ✅ 10 di-wire: `reservation.max_active_per_lead` + `override_roles` (deals/reserve), `require_booking_fee_before_spr`, `slik.gate`, `lead.required_demography` (gerbang SPR di `docgen.applicable`), `kpr.sla_days` (`kpr_stage_due_at`), `addon.require_spkt_for_excess_land`, `addon.excess_land_price_per_m2`, `doc.require_verification_default`, `ui.table_page_size` (session → useListQuery). 2 dihapus karena fiturnya tidak ada: `partner.portal_enabled`, `addon.excess_land_discount_needs_approval` |
| 3 | Tab "Baris & biaya" hanya berpengaruh di pratinjau; PDF asli mengabaikan; bagian tidak bisa diurutkan | ✅ `documents/{id}/pdf` memakai `money_rows_for` + `layout_amounts(breakdown)`; `render_letter` mengurutkan blok sesuai `sections.order`; penanda `{{tabel_biaya}}` di naskah; RowsForm punya panah urutan bagian. Bagian "biaya" mati secara bawaan (naskah SPR sudah memuat rincian inline) |
| 4 | Satu aturan `docnum` untuk semua SPR | ✅ aturan per jenis `docnum:SPR-CASH`, `docnum:SPR-CASHB`, `docnum:SPR-KPR`, `docnum:SPKT` (menimpa bawaan bila diubah) |
| 5 | Panel konfigurasi tanpa `can()`; master biaya/all-in/KPR digembok `settings` (owner only) | ✅ `EditGate` (fieldset disabled + spanduk) di ConfigCenter & MasterData; allin_router → resource `catalog` |
| 6 | CoA input teks bebas | ✅ `ReferenceSelect group=gl_account` di Komponen Biaya; kode komponen manual all-in → dropdown master |
| 7 | Latar site plan dibuang oleh `/site-plan/{id}` & showroom publik | ✅ payload memuat `background{url}`; `SvgPlanMap` merender `<image>` |

## Backlog / P1
- Halaman KPR: tampilkan `kpr_stage_due_at` (tersangkut) di UI pembiayaan.
- Uji regresi semua panel konfigurasi dengan peran finance/sales_manager (EditGate).
- Naskah SPR bawaan: opsi mengganti rincian inline dengan `{{tabel_biaya}}`.

## Kredensial uji
Lihat `/app/memory/test_credentials.md` (`scripts/seed_demo_users.py` untuk menambah akun demo).

## Sesi 2026-09-06 — Audit Sintesis Tahap 1–2 + Tahapan Pembangunan & Survey
Sumber: `AUDIT_SINTESIS.md` (32 temuan). Semua temuan di bawah **diverifikasi dulu di runtime** sebelum diperbaiki.

| ID | Temuan (terbukti) | Perbaikan |
|---|---|---|
| WA-02 | Termin lunas tetap jadi kandidat pengingat (`item.paid` tidak ada; item menyimpan `paid_amount`) | `wa_reminder_engine.candidates` baca `paid_amount` + skip `status=paid` |
| DOC-01 | Invoice PDF kolom Dibayar per termin selalu Rp 0 | `ar_router.invoice_pdf` baca `paid_amount` |
| WA-13 | Pengajuan template Meta tanpa `example` → INVALID_FORMAT | `meta_components` sertakan `example.body_text`/`header_text`; `submit` menolak variabel tanpa contoh; field `examples` di template + UI |
| WA-04 | Body ↔ variables tidak divalidasi | `validate_variables` di create/update template (400) & submit |
| WA-01 | 5 jenis pengingat memakai 1 template `payment_reminder` | 5 template `reminder_*` di-seed untuk semua org (`ensure_reminder_templates`), default setting per jenis diganti |
| WA-03 | Riwayat body ≠ yang dikirim (reason ditempel) | `_render` hanya isi template |
| WA-12 | Template `rejected` tampil "Menunggu" di Lead WA | `TemplatesPanel` pakai status asli + alasan Meta |
| Fitur | Fase proyek (`construction_phases`) tidak bisa dibuat dari UI, tanpa template | `phase_templates.py` + `/construction/phase-templates` CRUD + `/project/{id}/phases/apply` (idempoten); tab **Tahapan Pembangunan**; detail proyek: Terapkan template / Tambah fase |
| Fitur | Survey hanya checklist datar tanpa tahapan | `survey_stages.py` + `/survey-stages`; tab **Tahapan Survey** (tahap → poin, toggle wajib); survey baru menyalin tahapan; form survey = wizard per tahap; finalisasi ditolak bila poin wajib `na` |
| Anti-kambuh | Pola A/B/C | `memory/FIELD_MAP.md`, `scripts/verify_field_names.py`, `scripts/verify_audit_fixes.py` (masuk `run_all_gates.sh`), `backend/tests/test_audit_tahap12_tahapan.py` (6 lulus) |

Keputusan default yang dipakai (belum dikonfirmasi pemilik): K-1 satukan template WA → sesi lanjut; K-3 KWITANSI cukup; K-4 progres resmi = fase berbobot; K-5 ganti label DSO.

### Gate yang masih MERAH (pra-eksisting di commit 7da1bd5, bukan regresi sesi ini)
~~`ux_audit`, `audit_forms_deep`, `verify_ia_v2`/`verify_build_hub`/`verify_budget_target`, `verify_33`, `verify_p66`/`verify_contract_legal_docgen`, `verify_p67`, `verify_p75-78`, `verify_cancellation_refund`, `verify_panel_resilience`~~ — **semua HIJAU per 2026-09-06 (sesi lanjutan)**; lihat catatan Tahap 7 di bawah.

### Backlog berikutnya (sesudah Tahap 7)
- Tahap 7 §4 (setengah tersisa): ~~rumus tertulis & nama sama = rumus sama~~ ✅ (gate 62 D2–D3).
- Pemulihan suite pytest legacy yang bergantung data seed lama (unit tipe `TIPE-45-90` untuk `test_p80_rab`, kontrak/booking fee untuk `test_p69b/c`, `test_p91/92/93`); tes WA yang menuntut kredensial Meta (`test_p100_wa_setup`, `test_p94_95_wa`) diberi skip jujur bila kredensial kosong.
- Audit lanjutan area yang belum diaudit (AUDIT_SINTESIS Bagian 6): akuntansi/GL, metrik BI non-lead, portal pembeli.

### Backlog berikutnya (Tahap 3–7 audit)
- ✅ Tahap 3: satukan layar template WA di Pusat Konfigurasi (WA-14, WA-05..09, WA-07) — iteration_2.
- ✅ Tahap 4: `ACTION_META` label aksi RBAC (RBAC-02/03) — iteration_2. Peran dinamis bila K-2 = ya (belum).
- ✅ Tahap 5 (2026-09-06, iteration_3): DOC-02 target `INVOICE` sendiri (kind table, kategori penagihan; dipakai PDF invoice AR & invoice biaya all-in, pratinjau contoh invoice); CFG-03/04 semua setting enum wajib `ref_group` → `option_labels` dari `/api/reference` (grup baru `reference_p100.py`: lead_won_trigger, slik_gate, attribution_model, docnum_scope, docnum_reset_policy, deletion_request_status; `handover_settlement_policy` dipakai ulang), dropdown Aturan Bisnis menampilkan label + kode kecil; UI-02 `DeletionRequestsTable` pakai registry (gate `audit_forms_deep` E5 hijau); UI-01 testid statis di `.map()` diberi pembeda (`ux_audit` hijau). WA-09 tambahan: `WaTemplateCreate.code` opsional dihormati (test `test_crud_header_type` hijau). Tes: `tests/test_audit_tahap5_doc_cfg_ui.py`.
- ✅ Tahap 6 (sudah ada di kode saat repo dipulihkan 2026-09-06 sesi lanjutan; kini DIJAGA): CFG-01 `core_utils.period_of` satu definisi + WIB; FIN-01 drill-down AR = kartu (`paid_amount` per termin); FIN-02 `work_home` → `_sync_with_drilldown`; FIN-03 `outstanding_pct` (bukan "DSO" palsu); PRJ-01 pembagi = semua unit; PRJ-02 `construction_progress` resmi vs `units_progress` rekap; BI-01 `MIN_SOURCE_SAMPLE`; BI-02 win rate satu definisi + `conversion_pct`. Tes: `tests/test_audit_tahap6_angka.py` (17).
- ✅ Tahap 7 §2 (2026-09-06): **gate 62 `scripts/verify_card_drilldown.py`** (148 pemeriksaan) — kartu Beranda per peran, partisi Pipeline Lead, Keuangan (AR/AP/ember aging), BI (rumus tertulis, nama sama = rumus sama), penjaga kode — masuk `run_all_gates.sh`.
- ✅ Tahap 7 §3 (2026-09-06): `audit_forms_deep.py` E6 memeriksa `<SelectItem>` hardcode → 16 dropdown di 14 berkas diganti `<ReferenceItems group=…/>` (komponen baru `patterns/ReferenceItems.js`); grup SSOT baru `wa_inbound_type`.
- ✅ Gate merah pra-eksisting dibersihkan (2026-09-06): `verify_contract_legal_docgen` (K11c 3 kode penahan masuk Kamus Data `docgen_block`; fixture melalui SLIK berbukti lewat API nyata), `verify_p66` (probe tabel menyalakan bagian `biaya` yang kini mati bawaan), `verify_p67` (h1 `SimpleMarkdown` → `page-title`). `run_all_gates.sh` → **OVERALL PASS (62 gates)**.
- Lingkungan: `backend/.env` butuh `JWT_SECRET`, `SEED_DEMO_USERS=true`, `BACKUP_DIR`, `DEFAULT_ORG_ID`, `PORTAL_MASTER_OTP`; `emergentintegrations` dipasang terpisah (konflik `litellm` pin di requirements.txt). `tests/conftest.py` kini membaca URL dari `frontend/.env` dan mengekspor `REACT_APP_BACKEND_URL` untuk seluruh suite (banyak modul uji lama menyimpan URL pod yang sudah mati).
- Suite pytest legacy: sebagian tes bergantung data seed lama (`TIPE-45-90`, kontrak tertentu) atau kredensial Meta — bukan regresi; dicatat di backlog.
- Pre-existing gagal karena data lingkungan (bukan regresi): `test_iter149_legal.py::test_admin_update_user`, `test_p97_template_compliance.py::test_opt_out_blocks_marketing_not_utility`.
