# LAPORAN SESI 2026-09-05 — SESI 8: ratchet 54 → 51 · label potongan · peta paginasi

## 1. Ratchet INV-ATOMIC-01 (54 → 51)
| Endpoint | Klaim | Prasyarat | Bukti |
|---|---|---|---|
| `POST /crm/leads/{id}/convert` | `crm_leads` (service `convert_lead`) | `customer_id` kosong | kunci → 409; 2× bersamaan → `[200, 400]`, **tepat 1 pelanggan** lahir |
| `POST /purchase-returns/{id}/goods-back` | `purchase_returns` (service `goods_back`) | `supplier_status != goods_back`, sesudah `assert_transition` | kunci → 400 transisi-dulu / 409 |
| `POST /putaway-orders/{id}/resolve-exception` | `putaway_orders` (service `resolve_exception`) | sesudah target item exception ditentukan | kunci → 409; 2× bersamaan → `[200, 409]` |
- `saga_locks.LOCKED_COLLECTIONS` + `crm_leads` (panel: "Prospek (lead)"). Guard 36 cek PASS, `BASELINE_UNREVIEWED = 51`.
- `simulate-payment` (invoices.py) sengaja belum: simulasi, bukan tulisan produksi — kandidat "compensate/log_only" sesi berikutnya.

## 2. Cetak label potongan (HP gudang)
- `MobileTaskActions.printSampleLabel()` — sesudah DIPOTONG muncul tombol **Cetak label potongan** (testid `mw-sample-print-{task}`): jendela cetak 58×40 mm berisi **nomor roll anak (besar)**, pelanggan, produk·SKU, **panjang + satuan**, roll asal, nomor SMP/SO, tanggal.

## 3. Peta lacak lapangan per halaman
- `LiveTrackingView.loadTrail()` menarik `/hr/field-tracks?page=&page_size=500` **halaman demi halaman** (maks 40 halaman = 20.000 titik), garis diperpanjang tiap halaman tiba (`setLatLngs`), `fitBounds` hanya pada halaman pertama; teks `live-trail-info` "Memuat jejak… n/total titik".

## 4. Bukti
- `scripts/probe_sesi8_ratchet.py` **10/10 PASS** (self-clean). Testing agent: `test_reports/iteration_319.json` (temuan 1 bug: tombol cetak hilang karena kartu tugas unmount) → perbaikan: banner hasil + tombol cetak diangkat ke `TaskList` (`mw-sample-done-{task}`) → retest `iteration_320.json` **PASS**.
- Self-test guard atomic-claim: fixture "service nyata TANPA klaim" dipindah ke `putaway_order_service.dispatch` (karena `resolve_exception` kini berklaim).
