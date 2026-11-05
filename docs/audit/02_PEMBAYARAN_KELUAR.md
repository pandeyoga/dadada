# Audit Pembayaran KELUAR / Pengeluaran Kas — SIPRO/Estora (instance #3: UI :3003, API :8003, DB sipro_out)

Auditor: stream "pembayaran-keluar". Tanggal uji: 2026-11-05/06. Repo read-only; seluruh data uji berawalan `AUDIT-`.
Folder bukti: (skrip uji tidak disertakan di repo) (skrip `t_*.py`, helper `h.py`), screenshot di `img/keluar/`.

## Ringkasan eksekutif
1. **Semua jalur uang keluar yang diuji bisa dibayar ganda** bila dua request datang bersamaan (klik ganda lintas tab, dua pengguna, retry). Pola sama di 17 jalur: baca status → tulis tanpa compare-and-set, dan `source_event` jurnal tidak unik (find-then-insert). Contoh terukur: tagihan AP net Rp 9,5 jt dibayar 2 request paralel → bank berkurang **Rp 38 jt** (4 jurnal) sementara subledger mencatat Rp 9,5 jt.
2. **Dispatcher event GL tidak eksklusif**: tiap `ap.approved/ap.paid/commission.*` diproses 2x bila dua request overlap → jurnal ganda walau dokumen berbeda (tagihan Rp 3 jt di-approve paralel → 2-1100 naik Rp 12 jt). Kontrol bawaan `/finance/reconcile` dan banner Dashboard Keuangan mendeteksi, tetapi tidak mencegah.
3. **Komisi bisa dibayar berulang**: `approve` pada komisi berstatus `paid` memundurkan status ke `approved` + terbit akrual baru; `pay` lagi → Rp 21,25 jt dibukukan & dikeluarkan 2x untuk 1 komisi (dan tak ada tombol Bayar komisi di UI sama sekali).
4. **Termin subkon & pencairan retensi**: approve paralel melahirkan 2 tagihan AP + 2 baris retensi; release retensi paralel (tanpa client_ref) melahirkan 2 tagihan AP.
5. **Tidak ada cek saldo kas/bank** di hampir semua pengeluaran (hanya transfer & kas kecil yang cek): bank operasional terbukti −Rp 92 M; UI hanya memperingatkan sesudah kejadian.
6. **Pemisahan tugas bocor**: satu akun `finance` dapat membuat PO (vendor fiktif) → menyetujui → GRN → tagihan → approve → bayar Rp 25 jt; AP Rp 600 jt di-approve+dibayar satu orang; pemohon dapat mencairkan pengajuannya sendiri (UI & API).
7. **Tidak ada pembalikan/void** untuk tagihan/pembayaran AP, termin, komisi, fee, angsuran, upah, refund; status pajak bisa dimundurkan dari UI tanpa membalik jurnal.
8. Data uji (retensi −50%/150%, uang muka diangsur 2x, dll.) membuktikan validasi nilai longgar → jurnal gagal, saldo uang muka negatif, tagihan bernilai negatif.
9. Banyak hal benar (lihat "Terverifikasi OK"): validasi lebih-bayar sekuensial, RBAC 403, gerbang retensi, tie-out penutupan periode, tombol UI memblokir klik ganda dan self-approve.

## Cakupan (apa yang diuji)
Inventarisasi jalur uang keluar dari kode+OpenAPI (±35 endpoint mutasi), lalu diuji API (sekuensial + paralel 2–4 request via thread) dan UI Playwright (peran finance, finlead=finance_manager, pm, site, sales; 1440x900):
- AP: buat/approve/bayar/bayar-dengan-PPh, retensi manual, 3-way match PO/GRN/tagihan, retur.
- Subkon: SPK, termin lump-sum, uang muka, potongan, retensi (gerbang, waive, request, release).
- Komisi sales, marketing fee agen/mitra.
- Kas bon (modul KB) & Pengajuan Keuangan (PGJ: expense/reimbursement/vendor_payment/advance), kas kecil imprest + void, transfer internal.
- Upah harian (absensi→rekap→bayar), pinjaman bank (aktivasi, angsuran), aset tetap (akuisisi), pajak (setor catatan pajak, bukti potong), refund pembatalan, refund titipan.
- Jalur tak disebut yang ditemukan: **penyaluran titipan biaya ke notaris/BPN** (`/contracts/{id}/cost-disbursements`), **beban developer all-in** (`cost-expenses`), **jurnal manual ke bank** (`/gl/journals`), refund booking fee, sweeper retensi AP.
- Kunci periode GL / kas, rekening sumber, bukti BKK.
Detail eksekusi tiap temuan ada di skrip `out3/t_*.py`.

## Temuan (urut severity)

