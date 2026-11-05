# Audit Estora/SIPRO — Ringkasan Eksekutif

> Tanggal: 5 Nov 2026 · Cakupan: alur pembayaran (masuk dan keluar), UI Percakapan WhatsApp, akuntansi dan finance (jurnal otomatis, hubungan akun↔rekening, gap, kebutuhan konfigurasi), pembuatan kontrak, konversi lead→customer.
> Ini **audit saja**. Tidak ada kode aplikasi yang diubah. Semua yang ada di folder ini adalah laporan dan bukti.

## 1. Cara audit dan batasannya (baca ini dulu)

- Aplikasi **dijalankan sungguhan** (backend FastAPI + MongoDB + frontend build produksi) dari kode di repo ini, lalu diakses lewat browser (Chromium/Playwright) sebagai user: login per peran (sales, manager, finance, PM, owner, super admin), klik tombol, isi form, klik ganda, buka dua tab. Pengujian paralel (dua request bersamaan) dilakukan lewat HTTP.
- Lima instance terpisah (backend + database + UI sendiri) dipakai agar tiap jalur audit tidak mengotori data jalur lain. Data adalah **data demo hasil seed**, bukan data produksi Anda. Angka seperti "Rp 38 jt keluar dua kali" adalah angka uji, bukan kerugian nyata.
- Mode WhatsApp = simulasi (kredensial Meta tidak ada). Perilaku mode LIVE **tidak bisa diuji**.
- Label bukti di tiap temuan: **TERBUKTI-UI** (direproduksi di browser), **TERBUKTI-API** (direproduksi lewat HTTP/DB), **DARI-KODE** (hanya dari membaca kode).
- Yang saya (koordinator) cek ulang sendiri di kode setelah menerima laporan auditor: KT-01 (`deals_router.py:505-564`), PK-01/PK-02 (`finance_ap.py:62-91`, `engine.py:637-652`, `seed_indexes.py:128`), GL-01 (`gl_engine.py:263-284`), GL-03 (`closing_engine.py:437-525`), GL-04 (`gl_engine.py:454-465`), dan semua temuan WhatsApp (diukur sendiri). Temuan lain mengandalkan reproduksi auditor dan belum saya ulang satu per satu.
- **Satu koreksi:** IN-10 (OTP master `000000`) semula dilaporkan "Tinggi". Bukti reproduksinya memakai nilai yang diisi lingkungan uji ini sendiri, sehingga saya turunkan menjadi "Sedang" dan menjelaskan kondisinya di laporan.

## 2. Hasil dalam angka

| Area | Dokumen | Kritis | Tinggi | Sedang | Rendah | Total |
|---|---|---:|---:|---:|---:|---:|
| Pembayaran masuk | `01_PEMBAYARAN_MASUK.md` | 5 | 8 | 9 | 1 | 23 |
| Pembayaran keluar | `02_PEMBAYARAN_KELUAR.md` | 4 | 11 | 7 | 1 | 23 |
| Akuntansi dan finance | `03_AKUNTANSI_*.md` (6 berkas) | 3 | 9 | 13 | 3 | 28 |
| Kontrak dan konversi lead | `04_KONTRAK_DAN_KONVERSI_LEAD.md` | 1 | 10 | 14 | 5 | 30 |
| Percakapan WhatsApp | `05_WHATSAPP_INBOX.md` | 0 | 5 | 4 | 2 | 11 |
| **Total** | | **13** | **43** | **47** | **12** | **115** |

Jumlah ini menyesatkan bila dibaca mentah: banyak temuan adalah **gejala dari beberapa akar masalah yang sama** (bagian 3). Memperbaiki sekitar tujuh akar itu menutup sebagian besar temuan kritis dan tinggi.

## 3. Akar masalah lintas-area

