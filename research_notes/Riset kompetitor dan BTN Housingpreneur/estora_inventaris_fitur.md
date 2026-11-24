# Inventaris Fitur Estora — Property Development OS (berbasis bukti repo)

Disusun 2026-11-24 dari repo `/home/user/dadada` (nama lama produk: **SIPRO**). Sumber dibaca:
`memory/PRD.md`, `plan.md`, `memory/VERIFIKASI_SIPRO_2026-09-06.md`, `docs/` (20 dokumen analisis +
30 spesifikasi v2), `deploy/`, `scripts/`, `backend/`, `frontend/src/`, `test_reports/`, serta riwayat git.

**Batas klaim.** Ini kajian baca-saja. Aplikasi, gate, dan tes **tidak dijalankan ulang** di sesi ini.
Status "lulus" di bawah diambil dari dokumen dan laporan yang tersimpan. Basis data di repo berisi
**seed demo**, bukan data produksi. `CODEBASE_MAP.md` dirujuk oleh `plan.md`, tetapi berkasnya
**tidak ada** di repo.

Arti status: **Ada** = mesin backend, layar, dan penjaga (gate/tes) tersedia · **Parsial** = sebagian
tersedia, manual, atau masih mode simulasi · **Tidak ada** = tidak ditemukan di kode.

---

## 1. Ringkasan eksekutif

- Estora adalah ERP dan CRM untuk developer perumahan Indonesia yang mencakup seluruh alur,
  dari lead sampai garansi. Teknologinya FastAPI + MongoDB dengan React 19 PWA, dan ia dibangun
  lewat >100 fase bernomor (Fase 1 s.d. ±124).
- Ukuran kodenya ±92 ribu baris Python di luar tes, 111 router, ±1.019 endpoint API, 56 halaman
  staf, dan 1 portal pembeli. Ada 12 peran bawaan ditambah peran kustom.
- Keunggulannya ada pada **kedalaman keuangan properti**: GL double-entry berjurnal otomatis, AR
  per termin, refund pembatalan berjurnal, denda keterlambatan, pencairan KPR bertahap per bank,
  rekonsiliasi bank, tutup buku, dan ekspor faktur XML Coretax.
- Rantai bukti di lapangan juga kuat: jadwal bangun per unit berbukti foto ber-watermark, QC dan
  punch list, absensi dan upah harian, antrean offline PWA, BAST bergerbang, dan garansi per
  komponen.
- Kematangan tercatat: **70 gate verifikasi** (`scripts/run_all_gates.sh`), 107 berkas pytest
  (±842 fungsi tes), dan 18 skrip uji mutasi. Gate terakhir tercatat **OVERALL PASS (70 gates)**
  pada 2026-09-07.
- Satu instance disebut **produksi**, yaitu `hl5` untuk proyek **Harmony Land 5**. **Tidak ada
  bukti** jumlah pengguna, volume transaksi, pelanggan berbayar, ataupun developer kedua.
- Celah utama: tidak ada payment gateway/VA, tidak ada modul penghuni/IPL, tidak ada aplikasi
  native, tidak ada BIM/IoT/AI, tidak ada booking publik, dan tidak ada billing SaaS. WhatsApp
  dan iklan siap-live, tetapi pengiriman live belum dibuktikan di repo.

## 2. Skala dan arsitektur (terukur dari repo)

| Ukuran | Nilai | Bukti |
|---|---|---|
| Backend | ±91.600 baris Python (tanpa tes), 111 router, ±1.019 dekorator endpoint | `backend/`, `backend/routers/` |
| Frontend | 56 halaman staf + portal pembeli, 51 folder komponen, 748 berkas JS (±99 ribu baris) | `frontend/src/pages/`, `frontend/src/components/` |
| Stack | FastAPI, Motor/MongoDB 7, APScheduler (6 modul penjadwal), React 19 + Tailwind + shadcn, Tiptap, PDF.js, Recharts, ReportLab (PDF) | `backend/requirements.txt`, `frontend/package.json` |
| RBAC | 12 peran bawaan + peran kustom, ±66 resource izin, cakupan baris (all/own/project) | `backend/rbac.py`, `backend/rbac_matrix.py` |
| Dokumentasi | 20 dokumen analisis (`docs/analysis/00–19`) + 30 spesifikasi v2 (`docs/v2/20–52`) | `docs/` |
| Cara pengembangan | Dibangun lewat platform agen AI Emergent (commit "Auto-generated changes", iterasi "testing agent"). Repo pernah dipulihkan dari beberapa repo sumber. Perubahan kode produk terakhir **2026-10-02**. | `.emergent/emergent.yml`, `git log`, `plan.md` |

