# AUDIT INDEPENDEN — repo `avacadasa/kn` (Kain Nusantara ERP)

> Tanggal audit: 2026-09-02 · Commit: `33822c5 Clean initial commit`
> Metode: (1) analisis statik seluruh backend (123 router · 191 service · 1.109 endpoint) dan frontend (622 berkas · 1.161 panggilan API); (2) **backend dijalankan sungguhan** (FastAPI + `seed-demo`) lalu skenario ditembak lewat HTTP untuk membuktikan temuan; (3) `npx craco build` frontend (sukses, hanya warning `exhaustive-deps`).
> Label bukti: **[RUNTIME]** = direproduksi di server yang berjalan (angka JE/saldo di bawah adalah hasil nyata); **[STATIK]** = dibuktikan dari kode (baris dikutip), belum dijalankan.
> Catatan anti-false-positive: temuan yang sudah ada di `memory/AUDIT_TEMUAN_2026-09-02.md` (FB-01/FB-02, P0-1 blank Audit tab) **tidak diulang** kecuali relevan. Bagian §9 mencatat hal-hal yang **sudah diperiksa dan BENAR** supaya agen tidak mengejarnya.

---

## 0. Ringkasan eksekutif (baca ini dulu)

Fondasi sistem ini kuat: registry scope entitas (`entity_scope.py`), pagar tulis mode gabungan (`entity_write_guard.py`), roll sebagai SSOT stok, nomor dokumen per-badan-usaha, 183 invarian. **Masalah besar bukan di isolasi baca, tetapi di WIRING KEUANGAN**: jurnal tidak diposting pada saat peristiwa bisnis terjadi, lalu "backfill" saat startup memposting ulang dokumen yang sudah berjurnal lewat jalur lain. Akibatnya buku besar bisa **kurang** (pendapatan belum diposting) dan sekaligus **lebih** (hutang/kas diposting dua kali) — dan sekali periode ditutup, backend **tidak bisa start**.

| ID | Sev | Ringkas | Bukti |
|---|---|---|---|
| F-01 | **P0** | Pendapatan & HPP SO tidak diposting saat kirim/terima uang; hanya lewat `simulate-payment` (legacy) atau backfill saat restart | RUNTIME |
| F-02 | **P0** | `backfill_journals()` tanpa try → `ClosedPeriodError` → **startup crash** + `POST /gl/sync` 500 | RUNTIME |
| F-03 | **P0** | Tagihan jasa makloon (`bill_type=makloon_service`) dijurnal 2× (subcon_service + vendor_bill) saat restart/sync → Hutang Usaha dobel | RUNTIME |
| F-04 | **P0** | Mutasi kas ber-`gl_posted: True` (pinjaman antar-PT, refund retur, settlement aset) dijurnal 2× saat restart/sync → Kas dobel + beban palsu | RUNTIME |
| F-05 | P1 | Kwitansi AR bisa dialokasikan ke order **pelanggan lain / badan usaha lain** (tanpa validasi) → Piutang PT lain terkredit | RUNTIME |
| F-06 | P1 | `create_receipt` menulis `payments[]` ke SO **sebelum** kwitansi tersimpan → pembayaran yatim bila alokasi ke-2 gagal | RUNTIME |
| F-07 | P1 | Dua jalur pembayaran paralel (`simulate-payment` vs AR receipt) dengan efek GL berbeda; `simulate-payment` tanpa guard lebih-bayar & tidak update `paid_total` | RUNTIME |
| F-08 | P1 | Netting settlement antar-PT diposting di dua buku tanpa cek saldo timbal-balik → IC-AP saldo debit / IC-AR saldo kredit | RUNTIME |
| F-09 | P1 | Dua mekanisme antar-PT hidup berdampingan (at-cost `warehouse_transfers` vs G-6 jual-beli); at-cost lolos kontrak/PPN/settlement | STATIK |
| F-10 | P1 | Retur (outcome `refund`) pada order kredit yang **sudah lunas** → Cr Piutang → Piutang negatif, uang pelanggan tidak tercatat sebagai kewajiban | STATIK |
| F-11 | P1 | Kegagalan posting GL ditelan (`except: pass/log`) tanpa antrean "belum berjurnal"; backfill hanya meliputi 3 jenis dokumen | STATIK |
| E-01 | P1 | `GET /products/{id}/stock-breakdown` mengembalikan **dokumen SO utuh badan usaha lain** (nama pelanggan, harga, alamat) ke sales PT lain | RUNTIME |
| E-02 | P2 | `GET /cycle-count/sessions` tanpa scope entitas | RUNTIME |
| F-12 | P2 | Pembeli non-PKP (CV Kanda) mencatat PPN Masukan antar-PT yang tidak bisa dikreditkan; PO/bill non-PKP dipaksa PPN 0 | RUNTIME |
| F-13 | P2 | Buku kas (`cash_transactions`) vs GL Kas tidak sinkron: order kontan & settlement antar-PT tunai hanya menyentuh GL | STATIK |
| F-14 | P2 | GR/IR (2-1150) tidak pernah dikliringkan bila harga/qty tagihan ≠ GR; tidak ada akun selisih harga beli | STATIK |
| F-15 | P2 | Nota kredit dihitung dari `items.price` (gross) mengabaikan diskon baris/order | STATIK |
| D-01 | P1 | Penomoran dokumen keuangan (CN, SRET, PRET, DN, VB, LCV, PR, FPM, RFQ, MKO, WO) **global lintas PT & non-atomik** (race → duplikat) | STATIK |
| D-02 | P2 | Nol unique index selain `products.sku`; `journal_entries.number`, `sessions.token`, `users.email`, `number_sequences` tidak dijaga DB | STATIK |
| D-03 | P3 | 18 koleksi tidak terdaftar di registry scope (`invoices`, `period_closings`, `store_credit_redemptions`, …) | STATIK |
| U-01 | P2 | 18 layar tidak refetch saat badan usaha diganti (data PT lama tetap tampil) | STATIK |
| U-02 | P3 | Tautan mati `GET /api/documents/{id}/print` (DocumentsView) + `previewTemplate` ke endpoint yang tidak ada | STATIK |

