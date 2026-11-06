> Laporan agen fuzz invarian (disalin apa adanya; path kerja dibersihkan). Alatnya ada di `scripts/fuzz/`. Verifikasi saya: `11_POLA_BUG_DAN_SAPUAN.md` bagian 8.3.

# Pola bug lewat FUZZ INVARIAN — penguji invarian + penjalan operasi acak (instance #12, API :8052, DB `<db_uji>`)
Tanggal: 2026-11-06 · Kode: cabang `claude/wizardly-heisenberg-7onk5l` @ HEAD (`906a827`) · Repo read-only; alat & data uji di scratchpad.
Alat: `scripts/fuzz/` — jalankan `python fuzz_invariants.py --api http://localhost:<port> --seed N --ops M --mode seq|conc` (lihat `README.md`).

## Ringkasan eksekutif
- Dibangun **alat permanen**: 74 invarian (65 keras + 9 indikator) berupa fungsi `snapshot → daftar pelanggaran` (modular: `fz/invariants/inv_*.py`), 49 jenis operasi acak berperan sesuai (`fz/ops.py`), mode **sekuensial** (cek tiap operasi, cek GL setelah antrean event kosong) dan **konkuren** (letusan 2–4 operasi serentak pada entitas sama, 45 pasangan), pengecil otomatis (ddmin) ke reproduksi minimal yang bisa diputar ulang, dan skrip verifikasi HTTP eksplisit.
- Dijalankan: **1,797 operasi sekuensial** (17 run, seed 11, 12, 13, 14, 15, 31, 41, 42, 43, 44, 45, 61, 62, 63, 71, 72, 73) dan **192 putaran konkuren** (1,326 operasi, 10 run, seed 21, 22, 23, 24, 25, 26, 27, 28, 29, 30); 2,391 pengecekan penuh; 145,085 evaluasi invarian; 49 jenis operasi berbeda; 0 HTTP 5xx.
- Hasil: **8 temuan baru** — 4 Tinggi (FZ-01, FZ-02, FZ-03, FZ-08), 3 Sedang (FZ-04, FZ-06, FZ-07), 1 Rendah (FZ-05) — ditambah konfirmasi 9 kelas temuan lama yang masih terbuka di HEAD. Semuanya direproduksi minimal (3–10 langkah) dan diverifikasi ulang dengan HTTP eksplisit.
- Pola yang berulang: **jalur "sampingan" yang tidak ikut penjaga jalur utama** — void kuitansi (FZ-01/02), BAST (FZ-03), tahap KPR (FZ-08), hapus-paksa (FZ-04/07), retur (FZ-06) — tiap perbaikan ronde 1–2 menutup satu pintu, pintu lain ke tabel yang sama tetap terbuka. Rekomendasi: satu penjaga status-kontrak/deal bersama + invarian ini sebagai gate CI.
- Kabar baik: jalur uang masuk utama (kuitansi, titipan, konversi, reservasi, giro, komisi, AP) **lolos semua invarian di bawah beban acak & serentak**; salinan nama pada tampilan hidup dan PIC setelah reassign konsisten (KT-15/KT-16 terbukti tertutup).

## Cakupan
- **Sekuensial** (`--mode seq`): tiap run membuat proyek `AUDIT-FZ <tag>` + 40 unit + 3 material + skema `AUDIT-FZ telat`; operasi dipilih acak berbobot (55% mengikuti "perjalanan" logis lead→reservasi→booking fee→booking→konversi→bayar/KPR→BAST, sisanya acak murni untuk menguji transisi tak sah). Invarian non-GL dicek setelah **setiap** operasi, invarian GL tiap 5 operasi setelah antrean event kosong.
- **Konkuren** (`--mode conc`): letusan serentak pada entitas yang sama, antrean event dibiarkan diproses dispatcher alami. Letusan yang dijalankan (jumlah putaran): late||late (12), reserve||reserve(unit sama) (10), cb_disburse||cb_disburse (9), receipt||receipt (9), return||bill (8), scheme||receipt (7), transfer||stock_out (6), pdc_clear||pdc_clear (6), bf||cancel (6), book||cancel (6), bast||bast (6), cancel||receipt (5), book||bf (5), late_waive||late_waive (5), bill_approve||bill_approve (5), reassign||edit (5), delete||receipt (5), dep_apply||receipt (5), cancel||convert (4), delete||void (4), grn||grn (4), edit_lead||edit_lead (4), late||receipt (4), stock_out||stock_out (4), commission approve||pay (4), bank_match||bank_match (4), void||void (3), late_waive||receipt (3), grn||po_cancel (3), convert||convert (3), bill_pay||bill_pay (3), return||return (3), reschedule||receipt (3), receipt||receipt_rest (3), bast||receipt (3), kpr_disb||cancel (2), bast||void (2), bf||bf (2), bill_pay||void (2), dep_refund||dep_refund (2), reserve||reserve(lead sama) (1), dep_apply||dep_refund (1), receipt||void (1).
- **Operasi** (berhasil/dicoba, gabungan): reserve 211/343, receipt 206/319, convert 210/230, lead_new 226/226, book 174/226, bf_pay 180/222, bast 6/126, kpr_stage 37/86, receipt_rest 38/86, stock_txn 54/69, cb 48/66, void_receipt 20/54, commission 24/54, scheme_change 10/53, po_new 50/50, late_apply 32/50, cancellation 22/47, cancel_deal 10/45, dep_in 39/43, dep_apply 8/42, edit_lead 40/40, grn 20/38, dep_refund 15/37, edit_customer 25/37, bill_approve 19/35, po_approve 31/34, bank_stmt 33/33, force_delete 31/33, reassign 32/32, late_waive 13/27, kpr_disb 0/27, activate 16/27, lead_contact 26/26, bill_manual 26/26, transfer 11/24, po_bill 9/22, pdc_new 17/22, pdc_act 10/20, reschedule 10/20, req 19/20, opname 20/20, bill_pay 6/19, return 15/15, bank_match 1/14, appt 11/11, lead_stage 9/9, po_cancel 7/8, tick 5/5, pay_void 2/5.
- Data uji berawalan `AUDIT-FZ` / `AUDIT-FZV`; tidak ada penulisan langsung ke DB (hanya pymongo baca-saja); tidak ada file repo yang diubah.
- Seed tercetak di baris pertama keluaran tiap run; urutan operasi lengkap tersimpan di `fuzz/runs/run_*.json` (dengan label simbolik) sehingga dapat diputar ulang.
- Baseline awal data demo (sebelum operasi alat pertama): **6 pelanggaran** — M19 komisi ganda deal `028aa9`; G16 tagihan AP approved tanpa jurnal (FN-05/FN-44); O11 ×2 (PIC deal ≠ PIC lead); O18 ×2 (deal `completed` tanpa pengakuan pendapatan) — bukan hasil operasi alat.

## Temuan (urut severity)