### [PK-01] [Severity: Kritis] Dispatcher event GL tidak eksklusif + idempotensi jurnal tidak atomik → jurnal ganda
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI] (banner)
- Lokasi: `backend/engine.py:637-653` (`dispatch_pending` membaca semua event `pending` tanpa klaim/lock lalu menjalankan handler), `backend/gl_engine.py:127-131` (idempotensi = find lalu insert), index `journal_entries(org_id, source_event)` **tidak unik** (`backend/seed_indexes.py:128`; hanya `entry_no` unik di `indexes.py:35`). Dipanggil sinkron di `finance_ap.py:44,107` dan terjadwal 8 dtk (`engine.py` scheduler).
- Reproduksi: `out3/t_ap1.py`: (a) buat tagihan AP Rp 10 jt retensi 5%, approve, lalu 2 request paralel `POST /finance/ap/bills/{id}/pay {amount:9500000}`. (b) `t_apapp.py`: 2 request paralel `approve` satu tagihan Rp 3 jt. (c) `t_ap2.py`: dua tagihan BERBEDA dibayar bersamaan oleh dua user.
- Hasil nyata: (a) 2 event `ap.paid`, **4 jurnal** JV/2026/00049-52 (masing-masing event diproses 2x, `source_event` kembar); 2-1100 −38.000.000, bank 1-1201 −38.000.000, padahal tagihan net 9.500.000. (b) 2 event, 4 jurnal, 2-1100 **+12.000.000** (harusnya +3.000.000). (c) Rp 6.000.000 keluar untuk 2×2.000.000. Akhir sesi: 15 jurnal dengan `source_event` kembar; `/finance/reconcile`: 2-1100 GL 704.700.000 vs subledger 652.585.000; Dashboard Keuangan menampilkan banner merah "2 akun kendali SELISIH dengan subledger" (`shots/.../finance-home.png`, `finance-banner-after.png`).
- Seharusnya: satu event → satu jurnal, apa pun jumlah request bersamaan.
- Dampak: kas/utang/beban di buku besar melenceng dari subledger; kas dikeluarkan secara pembukuan berkali-kali; laporan keuangan & penutupan periode (ditahan 409) macet. Berlaku untuk semua jalur berbasis event (AP approve/bayar, komisi, titipan, penerimaan).
- Akar masalah & arah: tidak ada klaim atomik event (`find_one_and_update status pending→processing`) dan tidak ada unique index parsial pada `source_event`; perbaiki dua-duanya (unique index + upsert/duplicate-key sebagai idempotensi).

### [PK-02] [Severity: Kritis] Pembayaran/pencairan ganda pada klik ganda/request paralel — di hampir seluruh jalur uang keluar
- Label bukti: [TERBUKTI-API] (UI tombol utama memblokir klik ganda satu tab — lihat OK; celah ada di lintas tab/dua pengguna/retry/API langsung)
- Pola kode: baca dokumen → cek status/sisa dari salinan basi → tulis (`update_one` tanpa filter status/`$inc` bersyarat). Tidak ada kunci idempotensi server (hanya opsional `client_ref` di retensi & refund, itupun tidak atomik).
- Reproduksi tiap jalur: skrip `out3/t_*.py` (2 request paralel pada dokumen yang sama; angka sebelum→sesudah):

| Jalur | Seharusnya keluar | Nyata | Bukti subledger vs GL |
|---|---|---|---|
| Bayar tagihan AP (`finance_ap.py:51-113`) | 9,5 jt | **38 jt** (4 jurnal) | `paid`=9,5 jt (lost update), `payments_out`=2 baris, `paid_consistent:false` |
| Cairkan pengajuan non-AP (`fund_requests.py:158-214`, PGJ/2026/0001, 5 jt) | 5 jt | **10 jt** (2 jurnal) | status 1x, history `disbursed` 2x |
| Cairkan pengajuan vendor_payment ke tagihan AP (PGJ/2026/0007, 4 jt) | 4 jt | **16 jt** (4 jurnal, 2 payments_out) | tagihan `paid`=4 jt |
| Kas bon KB/2026/0003 cair (`petty_cash.py:121-158`, 3 jt) | 3 jt | **6 jt**; 1-1500 +6 jt | `outstanding`=3 jt |
| Kas bon settle paralel (`petty_cash.py:186-218`, realisasi 4 jt, cair 3 jt) | WIP +4 jt, bank −1 jt | **WIP +8 jt, bank −2 jt, 1-1500 −6 jt** | `expense_total`=4 jt |
| Marketing fee MF/2026/0003 (`marketing_fee.py:184`, net 9,75 jt) | 9,75 jt | **19,5 jt**; 2-1500 jadi −9,75 jt | `paid_amount`=9,75 jt, `payments_out` 2 |
| Angsuran pinjaman PBY/2026/0002 (`loans.py:134`) angsuran-1 10.661.855 | 10,66 jt | **21,32 jt** | jadwal menunjukkan lunas 1x |
| Bayar rekap upah UPH/2026/0001 (`labor_engine.py:361`) 1.252.500 | 1,25 jt | **2,505 jt** (2 jurnal) | status `paid` 1x |
| Refund pembatalan BTL/2026/0001 (`cancellation_engine.py:532`) | — | 4 pembayaran @100 jt = **400 jt**, **bahkan dengan `client_ref` sama** | `refund_paid_total` hanya 200 jt |
| Refund titipan pembeli (`finance_engine.py:714`, titipan 2 jt) | 2 jt | **4 jt**; saldo titipan **−2 jt** | `customer_deposits.balance`=−2.000.000 |
| Setor pajak PPN 102 jt (`tax_router.py:60`) | 102 jt | **4 jurnal**; 6-1400 +204 jt | NTPN sama |
| Uang muka subkon UMK (`subcon_finance.py:82`, 20 jt) | 20 jt | 1 jurnal (kebetulan) tapi **`payments_out` 2 baris (40 jt)** | riwayat bayar ≠ GL |
| Retur/GRN paralel (`procurement_router.py:230`, PO 100 sak) | 100 | stok +200, PO "diterima 100", 2 GRN | |
| Tagihan PO paralel (`procurement_router.py:327`, PO 7 jt) | 7 jt | 2 tagihan @7 jt (14 jt) | `billed_value`=7 jt |
| Void kas kecil (`petty_expense.py:164`, expense 600 rb) | +600 rb | void 2x: kas **+1,2 jt** | saldo 1 jt→−0,8 jt→+0,4 jt |
| Cek saldo kas kecil (`petty_expense.py:123-126`) | tolak setelah saldo habis | 3×600 rb lolos dari saldo 1 jt → **saldo −800.000** | |
| Uang muka subkon batas 30% (`subcon_finance.py:42-48`) | maks 30 jt | 4 pengajuan paralel → **total 47 jt** | |
- Dampak bisnis: pengeluaran ganda nyata (kas berkurang berkali-kali), subledger tidak mencerminkan; utang ke penerima tampak lunas padahal sudah kelebihan bayar; saldo titipan/kas negatif.
- Akar & arah: transisi status harus `update_one({id, status: <dari>}, ...)` dengan cek `matched_count`; pembayaran bertahap pakai `$inc` bersyarat (`outstanding >= amount`); idempotency-key wajib di server untuk semua endpoint bayar; unique index `source_event`.

