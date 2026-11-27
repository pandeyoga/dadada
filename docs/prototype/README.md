# Rumah Dalam Genggaman — prototipe aplikasi penghuni Estora

Prototipe **frontend saja** untuk aplikasi penghuni Estora: satu aplikasi yang menemani pembeli rumah sejak
booking sampai serah terima (Mode Pembeli), lalu otomatis berganti menjadi aplikasi warga setelah BAST (Mode Warga),
ditambah aplikasi satpam, dasbor pengelola kawasan, dan portal mitra. Semua angka dan nama adalah **data contoh**
dari proyek fiktif "Estora Residence" (warga utama Rina Ayu, Blok C-12, rumah subsidi FLPP tipe 36/72).

- Kode: `frontend/src/prototype/` (rute `/app/*`, dimuat terpisah dari aplikasi staf).
- Rancangan: `docs/superpowers/specs/2026-11-25-aplikasi-penghuni-prototype-design.md`.
- Tangkapan layar semua layar, per peran dengan nama jelas: [`docs/prototype/screens/`](screens/README.md) (halaman penuh + layar pertama + lembar kontak; daftar lengkap di bawah).

## Menjalankan

Mode pengembangan (dari akar repo):

```bash
cd frontend && yarn start
```

Lalu buka **http://localhost:3000/app/demo** (peluncur demo).

Alternatif build produksi yang dilayani secara lokal:

```bash
cd frontend && yarn build
npx serve -s build -l 4173
```

Lalu buka **http://localhost:4173/app/demo**. Opsi `-s` wajib: semua rute `/app/...` dilayani oleh `index.html`.

Aplikasi bisa dipasang sebagai PWA dari rute `/app` (manifest sendiri "Rumah Dalam Genggaman · Estora",
nama pendek "Rumahku", warna tema `#00454D`). Manifest dan warna tema aplikasi staf dikembalikan begitu
pengguna keluar dari `/app`.

### Penjaga host

Rute `/app/*` hanya aktif di `localhost`, `127.0.0.1`, dan hostname yang diawali `demo.` atau `trial.`
(mis. `demo.estora.id`). Di host lain, termasuk host produksi yang dipakai pembeli sungguhan, `/app/*` langsung
dialihkan ke `/`. Untuk demo dari laptop, pakai `localhost`.

## Persona di peluncur demo

| Persona | Masuk ke | Isi |
|---|---|---|
| Rina · Pembeli | `/app/pembeli` | Rumah sedang dibangun (tahap Bangun 72 %), cicilan uang muka, KPR, dokumen |
| Rina · Warga | `/app/warga` | Rumah aman, kunci pintu, CCTV, SOS, tagihan IPL, komunitas, layanan rumah |
| Pak Joko · Satpam | `/app/satpam` | Pos gerbang utama: SOS masuk, pindai tamu, CCTV kawasan, patroli |
| Pengelola kawasan | `/app/pengelola` | Dasbor web: IPL per unit, tiket, pengumuman, kas, keamanan, mitra |
| Dimas · Mitra | `/app/mitra` | Agen rujukan: katalog unit, tautan beratribusi, rujukan, komisi |

Tombol lain di peluncur: **Simulasikan BAST** (pembeli → warga baru), pilihan **Lokasi** (di dalam/luar
kawasan, untuk gerbang pintar), sakelar **Pakai tanggal hari ini** (lihat *Tanggal demo*), **Reset data contoh**,
dan daftar **Semua layar (59)** untuk membuka layar mana pun.

### Tanggal demo

Data contoh disusun untuk **Rabu, 25 Nov 2026**: kerja bakti Minggu, 6 Des; senam pagi Minggu, 29 Nov; rapat warga
Sabtu, 12 Des; uang muka ke-3 dan IPL Desember jatuh tempo 10 Des. Agar jadwal itu tetap masuk akal kapan pun demo
dijalankan (mis. saat pitch pertengahan Desember), prototipe memakai **tanggal demo**: tanggal selalu 25 Nov 2026,
sedangkan jamnya mengikuti jam sungguhan (WIB), jadi hitung mundur kunci pintu dan jam laporan SOS tetap berjalan.
Peluncur menampilkan "Tanggal demo: Rabu, 25 Nov 2026".