---

## 3. Inventaris per tahap siklus pengembangan perumahan

### (1) Lahan, perizinan, dan penyiapan proyek

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Hierarki proyek → cluster → blok → unit, ditambah tipe unit, add-on, dan komponen biaya | Ada | `backend/masterplan.py`, `backend/catalog.py` | Kode unit otomatis via `backend/numbering.py` |
| Site plan interaktif (SVG) dengan status jual/bangun | Ada | `backend/site_plan_svg.py`, `frontend/src/components/siteplan/PlotMap.js` | Dua status paralel dan palet terkonfigurasi (Fase 74) |
| Studio Site Plan: latar PDF/gambar, tracing poligon, auto-match label, undo, ekspor PNG, buat unit dari bentuk | Ada | `backend/site_plan_studio.py`, `frontend/src/pages/SitePlanStudioPage.js` | Jenis bentuk: kavling, jalan, hijau, air, fasilitas, batas. **Tanpa DWG/DXF** |
| Perizinan (KRK, IMB, PBG, SLF, AMDAL, ANDALALIN, pengesahan site plan, jenis kustom) per proyek/cluster/blok/unit | Ada | `backend/routers/permits_router.py`, `backend/permit_scope.py`, `frontend/src/pages/PermitsPage.js` | Lingkup izin per objek (Fase 46) |
| Peringatan masa berlaku izin, berupa notifikasi dan tugas ke PIC | Ada | `backend/permit_alerts.py` | Idempoten per hari |
| PSU / fasum-fasos | Parsial | `backend/rab_sections.py` (bagian RAB "Fasum/Fasos"), `backend/rab_engine.py` (`fasum_draft`) | Hanya sebagai biaya RAB, SPK, dan bentuk peta. **Tidak ada** alur serah terima PSU ke Pemda |
| Pembebasan lahan / studi kelayakan proyek | Tidak ada | Pencarian `pembebasan lahan`, `feasibility`, `tanah induk`: 0 hasil di kode | — |

### (2) Pemasaran dan lead

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Penangkap lead dari 6 webhook: Meta, Google, TikTok, website, WhatsApp, mitra | Ada | `backend/routers/webhooks_router.py`, `backend/engine.py` (`process_lead_capture`) | Dedup nomor, auto-assign sales, skoring |
| Atribusi first/last touch, `campaign_id` disimpan sebagai fakta | Ada | `backend/attribution.py`, `frontend/src/pages/AttributionPage.js` | Model atribusi diatur di Pusat Konfigurasi |
| Kampanye dan biaya iklan (input manual/CSV), adapter Meta/Google Ads | Parsial | `backend/ads_engine.py`, `backend/ads_adapters/meta.py`, `backend/ads_adapters/google.py` | Tanpa token = `simulation`. Biaya iklan masih manual/CSV (keputusan D1, `docs/v2/30`) |
| Umpan balik konversi (Meta CAPI, Google Enhanced Conversions, TikTok) dengan dedup `event_id` | Parsial | `backend/capi.py` | Live hanya bila kredensial terpasang |
| Showroom publik per proyek (tautan dan QR, peta kavling, harga bisa disembunyikan) dengan form lead | Ada | `backend/routers/public_router.py`, `frontend/src/pages/PublicShowroom.js` | Honeypot dan pembatas laju. Lead saja, **bukan booking** |
| Siklus hidup lead sebagai gerbang bukti (tahap tidak bisa dipilih bebas), skor lead berbasis event | Ada | `backend/lead_lifecycle.py`, `backend/lead_scoring.py` | Skor berbasis aturan, **bukan ML** |
| Survey lokasi, janji temu, kalender kerja | Ada | `backend/routers/survey_router.py`, `frontend/src/pages/AppointmentsPage.js` | Tahapan survey berpoin (`backend/survey_stages.py`) |
| Mitra/agen/broker: master, 7 skema fee (persen, nominal, berjenjang, per lead, …), konflik atribusi, webhook per mitra | Ada | `backend/partner_fee.py`, `backend/partner_engine.py`, `frontend/src/pages/PartnersPage.js` | Fee lahir dari event (reservasi s.d. AJB), berjurnal. **Tidak ada portal login mitra** |
| Marketing fee eksternal (potong PPh, approval) dan komisi sales internal berjenjang | Ada | `backend/marketing_fee.py`, `backend/routers/commissions_router.py` | — |
| Impor lead dari Excel/CSV (dry-run, upsert per HP) | Ada | `backend/routers/leads_router.py`, `memory/PRD.md` (2026-06) | Backlog: deteksi duplikat customer dan riwayat impor |

