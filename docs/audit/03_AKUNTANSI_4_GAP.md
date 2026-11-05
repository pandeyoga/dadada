# GL-4 — Gap & temuan akuntansi/finance (Bagian D) — format temuan INSTANCES.md

Instance #4. Label bukti: [TERBUKTI-UI] direproduksi lewat browser · [TERBUKTI-API] direproduksi lewat HTTP/DB · [DARI-KODE] hanya dari membaca kode. Jurnal bukti disebut `JV/2026/000nn`. Skrip uji di (skrip uji tidak disertakan di repo) (t*.py). Catatan: sebagian uji saya sendiri memutus fitur di instance ini (jurnal tanggal sampah, tutup periode) — itu bagian dari temuan, bukan efek samping tak sengaja.

## Ringkasan eksekutif (≤10 baris)
1. Pondasi buku besar (double-entry, idempoten per `source_event`, SoD transfer, kunci periode, rekonsiliasi bank) bekerja dan rapi pada alur normal; seed awal cocok 100% dengan subledger (11 pasangan).
2. Model kewajiban kontrak runtuh SETELAH BAST: setiap uang yang masuk sesudah pengakuan pendapatan tetap dikreditkan ke `2-1400` (bukan mengurangi piutang `1-1300`) — GL-01. Denda dihitung dua kali sebagai pendapatan — GL-02.
3. Tutup tahun → buka → tutup lagi menghasilkan status "tertutup" TANPA jurnal penutup baru (laba berjalan tak pernah pindah ke Laba Ditahan) — GL-03.
4. Pajak: PPN keluaran/BPHTB dibebankan ke `6-1400`; PPN tidak dipisah dari pendapatan; PPN masukan tak dibukukan — GL-04.
5. Integritas: hapus paksa menghapus jurnal secara fisik (GL-05); satu jurnal manual bertanggal sampah mematikan layar Tutup Buku/Paket Owner dan menembus kunci periode (GL-06); satu dialog Rekonsiliasi Bank bisa menunjuk akun Piutang/WIP sebagai "rekening bank" dan menggandakan saldo kas (GL-08).
6. Tidak ada jalur koreksi akuntansi yang layak (void AP, void kuitansi manual, nota kredit) — GL-10; event GL gagal permanen tanpa retry — GL-09.
7. GL tanpa dimensi (proyek/unit/rekening): WIP/HPP org-wide, P&L per proyek tak lengkap — GL-11; persediaan material tidak berjurnal — GL-12.
8. Semua pemetaan peristiwa→akun adalah hardcode di ±25 file; satu-satunya konfigurasi (komponen biaya all-in) sebagian tak dibaca, dan `gl_account` pada add-on/komponen harga tidak dipakai sama sekali (GL-19) → kebutuhan Posting Profile di gl-5.

## A. Fitur yang memindahkan uang/nilai tetapi TIDAK (atau tidak benar) berjurnal

| Fitur | Yang terjadi | Berjurnal? | Temuan |
|---|---|---|---|
| Material masuk/keluar/opname/retur (`/materials/txn`, `/materials/opname`, `procurement_extra.create_return`) | Hanya `material_txns` (kuantitas, kadang `unit_price`) | **Tidak** | GL-12 |
| Penerimaan barang (GRN) | Menaikkan `received_value` PO | Tidak (utang baru diakui saat tagihan AP disetujui; tidak ada akrual GRNI) | GL-12 |
| Retur pembelian atas barang yang SUDAH ditagih | Ditolak sistem ("terbitkan nota kredit") — fitur nota kredit AP **tidak ada** | – | GL-10 |
| Void/reject tagihan AP, batal bayar AP | Tidak ada endpoint | – | GL-10 |
| Void kuitansi manual | Tidak ada (hanya lewat "batalkan pencocokan bank" dan hapus paksa) | sebagian | GL-05, GL-10 |
| PPN keluaran/masukan | Dihitung di `tax_records`/`ppn_input` (estimasi) | Keluaran → beban `6-1400`; masukan **tidak** | GL-04 |
| Akrual bunga pinjaman, kapitalisasi biaya pinjaman | Bunga hanya dicatat saat angsuran dibayar | Tidak ada akrual | GL-24 |
| Status tax_record `paid→pending` | Mengubah status | **Tidak ada jurnal balik** | GL-10 |
| Pembatalan kontrak terhadap komisi, marketing fee, tax_records | Tidak disentuh | Tidak | GL-23 |
| Pembayaran komisi lewat UI | **Tidak ada tombol** (hanya API) | – | GL-17 |
| `ap_retention_release_sweeper` (job terjadwal; laten karena `release_due_at` tak pernah ditulis) | Menandai retensi lepas + membuat `payments_out` "Pelepasan retensi" | **Tidak** (2-1200 tidak turun, `payments_out` mengaku kas keluar) | GL-27 |
| Data purge "Manajemen Data" | Menghapus jurnal, periode, nomor urut | hapus fisik | GL-27 |

## B. Jurnal yang akunnya meragukan / semua jenis ke satu akun