**A. Tidak ada penguncian atau idempotensi pada operasi yang menggerakkan uang.** Semua jalur bekerja dengan pola "baca status → hitung → tulis" tanpa syarat atomik. Dua request bersamaan (klik ganda di dua tab, dua staf, retry jaringan) sama-sama lolos.
- Terukur: tagihan AP net Rp 9,5 jt dibayar dua request paralel → Rp 38 jt keluar dari bank, subledger hanya mencatat Rp 9,5 jt (PK-02). Deposit Rp 2 jt dikembalikan Rp 4 jt, saldo titipan −Rp 2 jt. Refund pembatalan 4 × Rp 100 jt. Penerimaan ganda di semua jalur uang masuk (IN-01), dan 6 dari 14 deal ber-AR sudah tidak sinkron.
- Bukti di kode: `pay_ap_bill` menyetel `paid` sebagai nilai absolut tanpa syarat status sebelumnya (`finance_ap.py:81-91`); dispatcher event membaca event `pending` tanpa mengklaimnya (`engine.py:637-652`); indeks `source_event` pada jurnal **tidak unik** (`seed_indexes.py:128`) dan `post_journal` hanya `find_one` (`gl_engine.py:127-131`) lalu `insert_one` (`gl_engine.py:182`). Hasilnya jurnal kembar (IN-03, PK-01).
- Temuan terkait: IN-01..04, PK-01..05, GL-22, KT-02 (konversi lead paralel → HTTP 500, customer ganda, nomor kontrak berlubang), KT-08 (kupon kuota 1 terpakai dua kali).

**B. Dua jalur untuk hal yang sama, satu jalur tanpa gerbang.** Alur lama tidak dihapus waktu alur baru dibuat, sehingga gerbang bisnis bisa dilompati.
- KT-01 (kritis): jalur lama `/deals/{id}/ppjb` dan `/ajb` hanya meminta izin `deals:update`. Sales bisa menjadikan unit SOLD dengan booking fee Rp 5 jt dari harga Rp 720–850 jt, melewati DP, pelunasan, BAST, dan wewenang manajer. Kontrak tetap `draft` dan piutang tetap Rp 845 jt.
- Pola sama: tiga pintu pencairan KPR dengan izin berbeda (IN-11), dua sistem kas bon (GL-16, PK-21), dua model biaya kontrak yang membuat SPR tidak bisa ditandatangani (KT-03), dua resolver laporan per proyek (GL-25).

**C. Model kewajiban kontrak runtuh setelah BAST, dan jenis pembayaran tidak terbedakan di GL.** Semua penerimaan pembeli dikredit ke satu akun `2-1400` (`gl_engine.py:263-284`), termasuk yang masuk **setelah** BAST, padahal setelah BAST seharusnya mengurangi piutang `1-1300` (GL-01, IN-07). Denda dihitung dua kali sebagai pendapatan (GL-02, IN-06). Booking fee, DP, termin, KPR, dan biaya all-in tidak bisa dibedakan dari jurnalnya (IN-18). Lampu merah `/finance/reconcile` mendeteksi selisihnya, tetapi tidak mencegahnya.

**D. Tidak ada void, nota kredit, atau pembalikan yang layak.** "Hapus kuitansi" adalah hapus fisik: kewajiban kontrak tidak turun, jurnal ikut hilang (nomor JV bolong, BKM yatim), bukti pelanggan hilang (IN-05, GL-05). Tidak ada void AP atau pembayaran (PK-09, GL-10). Tutup tahun → buka → tutup lagi berstatus "tertutup" tanpa jurnal penutup baru, jadi laba tidak pernah pindah ke Laba Ditahan (GL-03; saya konfirmasi di `closing_engine.py`: `year_close` memakai `source_event` yang sama sehingga kena early-return idempotensi dan mengembalikan jurnal lama yang sudah dibalik).