### (3) Penjualan dan booking

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Penawaran dan simulasi harga (harga per skema, add-on, termin) | Ada | `backend/quotation_engine.py`, `backend/unit_pricing.py` | Angka bisa direkonstruksi |
| Mesin harga: skema diskon, promo, kupon berkuota, approval manajer | Ada | `backend/pricing_engine.py`, `frontend/src/components/sales/PricingApprovalBadge.js` | Diskon tidak bisa diketik bebas |
| Satu jalur reservasi (keep unit dengan masa tahan) → booking → deal | Ada | `backend/sales_reserve.py`, `backend/routers/deals_router.py` | Masa tahan dikonfigurasi (`BOOKING_HOLD_DAYS`) |
| Booking fee sebagai tagihan (INV-BF) → kwitansi → titipan 2-1450 → dialihkan ke termin | Ada | `backend/booking_fee.py`, `frontend/src/components/sales/BookingFeePanel.js` | Bukti transfer bisa diunggah dari portal (`backend/routers/portal_booking_fee_router.py`) |
| Pra-skrining SLIK/BI sebagai gerbang sebelum booking | Parsial | `backend/slik.py`, `frontend/src/components/sales/LeadSlikPanel.js` | **Pencatatan manual berbukti iDeb**. Tidak ada API OJK (diakui di kode) |
| Konversi lead → pembeli, kontrak, tahap legal (PPJB → akad → pelunasan → BAST → AJB → SHGB) | Ada | `backend/customer_convert.py`, `backend/contracts_engine.py`, `backend/reference_p53.py` | Gate `verify_contract_legal_docgen.py` |
| Generator dokumen dari template asli owner (SPR Cash Keras, Cash Bertahap, KPR, SPKT), PDF berkop, editor naskah (Tiptap) | Ada | `backend/docgen.py`, `docs/source_templates/*.docx`, `backend/document_richtext.py` | Klausul diambil dari konfigurasi. 23 jenis dokumen di registry (memo verifikasi) |
| Pembanding SPR vs tagihan sebelum tanda tangan | Ada | `backend/spr_compare.py`, `frontend/src/components/finance/SprComparePanel.js` | — |
| Tanda tangan elektronik / e-meterai | Tidak ada | Pencarian `privy`, `peruri`, `e-meterai`: 0 hasil | — |

### (4) Pembiayaan

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Pipeline KPR: berkas → diajukan → appraisal → SP3K → akad kredit → pencairan, dengan gerbang bukti per tahap | Ada | `backend/kpr_engine.py`, `frontend/src/components/contracts/KprPanel.js` | SP3K wajib berkas dan plafon disetujui |
| Master produk KPR per bank (bunga fix/floating, tenor), impor Excel | Ada | `backend/routers/kpr_products_router.py` | — |
| **FLPP** | Parsial (minim) | `backend/routers/kpr_products_router.py:76` (baris preset "BTN · KPR Subsidi FLPP · 5% · tenor 120/180/240") | Hanya preset produk. **Tidak ada** cek kelayakan FLPP (batas penghasilan, rumah pertama), integrasi SiKasep/SiKumbang/Tapera, atau dokumen khusus subsidi |
| Selisih plafon SP3K vs porsi bank → termin pembeli otomatis | Ada | `backend/kpr_plafon.py` | Total piutang tetap |
| Pencairan KPR bertahap per skema bank (akad, serah terima, sertifikat), berkwitansi dan berjurnal, dashboard per bank | Ada | `backend/kpr_disburse.py`, `frontend/src/components/finance/KprBankDashboard.js` | Gate `verify_p75-78.py` |
| Simulasi angsuran anuitas (staf dan portal) | Ada | `backend/kpr_schedule.py` | Ditandai "simulasi, bukan angka bank" |
| Skema pembayaran terkonfigurasi: cash keras, cash bertahap (cicilan in-house, DP nominal/persen, jumlah cicilan, tanggal jatuh tempo, termin berbasis peristiwa) | Ada | `backend/payment_scheme_engine.py` | Gate `verify_payment_schemes.py` (mutasi 28 mutan) |
| Biaya all-in vs exclude per komponen (BPHTB, notaris, BPN) → titipan/AP | Ada | `backend/allin_engine.py`, `backend/allin_amend.py` | — |
| Toleransi keterlambatan, denda berjurnal (Dr 1-1300 / Cr 4-1400), keringanan khusus Manajer Keuangan, denda terjadwal opsional | Ada | `backend/late_fee_engine.py`, `backend/late_fee_auto.py`, `backend/late_fee_report.py` | Gate `verify_late_fee.py` (67 pemeriksaan) |
| Tunggakan → kandidat pembatalan (diusulkan, tidak otomatis), surat peringatan | Ada | `backend/arrears_engine.py`, `frontend/src/components/finance/WarningLetterDialog.js` | — |
| Giro/cek mundur (PDC) | Ada | `backend/pdc_engine.py` | — |
| Pembiayaan korporat developer (kredit bank/leasing, jadwal angsuran) | Ada | `backend/loans.py`, `frontend/src/pages/CorporateFinancingPage.js` | — |

