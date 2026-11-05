# GL-2 — Rekonsiliasi subledger ↔ GL secara nyata, periode & penutupan, laporan (Bagian C)

Semua dijalankan di instance #4 (DB `sipro_gl`, org `org-sipro`) lewat HTTP API (token superadmin/finance/owner) dan dibaca ulang langsung dari MongoDB (baca-saja). Skrip: (skrip uji tidak disertakan di repo) (t1…t31, recon_seed.py). Data uji berawalan "AUDIT-". Layar yang dicek dengan Playwright: `img/gl/` (ui1-ui5.js).

## 1. Baseline data seed (sebelum transaksi saya) — `recon_seed.py`

Seluruh pasangan subledger↔GL yang punya subledger **cocok persis**: 2-1100 (486.200.000), 2-1200 (4.800.000), 2-1400 (2.270.000.000 — 4 deal), 2-1450 (0), 2-1600 (17.000.000), 2-1500 (20.825.000), 1-1500 (7.500.000), 1-1800 (30.000.000), 2-2100 (4.764.952.371), 1-2100 (1.342.500.000), 1-2200 (33.375.004). Neraca saldo seimbang (Σ Dr = Σ Cr = 12.686.885.068); neraca (`/gl/balance-sheet` & `/gl/reports/balance-sheet`) seimbang; arus kas "reconciled". `/finance/reconcile` OK.
Catatan seed: 2 deal berstatus `completed` (A-06 Rp 850 jt, B-01 Rp 1,25 M) **tanpa** `revenue_recognitions` — `4-1100`=0 dan Rp 2,1 M tetap kewajiban kontrak; komisi seed 3 baris pada satu deal (A-01) padahal mesin menjaga 1 komisi/deal (`finance_engine.py:763`). Keduanya hanya mungkin lahir dari seed (tidak ada jalur produk yang membuat status `completed` tanpa BAST) — ini cacat data demo, bukan alur.

## 2. Hasil per alur yang berjurnal (transaksi nyata)

Kolom: Jurnal = jurnal terbentuk? · Seimbang · Akun benar? · Idempoten saat dipanggil ulang · Catatan. "JV" = nomor jurnal bukti.

