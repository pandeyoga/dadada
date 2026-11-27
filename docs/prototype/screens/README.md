# Tangkapan layar prototipe

Tangkapan layar semua halaman prototipe "Rumah Dalam Genggaman", dikelompokkan per peran. Dibuat otomatis oleh `frontend/scripts/prototype-screens.js` dari `frontend/src/prototype/screens.json`.

**Penamaan.** Setiap halaman punya dua berkas di folder perannya: `<ID>-<judul>.png` dan `<ID>-<judul>--layar.png`. ID = huruf peran + nomor dua digit (mis. `W18`); judul ditulis huruf kecil dan disambung tanda hubung.

- **Halaman penuh** (`W18-pasar-warga.png`): seluruh isi halaman dari atas sampai bawah (maksimal 8000 px), menu bawah di dasar gambar. Halaman penuh ponsel diperkecil ke lebar 488 px (sekitar @1,25) agar ukuran folder wajar; dasbor pengelola 1366 px.
- **Layar pertama** (`W18-pasar-warga--layar.png`): yang terlihat sekilas saat halaman dibuka. Ponsel 390×844 @2x; dasbor pengelola 1366×900 @1x.
- `00-lembar-kontak.png` di tiap folder: kumpulan layar pertama untuk dilihat sekilas.
- `index.json`: daftar mesin-baca (ID, judul, penjelasan, rute, peran, jalur berkas) untuk bahan presentasi.

**Membuat ulang** (dari folder `frontend`):

```bash
REACT_APP_BACKEND_URL=http://127.0.0.1:9 yarn build
NODE_PATH="$(npm root -g)" node scripts/prototype-screens.js
python3 scripts/optimize-screens.py
```

## Demo (`01-demo/`)

