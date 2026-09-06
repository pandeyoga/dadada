# Verifikasi lanjutan SIPRO — 6 September 2026

## Acuan dan batas klaim
- Repo sumber: `agavafayaja/sipro`, branch default `main`, commit sumber `610e6178a8acb9593efb9bb73ae6ea7f5e85efe7`.
- Permintaan pengguna: verifikasi ulang `AUDIT_SINTESIS_1.md` dan rencana lama berdasarkan bukti; editor naskah seperti Word untuk merapikan paragraf dan memindahkan tabel; perbaikan overlap all-in dan jarak arah hadap; pertahankan desain.
- Salinan audit: `memory/verification/AUDIT_SINTESIS_1.md`.
- Lingkungan ini dipulihkan dari kode repo, BUKAN salinan database produksi. Data operasional yang terlihat adalah seed demo dan fixture tes. Tidak dilakukan migrasi saldo/jurnal produksi.
- Catatan lama menyebut **62 gate**. Daftar yang benar-benar dijalankan di repo saat ini berisi **70 skrip**; nomor fase historis bukan jumlah eksekusi.
- Registry berisi **23 jenis termasuk bawaan**. Ekspektasi penguji awal `>=24` tidak punya dasar kebutuhan; diganti pemeriksaan kehadiran semua 23 kode nyata dan render setiap kode. Tidak dibuat dokumen fiktif untuk meluluskan hitungan.

## Temuan terbukti → tindakan
| Area | Bukti sebelum | Perbaikan |
|---|---|---|
| Naskah | `ScriptForm` hanya textarea | Editor Tiptap: rata kiri/tengah/kanan/kanan-kiri, tebal/miring/garis bawah, daftar, undo/redo; simpan dan muat ulang |
| Tabel | Posisi otomatis tersedia sebagian di renderer tetapi `tabel_biaya` tidak dikenali validator/substitusi | Token biaya/rincian dipertahankan; sisip di posisi kursor, tabel native dapat ditambah/hapus baris-kolom dan dipindah atas/bawah |
| Hasil PDF | Renderer memecah teks per baris, belum memahami paragraf HTML | Renderer bersama memahami paragraf, format, daftar, tabel; sanitasi HTML dan escaping nilai placeholder |
| Ukuran tabel | Lebar tabel/signature memakai ukuran tetap, ukuran huruf biaya tidak mengikuti pengaturan | Lebar mengikuti area kertas/margin; lebar persen dan posisi kiri/tengah/kanan; ukuran huruf tabel biaya mengikuti konfigurasi; kontras header dibenahi |
| Invoice/laporan | `render_table` mengabaikan urutan bagian | Urutan naskah/rincian/catatan dan penempatan tabel di naskah diterapkan |
| Naskah sistem | KWITANSI/BKM/BKK/BAST/PENAWARAN mengabaikan naskah tersimpan; laporan dan INB juga tidak memakainya | Naskah dimasukkan melalui mesin PDF bersama dan konteks tanggal/nomor; angka transaksi tetap dari sumber asli |
| Pajak | Faktur/bukti potong memanggil jalur PDF lama tanpa layout | Endpoint faktur dan e-Bupot menyertakan layout dan gambar organisasi |
| Salinan pembeli | Portal tidak membawa baris biaya kontrak seperti endpoint staf | Helper bersama `document_pdf_context` untuk nominal dan konteks cetak; penanda eksplisit tetap bekerja saat bagian biaya mati secara bawaan |
| Pratinjau | Iframe PDF kosong pada browser uji | PDF.js canvas dengan navigasi halaman, menggunakan PDF yang dihasilkan backend, bukan tiruan HTML |
| All-in | Empat kolom `1fr` melebar mengikuti panjang pilihan; angka dan pemilih saling mendesak | Grid `minmax(0,...)`, label jelas, responsif, pemilih komponen tidak duplikat, tombol simpan terlihat pada desktop |
| Komponen biaya | Tabel mobile terlalu rapat | Lebar minimum tabel dalam wadah gulir; aksi menempel di kanan; kolom tidak dipaksa mengecil |
| Arah hadap | Teks dan `RefLabel` menjadi anak flex terpisah | Teks satu alur, ikon tidak menyusut, frasa arah hadap tetap menyatu; diverifikasi pada B-01/Utara menggunakan jalur yang sama untuk Tenggara |
| Harga panjang | Harga miliaran mendesak status dalam kartu sempit | Harga/status boleh pindah baris dengan jarak terukur |
| Input konfigurasi | String seperti `20:00`, kode template WA, dan isi pesan dipasang ke `type=number` | Tipe teks/jam/numerik dibedakan; nilai asli tidak diubah |
| Notifikasi | Koneksi WS dibuka ulang saat identitas fungsi navigasi berubah dan dibatalkan saat StrictMode setup | Navigasi via ref stabil; koneksi mengikuti identitas organisasi/pengguna; cleanup CONNECTING aman |
| Grafik/kursor | Ukuran grafik -1 saat mount; seleksi tabel menunjuk tableHeader | Dimensi awal grafik; seleksi editor menuju posisi teks sah dalam transaksi yang sama |