| # | Alur (endpoint) | Jurnal | Seimbang | Akun | Ulang/idempoten | Hasil & catatan |
|---|---|---|---|---|---|---|
| T1 | Penerimaan Rp 100 jt ke rekening Escrow (`POST /finance/ar/receipts`, `cash_account_id`) | Ya (JV/00048, ±9 dtk kemudian) | Ya | Dr `1-1202` / Cr `2-1400` | — | OK. Memo selalu "(uang muka)" untuk semua jenis termin |
| T2 | Penerimaan tunai tanpa rekening (`method=cash`) | Ya (JV/00049) | Ya | Dr `1-1101` Kas Besar (default kas) / Cr `2-1400` | — | OK |
| T3 | Kelebihan bayar (`allow_overpay`) | Ya (JV/00050+00051) | Ya | 2 jurnal: Cr `2-1400` 530 jt + Cr `2-1450` 30 jt | — | OK; jurnal titipan tanpa `source_deal_id` |
| T4 | BAST deal lunas (`POST /finance/ar/{deal}/bast`) | Ya (JV/00052) | Ya | Dr `2-1400` 850 jt / Cr `4-1100` 850 jt; Dr `5-1100` 595 jt (estimasi 70%) / Cr `1-1600` 595 jt | **Ya**: BAST ke-2 tidak membuat jurnal | OK; HPP `estimate_70pct` karena tak ada RAB tipe |
| T5 | BAST deal baru terbayar 100 jt dari 850 jt | Ya (JV/00054) | Ya | Dr `2-1400` 100 jt + Dr `1-1300` 750 jt / Cr `4-1100` 850 jt; Dr `5-1100` 595 jt / Cr `1-1600` 261 jt (sisa saldo WIP) + Cr `2-1700` 334 jt | – | **Tidak ada gerbang** pelunasan/serah-terima (GL-07) |
| **T6** | **Penerimaan 200 jt SETELAH BAST** | Ya (JV/00055) | Ya | **Dr bank / Cr `2-1400`** (seharusnya Cr `1-1300`) | – | **GL-01**: `1-1300` tetap 750 jt; `contract_liabilities.balance` naik walau `recognized=true`; `/finance/reconcile` 2-1400 MERAH (GL 2,3 M vs subledger 2,1 M) |
| T11 | Titipan masuk / dipakai / dikembalikan pada deal pasca-BAST | Ya (JV/00059-61) | Ya | pakai titipan → Dr `2-1450` / Cr `2-1400` (lagi) | – | Akar sama dengan GL-01 |
| T13 | Denda: apply lalu lunas total + BAST (deal 13223060) | Ya (JV/00062-65) | Ya | Denda: Dr `1-1300` / Cr `4-1400` 22,95 jt. Lunas: Cr `2-1400` 872,95 jt. BAST: Cr `4-1100` 872,95 jt | apply ke-2 ditolak 400 | **GL-02**: denda dihitung 2× pendapatan; `1-1300` denda tak pernah lunas |
| T7-T9 | AP: buat→setujui→bayar (dari rekening kas kecil saldo 0)→bayar+PPh | Ya (JV/00056-58) | Ya | Dr `2-1700` (akrual dilunasi dulu) / Cr `2-1100` 95 jt + `2-1200` 5 jt; bayar: Dr `2-1100` / Cr `1-1102`; PPh: Dr `2-1100` 30 jt / Cr bank 29,4 jt + `2-1300` 0,6 jt | setujui ke-2 → 400; bayar > sisa → 400; rekening tak ada → 400 | OK, kecuali **saldo kas kecil menjadi −40 jt** (GL-18) |
| T10 | Hapus paksa kuitansi (`DELETE /finance/ar/receipts/{id}`) | jurnal DIHAPUS | – | – | – | **GL-05**: JV/00048 hilang (celah nomor), BKM/2026/0009 yatim, `contract_liabilities` tak diubah, tanpa jurnal balik |
| T12 | Komisi: setujui ×2, bayar ×2 (`cash_account_id`) | Ya (JV/00068, 00069) | Ya | Dr `6-1100` / Cr `2-1600`; Dr `2-1600` / Cr `1-1202` | **Ya** (kedua kali tak menambah jurnal) | OK |
| T14 | Pembatalan kontrak: keputusan + bayar refund (`client_ref`) | Ya (JV/00066, 00067) | Ya | Dr `2-1400` 850 jt / Cr `4-1200` 297,5 jt + `2-1460` 552,5 jt; Dr `2-1460` / Cr `1-1201` | **Ya** (replay `client_ref` → tidak membayar dua kali) | OK; potongan masuk `4-1200` (H); pajak/komisi deal batal tidak disentuh (GL-23) |
| T15-16 | Pengajuan Dana: kas bon & beban langsung | Ya (JV/00070-71) | Ya | advance: Dr `1-1500` / Cr `1-1101`; expense `biaya_proyek`: Dr `1-1600` / Cr bank | – | **GL-16**: `1-1500` GL 12,5 jt vs ringkasan Kas Bon 7,5 jt |
| T20 | Kas Bon (petty-cash): setuju→cair→pertanggungjawaban | Ya (JV/00087-88) | Ya | Dr `1-1500` / Cr `1-1101`; settle: Dr `1-1600` 2 jt + `6-1300` 0,3 jt + Dr `1-1101` 0,7 jt / Cr `1-1500` 3 jt | cair ke-2 → 400 | OK |
| T22 | Aset tetap: perolehan bank, **tanah**, penyusutan ×2, masa depan, lepas ×2 | Ya (JV/00072-75) | Ya | Dr `1-2100` / Cr bank; dep Dr `6-1500` / Cr `1-2200`; lepas Dr bank + `1-2200` / Cr `1-2100` + `4-1300` | dep ke-2 → 0 baru; periode masa depan → 400; lepas ke-2 → 400 | OK; tanah tercatat sebagai Aset Tetap `1-2100` (Rp 2 M) |
| T23 | Pinjaman: buat→cair→angsuran | Ya (JV/00076-77) | Ya | Dr bank 990 jt + `6-1600` 10 jt / Cr `2-2100` 1 M; angsuran Dr `2-2100` 40 jt + `6-1600` 10 jt / Cr bank | – | OK; **arus kas**: utang bank terklasifikasi OPERASI (GL-14) |
| T24 | Pajak: reported → paid (± ulang, ± balik ke pending) | Ya (JV/00078-79) | Ya | Dr `6-1400` 102 jt (PPN keluaran!) / Cr `2-1300`; Dr `2-1300` / Cr bank | paid ke-2 → tidak ada jurnal baru | **GL-04** (PPN dibebankan) dan **GL-10** (balik ke pending tanpa jurnal) |
| T25 | Giro (PDC): terima → kliring (rekening kas ditolak) → tolak | Ya (JV/00081-83) | Ya | Dr `1-1350` / Cr `2-1480`; kliring: balik + Cr `2-1400` (apply_receipt) | – | OK sebagai "memorandum"; menggelembungkan neraca Rp 50 jt selama giro di tangan |
| T26 | Bank: impor mutasi, cocokkan AR/biaya/jasa giro, batalkan | Ya (JV/00111-115) | Ya | biaya `6-1600`, jasa giro `4-1200`, receipt_void Dr `2-1400` / Cr bank | – | OK; rekonsiliasi `unexplained=0` |
| T27 | Booking fee tunai (`method=cash`) lalu pesan | Ya (JV/00116-117) | Ya | Dr **`1-1201` Bank Mandiri** / Cr `2-1450`; lalu Dr `2-1450` / Cr `2-1400` | – | **GL-17**: booking fee tunai masuk BANK; memo "kelebihan bayar" |
| T28 | Marketing fee: setujui+bayar | Ya (JV/00124-125) | Ya | Dr `6-1200` / Cr `2-1500`+`2-1300`; lalu Dr `2-1500` / Cr bank | – | OK; **tanggal jurnal 2027-01-01** (GL-15) |
| T29 | Jurnal manual (10 skenario) | Ya | Ya, ditolak bila tak seimbang/negatif/akun tak ada | lihat GL-06, GL-21 | – | tanggal sampah/2030/akun kendali/induk kas diterima |
| T30 | Tutup bulan, jurnal manual di periode tutup, posting otomatis di periode tutup | – | – | – | – | manual ditolak; otomatis digeser dengan catatan memo (OK); lihat §3 |
| T31 | AP retensi 150% | **Tidak** (event `failed`) | – | – | – | **GL-09** |
| T32 | Dua POST kuitansi identik serentak | Ya ×2 | Ya | 2 kuitansi + 2 jurnal | tidak idempoten | **GL-22** |
| — | Tidak dijalankan | | | | | Upah harian (labor_engine), klaim/potongan subkon, biaya all-in (invoice/penyaluran/beban dev.), KPR disbursement, retensi subkon end-to-end: lihat "Tidak bisa diverifikasi" |

