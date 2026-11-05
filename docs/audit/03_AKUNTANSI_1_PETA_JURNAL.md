# GL-1 — Peta sumber jurnal & peta SSOT (Bagian A)

Instance #4 (UI :3004, API :8004, DB `sipro_gl`, org `org-sipro`). Semua baris di bawah berasal dari pembacaan kode (path:baris) DAN dicocokkan dengan jurnal nyata yang dihasilkan lewat API (label [TERBUKTI-API]) bila alurnya dijalankan. Alur yang tidak dijalankan ditandai [DARI-KODE].

## 1. Cara jurnal terbentuk (arsitektur)

* Satu-satunya "pintu tulis" jurnal: `gl_engine.post_journal` (`backend/gl_engine.py:113-187`). Ia: (1) dedup bila `source_event` ada, (2) memvalidasi kode akun ada di CoA (tidak memeriksa `is_active`, tidak memeriksa induk/anak, kecuali kas/bank), (3) menolak negatif / tidak seimbang, (4) memetakan `1-1100`/`1-1200` ke sub-akun rekening default atau `cash_account_id` (`cash_bank.resolve_code(strict=False)`, baris 139-143), (5) menggeser tanggal bila periode tutup / kas terkunci (`gl_periods.resolve_post_date`, `cash_period_lock.resolve_date`), (6) menerbitkan nomor `JV/<tahun>/<5 digit>`, (7) menerbitkan bukti kas BKM/BKK per baris kas (`cash_voucher.issue_for_journal`). Jurnal TIDAK memiliki dimensi: field jurnal = `entry_no,date,memo,lines,total_*,source_type,source_id,source_event,auto,posted_by,source_deal_id(opsional)`; baris = `account_code/id/name/type,debit,credit,memo` (diperiksa di DB: 0 dari 120 jurnal punya `project_id`; 0 baris punya dimensi proyek/unit/rekening-id).
* Dua jalur pemicu: (a) **event outbox** (`engine.emit` → `engine.dispatch_pending` tiap 8 dtk atau dipanggil langsung oleh AP) → handler di `gl_engine.register_gl_handlers` (9 tipe event); (b) **panggilan langsung** `gl.post_journal(...)` dari modul domain (lihat tabel). Jurnal jalur (a) terbit ASINKRON (sampai ±8 dtk setelah respons API; terukur: respons kuitansi 200 → jurnal muncul ≤ 9 dtk). Jalur (a) yang gagal 3× menjadi `status=failed` PERMANEN, tanpa endpoint retry (lihat GL-09).
* Kunci idempotensi: `source_event`. Untuk event outbox = `ev:<event_id>` (idempoten per EVENT, bukan per dokumen); untuk jalur langsung = kunci bisnis (`cashbon.disburse:<id>`, `asset.depr:<asset>:<periode>`, `tax.setor:<rec>` dst).
* Sumber lain yang MENULIS ke `journal_entries` tanpa `post_journal`: `cash_bank._migrate_header_lines` (`cash_bank.py:87-104`, meng-UPDATE baris jurnal lama saat startup), `force_delete` (`force_delete.py:87,177` HAPUS FISIK jurnal), `projects_router.py:142` (delete_many jurnal by `project_id` yang tak pernah ada), `data_mgmt_purge.py:22` (hapus massal jurnal+periode+counters). Tidak ada jalur INSERT lain (grep `journal_entries.insert` hanya di `post_journal`).

## 2. MATRIKS: peristiwa → jurnal

Kunci kolom "Akun": H = hardcode di kode; K = dari konfigurasi data (cost component). "kas*" = sub-akun rekening terpilih (`cash_account_id`) atau, bila kosong, rekening DEFAULT jenisnya (kas→`1-1100`→default kas; bank→`1-1200`→default bank). "now" = tanggal/jam saat jurnal diproses (bukan tanggal transaksi).

