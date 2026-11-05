# Audit Pembayaran MASUK — SIPRO/Estora (instance #2: UI :3002, API :8002, DB `sipro_in`)

Auditor: stream "pembayaran-masuk". Semua angka dalam Rupiah. Skrip uji & data kerja: (skrip uji tidak disertakan di repo) (lib.py, ui*.js, notes.md). Screenshot: `img/masuk/`.
Data uji (awalan AUDIT-): lead AUDIT-Pembeli 1..13; deal A-03 (BF ganda), A-04/D2 (paralel+titipan), A-05/D3 (overpay), B-02/D4 (hapus kuitansi, bank match), B-03/D5 (BF+BAST), B-04/D6 (KPR), B-05/D7 (all-in), B-06/D8 (refund BF), C-01/D9 (ganti skema), C-02/D10 (KPR UI sales), C-03/D11 (deal batal), C-04/D12 (BF proof).

## Ringkasan eksekutif
1. Seluruh jalur uang masuk (kuitansi manual, verifikasi bukti portal, booking fee, pencairan KPR, kliring giro, pencocokan mutasi bank, invoice biaya all-in) TIDAK punya kunci idempotensi maupun penguncian atomik. Dua permintaan bersamaan (dua tab/dua staf/retry) melahirkan DUA penerimaan, sedangkan tagihan (AR) hanya naik sekali: kas GL & kewajiban kontrak menggelembung, AR tidak (IN-01). Terbukti lewat API dan lewat dua tab UI.
2. Titipan bisa menjadi NEGATIF (-Rp 65 jt tampil di layar Titipan) dan penyaluran titipan biaya bisa melebihi saldo (IN-02); jurnal GL bisa terposting dua kali karena `source_event` tidak unik dan dispatcher event tidak aman paralel (IN-03); refund/kas keluar bisa dobel (IN-04).
3. "Hapus kuitansi" (satu-satunya pembalikan penerimaan manual) adalah penghapusan fisik: kewajiban kontrak tidak turun, jurnal titipan/booking fee tidak ikut terhapus, bukti pelanggan ikut hilang, nomor kuitansi bolong (IN-05). Tidak ada jalur void resmi kecuali lewat batal-cocok bank / batal pencairan KPR.
4. Salah akun GL pada dua keadaan nyata: denda yang dibayar & pembayaran setelah BAST dikreditkan ke 2-1400 (bukan mengurangi Piutang 1-1300); pendapatan BAST memuat denda sehingga denda terhitung dua kali di 4-1100 dan 4-1400 (IN-06, IN-07).
5. Rekonsiliasi bank: mutasi bisa dicocokkan ke dokumen bernominal beda (9 jt ke bukti 1 jt) dan uang yang sama bisa tercatat dua kali (kuitansi manual + cocok bank) (IN-08). Portal pembeli punya OTP master statis yang selalu diterima di semua lingkungan (IN-10; tingkat bergantung konfigurasi produksi, lihat koreksi di temuannya).
6. RBAC/SoD: peran `sales` bisa mencatat pencairan KPR lewat API; sales_manager bisa mengeksekusi refund booking fee; pemicu denda bisa meringankan dendanya sendiri (IN-11, IN-12).
7. Kontrol bawaan `/finance/reconcile` (2-1400 & 2-1450) MENDETEKSI selisih akibat temuan di atas (selisih -Rp 1,16 M di 2-1400), tetapi tidak ada kontrol AR.paid = Σ kuitansi sehingga 6 dari 14 deal sudah tidak sinkron (IN-01).
8. Yang benar: guard klik-ganda satu tab di UI, validasi nominal (0/negatif/desimal), pencegahan kelebihan bayar tanpa persetujuan, nomor kuitansi unik di bawah beban paralel, pilihan rekening kas/bank pada kuitansi AR, void pencairan KPR simetris, RBAC dasar 403 konsisten, IDOR portal tertutup.

Jumlah temuan: Kritis 5 (IN-01..05) · Tinggi 8 (IN-06,07,08,11..15) · Sedang 9 (IN-09, IN-10, IN-16..22) · Rendah 1 butir gabungan berisi 7 catatan kecil (IN-23).

## Cakupan (apa yang diuji)
Inventarisasi jalur uang masuk dari kode (finance_engine.apply_receipt/receive_deposit/apply_deposit/refund_deposit, booking_fee.pay/verify_proof/refund, payment_intake.verify (portal), kpr_disburse.disburse (3 pintu: /financing/{id}/disburse, /contracts/{id}/kpr/disbursements, /contracts/{id}/kpr/stage/pencairan), allin_engine.pay_cost_invoice/apply_booking_deposit/disburse_titipan, pdc_engine.clear, bank_match.match/_apply, late_fee_engine.apply/waive, cancellation_engine.decide/pay_refund, deal_cancel.cancel, force_delete.delete_receipt, bank_match.void_receipt, recognize_revenue/BAST).
| Jenis pembayaran | Diuji (API/UI) | Akun GL yang kena (diukur) |
|---|---|---|
| Booking fee / tanda jadi | bayar, paralel, portal proof, verify, refund, cancel, hapus | Dr bank DEFAULT 1-1201 / Cr 2-1450 (rekening & metode diabaikan) |
| DP & termin (kuitansi manual) | pas/kurang/lebih, alokasi, paralel, hapus, ganti skema, deal batal, pasca-BAST | Dr kas/bank pilihan / Cr 2-1400 (SEMUA jenis ke akun yang sama) |
| Kelebihan bayar / titipan | allow_overpay, terima titipan, pakai, refund, paralel | Cr 2-1450; dipakai: Dr 2-1450 Cr 2-1400 |
| KPR / SP3K / pencairan | tahap SP3K→akad→cair, paralel, RBAC sales, batal | Dr bank / Cr 2-1400 (sama dgn setoran pembeli) |
| Biaya all-in (BPHTB/notaris) | terbit invoice, bayar, paralel, salurkan titipan | Dr bank DEFAULT / Cr 2-1470 |
| Denda & keringanan | auto-run, bayar denda, waive, paralel, efek ke BAST | Dr 1-1300 / Cr 4-1400; dibayar: Cr 2-1400 (salah) |
| Pembatalan & refund | cancel deal (BF), keputusan pembatalan, refund bertahap | Dr 2-1400 / Cr 4-1200 & 2-1460; refund Dr 2-1460 Cr bank |
| Portal pembeli | login OTP, unggah bukti, kirim bukti, tampilan pembayaran/kuitansi | — |
| Impor & cocok mutasi bank | impor ganda, baris kembar, match paralel, manual+match, intake salah nominal | memakai jalur resmi kuitansi |
| Giro/cek mundur (PDC) | terima, duplikat nomor, kliring paralel | memorandum 1-1350/2-1480, kliring → 2-1400 |
| Kuitansi | penomoran, PDF, void, hapus, cetak ulang | — |
UI diuji dengan Playwright sebagai finance (AR, dialog Terima Bayar, Titipan, Detail AR, Rekonsiliasi Bank), sales (tab KPR pembeli, aksi ditolak) dan pembeli (portal). RBAC diuji pada 16 endpoint × 6 peran.