### [PK-03] [Severity: Kritis] Komisi: `approve` pada komisi yang sudah `paid` memundurkan status dan memicu akrual + pembayaran baru
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI] (daftar)
- Lokasi: `backend/finance_engine.py:793-806` (`approve_commission` hanya `return com` bila status `approved`; status `paid` jatuh ke `$set status approved` + `emit commission.approved`), `routers/commissions_router.py:72-79`; handler `gl_engine.py:386-409`.
- Reproduksi (`out3/t_com2.py`): `compute` komisi Rp 21.250.000 → approve → pay → approve LAGI (200, status kembali `approved`) → pay LAGI (200, `paid`).
- Hasil: jurnal JV/2026/00064 (akrual), 00065 (bayar), **00066 (akrual lagi), 00067 (bayar lagi)**; 6-1100 +42,5 jt, bank −42,5 jt untuk satu komisi 21,25 jt; subledger hanya 1 komisi `paid`. Siklus bisa diulang tanpa batas oleh siapa pun berizin `commissions:approve`.
- Dampak: kebocoran kas berulang yang sulit dilacak (subledger bersih), beban komisi digelembungkan.
- Perbaikan: tolak approve bila status ≠ `pending`; kunci `commission.approved`/`paid` per komisi.

### [PK-04] [Severity: Kritis] Persetujuan termin subkon paralel → 2 tagihan AP + 2 retensi
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/subcon_claims_router.py:305-358` (`approve_claim`: cek status → `create_ap_bill` → `approve_ap_bill` → `register_retention` idempoten per **tagihan**, bukan per termin).
- Reproduksi (`out3/t_sub2.py`): SPK AUDIT-SPK-1 (Rp 100 jt, retensi 5%), termin 50% diajukan site, di-opname PM, lalu 2 request paralel `approve` oleh finance.
- Hasil: 2 tagihan AP @gross 50 jt/net 47,5 jt (status `approved`), 2 retensi RET/2026/0003 & 0004 (2,5 jt), klaim hanya mencatat 1 tagihan; GL 2-1100 +190 jt, 2-1200 +10 jt, 1-1600 +200 jt (dengan efek PK-01). Layar Keuangan › Utang menampilkan dua tagihan "Termin TRM/2026/0002" siap bayar (`shots/.../ap-tab.png`).
- Dampak: subkon dapat dibayar 2x untuk termin yang sama; retensi ganda.
- Perbaikan: transisi status atomik di klaim (`submitted/verified → approving`), unique index `ap_invoices.claim_id`.

### [PK-05] [Severity: Tinggi] Pencairan retensi paralel tanpa `client_ref` → 2 tagihan AP; idempotensi hanya opsional
- Label bukti: [TERBUKTI-API] (UI mengirim `client_ref` per dialog: `components/subcon/RetentionsPanel.js:265`, jadi jalur UI terlindungi; tidak diuji paralel dengan `client_ref` sama)
- Lokasi: `subcon_finance.py:452-495`, `routers/subcon_finance_router.py:243-281`.
- Reproduksi (`out3/t_ret.py`, `t_ret2.py`): waive (finlead) → ajukan (pm) → 2 request paralel `release` oleh finlead tanpa `client_ref`.
- Hasil: 2 tagihan AP "Pencairan retensi RET/2026/0003" @2,5 jt (masing-masing `approved`), 2 jurnal; 2-1200 turun 5 jt untuk retensi 2,5 jt (UI AP menampilkan keduanya).
- Perbaikan: `client_ref` wajib atau transisi `release_requested → released` atomik, unique `retention_id` pada tagihan pencairan.

### [PK-06] [Severity: Tinggi] Hampir semua pengeluaran tidak memeriksa saldo kas/bank → saldo negatif
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: tidak ada cek saldo di `finance_ap.py:51`, `fund_requests.py:158`, `petty_cash.py:121`, `marketing_fee.py:184`, `loans.py:134`, `labor_engine.py:361`, `subcon_finance.py:82`, `fixed_assets.py:114`, `cancellation_engine.py:532`, `finance_engine.pay_commission`, `allin_engine.py:421`; cek ada hanya di `cash_bank.py:403-406` (saat membuat transfer; tidak di approve) dan `petty_expense.py:123`.
- Reproduksi: (a) `t_ap3.py` bayar tagihan Rp 3.333.333 dari "Kas Kecil Site" (saldo 0) → 200, saldo −3.333.333. (b) `t_fa.py` akuisisi aset Rp 99 miliar dari bank → 200; Rekening Operasional **−Rp 92,0 miliar** (Kas & Bank › Posisi Kas: banner "Saldo buku negatif … Uang keluar dicatat tanpa dana masuk", `shots/.../cashbank-home.png`).
- Dampak: uang keluar fiktif melebihi dana nyata tidak tertahan; kontrol baru terlihat setelah terjadi.
- Perbaikan: guard saldo terpusat di `post_journal` untuk sub-akun kas/bank (atau kebijakan eksplisit "boleh minus" + otorisasi).

### [PK-07] [Severity: Tinggi] Pemisahan tugas (maker-checker) bocor; tidak ada batas wewenang bertingkat
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Bukti per jalur:
  1. **P2P penuh satu akun**: `t_p2p.py` — `finance@sipro.co.id` membuat PO vendor fiktif "AUDIT PT Fiktif Tanpa Master" (Rp 25 jt, tipe `general`) → approve PO sendiri → GRN sendiri → tagihan (3-way "matched" karena GRN buatan sendiri) → approve tagihan → bayar: semua 200; bank −25 jt. `procurement_router.py:87,177,230,327`, `ap_router.py:38,87,97` tidak membandingkan `created_by` dengan approver/pembayar.
  2. **Approve & bayar oleh satu orang**: `approve_ap_bill` (`finance_ap.py:33`) tanpa cek pembuat; `finance:approve` dipakai untuk approve DAN bayar (`ap_router.py:87,97`); komisi approve & pay satu izin `commissions:approve`; finlead memutuskan lalu membayar uang muka subkon (`t_adv.py`, izin `manage`+`approve` sama-sama dimiliki).
  3. **Tanpa batas nilai**: uji inline (skrip tidak disimpan) membuat tagihan AP Rp 600 jt, approve + bayar oleh `finance` sendirian (200 dan 200); satu-satunya ambang tertinggi hanya PO > Rp 500 jt (`procurement_router.py:30`) — dilewati lewat tagihan AP manual tanpa PO.
  4. **Pemohon mencairkan pengajuannya sendiri**: [UI] finance membuat PGJ/2026/0013 (disetujui finlead), tombol "Cairkan" tampil & berfungsi untuk pemohon sendiri; bukti `fundreq-after-disburse.png`; kode `FundRequestsPage.js:184-185` (tidak memeriksa `isMine`) dan `fund_requests.py:158` (tidak memeriksa `requested_by`). (Self-approve DIBLOKIR — lihat OK.)
  5. **Satu langkah tanpa approver**: penyaluran titipan biaya ke notaris/BPN (`allin_engine.py:421`, `allin_router.py:258`, izin `finance:create`) langsung mengeluarkan kas; refund titipan (`ar_router.py:122`, `finance:update`) tanpa approver; jurnal manual `Cr` bank/escrow oleh `finance` (`gl_router.py:80`; `t_gl.py` mengambil Rp 1.234.567 dari Rekening Escrow, 200).
- Dampak: risiko fraud internal/kesalahan tanpa kontrol kedua.
- Perbaikan: wajibkan approver ≠ pembuat ≠ pembayar; matriks batas nilai; approval untuk disbursement notaris/refund titipan/jurnal manual ke kas.

### [PK-08] [Severity: Tinggi] `retention_pct` tanpa batas → tagihan bernilai negatif / jurnal gagal / tagihan "disetujui" tanpa jurnal
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: `finance_ap.py:13-15` (`retention_held = round(claimed*pct/100)`), `models.py:439-445` (`retention_pct: float` tanpa batas), `models_procurement.py:171` (default 5%), `ApPanel.js:160-166` (`<input type=number>` tanpa min/max), SPK `subcon_router.py:298` (retensi SPK bebas).
- Reproduksi: `t_ap3.py`/`t_ap4.py`: tagihan Rp 1 jt retensi 150% → net −500.000; retensi −50% → net 1.500.000 (> klaim). UI (`ui_ap4.js`): tagihan Rp 1.230.000 retensi 150 → baris "Sisa −Rp 615.000", Setujui → toast sukses "net Rp −615,000 siap dibayar" dan muncul tombol Bayar (`shots/.../ap-ret150-after-approve.png`). Event `ap.approved` gagal ("Nilai debit/kredit tidak boleh negatif" / "Jurnal tidak seimbang: debit Rp 1,000,000 != kredit Rp 1,500,000") → tagihan `approved` tanpa jurnal; 3 event `failed` di akhir uji; `/finance/reconcile` 2-1100 gagal. Tagihan retensi −50% (net 1,5 jt > nilai pekerjaan 1 jt) bisa dibayar penuh.
- Dampak: vendor dibayar lebih dari klaim; subledger ≠ GL; banner "jurnal otomatis GAGAL diposting".
- Perbaikan: validasi 0 ≤ retensi ≤ 100 (Pydantic `ge/le`), approve tolak bila jurnal tidak bisa dibentuk (post sinkron, bukan event diam-diam).

### [PK-09] [Severity: Tinggi] Tidak ada pembalikan/void/kredit-note untuk pengeluaran; pesan retur menunjuk fitur yang tidak ada; status pajak bisa dimundurkan tanpa jurnal balik
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: tidak ada endpoint cancel/void untuk tagihan/pembayaran AP (`POST /finance/ap/bills/{id}/void|cancel|reverse` → 404, `DELETE` → 405), termin disetujui, komisi dibayar, fee dibayar, angsuran, upah, refund, uang muka, kas bon cair, pengajuan cair. `procurement_extra.py:154-158` memberi pesan "Terbitkan nota koreksi/kredit atas tagihan vendor lebih dulu" — tidak ada fitur itu. Hanya ada void kas kecil, unmatch bank, transfer reject (pending).
- Tax: `tax_router.py:60-95`, UI Catatan Pajak › Status: `paid` → "Menunggu" disimpan tanpa konfirmasi; baris tampil "Belum dilaporkan" tetapi tetap menampilkan NTPN-2 dan JV/2026/00110; GL tidak berubah (2-1300 3.550.000, bank Escrow 227.515.433 sebelum=sesudah) — [UI] `ui_tax2.js`, `shots/.../tax-after-revert.png`.
- Dampak: kesalahan input/duplikat (PK-02) tidak dapat dibetulkan secara sah di sistem; jejak kas ≠ status dokumen.
- Perbaikan: dokumen pembalik berjurnal dengan SoD; larang mundur status yang sudah berjurnal.

### [PK-10] [Severity: Tinggi] Uang muka subkon bisa diangsur melebihi nilainya (dua potongan pending) → saldo 1-1800 negatif, subkon dipotong lebih
- Label bukti: [TERBUKTI-API]
- Lokasi: `subcon_finance.py:123-151` (cek `amount > outstanding` hanya per potongan; potongan pending lain tidak dihitung), `:185-225` (`attach_deductions`, `outstanding = max(0, …)` menutupi selisih).
- Reproduksi (`t_adv2.py`, `t_ded.py`): uang muka 20 jt dibayar; buat 2 potongan `advance` @20 jt (keduanya 200); approve termin 50 jt (retensi 2,5 jt).
- Hasil: potongan total 40 jt, net termin 7,5 jt; uang muka `amortized`=40 jt (> 20 jt), `closed`; GL 1-1800 −40 jt. Subkon kehilangan 20 jt yang bukan utangnya.
- Perbaikan: validasi Σ potongan pending ≤ sisa uang muka; `$inc` bersyarat.

### [PK-11] [Severity: Tinggi] PM dapat mengubah nilai kontrak/retensi/progres SPK langsung → melewati Change Order dan menagih progres yang sama berulang
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/subcon_router.py:298-322` (`update_spk` izin `subcon:update` — PM/site boleh; tak ada cek nilai tertagih untuk `contract_value`/`progress_pct`/`retention_pct` pada SPK lump-sum), `subcon_claims_router.py:98-100`.
- Reproduksi (`t_sub1.py`, `t_sub3.py`): PM mengubah `contract_value` 100 jt→1 miliar (200), `retention_pct` 150; setelah termin 0→50% disetujui PM me-reset `progress_pct` ke 0 lalu termin 0→50% disetujui lagi.
- Hasil: Σ klaim disetujui **150 jt** untuk SPK bernilai 100 jt (cap hanya berlaku pada termin 100%); dua pembayaran untuk 50% pekerjaan yang sama.
- Dampak: kontrol Change Order (disetujui finance) dapat dilewati; pembayaran ganda pekerjaan.
- Perbaikan: field finansial SPK hanya lewat CO/finance; progres lump-sum read-only (turunan klaim).

