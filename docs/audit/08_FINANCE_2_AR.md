# Audit Ronde 2 — PIUTANG (AR) — SIPRO/Estora

Auditor: stream "finance AR/AP + komponen biaya" (instance #8, UI :3042, API :8042, DB `sipro_fin`). Kode terbaru pasca-perbaikan gelombang 1. Angka dalam Rupiah. Data uji `AUDIT-*`. Skrip: (berkas uji tidak disertakan di repo) · Screenshot: `(tidak disertakan di repo)`.

## Ringkasan eksekutif
1. **Inti AR sehat.** Pada 17 deal (seed + 13 deal uji) tiga arah **AR.paid = Σ item.paid = Σ kuitansi.applied** (0 deal tidak sinkron); `/finance/reconcile` 2-1400 / 2-1450 cocok; penerimaan paralel menghasilkan satu efek (409 + 200); pelunasan denda & penerimaan pasca-BAST kini ke 1-1300 (perbaikan GL-01/02 terbukti); void kuitansi memberi jurnal pembalik.
2. **Yang salah terbesar ada di sekeliling inti:** (a) skema pembayaran lewat jalur lama **tanpa validasi** — skema 70%/80% atau DP 150% & −50% tersimpan dan menagih kurang/lebih dari harga (FN-20, juga lewat layar Finance › Konfigurasi); (b) **aging & dasbor AR menghitung deal batal** (Rp 845 jt piutang hantu, FN-21); (c) **toleransi denda bawaan 7 hari tidak pernah berlaku** — denda dihitung dari hari pertama (FN-22); (d) **BAST tanpa gerbang pelunasan** (pendapatan Rp 850 jt diakui pada deal yang belum bayar sepeser pun, FN-23); (e) **Faktur Pajak bisa terbit atas deal batal**, PPN tidak ada di AR maupun GL (FN-24).
3. Klaim ronde 1 yang **belum tertutup** (diverifikasi ulang): GL-07 (BAST), IN-14 (ganti skema memutus tautan alokasi kuitansi), KT-10/KT-11 (konfigurasi `payment.staged.*` diabaikan; jatuh tempo dari booking), IN-17 (bukti bayar palsu/berulang), IN-19 (tidak ada tanggal bayar).
4. Tidak ada kontrol rekonsiliasi untuk AR (GL 1-1300 baru terisi saat BAST; sebelum itu AR Rp 9–10 M hanya ada di subledger) dan tidak ada tie-out aging ↔ jadwal ↔ GL (FN-28).

## Cakupan
Pembangkitan jadwal (`compute_scheme_items`, `create_ar_for_deal`, `payment_scheme_engine`, legacy `/finance/config/payment-schemes` vs `/payment-schemes`), pembulatan (Σ termin = harga) pada harga 1…10^12 dan 12 cicilan, tanggal jatuh tempo (due_day, bulan Februari), alokasi (FIFO, alokasi terpilih, parsial, lebih → titipan, 0/negatif/desimal/10^15, ditolak tanpa `allow_overpay`), titipan (terima/pakai/refund, melebihi saldo), booking fee → termin / titipan / komponen BOOKING, KPR (skema pencairan 2 tahap, gerbang syarat, toleransi ±1%, SP3K mengubah porsi bank/pembeli, DP pembeli), denda & keringanan (apply, bayar denda, waive SoD, tagih ulang), aging & dasbor AR (API vs DB vs GL), BAST/RevRec (deal lunas & belum bayar), void kuitansi, pembatalan & refund, faktur pajak, laporan penerimaan/pendapatan/arus kas, UI Finance (Dashboard, Piutang, Konfigurasi), RBAC. Verifikasi ulang IN-01..19, GL-01/02/07, KT-05/06/07/10/11.

---
## Temuan (urut severity)

### [FN-20] [Severity: Tinggi] Skema pembayaran lewat jalur lama tanpa validasi: jumlah ≠ 100%, DP 150%, termin negatif
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (`img/finance/s01-skema-70persen.png`, `s02-skema-70persen-hasil.png`)
- Lokasi: layar *Keuangan › Konfigurasi › Skema Pembayaran (AR) › Tambah* (`components/finance/SchemeDialogs.js:48`) → `POST /finance/config/payment-schemes` (`PaymentSchemeCreate`, tanpa pemeriksaan). Jalur baru `POST /payment-schemes` memakai `payment_scheme_engine.blocks()` (wajib 100%) — dua pintu untuk satu koleksi.
- Reproduksi: (1) UI sebagai finlead: nama "AUDIT-UI skema 70 persen", termin "DP 50" 50% + "Pelunasan 20" 20% → "Simpan Skema" → muncul di daftar tanpa peringatan. (2) API: `{"items":[{"basis":"percent","value":50},{"basis":"percent","value":30}]}` → 200. Reservasi unit C-06 (harga Rp 810.000.000) dengan skema itu → book → **AR total Rp 648.000.000** (DP 405 jt + Pelunasan 243 jt): Rp 162 jt (20% harga) tidak pernah tertagih. (3) Skema `value:150` dan `value:-50` → reservasi unit C-03 (Rp 1,55 M) → AR memuat **DP Rp 2.325.000.000 dan termin "X" −Rp 775.000.000**.
- Seharusnya: jalur lama memakai validasi yang sama (persen = 100%, nilai > 0) atau dimatikan.
- Dampak: piutang kurang tertagih; bila skema sampah dipilih sales, AR/SPR/jadwal denda salah. Aging menjumlah hanya baris positif sehingga angka AR menggelembung (lihat FN-21).
- Saran: arahkan semua UI ke `/payment-schemes`; blokir skema yang `Σ ≠ harga` di `create_ar_for_deal`.

### [FN-21] [Severity: Tinggi] Aging, ringkasan, dan dasbor AR menghitung piutang deal yang sudah DIBATALKAN
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (Dashboard "Piutang (AR) Outstanding")
- Lokasi: `finance_engine.ar_aging:1014-1024` (iterasi `items[].amount − paid_amount` untuk semua `ar_invoices`, tanpa menyaring `status != cancelled`), dipakai `/finance/ar/aging`, `/finance/summary`, dasbor, Laporan › Aging Piutang.
- Reproduksi: deal A-03 dibatalkan (AR `status=cancelled, outstanding=0` di kolom, tetapi `items` utuh: DP 680 jt terbayar 5 jt, 6 cicilan). `GET /finance/ar/aging` total **Rp 10.799.200.000** vs Σ `ar_invoices.outstanding` non-batal Rp 9.179.200.000: selisih Rp 1.620.000.000 = **Rp 845.000.000 (A-03 batal)** + Rp 775.000.000 (efek termin negatif FN-20, baris negatif dibuang `bucketize`). `ar_total_value` ikut memuat total deal batal.
- Dampak: dasbor melebih-lebihkan piutang dan "belum tertagih %"; deal batal terus tampak "Lancar"/menua; keputusan penagihan salah.
- Saran: saring `status != cancelled` dan gunakan `ar.outstanding` sebagai sumber tunggal.

### [FN-22] [Severity: Tinggi] Toleransi denda bawaan (`payment.late.grace_days = 7`) tidak pernah berlaku; denda berjalan sejak hari pertama
- Label bukti: [TERBUKTI-API]
- Lokasi: `finance_engine.compute_scheme_items:136-140` (`"grace_days": int(i.get("grace_days") or 0)` → selalu angka, 0 bila kosong) + `late_fee_engine.grace_of:92-95` (`g not in (None, "")` → 0 dianggap eksplisit, tidak jatuh ke bawaan).
- Reproduksi: deal seed A-01, Termin I Rp 212.500.000 jatuh tempo 2026-10-11, hari ini 2026-11-05 (25 hari). Kebijakan layar: toleransi 7 hari, 2%/bulan, batas 5%. `GET /finance/late-fees/{deal}` → `grace_days:0, days_late:25, denda_running 3.541.667`. Dengan toleransi 7 hari seharusnya 18 hari → 212,5 jt × 2% × 18/30 = **Rp 2.550.000** (kelebihan tagih Rp 991.667). `POST …/apply` → `JV/2026/00085` Dr 1-1300 / Cr 4-1400 3.541.667, memo "(25 hari lewat toleransi)" — menyebut toleransi yang tidak diberikan. Semua item AR semua deal berisi `grace_days:0`.
- Dampak: pembeli ditagih denda lebih tinggi dari kebijakan owner; keputusan Finance menjalankan denda "otomatis" (`payment.late.auto_apply`) akan mengulang kekeliruan yang sama. Terkait KT-10 (toleransi tanggal 20 juga diabaikan).
- Tambahan [DARI-KODE]: `late_fee_engine.assess_item` tidak mengecualikan termin `payer="bank"` — porsi bank (mis. Rp 850 jt KPR) yang terlambat dicairkan bank dikenai denda ke pembeli. Tidak bisa diuji (butuh jatuh tempo lampau pada deal KPR).
- Saran: simpan `grace_days=None` bila tidak diisi; kecualikan termin bank dari denda.

### [FN-23] [Severity: Tinggi — GL-07 belum tertutup] BAST/pengakuan pendapatan tanpa gerbang pelunasan atau serah terima
- Label bukti: [TERBUKTI-API]
- Lokasi: `finance_engine.recognize_revenue:921-974`, `routers/ar_router.py:226-233` (izin `finance:update`).
- Reproduksi: deal B (KPR, Rp 850 jt, terbayar Rp 0, hanya booking fee Rp 5 jt di titipan): `POST /finance/ar/{deal}/bast` → 200; `JV/2026/00088`: Dr 1-1300 850.000.000 / Cr 4-1100 850.000.000; Dr 5-1100 595.000.000 / Cr 1-1600 261.000.000 / Cr 2-1700 334.000.000; unit `sold`, deal `completed`. Laporan Pendapatan menampilkan revenue Rp 1,7 M (2 deal). HPP = estimasi 70% harga (`cogs_source: estimate_70pct`) karena RAB unit tidak ada — ditandai tetapi tetap dijurnal.
- Pada deal lunas (A-05): benar — Dr 2-1400 850 jt / Cr 4-1100 850 jt, HPP 595 jt, kewajiban kontrak → 0.
- Dampak: pendapatan & laba diakui sebelum syarat bisnis; piutang 1-1300 Rp 850 jt tanpa tagihan jatuh tempo.

### [FN-24] [Severity: Tinggi] Faktur Pajak: bisa terbit untuk deal batal dan belum bayar; DPP = harga penuh; PPN tidak ada di AR/GL
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/tax_router.py` `POST /tax/faktur`, `tax_engine.faktur_candidates`, `finance_engine.compute_taxes:77-89`.
- Reproduksi: `GET /tax/faktur-candidates` memuat A-03 (batal), A-01 (baru bayar DP), deal belum bayar. `POST /tax/faktur {deal_id: A-03, buyer_npwp, "010"}` → 200 `010.000-26.00000003`, DPP 850.000.000, **PPN 102.000.000** (12% × harga penuh) untuk kontrak yang dibatalkan dengan uang diterima Rp 5 jt. `tax_records.ppn` Rp 102 jt tercipta untuk setiap deal, tetapi **tidak ada** di total AR (AR = harga unit), tidak ada jurnal PPN keluaran (GL-04 ronde 1 tetap).
- Dampak: SPT Masa PPN (rekap dari faktur 'issued') memuat PPN keluaran deal batal; besar PPN Rp 102 jt tidak pernah ditagih ke pembeli → menggerus margin atau harga dianggap inklusif tanpa pemisahan DPP. Selain itu DPP "nilai lain" 11/12 untuk barang non-mewah (basis efektif 11%) tidak dimodelkan; PPN dibebaskan/DTP untuk rumah tertentu tidak ada pembeda [regulasi menurut pengetahuan auditor, mohon konfirmasi konsultan pajak].
- Pertanyaan pemilik #1 (harga inklusif/eksklusif PPN) tetap menentukan.

### [FN-25] [Severity: Sedang — IN-14 belum tertutup] Ganti/regenerasi skema memutus tautan alokasi kuitansi
- Label bukti: [TERBUKTI-API]
- Reproduksi: deal B-06: bayar Rp 50 jt (alokasi DP) → `POST /finance/ar/{deal}/schedule` skema lain → `items` baru ber-ID baru; jumlah terbayar dibawa FIFO (AR.paid 55 jt benar) tetapi **ketiga kuitansi** (`KWT/2026/0011, 0012, 0027`) menunjuk `allocations[].item_id` yang sudah tidak ada ("TAUTAN PUTUS"). Void kuitansi sesudahnya tidak bisa membalik alokasi per item secara tepat.
- Tambahan: regenerasi menghapus `tax_records` yang sudah `paid` (lihat finance-komponen-biaya FN-07).

### [FN-26] [Severity: Sedang — KT-10/KT-11 belum tertutup] Konfigurasi jatuh tempo diabaikan; jatuh tempo dihitung dari booking
- Label bukti: [TERBUKTI-API]
- Reproduksi: `payment.staged.due_day=7`, `grace_day=20` (Pusat Konfigurasi). Skema bawaan "Cash bertahap (DP 80% + 6× cicilan)" tetap `due_mode: offset_days` ("30 hari setelah kontrak diaktifkan"), AR: cicilan 1 jatuh tempo 2026-12-05 (booking + 30 hari). DP "saat kontrak diaktifkan" memperoleh tanggal = tanggal booking (2026-11-05) padahal kontrak masih `draft`. SPR memuat kalimat itu.
- Dampak: dokumen yang ditandatangani pembeli ≠ kebijakan owner; denda menghitung dari tanggal yang keliru.
- Catatan: `due_day` maksimum 28 (validator "supaya Februari tidak meleset") — jatuh tempo "akhir bulan/29–31" tidak bisa disusun; Februari terbukti benar (bulan ke-1 dari 31 Jan → 28 Feb).

### [FN-27] [Severity: Sedang] Booking fee pada skema KPR tanpa termin pembeli tertahan di titipan
- Label bukti: [TERBUKTI-API]
- Reproduksi: skema "KPR (DP 0% + pencairan bank)" (satu termin bank 100%): booking fee Rp 5 jt tetap di `customer_deposits` (saldo 5.000.000, 2-1450) karena tak ada termin pembeli yang bisa dilunasi; AR 850 jt seluruhnya porsi bank. Tidak ada peringatan/aksi (kembalikan/kurangi plafon). Pada skema KPR ber-DP (Standar KPR DP 20%) booking fee masuk DP dengan benar.
- Dampak: uang pembeli menggantung; setelah BAST tersisa sebagai titipan.

### [FN-28] [Severity: Sedang] Tidak ada kontrol rekonsiliasi AR dan tie-out aging; neraca tidak memuat piutang sebelum BAST
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- `/finance/reconcile` hanya 2-1100, 2-1200, 2-1400, 2-1450, 2-1600, TB — tidak ada 1-1300 dan tidak ada 2-1470. GL 1-1300 = 0 sampai BAST/denda (Rp 9–10 M piutang "Piutang (AR) Outstanding" di dasbor tidak ada di neraca). Setelah BAST terkontrol: GL 1-1300 Rp 850.000.000 = Σ outstanding deal ber-BAST (cocok, diuji manual), tetapi tidak dijaga otomatis. Tidak ada rekonsiliasi `ar_aging` ↔ `ar_invoices.outstanding` ↔ GL — itulah sebabnya FN-21 lolos.

### [FN-29] [Severity: Sedang] Tabel Piutang & Utang: kolom penting tertutup kolom "Aksi" sticky pada layar 1440 px
- Label bukti: [TERBUKTI-UI] (`f02-piutang.png`, `f03-utang.png`; pengukuran DOM: tabel AP lebar 1396 vs wadah 1118; kolom "Jatuh tempo" 67 px, "Sisa" tampil "Rp" terpotong)
- Lokasi: *Keuangan › Utang › Tagihan Vendor*: SISA/JATUH TEMPO/STATUS tertutup; *Piutang › Daftar Piutang*: PIUTANG BIAYA/TITIPAN/STATUS/UMUR tertutup (harus scroll horizontal). Kolom status & sisa adalah informasi utama penagih.

### [FN-30] [Severity: Rendah] Lain-lain
- IN-19 belum: `ReceiptCreate` tidak punya tanggal bayar (juga `ApPay`, `PayIn`): tanggal = waktu input (UTC) → pembayaran kemarin yang baru dicatat menjadi jurnal hari ini; antar-bulan masuk periode salah.
- Banker's rounding `round()` pada denda/termin (selisih ≤ Rp 1; Σ termin tetap = harga karena baris terakhir menyerap selisih).
- IN-17: id bukti palsu & bukti dipakai ulang diterima pada kuitansi AR (lihat finance-komponen-biaya FN-15).
- Memo jurnal pembayaran denda "Penerimaan pembayaran pembeli (uang muka)" padahal mengkredit 1-1300.

---
## Verifikasi ulang klaim ronde 1 (area AR)
| ID | Status | Bukti |
|---|---|---|
| IN-01/02 (penerimaan ganda, titipan negatif) | **Tertutup** | 2 receipt identik paralel → 409+200; 2 nominal beda → 409+200; refund titipan > saldo 400; pakai titipan tanpa saldo 400 |
| IN-04 refund ganda | Tertutup (kode+guard; refund dibatasi ketentuan jual-ulang) | `POST /cancellations/{id}/refund` 400 dengan alasan jelas |
| IN-05/GL-10 void | **Tertutup** | void receipt 100 jt → `JV/00105` Dr 1-1300/Cr bank; AR.paid kembali 0; sinkron |
| IN-06/07 (GL-01/02) | **Tertutup** | penerimaan pasca-BAST → Cr 1-1300; pelunasan denda → Cr 1-1300; BAST tidak memuat denda |
| IN-12 (waive SoD) | **Tertutup** | finance 403 (`late_fee:override`), finlead 200 + jurnal balik; tagih ulang 400 |
| IN-13 (bayar ke deal batal) | **Tertutup** | 400 jelas |
| IN-15 (`method=kpr` manual) | **Tertutup** | 400 |
| KT-07 (jadwal pada deal batal) | **Tertutup** | 400 |
| IN-14 (tautan alokasi) | **Belum** | FN-25 |
| IN-17 (bukti palsu/berulang) | **Belum** (jalur masuk) | FN-15 |
| IN-19 (tanggal bayar) | **Belum** | FN-30 |
| GL-07 (BAST) | **Belum** | FN-23 |
| KT-10/KT-11 | **Belum** | FN-26 |
| KT-05 | **Belum** | finance-komponen-biaya FN-11 |
| GL-04 (PPN dibebankan 6-1400) | Belum | FN-24 / finance-ap FN-40 |

## Terverifikasi OK
- Pembangkitan jadwal: Σ termin = harga pada harga 1, 7, 100.000.001, 123.456.789, 999.999.999, 10^12 (selisih 0; baris terakhir menyerap); 12 cicilan 5,8333% + DP 30% balanced; Februari → 28 Feb.
- Alokasi: FIFO (jatuh tempo terlama), alokasi terpilih ("Cicilan 3/6" Rp 10 jt) menang atas FIFO, parsial, lebih tanpa `allow_overpay` → 400 dengan angka kelebihan; `allow_overpay` → titipan Rp 5 jt (2-1450 Rp 5 jt = subledger); 0/negatif/desimal (1000.5)/10^15 → 400; porsi bank tidak bisa dilunasi setoran pembeli kecuali `allow_bank_portion`.
- KPR: tahap bernominal ±1% toleransi (Rp 500 jt vs 548,8 jt → 400); syarat "serah terima" menahan tahap 2; SP3K plafon 784 jt mengubah AR: DP pembeli 196 jt + porsi bank 784 jt; booking fee masuk DP; pencairan → Dr bank / Cr 2-1400 548.800.000; AR 3-arah sinkron.
- Denda: rumus 2%/bulan × hari/30 (batas 5% dan minimum Rp 50 rb) cocok hitungan manual; jurnal Dr 1-1300 / Cr 4-1400; keringanan oleh manajer lain membalik jurnal & mencegah tagih ulang.
- Booking fee → termin otomatis; komponen BOOKING; pembatalan: jurnal Dr 2-1400 / Cr 4-1200 (potongan 35%) / Cr 2-1460.
- Laporan penerimaan: Σ amount = Σ `receipts.amount` DB (Rp 3.882.341.667 pada 33 baris, diuji akhir sesi); dasbor Kewajiban Kontrak Rp 2.898.800.000, Titipan Rp 7.000.000, Pendapatan Diakui Rp 1.700.000.000 = subledger = GL (2-1400, 2-1450, 4-1100).
- Pembukuan GL berjalan via dispatcher dengan jeda ≤ ~8 dtk (event_pending ditampilkan di `/finance/reconcile`).

## Tidak bisa diverifikasi
- Denda pada porsi bank dan toleransi tanggal-20 (butuh jam sistem lampau); penagihan otomatis harian (`payment.late.auto_apply` = off).
- Pencairan KPR sampai tahap 2 (butuh serah terima fisik) dan plafon < porsi bank (kode memaksa jatuh tempo selisih; tidak diuji).
- Refund pembatalan pasca-penjualan ulang unit.
- Multi-worker / ribuan deal (kinerja `ar_aging` memuat 2000 AR ke memori).

## Pertanyaan terbuka
1. Harga jual inklusif atau eksklusif PPN? Apakah faktur pajak diterbitkan saat uang muka atau saat BAST/AJB?
2. Titik pengakuan pendapatan (serah terima fisik, AJB, pelunasan) — menentukan perbaikan FN-23.
3. Siapa yang menanggung denda keterlambatan pencairan bank pada KPR (pembeli atau developer)?