> Semua temuan di bawah **ditemukan oleh penjalan acak, dikecilkan (shrink) ke reproduksi minimal, lalu diverifikasi ulang dengan skrip HTTP eksplisit tanpa kerangka fuzz** (`verify_fz.py`, keluaran mentah di `fuzz/runs/verify_FZ*.txt`). Urutan operasi di tiap temuan memakai label simbolik (`lead#1`, `deal#2`, `unit#5`) dan dapat diputar ulang: `python fuzz_invariants.py --replay <berkas repro>`.

### [FZ-01] [Severity: Tinggi] Void kuitansi SETELAH BAST membalik uang ke `2-1400` yang sudah nol: kewajiban kontrak negatif, piutang `1-1300` tidak muncul, unit "terjual" bertanda "sebagian dibayar"
- Label bukti: [TERBUKTI-API] (verifikasi manual `verify_fz.py FZ-01`) + ditemukan fuzz (M12/M21, 32 deal terdampak di DB uji)
- Kelas: varian **GL-01 / IN-05 / GL-10** (GL-01 menutup penerimaan & titipan *sesudah* BAST; jalur *void* sesudah BAST belum tersentuh).
- Lokasi: `backend/bank_match.py:382-396` (`_void_receipt_locked`: `_recalc_invoice` → `contract_liabilities $inc -liab_part` → `credit_lines_for_collection(..., debit=True)` memakai `gl_split` saat kuitansi dibuat, tanpa memeriksa `contract_liabilities.recognized`/`revenue_recognitions`). Tombol UI: Keuangan › Piutang › kuitansi › Batalkan.
- Reproduksi minimal (fuzz, seed 3, 6 langkah, `fuzz/runs/repro_s3r1_M12_0.json`): `lead_new → reserve(bf=0, kpr) → book → receipt_rest (lunas) → bast → void_receipt`. Verifikasi manual (skema Cash keras, harga Rp 500 jt): bayar Rp 495 jt → BAST → void kuitansi Rp 495 jt.
- Hasil nyata: AR `paid` → `partial` (paid 5 jt, outstanding 495 jt); `contract_liabilities.balance = −495.000.000` (recognized=true); unit `sold` + `payment_status=partial`; jurnal pembalik `Dr 2-1400 495 jt / Cr 1-1201 495 jt` (GL 2-1400 bertambah debit 495 jt, bank −495 jt); `1-1300` Δ=0, `4-1100` Δ=0.
- Seharusnya: piutang pembeli yang timbul karena pembatalan pembayaran pasca-BAST dibukukan `Dr 1-1300 Piutang` (bukan `2-1400` yang sudah dibersihkan RevRec), kewajiban kontrak tidak boleh negatif; atau void pasca-BAST ditolak dan diarahkan ke nota koreksi.
- Dampak: neraca memuat akun kewajiban bersaldo debit (understated liability) dan piutang Rp 495 jt hilang dari `1-1300`; subledger kewajiban kontrak negatif (tie-out G01/M11/M12 retak); laporan penjualan menganggap unit terjual dengan status bayar sebagian. Muncul di 32 deal pada DB uji hanya dari ±1.200 operasi acak — operasi "batalkan kuitansi" pada deal yang sudah BAST adalah hal yang wajar dilakukan staf (salah input nominal).
- Saran: di `_void_receipt_locked` cabangkan menurut keadaan deal: (a) belum BAST → perilaku sekarang; (b) sudah BAST → `Dr 1-1300` & tahan `contract_liabilities`; (c) kontrak dibatalkan → tolak (arahkan ke refund). Tambahkan invarian M12/M11 sebagai gate CI.

### [FZ-02] [Severity: Tinggi] Void kuitansi sesudah pembatalan kontrak disetujui menghidupkan kembali AR deal batal dan membalik `2-1400` kedua kali (utang refund tidak ikut turun)
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-02`) + fuzz (M04/M12/M21/O03, 21 deal terdampak)
- Kelas: varian **IN-13** (IN-13 menutup `apply_receipt` ke deal batal; jalur *void* tidak memakai `_deal_closed_reason`) dan **GL-10**.
- Lokasi: `backend/bank_match.py:382-396` (tanpa `fe._deal_closed_reason`, `finance_engine.py:546`); `cancellation_engine.py:437-461` (keputusan pembatalan sudah menolkan `contract_liabilities` & memindahkan uang ke `2-1460`).
- Reproduksi minimal (fuzz, seed 11, 8 langkah, `repro_s11r1_M21_0.json`): `reserve(bf=0) → book → convert → cancellation(ajukan) → receipt → cancellation(setujui) → void_receipt`. Manual: kuitansi tunai Rp 40 jt, pengajuan & persetujuan pembatalan, lalu void kuitansi itu.
- Hasil nyata: sebelum void — deal `cancelled`, AR `cancelled`, unit `available/none`, `2-1460 = Rp 1.314.299.996`. Sesudah void — AR `partial` (outstanding Rp 495 jt pada deal BATAL), unit **`available` dengan `payment_status=partial`**, `contract_liabilities = −40.000.000`, `Dr 2-1400 40 jt / Cr bank 40 jt`; `2-1460` (utang refund) tetap Rp 1.314.299.996 padahal uang yang menjadi dasarnya sudah dibalik.
- Dampak: uang pembeli tercatat keluar dari bank lewat void, tetapi kewajiban refund ke pembeli yang sama tetap ada dan bisa dibayar → kas keluar ganda; AR deal batal tampil "tertagih" (laporan umur piutang FN-21 menghitungnya lagi); unit tersedia tampil "sebagian dibayar" (tautan basi KT-25).
- Saran: tolak void bila deal/kontrak `cancelled` atau pembatalan `disetujui`/`selesai` (pakai `_deal_closed_reason` yang sama dengan `apply_receipt`); koreksi uang pasca-pembatalan lewat refund.

### [FZ-03] [Severity: Tinggi] `POST /finance/ar/{deal}/bast` tidak memeriksa apa pun: deal baru "reserved" (tanpa booking, AR, kontrak, atau pembayaran) langsung diakui pendapatannya dan menjadi "completed/sold"
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-03`) + fuzz (O01/O05/O18; konsekuensi lanjutan O04/M04)
- Kelas: varian **GL-07 / FN-23** (BAST tanpa gerbang pelunasan; masih terbuka ⚖). Fakta baru: gerbang yang hilang bukan hanya "pelunasan" — **status deal, keberadaan AR, kontrak, dan pembatalan tidak diperiksa sama sekali**.
- Lokasi: `backend/routers/ar_router.py:291-298` (hanya `404` bila deal tak ada) → `finance_engine.py:921-967` (`recognize_revenue`: satu-satunya penjaga adalah idempotensi `existing`).
- Reproduksi minimal (fuzz, `repro_s3r1_O05.json`, 3 langkah): `lead_new → reserve(bf=5 jt) → bast`. Manual: reserve unit Rp 500 jt tanpa booking fee, lalu BAST.
- Hasil nyata: HTTP 200; `revenue_recognitions` terbentuk (revenue Rp 500 jt, HPP estimasi Rp 350 jt); jurnal `Dr 1-1300 500 jt / Cr 4-1100 500 jt`; deal `reserved → completed`; unit `sold/paid_off` tetapi `booked_by_deal=null` (hanya `reserved_by_deal` terisi → invarian dua-arah unit↔deal patah); tidak ada AR/kontrak/pembayaran. Seluruh ratusan "pelanggaran bawaan" O01/O05/O18 di DB uji berasal dari jalur ini.
- Varian lebih berat (**FZ-03b**, [TERBUKTI-API] `fuzz/runs/verify_FZ03b.txt`): BAST pada deal yang sudah **DIBATALKAN** juga HTTP 200 — deal `cancelled → completed`, unit yang sudah dilepas ke stok (`available`) menjadi `sold/paid_off`, pendapatan diakui; unit yang tersedia untuk dijual ke pembeli lain ditandai terjual.
- Dampak: satu klik Finance membukukan pendapatan Rp 500 jt + piutang fiktif untuk unit yang belum dibeli siapa pun; state machine dok 12 (§3: hanya `active → completed`) dilompati; pembayaran sesudahnya menghasilkan status ganjil (`sold` + `partial`).
- Saran: gerbang di `recognize_revenue`: `deal.status ∈ {booked}` + AR ada & `outstanding == 0` (atau penerimaan tertulis oleh Direksi) + serah terima (`unit_handovers`) — sejalan dengan keputusan produk GL-07.

