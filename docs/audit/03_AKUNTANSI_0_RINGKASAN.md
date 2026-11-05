# GL-00 — Ringkasan audit akuntansi/finance (SIPRO/Estora, instance #4)

Auditor: stream "akuntansi/GL". Instance: UI http://localhost:3004, API http://localhost:8004, DB `sipro_gl`, org `org-sipro` (+ org `org-nusa` tidak disentuh). Tanggal sistem uji: 2026-11-05. Seluruh data uji berawalan "AUDIT-".

## Ringkasan eksekutif (≤10 baris)
1. Buku besar double-entry, idempotensi per `source_event`, SoD transfer, kunci periode dan rekonsiliasi bank bekerja pada alur normal; seed awal cocok 100% dengan subledger (11 pasangan akun).
2. **Model kewajiban kontrak runtuh setelah BAST**: uang masuk pasca-BAST (termin, titipan dipakai, pencocokan bank) tetap Cr `2-1400`, piutang `1-1300` tak pernah turun (GL-01); **denda dihitung dua kali sebagai pendapatan** (GL-02).
3. **Tutup tahun → buka → tutup lagi** berstatus "tertutup" tanpa jurnal penutup baru (GL-03).
4. **PPN keluaran/BPHTB dibebankan ke `6-1400`**, PPN tak dipisah, PPN masukan tak dibukukan (GL-04).
5. Integritas: hapus paksa menghapus jurnal fisik (GL-05); satu jurnal manual bertanggal sampah mematikan tab Tutup Buku/Paket Owner (HTTP 500) dan menembus kunci periode (GL-06); dialog Rekonsiliasi Bank bisa menunjuk akun Piutang/WIP/induk sebagai "rekening" dan menggandakan saldo kas (GL-08).
6. Tidak ada koreksi akuntansi yang layak (void AP/kuitansi/nota kredit) dan event GL yang gagal berstatus `failed` permanen tanpa retry (GL-09, GL-10).
7. GL tak punya dimensi proyek/unit/rekening; WIP/HPP org-wide; persediaan material tidak berjurnal (GL-11, GL-12).
8. Seluruh pemetaan peristiwa→akun adalah hardcode di ±25 file; satu-satunya "konfigurasi akun" (all-in) setengah dipakai dan `gl_account` add-on/komponen harga dekoratif (GL-19). Kebutuhan Posting Profile + rute rekening + dry-run dirinci di gl-5, lengkap dengan tabel pemetaan awal v0 yang menyalin perilaku hari ini.

## Daftar laporan
| File | Isi |
|---|---|
| `03_AKUNTANSI_1_PETA_JURNAL.md` | Bagian A: arsitektur posting, matriks 39 jenis jurnal (pemicu, Dr/Cr, idempotensi, tanggal, dimensi, hardcode/konfigurasi), peta SSOT per akun, pemakaian CoA |
| `03_AKUNTANSI_2_REKONSILIASI.md` | Bagian C: baseline seed, hasil uji nyata per alur (JV bukti), periode & tutup buku/tahun, konsistensi laporan vs layar vs API |
| `03_AKUNTANSI_3_KAS_BANK.md` | Bagian B: koneksi CoA↔rekening kas/bank, alur yang bisa/tidak memilih rekening, kondisi kosong/salah/nonaktif/negatif, angka kas di layar vs GL |
| `03_AKUNTANSI_4_GAP.md` | Bagian D: daftar gap + 28 temuan berformat standar (GL-01…GL-28), terverifikasi OK, tidak bisa diverifikasi, pertanyaan terbuka |
| `03_AKUNTANSI_5_KEBUTUHAN_KONFIGURASI.md` | Bagian E: apa yang sudah/belum configurable, rancangan Posting Profile/Account Mapping (entitas, hak ubah, validasi, fail-closed, versi, migrasi, UI, urutan, risiko) + tabel pemetaan awal usulan |

