# Aplikasi Pascahuni (Resident/Estate) Indonesia — Benchmark untuk Keluarga Ningrat & Estora

Tanggal riset: **2026-11-24**. Cakupan: hanya domain aplikasi (bukan profil perusahaan). Semua angka toko dibaca langsung pada 2026-11-24 dari:
- **Google Play** halaman listing publik `hl=id&gl=ID` (Playwright/Chromium). Data diambil dari dialog "Tentang aplikasi ini" dan dialog "Lihat semua ulasan", diurutkan **Terbaru**. Karena `hl=id`, hanya ulasan berbahasa Indonesia yang tampil, maksimal sekitar 100–140 per aplikasi.
- **App Store**, lewat iTunes Lookup API publik (`country=id`) dan halaman publik `apps.apple.com/id/app/id…?see-all=reviews`.

**Catatan metode penting:** endpoint RSS ulasan iOS (`https://itunes.apple.com/id/rss/customerreviews/id=<ID>/sortby=mostrecent/json`) hari ini mengembalikan feed **tanpa entri** untuk semua aplikasi. Ini termasuk aplikasi kontrol WhatsApp (id310633997), jadi kosongnya bukan karena aplikasinya — [RSS kontrol](https://itunes.apple.com/id/rss/customerreviews/id=310633997/sortby=mostrecent/json). Sebagai gantinya, ulasan iOS diambil dari halaman ulasan publik App Store. Halaman itu menampilkan sekitar 10 ulasan pilihan Apple, bukan urut terbaru. Tanggal di sana berformat dd/mm/yyyy; tanggal tanpa tahun (mis. "22 Sept") berarti dalam 12 bulan terakhir, kemungkinan 2026.

Tidak ada login, registrasi, APK, atau API privat/internal yang dipakai. Skrip disimpan terpisah di scratchpad sesi (`/tmp/claude-0/-home-user-dadada/4c43c2dd-1aa7-553c-9e9f-59508645de56/scratchpad/pascahuni/scripts/`).

Pemilihan white-label: **BumiHub, IPL-GO, dan Klasterpintar/iHome tidak ditemukan** di Google Play, App Store, maupun web (lihat Gaps P1). Yang dianalisis adalah tiga aplikasi dari daftar yang punya kehadiran nyata di toko (**RTPintar, eWarga, Klasterin**), ditambah **MAS IPL** (Kota Sutera) sebagai contoh IPL berbasis web untuk satu estate.

---

## P1. Fakta toko per aplikasi (ID paket, penerbit, install, rating, versi, tanggal)

### Takeaway
Aplikasi estate milik developer besar punya basis install besar (Ciputra Hub dan OneSmile 100rb+) tetapi rating rendah: Play 2,2–3,9 dan iOS 1,4–2,9. Rating tertinggi justru milik platform pihak ketiga atau bank: RTPintar 4,6 (50rb+) dan bale community BTN 4,5 (50rb+). Rating bale community sangat terdongkrak lonjakan ulasan saat peluncuran Januari 2023 (lihat P4). Keluarga Ningrat (1rb+, belum ada rating) setara skala dengan Rumahku Puri Delta Asri (500+) dan eWarga (1rb+). Klasterin baru dirilis (1+ unduhan).

### Cited Findings

**Tabel fakta toko (dibaca 2026-11-24)**

| Aplikasi | Play: paket / penerbit | Play: install · rating (jumlah) · versi · update · rilis | iOS: ID / seller | iOS: rating (jumlah) · versi · update · rilis |
|---|---|---|---|---|
| **Ciputra Hub** | `com.ciputra.ciputrahub` / Ciputra Group | 100rb+ · 2,9 (379) · 3.2.24 · 5 Nov 2026 · 29 Feb 2024 | id6478900292 / CIPUTRA DEVELOPMENT, PT TBK | 2,68 (72) · 3.2.24 · 2026-11-05 · 2024-03-07 |
| **OneSmile** (Sinar Mas Land, BSD) | `com.sinarmasland.onesmile` / OneSmile Digital (berisi iklan) | 100rb+ · 2,2 (315) · 5.261106.474 · 6 Nov 2026 · 27 Jan 2021 | id1551898065 / PT. APLIKASI KOTA PINTAR | 2,86 (149) · 474 · 2026-11-10 · 2021-02-24 |
| **Summarecon Home** | `com.summareconhome` / PT. Satu Summarecon Sukses (berisi iklan) | 10rb+ · 3,9 (122) · 2.3.7 · 6 Nov 2026 · 1 Sep 2021 | id1584050086 / PT. SATU SUMMARECON SUKSES (bundle `com.smra.nvb.smshome`) | 2,95 (58) · 2.3.7 · 2026-11-07 · 2021-09-28 |
| **LEAP** (Lippo) | `com.lippohomes.leap` / PT Lippo Karawaci Tbk | 10rb+ · 2,8 (61) · 1.0.32 · 14 Okt 2026 · 25 Agu 2024 | id6502327505 / LIPPO KARAWACI, PT TBK | 1,8 (30) · 1.0.53 · 2026-10-17 · 2024-09-18 |
| **Paramount Estate** | `com.paramountland.estate` / IT Paramount | 10rb+ · 2,7 (56) · 1.0.20 · 6 Okt 2026 · 1 Jun 2022 | id1624020170 / PT. PARAMOUNT ENTERPRISE INTERNATIONAL | 1,38 (32) · 1.0.20 · 2026-10-12 · 2022-06-05 |
| **JSmart 2.0** (Jababeka) | `com.jababeka.android` / Jababeka | 5rb+ · 4,7 (53) · 2.2.7 · 13 Jun 2026 · 31 Agu 2018 | id1438657494 / GRAHABUANA CIKARANG, PT (bundle `com.jababeka.Jababeka`) | 5,0 (2) · 1.1.3 · 2026-06-13 · 2018-10-17 |
| **Rumahku Puri Delta Asri** | `com.dwiwahanadeltamegah.rumahku` / Puri Delta Asri Dev | 500+ · belum ada rating · 1.0.0 · 12 Nov 2026 · 3 Nov 2025 | tidak ada di iOS | — |
| **bale community** (BTN, dulu "BTN Smart Residence") | `id.co.btn.smartresidence` / PT. Bank Tabungan Negara (Persero), Tbk | 50rb+ · 4,5 (651) · 2.4.0 · 22 Okt 2026 · 12 Sep 2021 | id1585400678 / BANK TABUNGAN NEGARA (bundle `com.btn.smart-residence`) | 4,93 (245) · 2.4.0 · 2026-10-23 · 2021-09-21 |
| **RTPintar** (white-label/SaaS) | `com.rt_pintar` / APLINDO | 50rb+ · 4,6 (503) · 2.9.0 · 13 Okt 2026 · 21 Agu 2019 | id1458259481 / "Buyung Bahari" (bundle `com.aplindo.rtpintar`) | 4,55 (31) · 2.8.2 · 2026-04-09 · 2019-04-06 |
| **eWarga** (SaaS RT/RW) | `id.citraikatsahabat.ewarga` / Citra Ikat Sahabat (pembelian dalam aplikasi) | 1rb+ · 5,0 (5) · 3.6.5 · 23 Nov 2026 · 11 Mar 2024 | id6820338441 / PT. Mitra Inovasi Jayantara (bundle `id.minova.ewarga`) | belum ada rating · 1.0 · 2026-11-23 · 2026-11-22 |
| **Klasterin** (SaaS estate) | `id.klasterin.app` / PT. BISA DAGANG INDONESIA | 1+ · belum ada rating · 1.0.0 · 29 Sep 2026 · 28 Sep 2026 | id6817015419 / PT. BISA DAGANG INDONESIA | 5,0 (1) · 1.0.0 · 2026-10-02 · 2026-10-02 |
| **MAS IPL** (Kota Sutera) | `com.ks.masipl` / rubik.tech | 1rb+ · 4,8 (5) · 1.2 · 29 Agu 2026 · 17 Des 2023 | tidak dicek/ditemukan | — |
| *Baseline:* **Keluarga Ningrat** | `com.trusmi.keluarganingrat` / Trusmi Group | 1rb+ · belum ada rating · 1.0.11 · 20 Nov 2026 · 25 Jun 2026 | id6752388007 "KeluargaNingrat" / **Anggi Supriatna** (akun individu) | belum ada rating · 2.1 · 2026-06-29 · 2025-11-23 |

**Sumber per baris (Play | iOS)**
- Ciputra Hub — [Play](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id6478900292), [Lookup](https://itunes.apple.com/lookup?id=6478900292&country=id)
- OneSmile — [Play](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1551898065), [Lookup](https://itunes.apple.com/lookup?id=1551898065&country=id)
- Summarecon Home — [Play](https://play.google.com/store/apps/details?id=com.summareconhome&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1584050086), [Lookup](https://itunes.apple.com/lookup?id=1584050086&country=id)
- LEAP — [Play](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id6502327505), [Lookup](https://itunes.apple.com/lookup?id=6502327505&country=id)
- Paramount Estate — [Play](https://play.google.com/store/apps/details?id=com.paramountland.estate&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1624020170), [Lookup](https://itunes.apple.com/lookup?id=1624020170&country=id)
- JSmart 2.0 — [Play](https://play.google.com/store/apps/details?id=com.jababeka.android&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1438657494), [Lookup](https://itunes.apple.com/lookup?id=1438657494&country=id)
- Rumahku Puri Delta Asri — [Play](https://play.google.com/store/apps/details?id=com.dwiwahanadeltamegah.rumahku&hl=id&gl=ID) | tidak ada di iOS ([iTunes search](https://itunes.apple.com/search?term=rumahku%20puri%20delta&country=id&entity=software))
- bale community — [Play](https://play.google.com/store/apps/details?id=id.co.btn.smartresidence&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1585400678), [Lookup](https://itunes.apple.com/lookup?id=1585400678&country=id)
- RTPintar — [Play](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id1458259481), [Lookup](https://itunes.apple.com/lookup?id=1458259481&country=id)
- eWarga — [Play](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id6820338441), [Lookup](https://itunes.apple.com/lookup?id=6820338441&country=id)
- Klasterin — [Play](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id6817015419), [Lookup](https://itunes.apple.com/lookup?id=6817015419&country=id)
- MAS IPL — [Play](https://play.google.com/store/apps/details?id=com.ks.masipl&hl=id&gl=ID)
- Keluarga Ningrat — [Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID) | [App Store](https://apps.apple.com/id/app/id6752388007), [Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id)

**Fakta tambahan**
- **Nama BTN.** Paket Android BTN masih `id.co.btn.smartresidence`, tetapi namanya kini "bale community". Pencarian Play "btn smart residence" langsung mengarah ke aplikasi ini — [Play search](https://play.google.com/store/search?q=btn%20smart%20residence&c=apps&hl=id&gl=ID). BTN mengumumkan aplikasi penghubung penghuni dan pengelola ini pada 2 Des 2021. Rencananya Android/iOS untuk penghuni dan **web untuk pengelola**, ditawarkan ke mitra developer dan debitur KPR/KPA, dengan peluncuran bersamaan HUT KPR BTN 10 Desember — [JPNN, 2 Des 2021](https://www.jpnn.com/news/manjakan-nasabah-btn-bakal-meluncurkan-aplikasi-baru).
- **Penerbit eWarga.** Deskripsi iOS (PT. Mitra Inovasi Jayantara, rilis 22 Nov 2026) identik kata per kata dengan deskripsi Play (Citra Ikat Sahabat) — [Lookup iOS](https://itunes.apple.com/lookup?id=6820338441&country=id); [Play](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID).
- **Penerbit RTPintar.** Di Play "APLINDO"; di iOS seller adalah individu "Buyung Bahari". Situs menyebut badan usahanya PT ARSITEK PERANGKAT LUNAK INDONESIA — [rtpintar.com](https://rtpintar.com).
- **Keluarga Ningrat di iOS** tercatat atas nama individu "Anggi Supriatna", v2.1, terakhir update 2026-06-29. Rilis iOS-nya (2025-11-23) lebih dulu dari Play (2026-06-25) — [Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id). Catatan riset sebelumnya menyatakan aplikasi ini tidak ditemukan di iOS. Penyebabnya, judul iOS ditulis tanpa spasi ("KeluargaNingrat"), sehingga pencarian "keluarga ningrat" gagal.

### Inferences
- Rating rendah aplikasi developer besar konsisten di Play dan iOS. Basis install besar terjadi karena pembayaran IPL/utilitas diwajibkan lewat aplikasi (lihat ulasan P4), bukan karena aplikasinya disukai.
- Seller iOS Keluarga Ningrat berupa akun individu, dengan versi iOS (2.1, Juni 2026) yang berbeda dari Android (1.0.11, Nov 2026). Ini mengisyaratkan rilis iOS dikelola terpisah atau tertinggal. Ada risiko tata kelola: akun toko tidak atas nama badan usaha. Hal yang sama terlihat pada RTPintar iOS ("Buyung Bahari").
- LEAP: versi Play (1.0.32) lebih rendah dari iOS (1.0.53). Kemungkinan rilis per platform tidak sinkron.

### Gaps
- **BumiHub, IPL-GO, Klasterpintar/iHome** tidak ditemukan di Play, dengan pencarian "bumihub", "bumi hub warga", "ipl-go", "IPL GO perumahan", "klaster pintar", "klasterpintar", "ihome klaster pintar", dan "iHome warga perumahan" — [Play search contoh](https://play.google.com/store/search?q=bumihub&c=apps&hl=id&gl=ID). Juga tidak ditemukan di iTunes Search maupun pencarian web. Kemungkinan namanya berbeda, hanya berupa web, atau tidak ada.
- Rilis pertama iOS OneSmile vs Play berbeda sekitar 1 bulan. Tanggal rilis Play adalah tanggal listing, belum tentu tanggal peluncuran ke warga.
- Unduhan iOS tidak dipublikasikan Apple, jadi hanya jumlah rating yang tersedia.

---

## P2. Fitur per aplikasi (dikelompokkan)

### Takeaway
Inti yang hampir universal adalah **tagihan IPL/utilitas + pembayaran VA**, **pengumuman/berita**, dan **pengajuan (izin/keluhan)**. Keamanan digital (gate/QR tamu/SOS) hanya ada di sebagian: Paramount, OneSmile, Klasterin, RTPintar, Keluarga Ningrat. Live CCTV jarang: RTPintar, Summarecon (menu), Keluarga Ningrat; OneSmile menghapusnya pada 2026. Marketplace/PPOB jarang. Hanya dua aplikasi yang menggabungkan informasi pembeli (angsuran/progres bangun) dengan pascahuni: **Rumahku Puri Delta Asri** dan sebagian **Ciputra Hub** (menu "Konstruksi"). Pola ini paling relevan untuk Estora.

### Cited Findings

**Ciputra Hub (Ciputra)**
- **Deskripsi resmi:** bayar tagihan IPL, listrik, dan air; kelola renovasi unit; reservasi fasilitas; lapor keluhan; info darurat; akses pengunjung; promo — [Play](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)
- **Screenshot resmi:**
  - Grid beranda: Unitku, **Konstruksi**, Fasilitas, Tagihan, **Kartu Tamu**, Layanan, Keluhan, Berita.
  - Banner "Sarankan teman untuk beli unit di Ciputra" (referral).
  - Layar "Bayar sekali untuk semua unit" lintas proyek, berlabel "Mendukung Multipayment".
  - "Telepon Darurat" (Satpam, Rumah Sakit, Polisi, Pemadam).
  - Sumber: [screenshot iOS 1–4](https://apps.apple.com/id/app/id6478900292) (file: `screenshots/pascahuni_ciputrahub/`)
- **Pembayaran:** ulasan menyebut VA BCA (8 Des 2025) dan "jangan cuma terpaut sama 2 bank itu aja" (25 Agu 2026) — [Play ulasan](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)

**OneSmile (Sinar Mas Land – BSD City)**
- **Deskripsi resmi:** penyedia dokumen dengan pengembang, wadah info antarwarga, rekomendasi tempat/acara, jadwal BSD Link — [Play](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID)
- **Screenshot resmi:** "Open Smart Gate", "Booking Club House", "Booking Sports Club", "City Guide" (jadwal BSD Link, KRL, Transjabodetabek), layar Masuk/Registrasi — [App Store](https://apps.apple.com/id/app/id1551898065)
- **Pembayaran IPL:** kolaborasi Blibli–OneSmile memungkinkan bayar IPL dan tagihan rutin langsung di aplikasi via **e-wallet, QRIS, dan virtual account**, dengan status real-time dan jadwal tagihan berulang — [JawaPos, 8 Nov 2025](https://www.jawapos.com/properti/2511070406/transformasi-gaya-hidup-digital-bayar-ipl-kini-bisa-dalam-satu-aplikasi)
- **CCTV jalan dihapus:** "fitur cctv sudah tidak ada" (12 Sep 2026); "sudah gak ada lagi yaa cctv-nya" (9 Sep 2026) — [Play ulasan](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID)
- **Market dan QR fasilitas:** "fitur market" ada; pengguna mengeluh tak ada tombol komplain (27 Feb 2026) — [Play](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID). QR wajib untuk berenang (23 May) — [App Store ulasan](https://apps.apple.com/id/app/id1551898065?see-all=reviews)

**Summarecon Home**
- **Deskripsi resmi:** pengajuan perizinan (tanpa ke Town Management); pembayaran tagihan multi-properti dalam satu kali bayar; info kawasan; Premium Stamps terintegrasi Friendship Card Summarecon Mall — [Play](https://play.google.com/store/apps/details?id=com.summareconhome&hl=id&gl=ID)
- **Screenshot resmi:**
  - Grid: Mall, **Emergency**, **Shuttle**, **CCTV**, Quiz.
  - "Buat Family Account", "Verifikasi", "+ Daftarkan Properti" (status APPROVED).
  - Bayar tagihan IPL, listrik, dan air (centang multi-unit).
  - Berita/Event/Promo.
  - Sumber: [App Store](https://apps.apple.com/id/app/id1584050086)

**LEAP (Lippo Karawaci)**
- **Deskripsi resmi:** izin renovasi; kelola dan bayar tagihan IPL; asisten "Tanya LIA" 24 jam; melayani Lippo Village, Lippo Cikarang, Tanjung Bunga Makassar, Park Serpong — [Play](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID)
- **Screenshot resmi:**
  - Beranda dengan **Kode Pelanggan**, Township, Billing.
  - Menu Pengajuan, Tagihan, Renovasi, Acara, Berita.
  - **Grafik Penggunaan Air** per unit (metering).
  - "Jelajahi Sekitar" (toko/jasa sekitar).
  - "Pengajuan Saya": Izin Renovasi, **Izin Muat Barang**, **Kartu Kendaraan**, dengan status Dalam Proses/Menunggu Pembayaran/Selesai.
  - Tagihan "dari listrik, internet hingga pajak bangunan" dan **Faktur Pajak**.
  - Sumber: [App Store](https://apps.apple.com/id/app/id6502327505)
- **Klaim garansi:** disebut pengguna: "Mengecek Pembayaran jatuh tempo IPL, Air, PerIjinan Kecil, Klaim Garansi" (13 Okt 2026) — [Play ulasan](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID)

**Paramount Estate**
- **Deskripsi resmi:** lihat tagihan bulanan dan riwayat bayar; **Tombol Panik/SOS**; berita/pengumuman; FAQ — [Play](https://play.google.com/store/apps/details?id=com.paramountland.estate&hl=id&gl=ID)
- **Rilis terbaru:** "Add Feature Perizinan / Bug Fix minor bugs Visual View when reject Registration" — [Play](https://play.google.com/store/apps/details?id=com.paramountland.estate&hl=id&gl=ID)
- **Screenshot resmi:** login nomor HP → OTP; beranda "Homes" dengan jumlah Occupant; tab Home/**QR**/Help/Account — [App Store](https://apps.apple.com/id/app/id1624020170)
- **QR gate:** QR dipakai untuk gerbang warga dan tamu: "QR Gate … Buat keluar masuk rumah sendiri seribet iniiiii, mending pake kartu" (23/02/2025); "QR for guest" (19/12/2024) — [App Store ulasan](https://apps.apple.com/id/app/id1624020170?see-all=reviews)
- **Pembayaran:** IPKL **hanya via Mandiri**: "PAKE TOKPED GA BISA … HARUS BUKA REKENING MANDIRI DULU" (13 Jun, tahun berjalan) — [App Store ulasan](https://apps.apple.com/id/app/id1624020170?see-all=reviews)

**JSmart 2.0 (Jababeka)**
- **Deskripsi resmi:** info produk (rumah, ruko, apartemen), promo tenant, **simulasi harga dan cara bayar**, **billing tagihan air**, city events — [Play](https://play.google.com/store/apps/details?id=com.jababeka.android&hl=id&gl=ID)
- **Screenshot resmi:** katalog (site plan, floor plan, brosur, pricelist), promosi, "Lihat update perkembangan residence" (foto progres per tanggal), simulasi pinjaman/KPR — [App Store](https://apps.apple.com/id/app/id1438657494)
- Lebih condong ke aplikasi pemasaran/pembeli; fitur pascahuninya hanya tagihan air.

**Rumahku Puri Delta Asri (developer subsidi, Kendal)**
- **Deskripsi resmi:** pengumuman dan info proses pembelian rumah; tagihan dan status iuran bulanan; surat pengajuan perbaikan — [Play](https://play.google.com/store/apps/details?id=com.dwiwahanadeltamegah.rumahku&hl=id&gl=ID)
- **Screenshot resmi:**
  - "Monitor angsuran, progres pembangunan, serta tagihan IPL Anda ketika menjadi warga".
  - Menu **Angsuran, Progress Bangun, Komplain, Air**.
  - Mode "Pengunjung" (belum login) dengan promo proyek ("3jt-an Bisa Punya Rumah") dan pengumuman NUP proyek baru.
  - Sumber: [Play](https://play.google.com/store/apps/details?id=com.dwiwahanadeltamegah.rumahku&hl=id&gl=ID)

**bale community (BTN)**
- **Deskripsi resmi:**
  - Pembayaran tagihan IPL, parkir, dan fasilitas lain via **Nomor Virtual Account** per tagihan.
  - Berita/Informasi.
  - Keluhan pelanggan/komunitas untuk ditindaklanjuti pengelola.
  - Sumber: [Play](https://play.google.com/store/apps/details?id=id.co.btn.smartresidence&hl=id&gl=ID)
- **Screenshot resmi:**
  - "Ajukan Persetujuan" untuk bergabung ke komunitas, dengan daftar unit dan "Lihat Penyewa".
  - Menu Informasi, Tagihan, Pengaduan, **Parkir**.
  - Invoice berisi No. VA, **"Biaya Layanan Rp 2.000"**, riwayat pembayaran bertahap dengan "Sisa Bayar", dan status Belum Dibayar/Sudah Dibayar/Expired.
  - Sumber: [App Store](https://apps.apple.com/id/app/id1585400678)

**RTPintar (SaaS untuk RT/RW/cluster/perumahan)**
- **Deskripsi resmi:**
  - Tagihan rutin dan insidentil.
  - Broadcast penagihan lewat **chatbot WhatsApp**.
  - Tiga mode pembayaran: **Validasi Otomatis (Virtual Account, QRIS, e-Wallet)**, semi-otomatis (transfer ke rekening pengurus + bukti), dan manual/tunai.
  - Notifikasi WA, surat-menyurat, polling, laporan warga, pencatatan kas, **CCTV**, pengelolaan real estate.
  - Klaim ">100.000" unduhan iOS+Android.
  - Sumber: [Play](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID)
- **iOS:** layanan mandiri: tagihan, **Tombol Panik dan Lapor**, berbagi info, surat (RT), polling, kas — [App Store](https://apps.apple.com/id/app/id1458259481)
- **Screenshot resmi:** login nomor HP → **OTP via WhatsApp**; grid Tagihan, Bagikan Info, Riwayat, Buat Surat, Lapor, CCTV; tombol **PANIC** melayang; tab Kas dan Inbox — [App Store](https://apps.apple.com/id/app/id1458259481)
- **Harga per bulan (langganan pengelola):**
  - Rp120.000 (≤100 unit), Rp170.000 (200), Rp245.000 (400), Rp300.000 (600), Rp375.000 (800), Rp450.000 (1.000), Rp600.000 (1.500), Rp900.000 (2.500).
  - Paket tahunan = 10× bulanan.
  - Sumber: [rtpintar.com/harga](https://rtpintar.com/harga)
- **Klaim situs:** chatbot WA billing dengan "success rate diatas 80%" — [rtpintar.com](https://rtpintar.com)
- **Biaya transaksi:** seorang pengguna menyebut biaya tambahan "@Rp. 5.000 setiap warga bayar iuran dg metode … validasi otomatis" (19 Mei 2024) — [Play ulasan](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID). Angka ini tidak tercantum di halaman harga.

**eWarga (SaaS RT/RW)**
- **Deskripsi resmi:** registrasi dengan Gmail; pengelolaan anggota (status kepemilikan hunian, keluarga, kontak); broadcast message; UMKM; pemetaan wilayah; galeri; agenda — [Play](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID)
- **Rilis v3:** "Menu Iuran Baru: Catat dan pantau kas iuran warga" — [Play](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID)
- **Screenshot resmi:** "Masuk dengan Google"; "Gabung Instansi" **dengan fitur scan QR** atau **kode unik** dari pengurus; "Subscribe Halaman RT RW untuk akses lebih tanpa batas"; indeks berita — [Play](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID)
- Tidak ditemukan payment gateway; iuran hanya dicatat.

**Klasterin (SaaS estate, PT Bisa Dagang Indonesia)**
- **Deskripsi resmi**
  - Warga: lihat/bayar IPL, lapor masalah dan pantau progres, **undang tamu dengan QR sekali pakai**, panic button, reservasi fasilitas, pengumuman, iklan antarwarga.
  - Satpam: validasi tamu scan QR, terima panic, **catat patroli**.
  - Pengelola: kelola IPL, verifikasi pembayaran, laporan keuangan per cluster, **tiket/work order dengan SLA**, pengumuman.
  - Sumber: [Play](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID)
- **Rilis perdana:** "Bayar IPL lewat QRIS dan virtual account" — [Play](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID)
- **Screenshot resmi:**
  - Detail tiket: nomor tiket, kategori, prioritas, "Ditangani oleh", **"Perkiraan selesai"**, lampiran foto, **Linimasa** status.
  - Undangan tamu: QR + kode pendek, dengan catatan "QR hanya memuat token akses. Data pribadi tamu tidak disimpan di dalam QR".
  - Detail tagihan IPL dengan **VA BCA / VA Mandiri**.
  - "Booking mendatang" (kolam renang).
  - Sumber: [App Store](https://apps.apple.com/id/app/id6817015419)
- **Harga dan pembayaran:**
  - Promo **Rp180.000 per 100 unit/bulan** (normal Rp450.000), berlaku selamanya untuk kawasan yang mendaftar sebelum 31 Des 2026.
  - Coba gratis 1 bulan.
  - "Pembayaran tagihan via VA/QRIS".
  - Sumber: [klasterin.id](https://klasterin.id)

**MAS IPL (Kota Sutera)**
- Pembayaran IPL digital untuk warga Kota Sutera dengan **Payment Gateway**. Bisa juga via web `ipl.kotasutera.web.id/auth_warga` — [Play](https://play.google.com/store/apps/details?id=com.ks.masipl&hl=id&gl=ID)
- **Screenshot:** aplikasi berupa pembungkus web (bar alamat ipl.kotasutera.web.id); daftar dengan Nama/No Tlp/Email/Password lalu "Masukkan Data Unit"; Tagihan Belum/Sudah Dibayar — [Play](https://play.google.com/store/apps/details?id=com.ks.masipl&hl=id&gl=ID)

**Keluarga Ningrat (baseline)**
- **Deskripsi resmi:** Marketplace, Ningrat Pay, IPL, Panic Button, **Smart Main Gate**, **Live CCTV**, Service Place, Hobby Community, Event Warga, **Security On Duty**, **Complaint Management** — [Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)
- **Dari screenshot (catatan sebelumnya):**
  - IPL via VA BRI; PPOB/token PLN via VA Permata.
  - CCTV EZVIZ.
  - Gate dengan validasi geofence GPS.
  - Riwayat akses gate.
  - Sumber: lihat `research_notes/Riset Rumah Ningrat dan aplikasinya/cek_aplikasi.md` dan [App Store](https://apps.apple.com/id/app/id6752388007).

### Inferences
- Dari sisi kelengkapan menu, Keluarga Ningrat termasuk yang terluas (keamanan + commerce + komunitas). Ia **tidak** menampilkan izin renovasi, booking fasilitas, pass tamu/QR tamu, metering utilitas, atau info pembeli (angsuran/progres) di dalam aplikasi. Untuk developer, keempat fitur pertama adalah pembeda yang paling sering ada di aplikasi developer besar.
- Klasterin (baru, Sep/Okt 2026) secara desain paling dekat dengan "modul pascahuni ideal": ada tiket dengan SLA dan linimasa, QR tamu yang menjaga privasi, VA multi-bank + QRIS, dan peran satpam/pengelola. Harganya juga sangat murah. Ia belum terbukti di pasar (1+ unduhan).
- Hanya Rumahku Puri Delta Asri yang secara eksplisit menyambung perjalanan pembeli ke warga dalam satu akun/aplikasi. Ciputra Hub sebagian (menu Konstruksi dan referral). Ini relevan langsung bagi Estora yang sudah punya portal pembeli.

### Gaps
- Metode bayar persis Ciputra Hub (bank mana saja selain BCA), Summarecon Home, dan LEAP tidak disebut publik.
- Detail menu Keluarga Ningrat yang terkunci login (Complaint Management, Service Place) tidak bisa diverifikasi tanpa akun. Tidak dicoba.
- Halaman produk BTN Smart Residence di btn.co.id tidak bisa dirender (kosong via fetch/Playwright). Fitur pengelola versi web dan model biaya hanya diketahui dari deskripsi toko, screenshot ("Biaya Layanan Rp2.000"), dan berita 2021.

---

## P3. Model akses/onboarding penghuni

### Takeaway
Ada empat pola:
1. **Daftar mandiri lalu klaim/daftarkan unit dengan verifikasi**: Ciputra Hub, Summarecon (plus foto KTP), OneSmile (NIK + aktivasi), MAS IPL, Keluarga Ningrat.
2. **Login dengan kode pelanggan/ID yang diterbitkan pengelola**: LEAP (Kode Pelanggan + PIN).
3. **Nomor HP + OTP lalu persetujuan pengelola**: Paramount (registrasi bisa ditolak), bale community (barcode/referral komunitas + "Ajukan Persetujuan").
4. **Akun dibuat/diundang pengelola**: Klasterin; RTPintar (data warga diimpor, login OTP WhatsApp); eWarga (Google + QR/kode unik instansi).

Pola 1 dan 3 adalah sumber keluhan terbesar (gagal OTP, verifikasi KTP gagal, proyek tidak terdaftar, ditolak berulang).

### Cited Findings
- **Ciputra Hub**
  - Layar Unit memisahkan "Diklaim" dan "Menunggu", dengan teks "Tidak ada unit — Masuk untuk melakukan klaim unit" — [App Store screenshot](https://apps.apple.com/id/app/id6478900292)
  - Keluhan proyek tidak terdaftar dan akun ganda: "mau buat akun lagi email dan nmr tlp sdh di pake.. Tlg utk proyek citragarden Lampung di tambahkan" (6 Okt 2026) — [Play](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)
  - "daftar pakai nomor hp tapi verifikasi otp dikirim lewat email" (1 Jul 2026) — [Play](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)
- **Summarecon Home**
  - Registrasi no HP + email, verifikasi KTP, "Daftarkan Properti" (APPROVED), Family Account — [App Store screenshot](https://apps.apple.com/id/app/id1584050086)
  - Developer menjawab "proses pendaftaran dengan verifikasi menggunakan KTP bertujuan untuk keamanan Akun Anda" (balasan untuk ulasan 15 Nov 2024) — [Play](https://play.google.com/store/apps/details?id=com.summareconhome&hl=id&gl=ID)
  - "ktp gagal dikenali mulu" (31 Jan) — [App Store ulasan](https://apps.apple.com/id/app/id1584050086?see-all=reviews)
- **OneSmile**
  - Masuk/Registrasi — [App Store screenshot](https://apps.apple.com/id/app/id1551898065)
  - Validasi NIK: "Masukin NIK gaboleh 5 angka kembar" (30 Mei 2025) — [Play](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID)
  - Aktivasi via WhatsApp: "Sudah 2 hari layanan OneSmile di WhatsApp saya chat untuk mengaktifkan akun tidak ada responsnya" (28 Jul) — [App Store ulasan](https://apps.apple.com/id/app/id1551898065?see-all=reviews)
- **LEAP**
  - Kode Pelanggan sebagai identitas, "Pilih Kode Pelanggan" untuk multi-unit — [App Store screenshot](https://apps.apple.com/id/app/id6502327505)
  - "tertulis tidak ada kode pelanggan, sedangkan kode pelanggannya gatau masukin dimana" (24/10/2025) — [App Store ulasan](https://apps.apple.com/id/app/id6502327505?see-all=reviews)
  - "tidak tau harus menggunakan akun yg mana" (22 Okt 2026) — [Play](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID)
- **Paramount Estate**
  - Nomor HP → OTP — [App Store screenshot](https://apps.apple.com/id/app/id1624020170)
  - Registrasi bisa ditolak ("reject Registration" di catatan rilis); ulasan "rejecttt teroooss" (3 Apr 2026) — [Play](https://play.google.com/store/apps/details?id=com.paramountland.estate&hl=id&gl=ID)
  - Batas OTP: "You have requested Otp too many times for today" (08/07/2023) — [App Store ulasan](https://apps.apple.com/id/app/id1624020170?see-all=reviews)
- **bale community**
  - "Kirain terhubung otomatis dengan pinjaman rumah yg ada sekarang rupanya harus scan barcode atw referal yg entah dimana dicari" (23 Jun 2023) — [Play](https://play.google.com/store/apps/details?id=id.co.btn.smartresidence&hl=id&gl=ID)
  - Layar "Ajukan Persetujuan" — [App Store screenshot](https://apps.apple.com/id/app/id1585400678)
- **Klasterin:** "Akun Klasterin dibuat oleh pengelola kawasan Anda" — [Play](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID)
- **RTPintar:** login nomor HP terdaftar + OTP via WhatsApp — [App Store screenshot](https://apps.apple.com/id/app/id1458259481). Situs menyebut undang/impor data warga saat setup — [rtpintar.com](https://rtpintar.com)
- **eWarga:** Masuk dengan Google; gabung instansi via QR atau kode unik dari pengurus — [Play screenshot](https://play.google.com/store/apps/details?id=id.citraikatsahabat.ewarga&hl=id&gl=ID)
- **MAS IPL:** daftar Nama/No Tlp/Email/Password lalu "Masukkan Data Unit" — [Play screenshot](https://play.google.com/store/apps/details?id=com.ks.masipl&hl=id&gl=ID)
- **Keluarga Ningrat:** tombol "Buat Akun"/"Masuk" (daftar mandiri) — catatan `cek_aplikasi.md`; [App Store](https://apps.apple.com/id/app/id6752388007)

### Inferences
- Gesekan onboarding terbesar muncul ketika warga harus **membuktikan ulang** kepemilikan yang sebenarnya sudah diketahui developer: foto KTP, klaim unit, kode pelanggan yang tidak diketahui, referral/barcode yang tidak dijelaskan.
- Estora sudah punya akun pembeli terverifikasi lewat WhatsApp OTP yang terikat ke unit. Karena itu Estora bisa melewati seluruh langkah ini: saat serah terima, akun pembeli otomatis menjadi akun warga untuk unit tersebut (model "pre-provisioned", seperti Klasterin/RTPintar, tetapi tanpa impor manual). Ini keunggulan struktural yang tidak dimiliki Ciputra Hub, Summarecon, maupun Keluarga Ningrat (daftar mandiri).
- OTP via WhatsApp (RTPintar, Estora) tampak lebih andal daripada SMS/email OTP, yang sering dikeluhkan di bale, OneSmile, Ciputra, dan Paramount. Ini inferensi dari pola keluhan, bukan data uji.

### Gaps
- Tidak diketahui apakah Keluarga Ningrat memvalidasi "Buat Akun" ke data unit atau perlu persetujuan admin. Alurnya terkunci di balik registrasi dan tidak dicoba.
- Rasio penolakan registrasi atau waktu aktivasi di aplikasi mana pun tidak dipublikasikan.

---

## P4. Keluhan dan pujian pengguna (sampel ulasan terbaru)

### Takeaway
Keluhan dominan di aplikasi developer, berurutan dari yang paling sering:
1. **Pembayaran IPL gagal/macet**, termasuk status tidak ter-update setelah saldo terpotong dan lambat di awal bulan.
2. **Login/registrasi/OTP**.
3. **Pilihan bank/metode bayar terbatas**: Paramount hanya Mandiri; Ciputra hanya 2 bank.
4. **Modul komplain tidak bisa dipakai atau ditutup sepihak**.
5. **CS tidak responsif**.
6. **Pemaksaan digital tanpa alternatif**: QR gate menggantikan kartu, QR untuk berenang.

Pujian muncul saat pembayaran dan pelaporan berjalan lancar dan CS cepat tanggap (RTPintar). Tren rating Ciputra Hub dan OneSmile memburuk tajam pada 2025–2026.

### Cited Findings

**Statistik sampel ulasan Play (bahasa Indonesia, urut Terbaru, diambil 2026-11-24)** — sumber: halaman Play masing-masing (tautan di P1)

| Aplikasi | n ulasan (rentang tanggal) | Rata-rata bintang per tahun dalam sampel |
|---|---|---|
| Ciputra Hub | 100 (18 Apr 2024 – 6 Okt 2026) | 2024: **4,17** (n=42) → 2025: **2,91** (n=32) → 2026: **1,77** (n=26) |
| OneSmile | 76 (3 Feb 2021 – 19 Nov 2026) | 2023: 4,79 (n=19) → 2024: 2,50 (n=6) → 2025: **1,29** (n=17) → 2026: 2,11 (n=19) |
| bale community | 140 (14 Jan 2023 – 9 Nov 2026) | **119 dari 140 ulasan bertanggal Januari 2023** (rata-rata 2023: 4,91); 2025: **1,00** (n=5); 2026: 2,25 (n=4) |
| RTPintar | 140 (9 Nov 2020 – 3 Okt 2026) | 2024: 4,60 (n=20); 2025: 5,00 (n=9); 2026: 5,00 (n=7); lonjakan 22 ulasan pada Jan 2021 |
| Summarecon Home | 15 (Okt 2021 – Nov 2025) | 5★×7, 1★×5 |
| LEAP | 8 (Mei 2025 – Okt 2026) | 1★×5, 5★×3 |
| Paramount Estate | 7 (Jun 2023 – Apr 2026) | sebagian besar 5★ singkat; ulasan iOS jauh lebih negatif (1,38) |
| JSmart 2.0 | 14 (Okt 2018 – Okt 2022) | 12× 5★, tidak ada ulasan sejak 2022 |
| Rumahku PDA, Klasterin, eWarga, Keluarga Ningrat | 0 ulasan tampil | — |

**Tema per aplikasi (kutipan pendek dan tanggal)**
- **Ciputra Hub** — [Play](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id6478900292?see-all=reviews)
  - Pembayaran dan beban awal bulan:
    - "setiap awal bulan selalu lama loding" (31 Agu 2026, 2★)
    - "sudah bayar tapi statusnya masih belum bayar … mau komplain jadi ga bisa" (5 Agu 2026, 1★)
    - "saldo sudah terpotong tetapi di aplikasi tidak terupdate" (3 Des 2025, 1★)
  - Update paksa: "Setelah dipaksa update bulan agustus 2026 ini kok malah jadi loading terus" (5 Agu 2026, 1★)
  - Metode bayar: "bikin kode bayarnya tuh universal … jangan cuma terpaut sama 2 bank itu aja" (25 Agu 2026, 2★)
  - Komplain:
    - "pelanggan tidak bisa memberikan feedback dan pihak Citra bisa mengclose padahal kerjaan belum beres" (25 Feb 2025, 1★)
    - iOS: "Mudah untuk bayar, susah untuk complain" (14/01/2025)
    - iOS: "Gabisa submit komplain, stuck loading" (10 Aug)
  - Tagihan salah/denda: "Tagihan air tidak keluar, sudah dapat teguran dan kena denda" (iOS 03/09/2024)
  - Pujian: "Untuk izin renovasi, pembayaran tagihan IPL serta pemesanan fasilitas seperti kolam renang dan gym jadi lebih mudah" (3 Jul 2024, 5★)
  - Developer membalas hampir semua ulasan dengan templat yang sama yang mengarahkan ke email `customer.care@ciputrahub.com`.
- **OneSmile** — [Play](https://play.google.com/store/apps/details?id=com.sinarmasland.onesmile&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id1551898065?see-all=reviews)
  - Keluhan dominan ada pada fitur kota (jadwal/pelacakan BSD Link): "Masih banyak rute BSDLINK yang tidak bisa di tracking … sangat berat dan lambat" (10 Okt 2026, 1★)
  - Fitur dihapus: "fitur cctv sudah tidak ada" (12 Sep 2026)
  - OTP: "kode otp nya ga masuk2" (12 Nov 2025)
  - Booking: "lapangan tennis masih kosong, tapi tidak bisa dibook" (iOS, 7 Sept)
  - Marketplace tanpa jalur komplain (27 Feb 2026)
  - Pujian iOS: "Membantu banget appnya, karena ada fitur live camnya, banyak misi berhadiah dan info event BSD" (26 May)
- **Summarecon Home** — [Play](https://play.google.com/store/apps/details?id=com.summareconhome&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id1584050086?see-all=reviews)
  - Login berulang/freeze saat registrasi (iOS 13/03/2025, 26/01/2025, 07/06/2024)
  - KTP gagal dikenali (31 Jan)
  - Proyek belum terdaftar: "Summarecon bogor belum ada dipilihan aplikasinya" (7 Okt 2023)
  - Minta metode bayar diperbanyak (16 Sep 2024, 4★)
  - Saran pengguna: "Sudah saatnya bikin SUPER APPS kaya developer BSD & Bintaro Jaya" (iOS 23/12/2024)
- **LEAP** — [Play](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id6502327505?see-all=reviews)
  - "tiap kali mau bayar pasti error, harus dicoba berulang bbrp hari baru bisa" (iOS 28 Oct)
  - "sesudah update app ga bisa dibuka sama sekali" (20 Okt 2026)
  - Push notifikasi berisi tag HTML: "Testing notif di envi prod?" (iOS 01/12/2025)
  - Pujian: cek jatuh tempo IPL, air, izin, klaim garansi (13 Okt 2026, 5★)
- **Paramount Estate** — [App Store](https://apps.apple.com/id/app/id1624020170?see-all=reviews)
  - Monopoli bank: "HARUS BUKA REKENING MANDIRI DULU … SAYA PAKE CIPUTRA HUB JAUH LEBIH BAIK" (13 Jun)
  - QR gate menggantikan kartu dianggap merepotkan (23/02/2025, 06/12/2024, 30/11/2024)
  - Inbox duplikat tak bisa dihapus (23/10/2025)
- **bale community (BTN)** — [Play](https://play.google.com/store/apps/details?id=id.co.btn.smartresidence&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id1585400678?see-all=reviews)
  - Ulasan pasca-peluncuran didominasi masalah akses dan VA:
    - "kode VA ny kenapa nga bisa di pake" (1 Jun 2026, 2★)
    - "udah coba selama 1 minggu mendaftar tetap gak bisa masuk" (19 Mei 2026, 1★)
    - "minta kode otp nya sampai saat ini gak dikirim2" (11 Sep 2025, 1★)
  - Pengaduan tak dijawab: "Kirim ke Pengaduan dari tgl 13 Juni 2023 sampe … 8 Sept 2023, kagak di bales" (8 Sep 2023)
  - iOS: "Aplikasi sangat lambat" (10/09/2025); "tidak kompetibel dengan iphone 15" (05/05/2024)
  - Balasan developer memakai templat "bale by BTN" (aplikasi bank), bukan konteks komunitas.
- **RTPintar** — [Play](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id1458259481?see-all=reviews)
  - Pujian konsisten pada CS dan transparansi:
    - "bantu sat set untuk bayar iuran, mempermudah juga untuk transparansi laporan keuangannya, di tambah customer support yang bantu" (3 Okt 2026, 5★)
    - "CS nya sangat membantu" (iOS 11 Mar)
    - "laporan kas cluster bisa rapi" (iOS 10/02/2021)
  - Keluhan biaya:
    - "Kemahalan untuk warga kami" (5 Nov 2025)
    - biaya Rp5.000 per transaksi otomatis "sangat berat" (19 Mei 2024)
  - Kebingungan model berlangganan (2021)
  - Setting CCTV sulit (11 Feb 2024, 3★)
- **JSmart 2.0** — [Play](https://play.google.com/store/apps/details?id=com.jababeka.android&hl=id&gl=ID): ulasan positif singkat, terakhir Okt 2022. iOS: "Sangat membantu untuk lihat tagihan air" (17/06/2020) — [App Store](https://apps.apple.com/id/app/id1438657494?see-all=reviews)

### Inferences
- **Rating 4,5–4,9 bale community kemungkinan besar terdongkrak kampanye peluncuran.** 119 dari 140 ulasan Indonesia di Play dan banyak ulasan 5★ iOS bertanggal akhir Januari 2023, dengan teks generik ("Top", "Mantap", "BTN ❤️"). Ulasan sesudah 2024 mayoritas 1–2★. Rating agregatnya tidak mencerminkan pengalaman terkini.
- **Ciputra Hub memburuk seiring wajibnya pembayaran via aplikasi.** Sampel turun dari 4,17 (2024) ke 1,77 (2026), dengan pola keluhan "awal bulan" dan "sudah bayar tapi belum lunas". Ini menunjukkan masalah kapasitas puncak dan rekonsiliasi pembayaran, bukan kekurangan fitur.
- Penilaian warga ditentukan oleh **keandalan beberapa alur inti** (bayar → lunas tercatat; lapor → ditindaklanjuti; masuk → tidak gagal OTP), bukan jumlah fitur.
- Paramount Estate (iOS 1,38) adalah contoh bahwa memaksakan kanal tunggal (satu bank, QR gate tanpa kartu) langsung menghasilkan ulasan 1★.

### Gaps
- Ulasan berbahasa Inggris dan bahasa lain di Play tidak ikut (filter `hl=id`), jadi sampel bisa bias.
- Halaman ulasan iOS hanya menampilkan sekitar 10 ulasan pilihan Apple. RSS kosong, jadi tidak ada sampel "terbaru" iOS yang lengkap.
- Belum ada ulasan publik untuk Keluarga Ningrat, Rumahku PDA, Klasterin, maupun eWarga. Kepuasan pengguna aplikasi kecil ini belum bisa dinilai.

---

## P5. Matriks fitur dan faktor pendorong rating

### Takeaway
Tidak ada korelasi positif antara jumlah fitur dan rating. Aplikasi dengan fitur terbanyak (OneSmile, Ciputra Hub) berating 2,2–2,9. Aplikasi sempit tetapi andal dengan CS responsif (RTPintar) berating 4,6. Rating baik dipengaruhi **bayar lancar dengan banyak metode, status lunas instan, CS/tiket yang ditanggapi, dan login mudah**. Rating buruk dipengaruhi **pembayaran gagal/tidak sinkron, kanal bayar tunggal, OTP/verifikasi gagal, update yang merusak, dan komplain yang ditutup tanpa penyelesaian**.

### Cited Findings

**Matriks fitur** (✅ terverifikasi di listing/screenshot/pers; ◐ parsial/terbatas/dari ulasan; — tidak ditemukan di materi publik). Sumber tiap sel ada di P2/P3.

| Aplikasi | IPL & metode bayar | Utilitas/meter | Keamanan (CCTV/gate/tamu/SOS) | Komplain/tiket | Komunitas (info/event/forum) | Marketplace/PPOB/promo | Izin renovasi | Booking fasilitas | Info pembeli/dokumen | Onboarding |
|---|---|---|---|---|---|---|---|---|---|---|
| **Keluarga Ningrat** | ✅ VA (BRI terlihat) | ◐ token PLN/PDAM via PPOB | ✅ CCTV EZVIZ, gate geofence, SOS, satpam bertugas; tamu — | ✅ (detail terkunci) | ✅ event, hobi | ✅ marketplace, service, PPOB | — | — | — (di portal web terpisah) | daftar mandiri |
| Ciputra Hub | ✅ IPL+listrik+air, multi-unit, VA "multipayment" (◐ 2 bank) | ✅ tagihan listrik/air | ◐ Kartu Tamu, telepon darurat | ◐ ada, sering gagal/ditutup sepihak | ✅ berita | ✅ promo, referral | ✅ | ✅ | ◐ menu Konstruksi | daftar + klaim unit |
| OneSmile | ✅ via Blibli: VA, QRIS, e-wallet | ✅ tagihan air | ◐ Smart Gate; CCTV jalan dihapus 2026 | ◐ hotline/WA | ✅ forum, event, city guide, BSD Link | ◐ market, misi berhadiah | — | ✅ club house, sport | ✅ dokumen dengan pengembang | daftar + NIK + aktivasi |
| Summarecon Home | ✅ multi-properti 1× bayar (◐ metode terbatas) | ✅ listrik/air | ◐ menu Emergency & CCTV | ◐ tombol bantuan/email | ✅ berita/event/promo | ✅ loyalti stamp mall | ✅ perizinan | — | ◐ progres township | HP + KTP + daftarkan properti |
| LEAP | ✅ IPL, listrik, internet, PBB, faktur pajak | ✅ grafik pemakaian air | — | ✅ pengajuan berstatus | ✅ acara/berita | ◐ "jelajahi sekitar" | ✅ + muat barang, kartu kendaraan | — | ◐ klaim garansi | kode pelanggan + PIN |
| Paramount Estate | ✅ tagihan + riwayat (◐ hanya Mandiri) | — | ✅ SOS, QR gate warga & tamu | ◐ menu Help | ✅ berita, FAQ | ◐ banner promo | ✅ perizinan (baru) | — | — | HP + OTP + approval |
| JSmart 2.0 | — | ✅ tagihan air | — | — | ✅ city events | ✅ promo tenant | — | — | ✅ katalog, simulasi harga, progres | terbuka |
| Rumahku PDA | ✅ tagihan & status iuran | ✅ menu Air | — | ✅ komplain, surat perbaikan | ✅ pengumuman, video | ◐ promo (mode pengunjung) | — | — | ✅ **angsuran, progres bangun** | mode pengunjung + login |
| bale community | ✅ IPL/parkir via VA, biaya layanan Rp2.000, bayar sebagian | ◐ item tagihan air | — | ✅ pengaduan | ✅ berita/informasi | — | — | — | ◐ daftar unit/penyewa | daftar + barcode/referral + persetujuan |
| RTPintar | ✅ VA, QRIS, e-wallet otomatis + transfer + tunai; chatbot WA | — | ✅ panic, CCTV | ✅ lapor | ✅ info, polling, surat, kas | — | — | — | — | HP + OTP WA (diimpor pengurus) |
| eWarga | ◐ catat kas iuran (tanpa gateway) | — | — | — | ✅ broadcast, agenda, galeri, peta | ◐ direktori UMKM | — | — | — | Google + QR/kode instansi |
| Klasterin | ✅ VA BCA/Mandiri + QRIS | — | ✅ QR tamu sekali pakai, panic, patroli | ✅ tiket + linimasa + SLA | ✅ pengumuman, iklan antarwarga | ◐ iklan antarwarga | — | ✅ | — | akun dibuat pengelola |
| MAS IPL | ✅ payment gateway, juga via web | — | — | — | — | — | — | — | — | daftar + data unit |

**Bukti faktor pendorong rating (dari P4)**
- **Pendorong positif**
  - CS cepat dan transparansi kas (RTPintar, 4,6; 2025–2026 sampel 5,0) — [Play](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID)
  - Kemudahan bayar dan izin di satu tempat (Ciputra Hub 2024, LEAP 5★) — [Play CH](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID); [Play LEAP](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID)
  - Kanal bayar fleksibel dijadikan pembanding positif: "SAYA PAKE CIPUTRA HUB JAUH LEBIH BAIK DAN LEBIH FLEKSIBEL" — [App Store Paramount](https://apps.apple.com/id/app/id1624020170?see-all=reviews)
- **Pendorong negatif**
  - Pembayaran gagal atau status tidak sinkron (Ciputra Hub, LEAP, bale)
  - Kanal bayar tunggal (Paramount–Mandiri, Ciputra 2 bank)
  - OTP/registrasi/KTP gagal (Summarecon, bale, OneSmile, Paramount)
  - Update paksa yang merusak (Ciputra Agu 2026, LEAP Okt 2026, OneSmile)
  - Komplain gagal dikirim atau ditutup tanpa konfirmasi warga (Ciputra)
  - Penghapusan fitur yang disukai (CCTV OneSmile)
  - Pemaksaan QR tanpa alternatif (Paramount, OneSmile)
  - Sumber: tautan ulasan di P4

### Inferences
- Pembayaran adalah **momen kebenaran** aplikasi pascahuni. Ia terjadi setiap bulan dan serentak (awal bulan), dan kegagalan langsung berujung denda/teguran. Rekonsiliasi pembayaran real-time (webhook gateway → status lunas) dan kapasitas di awal bulan lebih menentukan rating daripada fitur tambahan apa pun.
- Fitur keamanan seperti gate/QR menambah gesekan harian. Jika dipaksakan tanpa fallback (kartu, satpam), fitur itu menurunkan rating (Paramount). CCTV justru disukai dan dikeluhkan ketika dihapus (OneSmile).
- Komplain dengan SLA hanya membantu jika **warga ikut menutup tiket** (konfirmasi selesai dan rating) dan ada linimasa yang terlihat. Pola Klasterin (linimasa, perkiraan selesai, penanggung jawab) menjawab keluhan Ciputra Hub.

### Gaps
- Korelasi fitur→rating di sini kualitatif (sampel ulasan), bukan analisis statistik. Jumlah sampel per aplikasi kecil (7–140).
- Tidak ada data internal (tingkat adopsi, tingkat bayar tepat waktu) dari aplikasi mana pun.

---

## P6. Modul pascahuni minimum untuk platform developer (Estora) dan posisi Keluarga Ningrat

### Takeaway
Modul pascahuni minimum yang layak untuk Estora:
1. **Transisi otomatis akun pembeli → warga saat serah terima**, memakai akun WhatsApp OTP yang sudah ada.
2. **Tagihan IPL dengan VA multi-bank + QRIS (+ e-wallet), rekonsiliasi otomatis, dan link bayar via WhatsApp.**
3. **Tiket keluhan/perbaikan dengan SLA (memperluas SLA 48 jam yang sudah ada), linimasa, dan konfirmasi penutupan oleh warga.**
4. **Pengumuman/broadcast.**
5. **Dashboard web pengelola** (penagihan, tunggakan, laporan per cluster).

QR tamu dan tombol darurat cocok sebagai tahap 2. CCTV, gate, marketplace/PPOB, dan booking fasilitas sebaiknya tahap 3. Keluarga Ningrat unggul di breadth (keamanan + commerce) dibanding semua developer subsidi dan sebagian besar developer besar. Namun ia belum terbukti (1rb+, nol rating), tanpa izin renovasi/booking/QR tamu, tanpa jembatan pembeli→warga di dalam aplikasi, dan dengan akun iOS atas nama individu.

### Cited Findings
- **Pola akun pre-provisioned:** "Akun Klasterin dibuat oleh pengelola kawasan Anda" — [Play Klasterin](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID). RTPintar login dengan nomor terdaftar + OTP WhatsApp — [App Store RTPintar](https://apps.apple.com/id/app/id1458259481)
- **Kesinambungan pembeli→warga:** "Monitor angsuran, progres pembangunan, serta tagihan IPL Anda ketika menjadi warga" — [Play Rumahku PDA](https://play.google.com/store/apps/details?id=com.dwiwahanadeltamegah.rumahku&hl=id&gl=ID). Ciputra Hub memiliki menu "Konstruksi" dan referral — [App Store](https://apps.apple.com/id/app/id6478900292)
- **Pembayaran:**
  - Multi-metode (VA, QRIS, e-wallet) dengan validasi otomatis plus fallback transfer/tunai — [Play RTPintar](https://play.google.com/store/apps/details?id=com.rt_pintar&hl=id&gl=ID)
  - VA BCA/Mandiri + QRIS — [Play Klasterin](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID)
  - OneSmile via Blibli (VA, QRIS, e-wallet) — [JawaPos](https://www.jawapos.com/properti/2511070406/transformasi-gaya-hidup-digital-bayar-ipl-kini-bisa-dalam-satu-aplikasi)
  - Permintaan warga agar bisa bayar tanpa membuka aplikasi, cukup dengan nomor VA tetap seperti PLN/PAM (4 Apr 2025, 6 Mar 2025) — [Play Ciputra Hub](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)
  - Rincian tagihan yang transparan diminta (LEAP, 22 Okt 2026) — [Play LEAP](https://play.google.com/store/apps/details?id=com.lippohomes.leap&hl=id&gl=ID)
- **Penagihan via WhatsApp:** chatbot WA billing dengan klaim "success rate diatas 80%" — [rtpintar.com](https://rtpintar.com)
- **Tiket dengan SLA:** "Tangani tiket dan work order dengan SLA"; screenshot berisi linimasa, perkiraan selesai, petugas — [Play Klasterin](https://play.google.com/store/apps/details?id=id.klasterin.app&hl=id&gl=ID); [App Store](https://apps.apple.com/id/app/id6817015419)
- **Patokan harga SaaS pascahuni:**
  - RTPintar Rp120rb/bulan (≤100 unit) s.d. Rp900rb/bulan (2.500 unit) — [rtpintar.com/harga](https://rtpintar.com/harga)
  - Klasterin Rp180rb per 100 unit/bulan (promo; normal Rp450rb) — [klasterin.id](https://klasterin.id)
  - bale community membebankan "Biaya Layanan Rp 2.000" per tagihan (screenshot invoice) — [App Store](https://apps.apple.com/id/app/id1585400678)
- **Web sebagai kanal sah:** MAS IPL melayani warga via aplikasi maupun web — [Play MAS IPL](https://play.google.com/store/apps/details?id=com.ks.masipl&hl=id&gl=ID). Warga Ciputra meminta "Minimal ada opsi lain lah selain di app nya. Misalnya bisa login di web" (3 Agu 2026) — [Play Ciputra Hub](https://play.google.com/store/apps/details?id=com.ciputra.ciputrahub&hl=id&gl=ID)
- **Keluarga Ningrat:** 1rb+ unduhan, tanpa rating, v1.0.11 (Play, 20 Nov 2026); iOS v2.1 oleh "Anggi Supriatna" (update terakhir 2026-06-29) — [Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID); [Lookup iOS](https://itunes.apple.com/lookup?id=6752388007&country=id)

### Inferences

**Usulan modul pascahuni minimum Estora (inferensi dari matriks dan pola keluhan)**

| Prioritas | Fitur | Alasan berbasis bukti |
|---|---|---|
| MVP | **Akun warga otomatis saat serah terima.** Akun pembeli (WA OTP) diberi peran "warga" pada unitnya; anggota keluarga/penyewa diundang oleh pemilik | Menghapus gesekan klaim unit/KTP/kode pelanggan/referral yang paling sering dikeluhkan (Ciputra, Summarecon, LEAP, bale, Paramount) |
| MVP | **Tagihan IPL**: generate massal per cluster, VA multi-bank + QRIS (+ e-wallet) lewat payment gateway, status lunas via webhook, kuitansi, rincian komponen, denda/pengingat; **link bayar via WhatsApp** (tanpa wajib install) | Pembayaran = penyebab utama 1★ (Ciputra, LEAP, Paramount, bale); kanal tunggal dibenci; warga minta bayar tanpa buka aplikasi |
| MVP | **Tiket keluhan/perbaikan pascahuni** = perluasan modul komplain 48 jam: kategori, foto, petugas, linimasa, perkiraan selesai, **konfirmasi selesai & rating oleh warga**, eskalasi bila SLA lewat | Keluhan "ditutup padahal belum beres" (Ciputra); Klasterin menunjukkan pola yang benar |
| MVP | **Pengumuman/broadcast** (in-app + WhatsApp) | Universal di semua aplikasi; RTPintar/eWarga menunjukkan WA lebih menjangkau |
| MVP | **Dashboard web pengelola**: daftar unit & warga, tunggakan, rekonsiliasi, laporan keuangan per cluster, peran (admin estate, keuangan, teknisi) | BTN, Klasterin, RTPintar semua punya sisi pengelola web; tanpa ini tagihan tidak bisa dijalankan |
| Tahap 2 | Undangan tamu QR sekali pakai + validasi satpam; tombol darurat + kontak darurat; izin renovasi/muat barang dengan status | Ada di Klasterin, Paramount, Ciputra, LEAP, Summarecon; wajib ada **fallback non-aplikasi** (kartu/satpam) agar tidak bernasib seperti Paramount |
| Tahap 2 | Klaim garansi/defect pascaserah terima (tersambung ke data unit Estora) | LEAP menyebut klaim garansi; ini alami untuk platform developer (data unit & serah terima sudah ada) |
| Tahap 3 | Live CCTV, smart gate, booking fasilitas, marketplace/PPOB, loyalti | Bernilai tetapi mahal secara operasional/hardware; OneSmile bahkan menghapus CCTV; bukan penentu rating |

- **Bentuk produk:** karena Estora belum punya aplikasi native, **PWA/portal web + WhatsApp** dapat menutup MVP. Contohnya MAS IPL (web), RTPintar (chatbot WA), dan permintaan warga Ciputra akan opsi web. Ini juga menghindari risiko "update paksa merusak" dan inkonsistensi versi iOS/Android yang terlihat di Ciputra, LEAP, dan Keluarga Ningrat. Aplikasi native bisa menyusul saat fitur tahap 2–3 (QR gate, push, CCTV) dibutuhkan.
- **Model biaya:** harga pasar SaaS pascahuni sekitar Rp360–1.800 per unit/bulan. Rinciannya: RTPintar Rp1.200/unit untuk ≤100 unit, turun ke Rp360/unit pada paket 2.500 unit; Klasterin promo Rp1.800/unit. Ini ditambah atau diganti biaya layanan per transaksi (bale Rp2.000; klaim Rp5.000 di RTPintar). Biaya per transaksi dikeluhkan warga, jadi Estora sebaiknya membebankan langganan ke developer/pengelola, bukan ke warga.
- **Posisi Keluarga Ningrat:**
  - Breadth fitur di atas semua developer subsidi (Rumahku PDA, Pesona Kahuripan) dan setara atau lebih luas dari developer besar untuk keamanan/commerce: live CCTV, gate geofence, SOS, satpam bertugas, marketplace, PPOB.
  - Kekurangannya:
    - tidak ada izin renovasi, booking fasilitas, QR tamu, atau metering;
    - perjalanan pembeli (KPR, progres) ada di portal web terpisah, belum menyatu seperti Rumahku PDA;
    - belum ada bukti keandalan (nol rating, 1rb+);
    - bukti pembayaran baru terlihat VA BRI/Permata, belum terlihat QRIS/e-wallet;
    - rilis iOS dari akun individu dan tertinggal versi.
  - Pelajaran dari Ciputra/OneSmile: breadth tanpa keandalan pembayaran/komplain berujung rating 2-an begitu penggunaan diwajibkan.
- **Peluang Estora:** Estora tidak perlu menyaingi breadth Keluarga Ningrat. Pembedanya adalah (a) kesinambungan pembeli→warga dalam satu akun, (b) pembayaran IPL multi-kanal yang andal, dan (c) tiket dengan SLA dan konfirmasi warga. Kombinasi ketiganya tidak ditemukan utuh di aplikasi developer mana pun yang dianalisis.

### Gaps
- Tidak ada data tingkat adopsi atau kepatuhan bayar IPL dari aplikasi mana pun, sehingga dampak finansial modul tidak bisa dikuantifikasi.
- Biaya payment gateway (MDR QRIS, biaya VA) tidak diteliti di sini.
- Kesesuaian regulasi (pengelolaan dana IPL, PSE Kominfo, UU PDP untuk data KTP/tamu) tidak dianalisis.

---

## P7. Screenshot resmi toko yang disimpan

### Takeaway
46 screenshot resmi dari 12 aplikasi disimpan, maksimal 4 per aplikasi. Rumahku PDA hanya punya 2 di Play. Sumber iOS diambil dari `screenshotUrls` iTunes Lookup dengan segmen ukuran diganti `/600x0w.png`. Sumber Play diambil dari gambar `play-lh.googleusercontent.com` yang ber-alt "Gambar screenshot" dengan sufiks `=w526-h296-rw`, diunduh sebagai `=w1080`. Ikon 512×512 dilewati. Keluarga Ningrat tidak diunduh ulang karena sudah didokumentasikan di `cek_aplikasi.md`.

### Cited Findings
Semua path relatif terhadap `/home/user/dadada/research_notes/Riset aplikasi pesaing dan pemenang BTN/`. Sumber daftar: [iTunes Lookup](https://itunes.apple.com/lookup?id=6478900292&country=id) dan halaman Play di P1.

**Ciputra Hub** (iOS id6478900292)
- `screenshots/pascahuni_ciputrahub/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/ed/90/b7/ed90b73a-f0e2-dd29-f357-03a55e569f0b/1.__Appstore_-Home_1.png/600x0w.png (Beranda)
- `screenshots/pascahuni_ciputrahub/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/e6/33/14/e633141c-194b-e5ac-a7e5-a28e686e0149/2._Appstore_-_Unit_1.png/600x0w.png (Unit: Diklaim/Menunggu)
- `screenshots/pascahuni_ciputrahub/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/15/6c/c5/156cc5bc-3ef0-1727-8e19-dea9f68621f1/3._Appstore_-_Billing_1.png/600x0w.png (Tagihan multi-unit)
- `screenshots/pascahuni_ciputrahub/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/19/6f/42/196f423b-ee29-b954-cc04-c9f645ee846a/4._Appstore_-_Emergency_1.png/600x0w.png (Telepon Darurat)

**OneSmile** (iOS id1551898065)
- `screenshots/pascahuni_onesmile/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/aa/ff/f6/aafff6e3-94a4-5bb7-c7a6-01cd0c954a45/118a0848-bcad-418a-a0db-77bebc94cc5a_Artboard_1__U00282_U0029.jpg/600x0w.png
- `screenshots/pascahuni_onesmile/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/84/37/35/8437357e-09a9-1426-bfb0-b19369e02390/232f5fe1-82ba-4187-bcb4-bf80c22b84b9_Artboard_2_1242_x_2208_pixels__U00282_U0029.png/600x0w.png (Smart Gate/Booking)
- `screenshots/pascahuni_onesmile/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/c7/6f/a3/c76fa319-04e5-3fd3-0afe-dd52831f786c/2ff33c62-0ddc-469b-be7e-02d88146647a_Artboard_3_1242_x_2208_pixels__U00282_U0029.png/600x0w.png (City Guide)
- `screenshots/pascahuni_onesmile/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/a9/78/ef/a978ef3d-85d9-6a6c-3ba8-6c0185572e80/67132cf4-1b3b-4574-8e59-bf9f17517fdc_iphone_5_U002c5-1-4.png/600x0w.png (Masuk/Registrasi)

**Summarecon Home** (iOS id1584050086)
- `screenshots/pascahuni_summareconhome/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/0a/83/13/0a83139f-0ae6-4f8c-7b5b-03c66fddaa2a/1be16e2d-be04-4dd0-b224-403302ed8163_1242x2208__U0028depan_1_U0029.jpg/600x0w.png
- `screenshots/pascahuni_summareconhome/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/90/44/ed/9044ed7e-4d04-622d-d2ae-89735ccf1b2e/c9ad17fc-c0fe-466e-bded-ce73fc85f338_1242x2208__U0028depan_2_U0029.jpg/600x0w.png
- `screenshots/pascahuni_summareconhome/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/88/46/fa/8846facc-335b-36e9-319e-79852a2150ea/b9284c3a-8846-4e86-a36a-adaf05052cc8_1242x2208__U0028slide_1_U0029.jpg/600x0w.png
- `screenshots/pascahuni_summareconhome/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/74/cc/6d/74cc6de9-9a8b-d6af-9c37-d3db5c93e299/c5d53df1-11b7-4479-a921-2cfc392caf7e_1242x2208__U0028slide_2_U0029.jpg/600x0w.png

**LEAP** (iOS id6502327505)
- `screenshots/pascahuni_leap/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/0e/a8/b5/0ea8b50a-220c-cb14-7454-0de089604b94/e0d383be-c652-42de-b96a-2bafb17f1196_Screen_1.png/600x0w.png
- `screenshots/pascahuni_leap/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/b3/a4/ba/b3a4ba11-b265-aa72-1a94-3c2864d3df39/e727c646-b3ee-48be-a4ef-e5cd0413d5a6_Screen_2.png/600x0w.png
- `screenshots/pascahuni_leap/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/e8/f3/29/e8f32966-f9a4-c4ef-3b9d-c085701159e1/e863d472-e1b6-4d3a-9283-9824d9e318dd_Screen_3.png/600x0w.png
- `screenshots/pascahuni_leap/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/36/0e/94/360e94f0-bec6-0a85-748b-b7c04983df0a/55e4ba25-1bbf-4ba5-b3ce-606223610faa_Screen_4.png/600x0w.png

**Paramount Estate** (iOS id1624020170)
- `screenshots/pascahuni_paramountestate/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource116/v4/d5/50/55/d5505526-1554-122d-5f4a-f2ecbbfd345f/947aeb4c-e8ee-445f-ac37-d71f2482b488_1_-_first_screen_.png/600x0w.png
- `screenshots/pascahuni_paramountestate/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource126/v4/9c/8b/8c/9c8b8ca4-c070-33b8-4802-edb9552efd21/f63ed8fd-aa20-43e5-930f-b3ddb362c6f6_2_-_mobile_phone.png/600x0w.png
- `screenshots/pascahuni_paramountestate/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource116/v4/6d/91/30/6d913008-b0de-fa60-534d-a37f60d15163/27f24f32-e80c-4122-9075-23a72d44bad1_3_-_otp.png/600x0w.png
- `screenshots/pascahuni_paramountestate/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource116/v4/19/5e/e0/195ee00c-2a99-4e2a-0526-c83a854498bd/cf38ebe5-ee77-46a5-809a-f7225b5edc24_4-_home.png/600x0w.png

**JSmart 2.0** (iOS id1438657494)
- `screenshots/pascahuni_jsmart/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/bd/4c/c7/bd4cc78b-1708-dea3-c04c-046ae8ed4d94/pr_source.jpg/600x0w.png
- `screenshots/pascahuni_jsmart/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/23/c2/df/23c2dfa7-57f4-853c-94e7-7ec82042bc6d/pr_source.jpg/600x0w.png
- `screenshots/pascahuni_jsmart/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/85/cd/de/85cdded6-440a-177f-f6e8-1c2fb9cd1585/pr_source.jpg/600x0w.png
- `screenshots/pascahuni_jsmart/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/c1/01/a6/c101a610-13c5-0e3b-ed4a-3c01f5c51eac/pr_source.jpg/600x0w.png

**bale community** (iOS id1585400678)
- `screenshots/pascahuni_balecommunity/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/78/67/d8/7867d82e-a491-a822-84a9-67da6cdc82f4/Page_5.jpg/600x0w.png (Ajukan Persetujuan/unit)
- `screenshots/pascahuni_balecommunity/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/c9/e6/fc/c9e6fc0f-b9a5-e48d-a558-a1f88f0f9e2a/Page_2.jpg/600x0w.png (Daftar Komunitas)
- `screenshots/pascahuni_balecommunity/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/75/f7/ac/75f7aca6-88ec-fcd3-8c71-26e3a6ae0cb5/Page_4.jpg/600x0w.png (Invoice VA + biaya layanan)
- `screenshots/pascahuni_balecommunity/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/ed/86/3c/ed863cf9-a4d8-960a-a26a-e74a5fbe96ae/Page_3.jpg/600x0w.png (List tagihan)

**RTPintar** (iOS id1458259481)
- `screenshots/pascahuni_rtpintar/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/22/2d/60/222d6080-5963-07d8-39d5-c95ab6de4e88/9021b355-c29f-4ee4-9a2d-769e7ddbbbfd_Simulator_Screenshot_-_iPhone_8_Plus_-_2024-02-28_at_04.08.51.png/600x0w.png
- `screenshots/pascahuni_rtpintar/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/be/ec/f7/beecf776-066d-0887-75ba-b080cbc84dc4/7dfba370-5a33-4dcb-a388-49053618fa23_Simulator_Screenshot_-_iPhone_8_Plus_-_2024-02-28_at_05.41.26.png/600x0w.png
- `screenshots/pascahuni_rtpintar/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/72/d2/73/72d2732e-3126-b0f5-89e6-929bb743a284/7f76e135-f31b-438a-a5f0-9dd2414b051b_Simulator_Screenshot_-_iPhone_8_Plus_-_2024-02-28_at_05.41.47.png/600x0w.png (OTP via WhatsApp)
- `screenshots/pascahuni_rtpintar/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/29/4c/36/294c362a-4b05-8199-fe60-ccfd8fdfaeaa/ec4a656e-ddeb-4693-9d4f-35c03ec0fe21_Simulator_Screenshot_-_iPhone_8_Plus_-_2024-02-28_at_05.39.50.png/600x0w.png (Beranda + PANIC)

**Klasterin** (iOS id6817015419)
- `screenshots/pascahuni_klasterin/ios_01.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/c1/48/c6/c148c635-35f0-3e01-0a5d-02235d02fc08/01-home.png/600x0w.png
- `screenshots/pascahuni_klasterin/ios_02.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/fd/fa/ac/fdfaac82-4d92-cea0-4e9d-11c4d36998ef/03-tiket.png/600x0w.png (Detail tiket + linimasa)
- `screenshots/pascahuni_klasterin/ios_03.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/e5/93/1d/e5931d2e-3272-946e-cd64-c6dd01a510dc/04-tamu.png/600x0w.png (QR tamu)
- `screenshots/pascahuni_klasterin/ios_04.png` ← https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/3a/1e/11/3a1e11e8-c28a-7a82-953f-ec5a019a1928/02-ipl.png/600x0w.png (Tagihan IPL, VA BCA/Mandiri)

**Rumahku Puri Delta Asri** (Play; hanya 2 screenshot tersedia)
- `screenshots/pascahuni_rumahku_pda/play_01.png` ← https://play-lh.googleusercontent.com/EGsJe8_m6sjo8CYYFQ-HVn-GFJmOtuh83PmWCNeJ09hVFgdtlXMkxcVUVYmRdbnPwrrOmc7nceJGgM8YDWwq-w=w1080
- `screenshots/pascahuni_rumahku_pda/play_02.png` ← https://play-lh.googleusercontent.com/HB6rYPzZCX7y_6O5hwBAUZUXaoFnfhxS7fHLmVzJNvvPZJScvu0fDyQgiXhkh6vClXNwuiavsKvq_2y6O2qkCHE=w1080 (Angsuran/Progress Bangun/Komplain/Air)

**eWarga** (Play `id.citraikatsahabat.ewarga`)
- `screenshots/pascahuni_ewarga/play_01.png` ← https://play-lh.googleusercontent.com/xjjF4LekmkFkpzsYOGTo1Gt-XLtzTlGQtaVqfZLVsidO6kCtn2G0YIVsUef32tLIZ4S3ZMv1zCkqGyWcpcUqMz8=w1080
- `screenshots/pascahuni_ewarga/play_02.png` ← https://play-lh.googleusercontent.com/LNZFexKqjLvf4LPsfhRJ9t8O7zCWfcm4PR-3VeL190wQAm5PrCSkAjTp2P9YrFOVqPm06oOHHSrvyNrkEjZw=w1080
- `screenshots/pascahuni_ewarga/play_03.png` ← https://play-lh.googleusercontent.com/VAb90fLmU_Qn28DO_yPEO_aRUcuH25zkILZfKQZu-UdTIkn7kcuGjcXjPH0X830amczggOpZQ0XRkRbwUf6cZw=w1080 (Gabung instansi: QR/kode unik)
- `screenshots/pascahuni_ewarga/play_04.png` ← https://play-lh.googleusercontent.com/WveBhtTR9MN_xqmfDYTpzIu5p1nBwNQWlaL9aaYMD4u0ZAmLNP7c4yf8CWYNIDqIYtQG4j9t2k-NBRJE5Z_R=w1080

**MAS IPL** (Play `com.ks.masipl`)
- `screenshots/pascahuni_masipl/play_01.jpg` ← https://play-lh.googleusercontent.com/hHazahlioEvdwVz_LrfGxHuZimJ-bxo8KN2zkaTLFEu21H817EU2uCZkBDnYZgb0H0wD-kSTjQoVxz609uZ9=w1080
- `screenshots/pascahuni_masipl/play_02.jpg` ← https://play-lh.googleusercontent.com/sKMqwz_QLBURh0XZFhQuH2NkjQROIQFnYKoM6wdT2-mEExNco2hFaLPqCAlPgttuO9tBnxS8xxQeVC5dPIwHJA=w1080
- `screenshots/pascahuni_masipl/play_03.jpg` ← https://play-lh.googleusercontent.com/x1xuZf9ppFG8mpClxVrJfwrtbdvMm51p9IvERBWJysHdmR8bgkr9rdtkCpPqLa7RI3k2vctKK3CEn-peZd0jzg=w1080
- `screenshots/pascahuni_masipl/play_04.jpg` ← https://play-lh.googleusercontent.com/XDOXG_6fLN4ckgDas-o7kZZjc7vsfWvnXt8LMIyL3cHHMJuAqyu1qjq8LohjjQ7VlAzysBHGVATuSekMQQOn=w1080

### Inferences
- Untuk aplikasi yang ada di kedua toko, screenshot iOS dipilih karena resolusinya konsisten (600 px lebar). Screenshot Play biasanya berupa set materi yang sama.

### Gaps
- Screenshot Play untuk aplikasi yang diambil dari iOS tidak diunduh (diasumsikan duplikat, tidak diverifikasi satu per satu). Screenshot ke-5 dan seterusnya di toko tidak disimpan (batas 4).
