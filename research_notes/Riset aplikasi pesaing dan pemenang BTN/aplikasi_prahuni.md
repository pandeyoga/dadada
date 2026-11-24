# Aplikasi pra-serah-terima (prahuni) di siklus pengembangan perumahan Indonesia: benchmark tingkat aplikasi untuk Estora

Riset dilakukan 2026-11-24. Semua halaman store dan web diakses pada tanggal itu. Catatan ini melengkapi (tidak mengulang) `Riset kompetitor dan BTN Housingpreneur/proptech_saas_pesaing.md` (profil perusahaan, harga vendor) dan `Riset Rumah Ningrat dan aplikasinya/mitra_ningrat.md` (portal mitra Rumah Ningrat). Fokus di sini adalah **aplikasi**: fitur, alur, layar, dan ulasan.

**Metode dan batas.**
- Data Google Play diambil dari halaman listing publik (`play.google.com/store/apps/details?id=...&hl=id&gl=ID`) dengan Playwright. Yang diambil: header, dialog "Tentang aplikasi ini" (versi, tanggal update, tanggal rilis, jumlah unduhan), dan dialog "Lihat semua ulasan" (urutan "Paling relevan", jadi bukan selalu yang terbaru). Tanggal ulasan tanpa tahun di App Store berarti tahun 2026.
- Data iOS diambil dari iTunes Lookup API publik (`itunes.apple.com/lookup?id=...&country=id`) dan halaman publik `apps.apple.com/id/app/id...`. **Feed RSS ulasan iOS** (`itunes.apple.com/id/rss/customerreviews/id=.../sortby=mostrecent/json`) mengembalikan HTTP 200 tetapi **tanpa entri sama sekali** untuk semua aplikasi yang dicek, termasuk kontrol Instagram (US). Karena itu kutipan iOS diambil dari halaman App Store web.
- Tidak ada login, registrasi, uji coba, atau pemanggilan API internal. Isi aplikasi di balik login hanya dinilai dari screenshot resmi di store. Screenshot adalah materi pemasaran vendor dan bisa memakai data demo.
- Penanda: **[Terverifikasi]** = terlihat di listing/screenshot/halaman resmi; **[Klaim]** = hanya teks deskripsi vendor; **[Inferensi]** = kesimpulan saya.

---

## 1. Aplikasi bank dan pemerintah: BTN Properti for Developer / balé developer, bale by BTN (Bale Properti), Tapera Mobile (eks SiKasep)

### Takeaway
Ekosistem BTN memberi developer alat **gratis** untuk stok unit, SPR otomatis, VA booking fee/DP, dan pengajuan KPR BTN. Pembeli melacak KPR dari bale by BTN, dan untuk subsidi dari Tapera Mobile. Ketiga aplikasi ini memiliki keluhan yang sama: login/OTP gagal. Di Tapera muncul juga keluhan status antar sistem yang tidak sinkron (Tapera vs bank penyalur), data yang tidak bisa diedit atau dibatalkan, dan stok "unit ready" yang tidak akurat. Celah inilah yang bisa diisi Estora sebagai "sumber kebenaran" status per unit dan per pembeli, **berdampingan** dengan aplikasi BTN/Tapera, bukan menggantikannya.

### Cited Findings