### (5) Keuangan dan akuntansi

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| GL double-entry, CoA properti, jurnal otomatis dari event (model kewajiban kontrak, selaras PSAK 72) | Ada | `backend/gl_engine.py`, `docs/analysis/15_FINANCE_MODEL_AND_TAX.md` | — |
| Pengakuan pendapatan dan HPP saat BAST dari RAB (bukan tebakan %) | Ada | `backend/revrec_cogs.py` | — |
| AR per termin, aging, penagihan, dan AP (tagihan vendor/subkon, retensi) | Ada | `backend/routers/ar_router.py`, `backend/finance_ap.py`, `frontend/src/components/finance/ArPanel.js` | — |
| Bukti transfer pelanggan: diklaim pembeli, lalu diverifikasi finance | Ada | `backend/payment_intake.py`, `frontend/src/components/finance/PaymentIntakePanel.js` | — |
| Kas dan bank: sub-akun per rekening, impor mutasi, pencocokan, rekonsiliasi, kunci periode per rekening | Ada | `backend/cash_bank.py`, `backend/bank_import.py`, `backend/bank_recon.py`, `backend/cash_period_lock.py` | Impor mutasi via berkas, **bukan API bank** |
| Pembatalan dan refund berjurnal (potongan 35%/50%, pemisahan tugas pengaju ≠ pemutus ≠ pembayar), laporan utang refund 2-1460 | Ada | `backend/cancellation_engine.py`, `backend/refund_debt.py` | Gate `verify_cancellation_refund.py` |
| Tutup buku bergerbang (bulan/tahun, reversible), paket laporan bulanan owner | Ada | `backend/closing_engine.py`, `backend/owner_pack.py` | — |
| Laporan neraca, laba-rugi, arus kas, laba per proyek | Ada | `backend/gl_reports.py`, `frontend/src/pages/AccountingReportsPage.js` | Gate `verify_gl_reconciliation.py` |
| Pajak: PPN, PPh Final 4(2), BPHTB, faktur pengganti/batal, **ekspor XML Coretax**, e-Bupot | Ada | `backend/tax_engine.py`, `backend/tax_faktur_export.py` | Ekspor berkas, bukan API DJP |
| Pengajuan dana (dengan bukti bayar), kas bon, petty expense, aset tetap dan penyusutan | Ada | `backend/fund_requests.py`, `backend/petty_cash.py`, `backend/fixed_assets.py` | — |
| Anggaran 3 lapis (rencana, komitmen, realisasi) dan target proyek | Ada | `backend/budget_engine.py`, `backend/target_engine.py` | — |
| BI dan analitik per persona, KPI dengan drilldown (angka kartu = jumlah baris) | Ada | `backend/analytics_engine.py`, `backend/metrics/`, `frontend/src/pages/BiPage.js` | Audit menyeluruh BI non-lead **belum ditutup** (memo verifikasi) |

