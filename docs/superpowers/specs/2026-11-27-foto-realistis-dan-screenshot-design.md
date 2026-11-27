# Foto realistis dan screenshot rapi — desain singkat

Tanggal: 27 Nov 2026 · Prototipe "Rumah Dalam Genggaman" (`frontend/src/prototype/`) · Tenggat lomba 30 Nov 2026

## Maksud
Pemilik produk ingin prototipe terlihat sungguhan di depan juri BTN Housingpreneur: semua gambar placeholder (ilustrasi SVG) diganti foto realistis, lalu semua halaman di-screenshot ulang dan disusun rapi dengan nama yang mudah dicari untuk berkas lomba.

## Sasaran
1. ±40 slot gambar diganti foto, disimpan **lokal** (tanpa URL luar):
   - Pasar warga (12): nasi kuning, brownies kukus, keripik singkong pedas, es kopi susu botol, kopi susu gula aren, bibit cabai rawit, pot gerabah, sprei batik, telur ayam kampung (10 butir), gantungan kunci rajut, beras 5 kg, paket laundry.
   - Progres bangun (6): lahan, pondasi, dinding bata, kusen pintu-jendela, rangka atap, plester/lantai — juga dipakai sebagai foto contoh di Lapor kerusakan (W21).
   - Unit katalog mitra (3): tipe 30/60, 36/72, 45/90 — rumah tapak sederhana bergaya perumahan Indonesia.
   - Promo (3): akad/tanda tangan dokumen (tangan saja), kanopi & pagar rumah, ajak tetangga (kunci rumah/serah kunci, tanpa wajah).
   - CCTV (8): teras depan, taman belakang, gerbang utama, pos satpam, taman bermain, jalan blok, lapangan serbaguna, gerbang belakang — tampilan ala CCTV (sedikit pudar/kontras) dengan lapisan LIVE + jam yang sudah ada.
   - Fasilitas (4): lapangan serbaguna, musala, balai warga, taman bermain — foto kecil menggantikan ikon di W25.
2. Foto rumah/progres/unit/promo diberi label kecil **"Foto ilustrasi"** (pilihan A pemilik produk: foto stok, bukan proyek asli). CCTV tetap berlabel simulasi.
3. Screenshot **semua halaman** (59 rute) **satu halaman penuh** sampai bawah, disusun per peran dengan nama jelas, plus daftar isi.

## Bukan sasaran
Avatar inisial, ilustrasi dokumen, logo, ikon, fitur baru, teks/konten selain label "Foto ilustrasi".

## Anti-sasaran (gagal walau jalan)
- Gambar dimuat dari URL luar (hotlink).
- Wajah orang yang dikenali, apalagi dipakai sebagai warga bernama.
- Logo/merek dagang terlihat jelas (kemasan, papan nama perumahan lain).
- Foto rumah tanpa label sehingga terkesan proyek Estora asli.
- Ukuran repo membengkak (target total foto ≤ 6 MB).

## Batasan
- Sumber: **Pexels** (lisensi Pexels: bebas dipakai komersial, tanpa wajib atribusi, boleh diubah). Kredit tetap dicatat di `docs/prototype/FOTO-KREDIT.md` (berkas, URL halaman Pexels, fotografer).
- Simpan di `frontend/public/rdg/foto/<kategori>/<nama>.jpg`, sisi panjang ≤ 900 px (CCTV dipotong 16:9 960×540), JPEG kualitas ±78, ≤ 150 KB per foto.
- Aturan lama tetap: Bahasa Indonesia, kontras ≥ 4,5:1, tidak ada kata "Ningrat", semua tes lulus, `59 layar, 0 overflow`.

## Pendekatan
1. **Pexels via CDN, ID dicari lewat pencarian web — dipilih.** CDN Pexels bisa diakses dari lingkungan ini, lisensinya paling longgar, dan banyak foto bernuansa Indonesia.
2. Wikimedia Commons — lebih banyak foto khas Indonesia, tetapi lisensi CC BY-SA wajib atribusi di aplikasi, dan API-nya sedang membalas 429 di lingkungan ini. Tidak dipakai.
3. Foto buatan AI — tidak ada alat pembuat gambar di lingkungan ini. Tidak dipakai.
(Unsplash terblokir tantangan anti-bot; Openverse dibatasi ±11 jam.)

## Rancangan
- **Satu peta foto** `frontend/src/prototype/lib/photos.js`: kunci yang sudah dipakai fixture (`market/nasi-kuning`, `progress/atap`, `unit/tipe-36`, `facility/lapangan`, `promo/pr-1`, `cctv/teras`…) → `{ src, alt, illustrative }`.
- **Satu komponen** `components/Photo.js`: `<img loading="lazy">` object-cover, alt Bahasa Indonesia, chip "Foto ilustrasi" bila `illustrative`, dan **fallback ke SVG lama** bila berkas gagal dimuat. Komponen yang ada (StageIllustration, PromoIllustration, MarketIllustration, UnitArt, TicketPhoto, CameraView) mendelegasikan ke sini; SVG tetap ada sebagai cadangan.
- Tes: setiap kunci `img` di fixture punya foto; semua `src` diawali `/rdg/foto/`; setiap berkas ada di `frontend/public`; alt tidak kosong.
- **Screenshot** (`frontend/scripts/prototype-screens.js`): halaman penuh — tinggi viewport disetel ke tinggi dokumen sebelum memotret supaya bilah navigasi bawah tetap di bawah, bukan menimpa tengah. Struktur:
  ```
  docs/prototype/screens/
    README.md                (daftar isi: ID, judul, rute, berkas)
    01-demo/       U01-peluncur-demo.png, U02-masuk.png
    02-pembeli/    P01-beranda-pembeli.png … P11-promo.png
    03-serah-terima/ T01-selamat-datang.png
    04-warga/      W01-beranda-warga.png … W29-ajak-teman.png
    05-satpam/     S01-beranda-pos.png …
    06-pengelola/  K01-ringkasan.png … (1366 px)
    07-mitra/      M01-daftar-mitra.png …
    (setiap folder: 00-lembar-kontak.png)
  ```
  Nama = ID dua digit + slug judul dari `screens.json` (huruf kecil, tanpa aksen, tanda hubung). Berkas lama yang datar (`W18.png` dst.) dihapus; tautan README demo diperbarui.

## Diserahkan ke builder
Pilihan foto persisnya, potongan/crop, gaya filter CCTV, posisi chip "Foto ilustrasi", dan slug yang terlalu panjang boleh dipendekkan asal tetap jelas.
