# PRD — Kain Nusantara ERP (lanjutan dari repo github.com/kakjsbsbs/KN)

## Problem statement (asli, 2026-09-17)
Lanjutkan development repo KN. Fitur dispatch/pengiriman masih sangat basic: tidak ada quick action di dasbor
(hanya list yang harus buat dispatch), belum ada history pengiriman, visualisasi status pengiriman yang sedang
diproses, ketersediaan armada internal, jenis pengiriman (kurir pihak ketiga dll). Pertanyaan: bagaimana fitur
customer ambil sendiri & validasinya? Data pengiriman (alamat kirim) masih bocor/terekspos pada SO yang ambil sendiri.

## Pilihan user
- Bangun semua sekaligus: dasbor dispatch + quick action, visualisasi status, ketersediaan armada, jenis pengiriman
  (internal / kurir pihak ketiga / ambil sendiri), history.
- Ambil sendiri: kode pickup unik + verifikasi identitas pengambil (nama + no. ID), tanpa driver/armada/alamat kirim.
- Kurir pihak ketiga: nama kurir, no. resi, biaya kirim, estimasi tiba.
- Armada: master kendaraan + driver dengan status (tersedia / dalam perjalanan / perawatan), status berubah otomatis.

## Arsitektur (yang disentuh)
- Backend FastAPI: `services/logistics_service.py` (moda self_pickup, kode pickup, handover, dashboard, history, redaksi kode),
  `services/fleet_service.py` (baru — master kendaraan `fleet_vehicles`, status sopir turunan), `routers/logistics.py`
  (endpoint baru), `schemas_logistics.py`, `entity_scope.py` (+fleet_vehicles scoped), `services/so_verify_service.py`
  (anti-bocor alamat pada SO ambil).
- Frontend React: `features/logistics/` → `LogisticsView` (tab Dasbor/Daftar/Riwayat/Armada), `DispatchDashboard`,
  `HistoryPanel`, `FleetPanel`, `PickupHandoverPanel`, `DeliveryCreateModal` (moda otomatis dari metode pemenuhan SO),
  `DeliveryDetailModal` (cabang pickup), `sales_admin/OrderPreviewCard` (sembunyikan alamat untuk SO ambil).
- Frontend TIDAK hot-reload: `setsid nohup bash /app/scripts/rebuild_frontend.sh > /app/.rebuild.out 2>&1 &`.
- Env: backend/.env CORS_ORIGINS harus daftar origin eksplisit (bukan `*`).

## Persona
Admin gudang / manajer (buat & kelola pengiriman, armada), petugas gudang (serah terima pickup), sopir (tugas hari ini),
sales / admin sales (pantau, bagikan kode pickup ke pelanggan).

## Sudah diimplementasikan (2026-09-17)
- Dasbor Pengiriman: KPI (SJ menunggu, menunggu diambil, diproses, di jalan, ETA hari ini, terlambat, terkirim hari ini),
  aksi cepat per SJ (Buat pengiriman / Siapkan pickup), antrean serah terima pickup, alur status (bar), moda (donut),
  ringkasan armada, daftar sedang diproses, baru selesai/gagal.
- Jenis pengiriman: Ekspedisi (kurir, resi, layanan, biaya kirim, ETA) · Armada sendiri (kendaraan master + sopir) ·
  Diambil pelanggan (kode pickup 6 karakter, tanggal ambil).
- Validasi ambil sendiri: SO `fulfillment_method=ambil` wajib moda self_pickup (dan sebaliknya ditolak); tidak ada
  alamat/plat/sopir; tahapan hanya lewat POST pickup-handover (kode cocok + nama pengambil [+ no. ID]); kode salah
  ditolak & dihitung; kode disembunyikan dari peran gudang/sopir (mereka mencocokkan kode yang disebut pengambil).
- Anti-bocor: `shipments/unassigned` & `order_preview` tidak mengirim alamat kirim untuk SO ambil.
- Riwayat: filter tanggal/moda/status/kata kunci, statistik (terkirim, gagal, rata-rata hari, total biaya ekspedisi), CSV.
- Armada: CRUD kendaraan, perawatan ⇄ tersedia, otomatis on_trip saat berangkat & lepas saat tiba/gagal/selesai,
  status sopir turunan dari pengiriman aktif; kendaraan maintenance/on_trip tak bisa dipilih.
- Seed demo: `scripts/seed_dispatch_demo.py`; smoke API: `scripts/smoke_dispatch.sh`.