### [PK-12] [Severity: Tinggi] Komisi/fee tetap diproses untuk deal yang dibatalkan; pembatalan tidak mengubah komisi, fee, atau catatan pajak
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: `finance_engine.py:754-790` (tak cek status deal), `marketing_fee.py:90-130`, `cancellation_engine.py` (tak menyentuh `commissions`/`marketing_fees`/`tax_records`).
- Reproduksi (`t_cxcom.py`): deal 406d2ee0 berstatus `cancelled` → `compute` komisi (200) → approve → pay (200); fee agen dibuat untuk deal itu (200). UI Keuangan › Utang › Komisi menampilkan "A-06 … Dibayar" tanpa tanda deal batal (`komisi-tab.png`). Catatan pajak A-06 (PPN 102 jt dst.) tetap "Belum dilaporkan" (`tax-records.png`).
- Dampak: pembayaran komisi/fee atas penjualan yang sudah batal; tidak ada clawback.
- Perbaikan: blokir compute/approve/pay untuk deal batal; saat pembatalan, batalkan komisi/fee pending & tandai clawback untuk yang dibayar.

### [PK-13] [Severity: Tinggi] Bukti pencairan/kas kecil/reimbursement hanya dipaksa di UI; API menerima tanpa bukti, id palsu, berkas dipakai ulang
- Label bukti: [TERBUKTI-API] (+ UI mewajibkan, [TERBUKTI-UI])
- Lokasi: `fund_requests.py:72-73,199` (`_files` hanya menyaring id yang ada; `payload.attachment_ids` dianggap cukup), `petty_expense.py:121-122` (`if require_proof and not file_ids`), `models_fund_request.py` (`proof_ids` opsional). UI mewajibkan foto: `FundRequestActionDialogs.js:82,88`.
- Reproduksi (`t_proof.py`, `t_pe2.py`, `t_fr.py`): (1) disburse pengajuan via API tanpa `proof_ids` → 200 `settled`, `payment_proofs: []`. (2) satu berkas yang sama dilampirkan sebagai bukti 2 pencairan berbeda → 200 keduanya. (3) reimbursement dengan `attachment_ids:['fake-id-123']` → 200, `attachments: []` (syarat "wajib bukti" terlewati). (4) pengeluaran kas kecil dengan `file_ids:['FAKE-FILE-ID']` → 200 (3 kali). (5) berkas KTP lead milik sales dilampirkan sebagai nota reimbursement pm → diterima.
- Dampak: foto bukti bisa dipalsukan/didaur ulang; kontrol bukti tidak berlaku di luar UI.
- Perbaikan: server memvalidasi id berkas nyata, pemilik/owner_type sesuai, belum terpakai di transaksi lain, dan jumlah ≥ 1.