### [FZ-08] [Severity: Tinggi] Tahap KPR (SP3K / akad) tetap diterima pada kontrak yang SUDAH dibatalkan: AR deal batal hidup lagi dengan sisa Rp 500 jt, pengajuan KPR "approved", unit tersedia bertanda `booking_fee`/`paid_off`
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-09`) + fuzz (O03/O04 seed 62; shrink 10 langkah)
- Kelas: varian **IN-13** (pintu KPR tidak ikut penjaga "deal/kontrak batal") dan **KT-25** (tautan basi pada unit available).
- Lokasi: `backend/routers/contracts_router.py:224-244` (`kpr_stage`) → `kpr_engine.kpr_advance` — tidak ada pemeriksaan `contract.state == "cancelled"` / `deal.status`; bandingkan `finance_engine._deal_closed_reason` (`:546`) yang hanya dipakai `apply_receipt`/`apply_deposit`.
- Reproduksi minimal (fuzz, `fuzz/runs/repro_s62r1_O03_0.json`, 10 langkah): `lead_new → reserve(kpr, bf=25 jt) → bf_pay → book → convert → kpr_stage(diajukan_ke_bank) → kpr_stage(appraisal) → cancellation(ajukan) → cancellation(setujui) → kpr_stage(sp3k)` → HTTP 200. Manual: sesudah persetujuan pembatalan `deal=cancelled, unit=available/none, AR=cancelled(outstanding 0)`; sesudah `POST …/kpr/stage/sp3k` dan `…/akad_kredit` (keduanya 200): AR **`unpaid`, outstanding Rp 500.000.000** pada deal batal, unit `available` dengan `payment_status=booking_fee`, pengajuan KPR `approved / akad_kredit`.
- Dampak: piutang fiktif Rp 500 jt masuk aging & dasbor (FN-21 menghitung AR deal batal); pengajuan KPR berstatus `approved` tetap aktif untuk unit yang sudah dilepas ke stok (bisa dipesan pembeli lain); [belum diuji] apakah pencairan KPR sesudahnya berhasil membuat kuitansi pada kontrak batal.
- Saran: satu penjaga `assert_contract_open(contract)` dipakai SEMUA pintu yang menyentuh AR/KPR/kuitansi (receipt, deposit, void, KPR stage, disbursement, schedule); tambahkan M21/O03/O06 ke gate.

### [FZ-04] [Severity: Sedang] Hapus-paksa deal meninggalkan giro (`pdc_instruments`) dan bukti kas BKM/BKK yatim — daftar koleksi anak salah nama dan tidak mencakup bukti kas
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-04`) + fuzz (G21 ×19 distinct, O14/O20)
- Kelas: **residu GL-05** (GL-05 ditutup untuk jurnal kuitansi; jalur deal/giro/bukti kas belum).
- Lokasi: `backend/force_delete.py:26` (`"pdc_cheques"` — koleksi sebenarnya `pdc_instruments`, `pdc_engine.py:34,102`); `force_delete.py:87` (jurnal deal dihapus, tetapi `cash_vouchers` hanya dibersihkan di `delete_receipt` `:191`).
- Reproduksi minimal (fuzz, `repro_s31r1_G21_0.json`, 5 langkah): `lead_new → reserve(bf=25 jt) → bf_pay → book → force_delete`. Manual: deal + kuitansi Rp 25 jt + giro Rp 10 jt + titipan Rp 3 jt, lalu hapus-paksa.
- Hasil nyata: deal hilang, tetapi `pdc_instruments` (status `received`, `deal_id` menunjuk deal tak ada) tertinggal; bukti kas `BKM/2026/0772` (receipt, Rp 25 jt) dan `BKM/2026/0773` (deposit, Rp 3 jt) menunjuk jurnal yang sudah tidak ada. Di DB uji: 258 bukti kas yatim.
- Dampak: buku kas (daftar BKM/BKK) memuat uang yang sudah tak ada di GL (register bukti kas ≠ buku besar) [TERBUKTI-API]; giro yatim berstatus `received` ikut dihitung "giro di tangan" (`pdc_engine.py:217`) [DARI-KODE — belum diuji apakah masih bisa dikliring].
- Saran: ganti nama koleksi; hapus `cash_vouchers` berdasarkan `journal_id` setiap kali jurnal dihapus (satu helper); tambahkan invarian G21/O20 ke gate `verify_business_invariants.py`.

