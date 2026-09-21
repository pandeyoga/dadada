# Audit KN — Master produk, varian, R&D, galeri, dan mockup AI

Tanggal: 2026-09-06  
Sumber: https://github.com/snakissb/KN  
Branch/commit: `main` / `0bfdf1aec6b82578527a855f85fc52d181eb3af5`  
Lingkup: **audit saja; belum ada perubahan kode aplikasi atau data**.

## Kesimpulan
Kritik pengguna didukung kode: fondasi induk dan SKU varian sudah tersedia, namun pengelolaannya belum setara alur katalog e-commerce dengan kombinasi atribut dan galeri per varian. R&D masih melahirkan SKU dengan kontrak berbeda. Foto produk masih satu URL. Galeri desain/AI sudah ada, tetapi bukan galeri varian yang digunakan sales. Karena itu mengganti layout saja tidak cukup.

## Metode dan keterbatasan
- Salinan sumber diaudit terpisah di `/tmp/kn-audit` tanpa menjalankan server KN, startup/seed, migrasi, API mutasi, maupun provider AI.
- Membaca implementasi aktif dan pembanding riwayat; catatan sesi lama bukan bukti fitur masih memenuhi kebutuhan baru.
- Testing agent melakukan verifikasi statis independen dan menjalankan fungsi terisolasi dengan input sintetis. Tidak mengakses database.
- Tampilan dijelaskan dari struktur komponen React; **belum ada inspeksi visual browser KN**, ukuran layar nyata, atau pengujian akses akun aktif.
- Konfigurasi AI/izin tersimpan dan jumlah data nyata tidak diperiksa. Risiko akses dan lifecycle di bawah bersumber dari kode, bukan klaim kebocoran/transaksi yang sudah terjadi.
- Aplikasi preview `/app` masih starter, bukan repo KN. Tidak diuji seolah-olah merupakan KN.

## Yang sudah tersedia dan perlu dipertahankan
- `product_templates` sebagai induk; `products.template_id` sebagai tautan. SKU tetap unit transaksi/stok/roll/RFID.
- Generator kartesian backend membaca axis generik dan menyimpan `variant_attrs`.
- Pengelompokan katalog POS dan pemilih varian desktop/mobile.
- Gerbang lifecycle R&D untuk SKU yang memiliki status eksplisit.
- Galeri desain mempunyai `files[]`, unggahan, versi/desain, `product_id` opsional dan ilustrasi AI.
- Integrasi Gemini dengan mode mockup/modify. Tidak perlu menganggap fitur AI belum ada sama sekali.

## Temuan utama dengan bukti

### A01 — R&D belum mengeluarkan keluarga produk dan kombinasi varian (P0)
`SpecInput` menyimpan satu `target`, satu `color_target`, satu desain; tidak ada pilihan induk atau matriks kombinasi. `approve_spec` membuat tepat satu dokumen produk melalui `_product_draft`, lalu menyimpan satu `product_id` pada spesifikasi.

Produk hasil R&D tidak memuat `template_id`, `variant_attrs`, `image` atau koleksi media. Ada `design_id` dan `design_version`, tetapi tidak ada pengaitan galeri yang dikonsumsi katalog. `ensure_parent` tidak dipanggil di jalur ini; pemanggil aktifnya adalah POST products dan reparasi manual.

Bukti: `backend/schemas_rnd.py:44-87`; `backend/services/rnd_spec_service.py:87-122,259-288`; `frontend/src/features/rnd/SpecFormModal.jsx:52-109`.

Dampak: produk dari R&D tidak otomatis menjadi anggota keluarga varian, dan visual desain tidak otomatis tampil sebagai foto varian di sales.

### A02 — Pengelolaan master belum berupa etalase induk + editor varian terpadu (P1)
Master menampilkan record per SKU dengan teks, atribut dan tombol pengelolaan; editor produk tunggal terpisah dari modul template. Tampilan template adalah daftar induk di kiri dan tabel SKU/nama/atribut/harga di kanan. Tidak ada galeri foto atau editor media per baris varian pada layar template.

