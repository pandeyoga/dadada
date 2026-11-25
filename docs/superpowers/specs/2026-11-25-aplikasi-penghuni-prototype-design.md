# Desain: Prototipe aplikasi penghuni Estora "Rumah Dalam Genggaman"

Tanggal: 25 November 2026 · Status: menunggu persetujuan pemilik produk

## 1. Maksud dan alasan

Estora akan ikut BTN Housingpreneur Batch 3 (pendaftaran tutup **30 November 2026**; live pitching 14–18 Desember; Grand Judging 13–14 Januari 2027). Riset sesi ini menunjukkan celah terbesar Estora bukan mesin back-office (yang sudah dalam), tetapi **layar untuk pihak di luar developer**: pembeli, warga, satpam, pengelola kawasan, dan mitra/agen.

Pemilik produk ingin, dalam **5 hari**, sebuah **prototipe frontend** aplikasi pengguna bernama **"Rumah Dalam Genggaman"** yang:

- bisa ditunjukkan dan diklik juri (screenshot untuk berkas 30 Nov, demo klik untuk live pitching),
- memuat **semua fitur** yang dibahas: fitur aplikasi Rumah Ningrat (Keluarga Ningrat, Ningrat Apps, Dashboard Warga, Mitra Ningrat), isi pitch deck Estora, dan portal pembeli Estora yang sudah ada,
- menonjolkan **IoT fase 1 = keamanan**: keamanan unit rumah (kunci pintu pintar, CCTV rumah) dan kawasan (SOS, CCTV kawasan, gerbang, tamu),
- dibangun **di dalam aplikasi Estora** sehingga, bila lolos tahap awal, backend tinggal disambungkan tanpa membuang pekerjaan.

Pembeda yang ingin ditunjukkan: **satu aplikasi dari pembeli menjadi warga.** Sebelum serah terima, aplikasi menampilkan perjalanan KPR dan progres bangun; setelah BAST, aplikasi otomatis berganti ke mode warga. Rumah Ningrat memecah ini menjadi tiga aplikasi terpisah.

Konteks pitch deck Estora (lampiran pemilik): tagline "Smart Living, Greener Tomorrow"; posisi "Ekosistem Developer & Residensial"; pertanyaan penghuni yang ingin dijawab: *"Proses KPR saya sudah sampai mana?"*, *"Siapa tetangga saya, ada apa di perumahan ini?"*, *"Apakah iuran IPL sudah saya bayar?"*, *"Apa saya sudah mematikan perangkat di rumah?"*. Model bisnis: Developer (langganan), Resident (layanan + premium), Marketplace (komisi vendor), Smart & Green (IoT).

## 2. Sasaran, bukan-sasaran, anti-sasaran

**Sasaran**
1. Semua layar pada inventaris (bagian 7) ada dan bisa dibuka lewat navigasi, dengan data contoh yang masuk akal dan konsisten antarlayar.
2. **Alur demo utama** (bagian 8) mulus, bisa diklik dari awal sampai akhir, dengan perubahan status yang terasa nyata (bayar → lunas, kunci → terbuka, SOS → diterima satpam).
3. Tampilan glassmorphism dengan gradasi hijau logo Estora, konsisten di semua layar, mobile-first (lebar 360–430 px), terbaca jelas di HP Android kelas menengah.
4. Data berasal dari satu lapisan layanan contoh yang bentuknya meniru API sehingga bisa diganti ke API asli kemudian.
5. Aplikasi admin Estora yang sudah ada **tidak berubah tampilan maupun perilakunya**.

**Bukan sasaran (5 hari ini)**
- Backend, endpoint baru, basis data, autentikasi sungguhan (OTP asli), pembayaran sungguhan, integrasi perangkat IoT sungguhan, integrasi BTN/Tapera.
- Aplikasi native / publikasi ke Play Store atau App Store.
- Uji otomatis menyeluruh (cukup pemeriksaan build dan tangkapan layar semua rute).