---

## Temuan (urut severity)

### [IN-01] [Severity: Kritis] Penerimaan ganda pada semua jalur uang masuk bila dua permintaan bersamaan (tanpa idempotensi/penguncian)
- Label bukti: [TERBUKTI-API] (8 jalur) dan [TERBUKTI-UI] (kuitansi manual, dua tab).
- Lokasi: finance_engine.py:513-598 (`apply_receipt`: baca AR :527, alokasi, tulis :557/:573; `_recalc_invoice` :489-500 menimpa seluruh `items`), payment_intake.py:124-150 (`verify`: cek `state` :128 lalu `apply_receipt`), booking_fee.py:102-165 (`pay`: baca invoice, tulis `paid = inv.paid + amount` dari nilai basi), kpr_disburse.py:176-262, pdc_engine.py:95-135, bank_match.py:243-270 (`match`: cek `match_state` lalu `_apply`), allin_engine.py:386-418; routers/ar_router.py:184-199 (ReceiptCreate tanpa idempotency key). UI: Keuangan > Piutang > Daftar Piutang > [Terima Bayar] > Simpan Pembayaran.
- Langkah & hasil (angka selisih):
  1. Kuitansi manual: 2 POST `/finance/ar/receipts` paralel @100.000.000 ke A-04. Hasil: dua kuitansi (KWT/2026/0007, 0008); AR terbayar +100 jt saja; kewajiban kontrak (CL) +200 jt; GL 2-1400 & bank +200 jt. Seharusnya satu kuitansi atau satu ditolak.
  2. UI: dua sesi finance membuka dialog "Terima Pembayaran" B-03 lalu klik Simpan bersamaan (`in/ui3.js`): dua kuitansi KWT/2026/0031 & 0032 (@2 jt), AR terbayar 13→15 jt (+2), CL +4 jt; kedua tab menampilkan sukses. Screenshot `f3-tabA-after.png`, `f3-tabB-after.png`.
  3. Verifikasi bukti pelanggan (intake d3ceafe1, 212.500.000) dua kali paralel: dua kuitansi (KWT0016/0017); AR hanya +212,5 jt; CL & GL +425 jt.
  4. Booking fee 5 jt dibayar paralel x2 (A-03): faktur lunas 5 jt tetapi dua kuitansi (KWT0004/0005), titipan 10 jt, GL 2-1450 10 jt.
  5. Pencairan KPR tahap T1 (plafon 300 jt, satu tahap) paralel x2 (B-04): dua kuitansi 300 jt (KWT0028/0029), CL 600 jt; `financing_apps.disbursed_total` hanya 300 jt.
  6. Kliring giro 7 jt paralel x2: dua kuitansi (KWT0036/0037), dua jurnal pembalik memorandum, AR +7 jt vs CL +14 jt.
  7. Satu mutasi bank 50 jt dicocokkan paralel x2: dua kuitansi 50 jt (KWT0021/0022), satu mutasi.
  8. Bayar invoice biaya all-in paralel x2 @30 jt (invoice 47,6 jt): kuitansi biaya 70 jt (> invoice), invoice mencatat paid 40 jt.
  9. Akibat bersih: dari 14 deal ber-AR, 6 tidak cocok antara AR.paid, Σ kuitansi (non-void) dan CL (A-06 juga berbeda tetapi wajar: CL dinolkan oleh pembatalan) (mis. A-04 AR 147 jt vs kuitansi 374 jt vs CL 374 jt; A-01 AR 174,5 jt vs 387 jt vs CL 599,5 jt). Layar Detail AR menampilkan "Terbayar Rp 140.000.000" bersebelahan dengan "Kewajiban kontrak: Rp 360.000.000" (`f4-detail-A04.png`); portal pembeli menampilkan "Sudah Dibayar 173,5 jt" dengan riwayat 386 jt (`p4-portal-pembayaran.png`).
- Dampak bisnis: kas/uang muka di GL lebih besar daripada piutang yang dilunasi; pembeli bisa tampak belum membayar padahal sudah (atau dua kali bayar); komisi, BAST, perhitungan refund pembatalan (memakai CL) ikut salah. Kontrol `/finance/reconcile` hanya menangkap 2-1400/2-1450, tidak AR.
- Akar masalah & arah: read-modify-write tanpa transaksi/atomik pada `ar_invoices.items`; pengecekan status dilakukan sebelum `await` panjang. Arah: klaim atomik (`find_one_and_update` status pending→processing), versi optimistik pada `ar_invoices`, header/field `client_ref`/idempotency-key wajib di ReceiptCreate/BF/titipan/pencairan (saat ini hanya refund & denda memilikinya), indeks unik (org, sumber, sumber_id), dan kontrol rekonsiliasi AR.paid = Σ kuitansi aktif.
- Catatan: klik-ganda DALAM satu tab dijaga UI (lihat Terverifikasi OK); celahnya ada pada dua tab/dua staf/retry jaringan/skrip.