| Hal | Bukti |
|---|---|
| Semua penerimaan (DP, termin, pelunasan, KPR, denda, add-on) → Cr `2-1400`, memo "(uang muka)" | JV/00048-55, 00064, 00083 |
| Booking fee & titipan di muka → memo "Titipan pelanggan (kelebihan bayar)" | JV/00116 |
| PPN keluaran, PPh final, BPHTB → semuanya Dr `6-1400` Beban Pajak | JV/00078, 00080, 00102, 00107 |
| Potongan pembatalan, denda/penalti subkon, "other", hangus booking fee, jasa giro → `4-1200` Pendapatan Lain-lain | JV/00066; `reference_p48.py:185` |
| Semua aset tetap (termasuk TANAH Rp 2 M) → `1-2100`; penyusutan alat proyek → beban `6-1500` (bukan WIP) | AST/2026/0005-0006; JV (dep) |
| Kategori kas bon `biaya_proyek`/`upah_harian` → langsung Dr `1-1600` WIP tanpa PO/SPK/RAB | JV/00071, 00088 |
| HPP: `estimate_70pct` bila tak ada RAB tipe; kredit WIP sebatas saldo WIP seluruh org, sisanya `2-1700` (829 jt pada uji) | JV/00052, 00054, 00065 |
| AP tanpa PO / PO tipe baru → default `1-1600`; urutan pelunasan akrual `2-1700` mendahului WIP | JV/00056 (AP Rp 100 jt langsung Dr `2-1700`) |
| Komisi: beban `6-1100` saat disetujui (bukan biaya perolehan kontrak PSAK 72) | JV/00068 |
| PDC: memorandum `1-1350`/`2-1480` menggelembungkan neraca | JV/00081 |

## C. Ketidaksamaan angka yang terbukti
(angka dari instance uji akhir; lihat gl-1 §3 dan gl-2)
* `2-1400`: GL 1.432.474.134 · reconcile 1.255.000.000 · dasbor Keuangan 1.532.469.134.
* `1-1500`: GL 12.500.000 · ringkasan Kas Bon 7.500.000 (dua subledger).
* Kas: neraca 8.006.942.936 · Posisi Kas 15.761.930.872 (duplikasi GL via dialog legacy).
* Laba bersih: 602.331.517 (laporan lama) · 602.333.817 (neraca as-of) · 602.332.717 (L/R periode 2000-2099).
* Snapshot penutupan Okt `expense_at_close` 55.139.819 vs hidup 55.140.019.

## D. Risiko double-counting
* Denda → `4-1400` lalu masuk lagi di `4-1100` saat BAST (GL-02).
* BPHTB: titipan pembeli `2-1470` (all-in) **dan** `tax_records` BPHTB → `6-1400` (GL-04).
* Kas bon: modul Kas Bon dan Pengajuan Dana (type advance) sama-sama `1-1500` (GL-16).
* Biaya proyek: Pengajuan Dana `expense/biaya_proyek` → WIP langsung vs jalur PO/AP/SPK → WIP.
* `late_fee` + `ar_invoices.total` dipakai sebagai pendapatan (GL-02).
* Tutup tahun ulang (idempotensi menahan jurnal baru) (GL-03).
* Double-submit penerimaan (GL-22).

## E. Yang tidak bisa diaudit
* Jurnal manual: `source_id=None`, tanpa `source_event`, tanpa lampiran, tanpa pemeriksa kedua (18 dari 120 jurnal pada uji).
* Jurnal penerimaan/AP/komisi memakai `source_event=ev:<event>`; kuitansi/tagihan dapat dilacak, tetapi titipan, revrec, void, pembatalan penerimaan tidak membawa `source_deal_id` (jejak per-deal terputus).
* Jurnal tidak membawa proyek/unit/rekening-id/dokumen lampiran; sub-akun kas hanya dikenali dari kode.
* Hapus paksa menghilangkan jurnal TANPA jejak jurnal (hanya `audit_log` aplikasi) dan menyisakan BKM/BKK yatim.

---

# TEMUAN (urut severity)

### [GL-01] [Severity: Kritis] Penerimaan dan pemakaian titipan SETELAH BAST tetap dikreditkan ke Kewajiban Kontrak `2-1400`; piutang `1-1300` tak pernah turun
- Label bukti: [TERBUKTI-API]
- Lokasi: `backend/gl_engine.py:263-284` (`_gl_payment_received` selalu Cr `2-1400`), `:301-315` (`_gl_deposit_applied` Cr `2-1400`), `backend/finance_engine.py:574-580` (`contract_liabilities.$inc` tanpa menengok `recognized`), `backend/gl_engine.py:412-437` (BAST membentuk `1-1300`); `bank_match.py:312` (void mendebet `2-1400`).
- Langkah reproduksi: login superadmin → (1) `POST /finance/ar/receipts` Rp 100 jt untuk deal 76278c70 (A-02) → (2) `POST /finance/ar/{deal}/bast` (JV/00054: Dr `2-1400` 100 jt, Dr `1-1300` 750 jt, Cr `4-1100` 850 jt) → (3) `POST /finance/ar/receipts` Rp 200 jt. Hasil nyata: JV/00055 Dr bank 200 jt / **Cr `2-1400` 200 jt**; `1-1300` tetap 750 jt; `contract_liabilities.balance=200 jt` dengan `recognized=true`; `/finance/reconcile` → 2-1400 MERAH (GL Rp 2,3 M vs subledger Rp 2,1 M); sama untuk titipan dipakai (JV/00060) dan pencocokan bank AR (JV/00113). Seharusnya: Cr `1-1300` (mengurangi piutang), kewajiban kontrak tidak bertambah.
- Dampak bisnis: setelah BAST, setiap termin pasca-serah-terima (pelunasan KPR, sisa DP) menggelembungkan Kewajiban Kontrak (liabilitas) DAN Piutang (aset) secara permanen; neraca tampak "seimbang" tetapi aset & liabilitas sama-sama terlalu besar; rasio lancar/DER salah; tutup bulan tertahan oleh tie-out; piutang tidak pernah bisa ditagih bersih di GL.
- Akar masalah & arah: handler penerimaan tidak mengenal keadaan kontrak (belum/sudah diakui). Arah: peta posting bersyarat (profil posting dengan syarat `contract.recognized`) — Cr `1-1300` bila deal sudah BAST; hentikan `$inc contract_liabilities` untuk deal `recognized`; lihat gl-5 §Syarat.