### [FZ-06] [Severity: Sedang] Dua retur GRN serentak sama-sama lolos: retur melebihi penerimaan, stok negatif, `returned_qty` GRN & nilai PO salah (KONKUREN, 6/6)
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-06`: 6 dari 6 percobaan) + fuzz konkuren (P01/P02/S01, 15 pelanggaran, 4 seed)
- Kelas: **PG-04 / PG-05 masih terbuka di HEAD** ("retur tidak atomik") — dilaporkan sebagai konfirmasi + angka reproduksi, bukan temuan baru.
- Lokasi: `backend/procurement_extra.py:127-205` (`create_return`: baca GRN → hitung `avail` → `insert_one` → `update_one($set items…)` tanpa kunci/CAS; jalur uang lain sudah memakai `idempotency.locked`).
- Reproduksi (konkuren): GRN 100 sak; dua `POST /procurement/returns` serentak masing-masing `qty_returned=100`. Hasil 6/6: kedua HTTP 200; Σ retur = 200 (GRN diterima 100); `grns.items[0].returned_qty = 100` (lost update); stok buku material **−100 per percobaan**; `purchase_orders.received_value = 0`. Fuzz: `returned_qty=20 ≠ Σ retur=120`; Σ(GRN−retur) = −Rp 1.400.000 (nilai retur melebihi nilai penerimaan) sementara `received_value` tercatat Rp 5.600.000.
- Dampak: stok fisik negatif & nilai persediaan menyimpang; retur ke vendor dicatat melebihi barang yang pernah diterima (klaim ke vendor tak terbukti).
- Fasilitas lain (fuzz konkuren seed 29, 1×): `opname‖stock_out` — out 100 dan opname fisik 40 serentak pada stok 100 → stok buku −60 (selisih opname dihitung dari stok yang sudah dibaca).
- Saran: kunci per-GRN (`locked("grn.return", grn_id)`) atau `find_one_and_update` bersyarat pada `items.$.returned_qty`; sama untuk opname/transfer/issue (PG-04).

### [FZ-07] [Severity: Sedang] Hapus-paksa deal serentak dengan penerimaan kuitansi: uang masuk tercatat tanpa jurnal, kuitansi & kewajiban kontrak yatim (KONKUREN)
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-07`: 3/20 percobaan; fuzz konkuren: 3 dari 4 putaran `hapus-paksa‖kuitansi`) — probabilistik karena bergantung pada urutan waktu
- Kelas: **GL-05 / IN-05** (race baru pada jalur hapus-paksa).
- Lokasi: `backend/force_delete.py:70-134` (`delete_deal_cascade` membaca anak deal lalu menghapus; tidak ada kunci deal) vs `finance_engine.py:555+` (`apply_receipt` tidak menolak bila penghapusan sedang berjalan); `gl_engine.py:313-318` (event `payment.received` dilewati bila kuitansi/deal sudah tak ada → tidak ada jurnal).
- Hasil nyata (fuzz): `KWT/2026/0585` Rp 427.500.000 dan `KWT/2026/0621` Rp 215.500.000 tercatat dengan HTTP 200 (uang dianggap masuk), deal terhapus; tidak ada jurnal (`G13`), kuitansi tanpa deal (`M09/O14`), `contract_liabilities` yatim (`O20`); tie-out 2-1400 bergeser sebesar kuitansi itu (`G01 Δ −215.500.000`).
- Fasilitas kedua (**FZ-07b**, [TERBUKTI-API] `verify_fz.py FZ-07b`: 2 dari 10 percobaan; fuzz G15 pada 2 seed): hapus-paksa serentak dengan *void* kuitansi yang barusan dibuat (event jurnal masih antre). `void_receipt` memanggil `dispatch_pending()` (`bank_match.py:350`) sehingga jurnal penerimaan terbit **di tengah** penghapusan → jurnal `receipt` yatim (mis. `JV/2026/02376`, `JV/2026/02379`) tertinggal untuk deal yang sudah tidak ada: kas bank di GL naik tanpa subledger (G01/G15).
- Dampak: uang pembeli nyata (transfer bank) tidak ada di buku besar maupun di deal mana pun (FZ-07) atau ada di GL tanpa dokumen (FZ-07b); bukti bayar tak bisa dikaitkan ke pembeli.
- Saran: penghapusan-paksa mengambil kunci deal (`mutex("deal:"+id)`) yang juga diambil jalur uang masuk, atau tolak hapus-paksa bila ada kuitansi aktif dalam N detik terakhir.

### [FZ-05] [Severity: Rendah] `POST /deals/{id}/book` selalu menulis `units.payment_status = "booking_fee"` walau piutang sudah terbayar sebagian/penuh sebelum booking
- Label bukti: [TERBUKTI-API] (`verify_fz.py FZ-05`) + fuzz (O04 ×3)
- Lokasi: `backend/routers/deals_router.py:454` (nilai tetap); `finance_engine.py:520-532` (`_recalc_invoice` menurunkan nilai yang benar, tetapi hanya dipanggil saat pembayaran).
- Reproduksi minimal (fuzz, `repro_s4r1_O04_0.json`, 5 langkah): `reserve(bf=0) → dep_in 54 jt → reschedule (POST /finance/ar/{id}/schedule) → book`. Hasil: AR `partial` Rp 54 jt, CL Rp 54 jt, unit `booked` + `payment_status=booking_fee`. Variasi (seed 12): `receipt_rest` (AR lunas Rp 600 jt) lalu `book` → `booking_fee`.
- Dampak: papan unit / filter `payment_status` / peringkat piutang salah baca; self-heal baru terjadi pada pembayaran berikutnya. Kosmetik namun satu angka dua nilai.
- Saran: `book` memanggil penurunan status dari AR (atau tidak menyentuh `payment_status` bila AR sudah ada).

### Varian temuan lama yang DIKONFIRMASI masih terbuka di HEAD (tidak dihitung temuan baru)
| Kelas lama | Invarian | Reproduksi minimal (fuzz) | Catatan |
|---|---|---|---|
| **PG-06** PO dibatalkan padahal barang sudah diterima | P02 | `po_new → po_approve → grn(25%) → po_cancel` → 200 (`repro_s15r1_P02_0.json`) | stok sudah masuk, PO "cancelled" |
| **PG-21** `materials.consumed_qty` tersimpan basi (transfer/retur memakai `type=out` tanpa memperbarui agregat) | S02 | `transfer` lalu baca material: `consumed_qty=0` vs Σ out=200; 8 seed | persis reproduksi PG-21 |
| **IN-14 / FN-25** ganti/regenerasi skema memutus tautan alokasi kuitansi | M07 | `reserve(bf=10 jt, telat) → bf_pay → book → reschedule` → termin `paid_amount=10 jt` tetapi alokasi kuitansi menunjuk id termin lama (`repro_s42r1_M07_0.json`) | kini terjadi juga pada uang booking fee/titipan |
| **PK-12 / GL-23** komisi `approved` & catatan pajak `pending` (PPN/PPh/BPHTB) untuk deal batal | O16 | `cancellation(setuju)` → komisi Rp 15 jt `approved`, 3 catatan pajak `pending` | 12 distinct |
| **KT-29** tugas terbuka untuk deal/kontrak batal atau sudah dihapus-paksa | O15 | setelah `cancellation`/`force_delete` | soft |
| **KT-13** lead tetap `won` setelah deal batal/dihapus; tahap lead dioverride mundur dengan deal hidup | O08 | `force_delete`, `cancel_deal`, `lead_stage(override)` | 9 distinct |
| **IN-13 (desain)** titipan boleh diterima pada deal batal tanpa catatan pembatalan | M24 | `cancel_deal → dep_in` | disengaja menurut pesan sistem; uang tertahan sampai di-refund manual |
| **KT-02** lubang nomor kontrak/pembatalan/GRN | O13 | hapus-paksa & permintaan gagal | soft; wajar pada hard-delete |
| **KT-15 (aturan aman)** nama pembeli ≠ nama lead bila pembeli diedit sendiri | O10 | `edit_customer` | sesuai desain `leads_router._sync_contact_downstream`; indikator soft |