### [IN-02] [Severity: Kritis] Titipan pelanggan bisa negatif; penyaluran titipan biaya melebihi saldo
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (layar Titipan).
- Lokasi: finance_engine.py:663-711 (`apply_deposit`: saldo dibaca lalu `$inc` negatif tanpa syarat), :714-732 (`refund_deposit`), :602-630 (`_deposit_move` tanpa pengaman saldo ≥ 0), booking_fee.py:268-340 (`refund` memakai `_deposit_move` tanpa cek saldo), allin_engine.py:421-443 (`disburse_titipan`).
- Langkah: (a) A-04: terima titipan 100 jt lalu `POST /finance/ar/{deal}/deposit/apply` 40 jt paralel x4 → empat kuitansi, saldo titipan **-60 jt**, CL +160 jt, AR +40 jt saja. (b) D7: penyaluran titipan BPHTB paralel x2 senilai seluruh saldo 70 jt → `paid_out` 140 jt, saldo titipan **-70 jt**, GL 2-1470 bersaldo debit 70 jt, bank dikredit 140 jt. (c) Hapus kuitansi booking fee yang titipannya sudah dipakai ke termin → saldo -5 jt (IN-05).
- UI: Keuangan > Piutang > Titipan menampilkan KPI "Saldo Titipan Pelanggan -Rp 65.000.000" dan baris A-04 "-Rp 60.000.000" tanpa peringatan (`f4-titipan.png`).
- Dampak: kewajiban bernilai negatif; uang keluar melebihi uang masuk; saldo titipan tidak lagi bisa dipercaya untuk refund/pembatalan.
- Saran: batasi saldo ≥ 0 secara atomik (`update_one` dengan filter `balance >= amount`), tolak refund BF bila titipan sudah dialihkan.

### [IN-03] [Severity: Kritis] Jurnal GL ganda: `source_event` tidak unik + dispatcher event tidak aman paralel
- Label bukti: [TERBUKTI-API].
- Lokasi: gl_engine.py:127-131 (`post_journal`: `find_one` lalu `insert_one`), seed_indexes.py:128 (indeks `source_event` NON-unik; hanya `entry_no` unik di indexes.py:35), engine.py:637-654 (`dispatch_pending` mengambil event `pending` tanpa mengklaimnya; dipanggil inline oleh book_deal/deal_cancel dan oleh scheduler tiap 8 dtk).
- Langkah & hasil: (a) Keputusan pembatalan A-06 (850 jt) dijalankan paralel x2 oleh owner: dua jurnal dengan `source_event` sama (JV/2026/00075 & 00076): Dr 2-1400 1,7 M (seharusnya 850 jt), Cr 2-1460 1,105 M (utang refund versi GL, padahal settlement 552,5 jt), Cr 4-1200 595 jt (potongan 297,5 jt). (b) Pembatalan reservasi B-06 paralel x2: 2 refund tercatat tetapi 4 jurnal "Titipan dikembalikan" (JV106-109): setiap event diproses dua kali oleh dua dispatcher bersamaan. (c) Keringanan denda paralel x2: dua jurnal JV112/113 (@2,38 jt). (d) Kliring giro paralel: dua jurnal pembalik memorandum.
- Dampak: GL tidak lagi sama dengan subledger (tie-out 2-1400 selisih -Rp 1,16 M saat uji; 2-1450 selisih Rp 5 jt); pendapatan "potongan pembatalan" bisa dobel.
- Saran: indeks unik parsial (org_id, source_event); klaim event atomik sebelum handler; handler yang gagal 3x kini menjadi `failed` permanen tanpa jurnal (engine.py:644-650) — butuh alarm (lihat Tidak bisa diverifikasi).

### [IN-04] [Severity: Kritis] Refund / kas keluar ganda
- Label bukti: [TERBUKTI-API].
- Lokasi: cancellation_engine.py:532-610 (`pay_refund`: `refund_paid_total` ditulis dari nilai basi `paid + amount`; `client_ref` opsional), booking_fee.py:268-340, deal_cancel.py:96-150.
- Langkah & hasil: (a) Refund pembatalan A-06 (utang refund 552,5 jt) dibayar paralel x2 @300 jt tanpa `client_ref` → dua jurnal kas keluar 300 jt (JV77/78) = 600 jt, `refund_paid_total` hanya 300 jt sehingga sistem masih mengizinkan 252,5 jt lagi (total potensi 852,5 jt vs kewajiban 552,5 jt). (b) Pembatalan reservasi B-06 (BF 5 jt) paralel x2 oleh sales_manager: dua bukti refund RF-BF/2026/0001 & 0002 (@5 jt), titipan -5 jt.
- Dampak: uang perusahaan keluar melebihi kewajiban; sulit ditarik kembali.
- Saran: sama seperti IN-01; `client_ref` WAJIB untuk setiap pembayaran keluar; update bersyarat `refund_paid_total` dengan `$inc` dan cek sisa dalam filter.

### [IN-05] [Severity: Kritis] "Hapus kuitansi" = penghapusan fisik yang tidak simetris; tidak ada void resmi untuk penerimaan manual
- Label bukti: [TERBUKTI-API] (superadmin) + [DARI-KODE] untuk konsekuensi lanjut.
- Lokasi: routers/ar_router.py:246-263, force_delete.py:133-181 (`delete_receipt`); void hanya ada di bank_match.py:275-312 (`void_receipt`, dipanggil dari batal-cocok bank & batal pencairan KPR).
- Langkah & hasil:
  1. Deal B-02: bayar 50 jt lalu superadmin DELETE → GL 2-1400 turun 50 jt tetapi `contract_liabilities.balance` TETAP (55 jt vs seharusnya 5 jt); force_delete tidak menyentuh CL pada cabang AR (force_delete.py:153-176).
  2. Hapus kuitansi booking fee (titipan sudah dipindah ke termin): saldo titipan -5 jt, faktur BF kembali "unpaid" padahal AR masih menghitung 5 jt, dan jurnal Dr bank/Cr 2-1450 TIDAK terhapus (jurnal titipan bersumber `deposit.id`, bukan `receipt.id` — pencarian jurnal di force_delete.py:177 memakai `source_id=rid`); selisih GL vs Σ titipan.
  3. Bukti transfer pelanggan (`payment_intakes`) ikut DIHAPUS (force_delete.py:178) sehingga klaim pelanggan hilang dari portal dan bisa dikirim ulang.
  4. Nomor kuitansi bolong: KWT/2026/0017 dan 0018 tidak ada lagi (tidak ada tanda "batal" berurutan).
  5. Akibat ganti skema (IN-14): alokasi kuitansi menunjuk id termin lama; setelah hapus, AR tetap menampilkan paid 50 jt tanpa kuitansi sama sekali.
  6. Efek samping `paid_off` (komisi, notifikasi) dan BAST tidak dibalik.
