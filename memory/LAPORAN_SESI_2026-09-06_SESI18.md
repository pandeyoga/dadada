# Laporan Sesi 18 — 2026-09-06 (Ratchet INV-ATOMIC-01 24 → 0)

## Diminta
"Bisakah ini sampai 0" → pilihan (a) sekali jalan: semua 24 endpoint multi-koleksi ditinjau.

## Mekanisme per endpoint
| Endpoint | Mekanisme |
|---|---|
| esign `/verify` | klaim `esign_requests` (pending) sesudah OTP valid; finish_set verified |
| esign `/request` | ditinjau: hanya `esign_requests` ditulis |
| fixed-assets run-depreciation | CAS per aset `depreciation_periods $addToSet` |
| hr payroll runs | kompensasi: run ganda / slip gagal → `rollback_run` |
| input-tax create / cancel | klaim `vendor_bills` / `tax_invoices_in`; finish_set |
| inventory putaway | ditinjau: bin idempoten + mutasi qty 0 |
| landed-cost approve / pay | klaim voucher; mark_failed bila alokasi/kas gagal; finish_set (+$inc) |
| makloon receive / record-service | klaim `makloon_orders`; replace_one tanpa lock + release; mark_failed bila tarif gagal sesudah konsumsi |
| loading-check complete | klaim sesi (open); finish_set |
| product-templates DELETE | klaim; release bila detach gagal; delete_one |
| RFQ award | klaim (open); release/mark_failed; finish_set awarded |
| R&D issue-material | CAS roll status + length_remaining |
| SO mark-delivered | `_transition` CAS |
| sales-return → create-purchase-return | klaim (linked_purchase_return_id kosong); finish_set |
| sample-requests POST | kompensasi: task gagal → request dihapus |
| request-credit-approval | klaim `sales_orders`; finish_set credit_hold |
| special-order create-pr / create-sku | klaim (linked_pr_id / linked_product_id kosong); release; finish_set |
| users POST / PATCH | kompensasi (POST) / ditinjau idempoten (PATCH) |
| warehouse-sites seed-blueprint | ditinjau upsert idempoten |

## Bukti
- Guard 91 cek hijau, self-test hijau, baseline 0. Gate `--quick` hijau.
- `scripts/probe_sesi18.py` ALL PASS (409 saat terkunci, kunci lepas, balapan 2× → satu tulisan). Probe 16/17 regresi PASS.
- Testing agent iteration_336: 14/14 PASS (`backend/tests/test_sesi18_regression.py`).

## Catatan
- Guard diperluas: `raise 4xx` yang didahului `mark_failed(` ≤3 baris bukan pelanggaran (saga gagal sesudah tulisan turunan → kunci sengaja dibiarkan).
- `saga_locks.LOCKED_COLLECTIONS` + label FE Kunci Saga: +11 koleksi.
- Status: shipped + testing-agent verified, belum dikonfirmasi pengguna.