## Setup ulang 2026-09-18 (repo nakisbdvsb/KN)
- Repo di-overlay ke /app (`.env` dipertahankan; CORS_ORIGINS diisi origin preview eksplisit — wajib, server menolak `*`).
- pip: filter baris `emergentintegrations`/`litellm` (konflik pin; sudah ada di base image). FE: `yarn install --frozen-lockfile` + `bash scripts/rebuild_frontend.sh`.
- Seed: `python seed_realistic.py` → `scripts/seed_dispatch_demo.py` → `backfill_po_payment_due.py` → `seed_endek_showcase.py` → `seed_design_scores_demo.py`.
- Verifikasi: `/api/logistics/dashboard` mengembalikan 5 pengiriman demo; UI Dasbor Pengiriman render (screenshot).
- Temuan kecil: `OrderJourneyPanel` menampilkan "Armada sendiri" untuk moda self_pickup (belum ada cabang pickup) → masuk P1 di bawah.

## Sinkron Permintaan Desain ↔ Design Studio (2026-09-18)
- Permintaan Desain kini memakai master kategori yang SAMA dengan Design Studio (Kategori Pattern + Kategori Design)
  menggantikan `target_type` legacy (tetap diterima API). Modal buat permintaan 3 bagian (sumber · apa · siapa/kapan).
- Desainer: dari detail permintaan → "Buat & buka desain" (`POST /design-requests/{id}/create-design`: desain Studio dibuat
  dengan kode otomatis, brief/kategori/lini ikut, tertaut dua arah `request_id`, permintaan → Dikerjakan) atau "Tautkan
  yang sudah ada" (`/link-design`; hanya desain berjalan & belum tertaut).
- Status permintaan MENGIKUTI siklus hidup desain (`design_studio_service.transition` → `sync_from_design`):
  submit → Menunggu keputusan · request_revision → Minta revisi (+revision_count, alasan) · approve → ACC.
  approve/reject langsung di permintaan yang tertaut Studio ditolak 400 (keputusan + nilai di halaman desain).
- UI: detail 2 kolom (brief, desain tertaut dengan cover/status/nilai, riwayat | fakta, tindakan), stepper status,
  kartu papan menampilkan kategori, pelanggan/SO, kode & status desain, desainer, tenggat. Deep-link `openRnd({view:"rnd-designs", designId})`
  → `RndDesignsView` prop `focus`. Halaman desain menampilkan chip "Dari permintaan …".
- Seed `seed_design_requests()` memakai alur sinkron. Uji: `backend/tests/test_iter319_dsr_studio_sync.py` (9/9), iteration_28.

## Galeri Referensi Brief (2026-09-18)
- `design_requests.references[]` (storage scope `design_requests`): POST/GET/DELETE `/design-requests/{id}/references[/{fid}]`
  (unggah/hapus izin `design_request.create` = pembuat permintaan; hanya gambar; status belum ACC/batal).
- `_propagate_references` menyalin ke desain tertaut sebagai berkas `kind=reference` (penanda `source_reference_id`, idempoten)
  saat create-design / link-design dan saat referensi baru ditambah setelah tertaut.
- UI: `ReferenceGallery.jsx` — pratinjau lokal di modal buat (diunggah setelah permintaan tercipta), galeri + unggah/hapus di
  detail, thumbnail kecil di kartu papan.

## Permintaan Sample R&D — UI baru cermin alur Desainer (2026-09-18)
- Setup ulang dari repo gatadadavaoa/KN (overlay ke /app, .env dipertahankan, CORS eksplisit, seed `seed_realistic.py`).
- Pilihan user: satu papan "Permintaan Sample" + rincian bergaya Studio dengan 3 TAB terpisah Labdip / Handfeel / Proofing;
  pembuat admin/manager/MD/sales; pengerja role MD (custom role & access diperbaiki nanti). Mekanisme server TIDAK diubah.
- Frontend `features/rnd/`: `RndSamplesView` (KPI, tab Papan/Daftar, chip jenis & status, kolom draft→decided,
  `SampleBoardCard`), `SampleFormModal` (FormModal 3 bagian bernomor: dari mana · apa yang disampling · kapan),
  `SampleDetailPanel` (DetailModal framed, kepala + stepper, 2 kolom, aksi kanan), `SampleTypeTabs` (tab per jenis,
  jenis yang belum diminta → tombol tambah via PATCH sample_types), `SampleRoundList` (+prop `onlyType`).
- `hubTabs`: rnd-samples kini juga untuk `md` & `sales_admin`. `navMeta` judul diperbarui.
- Testing agent iterasi 29: backend 5/5, frontend 100% (papan, filter, buat, tab jenis, kirim, batal, role MD).