#### 1a. BTN Properti for Developer (Android/iOS), versi web "balé developer"
- **Pengguna:** admin developer, marketing, finance (peran bawaan di "Manajemen User Developer") — [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id)
- **Fakta store (Play):** paket `com.btnproperti.developer`, penerbit PT. Bank Tabungan Negara (Persero), Tbk; 10.000+ unduhan; rating 4,3 (56 ulasan); versi 1.0.60; diupdate 21 Nov 2025; dirilis 17 Feb 2022; kategori Bisnis — [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id)
- **Fakta store (iOS):** ID 1607611713, seller BANK TABUNGAN NEGARA; versi 1.0.59 (26 Nov 2025); rating 4,41 (17 rating); gratis; catatan rilis terakhir hanya "Update syarat dan ketentuan dan kebijakan privasi" — [iTunes Lookup](https://itunes.apple.com/lookup?id=1607611713&country=id), [App Store](https://apps.apple.com/id/app/id1607611713)
- **Harga:** gratis (store) — [App Store](https://apps.apple.com/id/app/id1607611713)
- **Fitur menurut deskripsi resmi [Klaim]:** Dashboard KPR; Profil Developer (tampil ke calon konsumen); Manajemen Stok (proyek, tipe, unit); Pengajuan KPR Online oleh developer; Report Monitoring pembayaran booking fee, uang muka, pembelian cash, dan status KPR di BTN; Manajemen User (admin/marketing/finance); Generate SPR otomatis; Generate Virtual Account untuk tagihan "cash keras, cash bertahap, ataupun KPR" untuk booking fee dan uang muka — [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id)
- **Layar dari screenshot resmi [Terverifikasi]:**
  - Login email + password, dengan tautan "Registrasi Developer? SIGN UP" (developer mendaftar mandiri).
  - "Dashboard Penjualan" berisi kartu stok Available/Booked/Sold Out dan kartu KPR per status (Draft/In Progress) dalam rupiah dan jumlah unit.
  - "Manajemen Stok" berisi hitungan proyek, tipe, dan unit, daftar proyek berlabel "Approved", serta tombol "Tambah Pengajuan Proyek Properti" (proyek perlu disetujui BTN).
  - "Pengajuan KPR Online" berisi tombol Tambah/Monitoring, chip status **Draft, In Progress, Approved, Booked, Reject**, dan kartu per pengajuan (nomor KPR, nama pembeli, kantor cabang BTN, proyek, tipe, harga).
  - Menu akun: Edit Profile, Pesan, Report Pembayaran, Manajemen User, **Parameterisasi SPR**, Live Chat, Panduan.
  - Tidak terlihat siteplan, CRM lead, komisi, konstruksi, maupun jadwal angsuran/denda.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id); berkas `prahuni_btn_properti_developer/play_02–05.png`
- **Konteks peluncuran:** diluncurkan Feb 2022. BTN mengklaim pengajuan KPR online lewat aplikasi ini memangkas waktu "dari 40 jam menjadi 20 jam". Saat peluncuran ada 3.204 pengembang mitra, dengan target 5.000. Aplikasi "terintegrasi dengan portal properti BTN" sehingga stok bisa dikinikan terpusat — [Pasardana, 23 Feb 2022](https://pasardana.id/news/2022/2/23/btn-properti-for-developer-pangkas-waktu-pengajuan-kpr-jadi-20-jam/)
- **Skala ekosistem:** >12.600 developer bergabung di Bale Properti per Juli 2025. Developer bisa "langsung mengunggah proyek mereka, melacak pengajuan KPR dari pembeli, hingga mengatur stok unit". BTN memberi penghargaan kepada 50 developer dengan pengajuan KPR terbanyak lewat Bale Properti (siaran pers 8 Agu 2025) — [Kontan](https://keuangan.kontan.co.id/news/btn-targetkan-pengajuan-kpr-online-lewat-bale-properti-capai-47-ribu-pada-tahun-ini)
- **Versi web "balé developer":** halaman resmi btn.co.id dan btnproperti.co.id mengembalikan HTTP 403 ke browser otomatis, jadi tidak ada screenshot web — [btn.co.id](https://www.btn.co.id/id/Business/Digital-Mortgage/Digital-Mortgage-Platform/bale-developer)
- **Ulasan, tema login sulit (dominan):**
  - "mau masuk aja susah bgt, padahal sandi email sudah sesuai tapi tidak bisa masuk terus" (Play, 28 Jun 2026)
  - "sumpah dah ribet bgt buat sekedar masuk aplikasi aja" (Play, 14 Jan 2026)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id)
- **Ulasan, tema perawatan:** "minimal dirawat di update jangan sampe sering error ... harus terus nanya ke petugas" (iOS, 27/09/2025) — [App Store](https://apps.apple.com/id/app/id1607611713)
- **Ulasan, pujian pada pelacakan real-time:**
  - "Bagus bagi developer cek real time pengajuan berkas di btn" (Play, 13 Jul 2023, 50 orang merasa berguna)
  - "bantu bgt utk developer jual rumah bisa dimana aja dan kapan aja" (iOS, 12/01/2023)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id), [App Store](https://apps.apple.com/id/app/id1607611713)
- **Aplikasi BTN lain untuk developer:** BTN Property Advisory System (BTN PAS) adalah aplikasi mentoring (legal, capital/financing, land & environment, skillset) untuk peserta/alumni pelatihan Housing Finance Center BTN. Data store: 5.000+ unduhan, 4,4 (20 ulasan), v1.0.3, update 11 Jun 2025 — [Google Play](https://play.google.com/store/apps/details?id=com.app.btnpropertyadvisor&hl=id)

#### 1b. bale by BTN (super app; fitur Bale Properti untuk pembeli)
- **Pengguna:** nasabah/calon debitur KPR (pembeli) — [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id)
- **Fakta store (Play):** paket `id.co.btn.mobilebanking.android`; 10.000.000+ unduhan; 4,2 (36,1 rb ulasan); v2.8.0; update 18 Sep 2026; rilis 19 Okt 2022 — [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id)
- **Fakta store (iOS):** ID 6443466424; v2.8.0 (5 Okt 2026); 3,82 (4.177 rating) — [App Store](https://apps.apple.com/id/app/id6443466424)
- **Fitur properti [Klaim]:** modul Properti untuk "temukan rumah impian, menghitung simulasi KPR, pengajuan KPR secara online"; ekosistem "properti, merchant, bisnis, residence"; Single Sign On; "balé Space" untuk cari hunian — [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id). Melalui Bale Properti calon nasabah dapat "mencari hunian, melakukan simulasi pembiayaan, mengajukan KPR hingga memantau proses pengajuan sampai persetujuan" (9 Sep 2026) — [Kontan](https://keuangan.kontan.co.id/news/btn-dorong-bale-properti-jadi-ekosistem-digital-kepemilikan-rumah)
- **Kinerja:**
  - Pengajuan KPR online lewat Bale Properti >38 ribu aplikasi pada 2024 (sekitar 21% dari total pengajuan KPR BTN), target 47 ribu pada 2025. Pengajuan "terintegrasi langsung dengan sistem backend perbankan", sehingga persetujuan sampai pencairan "dapat dipantau secara real time" — [Kontan, 8 Agu 2025](https://keuangan.kontan.co.id/news/btn-targetkan-pengajuan-kpr-online-lewat-bale-properti-capai-47-ribu-pada-tahun-ini)
  - Sekitar 20% KPR Januari 2025 diproses di aplikasi Bale. Rata-rata keputusan kredit 3 hari (Dirut BTN, 20 Mar 2025) — [Kontan](https://keuangan.kontan.co.id/news/btn-catat-20-proses-kpr-beralih-ke-aplikasi-bale)
- **Layar [Terverifikasi]:** beranda dengan ikon Properti/Residence/Merchant/Bisnis; "balé space – Cari hunian impianmu" dengan kartu proyek dan harga; "satu akun untuk semua"; layanan terintegrasi (properti, merchant, bisnis, smart residence) — [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id); berkas `prahuni_bale_by_btn/play_01,02,03,06.png`
- **Ulasan:** sebagian besar ulasan menyangkut perbankan, bukan KPR:
  - Login/akses ditolak: "sering banget gak bisa login, sehari paling tidak sekali error" (Play, 6 Nov 2026)
  - Debitur KPR meminta transparansi: "harus ada fitur lihat cicilan rumah kita masuk berapa dan potongan admin berapa biar transparan" (Play, 12 Okt 2026)
  - BTN membalas hampir semua ulasan dengan templat (update aplikasi/email contact center).
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id), [App Store](https://apps.apple.com/id/app/id6443466424)

#### 1c. Tapera Mobile (pengganti SiKasep) dan SiKasep (lama)
- **Pengguna:** peserta Tapera dan calon debitur KPR subsidi FLPP (pembeli) — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Fakta store Tapera Mobile (Play):** paket `com.tapera.mobile`, penerbit BP TAPERA (lencana "Pemerintah"); 500.000+ unduhan; 3,5 (885 ulasan); v2.2.4-stable.1; update 11 Agu 2026; rilis 25 Jun 2023 — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Fakta store Tapera Mobile (iOS):** ID 6462958688; v2.2.4 (13 Agu 2026); 3,61 (67 rating); catatan rilis: "kini dapat mengirim otp melalui Email", "Simplifikasi lupa kata sandi" — [iTunes Lookup](https://itunes.apple.com/lookup?id=6462958688&country=id)
- **SiKasep (lama):** paket `com.lpdpp.sikasep`; 1.000.000+ unduhan; 3,1 (6,95 rb ulasan); v1.9.3; update 15 Sep 2025; rilis 28 Nov 2019. Deskripsinya kini berbunyi: "aplikasi SiKasep resmi dialihkan ke aplikasi Tapera Mobile ... segera lakukan pendaftaran ulang data diri" — [Google Play](https://play.google.com/store/apps/details?id=com.lpdpp.sikasep&hl=id)
- **Fitur Tapera Mobile [Klaim]:** saldo/pemupukan Tapera; pembiayaan KPR, KBR, KRR, dan KPR FLPP; simulasi; "status pengajuan pembiayaan perumahan"; "lokasi perumahan" — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Layar Tapera Mobile [Terverifikasi]:**
  - Beranda: "Pilih layanan pembiayaan".
  - Akun: "Status Pemanfaatan – Lacak Status".
  - Pencarian perumahan dengan filter Terbaru/Terdekat/Harga. Kartu proyek memuat harga, nama developer, tipe, dan **jumlah unit subsidi** (contoh "PESONA KAHURIPAN 7 by PT. HIKMAH ALAM SENTOSA ... 48 Unit Subsidi").
  - Menu Pembiayaan KPR/KRR/KBR/KPR FLPP.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id); berkas `prahuni_tapera_mobile/play_02–05.png`
- **Layar SiKasep [Terverifikasi]:**
  - Rekam Data Diri: KTP, NPWP, penghasilan per bulan, HP.
  - Menu: Lokasi Rumah Idaman, Perumahan Sekitar, Pilih Bank Pelaksana KPR Subsidi, Cek Status Pengajuan.
  - Pemilihan bank dari grid logo bank.
  - **Status 6 tahap:** Terdaftar → Proses Pengajuan Subsidi Checking → Lolos Subsidi Checking → Proses Pengajuan Verifikasi Bank → Lolos Verifikasi Bank → Proses Pengajuan Dana oleh Bank.
  - Galeri perumahan dengan tautan ke sikumbang.ppdpp.id.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.lpdpp.sikasep&hl=id); berkas `prahuni_sikasep/play_03,04,06,07.png`
- **Ulasan, tema status tidak sinkron dengan bank:**
  - "status udah sp3k malah keterangan di aplikasi masih di follow up" (Play, 14 Apr 2026)
  - "sudah di tahap 4 layak huni malah pengajuan KPR saya tidak muncul di bank penyalur" (Play, 21 Apr 2026)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Ulasan, tema tidak bisa batal/ganti bank/edit:**
  - "Tambahkan opsi pembatalan/pindah bank penyalur ... Batal akad tapi pengajuan masih menggantung" (Play, 2 Mei 2026)
  - "tidak ada menu edit maupun menu hapus ... sudah mundur satu Minggu lebih untuk akad" (Play, 15 Apr 2026)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Ulasan, tema stok developer tidak akurat:** "status unit ready banyak tapi di lapangan ... nggak ada unit yg ready ... cmn sbg pajangan iklan developer" (Play, 14 Sep 2026) — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Ulasan, tema proses tetap offline:** "pengajuan via aplikasi ternyata harus datang sendiri ke bank penyalur" (Play, 27 Agu 2026) — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Ulasan, tema OTP/verifikasi gagal:**
  - "kode otp ... coba di benerkan kode 500" (Play, 7 Jun 2026)
  - "gagal verifikasi mulu, gabisa nge-detect ktp" (iOS, 29 Jul 2026)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id), [App Store](https://apps.apple.com/id/app/id6462958688)
- **Ulasan, usulan pengguna:** "tambahin fitur Pelanggan KPR bisa kasih rating ke Developer nya" (Play, 20 Sep 2024) — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)
- **Ulasan SiKasep era 2020–2023 (pola sama):**
  - "Permohonan reset akun lama, sementara sudah mau akad" (Play, 7 Feb 2023, 88 orang merasa berguna)
  - "ngga ada fitur lupa sandi" (Play, 23 Jan 2020)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.lpdpp.sikasep&hl=id)

### Inferences
- BTN Properti for Developer adalah pesaing "gratis" untuk **stok + SPR + VA booking fee/DP + pengajuan KPR BTN**. Namun dari layarnya terlihat aplikasi ini bukan sistem operasi developer: tidak ada siteplan, lead, termin/denda, komisi, konstruksi, maupun BAST. Jumlah unduhan 10 rb+ jauh di bawah ">12.600 developer", sehingga kemungkinan besar sebagian besar admin bekerja lewat web balé developer, atau satu admin melayani banyak proyek.
- Keluhan Tapera Mobile menunjukkan **masalah koordinasi antarsistem** (Tapera, bank penyalur, developer), bukan sekadar masalah UI. Estora dapat menawarkan nilai "status tunggal per pembeli" (tahap FLPP + bukti + tanggal). Developer bisa memakainya untuk menjawab pertanyaan pembeli lewat portal/WA tanpa bergantung pada sinkronisasi Tapera–bank. Ini kebutuhan nyata, tetapi belum ada bukti developer mau membayar untuknya.
- Kartu proyek Tapera menampilkan stok developer langsung ke pembeli. Jadi akurasi stok di SiKumbang/Tapera adalah masalah reputasi developer. Estora bisa menjadikan "ekspor/rekonsiliasi stok ke SiKumbang/Bale Properti" sebagai fitur kepatuhan.

### Gaps
- Layar web balé developer tidak bisa dilihat (HTTP 403 untuk akses otomatis). Belum terkonfirmasi apakah versi web punya fitur lebih (misalnya siteplan atau impor massal).
- Belum ada bukti API publik untuk BTN Properti for Developer, Bale Properti, atau Tapera Mobile. Hasil pencarian menyebut portal BTN Open API (developer.btn.co.id) dengan produk Virtual Account dan QRIS (snippet), tetapi halamannya tidak diverifikasi — [btn.co.id BTN Open API](https://btn.co.id/en/Business/Jasa-Layanan/e-Channels/BTN-Open-API)
- Ulasan iOS lewat RSS tidak tersedia (feed kosong). Hanya sekitar 10 ulasan teratas per aplikasi yang terbaca dari halaman web App Store.

---

## 2. Aplikasi sales/agen dari developer dan portal: Paramount Sales, Sinar Mas Land eAgent, Pesona Kahuripan, Perumnas (QPer + Digital Property Platform/Sobat Bisnis), Pinhome Rekan Agen, Rumah123 Pro/99.co

### Takeaway
Developer besar membangun aplikasi sempit untuk satu peran, masing-masing dengan pola UX yang belum dimiliki Estora:
- **Paramount Sales**: katalog stok, siteplan interaktif, dan pricelist PDF untuk tenaga penjual.
- **SML eAgent**: laporan poin, komisi, dan pembayaran per transaksi untuk agen.
- **Pesona Kahuripan**: booking mandiri oleh pembeli lewat grid kavling, dibayar dengan VA BTN.
- **Perumnas QPer**: penilaian mutu rumah dengan skor, NCR, dan peringatan dini.

Portal agen (Pinhome, Rumah123 Pro) adalah sumber lead dan jaringan agen. Keluhan utamanya: lead palsu/pasif dan biaya iklan/aturan poin yang berubah.

### Cited Findings

#### 2a. Paramount Sales (Paramount Land)
- **Pengguna:** tenaga penjual/agen Paramount (nama aplikasi). Deskripsinya ditulis seperti aplikasi pencarian properti [Inferensi peran dari nama dan layar] — [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id)
- **Fakta store (Play):** paket `com.paramountland.sales`, penerbit "IT Paramount"; 1.000+ unduhan; 4,7 (23 ulasan); v1.0.31; update 9 Des 2025; rilis 15 Feb 2022 — [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id)
- **Fakta store (iOS):** ID 1609202939, seller PT. PARAMOUNT ENTERPRISE INTERNATIONAL; v1.0.31 (17 Des 2025); belum ada rating; catatan rilis: "Now can choose pdf pricelist more than 2 pricelist merging", lazy loading berita — [iTunes Lookup](https://itunes.apple.com/lookup?id=1609202939&country=id)
- **Fitur [Klaim]:** daftar stok terbaru proyek Paramount (">1.000 unit" rumah tapak, apartemen, ruko, kavling komersial, tanah); tampilan 3D unit; berita; video YouTube — [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id)
- **Layar [Terverifikasi]:**
  - Beranda: Projects dan News.
  - Halaman proyek dengan tab Project Detail/Unit List dan tombol **Siteplan, Brochure, Pricelist**.
  - Pricelist PDF yang bisa dianotasi (ikon pena).
  - **Siteplan interaktif berwarna** per kavling.
  - "Unit Detail": cluster, lokasi, tipe, **status INDENT**, LT/LB, bentuk, **Cash Price IDR 843.700.000**, dan "Unit Position" berupa pin di siteplan.
  - Tombol share/ekspor.
  - FAQ estate (Perizinan, PJU, SAD).
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id); berkas `prahuni_paramount_sales/play_03,05,07,08.png`
- **Ulasan:** hanya satu ulasan yang terbaca: "Paramount Sales OK" (Play, 6 Nov 2024) — [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id)
- **Pembanding pasca-huni:** aplikasi penghuni "Paramount Estate" (iOS 1,375 dari 32 rating) dibahas peneliti pascahuni — [iTunes Lookup](https://itunes.apple.com/lookup?id=1624020170&country=id)

#### 2b. eAgent by Sinar Mas Land
- **Pengguna:** agen penjualan eksternal, dan sejak Okt 2026 juga sales internal ("add feature for sales internal") — [iTunes Lookup](https://itunes.apple.com/lookup?id=1643079818&country=id)
- **Fakta store (Play):** paket `com.mycompany.eagent`, penerbit "Sinar Mas Land"; 100+ unduhan; tanpa rating; v3.1.1; update 9 Okt 2026; rilis 30 Sep 2022; deskripsi satu baris: "Aplikasi Agen Penjualan Sinar Mas Land untuk cek point dan pembayaran disana" — [Google Play](https://play.google.com/store/apps/details?id=com.mycompany.eagent&hl=id)
- **Fakta store (iOS):** ID 1643079818, seller Bumi Serpong Damai Pt Tbk, bundle `com.sinarmasland.eagent`; v3.1.2 (30 Okt 2026); 5,0 (1 rating) — [iTunes Lookup](https://itunes.apple.com/lookup?id=1643079818&country=id)
- **Layar [Terverifikasi]:**
  - **Registrasi mandiri agen** (nama, email, telepon, sandi).
  - Dasbor "My Point" (81 poin) dengan grafik **Monthly Point** (garis Total, Adendum, Point) dan kartu **"Paid Rp 0 / Rp 4.050.000"**.
  - Tabel Detail Point per bulan: jumlah transaksi, poin, Income, Paid, dan jatuh tempo.
  - Daftar Transaction dengan nama konsumen, unit, nomor SO, dan tanggal.
  - Transaction Detail: nama konsumen, unit "NASHVILLE 100/161 TD5/17", **Sales Program "Double Dream"**, LT/LB, Net Value, Points, Income.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.mycompany.eagent&hl=id); berkas `prahuni_sml_eagent/play_04–07.png`
- **Ulasan:** tidak ada ulasan Play yang terbaca — [Google Play](https://play.google.com/store/apps/details?id=com.mycompany.eagent&hl=id)

#### 2c. Pesona Kahuripan (aplikasi pembeli milik developer subsidi/komersial, Klapanunggal–Cileungsi, Bogor)
- **Pengguna:** calon pembeli, untuk "proses Pemesanan dan Pengajuan KPR" — [Google Play](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id)
- **Fakta store:** paket `com.pesonakahuripan.mobile`, penerbit perorangan "Widi Mawardi"; 100+ unduhan; tanpa rating; v0.1.0; update 10 Jul 2024; rilis 27 Jun 2024; label "Pembelian Dalam Aplikasi". Deskripsi menyebut "PT.HIKMAH AGUNG SEJAHTERA". Tidak ditemukan di iOS — [Google Play](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id)
- **Layar [Terverifikasi], booking mandiri end-to-end:**
  - Beranda: kategori tipe rumah (70/90, Ruko 70/75, 36/66, 45/72, 120/120) dan banner **"Undang Teman – Ajak teman kamu untuk membeli rumah ... dan dapatkan keuntungan besar"**.
  - Detail unit: "Rumah Type 36/66 Rp 410.000.000", label "TOTAL BIAYA ALL IN Rp 1.000.000", tombol "Lihat Site Plan", tab Blok A–E dengan **grid nomor kavling** (unit terpilih disorot), dan tombol **BOOKING**.
  - "Selesaikan Pembayaran": **Nomor Virtual Account BTN**, total Rp1.000.000, cara bayar (Mobile Banking BTN / ATM BTN / ATM bank lain), dan tombol "LIHAT STATUS PEMBAYARAN".
  - Halaman berita/promo.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id); berkas `prahuni_pesona_kahuripan/play_01–04.png`
- **Proyek yang sama di Tapera:** "PESONA KAHURIPAN 7" tampil di Tapera Mobile dengan nama badan usaha berbeda ("PT. HIKMAH ALAM SENTOSA"), Rp168.000.000, 48 unit subsidi — [Google Play Tapera Mobile, screenshot](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id)

#### 2d. Perumnas: QPer (QC konstruksi) dan Perumnas Digital Property Platform (afiliasi "Sobat Bisnis Perumnas")
- **QPer Perumnas, pengguna:** pimpinan proyek dan QHSE Perumnas (login NIP) — [Google Play](https://play.google.com/store/apps/details?id=com.perumnas.qper&hl=id)
- **QPer Perumnas, fakta store:** paket `com.perumnas.qper`, penerbit Perum Perumnas; 100+ unduhan; v1.0.80; **update 23 Nov 2026**; rilis 15 Des 2023 — [Google Play](https://play.google.com/store/apps/details?id=com.perumnas.qper&hl=id)
- **QPer, fitur [Klaim, dan terlihat di screenshot]:**
  - Dashboard nilai rata-rata kontrak per proyek ("Skor Pembangunan 80,75").
  - Persentase temuan ketidaksesuaian per bulan dan akumulatif.
  - Penilaian tiap sekuens pekerjaan di 3 titik per NDR, dengan 12 parameter struktur/arsitektur/MEP (checklist ✓/✗, misalnya kriteria pondasi batu kali).
  - Unggah foto fasad dan progres fisik.
  - Rekap defect open/closed real-time ("20 total defect, 19 open, 1 closed").
  - **Verifikasi closing hanya oleh akun pimpinan proyek.**
  - Detail NDR: skor per parameter, "TOTAL SKOR 84,62 vs TARGET 80,00 → TERCAPAI".
  - Fitur share laporan.
  - **Early Warning System** tenggat closing temuan (notifikasi dari "QHSE PUSAT" berisi foto).
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.perumnas.qper&hl=id); berkas `prahuni_perumnas_qper/play_02,03,04,06.png`
- **Aplikasi Perumnas lain di Play:** "ePropman Perumnas" (rusunawa: catat meter listrik/air/gas; 10+ unduhan; update 24 Des 2024) berada di luar lingkup prahuni — [Google Play](https://play.google.com/store/apps/details?id=com.perumnas.epropman&hl=id)
- **Perumnas Digital Property Platform:** diluncurkan sekitar 27 Agu 2026 untuk pembeli rumah pertama generasi muda. Isinya pencarian hunian tapak/apartemen berdasarkan lokasi, harga, dan estimasi keterjangkauan; simulasi KPR; dan **"fitur affiliate yang membuka peluang bagi masyarakat untuk bergabung dalam komunitas Sobat Bisnis Perumnas"**. Plt. Dirut Imelda Alini Pohan menyatakan "Hampir dari 60% penjualan berasal dari digital marketing content kami" dan Perumnas sebelumnya juga menggandeng Blibli.com — [Kontan, 27 Agu 2026](https://industri.kontan.co.id/news/perumnas-rilis-platform-properti-digital-bidik-generasi-muda-pembeli-rumah-pertama)
- **Portal kemitraan Perumnas:** kemitraan.perumnas.co.id adalah portal kemitraan B2B (lahan, KSO dengan developer seperti BSA Land), **bukan** portal afiliasi perorangan — [kemitraan.perumnas.co.id](https://kemitraan.perumnas.co.id/en/home/)

#### 2e. Rekan Agen Properti Pinhome
- **Pengguna:** agen independen dan agen APEX Real Estate. Mereka memasarkan listing secondary, tawaran owner, dan **proyek primary developer** — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Fakta store (Play):** paket `id.pinhome.agent`; 50.000+ unduhan; 4,1 (871 ulasan); v1.136.3; update 14 Sep 2026; rilis 10 Mei 2020 — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Fakta store (iOS):** ID 1502834833 "Rekan Agen Pinhome"; v1.136.3 (15 Sep 2026); 4,82 (76 rating) — [App Store](https://apps.apple.com/id/app/id1502834833)
- **Harga dan model:** pasang iklan "GRATIS", tetapi kuota listing bisa ditambah. Komisi proyek primer "diatas 3%" lewat APEX. Bantuan "pengajuan dan referral KPR juga bisa dapat tambahan komisi hingga jutaan rupiah" [Klaim] — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Layar [Terverifikasi]:**
  - Beranda: Pasang Listing Secondary, Ajukan KPR, Kalkulator KPR, Tawaran Listing Owner, Co-Bro; keuntungan (komisi menjanjikan, gratis jasa admin).
  - "Ada Tawaran Listing!" dengan **timer kedaluwarsa** dan tombol Terima/Tidak Tertarik.
  - Deskripsi listing otomatis oleh AI.
  - **"Link Katalog"** (katalog website pribadi agen) dengan performa listing dan badge "Star Agent".
  - Kuota listing aktif dan tombol Tambah Kuota.
  - Simulasi KPR dengan tombol **"Bagikan Hasil"**.
  - Navigasi bawah: Beranda, Leads, Listing, Katalog, Chat.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id); berkas `prahuni_pinhome_rekan_agen/play_01,03,04,06.png`
- **Ulasan, tema lead palsu/pasif:**
  - "Kebanyakan leads yg tanya fake" (iOS, 26/10/2022)
  - "Kebanyakan LEADS PASIF tiba2 datang tiba tiba hilang" (Play, 29 Jul 2025)
  - Sumber: [App Store](https://apps.apple.com/id/app/id1502834833), [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Ulasan, tema aturan insentif berubah:** "Kemarin tukar poin ke uang minimal 100rb ... Barusan berubah min 250" (Play, 3 Okt 2023) — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Ulasan, tema akses proyek primary:** "setelah di upgrade ... primary project tidak ada" (Play, 5 Mei 2024) — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)
- **Ulasan, pujian:** "dibantu oleh staf Pinhome dlm follow up Leads" (Play, 10 Nov 2022) — [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id)

#### 2f. Rumah123 Pro (agen/in-house marketing; listing tersindikasi ke 99.co) dan aplikasi 99.co
- **Pengguna:** "agen, inhouse marketing ataupun pemilik properti" yang terdaftar di Rumah123 — [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id)
- **Fakta store (Play):** paket `com.rumah123.android.agent2`, penerbit 99 Group Indonesia; 100.000+ unduhan; 4,7 (12,9 rb ulasan); v3.28.2; update 28 Okt 2026; rilis 7 Apr 2015 — [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id)
- **Fakta store (iOS):** ID 1017277325; v3.28.2 (30 Okt 2026); 4,86 (2.187 rating) — [App Store](https://apps.apple.com/id/app/id1017277325)
- **Layar [Terverifikasi]:**
  - Dasbor dengan Pasang Iklan, Top Up kredit, **AI Video Maker, AI Photo Makeover**, Sundul, Boost, dan "Rekomendasi Booster & SUNDUL".
  - Daftar iklan (Tayang/Tunda/Terjual) dengan **Skor Iklan**, label "H-30 Expired"/"Featured", dan statistik per iklan.
  - **"Klien Saya"**: total respons 30 hari (208), belum dibaca, perlu dihubungi, dan respons per tipe iklan.
  - Wizard pasang iklan dengan pertanyaan wajib **"Apakah properti baru dari Developer?"** (Baru/Second/Aset Bank).
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id); berkas `prahuni_rumah123_pro/play_02–05.png`
- **Fitur lead [Klaim]:** Rumah123 Pro menarik lead dari WhatsApp, telepon, email, dan crosspost 99 ke satu tampilan (sudah tercatat di riset terdahulu) — [rumah123.com](https://www.rumah123.com/explore/agent/app/)
- **Harga (dilaporkan pengguna):** "Saya beli paket 1 iklan 600rb, setelah sebulan belum dapat leads sama sekali" (iOS, 07/05/2025) — [App Store](https://apps.apple.com/id/app/id1017277325)
- **Ulasan, tema lead dummy:** "95% adalah customer2an karena hanya bertanya basa basi" (iOS, 23 Okt 2026) — [App Store](https://apps.apple.com/id/app/id1017277325)
- **Ulasan, tema harga naik:**
  - "harga member naik trus jadi tidak ramah di kantong para agent" (Play, 11 Agu 2026)
  - "Skrng harga langganan naik banyak tapi gak disambungin sama 99.co lagi" (Play, 21 Mar 2025)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id)
- **Ulasan, pujian:** "leads terbanyak" (Play, 3 Agu 2026) — [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id)
- **Aplikasi 99.co Indonesia (sisi pencari; agen bisa membaca pesan):** paket `com.urbanindo.android`; 500.000+ unduhan; 3,4 (7,24 rb ulasan); v6.18.4; update 6 Nov 2026. Fitur: pencarian peta/GPS, direktori agen, kalkulator KPR, share — [Google Play](https://play.google.com/store/apps/details?id=com.urbanindo.android&hl=id)

### Inferences
- Pola yang **dibangun sendiri oleh developer besar** menunjukkan modul yang dianggap bernilai:
  - katalog stok + siteplan + pricelist untuk sales (Paramount);
  - laporan komisi/poin untuk agen (SML);
  - booking mandiri + VA untuk pembeli (Pesona Kahuripan);
  - skor mutu + NCR + peringatan dini untuk QC (Perumnas).

  Developer kecil/subsidi tidak punya tim IT untuk membuat semua ini. Estora sudah punya mesin di belakang ketiga yang pertama, tetapi **antarmuka untuk agen dan pembeli** (login mitra, booking publik, pembayaran online) belum ada.
- Pesona Kahuripan (v0.1.0, 100+ unduhan, penerbit perorangan) menunjukkan bahwa booking mandiri + VA BTN bisa dibangun developer menengah dengan biaya rendah. Adopsinya rendah, jadi permintaan pembeli untuk "booking lewat aplikasi" belum terbukti.
- Keluhan terbesar di portal agen adalah **kualitas lead** dan **perubahan aturan insentif**. Ini mendukung desain Estora yang mencatat atribusi sampai akad dan memakai skema fee yang terdokumentasi dan berbukti. Mesin fee Estora bisa dijadikan nilai jual kepada agen ("aturan komisi Anda tidak berubah diam-diam; lihat statusnya"), asalkan ada portal mitra.
- Perumnas memakai afiliasi publik (Sobat Bisnis Perumnas) dan mengklaim ~60% penjualan berasal dari konten digital. Bersama Rumah Ningrat (Mitra Ningrat) dan SML (eAgent), ini tanda bahwa **jaringan afiliasi dengan login sendiri** sudah menjadi standar developer menengah–besar.

### Gaps
- Alamat web Perumnas Digital Property Platform dan detail program Sobat Bisnis Perumnas (komisi, alur daftar) tidak ditemukan. perumnas.co.id mengembalikan "upstream request failed" (502) saat riset, sehingga tidak ada screenshot web.
- Aplikasi Sobat Bisnis Perumnas di store tidak ditemukan (pencarian Play "Sobat Bisnis Perumnas" nihil).
- Angka harga paket Rumah123 Pro dan kuota Pinhome tidak dipublikasikan di listing. Satu-satunya angka berasal dari ulasan pengguna.
- Fitur Paramount Sales/eAgent setelah login (misalnya alur reservasi oleh agen) tidak bisa dicek tanpa akun.

---

## 3. Aplikasi software developer (mobile/web): Ndalem Mobile, Mandep, Simandor + SmartMandor, Porta Pro (ECes.Q), vCloudProperty+ (Approvals), AutoKon

### Takeaway
Aplikasi mobile vendor ERP developer adalah **pendamping** sistem web dengan unduhan sangat kecil:
- vCloud Approvals: 1+
- Ndalem: 10+
- Mandep: 500+
- Porta Pro: 1 rb+

**Porta Pro (ECes.Q) adalah pembanding terdekat Estora di level aplikasi.** Ia memuat 10 status unit (Open → Reservasi → Booking → Kontrak → SP3K → Akad → AJB → BAST/Batal), siteplan berwarna, reserve dengan konfirmasi, progres bangunan per unit, dan kartu pembayaran dengan tombol "Kirim WA Tagihan". vCloud Approvals menonjol untuk persetujuan mobile (pembatalan penjualan, pengalihan hak) yang dikunci biometrik. AutoKon menempati konstruksi berbasis WhatsApp dengan dukungan REI. Tidak satu pun yang mengiklankan mode offline.

### Cited Findings

#### 3a. Ndalem Mobile (Ndalem Software)
- **Pengguna:** pengguna ERP Ndalem; layar menampilkan akun "Direktur" [Terverifikasi] — [Google Play](https://play.google.com/store/apps/details?id=com.pt_ndalem_technology.ndalem_mobile_app&hl=id)
- **Fakta store:** paket `com.pt_ndalem_technology.ndalem_mobile_app`, penerbit Ndalem Technology; 10+ unduhan; v1.0.5; update 10 Agu 2026; rilis 4 Mar 2025. Tidak ditemukan di iOS — [Google Play](https://play.google.com/store/apps/details?id=com.pt_ndalem_technology.ndalem_mobile_app&hl=id)
- **Harga web ERP:** Rp1.499.000/bulan (riset terdahulu) — [ndalem.app](https://ndalem.app/)
- **Layar [Terverifikasi]:**
  - Beranda "Ringkasan Saldo Keuangan": Penerimaan, Piutang, HPP, Hutang; kartu "Kinerja Pemasaran".
  - Daftar Menu: RAB HPP, Hutang Kavling, Hutang Kavling Kolektif, Hutang Fasum, Hutang Lain, Piutang Kavling, Piutang Lain, Laporan Operasional, Laporan Pemasaran, Laporan Rekap Keuangan, Laporan Akuntansi.
  - Siteplan (gambar statis) dengan "Daftar Kavling": nomor, nama pembeli, status **Dipesan/BAST/Free**.
  - Profil dengan daftar perumahan yang dikelola (multi-proyek).
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.pt_ndalem_technology.ndalem_mobile_app&hl=id); berkas `prahuni_ndalem_mobile/play_01–04.png`

#### 3b. Mandep
- **Pengguna:** admin, staf lapangan, dan pemasaran developer (menu Absensi, Pemasaran, Gudang, Keuangan, Proyek, Persetujuan, Admin) [Terverifikasi] — [Google Play](https://play.google.com/store/apps/details?id=id.mandep.apps&hl=id)
- **Fakta store (Play):** paket `id.mandep.apps`, penerbit Fanatech Dev; 500+ unduhan; update 2 Des 2025 — [Google Play](https://play.google.com/store/apps/details?id=id.mandep.apps&hl=id)
- **Fakta store (iOS):** ID 6741072888, seller perorangan "Nasihun Amin Suhardiyan Putra"; v1.2.0 (29 Nov 2025); belum ada rating; catatan rilis: "Penambahan Kolom Total pada Dashboard Penjualan Unit" — [iTunes Lookup](https://itunes.apple.com/lookup?id=6741072888&country=id)
- **Harga web:** Rp15–40 jt/tahun (riset terdahulu) — [mandep.id/harga](https://mandep.id/harga/)
- **Layar [Terverifikasi]:**
  - Beranda: jam masuk/keluar dan pengumuman.
  - "Detil Laporan Harian": progres 75%, tab Pekerjaan/Material/Proses, foto dokumentasi.
  - "Detil Pembayaran": nama pembeli, jabatan/instansi, unit, **Total Piutang Rp167.000.000, Sisa Piutang Rp165.500.000**, jenis Booking Fee, invoice INV2024080003 berstatus **Approved**.
  - Absensi: riwayat clock in/out dengan ikon lokasi; Izin; Cuti/Off.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=id.mandep.apps&hl=id); berkas `prahuni_mandep/play_01–04.png`

#### 3c. Simandor (web) + SmartMandor (aplikasi pembeli)
- **Platform:** web app `app.simandor.id` (login email/sandi, ada "Daftar disini"). Situs menyebut "SiMandor Mobile Apps" untuk developer dan "SmartMandor Mobile Apps" gratis untuk pembeli, untuk "melihat kewajiban customer dan progres pembangunan secara realtime" — [simandor.id](https://simandor.id/), [app.simandor.id](https://app.simandor.id/login)
- **Penerbit SmartMandor:** CV Solusi Banget Dot Com; "SmartMandor is a tools for SiMandor Customers to monitor house construction progress" — [Privacy Policy SmartMandor](https://simandor.id/privacy-policy-smartmandor/)
- **Fitur dari dokumentasi publik [Terverifikasi di halaman docs]:**
  - Data Konsumen memuat pekerjaan, "Pendapatan kotor", "Pendapatan tambahan", dan **"Daftar cicilan calon konsumen"** (pra-skrining manual).
  - **Customer Booking** dengan aksi Edit, **SPR**, Booking Detail, Update Status, serta filter "status pengajuan".
  - SPK Project.
  - Konfirmasi pembangunan konsumen ("Upload file denah yang telah disetujui konsumen").
  - Laporan harian progres pembangunan per kavling.
  - Pembayaran Konsumen dengan lampiran bukti bayar lalu konfirmasi oleh Keuangan.
  - Master Persyaratan Konsumen per tipe pembayaran.
  - Sumber: [simandor.id/docs](https://simandor.id/docs/)
- **Fitur dari situs:** siteplan interaktif "dilengkapi dengan data timeline pembayaran dan progres pembangunan"; approval pembayaran yang menerbitkan e-invoice; absensi selfie + geolokasi; dukungan "satu konsumen satu group whatsapp"; uji coba 7 hari — [simandor.id](https://simandor.id/)
- **Ketersediaan di store:** SiMandor/SmartMandor tidak ditemukan di Google Play maupun App Store lewat pencarian publik (Play: "Simandor", "Smart Mandor", "simandor.id" → nihil) — [Google Play search](https://play.google.com/store/search?q=Simandor&c=apps&hl=id&gl=ID)
- **Screenshot web:** `prahuni_simandor/web_01_landing_simandor.id.png` (landing), `prahuni_simandor/web_02_login_app.simandor.id.png` (halaman login)

#### 3d. Porta Pro (Media Sarana Informasi; pendamping ECes.Q)
- **Pengguna:** staf developer pengguna ECes.Q ("Hanya dapat digunakan oleh perusahaan yang Telah melakukan Implementasi Software ECes.Q"). Login memakai **Kode Perusahaan** + nama user + sandi — [Google Play](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id)
- **Fakta store (Play):** paket `com.mediasarana.portapro`; 1.000+ unduhan; 4,9 (16 ulasan); v2.1.001; update 11 Nov 2026; rilis 11 Jul 2022 — [Google Play](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id)
- **Fakta store (iOS):** ID 1661054603; v2.0.001 (11 Nov 2026); 5,0 (4 rating). Catatan rilis: "menyempurnakan Marketing Tools", unggah hingga 4 file sekaligus, media dikelompokkan per sesi — [iTunes Lookup](https://itunes.apple.com/lookup?id=1661054603&country=id)
- **Layar [Terverifikasi]:**
  - Dashboard "Status Unit" berupa donut dengan **Open, Asset, Reservasi, Booking, Kontrak, SP3K, Akad, AJB, BAST, Batal**, ditambah grafik "Resume Penjualan".
  - **Site Plan berwarna per status**.
  - Kartu Status Unit (total 79, sisa 42, per status).
  - **"Reserve Unit"**: daftar dengan status Reserve / Belum Konfirmasi / Sudah Konfirmasi / Batal.
  - **"Progres Bangunan"**: persentase per unit dengan tanggal.
  - **"Kartu Pembayaran"**: sisa pembayaran, persentase lunas, tunggakan s/d hari ini, pembayaran berikutnya, jadwal (Booking Fee, Uang Muka ke-1, ke-2), dan menu aksi **"Kirim WA Info", "Kirim WA Tagihan", "Kirim E-mail", "Telepon"**.
  - "Mutasi Kas/Bank" per rekening.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id); berkas `prahuni_porta_pro/play_02,03,05,07.png`
- **Ulasan:** semua positif dan singkat (2022–2023), misalnya "Sangat bermanfaat untuk developer property 👍" (Play, 23 Jan 2023) — [Google Play](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id)
- **Aplikasi penghuni:** MSI juga menerbitkan "Porta Home" (aplikasi penghuni pasca-huni; 10+ unduhan; rilis 8 Sep 2026; v1.1.14) — [Google Play](https://play.google.com/store/apps/details?id=id.portahub.portaliving&hl=id)

#### 3e. vCloudProperty+ Approvals (dan aplikasi penghuni vCloudProperty+)
- **Pengguna:** staf/manajer pemberi persetujuan ("memerlukan akun staf pada sistem vCloudProperty+") — [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id)
- **Fakta store:** paket `com.vcloud.vworkflow`, penerbit PT Virtual Properti Plus; 1+ unduhan; v1.0.0; update 29 Jul 2026; rilis 28 Jul 2026 — [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id)
- **Fitur [Klaim]:** tinjau dan setujui dokumen; **matriks persetujuan bertingkat** dengan tahapan dan waktu; riwayat; **pindah antar entitas/proyek**; "Kata sandi persetujuan tersimpan terkunci di perangkat dan hanya dapat dibuka dengan sidik jari, wajah, atau PIN"; notifikasi tiap dokumen baru — [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id)
- **Layar [Terverifikasi]:**
  - Antrian per modul (contoh demo): SALES 19, PO 138, AP 41, AR 9, INVENTORY 26, GL 198, CASHBOOK 4.789.
  - Jenis persetujuan sales: **Pembatalan Penjualan, Pengalihan Hak (ganti pembeli), Reservasi Unit**.
  - Daftar dokumen EF/CL dengan pencarian nomor dokumen/unit/konsumen.
  - Detail berstatus "Pending approval" dengan tombol "Keputusan".
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id); berkas `prahuni_vcloudproperty_approvals/play_01–04.png`
- **Aplikasi penghuni dalam keluarga yang sama (pasca-huni):**
  - "vCloudProperty+ Mobile" (IPL, keluhan, booking fasilitas; 10+ unduhan; v1.0.0; update 27 Sep 2026) — [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.ateraland&hl=id)
  - "vCloudProperty+ Waskita" (v1.2.1; update 19 Nov 2026) — [Google Play](https://play.google.com/store/apps/details?id=com.yabes.waskita&hl=id)

#### 3f. AutoKon (pengawasan konstruksi via WhatsApp)
- **Badan usaha:** PT Autokon Digital Indonesia
- **Dukungan REI:** MoU dengan REI pada 30 Okt 2025. Penerapan pertama di proyek subsidi Buana Kassiti Group (Ketua REI Joko Suranto) di Jawa Barat
- **Fitur:** pengawasan lewat WhatsApp "tanpa sistem yang rumit", paperless, pemantauan progres real-time, dan laporan kesiapan serah terima
- **Harga dan URL:** tidak disebutkan
- Sumber: [Investortrust, 30 Okt 2025](https://www.investortrust.id/business/83968/rei-gandeng-autokon-untuk-perkuat-digitalisasi-pengawasan-proyek-perumahan)
- **Peluncuran Malang Raya (19 Nov 2025):** bersama REI Malang Raya dan PT Kharisma Karang Ploso; WhatsApp sebagai antarmuka utama; dokumentasi terdigitalisasi; pemantauan tahapan konstruksi dan mutu "hingga serah terima" — [TIMES Indonesia](https://timesindonesia.co.id/indonesia-positif/565732/rei-malang-raya-siap-wujudkan-digitalisasi-demi-bantu-percepat-program-3-juta-rumah)
- **Fitur menurut liputan detik (riset terdahulu):** lembar pengawasan, material masuk, progres, jadwal, laporan AI; pembeli bisa diberi akses untuk melaporkan keluhan mutu — [detik](https://www.detik.com/properti/berita/d-8186216/pengembang-beralih-ke-digital-pengawasan-proyek-kini-bisa-lewat-whatsapp)
- **Kehadiran digital:** tidak ditemukan aplikasi store maupun situs publik. autokon.id dan www.autokon.id mengembalikan 404 ("Site Not Found | Framer"); autokon.ai mengarah ke domain parkir — [autokon.id](https://autokon.id/)

### Inferences
- Porta Pro membuktikan bahwa **pipeline status unit end-to-end di ponsel** (termasuk SP3K/Akad/AJB/BAST) dan **penagihan satu ketuk lewat WhatsApp** sudah menjadi praktik vendor lama (MSI, "400+ proyek"). Estora unggul di kedalaman akuntansi (denda berjurnal, refund, GL) dan offline, tetapi UX penagihan Porta ("Kirim WA Tagihan" dari kartu pembayaran) lebih langsung daripada desain WABA Estora yang belum live.
- vCloud Approvals menunjukkan bahwa persetujuan sensitif (pembatalan, pengalihan hak) dipindahkan ke ponsel dengan kunci biometrik dan notifikasi push. Estora sudah punya pemisahan tugas pembatalan/refund, tetapi tanpa push di luar aplikasi (inventaris hanya menyebut notifikasi in-app WebSocket).
- AutoKon tidak punya jejak web/store yang bisa diverifikasi. Kekuatannya adalah distribusi lewat asosiasi (REI), bukan produk yang terdokumentasi. Bagi developer anggota REI, AutoKon bisa menjadi "default" untuk pengawasan. Estora sebaiknya bisa hidup berdampingan (misalnya menerima foto/laporan sebagai bukti) daripada memaksa developer memilih.
- Jumlah unduhan yang kecil (1+ sampai 1 rb+) memperlihatkan bahwa developer software di segmen ini tetap berpusat di web. Ketiadaan aplikasi native di Estora tidak merugikan untuk peran back-office. Kekurangan yang nyata ada pada push notifikasi dan pada peran yang **di luar perusahaan** (agen, pembeli).

### Gaps
- Harga Porta Pro/ECes.Q, Simandor, vCloud+, dan AutoKon tidak dipublikasikan.
- Listing store SmartMandor tidak ditemukan, sehingga jumlah pengguna dan layarnya tidak diketahui.
- Rating Play untuk Ndalem, Mandep, dan vCloud tidak ditampilkan (ulasan terlalu sedikit), sehingga tidak ada sinyal kepuasan pengguna.
- Fitur web Mandep/Ndalem di luar yang terlihat di layar mobile hanya berasal dari klaim situs (lihat riset terdahulu).

---

## 4. Aplikasi pembeli dari agregator KPR: IDEAL dan Ringkas

### Takeaway
IDEAL (aplikasi native) dan Ringkas (web/PWA, tanpa aplikasi native) memberi pembeli **pengajuan ke beberapa bank sekaligus, pelacakan status per bank, dan cek kredit/prakualifikasi instan**. Pengajuan multi-bank paralel tidak ada di aplikasi BTN, dan cek kredit instan belum dimiliki Estora (Estora: pencatatan iDeb manual). Keduanya terdaftar OJK dan punya program mitra developer/agen. Jadi keduanya adalah **mitra integrasi** untuk modul pre-screen dan KPR Estora, bukan pesaing.

### Cited Findings

#### 4a. IDEAL – Pengajuan KPR Online
- **Fakta store (Play):** paket `id.ideals.app`, penerbit Ideal Indonesia; 100.000+ unduhan; 4,6 (223 ulasan); v2.4.92; update 13 Feb 2026; rilis 12 Mei 2022 — [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id)
- **Fakta store (iOS):** ID 1621647910, seller PT. HIDUP IDEAL SEJAHTERA; v2.4.92 (14 Feb 2026); 4,5 (42 rating) — [App Store](https://apps.apple.com/id/app/id1621647910)
- **Fitur [Klaim]:** KPR Primary/Secondary/Takeover; "memilih 3 produk KPR dari 3 bank pilihan Anda", cukup mengirim dan memverifikasi data sekali; Affordability Calculator; real-time Tracking. Bank mitra: Mandiri, OCBC NISP, CIMB Niaga, Permata, Danamon, Panin, Maybank. Developer mitra: Sinar Mas Land, Agung Sedayu, Ciputra, Cipta Harmoni Lestari — [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id)
- **Layar [Terverifikasi]:**
  - Layanan: Take Over KPR, Pinjaman Multiguna, Secondary/Primary KPR.
  - "Aktivitas Pengajuan KPR" (Berlangsung/Selesai) dengan kartu "Aurora Residence Unit AB1 – 3 Produk KPR – 2 Bank – Pengajuan Fase 1".
  - Hasil analisis dengan rekomendasi produk dan cicilan.
  - **"ideal Checking"**: hasil verifikasi KTP + riwayat kredit, "Status Scoring: Hijau", dan **"Pembatalan Otomatis 7 Des 23, 23:59"** (masa berlaku).
  - Kuis "ideal Compass" untuk rekomendasi.
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id); berkas `prahuni_ideal/play_01,02,04,06.png`
- **Ulasan, pujian multi-bank dan CS:**
  - "Bisa ngajuin KPR antiribet ke 3 bank sekaligus cuma dari satu aplikasi" (iOS, 14/04/2023)
  - "CS cepat sekali respons" (Play, 1 Mei 2024)
  - Sumber: [App Store](https://apps.apple.com/id/app/id1621647910), [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id)
- **Ulasan, keluhan:**
  - "kirim OTP tidak sampai2. Sudah diulang sampai 10x" (Play, 23 Feb 2023)
  - "Awal2 respon cepat sekali, tapi setelah tau data saya respon tidak ada" (Play, 16 Jan 2024)
  - Sumber: [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id)

#### 4b. Ringkas (web app/PWA)
- **Platform:**
  - Web `app.ringkas.co.id` dengan banner **"Tambah Ringkas di layar utama untuk akses cepat"** (pola install PWA). Alur di halaman: Pilih Produk → **Ajukan Sekaligus** ("Satu pengajuan untuk banyak bank dan multifinance") → **Pantau Pengajuan** ("Monitor status dari setiap bank dan multifinance") → Dapatkan Persetujuan. Produk: KPR properti baru, KPR seken, Take Over, Take Over & Top Up, Kredit Agunan Properti. Terdaftar OJK S-550/IK.01/2024 — [app.ringkas.co.id](https://app.ringkas.co.id/)
  - Situs utama: "Prakualifikasi cepat", asisten RISA AI (simulasi cicilan, pengecekan kapasitas), "Mitra Property & Agent", serta "Ringkas Hadir di Aplikasi DANA" (10 Des 2025) — [ringkas.co.id](https://ringkas.co.id/)
- **Aplikasi native:** tidak ada. "Ringkas App" di iOS (ID 6755289734, Jerry Mulyadi) dan "Ringkas: Ringkasan Buku" di Play adalah aplikasi ringkasan buku yang tidak terkait — [iTunes Lookup](https://itunes.apple.com/lookup?id=6755289734&country=id)
- **Screenshot web:** `prahuni_ringkas/web_01_landing_ringkas.co.id.png`, `prahuni_ringkas/web_02_app.ringkas.co.id.png`

### Inferences
- Ringkas adalah bukti bahwa produk keuangan berlisensi OJK bisa berjalan sebagai **PWA tanpa aplikasi native**, dan bahkan didistribusikan lewat aplikasi lain (DANA). Ini memperkuat posisi PWA Estora untuk portal pembeli.
- Polanya "satu pengajuan, banyak bank, status per bank" dengan "skor hijau/kuning/merah dan masa berlaku". Estora bisa memakai format yang sama untuk pipeline KPR multi-bank internalnya: tampilan status per bank di portal pembeli, dan hasil pre-screen iDeb dengan masa berlaku.
- Cluster ulasan bintang 5 IDEAL pada 24 Apr – 1 Mei 2024 (dibalas developer 26 Apr – 2 Mei) dengan gaya serupa ("CS sangat ramah dan fast response") mungkin hasil kampanye ulasan. Rating 4,6 sebaiknya tidak dijadikan bukti kepuasan.

### Gaps
- Jumlah pengguna/aplikasi KPR yang diproses IDEAL dan Ringkas tahun 2025–2026 tidak ditemukan.
- Belum terlihat apakah IDEAL/Ringkas punya API atau portal mitra developer yang bisa menerima pengajuan dari sistem developer. Menu "Portal Agen/Kemitraan" ada di situs IDEAL (riset terdahulu), tetapi isinya di balik login.

---

## 5. Sintesis: matriks fitur (termasuk Estora), pola yang belum dimiliki Estora, dan aplikasi yang sebaiknya diintegrasikan

### Takeaway
Estora unggul pada kedalaman operasi internal: termin/denda berjurnal, pembatalan/refund, mesin fee mitra, konstruksi berbukti foto, BAST/garansi, portal pembeli OTP WA, dan offline. Yang belum dimiliki Estora, berdasarkan apa yang terlihat di aplikasi pesaing, adalah **antarmuka transaksi bagi pihak luar**:
- pembayaran online VA;
- booking mandiri pembeli;
- portal login mitra/agen dengan laporan komisi dan tautan katalog;
- cek kredit instan;
- penagihan WA satu ketuk;
- persetujuan mobile dengan push.

Aplikasi BTN/Tapera dan agregator KPR sebaiknya **diintegrasikan**. Vendor ERP (Porta Pro/ECes.Q, Simandor, Mandep, Ndalem, vCloud+) adalah pesaing langsung.

### Cited Findings

**Legenda:** Y = ada dan terlihat di screenshot/listing/dokumen resmi · K = hanya klaim deskripsi · P = parsial · – = tidak terlihat/tidak ada. Kolom Estora diambil dari [estora_inventaris_fitur.md](../Riset%20kompetitor%20dan%20BTN%20Housingpreneur/estora_inventaris_fitur.md) (status Ada/Parsial/Tidak ada). Sumber sel kompetitor ada di bagian 1–4 di atas.

**Tabel A — Bank, pemerintah, agregator KPR (sisi developer dan pembeli)**

| Fitur siklus | Estora | BTN Properti for Developer | bale by BTN (Bale Properti) | Tapera Mobile (eks SiKasep) | IDEAL | Ringkas |
|---|---|---|---|---|---|---|
| Platform | Web/PWA | Android + iOS | Android + iOS | Android + iOS | Android + iOS | Web/PWA |
| Pengguna | Staf developer + pembeli | Admin/marketing/finance developer | Pembeli/debitur | Calon debitur subsidi | Pembeli | Pembeli |
| Lead/CRM + atribusi | Y (6 webhook, first/last touch) | – | – | – | – | – |
| Stok unit & siteplan | Y (Studio Site Plan) | Stok Y, siteplan – | Listing hunian Y | Listing proyek + jumlah unit subsidi Y | K (proyek mitra) | – |
| Reservasi/booking oleh staf | Y (masa tahan) | Y (status Booked, SPR) | – | – | – | – |
| Booking mandiri pembeli | – (showroom hanya lead) | – | – | – | – | – |
| Bayar online VA/QRIS | – (transfer + unggah bukti) | Y (VA BTN booking fee/DP) | Y (mbanking, QRIS) | – | – | – |
| Jadwal bayar/piutang/denda + jurnal | Y | P (monitoring BF/DP/cash) | – | – | – | – |
| Pengajuan & status KPR | Y (multi-bank internal, tanpa API) | Y (BTN saja; 5 status) | Y (BTN saja) | Y (FLPP; 6 tahap di SiKasep) | Y (≤3 bank) | Y (banyak bank) |
| Cek kredit/pre-screen | P (iDeb manual) | – | P (kemampuan bayar) | P (subsidi checking) | Y (ideal Checking, skor) | Y (prakualifikasi) |
| Dokumen SPR/PPJB | Y (docgen) | Y (SPR + parameterisasi) | – | – | – | – |
| Komisi/afiliasi | P (mesin fee, tanpa login mitra) | – (insentif admin = program) | – | – | K (referral, portal agen) | K (mitra agen) |
| Konstruksi & QC | Y | – | – | P (tahap "layak huni") | – | – |
| Pembatalan/approval | Y (pemisahan tugas) | P (status Reject) | – | – (diminta pengguna) | P (pembatalan otomatis cek) | – |
| BAST/garansi | Y | – | – | – | – | – |
| Notifikasi | P (WA siap-live, in-app) | P (Pesan, Live Chat) | ? | OTP SMS/email | OTP + CS | WA CS |
| Offline | Y (PWA antrean) | – | – | – | – | – (PWA, offline tak diketahui) |
| Portal pembeli | Y (OTP WA) | – | Y | Y | Y | Y |

**Tabel B — Aplikasi sales/agen developer dan portal agen**

| Fitur siklus | Estora | Paramount Sales | SML eAgent | Pesona Kahuripan | Perumnas (QPer + Digital Platform) | Pinhome Rekan Agen | Rumah123 Pro | Mitra Ningrat (riset terdahulu) |
|---|---|---|---|---|---|---|---|---|
| Platform | Web/PWA | Android + iOS | Android + iOS | Android | Android (QPer) + web (platform) | Android + iOS | Android + iOS | Web |
| Pengguna | Staf + pembeli | Sales/agen | Agen (+ sales internal) | Pembeli | QC internal; publik/afiliasi | Agen | Agen/in-house | Mitra/afiliasi |
| Lead/CRM | Y | – | – | P (Undang Teman) | K (platform) | Y (Leads, Chat) | Y (Klien Saya) | K |
| Stok & siteplan | Y | Y (siteplan interaktif, posisi unit, status, harga) | – | Y (grid kavling per blok) | K (platform) | P (proyek primary) | P (flag "baru dari developer") | Y (katalog) |
| Booking mandiri pembeli | – | – | – | Y (BOOKING) | – | – | – | K ("Booking Sekarang") |
| Bayar online VA | – | – | – | Y (VA BTN) | – | – | – | – |
| KPR | Y | – | – | K | K (simulasi) | Y (simulasi + ajukan/referral) | – | Y (simulator) |
| Pre-screen kredit | P | – | – | – | – | – | – | K (Instan BIC) |
| Materi jual (pricelist/brosur) | P (dokumen, showroom) | Y (pricelist PDF, brosur) | – | – | – | Y (AI deskripsi) | Y (AI foto/video) | Y (bank konten) |
| Komisi/poin/afiliasi | P (mesin fee, tanpa login mitra) | – | Y (poin, income, paid per transaksi) | P (referral) | K (Sobat Bisnis Perumnas) | Y (komisi primer >3%, komisi KPR) | – (agen bayar iklan) | Y (berjenjang, leaderboard) |
| Konstruksi & QC | Y (foto watermark, punch list) | – | – | – | Y (skor NDR, NCR, EWS) | – | – | – |
| Approval | Y | – | – | – | Y (closing hanya pimpinan proyek) | – | – | – |
| Tautan/QR yang bisa dibagikan | Y (showroom tautan & QR) | Y (share/ekspor) | – | Y (ikon share unit) | Y (share laporan QC) | Y (Link Katalog, Bagikan Hasil) | – | Y (Share produk) |
| Login pihak luar | Pembeli saja | Sales | Agen (daftar mandiri) | Pembeli | Afiliasi (K) | Agen | Agen | Mitra (daftar mandiri) |

**Tabel C — Software developer (mobile/web) dan konstruksi**

| Fitur siklus | Estora | Ndalem Mobile | Mandep | Simandor + SmartMandor | Porta Pro (ECes.Q) | vCloud+ Approvals | AutoKon |
|---|---|---|---|---|---|---|---|
| Platform | Web/PWA | Android (+ web) | Android + iOS (+ web) | Web (+ app, listing tak ditemukan) | Android + iOS (+ web ECes.Q) | Android (+ web) | WhatsApp |
| Unduhan | n/a | 10+ | 500+ | n/a | 1 rb+ | 1+ | n/a |
| Lead/CRM | Y | P (laporan pemasaran) | P (menu Pemasaran) | Y (data konsumen + penghasilan & cicilan) | P (Marketing Tools) | – | – |
| Stok & siteplan | Y | Y (gambar + daftar kavling berstatus) | K (siteplan interaktif web) | Y (siteplan + timeline bayar & progres) | Y (siteplan berwarna, 10 status) | – | – |
| Reservasi/booking staf | Y | Y (Dipesan) | Y (booking fee) | Y (Customer Booking + SPR) | Y (Reserve + konfirmasi) | Y (approval Reservasi) | – |
| Bayar online VA/QRIS | – | – | – | – | – | – | – |
| Piutang/termin/denda | Y (denda berjurnal) | P (piutang/hutang) | P (total/sisa piutang) | P (approval bayar → e-invoice) | Y (kartu pembayaran, tunggakan, jatuh tempo) | P (antrian AR) | – |
| KPR | Y | K (web: KPR bank/non-bank) | – | P (status pengajuan) | Y (SP3K/Akad dalam status unit) | – | – |
| Komisi mitra | P | – | – | – | – | – | – |
| Konstruksi & foto | Y (watermark, verifikator ≠ pengaju) | P (RAB HPP) | Y (laporan harian + foto) | Y (foto progres, laporan harian) | Y (progres % per unit) | – | Y (WA, laporan AI) |
| Approval mobile | P (PWA, tanpa push) | – | Y (Persetujuan) | Y (approval bayar, stok > RAP) | P (status Batal) | Y (bertingkat, biometrik, push) | – |
| Pembatalan/pengalihan hak | Y | – | – | – | P | Y | – |
| BAST/garansi | Y | P (status BAST) | – | – | P (status BAST) | – | P (laporan kesiapan serah terima, keluhan pembeli) |
| Penagihan via WA | P (WABA, simulasi) | – | – | grup WA per konsumen (support) | Y ("Kirim WA Tagihan" manual) | – | Y (WA-native) |
| Offline | Y | – | – | – | – | – | n/a |
| Aplikasi pembeli | Y (portal OTP) | – | – | Y (SmartMandor) | – (Porta Home = penghuni) | – (vCloud Mobile = penghuni) | P (lapor keluhan) |
| Absensi geo/selfie | Y (absensi tenaga kerja) | – | Y | Y | – | – | – |

**Pola yang paling relevan dan belum dimiliki Estora (urut prioritas, dengan bukti):**
1. **Pembayaran booking fee/DP via VA dengan status otomatis.** BTN memberi VA ke developer lewat BTN Properti for Developer — [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id). Pesona Kahuripan memakai VA BTN di aplikasi pembeli, lengkap dengan tombol "Lihat Status Pembayaran" — [Google Play](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id). Estora masih memakai transfer + unggah bukti + verifikasi finance (inventaris).
2. **Booking mandiri pembeli dari grid kavling/siteplan** (BOOKING → VA → status) — [Pesona Kahuripan](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id). Estora punya mesin reservasi bermasa tahan, tetapi showroom publiknya hanya menangkap lead (inventaris).
3. **Portal login mitra/agen**, dengan bukti di tiga aplikasi:
   - registrasi mandiri, dasbor poin/komisi per transaksi, dan status "Paid" — [eAgent SML](https://play.google.com/store/apps/details?id=com.mycompany.eagent&hl=id);
   - tautan katalog pribadi dan simulasi KPR yang bisa dibagikan — [Pinhome](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id);
   - leaderboard dan microsite (riset Mitra Ningrat).

   Mesin fee Estora (7 skema, berjurnal) belum terlihat oleh mitra.
4. **Cek kredit/prakualifikasi instan dengan skor dan masa berlaku**: "ideal Checking" (skor Hijau, pembatalan otomatis) — [IDEAL](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id); prakualifikasi Ringkas — [ringkas.co.id](https://ringkas.co.id/). Estora masih mencatat iDeb secara manual.
5. **Penagihan WhatsApp satu ketuk dari kartu pembayaran** ("Kirim WA Tagihan/Info") — [Porta Pro](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id). Estora bergantung pada WA Cloud API yang belum terbukti live (inventaris).
6. **Kotak persetujuan mobile dengan push dan kunci biometrik** untuk pembatalan, pengalihan hak, dan reservasi — [vCloud+ Approvals](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id). Inventaris Estora hanya menyebut notifikasi in-app WebSocket, tanpa Web Push.
7. **Skor mutu per unit/kontrak vs target + Early Warning System tenggat closing temuan + share laporan** — [QPer Perumnas](https://play.google.com/store/apps/details?id=com.perumnas.qper&hl=id). Estora punya QC → punch list dan eskalasi telat bangun, tetapi belum ada skor mutu dengan target.
8. **Materi jual siap pakai untuk sales**: pricelist PDF yang bisa digabung, brosur, dan posisi unit di siteplan — [Paramount Sales](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id). Juga AI deskripsi/foto — [Pinhome](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id), [Rumah123 Pro](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id).
9. **Penilaian developer oleh pembeli**: usulan pengguna Tapera "Pelanggan KPR bisa kasih rating ke Developer nya" (20 Sep 2024) — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id). Ini bisa menjadi fitur reputasi berbasis data garansi/komplain Estora [Inferensi].

**Keluhan berulang lintas aplikasi (pelajaran desain):**
- Login/OTP gagal muncul di BTN Properti for Developer, bale by BTN, Tapera Mobile, SiKasep, IDEAL, dan 99.co (lihat kutipan di bagian 1–4).
- Status tidak sinkron dan data tidak bisa diedit/dibatalkan: Tapera Mobile, SiKasep.
- Lead palsu/pasif: Pinhome, Rumah123 Pro.
- Biaya/aturan insentif berubah: Rumah123 Pro, Pinhome.
- Sumber: tautan store di bagian 1–2.

**Integrasi vs bersaing:**

| Aplikasi | Rekomendasi | Alasan (bukti) |
|---|---|---|
| BTN Properti for Developer / balé developer / Bale Properti | **Integrasi** (sinkron stok, SPR, status KPR BTN; pakai VA BTN) | Gratis, >12.600 developer, insentif admin developer dari BTN, dan BTN adalah penyelenggara Housingpreneur — [Kontan](https://keuangan.kontan.co.id/news/btn-targetkan-pengajuan-kpr-online-lewat-bale-properti-capai-47-ribu-pada-tahun-ini) |
| Tapera Mobile / SiKumbang | **Integrasi** (ekspor/rekonsiliasi stok; tahap FLPP dicatat di portal pembeli) | Wajib untuk FLPP. Pembeli melihat stok developer di Tapera, dan keluhan stok tidak akurat merusak reputasi developer — [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id) |
| IDEAL, Ringkas | **Integrasi/kemitraan** untuk pre-screen kredit dan pengajuan multi-bank | Berlisensi OJK, multi-bank, punya program mitra. Developer bukan Pelapor SLIK (riset terdahulu) — [IDEAL](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id), [Ringkas](https://app.ringkas.co.id/) |
| Rumah123 Pro / 99.co, Pinhome Rekan Agen | **Integrasi sebagai sumber lead dan jaringan agen** (lead masuk ke webhook, agen terdaftar sebagai mitra di mesin fee) | Portal menjual traffic/lead dan tidak mengelola operasi developer. Agen mengeluhkan kualitas lead, sehingga atribusi sampai akad bernilai — [Rumah123 Pro](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id), [Pinhome](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id) |
| AutoKon | **Koeksistensi/integrasi** untuk developer anggota REI (terima laporan WA sebagai bukti) | Didukung REI lewat MoU 30 Okt 2025, tetapi produknya tidak terdokumentasi publik — [Investortrust](https://www.investortrust.id/business/83968/rei-gandeng-autokon-untuk-perkuat-digitalisasi-pengawasan-proyek-perumahan) |
| Porta Pro/ECes.Q, Simandor, Mandep, Ndalem, vCloudProperty+ | **Bersaing langsung** | Menjual sistem operasi developer yang sama (stok, booking, piutang, konstruksi) |
| Paramount Sales, SML eAgent, Pesona Kahuripan, Perumnas QPer | **Bukan pesaing; acuan fitur** | Aplikasi in-house developer besar. Estora bisa menawarkan modul setara secara siap pakai kepada developer kecil/menengah [Inferensi] |

### Inferences
- Ada tiga "antarmuka luar" yang paling menentukan nilai Estora di mata juri BTN dan developer subsidi: (1) VA/pembayaran online yang terhubung ke BTN, (2) portal mitra/agen, dan (3) status KPR/FLPP yang jelas untuk pembeli. Ketiganya memanfaatkan mesin yang sudah ada di Estora (termin, fee mitra, pipeline KPR), sehingga biaya tambahannya kemungkinan lebih kecil daripada membangun dari nol. Ini belum diukur.
- Di sisi integrasi BTN, Estora sebaiknya tidak mereplikasi pengajuan KPR BTN. Lebih baik Estora menjadi tempat **menyiapkan berkas** (pre-screen, kelengkapan dokumen), lalu admin mengirim lewat balé developer, sehingga developer tetap mendapat insentif admin BTN. Status SP3K/akad kemudian kembali dicatat di Estora.
- Pola WA satu ketuk (wa.me) bisa menjadi jembatan sementara selama WABA Estora belum live. Ini tidak butuh persetujuan template Meta.
- Booking mandiri publik + VA membawa risiko (double booking, pembatalan, refund). Estora punya keunggulan di sini karena mesin masa tahan, pembatalan, dan refund berjurnalnya sudah ada. Pesona Kahuripan tidak menunjukkan penanganan sisi itu.

### Gaps
- Tidak ada data pemakaian nyata (DAU, transaksi) untuk aplikasi mana pun selain angka unduhan store dan rilis pers BTN.
- Tidak diverifikasi apakah BTN membuka API VA/Bale Properti untuk vendor software developer. Sampai terbukti, rekomendasi "integrasi" berarti ekspor/impor manual atau kerja sama formal.
- Penilaian "Y" untuk fitur kompetitor berasal dari screenshot pemasaran, yang bisa berupa mock-up. Kedalaman (misalnya apakah Porta Pro menghitung denda) tidak bisa diuji tanpa demo.

---

## 6. Bukti visual: screenshot yang disimpan (folder `screenshots/` di folder riset ini)

### Takeaway
Ada 64 berkas di 17 folder `prahuni_*`: 60 screenshot store resmi (Google Play, 4 per aplikasi untuk 15 aplikasi) dan 4 screenshot web Playwright (Simandor, Ringkas). Tidak ada screenshot untuk balé developer web (403), Perumnas Digital Property Platform (URL tak ditemukan; situs 502), AutoKon (tanpa situs/app), SmartMandor (listing tak ditemukan), eAgent iOS, dan 99.co (sisi pencari, tidak disimpan).

### Cited Findings
Store screenshots diunduh dari `play-lh.googleusercontent.com/<id>=w1080` (ID diambil dari halaman listing Play publik, varian `=w526-h296-rw`). Nomor berkas `play_NN` = urutan di galeri listing. Screenshot web memakai viewport 1366×900, deviceScaleFactor 1, tinggi di bawah 8000 px.
- **BTN Properti for Developer** — listing [Google Play](https://play.google.com/store/apps/details?id=com.btnproperti.developer&hl=id) — isi: Dashboard Penjualan; Manajemen Stok; Pengajuan KPR; Account Management
  - `screenshots/prahuni_btn_properti_developer/play_02.png` ← https://play-lh.googleusercontent.com/EwYtgP3PdXzh5NS7NPFlt8Q-gL7C_6m5HXUa3kZY8bbtny_LNemGWPihX5P5rjEcWP6DfEwDxd2t5J7xGeiryg=w1080
  - `screenshots/prahuni_btn_properti_developer/play_03.png` ← https://play-lh.googleusercontent.com/wfzQxoyenolBdLfHInoyrCfHXCZ6cP9ScU1qYVzbpiXioKaI8O0fwZS-qXwkNBQ_C_lJV3twc8VhWKcsruHhTQ=w1080
  - `screenshots/prahuni_btn_properti_developer/play_04.png` ← https://play-lh.googleusercontent.com/CtzSMC7PsD-EMVpm5iVP_0YNj7ESlzTRLgH4Rfjka8IZb29P5-nm03_wk8_uQqUpIz8F7u3g-aJy5dV8e1vUhdo=w1080
  - `screenshots/prahuni_btn_properti_developer/play_05.png` ← https://play-lh.googleusercontent.com/obV1rlg7BJhktbxI6Uk4xN4CfQg1eK2EwdhgdNi7m_dnSgtL3DnVWZDzH_xLTwPUUwuQBSSNiwUpn6E_7QZc=w1080
- **bale by BTN** — listing [Google Play](https://play.google.com/store/apps/details?id=id.co.btn.mobilebanking.android&hl=id) — isi: Beranda; ekosistem layanan; satu akun; balé space (cari hunian)
  - `screenshots/prahuni_bale_by_btn/play_01.png` ← https://play-lh.googleusercontent.com/4pSV9HXyhX8VD6YPc9Ns5smQCx_fGgNHDLnipZhKIglWN9NcWcla6ktimsvshhITWeRm_B8RjRtoWTgeLCFu3g=w1080
  - `screenshots/prahuni_bale_by_btn/play_02.png` ← https://play-lh.googleusercontent.com/Gfoizi6ZMMClVNdBfnWg_I8vVpugEWaWk9BgUAZ02R4zmeGUG1N1hAKPGb8ZPoM-87wg_v3aiLGuaNHwvUdyIjg=w1080
  - `screenshots/prahuni_bale_by_btn/play_03.png` ← https://play-lh.googleusercontent.com/-9O9dvASwnO_Ht6skfA9-uhoITcAmkMEeWZ1rwwEPH46D6RTHlpVSgJhaZ4TY29oqIXYVPsBdqwGYYXbyytc=w1080
  - `screenshots/prahuni_bale_by_btn/play_06.png` ← https://play-lh.googleusercontent.com/FFfiEFRoQOQeowBD609jsYC6tAbl8hcLLBWeyO6uRlc8VL1xZSzUZi7LG6REMD0jHnsl4Abp80IYwDoWWkiomg=w1080
- **Tapera Mobile** — listing [Google Play](https://play.google.com/store/apps/details?id=com.tapera.mobile&hl=id) — isi: Beranda; Status Pemanfaatan/Lacak Status; pencarian perumahan + unit subsidi; menu pembiayaan
  - `screenshots/prahuni_tapera_mobile/play_02.png` ← https://play-lh.googleusercontent.com/kRU4Dupd7g1Z-qdJWlN6n56R0wRVrU-VJD6rXE7vjVQUR2kuk0L8AtTwbwNos-EaSsWPLqlYVIRYto73zhRw=w1080
  - `screenshots/prahuni_tapera_mobile/play_03.png` ← https://play-lh.googleusercontent.com/xDLCwoXetdouCDL6o5JfqJhy4C1iQit5BcKXDX7ykBtTtjyv9fbqlKpc5Vm1MffGm94N5WmlITdxPhsTGKwl4A=w1080
  - `screenshots/prahuni_tapera_mobile/play_04.png` ← https://play-lh.googleusercontent.com/X7aVhpkYHpKrtuygfr7AhpNeDUOpOx3H2QdKUZEWU1V_Ol72EExKgHqYDCipqmH3aqy4uZXiPDO4nLE8DZVi=w1080
  - `screenshots/prahuni_tapera_mobile/play_05.png` ← https://play-lh.googleusercontent.com/2F9nFpCdATgL-WnWH18kiReoQGRww8rrseSwa1ZVi09WIGrJE6UyNpVc2bqTRE-1IAhRcuVJo9xBorghQeKI=w1080
- **SiKasep (lama)** — listing [Google Play](https://play.google.com/store/apps/details?id=com.lpdpp.sikasep&hl=id) — isi: Rekam Data Diri; Menu Utama; pilih bank pelaksana; status 6 tahap
  - `screenshots/prahuni_sikasep/play_03.png` ← https://play-lh.googleusercontent.com/R4lPqAO-RkwYp1DAL8sj2cKlWJVZF7q6CX1swRff6Dz4Lyeif7dXwXAxMmB7UXtQjY_sQlg3svnpMgo1jVWxhA=w1080
  - `screenshots/prahuni_sikasep/play_04.png` ← https://play-lh.googleusercontent.com/LoY1ELLWMPdaeG4tTgEYssA7Oya4Klxge-M4VwqGqljg217ZRJDdJAe9PxKbimeqfl8MIcV5N5qbOTwghACx4Q=w1080
  - `screenshots/prahuni_sikasep/play_06.png` ← https://play-lh.googleusercontent.com/iRDcLwiT8YI_xNfCszlGcInTsjWnIeAksnrLzHQehP6nBRu6chorgZUAJ3iqcp5_MKqJrCFRYFqJ5UeZD-TDZA=w1080
  - `screenshots/prahuni_sikasep/play_07.png` ← https://play-lh.googleusercontent.com/jlCSiJpPBj4AArcijAx2hAXxe_s2GqjRBeee5pI4MV_6IGjpdZbL0P68iNw0g0KNtU3ONQllkclDXSlD_tCp=w1080
- **Paramount Sales** — listing [Google Play](https://play.google.com/store/apps/details?id=com.paramountland.sales&hl=id) — isi: Project detail (Siteplan/Brochure/Pricelist); Home; siteplan interaktif; Unit Detail + posisi unit
  - `screenshots/prahuni_paramount_sales/play_05.png` ← https://play-lh.googleusercontent.com/tFWlR-fdGkwqogXeBfK9bQdmdLVDcAoRiqFS-PEkR7hDIF4HvjeqBaDwxw5oqELSg_fziHoX6X1dJwIEAl2oBe0=w1080
  - `screenshots/prahuni_paramount_sales/play_03.png` ← https://play-lh.googleusercontent.com/OVKMOq1MIma7lbB0ZG-o-_FHiAmkaYUZehL9UjSj8t7_gjtQTqmSgYtgDEUk5Z5-W32pz6rDOzfFRBIBkodPhfo=w1080
  - `screenshots/prahuni_paramount_sales/play_07.png` ← https://play-lh.googleusercontent.com/VQufwtyDvjB01QNDKwHFbphddIA3of9Vsosp2HSNYxMeyU17QIuJ_p9nz1rIYDf53U14DdxiAJH2UL51HM3u=w1080
  - `screenshots/prahuni_paramount_sales/play_08.png` ← https://play-lh.googleusercontent.com/FD4KyM1sFGzzmdFjPpmdqG3nNxtuuGavTMne06DBbID3kJVQSOUicSoWkHfX0pxFfUqfWOKTXle1pBizECH7Bw=w1080
- **eAgent Sinar Mas Land** — listing [Google Play](https://play.google.com/store/apps/details?id=com.mycompany.eagent&hl=id) — isi: My Point + Monthly Point; Detail Point; Transaction Detail; daftar Transaction
  - `screenshots/prahuni_sml_eagent/play_04.png` ← https://play-lh.googleusercontent.com/mdD-OPejESpgEsBvFwp6b02v3pPzcVYDkwS1iRNoiTrjlJeAaS6BoDd_zRf2DHH7U1lYj4kGc4A-O74UilJ3yL4=w1080
  - `screenshots/prahuni_sml_eagent/play_05.png` ← https://play-lh.googleusercontent.com/hVo5w8eKdYZZdUgdpMlMk74g3QycMXDFrdmnCeC5TQzhpsnpN28RWTLX8J3RBIcZn8zUgwrqMlXpv2twwyu7=w1080
  - `screenshots/prahuni_sml_eagent/play_06.png` ← https://play-lh.googleusercontent.com/ozGhA1AyOTTdaHgrh5nxw6Ugz63RWsexe5KGsTWJblp-eh3jMU7sK174OBZEVIwSkg8x0WgRyJc3eglcP1w0=w1080
  - `screenshots/prahuni_sml_eagent/play_07.png` ← https://play-lh.googleusercontent.com/szfcFz1D_ATTI4iy9wB1YL3hbseQJ0vb9Pq7_DFYO7ZSc_wiQ0Fjyo3b9-wQxioYdGbYFkRQ1bYjzqCE4MkB5Q=w1080
- **Pesona Kahuripan** — listing [Google Play](https://play.google.com/store/apps/details?id=com.pesonakahuripan.mobile&hl=id) — isi: Tipe unit; beranda + Undang Teman; pilih kavling + BOOKING; pembayaran VA BTN
  - `screenshots/prahuni_pesona_kahuripan/play_01.png` ← https://play-lh.googleusercontent.com/ka0Lxtyr58CjQY7124tvc73b2H8ppC6pwdP27c1QbV0YXjkwcGcSYntvahjGCR5bMgufsVGi1wbhBr-WqQK48w=w1080
  - `screenshots/prahuni_pesona_kahuripan/play_02.png` ← https://play-lh.googleusercontent.com/AwcpU5zMvIB04wjcWgTdrsjfb4A5ZCRW_BPWyAJkYIOmOm8vbMyeC4cHMQGJinraW2k5mhpdlUx5K7FuqCXMIA=w1080
  - `screenshots/prahuni_pesona_kahuripan/play_03.png` ← https://play-lh.googleusercontent.com/Ok6PuJnWbw_bfWa2J9sfK1_mBgZZ_yZIzci9v1su9J2fPxteSDd1gymq76UeQZpAHWA2MV-2bG3PwpMkzVgpzQ=w1080
  - `screenshots/prahuni_pesona_kahuripan/play_04.png` ← https://play-lh.googleusercontent.com/Dotm1ylP74tPQ5eprh6-LpUcCi0CrUiF0NW8PxRTlg0UITgB8SMAYPU2yu7DciPkN1GFRuzVjrFbmlko2jRf=w1080
- **QPer Perumnas** — listing [Google Play](https://play.google.com/store/apps/details?id=com.perumnas.qper&hl=id) — isi: Dashboard skor; NCR open/closed; penilaian per sekuens; Detail NDR skor vs target
  - `screenshots/prahuni_perumnas_qper/play_02.png` ← https://play-lh.googleusercontent.com/y-iyHScQrCFeCuwYkeo1XTwYB0kQ-rm6zhshjdVpeVBaLds5yQ0JmltwmZ6JTL_vm-Z6TH37nSt7tJpOvvj7zrE=w1080
  - `screenshots/prahuni_perumnas_qper/play_03.png` ← https://play-lh.googleusercontent.com/S8NJ7sCJqF2_sVEctFVN1ozXMYwyQVSy8p6k5yxK0Wp_9o_H3aWTAee01rWSfSzuXYjVAEyD2FGp9sR36Qf06OM=w1080
  - `screenshots/prahuni_perumnas_qper/play_04.png` ← https://play-lh.googleusercontent.com/cBtkT2vJ3VKecHlPGWxqJMwkMxsDI_Iou-YJ7uKd2k3Q58eHz282GHzWCspvCtH0NzBGE2XzCIc1t5ykZ0Z2jQ=w1080
  - `screenshots/prahuni_perumnas_qper/play_06.png` ← https://play-lh.googleusercontent.com/OhELwNmUWU7j66qGNZ2k2tQr88a-R7E7G0G9MgClULmR367Qqc4NYKngZOZUh1G7f-d3UbnGduK1aZdxiEPo=w1080
- **Rekan Agen Properti Pinhome** — listing [Google Play](https://play.google.com/store/apps/details?id=id.pinhome.agent&hl=id) — isi: Beranda agen; AI deskripsi; Link Katalog; Simulasi KPR + Bagikan Hasil
  - `screenshots/prahuni_pinhome_rekan_agen/play_01.png` ← https://play-lh.googleusercontent.com/azlpsb_23xoql-RUfNl_NatKqXdBEk9bGMIjEmPF-1KOJBsO0hxdEJdcna7-hf6mTwumZnBPp0Q5y-CsGMvIzA=w1080
  - `screenshots/prahuni_pinhome_rekan_agen/play_03.png` ← https://play-lh.googleusercontent.com/TJPEwOUFxyZTbjaTc3kEDaxp8HogRh_3rLom0kEXDQveU05MHvPaMOPp_sSRtECEw4-lAXLQvySp_YSYxBPiwA=w1080
  - `screenshots/prahuni_pinhome_rekan_agen/play_04.png` ← https://play-lh.googleusercontent.com/Ea9CGMGmbT6pW0NE-hCXdLW9oSQQ2tt53iQZvaM_WDlWpkduo7mLDO_4PWjYnT8kKp0wayGHXzi9MEihrgnhnw=w1080
  - `screenshots/prahuni_pinhome_rekan_agen/play_06.png` ← https://play-lh.googleusercontent.com/8sw_XIRqoga7qubFBRtk_CpZnPUH-coPUkAAawFxT_53rBms6ITdFtQUeI6WSJMFq2bzn4D4N3SIcFeh8uRfyw=w1080
- **Rumah123 Pro** — listing [Google Play](https://play.google.com/store/apps/details?id=com.rumah123.android.agent2&hl=id) — isi: Dasbor (AI, Sundul, Boost); daftar iklan + skor; Klien Saya (leads); wizard iklan "baru dari developer?"
  - `screenshots/prahuni_rumah123_pro/play_02.png` ← https://play-lh.googleusercontent.com/gPd6IMS2VCG_8meSMbi5rOOah19VJXXxncp_uZPRR831HuggmS3jO-9Gycgv_7HhHvHDCvN7QZs0RTvC07Mm214=w1080
  - `screenshots/prahuni_rumah123_pro/play_03.png` ← https://play-lh.googleusercontent.com/swm8fTyOgBnsY1iSHlXRznM6F7x9M-ny0PFxXU5KNtmihcAajr2fhRQfwNezoy_LFKim_HSPlheBxP4xFw3w=w1080
  - `screenshots/prahuni_rumah123_pro/play_04.png` ← https://play-lh.googleusercontent.com/vd3hAwXe8xLx6DoUI2v0rSbpjGaby-dAYb8EDLNxbqq0iwaEfuKINVv8HNSazTXG9MDWXKrkWipmQrvHpUuqGNg=w1080
  - `screenshots/prahuni_rumah123_pro/play_05.png` ← https://play-lh.googleusercontent.com/36ZIaE5q64sKfYWPoRet0gPrnr6XJWqJ-SuLG50MkYh28EdIU4sv1Ux0AZqA6eESE7bRVwDVxBykqDaLLOF-vY8=w1080
- **Ndalem Mobile** — listing [Google Play](https://play.google.com/store/apps/details?id=com.pt_ndalem_technology.ndalem_mobile_app&hl=id) — isi: Daftar Menu; Siteplan + Daftar Kavling; Profil (perumahan dikelola); Beranda ringkasan keuangan
  - `screenshots/prahuni_ndalem_mobile/play_01.png` ← https://play-lh.googleusercontent.com/9x0BhmHKVczMBTA7k5K5CtTQWvkfJCNO_6gu7SjHGarCea8ZSnGtizlpR-ZSiFNY5aYH_XX_SDDPZxiJa5jFQA=w1080
  - `screenshots/prahuni_ndalem_mobile/play_02.png` ← https://play-lh.googleusercontent.com/BJ0_PhSENan4lAF7N99uU3rBokvF9wDDhyZ9JPednDXR3NEL2DJomZH2WrmaHyO4ZDuxcVy2W-7GSexP7_T5sAw=w1080
  - `screenshots/prahuni_ndalem_mobile/play_03.png` ← https://play-lh.googleusercontent.com/y1j9Ppe6mQcLgN0K06hFTAj8lYNP93WCYN4fc3nS3Nk4v_809HVmBgwgwWGO_eANau9TczRhtSOrng5BOHFChQ=w1080
  - `screenshots/prahuni_ndalem_mobile/play_04.png` ← https://play-lh.googleusercontent.com/xaQdt3KxeS1TlGjiYTF0KoBG7AuQ-ccAYV6A5mkIwQnJDpBoGQsLAKgEfqYOb3pLhczDXTiXZX-vvGoPvbMEkb4=w1080
- **Mandep** — listing [Google Play](https://play.google.com/store/apps/details?id=id.mandep.apps&hl=id) — isi: Beranda (absensi, modul); Detil Laporan Harian + foto; Detil Pembayaran (piutang, booking fee); Absensi
  - `screenshots/prahuni_mandep/play_01.png` ← https://play-lh.googleusercontent.com/V3q8gIBrQsIke7IiHAnZ-e4lsXZl4MPyAnjLvNBDN5Znq28Xmg3eWEEVZw5qWzb_XxlBh4N9Ffp6d2qOzpyvWA=w1080
  - `screenshots/prahuni_mandep/play_02.png` ← https://play-lh.googleusercontent.com/HdC3Dcmu8yIuTlJiQoOkS46Z6vKwEjnxVF_8jY4TNjsuk91a2UI3bJ-E-pAVYbLHt7a8Sa9X2r6tU7w6HQdKJlY=w1080
  - `screenshots/prahuni_mandep/play_03.png` ← https://play-lh.googleusercontent.com/spZlrfYuSj8YxFQKbkrcC-OQyfHgOK7FOwnZilvGVD7vgRwyGNBNCf2JNF7ORsYguqKH7eC139T_mQvmnYTb8w=w1080
  - `screenshots/prahuni_mandep/play_04.png` ← https://play-lh.googleusercontent.com/s9WkgWgnxbWvAOLMl4tnqkdoAiO2grWOBz03RUh3MV0INuZ4fMWKS7aLbCKGrG3w59h_r3pb6VxotY4_VVx870s=w1080
- **Porta Pro (ECes.Q)** — listing [Google Play](https://play.google.com/store/apps/details?id=com.mediasarana.portapro&hl=id) — isi: Dashboard status unit; Site Plan berwarna; Reserve Unit; Kartu Pembayaran + Kirim WA Tagihan
  - `screenshots/prahuni_porta_pro/play_02.png` ← https://play-lh.googleusercontent.com/Tt54mp2_oDMj4EAxb6fAPO3Wa_Ejy46Isd9rTItPxKiZDLNqsXZB6DhRmaiQH_bTUIByg-ZhLVlfF-Z5_P-QpQ=w1080
  - `screenshots/prahuni_porta_pro/play_03.png` ← https://play-lh.googleusercontent.com/53wLGRPbQ-wy7VeDPaEUSt28vG8TBnx8VEuYEDmYp2PAaqJ1ctaOAchvi3WzBWBVX8Ux8qooWrGoLoX49WoTfQ=w1080
  - `screenshots/prahuni_porta_pro/play_05.png` ← https://play-lh.googleusercontent.com/CxaHGPKPZUNl88bH8ypfLwn2svNOeyUQO3wb1jYxGW1SXwkpHWX_7HtGClLjRYK67N1noBQ5VB7CznfiN9lj958=w1080
  - `screenshots/prahuni_porta_pro/play_07.png` ← https://play-lh.googleusercontent.com/9hN4iDdsdS4h3qtqmNm2oAZNkTT-4ppYxS6_BKgxKQYa4Plv2p3yP4OoEWVpVK8OcAMTdsOiorV-u3Jzvrc3GQ=w1080
- **vCloudProperty+ Approvals** — listing [Google Play](https://play.google.com/store/apps/details?id=com.vcloud.vworkflow&hl=id) — isi: Antrian per modul; persetujuan Sales (Pembatalan/Pengalihan Hak/Reservasi); daftar dokumen; detail + Keputusan
  - `screenshots/prahuni_vcloudproperty_approvals/play_01.png` ← https://play-lh.googleusercontent.com/gaufqZz33_v42yb4ym9Ag8D3_SE1Gd9cJgCMBv16tw-td_yw6Fic6EfEVNkCwf0C0QnQ8Z1z1ZZEyolC8CzwMA=w1080
  - `screenshots/prahuni_vcloudproperty_approvals/play_02.png` ← https://play-lh.googleusercontent.com/BK4bJxJB8ToSrJEXvz-SokVEza5MVFnr_7FpMWDrnrBHg5OaDITr7CErGHqqhQ9cW6aBhkHIFlNPlA2moTzynQ=w1080
  - `screenshots/prahuni_vcloudproperty_approvals/play_03.png` ← https://play-lh.googleusercontent.com/bzqY03jWef5o9QIfzbu9NF2MLp08aML27TB6G928HTKXlZmQz0m0kWaCLJxu2Y3PdSTEsA-KQJVrashr2ds9lGY=w1080
  - `screenshots/prahuni_vcloudproperty_approvals/play_04.png` ← https://play-lh.googleusercontent.com/Dx-QJqnSpOT52pQFy-Vsj1uEZQxrSPu1O1OZLDKeEiCqW1UhtVRrNBl6zmdF6DPWldHOMOGDXxmcyOKDVpet=w1080
- **IDEAL – Pengajuan KPR Online** — listing [Google Play](https://play.google.com/store/apps/details?id=id.ideals.app&hl=id) — isi: Layanan; Aktivitas Pengajuan KPR; rekomendasi produk; ideal Checking (skor)
  - `screenshots/prahuni_ideal/play_01.png` ← https://play-lh.googleusercontent.com/TdFPS7GJs0emrv7ydEhgC3t8xKaglfX_dqPzwkNjmzWwLH17JHL1b2lK6oeIETCuv30HAYfEUuPCz_DNOdPdvQ=w1080
  - `screenshots/prahuni_ideal/play_02.png` ← https://play-lh.googleusercontent.com/eqfINc8o3nwcDyeRkEho9DOciVGv5WISeaFfD7_IOYaWsMlg_oWh03mcy-16llrbW2WE1PVOPwW_9U80MKZRFw=w1080
  - `screenshots/prahuni_ideal/play_04.png` ← https://play-lh.googleusercontent.com/QQKnLCPNsBzkZTPPZ8PpJLfwzpB40hVk9I4gt0MTEJTWFL2dMmBFmNi7X2wfgDl9vSqRtxKgddT4M29iRsf39w=w1080
  - `screenshots/prahuni_ideal/play_06.png` ← https://play-lh.googleusercontent.com/DqdHbT_Sz11goOUZyXzJuLQSdvVKZvqP-M_W8jPcI9dliAcXfIHkyYgeo3KLhcT16BDMA5N20K1USG6aqjqwBw=w1080
- **Simandor (web, tanpa listing store)** — Playwright, 1366×900, DPR 1
  - `screenshots/prahuni_simandor/web_01_landing_simandor.id.png` ← https://simandor.id/ (tinggi 6261 px)
  - `screenshots/prahuni_simandor/web_02_login_app.simandor.id.png` ← https://app.simandor.id/login (900 px)
- **Ringkas (web/PWA, tanpa aplikasi native)** — Playwright, 1366×900, DPR 1
  - `screenshots/prahuni_ringkas/web_01_landing_ringkas.co.id.png` ← https://ringkas.co.id/ (5642 px)
  - `screenshots/prahuni_ringkas/web_02_app.ringkas.co.id.png` ← https://app.ringkas.co.id/ (5208 px; banner "Tambah Ringkas di layar utama")

### Inferences
- Screenshot store adalah materi pemasaran (data demo, misalnya "Developer Batara", "Justin Pratama", "Project Demo"). Screenshot ini cukup untuk membuktikan keberadaan layar/alur, tetapi tidak membuktikan kualitas implementasi.

### Gaps
- Tidak ada screenshot untuk: balé developer web (HTTP 403), Perumnas Digital Property Platform/Sobat Bisnis (URL tidak ditemukan; perumnas.co.id 502), AutoKon (tanpa situs/aplikasi publik), SmartMandor (listing store tidak ditemukan).
- Screenshot iOS tidak diunduh terpisah karena listing Play sudah memuat layar yang sama atau lebih lengkap untuk semua aplikasi yang dipilih.