Bukti pendukung: skrip uji tidak disertakan di repo; screenshot `img/gl/` (mis. `acc_Penutupan_Buku.png`, `rep_Tutup_Periode.png`, `rep_Paket_Laporan_Owner.png`, `fin_bank_dialog_gl_options.png`, `fin_bank_tab.png`, `cb_Posisi_Kas.png`, `acc_Bagan_Akun.png`).

## Cakupan (apa yang diuji)
Baca kode seluruh pemanggil `post_journal` (±37 titik panggil di 17 modul di luar seed, ditambah handler di `gl_engine`), 9 handler event, jalur tulis lain ke `journal_entries`, `cash_bank`, `gl_periods`, `closing_engine`, `gl_reports`, `gl_project_cash`, router GL/kas-bank/bank, `settings_store`/Pusat Konfigurasi, frontend Akuntansi/Laporan/Kas&Bank. Uji nyata via API: penerimaan (tunai/bank/rekening/overpay/ganda/pasca-BAST), titipan, BAST, denda, AP (+PPh, saldo nol), komisi, pembatalan+refund, pengajuan dana, kas bon, aset tetap (beli/tanah/susut/lepas), pinjaman, pajak, giro, impor+cocok+batal bank, booking fee, marketing fee, transfer & rekening, CoA, jurnal manual (10 skenario + RBAC), tutup bulan/tahun/buka tahun, hapus paksa kuitansi, event gagal. UI (Playwright): Buku Besar & Jurnal (5 tab), Laporan Keuangan (9 tab), Kas & Bank (3 tab), Keuangan→Rekonsiliasi Bank.

## Temuan (ID — severity — judul)
| ID | Severity | Judul | Bukti |
|---|---|---|---|
| GL-01 | Kritis | Penerimaan/titipan sesudah BAST masuk lagi ke `2-1400`; `1-1300` tak turun | TERBUKTI-API |
| GL-02 | Kritis | Denda dihitung dua kali sebagai pendapatan; piutang denda tak lunas | TERBUKTI-API |
| GL-03 | Kritis | Tutup tahun ulang setelah buka: "tertutup" tanpa jurnal penutup baru | TERBUKTI-API |
| GL-04 | Tinggi | PPN keluaran/BPHTB/PPh dibebankan `6-1400`; PPN tak dipisah; PPN masukan tak dibukukan | TERBUKTI-API+KODE |
| GL-05 | Tinggi | Hapus paksa menghapus jurnal fisik; BKM yatim; subledger tak sinkron | TERBUKTI-API |
| GL-06 | Tinggi | Jurnal manual tanggal tak valid memutus Tutup Buku/Paket Owner (500) & menembus kunci periode | TERBUKTI-API+UI |
| GL-07 | Tinggi | Pengakuan pendapatan (BAST) manual tanpa gerbang; terpisah dari serah terima | TERBUKTI-API+KODE |
| GL-08 | Tinggi | `/bank/accounts` menerima GL sembarang/kembar → saldo kas ganda; dropdown UI memuat Piutang/WIP | TERBUKTI-UI+API |
| GL-09 | Tinggi | Event GL `failed` permanen tanpa retry; AP retensi >100% lolos | TERBUKTI-API |
| GL-10 | Tinggi | Tak ada jalur koreksi/pembalikan (void AP, kuitansi manual, nota kredit; pajak mundur tanpa jurnal) | TERBUKTI-API+KODE |
| GL-11 | Tinggi | Jurnal tanpa dimensi; WIP/HPP org-wide; cek hapus-proyek "jurnal" selalu 0 | TERBUKTI-API+KODE |
| GL-12 | Tinggi | Persediaan/material (keluar, opname, retur, GRN) tidak berjurnal & tak bernilai | DARI-KODE |
| GL-13 | Sedang | CoA tak mengikat posting (nonaktif/rename/kode "ABC"/"2-1400 "/tipe vs prefiks) | TERBUKTI-API |
| GL-14 | Sedang | Klasifikasi arus kas salah (utang bank=operasi, uang muka subkon=investasi, dll.) | TERBUKTI-API |
| GL-15 | Sedang | Tiga definisi periode; jurnal masuk periode tutup via selisih WIB/UTC; posting digeser ke 2027-01-01; tanpa tanggal transaksi | TERBUKTI-API |
| GL-16 | Sedang | Kas bon dua sistem → `1-1500` dua subledger | TERBUKTI-API |
| GL-17 | Sedang | Banyak alur tak bisa pilih rekening; booking fee tunai ke bank; komisi tak bisa dibayar dari UI | TERBUKTI-API+KODE |
| GL-18 | Sedang | Saldo kas negatif tak dicegah (AP dari kas kecil saldo 0 → −Rp 37 jt) | TERBUKTI-API+UI |
| GL-19 | Sedang | Konfigurasi dekoratif (`gl_account` add-on/komponen harga) & hardcode ±25 file | DARI-KODE |
| GL-20 | Sedang | Tie-out sempit (5/4 akun), kumulatif; tiga angka kewajiban kontrak | TERBUKTI-API |
| GL-21 | Sedang | Jurnal manual tanpa maker-checker/ke akun kendali; induk kas dialihkan diam-diam | TERBUKTI-API |
| GL-22 | Sedang | Dua POST kuitansi identik → dua kuitansi + dua jurnal | TERBUKTI-API |
| GL-23 | Sedang | Pembatalan kontrak tak menyentuh komisi/fee/pajak; pajak deal batal masih bisa diakrual | TERBUKTI-API+KODE |
| GL-24 | Sedang | Bunga basis kas, provisi sekaligus, tanah sebagai aset tetap, penyusutan alat proyek ke beban | TERBUKTI-API+KODE |
| GL-25 | Sedang | Laporan per proyek memakai dua resolver; abaikan `source_deal_id` | TERBUKTI-API |
| GL-26 | Rendah | Giro dijurnal sebagai memorandum yang menggelembungkan neraca | TERBUKTI-API |
| GL-27 | Rendah | Cacat laten (sweeper retensi tanpa jurnal, migrasi header mutasi riwayat, purge, field salah) | DARI-KODE |
| GL-28 | Rendah | Cacat data seed (deal `completed` tanpa revrec, 3 komisi 1 deal) | TERBUKTI-API |