### [PK-14] [Severity: Tinggi] Jurnal kas keluar terbit walau request gagal; tanggal sembarang menembus kunci periode
- Label bukti: [TERBUKTI-API]
- Lokasi: `loans.py:134-205` (post_journal sebelum update jadwal; `date` bebas), `gl_periods.py:36-60` & `cash_period_lock.py:55-62` (perbandingan string `date[:7]`; tanggal tak berformat tidak pernah dianggap periode tertutup).
- Reproduksi (`t_per.py`): `POST /corp-financing/loans/{id}/pay {installment_no:2, amount:1000, date:'garbage-date'}` → 400 "invalid literal for int() with base 10: 'garb'" — **tetapi** JV/2026/00121 (Dr 6-1600 / Cr 1-1201 Rp 1.000, `date:'garbage-date'`) sudah terbit tanpa catatan angsuran. `date:'2035-01-01'` → 200, jurnal bertanggal 2035. Pada tax paid_date 2020-01-01 (`t_tax.py`) jurnal setor bertanggal 2020.
- Dampak: kas keluar tanpa dokumen subledger; laporan per tanggal/penguncian bisa dihindari; pesan galat menyesatkan.
- Perbaikan: validasi tanggal ISO + rentang (tak boleh masa depan / sebelum tahun buku) sebelum posting; posting dan update subledger dalam satu transaksi.