**E. Pemisahan tugas (maker-checker) dan izin tidak konsisten antara UI dan API.** Satu akun finance bisa menjalankan PO → approve → GRN → tagihan → approve → bayar Rp 25 jt (PK-07). Pemohon bisa mencairkan pengajuannya sendiri. Sales bisa mencatat pencairan KPR lewat API walau UI menolak (IN-11). PM bisa menaikkan nilai kontrak SPK (PK-11). Sales membaca kontrak, harga, AR, dan NIK milik sales lain lewat `/customers/{id}/…` (KT-09). Pemicu denda bisa meringankan dendanya sendiri (IN-12). Wajib bukti foto pencairan hanya ditegakkan di UI, bukan di API (PK-13).

**F. Validasi dan kontrol saldo bolong.** Saldo kas/bank tidak dicek di sebagian besar jalur: akuisisi aset Rp 99 M lolos dan rekening operasional jadi −Rp 92 M (PK-06, GL-18). `retention_pct` 150% diterima, tagihan jadi net negatif lalu "disetujui" (PK-08). Pembayaran bisa masuk ke deal yang sudah dibatalkan (IN-13), dan piutang hantu Rp 1,55 M bisa dihidupkan pada deal batal (KT-07).

**G. Pemetaan peristiwa→akun semuanya hardcode, tanpa dimensi.** Sekitar 25 file menulis kode akun langsung. Pusat Konfigurasi (129 kunci) tidak punya satu pun kunci akun. Kolom `gl_account` pada add-on dan komponen harga **dekoratif** (tidak dibaca saat menjurnal) (GL-19). Jurnal tidak membawa dimensi proyek/unit/rekening, sehingga WIP dan HPP bersifat organisasi-wide (GL-11). Persediaan material tidak berjurnal sama sekali (GL-12). PPN keluaran, BPHTB, dan PPh semuanya dibebankan ke `6-1400`, PPN tidak dipisah dan PPN masukan tidak dibukukan (GL-04; terkonfirmasi di `gl_engine.py:454-465`).

## 4. Jawaban atas pertanyaan Anda satu per satu

**"Audit semua flow kritis pembayaran dan semua jenis pembayarannya"** → `01_PEMBAYARAN_MASUK.md` dan `02_PEMBAYARAN_KELUAR.md`. Masuk: booking fee, DP/termin, KPR, biaya all-in/BPHTB, titipan, denda, refund, portal pembeli, mutasi bank, giro. Keluar: AP vendor, subkon (termin, uang muka, retensi), komisi, marketing fee, kas kecil, kas bon, pengajuan keuangan, upah, pinjaman, aset tetap, pajak, refund. Ada pula jalur yang tidak Anda sebut, mis. penyaluran titipan ke notaris/BPN dan jurnal manual ke bank.

**"UI Inbox WhatsApp sangat buruk, scroll ke bawah jauh, semakin banyak chat"** → **Benar dan sudah direproduksi** (`05_WHATSAPP_INBOX.md`, dengan screenshot). Daftar chat tidak punya wadah gulir sendiri dan tidak ada paginasi, jadi halaman memanjang (5.979 px untuk 50 chat; 6.735 px di HP), panel percakapan tidak menempel sehingga kolom kanan kosong saat daftar di-scroll, dan halaman mendarat dalam keadaan ter-scroll. Ada tiga masalah data yang lebih serius: hanya 50 dari 223 chat yang bisa dijangkau, thread di atas 500 pesan **kehilangan pesan terbarunya** (balasan baru tidak terlihat), dan tombol "Kirim sbg Pesan Masuk" memungkinkan sales memalsukan pesan pelanggan lalu membuka kembali jendela 24 jam.