- Dampak: audit trail penerimaan hilang; subledger dan GL berselisih; kuitansi yang sudah diserahkan ke pembeli tidak lagi ada di sistem.
- Saran: pembalikan sebagai void bernomor (status void + jurnal pembalik + CL/titipan/AR simetris) untuk semua jenis kuitansi; hapus fisik hanya untuk data uji.

### [IN-06] [Severity: Tinggi] Denda: pembayaran denda masuk 2-1400; pendapatan BAST memuat denda (dobel di 4-1100 & 4-1400, dobel Piutang)
- Label bukti: [TERBUKTI-API].
- Lokasi: late_fee_engine.py:269-330 & :373-383 (`apply` menambah item denda ke `ar_invoices.items` dan menaikkan `total`), gl_engine.py:263-284 (`_gl_payment_received` selalu Cr 2-1400), finance_engine.py:837-884 (`recognize_revenue`: `price = inv.total`).
- Langkah & hasil: auto-run denda (A-01: 3.541.667 JV85; A-02: 2.380.000 JV86; jurnal Dr 1-1300/Cr 4-1400). (a) Bayar denda A-01 dengan alokasi ke item denda: GL Dr bank/Cr **2-1400** +3.541.667; 1-1300 TIDAK berkurang (968.919.667 tetap); 4-1400 tetap. (b) BAST A-02 (harga unit 850.000.000): `revenue` 852.380.000; 4-1100 +852.380.000 (harusnya 850 jt), 1-1300 didebit 852,38 jt padahal denda 2,38 jt sudah didebit saat penagihan; denda juga tetap di 4-1400. Pembayaran denda yang masuk CL ikut "dibebaskan" sebagai pendapatan penjualan saat BAST.
- Dampak: Piutang Usaha & Uang Muka menggelembung permanen; pendapatan penjualan dan pendapatan denda saling tumpang; refund pembatalan menghitung denda sebagai uang muka.
- Saran: denda diperlakukan sebagai tagihan tersendiri (bukan item termin unit): pelunasan denda → Cr 1-1300; `recognize_revenue` memakai `unit_total` (+ add-on), bukan `total`.

### [IN-07] [Severity: Tinggi] Pembayaran setelah BAST dikreditkan ke 2-1400; BAST tidak mensyaratkan pelunasan dan menandai unit "paid_off"
- Label bukti: [TERBUKTI-API].
- Lokasi: finance_engine.py:574-582 (selalu `contract_liabilities +applied` & event `payment.received`), gl_engine.py:263-284, finance_engine.py:837-884; routers/ar_router.py:224-231 (BAST: `finance:update`).
- Langkah & hasil: deal B-03 (terbayar 1,5% dari 980 jt): owner/finance `POST /finance/ar/{deal}/bast` → 200; deal `completed`, unit `sold`, `payment_status=paid_off`, pendapatan 980 jt diakui, HPP 686 jt (`cogs_source=estimate_70pct`, padahal `rab_hpp` 29,6 jt). Kuitansi 1.234.567 sesudah BAST: GL Cr 2-1400 +1.234.567, 1-1300 tidak berubah (968.919.667), CL kembali positif. `units.payment_status` dari paid_off kembali "partial".
- Dampak: skema in-house (cicilan setelah serah terima) membuat Piutang Usaha tidak pernah turun dan Uang Muka naik lagi; status unit "lunas" salah pada deal yang belum lunas; HPP/margin estimasi 70%.
- Saran: setelah `recognized`, penerimaan harus Dr kas/Cr 1-1300; BAST (atau status paid_off) harus melihat pelunasan/aturan khusus; tandai estimasi HPP sebagai peringatan.

### [IN-08] [Severity: Tinggi] Rekonsiliasi bank: pencocokan tidak memeriksa nominal, dan uang yang sama bisa tercatat dua kali
- Label bukti: [TERBUKTI-API].
- Lokasi: bank_match.py:243-270 (`match`) & :200-240 (`_apply`: kind `payment_intake` memakai nominal bukti, bukan nominal mutasi; kind `ar_deal` tidak mengecek kuitansi yang sudah ada), bank_match.py:149-197 (`_ar_candidates` tidak mengecualikan uang yang sudah dikuitansi manual).
- Langkah & hasil: (a) Mutasi 9.000.000 (5c4df684) dicocokkan ke bukti portal 1.000.000 → 200; kuitansi 1 jt (KWT0041), mutasi berstatus "matched", 8 jt tidak tercatat dan lenyap dari daftar "belum cocok". (b) Kuitansi manual 30 jt untuk deal B-02, lalu mutasi 30 jt yang sama dicocokkan ke deal itu → dua kuitansi (KWT0023/0024); saran kandidat tidak memperingatkan. (c) Bukti pelanggan yang diverifikasi manual (KWT0016) tetap menyisakan mutasi 212,5 jt "belum cocok" (a2aec75b) yang bila dicocokkan ke AR menjadi penerimaan ketiga.
- Dampak: kas GL ≠ mutasi rekening; rekonsiliasi tampak bersih padahal uang belum/dobel tercatat.
- Saran: wajibkan nominal sama (atau selisih eksplisit sebagai biaya bank/titipan), tautkan kuitansi manual ke mutasi (`bank_txn_id`) dan tolak pencocokan bila deal sudah menerima nominal/tanggal yang sama; peringatan "sudah ada kuitansi manual serupa".