### (6) Konstruksi dan QC

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| RAB/BoQ per tipe unit, add-on, fasum, umum: versi, salin dari tipe lain, impor Excel, akses per bagian | Ada | `backend/rab_engine.py`, `backend/rab_sections.py`, `frontend/src/pages/BoQPage.js` | Gate `verify_p80_81.py` |
| Jadwal bangun per unit berbukti: template, mulai → ajukan hasil dan foto → verifikasi (verifikator ≠ pengaju) | Ada | `backend/build_engine.py`, `frontend/src/components/construction/ForemanBoard.js` | "Papan Mandor" |
| Gerbang mulai bangun (misalnya DP diterima), pantauan deviasi, eskalasi telat, kurva-S, kalibrasi template | Ada | `backend/build_readiness.py`, `backend/build_monitor.py`, `backend/build_calibration.py` | — |
| Foto: kompresi, hapus EXIF/GPS, watermark proyek/kavling dan waktu WIB | Ada | `backend/photo_utils.py` | — |
| QC/inspeksi checklist → punch list otomatis, buku harian proyek | Ada | `backend/routers/inspection_router.py`, `backend/routers/field_router.py` | — |
| Absensi dan upah harian tenaga kerja, berjurnal | Ada | `backend/labor_engine.py` | — |
| Pengadaan: permintaan → PO, 3-way match yang menahan, retur, master vendor, uji kewajaran harga, stok, transfer antar proyek | Ada | `backend/procurement_extra.py`, `backend/vendor_engine.py`, `backend/stock_control.py` | Gate `verify_procurement_vendor.py`, `verify_stock_control.py` |
| Subkon: SPK dari RAB, opname berbasis item terverifikasi, uang muka, potongan, retensi | Ada | `backend/opname.py`, `backend/subcon_finance.py`, `backend/routers/spk_scope_router.py` | — |
| BIM / digital twin / IoT / sensor | Tidak ada | Pencarian `BIM`, `IoT`: 0 hasil | — |

### (7) Serah terima dan purna jual

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| BAST bernomor dengan checklist penahan (punch list terbuka, inspeksi, kewajiban bayar), terobosan wajib beralasan | Ada | `backend/handover_engine.py`, `frontend/src/components/handover/HandoverChecklistPanel.js` | Gate `verify_handover_warranty.py` |
| Garansi per bagian (struktur, atap, plumbing, …), mulai dari tanggal BAST | Ada | `backend/handover_engine.py`, `frontend/src/components/handover/WarrantyBoardPanel.js` | — |
| Klaim garansi dari portal dan pengakuan pembeli. Retensi subkon dikaitkan ke klaim garansi | Ada | `backend/routers/portal_router.py` (`/warranty/claims`), `docs/v2/46_RETENTION_WARRANTY_SPEC.md` | Gate `verify_portal_warranty.py`, `verify_retention_warranty.py` |
| Komplain dengan SLA 48 jam, tugas ke PIC, penanda SLA terlewati, dashboard | Ada | `backend/routers/complaints_router.py`, `frontend/src/pages/ComplaintsPage.js` | SLA tetap 48 jam di kode |
| Modul penghuni / estate management / IPL | Tidak ada | Pencarian `IPL`, `iuran pengelolaan`, `penghuni`: 0 hasil | — |

### (8) Portal pembeli dan komunikasi

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Portal pembeli login OTP via WhatsApp (token portal terpisah dari staf) | Ada | `backend/routers/portal_router.py`, `backend/portal_security.py`, `frontend/src/pages/portal/PortalApp.js` | OTP master acak per instance saat deploy (`deploy/add_instance.sh`) |
| Isi portal: ringkasan, pembayaran dan unggah bukti, booking fee, status KPR dan simulasi angsuran, progres dan foto, site plan, dokumen PDF, kwitansi, BAST, garansi, komplain, pembatalan, denda | Ada | `frontend/src/components/portal/panels/` (10 panel) | Gate `verify_portal_proof.py` |
| WhatsApp Cloud API (Meta) lewat satu gateway, webhook bertanda tangan, outbox, kredensial terenkripsi | Parsial | `backend/wa_gateway.py`, `backend/wa_inbound.py`, `backend/routers/webhooks_router.py` | Bawaan `simulation`. **Pengiriman live belum dibuktikan di repo** (memo verifikasi §5) |
| Kepatuhan WA: template wajib approved, opt-out, jam kirim, broadcast tanpa status karangan | Ada | `backend/wa_compliance.py`, `backend/wa_template_governance.py`, `backend/routers/broadcasts_router.py` | — |
| Playbook WA per tahap lead, pengingat otomatis (jatuh tempo, tunggakan, garansi), balasan cerdas berbasis aturan (tanpa LLM) | Ada | `backend/wa_playbooks.py`, `backend/wa_reminder_engine.py`, `backend/wa_suggest.py` | — |
| Inbox percakapan, WA capture, kirim dokumen via tautan berbatas waktu ke vendor/subkon | Ada | `frontend/src/pages/InboxPage.js`, `backend/doc_share.py` | — |
| Notifikasi in-app real-time (WebSocket), pusat notifikasi berkelompok, preferensi per pengguna | Ada | `backend/routers/realtime_router.py`, `backend/notif_center.py`, `backend/notif_prefs.py` | — |
| Email (SMTP) / ringkasan harian | Tidak ada | Pencarian `smtp`, `sendgrid`: 0 hasil. Backlog di `memory/PRD.md` | — |

