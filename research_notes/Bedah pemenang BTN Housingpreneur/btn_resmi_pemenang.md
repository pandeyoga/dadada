# Materi resmi BTN dan liputan media tentang pemenang BTN Housingpreneur Batch 1 (2024) dan Batch 2 (2025)

Diambil 2026-11-24. Fokus: kanal resmi BTN (btnhousingpreneur.com: Kilas Balik, Galeri, Berita, Beranda) dan liputan media atas malam penghargaan dan BTN Expo. Melengkapi dua catatan sebelumnya, yang tidak diulang di sini kecuali bila perlu untuk kelengkapan daftar:
- `Riset kompetitor dan BTN Housingpreneur/btn_housingpreneur_detail.md`
- `Riset aplikasi pesaing dan pemenang BTN/pemenang_btn_produk.md`

Cara kerja:
- Semua halaman dirender dengan Chromium/Playwright (viewport 1366×900, deviceScaleFactor 1). Tab dan akordeon Kilas Balik diklik satu per satu. Popup tenggat pendaftaran disembunyikan sebelum memotret.
- Foto resmi pemenang dibuka di URL gambarnya sendiri dan disimpan sebagai PNG.
- Halaman tonton YouTube menampilkan reCAPTCHA ("Saya bukan robot"), jadi tidak dipaksa. Sebagai gantinya dipakai halaman hasil pencarian YouTube, endpoint publik oEmbed (judul/kanal), dan thumbnail publik i.ytimg.com. Tidak ada video yang diunduh.
- Tidak login, tidak mendaftar, tidak memakai API privat.
- Skrip ada di `/tmp/claude-0/-home-user-dadada/4c43c2dd-1aa7-553c-9e9f-59508645de56/scratchpad/bedah_resmi/scripts/`. Teks mentah artikel ada di `.../bedah_resmi/out/art/`.

Konvensi:
- **Cited Findings** berisi fakta bersumber (URL, plus tanggal terbit atau akses).
- **Inferences** berisi penalaran saya.
- **[ringkasan pencarian]** berarti fakta hanya berasal dari ringkasan mesin pencari, belum terverifikasi di halaman sumber.
- **[dari foto]** berarti fakta dibaca langsung dari foto resmi, misalnya papan hadiah.
- Kolom "Digital?": **Ya** = produk utamanya aplikasi/platform/software; **Sebagian** = perangkat atau layanan fisik plus aplikasi; **Tidak** = material, desain, developer, atau jasa fisik; **?** = tidak diketahui.

---

## 1. Daftar lengkap pemenang per batch dan kategori

### Takeaway
- **Batch 1 (2024)** punya **20 pemenang** di empat kategori: Housing Related Innovation, Landed Residential, Eco House Design, Rumah Nusantara. Mereka dipilih dari 946 tim dan diumumkan di BTN Awards 2025, JICC, 15 Feb 2025.
- **Batch 2 (2025)** punya **27 pemenang**: 8 Business Ideation Mahasiswa, 8 Business Ideation Umum, 11 Developer & Pengusaha (Established). Mereka dipilih dari 58 finalis dan 1.171 submission, dan diumumkan di BTN Expo 2026, JICC, 31 Jan 2026.
- Situs resmi hanya memuat **edisi 2025**. Tidak ada pemilih edisi 2024. Daftar lengkap Batch 1 hanya ada di media, dengan sumber terlengkap Sumsel Pos.
- **Temuan baru dari foto resmi Kilas Balik: nominal hadiah per peringkat Batch 2 terbaca di papan cek.** Established (Tech, Value Chain, Affordable): Rp100 jt / Rp70 jt / Rp50 jt. Totalnya cocok persis dengan Rp1,5 miliar (lihat tabel hadiah).
- Produk digital di antara pemenang:
  - Batch 1: CIROES (aplikasi), Paktukang (platform web), dan konsep Platform Rusun Swadaya.
  - Batch 2: TRAIN-O (platform pelatihan + VR), GeoFloodAI (aplikasi ML), serta AITOMA dan myECO (IoT + aplikasi).
  - Tidak ada pemenang yang berupa software operasional developer.

### Cited Findings

**Batch 1: BTN Housingpreneur 2024 (Awarding: BTN Awards 2025, JICC Jakarta, Sabtu 15 Feb 2025)**
- Konteks: "BTN Housingpreneur Awards diberikan kepada 20 pemenang dari empat kategori berbeda, yang dipilih dari 946 tim peserta kompetisi." Di malam yang sama BTN memberi BTN Property Awards kepada 18 developer mitra di enam kategori. — [Sumsel Pos, 15 Feb 2025](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); [Investortrust, 16 Feb 2025](https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah); [Antara, 16 Feb 2025](https://megapolitan.antaranews.com/berita/355285/pemerintah-dukung-ide-inovasi-berkelanjutan-bagi-pembangunan-rumah-rakyat)
- Kick-off Batch 1: 26 Nov 2024 di UGM, lalu ITB dan kampus lain, termasuk Sayembara Desain Rumah Nusantara "BTN Nusantara Future House Design Competition" bersama IAI untuk desain rumah subsidi berunsur budaya lokal. — [Metro TV, 19 Feb 2025](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan); [Stockwatch](https://stockwatch.id/btn-housingpreneur-ajang-para-inovator-ciptakan-rumah-ramah-lingkungan-untuk-masa-depan/)

| Kategori / sub-kategori | Peringkat | Tim / perusahaan – perwakilan | Produk (satu baris) | Digital? | Sumber |
|---|---|---|---|---|---|
| Housing Related Innovation – Established Business (Value Chain) | J1 | PT Dua Mitra Gemilang – Tan Novita | Tidak ditemukan deskripsi produk | ? | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); J1 juga di [Kontan](https://keuangan.kontan.co.id/news/btn-dorong-kemunculan-inovasi-pengembangan-perumahan-ramah-lingkungan) |
| HRI – Established (Value Chain) | J2 | PT Plustik Maju Bersama – Reza Hasfinanda | Material bangunan dari sampah plastik rumah tangga, ikut Program Rumah Rendah Emisi BTN | Tidak | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); konfirmasi resmi "Juara 2 BTN Housingpreneur 2024 … Value Chain & Founder Plustik" di [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar) |
| HRI – Established (Technology) | J1 | PT Inovasi Keberlanjutan Indonesia (**CIROES**) – Sandy Wijaya | Aplikasi bank sampah dan penjemputan sampah terpilah (Android, 5 rb+ unduhan) | **Ya** | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); produk: [Google Play](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp) (catatan sebelumnya) |
| HRI – Established (Technology) | J2 | Paktukang Teknologi Karya Global – Moh. Rozaqul Anam | Platform jasa tukang, renovasi, dan bangun rumah dengan RAB transparan, monitoring progres, dan kredit | **Ya** (web + WA) | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); produk: [paktukang.com](https://paktukang.com/) (catatan sebelumnya) |
| HRI – Established (Technology) | J3 | PT Berdikari Teknologi Indonesia (**Autoconz**) – Antonius Ali | 3D construction printing (mesin + mortar) | Tidak (hardware) | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); [Kompasiana akun Autoconz](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi) |
| HRI – Business Ideation | J1 | Anugerah Nurrewa (bersama Imam dan Dimas, mitra dari startup mobility) | **Platform Rusun Swadaya**: menghimpun komunitas untuk membangun rusun swadaya di pusat kota dekat transportasi umum, dengan "akses pembiayaan dari BTN" | **Ya** (konsep platform) | [Investortrust, 19 Feb 2025](https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living); [Kontan](https://keuangan.kontan.co.id/news/btn-dorong-kemunculan-inovasi-pengembangan-perumahan-ramah-lingkungan) |
| HRI – Business Ideation | J2 | Yoval Julianto | Tidak ditemukan | ? | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/) |
| Landed Residential – Best Affordable House | Pemenang | PT Sembilan Bintang Lestari – Adhiimsyah Lutfhi (Jember) | Developer rumah subsidi berkonsep "eco green living" | Tidak | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan) |
| Landed Residential – Best Eco House Development | Pemenang | PT Habitat Tempat Hidup (Habitatland) – Ryan Adam | Developer eco-house, Bogor | Tidak | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/) |
| Landed Residential – Best Syariah Project | Pemenang | PT Kreasi Prima Nusantara – Hadiana | Developer proyek syariah | Tidak | idem |
| Landed Residential – Inspiring Sharia Project | Pemenang | PT Prosya Bangun Indonesia – Nurul Aini | Developer proyek syariah | Tidak | idem |
| Eco House Design – Established Business | Pemenang | PT Harmony Land Group – Muhammad Ridlo Aditya | Desain rumah ramah lingkungan ("menggabungkan inovasi teknologi dengan kearifan lokal") | Tidak | idem; kutipan di [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan) |
| Eco House Design – Business Ideation | J1 | Bramana Anjasmara Putra | Desain (judul tidak dipublikasikan) | Tidak | idem |
| Eco House Design – Business Ideation | J2 | Noor Indra Harjanto | Desain | Tidak | [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/) |
| Rumah Nusantara – Mahasiswa | J1 / J2 / J3 | **Rampak Huni** (desain khas Jawa Barat) / Nafas Bumi / Nusa Tropika | Desain rumah subsidi berunsur budaya lokal (sayembara bersama IAI) | Tidak | idem |
| Rumah Nusantara – Profesional | J1 / J2 / J3 | **Uma Lamo** (desain khas NTB) / Jiwana Carita / Rumah Multifungsi | idem | Tidak | idem |