Urutan eksekusi yang disarankan ada di §8.

---

## 1. Temuan P0 — Keuangan / GL

### F-01 · P0 · [RUNTIME] Pendapatan & HPP tidak diposting saat peristiwa bisnis

**Lokasi**
- `backend/services/gl_service.py:733` `post_sales_order()` dan `:808` `post_order_cogs()` — hanya dipanggil dari:
  - `backend/routers/invoices.py:88-89` (`POST /api/sales-orders/{order_id}/simulate-payment`, jalur legacy "Simulate Payment"), dan
  - `backend/services/gl_service.py:2103` `backfill_journals()` (dipanggil `bootstrap.py:1527` saat startup dan `routers/gl.py:194` `POST /api/gl/sync`).
- Jalur bisnis nyata **tidak memanggilnya**: `services/shipment_service.py:28 dispatch_task()` (SO → `shipped`), `services/ar_receipt_service.py:318 create_receipt()` (hanya `post_cash_transaction`), `routers/sales_orders_extra.py:483 mark-delivered`.
- Tidak ada job scheduler yang memanggil backfill (`services/scheduler_service.py` JOBS: nihil).

**Reproduksi [RUNTIME]**
1. `POST /sales-orders/so_006/verify` → `/confirm` → `POST /wms/tasks/outbound-from-order/so_006` → `scan-pick` → `dispatch` kedua task. SO-0006 status `shipped`, grand 9.213.000.
2. `GET /gl/journal?entity_id=all` → **tidak ada JE** `source_id=so_006`.
3. `POST /ar-receipts` (9.213.000 ke so_006) → JE `Dr 1-1100 / Cr 1-1200` terbit **tanpa** `Dr 1-1200 / Cr 4-1000` → Piutang 1-1200 turun 9,2 jt untuk pendapatan yang belum pernah diakui.
4. `POST /finance/closing/close {"period_key":"2026-09"}` → periode ditutup dengan `revenue_total: 3.820.379` — SO-0006 (9,2 jt, dikirim September) **tidak ikut**.

**Dampak**: neraca saldo intra-hari salah (Piutang bisa negatif), laporan laba rugi & tutup buku tidak memuat penjualan yang belum di-backfill, dan revenue baru "muncul" setelah restart server.

**Perbaikan**
1. Panggil posting pada peristiwa: di `services/shipment_service.py` setelah `await recompute_so_status(task["order_id"])` (baris 90) tambahkan:
   ```python
   fresh = await db.sales_orders.find_one({"id": task["order_id"]}, {"_id": 0})
   await gl_service.post_sales_order(fresh)     # idempotent by source_id
   await gl_service.post_order_cogs(fresh)
   ```
   dan di `services/ar_receipt_service.py::_apply_to_order` (setelah baris 310) panggil hal yang sama untuk `order_id` (bungkus try/except **yang mencatat ke antrean** — lihat F-11, jangan `pass`).
2. Putuskan kebijakan pengakuan (lihat B-01): bila pendapatan hanya saat KIRIM, ubah `_revenue_eligible()` (`gl_service.py:700`) agar **tidak** true karena `paid`; uang muka sebelum kirim harus ke `2-1400 Uang Muka Pelanggan` (bukan Cr Piutang). Bukti masalah kebijakan saat ini: seed SO-0007 `waiting_approval` + `paid` sudah punya JE pendapatan penuh (KSC/JE-00009).
3. `post_sales_order` untuk `partially_shipped` mengakui **seluruh** grand_total (`gl_service.py:742`). Ubah menjadi proporsional qty terkirim (Σ `shipments.qty × price`) dengan `source_id=f"{order_id}:{shipment_id}"`, atau tunda sampai `shipped`. Bukti: seed SO-0003 `partially_shipped` → KSC/JE-00003 = grand penuh 24.919.500.

**Tes penerimaan**: setelah dispatch penuh, `GET /gl/journal?source=sales_order` memuat `source_id` SO tersebut di detik yang sama; `verify_data_integrity` tambah invarian **INV-GL-REV-01**: setiap SO berstatus ∈ `REVENUE_STATUSES` dengan `grand_total>0` wajib punya JE `sales_order` non-void.

### F-02 · P0 · [RUNTIME] Backfill tanpa penjaga → startup crash setelah periode ditutup

**Lokasi**: `backend/bootstrap.py:1527` `await gl_service.backfill_journals()` (tidak dibungkus try — bandingkan langkah lain di `run_bootstrap` yang dibungkus); `backend/routers/gl.py:194`; `gl_service.py:2112-2131` loop tanpa per-dokumen try; `gl_service._insert_entry:524` melempar `ClosedPeriodError`.

**Reproduksi [RUNTIME]**: setelah langkah F-01 (SO-0006 belum berjurnal, dikirim 2026-09-02) → tutup periode 2026-09 → `POST /api/gl/sync` → **HTTP 500** (`ClosedPeriodError: Periode September 2026 sudah DITUTUP …` di log). Karena kode yang sama dipanggil dari `lifespan()` tanpa penjaga, restart backend berikutnya gagal di `run_bootstrap()`.

**Perbaikan**
1. `backfill_journals()`: bungkus **per dokumen** dengan `try/except ClosedPeriodError` → kumpulkan ke daftar `skipped_closed` dan kembalikan di hasil; jangan biarkan satu dokumen menghentikan loop.
2. `bootstrap.py:1527`: bungkus `try/except Exception` + log (pola yang sudah dipakai di baris 1533-1539).
3. `closing_service.close_period()` (`services/closing_service.py:253`): sebelum menghitung `income_statement`, panggil `backfill_journals()` untuk `entity_id` tersebut (atau tolak close bila masih ada dokumen belum berjurnal — pakai antrean F-11) supaya tutup buku tidak mengunci pendapatan yang belum diposting.

### F-03 · P0 · [RUNTIME] Tagihan jasa makloon dijurnal dua kali