## Verifikasi yang telah dijalankan
- Penguji independen: `test_reports/iteration_5.json`; laporan awal dipertahankan apa adanya untuk jejak temuan, bukan status final.
- **48 tes terfokus lulus** sesudah koreksi: `memory/verification/focused-final.log` dan `test_reports/pytest/verified-final.xml`.
  - Tahap 1–2/tahapan pembangunan & survey, Tahap 5, Tahap 6, dokumen Fase 66, dan regresi editor/PDF/RBAC.
  - Seluruh **23 target PDF pratinjau** menghasilkan PDF; unknown placeholder dan alignment/lebar ilegal ditolak; sales tidak boleh menulis naskah/layout atau menjalankan pratinjau konfigurasi.
- UI: simpan-muat ulang naskah, align/list/table/undo-redo, perpindahan tabel, preview/next/prev/download; all-in ALLIN_STD dan EXCLUDE desktop dan mobile oleh penguji; pemeriksaan ulang desktop setelah koreksi.
- PDF pratinjau dihasilkan lewat endpoint aplikasi, dirender ke PNG, dan dilihat tiap halaman (bukan hanya ekstraksi teks). Halaman tanda tangan terpisah adalah pemenggalan alami, bukan halaman kosong.
- Pemeriksaan kedua console: warning parsing input, TextSelection, WS reconnect, dan ukuran grafik yang dilaporkan tidak muncul lagi pada alur yang diulang; permintaan dibatalkan saat pindah halaman dibedakan dari kegagalan server.
- Rangkaian lengkap terbaru: `memory/verification/verified-final-gates.log` (status akhir dicatat setelah proses selesai).

## Penjaga lama yang dikoreksi berdasarkan bukti
- P60/P66: syarat literal `iframe` diganti pemeriksaan komponen preview/canvas berdampingan; kewajiban PDF server tetap ada.
- Gate UI: pencarian substring CSS tidak lagi mensyaratkan `whitespace-nowrap` langsung setelah `justify-between`; latar padat tetap wajib.
- Gate kontrak: pemeriksaan biaya menggunakan isi paragraf HTML atau baris teks lama, bukan hanya `startswith` pada string HTML.
- Gate anggaran: memilih proyek yang benar-benar memiliki target aktif, bukan proyek kosong pertama dalam daftar. Ini masih fixture berbasis demo, BELUM setara seluruh suite legacy mandiri.
- Fixture P75 membersihkan lead yang dibuatnya dengan guard tidak ada transaksi; fixture P48 membersihkan cluster/blok yang ikut dibuat pada proyek tesnya.
- Satu cluster yatim hasil migrasi pada proyek Gate48 dan lead P75 milik run ini dibersihkan sesudah memastikan tidak terkait unit/deal/kontrak/pembeli/dokumen keuangan. Bukti: `memory/verification/test-artifact-cleanup.log`. Tidak dilakukan purge massal database.

## Recheck catatan audit lama
| Area | Kesimpulan terukur |
|---|---|
| WA-01/02/03/04/12/13 dan template terpusat | Penjaga lokal/tes audit tersedia dan dijalankan. Persetujuan template dan pengiriman nyata Meta BELUM dibuktikan tanpa kredensial live. |
| RBAC-02/03 | Bahasa aksi dan izin tetap dijaga. Peran dinamis RBAC-01 masih keputusan/pekerjaan terpisah, tidak diam-diam ditambahkan. |
| DOC-01/02, CFG/UI Tahap 5 | Tes audit lulus, tetapi ditemukan celah cetak tambahan di atas; sudah ditangani, bukan menganggap catatan lama otomatis benar. |
| CFG-01/FIN/PRJ/BI Tahap 6 | 17 tes audit angka tercakup di 48 tes, ditambah gate kartu/drilldown. Tidak diubah rumus bisnis atau saldo historis. |
| Tahap 7 | Penjaga field, kamus dropdown, KPI/drilldown tetap berjalan. Ini bukan pengganti audit semua rumus GL/BI. |

## Yang belum boleh diklaim selesai
1. **Seluruh suite pytest legacy** mandiri (tipe unit/booking fee/kontrak) belum diselesaikan. Beberapa tes audit lama masih meninggalkan proyek/survey contoh; hindari suite destruktif `test_iter148`.
2. Audit angka menyeluruh GL/neraca/laba-rugi/arus-kas/pajak dan BI non-lead, pengadaan, retensi, serta portal lintas skenario belum ditutup hanya dengan gate hijau.
3. Sapuan visual meliputi alur inti dan rute representatif, **bukan setiap popup pada semua peran, perangkat, dan keadaan data**. Lanjutkan matriks audit visual sistematis.
4. Lencana global indikasi data uji belum dibuat. Cleanup fixture tertentu bukan bukti semua fixture lama bersih.
5. Skip tes WA yang benar-benar membutuhkan kredensial perlu inventarisasi terpisah; tes unit MockTransport tidak boleh dilewati hanya karena kredensial live kosong. Integrasi WhatsApp/CAPI lingkungan ini tetap mode simulasi bawaan, bukan bukti pengiriman live.
6. Editor menyediakan format dasar seperti Word, bukan pembaca/penyunting file DOCX penuh. Keluarga invoice/kwitansi tertentu masih berbagi jenis template yang sama sebagaimana arsitektur lama.

## Urutan lanjut yang disarankan
P1: fixture legacy terisolasi + indikator data uji → matriks GL/BI sampai sumber baris → audit visual semua dialog per peran.
P2: versi/diff template dan konfirmasi sebelum mengganti dokumen, pengaturan tipografi naskah lebih lengkap, pemisahan template turunan invoice/kwitansi bila diperlukan.