## Statistik
| Metrik | Sekuensial | Konkuren |
|---|---|---|
| Run / seed | 17 / 11, 12, 13, 14, 15, 31, 41, 42, 43, 44, 45, 61, 62, 63, 71, 72, 73 | 10 / 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 |
| Operasi dijalankan | 1,797 | 1,326 (dalam 192 putaran) |
| Diterima (2xx) / ditolak (4xx) / dilewati | 929 / 627 / 241 | 1,155 / 155 / 16 |
| HTTP 5xx | 0 | 0 |
| Pengecekan penuh | 2,189 | 202 |
| Evaluasi invarian (Σ) | 130,137 | 14,948 |
| Pelanggaran BARU unik (per invarian × pola pesan, dedup) | 157 | 74 |

Pelanggaran baru per invarian (seq+conc): G01 5, G07 1, G13 4, G15 2, G21 31, M04 1, M07 6, M09 4, M11 1, M12 4, M13 1, M21 4, O03 3, O04 4, O08 18, O09 7, O10 21, O13 22, O14 7, O15 29, O16 19, O20 11, P01 3, P02 4, S01 2, S02 17.
Letusan yang menghasilkan pelanggaran baru (jumlah pelanggaran): delete||receipt: 37, delete||void: 16, return||return: 15, return||bill: 12, edit_lead||edit_lead: 7, transfer||stock_out: 5, grn||grn: 3, late_waive||receipt: 1, late||late: 1, receipt||receipt: 1, reschedule||receipt: 1, reassign||edit: 1, book||cancel: 1. (Pelanggaran O13/O15/O10/S02 ikut terhitung di sana; temuan nyata hanya `hapus-paksa‖kuitansi`, `hapus-paksa‖void`, `retur‖retur`.)
Kelompok akar masalah → temuan: void pasca-BAST/pasca-batal (FZ-01/02: M04, M11, M12, M21, O03, G01); BAST tanpa gerbang (FZ-03: O01, O05, O18, O04); pintu KPR pada kontrak batal (FZ-08: O03, O04, M21); residu hapus-paksa (FZ-04: G21, O14, O20); balapan hapus-paksa (FZ-07: G13, M09, G15, G01); retur paralel (FZ-06: P01, P02, S01); `book` menimpa status (FZ-05: O04); varian lama (M07, O08, O15, O16, S02, P02).

## Alat & berkas
- Alat: `fuzz/fuzz_invariants.py`, `fuzz/fz/` (`core.py` registri+snapshot+klien, `invariants/inv_money|inv_gl|inv_ops|inv_stock.py`, `ops.py`, `conc.py`, `runner.py` shrink/replay, `world.py`), `fuzz/README.md`.
- Reproduksi minimal (JSON, putar ulang dengan `--replay`): `fuzz/runs/repro_s3r1_M12_0.json` (FZ-01), `repro_s11r1_M21_0.json` (FZ-02), `repro_s3r1_O05.json` / `repro_s3r1_O01.json` (FZ-03), `repro_s62r1_O03_0.json` (FZ-08), `repro_s31r1_G21_0.json` (FZ-04), `repro_s4r1_O04_0.json` (FZ-05), `repro_conc_return_return.json` (FZ-06), `repro_conc_delete_receipt.json` / `repro_conc_delete_void.json` (FZ-07), `repro_s15r1_P02_0.json` (PG-06), `repro_s42r1_M07_0.json` (IN-14).
- Verifikasi HTTP eksplisit: `fuzz/verify_fz.py FZ-01 … FZ-09` (keluaran mentah `fuzz/runs/verify_FZ*.txt`). Peta nama skrip ⇄ temuan: skrip `FZ-01..05` = temuan FZ-01..05; skrip `FZ-06` = FZ-06 (retur paralel); skrip `FZ-07`/`FZ-07b` = FZ-07 (hapus-paksa‖kuitansi / ‖void); skrip `FZ-09` = temuan FZ-08 (KPR sesudah batal); FZ-03b = `verify_FZ03b.txt`.
- Utilitas: `triage.py` (kelompokkan temuan dari run_*.json), `statsum.py` (statistik operasi + alasan penolakan), `showrepro.py` (cetak reproduksi), `catalog_status.py`, `stats_final.py`, `build_report.py`.
- Ringkasan per run: `fuzz/runs/run_seq_seed*.json`, `run_conc_seed*.json`; tabel katalog: `fuzz/runs/catalog_status.txt`.

## Katalog invarian dan status
Status: **LOLOS** = dievaluasi dan tak pernah dilanggar oleh operasi alat; **DILANGGAR** = pelanggaran baru oleh operasi acak (rujuk temuan); **indikator** = invarian lunak (bukan bukti kerugian); **lolos untuk operasi fuzz** = hanya sisa data demo.