### (9) Platform

| Kemampuan | Status | Bukti (file) | Catatan |
|---|---|---|---|
| Multi-tenant (`org_id` di semua data), onboarding tenant dan owner, pindah organisasi oleh super admin | Ada | `backend/routers/orgs_router.py`, `backend/db.py` ("internal-first … for future SaaS") | Dideploy sebagai **instance terpisah per klien** (`deploy/compose.instance.yml`) |
| RBAC terkonfigurasi: matriks dan editor "Per Peran", peran kustom, cakupan baris, akses per bagian RAB, log audit | Ada | `backend/rbac.py`, `frontend/src/pages/AdminPermissions.js`, `frontend/src/pages/AuditLogsPage.js` | Gate `verify_rbac.py`, `verify_rbac_ui.py` |
| Pusat Konfigurasi (aturan bisnis tanpa deploy), penomoran dokumen terkonfigurasi | Ada | `backend/settings_store.py`, `backend/numbering.py`, `frontend/src/pages/ConfigCenterPage.js` | — |
| Work Hub: tugas per divisi dan jobdesk, katalog event | Ada | `backend/workhub.py`, `backend/jobdesk_catalog.py`, `docs/analysis/19_EVENT_AND_JOBDESK_CATALOG.md` | — |
| Manajemen data: impor master dari Excel (dry-run), ekspor, backup/restore JSON per organisasi, hapus massal | Ada | `backend/data_mgmt_import.py`, `backend/data_mgmt_backup.py`, `frontend/src/pages/DataManagementPage.js` | — |
| Halaman legal publik (privasi, S&K, penghapusan data, ID+EN) | Ada | `backend/legal_pages.py`, `frontend/src/pages/LegalPublicPage.js` | Untuk UU PDP dan verifikasi Meta |
| Ketahanan sesi (refresh token, 401 jujur) | Ada | `docs/v2/49_SESSION_RESILIENCE_SPEC.md` | Gate `verify_session_resilience.py` |
| PWA offline (cangkang aplikasi di-cache, antrean IndexedDB untuk pengajuan bangun, absensi, buku harian, punch list) | Ada | `frontend/public/service-worker.js`, `frontend/public/manifest.json`, `backend/offline_intake.py` | Gate `verify_offline_queue.py`. **Bukan aplikasi native** |
| Deploy: Docker Compose (Mongo + FastAPI + nginx/React), Caddy HTTPS otomatis, multi-instance, backup, update, migrasi dengan rollback otomatis | Ada | `deploy/install_vps.sh`, `deploy/migrate_estora.sh`, `deploy/update.sh`, `deploy/backup.sh`, `docs/DEPLOY_VPS.md` | Lihat §4 tentang status eksekusi |

---

## 4. Sinyal kematangan