## Terverifikasi OK (ringkas — rincian di `03_AKUNTANSI_2_REKONSILIASI.md` §5 dan `03_AKUNTANSI_3_KAS_BANK.md` §6)
Jurnal selalu seimbang; idempotensi BAST/komisi/pajak/penyusutan/denda/refund/setuju AP; RBAC jurnal manual & buka periode; posting otomatis ke periode tutup digeser dengan memo; transfer SoD & cek saldo; giro memorandum konsisten; rekonsiliasi bank jujur; baseline subledger↔GL seed 100% cocok; first-time tutup tahun benar.

## Tidak bisa diverifikasi
Upah harian, klaim/potongan subkon end-to-end, biaya all-in & KPR disbursement (jurnal hanya dari kode); crash antara subledger dan `emit`; multi-worker/konkurensi (cache rekening default, saldo WIP); purge/hapus paksa proyek; zona waktu 17:00-24:00 UTC pada jam nyata (diuji dengan tanggal eksplisit); kunci periode kas.

## Pertanyaan terbuka
1. Harga jual inklusif atau eksklusif PPN? (menentukan perbaikan GL-04). 2. Titik pengakuan pendapatan: serah terima fisik, AJB, atau pelunasan? 3. BPHTB: titipan pembeli, ditanggung developer, atau campuran? 4. Komisi: biaya perolehan kontrak (dikapitalisasi) atau beban saat disetujui? 5. Apakah rekening escrow per proyek perlu dimodelkan (`project_id` pada rekening)?

## Catatan kondisi instance
Instance #4 sengaja diubah oleh uji (jurnal bertanggal sampah JV/2026/00092/00104, periode 2026-08…12 ditutup dengan override, tahun 2026 dalam keadaan "closed" tanpa jurnal penutup aktif, rekening kembar/akun uji ber-awalan AUDIT-). Tab Tutup Buku/Paket Owner di UI :3004 error akibat GL-06 — itu efek dari temuan, bukan kerusakan lain.