### [IN-09] [Severity: Sedang] Impor mutasi menelan transaksi kembar yang sah
- Label bukti: [TERBUKTI-API].
- Lokasi: bank_import.py:123-130 (`fingerprint`: rekening+tanggal+arah+nominal+ref atau keterangan) & :205-212.
- Langkah: CSV dengan dua baris identik tanpa kolom referensi (tgl 2026-11-04, "TRANSFER MASUK AUDIT-GANDA", 7.000.000) → "4 mutasi baru, 1 sudah ada": baris kedua dianggap duplikat. Dua pembeli berbeda yang menyetor nominal sama dengan berita sama pada hari yang sama kehilangan satu mutasi.
- Dampak: saldo rekening versi sistem kurang dari mutasi asli; uang masuk tak terlihat. Saran: tambahkan nomor urut baris/kolom saldo ke kunci bila `ref` kosong dan tampilkan peringatan.

### [IN-10] [Severity: Sedang — dikoreksi koordinator dari "Tinggi"] Master OTP statis selalu diterima oleh login portal pembeli
- Label bukti: [TERBUKTI-API] dan [TERBUKTI-UI] pada lingkungan uji, **dengan catatan penting di bawah**; sifat "selalu aktif" adalah [DARI-KODE].
- Lokasi: `backend/routers/portal_router.py:137-150` — `master = os.environ.get("PORTAL_MASTER_OTP", "000000")`; kode yang sama dengan master selalu lolos tanpa memeriksa OTP asli pembeli.
- **Koreksi atas laporan auditor:** bukti reproduksi memakai `PORTAL_MASTER_OTP=000000` di `backend/.env` yang diisi oleh lingkungan uji ini sendiri (sama seperti catatan pemulihan di repo). Itu bukan konfigurasi produksi. Skrip deploy `deploy/add_instance.sh:49` membuat nilai acak 6 digit, dan `docker-compose.yml:31` meneruskan `${PORTAL_MASTER_OTP}`. Jadi pada instance yang di-deploy dengan skrip repo, kode `000000` **tidak** berlaku.
- Yang tetap benar: (1) master OTP ada di semua lingkungan, bukan hanya non-produksi, dan satu nilai statis membuka portal **setiap** pembeli bila nomor HP/emailnya diketahui; (2) jika env tidak diisi sama sekali, bawaan kode adalah `000000`; (3) jika env terisi string kosong (mis. `${PORTAL_MASTER_OTP}` di compose tanpa nilai), master menjadi `""`. Dari kode: `PortalOtpVerify.code` adalah `str` tanpa batas panjang (`models.py:531-533`) dan `verify_otp` membandingkan `code != master` (`portal_router.py:143-144`), sehingga kode kosong akan **lolos** dan token terbit untuk siapa pun yang nomor HP-nya terdaftar. Ini [DARI-KODE], belum dijalankan di server nyata.
- Dampak: akses ke tagihan, kuitansi, dan unggah bukti transfer pembeli bagi siapa pun yang tahu rahasia master. Tingkat riil bergantung pada nilai yang dipakai di server produksi.
- Saran: hapus nilai bawaan `"000000"` dari kode (gagal-tutup bila env kosong), nonaktifkan master OTP di produksi, dan pastikan nilai di server produksi bukan `000000`.

### [IN-11] [Severity: Tinggi] RBAC pencairan KPR tidak konsisten: peran sales dapat mencatat pencairan (uang masuk) lewat API
- Label bukti: [TERBUKTI-API] (bypass) + [TERBUKTI-UI] (aksi ditolak di jalur UI).
- Lokasi: routers/allin_router.py:348 (`/contracts/{cid}/kpr/disbursements` memakai `financing:update`; sales memiliki update pada financing di rbac_matrix.py:79-84), routers/financing_router.py:141-143 (`/financing/{fid}/disburse` memakai `financing:approve`), kpr_engine.py:120-123 (`stage/pencairan` pintu ketiga).
- Langkah: login sales@, `POST /contracts/{C6}/kpr/disbursements {"tranche_code":"T1","file_id":...}` → 200 (dua kali paralel = dua kuitansi 300 jt); pm@ → 403. Di UI (Customer & Kontrak > AUDIT-Pembeli 10 > tab KPR) sales melihat tombol "Cairkan", mengisi form, lalu toast "Akses ditolak: tidak memiliki izin 'approve' pada 'financing'" dan konsol 403 (GET /finance/ar, GET /cash-bank/accounts) sehingga dropdown berisi "Belum ada rekening aktif" (`s3`, `s4`, `s5` di folder screenshot).
- Dampak: pemisahan tugas rusak — pencairan bank (kas masuk + kuitansi + jurnal) bisa dicatat sales yang berkepentingan pada komisi; tombol UI menyesatkan untuk peran yang tidak berhak.
- Saran: satu izin (`approve`) untuk semua pintu pencairan; sembunyikan tombol bila `can("financing","approve")` salah.

### [IN-12] [Severity: Tinggi] Pemisahan tugas (SoD) tidak ditegakkan pada keringanan denda, refund BF, dan amandemen
- Label bukti: [TERBUKTI-API] (denda, refund BF) + [DARI-KODE] (amandemen).
- Lokasi: late_fee_engine.py:332-370 (tidak ada cek `actor != created_by`, padahal docstring modul menjanjikannya), deal_cancel.py:23-24 & :96-150 (ADMIN_ROLES termasuk sales_manager memutuskan sekaligus mengeksekusi refund kas), booking_fee_router.py:56-95 (verifikasi bukti & refund BF hanya `finance:create`, sementara verifikasi bukti termin `finance:approve` di intake_router.py:51), allin_amend.py:80-90 (super_admin boleh menyetujui amandemennya sendiri).
- Langkah: owner@ memicu auto-run denda (A-02, 2,38 jt) lalu `POST /finance/late-fees/{deal}/waive/{id}` oleh owner sendiri → 200 (jurnal pembalik). Sales_manager (manager@) membatalkan reservasi B-06 dengan refund penuh → kas keluar tanpa persetujuan keuangan (finance sendiri 403 karena tak punya `deals:update`).
- Dampak: tidak ada maker-checker untuk keputusan yang melepaskan uang/pendapatan.
- Saran: tegakkan `actor != created_by` dan persetujuan finance untuk refund; samakan izin verifikasi bukti BF dengan bukti termin.

