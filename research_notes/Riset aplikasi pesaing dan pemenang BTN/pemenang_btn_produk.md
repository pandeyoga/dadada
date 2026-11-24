# Produk pemenang dan finalis BTN Housingpreneur Batch 1 (2024) dan Batch 2 (2025): apa yang menang, terutama aplikasi/platform digital, dan relevansinya untuk Estora

Diambil 2026-11-24. Melanjutkan bagian 4 `Riset kompetitor dan BTN Housingpreneur/btn_housingpreneur_detail.md` (daftar pemenang tidak diulang lengkap; yang ditambahkan di sini adalah **isi produknya**). Halaman dirender dengan Chromium/Playwright, Play Store dibaca dari halaman listing publik, dan pencarian App Store memakai endpoint publik iTunes Search. Tidak ada login, pendaftaran, atau API privat.

Konvensi:
- "Cited Findings" berisi fakta bersumber (URL, plus tanggal terbit atau tanggal akses).
- **[ringkasan pencarian]** berarti fakta hanya berasal dari ringkasan mesin pencari karena halaman sumber tidak bisa dibuka atau tidak teridentifikasi. Perlakukan sebagai belum terverifikasi.
- "Inferences" berisi penilaian saya, termasuk rating relevansi untuk Estora (Tinggi/Sedang/Rendah).

Pemetaan kategori antar-batch (dari catatan sebelumnya): HRI–Established (Technology) 2024 → House Technology Innovation 2025 → Housing Tech 2026; HRI–Established (Value Chain) 2024 → House Value Chain Innovation 2025 → Housing Ecosystem 2026.

---

## 1. Batch 1 (2024, awarding 15 Feb 2025): produk apa yang dimenangkan?

### Takeaway
Kategori Technology 2024 dimenangi dua **layanan digital yang menempel pada layanan fisik**, lalu satu hardware:
- **Juara 1 CIROES**: aplikasi bank sampah/marketplace daur ulang plus penjemputan sampah, Balikpapan. Android, 5 rb+ unduhan.
- **Juara 2 Paktukang.com**: platform jasa tukang, renovasi, dan bangun rumah dengan RAB transparan, survei, monitoring progres, dan skema cicilan/kredit. Web + WhatsApp, Surabaya/Malang.
- **Juara 3 PT Berdikari Teknologi Indonesia (Autoconz)**: mesin dan mortar 3D Construction Printing.

Juara 1 Business Ideation adalah **Platform Rusun Swadaya**, platform komunitas yang menyalurkan pembiayaan BTN. Pemenang lain berupa developer (Habitatland, Prosya Bangun, dan lainnya) atau material (Plustik). Isi produk PT Dua Mitra Gemilang (Juara 1 Value Chain) tidak ditemukan. Tidak satu pun pemenang 2024 adalah software back-office untuk developer.

### Cited Findings

**Daftar resmi dan konteks penjurian Batch 1**
- Daftar lengkap HRI 2024:
  - Value Chain: J1 PT Dua Mitra Gemilang – Tan Novita; J2 PT Plustik Maju Bersama – Reza Hasfinanda.
  - Technology: J1 PT Inovasi Keberlanjutan Indonesia (CIROES) – Sandy Wijaya; J2 Paktukang Teknologi Karya Global – Moh. Rozaqul Anam; J3 PT Berdikari Teknologi Indonesia – Antonius Ali.
  - Business Ideation: J1 Anugerah Nurrewa; J2 Yoval Julianto.

  Housingpreneur Awards diberikan kepada "20 pemenang dari empat kategori berbeda, yang dipilih dari 946 tim peserta". Juri Ridwan Kamil: "Dari 400 inovasi yang masuk, para juri memilih yang terbaik". Daftar ini dari media berita, bukan lagi hanya agregator seperti dicatat sebelumnya. — [Sumsel Pos, liputan BTN Awards 15 Feb 2025](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/)