| Sinyal | Temuan | Bukti |
|---|---|---|
| Gate verifikasi | **70 skrip gate** terdaftar dan semuanya ada. 71 `verify_*.py`, 146 skrip di `scripts/` | `scripts/run_all_gates.sh` |
| Hasil gate terakhir tercatat | **OVERALL PASS (70 gates)**, seed bersih dan run ulang, 2026-09-07 | `memory/VERIFIKASI_SIPRO_2026-09-06.md` (log `memory/verification/*.log` **tidak ikut di-commit**) |
| Uji mutasi | 18 skrip `mutasi_*.py`. TSV tersimpan: 279 mutan tertangkap, 24 lolos (dari 303). `plan.md` mengklaim 49/49 (Fase 56) dan 31/31 (Fase 58), berbeda dari TSV (kemungkinan TSV dari run lebih lama) | `memory/gatelogs/mutasi_*_hasil.tsv`, `plan.md` |
| Pytest | 107 berkas `backend/tests/test_*.py` (±842 fungsi), 6 smoke di `tests/`, 13 berkas tes lama di `backend/` | `backend/tests/`, `tests/` |
| Laporan uji | 46 laporan JSON testing agent (iterasi 41–46: 100% untuk alur yang diuji). 39 XML pytest historis (agregat 466 kasus, 5 gagal, 4 skip). `verified-final.xml` 48/48 lulus (2026-09-06) | `test_reports/` |
| Yang secara eksplisit **belum boleh diklaim** | Suite pytest lama belum mandiri. Audit angka GL/BI/pajak menyeluruh belum ditutup. Audit visual belum mencakup semua dialog dan peran. WA live belum dibuktikan | `memory/VERIFIKASI_SIPRO_2026-09-06.md` §"Yang belum boleh diklaim selesai" |
| Disiplin kode | Batas 800 baris per berkas dijaga gate. Klausul "SSOT, satu mesin" konsisten di header modul | `scripts/validate_compliance.py`, `plan.md` §3b |
| Deploy dan domain | Instance `hl5` di VPS (dulu `hl5.portalsipro.com`) disebut "**data produksi yang sekarang**". Migrasi ke `hl5.estora.id` + `demo` + `trial` sudah disiapkan, tetapi per commit 2026-10-02 **"belum dijalankan di VPS sungguhan"** (baru diuji dengan simulasi Docker). Status live saat ini **tidak diverifikasi** | `docs/DOMAIN_ESTORA.md`, `docs/DEPLOY_VPS.md`, commit `262525f` |
| Aktivitas pengembangan | Jejak paling awal "Implemented (2026-06)", spesifikasi v2 16 Agu 2026, perubahan kode terakhir 2026-10-02. Sesudahnya hanya catatan riset | `memory/PRD.md`, `docs/v2/20_INDEX_V2.md`, `git log` |

## 5. Bukti pelanggan / pengguna nyata

| Pertanyaan | Jawaban berbasis repo |
|---|---|
| Ada instance produksi? | **Ya, satu**: `hl5` untuk **Harmony Land 5**. Template SPR/SPKT asli owner memuat developer "PT. Harmony Cahaya Land" (`docs/source_templates/`, `docs/v2/27_DOCGEN_SPEC.md`). Nama org bawaan "Harmony Land 5" (`backend/db.py`). Dokumen menyebut link portal pembeli dan WA lama "tetap jalan" (`docs/DOMAIN_ESTORA.md`) |
| Siapa penggunanya? | Tampaknya developer pemilik produk sendiri ("internal-first"). Fitur digerakkan "catatan owner" (`backend/tests/test_owner_notes_2026_09_12.py`, `backend/docgen.py`) |
| Jumlah pengguna, unit terjual lewat sistem, transaksi, pembeli di portal? | **Tidak ada bukti** di repo. DB repo adalah seed demo |
| Pelanggan berbayar / developer kedua / testimoni / kontrak / harga langganan? | **Tidak ada bukti**. Instance `demo`/`trial` direncanakan untuk "calon klien" (commit `262525f`). Tidak ada modul billing SaaS |
| Kesimpulan | **Belum ada bukti pelanggan eksternal maupun metrik pemakaian.** Klaim yang aman: "dipakai di 1 proyek perumahan (HL5) sebagai instance produksi". Angka pemakaian harus diambil langsung dari instance produksi sebelum dicantumkan di deck |

## 6. Celah (ada/tidak) dengan bukti