Bukti: `frontend/src/features/admin/AdminView.jsx:405-466`; `frontend/src/features/sales/ProductTemplatesView.jsx:122-219`.

Penilaian ini berdasarkan kode struktur UI, bukan screenshot aplikasi berjalan. Etalase POS yang sudah ada tidak sama dengan pengelolaan master berorientasi induk.

### A03 — Pembuatan dan pemilihan atribut tidak fleksibel end-to-end (P0/P1)
Backend menerima axis generik, tetapi UI hanya menawarkan preset **warna, grade, lebar**. Tidak tersedia kontrol menambah jenis atribut seperti ukuran/material sendiri.

Pemilih sales `deriveAxisOptions`/`resolveVariant` hanya menggunakan warna+grade. Saat axis mode aktif, dua SKU dengan warna dan grade sama tetapi lebar/material berbeda tidak dapat dibedakan lewat pilihan tambahan. Resolver mengambil kandidat pertama. Pada mode daftar cadangan semua SKU bisa ditampilkan, tetapi label utamanya tetap warna/grade dan tidak menjamin kombinasi jelas.

Bukti: `frontend/src/features/sales/ProductTemplatesView.jsx:26-30,363-394`; `frontend/src/utils/variants.js:43-99`; `frontend/src/components/ProductQuickView.jsx:47-51,110-129`; `frontend/src/features/sales/mobile/MobileQuickView.jsx:71-92`.

Reproduksi terisolasi: dua kandidat Merah/A (`SKU-MER-A-115-COT` dan `SKU-MER-A-150-POLY`) menghasilkan pilihan pertama tanpa pembeda lebar/material. Ini membuktikan ambiguitas resolver, bukan membuktikan transaksi pelanggan salah telah terjadi.

### A04 — Foto masih satu URL per varian (P1)
`ProductPayload.image` dan template `image` adalah string tunggal. Form master hanya menyediakan satu input URL beserta pratinjau. Generator menyalin gambar induk yang sama ke semua varian. Quickview desktop/mobile hanya merender satu gambar.

Tidak ditemukan alur master produk untuk banyak unggahan per SKU, pemilihan cover, pengurutan, zoom galeri, atau pengelompokan foto asli/detail/mockup.

Bukti: `backend/schemas.py:199-204,223-224`; `backend/routers/products.py:133-142`; `backend/services/product_template_service.py:241`; `frontend/src/features/admin/products/ProductMasterForm.jsx:364-383`; `frontend/src/components/ProductQuickView.jsx:93`; `frontend/src/features/sales/mobile/MobileQuickView.jsx:64`.

Catatan: dukungan banyak file memang ada di galeri desain, namun itu tidak sama dengan dukungan galeri media per kombinasi di master/sales.

### A05 — Mockup AI tersedia, tetapi belum menjadi media varian siap dipresentasikan (P1)
Galeri desain dapat menyimpan ilustrasi `ai_illustration` mode mockup atau modify, dengan metadata sumber/prompt/model. Galeri juga punya `product_id` opsional. Namun hasil AI tetap berada di `design_gallery.files`, tidak otomatis menjadi media SKU dan tidak dibaca quickview sales.

Bukti: `backend/schemas_design_gallery.py:21,69-72`; `backend/services/design_gallery_service.py:384-431`; `backend/services/gemini_image_service.py:20-26,169-193`.

**MODE DEMO bersyarat:** jika key tidak tersedia, kode menggunakan gambar lokal bertanda demo, bukan panggilan model AI. Bila key ada, jalur SDK Gemini tersedia. Status konfigurasi dan keberhasilan API live belum diperiksa; jangan menyatakan AI saat ini aktif atau mati.

