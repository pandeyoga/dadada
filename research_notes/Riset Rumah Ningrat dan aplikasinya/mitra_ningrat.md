# Analisis "Mitra Ningrat" (Portal Agen/Afiliasi) — 2026-11-24

## Ringkasan

**Mitra Ningrat adalah portal WEB, bukan aplikasi di store.** Alamatnya
`https://mitra.rumahningrat.com` (judul halaman "Mitra Ningrat"; di layar login
menyebut dirinya "Aplikasi Mitra", di landing "Mitra Apps"). Tidak ada aplikasi
"Mitra Ningrat" di Google Play maupun App Store (iTunes search "mitra ningrat"
/ "ningrat mitra" = nihil). Stack server-rendered gaya Laravel (ada token CSRF),
aset `@mdi/font`, `notyf`, `swiper` — konsisten dengan dibangun in-house oleh
IT Trusmi Group.

Fungsinya: **program afiliasi/keagenan resmi** ("jaringan affiliate resmi")
untuk merekrut mitra (agen, influencer, konsumen) agar menjual/mereferensikan
rumah subsidi Rumah Ningrat dengan komisi.

## Akses: mana yang publik, mana yang terkunci

| Halaman | Akses | Isi |
|---|---|---|
| `/` (landing) | Publik | Marketing program mitra: benefit, tools, produk, leaderboard, testimoni, FAQ |
| `/register` | Publik | Wizard 4 tahap: **Akun → Pribadi → Rekening → Media Sosial** |
| `/login` | Publik (form saja) | Email + Password (ada toggle lihat sandi), tombol Daftar/Login |
| `/product/<slug>` | Publik | Detail unit + **simulator KPR** + katalog "Hot Produk" |
| Dashboard mitra | **Terkunci** (perlu login akun mitra) | Tidak diperiksa — butuh akun agen sah |

Catatan: isian wizard tahap 2–4 (Pribadi/Rekening/Media Sosial) baru dimuat
setelah tahap 1 disubmit. **Tidak saya paksa** dengan data palsu, jadi field
detailnya tidak terekam — hanya label tahapannya yang terlihat.

## Isi portal (dari screenshot)

### Registrasi (onboarding mitra)
Wizard 4 langkah. Langkah **Akun**: Nama Lengkap, Nama Panggilan, Username
(otomatis), Email, Atur Kata Sandi + Konfirmasi, Nomor WhatsApp. Label langkah
berikutnya: **Pribadi** (data pribadi/kemungkinan KTP), **Rekening** (rekening
bank — untuk pencairan komisi), **Media Sosial** (akun sosial — untuk
influencer/atribusi). Kontak: (021) 895-6500, halo@rumahningrat.com, Jl. H.
Abbas No. 48 Trusmi Kulon Weru, jam 08.00–20.00 WIB.

### Benefit yang diiklankan
Komisi Berjenjang (tiered commission), Akses Awal Produk (early access),
Dukungan Pemasaran Bersama (co-marketing), Sesi Pelatihan & Workshop, Hadiah
Pencapaian Kinerja (bonus + gadget/liburan), Garansi Kepuasan 30 Hari, Poin
Loyalitas & Diskon, Dukungan Prioritas 24/7, E-Book Panduan, **Instan BIC**
(BI Checking cepat untuk konsumen).

### Tools untuk mitra (bagian "Mendorong Kinerja Mitra Melalui Teknologi")
- **Landing Page Personal / Website Pribadi untuk Mitra** — tiap mitra dapat
  microsite berbranding sendiri dengan listing & identitas profesional.
- Fitur: Tracking Progress User, User Engagement, Bank Content Siap Upload
  (bank materi siap repost), Listing Product, Setting Product, Personal
  Website Branding.
- **"Mitra Apps untuk Monitoring Proses Referral"** — pantau aktivitas
  penjualan & performa referral real-time (ditampilkan sebagai mockup HP).

### Halaman produk + simulator KPR (publik, bisa di-share)
- Header: Type 30/60, Rp166.000.000, tombol **Booking Sekarang**.
- Detail Hunian (tab): Fasilitas Rumah / Fasilitas Umum / Spesifikasi /
  Kelebihan — 2 KT, 1 KM, LB 30 m²/LT 60 m², 1 carport.