**Lokasi**
- `services/makloon_order_service.py:806-827`: bill dibuat di `vendor_bills` dengan `bill_type: "makloon_service"`, `status: "posted"`, lalu `gl.post_subcon_service()` (JE `source_type="subcon_service"`, Dr 1-1350 WIP / Cr 2-1100).
- `services/gl_service.py:2128-2132` `backfill_journals()`: `db.vendor_bills.find({"status": {"$in": ["posted","paid"]}})` → `post_vendor_bill()` yang idempoten hanya terhadap `source_type="vendor_bill"` (`:1313`) → JE kedua Dr 2-1150 GR/IR / Cr 2-1100.

**Bukti [RUNTIME]**: `POST /gl/sync` → `{"vendor_bills": 6}`. `vb_163fe89a85f4` (VBM-00001, 381.500) kini punya **KSC/JE-00022** (`subcon_service`) **dan KSC/JE-00087** (`vendor_bill`), keduanya `Cr 2-1100 381.500`. Total Hutang Usaha KSC lebih 3.481.500 (6 bill) hanya karena server pernah restart.

**Perbaikan**
1. `post_vendor_bill()`: tambahkan di awal `if bill.get("bill_type") == "makloon_service": return None`.
2. `backfill_journals()`: filter `"bill_type": {"$ne": "makloon_service"}`.
3. Lebih kuat: buat helper `gl_service.any_posting_for(source_id)` (cek `journal_entries.source_id == bill_id` apa pun `source_type`-nya) dan pakai di semua `post_*` yang menerima dokumen.
4. Migrasi data: cari JE `source_type="vendor_bill"` yang `source_id`-nya juga punya JE `subcon_service` → `reverse_document()` dengan alasan "duplikat backfill".

**Tes**: invarian **INV-GL-DUP-01**: untuk setiap `source_id`, tidak boleh ada dua JE non-void non-reversal yang sama-sama mengkredit akun yang sama untuk nilai yang sama.

### F-04 · P0 · [RUNTIME] Mutasi kas `gl_posted: True` dijurnal ulang oleh backfill

**Lokasi**
- Penulis flag: `services/cash_ledger.py:64` (`record_return_cash`, dipakai `return_service.py:1231` refund retur jual & `purchase_return_service.py:329` refund retur beli), `services/interco_money_service.py:97` (`twin_cash`, dipakai `interco_loan_service.py:175,218` dan `fixed_asset_service.py:440`).
- **Tidak ada pembaca flag**: `grep gl_posted` di `services/`+`routers/` hanya menemukan penulisnya. `gl_service.post_cash_transaction():1997-2003` dan `backfill_journals():2121-2125` tidak memeriksanya.

**Bukti [RUNTIME]**: `POST /interco/loans` (KSC→Kanda 2.000.000) → `/disburse` → JE benar: KSC/JE-00093 (Dr 1-1250 / Cr 1-1100) & KANDA/JE-00026 (Dr 1-1100 / Cr 2-1250). Lalu `POST /gl/sync` → `{"cash_transactions": 2}` → **KSC/JE-00094** `Dr 6-4000 Beban Operasional 2.000.000 / Cr 1-1100` (kas keluar dobel + beban fiktif) dan **KANDA/JE-00027** `Dr 1-1100 / Cr 1-9999 Suspense`. Saldo Kas KSC bergeser −2 jt setelah sync.

**Perbaikan**
1. `post_cash_transaction()`: `if txn.get("gl_posted"): return None` (baris pertama setelah cek void).
2. `backfill_journals()`: filter `"gl_posted": {"$ne": True}`.
3. Migrasi: JE `source_type="cash_transaction"` yang `source_id`-nya adalah cash doc ber-`gl_posted:true` → reverse.
4. Tambah `INV-CASH-02`: cash doc `gl_posted:true` tidak boleh punya JE `source_type="cash_transaction"`.

---

## 2. Temuan P1 — Keuangan & multi-entitas

### F-05 · P1 · [RUNTIME] Alokasi kwitansi AR tidak memvalidasi pemilik order (pelanggan & badan usaha)

**Lokasi**: `services/ar_receipt_service.py:264 _apply_to_order()` — hanya memeriksa `order` ada & outstanding; `create_receipt():355-368` meneruskan `a["order_id"]` dari payload apa adanya; `routers/ar_receipts.py:65-73` tidak memeriksa order ∈ `ctx.allowed_entity_ids`. Pagar `assert_body_entity_allowed` hanya melihat field `entity_id` di body, bukan `allocations[].order_id`.

**Bukti [RUNTIME]**
- Kwitansi `cust_toko_kain` dialokasikan ke `so_008` milik `cust_butik_bali` → **200 OK**.
- Konteks `X-Entity-Id: ent_kanda`, kwitansi `KANDA/AR-00003` (pelanggan Kanda) dialokasikan ke `so_008` (**ent_ksc**) → 200 OK; `so_008.payments[]` memuat `KANDA/AR-00003`; JE **KANDA/JE-00025** `Cr 1-1200` di buku **Kanda** padahal piutangnya milik KSC → Piutang Kanda negatif, Piutang KSC tetap tinggi.

**Perbaikan** (di `_apply_to_order` sebelum mutasi): `if o["customer_id"] != receipt_customer_id: raise 400`; `if o.get("entity_id") != receipt_entity_id: raise 403`. Teruskan `customer_id` & `entity_id` kwitansi sebagai parameter. Tambahkan pemeriksaan yang sama di `payment_variance_service.apply_from_deposit/…` dan `store_credit_service.redeem` bila menerima `order_id` dari klien (periksa; pola sama).

### F-06 · P1 · [RUNTIME] Pembayaran yatim: SO dimutasi sebelum kwitansi tersimpan

**Lokasi**: `services/ar_receipt_service.py:355-378` (`_apply_to_order` per alokasi → `$push payments`, `$inc paid_total`) dilakukan **sebelum** `db.ar_receipts.insert_one(doc)` di `:409`. Bila alokasi ke-2 melempar (`400` melebihi outstanding, `404` order tidak ada, `409` guard `$expr`), alokasi ke-1 sudah tertulis, kwitansi tidak pernah ada, kas & JE tidak ada.