### [IN-13] [Severity: Tinggi] Pembayaran diterima pada deal yang sudah DIBATALKAN
- Label bukti: [TERBUKTI-API].
- Lokasi: finance_engine.py:513-598 (`apply_receipt` tidak memeriksa status deal/AR), :602-630, :638-660 (`receive_deposit`).
- Langkah: deal C-03 dibatalkan sales (AR status `cancelled`, semua termin `cancelled`, unit `available`). `POST /finance/ar/receipts` 20 jt → 200 (KWT0042): AR berubah `cancelled`→`partial`, unit C-03 (available) bertanda `payment_status=partial`; titipan 1 jt juga diterima.
- Dampak: uang masuk ke kontrak yang sudah tidak ada; unit tersedia tampil "sebagian dibayar"; tidak ada jalur refund otomatis.
- Saran: tolak penerimaan untuk AR/deal berstatus cancelled/expired (arahkan ke titipan/refund bila uang sudah masuk).

### [IN-14] [Severity: Tinggi] Ganti skema pembayaran memutus tautan alokasi kuitansi
- Label bukti: [TERBUKTI-API].
- Lokasi: finance_engine.py:319-420 (`create_ar_for_deal(replace=True)` membangun item baru dan mengalokasikan ulang `carried_paid`), kuitansi lama tetap menyimpan `allocations[].item_id` lama; force_delete.py:154-166 & bank_match.py:296-303 mencari item per id.
- Langkah: deal C-01 bayar 50 jt; ganti skema ke "Cash keras"; id termin berubah (alokasi kuitansi tidak ditemukan di AR); hapus kuitansi → AR tetap paid 50 jt dan CL 50 jt tanpa satu pun kuitansi.
- Dampak: pembalikan/void sesudah ganti skema tidak mengembalikan AR. Saran: petakan ulang `allocations` saat skema diganti atau simpan alokasi pada level deal, bukan id termin.

### [IN-15] [Severity: Tinggi] `method="kpr"` pada kuitansi manual menembus seluruh gerbang KPR
- Label bukti: [TERBUKTI-API].
- Lokasi: finance_engine.py:532-540 (`is_kpr = method == "kpr"` → alokasi mendahulukan porsi bank), routers/ar_router.py:184-199 (method hanya divalidasi sebagai referensi).
- Langkah: deal B-02 (0 pengajuan KPR) `POST /finance/ar/receipts {"method":"kpr","amount":10000000,"proof_file_ids":["x"]}` → 200; termin "Pelunasan / KPR 30%" terbayar 10 jt tanpa SP3K, akad, tahap, maupun bukti bank.
- Dampak: porsi bank bisa dilunasi "di atas kertas" tanpa dana bank. Saran: method `kpr` hanya dari modul pencairan.

### [IN-16] [Severity: Sedang] Bukti transfer: validasi lemah pada portal & jalur staf; verifikasi BF memotong nominal diam-diam; verifikasi generik menembus jenis bukti
- Label bukti: [TERBUKTI-API].
- Lokasi: models_p47.py:96-103 (`transfer_date` hanya panjang 10 karakter; `amount` tanpa batas), routers/portal_router.py:249-291 (tipe konten percaya header), booking_fee.py:242-265 (`amount = min(row.amount, outstanding)`), routers/intake_router.py:51 & payment_intake.py:124 (tidak memeriksa `kind`), bank_match.py:106-120 (kandidat memuat semua intake pending).
- Hasil: (a) portal menerima tanggal "abcdefghij" dan "2099-12-31" dan nominal 999.999.999.999 (tampil di layar pembeli, `p4`); HTML berkedok PNG diterima. (b) Bukti BF 8 jt untuk tagihan 5 jt diverifikasi: kuitansi 5 jt, bukti tercatat "Terverifikasi 8 jt", 3 jt tidak tercatat di mana pun. (c) Bukti BF pending + BF dibayar langsung + `/payment-intakes/{id}/verify` → 5 jt masuk lagi ke AR termin (BF dihitung dua kali, deal B-03: AR 10 jt vs BF 5 jt).
- Saran: validasi tanggal ≤ hari ini & nominal ≤ tagihan×n; verifikasi BF menolak/menitipkan selisih; tutup bukti pending saat BF dibayar langsung; `verify` generik menolak `kind=booking_fee`.

### [IN-17] [Severity: Sedang] Bukti bayar staf tidak divalidasi dan bisa dipakai berulang
- Label bukti: [TERBUKTI-API].
- Lokasi: models.py:436 (`proof_file_ids` hanya `min_length=1`), finance_engine.py:571 (disimpan apa adanya), booking_fee.py:128, allin_engine.py:407.
- Hasil: `proof_file_ids:["x"]`/`["fake"]` diterima di kuitansi, BF, titipan, invoice biaya. Satu file nyata dipakai sebagai bukti 3 kuitansi pada 3 deal (KWT0047-0049); file sama (sha256) diunggah ulang diterima. Jalur portal menolak sha256 yang sama (payment_intake.py:55-62), jalur staf tidak.
- Dampak: "bukti bayar wajib" tampil di laporan sebagai terpenuhi padahal kosong/ganda. Saran: validasi keberadaan & kepemilikan file, tolak sha256 yang sudah dipakai kuitansi lain.