### [GL-02] [Severity: Kritis] Denda keterlambatan dihitung dua kali sebagai pendapatan dan piutang dendanya tak pernah lunas
- Label bukti: [TERBUKTI-API]
- Lokasi: `late_fee_engine.py:292-299` (Dr `1-1300`/Cr `4-1400`), `finance_engine.py:849` (`price = ar_invoices.total`, total memuat item denda), `gl_engine.py:412-437`.
- Langkah reproduksi: deal baru (A-03) → skema bayar uji dengan jatuh tempo mundur → `POST /finance/late-fees/{deal}/apply` (JV/00062-63: Dr `1-1300` 22,95 jt / Cr `4-1400` 22,95 jt; total AR naik jadi 872,95 jt) → `POST /finance/ar/receipts` melunasi 872,95 jt (JV/00064: Cr `2-1400` 872,95 jt) → `POST /finance/ar/{deal}/bast` (JV/00065: Cr `4-1100` **872,95 jt**). Hasil nyata: `4-1400`=22,95 jt **dan** `4-1100` memuat 22,95 jt denda yang sama; `1-1300` denda 22,95 jt tidak pernah dikreditkan. Seharusnya: pelunasan denda mengkredit `1-1300`; pendapatan BAST = harga unit (+add-on) tanpa denda.
- Dampak bisnis: pendapatan dilebihkan sebesar seluruh denda tertagih; piutang aset tetap menumpuk; denda yang diringankan (`waive`) membalik 4-1400 tetapi pendapatan BAST tetap memuat nilai awal bila belum dikoreksi.
- Akar masalah & arah: satu rekening AR (`ar_invoices.items`) mencampur termin unit, add-on, denda; jurnal penerimaan tidak mengenali jenis item yang dialokasikan (`receipt.allocations`). Arah: posting per-jenis-alokasi (termin → `2-1400`, denda → `1-1300`), dan `recognize_revenue` memakai Σ item non-penalti.

### [GL-03] [Severity: Kritis] Tutup tahun → buka kembali → tutup lagi: status "tertutup" tanpa jurnal penutup baru; laba berjalan tak pernah masuk Laba Ditahan
- Label bukti: [TERBUKTI-API]
- Lokasi: `closing_engine.py:437-498` (`year_close`, `source_event=f"year_close:{org}:{year}"`), `:501-` (`year_reopen`), `gl_engine.py:127-131` (dedup `source_event` mengembalikan jurnal lama).
- Langkah reproduksi: tutup bulan 08-12 (override) → `POST /gl/year/close {year:2026}` (JV/00118, `3-1900` +602.333.817, P&L 0) → `POST /gl/year/reopen` (JV/00119 pembalik) → tutup Des → `POST /gl/year/close` lagi. Hasil nyata: 200, `idempotent=false`, `entry_no=JV/2026/00118` (jurnal lama), 0 jurnal baru; P&L 2026 kembali Rp 2.898.442.000 pendapatan/Rp 2.296.108.283 beban, `3-1900`=0; dokumen `gl_year_closings.state=closed`, `reversal=None`. Seharusnya: jurnal penutup baru (kunci bersyarat versi/penutupan ke-n) atau ditolak.
- Dampak bisnis: tahun buku tampak ditutup padahal akun laba-rugi masih terbuka — ekuitas tidak benar, laba tahun lalu bercampur dengan tahun berjalan pada laporan kumulatif; audit eksternal menemukan "tertutup" tanpa jurnal.
- Akar masalah & arah: kunci idempotensi tidak membawa nomor siklus penutupan; reopen membuat jurnal 31 Des yang juga mensyaratkan Des ditutup lagi. Arah: kunci `year_close:<org>:<thn>:<n>` + guard bahwa jurnal penutup aktif ada dan tak dibalik sebelum mengatakan `closed`.

### [GL-04] [Severity: Tinggi] PPN keluaran, PPh final & BPHTB dibebankan ke `6-1400`; PPN tidak dipisah dari pendapatan; PPN masukan tidak dibukukan
- Label bukti: [TERBUKTI-API] (JV/00078, 00080, 00102, 00107) + [DARI-KODE]
- Lokasi: `gl_engine.py:454-465` (`post_tax_accrual`: semua jenis Dr `6-1400`/Cr `2-1300`), `finance_engine.py:376-396` (`tax_records` PPN = `price × ppn_rate`, AR tidak memuat PPN), `tax_engine.py:ppn_input` (masukan hanya estimasi).
- Langkah reproduksi: `PUT /tax/records/{ppn}` status `reported` lalu `paid` pada deal A-02 → Dr `6-1400` 102 jt / Cr `2-1300`; Dr `2-1300`/Cr bank. Hasil nyata: PPN keluaran menjadi BEBAN (laba turun Rp 102 jt per deal Rp 850 jt) sementara pendapatan `4-1100` = harga penuh. BPHTB (pajak pembeli; di skema all-in titipan `2-1470`) juga dibeban. Tidak ada akun PPN masukan/keluaran; AP dibukukan bruto ke WIP/persediaan.
- Dampak bisnis: laba bersih tidak mencerminkan PPN yang seharusnya hanya kewajiban kolektif; SPT Masa PPN (modul `vat-return`) tidak berpasangan dengan buku besar; potensi dobel BPHTB (titipan + beban). (ASUMSI perlu konfirmasi: apakah harga jual inklusif PPN — lihat Pertanyaan Terbuka.)
- Akar masalah & arah: satu peta pajak generik. Arah: profil posting per jenis pajak (PPN keluaran → `2-13xx` PPN Keluaran, masukan → aset PPN Masukan, PPh final → beban/utang, BPHTB → titipan bila pass-through) dengan DPP terpisah dari harga.