**Anti-sasaran (gagal walau "jalan")**
- Tampilan atau merek yang meniru Rumah Ningrat (nama, logo, susunan visual persis). Yang diambil adalah **fitur dan alur**, bukan tampilan.
- Mengubah tampilan aplikasi admin atau mematahkan rute yang sudah ada (`/`, `/portal`, `/showroom/:token`, dll.).
- Teks putih di atas latar tembus pandang yang sulit dibaca; layar yang patah di HP kecil.
- Klaim di layar yang seolah fitur sudah berjalan sungguhan ke pihak luar. Semua layar prototipe diberi penanda kecil **"Data contoh"** di menu Akun / peluncur demo (bukan di setiap layar, agar screenshot tetap bersih).

## 3. Batasan

- **Waktu:** 5 hari kerja sampai 30 November 2026; target ±45 layar.
- **Teknologi yang ada (dipakai apa adanya):** React 19, Create React App lewat craco, react-router-dom 7, Tailwind 3 + tailwindcss-animate, komponen shadcn/Radix di `frontend/src/components/ui/`, lucide-react, framer-motion, sonner, date-fns/dayjs. Alias impor `@/` → `frontend/src`. Pengelola paket: yarn 1. `node_modules` belum terpasang di sesi ini (`yarn install` diperlukan).
- **Rute yang ada:** `/login`, `/portal/*` (portal pembeli asli, memakai API), `/showroom/:token`, halaman legal, dan seluruh aplikasi staf di balik `RequireAuth`. Semua didaftarkan di `frontend/src/App.js`.
- **Portal pembeli asli** (`frontend/src/components/portal/`) memanggil API langsung (`portalApi`), sehingga panelnya **tidak bisa dipakai ulang apa adanya** dengan data contoh. Prototipe membuat komponen baru bergaya glass; panel lama tetap utuh.
- **PWA:** `public/manifest.json` saat ini untuk aplikasi staf (`start_url` `/construction`). Service worker sudah ada.
- **Bahasa:** seluruh teks antarmuka berbahasa Indonesia yang wajar untuk pembeli rumah subsidi (bukan istilah teknis).
- **Perangkat sasaran:** HP Android kelas menengah; efek blur berat harus dibatasi.

## 4. Pendekatan yang dipertimbangkan

| Pendekatan | Untung | Rugi |
|---|---|---|
| **A. Di dalam aplikasi Estora, rute baru, data contoh di satu lapisan layanan** ✅ dipilih | Tak ada pekerjaan yang dibuang saat backend dibuat; satu deploy; bisa memakai komponen UI, utilitas, dan PWA yang ada | Harus hati-hati agar gaya glass tidak bocor ke aplikasi admin; build CRA lebih lambat |
| B. Proyek prototipe terpisah (Vite) | Paling cepat, nol risiko ke produksi, mudah jadi tautan statis | Harus dipindah/ditulis ulang ke Estora nanti |
| C. Mockup HTML statis per layar | Tercepat dan paling mirip mockup | Bukan aplikasi; tak terpakai ulang |

Pemilik produk memilih **A** karena tujuan akhirnya prototipe yang langsung disambung ke backend bila lolos.

## 5. Keputusan yang sudah diambil pemilik produk

1. **Nama:** "Rumah Dalam Genggaman" (aplikasi penghuni Estora).
2. **Semua fitur masuk prototipe** — tidak ada yang ditunda ke fase 2, termasuk fitur Rumah Ningrat (PPOB, marketplace, jasa rumah, kelompok hobi, event warga, satpam bertugas, gerbang pintar, ajak teman/afiliasi, portal mitra) dan fitur deck (energi rumah, laporan kas, komunitas).
3. **IoT fase 1 = keamanan:** unit rumah (kunci pintu pintar, CCTV rumah) dan kawasan (SOS, CCTV kawasan, gerbang pintar, tamu).
4. **Dua mode dalam satu aplikasi:** Mode Pembeli → layar transisi saat BAST → Mode Warga.
5. **Gaya visual:** glassmorphism dengan aksen dan gradasi hijau dari logo Estora (mockup v1 sudah disetujui sebagai arah).
6. **Cara bangun:** pendekatan A.

## 6. Arah visual dan sistem desain

**Warna (diambil dari logo Estora):**