Usulan: gunakan sumber foto/artwork terpilih, tautkan hasil ke kombinasi SKU tertentu, labeli sebagai ilustrasi, lalu butuhkan persetujuan manusia sebelum sales menampilkan. AI tidak menjamin kesesuaian warna/material produk fisik.

### A06 — Aturan induk wajib tidak konsisten di seluruh jalur (P0)
`ensure_parent` mencoba menjamin induk hidup pada pembuatan produk langsung. Tetapi delete template dan detach justru mengosongkan `template_id`. PATCH products juga menerima `template_id` tanpa memvalidasi keberadaan induk. R&D menghindari helper tersebut. Reparasi yatim adalah aksi manual, bukan pengaman universal.

Bukti: `backend/routers/products.py:118-123,133-186`; `backend/services/product_template_service.py:128-143,274-278`; `backend/services/product_variant_service.py:72-117`.

Kontradiksi tambahan: `ensure_parent` mengirim axis dengan `values[]`, sementara normalisasi hanya membaca `options[]`. Uji fungsi menunjukkan hasil axis kosong. Normalisasi juga membuang `hex` yang dikirim UI, sehingga swatch tidak diwariskan oleh generator sesuai harapan.

Bukti fungsi: `backend/services/product_variant_service.py:88`; `backend/services/product_template_service.py:80-97,209-212`; `/app/test_reports/isolated_normalize_axes_result.json`.

### A07 — Generator varian melewati penetapan lifecycle produk baru (P0)
Produk hasil generator tidak mempunyai `lifecycle`, sedangkan `rnd_gate.lifecycle_of` menganggap lifecycle kosong sebagai `produksi` untuk kompatibilitas data lama. Generator tidak menerapkan pengaturan default produk baru sebagaimana POST products.

Bukti: `backend/services/product_template_service.py:224-245`; `backend/services/rnd_gate.py:69-76,124-130`; `backend/routers/products.py:110-113`.

Dampak: varian baru diklasifikasikan boleh dipesan oleh gerbang lifecycle tanpa melalui status R&D eksplisit. Ini risiko kebijakan; belum diuji dengan transaksi nyata atau konfigurasi pengguna.

### A08 — Jalur template belum memakai pengamanan setara katalog products (P0)
`/products` membatasi eksklusivitas sales/lini serta menghapus HPP untuk peran non-cost. `/product-templates` dan detail/summary hanya memeriksa izin `product.view`, lalu membaca template/varian tanpa guard pembanding tersebut. Detail mengembalikan dokumen varian, termasuk field biaya jika tersimpan. Summary mengumpulkan stok tanpa konteks pengguna pada service.

Izin bawaan sales mencakup product.view. Tidak ditemukan guard global pengganti; konfigurasi permission yang tersimpan belum diperiksa.

Bukti: `backend/routers/products.py:25-37,67`; `backend/routers/product_templates.py:17-50`; `backend/services/product_template_service.py:156-177`; `backend/services/product_variant_service.py:126-152`; `backend/core_utils.py:362-376`; `backend/permissions_config.py:96-99`.

Ini risiko keterbukaan produk eksklusif/HPP melalui jalur lain, bukan klaim sudah terjadi kebocoran data. Katalog induk memang SHARED berdasarkan desain repo; jangan mengubahnya menjadi tenant-owned tanpa keputusan bisnis. Yang perlu konsisten adalah pembatasan per peran, lini, eksklusivitas, dan cakupan stok.

## Mengapa laporan sesi sebelumnya bisa terlihat selesai
Tes template lama memeriksa kartesian, SKU, assign/detach dan CRUD. Tes R&D memeriksa spesifikasi/sampel/approval/rilis. Belum ada pembuktian terpadu yang menuntut R&D menghasilkan keluarga dengan seluruh kombinasi, galeri per SKU dan pemilihan SKU tepat di sales. Bahkan tes penghapusan template lama mengharapkan varian dilepas, bertentangan dengan keputusan induk wajib yang lebih baru.