### [PK-15] [Severity: Tinggi] Tidak ada nomor faktur vendor & deteksi duplikat tagihan; tagihan AP manual melewati 3-way match; vendor/proyek fiktif diterima API
- Label bukti: [TERBUKTI-API]
- Lokasi: `models.py:439-445` & `models_procurement.py:167-177` (tak ada field no. faktur vendor), `ap_router.py:38-45`, `finance_ap.py:10-30`.
- Reproduksi (`t_ap3.py`): dua tagihan identik (vendor, nilai, catatan "AUDIT-INV-0001") → keduanya 200 id berbeda; `vendor:''` → 200; `project_id:'nonexistent'` → 200; tagihan `claimed:99999999999999` → 200. Bill manual tidak punya PO sehingga tidak kena 3-way.
- Dampak: faktur yang sama bisa diinput dan dibayar dua kali tanpa peringatan; vendor tak terdaftar dibayar (UI memakai ReferenceSelect vendor, API tidak).
- Perbaikan: wajib `vendor_invoice_no` + unique (vendor, no); vendor_id master wajib; PO/SPK wajib atau approval khusus untuk "non-PO".

### [PK-16] [Severity: Sedang] Retensi pada tagihan manual/PO (default 5%) tidak punya jalur pencairan; sweeper mati
- Label bukti: [TERBUKTI-API] [DARI-KODE]
- Lokasi: `finance_ap.py:116-133` (sweeper hanya bila `release_due_at` terisi — tidak pernah diisi di kode), `models_procurement.py:171` (default 5% pada tagihan PO), `subcon_finance.py` (retensi hanya untuk termin).
- Bukti: `t_ap...` tagihan manual 500.000 + 2 tagihan lain: `subcon_retentions` tidak punya baris; 2-1200 menampung Rp 16,3 jt yang tidak bisa dibayar lewat UI/API. Bila `release_due_at` diisi lewat impor DB, sweeper menulis `payments_out` TANPA jurnal.
- Dampak: utang retensi vendor material menumpuk tanpa jalan bayar; potensi pembayaran tanpa jurnal.

### [PK-17] [Severity: Sedang] PPh dipotong: tarif/dasar bebas, bukti potong terbit tetapi tidak ada jalur setor PPh potongan
- Label bukti: [TERBUKTI-API] [DARI-KODE]
- Lokasi: `ap_router.py:111-157` (tarif/dasar dari pemanggil; hanya cek `withheld < amount`), `models_p49.py:207-220` (`rate` float tanpa batas), `withholding_engine.py:254-284` (koreksi mengubah nilai bukti tanpa jurnal), tak ada kode yang men-debit 2-1300 untuk potongan.
- Reproduksi (`t_wh.py`): bayar Rp 4 jt dengan `kind:pph23, rate:50` → 200: vendor menerima Rp 2 jt, 2-1300 +2 jt, bukti potong 0100000002 terbit (tarif 50%). Kind & object_code tak sah ditolak (baik).
- Dampak: vendor ditahan separuh pembayarannya tanpa batas wajar; PPh potongan (2-1300) tak punya alur setor; koreksi bukti potong tidak sinkron dengan jurnal.

### [PK-18] [Severity: Sedang] Setoran pajak: NTPN asal, tanggal setor bebas, PPN keluaran dibukukan sebagai Beban Pajak
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: `tax_router.py:60-95`, `gl_engine.py:454-485`.
- Reproduksi (`t_tax.py`, `ui_tax2.js`): `status:paid, ntpn:'x', paid_date:'2020-01-01', cash_account_id: Escrow` → 200 (NTPN tak divalidasi; jurnal setor bertanggal 2020; UI dialog menampilkan Tgl. Setor 01/01/2020). Setor PPN keluaran memposting Dr 6-1400 Beban Pajak / Cr 2-1300 (akrual) lalu Dr 2-1300 / Cr bank → laba tergerus Rp 102 jt per catatan PPN (pertanyaan terbuka: apakah PPN keluaran sudah di luar pendapatan?). Mengganti `cash_account_id` setelah setor tidak memindahkan jurnal (UI menampilkan rekening yang tidak sama dengan jurnal).