## Galeri Bukti Per Tab (2026-09-18)
- `features/rnd/SampleProofGallery.jsx` (kolom per supplier, thumbnail tiap round dgn lencana R<n> & titik hasil, lightbox
  prev/next/Esc) + `ProofImage.jsx` (muat bukti via axios blob agar header Authorization/X-Entity-Id ikut; cache object URL).
- Dipasang di `SampleTypeTabs` setelah tabel perbandingan, hanya untuk jenis yang diminta. Testing agent iterasi 30: 100%.

## Tab per Jenis di hub R&D — Labdip / Handfeel / Proofing (Master) (2026-09-18)
- View baru `rnd-labdip`, `rnd-handfeel`, `rnd-proofing` → `features/rnd/SampleTypeGalleryView.jsx` (+ `SampleTypeCard.jsx`),
  cermin "Desain & Pattern (Master)": KPI, cari + saringan (status/supplier/hasil/skor/ronde/bukti), grid kartu bersampul
  foto bukti, tombol "Sampel <Jenis> Baru" (SampleFormModal `lockType`), klik kartu → rincian dengan tab jenis aktif
  (`initialType`). Dibatalkan disembunyikan kecuali difilter. Terdaftar di hubTabs/navMeta/roles/AppViewRouter.
- Testing agent iterasi 31: frontend 100% (MD + admin, buat dari tab, filter, regresi papan & desain).

### 2026-06 — Peran & Hak Akses (custom role, 3 tingkat per modul)
- Backend: `access_modules.py` (katalog 24 modul: label/deskripsi/resources/nav, `apply_levels`, `nav_for_levels`),
  `services/custom_role_service.py` (buat/ubah/hapus/reset; peran kustom tersimpan di `custom_roles`, matriks izin di
  `permission_settings.matrix`; registry `role_registry.register_custom_roles` disinkron saat start & tiap perubahan),
  router `/api/access/modules|roles` (izin permission.view/update). Admin dikunci; bawaan tidak bisa dihapus/ganti nama.
- Frontend: tab **Peran & Hak Akses** di Badan Usaha & Akses (`RoleAccessPanel`, `RoleEditorDrawer`, `RoleModuleRow`,
  `RoleMenuPreview`): kartu peran + jumlah akun, segmented 3 tingkat per modul, salin dari peran, semua-modul cepat,
  pratinjau menu nyata (buildNavGroups dgn overlay `__preview`), dialog konfirmasi perubahan, peringatan modul sensitif.
- `roles.js`: `registerDynamicRoles` (registry/ROLE_NAV/ROLE_HOME dinamis, ROLE_OPTIONS ikut → formulir akun),
  `roleCanSee` rekursif inherit. `App.js`: poll `/api/roles` + `/auth/me` tiap 60 dtk + event `kn:roles-changed`.
- Testing agent iterasi 32: backend 14/14, frontend 100%.
- Catatan lingkungan: frontend dilayani bundle statis → `bash scripts/rebuild_frontend.sh` setelah ubah src;
  backend/.env butuh CORS_ORIGINS eksplisit (bukan `*`).

### 2026-06 — Notifikasi sinkron dengan Peran & Hak Akses (iterasi 33)
- `services/notification_scope.py`: filter kotak notifikasi = audiens (peran/all/peran acuan/recipient_user) ∧ relevansi
  (link layar tujuan harus boleh dibuka: modul ≥ Lihat). Admin melihat SEMUA notifikasi kecuali yang ditujukan langsung
  (`recipient_user`) ke orang lain — perbaikan dari temuan iterasi 33 (sebelumnya admin hanya audiens admin/all).
- `services/turn_notification_service.py`: penerima "Giliran Anda" digerbang izin dari matriks (peran bawaan + kustom),
  admin/manager dikecualikan kecuali rule menyebutnya. `GET /api/access/roles/{id}` → `turn_alerts`; editor peran
  menampilkan `role-editor-turn-alerts`.
- Setup ulang env baru (2026-06): clone repo pandeyoga/KNHOST; peran kustom `cr_staf_penagihan` + akun penagihan@
  dibuat ulang via API (finance, accounting=view, ar=manage). Pytest `tests/test_notifications_iter33.py` 10/10 lulus.


### 2026-06 — Editor peran: pratinjau notifikasi live, duplikat peran, pindah akun massal
- Backend: `POST /api/access/roles/preview` (turn_alerts & screens dari tingkat yang belum disimpan),
  `POST /api/access/roles/{id}/move-users` (pindah semua akun ke peran lain; admin ditolak). Audit `role_users_moved`.