- Hadiah Batch 1: total Rp1 miliar (catatan sebelumnya). Papan cek yang terbaca di foto awarding Investortrust: Rumah Nusantara Mahasiswa J2 **Rp15.000.000**, J3 **Rp7.500.000**; Rumah Nusantara Profesional J2 **Rp25.000.000**, J3 **Rp10.000.000**. Satu papan Eco House Design hanya terbaca "RP 35.00…". **[dari foto]** — [Investortrust, 19 Feb 2025 (foto 1)](https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living)
- Ejaan nama berbeda: media menulis "Anugerah Nurrewa", sedangkan layar panggung di thumbnail iNews (16 Feb 2025) menulis "**Anugrah Nurrewa** – Platform Rusun Swadaya". — [YouTube iNews](https://www.youtube.com/watch?v=6UCwY5aLy3I)

**Batch 2: BTN Housingpreneur 2025 (Awarding: penutupan BTN Expo 2026, JICC Jakarta, Sabtu 31 Jan 2026)**
- Kilas Balik resmi: 1.171 submission, 746 peserta Business Idea & Evaluation, 181 peserta Live Pitching, 58 finalis Grand Judging. Pendaftaran dibuka 22 Okt 2025; kick start di UI 28 Okt 2025; roadshow ITB, ITS, USU, Unhas (selesai 3 Des 2025); pendaftaran ditutup 24 Des, diperpanjang 28 Des 2025 untuk daerah terdampak bencana Aceh/Sumatra. — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) (diakses 2026-11-24)
- Trofi dan hadiah "dengan nilai total Rp1,5 miliar" diserahkan BTN bersama Wamen PKP Fahri Hamzah "dari sebanyak 58 finalis yang disaring dari 1.170 submission sejak 22 Oktober 2025". — [CNBC Indonesia, 31 Jan 2026](https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan); [Industry.co.id](https://www.industry.co.id/read/147708/btn-expo-2026-tutup-gemilang-lahirkan-inovator-muda-penggerak-perumahan-nasional). Lokasi JICC: [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan)
- Daftar di bawah berasal dari Kilas Balik (HTML dan tangkapan setiap tab/akordeon) dan cocok dengan [Akurat "Daftar Lengkap Pemenang"](https://www.akurat.co/keuangan/1307137077/daftar-lengkap-pemenang-btn-housingpreneur-2025-57-inovator-muda-unjuk-solusi-hunian-masa-depan). Akurat tidak mencantumkan J3 HRI Umum (Co-housing).

| Kelompok · Kategori | Peringkat | Tim / perusahaan | Karya / produk (satu baris) | Digital? | Sumber |
|---|---|---|---|---|---|
| Mahasiswa · Rumah Nusantara | J1 | Kelompok 35 Degrees | **Dhurung Argapana** (desain; deskripsi tidak dipublikasikan) | Tidak | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) |
| Mahasiswa · Rumah Nusantara | J2 | Kelompok Abdihyang | **ModuLego House 30** (desain) | Tidak | idem |
| Mahasiswa · House Design | J1 | Rafi Zufarul Fahd | **Growing Habitat** (desain) | Tidak | idem |
| Mahasiswa · House Design | J2 | Kelompok AKSI NYATA (Institut Teknologi Sepuluh Nopember, terbaca di layar panggung) | **MERRHAUZ** (desain) | Tidak | idem; [foto resmi](https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-hd-j23.webp) |
| Mahasiswa · House Design | J3 | Kelompok Wicwakarma Udayana (Universitas Udayana) | **Umah Rintis** (desain) | Tidak | idem |
| Mahasiswa · Housing Related Innovation | J1 | Kelompok **GeoFloodAI** (Ali Sulas Hidayat dkk., Palembang) | Aplikasi machine learning: pengguna menandai lokasi lalu mendapat skor risiko banjir. Berasal dari tesis S2, sudah diuji ke ±50 pengguna | **Ya** | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik); [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan) |
| Mahasiswa · HRI | J2 | Kelompok Jelanpaint | **Jelanpaint** (tidak ada deskripsi) | ? | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) |
| Mahasiswa · HRI | J3 | Kelompok MiBi-Tech | **MiBi-Tech 2.0** (tidak ada deskripsi) | ? | idem |
| Umum · Rumah Nusantara | J1 | Mifta Syahrudin | **Groving House** (desain) | Tidak | idem |
| Umum · Rumah Nusantara | J2 | E Design Studio | **Rumah Kampung Kota** (desain) | Tidak | idem |
| Umum · House Design | J1 | Beni Suroso | **Aparthouse** (desain) | Tidak | idem |
| Umum · House Design | J2 | Kelompok Arkitekton Limatama | **Terra Griya** (desain) | Tidak | idem |
| Umum · House Design | J3 | Irwan Arifin Lubis | **K O T A [K] T U M B U H** (desain) | Tidak | idem |
| Umum · HRI | J1 | PT Inovasi Tangguh Bencana (Zamzam Multazam) | **Proteka**: coating seperti cat yang menaikkan kapasitas dinding meredam gempa, untuk retrofitting | Tidak | idem; [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan) |
| Umum · HRI | J2 | Maulana Derifato Achmad | **myECO** (kemungkinan perangkat IoT + aplikasi penghemat listrik; identitas dari catatan sebelumnya, belum dikonfirmasi BTN) | Sebagian | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik); [Google Play myECO](https://play.google.com/store/apps/details?id=id.myeco.myeco) |
| Umum · HRI | J3 | Anindya Dhiracitta | **Model Co-housing Skema Koperasi Perumahan Kolektif** (model kelembagaan/pembiayaan) | Tidak | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) (tidak tercantum di Akurat/CNBC) |
| Developer & Pengusaha · House Design (Established) | J1 (satu-satunya) | PT Sakura Lestari Internasional | **Green Pilar Asri** (proyek/desain perumahan) | Tidak | idem |
| Dev · House Value Chain Innovation | J1 | PT Raesaka Amanah Widyakarya | **Parongpong RAW Lab**: waste-to-material dari sampah residu non-plastik, misalnya Oriplast dari karung semen sebagai pengganti decking kayu | Tidak | idem; [CNBC, 30 Jan 2026](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan) |
| Dev · House Value Chain Innovation | J2 | PT Wasteforchange Alam Indonesia | **RR Board**: papan dan atap dari sampah (Repair Project) | Tidak | idem; [Detik, Jan 2026](https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026) |
| Dev · House Value Chain Innovation | J3 | PT Andalusia Intra Teknologi (GridSolr) | **KPR Energy**: memudahkan kepemilikan panel surya bagi pemilik hunian baru, dengan monitoring real-time | Sebagian | idem; [gridsolr.com](https://gridsolr.com/) (catatan sebelumnya) |
| Dev · House Technology Innovation | J1 | PRANA TECH | **TRAIN-O**: platform pelatihan, sertifikasi, dan penempatan tenaga konstruksi (mobile learning + VR) | **Ya** | idem; [Kitabaru, 3 Feb 2026](https://kitabaru.com/train-o-dan-modula-dua-inovasi-digital-jawab-tantangan-krusial-konstruksi-indonesia/) |
| Dev · House Technology Innovation | J2 | PT Hayago Robotika Indonesia | **AITOMA**: IoT + AI + aplikasi penghematan listrik untuk rumah dan kawasan | Sebagian | idem; [Beritajatim, 18 Feb 2026](https://beritajatim.com/inovasi-ai-pemuda-lamongan-sabet-juara-nasional-di-btn-housing-preneur-2026) |
| Dev · House Technology Innovation | J3 | PT Mercusuar Agresif Perkasa | **RUMAH GOKILS**: pest control sebagai "sistem perlindungan hunian" **[ringkasan pencarian]** | Tidak | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik); deskripsi dari catatan sebelumnya |
| Dev · Affordable House Development | J1 | PT Infiniti Triniti Jaya (GM Halbert Kurniadi) | **Perumahan Mulia Gading Kencana** (Jakarta): rumah subsidi dengan sertifikat bangunan gedung hijau ("yang pertama di Indonesia untuk perumahan subsidi"), septic tank fiber, material langsung dari pabrik mitra | Tidak | idem; [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan) |
| Dev · Affordable House Development | J2 | PT Sakura Sejahtera | **Mangkualam Asri** (Karawang) | Tidak | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik); lokasi: [Akurat](https://www.akurat.co/keuangan/1307137077/daftar-lengkap-pemenang-btn-housingpreneur-2025-57-inovator-muda-unjuk-solusi-hunian-masa-depan) |
| Dev · Affordable House Development | J3 | PT Bagus Permata Biru | **Permata Grati Garden** (Lumajang) | Tidak | idem |
| Dev · Commercial Residential – Special Award "Inspiring Residential Development" | ★ | PT Maumere Putra Development | **Perumahan Gloria Regency Waturia** (Maumere) | Tidak | [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) |

**Nominal hadiah Batch 2 per peringkat, dibaca dari papan cek di foto resmi Kilas Balik [dari foto]** (file `kilasbalik_2025_foto_*.png`; sumber gambar `https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/*.webp`)

| Kelompok · Kategori | J1 | J2 | J3 | Keterangan |
|---|---|---|---|---|
| Established · Affordable House Development | Rp100.000.000 | Rp70.000.000 | Rp50.000.000 | Terbaca (dev-ahd-j1, dev-ahd-j23) |
| Established · House Technology Innovation | Rp100.000.000 | Rp70.000.000 | Rp50.000.000 | Terbaca (dev-hti-j1, dev-hti-j23) |
| Established · House Value Chain Innovation | Rp100.000.000 | Rp70.000.000 | Rp50.000.000 | Terbaca (dev-hvci-j1, dev-hvci-j23) |
| Established · House Design | Rp85.000.000 | – | – | Terbaca (papan di dev-hd-j1 dan di latar mhs-hri-j1) |
| Established · Commercial Residential ("Inspiring Residential Development") | Rp40.000.000 | – | – | Terbaca (dev-cr-sa) |
| Umum · House Design | Rp65.000.000 | Rp45.000.000 | Rp25.000.000 | Terbaca (umum-hd-j1, umum-hd-j23) |
| Umum · Housing Related Innovation | Rp65.000.000 | Rp45.000.000 | **Rp50.000.000** | Terbaca. J3 lebih besar daripada J2; anomali, tetapi konsisten dengan total (lihat Inferences) |
| Umum · Rumah Nusantara | Rp65.000.000 | Rp45.000.000 | – | Terbaca |
| Mahasiswa · Housing Related Innovation | Rp55.000.000 | Rp35.000.000 | Rp20.000.000 | Terbaca (mhs-hri-j1, mhs-hri-j23) |
| Mahasiswa · Rumah Nusantara | Rp55.000.000 | Rp35.000.000 | – | Terbaca (mhs-rn-j1, mhs-rn-j2) |
| Mahasiswa · House Design | (Rp55 jt) | (Rp35 jt) | (Rp20 jt) | **Tidak terbaca.** Foto hanya menampilkan layar panggung; angka dalam kurung adalah inferensi |

- Papan cek berlogo "Danantara Indonesia", "btn", "btn housingpreneur 2025", dan "btn expo 2026". Penyerahan dilakukan bersama Wamen PKP Fahri Hamzah. — foto resmi di atas; [CNBC, 31 Jan 2026](https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan)
- Finalis non-pemenang yang tampil di Expo menurut media (tidak tercantum di Kilas Balik): Ontoown (aplikasi rent-to-own → DP KPR, Bandung; **Ya**), Agriya (cat dari sekam padi), dan Bell Living Lab (material limbah kopi). — [CNBC, 30 Jan 2026](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan)

### Inferences
- **Total hadiah Batch 2 cocok persis dengan Rp1,5 miliar** jika House Design Mahasiswa = 55/35/20 jt, sama dengan kategori Mahasiswa lain:
  - Established: 3×(100+70+50) + 85 + 40 = 785 jt.
  - Umum: (65+45+25) + (65+45+50) + (65+45) = 405 jt.
  - Mahasiswa: 110 + 90 + 110 = 310 jt.
  - Jumlah: **1.500 jt**.

  Hitungan ini memperkuat pembacaan papan, termasuk anomali J3 HRI Umum Rp50 jt.
- **Hirarki hadiah memperlihatkan prioritas BTN.** Juara kategori teknologi/value chain/affordable Established (Rp100 jt) dihargai sekitar 1,5× juara Business Ideation Umum (Rp65 jt) dan sekitar 1,8× juara Mahasiswa (Rp55 jt). Ini sejalan dengan bobot "Executable" dan bukti implementasi di guidebook (catatan sebelumnya). Untuk entri Estora di jalur Established, juara 1 Housing Tech/Ecosystem Batch 3 kemungkinan bernilai sekitar Rp100 jt atau lebih (total Batch 3 "miliaran"). Ini estimasi.
- Kategori Established Tech/Value Chain Batch 2 masing-masing punya 3 juara dari sekitar 10 peserta Live Pitching (catatan sebelumnya). Peluang juara per peserta Live Pitching di jalur ini sekitar 30%, jauh lebih tinggi daripada Business Ideation (3 dari 25).
- Produk digital murni yang menang hanya di level "platform yang mengorkestrasi layanan fisik" (CIROES, Paktukang, TRAIN-O) atau "aplikasi analitik risiko" (GeoFloodAI). Tidak ada pemenang yang berupa CRM/ERP/back-office developer.

### Gaps
- Daftar Batch 1 tidak ada di situs resmi BTN; hanya Sumsel Pos yang memuat daftar lengkap 20 nama. Media lain hanya memuat J1. Rilis resmi BTN untuk daftar Batch 1 (btn.co.id) tidak ditemukan lewat pencarian.
- Deskripsi karya desain (Business Ideation House Design dan Rumah Nusantara kedua batch), PT Dua Mitra Gemilang, Yoval Julianto, Jelanpaint, dan MiBi-Tech 2.0 tidak dipublikasikan.
- Nominal hadiah Batch 1 per peringkat hanya terbaca sebagian (Rumah Nusantara J2/J3). Kategori HRI Batch 1 tidak terbaca.
- Hadiah House Design Mahasiswa 2025 tidak terbaca di foto mana pun.

---

## 2. Apa kata juri dan BTN tentang alasan menang (termasuk siapa jurinya)

### Takeaway
- Tidak ada pernyataan juri yang menjelaskan alasan menang per pemenang. Yang ada hanya kerangka umum dari juri dan direksi BTN.
- **Batch 1** dibingkai sebagai "event matching" antara developer dan pemasok desain/material. Penekanannya pada perubahan iklim, kearifan lokal, TKDN, dan Program 3 Juta Rumah. Juri yang disebut: **Ridwan Kamil** (Dewan Juri Nasional; arsitek) dan **Yu Sing** (Founder AKANOMA), plus perwakilan BTN dan akademisi.
- **Batch 2** dibingkai sebagai pencarian **startup/proptech yang bisa di-scale up dan "layak dibiayai perbankan"**. Juri bernama yang terpublikasi hanya **Ryan Maurice Tallulah** (Founder BARDI Smart Home). Ia menyebut peserta Established mengincar "orderan dari developer-developer" BTN, bukan hadiahnya.

### Cited Findings

**Juri (nama dan latar)**
- Batch 1, juri bernama dan lokasi Grand Judging:
  - Ridwan Kamil disebut "salah satu Dewan Juri Nasional BTN Housingpreneur, M. Ridwan Kamil, yang juga arsitek dan entrepeneur" — [Investortrust, 16 Feb 2025](https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah). Ia Gubernur Jawa Barat 2018–2023 dan "menjadi juri untuk menyeleksi 400 inovasi perumahan" — [Antara, Feb 2025](https://megapolitan.antaranews.com/berita/355041/ridwan-kamil-jadi-juri-400-inovasi-perumahan).
  - Grand Judging digelar "di Menara BTN Harmoni pada 13 Februari 2025 … di hadapan dewan juri yang terdiri dari Ridwan Kamil (Gubernur Jawa Barat 2018-2023), **Yu Sing (Founder AKANOMA)**, perwakilan BTN, serta akademisi di bidang properti". — [Kompasiana, akun Autoconz (konten pengguna, bukan media redaksional)](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi)
  - Rilis Habitatland yang dikutip catatan sebelumnya kini mengembalikan HTTP 520 (2026-11-24), jadi tidak bisa diverifikasi ulang.
- Batch 2: "Ryan Maurice Tallulah, salah satu anggota Dewan Juri BTN Housingpreneur 2025 dan adalah founder BARDI Smart Home". — [Akurat, Feb 2026](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan). Ia juga narasumber talk show Kick Start 2025 di UI sebagai "Founder & CVO BARDI Smart Home". — [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar)
- Komposisi juri Batch 2 tanpa nama: seleksi ide oleh "Dewan Juri yang terdiri atas akademisi, arsitek, dan manajemen BTN"; Grand Judging "melibatkan pelaku industri perumahan". — [Metro TV, 16 Des 2025](https://www.metrotvnews.com/read/bJECjRza-masih-ada-waktu-jadi-inovator-perumahan) (catatan sebelumnya)
- Foto resmi di Beranda menunjukkan panggung "grand judging … elevate beyond your limit … [Jan]uari 2026" dan sesi "live pitching" 2025. Tanggal persis Grand Judging Batch 2 tidak terbaca. — [Beranda, foto Grand Judging](https://btnhousingpreneur.com/frontend/images/home/2026/foto-grand-judging-2025.webp); [foto Live Pitching](https://btnhousingpreneur.com/frontend/images/home/2026/foto-live-pitching-2025.webp)

**Batch 1: kutipan tentang apa yang dicari dan mengapa dipilih**
- Ridwan Kamil: "Sebagai juri yang memiliki latar belakang arsitek, saya melihat banyak sekali terobosan-terobosan luar biasa di tengah tantangan dunia termasuk isu climate change. Ada 400 inovasi yang muncul dari kompetisi ini. **Pilihan juri adalah yang terbaik dan diharapkan akan jadi solusi dan inspirasi untuk Indonesia makin maju**." — [Investortrust](https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah); [Antara](https://megapolitan.antaranews.com/berita/355285/pemerintah-dukung-ide-inovasi-berkelanjutan-bagi-pembangunan-rumah-rakyat); [Pasardana](https://pasardana.id/news/2025/2/16/bbtn-jaring-400-inovasi-perumahan)
- Ridwan Kamil: "Saya mengapresiasi BTN yang berinisiasi melaksanakan 'award' bagi **inovasi bisnis, inovasi desain, inovasi material baru ramah lingkungan**". Program 3 juta rumah "membutuhkan kolaborasi banyak pihak". — [Antara, Feb 2025](https://megapolitan.antaranews.com/berita/355041/ridwan-kamil-jadi-juri-400-inovasi-perumahan)
- Dirut BTN Nixon Napitupulu (15 Feb 2025): "Ini merupakan event pertama, tapi akan terus berlanjut setiap tahun agar menjadi **event matching antara developer dan anak-anak muda yang memproduksi desain dan material yang dibutuhkan oleh industri perumahan**. Jadi dari sisi supply dan demand ada kolaborasi yang baik." — [JPNN, 16 Feb 2025](https://www.jpnn.com/news/btn-beri-apresiasi-para-mitra-pengembang-desainer-dan-inovator-rumah); [Kontan](https://keuangan.kontan.co.id/news/btn-perkuat-kolaborasi-ekosistem-perumahan-lewat-btn-awards-2025)
- Nixon: "Kami ingin mendukung inovasi dalam desain rumah, teknologi perumahan yang berkelanjutan, serta keterlibatan pelaku usaha lokal. Sebagai contoh, kini telah dikembangkan produk batu bata dan floor deck berbasis sampah plastik." Ia juga menyebut TKDN sektor perumahan "mencapai 90%". — [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/)
- Nixon (19 Feb 2025): BTN berharap "tercipta sebuah **sistem bisnis yang berkesinambungan** untuk ekosistem perumahan, yang tidak hanya menguntungkan secara ekonomi, tetapi juga memberikan dampak positif bagi lingkungan dan masyarakat". — [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan)
- Dirjen Perumahan Perdesaan Kementerian PKP Imran: pemerintah mendukung ide "yang mengusung **budaya nusantara** dan selaras dengan prinsip-prinsip **keberlanjutan** sebagai referensi bagi pembangunan rumah rakyat". Ide pemenang diharapkan mendukung Program Tiga Juta Rumah. Bonny Z. Minang (Satgas Perumahan) menekankan "business matching". — [Investortrust](https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah)
- Saat kick-off Batch 1 (UGM, Nov 2024), Direktur Distribution & Institutional Funding BTN Jasmin berkata: "Para pemenang berkesempatan menjadi **mitra bisnis BTN** dalam ekosistem perumahan skala nasional". — [Liputan6, 27 Nov 2024](https://www.liputan6.com/bisnis/read/5809203/btn-komitmen-lahirkan-wirausahawan-muda-begini-caranya)
- Pembingkaian oleh pemenang sendiri:
  - Harmony Land (Eco House Design): "menggabungkan inovasi teknologi dengan kearifan lokal, menciptakan desain yang bukan hanya menarik secara visual, tetapi **solusi nyata** bagi masa depan".
  - Sembilan Bintang Lestari: rumah subsidi "yang keren, kekinian, dan … ramah terhadap lingkungan".
  - Platform Rusun Swadaya: "fasilitator pembiayaan dengan risiko yang minim dan pengamanan berlapis karena berbasis komunitas".

  — [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan); [Investortrust](https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living)

**Batch 2: kutipan tentang apa yang dicari dan mengapa dipilih**
- Juri Ryan Maurice Tallulah: "Para established business masuk ke kompetisi ini dan berharap bisa menang, namun **bukan untuk meraih hadiah ratusan juta rupiah, tetapi mereka berharap masuk ke dalam ekosistem BTN dan bisa mendapatkan orderan dari developer-developer yang sudah kerja sama bertahun-tahun dengan BTN**." — [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan)
- Direktur Risk Management BTN Setiyo Wibowo (6 Nov 2025, rilis resmi): pemenang "akan dibimbing agar ide mereka tak hanya kreatif, tapi juga **layak dibiayai perbankan**. Tujuan akhirnya adalah menciptakan **inovasi yang dapat diterapkan dan menghasilkan nilai ekonomi nyata**". Inkubasi 3 bulan diarahkan agar usaha "efisien, menguntungkan, dan **bankable**". Ide yang diincar mencakup "platform digital seperti marketplace material dan jasa konstruksi". — [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/BTN-Housingpreneur-2025-Buka-Akses-Inovator-Muda-ke-Ekosistem-Perumahan-Nasional)
- Setiyo (30 Jan 2026, pembukaan Expo): "Kami mengumpulkan startup-startup di bidang perumahan, mulai dari **property technology (proptech)**, produsen material bangunan yang mengandung unsur sustainability, desain rumah rendah emisi atau rumah hijau … Sebagai bank yang punya ekosistem perumahan paling besar, kami mencari mitra-mitra baru yang dapat diajak berkolaborasi untuk bisa **di-scale up**." — [CNBC, 30 Jan 2026](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan); [Investortrust](https://investortrust.id/financial/93101/inovasi-rumah-berbasis-limbah-hingga-ai-mitigasi-banjir-jadi-sorotan-btn-expo-2026)
- Ringkasan redaksi CNBC atas finalis: mayoritas inovasi yang lolos ke tahap akhir "tidak lagi memandang rumah semata sebagai bangunan fisik, melainkan juga ingin menjawab **persoalan struktural** sektor properti Indonesia, mulai dari keterbatasan daya beli, tingginya risiko bencana di kawasan permukiman, hingga ketergantungan pada material bangunan konvensional. … solusi yang ditawarkan dinilai memiliki **potensi untuk dikembangkan secara komersial dan berkelanjutan**." — [CNBC, 30 Jan 2026](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan)
- Nixon (31 Jan 2026): "Mayoritas peserta merupakan startup anak muda … terutama terkait **pemanfaatan teknologi di sektor perumahan**." Juga: "Startup-startup ini memang perlu kita beri ruang agar bisa dilihat masyarakat secara luas, sehingga banyak hal bisa menjadi lebih **efektif dan efisien**." Serta: "BTN percaya investasi terbaik adalah investasi pada talenta dan sumber daya manusia." — [CNBC, 31 Jan 2026](https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan); [Kontan](https://keuangan.kontan.co.id/news/btn-housingpreneur-2025-lahirkan-58-inovator-muda-di-bidang-perumahan)
- Wamen PKP Fahri Hamzah: program ini membantu anak muda memecahkan masalah sektor perumahan, "yakni masih **mismatch-nya supply dan demand** untuk hunian yang layak". — [CNBC, 31 Jan 2026](https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan)
- Corsec BTN Ramon Armando (Okt/Nov 2025): pemenang "bergabung dengan ekosistem BTN Housingpreneur yang berskala nasional dan berkesempatan untuk **menjadi mitra bisnis BTN**". BTN membentuk komunitas alumni per angkatan: "Housingpreneur bukan sekadar lomba, tapi sebuah movement". — [btnhousingpreneur.com, 29 Okt 2025](https://btnhousingpreneur.com/news/btn-housingpreneur-resmi-digelar); [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar)
- Cara pemenang Batch 2 membingkai karyanya saat menerima trofi:
  - GeoFloodAI: masalah "yang sering terlewat … untuk konsumen ritel dan developer", "user dapat melakukan tag lokasi … akan muncul scoring-nya", sudah user testing ke sekitar 50 pengguna.
  - Proteka: "produk yang mudah diaplikasikan, bentuknya coating seperti cat biasa".
  - Infiniti Triniti Jaya: "sertifikat bangunan gedung hijau. Ini yang pertama di Indonesia untuk perumahan subsidi … Semoga … menjadi suatu percontohan".

  — [Akurat](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan)
- Frasa "solusi yang bisa diimplementasikan" tidak ditemukan persis. Padanan terdekat dari BTN adalah "inovasi yang dapat diterapkan dan menghasilkan nilai ekonomi nyata" (Setiyo, rilis resmi 7 Nov 2025, di atas) dan "solusi nyata, bukan sekadar konsep" (Setiyo, [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026); catatan sebelumnya).

### Inferences
- Pola "mengapa menang" yang konsisten di dua batch, disimpulkan dari kutipan dan profil pemenang:
  1. **Sudah berjalan dan ada bukti.** Contoh: sertifikat hijau (Infiniti), uji pengguna (GeoFloodAI), unduhan aplikasi (CIROES), pekerjaan selesai (Paktukang).
  2. **Menjawab masalah struktural berskala nasional dengan angka.** Contohnya slide Autoconz "12 juta keluarga Indonesia masih menunggu rumah yang layak" (bagian 4).
  3. **Selaras dengan agenda pemerintah**: 3 Juta Rumah, iklim/keberlanjutan, kearifan lokal, TKDN.
  4. **Ada jalur ke bisnis BTN.** Batch 1 menekankan pasokan untuk developer (matching). Batch 2 menekankan "bankable", "di-scale up", dan proptech.
- Kutipan Ryan Tallulah menunjukkan bahwa juri melihat Established Business sebagai calon **pemasok ke jaringan developer BTN**. Untuk Estora, narasi yang paling selaras adalah "Estora membuat developer mitra BTN lebih efisien dan mempercepat akad KPR BTN" (penjualan ke jaringan developer BTN), bukan sekadar "aplikasi bagus".
- Juri Batch 1 berlatar arsitektur (Ridwan Kamil, Yu Sing), sedangkan juri Batch 2 yang bernama berlatar produk teknologi rumah (BARDI Smart Home). Ini selaras dengan pergeseran pemenang dari desain/material (2024) ke teknologi/IoT/AI (2025). Inferensi dari dua nama saja.

### Gaps
- Daftar lengkap dewan juri Batch 1 dan Batch 2 tidak dipublikasikan di situs resmi maupun media; hanya tiga nama yang ditemukan.
- Tidak ada lembar penilaian, skor, atau feedback tertulis per pemenang yang publik.
- Konten video YouTube (wawancara juri/direksi saat awarding) tidak bisa diakses karena halaman tonton terblokir reCAPTCHA. Deskripsi video tidak terbaca.

---

## 3. Sinergi BTN pascakompetisi per pemenang

### Takeaway
Bagian "Sinergi dengan BTN" dan "Kolaborasi strategis antar finalis" di Kilas Balik (berlabel Edisi 2025) hampir seluruhnya berisi **alumni Batch 1** (Autoconz, Habitatland, Harmony Land, CIROES, Paktukang, Prosya, Kreasi Prima), ditambah tiga nama yang tidak ada di daftar pemenang mana pun (Rumah Pracetak Bandung, RAWHAUS, TANAREKA). Semua sinergi langsung dengan BTN berbentuk **KPR/pembiayaan unit, pasokan untuk program BTN, atau pengembangan kawasan NPL**. Per 24 Nov 2026 belum ada sinergi BTN yang dipublikasikan untuk pemenang Batch 2. Yang terlihat hanya pelibatan alumni sebagai pembicara.

### Cited Findings
- Teks "Sinergi dengan BTN" (6 kartu) — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) (file `kilasbalik_2025_sinergi_*.png`):
  - Rumah Pracetak Bandung, label "Rumah Rendah Emisi BTN": "Produsen bahan bangunan untuk program Rumah Rendah Emisi BTN."
  - Habitatland, label "KPR BTN": "Kerja sama melalui skema KPR BTN."
  - RAWHAUS, label "KPR Hijau", "KPR BTN Tapera": "Kolaborasi KPR Hijau, KPR BTN Tapera, dan pengembangan rumah."
  - TANAREKA, label "KPR": "Fasilitas pembiayaan KPR untuk unit yang dibangun/dikelola."
  - Autoconz (3D Printing), label "KPR BTN": "Kolaborasi pembangunan rumah 3D dengan skema KPR BTN."
  - PT Harmony Land Group, label "Compact Harmony Living House": "Pengembangan kawasan NPL dengan Compact Harmony Living House."
- Teks "Kolaborasi strategis antar finalis" (4 klaster) — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik) (file `kilasbalik_2025_kolaborasi_*.png`):
  - **Pemberdayaan & Desain**: PT Prosya × Pak Adjie + Damare Design + Rumah Pracetak. "Kolaborasi untuk mempertemukan investor potensial dengan Prosya dan pembelajaran mendesain hotel."
  - **Inovasi Material & Hunian Berkelanjutan**: PT Berdikari × Rebricks + Kometa; Habitatland × Rebricks. "Inovasi pengolahan sampah menjadi material bangunan 3DCP dan pengembangan hunian terintegrasi pertanian."
  - **Pengelolaan Perumahan & Digitalisasi**: CIROES × Paktukang.com; PT Prosya Bangun × Habitatland. "Kerja sama dalam pengembangan manajemen IPL dan pelatihan digital marketing properti."
  - **Pengembangan Infrastruktur**: PT Harmonyland × TANAREKA; TANAREKA × PT Kreasi Prima. "Kolaborasi melalui sesi berbagi terkait perencanaan Masterplan Infrastruktur dan masterplan proyek."
- Program Rumah Rendah Emisi diluncurkan Q4 2024 bersama developer dan melibatkan startup pengolah sampah plastik: "Beberapa startup yang terlibat antara lain Rebrick, **Plustik**, dan Green Brick." — [btnhousingpreneur.com, 19 Okt 2026](https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-itb-bandung-inovasi-perumahan)
- Pelibatan alumni sebagai pembicara:
  - Founder Plustik Reza Hasfinanda (J2 Value Chain 2024) di talk show Kick Start 2025 UI. — [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar)
  - Direktur GridSolr Hamdan Wahyudi (J3 Value Chain 2025) di roadshow Batch 3 Semarang, Okt 2026. — [Aktual, 21 Okt 2026](https://aktual.com/btn-housingpreneur-hadir-di-semarang-bedah-inovasi-rumah-zaman-now/) (catatan sebelumnya)
- Janji pascakompetisi untuk pemenang Batch 2: inkubasi 3 bulan, diskusi dengan pengembang besar, bertemu pembeli potensial, dan dibimbing agar "layak dibiayai perbankan". — [btnhousingpreneur.com, 7 Nov 2025](https://btnhousingpreneur.com/news/BTN-Housingpreneur-2025-Buka-Akses-Inovator-Muda-ke-Ekosistem-Perumahan-Nasional)

**Tabel sinergi per pemenang** (sumber sinergi: Kilas Balik, kecuali disebut lain)

| Pemenang (batch, kategori) | Sinergi langsung dengan BTN | Kolaborasi antar-finalis / lainnya |
|---|---|---|
| CIROES (B1, J1 Tech) | Tidak tercatat | × Paktukang.com: manajemen IPL dan pelatihan digital marketing properti |
| Paktukang.com (B1, J2 Tech) | Tidak tercatat | × CIROES (idem) |
| Autoconz / PT Berdikari (B1, J3 Tech) | **KPR BTN**: rumah 3D dengan skema KPR BTN | × Rebricks + Kometa: sampah menjadi material 3DCP |
| Plustik (B1, J2 Value Chain) | Program Rumah Rendah Emisi BTN ([rilis Okt 2026](https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-itb-bandung-inovasi-perumahan)) | Founder menjadi pembicara Kick Start 2025 |
| PT Dua Mitra Gemilang (B1, J1 Value Chain) | Tidak tercatat | Tidak tercatat |
| Platform Rusun Swadaya (B1, J1 BI) | Tidak tercatat (walau konsepnya "akses pembiayaan dari BTN") | Tidak tercatat |
| Habitatland (B1, Best Eco House Dev.) | **KPR BTN** | × Rebricks (hunian terintegrasi pertanian); × PT Prosya Bangun (IPL, digital marketing) |
| PT Prosya Bangun Indonesia (B1, Inspiring Sharia) | Tidak tercatat | × Pak Adjie + Damare Design + Rumah Pracetak (investor, desain hotel); × Habitatland |
| PT Kreasi Prima Nusantara (B1, Best Syariah) | Tidak tercatat | × TANAREKA (sesi masterplan) |
| PT Harmony Land Group (B1, Eco House Design Est.) | **Compact Harmony Living House**: pengembangan kawasan NPL | × TANAREKA (masterplan infrastruktur) |
| PT Sembilan Bintang Lestari, desainer B1 (Bramana, Noor Indra, Rampak Huni, Uma Lamo, dll.) | Tidak tercatat | Tidak tercatat |
| Semua pemenang Batch 2 (TRAIN-O, AITOMA, RUMAH GOKILS, Parongpong, RR Board, KPR Energy, Infiniti, dll.) | **Belum ada yang dipublikasikan** per 2026-11-24 | GridSolr (KPR Energy) menjadi pembicara roadshow Semarang, Okt 2026 |
| Non-pemenang di daftar sinergi: Rumah Pracetak Bandung, RAWHAUS, TANAREKA | Rumah Rendah Emisi / KPR Hijau + KPR BTN Tapera / KPR untuk unit | Klaster desain dan infrastruktur |

### Inferences
- Kilas Balik "Edisi 2025" mencampur hasil 2025 (pemenang dan angka) dengan **sinergi yang terealisasi selama 2025 oleh alumni 2024**. Bagi pemenang, kemungkinan perlu sekitar 1 tahun sampai sinergi BTN muncul di materi resmi.
- Rumah Pracetak Bandung, RAWHAUS, dan TANAREKA tidak tercantum sebagai pemenang di Sumsel Pos (2024) maupun Kilas Balik (2025). Kemungkinan mereka finalis atau peserta 2024. Artinya, **finalis non-juara pun bisa mendapat sinergi KPR**. Ini inferensi; kategori dan peringkat mereka tidak terverifikasi.
- Dua pemenang digital Batch 1 (CIROES, Paktukang) **tidak** mendapat sinergi langsung dengan BTN yang tercatat. Mereka hanya berkolaborasi satu sama lain soal IPL dan digital marketing. Sinergi BTN yang tercatat jatuh ke pihak yang menghasilkan **unit rumah yang bisa di-KPR-kan** atau **pasokan program BTN**. Implikasi untuk Estora: slide "Sinergi BTN" sebaiknya menjanjikan sesuatu yang bisa diukur BTN dalam volume KPR/akad (misalnya unit developer pengguna Estora yang mengalir ke KPR BTN), bukan hanya integrasi teknis.
- Plustik sudah ikut Rumah Rendah Emisi sejak Q4 2024, berdekatan dengan masa lomba Batch 1. Belum jelas apakah sinergi ini hasil kemenangan atau sudah ada sebelumnya.

### Gaps
- Tidak ada angka (jumlah unit KPR, nilai pembiayaan, durasi) untuk satu pun sinergi yang tercatat.
- Isi program inkubasi 3 bulan dan siapa yang benar-benar mengikutinya tidak dipublikasikan.
- Kategori dan peringkat Rumah Pracetak Bandung, RAWHAUS, dan TANAREKA di kompetisi tidak ditemukan.

---

## 4. Galeri, berita, dan YouTube yang ditemukan

### Takeaway
- **Situs resmi** hanya punya satu halaman yang memuat pemenang, yaitu Kilas Balik 2025. Galeri hanya berisi album **roadshow Batch 3 (2026)**, padahal tajuknya "dari Kick-Start sampai Awarding". Berita resmi (8 artikel) tidak memuat satu pun artikel awarding, Grand Judging, Expo, atau daftar finalis Batch 1/2.
- Liputan awarding datang dari **media** (siaran pers BTN yang dimuat ulang) dan **YouTube kanal TV berita** (tvOne, Metro TV, iNews, BeritaSatu, VIVA).
- Tidak ditemukan kanal YouTube resmi BTN Housingpreneur. Situs hanya menautkan Instagram, TikTok, X, dan Facebook.
- Satu materi pitch yang terlihat publik: **foto slide "INSPIRATION" Autoconz saat Grand Judging Batch 1**.

### Cited Findings

**Kilas Balik** ([btnhousingpreneur.com/kilas-balik](https://btnhousingpreneur.com/kilas-balik), diakses 2026-11-24)
- Struktur halaman:
  - Hero "Edisi 2025".
  - Pencapaian Program 2025 (narasi + 4 angka).
  - Kutipan Nixon: "Ajang BTN Housingpreneur merupakan bukti nyata komitmen BTN dalam mendukung pembiayaan rumah yang layak dan terjangkau, sekaligus mendorong inovasi yang meningkatkan kualitas hidup masyarakat Indonesia."
  - Kolaborasi strategis antar finalis (4 klaster).
  - Sinergi dengan BTN (6 kartu).
  - Pemenang 2025 (tab segmen Mahasiswa / Umum (Non-Mahasiswa) / Developer & Pengusaha; setiap kategori berupa akordeon dengan foto penyerahan dan lightbox).
  - "Dampak nyata program": Pengembangan Bisnis, Ekosistem Berkelanjutan, Solusi Perumahan Inovatif.
- Tidak ada pemilih edisi 2024. String "2024" tidak muncul di HTML halaman.
- Foto pemenang tersedia di `https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/{mhs|umum|dev}-{kategori}-{j1|j2|j23|sa}.webp`, total 20 foto.

**Beranda** ([btnhousingpreneur.com](https://btnhousingpreneur.com/))
- Seksi "Kilas Balik BTN Housingpreneur 2025" berisi angka 1.171/746/181/58, lima foto (BTN Expo 2026, Grand Judging 2025, Kick-start UI 2025, Live Pitching 2025, Registrasi Kick-start 2025), dan tombol "Lihat Kilas Balik". Teks: "1.171 karya masuk pada edisi 2025. Kini giliran kamu ikut…"

**Galeri** ([btnhousingpreneur.com/galeri](https://btnhousingpreneur.com/galeri))
- Subjudul "8 dokumentasi kegiatan, dari Kick-Start sampai Awarding". Filter yang ada hanya 10 album roadshow 2026. Jumlah foto per filter (dihitung dari item yang tampil): Semua 403; Bandung Dev 60 / Mhs-Umum 65; Jakarta Dev 38 / Mhs-Umum 36; Malang Dev 28 / Mhs-Umum 33; Semarang Mhs-Umum 37 / Dev 26; Bali Mhs-Umum 49 / Dev 31.
- **Tidak ada album Awarding, Expo, Grand Judging, atau Live Pitching Batch 1/2.**

**Berita** ([btnhousingpreneur.com/news](https://btnhousingpreneur.com/news), 3 halaman, filter "Semua"/"Press Release")

| Tanggal | Judul |
|---|---|
| 19 Okt 2026 | [BTN Housingpreneur Batch 3 Ajak Anak Muda Bandung Ciptakan Inovasi Perumahan](https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-itb-bandung-inovasi-perumahan) (menyebut Plustik di Rumah Rendah Emisi) |
| 19 Okt 2026 | [BTN Housingpreneur Batch 3 Dorong Gen Z …](https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-dorong-gen-z-hadirkan-inovasi-sektor-perumahan) |
| 8 Jan 2026 | [Pengumuman Peserta yang Lolos Seleksi Ide Bisnis BTN Housingpreneur 2025](https://btnhousingpreneur.com/news/pengumuman-peserta-yang-lolos-seleksi-ide-bisnis-btnhp2025) (181 peserta Live Pitching; hanya nama ketua) |
| 21 Nov 2025 | [Blusukan Cari Inovasi Perumahan … Roadshow di USU Medan](https://btnhousingpreneur.com/news/blusukan-cari-inovasi-perumahan-btn-housingpreneur-gelar-roadshow-di-usu-medan) |
| 15 Nov 2025 | [BTN Housingpreneur Sapa Surabaya …](https://btnhousingpreneur.com/news/BTN-Housingpreneur-Ajak-Arsitek-Pengusaha-dan-Mahasiswa-Surabaya) |
| 7 Nov 2025 | [Cari Bibit Unggul Inovator Perumahan, Kick Start … 2025](https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar) (alumni Plustik sebagai pembicara; komunitas alumni) |
| 7 Nov 2025 | [BTN Housingpreneur 2025 Buka Akses Inovator Muda …](https://btnhousingpreneur.com/news/BTN-Housingpreneur-2025-Buka-Akses-Inovator-Muda-ke-Ekosistem-Perumahan-Nasional) (kutipan "layak dibiayai perbankan", "bankable") |
| 29 Okt 2025 | [BTN Housingpreneur Resmi Digelar](https://btnhousingpreneur.com/news/btn-housingpreneur-resmi-digelar) (pemenang "berkesempatan menjadi mitra bisnis BTN") |

**Media yang meliput awarding dan Expo** (judul dan foto disimpan; lihat bagian 5)
- Batch 1 (Feb 2025):
  - [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/): daftar lengkap.
  - [Investortrust 16 Feb](https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah) dan [Investortrust 19 Feb](https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living): foto panggung dengan papan hadiah.
  - [Antara 355285](https://megapolitan.antaranews.com/berita/355285/pemerintah-dukung-ide-inovasi-berkelanjutan-bagi-pembangunan-rumah-rakyat), [Antara 355041](https://megapolitan.antaranews.com/berita/355041/ridwan-kamil-jadi-juri-400-inovasi-perumahan), [JPNN](https://www.jpnn.com/news/btn-beri-apresiasi-para-mitra-pengembang-desainer-dan-inovator-rumah), [Kontan](https://keuangan.kontan.co.id/news/btn-dorong-kemunculan-inovasi-pengembangan-perumahan-ramah-lingkungan), [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan), [Pasardana](https://pasardana.id/news/2025/2/16/bbtn-jaring-400-inovasi-perumahan).
  - [Kompasiana Autoconz](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi): foto Grand Judging.
  - [bertuahpos](https://bertuahpos.com/?p=242020) menampilkan halaman verifikasi bot dan tidak dibuka.
- Batch 2 (Jan 2026):
  - [CNBC 30 Jan](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan) dan [CNBC 31 Jan](https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan).
  - [Industry.co.id](https://www.industry.co.id/read/147708/btn-expo-2026-tutup-gemilang-lahirkan-inovator-muda-penggerak-perumahan-nasional), [Kontan](https://keuangan.kontan.co.id/news/btn-housingpreneur-2025-lahirkan-58-inovator-muda-di-bidang-perumahan), [JPNN](https://www.jpnn.com/news/awarding-btn-housingpreneur-2025tutup-rangkaian-btn-expo-2026).
  - Akurat: [daftar lengkap](https://www.akurat.co/keuangan/1307137077/daftar-lengkap-pemenang-btn-housingpreneur-2025-57-inovator-muda-unjuk-solusi-hunian-masa-depan), [inovator siap](https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan), [expo ditutup](https://akurat.co/keuangan/830479/btn-expo-2026-resmi-ditutup-awarding-btn-housingpreneur-2025-lahirkan-57-inovator-muda-perumahan).
  - [Investortrust 93101](https://investortrust.id/financial/93101/inovasi-rumah-berbasis-limbah-hingga-ai-mitigasi-banjir-jadi-sorotan-btn-expo-2026), [Monitor Indonesia](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026), [Metro TV](https://www.metrotvnews.com/read/kewCjz0V-btn-buka-akses-hunian-hingga-peluang-usaha-dalam-satu-ekosistem).
  - [Detik: booth Waste4Change/RR Board](https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026) memuat 3 foto booth: stand biru "btn expo 2026 Build, Battle and Beat", meja/bangku dari papan daur ulang, dan kartu "You're looking at a product made from low-value plastic waste".
  - Tidak bisa dibuka: [Bisnis](https://ekonomi.bisnis.com/read/20260130/47/1948688/btn-expo-2026-perkenalkan-inovasi-perumahan-rent-to-own) (verifikasi Cloudflare) dan [BCA Sekuritas](https://bcasekuritas.co.id/latest-news/news/para-inovator-btn-housingpreneur-siap-dukung-program-perumahan) ("server sedang sibuk").
  - **Kompas.com: tidak ditemukan** artikel tentang awarding. Yang ada hanya video KompasTV tentang pembukaan Batch 3.
- Angka penyelenggara yang tidak seragam:
  - Batch 2: "1.170 submission", "57 inovator" (CNBC/Industry/Akurat) vs "58 inovator" (Kontan) vs "lebih dari 8.000 pendaftar" (Setiyo, CNBC 30 Jan).
  - Batch 1: "946 tim" (BTN) vs "400 inovasi" (Ridwan Kamil).

  Sumber sama seperti di atas.

**Materi pitch yang terlihat**
- Foto "Perwakilan Autoconz, Antonius Ali Saat Grand Judging di Menara BTN Harmoni, Jakarta" (13 Feb 2025):
  - Isi slide: **"INSPIRATION — 12 juta keluarga Indonesia masih menunggu rumah yang layak"**, foto keluarga di depan rumah, logo Autoconz, tagar "#TeknologiIndonesiaPunya".
  - Layar samping: "GRAND JUDGING BTN Housingpreneur". Dua juri duduk di meja depan.

  — [Kompasiana Autoconz](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi) (file `media_b1_2025-02_kompasiana_autoconz_foto_grand_judging_menara_btn.png`)
- Foto Beranda "Grand Judging 2025": presenter di depan layar "grand judging … elevate beyond your limit … [Jan]uari 2026". Isi slide peserta tidak terlihat. Foto "Live Pitching 2025": ruang rapat dengan layar "live pitching" dan foto bersama, tanpa slide peserta. — [foto Grand Judging](https://btnhousingpreneur.com/frontend/images/home/2026/foto-grand-judging-2025.webp); [foto Live Pitching](https://btnhousingpreneur.com/frontend/images/home/2026/foto-live-pitching-2025.webp)

**YouTube** (pencarian publik di youtube.com/results, 2026-11-24; metadata judul/kanal via oEmbed; tanggal relatif terhadap 24 Nov 2026)
- **Tidak ditemukan kanal resmi "BTN Housingpreneur".** Kanal resmi BTN ("Bank Tabungan Negara") muncul di hasil pencarian hanya dengan video lain (Danantara Housing Expo 2026, KPP BTN), bukan video awarding Housingpreneur.

| Video | Kanal | Waktu/tayang (relatif) | Isi yang terlihat di thumbnail |
|---|---|---|---|
| [Awarding BTN Housing Preneur 2025 \| Kabar Siang](https://www.youtube.com/watch?v=OXKC6jppGfg) | tvOneNews | ~9 bln lalu (≈Feb 2026), 1,1 rb | Layar "AWARDING btn housingpreneur 2025"; seluruh pemenang dengan papan cek; teks "BTN Housingpreneur 2025 wadah inovator bidang perumahan" |
| [BTN Housing Preneur 2025 Lahirkan Inovator Sektor Perumahan \| Kabar Siang](https://www.youtube.com/watch?v=S7EWjaK6xZw) | tvOneNews | ~9 bln lalu, 646 | Penyerahan papan "JUARA 3"; teks "BTN berperan penting dalam mendorong lahirnya inovasi di industri perumahan" |
| [BTN Housingpreneur Lahirkan Inovator Sektor Perumahan – Metro Pagi Primetime](https://www.youtube.com/watch?v=aYWcI36jW6o) | METRO TV | ~9 bln lalu, 1,1 rb | Papan "JUARA 1 … Rp85.000.000" dan "JUARA 2 … Rp45.000.000"; teks "Inovasi perumahan di puncak BTN Expo 2026" |
| [Sukses Tutup BTN Expo 2026, Anak Bangsa Tunjukkan Kreativitas dan Inovasi!](https://www.youtube.com/watch?v=KLktVqaSxEI) | BeritaSatu | ~9 bln lalu, 320 | Pejabat duduk di barisan depan; ticker "BTN Expo dorong anak muda di ekosistem perumahan" |
| [Usung Tema "Build, Batle and Beat", BTN Expo 2026 Resmi Dibuka](https://www.youtube.com/watch?v=FtZv2vYAqNU) | METRO TV | ~9 bln lalu, 618 | "BTN Expo 2026, perkuat transformasi bank dengan layanan bisnis" |
| [Intip Keseruan BTN Expo 2026 yang Resmi Dibuka di Jakarta](https://www.youtube.com/watch?v=RPnz-78--ig) | METRO TV | ~9 bln lalu, 678 | Papan "btn expo 2026 Build, Battle and Beat" dan hitung mundur "00:01"; "BTN Expo 2026 resmi dibuka, tawarkan hunian hingga peluang usaha" |
| [BTN EXPO 2026 Full Highlight](https://www.youtube.com/watch?v=Q1ohLtcn5-A) | Indonesia5 | ~8 bln lalu, 63 | Kerumunan pengunjung/konser |
| [KoBill Finalist BTN HP 2025 #pitching](https://www.youtube.com/watch?v=zW7afC4hWO0) | Bill Cri Wi (peserta) | ~1 thn lalu, 4 | Vlog peserta: teks "Live Pitching BTN HP 2025 'KoBill n Friends'" (tidak ada slide) |
| [BTN Housingpreneur 2025 Jadi Ajang Talenta Muda …](https://www.youtube.com/watch?v=-MMRr0f6EMI) | METRO TV | ~11 bln lalu, 459 | "BTN Housingpreneur 2025 di Makassar" (roadshow Unhas; papan "Bantuan Pendidikan Mahasiswa/i Universitas Hasanuddin Rp100.000.000") |
| [BTN Wujudkan Ekosistem Perumahan Kolaboratif Lewat Housingpreneur 2025](https://www.youtube.com/watch?v=smrc8ZLqwMs) | METRO TV | ~1 thn lalu, 219 | Talk show roadshow Bandung, 8 Nov 2025: "BTN ajak inovator muda ubah wajah industri perumahan nasional" |
| [Mendukung Program Prabowo, Inovasi Perumahan lewat Housingpreneur 2025](https://www.youtube.com/watch?v=tT1mjC_ldj8) | VIVA.CO.ID | ~11 bln lalu, 557 | "Rumah terjangkau ide anak bangsa"; dua orang memegang plakat |
| [Dukung Wirausaha Muda, BTN Tawarkan Hadiah Miliaran Rupiah](https://www.youtube.com/watch?v=PtztBc96MDk) | VIVA.CO.ID | ~1 thn lalu, 244 | Layar situs "Wujudkan Hunian Masa Depan Indonesia … Hadiah total hingga miliaran rupiah" (kick-off Batch 2) |
| [Desain Rumah Nusantara, BTN Berikan Penghargaan Untuk Developer \| iNews Pagi \| 16/02](https://www.youtube.com/watch?v=6UCwY5aLy3I) | Official iNews | ~1 thn lalu (16 Feb 2025), 329 | **Batch 1**: layar panggung BUMN/BTN 75 "Juara 1 Anugrah Nurrewa — Platform Rusun Swadaya" |
| [BTN Awards 2025, Dorong Karya Inovatif Arsitek Muda Berbakat](https://www.youtube.com/watch?v=q3bY7d2C8Io) | BeritaSatu | ~1 thn lalu (Feb 2025), 489 | **Batch 1**: wawancara Nixon di depan backdrop "btn awards 75"; teks "Inovasi desain perumahan di BTN Awards 2025" |

- Video profil pemenang di kanal pemenang sendiri: kanal "Parongpong RAW Lab" memuat "PARONGPONG RAW LAB VIDEO PROFILE" dan "Ghost Net to Building Materials". Tidak disimpan di sini karena di luar cakupan kanal BTN.

### Inferences
- BTN tidak memelihara arsip publik awarding di kanal sendiri (galeri, berita, YouTube). Arsip awarding yang bisa dibedah praktis hanya **foto pemenang di Kilas Balik** dan **rilis yang dimuat ulang media**.
- Slide Autoconz membuka dengan bagian "INSPIRATION" dan satu angka besar tentang backlog rumah. Ini sama dengan struktur wajib guidebook Batch 3 (Page 1–2 Inspiration: kondisi, masalah, urgensi). Struktur itu tampaknya sudah dipakai sejak Batch 1. Untuk Estora, buka deck dengan satu angka masalah nasional yang langsung terkait developer/KPR (misalnya backlog, lamanya proses KPR, atau rasio pembatalan).

### Gaps
- **Halaman tonton YouTube diblokir reCAPTCHA**, jadi deskripsi, tanggal unggah persis, dan durasi video tidak terambil. Hanya judul, kanal, tayangan, waktu relatif, dan thumbnail yang tersimpan.
- Instagram @btnhousingpreneur, TikTok @btnhousingpreneur, X @btnhpreneur, dan Facebook (ditautkan di footer situs) tidak dibuka karena biasanya meminta login. Kemungkinan materi pemenang terbanyak justru ada di Instagram.
- Rilis resmi di btn.co.id untuk awarding kedua batch tidak ditemukan lewat pencarian.
- Video pitching pemenang (rekaman Live Pitching/Grand Judging) tidak ditemukan publik.

---

## 5. Daftar screenshot

Folder: `/home/user/dadada/research_notes/Bedah pemenang BTN Housingpreneur/screenshots/btn_resmi/`. Semua diambil 2026-11-24 dengan Chromium/Playwright, viewport 1366×900, deviceScaleFactor 1. Semua gambar ≤ 3.487 px tinggi. Kolom "Ukuran" = lebar×tinggi piksel.
- File `*_judul.png` adalah potongan halaman mulai dari judul artikel (1366×1100), yang memuat judul, tanggal, dan foto utama. Iklan/banner situs kadang ikut terpotret.
- File `*_foto*.png` adalah tangkapan elemen gambar di artikel.
- File `kilasbalik_2025_foto_*.png` dan `home_foto_*.png` adalah gambar resmi yang dibuka dari URL gambarnya.
- File `yt_*_thumbnail.png` adalah thumbnail publik `i.ytimg.com/vi/<id>/hqdefault.jpg`.

Total **150 file**.

### Kilas Balik (resmi) (54 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `kilasbalik_2025_dampak_program.png` | Seksi "Dampak nyata program" | https://btnhousingpreneur.com/kilas-balik | 1366×408 |
| `kilasbalik_2025_developer_affordable_house_development.png` | Kartu Established · Affordable House Development (Mulia Gading Kencana; Mangkualam Asri; Permata Grati Garden); tab developer | https://btnhousingpreneur.com/kilas-balik | 1200×623 |
| `kilasbalik_2025_developer_commercial_residential.png` | Kartu Established · Commercial Residential – Special Award (PT Maumere Putra Development); tab developer | https://btnhousingpreneur.com/kilas-balik | 1200×581 |
| `kilasbalik_2025_developer_house_design.png` | Kartu Established · House Design (PT Sakura Lestari Internasional – Green Pilar Asri); tab developer | https://btnhousingpreneur.com/kilas-balik | 1200×581 |
| `kilasbalik_2025_developer_house_technology_innovation.png` | Kartu Established · House Technology (TRAIN-O; AITOMA; RUMAH GOKILS); papan Rp100/70/50 jt terlihat; tab developer | https://btnhousingpreneur.com/kilas-balik | 1200×624 |
| `kilasbalik_2025_developer_house_value_chain_innovation.png` | Kartu Established · House Value Chain (Parongpong RAW Lab; RR Board; KPR Energy); tab developer | https://btnhousingpreneur.com/kilas-balik | 1200×623 |
| `kilasbalik_2025_foto_dampak_bg.png` | Latar "Dampak": foto stok tangan menggambar denah | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dampak-bg.webp | 1600×1066 |
| `kilasbalik_2025_foto_developer_affordable_juara1_infiniti.png` | Foto resmi J1 Affordable House Development Rp100.000.000 & J2 Rp70.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-ahd-j1.webp | 900×600 |
| `kilasbalik_2025_foto_developer_affordable_juara2_3_sakura_bagus.png` | Foto resmi J2 Affordable Rp70.000.000 & J3 Rp50.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-ahd-j23.webp | 900×600 |
| `kilasbalik_2025_foto_developer_commercial_special_award_maumere.png` | Foto resmi Special Award "Inspiring Residential Development" (Commercial Residential); papan Rp40.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-cr-sa.webp | 900×600 |
| `kilasbalik_2025_foto_developer_house_design_juara1_sakura_lestari.png` | Foto resmi J1 House Design Established (panggung lebar); papan Rp85.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-hd-j1.webp | 900×599 |
| `kilasbalik_2025_foto_developer_house_technology_juara1_trainO.png` | Foto resmi J1 House Technology Rp100.000.000 & J2 Rp70.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-hti-j1.webp | 900×600 |
| `kilasbalik_2025_foto_developer_house_technology_juara2_3_aitoma_rumahgokils.png` | Foto resmi J2 House Technology Rp70.000.000 & J3 Rp50.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-hti-j23.webp | 900×600 |
| `kilasbalik_2025_foto_developer_value_chain_juara1_parongpong.png` | Foto resmi J1 House Value Chain Rp100.000.000 & J2 Rp70.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-hvci-j1.webp | 900×600 |
| `kilasbalik_2025_foto_developer_value_chain_juara2_3_rrboard_kprenergy.png` | Foto resmi J2 House Value Chain Rp70.000.000 & J3 Rp50.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/dev-hvci-j23.webp | 900×600 |
| `kilasbalik_2025_foto_hero_bg.png` | Latar hero Kilas Balik: panggung "AWARDING btn housingpreneur 2025" dengan seluruh pemenang | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/hero.webp | 1600×1065 |
| `kilasbalik_2025_foto_mahasiswa_house_design_juara1.png` | Foto resmi House Design Mahasiswa: layar panggung J1/J2/J3 (nama & kampus) | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-hd-j1.webp | 900×599 |
| `kilasbalik_2025_foto_mahasiswa_house_design_juara2_3.png` | Foto resmi layar panggung J2 Kelompok AKSI NYATA (ITS) & J3 Wicwakarma Udayana | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-hd-j23.webp | 900×599 |
| `kilasbalik_2025_foto_mahasiswa_hri_juara1_geofloodai.png` | Foto resmi J1 HRI Mahasiswa (GeoFloodAI) Rp55.000.000 & J2 Rp35.000.000; latar: papan J1 House Design Established Rp85.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-hri-j1.webp | 900×600 |
| `kilasbalik_2025_foto_mahasiswa_hri_juara2_3_jelanpaint_mibitech.png` | Foto resmi J2 HRI Mahasiswa Rp35.000.000 & J3 Rp20.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-hri-j23.webp | 900×599 |
| `kilasbalik_2025_foto_mahasiswa_rumah_nusantara_juara1.png` | Foto resmi J1 Rumah Nusantara Mahasiswa; papan Rp55.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-rn-j1.webp | 900×1579 |
| `kilasbalik_2025_foto_mahasiswa_rumah_nusantara_juara2.png` | Foto resmi J2 Rumah Nusantara Mahasiswa; papan Rp35.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/mhs-rn-j2.webp | 900×599 |
| `kilasbalik_2025_foto_quote_bg.png` | Latar kutipan: pembicara di podium (hitam-putih) | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/quote.webp | 842×595 |
| `kilasbalik_2025_foto_umum_house_design_juara1.png` | Foto resmi J1 House Design Umum; papan Rp65.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-hd-j1.webp | 900×537 |
| `kilasbalik_2025_foto_umum_house_design_juara2_3.png` | Foto resmi J2 (Rp45.000.000) & J3 (Rp25.000.000) House Design Umum | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-hd-j23.webp | 900×537 |
| `kilasbalik_2025_foto_umum_hri_juara1_proteka.png` | Foto resmi J1 HRI Umum (Proteka); papan Rp65.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-hri-j1.webp | 900×537 |
| `kilasbalik_2025_foto_umum_hri_juara2_3_myeco_cohousing.png` | Foto resmi J2 HRI Umum (kaos "myECO") Rp45.000.000 & J3 Rp50.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-hri-j23.webp | 900×537 |
| `kilasbalik_2025_foto_umum_rumah_nusantara_juara1.png` | Foto resmi J1 Rumah Nusantara Umum; papan Rp65.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-rn-j1.webp | 900×537 |
| `kilasbalik_2025_foto_umum_rumah_nusantara_juara2.png` | Foto resmi J2 Rumah Nusantara Umum; papan Rp45.000.000 | https://btnhousingpreneur.com/frontend/images/kilas-balik/2026/umum-rn-j2.webp | 900×537 |
| `kilasbalik_2025_hero.png` | Hero "Kilas Balik BTN Housingpreneur 2025 – Mendorong inovasi ekosistem perumahan Indonesia" | https://btnhousingpreneur.com/kilas-balik | 1366×900 |
| `kilasbalik_2025_kolaborasi_01_pemberdayaan_desain.png` | Klaster Pemberdayaan & Desain: PT Prosya × Pak Adjie + Damare Design + Rumah Pracetak | https://btnhousingpreneur.com/kilas-balik | 590×212 |
| `kilasbalik_2025_kolaborasi_02_inovasi_material_hunian_berkelanjutan.png` | Klaster Inovasi Material: PT Berdikari × Rebricks + Kometa; Habitatland × Rebricks | https://btnhousingpreneur.com/kilas-balik | 590×212 |
| `kilasbalik_2025_kolaborasi_03_pengelolaan_perumahan_digitalisasi.png` | Klaster Pengelolaan Perumahan & Digitalisasi: CIROES × Paktukang.com; Prosya × Habitatland (IPL, digital marketing) | https://btnhousingpreneur.com/kilas-balik | 590×212 |
| `kilasbalik_2025_kolaborasi_04_pengembangan_infrastruktur.png` | Klaster Pengembangan Infrastruktur: Harmonyland × TANAREKA; TANAREKA × Kreasi Prima | https://btnhousingpreneur.com/kilas-balik | 590×212 |
| `kilasbalik_2025_kolaborasi_antar_finalis.png` | Seksi "Kolaborasi strategis antar finalis" (4 klaster) | https://btnhousingpreneur.com/kilas-balik | 1366×710 |
| `kilasbalik_2025_kutipan_dirut.png` | Kutipan Dirut BTN Nixon Napitupulu | https://btnhousingpreneur.com/kilas-balik | 1366×654 |
| `kilasbalik_2025_mahasiswa_house_design.png` | Kartu Mahasiswa · House Design (J1 Growing Habitat; J2 MERRHAUZ; J3 Umah Rintis); tab mahasiswa | https://btnhousingpreneur.com/kilas-balik | 1200×623 |
| `kilasbalik_2025_mahasiswa_housing_related_innovation.png` | Kartu Mahasiswa · HRI (J1 GeoFloodAI; J2 Jelanpaint; J3 MiBi-Tech 2.0); tab mahasiswa | https://btnhousingpreneur.com/kilas-balik | 1200×624 |
| `kilasbalik_2025_mahasiswa_rumah_nusantara.png` | Kartu Mahasiswa · Rumah Nusantara (J1 35 Degrees – Dhurung Argapana; J2 Abdihyang – ModuLego House 30); tab mahasiswa | https://btnhousingpreneur.com/kilas-balik | 1200×581 |
| `kilasbalik_2025_pemenang_tab_developer.png` | Seksi pemenang 2025, tab Developer & Pengusaha; tab developer | https://btnhousingpreneur.com/kilas-balik | 1366×3487 |
| `kilasbalik_2025_pemenang_tab_mahasiswa.png` | Seksi pemenang 2025, tab Mahasiswa (semua akordeon terbuka); tab mahasiswa | https://btnhousingpreneur.com/kilas-balik | 1366×2253 |
| `kilasbalik_2025_pemenang_tab_umum.png` | Seksi pemenang 2025, tab Umum (Non-Mahasiswa); tab umum | https://btnhousingpreneur.com/kilas-balik | 1366×2253 |
| `kilasbalik_2025_pencapaian_angka.png` | Pencapaian Program 2025: narasi jadwal + 1.171 submission / 746 / 181 / 58 finalis | https://btnhousingpreneur.com/kilas-balik | 1366×462 |
| `kilasbalik_2025_sinergi_01_rumah_pracetak_bandung.png` | Kartu sinergi: Rumah Pracetak Bandung – Rumah Rendah Emisi BTN | https://btnhousingpreneur.com/kilas-balik | 387×170 |
| `kilasbalik_2025_sinergi_02_habitatland.png` | Kartu sinergi: Habitatland – KPR BTN | https://btnhousingpreneur.com/kilas-balik | 388×170 |
| `kilasbalik_2025_sinergi_03_rawhaus.png` | Kartu sinergi: RAWHAUS – KPR Hijau, KPR BTN Tapera | https://btnhousingpreneur.com/kilas-balik | 387×170 |
| `kilasbalik_2025_sinergi_04_tanareka.png` | Kartu sinergi: TANAREKA – KPR | https://btnhousingpreneur.com/kilas-balik | 387×170 |
| `kilasbalik_2025_sinergi_05_autoconz_3d_printing.png` | Kartu sinergi: Autoconz (3D Printing) – KPR BTN | https://btnhousingpreneur.com/kilas-balik | 388×170 |
| `kilasbalik_2025_sinergi_06_pt_harmony_land_group.png` | Kartu sinergi: PT Harmony Land Group – Compact Harmony Living House (kawasan NPL) | https://btnhousingpreneur.com/kilas-balik | 387×170 |
| `kilasbalik_2025_sinergi_dengan_btn.png` | Seksi "Sinergi dengan BTN" (6 kartu) | https://btnhousingpreneur.com/kilas-balik | 1366×626 |
| `kilasbalik_2025_umum_house_design.png` | Kartu Umum · House Design (J1 Aparthouse; J2 Terra Griya; J3 KOTA[K] TUMBUH); tab umum | https://btnhousingpreneur.com/kilas-balik | 1200×623 |
| `kilasbalik_2025_umum_housing_related_innovation.png` | Kartu Umum · HRI (J1 Proteka; J2 myECO; J3 Co-housing koperasi); tab umum | https://btnhousingpreneur.com/kilas-balik | 1200×624 |
| `kilasbalik_2025_umum_rumah_nusantara.png` | Kartu Umum · Rumah Nusantara (J1 Groving House; J2 Rumah Kampung Kota); tab umum | https://btnhousingpreneur.com/kilas-balik | 1200×581 |
| `kilasbalik_2025_viewport_atas.png` | Tampilan pertama halaman Kilas Balik (Edisi 2025) | https://btnhousingpreneur.com/kilas-balik | 1366×900 |

### Beranda (resmi) (9 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `home_benefit.png` | Beranda: benefit (hadiah miliaran, inkubasi 3 bulan, dll.) | https://btnhousingpreneur.com/ | 1366×1040 |
| `home_foto_btn_expo_2026.png` | Foto Beranda: gerbang BTN Expo 2026 | https://btnhousingpreneur.com/frontend/images/home/2026/foto-btn-expo-2026.webp | 900×600 |
| `home_foto_grand_judging_2025.png` | Foto Beranda: panggung Grand Judging BTN Housingpreneur 2025 (Jan 2026) | https://btnhousingpreneur.com/frontend/images/home/2026/foto-grand-judging-2025.webp | 900×600 |
| `home_foto_kickstart_ui_2025.png` | Foto Beranda: Kick-start UI 2025 (audiens) | https://btnhousingpreneur.com/frontend/images/home/2026/foto-kickstart-ui-2025.webp | 900×600 |
| `home_foto_live_pitching_2025.png` | Foto Beranda: sesi Live Pitching 2025 (foto bersama di ruang rapat) | https://btnhousingpreneur.com/frontend/images/home/2026/foto-live-pitching-2025.webp | 900×600 |
| `home_foto_registrasi_kickstart_2025.png` | Foto Beranda: meja registrasi Kick-start 2025 | https://btnhousingpreneur.com/frontend/images/home/2026/foto-registrasi-kickstart-2025.webp | 900×600 |
| `home_hero.png` | Beranda: hero Batch 3 | https://btnhousingpreneur.com/ | 1366×900 |
| `home_jadwal.png` | Beranda: jadwal Batch 3 (konteks) | https://btnhousingpreneur.com/ | 1366×2830 |
| `home_kilas_balik_2025.png` | Beranda: seksi Kilas Balik 2025 (angka + kolase 5 foto) | https://btnhousingpreneur.com/ | 1366×1029 |

### Galeri (resmi) (11 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `galeri_album_01_roadshow_bandung_developer_pengusaha.png` | Galeri: album roadshow bandung developer pengusaha (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Bandung / Developer & Pengusaha | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_02_roadshow_bandung_mahasiswa_umum.png` | Galeri: album roadshow bandung mahasiswa umum (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Bandung / Mahasiswa & Umum | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_03_roadshow_jakarta_developer_pengusaha.png` | Galeri: album roadshow jakarta developer pengusaha (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Jakarta / Developer & Pengusaha | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_04_roadshow_jakarta_mahasiswa_umum.png` | Galeri: album roadshow jakarta mahasiswa umum (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Jakarta / Mahasiswa & Umum | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_05_roadshow_malang_developer_pengusaha.png` | Galeri: album roadshow malang developer pengusaha (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Malang / Developer & Pengusaha | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_06_roadshow_malang_mahasiswa_umum.png` | Galeri: album roadshow malang mahasiswa umum (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Malang / Mahasiswa & Umum | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_07_roadshow_semarang_mahasiswa_umum.png` | Galeri: album roadshow semarang mahasiswa umum (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Semarang / Mahasiswa & Umum | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_08_roadshow_semarang_developer_pengusaha.png` | Galeri: album roadshow semarang developer pengusaha (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Semarang / Developer & Pengusaha | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_09_roadshow_bali_mahasiswa_umum.png` | Galeri: album roadshow bali mahasiswa umum (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Bali / Mahasiswa & Umum | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_album_10_roadshow_bali_developer_pengusaha.png` | Galeri: album roadshow bali developer pengusaha (Batch 3, 2026; tidak memuat pemenang); filter: Roadshow Bali / Developer & Pengusaha | https://btnhousingpreneur.com/galeri | 1366×900 |
| `galeri_atas_filter_album.png` | Galeri: hero "Lihat Keseruan BTN Housingpreneur – 8 dokumentasi kegiatan, dari Kick-Start sampai Awarding" | https://btnhousingpreneur.com/galeri | 1366×900 |

### Berita (resmi) (11 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `news_2025-11-07_buka_akses_inovator_muda_judul.png` | Rilis resmi "Buka Akses Inovator Muda" (judul) | https://btnhousingpreneur.com/news/BTN-Housingpreneur-2025-Buka-Akses-Inovator-Muda-ke-Ekosistem-Perumahan-Nasional | 1366×900 |
| `news_2025-11-07_buka_akses_inovator_muda_kutipan_setiyo_bankable.png` | Kutipan Setiyo: "layak dibiayai perbankan", "bankable", inkubasi 3 bulan; bagian: "layak dibiayai perbankan" | https://btnhousingpreneur.com/news/BTN-Housingpreneur-2025-Buka-Akses-Inovator-Muda-ke-Ekosistem-Perumahan-Nasional | 1366×500 |
| `news_2025-11-07_kickstart_2025_alumni_plustik_pembicara.png` | Paragraf: Juara 2 HRI Value Chain 2024 (Plustik) & Ryan Tallulah sebagai pembicara; bagian: "Juara 2 BTN Housingpreneur 2024" | https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar | 1366×360 |
| `news_2025-11-07_kickstart_2025_judul.png` | Rilis resmi Kick Start 2025 (judul) | https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar | 1366×900 |
| `news_2025-11-07_kickstart_2025_komunitas_alumni.png` | Kutipan komunitas alumni ("bukan sekadar lomba, tapi sebuah movement"); bagian: "Kami juga membentuk komunitas alumni" | https://btnhousingpreneur.com/news/Cari-Bibit-Unggul-Inovator-Perumahan-Kick-Start-Kompetisi-BTN-Housingpreneur-2025-Resmi-Digelar | 1366×300 |
| `news_2026-01-08_pengumuman_lolos_seleksi_ide_judul.png` | Pengumuman peserta lolos seleksi ide 2025 (Live Pitching) | https://btnhousingpreneur.com/news/pengumuman-peserta-yang-lolos-seleksi-ide-bisnis-btnhp2025 | 1366×1300 |
| `news_2026-10-19_batch3_itb_bandung_judul.png` | Rilis Batch 3 ITB (judul) | https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-itb-bandung-inovasi-perumahan | 1366×900 |
| `news_2026-10-19_batch3_itb_bandung_rumah_rendah_emisi.png` | Paragraf Program Rumah Rendah Emisi: Rebrick, Plustik, Green Brick; bagian: "Program Rumah Rendah Emisi" | https://btnhousingpreneur.com/news/btn-housingpreneur-batch-3-itb-bandung-inovasi-perumahan | 1366×480 |
| `news_daftar_halaman_1.png` | Daftar Berita halaman 1 | https://btnhousingpreneur.com/news | 1200×400 |
| `news_daftar_halaman_2.png` | Daftar Berita halaman 2 | https://btnhousingpreneur.com/news | 1200×421 |
| `news_daftar_halaman_3.png` | Daftar Berita halaman 3 | https://btnhousingpreneur.com/news | 1200×421 |

### Media Batch 1 (Feb 2025; kick-off Nov 2024) (25 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `media_b1_2024-11-27_liputan6_kickoff_ugm_judul.png` | Judul, tanggal & foto utama artikel | https://www.liputan6.com/bisnis/read/5809203/btn-komitmen-lahirkan-wirausahawan-muda-begini-caranya | 1366×1100 |
| `media_b1_2025-02-15_sumselpos_daftar_pemenang_daftar_housingpreneur.png` | Daftar lengkap 20 pemenang BTN Housingpreneur Awards 2024/25; bagian: "Berikut daftar lengkap pemenang BTN Awards 2025" | https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/ | 1366×1150 |
| `media_b1_2025-02-15_sumselpos_daftar_pemenang_judul.png` | Judul, tanggal & foto utama artikel | https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/ | 1366×1100 |
| `media_b1_2025-02-15_sumselpos_daftar_pemenang_kutipan_ridwan_kamil.png` | Kutipan juri Ridwan Kamil; bagian: "Salah satu Dewan Juri Nasional" | https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/ | 1366×420 |
| `media_b1_2025-02-16_antara_pemerintah_dukung_judul.png` | Judul, tanggal & foto utama artikel | https://megapolitan.antaranews.com/berita/355285/pemerintah-dukung-ide-inovasi-berkelanjutan-bagi-pembangunan-rumah-rakyat | 1366×1100 |
| `media_b1_2025-02-16_investortrust_btn_awards_foto1.png` | Foto BTN Awards 2025: barisan penerima penghargaan di panggung; foto: 1739756753440 | https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah | 681×459 |
| `media_b1_2025-02-16_investortrust_btn_awards_foto2.png` | Foto BTN Awards 2025: penerima dengan trofi; foto: 1739756815370 | https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah | 429×303 |
| `media_b1_2025-02-16_investortrust_btn_awards_foto3.png` | Foto BTN Awards 2025: penyerahan trofi; foto: 1739756861518 | https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah | 429×302 |
| `media_b1_2025-02-16_investortrust_btn_awards_judul.png` | Judul, tanggal & foto utama artikel | https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah | 1366×1100 |
| `media_b1_2025-02-16_investortrust_btn_awards_kutipan_ridwan_kamil.png` | Kutipan Ridwan Kamil (Dewan Juri Nasional) + foto; bagian: "Salah satu Dewan Juri Nasional" | https://investortrust.id/financial/56805/btn-beri-apresiasi-penghargaan-ke-mitra-pengembang-desainer-dan-inovator-rumah | 1366×520 |
| `media_b1_2025-02-16_jpnn_btn_awards_judul.png` | Judul, tanggal & foto utama artikel | https://www.jpnn.com/news/btn-beri-apresiasi-para-mitra-pengembang-desainer-dan-inovator-rumah | 1366×1100 |
| `media_b1_2025-02-16_pasardana_400_inovasi_judul.png` | Judul, tanggal & foto utama artikel | https://pasardana.id/news/2025/2/16/bbtn-jaring-400-inovasi-perumahan | 1366×1100 |
| `media_b1_2025-02-19_investortrust_eco_green_living_foto1.png` | Foto panggung "BTN HOUSINGPRENEUR" Batch 1; papan Rumah Nusantara J2/J3 (Rp15 jt, Rp7,5 jt, Rp25 jt, Rp10 jt); foto: 1739951254636 | https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living | 681×452 |
| `media_b1_2025-02-19_investortrust_eco_green_living_foto2.png` | Foto kunjungan pejabat ke booth pameran BTN Awards 2025; foto: 1739951291592 | https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living | 429×292 |
| `media_b1_2025-02-19_investortrust_eco_green_living_foto3.png` | Foto penyerahan papan "JUARA 2" Batch 1 (pemenang berjaket putih); foto: 1739951358558 | https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living | 429×341 |
| `media_b1_2025-02-19_investortrust_eco_green_living_judul.png` | Judul, tanggal & foto utama artikel | https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living | 1366×1100 |
| `media_b1_2025-02-19_investortrust_eco_green_living_rusun_swadaya.png` | Paragraf Platform Rusun Swadaya (J1 HRI Business Ideation) + kutipan Anugerah; bagian: "Sebagai juara pertama inovasi terkait perumahan" | https://investortrust.id/financial/57120/btn-housingpreneur-dorong-kreativitas-dan-inovasi-bangun-eco-green-living | 1366×700 |
| `media_b1_2025-02-19_metrotv_batu_loncatan_foto1.png` | Foto artikel Metro TV (kunjungan pameran BTN Awards 2025); foto: a_67b5b96265086 | https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan | 702×490 |
| `media_b1_2025-02-19_metrotv_batu_loncatan_judul.png` | Judul, tanggal & foto utama artikel | https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan | 1366×1100 |
| `media_b1_2025-02_antara_ridwan_kamil_juri_judul.png` | Judul, tanggal & foto utama artikel | https://megapolitan.antaranews.com/berita/355041/ridwan-kamil-jadi-juri-400-inovasi-perumahan | 1366×1100 |
| `media_b1_2025-02_antara_ridwan_kamil_juri_kutipan_juri.png` | Kutipan Ridwan Kamil: apresiasi inovasi bisnis, desain, material ramah lingkungan; bagian: "Ridwan Kamil menjadi juri" | https://megapolitan.antaranews.com/berita/355041/ridwan-kamil-jadi-juri-400-inovasi-perumahan | 1366×700 |
| `media_b1_2025-02_kompasiana_autoconz_foto_grand_judging_menara_btn.png` | Foto Grand Judging Batch 1 (Menara BTN Harmoni, 13 Feb 2025): slide Autoconz "INSPIRATION – 12 juta keluarga Indonesia masih menunggu rumah yang layak" | https://assets.kompasiana.com/items/album/2025/02/20/dry02777-67b6ab09ed64151dc90fc522.jpg?t=o&v=770 | 770×513 |
| `media_b1_2025-02_kompasiana_autoconz_juri_judul.png` | Judul, tanggal & foto utama artikel | https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi | 1366×1100 |
| `media_b1_2025-02_kompasiana_autoconz_juri_juri_yu_sing.png` | Paragraf dewan juri Batch 1: Ridwan Kamil, Yu Sing (AKANOMA), perwakilan BTN, akademisi; bagian: "Yu Sing" | https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi | 1366×600 |
| `media_b1_2025-02_kontan_inovasi_ramah_lingkungan_judul.png` | Judul, tanggal & foto utama artikel | https://keuangan.kontan.co.id/news/btn-dorong-kemunculan-inovasi-pengembangan-perumahan-ramah-lingkungan | 1366×1100 |

### Media Batch 2 (Jan–Feb 2026) (23 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `media_b2_2026-01-29_detik_waste4change_booth_foto1.png` | Booth Waste4Change/Repair Project di BTN Expo 2026; foto: 1769676073646 | https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026 | 694×522 |
| `media_b2_2026-01-29_detik_waste4change_booth_foto2.png` | Produk papan daur ulang + kartu "made from low-value plastic waste"; foto: 1769676073723 | https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026 | 518×389 |
| `media_b2_2026-01-29_detik_waste4change_booth_foto3.png` | Meja papan daur ulang + brosur Repair Project; foto: 1769676073776 | https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026 | 518×389 |
| `media_b2_2026-01-29_detik_waste4change_booth_judul.png` | Judul, tanggal & foto utama artikel | https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026 | 1366×1100 |
| `media_b2_2026-01-29_metrotv_satu_ekosistem_judul.png` | Judul, tanggal & foto utama artikel | https://www.metrotvnews.com/read/kewCjz0V-btn-buka-akses-hunian-hingga-peluang-usaha-dalam-satu-ekosistem | 1366×1100 |
| `media_b2_2026-01-30_cnbc_expo_foto1.png` | Foto booth BTN Expo 2026 (CNBC); foto: btn-expo-2026-1769752118553 | https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan | 714×402 |
| `media_b2_2026-01-30_cnbc_expo_judul.png` | Judul, tanggal & foto utama artikel | https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan | 1366×1100 |
| `media_b2_2026-01-30_cnbc_expo_kutipan_setiyo_proptech.png` | Kutipan Setiyo: proptech, "di-scale up"; ringkasan alasan finalis; bagian: "proptech" | https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan | 1366×500 |
| `media_b2_2026-01-30_investortrust_limbah_ai_banjir_judul.png` | Judul, tanggal & foto utama artikel | https://investortrust.id/financial/93101/inovasi-rumah-berbasis-limbah-hingga-ai-mitigasi-banjir-jadi-sorotan-btn-expo-2026 | 1366×1100 |
| `media_b2_2026-01-30_investortrust_limbah_ai_banjir_kutipan_setiyo.png` | Kutipan Setiyo (versi Investortrust); bagian: "Kami mengumpulkan startup" | https://investortrust.id/financial/93101/inovasi-rumah-berbasis-limbah-hingga-ai-mitigasi-banjir-jadi-sorotan-btn-expo-2026 | 1366×520 |
| `media_b2_2026-01-30_monitorindonesia_expo_foto1.png` | Foto pengunjung di booth finalis (jaket btn housingpreneur); foto: dari-sampah-jadi-hunian | https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026 | 822×463 |
| `media_b2_2026-01-30_monitorindonesia_expo_judul.png` | Judul, tanggal & foto utama artikel | https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026 | 1366×1100 |
| `media_b2_2026-01-31_cnbc_awarding_hadiah_1_5_miliar.png` | Paragraf penyerahan hadiah Rp1,5 miliar, 58 finalis, 1.170 submission; bagian: "menyerahkan trofi dan hadiah" | https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan | 1366×300 |
| `media_b2_2026-01-31_cnbc_awarding_judul.png` | Judul, tanggal & foto utama artikel | https://www.cnbcindonesia.com/news/20260131195529-4-707003/btn-housingpreneur-2025-lahirkan-inovator-muda-ekosistem-perumahan | 1366×1100 |
| `media_b2_2026-01-31_industry_expo_tutup_judul.png` | Judul, tanggal & foto utama artikel | https://www.industry.co.id/read/147708/btn-expo-2026-tutup-gemilang-lahirkan-inovator-muda-penggerak-perumahan-nasional | 1366×1100 |
| `media_b2_2026-01-31_jpnn_awarding_judul.png` | Judul, tanggal & foto utama artikel | https://www.jpnn.com/news/awarding-btn-housingpreneur-2025tutup-rangkaian-btn-expo-2026 | 1366×1100 |
| `media_b2_2026-01-31_kontan_58_inovator_judul.png` | Judul, tanggal & foto utama artikel | https://keuangan.kontan.co.id/news/btn-housingpreneur-2025-lahirkan-58-inovator-muda-di-bidang-perumahan | 1366×1100 |
| `media_b2_2026-02_akurat_daftar_lengkap_daftar_pemenang.png` | Daftar pemenang 2025 versi Akurat; bagian: "Kategori Rumah Nusantara" | https://www.akurat.co/keuangan/1307137077/daftar-lengkap-pemenang-btn-housingpreneur-2025-57-inovator-muda-unjuk-solusi-hunian-masa-depan | 1366×2000 |
| `media_b2_2026-02_akurat_daftar_lengkap_judul.png` | Judul, tanggal & foto utama artikel | https://www.akurat.co/keuangan/1307137077/daftar-lengkap-pemenang-btn-housingpreneur-2025-57-inovator-muda-unjuk-solusi-hunian-masa-depan | 1366×1100 |
| `media_b2_2026-02_akurat_inovator_siap_foto1.png` | Foto awarding: seluruh pemenang dengan papan cek di panggung AWARDING; foto: BTN-Housingpreneur-2025-2173210465 | https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan | 620×349 |
| `media_b2_2026-02_akurat_inovator_siap_geofloodai.png` | Paragraf GeoFloodAI (aplikasi ML, user testing ±50 pengguna); bagian: "Inovasinya yang bernama GeofloodAI" | https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan | 1366×700 |
| `media_b2_2026-02_akurat_inovator_siap_judul.png` | Judul, tanggal & foto utama artikel | https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan | 1366×1100 |
| `media_b2_2026-02_akurat_inovator_siap_kutipan_juri_ryan_tallulah.png` | Kutipan juri Ryan Maurice Tallulah (BARDI): established business mengincar orderan developer BTN; bagian: "Ryan Maurice Tallulah, salah satu anggota Dewan Juri" | https://www.akurat.co/keuangan/1307143346/jadi-pemenang-btn-housingpreneur-2025-para-inovator-siap-dukung-sektor-perumahan | 1366×450 |

### YouTube (17 file)

| File | Isi | Sumber | Ukuran |
|---|---|---|---|
| `yt_b1_beritasatu_btn_awards_2025_thumbnail.png` | Thumbnail YouTube: "BTN Awards 2025, Dorong Karya Inovatif Arsitek Muda Berbakat – Beritasatu" (BeritaSatu) | https://i.ytimg.com/vi/q3bY7d2C8Io/hqdefault.jpg (video https://www.youtube.com/watch?v=q3bY7d2C8Io) | 480×360 |
| `yt_b1_inews_desain_rumah_nusantara_btn_awards_thumbnail.png` | Thumbnail YouTube: "Desain Rumah Nusantara, BTN Berikan Penghargaan Untuk Developer – iNews Pagi – 16/02" (Official iNews) | https://i.ytimg.com/vi/6UCwY5aLy3I/hqdefault.jpg (video https://www.youtube.com/watch?v=6UCwY5aLy3I) | 480×360 |
| `yt_b2_beritasatu_tutup_btn_expo_2026_thumbnail.png` | Thumbnail YouTube: "Sukses Tutup BTN Expo 2026, Anak Bangsa Tunjukkan Kreativitas dan Inovasi! #beritasatu" (BeritaSatu) | https://i.ytimg.com/vi/KLktVqaSxEI/hqdefault.jpg (video https://www.youtube.com/watch?v=KLktVqaSxEI) | 480×360 |
| `yt_b2_indonesia5_btn_expo_highlight_thumbnail.png` | Thumbnail YouTube: "[𝐁𝐓𝐍 𝐄𝐗𝐏𝐎 𝟐𝟎𝟐𝟔 𝐅𝐮𝐥𝐥 𝐇𝐢𝐠𝐡𝐥𝐢𝐠𝐡𝐭]" (Indonesia5) | https://i.ytimg.com/vi/Q1ohLtcn5-A/hqdefault.jpg (video https://www.youtube.com/watch?v=Q1ohLtcn5-A) | 480×360 |
| `yt_b2_kobill_finalist_pitching_thumbnail.png` | Thumbnail YouTube: "KoBill Finalist BTN HP 2025⁉️#smartstudent  #pitching #finalists #btn #2025" (Bill Cri Wi) | https://i.ytimg.com/vi/zW7afC4hWO0/hqdefault.jpg (video https://www.youtube.com/watch?v=zW7afC4hWO0) | 480×360 |
| `yt_b2_metrotv_ajang_talenta_muda_thumbnail.png` | Thumbnail YouTube: "BTN Housingpreneur 2025 Jadi Ajang Talenta Muda Wujudkan Mimpi Jadi Wirausaha Sukses" (METRO TV) | https://i.ytimg.com/vi/-MMRr0f6EMI/hqdefault.jpg (video https://www.youtube.com/watch?v=-MMRr0f6EMI) | 480×360 |
| `yt_b2_metrotv_btn_expo_dibuka_thumbnail.png` | Thumbnail YouTube: "Usung Tema "Build, Batle and Beat", BTN Expo 2026 Resmi Dibuka - [Selamat Pagi Indonesia]" (METRO TV) | https://i.ytimg.com/vi/FtZv2vYAqNU/hqdefault.jpg (video https://www.youtube.com/watch?v=FtZv2vYAqNU) | 480×360 |
| `yt_b2_metrotv_ekosistem_kolaboratif_thumbnail.png` | Thumbnail YouTube: "BTN Wujudkan Ekosistem Perumahan Kolaboratif Lewat Housingpreneur 2025" (METRO TV) | https://i.ytimg.com/vi/smrc8ZLqwMs/hqdefault.jpg (video https://www.youtube.com/watch?v=smrc8ZLqwMs) | 480×360 |
| `yt_b2_metrotv_intip_btn_expo_thumbnail.png` | Thumbnail YouTube: "Intip Keseruan BTN Expo 2026 yang Resmi Dibuka di Jakarta" (METRO TV) | https://i.ytimg.com/vi/RPnz-78--ig/hqdefault.jpg (video https://www.youtube.com/watch?v=RPnz-78--ig) | 480×360 |
| `yt_b2_metrotv_lahirkan_inovator_thumbnail.png` | Thumbnail YouTube: "BTN Housingpreneur Lahirkan Inovator Sektor Perumahan - [Metro Pagi Primetime]" (METRO TV) | https://i.ytimg.com/vi/aYWcI36jW6o/hqdefault.jpg (video https://www.youtube.com/watch?v=aYWcI36jW6o) | 480×360 |
| `yt_b2_tvone_awarding_btn_housingpreneur_2025_thumbnail.png` | Thumbnail YouTube: "Awarding BTN Housing Preneur 2025 – Kabar Siang" (tvOneNews) | https://i.ytimg.com/vi/OXKC6jppGfg/hqdefault.jpg (video https://www.youtube.com/watch?v=OXKC6jppGfg) | 480×360 |
| `yt_b2_tvone_lahirkan_inovator_thumbnail.png` | Thumbnail YouTube: "BTN Housing Preneur 2025 Lahirkan Inovator Sektor Perumahan – Kabar Siang" (tvOneNews) | https://i.ytimg.com/vi/S7EWjaK6xZw/hqdefault.jpg (video https://www.youtube.com/watch?v=S7EWjaK6xZw) | 480×360 |
| `yt_b2_viva_hadiah_miliaran_kickoff_thumbnail.png` | Thumbnail YouTube: "Dukung Wirausaha Muda, BTN Tawarkan Hadiah Miliaran Rupiah" (VIVA.CO.ID) | https://i.ytimg.com/vi/PtztBc96MDk/hqdefault.jpg (video https://www.youtube.com/watch?v=PtztBc96MDk) | 480×360 |
| `yt_b2_viva_inovasi_perumahan_2025_thumbnail.png` | Thumbnail YouTube: "Mendukung Program Prabowo, Inovasi Perumahan lewat Housingpreneur 2025" (VIVA.CO.ID) | https://i.ytimg.com/vi/tT1mjC_ldj8/hqdefault.jpg (video https://www.youtube.com/watch?v=tT1mjC_ldj8) | 480×360 |
| `yt_hasil_pencarian_btn_awards_2025.png` | Hasil pencarian YouTube "BTN Awards 2025 housingpreneur" | https://www.youtube.com/results?search_query=BTN+Awards+2025+housingpreneur | 1366×3200 |
| `yt_hasil_pencarian_btn_housingpreneur.png` | Hasil pencarian YouTube "BTN Housingpreneur" | https://www.youtube.com/results?search_query=BTN+Housingpreneur | 1366×3200 |
| `yt_hasil_pencarian_btn_housingpreneur_awarding.png` | Hasil pencarian YouTube "BTN Housingpreneur 2025 awarding" (judul, kanal, tayangan, thumbnail) | https://www.youtube.com/results?search_query=BTN+Housingpreneur+2025+awarding | 1366×3200 |