### [PK-19] [Severity: Sedang] Rekening sumber dana tidak bisa dipilih / tidak diteruskan di beberapa jalur
- Label bukti: [DARI-KODE] [TERBUKTI-UI]
- Rekening dipilih & dipakai dengan benar: AP (bayar dari Kas Kecil → 1-1102 turun), pengajuan, kas bon, pajak (Escrow), refund pembatalan, kas kecil. Tidak bisa dipilih: komisi (API menerima `cash_account_id`, UI `CommissionsPanel.js` tidak punya tombol Bayar sama sekali → komisi `approved` Rp 17 jt di UI tak dapat dibayar), marketing fee (`marketing_fee.py:184`, hanya `source` kas/bank), uang muka subkon (`subcon_finance.py:89` konstanta bank), upah (`labor_engine.py:372`), pinjaman, aset, refund titipan (`ar_router.py:126` tidak meneruskan `cash_account_id`), penyaluran notaris.
- Dampak: jalur-jalur itu selalu keluar dari rekening default (Operasional) walau ada Escrow/bank lain; Escrow bisa dipakai untuk biaya operasional tanpa pembatasan (lihat pertanyaan terbuka).

### [PK-20] [Severity: Sedang] Idempotensi refund di UI memakai `Date.now()` per pengiriman
- Label bukti: [DARI-KODE]
- Lokasi: `components/contracts/CancellationPanel.js:124` (`client_ref: \`ui-${id}-${Date.now()}\``) berbeda dengan retensi yang membuat ref sekali per dialog. Retry setelah jaringan putus akan menghasilkan ref baru → pembayaran kedua. Komentar kode ("tidak boleh melahirkan pembayaran kedua") tidak berlaku.

### [PK-21] [Severity: Sedang] Dua modul kas bon paralel dan jalur biaya tumpang-tindih
- Label bukti: [TERBUKTI-UI] [DARI-KODE]
- Menu "Kas Bon" (`cash_advances`, KB) dan "Pengajuan" jenis `advance` (PGJ) sama-sama mencairkan ke 1-1500 (`petty_cash.py:139`, `fund_requests.py:183`); kategori `upah_harian`/`biaya_proyek` pada pengajuan mendebit WIP sama dengan rekap upah/AP/kas kecil (`reference_p27.CASHBON_ACCOUNT`) → satu biaya bisa masuk lewat 4 pintu tanpa penautan antar dokumen. Tak ada batas satu kas bon terbuka per karyawan.

### [PK-22] [Severity: Sedang] Aset tetap: tidak ada deteksi duplikat; tak cek saldo
- Label bukti: [TERBUKTI-API]
- Lokasi: `fixed_assets.py:114-182`. Pembuatan identik 4x (`t_fa.py`) → 4 aset (AST/2026/0005-0008+), Rp 15 jt ×4 keluar dari bank; aset Rp 99 miliar disahkan.

### [PK-23] [Severity: Rendah] Hal kecil lain
- `routers/subcon_router.py:162`: `maintenance_days: int(payload.maintenance_days or 90)` → 0 hari (sah, kata `subcon_finance._maintenance_days`) disimpan 90 hari [TERBUKTI-API: input 0 → tersimpan 90, retensi ditahan 90 hari].
- `subcon_claims_router.py:86`: termin boleh diajukan/dibayar untuk SPK berstatus `draft`.
- Dashboard AP (653.700.000) ≠ subledger reconcile (652.585.000): dua definisi — tagihan bernilai negatif (net −500.000 dan −615.000) dihitung di reconcile, tidak di aging [TERBUKTI-API].
- `payments_out` bukan sumber tunggal (komisi, pinjaman, pengajuan non-AP, kas bon, upah, pajak tidak masuk) dan `amount` memuat nilai bruto (termasuk PPh dipotong) sehingga ringkasan "paid_total" melebihi kas keluar [DARI-KODE].
- Label status pengajuan jenis biaya yang dibayar langsung tampil "Dipertanggungjawabkan" (`fund_requests.py:195`) [TERBUKTI-UI].
- Seed data: tiga komisi untuk satu deal (dd493f78) dengan nilai berbeda; handler `_gl_commission_approved` mencari komisi lewat `deal_id` (`gl_engine.py:388`) sehingga ambigu bila >1 [TERBUKTI-API, data seed].
- Booking fee refund (`booking_fee.py:268-341`) membatasi nilai pada `refundable` faktur, sedangkan `_deposit_move` (`finance_engine.py:602`) tidak memeriksa saldo titipan; jika titipan sudah dikembalikan lewat `/deposit/refund`, refund booking fee kedua dapat membuat saldo titipan negatif [DARI-KODE, tidak direproduksi karena tidak ada faktur booking fee di seed].