| Token | Hex | Peran |
|---|---|---|
| `leaf` | `#49AE42` | hijau daun, awal gradasi, tombol utama |
| `green` | `#209F59` | hijau tengah |
| `teal-green` | `#01916F` | toska |
| `teal` | `#007F83` | toska tua |
| `deep` | `#006284` | biru toska (ujung gradasi) |
| `ink` | `#00454D` | teks judul, latar gelap |
| `ink-900` | `#00353B` | latar paling gelap |
| `forest` | `#006747` | hijau judul deck, ikon aktif |
| `mint` | `#E7FFEF` | latar terang |
| `lime` | `#B5E26B` | aksen "aman/aktif" di atas latar gelap |
| `sos` | `#E5484D` | darurat saja |

- Gradasi utama: `leaf → teal-green → deep`; latar hero: `ink → forest → green` dengan "gumpalan" radial `lime/teal-green/deep`.
- **Huruf:** Plus Jakarta Sans (400–800) untuk aplikasi penghuni (dipasang lewat `@fontsource/plus-jakarta-sans` agar jalan offline); aplikasi admin tetap Inter/Space Grotesk.
- **Ikon:** lucide-react.
- **Kaidah glass (dari riset):**
  - Glass (blur 14–18 px, putih 12–18 %, garis tepi putih 30 %) hanya pada **permukaan utama**: kartu di area hero gelap, menu bawah, tombol kecil di header. Area konten memakai kartu putih buram 75–85 % dengan teks gelap.
  - Kontras teks ≥ 4,5:1 (teks besar ≥ 3:1) terhadap latar terburuk di belakangnya.
  - Cadangan solid bila `backdrop-filter` tidak didukung (`@supports not`) dan bila `prefers-reduced-transparency: reduce`.
  - Maksimal ±4 permukaan blur per layar; jangan menganimasikan blur.
- **Kaidah interaksi keamanan:**
  - Status kunci selalu warna + ikon + kata ("Terkunci" / "Terbuka").
  - Buka kunci memakai **geser**, bukan sekali ketuk.
  - SOS memakai **tahan 3 detik** dengan cincin hitung mundur; bisa dibatalkan sebelum terkirim.
  - Notifikasi berjenjang: **Darurat › Keamanan › Info**, warna dan urutan berbeda.
- **Isolasi gaya:** semua gaya prototipe di-scope di bawah satu kelas akar (mis. `.rdg-app`) atau token Tailwind berprefiks; tidak mengubah `:root`, `body`, atau kelas global yang dipakai admin.
- Mockup v1 (`assets/2026-11-25-mockup-v1.png`: Beranda, Keamanan rumah, SOS) menjadi acuan rasa dan ukuran: sudut kartu 20–26 px, tombol pil, grid layanan 4 kolom dengan ikon berlatar gradasi, menu bawah melayang dengan tombol SOS menonjol di tengah.

## 7. Struktur, navigasi, dan inventaris layar

### 7.1 Permukaan dan rute

Semua di bawah satu awalan baru agar terpisah dari rute yang ada (nama akhir diserahkan ke builder; saran: `/app`).

| Permukaan | Saran rute | Bentuk |
|---|---|---|
| Peluncur demo | `/app/demo` | pilih persona; tombol "Simulasikan BAST"; "Reset data contoh" |
| Aplikasi penghuni (mode Pembeli & Warga) | `/app/...` | mobile-first, menu bawah |
| Aplikasi satpam (pos jaga) | `/app/satpam/...` | mobile-first |
| Dasbor pengelola kawasan | `/app/pengelola/...` | web desktop (tetap rapi di tablet) |
| Portal mitra / agen | `/app/mitra/...` | mobile-first, juga rapi di desktop |

Di desktop, layar mobile ditampilkan di tengah dengan lebar maksimum ±430 px (bingkai HP opsional) agar demo di laptop tetap terlihat seperti aplikasi.

### 7.2 Navigasi aplikasi penghuni