**Bukti [RUNTIME]**: `so_008.payments[]` berisi `KSC/AR-00012` (1.000.000) sementara `GET /ar-receipts` tidak memuat `KSC/AR-00012`; `paid_total` naik. (Di lingkungan audit pemicunya adalah guard 409; di produksi pemicu pastinya adalah alokasi ke-2 yang tidak valid — baris 272-275 melempar 400 setelah alokasi ke-1 sukses.)

**Perbaikan**: validasi **semua** alokasi dulu (pemilik, outstanding, entitas) tanpa menulis; simpan `ar_receipts` dengan `status:"applying"`; baru mutasi order; bila ada kegagalan di tengah → kompensasi (hapus `payments[]` ber-`receipt_id` ini, `$inc paid_total` balik) lalu hapus/void kwitansi. Tambah `INV-AR-02`: setiap `payments[].receipt_id` wajib ada di `ar_receipts` non-void.

### F-07 · P1 · [RUNTIME] Dua jalur pembayaran paralel; `simulate-payment` tanpa guard & tidak sinkron `paid_total`

**Lokasi**: `routers/invoices.py:36-115` vs `services/ar_receipt_service.py`. UI masih menampilkan tombol "Simulate Payment" (`frontend/src/features/orders/OrderDetailPanel.jsx:551-554`, `useAppActions.js:356`).

**Bukti [RUNTIME]**: `POST /sales-orders/so_007/simulate-payment {"amount":1000000}` pada order yang **sudah lunas** → 200; `Σpayments = 18.427.000 > grand 17.427.000`; `paid_total` tetap 17.427.000 (endpoint hanya `$push payments` + `$set payment_status`, baris 76-80, tidak `$inc paid_total`); juga membuat `invoices` + cash + JE `Cr 1-1200` → Piutang negatif.

**Dampak tambahan**: `paid_total` dibaca UI (`components/PaymentBadge.jsx:9`, `OrdersView.jsx:25`, `SOCompactPanel.jsx:68`) dan `order_journey_service.py:158`, `cashflow_forecast_service.py:87`, sedangkan AR/aging memakai Σ`payments[]` → dua angka "sudah dibayar" yang berbeda di layar berbeda.

**Perbaikan**: (a) hapus/nonaktifkan `simulate-payment` di produksi atau jadikan pembungkus tipis ke `ar_receipt_service.create_receipt` (satu pintu); (b) tetapkan satu SSOT: hapus field `paid_total` atau jadikan turunan yang di-set ulang dari Σ`payments[]` setiap kali `payments[]` berubah (satu helper `sync_paid_total(order_id)`); (c) koleksi `invoices` (isinya = catatan pembayaran, bukan faktur) sebaiknya dihentikan; faktur yang sah = `tax_invoices` / dokumen PDF.

### F-08 · P1 · [RUNTIME] Netting antar-PT tanpa cek saldo timbal-balik

**Lokasi**: `services/interco_service.py:1064-1110 _post_gl_settlement()`; `method` default `"netting"` (`:993`); `create_settlement()` tidak memeriksa apakah **payer** juga punya piutang ke payee.

**Bukti [RUNTIME]** (data seed): `KANDA/ICS-00001` netting 1.887.888 padahal hanya Kanda yang berutang ke KSC. Hasil: buku KSC `2-1250 IC-AP` **saldo debit** 1.887.888 (kewajiban bersaldo debit), buku Kanda `1-1250 IC-AR` **saldo kredit** 1.887.888. `interco_accounts` (INV-IC-04) tampak benar (outstanding 1.742.700), tetapi GL per akun salah dan eliminasi konsolidasi (IC-AR vs IC-AP) tidak akan cocok.

**Perbaikan**: di `create_settlement()`, bila `method=="netting"` hitung `ar_reverse = outstanding(payee→payer)`; tolak bila `total > ar_reverse` ("tidak ada piutang balik untuk di-net"). Default `method` sebaiknya `"transfer"`. Untuk data lama: reverse JE settlement netting satu arah.

### F-09 · P1 · [STATIK] Dua mekanisme antar-PT hidup berdampingan

**Lokasi**
- Jalur A (lama, at-cost): `services/sales_order_helpers.py:98-140` (SO "beli per roll" lintas-entitas otomatis membuat `warehouse_transfers.transfer_kind="inter_entity"`, `transfer_price: 0`, **tanpa** `interco_pair_id`), `routers/transfers.py:326-367` (`POST /transfers/inter-company` tanpa pair), dan cabang `else` `routers/transfers.py:459-463` → `gl_service.post_intercompany_transfer()` (`gl_service.py:866`, Dr IC-AR / Cr Persediaan at-cost, tanpa PPN, tanpa dokumen faktur).
- Jalur B (G-6): `services/interco_service.py` — harga kontrak, PPN, `interco_accounts`, settlement.

**Masalah**: saldo IC-AR/IC-AP dari jalur A **tidak masuk** `interco_accounts` (`_update_account_balance` hanya Σ `interco_transactions` − settlement) → tidak pernah tampil di layar settlement, tidak bisa dilunasi/di-net, dan melanggar keputusan pemilik G-6 ("tanpa kontrak → ditolak"; PPN antar PT PKP). Jalur A juga meng-HPP-kan persediaan PT sumber tanpa pendapatan (transfer at-cost) sehingga margin per PT tidak nyata.

**Perbaikan**: jadikan jalur A selalu membuat `interco_transactions` (panggil `interco_service.create()` dari `sales_order_helpers` cross-entity, lalu `create_warehouse_task`) — atau blokir jalur A bila `settings.inventory.intercompany_transfer_required` aktif dan hapus `else` at-cost di `transfers.py` (kembalikan 400 "buat Transaksi Antar-Entitas dulu"). Tambah invarian: JE `inter_company_transfer` baru = MERAH.

### F-10 · P1 · [STATIK] Retur `refund` pada order kredit yang sudah lunas → Piutang negatif