- Frontend: `RoleNotifPreview` (diff vs tersimpan: "(baru)"/"(hilang)"), tombol `role-card-duplicate-<id>` → editor
  mode duplikat (acuan = peran sumber; hanya modul yang diubah dikirim agar izin parsial tetap setia), panel pindah akun di
  `RoleAccountsList` dengan `RoleDangerDialog` kind "move"; editor tetap terbuka & disegarkan setelah pindah.
- Testing agent iterasi 37: backend 11/11, frontend 100%.

## Design Studio — Nilai hanya saat ACC · HOLD · Label Proofing · Riwayat detail (2026-09-18, repo pandeyoga/KNHOST)
Problem statement: lanjutkan ke Desainer — (1) point hanya di akhir ketika ACC; (2) desain ACC bisa di-HOLD → tidak bisa masuk proofing R&D,
label jelas + filter; label proofing (on progress / finished) + info master produk; navigasi cepat tanggal; (3) history lebih detail.
Pilihan user: hapus semua penilaian kecuali dialog ACC; hold oleh admin/manager (izin `rnd.hold`, dapat diatur di matriks akses);
acuan tanggal ACC & update terakhir (bisa dipilih); riwayat lengkap (diff field, berkas, hold, nilai, proofing & master produk) + filter jenis; seed demo repo.
- Backend: `design_studio_service` — `transition` hanya menyimpan nilai pada `approve` (revisi mengabaikan score), `activate` ditolak saat hold;
  `set_hold`/`release` (field `on_hold`, `hold`, `hold_history`, event `hold`/`release_hold`); `attach_proofing` (batch md_samples/md_specs/products →
  `proofing{state none|in_progress|finished|master, label, detail, samples[], specs[], master_product}`); `log_external` (peristiwa lintas modul).
  `design_gallery_service` — `update_gallery` menulis event `updated` + `changes[{field,label,from,to}]`, `delete_file` → `file_deleted`, unggah colorway ikut timeline,
  filter `on_hold`. `rnd_sample_service` — `_assert_design_not_held` (proofing ditolak saat HOLD) + hook `proofing_requested/finished/decided`.
  `rnd_spec_service` — hook `spec_linked`, `master_product_created`, `master_product_released`. Router: `POST /design-gallery/{id}/lifecycle/hold|release-hold`
  (izin `rnd.hold`), `GET /design-gallery/{id}/history?kind=`; endpoint `/versions/{v}/score` DIHAPUS. `permissions_config`: `rnd.hold` admin+manager (merge otomatis saat restart).
- Frontend: `RndDesignsView` (KPI hold/proofing/master klik-saring, filter `rnd-filter-hold|proofing`, `DateQuickNav`, kartu ber-lencana hold/proofing/master/tanggal),
  `DesignDetailPage` (lencana + banner hold, tab Proofing R&D `ProofingPanel`, tab Riwayat `HistoryPanel` menggantikan TimelinePanel), `LifecycleActions`
  (hold/lepas hold via `canHold`, nilai hanya di dialog ACC, revisi tanpa nilai), `VersionsPanel` tanpa tombol nilai, `DesignBadges`, `SampleFormModal` menandai desain HOLD.
- Seed demo: `scripts/seed_design_hold_proofing_demo.py`. Testing agent iterasi 39: backend 14/14, frontend 100%.


## Backlog
- P2 (Akses): ganti `window.confirm` hapus/reset peran dengan modal in-app — SELESAI 2026-06 (`RoleDangerDialog`).
- P2 (Akses): daftar akun pemakai peran di editor — SELESAI 2026-06 (`RoleAccountsList`, `accounts[]` di GET /api/access/roles/{id}).
- P2 (Akses): router tuple peran hardcoded mengenal peran kustom — SELESAI 2026-06 (`role_registry.role_in` di design_requests, internal_requests, rnd, rnd_org, dan `dependencies.require_role`; frontend `roleIs` di rnd/design/designer views; deep-link `?view=` untuk peran `cr_*` menunggu registrasi peran kustom). Testing agent iterasi 35–36: backend 100%, frontend 100%.
- P2 (RND): revoke object URL cache galeri bukti (LRU) untuk sesi panjang; kolom galeri responsif di layar sempit.
- P1 (RND): sticky footer/ringkasan aksi di rincian sample; skeleton KPI saat memuat (kilat 0 ~200ms).
- P1 (RND): testid per-supplier di `SampleSendModal` (`sample-send-supplier-<id>`); galeri foto bukti per tab jenis.
- P1 (RND): perbaikan custom role & access — SELESAI 2026-06 (lihat bagian Peran & Hak Akses).
- P1: notifikasi WA otomatis kode pickup ke pelanggan saat pengiriman pickup dibuat (sekarang tombol WA manual).
- P1: kadaluarsa kode pickup / regenerasi kode oleh admin; batas percobaan kode salah → kunci sementara.
- P1: tampilkan badge moda & kode pickup di Perjalanan Pesanan (OrderJourneyPanel) dan Meja Admin Gudang.
- P2: biaya kirim ekspedisi → jurnal beban pengiriman (GL) / tagihan ke pelanggan.
- P2: jadwal kendaraan (kalender), riwayat perawatan, KM.
- P2: peta posisi live untuk semua pengiriman aktif di dasbor.