- **Mode Pembeli** — menu bawah: **Beranda · Progres · Bayar · Dokumen · Akun**.
- **Layar transisi BAST** — "Selamat datang di rumah baru": aktifkan kunci pintu & kamera, undang keluarga, isi kontak darurat.
- **Mode Warga** — menu bawah: **Beranda · Keamanan · SOS (tengah, menonjol) · Tagihan · Komunitas**. Akun lewat foto profil di header; notifikasi lewat lonceng.
- Grid **"Semua layanan"** di Beranda warga memuat fitur yang tidak ada di menu bawah.
- Peta navigasi visual: `assets/2026-11-25-peta-navigasi-v1.png` (label "Fase 2" di gambar itu sudah dibatalkan — semua masuk prototipe). Inventaris di bawah adalah acuan yang mengikat.

### 7.3 Inventaris layar

Kolom **Tingkat**: **D** = bagian alur demo, harus paling halus; **L** = lengkap dan bisa diklik dengan data contoh, isinya boleh lebih sederhana. Kolom **Backend nanti** menandai yang sudah punya endpoint portal (`/portal/*`) di Estora.

**Umum**
| # | Layar | Tingkat | Catatan |
|---|---|---|---|
| U1 | Peluncur demo (persona, simulasikan BAST, reset) | D | bukan bagian produk; untuk presentasi |
| U2 | Masuk dengan nomor WhatsApp + OTP (simulasi, kode apa saja diterima) | D | |

**Mode Pembeli**
| # | Layar | Tingkat | Backend nanti |
|---|---|---|---|
| P1 | Beranda: kartu "perjalanan rumah" (Booking → BI checking → KPR/SP3K → Akad → Bangun → BAST), tagihan berikutnya, progres %, info & promo | D | sebagian (`/portal/overview`) |
| P2 | Progres: linimasa foto per tahap, estimasi serah terima | D | ada (`/portal/progress`) |
| P3 | Peta kavling / siteplan (unit sendiri disorot) | L | ada (`/portal/site-plan`) |
| P4 | Bayar: jadwal & riwayat | D | ada (`/portal/payments`) |
| P5 | Bayar via VA/QRIS: pilih metode → nomor VA/kode QR → status "menunggu" → "lunas" | D | baru |
| P6 | Status KPR & jadwal angsuran | L | ada (`/portal/kpr`) |
| P7 | Pembatalan & refund (baca saja) | L | ada (`/portal/cancellations`) |
| P8 | Dokumen: SPR, PPJB, kuitansi, berkas KPR | L | ada (`/portal/documents`) |
| P9 | Akun: profil, anggota keluarga, tanya/komplain pra-serah terima | L | sebagian (`/portal/complaints`) |
| P10 | Ajak teman (referral): kode/tautan, status rujukan, hadiah | L | baru |
| P11 | Promo & info developer (detail) | L | baru |

**Transisi**
| # | Layar | Tingkat |
|---|---|---|
| T1 | "Selamat datang di rumah baru" → hubungkan kunci & kamera → undang keluarga → kontak darurat → selesai | D |