Status akhir `/finance/reconcile` (setelah uji): `ok=false` — 2-1100 selisih 5.004.821; 2-1200 −15.000.000; 2-1400 +177.474.134; `events_failed=1`. Semua selisih dapat ditelusuri ke temuan GL-01 (+ jurnal manual saya ke akun kendali = Rp 4.821 pada 2-1100 dan Rp 1.000/1.000 dst) dan GL-09.

## 3. Periode & penutupan

| Uji | Hasil |
|---|---|
| `close-check` periode 2026-08/10 setelah transaksi saya | tie-out BLOCKING (2-1100/2-1400) → `POST /gl/periods/close` → **409 DITAHAN** (OK: gerbang bekerja; tetapi cek memakai saldo KUMULATIF sekarang, jadi jurnal manual ke akun kendali di periode mana pun memblok penutupan SEMUA periode) |
| Tutup dengan `override` + alasan | 200 (hanya peran `gl:close_override`); periode tidak harus berurutan (Okt ditutup tanpa Agu/Sep) |
| Jurnal manual bertanggal di periode tutup | 400 "Periode 2026-10 sudah ditutup" (OK) |
| Jurnal manual `date="xx"` / `"bukan-tanggal"` | **DITERIMA** — tidak ada validasi format, `period_of()` mengembalikan `None` sehingga kunci periode terlewati (GL-06) |
| Jurnal manual 2026-10-31T20:00:00+00:00 (=1 Nov WIB) dan 2026-10-31T17:30Z | DITERIMA setelah Okt ditutup; di laporan Laba Rugi Oktober (bucket tanggal UTC) ia MASUK → snapshot saat tutup `expense_at_close`=55.139.819 vs live=55.140.019 (GL-15) |
| Posting otomatis (setor pajak `paid_date` 2026-10-20) di periode tutup | digeser ke periode terbuka + catatan "posting digeser (periode 2026-10 ditutup)" (OK) |
| Posting otomatis saat SEMUA bulan s.d. bulan berjalan ditutup (marketing fee) | tanggal jurnal **2027-01-01** (masa depan; `gl_periods.py:56-62`) — saldo kas di layar Kas&Bank (semua tanggal) ≠ neraca "per hari ini" |
| Buka kembali periode oleh finance | 403 (butuh `gl:approve`) — OK |
| Tutup tahun 2026: pertama kali | OK: JV/00118 (31 Des), P&L tahun → 0, `3-1900` +602.333.817, TB seimbang |
| Buka tahun lagi (reason ≥10 huruf) | OK: JV/00119 pembalik; P&L pulih. **Namun** jurnal pembalik bertanggal 31 Des membuat Des "bertransaksi & belum ditutup" → tutup tahun ditahan sampai Des ditutup |
| **Tutup tahun ulang** (setelah Des ditutup) | **200 "closed" tanpa jurnal baru** (`idempotent` pada kunci `year_close:<org>:2026` → mengembalikan jurnal LAMA yang sudah dibalik): `P&L 2026` tetap Rp 2,898 M pendapatan, `3-1900`=0, dokumen penutupan `state=closed`, `reversal=None` (GL-03) |
| Jurnal 15 Des 2026 sesudah tutup tahun | diterima (Des belum ditutup) — tidak ada larangan posting ke tahun yang "ditutup" selama bulannya terbuka |