- Grand Judging Batch 1 digelar 13 Feb 2025 di Menara BTN Harmoni. Dewan juri: Ridwan Kamil, Yu Sing (Founder AKANOMA), perwakilan BTN, dan akademisi properti. — [Kompasiana akun Autoconz, 15 Feb 2025 (konten pengguna)](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi); dikonfirmasi [Habitatland (rilis, 17 Feb 2025)](https://habitatland.id/raih-juara-dalam-kompetisi-btn-housingpreneur-2025-habitatland-resmi-masuk-jaringan-pengembang-properti-berkelanjutan/)
- Dirut BTN di BTN Awards 2025 menyoroti "produk batu bata dan floor deck berbasis sampah plastik" dan menyebut BTN Awards sebagai ajang "mempertemukan developer dengan para inovator di bidang desain dan material perumahan". — [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/)

**CIROES – PT Inovasi Keberlanjutan Indonesia (Juara 1 Technology 2024)**
- Kategori: **aplikasi mobile + layanan fisik** (penjemputan sampah, bank sampah "Cistore", TPST).
- Deskripsi Play Store: "Ciroes merupakan aplikasi yang dapat membantu kamu mendapatkan penghasilan tambahan dengan cara menjual sampah ke Bank Sampah (Cistore) terdekat." Tagline "Pahlawan Circular Economy".
  - Metrik: rating 4,3 (48 ulasan), **5 rb+ unduhan**, kategori Gaya Hidup, terakhir diperbarui **4 Sep 2025** (catatan rilis "Perbaikan bug reset password").
  - Ulasan publik: keluhan login/daftar akun (29 Jun 2026), "hanya tersedia di Kalsel" (13 Jun 2025), dan keluhan timbangan di admin Balikpapan (26 Okt 2024).
  - Developer "Ciro Waste", situs cirowaste.com.

  — [Google Play: Ciroes](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp) (diakses 2026-11-24)
- Fitur dan alur yang terlihat di screenshot resmi Play Store:
  - Beranda: "Total Saldo" + tombol "Tarik Saldo"; menu "Cistore Terdekat", "Langganan", "Layanan Spesifik", "Layanan B3"; artikel edukasi; banner "Kami Ciroes siap menjemput sampah terpilah Anda dengan terjadwal setiap hari".
  - Peta "Cistore Terdekat" dengan tombol "Tunjukkan Arah", dibingkai sebagai "Bank Sampah Digital".
  - Alur jual: "Kumpulkan, Pilah dan Order" → layar "Pilih Sampah" per jenis dengan harga per kg (contoh: Kardus Rp1.000/kg, Gelas PP Bening Rp1.500/kg) → "Total Estimasi Penjualan" → tombol "Jemput". Ada pesan bila jumlah belum mencukupi untuk dijemput ("Ayo setor sampah ke Cistore terdekat").
  - Fitur "Langganan": "Setor sampah dari rumah" secara berkala.
  - Materi promosi memuat badge App Store, tetapi aplikasi iOS tidak ditemukan (lihat butir berikut).

  — [Google Play: Ciroes, screenshot](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp); file lokal di bagian 4.
- Situs resmi:
  - Ciro Waste adalah "circular economy marketplace yang menghubungkan penjual dan pembeli sampah daur ulang".
  - Klaim "Puluhan perusahaan di Indonesia telah memakai jasa Ciro Waste".
  - Fitur: lacak dan kelola sampah sebelum dikirim ke bank sampah, komunitas, edukasi; liputan TVRI.
  - Alamat Balikpapan Selatan; footer "© 2026 PT. Inovasi Keberlanjutan Indonesia".

  — [cirowaste.com](https://www.cirowaste.com) (diakses 2026-11-24)
- Studi Telkom University: Ciro Waste mengembangkan dua aplikasi, CIROES (warga) dan CISTORE ("Bank Sampah Masa Kini"). Studi menyimpulkan aplikasi ini berkontribusi signifikan pada pengelolaan sampah di Balikpapan. Sandy Wijaya disebut CEO. **[ringkasan pencarian]** — [Telkom University Open Library](https://openlibrary.telkomuniversity.ac.id/pustaka/files/218539/bab1/evaluasi-sistem-pengelolaan-sampah-berbasis-aplikasi-ciro-waste-dalam-konteks-sdg-11-6-di-kota-balikpapan-dalam-bentuk-buku-karya-ilmiah.pdf)
- Tidak ditemukan aplikasi iOS (pencarian iTunes "ciroes" dan "ciro waste", country=id, tanpa hasil relevan). — [iTunes Search API](https://itunes.apple.com/search?term=ciroes&country=id&entity=software)
- Pasca-kompetisi: Kilas Balik mencatat kolaborasi **CIROES × Paktukang.com** di klaster "Pengelolaan Perumahan & Digitalisasi", berupa "kerja sama dalam pengembangan **manajemen IPL** dan pelatihan digital marketing properti". — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)
- Model bisnis (dari situs dan app): jasa pengumpulan sampah untuk perusahaan, layanan "Langganan" dan "Layanan B3", serta selisih jual-beli di marketplace daur ulang. Harga tidak dipublikasikan. — [cirowaste.com](https://www.cirowaste.com); [Google Play](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp)

**Paktukang.com – PT Paktukang Teknologi Karya Global (Juara 2 Technology 2024)**
- Kategori: **platform web jasa konstruksi/renovasi (marketplace tukang terkurasi) + layanan kontraktor**. Pemesanan lewat konsultasi CS/WhatsApp. Tidak ditemukan aplikasi di Play Store maupun App Store.
- Layanan: Renovasi, Bangun Rumah ("desain, perencanaan, pengerjaan, hingga perizinan"), atap/plafon, cat, listrik, service AC, interior & kitchen set, pagar/kanopi, sanitasi & gas, perbaikan kecil.
- Alur pemesanan 4 langkah: (1) konsultasi kebutuhan ke CS → (2) jadwalkan survei → (3) "Perhitungan RAB: estimasi … jasa dan material terpisah secara transparan", dengan pilihan jasa+material atau jasa saja → (4) eksekusi.
- Metrik di beranda: "658+ pekerjaan diselesaikan, 76+ partner & supplier lokal, 158+ mitra tukang berdaya, 4321+ konsultasi budget". Ada menu "Gabung Mitra Tukang"; portofolio di Surabaya dan Malang; alamat Surabaya.

— [paktukang.com](https://paktukang.com/) (diakses 2026-11-24)
- Rekap 2025 (blog, 29 Des 2025):
  - "Konsultasi 2061 orang", "Membantu renovasi 91 rumah", "Realisasi Kredit Bangun & Renovasi Rumah di Kota Malang & Surabaya", "**Juara 2 BTN Housingpreneur**", "158 tukang terampil", "92 supplier lokal".
  - Layanan pembiayaan: "Bangun rumah dengan **kredit multiguna**".
  - Pengawasan proyek: "Monitoring Real-Time: … progres proyek dilaporkan secara berkala".
  - Tagline footer: "memudahkan Anda membangun, mengelola, mengawasi, dan mengamankan segala macam kebutuhan proyek".

  — [Paktukang blog, 29 Des 2025](https://paktukang.com/blog/menuju-hunian-impian-catatan-perjalanan-paktukang-di-tahun-2025/)
- Skema B2B2C (blog, 4 Okt 2024): "Program Layanan Konstruksi Bagi Karyawan", berupa renovasi/bangun rumah dengan "cicilan hingga 15 tahun tanpa agunan dan tanpa DP" bagi karyawan swasta, PPPK, dan PNS. Dijual ke perusahaan sebagai benefit karyawan lewat audiensi. Lembaga pembiayaannya tidak disebut. — [Paktukang blog, 4 Okt 2024](https://paktukang.com/blog/jasa-kontraktor-bangun-rumah-bisa-dicicil-1-j/)
- Pasca-kompetisi: kolaborasi dengan CIROES (manajemen IPL dan digital marketing properti). — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik). Kerja sama pembiayaan spesifik dengan BTN tidak ditemukan; blog hanya menyebut "kredit multiguna" tanpa nama bank.

**PT Berdikari Teknologi Indonesia / Autoconz (Juara 3 Technology 2024)**
- Kategori: **hardware konstruksi (3D Construction Printing, 3DCP) + mortar**. Antonius Ali tampil sebagai "Perwakilan Autoconz" yang meraih posisi ketiga HRI–Established (Technology). Teknologinya disebut "mempercepat pembangunan perumahan, meningkatkan efisiensi konstruksi … mengurangi limbah". — [Kompasiana akun Autoconz, 15 Feb 2025](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi)
- Rumah pilot tipe 36 hasil 3D printing di Turi, Sleman, dirujuk sebagai karya "Autoconz dan PT Berdikari Teknologi Indonesia (2022)". **[ringkasan pencarian]** — [Prosiding SIAR UMS](https://proceedings.ums.ac.id/siar/article/download/7180/6522/13696). Judul artikel terkait di akun yang sama: mortar Autoconz meraih sertifikasi TKDN 68,29%. — [Kompasiana Autoconz (daftar artikel)](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi)
- Sinergi BTN: Kilas Balik mencatat "Autoconz (3D Printing) – KPR BTN: Kolaborasi pembangunan rumah 3D dengan skema KPR BTN" dan kolaborasi "PT Berdikari × Rebricks + Kometa" (sampah menjadi material 3DCP). — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)

**Platform Rusun Swadaya – Anugerah Nurrewa (Juara 1 HRI Business Ideation 2024)**
- Kategori: **konsep platform komunitas + pembiayaan**. Platform menghimpun komunitas untuk membangun rusun swadaya di pusat kota dekat transportasi umum, sehingga komunitas "bisa mendapat akses pembiayaan dari BTN". Platform berperan sebagai "fasilitator pembiayaan dengan risiko yang minim … karena berbasis komunitas". Dikembangkan bersama dua mitra dari startup mobility. — [Metro TV, 19 Feb 2025](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan); [Kontan, Feb 2025](https://keuangan.kontan.co.id/news/btn-dorong-kemunculan-inovasi-pengembangan-perumahan-ramah-lingkungan) (dikutip dari catatan sebelumnya)
- Tidak ditemukan situs, aplikasi, maupun kelanjutan publik setelah kompetisi.

**PT Dua Mitra Gemilang – Tan Novita (Juara 1 HRI Value Chain 2024)**
- Hanya nama perusahaan dan nama perwakilan yang terverifikasi. — [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/). **Deskripsi produk tidak ditemukan.** Pencarian nama perusahaan + material/produk tidak memberi hasil relevan.

**Habitatland – PT Habitat Tempat Hidup (Best Eco House Development 2024)**
- Kategori: **developer perumahan eco-house** (Gunung Batu, Kota Bogor), bukan produk digital.
- Fitur hijau: sumur resapan/biopori, bio paving block (20% sampah), maggot untuk sampah organik, bio septic tank, bonus Water RO per rumah. Klaim hemat 240 galon/tahun (≈Rp5 juta).
- Rilis pemilik (Ryan Adam): menang "dari 946 peserta".

— [Habitatland, rilis 17 Feb 2025](https://habitatland.id/raih-juara-dalam-kompetisi-btn-housingpreneur-2025-habitatland-resmi-masuk-jaringan-pengembang-properti-berkelanjutan/)
- Aset digital di situs: halaman "Simulasi KPR" dan "Kelas online yang akan membantu kamu dalam memilih rumah dan memulai bisnis properti". — [habitatland.id](https://habitatland.id/) (diakses 2026-11-24)
- Sinergi BTN: "Kerja sama melalui skema KPR BTN". Kolaborasi dengan Rebricks (material) dan PT Prosya Bangun (klaster IPL/digital marketing). — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)

**PT Prosya Bangun Indonesia – Nurul Aini (Inspiring Sharia Project 2024)**
- Kategori: **developer perumahan syariah** (kategori Landed Residential). — [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/)
- Pasca-kompetisi:
  - "PT Prosya × Pak Adjie + Damare Design + Rumah Pracetak", berupa "Kolaborasi untuk mempertemukan investor potensial dengan Prosya dan pembelajaran mendesain hotel".
  - "PT Prosya Bangun × Habitatland" di klaster IPL/digital marketing.

  — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik). Proyek dan produk spesifiknya tidak ditemukan.

**Pemenang 2024 lain (klasifikasi singkat, non-digital)**
- PT Plustik Maju Bersama (J2 Value Chain): material dari sampah plastik, masuk Program Rumah Rendah Emisi BTN (catatan sebelumnya).
- PT Sembilan Bintang Lestari dan PT Kreasi Prima Nusantara: developer.
- PT Harmony Land Group: desain eco house.
- Bramana Anjasmara Putra, Rampak Huni, Uma Lamo, dan lainnya: desain.

— [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/)

### Inferences
- **Rating relevansi untuk Estora (Batch 1):**

| Produk | Kategori produk | Relevansi | Alasan singkat |
|---|---|---|---|
| CIROES | Aplikasi Android + layanan fisik (bank sampah) | **Sedang** | Fungsinya beda, tapi ini preseden terkuat: aplikasi dengan pengguna nyata menang Juara 1 Tech, dan dikaitkan dengan "manajemen IPL" (purna jual/estate) |
| Paktukang.com | Platform web jasa konstruksi + RAB + progres + kredit | **Sedang** | Bersinggungan dengan modul progres konstruksi, RAB, garansi/perbaikan, dan pembiayaan Estora, tetapi B2C/kontraktor, bukan OS developer |
| Berdikari/Autoconz | Hardware 3DCP | Rendah | Teknologi konstruksi fisik |
| Platform Rusun Swadaya | Konsep platform komunitas → pembiayaan BTN | **Sedang** | Menunjukkan juri menyukai platform sebagai *saluran nasabah pembiayaan BTN* |
| PT Dua Mitra Gemilang | Tidak diketahui | Tidak dapat dinilai | Deskripsi produk tidak ditemukan |
| Habitatland | Developer eco-house | Rendah (sebagai produk) | Tipe calon pengguna Estora: developer kecil pemenang, pakai KPR BTN, situs dengan simulasi KPR |
| Prosya Bangun | Developer syariah | Rendah (sebagai produk) | Calon pengguna; segmen syariah butuh skema bayar non-KPR/in-house |

- Kategori Technology 2024 dimenangi **produk yang ada pengguna dan operasinya**, bukan prototipe: CIROES (5 rb+ unduhan, jasa ke perusahaan), Paktukang (ratusan pekerjaan, ribuan konsultasi), Autoconz (rumah pilot). Software murni tanpa layanan fisik belum ada di daftar pemenang.
- Kolaborasi CIROES × Paktukang soal **manajemen IPL** adalah satu-satunya jejak "software operasional perumahan" di dua batch. Ini area yang bersinggungan dengan modul purna jual Estora dan juga peluang kolaborasi (Estora sebagai sistem developer, CIROES/Paktukang sebagai layanan estate/perbaikan).

### Gaps
- Isi produk PT Dua Mitra Gemilang (Juara 1 Value Chain 2024) tidak ditemukan.
- Tidak ada metrik pengguna aktif CIROES selain jumlah unduhan Play Store. Cakupan wilayah aktual tidak jelas (ulasan menyebut Kalsel; situs di Balikpapan).
- Mitra pembiayaan "kredit multiguna"/cicilan 15 tahun Paktukang tidak disebut, sehingga tidak jelas apakah BTN.
- Platform Rusun Swadaya: tidak ada situs, prototipe, atau tindak lanjut publik.

---

## 2. Batch 2 (2025, awarding 31 Jan 2026): produk apa yang dimenangkan, dan finalis digital mana yang tampil?

### Takeaway
"House Technology Innovation" 2025 dimenangi:
- **J1 TRAIN-O (PRANA)**: platform digital pelatihan + VR + sertifikasi + penempatan kerja untuk tenaga konstruksi; 4.324 orang terlatih pada 2024.
- **J2 AITOMA (Hayago Robotika)**: IoT + AI + aplikasi untuk penghematan listrik rumah dan kawasan.
- **J3 RUMAH GOKILS (GoodKills/Mercusuar Agresif Perkasa)**: jasa pengendalian hama/anti rayap sebagai "sistem perlindungan hunian".

"House Value Chain Innovation" dimenangi:
- **Parongpong RAW Lab**: material dari sampah residu.
- **RR Board (Waste4Change/Repair Project)**: papan dan atap dari sampah Sungai Citarum.
- **KPR Energy (GridSolr)**: kepemilikan panel surya untuk pemilik rumah baru yang dikaitkan dengan KPR.

Di Business Ideation:
- GeoFloodAI: AI risiko banjir untuk perencanaan.
- myECO: kemungkinan besar startup IoT penghemat listrik asal Malang.
- Proteka: pelapis tahan gempa.

Finalis digital yang paling relevan adalah **Ontoown**, aplikasi rent-to-own (sewa → tabungan DP → KPR). Tidak ada pemenang atau finalis yang terlihat berupa software operasional developer.

### Cited Findings

**Daftar resmi**: lihat catatan sebelumnya. Dikonfirmasi ulang dari HTML tab Kilas Balik (2026-11-24), yang juga memuat kategori Business Ideation Umum dan Developer:
- Umum HRI: J1 PT Inovasi Tangguh Bencana – Proteka; J2 Maulana Derifato Achmad – myECO; J3 Anindya Dhiracitta – Model Co-housing Skema Koperasi Perumahan Kolektif.
- Mahasiswa HRI: J1 GeoFloodAI; J2 Jelanpaint; J3 MiBi-Tech 2.0.

— [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)

**TRAIN-O – PRANA TECH (Juara 1 House Technology Innovation 2025)**
- Kategori: **platform digital pelatihan dan sertifikasi tenaga kerja konstruksi** (mobile learning + simulasi VR).
- Masalah yang diangkat: "Indonesia kekurangan 8,3 hingga 9 juta tenaga aplikator konstruksi yang terampil" (data 2023).
- Alur: "verifikasi awal, pelatihan via mobile learning dan simulasi Virtual Reality (VR), hingga sertifikasi resmi dan penempatan kerja", selaras dengan Building Code nasional.
- Traksi: "3.500 tenaga kerja terlatih (2022), 3.569 orang (2023), dan 4.324 orang (2024)".
- Mitra: BLK, SMK, BNSP, serta mitra Australia dan Jepang.
- Tim: Founder Elisa Haryonugroho; Co-founder Rizqi Putra Satiadi.
- PRANA juga mengembangkan **MODULA** (rumah modular precast, siap huni 7 hari, limbah turun hingga 70%, konsep "rumah tumbuh", kompatibel dengan enam domain industri prefab).

— [Kitabaru, 3 Feb 2026](https://kitabaru.com/train-o-dan-modula-dua-inovasi-digital-jawab-tantangan-krusial-konstruksi-indonesia/)
- Indoposco (3 Feb 2026) menulis "TRAIN-O (Peringkat I – Kategori SDM & Digital)" dan "MODULA oleh PRANA (Peringkat I – Kategori Teknologi Konstruksi)". Angkanya "58 inovator terpilih dari total 8.000 lebih pendaftar", "telah melatih lebih dari 4.000 tenaga kerja pada tahun 2024". — [Indoposco, 3 Feb 2026](https://indoposco.id/2026/02/03/sabet-peringkat-pertama-train-o-dan-modula-ungguli-58-inovator-di-btn-expo-2026/). **Konflik:** daftar resmi hanya mencantumkan "PRANA TECH – TRAIN-O" sebagai Juara 1 House Technology Innovation. Tidak ada kategori "SDM & Digital" atau "Teknologi Konstruksi", dan MODULA tidak tercantum. — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik). Kedua artikel tampak berasal dari rilis pihak PRANA.
- Platform/aplikasi: tidak ditemukan situs resmi, aplikasi Play Store, atau App Store dengan nama TRAIN-O (pencarian publik; trainoid.com berstatus domain dijual). Model bisnis dan harga tidak dipublikasikan.
- Sinergi BTN pasca-menang: tidak ditemukan.

**AITOMA – PT Hayago Robotika Indonesia (Juara 2 House Technology Innovation 2025)**
- Kategori: **IoT hardware + aplikasi cloud dengan analitik AI** ("Smart Home Energy Solution").
- Perangkat: (1) stopkontak pintar untuk memantau perangkat berat (AC, kulkas, pompa air); (2) sensor panel listrik untuk satu rumah "maupun kawasan perumahan multi-unit".
- Aplikasi ponsel menampilkan pola konsumsi harian/bulanan, "proyeksi biaya listrik ke depan", dan mendeteksi perangkat boros. Klaim penghematan "hingga 40 persen". Sistem disebut "non-intrusive, mudah dipasang, dan fleksibel diterapkan mulai dari satu rumah hingga kawasan perumahan".
- CEO Muhammad Hariz Izzuddin (Lamongan).

— [Beritajatim, 18 Feb 2026](https://beritajatim.com/inovasi-ai-pemuda-lamongan-sabet-juara-nasional-di-btn-housing-preneur-2026)
- Tidak ditemukan aplikasi AITOMA di App Store (iTunes Search) maupun Play Store (pencarian publik). Traksi, harga, dan sinergi BTN tidak ditemukan.

**RUMAH GOKILS – PT Mercusuar Agresif Perkasa (Juara 3 House Technology Innovation 2025)**
- Perusahaan: PT Mercusuar Agresif Perkasa beroperasi dengan merek **GoodKills**, layanan home cleaning dan pest control (rumah dan apartemen) di Surabaya, juga outsourcing. Ukuran 51–200 karyawan; lowongan teknisi pest control, cleaning, dan "Sales Project". **[ringkasan pencarian]** (halaman Glints memblokir akses otomatis) — [Glints: GoodKills](https://glints.com/id/companies/pt-mercusuar-agresif-perkasa-goodkills/54e24f27-f12f-4631-a00a-9de5907eaec3); [KitaLulus](https://www.kitalulus.com/company/pt-mercusuar-agresif-perkasa-nrwe); [companieshouse.id](https://companieshouse.id/mercusuar-agresif-perkasa)
- Isi produk RUMAH GOKILS menurut ringkasan mesin pencari:
  - Berdiri 2020, dirintis Adhit(ya Chandra) dan Deny Kristanto Yudianto dengan modal sekitar Rp4 juta.
  - Goodkills disebut "tak hanya sekedar manajemen pengendalian hama tetapi juga sebuah sistem perlindungan hunian yang modern" dengan konsep *one health*, insektisida dari mitra Jerman, aman bagi manusia dan hewan peliharaan.

  **[ringkasan pencarian; artikel sumber tidak teridentifikasi/terbuka]** — dikaitkan dengan [Tempo, info-tempo](https://www.tempo.co/info-tempo/btn-housingpreneur-bangun-ekosistem-hunian-inovatif-2132063) (HTTP 403 saat diakses).
- goodkills.id ada, tetapi menampilkan halaman verifikasi bot saat dirender. Tidak ditemukan aplikasi di Play Store.

**Parongpong RAW Lab – PT Raesaka Amanah Widyakarya (Juara 1 House Value Chain 2025)**
- Kategori: **material** (waste-to-material dari sampah residu non-plastik).
- Produk "**Oriplast**" dibuat dari karung semen sebagai "pengganti decking kayu". Bahan baku lain: jaring nelayan bekas, puntung rokok, cangkang kerang. Melibatkan keluarga nelayan pesisir. Program Manager: Kendan Maranatha.

— [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026)

**RR Board – PT Wasteforchange Alam Indonesia (Juara 2 House Value Chain 2025)**
- Kategori: **material daur ulang**.
- Waste4Change, lewat unit bisnis **Repair Project** (joint operation dengan **River Recycle**), mengambil sampah dari Sungai Citarum dan mengolahnya menjadi "papan daur ulang". Dari papan itu dibuat furnitur. Untuk perumahan, yang ditawarkan adalah "roofing atau atap dari sampah".
- Kutipan Commercial Lead Carissa Eukairin (28 Jan 2026): "Makanya kita ke BTN ini supaya bisa mencoba ke yang lebih besar … Kami bertemu dengan banyak kontraktor, arsitek, hingga developer."

— [detikProperti, Jan 2026](https://www.detik.com/properti/berita/d-8331311/waste4change-bawa-atap-rumah-dari-sampah-ke-btn-expo-2026)
- Bahwa "RR" berarti Repair/River Recycle adalah inferensi saya dari artikel ini; tidak ada sumber yang mengeja kepanjangannya.

**KPR Energy – PT Andalusia Intra Teknologi / GRIDSOLR (Juara 3 House Value Chain 2025)**
- Kategori: **energi (PLTS atap hybrid) + skema pembiayaan terkait KPR**.
- Situs GridSolr menulis: "Juara 3 kategori House Value Chain untuk inovasi **KPR Energy** yang memudahkan kepemilikan panel surya bagi pemilik hunian baru".
- Produk:
  - "Paket Kemandirian Energi 4700 WattPeak" ("pilihan utama bagi 80% pelanggan kami").
  - Konsep DIY-assisted (pelanggan ikut desain; tim ahli memasang dan menyertifikasi).
  - "BOM (Bill of Materials) terbuka" (merek, harga, spesifikasi transparan).
  - Klaim "ROI dalam 4-5 tahun", "garansi performa panel 25 tahun", baterai dirakit lokal.
  - "Monitoring real-time yang dapat diakses dari mana saja".
  - Badge "3rd Winner BTNHousingPreneur 2025".

  — [gridsolr.com](https://gridsolr.com/) (diakses 2026-11-24)
- Direktur PT Andalusia Intra Teknologi (GridSolr) Hamdan Wahyudi, "peraih Juara 3 BTN Housingpreneur 2025", menjadi pembicara Inspiration Talk Roadshow Batch 3 di Semarang. Ini berarti alumni dilibatkan kembali oleh BTN. — [Aktual, 21 Okt 2026](https://aktual.com/btn-housingpreneur-hadir-di-semarang-bedah-inovasi-rumah-zaman-now/); [JabarPos, 20 Okt 2026](https://www.jabarpos.com/finance/208149/hadir-di-semarang-btn-housingpreneur-bedah-rumah-zaman-now/)
- Mekanisme "KPR Energy" (apakah biaya PLTS dimasukkan ke plafon KPR, kredit tambahan, atau cicilan terpisah) tidak dijelaskan di sumber publik.

**GeoFloodAI (Juara 1 HRI Business Ideation Mahasiswa 2025)**
- Kategori: **AI/geospasial (konsep/prototipe)**. Asal Palembang. Teknologi AI "untuk memetakan risiko banjir dan karakter lahan sejak tahap perencanaan, sehingga desain hunian dapat disesuaikan dengan kondisi iklim dan wilayah". — [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026); [digitalbank.id](https://www.digitalbank.id/digi-news/77674638/ajang-btn-expo-2026-ditutup-cetak-housingpreneur-muda-untuk-revolusi-hunian-indonesia/)
- Tidak ditemukan situs atau aplikasi. Ada paper akademik GeoAI-CNN pemetaan potensi banjir Palembang dari Universitas Sriwijaya/Polsri, tetapi tidak ada sumber yang mengaitkannya dengan tim GeoFloodAI. **[ringkasan pencarian]** — [IIETA](https://iieta.org/node/22926)

**myECO – Maulana Derifato Achmad (Juara 2 HRI Business Ideation Umum 2025)**
- Kategori (kemungkinan besar): **IoT penghemat listrik + aplikasi smart home**.
- Aplikasi Play Store "myECO - Penghemat Listrik" (developer myECO Teknologi Nusantara):
  - Produk "Smart EcoRoom" dengan klaim "penghematan hingga 55%".
  - Kontrol dengan 3 mode: jadwal, manual via web, dan otomatis berdasarkan sensor ruangan.
  - Metrik: rating 4,9 (34 ulasan), **1 rb+ unduhan**, diperbarui **19 Nov 2026**.

  — [Google Play: myECO](https://play.google.com/store/apps/details?id=id.myeco.myeco) (diakses 2026-11-24)
- Pendiri "Maulana Derifato A." (mahasiswa Sistem Informasi Universitas Brawijaya, Malang). Produk mulai dijual 2022. Klien yang disebut: PLN (beberapa kantor pusat dan ICON Plus), uji coba Telkomsel, OYO, RedDoorz. Juara I Technopreneur Wirausaha Muda Pemula Kemenpora. — [Beritajatim, 21 Jul 2023](https://beritajatim.com/?p=1031039). MyEco Teknologi Nusantara berdiri Okt 2020 dan punya 12 jenis produk. — [Gizmologi, 4 Feb 2023](https://gizmologi.id/?p=93385)
- **Catatan identitas:** tidak ada sumber yang secara eksplisit menyatakan bahwa entri myECO di BTN Housingpreneur adalah produk startup ini. Kecocokan nama (Maulana Derifato) membuatnya sangat mungkin. Isi pitch untuk perumahan tidak ditemukan.

**Jelanpaint (J2) dan MiBi-Tech 2.0 (J3), Business Ideation Mahasiswa 2025**
- Hanya nama kelompok/produk yang tercantum. — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik). **Deskripsi produk tidak ditemukan** (pencarian nama tidak memberi hasil relevan). Dari namanya, Jelanpaint kemungkinan produk cat/pelapis (inferensi, belum terverifikasi).

**Proteka dan Model Co-housing (Business Ideation Umum 2025)**
- Proteka (PT Inovasi Tangguh Bencana): pelapis diperkuat serat untuk dinding tahan gempa, berupa **material** (catatan sebelumnya, [CNBC, 30 Jan 2026](https://www.cnbcindonesia.com/news/20260130124219-4-706680/mantap-btn-expo-2026-pamerkan-inovasi-perumahan-masa-depan)).
- "Model Co-housing Skema Koperasi Perumahan Kolektif" (Anindya Dhiracitta) adalah **model pembiayaan/kelembagaan**. Hanya judul yang tersedia. — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)

**Ontoown (finalis, dipamerkan di BTN Expo 2026; bukan pemenang)**
- Kategori: **aplikasi/platform rent-to-own** (Bandung).
- Ontoown "memperkenalkan aplikasi skema rent-to-own dan hunian bertahap yang memungkinkan masyarakat—terutama generasi muda dan berpenghasilan terbatas—memiliki rumah secara gradual melalui sistem sewa bulanan hingga siap membayar uang muka (DP) KPR".
- Kutipan Zikra (tim Ontoown): "Banyak aset hunian menganggur, sementara Gen Z membutuhkan rumah tetapi terkendala credit history dan DP. Platform ini menjembatani kesenjangan tersebut."

— [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026); [Indoposco, 3 Feb 2026](https://indoposco.id/2026/02/03/sabet-peringkat-pertama-train-o-dan-modula-ungguli-58-inovator-di-btn-expo-2026/)
- Pemberitaan menyebut "BTN Expo 2026 Perkenalkan Platform Digital Fasilitasi Skema Kepemilikan Rumah Rent to Own" (halaman KoranBUMN 404 dan Bisnis memblokir bot saat dibuka). **[ringkasan pencarian]** — [Bisnis, 30 Jan 2026](https://ekonomi.bisnis.com/read/20260130/47/1948688/btn-expo-2026-perkenalkan-inovasi-perumahan-rent-to-own)
- Tidak ditemukan situs (ontoown.com/.id/.co.id tidak merespons), Play Store, maupun App Store. Kategori lomba, besaran sewa, target DP, dan bank mitra tidak dipublikasikan.
- Konteks: BTN sendiri pernah merilis "KPR Rent to Own" (2022) yang mensyaratkan tabungan DP 10%; ini produk berbeda dari Ontoown. **[ringkasan pencarian]** — [Kontan](https://keuangan.kontan.co.id/news/btn-rilis-kpr-rent-to-own-bagi-generasi-milenial-dan-gen-z)

**Finalis lain yang disebut media (non-digital)**
- Agriya (Surabaya; cat tembok dari sekam padi) dan Bell Living Lab (Bandung; material dari limbah kopi): material. — [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026)
- Daftar 181 peserta Live Pitching 2025 hanya memuat nama ketua tanpa nama produk (catatan sebelumnya), sehingga finalis digital lain tidak bisa diidentifikasi.

**Cara BTN membingkai pemenang 2025**
- Setiyo Wibowo (Direktur Risk Management BTN, 30 Jan 2026): "Kami menghimpun startup di bidang perumahan, mulai dari property technology (proptech), produsen material bangunan berkelanjutan, hingga pengembang desain rumah rendah emisi … Semua ini kami dorong agar menjadi **solusi nyata, bukan sekadar konsep**." Juga: "BTN mencari mitra-mitra inovatif yang siap dikolaborasikan dan **di-scale up**." — [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026)
- Media merangkum finalis 2025 sebagai solusi atas "keterbatasan daya beli masyarakat, tingginya risiko bencana di kawasan permukiman, serta ketergantungan pada material bangunan konvensional", dan "seluruh solusi dinilai memiliki potensi komersial sekaligus keberlanjutan jangka panjang". — [Monitor Indonesia](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026)

### Inferences
- **Rating relevansi untuk Estora (Batch 2):**

| Produk | Kategori produk | Relevansi | Alasan singkat |
|---|---|---|---|
| Ontoown (finalis) | Aplikasi rent-to-own → DP → KPR | **Tinggi** | Alurnya menyentuh jadwal pembayaran, portal pembeli, dan pipeline KPR Estora; dibingkai sebagai jalan menuju KPR BTN bagi Gen Z |
| TRAIN-O (J1 Tech) | Platform digital pelatihan/sertifikasi + VR | **Sedang** | Domain beda (SDM konstruksi), tapi preseden juara Tech 2025 berupa platform digital dengan traksi tahunan |
| KPR Energy / GridSolr (J3 Value Chain) | PLTS + skema pembiayaan terkait KPR + monitoring | **Sedang** | Contoh sinergi BTN yang menang: add-on rumah yang ikut dibiayai di jalur KPR; bisa menjadi item upsell di modul booking/KPR Estora |
| AITOMA (J2 Tech) | IoT + AI + aplikasi energi | Rendah | Hardware energi; hanya bersinggungan bila developer membundel smart home per kawasan |
| myECO (J2 Ideation Umum) | IoT + aplikasi penghemat listrik | Rendah | Sama seperti AITOMA |
| GeoFloodAI (J1 Ideation Mhs) | AI risiko banjir untuk perencanaan lahan | Rendah | Tahap pra-proyek; hanya bersinggungan dengan site plan |
| RUMAH GOKILS (J3 Tech) | Jasa pest control/perlindungan hunian | Rendah | Layanan fisik; bisa menjadi mitra garansi/purna jual |
| Parongpong RAW Lab, RR Board, Proteka, MODULA, Agriya, Bell Living Lab | Material/konstruksi | Rendah | Non-digital |
| Co-housing koperasi | Model pembiayaan kolektif | Rendah | Konsep; tidak ada produk |
| Jelanpaint, MiBi-Tech 2.0 | Tidak diketahui | Tidak dapat dinilai | Deskripsi tidak ditemukan |

- Di 2025, kategori Tech bergeser dari "aplikasi + layanan" (2024) ke **teknologi yang menyentuh rumah atau penghuni secara fisik** (SDM konstruksi dengan VR, IoT energi, perlindungan hama). Pemenang Value Chain didominasi **material sirkular**, ditambah satu **inovasi pembiayaan energi berbasis KPR**.
- Ontoown dan Rusun Swadaya (2024) sama-sama platform yang menyalurkan calon debitur ke pembiayaan. Satu menang di Ideation, satu hanya finalis. Kemungkinan bedanya ada pada kematangan bukti (Ontoown tidak menunjukkan traksi publik), tetapi ini dugaan.

### Gaps
- Situs dan aplikasi TRAIN-O, AITOMA, Ontoown, GeoFloodAI tidak ditemukan secara publik, jadi tidak ada visual resmi, metrik toko aplikasi, maupun harga.
- Deskripsi RUMAH GOKILS hanya dari ringkasan mesin pencari; artikel Tempo (HTTP 403) tidak bisa diverifikasi.
- Mekanisme pembiayaan "KPR Energy" tidak dijelaskan, termasuk apakah sudah ada produk BTN yang membiayai PLTS GridSolr.
- Jelanpaint dan MiBi-Tech 2.0: tidak ada deskripsi.
- Tidak ditemukan bukti kontrak, pilot, atau integrasi BTN pasca-menang untuk pemenang Tech 2025 (TRAIN-O, AITOMA, RUMAH GOKILS).

---

## 3. Pola produk digital yang dihargai juri, cara membingkai sinergi BTN, dan pelajaran untuk entri aplikasi seperti Estora

### Takeaway
Juri dua batch menghargai produk yang (a) **sudah berjalan dengan angka traksi**, (b) **menggabungkan digital dengan layanan atau perangkat fisik** ("phygital"), (c) menjawab masalah struktural berskala nasional dengan data (backlog tenaga kerja, sampah, energi, risiko bencana, keterjangkauan), dan (d) punya **kaitan pembiayaan** (KPR, kredit bangun/renovasi, rent-to-own, pembiayaan komunitas). Software back-office developer murni belum pernah menang. Estora sebaiknya tampil sebagai "mesin konversi dan percepatan akad KPR BTN" yang terbukti berjalan di proyek developer nyata, dengan metrik dan dampak keterjangkauan atau keberlanjutan yang terukur.

### Cited Findings
- Preseden aplikasi menang Juara 1 kategori teknologi: CIROES (Android, 5 rb+ unduhan, jasa ke perusahaan). — [Google Play](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp); [cirowaste.com](https://www.cirowaste.com)
- Pemenang menampilkan angka traksi:
  - Paktukang: 658+ pekerjaan, 158 tukang, 2061 konsultasi (2025), 91 rumah direnovasi (2025). — [paktukang.com](https://paktukang.com/); [blog 29 Des 2025](https://paktukang.com/blog/menuju-hunian-impian-catatan-perjalanan-paktukang-di-tahun-2025/)
  - TRAIN-O: 3.500 → 3.569 → 4.324 orang terlatih (2022–2024). — [Kitabaru](https://kitabaru.com/train-o-dan-modula-dua-inovasi-digital-jawab-tantangan-krusial-konstruksi-indonesia/)
  - GridSolr: "80% pelanggan kami" memilih paket 4,7 kWp. — [gridsolr.com](https://gridsolr.com/)
- Pembingkaian pembiayaan:
  - KPR Energy: "memudahkan kepemilikan panel surya bagi pemilik hunian baru". — [gridsolr.com](https://gridsolr.com/)
  - Paktukang: kredit multiguna dan cicilan 15 tahun. — [blog](https://paktukang.com/blog/menuju-hunian-impian-catatan-perjalanan-paktukang-di-tahun-2025/)
  - Rusun Swadaya: "akses pembiayaan dari BTN". — [Metro TV](https://www.metrotvnews.com/read/b1oCVz5g-btn-jadi-batu-loncatan-inovator-di-sektor-perumahan)
  - Ontoown: sewa → DP KPR. — [Monitor Indonesia](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026)
- Sinergi BTN yang tercatat resmi semuanya berbentuk **KPR atau pembiayaan unit** atau **pasokan untuk program BTN**: Autoconz (rumah 3D dengan KPR BTN), Habitatland (KPR BTN), RAWHAUS (KPR Hijau/Tapera), TANAREKA (KPR), Rumah Pracetak (Rumah Rendah Emisi). Ditambah kolaborasi antar-finalis, misalnya CIROES × Paktukang (manajemen IPL, digital marketing properti). — [Kilas Balik](https://btnhousingpreneur.com/kilas-balik)
- BTN melibatkan alumni kembali di Batch 3: Direktur GridSolr menjadi pembicara roadshow Semarang (Okt 2026). — [Aktual, 21 Okt 2026](https://aktual.com/btn-housingpreneur-hadir-di-semarang-bedah-inovasi-rumah-zaman-now/)
- Bahasa BTN yang bisa dipakai ulang di pitch: "solusi nyata, bukan sekadar konsep", "proptech", "mitra … di-scale up". — [Monitor Indonesia, 30 Jan 2026](https://monitorindonesia.com/ekonomi/read/2026/01/619721/dari-sampah-jadi-hunian-dari-sewa-jadi-milik-inovasi-perumahan-masa-depan-unjuk-gigi-di-btn-expo-2026). Juri 2024 dari latar arsitektur (Ridwan Kamil, Yu Sing) menekankan perubahan iklim. — [Sumsel Pos](https://www.sumselpos.com/finance/1602/berikut-ini-daftar-pemenang-btn-awards-2025-penghargaan-untuk-inovasi-dan-pengembangan-perumahan/); [Kompasiana Autoconz](https://www.kompasiana.com/autoconz3dcp/67b6adb334777c7a823d06a2/autoconz-menjadi-juara-di-btn-housingpreneur-2025-dorong-kemajuan-teknologi-konstruksi)

### Inferences
**Pola produk digital yang menang**
1. **Digital sebagai lapisan orkestrasi layanan nyata.** CIROES mengatur penjemputan dan bank sampah; Paktukang mengatur tukang, RAB, dan monitoring progres; TRAIN-O mengatur pelatihan sampai penempatan kerja; AITOMA, myECO, dan GridSolr menjalankan aplikasi monitoring di atas perangkat fisik. Juri tampaknya menilai dampak di lapangan, bukan kecanggihan UI.
2. **Angka dampak sosial/lingkungan dikedepankan**: kg sampah, tukang berdaya, supplier lokal, % hemat listrik, ROI PLTS, % limbah berkurang, jumlah tenaga kerja tersertifikasi.
3. **Jembatan ke pembiayaan** menjadi pembeda di kategori value chain/ideation (KPR Energy, Rusun Swadaya, Ontoown, Paktukang).
4. **Skala nasional dan inklusi**: setiap pemenang membuka pitch dengan data masalah nasional (8,3 juta kekurangan tenaga terampil, backlog, sampah sungai, Gen Z tanpa credit history).

**Pelajaran untuk Estora (Batch 3, Housing Ecosystem/Innovation)**
- **Tunjukkan "solusi nyata"**: minimal satu proyek developer berdiri yang memakai Estora end-to-end (site plan, booking, KPR pipeline, cicilan, progres foto, BAST/garansi, portal pembeli). Sertakan angka: jumlah unit dikelola, lead → booking → akad, rata-rata hari booking-ke-akad, tunggakan tertagih lewat WA reminder, keluhan garansi tertutup. Ini selaras dengan aturan "site nyata" (lihat catatan sebelumnya) dan pola traksi pemenang.
- **Bingkai sebagai sistem orkestrasi ekosistem, bukan sekadar back-office**: Estora menghubungkan developer, pembeli, BTN (KPR), kontraktor/tukang (progres), dan layanan purna jual. Ini setara dengan cara CIROES dan Paktukang menang: digital mengatur layanan fisik.
- **Pembiayaan sebagai inti sinergi BTN**: meniru pola KPR Energy, Ontoown, dan Rusun Swadaya, posisikan Estora sebagai kanal yang mempercepat dan menyehatkan KPR BTN, misalnya:
  - pra-kualifikasi pembeli dan kelengkapan berkas;
  - status KPR terlacak (lihat integrasi BTN Properti for Developer di catatan sebelumnya);
  - jadwal DP/booking fee via VA/QRIS BTN;
  - peluang modul "tabungan DP bertahap" untuk pembeli yang belum siap KPR (dekat dengan konsep Ontoown, dengan BTN sebagai bank tujuan).
- **Tambahkan sudut keberlanjutan dan keterjangkauan yang terukur**: proses paperless, penurunan biaya transaksi/penjualan per unit, penurunan pembatalan, dan potensi bundling add-on hijau di tahap booking/KPR (preseden GridSolr: PLTS, Habitatland: eco features). Pemenang dua batch selalu punya angka hijau atau inklusi.
- **Manfaatkan alumni sebagai bukti ekosistem**: developer pemenang (Habitatland, Prosya Bangun, Sembilan Bintang, dan lainnya) adalah calon pilot. Penyedia layanan alumni (CIROES dan Paktukang untuk IPL/perbaikan/garansi, RUMAH GOKILS untuk perlindungan hunian, GridSolr untuk PLTS) bisa diposisikan sebagai mitra plug-in di modul purna jual atau upsell Estora. Ini menjawab kriteria "Potensi Kolaborasi Ekosistem" dan mengikuti pola kolaborasi antar-finalis yang dicatat BTN di Kilas Balik.
- **Risiko**: belum ada preseden pemenang berupa software operasional developer. Juri 2025 condong ke teknologi fisik/IoT dan material. Estora perlu demo yang kuat dan bukti lapangan agar tidak dinilai "sekadar aplikasi admin". Hindari klaim fitur yang tumpang tindih dengan produk BTN (BTN Properti for Developer, Smart Residence); bingkai sebagai pengumpan data ke kanal BTN.

### Gaps
- Bobot penilaian aktual juri per pemenang dan feedback tertulis tidak dipublikasikan, sehingga pola di atas adalah inferensi dari profil pemenang.
- Belum ditemukan bukti bahwa pemenang berbasis aplikasi (CIROES, Paktukang, TRAIN-O) mendapat integrasi teknis, pilot berbayar, atau pembiayaan langsung dari BTN setelah menang.

---

## 4. Visual publik (screenshot) yang disimpan untuk produk berelevansi Tinggi/Sedang

### Takeaway
Sembilan file disimpan untuk tiga produk berelevansi Sedang yang punya visual publik: CIROES (4 screenshot resmi Play Store), Paktukang (3 tangkapan situs), dan GridSolr/KPR Energy (2 tangkapan situs). Produk Tinggi/Sedang lainnya (Ontoown, TRAIN-O, Platform Rusun Swadaya) tidak punya situs atau aplikasi publik yang ditemukan, jadi tidak ada visual yang disimpan.

### Cited Findings
Folder: `/home/user/dadada/research_notes/Riset aplikasi pesaing dan pemenang BTN/screenshots/`. Semua diambil 2026-11-24. Tangkapan situs memakai Playwright Chromium (viewport 1366×900, deviceScaleFactor 1, full-page <8000 px). Screenshot Play Store diunduh dari URL dasar dengan sufiks `=w1080` (ikon 512×512 tidak diambil).

**pemenang_ciroes/** (sumber listing: [Google Play com.cirowaste.ciroapp](https://play.google.com/store/apps/details?id=com.cirowaste.ciroapp))

| File | Isi | Sumber |
|---|---|---|
| `pemenang_ciroes/ciroes_playstore_1.png` | Beranda: Total Saldo, Tarik Saldo, menu Cistore Terdekat/Langganan/Layanan Spesifik/Layanan B3 (500×1024) | https://play-lh.googleusercontent.com/rEFh71WdDHcralThq2DEjIG91KYnpjNbN40YphOMQMUmeMFLv30czdASei38J08_yyxjz9dxFGFDZw6tdRK7=w1080 |
| `pemenang_ciroes/ciroes_playstore_2.png` | "Kumpulkan, Pilah dan Order": layar Pilih Sampah dengan harga/kg, Total Estimasi Penjualan, tombol Jemput (500×1024) | https://play-lh.googleusercontent.com/sy0eWOzuEyxl6uCCj4icQ28fpXcihJsSC46Yt4kCrsEzW1aO_F_Ca5pICx43l3UnkscVS5YXbhC7A2S3XBhP=w1080 |
| `pemenang_ciroes/ciroes_playstore_3.png` | "Bank Sampah Digital": peta Cistore Terdekat (500×1024) | https://play-lh.googleusercontent.com/e1h9_IPw5Tk3dyrMmA_CvWkYfyIeTZQZfs9TMJa72HfZu3GzO98ajy4STsACaMkIY9UYJ49-1I7gIlAszoe7BuU=w1080 |
| `pemenang_ciroes/ciroes_playstore_4.png` | "Fitur Langganan": setor sampah dari rumah secara berlangganan; mobil jemput berbranding (500×1024) | https://play-lh.googleusercontent.com/_XXZ6cUjjaK7vid98ylgzXujl-ciB575BIE88CNszgy5v6IVh1AAZ2AperINMQk4bA2BJySHCB1eUyjk-Wuggg=w1080 |

**pemenang_paktukang/**

| File | Isi | Sumber |
|---|---|---|
| `pemenang_paktukang/paktukang_home_viewport.png` | Hero beranda (1366×900) | https://paktukang.com/ |
| `pemenang_paktukang/paktukang_home_fullpage.png` | Beranda penuh: layanan, metrik, alur 4 langkah, portofolio, testimoni (1387×6970) | https://paktukang.com/ |
| `pemenang_paktukang/paktukang_blog_recap2025.png` | Blog rekap 2025 (Juara 2 BTN, kredit multiguna, metrik) (1366×5742) | https://paktukang.com/blog/menuju-hunian-impian-catatan-perjalanan-paktukang-di-tahun-2025/ |

**pemenang_kpr-energy-gridsolr/**

| File | Isi | Sumber |
|---|---|---|
| `pemenang_kpr-energy-gridsolr/gridsolr_home_viewport.png` | Hero beranda dengan badge "3rd Winner BTNHousingPreneur 2025" dan "Estimasi ROI 4-5 tahun" (1366×900) | https://gridsolr.com/ |
| `pemenang_kpr-energy-gridsolr/gridsolr_home_fullpage.png` | Beranda penuh: paket 4700 Wp, BOM terbuka, monitoring, keterangan KPR Energy (1366×6829) | https://gridsolr.com/ |

Skrip pengambil berada di direktori scratch sesi (`/tmp/claude-0/-home-user-dadada/4c43c2dd-1aa7-553c-9e9f-59508645de56/scratchpad/btnwin/scripts/`), bukan di folder screenshot.

### Inferences
- Screenshot CIROES adalah materi promosi Play Store, bukan tangkapan layar langsung dari aplikasi yang dipakai. Tampilan nyata bisa berbeda.

### Gaps
- **Ontoown** (relevansi Tinggi), **TRAIN-O** dan **Platform Rusun Swadaya** (Sedang): tidak ditemukan situs atau aplikasi publik, sehingga tidak ada visual resmi. Foto di artikel berita tidak diambil karena bukan visual produk.
- Instagram @btnhousingpreneur dan video pitch YouTube tidak berhasil dijangkau lewat pencarian. Materi pitch pemenang (deck/video) tidak tersedia publik.