**Lokasi**: `services/return_service.py:1201-1203` (`settlement_type=None` untuk `OUTCOME_REFUND`) → `_create_credit_note_and_post_gl():214-216` memilih `"cash"` hanya untuk metode NON_AR, selain itu `"ar"` → `gl_service.post_sales_return():1933-1936` `Cr 1-1200 Piutang` **tanpa** memeriksa outstanding order. Order NET30 yang sudah lunas lalu diretur (kasus sangat umum) → Piutang negatif; tidak ada kas keluar, tidak ada kewajiban `2-1400`, tidak ada kasus di `finance_case_scan` (hanya memindai titipan & duplikat).

**Perbaikan**: di `_create_credit_note_and_post_gl` hitung `outstanding = grand − Σpayments`; bagian CN ≤ outstanding → `Cr 1-1200`; sisanya → `Cr 2-1400 Uang Muka/Kelebihan Bayar Pelanggan` + `_adjust_deposit(customer, sisa)` **atau** wajibkan outcome `store_credit`/refund tunai (buat `cash_transactions` keluar). Tambah invarian `INV-AR-03`: tidak ada order dengan `Σpayments − Σcredit_notes(ar) > grand_total` tanpa deposit yang setara.

### F-11 · P1 · [STATIK] Posting GL "best-effort" tanpa antrean pemulihan

**Lokasi** (hasil pemindaian AST — `try` yang menelan kegagalan posting): `routers/inbound_receiving.py:617` (`post_goods_receipt`), `routers/invoices.py:85`, `routers/sales_orders_extra.py:770`, `routers/vendor_bills.py:383`, `services/ar_receipt_service.py:100,518`, `services/inventory_service.py:55`; pola `je=None` di `services/return_service.py:266-268` (`post_sales_return`) dan `purchase_return_service.py` (`post_purchase_return`). `backfill_journals()` hanya meliputi `sales_orders`, `cash_transactions`, `vendor_bills` — GR, retur jual/beli, landed cost, store credit, dst. **tidak punya jalur ulang** bila gagal (mis. `ClosedPeriodError`, akun nonaktif).

**Perbaikan**: satu helper `gl_service.post_or_queue(fn, *args, source_type, source_id, entity_id)` yang, bila melempar, menulis dokumen ke koleksi baru `gl_posting_queue` (`{source_type, source_id, entity_id, error, attempts, created_at}`), ditampilkan di **Meja Finance** ("Belum berjurnal") dan di-retry oleh job scheduler. `backfill_journals()` → ganti menjadi pemroses antrean ini. Invarian `INV-GL-Q-01`: antrean kosong sebelum tutup buku.

### E-01 · P1 · [RUNTIME] Kebocoran dokumen SO lintas badan usaha lewat `stock-breakdown`

**Lokasi**: `routers/products.py:218-222` `reservations_raw = await db.sales_orders.find({"allocations.product_id": product_id, "status": {"$in": [...]}}, {"_id": 0})` — tanpa filter entitas; dikembalikan utuh di `:276` (`"reservations": [...]`). Izin hanya `product.view` (semua sales).

**Bukti [RUNTIME]**: login `sales3@` (home & allowed = `ent_kanda` saja), `GET /products/prod_batik_mega/stock-breakdown` → `reservations` berisi **SO-0004 milik ent_ksc** lengkap: `customer_name "Fashion Bandung Kencana"`, `grand_total 10.267.500`, `items[]`, `payments[]`, `shipping_address`, `sales_name`. `balances`/`ownership_matrix`/`rolls` juga memuat `owner_entity_id` PT lain (ini mungkin disengaja untuk matriks kepemilikan K1, tetapi `reservations` jelas bocor).

**Perbaikan**: `reservations_raw` → `apply_entity_scope("sales_orders", {...}, ctx, mode="allowed")` dan proyeksikan hanya `{id, number, entity_id, allocations, status}`; `rolls`/`balances` proyeksikan tanpa `reserved_ref` bila `owner_entity_id ∉ allowed`. Tambahkan endpoint ini ke `scripts/entity_audit/audit_entity_isolation.py` (saat ini tidak ada di daftar).

### D-01 · P1 · [STATIK] Penomoran dokumen keuangan global & non-atomik

**Lokasi** (semua pola "cari nomor tertinggi lalu +1", tanpa `entity_id`, tanpa unique index):
`services/return_service.py:124 next_return_number` (SRET-), `:138 next_credit_note_number` (CN-), `services/purchase_return_service.py:26,32` (PRET-, DN-), `services/vendor_bill_service.py:167` (VB-), `services/landed_cost_service.py:31` (LCV-), `services/purchase_requisition_service.py:31` (PR-), `services/input_tax_service.py:24` (FPM-), `services/rfq_service.py:24`, `services/makloon_order_service.py:163` (MKO-), `services/production_service.py:190` (WO-), `routers/makloons.py:27`, `routers/suppliers.py:25`.

**Masalah**: (1) satu seri nomor untuk dua badan hukum berbeda (nota kredit/nota debit/faktur pajak masukan PT A dan CV B bercampur); (2) dua request bersamaan menghasilkan nomor sama (read-then-write) — tidak ada unique index yang menolak; (3) tidak konsisten dengan SO/PO/JE/AR yang sudah `KSC/SO-00001`.

**Perbaikan**: ganti semuanya ke `core_utils.next_doc_number(collection, field, prefix, entity_id=<entitas dokumen>)` (sudah atomik via `number_sequences`), plus unique index `(entity_id, number)`. Sediakan skrip migrasi yang **tidak mengganti nomor lama** (cukup mulai seri baru per entitas dari max lama).

---

## 3. Temuan P2 / P3

### E-02 · P2 · [RUNTIME] `GET /cycle-count/sessions` tanpa scope
`routers/cycle_count.py:70` `db.cycle_count_sessions.find({})` — koleksi terdaftar SCOPED (`entity_scope.py:176`). Bukti: konteks `ent_kanda` mengembalikan `cc_seed_001/002` milik `ent_ksc`. Perbaikan: `resolve_list_scope("cycle_count_sessions", {}, ctx)`; `get_session/update_item/reject` (`:77,125,139,221`) tambah `assert_active_entity_access`.