| # | Fitur / peristiwa | Pemicu (file:baris) | Debit | Kredit | Idempotensi (source_event) | source_type / source_id | Tanggal | Dimensi | Akun |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Penerimaan pembeli (DP/termin/pelunasan/KPR/denda — semua jenis) | `finance_engine.apply_receipt:513` → event `payment.received` → `gl_engine._gl_payment_received:263` | kas* (method cash/tunai→`1-1100`, selain itu `1-1200`) | `2-1400` | `ev:<event>` | `receipt` / id kuitansi; `source_deal_id`=deal | now | deal saja | H |
| 2 | Titipan masuk (kelebihan bayar, titipan bebas, BOOKING FEE) | `_deposit_move:602` → `deposit.received` → `_gl_deposit_received:288` | kas* (default BANK; booking fee tunai pun ke bank — TERBUKTI) | `2-1450` | `ev:` | `deposit` / id titipan (tanpa `source_deal_id`) | now | tidak ada | H |
| 3 | Titipan dipakai termin | `apply_deposit` → `deposit.applied` → `:301` | `2-1450` | `2-1400` | `ev:` | `deposit` | now | – | H |
| 4 | Titipan dikembalikan | `refund_deposit` → `deposit.refunded` → `:318` | `2-1450` | kas* (default bank, router tak kirim `cash_account_id`) | `ev:` | `deposit` | now | – | H |
| 5 | Booking fee hangus | `booking_fee.py:305` | `2-1450` | `4-1200` | `bf:<inv>:forfeit:<rec>` | `booking_fee_forfeit` / id refund-rec; deal | now | deal | H |
| 6 | Pengakuan pendapatan + HPP (BAST) | `ar_router.bast` → `recognize_revenue:837` → `revenue.recognized` → `:412` | `2-1400`(dibersihkan) + `1-1300`(rev−dibersihkan); `5-1100`(HPP) | `4-1100`(=Σ AR **termasuk denda & add-on**); `2-1450`(bila dibersihkan>rev); `1-1600`(sebatas saldo WIP org) + `2-1700`(sisa) | `ev:` (+cek `revenue_recognitions` per deal) | `revrec` / id revrec (tanpa `source_deal_id`) | now | tidak ada; WIP org-wide | H |
| 7 | Denda keterlambatan ditagih | `late_fee_engine.py:292` | `1-1300` | `4-1400` | `late_fee:<deal>:<item>:<YYYY-MM>` | `late_fee` / deal | now | deal | H |
| 8 | Keringanan denda | `late_fee_engine.py:354` | `4-1400` | `1-1300` | `late_fee_waive:<pen>` | `late_fee_waiver` / id denda | now | deal | H |
| 9 | Pembatalan penerimaan (via "batalkan pencocokan bank" / revert KPR) | `bank_match.void_receipt:275` (jurnal :312) | `2-1400` | `cash_account_code` kuitansi | `receipt.void:<rid>` | `receipt_void` / rid | now | – (tanpa `source_deal_id`) | H |
| 10 | Pembatalan kontrak — keputusan | `cancellation_engine.py:330` | `2-1400`(total diterima) + `2-1450`(saldo titipan) | `4-1200`(potongan) + `2-1460`(utang refund) | `cancel:<id>:approve` | `cancellation` / id; deal | now | deal | H |
| 11 | Bayar refund pembatalan | `cancellation_engine.py:572` | `2-1460` | kas* (tunai→`1-1100`; selain → `1-1200`; boleh pilih rekening) | `cancel:<id>:refund:<pid>` | `cancellation_refund` / pid; deal | now | deal | H |
| 12 | Alihkan booking fee → titipan biaya BOOKING | `allin_engine.py:280` | `2-1450` | `comp.gl_liability` (default `2-1470`) | `cost_receipt:<id>` | `cost_receipt` | now | deal | K |
| 13 | Terima biaya pembeli (BPHTB/notaris/bank/asuransi) | `allin_engine.pay_cost_invoice:413` | `1-1200`→bank default (tak bisa pilih rekening) | `2-1470` (**H**, tidak membaca `comp.gl_liability`) | `cost_receipt:<id>` | `cost_receipt` | now | deal | H |
| 14 | Salurkan titipan biaya ke notaris/BPN | `allin_engine.py:438` | `2-1470` | `1-1200`→bank default | `cost_disb:<id>` | `cost_disbursement` | now | deal | H |
| 15 | Beban all-in ditanggung developer | `allin_engine.py:465` (+AP bill `approved` langsung) | `comp.gl_expense` (6-1700) | `comp.gl_ap` (2-1100) | `ap.sales_cost:<bill>` | `ap_bill` / bill | now | deal | K |
| 16 | Giro diterima | `pdc_engine.py:68` | `1-1350` | `2-1480` (kontra) | `pdc.receive:<id>` | `pdc` | tgl terima | – | H |
| 17 | Giro kliring / tolak / batal | `pdc_engine.py:88` (balik) + `apply_receipt` (→ baris 1) atau `:118` | `2-1480`; (no-deal: rekening bank pilihan) | `1-1350`; (no-deal: `2-1450`) | `pdc.<event>:<id>` | `pdc` | tgl kliring / now | – | H |
| 18 | Tagihan AP disetujui | `finance_ap.approve_ap_bill:43` → `ap.approved` → `_gl_ap_approved:331` | tipe PO: material→`1-1400`; general→`6-1300`; subkon/tanpa PO/tipe lain→`1-1600` (didahului pelunasan akrual `2-1700`) | `2-1100`(net) + `2-1200`(retensi) + potongan: advance→`1-1800`, material→`1-1400`, penalty/other→`4-1200` | `ev:` | `ap_bill` / bill | now | tak ada (bill punya project_id, jurnal tidak) | H (`DEDUCTION_GL` `reference_p48.py:185`) |
| 19 | Bayar AP (± potong PPh) | `pay_ap_bill:46` → `ap.paid` → `:365` | `2-1100`(bruto) | kas*(neto, boleh pilih rekening) + `2-1300`(PPh dipotong) | `ev:` | `ap_bill` / bill | now | – | H |
| 20 | Uang muka subkon dibayar | `subcon_finance.py:87` | `1-1800` | `1-1200`→bank default | `subcon_advance_paid:<id>` | `subcon_advance` | now | – | H |
| 21 | Pencairan retensi subkon | `subcon_finance.py:480` (+AP bill `approved`) | `2-1200` | `2-1100` | `retention_released:<id>` | `subcon_retention` | now | – | H |
| 22 | Komisi disetujui / dibayar | `finance_engine.py:802,827` → `:386,:400` | `6-1100` / `2-1600` | `2-1600` / kas* | `ev:` | `commission` / com id (approved: lookup by `deal_id`, bukan id) | now | – | H |
| 23 | Marketing fee disetujui / dibayar | `marketing_fee.py:155,198` | `6-1200` / `2-1500` | `2-1500`(net)+`2-1300`(PPh) / `cash_account(source)`→default | `mfee.approve:<id>`, `mfee.pay:<pid>` | `marketing_fee`, `marketing_fee_payment` | now | – | H |
| 24 | Pajak: akrual lalu setor | `tax_router.update_record` → `gl_engine.post_tax_accrual:454`, `post_tax_payment:468` | `6-1400` (SEMUA jenis: PPN keluaran, PPh final, BPHTB) / `2-1300` | `2-1300` / kas* | `tax.accrue:<rec>`, `tax.setor:<rec>` | `tax_accrual`, `tax_setor` / rec | akrual: now; setor: `paid_date` | – | H |
| 25 | Kas bon (modul Kas Bon) cair / pertanggungjawaban | `petty_cash.py:137,197` | `1-1500` / akun kategori (`CASHBON_ACCOUNT`: 6-1300, 6-1200, **1-1600**) + kas bila sisa | kas* / `1-1500` (+kas bila kurang) | `cashbon.disburse:<id>`, `cashbon.settle:<id>` | `cash_advance` | now | – | H (`reference_p27.py:30`) |
| 26 | Pengajuan Dana cair / kas bon / pertanggungjawaban | `fund_requests.py:188,226` | `1-1500` (type advance) atau akun kategori (default `6-1300`, `biaya_proyek`/`upah_harian`→`1-1600`); vendor_payment+AP → baris 19 | kas* | `fund_request.disburse:<id>`, `.settle:<id>` | `fund_request` | now | – | H |
| 27 | Kas kecil: pengeluaran & batal | `petty_expense.py:140,172` | akun kategori / kas kecil | kas kecil / akun kategori | `petty.expense:<id>`, `petty.expense.void:<id>` | `petty_expense` | tgl input (`auto=False`) | proyek disimpan di dokumen, TIDAK di jurnal | H |
| 28 | Aset tetap: perolehan | `fixed_assets.py:156` | `1-2100` (satu akun untuk semua kategori, termasuk TANAH) | kas→`1-1100` / bank→`1-1200` / utang→`2-1100` (+AP bill `approved`) | `asset.acquire:<id>` | `fixed_asset` | tgl perolehan | – (aset punya project_id) | H |
| 29 | Penyusutan bulanan | `fixed_assets.py:198` | `6-1500` (semua aset, termasuk alat proyek) | `1-2200` | `asset.depr:<id>:<periode>` | `asset_depreciation` | akhir periode / now | – | H |
| 30 | Pelepasan aset | `fixed_assets.py:254` | kas(source)+`1-2200`+`6-1800`(rugi) | `1-2100`+`4-1300`(laba) | `asset.dispose:<id>` | `fixed_asset` | tgl input | – | H |
| 31 | Pinjaman cair / angsuran | `loans.py:115,165` | kas(source) neto + `6-1600`(provisi) / `2-2100`+`6-1600`(bunga) | `2-2100` / kas(source) | `loan.activate:<id>`, `loan.pay:<pid>` | `loan`, `loan_payment` | tgl input | – | H |
| 32 | Upah harian dibayar | `labor_engine.py:370` | `1-1600` | `1-1200`→bank default | `labor.paid:<id>` | `labor_payroll` | `period_end` (`auto=False`) | proyek di dokumen | H |
| 33 | Transfer internal (disetujui) | `cash_bank.py:437` | sub-akun tujuan (+`6-1600` biaya) | sub-akun asal | `cashbank.transfer:<id>` | `cash_transfer` | tgl input | – | H (`TRANSFER_FEE_ACCOUNT`) |
| 34 | Saldo awal rekening/kas | `cash_bank.py:76` | sub-akun | `3-1950` | `cashbank.opening:<id>` | `cash_opening` | `opening_date`/created | – | H |
| 35 | Biaya bank / jasa giro (rekonsiliasi) | `bank_match.py:227,234` | `6-1600` / rekening | rekening / `4-1200` | `bank.fee:<txn>`, `bank.interest:<txn>` | `bank_txn` | tgl mutasi | – | H |
| 36 | Pembalikan pencocokan bank (non-AR) | `bank_match.py:359` | cermin | cermin | `bank.unmatch:<match>` | `bank_txn_void` | tgl jurnal asal | – | – |
| 37 | Jurnal penutup tahun / balik | `closing_engine.py:478,512` | pendapatan / (rugi→`3-1900`) | beban / (laba→`3-1900`) | `year_close:<org>:<thn>`, `year_reopen:<org>:<thn>` | `year_closing` | 31 Des (`allow_closed`) | – | H (`RETAINED_EARNINGS`) |
| 38 | Jurnal manual | `routers/gl_router.py:76-91` | bebas | bebas | **tidak ada** | `manual` / tanpa id | input user (tak divalidasi) | tak ada | bebas (akun kendali boleh) |
| 39 | Seed demo | `seed.py:725-745`, `seed_phase19.py:28` | – | – | `opening:seed`, `seed:*` | – | – | – | – |