---
## SESI 2026-09-18 — Lanjutan repo github.com/makkansbdb/KN: Desainer & R&D

### Problem statement (asli)
Desainer: (a) Ringkasan diperbaiki — tiap ronde revisi tampil ke bawah (judul ronde → foto dikirim → komentar revisi → ronde berikutnya…); tab "Ronde & Nilai" dihapus, nilai di akhir saat ACC. (b) Tab Final: tanpa varian warna — hanya mockup + file desain asli yang bisa diunduh. (c) Galeri Desain → showcase desain ACC saja (tanpa tambah), detail: foto, file asli, mockup, info desain & pattern, produk pemakai + status R&D; filter diperbanyak. (d) Rapikan pop-up.
R&D: (e) Interface labdip/handfeel/proofing seperti desainer: detail ronde, komentar sampai ACC, history, tanggal terima. (f) Spesifikasi produk dikonsolidasikan ke tab sample (input saat create). (g) Rapikan pop-up. (h) Nama & warna supplier diisi saat sampling ACC (bukan awal), sinkron ke master terkait. (i) UX master data yang lahir dari R&D dibuat jelas (varian / induk).
Pilihan user: clone ulang repo; Desainer dulu lalu R&D; nilai tetap satu kali di dialog ACC (tanpa duplikasi); dialog "Pilih pemenang" wajib isi warna supplier + otomatis buat/tautkan master data dengan preview.

### Implementasi (2026-09-18)
- Backend: `design_studio_service.final_requirement` → mockup≥1 + source≥1 (colorway tidak wajib); kind `source` (file bebas ≤50MB) di `add_file` & `upload_kind_file`; `GET files/{fid}?download=1` → attachment.
- Backend R&D: `SampleInput.spec` (spec dibuat & ditautkan saat create sample); `SampleDecideBody` + `supplier_color_name/code`, `approve_spec`, `product_sku/name`; `decide_sample` sinkron warna supplier ke `color_library.supplier_variants` (+factory_name), ACC spesifikasi → produk lahir; `master_data_of()` di GET sample.
- Frontend Desainer: `RoundsTimeline.jsx` (Ringkasan linimasa), tab versions dihapus, `FinalPanel`/`FilesPanel` (mockup + source), dialog ACC tanpa jumlah warna, `DesignImage.jsx` (gambar via axios blob).
- Frontend Galeri: `DesignGalleryView.jsx` showcase + 7 filter, `DesignShowcaseModal.jsx`.
- Frontend R&D: `SampleRoundList.jsx` linimasa per supplier×jenis (dikirim/tenggat/diterima, bukti, catatan, keputusan penilai), `DecideModal.jsx` 3 langkah + preview master data, `SampleMasterDataPanel.jsx`, `SampleFormModal.jsx` bagian 3 spesifikasi, tab hub "Spesifikasi Produk" dihapus.
- Env: `CORS_ORIGINS` di backend/.env wajib daftar origin (bukan '*'); frontend bundle statis → `bash scripts/rebuild_frontend.sh`.
- Uji: testing agent iterasi 40 — backend 8/8, frontend semua alur lolos.

### Backlog / P1–P2
- P1: audit pop-up lain di R&D (RoundActionModal, SampleSendModal, SampleFinishModal, IssueMaterialModal) untuk konsistensi font/spacing.
- P1: seed sample "assessed" ber-warna target agar field warna supplier langsung terlihat di demo.
- P2: hapus kode/komponen colorway yang tak lagi dipakai (ColorwaysPanel, VersionsPanel) bila sudah dipastikan tak dirujuk.
- P2: GET /api/color-library/{id} (saat ini hanya list) untuk layar detail warna versi supplier.

### 2026-09-19 — Pop-up R&D seragam + Riwayat warna supplier
- Refactor 5 pop-up R&D ke shell `FormModal` + `RndField` (Field/Hint/Footer): font 13.5px judul / 11px subjudul / 10.5px label / 11.5px isi, jarak `gap-3` seragam.
- Pustaka Warna: badge "N versi supplier" pada kartu → `SupplierColorVariantsModal` (supplier, nama & kode warna supplier, sampel asal dengan deep-link, tanggal ACC).