### F-12 · P2 · [RUNTIME] PPN untuk badan usaha non-PKP
- Antar-PT: `services/interco_service.py:667-669` selalu `Dr 1-1500 PPN Masukan` di buku pembeli walau pembeli non-PKP. Bukti: KANDA/JE-00009/11/12 memuat 1-1500 (172.700 / 187.088 / 51.810) padahal `ent_kanda.is_pkp=false` (kredit pajak yang tidak akan pernah bisa dipakai). Perbaikan: bila `buyer.is_pkp` false → PPN masuk ke `1-1310/1-1300` (kapitalisasi).
- Pembelian eksternal: `services/config_service.py:254-260` `compute_tax` memakai `is_pkp` **entitas pembeli** → PO/bill CV Kanda selalu `ppn 0` (semua PO ent_kanda di seed: `ppn 0.0`), padahal supplier PKP tetap memungut PPN. Perbaikan: PPN pembelian ditentukan oleh status PKP **supplier** (tambahkan `suppliers.is_pkp`); untuk pembeli non-PKP, PPN dikapitalisasi ke biaya, bukan `1-1500`.

### F-13 · P2 · [STATIK] Buku kas ≠ GL Kas
- Order kontan (`NON_AR_METHODS`): `gl_service.post_sales_order():746-747` mendebit `1-1100` saat revenue-eligible (termasuk saat hanya `shipped`, belum dibayar!) dan `routers/invoices.py:92` sengaja **tidak** membuat `cash_transactions`. Uang kontan tidak pernah ada di buku kas/rekonsiliasi bank.
- Settlement antar-PT `method=transfer/cash` (`interco_service.py:1112-1133`) memposting Cr/Dr `1-1100` tanpa `cash_transactions` (bandingkan `interco_money_service.twin_cash` yang benar membuat keduanya).
- `services/cashflow_forecast_service.py:22` mendefinisikan ulang `NON_AR_METHODS = {"tunai","cash"}` (tanpa `"kontan"`) — drift dari SSOT `customer_service.py:15`.
Perbaikan: setiap JE yang menyentuh 1-1100/1-1110 wajib berasal dari `cash_transactions` (buat helper tunggal `cash_ledger.record(...)` yang menulis doc kas **dan** JE); invarian `INV-CASH-01`: Σ`cash_transactions` per entitas per akun == saldo GL 1-1100/1-1110.

### F-14 · P2 · [STATIK] GR/IR tidak dikliringkan
`routers/inbound_receiving.py:615-619` GR = `qty × harga PO` → Dr 1-1300 / Cr 2-1150. `gl_service.post_vendor_bill():1324` Dr 2-1150 = `bill.net` (harga bill × qty bill). Bila harga/qty bill ≠ PO (toleransi 3-way match `vendor_bill_service.py:108-131` mengizinkan), residu 2-1150 abadi; tidak ada akun **Selisih Harga Beli (PPV)** dan tidak ada invarian/laporan GR/IR. Perbaikan: saat bill posted, hitung `grir_cleared = Σ GR untuk qty yang ditagih`; selisih → akun baru `5-9100 Selisih Harga Pembelian` (atau ke persediaan bila belum terjual); laporan GR/IR terbuka per PO.

### F-15 · P2 · [STATIK] Nota kredit mengabaikan diskon
`services/return_service.py:175,188`: `unit_price = items.price` (GROSS) × qty; `order_discount_percent`/`discount_amount` diabaikan. Saat ini diskon baris dimatikan di SO create (`routers/sales_orders.py:189`), tetapi masih bisa masuk lewat **amandemen** (`services/amendment_service.py:44-47` `discount_percent`, `order_discount_percent`) dan `order_discount_percent` bila setting diaktifkan. Perbaikan: pakai `line_total/quantity` dan bagi proporsional `order_discount_amount`.

### F-16 · P2 · [STATIK] `_insert_entry` tidak memverifikasi keseimbangan & jatuh ke entitas default
`gl_service.py:496-534`: tidak ada `assert abs(total_debit-total_credit) <= EPS` (hanya `create_manual_entry` yang memeriksa) dan `"entity_id": entity_id or DEFAULT_ENTITY_ID` (`:518`) — JE dokumen tanpa `entity_id` **diam-diam** masuk buku PT Kain Suka Cita. Perbaikan: `raise ValueError` bila tidak seimbang; `raise ValueError("entity_id wajib")` bila kosong (sesuai keputusan E7.4 "setiap uang milik satu badan usaha").

### F-17 · P2 · [STATIK] Ringkasan kas dipotong 2000 baris tanpa urutan
`routers/cash.py:76` `find(...).to_list(2000)` lalu difilter di Python → begitu mutasi kas > 2000, saldo kartu Kas Besar/Kecil salah tanpa peringatan. Ganti dengan `aggregate` `$match entity_id ∈ scope` + `$group`.

### D-02 · P2 · [STATIK] Tidak ada unique index
`indexes.py` sengaja non-unique; hanya `products.sku` (`bootstrap.py:1599`). Tambahkan unique (partial bila perlu): `users.email`, `sessions.token`, `number_sequences (entity_id, doc_type)`, `journal_entries.number`, `sales_orders.number`, `purchase_orders.po_number`, `ar_receipts.number`, `credit_notes.number`, `cash_transactions.number`, `business_entities.id`, dan `id` di setiap koleksi transaksi (`id` adalah kunci logis di seluruh kode).

### D-03 · P3 · [STATIK] Koleksi tidak terdaftar di `entity_scope`
Dipakai kode tetapi bukan SCOPED maupun SHARED: `invoices` (ber-`entity_id`; `GET /invoices` `routers/invoices.py:21` `find({})` tanpa scope — walau saat ini FE tidak memanggilnya), `period_closings` (ber-`entity_id`), `store_credit_redemptions`, `credit_overrides`, `intercompany_eliminations`, `document_deliveries`, `generated_documents`, `collection_followups`, `crm_leads`, `crm_interactions`, `document_signatures`, `esign_requests`, `pdf_templates`, `document_branding`, `integration_settings`, `login_attempts`, `rfid_devices`, `amendment_reasons`. Putuskan eksplisit per koleksi (pola L15) dan daftarkan.