Catatan penting dari matriks:
1. **Semua** akun pada kolom Akun bernilai H kecuali baris 12 dan 15 (komponen biaya all-in). Tidak ada tabel pemetaan peristiwa→akun yang bisa diubah user (bukti: `grep` — ±25 file memuat literal kode akun; Pusat Konfigurasi 129 kunci/22 grup tidak ada satu pun soal akun; lihat gl-5).
2. Hanya 6 dari 39 jenis jurnal memakai `source_deal_id`/`source_id` yang bisa ditelusuri ke deal sekaligus; titipan (2-4), revrec (6), void (9) tidak punya `source_deal_id` (terbukti `deposit`: 0 dari 6, `revrec`: 0 dari 3).
3. Penerimaan, bayar AP, bayar komisi, setor pajak (event outbox) **tidak bisa diberi tanggal transaksi**: jurnal selalu `now` (`apply_receipt`/`pay_ap_bill`/`pay_commission` tidak punya parameter tanggal).
4. Tidak ada satu pun jurnal untuk: pemakaian/pengeluaran material (stok keluar/opname/retur), penerimaan barang (GRN), nota kredit/debit AP, PPN masukan/keluaran terpisah, akrual bunga pinjaman, kapitalisasi biaya pinjaman, pengakuan biaya komisi sesuai PSAK 72 (biaya perolehan kontrak), pembalikan komisi saat batal (lihat gl-4).

