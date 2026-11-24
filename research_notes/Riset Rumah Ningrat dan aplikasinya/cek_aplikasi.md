# Cek Aplikasi Keluarga Ningrat — Akses & Isi (2026-11-23)

## Pertanyaan: bisakah isi aplikasi dicek / apakah bebas diakses?

**Jawaban: isi aplikasi TIDAK bebas diakses.** Aplikasi terkunci di balik login
penghuni terdaftar. Yang bisa dilihat publik hanya materi di halaman toko
(deskripsi, daftar fitur, screenshot resmi dari pengembang). Isi "di dalam"
(data IPL, CCTV, transaksi, histori gerbang) hanya muncul setelah masuk sebagai
warga yang rumahnya terdaftar — jadi tidak bisa, dan tidak boleh, diakses tanpa
akun yang sah (itu data pribadi orang lain).

Bukti dari layar pembuka: tombol **"Buat Akun"** dan **"Masuk"** — artinya warga
mendaftar sendiri lalu login. Semua layar fitur di screenshot menampilkan data
warga nyata (akun demo "Adhi pratama", RN Jayasampurna Blok F67), yang hanya
tampil setelah login.

## Metode

- **Bisa (sah):** screenshot resmi dari App Store (via iTunes Lookup API publik,
  `id=6752388007`) — 9 gambar, diunduh & dilihat. Deskripsi + release notes resmi.
- **Tidak berhasil:** unduh APK untuk bongkar statis. Aplikasi terlalu niche
  (~1.000 install), tidak ada di mirror umum (apkpure 403, apkcombo tidak punya,
  apkmonk/apkgk nihil). Satu upaya ke API internal mirror diblokir classifier
  (unauthorized access) dan tidak dilanjutkan.
- **Tidak dilakukan (etika/hukum):** login portal pembeli dengan KTP orang,
  memanggil/menyelidiki endpoint backend mereka, mengakses akun warga mana pun.

## Isi aplikasi dari 9 screenshot resmi (UI nyata)

1. **Welcome** — logo, "Selamat Datang di Keluarga Ningrat", tombol Buat Akun / Masuk.
2. **Beranda** — kartu profil (nama + estate + blok F67 + lencana), "ID Project
   CS2412160032", "Tagihan IPL Rp100.000"; grid fitur: Live CCTV, Panic Button,
   Market Place, Service Place, Hobbies, IPL, Event Warga, Lainnya; kartu
   **Security On Duty** (nama satpam, ID, "Shift Pagi 07:00–18:59"); "Promo &
   Aktifitas". Bottom nav: Beranda, Komunitas, (sapa/interaksi), Profil.
3. **Marketplace** — banner, kolom cari, ikon keranjang/pesanan/dompet, kategori
   (Elektronik Rumah, Fashion Wanita/Pria), produk dari tenant lokal (Daily
   Cleaning, Galon Isi Ulang, warung camilan).
4. **Gate System** — alamat estate + "Lokasi Saat Ini" dengan cek geofence
   (badge **"Tidak Sesuai"** = harus berada fisik di lokasi/GPS divalidasi);
   tombol Gate Masuk/Keluar; Buka/Tutup Gate; **Riwayat Akses Gate** (nama warga +
   jam + tanggal).
5. **Ningrat Pay** — PPOB: Pulsa, Paket Data, PLN, PDAM; Riwayat Transaksi dengan
   status (EXPIRED/SUCCESS); contoh beli token PLN.
6. **Pembayaran Berhasil** — rincian: Nomor Tujuan, Provider PLN TOKEN, **Metode
   Pembayaran "VA BANK_PERMATA"**, Total, Token PLN.
7. **SOS Panic Button** — tahan 3 detik; peringatan hukum mengutip **UU ITE
   Pasal 28 ayat (3) UU 1/2024** soal hoax.
8. **Pembayaran IPL** — warga + blok + alamat; "IPL Juni 2026 Rp100.000, Bayar
   sebelum 05 Juni 2026"; metode **Transfer Virtual Account Bank BRI**; tombol Bayar.
9. **Live CCTV** — kamera merek **EZVIZ** (IoT konsumen), kamera bernama (GATE
   BEKASI 3, AREA BANGUN BEKASI 3 CAM3), timestamp, tombol play.

## Catatan teknis untuk benchmark Estora (inferensi dari UI, bukan audit kode)

- **CCTV = EZVIZ** (lini konsumen Hikvision) — kamera jadi/off-the-shelf, kemungkinan
  via SDK/stream EZVIZ, bukan sistem CCTV custom. Murah & cepat dipasang, bukan nilai IT.
- **Pembayaran via Virtual Account banyak bank** (Permata & BRI terlihat) + PPOB
  (PLN/PDAM/pulsa) → kemungkinan pakai **payment gateway/aggregator** (gaya
  Midtrans/Xendit/iPaymu), bukan integrasi satu bank. Relevan untuk fitur
  "booking mandiri + bayar" yang direkomendasikan untuk Estora.
- **Gate dikunci geofence GPS** ("Tidak Sesuai" kalau tidak di lokasi) — kontrol
  anti-penyalahgunaan yang menarik.
- **Registrasi mandiri** ("Buat Akun") — warga daftar sendiri, kemungkinan
  divalidasi ke data unit.
- **Audit log gerbang** dengan nama + waktu — pola jejak audit yang bagus.
- Aplikasi ini **pascahuni murni** (IPL, CCTV, gerbang, SOS, marketplace); tidak
  ada sisi penjualan/KPR/booking di dalamnya (itu di portal web terpisah).
  Menguatkan temuan laporan: Estora kuat di sisi transaksi/penjualan, Rumah
  Ningrat kuat di pascahuni.

Screenshot tersimpan di scratchpad sesi (di luar repo):
`.../scratchpad/rn_shots/ios_01.png` … `ios_09.png`.

## Kelengkapan screenshot (update 2026-11-24)

Google Play juga sudah dicek: 8 screenshot-nya **identik** dengan set iOS
(CCTV, Beranda, Welcome, Pembayaran Berhasil, Marketplace, Ningrat Pay, SOS,
Gate System) — tidak ada layar baru, bahkan kurang layar "Pembayaran IPL" yang
ada di iOS. Jadi tidak ada screenshot Play yang disimpan (duplikat).

**Seluruh halaman yang DIPUBLIKASIKAN sudah ditangkap (9 layar unik):**
1. Welcome (Buat Akun/Masuk) · 2. Beranda · 3. Live CCTV · 4. Gate System ·
5. Ningrat Pay · 6. Pembayaran Berhasil · 7. Pembayaran IPL (iOS) ·
8. SOS Panic Button · 9. Marketplace.

**Halaman yang TIDAK dipublikasikan** (ada di grid/menu tapi terkunci di balik
login warga; tidak bisa di-screenshot tanpa akun sah, dan tidak saya coba):
Service Place, Hobbies/Hobby Community, Event Warga, Complaint Management,
menu "Lainnya", detail Security On Duty, Notifikasi, tab Komunitas, tab Profil,
detail/keranjang/checkout Marketplace, alur "Buat Akun", pemutar video CCTV,
riwayat penuh Gate & Ningrat Pay. Ini batas yang tidak bisa dilewati tanpa
menjadi penghuni terdaftar.