**"Audit komprehensif akuntansi dan finance: semua SSOT, semua flow jurnal otomatis, koneksi akun↔rekening, gap"** → `03_AKUNTANSI_1_PETA_JURNAL.md` (matriks 39 jenis jurnal: pemicu, Dr/Cr, kunci idempotensi, tanggal, dimensi, hardcode atau konfigurasi; peta SSOT per akun), `03_AKUNTANSI_2_REKONSILIASI.md` (uji nyata subledger vs GL), `03_AKUNTANSI_3_KAS_BANK.md` (akun↔rekening), `03_AKUNTANSI_4_GAP.md` (28 temuan).
- Yang baik: jurnal selalu seimbang; seed awal cocok 100% dengan subledger (11 pasangan akun); idempotensi per `source_event` bekerja untuk alur sekuensial; kunci periode, transfer antar rekening, dan rekonsiliasi bank bekerja pada alur normal.
- Akun↔rekening: induk `1-1100`/`1-1200` terkunci dan tiap rekening punya sub-akun, itu berfungsi. Celahnya: sekitar separuh alur uang tidak bisa memilih rekening (booking fee tunai masuk bank, titipan, all-in, pinjaman, aset, upah), event yang antre jatuh diam-diam ke rekening default, saldo negatif tidak dicegah, dan `/bank/accounts` menerima akun GL sembarang sehingga saldo kas di layar Kas & Bank (Rp 15,76 M) berbeda dari neraca (Rp 8,01 M) (GL-08).

**"Analisis kebutuhan konfigurasi koneksi fitur → auto-jurnal → akun"** → `03_AKUNTANSI_5_KEBUTUHAN_KONFIGURASI.md`. Isinya rancangan **Posting Profile / Account Mapping**: katalog peristiwa, peran akun, profil bersyarat berversi, rute rekening, hak ubah (maker-checker), validasi dan dry-run pratinjau jurnal, perilaku fail-closed untuk transaksi uang, jejak versi di jurnal, migrasi tanpa mengubah saldo historis, sketsa UI, urutan implementasi, dan **tabel pemetaan awal v0 yang menyalin perilaku hari ini persis** (dengan tanda profil koreksi untuk GL-01/02/04/14).

**"Pembuatan kontrak terkadang masih ada bug; perubahan lead ke customer juga masih bug"** → `04_KONTRAK_DAN_KONVERSI_LEAD.md` (30 temuan). Sebab "terkadang": (1) konversi tidak aman untuk request paralel: 4 request serentak ke `/deals/{id}/convert` menghasilkan 2 kali HTTP 500 dan 2 customer untuk satu lead (KT-02); (2) dua jalur legal yang bertabrakan (KT-01); (3) mengisi komponen biaya kontrak, yang justru tugas bawaan konversi, membuat SPR tidak bisa ditandatangani (KT-03); (4) konfigurasi `payment.staged.*` dan `payment.cash.*` diabaikan dan jatuh tempo dihitung dari booking, padahal teks SPR menyebut "setelah kontrak diaktifkan" (KT-10, KT-11); (5) lead langsung `won` saat konversi dan UI menulis "akad/AJB selesai" (KT-13).

## 5. Urutan perbaikan yang saya sarankan

**P0 — hentikan kebocoran uang dan data (sebelum dipakai transaksi sungguhan dalam volume)**
1. Penjagaan atomik pada semua operasi uang: update bersyarat (`find_one_and_update` dengan syarat status/saldo sebelumnya), kunci idempotensi (`client_ref` wajib), indeks unik `journal_entries(org_id, source_event)`, dan dispatcher yang mengklaim event secara atomik (`pending→processing`). Menutup akar A.
2. Matikan atau jadikan pembungkus tipis jalur lama `/deals/{id}/ppjb|ajb`, satukan tiga pintu pencairan KPR dengan satu izin `approve`. Menutup KT-01 dan IN-11.
3. Tegakkan maker-checker dan bukti pencairan di **API**, bukan hanya UI (akar E).
4. Cek saldo kas/bank dan batas validasi (retensi ≤100%, pembayaran ke deal batal) (akar F).
5. Inbox WA: perbaiki `inbox_router.py:88` (urut turun + limit + balik), batasi tombol "Pesan Masuk" ke mode simulasi, tolak `direction:"in"` di mode live.
6. Master OTP portal: hapus nilai bawaan `"000000"` dari kode dan gagal-tutup bila env kosong.