## 3. Peta SSOT per angka

Legenda "Tie-out otomatis": R = `finance_audit.reconcile` (`/finance/reconcile`, lampu di dasbor Keuangan); C = `closing_engine._check_tieout` (menahan tutup bulan). Tidak ada = tidak ada penjaga.

| Angka (akun GL) | Sumber kebenaran operasional (subledger) | Penjaga tie-out | Dua sumber yang bisa BERBEDA — bukti |
|---|---|---|---|
| Piutang usaha `1-1300` | `ar_invoices.items[]` (termin, add-on, denda) — **BUKAN** di GL sebelum BAST; GL hanya memuat piutang denda + sisa AR saat BAST | **tidak ada** | GL `1-1300`=Rp 772.950.777 vs `Σ ar_invoices.outstanding`=Rp 1.418.765.433 (definisi berbeda) dan **tidak pernah turun saat pembeli membayar setelah BAST** (GL-01) |
| Kewajiban kontrak `2-1400` | `contract_liabilities.balance` (tiap penerimaan `$inc`) | R, C | **TIGA angka**: GL 1.432.474.134; `reconcile` (hanya `recognized≠true`) 1.255.000.000; dasbor `/finance/summary.contract_liability` (semua) 1.532.469.134 (TERBUKTI) |
| Titipan pelanggan `2-1450` | `customer_deposits.balance` | R | cocok sampai hapus-paksa kuitansi berkelebihan bayar (jurnal titipan tidak ikut terhapus — [DARI-KODE]) |
| Titipan biaya `2-1470` | `cost_invoices/cost_receipts/cost_disbursements` (ledger all-in) | **tidak ada** | – |
| Utang usaha `2-1100` | `ap_invoices` (`net−paid`, status approved/partial/paid) | R, C | selisih Rp 5.004.821 pada instance uji: Rp 4.821 dari jurnal manual saya ke 2-1100 + Rp 5.000.000 dari tagihan retensi 150% yang event GL-nya `failed` (TERBUKTI) |
| Retensi `2-1200` | `ap_invoices.retention_held` (tak dilepas) + `subcon_retentions` | R, C | selisih −Rp 15.000.000 (tagihan retensi>100%, jurnal gagal) |
| Retensi piutang `1-1700` | – | – | akun TIDAK PERNAH dipakai kode (kode literal tak ada) |
| WIP `1-1600` | **tidak ada subledger nilai**; RAB per unit (`rab_engine`) hanya dipakai untuk HPP saat BAST | **tidak ada** (hanya tampil di `hpp_per_unit`) | saldo org-wide: BAST proyek A mengosongkan WIP proyek B (BAST uji 595 jt memakan seluruh WIP) |
| Akrual HPP `2-1700` | – | tidak ada | Rp 829.000.000 pada instance uji; dilunasi urut oleh tagihan AP **mana pun** (AP uji Rp 100 jt langsung mendebet 2-1700, bukan 1-1600) |
| Persediaan `1-1400` | **tidak ada nilai** (`material_txns` hanya kuantitas) | tidak ada | naik hanya dari AP PO-material; stok keluar/opname/retur tidak berjurnal |
| Kas & bank | `bank_accounts` (master) + `bank_transactions` (mutasi bank) | rekonsiliasi `bank_recon` (per rekening) | `/cash-bank/position` (semua tanggal, hanya rekening aktif) vs neraca `gl_reports.balance_sheet` (≤ as-of) vs `/gl/accounts`; TERBUKTI beda (lihat gl-3) |
| Utang komisi `2-1600` / beban `6-1100` | `commissions.status` | R | komisi dipicu lewat `deal_id` (handler cari komisi pertama per deal); seed memuat 3 komisi pada 1 deal |
| Utang marketing fee `2-1500` | `marketing_fees` (net−paid) | **tidak ada** | – |
| Kas bon `1-1500` | **DUA** subledger: `cash_advances` (Kas Bon) dan `fund_requests(type=advance)` | **tidak ada** | GL Rp 12.500.000 vs ringkasan Kas Bon (hanya `cash_advances`) Rp 7.500.000 (TERBUKTI) |
| Uang muka subkon `1-1800` | `subcon_advances.outstanding` | C | amortisasi subledger terjadi saat tagihan DITEMPELI potongan (`attach_deductions`) — jurnal baru saat tagihan DISETUJUI (jeda; jika klaim ditolak/tak disetujui → beda) [DARI-KODE] |
| Aset tetap `1-2100`/`1-2200` | `fixed_assets` | **tidak ada** | cocok pada uji (3.342.500.000 / 33.375.004) |
| Pinjaman `2-2100` | `loans.outstanding_principal` | **tidak ada** | cocok pada uji |
| Utang pajak `2-1300` | **TIGA** sumber: `tax_records` (status), PPh dipotong saat bayar AP, PPh dipotong marketing fee | **tidak ada** | status `paid→pending` diizinkan tanpa jurnal balik (TERBUKTI); tax_records tidak mencatat PPh potongan |
| Refund `2-1460` | `cancellations.settlement.payable_total − refund_paid_total` | **tidak ada** | cocok pada uji |
| Denda `4-1400` | `ar_invoices.items[is_penalty]` | **tidak ada** | pendapatan denda DOBEL setelah BAST (GL-02) |
| Giro `1-1350`/`2-1480` | `pdc_instruments(status=received)` | **tidak ada** | cocok pada uji |
| BPHTB titipan `2-1470` vs `tax_records(bphtb)` | dua mekanisme untuk satu pajak: titipan pembeli (all-in) vs catatan pajak → `6-1400` | **tidak ada** | risiko dobel (GL-04) |
| Pendapatan `4-1100` / HPP `5-1100` | `revenue_recognitions` | (tidak ada) | cocok, tetapi pendapatan = `ar.total` (ikut denda/add-on) |
| Laba tahun berjalan / `3-1900` | – | – | tutup-buka-tutup tahun meninggalkan laba berjalan terbuka (GL-03) |