## Terverifikasi OK
- AP sekuensial: bayar > sisa ditolak ("melebihi sisa tagihan"), bayar sebelum approve ditolak, approve dua kali ditolak, nominal 0/negatif/desimal ditolak (400); RBAC: pm/site/sales/marketing/manager mendapat 403 saat membuat/membayar AP.
- Bayar-dengan-PPh: jurnal tepat Dr 2-1100 bruto / Cr bank neto / Cr 2-1300 (Δ 4 jt / 2 jt / 2 jt), bukti potong terbit otomatis & idempoten per pembayaran; kind & kode objek tak sah ditolak; potongan ≥ pembayaran ditolak.
- Rekening sumber yang dipilih dipakai (AP dari Kas Kecil mengurangi 1-1102; setoran pajak dari Escrow mengurangi 1-1202).
- Kas bon & pengajuan: pemohon tak bisa menyetujui sendiri meski berizin approve (`out3/t_sod.py`: finance buat+approve sendiri → 400 "Pemisahan tugas" untuk pengajuan PGJ dan kas bon KB; tombol UI "Setujui" milik sendiri dinonaktifkan); pencairan melebihi nominal disetujui ditolak; satu tagihan AP tak bisa diajukan dua kali (sekuensial); pembayaran vendor melebihi sisa ditolak; reimbursement tanpa lampiran (daftar kosong) ditolak.
- Transfer internal: pembuat tak bisa menyetujui sendiri meski berizin (finlead buat+approve → 400 "SoD"); cek saldo saat membuat transfer; kas kecil: pencatat tak bisa membatalkan pengeluarannya sendiri (finlead → 400); wajib-bukti kas kecil menolak bila `file_ids` kosong (tetapi lihat PK-13); uang muka subkon: pengaju tak bisa memutus sendiri (finlead → 400).
- Subkon: termin diverifikasi orang lain (site tak bisa verify termin miliknya, 403 dengan pesan independensi), PM tak punya izin approve termin (403); gerbang retensi memeriksa masa pemeliharaan + punch + klaim garansi; waive hanya finance_manager (finance & pm 403); release butuh pengajuan orang lain & `manage`; uang muka diputus bukan oleh pengaju; batas 30% sekuensial berfungsi; potongan melebihi sisa termin ditolak (kode).
- Upah: absensi unik per pekerja/hari, absensi tanggal depan ditolak, rekap tumpang-tindih ditolak, pengaju tak bisa menyetujui, jurnal Dr WIP/Cr bank benar (sekuensial).
- Pengadaan: PO > Rp 500 jt hanya Owner (403 untuk finance); 3-way match menahan tagihan ketiga yang melebihi barang diterima (400, sekuensial); peran site tidak punya izin approve PO (403) — pemisahan pembuat≠penyetuju PO untuk peran finance TIDAK ada (PK-07).
- Penutupan periode GL ditahan (409) selama subledger tak tie-out (menyebut 2-1100/2-1200/1-1800) — kontrol deteksi bekerja.
- UI: dialog Bayar AP & Cairkan pengajuan hanya mengirim 1 POST pada dobel-klik (`ap-pay-after-dblclick.png`); layar menampilkan saldo negatif dan banner selisih kendali dengan jelas; peran site/pm/sales mendapat 403 data pada layar keuangan (shell halaman tetap terbuka).
- Penghitungan: jurnal tak seimbang/negatif ditolak `post_journal` (tapi lihat PK-08 efek sampingnya); uang IDR integer.

## Tidak bisa diverifikasi
- Termin berbasis item (opname, `op.settle_lines`, unique index INV-33-3) — tidak ada pekerjaan terverifikasi di seed; paralel approve jalur item tidak diuji.
- Rekonsiliasi bank (`bank_recon.py`, `bank_match.py` jurnal biaya bank), PDC, BKK/BKM penomoran duplikat, penyusutan massal & disposal aset, auto-fee mitra (`partner_engine`) — tidak diuji.
- Refund booking fee ganda vs refund titipan (tak ada faktur booking fee di seed).
- Perilaku dispatcher bila hanya SATU pengguna (tick scheduler 8 dtk berimpit dengan request) — kode memungkinkan, tidak direproduksi; semua duplikasi nyata di atas butuh dua request bersamaan.
- Pengiriman idempotensi `client_ref` pada retensi bila dua request dengan ref yang SAMA bersamaan (`offline_intake.begin`) — tidak diuji.
- `ap_retention_release_sweeper` bila `release_due_at` terisi — dibaca, tidak dijalankan.

## Pertanyaan terbuka
1. Apakah Rekening Escrow boleh membiayai pengeluaran operasional/AP/pajak/jurnal manual? Sistem mengizinkan tanpa batas (setor pajak & jurnal manual dari Escrow berhasil).
2. Apakah PPN Keluaran memang diakui sebagai Beban Pajak pada saat setor (`gl_engine.post_tax_accrual`) atau seharusnya liabilitas pass-through?
3. Apakah PM/Sales Manager memang boleh `finance:view_all` (melihat seluruh AP/AR dan riwayat bayar semua proyek)?
4. Kebijakan saldo minus kas/bank: dilarang, atau diizinkan dengan otorisasi? (sekarang transfer/kas kecil melarang, pengeluaran lain mengizinkan.)
5. Tarif PPh dipotong: apakah ada batas wajar per jenis (pph23 2%/4%, 4(2) konstruksi 1,75–6%) yang harus dikunci server?

## Lampiran
Data uji yang tertinggal di DB `sipro_out` (semua berawalan AUDIT-): vendor `AUDIT-Vendor-*`, `AUDIT-UI-1`, SPK/2026/0004 (AUDIT-SPK-1) dengan termin TRM/2026/0002-0006, retensi RET/2026/0003-0007, pinjaman PBY/2026/0002 (AUDIT-LOAN), agen "AUDIT Agen Uji", aset "AUDIT Laptop Uji" ×4 dan "AUDIT Aset Besar" Rp 99 miliar, jurnal manual JV/2026/00128, pengajuan PGJ/2026/0001-0013, kas bon KB/2026/0003, kas kecil KK/2026/0001-0004, BTL/2026/0001 (di-approve & 400 jt dibayar), komisi untuk deal batal, dan beberapa jurnal ganda hasil uji paralel. Saldo bank operasional kini ±−Rp 92 miliar akibat uji batas saldo.
Screenshot: `ap-tab.png` (tagihan retensi/termin ganda), `finance-home.png` & `finance-banner-after.png` (banner selisih), `cashbank-home.png` (saldo negatif), `komisi-tab.png` (komisi dibayar untuk deal batal, tanpa tombol bayar), `ap-ret150-after-approve.png`, `tax-status-dialog-paid.png` / `tax-after-revert.png`, `fundreq-disburse-dialog.png` / `fundreq-after-disburse.png`, `ap-pay-dialog.png` / `ap-pay-after-dblclick.png`, `rbac-site-finance.png` / `rbac-site-cash-bank.png`.