### 2026-09-19b — Pustaka Warna: sub-tab Warna Internal / Warna Supplier + keterkaitan
- Sub-tab terpisah; tab Warna Supplier = tabel versi warna per supplier (label supplier jelas), cari nama/kode warna supplier, filter supplier & "sudah/belum jadi produk".
- Modal keterkaitan 3 kolom: Warna internal ↔ Versi supplier ↔ Master produk (+ daftar sample R&D) — backend `color_links` & `list_supplier_variants` di color_service.

### 2026-09-19c — Spesifikasi WAJIB menyatu (1 sample = 1 spesifikasi)
- Koreksi user: tab Spesifikasi dihapus tetapi logikanya wajib & menyatu di form Labdip/Handfeel/Proofing (bukan opsional).
- Form 4 langkah (Acuan → Spesifikasi WAJIB adaptif per jenis → Brief → Kapan); server menolak sample tanpa spesifikasi; validasi per jenis.
- Panel Spesifikasi di rincian (ringkasan, ubah sebelum ACC, "Lengkapi spesifikasi" untuk data lama); ringkas spesifikasi di kartu.
- 2026-09-19d: dropdown "Acuan spesifikasi" dihapus (membingungkan); form 3 langkah; pesanan pelanggan dipindah ke langkah Brief. Anti-duplikasi spesifikasi lewat multi-jenis dalam satu permintaan / "Tambah jenis".

### 2026-09-19e — Dua warna (internal + supplier) visible di semua menu
- Denormalisasi warna internal, versi warna supplier (dilabeli supplier), dan supplier pemenang R&D ke master produk; disinkronkan saat ACC sampling / ACC spesifikasi (+ backfill).
- `ProductColorChip` dipakai di pemilih produk, PO (opsi & baris item, difilter supplier PO), RFQ, katalog (header & kartu varian), detail produk, panel master data R&D.

### 2026-09-19f — Special Order Fase 1
- Menu "Pesanan Khusus" di PENJUALAN (bawah Kasir & Portal). Intake terstruktur 4 langkah (pelanggan & tipe permintaan printing/labdip/handfeel; referensi; spesifikasi ringkas/lengkap; jumlah-harga-tenggat) + unggah referensi pelanggan.
- Routing otomatis saat disetujui: printing → Permintaan Desain (+referensi); labdip/handfeel → Spesifikasi + Permintaan Sample R&D (tertaut special_order_id, exclusive_customer_id). Rincian OD: lini masa fase + rantai dokumen (OD ↔ Desain ↔ Sample ↔ SKU ↔ PR/PO ↔ SO).
- Backlog Fase 2: ACC pelanggan atas sample, harga final (kontrak + margin), eksklusivitas SKU ditegakkan di Kasir/SO, PR/PO ke supplier pemenang, hapus "Buat SKU" ad hoc, proofing otomatis saat desain ACC, kartu ringkas di Meja Admin Sales.

### 2026-09-19g — Special Order Fase 2 (ACC pelanggan · harga final · eksklusivitas · proofing otomatis)
- Backend `services/special_order_phase2.py`: `customer_decide` (acc/revisi/tolak + catatan, tanggal, kontak; revisi → sample R&D baru otomatis dgn spesifikasi diwarisi, OD kembali Sampling; tolak → cancelled), bukti (`customer-decision/evidence`), `pricing_preview` (kontrak supplier pemenang + margin default 30% dari `system_settings{scope:special_order}.default_margin_pct`), `lock_price` (sales/sales_admin/manager/admin, wajib ACC pelanggan; harga & eksklusivitas ditulis ke master produk), `unlock_price` (admin + alasan, ditolak bila PR/SO sudah lahir), `assert_customer_allowed` (SO/POS ke pelanggan lain/walk-in → 400), `on_design_approved` (desain OD printing ACC → sample proofing + notifikasi MD).
- `special_order_routing`: fase baru `pricing`; `_phase` memakai sample terakhir (revisi) & kunci harga; `chain_of` → `review` + `pricing`. `approve_special_order` tak lagi membuat SKU ad hoc untuk OD terstruktur; PR/konversi SO OD terstruktur ditolak sebelum harga dikunci; PR memakai product_id & harga kontrak pemenang.
- `rnd_spec_service`: `exclusive_customer_id` diwariskan ke produk; `decide_sample` menstempel eksklusif pelanggan ke produk.
- Frontend: `SpecialOrderCustomerApprovalPanel.jsx`, `SpecialOrderPricingPanel.jsx` (di rincian OD setelah disetujui), badge "Eksklusif: <pelanggan>" di POS (`PosProductCard`), katalog (`VariantCard`), rantai OD.
- Testing agent iterasi 46: backend 9/9, frontend lolos. Catatan: relock setelah unlock membaca ulang harga kontrak sample pemenang terbaru (disengaja).