| ID | Area | Invarian | Evaluasi | Status | Rujukan |
|---|---|---|---|---|---|
| G01 | GL | GL 2-1400 Uang Muka Penjualan = Σ contract_liabilities.balance (belum BAST) | 594 | DILANGGAR | FZ-01, FZ-02, FZ-07 (selisih agregat) |
| G02 | GL | GL 2-1450 Titipan Pelanggan = Σ customer_deposits.balance | 594 | LOLOS |  |
| G03 | GL | GL 2-1100 Utang Usaha = Σ (net − paid) tagihan disetujui | 594 | LOLOS |  |
| G04 | GL | GL 2-1200 Utang Retensi = Σ retensi ditahan (belum dicairkan) | 594 | LOLOS |  |
| G05 | GL | GL 2-1600 Utang Komisi = Σ komisi approved belum dibayar | 594 | LOLOS |  |
| G06 | GL | GL 1-1500 Kas Bon = Σ kas bon + pengajuan dana jenis advance yang cair & belum dipertanggungjawabkan | 594 | LOLOS |  |
| G07 | GL | GL 1-1300 Piutang = piutang BAST belum tertagih + denda belum tertagih (turunan dari AR) | 594 | indikator (soft) — lolos | setelah koreksi alat; 1 selisih −123.457 pada deal BAST + pengajuan batal (tidak diselidiki) |
| G08 | GL | GL 1-2100/1-2200 = Σ perolehan / akumulasi aset tetap aktif; akumulasi = Σ jurnal susut | 594 | LOLOS (data demo) | tak ada operasi aset tetap di penjalan |
| G09 | GL | GL 2-2100 Utang Bank = Σ sisa pokok fasilitas aktif; 2-1500 Utang Fee = Σ fee disetujui belum dibayar | 594 | LOLOS (data demo) | tak ada operasi pinjaman/marketing fee di penjalan |
| G10 | Jurnal | tiap jurnal seimbang (Σ debit = Σ kredit = total_*), baris valid (satu sisi, ≥0), minimal 2 baris | 2391 | LOLOS |  |
| G11 | Jurnal | source_event jurnal unik (tak ada jurnal ganda dari satu peristiwa); entry_no unik | 2391 | LOLOS |  |
| G12 | Jurnal | kode akun jurnal ada di CoA organisasi | 2391 | LOLOS |  |
| G13 | Jurnal | tiap kuitansi aktif yang membawa kas punya tepat satu jurnal 'receipt' (debit kas = Σ kas kuitansi) | 594 | DILANGGAR | FZ-07 |
| G14 | Jurnal | tiap kuitansi void punya tepat satu jurnal pembalik 'receipt_void'; pembalik hanya untuk kuitansi void | 594 | LOLOS |  |
| G15 | Jurnal | jurnal otomatis tidak yatim: sumber (kuitansi/titipan/tagihan AP/komisi/…) masih ada | 594 | DILANGGAR | FZ-07b |
| G16 | AP | tiap tagihan AP disetujui punya jurnal pengakuan; saldo 2-1100 per tagihan = net − paid | 594 | lolos untuk operasi fuzz | 1 sisa data demo (AP approved tanpa jurnal; FN-05/FN-44) |
| G17 | Kas | saldo rekening kas/bank (API posisi kas) = Σ baris jurnal pada akun GL rekening itu | 594 | LOLOS |  |
| G18 | Kas | saldo rekening kas/bank tidak negatif | 594 | LOLOS |  |
| G19 | Kas | payments_out aktif tak melebihi tagihan & tiap pembayaran vendor aktif punya jurnal (Σ kredit kas) | 594 | LOLOS |  |
| G20 | Event | tidak ada event pembukuan gagal permanen / tersangkut (pending >120 dtk, processing >120 dtk) | 2391 | LOLOS |  |
| G21 | Kas | tiap jurnal yang menyentuh rekening kas/bank punya bukti kas (BKM/BKK) bernilai sama; tak ada bukti kas yatim | 485 | DILANGGAR | FZ-04 (residu GL-05) |
| M01 | AR | ar_invoices.paid = Σ items.paid_amount | 2391 | LOLOS |  |
| M02 | AR | outstanding = total − paid (AR batal: outstanding = 0) | 2391 | LOLOS |  |
| M03 | AR | Σ items.amount = total (AR tidak batal) | 2391 | LOLOS |  |
| M04 | AR | status & batas tiap termin: 0 ≤ paid_amount ≤ amount, status sesuai | 2391 | DILANGGAR | FZ-02 (varian IN-13) |
| M05 | AR | status invoice sesuai paid/outstanding | 2391 | LOLOS |  |
| M06 | AR | ar_invoices.paid = Σ kuitansi tidak-void (applied) per deal | 2391 | LOLOS |  |
| M07 | AR | paid_amount tiap termin = Σ alokasi kuitansi aktif ke termin itu | 2391 | DILANGGAR (varian lama) | IN-14/FN-25 masih terbuka |
| M08 | Kuitansi | Σ allocations.amount = applied; kas = applied + titipan; kuitansi dana-titipan: amount = 0 | 2391 | LOLOS |  |
| M09 | Kuitansi | kuitansi menunjuk deal & AR yang ada (tanpa kuitansi yatim) | 2391 | DILANGGAR | FZ-07 (setelah koreksi alat untuk kuitansi booking fee) |
| M10 | Kuitansi | nilai kuitansi aktif tidak melebihi total tagihan + titipan (tidak ada kelebihan alokasi) | 2391 | LOLOS |  |
| M11 | KewajibanKontrak | contract_liability.balance = Σ bagian liability kuitansi aktif (deal belum BAST, tidak batal) | 2391 | DILANGGAR | FZ-01 (akibat) |
| M12 | KewajibanKontrak | balance ≥ 0 dan tepat satu baris kewajiban per deal | 2391 | DILANGGAR | FZ-01, FZ-02 |
| M13 | Titipan | titipan: saldo = Σ masuk − Σ dipakai − Σ dikembalikan ≥ 0; total tersimpan = Σ mutasi | 2391 | lolos | setelah koreksi alat (jenis mutasi cancel_transfer) |
| M14 | Titipan | titipan dipakai = Σ applied kuitansi berdana-titipan aktif (tak ada pemakaian tanpa kuitansi) | 2391 | LOLOS |  |
| M15 | Titipan | titipan masuk = Σ deposit_amount kuitansi tunai aktif + setoran titipan langsung | 2391 | LOLOS |  |
| M16 | AP | ap_invoices.paid = Σ payments_out tidak-void; paid ≤ net; outstanding = net − paid | 2391 | LOLOS |  |
| M17 | AP | status AP sesuai pembayaran; retensi = round(claimed×pct%); net = claimed − retensi | 2391 | LOLOS |  |
| M18 | AP | tiap pembayaran vendor aktif punya tagihan induk yang ada & tidak pending/ditolak | 2391 | LOLOS |  |
| M19 | Komisi | komisi: amount = round(base×rate%) ≤ base; approved/paid punya approver; satu komisi per (deal, penerima) | 2391 | lolos untuk operasi fuzz | 1 sisa data demo (komisi ganda deal 028aa9) |
| M20 | KPR | KPR: disbursed_total = Σ pencairan ≤ plafon; receipt_id pencairan ada; bukan nominal ≤ 0 | 2391 | LOLOS |  |
| M21 | Pembatalan | deal batal ⇒ AR batal (outstanding 0) dan kewajiban kontrak tak menggantung tanpa kuitansi/pembatalan | 2391 | DILANGGAR | FZ-02, FZ-08 (varian IN-13) |
| M22 | Pembatalan | refund pembatalan: Σ refund dibayar ≤ Σ kuitansi aktif deal; refund_paid_total = Σ refund_payments | 2391 | LOLOS |  |
| M23 | PDC | giro: giro cair punya kuitansi/jurnal yang ada; giro batal/tolak tidak punya kuitansi aktif | 2391 | LOLOS | giro cair/batal/tolak konsisten dengan kuitansi |
| M24 | Pembatalan | deal batal tidak menyimpan titipan pelanggan tanpa catatan pembatalan/refund (uang tertahan) | 2391 | indikator (soft) | IN-13 desain: titipan di deal batal |
| M25 | BookingFee | faktur booking fee: paid = Σ kuitansi BF aktif (− refund); refunded_total = Σ refunds; status & nominal selaras deal.booking_fee | 1200 | LOLOS |  |
| O01 | Unit | status unit konsisten dua arah dengan deal (reserved/booked/sold ⇒ deal sesuai; deal hidup ⇒ unit menunjuk balik) | 2391 | DILANGGAR | FZ-03 (varian GL-07/FN-23); + sisa demo |
| O02 | Unit | satu unit hanya boleh punya satu deal hidup (reserved/booked/completed) | 2391 | LOLOS |  |
| O03 | Unit | unit available bersih: tanpa deal hidup & tanpa tautan basi (deal_id/lead_id/customer_id/lead_name/payment_status) | 2391 | DILANGGAR | FZ-02, FZ-08 (varian KT-25/IN-13) |
| O04 | Unit | payment_status unit = fungsi status AR deal hidupnya (none/booking_fee/partial/paid_off) | 2391 | DILANGGAR | FZ-05; FZ-08; akibat FZ-03 |
| O05 | Deal | deal hidup punya tepat satu AR (kecuali draft/sebelum booking) dan satu kontrak aktif paling banyak | 2391 | DILANGGAR | FZ-03 |
| O06 | Kontrak | status kontrak selaras deal: deal batal ⇒ kontrak batal & AR batal; kontrak aktif ⇒ deal booked/completed | 2391 | LOLOS |  |
| O07 | Lead | satu pembeli per lead; pembeli menunjuk lead yang ada; kontrak menunjuk pembeli milik lead yang sama | 2391 | LOLOS |  |
| O08 | Lead | tahap lead selaras deal: lead dgn deal hidup ⇒ booking/won; lead 'booking' tanpa deal hidup = basi | 2391 | DILANGGAR (varian lama) | KT-13 (◐) — lead 'won' setelah deal batal/dihapus |
| O09 | Salinan | salinan nama/kode (lead_name, unit_code, customer_name, project_name, …) pada tampilan hidup sama dengan master | 2391 | indikator | hanya salinan 'dokumen/foto-saat-itu' (cancellations.customer_name); tampilan hidup 0 pelanggaran |
| O10 | Salinan | pembeli ↔ lead: nama & telepon pembeli sama dengan lead asalnya (indikator: pembeli yang diedit sendiri sah berbeda — aturan aman KT-15) | 2391 | indikator (soft) | KT-15 aturan-aman: pembeli yang diedit sendiri sah berbeda |
| O11 | PIC | PIC (assigned_to) lead = PIC deal hidup/kontrak/AR/komisi turunan lead itu | 2391 | lolos untuk operasi fuzz | 2 sisa data demo (PIC deal ≠ PIC lead); reassign oleh fuzz tidak menimbulkan pelanggaran baru |
| O12 | Nomor | nomor dokumen unik per koleksi | 2391 | LOLOS |  |
| O13 | Nomor | nomor dokumen berurutan tanpa lubang per (awalan, tahun) dan counter ≥ nomor terbesar | 2391 | indikator (soft) | KT-02 — lubang nomor (hapus-paksa/permintaan gagal) |
| O14 | Yatim | tidak ada baris anak yang induknya tidak ada (FK logis) | 2391 | DILANGGAR | FZ-04, FZ-07 |
| O15 | Yatim | tugas terbuka & agenda mendatang tidak menunjuk entitas yang dibatalkan/dihapus | 2391 | indikator (soft) | KT-29 — tugas terbuka untuk entitas batal/hilang |
| O16 | Komisi | komisi/marketing fee/pajak tidak aktif untuk deal yang dibatalkan (pending/approved/accrual) | 2391 | DILANGGAR (varian lama) | PK-12/GL-23 — komisi approved & pajak pending untuk deal batal |
| O17 | Kupon | coupons.used_count = jumlah deal hidup yang memakai kupon itu; tak melebihi kuota | 2391 | LOLOS |  |
| O18 | Handover | unit yang BAST-nya terbit ('issued') ⇒ deal completed & unit sold; unit sold ⇒ ada pengakuan pendapatan | 2391 | DILANGGAR | FZ-03; + sisa demo (2) |
| O19 | Progres | progres jadwal unit = Σ bobot langkah selesai ÷ Σ bobot; unit.construction_progress = progres jadwal | 2391 | LOLOS (data demo) | penjalan tidak memiliki operasi pengubah langkah bangun |
| O20 | Yatim | FK otomatis: setiap kolom *_id (deal/lead/unit/contract/customer/project/receipt/po/…) di koleksi mana pun menunjuk baris yang ada | 2391 | DILANGGAR | FZ-04, FZ-07 |
| P01 | Pengadaan | PO.items[k].received_qty = Σ GRN.qty_received (item k) − Σ retur (item k); GRN.returned_qty = Σ baris retur; tidak melebihi qty pesan | 2391 | DILANGGAR | FZ-06 (konfirmasi PG-04/05) |
| P02 | Pengadaan | PO: received_value = Σ nilai (GRN − retur); billed_value = Σ klaim tagihan PO aktif; status PO sesuai penerimaan | 2391 | DILANGGAR | FZ-06; PO batal setelah GRN = PG-06 |
| P03 | Pengadaan | tiap GRN menghasilkan mutasi stok 'in' sebesar qty diterima (per material) dan retur menghasilkan 'out' | 2391 | LOLOS |  |
| P04 | Pengadaan | PO/GRN/tagihan menunjuk entitas induk yang ada; GRN hanya untuk PO disetujui | 2391 | LOLOS |  |
| P05 | Pengadaan | tiap retur GRN menghasilkan mutasi stok 'out' (return_id) sebesar qty retur | 2391 | LOLOS |  |
| S01 | Stok | stok buku (Σ in − Σ out ± adjust) per material tidak negatif | 2391 | DILANGGAR | FZ-06 (juga opname‖stok keluar) |
| S02 | Stok | materials.consumed_qty (tersimpan) = Σ mutasi 'out'; over_budget = consumed > budget | 2391 | DILANGGAR (varian lama) | PG-21 — consumed_qty tersimpan basi |
| S03 | Stok | tiap mutasi stok menunjuk material yang ada & proyek yang sama dengan materialnya; qty > 0 untuk in/out | 2391 | LOLOS |  |

