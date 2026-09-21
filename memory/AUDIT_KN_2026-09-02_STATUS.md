# STATUS AUDIT INDEPENDEN 2026-09-02 — verifikasi ulang & perbaikan (sesi 2026-09-02b)

> Sumber: `memory/AUDIT_KN_2026-09-02_owner.md` (dokumen pemilik). Setiap butir diverifikasi ulang
> terhadap kode **dan** DB seed sebelum diperbaiki. Bukti runtime: `backend/test_audit_2026_09_02_poc.py`
> (21/21), testing agent `test_reports/iteration_292.json` (17/17 backend + 3/3 frontend),
> `backend/tests/test_iter292_*.py` (re-runnable).

## Hasil verifikasi

| # | Temuan | Verifikasi | Status | Perbaikan |
|---|---|---|---|---|
| **F-01** | Pendapatan/HPP SO hanya dijurnal saat restart | **VALID** — `dispatch_task` & `ar_receipt_service.create_receipt` tidak memanggil GL | ✅ DIPERBAIKI | `gl_service.post_order_revenue_and_cogs()` dipanggil saat dispatch SJ & setelah alokasi kwitansi AR. Invarian baru **INV-GL-REV-01**. Kebijakan pengakuan (B-01) TIDAK diubah — menunggu keputusan pemilik. |
| **F-02** | Backfill menghentikan startup bila periode tertutup | **VALID** — `post_sales_order` melempar `ClosedPeriodError` tanpa penangkap di loop | ✅ DIPERBAIKI | `backfill_journals()` per-dokumen try/except → `skipped_closed[]`/`errors[]`; `bootstrap.py` membungkus panggilan; `POST /gl/sync` melaporkan keduanya. |
| **F-03** | Tagihan jasa makloon dijurnal dua kali (Hutang dobel) | **VALID di DB seed**: 6 JE duplikat, Hutang Usaha lebih Rp 3.481.500 (persis angka audit) | ✅ DIPERBAIKI + DIMIGRASI | `post_vendor_bill` menolak `bill_type=makloon_service` & `any_posting_for()`; backfill mem-filter. `scripts/migrate_reverse_duplicate_backfill_je.py --apply` membalik 6 JE (append-only). Seed bersih + 2× restart → 0 duplikat. Invarian **INV-GL-DUP-01**. |
| **F-04** | `gl_posted:true` diabaikan backfill kas | **VALID (kode)** — 5 penulis, 0 pembaca | ✅ DIPERBAIKI | `post_cash_transaction` & backfill melewati `gl_posted:true`. Invarian **INV-CASH-02**. |
| **F-05** | Kwitansi AR ke order pelanggan/PT lain | **VALID** — `_apply_to_order` tak mengecek pemilik | ✅ DIPERBAIKI | `_validate_allocation_target()`: pelanggan lain → 400, badan usaha lain → 403; auto-alokasi ikut disaring per entitas. |
| **F-06** | Pembayaran yatim bila alokasi ke-2 gagal | **VALID** | ✅ DIPERBAIKI | Semua alokasi divalidasi dulu (tanpa menulis); bila tetap gagal di tengah → `_unapply_receipt()` mencabut yang sudah tertulis. Invarian **INV-AR-02**. |
| **F-07** | `simulate-payment` tanpa pagar lebih-bayar & `paid_total` tak sinkron | **VALID** | ✅ DIPERBAIKI (minimal) | Tolak order lunas / lebih-bayar (400); `$inc paid_total`. Endpoint & tombol UI tetap ada (penghapusan menunggu keputusan). |
| **F-08** | Netting satu arah tanpa piutang balik | **VALID** | ✅ DIPERBAIKI | Guard: netting > piutang balik terbuka → 400; netting **mengkonsumsi** piutang balik FIFO (`netted_against[]`, `settled_amount` dokumen balik + saldo ICA disegarkan); metode bawaan → `transfer` (schema + modal). |
| **E-01** | `stock-breakdown` membocorkan SO utuh PT lain | **VALID** | ✅ DIPERBAIKI | `apply_entity_scope(mode="allowed")` + proyeksi ringkas (tanpa harga/alamat/pembayaran). |
| **E-02** | `cycle_count_sessions` SCOPED tapi list `find({})` & detail tanpa cek | **VALID** | ✅ DIPERBAIKI | `resolve_list_scope` di daftar; `assert_active_entity_access` di detail/update/approve/reject; sesi baru distempel `entity_id`. |
| **U-01** | Ganti badan usaha tidak refetch | **VALID** | ✅ DIPERBAIKI | `<AppViewRouter key={selectedEntity}>`. |
| **U-02** | "Buka tampilan cetak" → rute tidak ada | **VALID** | ✅ DIPERBAIKI | `GET /api/documents/{id}/print` (HTML, cek izin + entitas). |
| **U-04 / P0-1** | Tab Audit mematikan SPA | **VALID** | ✅ DIPERBAIKI | `JSON.stringify(log.after ?? log.details ?? {})`; `components/ErrorBoundary.jsx` membungkus `AppViewRouter`. |
| Gate | `INV-CFG-01` merah setelah restart (`__migrations__:as01_value_approval`) | **VALID** (bug gate, pra-eksisting) | ✅ DIPERBAIKI | `audit_config_wiring.py` mengabaikan scope `__migrations__`. |

## Diverifikasi VALID tetapi DITUNDA (perlu keputusan pemilik / desain lebih besar)

| # | Temuan | Alasan ditunda |
|---|---|---|
| **B-01 / F-01 (kebijakan)** | Pengakuan pendapatan "shipped ATAU paid" tidak lazim | Pilih kebijakan: (a) saat kirim + uang muka sebagai kewajiban, atau (b) saat lunas. Menyentuh COA & laporan. |
| **F-09** | Retur penjualan tanpa JE (kalau retur bukan via CN) | Perlu peta alur retur & akun pembalik HPP. |
| **F-10** | Nota debit `at_cost` tanpa dampak persediaan/HPP | Perlu kebijakan biaya (harga jual vs. cost). |
| **F-11 / F-12 / F-13** | Retur pembelian, PPN masukan `tax_input`, PO tanpa GR | Desain akuntansi pajak & GR; F-13 sudah ada TODO di kode. |
| **F-14** | Deposit tidak ada `aging`/`refund` | Fitur baru. |
| **F-15** | Nota debit pelanggan menambah AR tanpa dokumen jual | Kebijakan bisnis. |
| **F-16 / F-17** | Kontrabon: Σ potongan > tagihan; `paid_amount` tidak sinkron | Perlu pembacaan alur kontrabon penuh. |
| **D-01 / D-02 / D-03** | Penomoran `count()+1` rawan balapan; `ICA` clobber; pembulatan | D-01 perlu migrasi counter atomik lintas 80+ koleksi (skrip terpisah). |
| **U-03 / U-05** | Toast redundan; label mode uji | Kosmetik. |
| **P1-1..P1-3, L-*, G-*, X-*** (AUDIT_TEMUAN_2026-09-02.md) | Backlog sesi sebelumnya | Belum disentuh — menunggu prioritas pemilik. |

## Cara jalankan ulang bukti
```bash
python backend/test_audit_2026_09_02_poc.py          # 21 asersi runtime (mutasi so_006 → jalankan seed_reset setelahnya)
cd backend && python -m pytest tests/test_iter292_*.py -n0
python scripts/verify_data_integrity.py               # gate 246 PASS, termasuk INV-GL-DUP-01 / INV-CASH-02 / INV-AR-02 / INV-GL-REV-01
python scripts/migrate_reverse_duplicate_backfill_je.py --report
```