[Lembar kontak](01-demo/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| U01 | Peluncur demo | Peluncur untuk presentasi: pilih peran, simulasikan serah terima (BAST), atau reset data demo. | `/app/demo` | [halaman penuh](01-demo/U01-peluncur-demo.png), [layar pertama](01-demo/U01-peluncur-demo--layar.png) |
| U02 | Masuk | Masuk dengan nomor WhatsApp dan kode OTP simulasi; kode apa saja diterima. | `/app/masuk` | [halaman penuh](01-demo/U02-masuk.png), [layar pertama](01-demo/U02-masuk--layar.png) |

## Pembeli (`02-pembeli/`)

[Lembar kontak](02-pembeli/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| P01 | Beranda pembeli | Beranda pembeli: perjalanan rumah dari booking sampai BAST, tagihan berikutnya, progres, dan promo. | `/app/pembeli` | [halaman penuh](02-pembeli/P01-beranda-pembeli.png), [layar pertama](02-pembeli/P01-beranda-pembeli--layar.png) |
| P02 | Progres | Linimasa foto progres pembangunan per tahap beserta estimasi serah terima rumah. | `/app/pembeli/progres` | [halaman penuh](02-pembeli/P02-progres.png), [layar pertama](02-pembeli/P02-progres--layar.png) |
| P03 | Peta kavling | Peta kavling kawasan dengan unit milik pembeli disorot, bisa diketuk untuk melihat detail. | `/app/pembeli/kavling` | [halaman penuh](02-pembeli/P03-peta-kavling.png), [layar pertama](02-pembeli/P03-peta-kavling--layar.png) |
| P04 | Bayar | Jadwal cicilan dan riwayat pembayaran uang muka serta angsuran, lengkap dengan status. | `/app/pembeli/bayar` | [halaman penuh](02-pembeli/P04-bayar.png), [layar pertama](02-pembeli/P04-bayar--layar.png) |
| P05 | Bayar uang muka | Pilih metode bayar, dapatkan nomor VA atau kode QRIS, lalu pantau status menunggu hingga lunas. | `/app/pembeli/bayar/dp-3` | [halaman penuh](02-pembeli/P05-bayar-uang-muka.png), [layar pertama](02-pembeli/P05-bayar-uang-muka--layar.png) |
| P06 | Status KPR | Pantau status pengajuan KPR atau SP3K dan lihat jadwal angsuran bulanan. | `/app/pembeli/kpr` | [halaman penuh](02-pembeli/P06-status-kpr.png), [layar pertama](02-pembeli/P06-status-kpr--layar.png) |
| P07 | Pembatalan & refund | Lihat ketentuan, status, dan perkiraan dana kembali bila pembelian dibatalkan (hanya baca). | `/app/pembeli/pembatalan` | [halaman penuh](02-pembeli/P07-pembatalan-dan-refund.png), [layar pertama](02-pembeli/P07-pembatalan-dan-refund--layar.png) |
| P08 | Dokumen | Kumpulan dokumen pembeli: SPR, PPJB, kuitansi, dan berkas KPR yang bisa dibuka kapan saja. | `/app/pembeli/dokumen` | [halaman penuh](02-pembeli/P08-dokumen.png), [layar pertama](02-pembeli/P08-dokumen--layar.png) |
| P09 | Akun pembeli | Profil pembeli, anggota keluarga, serta tanya dan komplain sebelum serah terima. | `/app/pembeli/akun` | [halaman penuh](02-pembeli/P09-akun-pembeli.png), [layar pertama](02-pembeli/P09-akun-pembeli--layar.png) |
| P10 | Ajak teman | Bagikan kode atau tautan ajakan ke teman, pantau status rujukan, dan lihat hadiahnya. | `/app/ajak-teman` | [halaman penuh](02-pembeli/P10-ajak-teman.png), [layar pertama](02-pembeli/P10-ajak-teman--layar.png) |
| P11 | Promo & info developer | Detail promo dan informasi dari developer, lengkap dengan syarat dan masa berlaku. | `/app/pembeli/promo/promo-1` | [halaman penuh](02-pembeli/P11-promo-dan-info-developer.png), [layar pertama](02-pembeli/P11-promo-dan-info-developer--layar.png) |

## Serah terima (`03-serah-terima/`)

[Lembar kontak](03-serah-terima/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| T01 | Selamat datang di rumah baru | Sambutan di rumah baru: hubungkan kunci dan kamera, undang keluarga, isi kontak darurat. | `/app/selamat-datang` | [halaman penuh](03-serah-terima/T01-selamat-datang-di-rumah-baru.png), [layar pertama](03-serah-terima/T01-selamat-datang-di-rumah-baru--layar.png) |

## Warga (`04-warga/`)

[Lembar kontak](04-warga/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| W01 | Beranda warga | Beranda warga: status pintu, kamera dan satpam, tagihan IPL, layanan, pengumuman, dan energi. | `/app/warga` | [halaman penuh](04-warga/W01-beranda-warga.png), [layar pertama](04-warga/W01-beranda-warga--layar.png) |
| W02 | Keamanan rumah | Buka kunci pintu dengan geser, lihat CCTV rumah ringkas, dan baca riwayat akses. | `/app/warga/keamanan` | [halaman penuh](04-warga/W02-keamanan-rumah.png), [layar pertama](04-warga/W02-keamanan-rumah--layar.png) |
| W03 | Kunci pintu | Atur kunci pintu: buat kode sementara untuk tamu atau ART, bagikan lewat WA, lalu cabut. | `/app/warga/keamanan/kunci` | [halaman penuh](04-warga/W03-kunci-pintu.png), [layar pertama](04-warga/W03-kunci-pintu--layar.png) |
| W04 | CCTV rumah | Tonton siaran kamera rumah (simulasi), pilih kamera, putar rekaman per jam, dan atur notifikasi. | `/app/warga/keamanan/cctv-rumah` | [halaman penuh](04-warga/W04-cctv-rumah.png), [layar pertama](04-warga/W04-cctv-rumah--layar.png) |
| W05 | Keamanan kawasan | Pantau CCTV kawasan di gerbang, jalan, dan taman, serta lihat satpam yang sedang bertugas. | `/app/warga/keamanan/kawasan` | [halaman penuh](04-warga/W05-keamanan-kawasan.png), [layar pertama](04-warga/W05-keamanan-kawasan--layar.png) |
| W06 | Gerbang pintar | Cek lokasi di dalam atau luar radius, buka gerbang masuk atau keluar, dan lihat riwayatnya. | `/app/warga/keamanan/gerbang` | [halaman penuh](04-warga/W06-gerbang-pintar.png), [layar pertama](04-warga/W06-gerbang-pintar--layar.png) |
| W07 | Undang tamu | Buat undangan tamu berupa QR sekali pakai dengan jam berlaku, lalu bagikan lewat WhatsApp. | `/app/warga/keamanan/tamu` | [halaman penuh](04-warga/W07-undang-tamu.png), [layar pertama](04-warga/W07-undang-tamu--layar.png) |
| W08 | SOS | Tahan tombol SOS, pilih jenis darurat, lalu pantau satpam yang menuju rumah sampai selesai. | `/app/warga/sos` | [halaman penuh](04-warga/W08-sos.png), [layar pertama](04-warga/W08-sos--layar.png) |
| W09 | Kontak darurat | Kelola daftar kontak darurat yang dihubungi saat tombol SOS ditekan. | `/app/warga/sos/kontak` | [halaman penuh](04-warga/W09-kontak-darurat.png), [layar pertama](04-warga/W09-kontak-darurat--layar.png) |
| W10 | Tagihan | Bayar IPL bulan ini lewat VA, QRIS, e-wallet, atau tautan WA, lalu unduh kuitansinya. | `/app/warga/tagihan` | [halaman penuh](04-warga/W10-tagihan.png), [layar pertama](04-warga/W10-tagihan--layar.png) |
| W11 | Riwayat tagihan | Riwayat tagihan IPL bulan-bulan sebelumnya beserta kuitansi pembayaran. | `/app/warga/tagihan/riwayat` | [halaman penuh](04-warga/W11-riwayat-tagihan.png), [layar pertama](04-warga/W11-riwayat-tagihan--layar.png) |
| W12 | Laporan kas kawasan | Laporan kas kawasan yang transparan: pemasukan dan pengeluaran per bulan. | `/app/warga/tagihan/kas` | [halaman penuh](04-warga/W12-laporan-kas-kawasan.png), [layar pertama](04-warga/W12-laporan-kas-kawasan--layar.png) |
| W13 | Bayar & Isi Ulang | Beli pulsa, paket data, token PLN, atau bayar PDAM, lalu terima token atau struk. | `/app/warga/isi-ulang` | [halaman penuh](04-warga/W13-bayar-dan-isi-ulang.png), [layar pertama](04-warga/W13-bayar-dan-isi-ulang--layar.png) |
| W14 | Komunitas | Pengumuman pengelola dan agenda kegiatan warga dalam satu halaman. | `/app/warga/komunitas` | [halaman penuh](04-warga/W14-komunitas.png), [layar pertama](04-warga/W14-komunitas--layar.png) |
| W15 | Event warga | Detail acara warga: waktu, tempat, deskripsi, dan tombol untuk ikut serta. | `/app/warga/komunitas/event/ev-1` | [halaman penuh](04-warga/W15-event-warga.png), [layar pertama](04-warga/W15-event-warga--layar.png) |
| W16 | Kelompok hobi | Daftar kelompok hobi warga; gabung dan lihat info kelompok. | `/app/warga/komunitas/hobi` | [halaman penuh](04-warga/W16-kelompok-hobi.png), [layar pertama](04-warga/W16-kelompok-hobi--layar.png) |
| W17 | Polling warga | Ikut polling warga, pilih jawaban, dan lihat hasil suara sementara. | `/app/warga/komunitas/polling` | [halaman penuh](04-warga/W17-polling-warga.png), [layar pertama](04-warga/W17-polling-warga--layar.png) |
| W18 | Pasar warga | Belanja produk tetangga dan tenant, isi keranjang, lalu bayar. | `/app/warga/pasar` | [halaman penuh](04-warga/W18-pasar-warga.png), [layar pertama](04-warga/W18-pasar-warga--layar.png) |
| W19 | Jasa rumah | Pesan jasa rumah seperti tukang, kebersihan, galon, dan servis AC dengan jadwal pilihan. | `/app/warga/jasa` | [halaman penuh](04-warga/W19-jasa-rumah.png), [layar pertama](04-warga/W19-jasa-rumah--layar.png) |
| W20 | Semua layanan | Grid lengkap semua layanan aplikasi warga untuk menjangkau fitur yang tidak ada di menu bawah. | `/app/warga/layanan` | [halaman penuh](04-warga/W20-semua-layanan.png), [layar pertama](04-warga/W20-semua-layanan--layar.png) |
| W21 | Lapor kerusakan | Buat tiket kerusakan dengan kategori dan foto, pantau linimasanya, lalu beri rating. | `/app/warga/lapor` | [halaman penuh](04-warga/W21-lapor-kerusakan.png), [layar pertama](04-warga/W21-lapor-kerusakan--layar.png) |
| W22 | Klaim garansi | Ajukan klaim garansi per bagian rumah dan pantau statusnya. | `/app/warga/garansi` | [halaman penuh](04-warga/W22-klaim-garansi.png), [layar pertama](04-warga/W22-klaim-garansi--layar.png) |
| W23 | Dokumen rumah | Dokumen rumah: BAST, status sertifikat, garansi, denah, dan jalur instalasi. | `/app/warga/dokumen` | [halaman penuh](04-warga/W23-dokumen-rumah.png), [layar pertama](04-warga/W23-dokumen-rumah--layar.png) |
| W24 | Izin renovasi | Ajukan izin renovasi ke pengelola dan pantau status persetujuannya. | `/app/warga/renovasi` | [halaman penuh](04-warga/W24-izin-renovasi.png), [layar pertama](04-warga/W24-izin-renovasi--layar.png) |
| W25 | Booking fasilitas | Pilih slot waktu untuk memesan lapangan, aula, atau kolam renang kawasan. | `/app/warga/fasilitas` | [halaman penuh](04-warga/W25-booking-fasilitas.png), [layar pertama](04-warga/W25-booking-fasilitas--layar.png) |
| W26 | Energi rumah | Bandingkan pemakaian listrik dan air bulan ini dengan bulan lalu, plus tips hemat. | `/app/warga/energi` | [halaman penuh](04-warga/W26-energi-rumah.png), [layar pertama](04-warga/W26-energi-rumah--layar.png) |
| W27 | Notifikasi | Notifikasi berjenjang dari Darurat, Keamanan, hingga Info, bisa ditandai sudah dibaca. | `/app/notifikasi` | [halaman penuh](04-warga/W27-notifikasi.png), [layar pertama](04-warga/W27-notifikasi--layar.png) |
| W28 | Akun warga | Profil warga, anggota keluarga dan penyewa dengan hak akses, perangkat, dan pengaturan. | `/app/warga/akun` | [halaman penuh](04-warga/W28-akun-warga.png), [layar pertama](04-warga/W28-akun-warga--layar.png) |

## Satpam (`05-satpam/`)

[Lembar kontak](05-satpam/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| S01 | Beranda pos | Beranda pos satpam: status shift, antrean SOS, dan daftar tamu yang diharapkan hari ini. | `/app/satpam` | [halaman penuh](05-satpam/S01-beranda-pos.png), [layar pertama](05-satpam/S01-beranda-pos--layar.png) |
| S02 | Peringatan SOS | Peringatan SOS layar penuh: terima, menuju lokasi, lalu tandai selesai agar warga tahu. | `/app/satpam/sos` | [halaman penuh](05-satpam/S02-peringatan-sos.png), [layar pertama](05-satpam/S02-peringatan-sos--layar.png) |
| S03 | Pindai QR tamu | Pindai QR tamu (simulasi kamera), lihat valid atau tidak, lalu catat tamu masuk. | `/app/satpam/tamu` | [halaman penuh](05-satpam/S03-pindai-qr-tamu.png), [layar pertama](05-satpam/S03-pindai-qr-tamu--layar.png) |
| S04 | CCTV kawasan | Grid CCTV kawasan untuk memantau gerbang, jalan, dan fasilitas dari pos. | `/app/satpam/cctv` | [halaman penuh](05-satpam/S04-cctv-kawasan.png), [layar pertama](05-satpam/S04-cctv-kawasan--layar.png) |
| S05 | Log patroli | Catat patroli dan kejadian selama shift dalam satu log berurutan. | `/app/satpam/patroli` | [halaman penuh](05-satpam/S05-log-patroli.png), [layar pertama](05-satpam/S05-log-patroli--layar.png) |

## Pengelola (`06-pengelola/`)

[Lembar kontak](06-pengelola/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| K01 | Ringkasan kawasan | Ringkasan kawasan untuk pengelola: tagihan, tiket, keamanan, dan kas dalam satu dasbor. | `/app/pengelola` | [halaman penuh](06-pengelola/K01-ringkasan-kawasan.png), [layar pertama](06-pengelola/K01-ringkasan-kawasan--layar.png) |
| K02 | Tagihan IPL | Pantau tagihan IPL semua unit, status bayarnya, dan kirim pengingat ke penunggak. | `/app/pengelola/ipl` | [halaman penuh](06-pengelola/K02-tagihan-ipl.png), [layar pertama](06-pengelola/K02-tagihan-ipl--layar.png) |
| K03 | Tiket & keluhan | Kelola tiket dan keluhan warga: tinjau, tugaskan, dan perbarui statusnya. | `/app/pengelola/tiket` | [halaman penuh](06-pengelola/K03-tiket-dan-keluhan.png), [layar pertama](06-pengelola/K03-tiket-dan-keluhan--layar.png) |
| K04 | Pengumuman & agenda | Buat pengumuman dan agenda kawasan untuk dilihat seluruh warga. | `/app/pengelola/pengumuman` | [halaman penuh](06-pengelola/K04-pengumuman-dan-agenda.png), [layar pertama](06-pengelola/K04-pengumuman-dan-agenda--layar.png) |
| K05 | Laporan kas | Laporan kas kawasan: pemasukan IPL, pengeluaran, dan saldo per bulan. | `/app/pengelola/kas` | [halaman penuh](06-pengelola/K05-laporan-kas.png), [layar pertama](06-pengelola/K05-laporan-kas--layar.png) |
| K06 | Keamanan | Pantau keamanan kawasan: kejadian SOS, log patroli, dan akses tamu. | `/app/pengelola/keamanan` | [halaman penuh](06-pengelola/K06-keamanan.png), [layar pertama](06-pengelola/K06-keamanan--layar.png) |
| K07 | Mitra layanan & pasar | Kelola mitra layanan dan pedagang pasar warga yang tampil di aplikasi. | `/app/pengelola/mitra` | [halaman penuh](06-pengelola/K07-mitra-layanan-dan-pasar.png), [layar pertama](06-pengelola/K07-mitra-layanan-dan-pasar--layar.png) |

## Mitra (`07-mitra/`)

[Lembar kontak](07-mitra/00-lembar-kontak.png)

| ID | Halaman | Penjelasan | Rute | Berkas |
|---|---|---|---|---|
| M01 | Daftar mitra | Formulir pendaftaran mitra: isi data usaha dan pilih jenis layanan yang ditawarkan. | `/app/mitra/daftar` | [halaman penuh](07-mitra/M01-daftar-mitra.png), [layar pertama](07-mitra/M01-daftar-mitra--layar.png) |
| M02 | Beranda mitra | Beranda mitra: ringkasan rujukan, komisi, dan pintasan ke katalog proyek. | `/app/mitra` | [halaman penuh](07-mitra/M02-beranda-mitra.png), [layar pertama](07-mitra/M02-beranda-mitra--layar.png) |
| M03 | Katalog proyek | Katalog proyek developer lengkap dengan harga dan tautan rujukan untuk dibagikan. | `/app/mitra/katalog` | [halaman penuh](07-mitra/M03-katalog-proyek.png), [layar pertama](07-mitra/M03-katalog-proyek--layar.png) |
| M04 | Rujukan saya | Daftar calon pembeli yang dirujuk mitra beserta tahap prosesnya. | `/app/mitra/rujukan` | [halaman penuh](07-mitra/M04-rujukan-saya.png), [layar pertama](07-mitra/M04-rujukan-saya--layar.png) |
| M05 | Komisi & pencairan | Lihat komisi yang didapat dan ajukan pencairan ke rekening mitra. | `/app/mitra/komisi` | [halaman penuh](07-mitra/M05-komisi-dan-pencairan.png), [layar pertama](07-mitra/M05-komisi-dan-pencairan--layar.png) |