### [IN-18] [Severity: Sedang] Jenis pembayaran tak terbedakan di GL; rekening/metode diabaikan pada jalur non-AR
- Label bukti: [TERBUKTI-API] (booking fee & invoice biaya, metode "cash") + [DARI-KODE] (GL).
- Lokasi: gl_engine.py:263-284 (DP, termin, KPR, denda, pasca-BAST semuanya Cr 2-1400), booking_fee.py:117-140 & finance_engine.py:602-630 (`_deposit_move` tanpa `cash_account_id`), allin_engine.py:386-418 (`GL_BANK` tetap), finance_engine.py:714 (`refund_deposit` tanpa rekening, `routers/ar_router.py:122-130`).
- Hasil: BF `method=cash` x2 (10 jt) menaikkan bank 1-1201 +10 jt dan tidak menyentuh Kas 1-1101; invoice biaya `method=cash` 10 jt juga masuk bank; refund titipan selalu dari rekening default. Sebaliknya kuitansi AR menghormati `cash_account_id` dan method cash → 1-1101 (lihat OK).
- Dampak: saldo kas/bank per rekening salah; rekonsiliasi bank per rekening tidak pernah cocok untuk BF/biaya tunai. Pembeda jenis (DP vs cicilan vs KPR vs denda) hanya ada pada label alokasi kuitansi, tidak pada akun.
- Saran: terima `cash_account_id` di BF/biaya/titipan; akun uang muka dipisah menurut jenis (atau sub-akun) bila dibutuhkan laporan.

### [IN-19] [Severity: Sedang] Tidak ada tanggal bayar; tanggal jurnal = waktu input/dispatch (UTC); tanggal layar ≠ PDF
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI].
- Lokasi: models.py:427-436 & booking_fee.py (tak ada field tanggal bayar), gl_engine.py:113-173 (`date or ts`), bank_match.py:200-240 (kuitansi tidak membawa tanggal mutasi), payment_intake.py:124-150 (transfer_date tidak dipakai), routers/ar_router.py:266-300 (PDF memakai `str(created_at)[:10]`).
- Hasil: bukti pelanggan ber-`transfer_date` 2026-11-04 diverifikasi → kuitansi bertanggal waktu verifikasi; mutasi bank 2026-11-04 yang dicocokkan 2026-11-05 → jurnal JV/2026/00071 bertanggal 2026-11-05T19:20 UTC. PDF kuitansi mencetak "Tanggal 2026-11-05" (format ISO, UTC) sementara layar WIB menampilkan "6 Nov 2026" untuk kuitansi yang sama (dibuat 19:31 UTC = 02:31 WIB).
- Dampak: kas tidak bisa dibukukan pada tanggal terjadinya (pergantian bulan/tahun, cut-off), rekonsiliasi per tanggal menampilkan selisih waktu; kuitansi bertanggal berbeda dengan layar. Periode tertutup menggeser jurnal otomatis ke periode terbuka (gl_periods.py:36-57) — tidak diuji agar instance tetap bersih.
- Saran: field `paid_date` (tanggal terjadi) terpisah dari `created_at`, validasi terhadap periode terkunci, tanggal kuitansi memakai zona waktu bisnis & format Indonesia.

### [IN-20] [Severity: Sedang] Kuitansi void tetap tampil/terunduh sebagai sah; laporan penerimaan & "Kas masuk" menghitungnya
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI].
- Lokasi: finance_reports.py:299-320 (`receipts_report`), metrics/sales.py:153-170 (SLS-05), routers/portal_router.py:225-231 & :718-724, routers/ar_router.py:140-162 & :266-300, components/finance/ArDetailSheet.js:314-345, components/portal/panels/PaymentsPanel.js (tanpa penanganan `status==="void"`).
- Hasil: KWT/2026/0028 (void, 300 jt): Laporan Penerimaan menjumlahkannya (total 4.348.277.234 vs 4.048.277.234 tanpa void); refund booking fee (RF-BF) ikut dijumlahkan sebagai penerimaan (+5 jt, `kind=booking_fee_refund` positif); AR Detail menampilkan dua baris "Pencairan KPR Rp 300.000.000" identik tanpa tanda batal (`f7-ar-detail-void.png`); pembeli menerima daftar & PDF kuitansi void (200) dengan teks "sah sebagai bukti penerimaan".
- Saran: filter `status!=void` & `kind` di semua agregat; tanda VOID pada PDF/layar; sembunyikan dari portal.

### [IN-21] [Severity: Sedang] Giro: nomor warkat varian (huruf besar/spasi) lolos pemeriksaan duplikat
- Label bukti: [TERBUKTI-API].
- Lokasi: pdc_engine.py:61-66 (perbandingan string persis).
- Hasil: "AUDIT-BG-001"/"AUDIT-BCA" ditolak saat identik, tetapi "audit-bg-001 "/"audit-bca " diterima sebagai GIRO/2026/0002 (7 jt kedua, bisa dikliring lagi menjadi uang masuk kedua).
- Saran: normalisasi (trim, uppercase) sebelum membandingkan.

### [IN-22] [Severity: Sedang] Kuitansi dari pemakaian titipan & penomoran
- Label bukti: [TERBUKTI-API].
- Lokasi: finance_engine.py:687-697 (receipt `amount: 0`, `method: deposit`, memakai seri KWT), routers/ar_router.py:266-300.
- Hasil: KWT/2026/0006 (pengalihan BF ke termin) bernominal "Rp 0" dengan alokasi "DP 20%: Rp 10.000.000" dan cara bayar "deposit"; seri KWT terpakai untuk dokumen non-kas sehingga daftar penerimaan berisi baris Rp 0. Tidak ada tanda "salinan/cetak ulang" pada PDF (selalu tampak asli).
- Saran: seri/jenis dokumen terpisah ("Memo pemindahan titipan"), cantumkan "SALINAN" pada cetak ulang.