Sakelar **Pakai tanggal hari ini** di peluncur beralih ke tanggal dan jam sungguhan dan mengulang data contoh
(semua tanggal relatif dibangun ulang terhadap hari ini; jadwal bertanggal tetap seperti di atas, jadi bisa sudah
lewat). Matikan sakelar untuk kembali ke tanggal demo. Pilihan ini tersimpan di peramban bersama data contoh dan
ikut berlaku di jendela lain pada peramban yang sama.

## Skrip demo (urutan presentasi)

Mulai dari **http://localhost:3000/app/demo** dan tekan **Reset data contoh** agar data kembali ke awal.

1. **Masuk sebagai pembeli.** Ketuk *Coba masuk dengan nomor WhatsApp*, isi nomor mana pun (≥ 10 angka),
   ketuk *Kirim kode*, isi 6 angka apa saja, ketuk *Masuk*. (Pintasan: ketuk *Rina · Pembeli* di peluncur.)
2. **Beranda pembeli.** Kartu "Perjalanan rumah Anda" berada di tahap *Bangun 72 %*. Ketuk *Lihat foto* untuk
   membuka Progres (linimasa foto per tahap dan estimasi serah terima). Bel notifikasi di Mode Pembeli hanya berisi
   kabar pembeli (uang muka jatuh tempo, foto progres); kabar rumah dan kawasan baru muncul di Mode Warga.
3. **Bayar cicilan uang muka lewat VA.** Menu *Bayar* → *Bayar uang muka 3 · Rp1.000.000* → *Pilih metode bayar*
   → pilih bank → nomor VA tampil → *Saya sudah bayar*. Status berubah *Lunas* dan kuitansi muncul.
   Angsuran KPR (Rp1.062.500/bulan) hanya simulasi dan "dibayar ke bank setelah akad".