- Detail Lokasi (peta — kemungkinan Leaflet; render kosong di screenshot).
- **Simulator "Temukan Estimasi Cicilan Terbaik"**: input Harga Properti
  (Rp185.000.000), Down Payment (Rp9.250.000), Jangka Waktu (20 Tahun),
  Bunga Efektif (6,5%/th) → tombol **Hitung** → **"Perkiraan Angsuran
  Perbulan Rp1.226.667, dari Total Pinjaman Rp184.000.000"** + logo
  **BTN, BNI, Mandiri**. Dokumen wajib ditandai: KTP, Kartu Keluarga,
  KTP Pasangan.
- Tombol **Share** (bagikan link produk — kemungkinan beratribusi ke mitra).
- Katalog "Hot Produk": grid kartu per proyek dengan jumlah listing
  (21/18/20/16/10 Listing), filter Tipe Rumah + Cari, pagination 1–6.
  Semua Rp166.000.000 (Majalengka, Getasan/Cirebon, Plumbon, Subang, Klayan).

### Leaderboard & sebaran produk
- Leaderboard: **Via Nurafiani Kosasih** (#1 Mitra Cirebon, 36 listing),
  **Saeful Anam** (#1 Mitra Indramayu, 1 listing).
- Sebaran: Cirebon 23, Kuningan 4, Bekasi 3, Majalengka 2, + Indramayu,
  Kendal, Subang.

## Catatan teknis / tata kelola

- **In-house, web-based**, bukan native app → cepat iterasi, tapi tidak ada
  pengalaman mobile khusus untuk agen.
- Nomor kontak (021) = Jakarta, beda dari HQ Cirebon; email `halo@` beda dari
  `admin@rumahningrat.com` di situs utama → kanal tersebar.
- Sebagian teks FAQ/benefit tampak **templated/placeholder** ("prosedur
  pembelian produk atau layanan", "MoU", "serah terima akhir", "Garansi Purna
  Jual 12 bulan", "Garansi Kepuasan 30 Hari / pengembalian dana penuh") —
  tidak pas untuk jual-beli rumah subsidi, kemungkinan sisa template generik.
- Daftar penghargaan (BTN 2017–2021) lebih masuk akal dari placeholder di
  homepage, tapi masih memuat "Best Selling Non Subsidiez 2018".

## Relevansi untuk Estora/SIPRO

Estora sudah punya konsep mitra (jenis `referral_pembeli` / `influencer`,
atribusi, fee dari peristiwa transaksi, pra-skrining SLIK). Yang **menonjol**
di Mitra Ningrat dan layak dipertimbangkan:

1. **Self-registration mitra** + capture rekening bank (payout komisi) +
   akun media sosial (atribusi influencer) dalam satu wizard.
2. **Microsite/landing page personal per mitra** dengan listing sendiri +
   **bank konten siap-share** → distribusi dipimpin agen.
3. **Halaman produk publik yang bisa di-share** dengan **simulator KPR**
   tertanam dan tombol Share beratribusi — pintu masuk lead dari jaringan agen.
4. **Gamifikasi**: leaderboard, jumlah listing, komisi berjenjang, poin
   loyalitas, bonus kinerja.
5. **Instan BI Checking** yang diekspos ke mitra (Estora punya pra-skrining
   SLIK — bisa dibuka sebagai alat mitra).

Keterbatasan analisis: dashboard mitra (setelah login) tidak diperiksa; field
wizard tahap 2–4 tidak terekam (tidak submit data); peta lokasi render kosong;
sebagian copy tampak template.

## Berkas screenshot (durabel di repo)

`research_notes/Riset Rumah Ningrat dan aplikasinya/screenshots/`
- `mitra/` — mitra_01_landing, mitra_02_register (tahap Akun), mitra_03_login,
  mitra_04_product (simulator+katalog), mitra_05..07 (tab Pribadi/Rekening/
  Media Sosial — sama dengan tahap Akun, penanda tab berpindah).
- `keluarga_ningrat/` — ios_01..09 (aplikasi penghuni, dari App Store).