## 4. Laporan: konsistensi antar-laporan & layar

* `/gl/balance-sheet` (legacy, semua tanggal) vs `/gl/reports/balance-sheet` (as-of hari ini): total aset 12.472.987.843 vs 12.470.518.709; laba bersih 602.331.517 vs 602.333.817; laba rugi legacy 602.331.517 vs laporan periode 2000-2099 602.332.717 — **tiga angka laba berbeda** karena jurnal bertanggal sampah (hanya legacy memuat) dan bertanggal 2030 (legacy & periode 2000-2099 memuat; as-of hari ini tidak). Dua "stack" laporan (`gl_engine.balance_sheet/income_statement` dan `gl_reports.*`) berjalan paralel dan di-expose keduanya.
* Neraca selalu `balanced=true` (ekuitas+laba berjalan dihitung sebagai plug laba bersih) — tidak membuktikan apa-apa tentang kebenaran klasifikasi; TB selalu seimbang karena `post_journal` memaksa.
* Arus kas: `reconciled=true` selalu (dihitung sebagai Σ per-lawan-akun = Δ kas). Klasifikasi: GL-14.
* Layar vs API (Playwright): Laba Rugi "Tahun berjalan" Pendapatan Rp 2.898.442.000 = `Σ 4-xxxx` API (cocok); Neraca Lajur "Laba periode Rp 602.333.817" = API (cocok); Bagan Akun "Kas Kecil Site −Rp 37.000.000" = API; Kas&Bank "Total Kas & Bank Rp 15.761.930.872" ≠ kas di neraca/arus-kas-proyek Rp 8.006.942.936 (duplikasi akun GL lewat dialog Rekonsiliasi Bank, GL-08). Tab "Penutupan Buku", "Paket Laporan Owner", "Tutup Periode" → "Gagal memuat…" (HTTP 500 dari `/gl/periods`, `/gl/year`, `/gl/reports/closing-history`) akibat satu jurnal bertanggal sampah (GL-06) — screenshot: `img/gl/acc_Penutupan_Buku.png`, `rep_Tutup_Periode.png`, `rep_Paket_Laporan_Owner.png`.
* P&L per proyek (`/gl/reports/projects`) memakai peta sumber lama yang mengabaikan `source_deal_id`: Pendapatan "Tidak teralokasi ke proyek" Rp 302.542.000 (potongan pembatalan Rp 297,5 jt `4-1200` + jasa giro + laba aset) padahal potongan itu punya `source_deal_id` ke deal berproyek. Arus kas per proyek (peta yang lebih luas) mengalokasikan 1 proyek vs 86% "tidak teralokasi" (Rp 6,88 M dari 8,01 M) — jurnal tidak menyimpan proyek, hanya diduga dari dokumen sumber.

## 5. Terverifikasi OK
* `post_journal` selalu menjaga Σ Dr = Σ Cr (TB seimbang pada seluruh uji (>120 jurnal)); menolak negatif, tak seimbang, akun tak ada.
* Idempoten: BAST ulang, bayar/setuju komisi ulang, setor pajak ulang, penyusutan ulang, apply denda ulang, replay refund (`client_ref`), setuju AP ulang, lepas aset ulang.
* RBAC jurnal manual: hanya finance/owner/superadmin (manager/sales/site/pm/marketing → 403). Buka periode: butuh `gl:approve`. Transfer: pembuat tak bisa menyetujui sendiri; approve hanya `bank:approve`.
* Posting otomatis ke periode tutup digeser + memo; manual ditolak; kas terkunci memakai pola serupa (kode).
* Alur giro memorandum berpasangan konsisten; kliring ke rekening kas ditolak.
* Rekonsiliasi bank: selisih "tak terjelaskan" dihitung jujur (0).