### Backlog Fase 3 OD
- P0: PR/PO otomatis ke supplier pemenang (pakai kontrak) + tracking produksi → konversi SO dengan harga final (tombol sudah digerbang kunci harga).
- P1: kartu ringkas OD di Meja Admin Sales; notifikasi WA ke pelanggan saat sample siap ACC.
- P1: routing OD printing mengisi Kategori Pattern/Design otomatis (sekarang desainer harus melengkapi via "Ubah" sebelum "Buat & buka desain").
- P2: pengaturan default margin OD di Pusat Pengaturan (sekarang hanya via DB `system_settings`).

### 2026-09-19h — Special Order Fase 3 (PR/PO otomatis · SO harga final · kategori desain otomatis)
- `lock_price` {margin_pct, warehouse_id, auto_po} → `auto_procure`: rilis SKU eksklusif ke produksi → PR (source special_order, "Sistem (OD)") → approve → PO ke supplier pemenang (harga kontrak pemenang; kontrak diikat ke product_id di `decide_sample`; jaminan harga di `auto_procure`), tenggat = expected_delivery OD, gudang default aktif pertama entitas → OD in_production. `POST /special-orders/{id}/procure` untuk ulang. PO completed (`recompute_po_status`) → OD ready. Supplier grup ditolak oleh aturan antar-entitas (pesan jelas).
- `convert-to-so` (in_production/ready + harga terkunci): SO memakai `pricing.product_id` & harga final terkunci (`special_order_price`, `cost_price`, `margin_pct` di baris SO) via `source_special_order_id` di `create_order`.
- OD printing: `pattern_category_code`/`design_category_code` di form intake (opsional) + fallback kategori pertama aktif → DSR siap "Buat & buka desain".
- `POST /special-orders/{id}/submit` (draft → pending_approval; OD dengan submit_for_approval selalu masuk persetujuan tanpa ambang). UI: tombol "Ajukan persetujuan", pilih gudang & toggle PR/PO otomatis di panel harga, chip PO, "Buat PR/PO sekarang".
- Testing agent iterasi 47 (17/18 → bug kontrak diperbaiki) & 48 (retest).

### 2026-09-19i — Special Order Fase 4 (pengiriman otomatis · kartu OD di Meja Admin Sales)
- lock-price (auto_po) → SO OD lahir otomatis (harga final). PO OD diterima gudang (`recompute_po_status` completed; atau setelah QC accept di `qc_service`) → `on_goods_received`: stok direservasi ke SO (backorder), SO confirmed otomatis, tugas Surat Jalan (outbound) lahir. `dispatch_task` → SJ terbit → OD shipped (`on_shipment_dispatched`); SO mark-delivered / logistik delivered → OD done (`on_delivered`). Kegagalan (mis. karantina QC) tercatat di `shipping_error`; tombol/endpoint `prepare-shipment` untuk mengulang. Panel `SpecialOrderShippingPanel` di rincian OD; `chain_of` → outbound_tasks & shipments.
- Meja Admin Sales: antrean `od_acc_pelanggan`, `od_kunci_harga`, `od_siap_kirim` (`work_desk_service` + `special_order_phase2.desk_rows`); ROW_TARGET special_order → deep-link `SpecialOrders` (`focusDoc`) langsung membuka rincian.
- Testing agent iterasi 49: backend 14/14, frontend lolos.
### Backlog OD
- P1: notifikasi WA ke pelanggan (sample siap ACC, barang siap kirim). P2: pengaturan margin OD di Pusat Pengaturan. P2: pengiriman fisik (pick/dispatch) tetap manual gudang — by design.

### 2026-09-19j — Modul Marketing & Sosial Media (baru)
- Backend `services/marketing_service.py` + `routers/marketing.py`: kampanye (`mkt_campaigns`), post (`mkt_posts`) dgn alur idea→draft→review→approved(manager/admin)→scheduled(publish_at+PIC)→published(+url), lampiran (storage), performa manual (metrics + history), bahan konten (desain galeri ACC/produk/OD), analitik per bulan/platform/kampanye, job scheduler `content_reminder` (15 mnt) → notifikasi PIC in-app/WA. Resource izin `marketing` (admin/manager penuh; designer/sales/sales_admin view/create/update). Modul akses "Marketing & Sosial Media".
- Frontend `features/marketing/`: ContentCalendar (bulan/daftar, filter, klik sel → buat), PostFormModal, PostDetailModal (aksi alur, lampiran, performa, riwayat), Campaigns, MarketingAnalytics. Menu standalone "Marketing & Sosmed" (hub marketing-hub: Kalender Konten · Kampanye · Performa).
- Testing agent iterasi 50: backend 30/30, frontend lolos. Tanpa AI & tanpa API sosmed (sesuai pilihan user).
### Backlog Marketing
- P1: template konten & duplikasi post; tampilan minggu; ekspor kalender PDF. P2: posting otomatis via Meta/TikTok API; AI caption (jika diinginkan); UTM link builder & pelacakan prospek ke CRM.