## Terverifikasi OK (invarian yang tidak pernah dilanggar oleh operasi acak)
Dengan seluruh operasi di atas (termasuk 152+ letusan serentak) invarian berikut **tidak** dilanggar — bukti positif bahwa perbaikan ronde 1–2 bertahan di HEAD:
- **Aritmetika AR**: `paid = Σ item.paid_amount = Σ kuitansi aktif`, `outstanding = total − paid`, `Σ item = total`, status termin/AR, tidak ada kelebihan alokasi (M01–M03, M05, M06, M08, M10).
- **Ganda/serentak pada jalur uang masuk**: kuitansi‖kuitansi, kuitansi‖sisa, void‖void, titipan pakai‖kembali, konversi‖konversi, reservasi unit sama / lead sama, booking-fee‖booking-fee, BAST‖BAST, kupon, giro‖giro, bayar AP‖bayar AP, setujui AP‖setujui AP, kas bon‖kas bon, komisi setuju‖bayar → **0 pelanggaran** (IN-01/02/03/04, KT-02/08/18, PK-02/03 terkonfirmasi tertutup). Satu `409` "Tagihan (AR) deal ini baru saja berubah…" muncul saat dua penerimaan serentak — kontrol versi bekerja.
- **Titipan**: `saldo = Σ masuk − Σ dipakai − Σ dikembalikan − Σ dipindah ke utang refund ≥ 0`, dan titipan terpakai = Σ kuitansi dana-titipan (M13, M14); tie-out GL 2-1450.
- **Buku besar**: semua jurnal seimbang, `source_event` unik, kode akun ada di CoA, tiap kuitansi aktif tepat satu jurnal dan tiap void tepat satu pembalik (kecuali jalur hapus-paksa), GL 2-1450 / 2-1100 / 2-1200 / 2-1600 / 1-1500 = subledger (2-2100 / 2-1500 / 1-2100 / 1-2200 hanya diuji pada data demo), saldo kas API = Σ jurnal, tak ada rekening kas negatif (G02–G06, G08–G12, G14, G17–G20); GL 1-1300 mengikuti piutang BAST + denda dalam alur normal (G07: Δ=0 pada denda → lunas → BAST).
- **AP**: `paid = Σ pembayaran aktif ≤ net`, retensi/net, status, pembayaran tak menunjuk tagihan belum disetujui (M16–M18).
- **Operasional**: tak ada unit dengan dua deal hidup (O02), status kontrak selaras deal (O06), satu pembeli per lead & kontrak menunjuk pembeli milik lead sama (O07), nomor dokumen unik (O12), `coupons.used_count` (O17), progres jadwal unit (O19, hanya data demo), salinan nama/kode pada **tampilan hidup** (deals/units/ar/contracts/commissions/…) selalu sama dengan master (O09 — KT-15 terbukti tertutup), PIC deal/kontrak/AR mengikuti reassign lead (O11 — KT-16 terbukti tertutup).
- **Pengadaan/stok**: stok tak negatif kecuali lewat retur paralel (S01), mutasi stok konsisten dengan GRN/retur (P03–P05), PO↔GRN↔tagihan menunjuk induk yang ada (P04); `received_qty` PO = Σ GRN − retur pada alur sekuensial (P01).

