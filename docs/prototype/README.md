# Rumah Dalam Genggaman — prototipe aplikasi penghuni Estora

Prototipe **frontend saja** untuk aplikasi penghuni Estora: satu aplikasi yang menemani pembeli rumah sejak
booking sampai serah terima (Mode Pembeli), lalu otomatis berganti menjadi aplikasi warga setelah BAST (Mode Warga),
ditambah aplikasi satpam, dasbor pengelola kawasan, dan portal mitra. Semua angka dan nama adalah **data contoh**
dari proyek fiktif "Estora Residence" (warga utama Rina Ayu, Blok C-12, rumah subsidi FLPP tipe 36/72).

- Kode: `frontend/src/prototype/` (rute `/app/*`, dimuat terpisah dari aplikasi staf).
- Rancangan: `docs/superpowers/specs/2026-11-25-aplikasi-penghuni-prototype-design.md`.
- Tangkapan layar semua layar: `docs/prototype/screens/` (daftar lengkap di bawah).

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
| U1 | Demo | Peluncur demo | `/app/demo` | D | [U1.png](screens/U1.png) |
| U2 | Demo | Masuk | `/app/masuk` | D | [U2.png](screens/U2.png) |
| P1 | Pembeli | Beranda pembeli | `/app/pembeli` | D | [P1.png](screens/P1.png) |
| P2 | Pembeli | Progres | `/app/pembeli/progres` | D | [P2.png](screens/P2.png) |
| P3 | Pembeli | Peta kavling | `/app/pembeli/kavling` | L | [P3.png](screens/P3.png) |
| P4 | Pembeli | Bayar | `/app/pembeli/bayar` | D | [P4.png](screens/P4.png) |
| P5 | Pembeli | Bayar uang muka | `/app/pembeli/bayar/dp-3` | D | [P5.png](screens/P5.png) |
| P6 | Pembeli | Status KPR | `/app/pembeli/kpr` | L | [P6.png](screens/P6.png) |
| P7 | Pembeli | Pembatalan & refund | `/app/pembeli/pembatalan` | L | [P7.png](screens/P7.png) |
| P8 | Pembeli | Dokumen | `/app/pembeli/dokumen` | L | [P8.png](screens/P8.png) |
| P9 | Pembeli | Akun pembeli | `/app/pembeli/akun` | L | [P9.png](screens/P9.png) |
| P10/W29 | Pembeli | Ajak teman | `/app/ajak-teman` | L | [P10.png](screens/P10.png) |
| P11 | Pembeli | Promo & info developer | `/app/pembeli/promo/promo-1` | L | [P11.png](screens/P11.png) |
| T1 | Transisi | Selamat datang di rumah baru | `/app/selamat-datang` | D | [T1.png](screens/T1.png) |
| W1 | Warga | Beranda warga | `/app/warga` | D | [W1.png](screens/W1.png) |
| W2 | Warga | Keamanan rumah | `/app/warga/keamanan` | D | [W2.png](screens/W2.png) |
| W3 | Warga | Kunci pintu | `/app/warga/keamanan/kunci` | D | [W3.png](screens/W3.png) |
| W4 | Warga | CCTV rumah | `/app/warga/keamanan/cctv-rumah` | D | [W4.png](screens/W4.png) |
| W5 | Warga | Keamanan kawasan | `/app/warga/keamanan/kawasan` | D | [W5.png](screens/W5.png) |
| W6 | Warga | Gerbang pintar | `/app/warga/keamanan/gerbang` | L | [W6.png](screens/W6.png) |
| W7 | Warga | Undang tamu | `/app/warga/keamanan/tamu` | D | [W7.png](screens/W7.png) |
| W8 | Warga | SOS | `/app/warga/sos` | D | [W8.png](screens/W8.png) |
| W9 | Warga | Kontak darurat | `/app/warga/sos/kontak` | L | [W9.png](screens/W9.png) |
| W10 | Warga | Tagihan | `/app/warga/tagihan` | D | [W10.png](screens/W10.png) |
| W11 | Warga | Riwayat tagihan | `/app/warga/tagihan/riwayat` | L | [W11.png](screens/W11.png) |
| W12 | Warga | Laporan kas kawasan | `/app/warga/tagihan/kas` | L | [W12.png](screens/W12.png) |
| W13 | Warga | Bayar & Isi Ulang | `/app/warga/isi-ulang` | L | [W13.png](screens/W13.png) |
| W14 | Warga | Komunitas | `/app/warga/komunitas` | D | [W14.png](screens/W14.png) |
| W15 | Warga | Event warga | `/app/warga/komunitas/event/ev-1` | L | [W15.png](screens/W15.png) |
| W16 | Warga | Kelompok hobi | `/app/warga/komunitas/hobi` | L | [W16.png](screens/W16.png) |
| W17 | Warga | Polling warga | `/app/warga/komunitas/polling` | L | [W17.png](screens/W17.png) |
| W18 | Warga | Pasar warga | `/app/warga/pasar` | L | [W18.png](screens/W18.png) |
| W19 | Warga | Jasa rumah | `/app/warga/jasa` | L | [W19.png](screens/W19.png) |
| W20 | Warga | Semua layanan | `/app/warga/layanan` | L | [W20.png](screens/W20.png) |
| W21 | Warga | Lapor kerusakan | `/app/warga/lapor` | D | [W21.png](screens/W21.png) |
| W22 | Warga | Klaim garansi | `/app/warga/garansi` | L | [W22.png](screens/W22.png) |
| W23 | Warga | Dokumen rumah | `/app/warga/dokumen` | L | [W23.png](screens/W23.png) |
| W24 | Warga | Izin renovasi | `/app/warga/renovasi` | L | [W24.png](screens/W24.png) |
| W25 | Warga | Booking fasilitas | `/app/warga/fasilitas` | L | [W25.png](screens/W25.png) |
| W26 | Warga | Energi rumah | `/app/warga/energi` | L | [W26.png](screens/W26.png) |
| W27 | Warga | Notifikasi | `/app/notifikasi` | L | [W27.png](screens/W27.png) |
| W28 | Warga | Akun warga | `/app/warga/akun` | L | [W28.png](screens/W28.png) |
| S1 | Satpam | Beranda pos | `/app/satpam` | D | [S1.png](screens/S1.png) |
| S2 | Satpam | Peringatan SOS | `/app/satpam/sos` | D | [S2.png](screens/S2.png) |
| S3 | Satpam | Pindai QR tamu | `/app/satpam/tamu` | D | [S3.png](screens/S3.png) |
| S4 | Satpam | CCTV kawasan | `/app/satpam/cctv` | L | [S4.png](screens/S4.png) |
| S5 | Satpam | Log patroli | `/app/satpam/patroli` | L | [S5.png](screens/S5.png) |
| K1 | Pengelola | Ringkasan kawasan | `/app/pengelola` | L | [K1.png](screens/K1.png) |
| K2 | Pengelola | Tagihan IPL | `/app/pengelola/ipl` | L | [K2.png](screens/K2.png) |
| K3 | Pengelola | Tiket & keluhan | `/app/pengelola/tiket` | L | [K3.png](screens/K3.png) |
| K4 | Pengelola | Pengumuman & agenda | `/app/pengelola/pengumuman` | L | [K4.png](screens/K4.png) |
| K5 | Pengelola | Laporan kas | `/app/pengelola/kas` | L | [K5.png](screens/K5.png) |
| K6 | Pengelola | Keamanan | `/app/pengelola/keamanan` | L | [K6.png](screens/K6.png) |
| K7 | Pengelola | Mitra layanan & pasar | `/app/pengelola/mitra` | L | [K7.png](screens/K7.png) |
| M1 | Mitra | Daftar mitra | `/app/mitra/daftar` | L | [M1.png](screens/M1.png) |
| M2 | Mitra | Beranda mitra | `/app/mitra` | L | [M2.png](screens/M2.png) |
| M3 | Mitra | Katalog proyek | `/app/mitra/katalog` | L | [M3.png](screens/M3.png) |
| M4 | Mitra | Rujukan saya | `/app/mitra/rujukan` | L | [M4.png](screens/M4.png) |
| M5 | Mitra | Komisi & pencairan | `/app/mitra/komisi` | L | [M5.png](screens/M5.png) |

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
SPA), membuka setiap rute di Chromium lewat Playwright, menyimpan PNG ke `docs/prototype/screens/<id>.png`, lalu
mengukur ulang setiap layar di lebar 360 px untuk mencari luapan horizontal. Butuh Playwright (paket npm
`playwright` beserta Chromium-nya) yang terpasang global.

```bash
cd frontend && yarn build
NODE_PATH="$(npm root -g)" node scripts/prototype-screens.js
```

Hasil yang diharapkan diakhiri `59 layar, 0 overflow`. Skrip keluar dengan kode 1 bila ada layar yang meluap di
360 px atau galat halaman. Opsi:

- `--only W8,S2` hanya layar tertentu;
- `--full` tangkapan halaman penuh (untuk pemeriksaan visual), bukan hanya layar pertama;
- `--out <folder>` folder keluaran lain;
- `--port 4173` port server lokal (bila terpakai, skrip memilih port bebas);
- `--now 2026-11-25T09:41:00+07:00` jam yang dibekukan di peramban.

Permintaan ke luar `127.0.0.1` diblokir dan dicetak di akhir; prototipe sendiri tidak memuat apa pun dari internet.
Untuk mengecilkan PNG tanpa mengubah gambar (perlu Python dengan Pillow), dari akar repo:

```bash
python3 -c "import glob; from PIL import Image; [Image.open(f).save(f, optimize=True) for f in glob.glob('docs/prototype/screens/*.png')]"
```

## Uji

```bash
cd frontend && CI=true npx craco test --watchAll=false src/prototype
```