### [GL-05] [Severity: Tinggi] "Hapus paksa" kuitansi/deal/proyek MENGHAPUS jurnal secara fisik, menyisakan bukti kas yatim dan subledger tak sinkron
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/ar_router.py:246-263` → `force_delete.py:133-195` (`_del("journal_entries",…)` baris 177; deal cascade baris 87), `routers/projects_router.py:142`.
- Langkah reproduksi: `DELETE /finance/ar/receipts/{id}?reason=...` (superadmin) pada kuitansi KWT/2026/0004 (Rp 100 jt, JV/00048). Hasil nyata: `removed={journal_entries:1, receipts:1}`; saldo `1-1202` −100 jt dan `2-1400` −100 jt; nomor JV/2026/00048 hilang (celah nomor); `BKM/2026/0009` tetap ada menunjuk jurnal tak ada; `contract_liabilities` tidak diubah; tidak ada jurnal balik; periode tertutup tidak dicek.
- Dampak bisnis: buku besar bisa diubah mundur tanpa jejak jurnal (hanya `audit_log`), melanggar prinsip jurnal immutable/penomoran berurutan; uang yang SUDAH masuk ke bank hilang dari buku (rekonsiliasi bank menjadi "tak terjelaskan"); sub-ledger titipan/kewajiban dapat saling berbeda; bukti kas yatim.
- Akar masalah & arah: koreksi dilakukan dengan menghapus, bukan membalik. Arah: ganti dengan jurnal pembalik berjejak (`void_receipt` generik untuk semua kuitansi), larang hapus jurnal; sisakan hapus paksa hanya untuk data uji dengan guard periode/rekonsiliasi.

### [GL-06] [Severity: Tinggi] Jurnal manual menerima tanggal tak valid/masa depan: memutus layar Tutup Buku/Paket Owner (HTTP 500), menembus kunci periode, dan tak bisa dihapus
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `routers/gl_router.py:76-91` (tanpa validasi `date`), `gl_engine.py:164` → `gl_periods.resolve_post_date` (`period_of(...)=None` → lolos), `routers/gl_reports_router.py:125-150` (`m=str(date)[:7]` → `month_range` ValueError), `closing_engine.year_list`.
- Langkah reproduksi: `POST /gl/journals {date:"bukan-tanggal", lines:[6-1300 Dr 1000, 2-1100 Cr 1000]}` → 200 (JV/00092). Lalu `GET /gl/periods`, `/gl/year`, `/gl/reports/closing-history` → **500**. UI: Akuntansi → Buku Besar & Jurnal → tab "Penutupan Buku" menampilkan "Gagal memuat daftar periksa tutup buku / status tutup tahun"; Laporan Keuangan → "Paket Laporan Owner" & "Tutup Periode" "Gagal memuat…" (screenshot `img/gl/acc_Penutupan_Buku.png`, `rep_Tutup_Periode.png`). Setelah Okt ditutup, `date:"xx"` tetap DITERIMA (menembus kunci). Juga `date:"2030-01-15"` diterima (masuk laporan semua-tanggal tetapi tidak laporan as-of).
- Dampak bisnis: satu salah ketik oleh finance/owner melumpuhkan proses tutup buku dan menyembunyikan jurnal dari laporan periode; jurnal tak bisa dihapus/dikoreksi tanpa akses DB; periode tutup dapat ditembus.
- Akar masalah & arah: `JournalCreate.date` bebas string. Arah: validasi ISO date, tolak masa depan, tolak tanggal di luar tahun fiskal terbuka; endpoint daftar periode harus tahan data buruk.

### [GL-07] [Severity: Tinggi] Pengakuan pendapatan (BAST) hanya tombol manual finance — tanpa gerbang pelunasan/serah terima, terpisah dari dokumen serah terima
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- Lokasi: `routers/ar_router.py:224-232` (`finance:update`), `finance_engine.py:837-880`; `unit_handovers` tidak memanggil `recognize_revenue` (grep: satu-satunya pemanggil adalah router ini).
- Langkah reproduksi: deal A-02 baru dibayar Rp 100 jt dari Rp 850 jt → `POST /finance/ar/{deal}/bast` → 200: pendapatan Rp 850 jt diakui, `1-1300` 750 jt (JV/00054). Tidak ada pengecekan handover/AJB/pelunasan.
- Dampak bisnis: titik pengakuan PSAK 72 (pengendalian berpindah) ditentukan klik; pendapatan dapat diakui tanpa serah terima, atau serah terima terjadi tanpa pendapatan (seed: 2 deal `completed` tanpa revrec); HPP diestimasi 70% bila RAB tak ada.
- Akar masalah & arah: dua "BAST" tak terhubung. Arah: pengakuan dipicu oleh dokumen serah terima + syarat kontrak (profil posting dengan syarat), bukan endpoint bebas; log `cogs_source`.

### [GL-08] [Severity: Tinggi] Dialog "Rekonsiliasi Bank → + Rekening" (`/bank/accounts`) menerima akun GL apa pun: Piutang/WIP/induk, dan akun kembar menggandakan saldo kas
- Label bukti: [TERBUKTI-UI] + [TERBUKTI-API]
- Lokasi: `routers/bank_router.py:39-81`, UI `frontend/src/components/finance/BankAccountDialog.js:35-40` (dropdown memuat semua `1-1*`), bandingkan `cash_bank.create_account` (aman).
- Langkah reproduksi: Keuangan → tab Rekonsiliasi Bank → "+ Rekening": dropdown akun menampilkan `1-1100 Kas … 1-1300 Piutang Usaha, 1-1400 Persediaan, 1-1500 Kas Bon, 1-1600 WIP, 1-1700, 1-1800` (screenshot `img/gl/fin_bank_dialog_gl_options.png`). Via API: `POST /bank/accounts {gl_account_code:"1-1300"}` → 200; `POST /bank/accounts {gl_account_code:"1-1201"}` (kedua) → 200; `PUT /bank/accounts/{id} {gl_account_code:"1-1200"}` → 200. Hasil: Posisi Kas "Total Kas & Bank Rp 15.761.930.872" vs kas neraca Rp 8.006.942.936; piutang Rp 772,95 jt muncul sebagai saldo "bank"; jurnal piutang menerbitkan BKM (BKM/2026/0025).
- Dampak bisnis: laporan kas/bank di layar tidak bisa dipercaya; rekonsiliasi bank terhadap akun yang salah; bukti kas palsu untuk akun non-kas.
- Akar masalah & arah: dua jalur master rekening (`/bank` lama vs `/cash-bank`), jalur lama tanpa validasi. Arah: hapus pembuatan rekening dari `/bank`, validasi unik/tipe/induk pada satu master, dan dropdown hanya memuat sub-akun kas/bank yang tersedia.

### [GL-09] [Severity: Tinggi] Event pembukuan yang gagal menjadi `failed` permanen tanpa retry; endpoint tetap menjawab sukses; AP menerima retensi >100%
- Label bukti: [TERBUKTI-API]
- Lokasi: `engine.py:638-652` (`dispatch_pending`: 3 kali lalu `failed`, tanpa endpoint requeue), `finance_ap.py:15-35` (tanpa validasi `retention_pct` 0-100), `finance_ap.py:43-44` (approve selalu 200).
- Langkah reproduksi: `POST /finance/ap/bills {claimed:10jt, retention_pct:150}` → net −5 jt; `POST …/approve` → 200 "approved"; event `ap.approved` → `status=failed, retries=3, last_error="Nilai debit/kredit tidak boleh negatif."`; 0 jurnal; `/finance/reconcile` `events_failed=1`, 2-1100 −5,0 jt selisih, 2-1200 −15 jt selisih.
- Dampak bisnis: tagihan "disetujui" dan bisa dibayar tanpa jurnal; hanya lampu reconcile yang tahu; tidak ada cara memproses ulang selain edit DB.
- Akar masalah & arah: GL asinkron tanpa jalur pemulihan/antrian pending terlihat. Arah: validasi di hulu, status event `failed` terlihat di layar dengan tombol "proses ulang" (setelah koreksi), dan posting sinkron bagi transaksi uang.

### [GL-10] [Severity: Tinggi] Tidak ada jalur koreksi/pembalikan akuntansi yang layak
- Label bukti: [TERBUKTI-API] (tax) + [DARI-KODE]/openapi (rute)
- Lokasi: tidak ada rute void/reject untuk `/finance/ap/bills*` (daftar rute OpenAPI), `bank_match.void_receipt` hanya dipanggil dari `unmatch` dan `kpr_disburse.py:289`, `tax_router.update_record` (status mundur), `procurement_extra.py:152-157` (menolak retur jika sudah ditagih dengan saran "nota kredit" yang tak ada).
- Langkah reproduksi: (a) `PUT /tax/records/{id} {status:"pending"}` setelah `paid` → 200, 0 jurnal balik, DB "pending" padahal JV/00078-79 masih ada. (b) AP: tidak ada endpoint reject/void/bayar-batal. (c) Kuitansi manual: hanya `DELETE` hapus paksa (GL-05).
- Dampak bisnis: kesalahan input tak bisa dikoreksi sesuai standar (jurnal balik); tim memakai jurnal manual langsung ke akun kendali atau hapus paksa.
- Akar masalah & arah: fitur koreksi tidak dirancang sebagai first-class. Arah: dokumen-pembalik per jenis (void AP, void kuitansi, nota kredit/debit, balik pajak) yang menghasilkan jurnal cermin dengan `source_id` asal.

### [GL-11] [Severity: Tinggi] Jurnal tanpa dimensi (proyek/unit/rekening); WIP & HPP org-wide; laporan per proyek tak lengkap; cek hapus-proyek "jurnal" selalu 0
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- Lokasi: `gl_engine.py:113-187` (tak ada parameter dimensi), `revrec_cogs.py:62-78` (`account_balance` seluruh org), `gl_reports.py:326-375` vs `gl_project_cash.py:43-93` (dua resolver), `master_delete.py:138` (`journal_entries {project_id}`), `routers/projects_router.py:142`.
- Langkah reproduksi: BAST deal B (JV/00054) mengkredit `1-1600` Rp 261 jt = sisa saldo WIP seluruh organisasi (setelah BAST A mengosongkan Rp 595 jt) dan sisa HPP ke `2-1700`; `GET /gl/reports/projects` → pendapatan "Tidak teralokasi" Rp 302.542.000 termasuk potongan pembatalan Rp 297,5 jt yang punya `source_deal_id`; arus kas per proyek: Rp 6,88 M dari Rp 8,01 M "tidak teralokasi". DB: 0 dari 120 jurnal punya `project_id`.
- Dampak bisnis: laba/rugi, WIP, HPP dan kas per proyek tidak bisa diaudit; HPP unit dibebankan dari WIP proyek lain; keputusan owner per proyek salah; hapus proyek tidak "melihat" jurnal; `delete_many journal project_id` tidak menghapus apa pun.
- Akar masalah & arah: dimensi tidak dimodelkan di jurnal. Arah: tambah dimensi (proyek/unit/deal/rekening) pada baris jurnal, WIP/akrual per proyek/unit.

### [GL-12] [Severity: Tinggi] Persediaan/material tidak berjurnal dan tidak bernilai
- Label bukti: [DARI-KODE]
- Lokasi: `routers/materials_router.py:179-204` (txn in/out), `:208-226` (opname), `procurement_extra.py:171-181` (retur), `stock_control.py`; `gl_engine.py:339-345` (`1-1400` hanya naik dari AP PO-material).
- Langkah/hasil: tidak ada `post_journal` pada seluruh modul material; stok keluar ke proyek tidak memindahkan `1-1400`→`1-1600`; selisih opname tak dibukukan; GRN tanpa akrual.
- Dampak bisnis: `1-1400` Persediaan Material hanya bertambah (pada uji tetap Rp 325 jt); biaya material proyek tidak masuk WIP/HPP; anggaran vs realisasi (budget_engine) membaca `material_txns` sedangkan GL membaca AP → dua versi biaya proyek.
- Arah: nilai persediaan (rata-rata tertimbang) + jurnal pemakaian/penyesuaian; akrual GRNI.

### [GL-13] [Severity: Sedang] Perubahan CoA tidak mengikat posting & validasi kode akun nihil
- Label bukti: [TERBUKTI-API]
- Lokasi: `gl_engine.py:144-146` (hanya cek keberadaan), `routers/gl_router.py:37-50,126-168`.
- Langkah reproduksi: `PUT /gl/accounts/2-1400 {is_active:false}` → 200, lalu penerimaan baru tetap memposting Cr `2-1400` (JV baru); `PUT … {name:"Pendapatan Penjualan (diganti)"}` diizinkan untuk akun terpakai (nama baris jurnal tersimpan sebagai snapshot lama); `PUT /gl/accounts/1-1700 {type:"revenue"}` diizinkan (belum terpakai); `POST /gl/accounts` menerima kode `"ABC"`, `"2-1400 "` (spasi — mirip akun kendali), `4-9999` bertipe asset, `1-1203` dengan `parent_code=1-1200`; `PUT /gl/accounts/1-1202 {is_active:false}` menonaktifkan sub-akun kas namun master rekening tetap aktif.
- Dampak bisnis: user dengan izin CoA dapat memutus/mengaburkan pemetaan sistem tanpa efek yang terlihat; akun mirip menyesatkan; tidak ada penanda akun-sistem/induk di layar.
- Arah: penanda `system_role`, kunci akun yang dirujuk profil posting, validasi format/prefiks-vs-tipe, `post_journal` menolak akun nonaktif/header.

### [GL-14] [Severity: Sedang] Klasifikasi arus kas salah (metode langsung berdasarkan prefiks akun lawan)
- Label bukti: [TERBUKTI-API]
- Lokasi: `gl_reports.py:25-29,270-324`.
- Hasil: `2-2100` Utang Bank/Leasing (`2-2` tidak masuk prefiks pendanaan) → **operasi** (+Rp 960 jt pada uji pinjaman Rp 1 M); `1-1800` uang muka subkon → **investasi** (−30 jt); `2-1500` marketing fee dan `2-17xx` akrual HPP → **pendanaan**; `1-2200` akumulasi penyusutan (non-kas) muncul di investasi; saldo awal "in-kind" (`1-1400`/`1-1600` vs `3-1100` pada seed) tampil sebagai arus operasi/pendanaan padahal non-kas. `reconciled` selalu true.
- Dampak: laporan arus kas menyesatkan bagi bank/investor; kovenan.
- Arah: pemetaan arus kas per akun/peran di profil posting (aktivitas operasi/investasi/pendanaan) dan pengecualian non-kas.

### [GL-15] [Severity: Sedang] Tanggal & periode: tiga definisi "periode", jurnal masuk periode tertutup via selisih zona, posting digeser ke masa depan, dan transaksi uang tak bisa diberi tanggal
- Label bukti: [TERBUKTI-API]
- Lokasi: `core_utils.period_of` (WIB) vs `gl_reports._date_query` (potongan string UTC) vs `cash_period_lock.resolve_date` (`[:7]`); `gl_periods.py:36-62`; `finance_engine.apply_receipt` (tanpa tanggal), `finance_ap.pay_ap_bill`, `finance_engine.pay_commission`.
- Hasil: jurnal manual 2026-10-31T20:00Z (=1 Nov WIB) dan 17:30Z diterima SETELAH Oktober ditutup, lalu masuk Laba Rugi Oktober → `expense_at_close` 55.139.819 vs hidup 55.140.019; marketing fee diposting bertanggal **2027-01-01** setelah semua bulan s.d. Nov-Des ditutup (JV/00124-125) — Posisi Kas memuatnya, neraca per hari ini tidak; penerimaan/AP/komisi/pajak (event) selalu bertanggal "sekarang" sehingga penerimaan bertanggal mundur (mutasi bank 20 Okt dicocokkan 5 Nov) tidak mungkin dicatat bertanggal benar.
- Dampak: laporan periode tertutup berubah; lonjakan perbedaan timing rekonsiliasi bank.
- Arah: satu fungsi periode (WIB) dipakai semua, tanggal transaksi (`value_date`) di setiap alur uang, posting otomatis ke periode terbuka terdekat bukan ke masa depan.

### [GL-16] [Severity: Sedang] Kas bon punya dua sistem (Kas Bon & Pengajuan Dana) yang sama-sama menjurnal `1-1500`
- Label bukti: [TERBUKTI-API]
- Lokasi: `petty_cash.py:137-197` dan `fund_requests.py:188-226`.
- Hasil: pengajuan `type=advance` cair Rp 5 jt (JV/00070) → `1-1500` GL Rp 12,5 jt, ringkasan Kas Bon `outstanding_amount` Rp 7,5 jt; tidak ada tie-out `1-1500`.
- Dampak: uang muka karyawan tak terkendali; pertanggungjawaban terpisah.
- Arah: satu modul kas bon, atau tie-out gabungan + profil posting yang sama.

### [GL-17] [Severity: Sedang] Banyak alur tidak bisa memilih rekening; booking fee tunai masuk bank; komisi tidak bisa dibayar dari UI
- Label bukti: [TERBUKTI-API] (booking fee) + [DARI-KODE] (UI)
- Lokasi: `booking_fee.pay` → `_deposit_move(...)` tanpa `cash_account_id`; `routers/ar_router.py` `DepositReceive/DepositRefund`; `allin_engine.py:413,438`; `loans.py`, `fixed_assets.py`, `marketing_fee.py`, `subcon_finance.py:87`, `labor_engine.py:370` (header → default); UI `CommissionsPanel.js` (hanya approve).
- Hasil: `POST /booking-fee/deals/{id}/pay {method:"cash"}` → Dr `1-1201` Bank Mandiri / Cr `2-1450` (JV/00116) dengan memo "(kelebihan bayar)". Lihat tabel gl-3 §2.
- Dampak: saldo kas vs bank salah; rekonsiliasi bank mismatch; Kas Besar tidak pernah menerima setoran tunai booking.
- Arah: `cash_account_id` wajib/default per metode di semua alur uang; profil posting memegang aturan default.

### [GL-18] [Severity: Sedang] Saldo kas negatif tidak dicegah di sebagian besar alur
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `finance_ap.pay_ap_bill` tanpa cek saldo; hanya `cash_bank.create_transfer` & `petty_expense.create_expense` memeriksa.
- Hasil: bayar AP Rp 40 jt dari Kas Kecil Site (saldo 0) → 200; saldo −Rp 37 jt; banner "Saldo buku negatif" di Posisi Kas.
- Arah: kebijakan saldo negatif per rekening (blok/peringatan/izin) di profil posting.

### [GL-19] [Severity: Sedang] Konfigurasi dekoratif & hardcode: `gl_account` komponen harga/add-on tidak dipakai; komponen biaya tanpa validasi; ±25 file memuat literal akun
- Label bukti: [DARI-KODE] (+ UI memuat dropdown)
- Lokasi: `catalog.py:28-67` (`gl_account` per komponen), `frontend/.../AddonPanel.js:201`, `PriceComponentPanel.js:151`; tak ada pembaca di jurnal (`grep gl_account`); `routers/allin_router.py:132` (tanpa validasi akun); `allin_engine.py:413` memakai `GL_TITIPAN_BIAYA` hardcode (bukan `comp.gl_liability`) sedangkan baris 282 memakai komponen; `record_developer_expense` (`allin_engine.py:455-473`) membuat AP bill `approved` baru memposting — bila akun salah, bill tersisa tanpa jurnal.
- Dampak: admin menyangka konfigurasi akun berlaku (UI "Akun GL" pada add-on) padahal semua pendapatan masuk `4-1100`; pass-through komponen tak ke akun yang dipilih.
- Arah: gl-5.

### [GL-20] [Severity: Sedang] Penjaga tie-out sempit dan bergantung saldo kumulatif; tiga angka kewajiban kontrak
- Label bukti: [TERBUKTI-API]
- Lokasi: `finance_audit.py:28-80` (5 akun), `closing_engine.py:203-259` (4 akun, memakai `_gl_balance(org, code)` tanpa batas periode), `finance_engine.finance_summary` (dasbor).
- Hasil: lihat §C. Tidak ada tie-out untuk `1-1300`, `1-1500`, `2-1500`, `2-1460`, `2-1470`, `1-1350/2-1480`, `2-2100`, `1-2100/1-2200`, `2-1300`, kas vs rekening, `1-1600`, `1-1400`, `4-1400`. Jurnal manual ke akun kendali (Rp 4.821 pada 2-1100) memblok penutupan semua periode.
- Arah: tie-out per periode untuk semua akun terpetakan, lahir dari profil posting.

### [GL-21] [Severity: Sedang] Jurnal manual tanpa persetujuan kedua, ke akun kendali, tanpa lampiran; induk kas dialihkan diam-diam; satu baris Dr=Cr diterima
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/gl_router.py:76-91`; `gl_engine.py:139-143`.
- Hasil: finance & owner posting langsung (200) ke `2-1400`/`1-1202` (JV/00094); `1-1200` → otomatis `1-1201`; baris Dr 1000/Cr 1000 pada akun sama menghasilkan 1 baris netto nol; memo kosong diterima; 18 jurnal manual tanpa `source_id`.
- Arah: maker-checker untuk jurnal manual, larangan ke akun kendali kecuali dengan alasan, lampiran wajib, tolak baris dua-sisi.