### 2026-09-19k — Marketing lanjutan: Akun Sosmed per PT · Dashboard · Ekspor PDF · Multi-entitas
- `services/marketing_ext.py`: master `mkt_accounts` (per badan usaha, banyak akun; validasi dup & kepemilikan PT/platform saat dipakai di post → snapshot `post.accounts`), `dashboard()` (KPI bulan ini vs lalu, tren 6 bulan, per platform/akun/PT, top, 7 hari ke depan, terlambat, tingkat tepat waktu ≤60 mnt), `calendar_pdf_html()` → weasyprint (A4 landscape, kop PT/Grup, grid, daftar rinci caption ≤120, ringkasan kampanye).
- Multi-entitas: posts/accounts/dashboard/PDF menerima `entity_id=all|ent_x` (resolve_list_scope); tiap respons post membawa `entity_name`; buat konten/akun selalu ke PT aktif (ditampilkan di form). UI mengikuti pemilih PT di header: badge PT di kalender/daftar/rincian saat "Semua".
- Tab hub: Kalender Konten (tombol Ekspor PDF) · Dashboard & Performa · Kampanye · Akun Sosmed. Testing agent iterasi 51 (16/16 + UI) & 52 (retest badge PT lolos).

### 2026-09-21 — Perapian UI Pesanan Khusus
- `SpecialOrderInfoPanels.jsx` ditulis ulang: panel Rincian item custom / Info pelanggan / Riwayat status memakai gaya seragam panel Fase 2–4 (section-card !p-3, kicker label, sel grid), label Bahasa Indonesia, tidak ada konten menempel tepi kartu; grid `items-start`. Popup Tolak → FormModal standar; label "Reject" → "Tolak"; kolom tabel "Expected Del." → "Perkiraan kirim". Testing agent iterasi 53: lolos (tanpa overflow).

---

## Sesi 2026-09-21 — Perbaikan fokus input form R&D (repo github.com/pandeyoga/KNHOST)

### Problem statement (asli)
"saya ingin anda lanjutkan development dari repo ini https://github.com/pandeyoga/KNHOST — perbaiki beberapa form di menu RND,
ketika saya buat labdip, proofing, dan handfeel ketika saya ingin isi form itu hanya setiap satu charakter saya harus klik kolom
form kembali sepertinya ada bug front end." Pilihan user: clone branch main; periksa & perbaiki semua form RND dengan pola sama.

### Akar masalah
`features/rnd/SampleSpecFields.jsx` mendefinisikan komponen pembungkus `L` DI DALAM fungsi render → tiap keystroke induk re-render,
referensi komponen baru → React unmount/remount `<input>` → fokus hilang. Pola sama di `features/rnd/design/FinalPanel.jsx` (`Row`).

### Yang dikerjakan
- `L` (SampleSpecFields) dan `Row` (FinalPanel) dipindah ke module scope. Berdampak ke form Labdip/Handfeel/Proofing
  (`sample-form-modal` dari `rnd-samples` & galeri `rnd-labdip|handfeel|proofing`) serta `SampleSpecPanel`.
- Audit pola yang sama di seluruh `frontend/src`: sisa kasus (LocationFields `L`, DocRefsPanel/ReallocateRollsModal `Row`,
  CoreWidgets `FavStar`, PdfEditorTabs `Diff`, DomainRegistryParts) TIDAK membungkus input → tidak menimbulkan bug fokus; dibiarkan.
- Lingkungan: backend/.env CORS_ORIGINS eksplisit + SESSION_COOKIE_SECURE; seed_realistic dijalankan; bundle frontend di-rebuild.
- Uji: testing agent iteration_54 — 21/21 field mempertahankan fokus saat mengetik kontinu di semua titik masuk.

### Catatan
- `sample-spec-sku` sengaja meng-uppercase ketikan (perilaku lama, bukan bug).
- Frontend statis: setelah ubah src → `setsid nohup bash /app/scripts/rebuild_frontend.sh > /app/.rebuild.out 2>&1 &` (±8 mnt).