### D-04 · P3 · Konsep ganda di DB (rangkuman)
| Konsep | Koleksi/field ganda | Rekomendasi |
|---|---|---|
| Pembayaran pelanggan | `invoices` (simulate) · `ar_receipts` · `sales_orders.payments[]` · `sales_orders.paid_total` | satu SSOT: `ar_receipts`; `payments[]` = cache turunan; `paid_total` dihapus/derivasi |
| Antar-PT | `warehouse_transfers.inter_entity` at-cost · `interco_transactions` | satu: G-6 |
| QC/inspeksi | `qc_inspection.py` (+`qc_service`) · `inspections` (FASE I) | migrasi penuh ke `inspections` |
| Retur beli | `purchase_returns` dibuat dari dua jalur (`qc_service._create_qc_return` dan `purchase_return_service.create_purchase_return`) dengan bentuk dokumen yang tidak identik | satu service pembuat dokumen |
| Cycle count | `cycle_count_sessions` (legacy) · `rfid_cycle_counts` (R6) | satu |
| Dokumen | `generated_documents` (ditulis, tak pernah dibaca; tautan `/print` mati) · `pdf` platform | hapus `generated_documents` |

### U-01 · P2 · [STATIK] Layar tidak refetch saat badan usaha diganti
`App.js:126-131` mengganti header `X-Entity-Id` tanpa me-remount `AppViewRouter` (tidak ada `key={selectedEntity}`), sementara 18 layar memuat data dengan `useEffect(..., [])` dan **tidak** menerima prop `selectedEntity`/`useEntityScope`: `TaxInvoices.jsx:66`, `SalesReturns.jsx`, `SpecialOrders.jsx:61`, `PriceApprovals.jsx`, `ApprovalInbox.jsx`, `EscalationManagement.jsx`, `InterCompanyTransfers.jsx`, `StockBucketsView.jsx`, `SalesHome.jsx`, `ReturnPoliciesView.jsx`, `ProductTemplatesView.jsx`, `GroupConsolidationView.jsx`, `SchedulerView.jsx`, `ExpenseCategoriesView.jsx`, `UomConversionView.jsx`, `ColorLibraryView.jsx`, `ChartOfAccounts.jsx`, `EmployeeSelfService.jsx` (yang bertanda master bersama boleh diabaikan). Akibat: admin/manager berpindah PT tetapi tabel Faktur Pajak/Retur/PO Custom masih menampilkan PT sebelumnya sampai pindah menu. Perbaikan termurah: `<AppViewRouter key={selectedEntity} …/>` di `App.js:415`.

### U-02 · P3 · [STATIK] Tautan/aksi FE ke endpoint yang tidak ada
- `frontend/src/features/documents/DocumentsView.jsx:79` `href={`${API}/documents/${lastDocument.id}/print`}` → tidak ada rute (router `documents.py` hanya `/documents/preview/{order_id}`) → 404 "Buka tampilan cetak" setelah generate dokumen.
- `frontend/src/hooks/useAppActions.js:553` `POST /document-templates/{id}/preview` → tidak ada rute (kode mati: `onPreviewTemplate` tidak dipakai `DocumentsView`).
Sisanya: 1.161 panggilan FE cocok dengan 1.109 endpoint BE (pencocokan otomatis), tidak ada ketidakcocokan lain.

### U-03 · P3 · Setting diskon "mati"
`settings.sales.allow_item_discount / allow_order_discount` masih ada di Pengaturan dan dihormati `compute_order_pricing`, tetapi FE (`CartPanel.jsx:55`, `useAppActions.js:291,305`) dan BE (`routers/sales_orders.py:189`) memaksa 0. Hapus toggle atau hidupkan kembali secara konsisten (INV konfigurasi `audit_config_wiring.py` seharusnya menandai ini ORPHAN_UI).

### U-04 · (sudah tercatat di `memory/AUDIT_TEMUAN_2026-09-02.md` P0-1) — masih ada
`features/admin/AdminView.jsx:358` `JSON.stringify(log.after).slice(0,240)` + tidak ada `ErrorBoundary` di seluruh `src/` (grep 0 hit). Tetap prioritas tinggi.

---

## 4. Audit database — ringkasan

- **Sinkron registry↔kode**: 121 koleksi dirujuk kode; 18 tidak terdaftar (D-03). Registry SCOPED/SHARED lainnya konsisten dengan penggunaan.
- **Duplikasi**: lihat D-04.
- **Relasi**: `doc_refs` dua arah bagus; lubang: `sales_orders.payments[].receipt_id` → `ar_receipts` tidak dijamin (F-06); `journal_entries.source_id` → dokumen sumber tidak unik per dokumen (F-03/F-04); `warehouse_transfers.inter_entity` tanpa `interco_pair_id` tidak terhubung ke `interco_accounts` (F-09).
- **Index**: `indexes.py` cukup untuk kueri panas; unique index nihil (D-02). Koleksi ber-tulis tanpa index sama sekali (mis. `cash_transactions`, `credit_notes`, `shipments`, `hr_*`, `rfid_*`) — tambahkan minimal `(entity_id, created_at)` dan `id`.
- **Transaksi**: nol penggunaan sesi/transaksi Mongo di seluruh repo; semua alur multi-dokumen (kwitansi, retur, interco, settle) non-atomik → pola kompensasi wajib (F-06).

## 5. Audit endpoint & alur — ringkasan

- 1.109 endpoint; 0 duplikat method+path; semua endpoint punya penjaga auth (12 kandidat "tanpa auth" ternyata memakai helper `_emp_for_user`/`_scope_query`/token perangkat — **bukan** temuan).
- Sweep 364 endpoint GET tanpa parameter path (admin, konteks KSC): **0 × 5xx** (32 × 422 = parameter wajib).
- Isolasi baca: `resolve_list_scope`/`assert_entity_access` dipakai konsisten; pengecualian yang terbukti: E-01, E-02, `GET /invoices` (D-03).
- Isolasi tulis: `entity_write_guard` bekerja; lubang: id dokumen di body (F-05) tidak diperiksa oleh `assert_body_entity_allowed`.