**Mode Warga**
| # | Layar | Tingkat | Backend nanti |
|---|---|---|---|
| W1 | Beranda: status rumah (pintu, kamera, satpam), tagihan IPL, grid layanan, pengumuman, kartu energi | D | baru |
| W2 | Keamanan · Rumah: kunci pintu (geser untuk buka, kunci otomatis), CCTV rumah ringkas, riwayat | D | baru (IoT) |
| W3 | Kunci pintu detail: kode sementara tamu/ART (buat, bagikan WA, cabut), riwayat akses | D | baru (IoT) |
| W4 | CCTV rumah: siaran "langsung" (simulasi), daftar kamera, rekaman per jam, notifikasi gerakan | D | baru (IoT) |
| W5 | Keamanan · Kawasan: CCTV kawasan (grid kamera gerbang/jalan/taman), satpam bertugas | D | baru |
| W6 | Gerbang pintar: cek lokasi (di dalam/luar radius), buka gerbang masuk/keluar, riwayat | L | baru |
| W7 | Undang tamu: QR sekali pakai (nama, tanggal, jam berlaku), bagikan WA, daftar undangan | D | baru |
| W8 | SOS: tahan 3 detik → pilih jenis (kemalingan, kebakaran, medis, lainnya) → status "Satpam menuju" → selesai | D | baru |
| W9 | Kontak darurat (kelola) | L | baru |
| W10 | Tagihan: IPL bulan ini, bayar VA/QRIS/e-wallet/link WA, status lunas, kuitansi | D | baru |
| W11 | Riwayat tagihan & kuitansi | L | baru |
| W12 | Laporan kas kawasan (pemasukan/pengeluaran per bulan, transparan) | L | baru |
| W13 | PPOB: pulsa, paket data, token PLN, PDAM → bayar → token/struk | L | baru |
| W14 | Komunitas: pengumuman & agenda warga | D | baru |
| W15 | Event warga (detail + ikut) | L | baru |
| W16 | Kelompok hobi (daftar, gabung, info kelompok) | L | baru |
| W17 | Polling warga (pilih, hasil) | L | baru |
| W18 | Pasar warga (produk warga & tenant, keranjang, pesan) | L | baru |
| W19 | Jasa rumah / mitra layanan (tukang, kebersihan, galon, servis AC → pesan jadwal) | L | baru |
| W20 | Semua layanan (grid lengkap) | L | — |
| W21 | Lapor kerusakan: tiket (kategori, foto, deskripsi) → linimasa (dibuat › diverifikasi › dikerjakan › selesai) → konfirmasi & rating warga | D | ada sebagian (`/portal/complaints`) |
| W22 | Klaim garansi per bagian rumah | L | ada (`/portal/warranty`) |
| W23 | Dokumen rumah: BAST, status sertifikat, garansi, denah, jalur instalasi | L | sebagian |
| W24 | Izin renovasi (ajukan, status) | L | baru |
| W25 | Booking fasilitas (lapangan, aula, kolam: pilih slot) | L | baru |
| W26 | Energi rumah: pemakaian listrik/air bulan ini vs bulan lalu, tips hemat (data contoh) | L | baru (IoT fase berikut) |
| W27 | Notifikasi berjenjang (Darurat › Keamanan › Info) | L | baru |
| W28 | Akun warga: profil, anggota keluarga & penyewa (hak akses), perangkat terhubung, pengaturan | L | baru |
| W29 | Ajak teman (sama dengan P10, tetap tersedia setelah jadi warga) | L | baru |

**Aplikasi satpam**
| # | Layar | Tingkat |
|---|---|---|
| S1 | Beranda pos: status shift, antrean SOS, tamu hari ini | D |
| S2 | Peringatan SOS layar penuh → terima → menuju Blok … → tandai selesai (status terlihat di W8 warga) | D |
| S3 | Pindai QR tamu (simulasi kamera) → valid/tidak valid → catat masuk | D |
| S4 | CCTV kawasan (grid) | L |
| S5 | Log patroli & kejadian | L |

**Dasbor pengelola kawasan (web)**
| # | Layar | Tingkat |
|---|---|---|
| K1 | Ringkasan kawasan: tingkat bayar IPL, tiket terbuka, SOS bulan ini, hunian | L |
| K2 | Tagihan IPL: terbitkan massal, status per unit, kirim pengingat WA | L |
| K3 | Tiket & keluhan: antrean, tugaskan teknisi, SLA | L |
| K4 | Pengumuman & agenda: buat, kirim | L |
| K5 | Laporan kas kawasan | L |
| K6 | Keamanan: log SOS, tamu, satpam bertugas | L |
| K7 | Mitra layanan & pasar warga (kurasi vendor) | L |

**Portal mitra / agen**
| # | Layar | Tingkat |
|---|---|---|
| M1 | Daftar mitra (wizard: akun, data pribadi, rekening, media sosial) | L |
| M2 | Beranda mitra: poin, komisi berjalan, peringkat (leaderboard) | L |
| M3 | Katalog proyek & unit tersedia + tautan/QR beratribusi + simulasi KPR yang bisa dibagikan | L |
| M4 | Rujukan saya: status per calon pembeli (lead → booking → akad) | L |
| M5 | Komisi & pencairan | L |

## 8. Alur demo utama (urutan presentasi)