### [IN-23] [Severity: Rendah] Temuan kecil
- Format Rupiah tidak seragam: pesan error `apply_receipt` "Rp 900,000,000" (finance_engine.py:545) vs titik di tempat lain [TERBUKTI-API].
- BAST paralel x3: satu sukses, dua "500 Internal Server Error" (indeks unik menyelamatkan dobel pendapatan, tetapi tanpa pesan ramah) [TERBUKTI-API].
- Setiap kuitansi tambahan pada AR yang sudah lunas memicu ulang `payment.paid_off` & notifikasi "AR lunas" (notifikasi 4→12 setelah 2 kuitansi) [TERBUKTI-API]; komisi tetap satu.
- Portal "Total Harga Rp 853.541.667" memasukkan denda 3,54 jt padahal harga 850 jt [TERBUKTI-UI].
- Dashboard "AR belum tertagih Rp 11,43 M" (seluruh sisa termin, termasuk yang belum jatuh tempo) vs GL Piutang Usaha 1-1300 Rp 1,82 M — definisi berbeda tanpa catatan di layar [TERBUKTI-API].
- Pesan error menyesatkan untuk peran tanpa izin: dropdown "Belum ada rekening aktif" (padahal 403) [TERBUKTI-UI].
- Amandemen all-in: super_admin dapat menyetujui amandemennya sendiri (allin_amend.py:88) [DARI-KODE].

---

## Terverifikasi OK
- Klik ganda cepat pada tombol "Simpan Pembayaran" di SATU tab menghasilkan satu kuitansi (KWT0030) [TERBUKTI-UI, `f2-after-dblclick.png`].
- Pengiriman berurutan (bukan paralel): verifikasi bukti BF yang sudah diproses ditolak ("Bukti ini sudah diproses"); keputusan pembatalan kedua kali ditolak ("tidak bisa diputus dua kali"); batal pencairan KPR kedua kali ditolak; refund BF/waive/clear giro berurutan dijaga status (kode) [TERBUKTI-API untuk tiga yang pertama].
- Validasi nominal: 0, negatif, desimal ditolak; kelebihan bayar ditolak tanpa `allow_overpay` dengan pesan jelas; dengan `allow_overpay` kelebihan masuk titipan 2-1450 (kuitansi memisah `applied` dan `deposit_amount`, CL hanya naik sebesar `applied`), refund titipan memposting Dr 2-1450/Cr bank [TERBUKTI-API].
- Alokasi sebagian & FIFO sesuai jatuh tempo; jumlah termin skema standar = harga unit (pembulatan tutup di termin terakhir) [TERBUKTI-API/DARI-KODE finance_engine.py:148-150].
- Kuitansi AR menghormati metode & rekening: method cash → 1-1101; `cash_account_id` Rekening Escrow → 1-1202; id rekening organisasi lain ditolak "tidak ditemukan" [TERBUKTI-API].
- Nomor kuitansi tidak bentrok di bawah beban paralel (0004-0049 unik); AR unik per deal (indeks unik) [TERBUKTI-API].
- Void pencairan KPR (superadmin) simetris: status void, CL -300 jt, jurnal pembalik, item AR turun, pembatalan kedua ditolak; sales 403 [TERBUKTI-API].
- RBAC dasar: sales/marketing/pm/site/manager 403 pada 15 dari 16 endpoint uang masuk; finance tidak bisa hapus kuitansi (403) dan tidak bisa memutuskan pembatalan; pengaju pembatalan (manager) tidak bisa memutuskan (403) [TERBUKTI-API].
- Portal: IDOR tertutup (pembeli lain 404 untuk unggah bukti & PDF kuitansi orang lain); tipe berkas non-gambar/PDF ditolak; nominal ≤0 ditolak; sha256 bukti sama ditolak; satu bukti BF pending per deal; booking wajib BF lunas (konfigurasi aktif) [TERBUKTI-API].
- Kontrol GL `/finance/reconcile` mendeteksi selisih 2-1400 dan 2-1450 akibat temuan di atas (gagal 2 dari 6 cek) [TERBUKTI-API].
- BAST ganda tidak menggandakan pendapatan (indeks unik `revenue_recognitions`), walau gagal dengan 500 [TERBUKTI-API].
- Impor mutasi: berkas yang sama diimpor ulang → 0 baru (idempoten) [TERBUKTI-API].

## Tidak bisa diverifikasi
- Efek periode TERTUTUP pada penerimaan (menutup periode akan menggeser seluruh posting uji ke bulan berikutnya dan merusak instance); hanya dibaca dari gl_periods.py:36-57 — jurnal otomatis digeser, tidak ditolak.
- Event yang gagal 3x menjadi `failed` tanpa jurnal (engine.py:644-650): tidak direproduksi (events_failed = 0).
- Pembatalan kontrak setelah pencairan KPR: `compute()` memakai Σ CL (cancellation_engine.py:103-130) yang mencakup dana bank — apakah refund pembeli ikut memuat uang bank belum diuji end-to-end [DARI-KODE]; juga refund_debt.py (utang refund Fase 59) tidak diuji.
- Amandemen skema all-in end-to-end dan pencairan KPR dengan kelebihan lalu pembatalan (pesan "batalkan dari layar Titipan" merujuk fitur batal-titipan yang tidak ditemukan di kode: bank_match.py:288-291) [DARI-KODE].
- Pengiriman WhatsApp ke pembeli (mode simulasi), serta tampilan mobile/portal pada ukuran layar lain.
- Mode `kind=bank_interest` dan `bank_fee` pada mutasi masuk/keluar (di luar uang masuk pembeli) tidak diuji.

## Pertanyaan terbuka
1. Apakah GL "Piutang Usaha" memang hanya diisi saat BAST (PSAK 72) sehingga Dashboard AR (Rp 11,4 M) bukan piutang akuntansi? Bila ya, label layar perlu menyebut "tagihan belum jatuh tempo".
2. Apakah DP, cicilan in-house, dan pencairan KPR memang sengaja dikreditkan ke satu akun 2-1400 (pembeda hanya label)? Bila perlu laporan per jenis, butuh sub-akun.
3. Apakah perusahaan menghendaki penerimaan setelah BAST (cicilan in-house) mengurangi 1-1300? Saat ini tidak (IN-07).
4. Kebijakan pasca-hapus kuitansi: haruskah ada void bernomor sebagai satu-satunya jalan, dengan hapus fisik hanya untuk data uji?
5. Peran `finance_manager` dirujuk kode (DECIDER_ROLES, CANCEL_ROLES) tetapi tidak ada akun/peran itu di instance ini; siapa pemegang izin `finance:manage` sebenarnya (selain owner/super_admin)?