## Artefak alat yang ditemukan dan dikoreksi (TIDAK dilaporkan sebagai bug aplikasi)
| Invarian awal | Penyebab artefak | Koreksi |
|---|---|---|
| M13 titipan | tidak mengenal jenis mutasi `cancel_transfer` (titipan dipindah ke utang refund saat pembatalan, `cancellation_engine.py:442-452`) | rumus: `saldo = in − apply − refund − cancel_transfer` |
| M09 / M07 / M08 | kuitansi `kind=booking_fee` sah tanpa AR dan beralokasi semu (`item_id=null`, `applied=0`, uang parkir sebagai titipan) | dikecualikan |
| M21 | AR yang SUDAH LUNAS sengaja tidak ditandai `cancelled` oleh pembatalan formal (`cancellation_engine._void_ar:304-306`); titipan di deal batal sengaja diperbolehkan (pesan `_deal_closed_reason`) | dikecualikan / jadi indikator M24 |
| G07 / M11 | pengajuan pembatalan yang masih `diajukan` dianggap membatalkan | hanya `disetujui/refund_sebagian/selesai` |
| O04 | AR belum dibayar sah berlabel `none` atau `booking_fee`; status `handed_over` sah setara `sold` | dilonggarkan |
| O09 | `spk.spk_number` bukan `number`; dokumen/foto-saat-itu (`cancellations.customer_name`) sah berbeda dari master | master dikoreksi; pelanggaran koleksi non-"tampilan hidup" hanya indikator |
| O10 | KT-15 memang sengaja membiarkan pembeli yang diedit sendiri berbeda dari lead | diturunkan ke indikator (soft) |
| Alat | `POST /bank/statements/import` bawaan `dry_run=true` → impor mutasi tidak pernah menulis pada percobaan awal | `dry_run:false` |
| Alat | `nudge` (membuat lead AUDIT-FZ) mempercepat dispatcher pada mode sekuensial — dapat menyembunyikan balapan dispatcher; karena itu mode konkuren **tidak** memakai nudge | terdokumentasi |

## Tidak bisa diverifikasi / keterbatasan
- **Operasi yang belum ada di penjalan**: portal pembeli & verifikasi bukti, WhatsApp/inbox, SPK/opname/termin subkontraktor & retensi, pengajuan dana (`fund-requests`), upah/absensi, jurnal manual, tutup buku/tahun, aset tetap, pinjaman, marketing fee, faktur pajak, serah terima fisik (`/handover`), pembayaran PPh/pajak, impor/ekspor data. Invarian G08/G09/O19 untuk area itu hanya dievaluasi pada **data demo** (lolos), bukan setelah operasi acak.
- **Pencairan KPR** (`kpr_disb`): baru pada batch terakhir dapat dijalankan (butuh skema pencairan `BANK_STD`/tranche `T1`); cakupannya kecil.
- **Waktu**: tanggal jatuh tempo masa depan tidak bisa digeser; denda diuji lewat skema khusus `AUDIT-FZ telat` (termin berusia 45/20 hari). Sweeper terjadwal (kedaluwarsa reservasi, denda otomatis) tidak dipicu.
- **Balapan probabilistik**: FZ-07/07b terjadi pada 15% / 20% percobaan manual; "tidak ditemukan" pada letusan lain bukan bukti ketiadaan (hanya 1–10 putaran per jenis letusan).
- **Baseline kotor**: kampanye resmi berjalan pada DB yang sudah memuat sisa data uji eksplorasi alat ini (mis. ratusan deal hasil BAST-paksa). Mekanisme "baru/berubah dibanding cek sebelumnya" memisahkan hal itu; namun invarian agregat (G01, G07) hanya dapat dilaporkan sebagai Δ.
- **G07** (1-1300) adalah *turunan* dari AR (indikator): satu selisih −Rp 123.457 pada deal BAST yang sedang diajukan batal tidak diselidiki.
- Tidak diperiksa: UI (tidak ada pengujian browser dalam tugas ini).

## Pertanyaan terbuka (butuh keputusan produk)
1. Void kuitansi **sesudah BAST**: apakah harus ditolak (nota koreksi) atau dibukukan sebagai kenaikan piutang `1-1300` (FZ-01)? Aturan serupa untuk deal yang pembatalannya sudah disetujui (FZ-02).
2. Perlukah BAST **tanpa pelunasan** tetap dimungkinkan (GL-07 ⚖)? Minimal: deal harus `booked` dan punya AR (FZ-03).
3. Lead yang dioverride supervisor mundur tahap (`/leads/{id}/stage/override`) saat punya deal hidup — disengaja? (O08, KT-13 ◐).
4. Hapus-paksa deal: bolehkah dijalankan pada jam kerja saat jalur uang aktif? Tambahkan kunci deal (FZ-07).
5. Titipan pada deal batal (M24): disengaja menahan uang sampai refund manual — perlu tugas/alarm refund?