Bukti: `backend/tests/test_f1b_product_templates.py:132-150,316-332`; `backend/test_fase_f_rnd_poc.py`; hasil audit independen `/app/test_reports/iteration_1.json`.

## Usulan alur tujuan — belum implementasi
1. Buat/pilih induk produk; definisikan atribut dan nilai yang berlaku.
2. Susun matriks kombinasi; tentukan SKU, harga, status dan spesifikasi per kombinasi. Tetapkan batas jumlah kombinasi dan cegah duplikasi.
3. R&D menautkan desain/versi, sampel dan keputusan ke induk serta kombinasi yang relevan. Approval/rilis satu varian tidak otomatis meluluskan varian berbeda yang belum disetujui.
4. Kelola banyak foto per SKU: foto fisik/detail/warna/mockup model, cover, urutan, sumber dan status publikasi. Satu aset boleh dipakai beberapa varian secara eksplisit jika memang identik.
5. Hasil AI masuk review, bukan otomatis menjadi bukti produk fisik atau artwork final.
6. Sales membuka satu produk, memilih SEMUA atribut yang diperlukan, lalu galeri/harga/stok mengikuti SKU terpilih; kombinasi tidak tersedia tidak diganti diam-diam.

## Bentuk model yang disarankan
- Pertahankan `product_templates` dan `products.id` agar referensi transaksi tidak berubah.
- Induk menyimpan definisi axis dengan ID/kode stabil dan opsi, bukan hanya label bebas.
- SKU menyimpan pilihan opsi untuk seluruh axis; aturan unik induk+kombinasi dan SKU dijaga server.
- Media menyimpan product_id (SKU), jenis, storage reference, cover/order, sumber desain/versi, status persetujuan dan metadata AI jika relevan.
- Relasi R&D harus menjelaskan cakupan induk/varian; jangan menebak kelompok produk dari nama saja.
- Pisahkan status kelayakan produksi/transaksi dari kelayakan tampil di katalog pelanggan.
- Gunakan storage yang ada dahulu kecuali keputusan bisnis baru menyetujui penggantian; perlu validasi tipe file sebenarnya, thumbnail, batas ukuran, otorisasi download dan penghapusan.

## Urutan kerja setelah persetujuan
**Tahap 1 — Integritas dan izin:** tutup ketimpangan akses, selaraskan parent/lifecycle/axis, rencanakan migrasi dry-run dan pertahankan ID SKU lama.

**Tahap 2 — Pengelolaan katalog:** etalase induk + halaman detail dengan informasi, kombinasi varian, media, dan riwayat R&D; semua pengubahan varian berada dalam konteks induknya.

**Tahap 3 — Media dan sales:** unggah banyak foto, galeri desktop/mobile, mockup AI yang disetujui dan mode presentasi customer.

### Kriteria penerimaan yang disarankan
- Contoh 3 warna × 2 ukuran × 2 material menghasilkan 12 kombinasi unik dan terpilih tepat.
- Minimal 3 foto berbeda disimpan pada satu SKU; berpindah SKU mengganti galeri yang sesuai.
- R&D menghasilkan/menautkan varian ke induk valid, mempertahankan referensi desain/sampel, tanpa duplikasi saat retry.
- Penghapusan/arsip induk tidak meninggalkan SKU yatim atau memutus riwayat transaksi.
- Sales non-pemilik tidak memperoleh produk eksklusif maupun HPP lewat list/detail/summary/media API.
- Mockup AI terlabel, membutuhkan review, dan tidak menggantikan foto fisik diam-diam.
- Status belum dirilis tidak menjadi boleh jual melalui generator atau jalur lain.

## Status penutupan audit
Audit selesai. Semua temuan tetap backlog dan **belum diperbaiki**, sesuai pilihan pengguna. Tidak ada klaim fungsi live telah diuji. Langkah berikutnya adalah persetujuan arah perbaikan, bukan implementasi otomatis.