1. Peluncur demo → persona **Rina (pembeli)** → masuk OTP.
2. Beranda pembeli: perjalanan rumah di tahap "Bangun 72 %"; buka Progres (foto per tahap).
3. Bayar cicilan bertahap lewat VA → status berubah "Lunas", kuitansi muncul.
4. Peluncur: **Simulasikan BAST** → layar transisi "Selamat datang di rumah baru" → hubungkan kunci & kamera, undang keluarga.
5. Beranda warga: "Rumah aman"; Keamanan → geser untuk buka pintu → riwayat bertambah; buat kode tamu ART → bagikan.
6. CCTV rumah (siaran simulasi) → CCTV kawasan.
7. Undang tamu (QR) → pindah ke **aplikasi satpam** → pindai QR → tamu tercatat masuk; warga mendapat notifikasi.
8. **SOS**: tahan 3 detik → "Kemalingan" → layar satpam menerima peringatan → "Satpam menuju" muncul di HP warga → selesai.
9. Tagihan IPL → bayar → lunas; buka laporan kas kawasan.
10. Lapor kerusakan → linimasa tiket.
11. (Opsional) Dasbor pengelola: tingkat bayar IPL dan tiket; portal mitra: tautan beratribusi.

## 9. Data contoh dan lapisan layanan

- **Satu lapisan layanan** (mis. `frontend/src/prototype/services/`) berisi fungsi bernama seperti endpoint masa depan (`getHome()`, `payBill(id, method)`, `unlockDoor()`, `sendSos(type)`, `createGuestPass(...)`, …) yang mengembalikan Promise dengan jeda kecil (200–600 ms) agar terasa seperti jaringan. Layar **tidak** membaca fixture secara langsung.
- **Fixture** konsisten satu dunia: proyek demo netral **"Estora Residence"** (bukan nama proyek nyata), warga utama **Rina Ayu**, Blok C-12, tipe 36/72, harga dan tanggal yang masuk akal untuk rumah subsidi/komersial menengah; ±20 unit tetangga, 3 satpam, 6 kamera kawasan, 2 kamera rumah, tagihan IPL ±Rp150.000/bulan, dsb.
- **Status bisa berubah dan bertahan** (bayar, kunci, SOS, tamu, tiket, polling, keranjang) disimpan di `localStorage` dengan tombol **Reset** di peluncur demo.
- **Sinkron antartab** di peramban yang sama (event `storage` atau `BroadcastChannel`) supaya SOS dan tamu dari tab warga langsung muncul di tab satpam saat demo dua jendela berdampingan. Sinkron antarperangkat **tidak** termasuk (butuh backend).
- **IoT disimulasikan:** kamera = ilustrasi/gambar lokal dengan penanda "LIVE", jam berjalan, dan efek bergerak ringan; tanpa tautan gambar dari internet. Kunci pintu mengunci otomatis setelah ±30 detik terbuka.
- **Pembayaran disimulasikan:** nomor VA/QR contoh; tombol "Saya sudah bayar" atau hitung mundur otomatis mengubah status ke lunas.

## 10. Integrasi dengan kode yang ada

- Tambah rute baru di `frontend/src/App.js` **di luar** `RequireAuth` (seperti `/portal/*`), tanpa mengubah rute lain.
- Komponen baru di folder sendiri (mis. `frontend/src/prototype/`), memakai komponen `components/ui/` dan utilitas yang ada bila cocok; **tidak mengubah** komponen portal lama.
- Gaya: token dan kelas di-scope; Plus Jakarta Sans hanya dimuat untuk rute prototipe bila memungkinkan.
- Manifest PWA: tidak mengganggu manifest staf. Bila mudah, rute prototipe memasang manifest sendiri ("Rumah Dalam Genggaman", `start_url` ke `/app`) saat dibuka; bila tidak mudah, cukup tanpa instalasi PWA khusus.

## 11. Verifikasi

- `yarn build` berhasil tanpa galat baru; linter tanpa galat baru di file prototipe.
- Skrip tangkapan layar Playwright yang membuka **setiap rute** prototipe di 390×844 (dan pengelola di 1366×900), menyimpan PNG untuk berkas pitch dan untuk dicek visual (tidak ada teks terpotong/bertumpuk).
- Alur demo (bagian 8) dijalankan otomatis atau manual sekali penuh, termasuk dua tab warga + satpam.
- Rute lama (`/login`, `/portal`, `/showroom/:token`) tetap terbuka seperti sebelumnya.