### [GL-22] [Severity: Sedang] Dua POST kuitansi identik serentak membuat dua kuitansi dan dua jurnal
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/ar_router.py:184-199` (tanpa `client_ref`); bandingkan refund (`client_ref` ada).
- Hasil: 2× `POST /finance/ar/receipts` Rp 1.234.567 serentak → 2 kuitansi, 2 jurnal (Cr `2-1400` 2.469.134).
- Dampak: klik ganda/timeout-retry menggandakan uang masuk di buku.
- Arah: kunci idempotensi per permintaan.

### [GL-23] [Severity: Sedang] Pembatalan kontrak tidak menyentuh komisi, marketing fee, dan catatan pajak — pajak deal batal masih bisa diakrual
- Label bukti: [TERBUKTI-API] (pajak) + [DARI-KODE]
- Lokasi: `cancellation_engine.decide` (tidak ada referensi komisi/fee/tax); `tax_router.update_record`.
- Hasil: setelah pembatalan A-06, `PUT /tax/records/{bphtb deal batal} {status:"reported"}` → 200, JV/00080 Dr `6-1400` 38,5 jt (beban untuk deal yang sudah batal).
- Arah: aturan turunan saat batal (balik/larang) di profil posting.

### [GL-24] [Severity: Sedang] Pinjaman & aset tetap: bunga basis kas, provisi dibeban sekaligus, tanah sebagai aset tetap, penyusutan alat proyek ke beban
- Label bukti: [TERBUKTI-API] (aset/pinjaman) + [DARI-KODE] (kebijakan)
- Lokasi: `loans.py:115-175` (bunga hanya saat dibayar, provisi `6-1600` penuh), `fixed_assets.py:156,198` (`1-2100` untuk semua kategori; `6-1500` untuk semua).
- Hasil: pinjaman Rp 1 M: provisi Rp 10 jt langsung beban (JV/00076); tidak ada akrual bunga antar-jatuh-tempo; "Tanah lahan pengembangan" Rp 2 M masuk `1-2100`.
- Dampak: persediaan lahan/WIP developer salah klasifikasi; biaya pinjaman proyek tidak dikapitalisasi (PSAK 26); beban bulanan tak akurat.
- Arah: akun persediaan lahan, akrual bunga, kapitalisasi (kebijakan per proyek) lewat profil posting.

### [GL-25] [Severity: Sedang] Laporan per-proyek memakai dua resolver berbeda dan mengabaikan `source_deal_id`
- Label bukti: [TERBUKTI-API]
- Lokasi: `gl_reports._project_resolver` (`:326-348`) vs `gl_project_cash.project_resolver`.
- Hasil: L/R per proyek menempatkan potongan pembatalan Rp 297,5 jt di "Tidak teralokasi" padahal `source_deal_id` ada; arus kas per proyek (resolver lebih luas) memberi hasil lain.
- Arah: dimensi di jurnal (GL-11) menghapus kebutuhan resolver.

### [GL-26] [Severity: Rendah] Giro (PDC) dijurnal sebagai memorandum yang menggelembungkan neraca
- Label bukti: [TERBUKTI-API]
- Lokasi: `pdc_engine.py:68-86`.
- Hasil: BG Rp 50 jt diterima → Dr `1-1350` / Cr `2-1480` (JV/00081): aset dan liabilitas naik tanpa uang; baru kliring mengakui kas.
- Dampak: rasio lancar/DER terlihat membaik/memburuk palsu selama giro di tangan. Dapat dipertahankan bila hanya di akun memorandum di luar neraca.

### [GL-27] [Severity: Rendah] Cacat laten
- Label bukti: [DARI-KODE]
- `finance_ap.py:116-134` `ap_retention_release_sweeper`: menandai retensi lepas + `payments_out` "Pelepasan retensi" tanpa jurnal (laten: tak ada kode yang menulis `release_due_at`).
- `cash_bank.py:87-104` `_migrate_header_lines` menulis ulang baris jurnal lama ke rekening default.
- `force_delete.py:90` menghapus `payments_out` memakai field `ap_invoice_id` yang tidak ada (field asli `bill_id`).
- `data_mgmt_purge.py:22` menghapus `journal_entries`, `accounting_periods`, `gl_year_closings`, `counters` dalam satu grup.
- Dua stack laporan paralel (`gl_engine.balance_sheet/income_statement` vs `gl_reports.*`) di-expose bersamaan.
- Pembayaran komisi lewat event: handler `commission.approved` mencari komisi per `deal_id` (bukan id) — salah komisi bila ada >1 per deal (seed).

### [GL-28] [Severity: Rendah] Cacat data seed demo
- Label bukti: [TERBUKTI-API]
- 2 deal `completed` tanpa `revenue_recognitions` (Rp 2,1 M tetap `2-1400`); 3 komisi pada satu deal (A-01).

---

## Terverifikasi OK
Lihat gl-2 §5 dan gl-3 §6.

## Tidak bisa diverifikasi
* Upah harian (`labor_engine.pay_payroll`) — alur worker/attendance tidak dijalankan; dari kode: `Dr 1-1600 / Cr 1-1200 default`, `auto=False` bertanggal `period_end`.
* Klaim subkon + potongan uang muka/retensi end-to-end — dari kode: amortisasi uang muka di subledger terjadi saat tagihan ditempeli potongan (sebelum disetujui), jurnal saat disetujui.
* Biaya all-in (invoice biaya/penyaluran/beban developer) dan KPR disbursement — jurnal dari kode saja.
* Crash di antara tulis subledger dan `emit` (tidak ada transaksi Mongo): hanya dari kode (`finance_engine.py:566-580`).
* Perilaku multi-worker (`_DEFAULT_CACHE`, `_ENSURED`), konkurensi `cogs_credit_lines` membaca saldo WIP lalu memposting (race).
* Data purge dan hapus paksa proyek (destruktif) tidak dijalankan.
* Pergeseran tanggal jam 17:00-24:00 UTC pada waktu nyata (diuji dengan tanggal eksplisit lewat jurnal manual).

## Pertanyaan terbuka
1. Apakah harga jual rumah diset inklusif PPN (rumah komersial) atau PPN-nya dipungut di luar harga? Menentukan perbaikan GL-04.
2. Siapa pemilik keputusan titik pengakuan pendapatan (serah terima fisik, AJB, atau pelunasan)? GL-07.
3. BPHTB: murni titipan pembeli, ditanggung developer (all-in), atau campuran per deal? GL-04.
4. Apakah komisi sales harus dikapitalisasi sebagai biaya perolehan kontrak (PSAK 72) atau dibeban saat disetujui?
5. Apakah satu organisasi memiliki banyak proyek dengan rekening escrow terpisah (butuh `project_id` pada rekening)?