**P1 — perbaiki kebenaran pembukuan**
7. Model kewajiban kontrak pasca-BAST: penerimaan setelah BAST mengurangi `1-1300`; pisahkan denda dari pendapatan unit (GL-01, GL-02).
8. Void/nota kredit sebagai fitur resmi; hentikan hapus fisik kuitansi dan jurnal (akar D); perbaiki tutup-tahun-ulang (GL-03).
9. Pisahkan PPN keluaran/masukan dari `6-1400`; validasi tanggal jurnal manual (GL-06).
10. Konversi lead idempoten (kunci per deal, tangkap `DuplicateKeyError`, indeks unik `customers(org_id, lead_id)`) dan sinkronisasi data lead↔customer↔deal (KT-02, KT-15..17).

**P2 — fondasi dan UX**
11. Posting Profile / Account Mapping (dokumen 03_AKUNTANSI_5), mulai dari katalog peristiwa + profil v0 + dry-run yang hanya-baca, lalu dimensi proyek/unit/rekening.
12. Desain ulang Inbox WA: dua panel setinggi layar, infinite scroll + pencarian, thread paginasi, pembaruan real-time, master–detail di HP.

## 6. Keputusan yang saya butuhkan dari Anda (mengubah cara perbaikan)

1. Harga jual **inklusif atau eksklusif PPN**? (menentukan perbaikan GL-04)
2. Titik pengakuan pendapatan: serah terima fisik, AJB, atau pelunasan? (GL-01/07)
3. BPHTB: titipan pembeli, ditanggung developer, atau campuran?
4. Komisi: dikapitalisasi sebagai biaya perolehan kontrak atau dibeban saat disetujui?
5. Perlukah rekening escrow per proyek dimodelkan?

## 7. Yang tidak bisa diverifikasi

- Mode LIVE WhatsApp/Meta; kinerja pada ribuan chat.
- Konkurensi pada banyak worker/server (uji paralel dijalankan pada satu proses backend).
- KPR sampai pencairan penuh, amandemen all-in, penyusutan/disposal aset, upah harian, termin berbasis opname, rekonsiliasi bank dan giro (sebagian), efek periode tertutup di jalur pembayaran masuk, event gagal 3×, pewarisan dokumen lead→customer, tombol Back/refresh di tengah dialog.
- Data produksi Anda: audit memakai data demo hasil seed; temuan integritas (mis. "6 dari 14 deal tidak sinkron") menggambarkan data uji, bukan kondisi database produksi. Disarankan menjalankan kontrol `/finance/reconcile` dan pemeriksaan serupa pada salinan data produksi sebelum memperbaiki.

## 8. Daftar dokumen

| Berkas | Isi |
|---|---|
| `01_PEMBAYARAN_MASUK.md` | 23 temuan, tabel jenis pembayaran × akun GL, hal yang terverifikasi benar |
| `02_PEMBAYARAN_KELUAR.md` | 23 temuan |
| `03_AKUNTANSI_0_RINGKASAN.md` … `03_AKUNTANSI_5_KEBUTUHAN_KONFIGURASI.md` | Peta jurnal, rekonsiliasi, kas-bank, gap, rancangan konfigurasi |
| `04_KONTRAK_DAN_KONVERSI_LEAD.md` | 30 temuan |
| `05_WHATSAPP_INBOX.md` | 11 temuan + arah perbaikan |
| `img/` | Screenshot bukti (dikompres) |

> Catatan: laporan menyebut `localhost:300x/800x` dan "instance #N". Itu alamat lingkungan uji sementara yang sudah tidak diperlukan; ID temuan (IN-, PK-, GL-, KT-, WA-) yang menjadi acuan.