## 12. Yang diserahkan ke builder

- Nama awalan rute final, struktur folder, pemecahan komponen, dan manajemen state (Context/reducer sudah cukup).
- Isi detail fixture (nama, angka, teks), ilustrasi kamera, foto progres contoh (boleh ilustrasi).
- Urutan pengerjaan, dengan syarat alur demo (tingkat D) selesai dan halus lebih dulu.
- Detail animasi (framer-motion boleh dipakai seperlunya).
- Cara menampilkan aplikasi mobile di layar laptop (bingkai HP atau kolom tengah).

## 13. Risiko

- **Cakupan besar (±45 layar) dalam 5 hari** → tingkat D dikerjakan dulu; layar L dibuat dari pola komponen yang sama.
- **Performa blur di Android murah** → kaidah glass di bagian 6 dan cadangan solid.
- **Klaim traksi di pitch deck** ("3 developer aktif, 578 unit, 10+ bulan") tidak terlihat dari data repo; siapkan buktinya terpisah dari prototipe.
- **Kemiripan dengan Rumah Ningrat** → hanya fitur dan alur; merek, nama fitur, dan tata letak milik Estora.

## 14. Keputusan tambahan setelah tinjauan builder (25 Nov 2026)

Pemilik produk meminta pekerjaan dilanjutkan sampai selesai tanpa putaran tanya lagi; keputusan berikut diambil oleh Claude dan dicatat agar bisa diperiksa.

1. **Jadwal.** Semua layar inventaris (60 entri, bukan ±45) dibangun dan bisa diklik. Layar tingkat **D** dikerjakan dan disempurnakan lebih dulu, lalu di-screenshot untuk halaman 5 proposal ("Konsep, Desain, atau Prototype"). Layar **L** menyusul dengan pola komponen yang sama. Bila waktu habis, yang dikorbankan adalah kedalaman layar L, bukan alur D.
2. **Hosting dan keamanan produksi.** Deploy bukan bagian pekerjaan ini. Karena image frontend dipakai bersama semua instance (termasuk `hl5.estora.id` yang dipakai pembeli sungguhan), rute prototipe dijaga saat runtime: hanya aktif di `localhost`, `127.0.0.1`, dan hostname yang diawali `demo.` atau `trial.`; selain itu `/app/*` dialihkan ke `/`. Presentasi diasumsikan dari laptop (dua jendela berdampingan untuk warga + satpam). Peluncur demo tetap menuntun bila juri membuka sendiri.
3. **Cerita pembayaran Rina.** Rumah **subsidi FLPP**, Estora Residence Blok C-12, tipe 36/72, harga Rp166.000.000. Urutan perjalanan: **Booking → Cek kredit → Bangun → Pengajuan KPR/SP3K → Akad → Serah terima** (FLPP mensyaratkan rumah siap sebelum akad). Saat "Bangun 72 %", yang dibayar lewat VA adalah **uang muka yang dicicil ke developer** (mis. DP Rp5.000.000 dalam 5 kali). Panel KPR menampilkan status pengajuan dan simulasi angsuran bulanan dengan keterangan "dibayar ke bank setelah akad". Nama bank tampil sebagai data contoh ("KPR Subsidi · Bank BTN"); tidak ada teks yang mengklaim integrasi dengan bank mana pun. Pilihan VA memuat beberapa bank umum.
4. **Logo.** Diambil dari pitch deck (halaman logo) ke `assets/brand/`: `estora_logo_full.png` (logo + tagline, untuk latar terang), `estora_mark.png` (ikon saja, transparan), `estora_wordmark.png`, dan ikon aplikasi `rdg-icon-192.png`/`rdg-icon-512.png`. "Rumah Dalam Genggaman" ditulis sebagai teks (Plus Jakarta Sans) di samping ikon Estora; tidak ada logo terpisah. Di latar gelap, pakai ikon + teks putih (bukan wordmark PNG).
5. **Menu bawah warga** mengikuti teks dokumen ini (Komunitas di menu; Akun lewat foto profil), bukan mockup v1.