| Item | Status | Bukti |
|---|---|---|
| Payment gateway / Virtual Account online | **Tidak ada**. "virtual_account" hanya label metode bayar. Pembayaran = transfer manual + unggah bukti + verifikasi finance + impor mutasi | `backend/reference.py:77`, `backend/payment_intake.py`. Pencarian `midtrans`, `xendit`: 0 |
| Modul penghuni / IPL / estate management | **Tidak ada** | Pencarian `IPL`, `penghuni`: 0 |
| Aplikasi mobile native | **Tidak ada**. Hanya PWA (start_url Papan Mandor) | Tidak ada folder `android/`/`ios/` atau react-native/capacitor. Lihat `frontend/public/manifest.json` |
| BIM / digital twin / IoT | **Tidak ada**. Site plan 2D SVG/PDF | Pencarian `BIM`, `IoT`: 0 |
| Booking/reservasi publik oleh pembeli | **Tidak ada**. Showroom publik hanya menangkap lead. Reservasi dilakukan staf | `backend/routers/public_router.py` (hanya GET showroom + POST lead) |
| FLPP / KPR subsidi end-to-end | **Parsial minim**. Ada preset produk BTN FLPP, tidak ada kelayakan atau integrasi SiKasep/SiKumbang/Tapera | `backend/routers/kpr_products_router.py:76`. Pencarian `sikasep`, `sikumbang`, `tapera`: 0 |
| Integrasi API bank/BTN (pengajuan KPR, SP3K, mutasi) | **Tidak ada**. SP3K diunggah manual, mutasi diimpor dari berkas | `backend/kpr_engine.py`, `backend/bank_import.py` |
| SLIK otomatis | **Tidak ada** (dicatat manual + bukti iDeb) | `backend/slik.py` |
| WhatsApp/Meta/Google Ads live | **Siap-live, belum terbukti live** di repo | `backend/wa_gateway.py`, `memory/VERIFIKASI_SIPRO_2026-09-06.md` |
| AI/LLM | **Tidak dipakai**. Skor lead dan balasan cerdas berbasis aturan. Paket `openai`/`litellm` ada di requirements tetapi tidak dipanggil kode | `backend/wa_suggest.py`, `backend/lead_scoring.py` |
| E-sign / e-meterai | **Tidak ada** | Pencarian `privy`, `peruri`, `meterai`: 0 |
| Email / ringkasan harian | **Tidak ada** (backlog) | `memory/PRD.md` |
| Billing/langganan SaaS, self-signup tenant | **Tidak ada**. Tenant dibuat super admin, instance dibuat skrip | `backend/routers/orgs_router.py`, `deploy/add_instance.sh` |
| Portal mitra/agen (login mitra) | **Tidak ada**. Mitra hanya lewat webhook dan dikelola staf | `backend/routers/partners_router.py` |
| Serah terima PSU ke Pemda, pecah sertifikat | **Tidak ada**. Hanya tahap legal "sertifikat (SHGB) diserahkan" | `backend/reference_p53.py` |
| Pembebasan lahan / feasibility | **Tidak ada** | Pencarian: 0 |
| Peta (Google Maps) | **Tidak ada** | Pencarian `google maps`, `leaflet`: 0 |

## 7. Implikasi singkat untuk deck dan BTN Housingpreneur

(Kriteria dari `btn_housingpreneur_kriteria.md` di folder ini.)

- **Housing Ecosystem** (jalur Developer) paling cocok. Cakupannya memang "perencanaan → pengadaan →
  konstruksi → distribusi → layanan purna jual", dan semuanya punya bukti di §3 (1)–(7). Bobot
  "Keunggulan & Kematangan Teknologi 25%" bisa ditopang oleh 70 gate, uji mutasi, dan
  keuangan/akuntansi berjurnal.
- Bobot "Kelayakan Bisnis 20%" dan "Skalabilitas 20%" lemah buktinya. Hanya ada 1 instance produksi,
  tanpa metrik, tanpa model harga, dan tanpa billing. Deployment multi-instance siap tetapi belum
  dieksekusi (per 2026-10-02). Perlu data pemakaian HL5 dan rencana harga.
- Syarat "usaha ≥ 2 tahun / inovasi sudah diimplementasikan": jejak pengembangan Estora di repo baru
  sejak ±Juni 2026. Kelayakan jalur Developer bergantung pada umur usaha developer pengusung, bukan
  umur produk. Kalau tidak memenuhi, jalur Umum › Housing Innovation (contoh resminya "platform
  terintegrasi pencarian, pembiayaan, pengelolaan hunian") lebih realistis.
- Kecocokan dengan BTN: master produk KPR per bank, preset BTN FLPP, pencairan bertahap per skema
  bank, dan dashboard pencairan per bank sudah ada. FLPP end-to-end dan integrasi API bank **belum**
  ada. Jangan mengklaim integrasi BTN.
- Celah yang paling terlihat juri Housing Tech (IoT, BIM, aplikasi native, pembayaran online)
  sebaiknya diposisikan sebagai roadmap, bukan fitur.

## 8. Catatan kredensial

Repo memuat kredensial bawaan (akun super admin/demo di `memory/PRD.md`, `docs/DEPLOY_VPS.md`, dan pesan
commit) serta berkas token uji di `memory/tmp/`. Nilainya **tidak disalin** ke catatan ini.
Sandi bawaan yang lemah disebut berlaku juga untuk instance produksi `hl5`. Kredensial ini sebaiknya
dirotasi sebelum repo atau dokumen apa pun dibagikan ke juri atau pihak luar.