## 6. Frontend — ringkasan

- Build produksi sukses; 30 warning `react-hooks/exhaustive-deps` (beberapa = U-01).
- Form utama (SO, PO, AR receipt, retur, interco) mengirim field yang dikenal backend (dicek terhadap `schemas*.py`); tidak ada field "hilang" yang menyebabkan 422.
- Tabel: kontrak `{items,total}` vs array telanjang ditangani `usePagedList`; tidak ditemukan mismatch.
- Temuan: U-01..U-04.

## 7. Kesenjangan bisnis / usability (percabangan kasus)

| ID | Kasus nyata | Kondisi sekarang | Saran |
|---|---|---|---|
| B-01 | Kapan pendapatan diakui | Saat kirim **atau** saat dibayar (F-01/#2) — DP 50% pada order belum kirim = pendapatan | Putuskan: pendapatan saat kirim; DP → 2-1400; tulis di `memory/INVARIANTS.md` |
| B-02 | Pengiriman sebagian lalu pelanggan membatalkan sisanya | `POST /sales-orders/{id}/cancel` menolak `partially_shipped` (`sales_orders_extra.py:754`); tidak ada "tutup pendek" SO; pendapatan penuh sudah diposting | Tambah `close-short` (lepas roll sisa, sesuaikan grand_total/JE proporsional, backorder ditutup) |
| B-03 | Retur pada order yang sudah lunas | F-10 | Wajib pilih: refund tunai (kas keluar) / store credit / kompensasi ke order berikutnya |
| B-04 | Pembeli/penjual non-PKP dalam grup | F-12 | Model PKP pada supplier & pelanggan; PPN dikapitalisasi bila non-PKP |
| B-05 | Uang antar-PT | Netting bebas (F-08), transfer at-cost (F-09) | Satu jalur G-6; netting hanya sebesar piutang balik |
| B-06 | "Apa yang belum berjurnal?" | Tidak ada layar/antrean (F-11) | Kartu "Belum berjurnal" di Meja Finance + blokir tutup buku |
| B-07 | Kas fisik vs GL | F-13 | Rekonsiliasi harian buku kas vs 1-1100/1-1110 |
| B-08 | Tagihan supplier beda harga dari PO | F-14 | Akun PPV + laporan GR/IR terbuka |
| B-09 | Ganti badan usaha di tengah layar | U-01 | remount |

## 8. Urutan eksekusi untuk agen (setiap langkah = 1 PR, disertai tes/invarian)

1. **F-03 + F-04** (hentikan double-post): patch `post_vendor_bill`, `post_cash_transaction`, `backfill_journals`; skrip `scripts/migrate_reverse_duplicate_backfill_je.py --report|--apply`; invarian `INV-GL-DUP-01`, `INV-CASH-02`.
2. **F-02**: bungkus backfill; `close_period` memanggil backfill / menolak bila antrean tidak kosong.
3. **F-01 (+B-01)**: posting saat dispatch & AR receipt; kebijakan `_revenue_eligible`; proporsional partial shipment; `INV-GL-REV-01`.
4. **F-11**: `gl_posting_queue` + job + kartu Meja Finance.
5. **F-05 + F-06 + F-07**: validasi & atomisitas kwitansi; matikan `simulate-payment`; `sync_paid_total`; `INV-AR-02`.
6. **E-01 + E-02 + D-03**: scope `stock-breakdown`, `cycle-count`, daftarkan koleksi; tambahkan kedua endpoint ke `audit_entity_isolation.py`.
7. **F-08 + F-09**: guard netting; tutup jalur at-cost.
8. **F-10 + F-15**: nota kredit vs outstanding & diskon.
9. **D-01 + D-02**: penomoran per entitas + unique index (migrasi tanpa mengganti nomor lama).
10. **F-12, F-13, F-14, F-16, F-17**: PKP, buku kas, GR/IR, guard `_insert_entry`, agregasi kas.
11. **U-01..U-04**: `key={selectedEntity}`, tautan mati, ErrorBoundary, setting diskon.

Skrip verifikasi ulang cepat setelah tiap PR (lingkungan dengan Mongo): `python seed_realistic.py && bash scripts/gate.sh --full`, lalu **restart backend dua kali** dan jalankan `python scripts/verify_data_integrity.py` — jika INV-GL-DUP-01/INV-CASH-02 belum ada, cek manual: `db.journal_entries.aggregate([{$match:{status:{$ne:"void"}}},{$group:{_id:"$source_id",n:{$sum:1},types:{$addToSet:"$source_type"}}},{$match:{n:{$gt:1}}}])`.

## 9. Sudah diperiksa dan BENAR (jangan dikejar)

- `entity_ctx` / `resolve_list_scope` / `assert_active_entity_access` / `entity_write_guard` (deny-by-default 409) bekerja; `X-Entity-Id` di luar penugasan → 403.
- Reservasi roll atomik (`find_one_and_update` dengan guard status & `length_remaining`), `inventory_balances` dibangun ulang dari roll (SSOT benar).
- 3-way match vendor bill dengan toleransi; guard lebih-bayar bill (409) bekerja.
- Interco G-6: JE penjual/pembeli seimbang, INV-IC-05 (PPN dua sisi sama) dipatuhi; `receive` menolak bila tugas gudang belum `completed`; cancel setelah dikonfirmasi wajib alasan & membalik JE.
- Idempotensi JE per `(source_type, source_id)` konsisten di semua `post_*` (masalahnya hanya lintas `source_type`, F-03/F-04).
- Batas qty retur (`assert_return_within_limits`), snapshot kebijakan retur, tautan dua arah `doc_refs` di titik lahir.
- Sesi: TTL + sliding renewal; kunci-tulis badan usaha terarsip di `current_user`.
- Tidak ada endpoint tanpa auth; tidak ada 5xx pada sweep GET.
- Semua 1.161 panggilan API frontend (kecuali U-02) punya rute backend yang cocok.