Penjaga tie-out yang ada hanya menutup 5 (R) + 4 (C) akun dari ≥ 25 akun yang bergerak; tidak per periode (C memakai saldo kumulatif walau teksnya "sampai akhir periode", `closing_engine.py:215`).

## 4. Akun CoA ↔ pemakaian kode

* STANDARD_COA (`gl_engine.py:30-86`) = 39 akun (+ sub-akun kas/bank yang dibuat otomatis per rekening: 43 akun pada instance uji). Akun yang TIDAK pernah diposting oleh kode alur normal: `1-1700` (Piutang Retensi), `3-1100` (hanya seed), `1-1300` hanya oleh denda & BAST, `2-1480/1-1350` hanya giro.
* Kode akun yang dipakai kode tetapi bergantung pada data: `comp.gl_expense/gl_liability/gl_ap` (komponen biaya all-in) — backend tidak memvalidasi keberadaan/tipe akun (`routers/allin_router.py:132`); `gl_account` pada add-on/komponen harga tampil di UI tetapi **tidak dibaca oleh satu pun jurnal** ([DARI-KODE]: `grep gl_account` hanya `quotation_engine.py:89` (salin) dan budget).
* Akun yang bisa diubah/dihapus user lewat layar Bagan Akun: tambah (kode bebas), ubah nama/tipe (tipe terkunci bila sudah dipakai), nonaktifkan; tidak ada hapus. Perubahan itu tidak berdampak ke posting karena `post_journal` tidak membaca `is_active` (TERBUKTI, lihat GL-13).