4. **Serah terima.** Kembali ke peluncur (`/app/demo`) → *Simulasikan BAST* → layar "Selamat datang di rumah baru"
   → *Mulai* → ketuk *Hubungkan sekarang* → tunggu kunci dan kamera terhubung → *Lanjut* → undang keluarga: isi
   nama + nomor WhatsApp → *Tambah* → *Lanjut* → kontak darurat (boleh dikosongkan) → *Selesai*. Nama + nomor yang
   sudah diketik tapi belum ditambahkan ikut disimpan saat *Lanjut*/*Selesai*; isian yang belum lengkap ditahan
   dengan pesan (lengkapi atau kosongkan).
5. **Beranda warga.** Kartu "Rumah aman". Buka *Keamanan* → **geser** *Geser untuk buka* → pintu terbuka, hitung
   mundur kunci otomatis 30 detik, riwayat akses bertambah. Di *Kunci pintu* buat kode sementara untuk ART
   (mis. "Bu Siti · ART") lalu bagikan lewat *WhatsApp*.
6. **CCTV.** *CCTV rumah* (siaran simulasi dengan jam berjalan, rekaman per jam) → tab *Kawasan* / *CCTV kawasan*
   (6 kamera, satpam bertugas).
7. **Undang tamu (dua jendela).** Buka jendela kedua di peramban yang sama, ke
   **http://localhost:3000/app/satpam**, dan letakkan berdampingan.
   - Jendela warga: *Keamanan* → *Undang tamu* → isi nama tamu → *Buat undangan* → QR dan kode 6 karakter tampil.
   - Jendela satpam: menu *Tamu* → *Pindai QR* → ketuk nama tamu di "Undangan hari ini" (atau ketik kodenya lalu
     *Periksa kode*) → "Tamu valid". Warga menerima notifikasi "Tamu … sudah masuk".
8. **SOS (dua jendela).**
   - Jendela warga: tombol **SOS** di tengah menu bawah → **tahan 3 detik** (lepas sebelum itu = batal) →
     pilih *Kemalingan* → *Kirim laporan*. Status: "Menunggu satpam…". Di HP: tahan dengan jari sampai lembar
     "Pilih jenis darurat" muncul, lalu angkat jari; lembar tetap terbuka. Tombol *Telepon* pada kontak darurat
     hanya simulasi (tidak menelepon).
   - Jendela satpam: kartu merah "Laporan darurat Kemalingan" muncul tanpa muat ulang → ketuk →
     layar penuh merah → *Terima & menuju*.
   - Jendela warga berubah menjadi "**Pak Joko menuju rumah Anda**". Jendela satpam: *Tandai selesai* →
     status warga menjadi *Selesai*.
9. **Tagihan IPL.** Menu *Tagihan* → *Bayar sekarang* (IPL Desember Rp150.000) → pilih metode → *Saya sudah bayar*
   → *Lunas* + kuitansi. Lalu buka *Laporan kas kawasan* (pemasukan/pengeluaran 6 bulan).
10. **Lapor kerusakan.** *Semua layanan* → *Lapor rusak* → *Lapor kerusakan baru* → pilih kategori, ceritakan
    kerusakannya → *Kirim laporan* → tiket tampil dengan linimasa *Dibuat › Diverifikasi › Dikerjakan › Selesai*.
11. **(Opsional) Pengelola dan mitra.**
    - **Dua tab IPL:** sebelum langkah 9, buka tab kedua ke **http://localhost:3000/app/pengelola**. Ringkasan
      menunjukkan *70 %* tagihan IPL lunas (14 dari 20 unit). Setelah warga membayar di langkah 9, angka di tab
      pengelola berubah sendiri menjadi *75 %* dan C-12 hilang dari "Iuran belum lunas".
    - Di *Tiket & keluhan* pengelola bisa memajukan tiket dari langkah 10; warga melihat linimasanya bergerak
      dan setelah *Selesai* bisa *Konfirmasi selesai + beri nilai*.
    - Portal mitra (`/app/mitra`): *Katalog* → *Bagikan* membuat tautan/QR beratribusi; *Simulasi* menghitung KPR.

Sinkron antarjendela memakai `localStorage` dan event `storage`, jadi kedua jendela harus berada di **peramban
dan profil yang sama**. HP dan laptop yang berbeda tidak saling sinkron.

## Daftar layar dan tangkapan layar

59 rute, 60 id layar (W29 "Ajak teman" memakai rute yang sama dengan P10). Tingkat **D** = bagian alur demo,
**L** = lengkap dengan data contoh. Gambar HP berukuran 390×844 (@2x); gambar pengelola 1366×900.
Rute bertanda contoh memakai parameter: P5 `/app/pembeli/bayar/:itemId`, P11 `/app/pembeli/promo/:id`,
W15 `/app/warga/komunitas/event/:id`.

| Id | Permukaan | Layar | Rute | Tingkat | Gambar |
|---|---|---|---|---|---|
| U1 | Demo | Peluncur demo | `/app/demo` | D | [U1.png](screens/01-demo/U01-peluncur-demo.png) |
| U2 | Demo | Masuk | `/app/masuk` | D | [U2.png](screens/01-demo/U02-masuk.png) |
| P1 | Pembeli | Beranda pembeli | `/app/pembeli` | D | [P1.png](screens/02-pembeli/P01-beranda-pembeli.png) |
| P2 | Pembeli | Progres | `/app/pembeli/progres` | D | [P2.png](screens/02-pembeli/P02-progres.png) |
| P3 | Pembeli | Peta kavling | `/app/pembeli/kavling` | L | [P3.png](screens/02-pembeli/P03-peta-kavling.png) |
| P4 | Pembeli | Bayar | `/app/pembeli/bayar` | D | [P4.png](screens/02-pembeli/P04-bayar.png) |
| P5 | Pembeli | Bayar uang muka | `/app/pembeli/bayar/dp-3` | D | [P5.png](screens/02-pembeli/P05-bayar-uang-muka.png) |
| P6 | Pembeli | Status KPR | `/app/pembeli/kpr` | L | [P6.png](screens/02-pembeli/P06-status-kpr.png) |
| P7 | Pembeli | Pembatalan & refund | `/app/pembeli/pembatalan` | L | [P7.png](screens/02-pembeli/P07-pembatalan-dan-refund.png) |
| P8 | Pembeli | Dokumen | `/app/pembeli/dokumen` | L | [P8.png](screens/02-pembeli/P08-dokumen.png) |
| P9 | Pembeli | Akun pembeli | `/app/pembeli/akun` | L | [P9.png](screens/02-pembeli/P09-akun-pembeli.png) |
| P10/W29 | Pembeli | Ajak teman | `/app/ajak-teman` | L | [P10.png](screens/02-pembeli/P10-ajak-teman.png) |
| P11 | Pembeli | Promo & info developer | `/app/pembeli/promo/promo-1` | L | [P11.png](screens/02-pembeli/P11-promo-dan-info-developer.png) |
| T1 | Transisi | Selamat datang di rumah baru | `/app/selamat-datang` | D | [T1.png](screens/03-serah-terima/T01-selamat-datang-di-rumah-baru.png) |
| W1 | Warga | Beranda warga | `/app/warga` | D | [W1.png](screens/04-warga/W01-beranda-warga.png) |
| W2 | Warga | Keamanan rumah | `/app/warga/keamanan` | D | [W2.png](screens/04-warga/W02-keamanan-rumah.png) |
| W3 | Warga | Kunci pintu | `/app/warga/keamanan/kunci` | D | [W3.png](screens/04-warga/W03-kunci-pintu.png) |
| W4 | Warga | CCTV rumah | `/app/warga/keamanan/cctv-rumah` | D | [W4.png](screens/04-warga/W04-cctv-rumah.png) |
| W5 | Warga | Keamanan kawasan | `/app/warga/keamanan/kawasan` | D | [W5.png](screens/04-warga/W05-keamanan-kawasan.png) |
| W6 | Warga | Gerbang pintar | `/app/warga/keamanan/gerbang` | L | [W6.png](screens/04-warga/W06-gerbang-pintar.png) |
| W7 | Warga | Undang tamu | `/app/warga/keamanan/tamu` | D | [W7.png](screens/04-warga/W07-undang-tamu.png) |
| W8 | Warga | SOS | `/app/warga/sos` | D | [W8.png](screens/04-warga/W08-sos.png) |
| W9 | Warga | Kontak darurat | `/app/warga/sos/kontak` | L | [W9.png](screens/04-warga/W09-kontak-darurat.png) |
| W10 | Warga | Tagihan | `/app/warga/tagihan` | D | [W10.png](screens/04-warga/W10-tagihan.png) |
| W11 | Warga | Riwayat tagihan | `/app/warga/tagihan/riwayat` | L | [W11.png](screens/04-warga/W11-riwayat-tagihan.png) |
| W12 | Warga | Laporan kas kawasan | `/app/warga/tagihan/kas` | L | [W12.png](screens/04-warga/W12-laporan-kas-kawasan.png) |
| W13 | Warga | Bayar & Isi Ulang | `/app/warga/isi-ulang` | L | [W13.png](screens/04-warga/W13-bayar-dan-isi-ulang.png) |
| W14 | Warga | Komunitas | `/app/warga/komunitas` | D | [W14.png](screens/04-warga/W14-komunitas.png) |
| W15 | Warga | Event warga | `/app/warga/komunitas/event/ev-1` | L | [W15.png](screens/04-warga/W15-event-warga.png) |
| W16 | Warga | Kelompok hobi | `/app/warga/komunitas/hobi` | L | [W16.png](screens/04-warga/W16-kelompok-hobi.png) |
| W17 | Warga | Polling warga | `/app/warga/komunitas/polling` | L | [W17.png](screens/04-warga/W17-polling-warga.png) |
| W18 | Warga | Pasar warga | `/app/warga/pasar` | L | [W18.png](screens/04-warga/W18-pasar-warga.png) |
| W19 | Warga | Jasa rumah | `/app/warga/jasa` | L | [W19.png](screens/04-warga/W19-jasa-rumah.png) |
| W20 | Warga | Semua layanan | `/app/warga/layanan` | L | [W20.png](screens/04-warga/W20-semua-layanan.png) |
| W21 | Warga | Lapor kerusakan | `/app/warga/lapor` | D | [W21.png](screens/04-warga/W21-lapor-kerusakan.png) |
| W22 | Warga | Klaim garansi | `/app/warga/garansi` | L | [W22.png](screens/04-warga/W22-klaim-garansi.png) |
| W23 | Warga | Dokumen rumah | `/app/warga/dokumen` | L | [W23.png](screens/04-warga/W23-dokumen-rumah.png) |
| W24 | Warga | Izin renovasi | `/app/warga/renovasi` | L | [W24.png](screens/04-warga/W24-izin-renovasi.png) |
| W25 | Warga | Booking fasilitas | `/app/warga/fasilitas` | L | [W25.png](screens/04-warga/W25-booking-fasilitas.png) |
| W26 | Warga | Energi rumah | `/app/warga/energi` | L | [W26.png](screens/04-warga/W26-energi-rumah.png) |
| W27 | Warga | Notifikasi | `/app/notifikasi` | L | [W27.png](screens/04-warga/W27-notifikasi.png) |
| W28 | Warga | Akun warga | `/app/warga/akun` | L | [W28.png](screens/04-warga/W28-akun-warga.png) |
| S1 | Satpam | Beranda pos | `/app/satpam` | D | [S1.png](screens/05-satpam/S01-beranda-pos.png) |
| S2 | Satpam | Peringatan SOS | `/app/satpam/sos` | D | [S2.png](screens/05-satpam/S02-peringatan-sos.png) |
| S3 | Satpam | Pindai QR tamu | `/app/satpam/tamu` | D | [S3.png](screens/05-satpam/S03-pindai-qr-tamu.png) |
| S4 | Satpam | CCTV kawasan | `/app/satpam/cctv` | L | [S4.png](screens/05-satpam/S04-cctv-kawasan.png) |
| S5 | Satpam | Log patroli | `/app/satpam/patroli` | L | [S5.png](screens/05-satpam/S05-log-patroli.png) |
| K1 | Pengelola | Ringkasan kawasan | `/app/pengelola` | L | [K1.png](screens/06-pengelola/K01-ringkasan-kawasan.png) |
| K2 | Pengelola | Tagihan IPL | `/app/pengelola/ipl` | L | [K2.png](screens/06-pengelola/K02-tagihan-ipl.png) |
| K3 | Pengelola | Tiket & keluhan | `/app/pengelola/tiket` | L | [K3.png](screens/06-pengelola/K03-tiket-dan-keluhan.png) |
| K4 | Pengelola | Pengumuman & agenda | `/app/pengelola/pengumuman` | L | [K4.png](screens/06-pengelola/K04-pengumuman-dan-agenda.png) |
| K5 | Pengelola | Laporan kas | `/app/pengelola/kas` | L | [K5.png](screens/06-pengelola/K05-laporan-kas.png) |
| K6 | Pengelola | Keamanan | `/app/pengelola/keamanan` | L | [K6.png](screens/06-pengelola/K06-keamanan.png) |
| K7 | Pengelola | Mitra layanan & pasar | `/app/pengelola/mitra` | L | [K7.png](screens/06-pengelola/K07-mitra-layanan-dan-pasar.png) |
| M1 | Mitra | Daftar mitra | `/app/mitra/daftar` | L | [M1.png](screens/07-mitra/M01-daftar-mitra.png) |
| M2 | Mitra | Beranda mitra | `/app/mitra` | L | [M2.png](screens/07-mitra/M02-beranda-mitra.png) |
| M3 | Mitra | Katalog proyek | `/app/mitra/katalog` | L | [M3.png](screens/07-mitra/M03-katalog-proyek.png) |
| M4 | Mitra | Rujukan saya | `/app/mitra/rujukan` | L | [M4.png](screens/07-mitra/M04-rujukan-saya.png) |
| M5 | Mitra | Komisi & pencairan | `/app/mitra/komisi` | L | [M5.png](screens/07-mitra/M05-komisi-dan-pencairan.png) |

Keadaan yang terlihat di gambar: jam dibekukan pada Rabu, 25 November 2026 pukul 09.41 WIB; layar warga
ditampilkan sesudah BAST; P5 dengan nomor VA terbuka; W7 dengan QR undangan; W8 setelah SOS diterima satpam;
S2 dengan SOS yang menunggu diterima; S1/S3 dengan satu undangan tamu hari ini; W13 dengan Token listrik dipilih.

## Batasan

- **Data contoh saja.** Semua nama, unit, harga, dan angka bersifat fiktif. Label "Data contoh" ada di peluncur
  demo, Akun pembeli (P9), dan Akun warga (W28).
- **Tanpa backend.** Lapisan layanan (`frontend/src/prototype/services/`) meniru API dengan jeda 200–600 ms dan tidak
  memanggil jaringan. Tidak ada OTP sungguhan; kode 6 angka apa pun diterima.
- **Tanpa integrasi sungguhan.** Tidak tersambung ke perangkat IoT (kunci, kamera, meter energi), bank, VA/QRIS,
  dompet digital, atau biller pulsa/PLN/PDAM. Nomor VA, QR, token, dan struk dibuat acak di peramban. Nama bank hanya
  tampil sebagai data contoh. Tombol *Telepon* tidak memanggil nomor apa pun; prototipe hanya menampilkan catatan
  "Panggilan … disimulasikan di prototipe".
- **Tanggal demo.** Bawaannya tanggal dibekukan pada 25 Nov 2026 dengan jam berjalan (lihat *Tanggal demo*).
- **Penyimpanan per peramban.** Status (pembayaran, kunci, SOS, tamu, tiket, keranjang, polling) disimpan di
  `localStorage` peramban itu saja. Peramban atau perangkat lain punya datanya sendiri. Tombol
  **Reset data contoh** di peluncur mengembalikan semuanya ke awal. Data simpanan dari versi prototipe sebelumnya
  dibuang otomatis sekali saat versi data berubah.
- **Hanya di host yang diizinkan** (lihat *Penjaga host*). Prototipe tidak bisa dibuka dari host produksi.
- **Di luar cakupan prototipe:** service worker milik aplikasi staf (tidak diubah) dan akun/kata sandi bawaan
  aplikasi staf. Sebelum membagikan URL demo publik (`demo.`/`trial.`), ganti dulu semua kata sandi bawaan di
  instance itu.

## Membuat ulang tangkapan layar

Skrip `frontend/scripts/prototype-screens.js` melayani `frontend/build` dengan server http Node bawaan (fallback
SPA), membuka setiap rute di Chromium lewat Playwright, menyimpan PNG ke `docs/prototype/screens/<folder-peran>/<ID>-<judul>.png` (halaman penuh) dan `...--layar.png` (layar pertama), membuat `00-lembar-kontak.png` per folder, `index.json`, dan `README.md`, lalu
mengukur ulang setiap layar di lebar 360 px untuk mencari luapan horizontal. Butuh Playwright (paket npm
`playwright` beserta Chromium-nya) yang terpasang global.

```bash
cd frontend && yarn build
NODE_PATH="$(npm root -g)" node scripts/prototype-screens.js
```

Hasil yang diharapkan diakhiri `59 layar, 0 overflow`. Skrip keluar dengan kode 1 bila ada layar yang meluap di
360 px atau galat halaman. Opsi:

- `--only W8,S2` hanya layar tertentu;
- `--out <folder>` folder keluaran lain;
- `--port 4173` port server lokal (bila terpakai, skrip memilih port bebas);
- `--now 2026-11-25T09:41:00+07:00` jam yang dibekukan di peramban.

Permintaan ke luar `127.0.0.1` diblokir dan dicetak di akhir; prototipe sendiri tidak memuat apa pun dari internet.
Untuk mengoptimalkan PNG (lossless) dan memperkecil halaman penuh ponsel ke lebar 488 px agar folder < 40 MB (perlu Python dengan Pillow), dari akar repo:

```bash
python3 frontend/scripts/optimize-screens.py
```

## Uji

```bash
cd frontend && CI=true npx craco test --watchAll=false src/prototype
```
