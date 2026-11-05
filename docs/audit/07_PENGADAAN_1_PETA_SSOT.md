# Audit PENGADAAN ronde 2 — Bagian A: Peta alur & SSOT (instance #7: UI :3041, API :8041, DB sipro_proc)

Auditor: stream "pengadaan". Repo read-only; data uji berawalan `AUDIT-`. Label bukti: [TERBUKTI-UI] [TERBUKTI-API] [DARI-KODE].
Folder skrip: (skrip uji tidak disertakan di repo) (t1..t17 = skenario API, ui1..ui9.js = Playwright). Screenshot: `img/pengadaan/`.

## A.1 Peta alur (kode eksak)

```
material_requisitions ──approve(PM)──► [issue → material_txns out]            routers/materials_router.py:316,346
        │  (shortage → to-po)                                                  procurement_extra.py:29,56 ; routers/procurement_extra_router.py:80,98
        ▼
purchase_orders (draft) ──approve(finance/owner; pembuat≠penyetuju; >500jt owner)  routers/procurement_router.py:87,178 ; :32
        │ po_type = material | subcon | general   (menentukan akun GL nanti!)    gl_engine.py:376-379
        ▼
grns (+ material_txns in, PO.items.received_qty, PO.received_value, PO.status)   procurement_router.py:240-324
   └─ grn_returns (+ material_txns out, PO.received_value turun)                 procurement_extra.py:127-197
        ▼
ap_invoices (pending_approval; PO.billed_value += claimed; 3-way match)          procurement_router.py:352-437 ; procurement_extra.py:210-241
        ▼ approve (pembuat≠penyetuju)                                            routers/ap_router.py:109 ; finance_ap.py:59
event ap.approved ──► JURNAL (satu-satunya jembatan pengadaan→GL)                gl_engine.py:367-398
        ▼ bayar / bayar+PPh (penyetuju≠pembayar, cek saldo kas, anti-ganda)      ap_router.py:127,146 ; finance_ap.py:105
payments_out + event ap.paid ──► JURNAL                                          gl_engine.py:401-419
```
Jalur lain yang bersinggungan: master vendor + daftar harga (`vendor_engine.py`, `vendors_router.py`), stok manual (`/materials/txn`, `/materials/opname`), transfer antar proyek (`stock_control.py`), anggaran (`budget_engine.py`, `boq_router.py`, `metrics/project.py`), tagihan manual tanpa PO (`/finance/ap/bills`), pajak masukan (`tax_engine.py:32`).
Tidak ada: endpoint ubah PO, batal/void GRN, nota kredit/koreksi tagihan, uang muka PO material (1-1800 hanya untuk SPK), pencairan retensi tagihan PO/manual, lampiran/surat jalan pada GRN.

## A.2 Tabel peristiwa → dokumen → jurnal GL → dampak subledger lain
(Hasil uji nyata; angka dari `trial-balance` sebelum/sesudah; skrip t2–t10)

| Peristiwa | Dokumen yang berubah | Jurnal GL? | Subledger/dampak lain |
|---|---|---|---|
| Permintaan material dibuat/disetujui | `material_requisitions` | Tidak | – |
| Permintaan → PO (`to-po`) | PO draft; `req.items.qty_po`; `po_ids` | Tidak | – |
| PO disetujui | PO.status | Tidak (tidak ada akuntansi komitmen — wajar) | notifikasi |
| GRN (penuh/parsial) | `grns`, PO.items.received_qty, PO.received_value, status; `material_txns` in (+unit_price) | **TIDAK** (1-1400 tetap 325.000.000 setelah GRN 300 sak = Rp 18 jt; tidak ada akrual GRNI) | stok +300, valuasi +Rp 18 jt |
| Retur GRN | `grn_returns`; `material_txns` out; PO.received_value turun; GRN.returned_value | **TIDAK** (tidak ada kredit vendor) | stok turun |
| Tagihan dari PO dibuat | `ap_invoices`(pending), PO.billed_value | Tidak | **realisasi anggaran & PPN-masukan-estimasi langsung bertambah** walau belum disetujui |
| Tagihan disetujui | `ap_invoices.status` | **Ya**: Dr `1-1400` (PO material) / `6-1300` (PO general) / `1-1600` (subcon, manual) = klaim; Cr `2-1100` net; Cr `2-1200` retensi (+ potongan) → JV/2026/00048: 1-1400 +18.050.000 / 2-1100 +18.050.000 | – |
| Bayar (parsial/penuh) | `payments_out`, `ap_invoices.paid` | **Ya**: Dr 2-1100 / Cr bank (net) | cek saldo kas OK |
| Bayar + PPh | + `withholding_docs` (bukti potong) | **Ya**: Dr 2-1100 4.000.000 / Cr 1-1201 3.920.000 / Cr 2-1300 80.000 | – |
| Stok keluar ke pekerjaan (`issue`/`txn out`) | `material_txns` out; `req.qty_issued`; `materials.consumed_qty` | **TIDAK** (1-1400 tetap 343.050.000 walau stok fisik 0; 1-1600 tidak naik) | cek RAB (qty) |
| Opname / koreksi stok | `material_txns` adjust | **TIDAK** (selisih tak berjurnal, tak bernilai) | – |
| Transfer antar proyek | `material_transfers` + 2 `material_txns` | **TIDAK** (tanpa dimensi proyek di GL pula) | – |
| PO dibatalkan | PO.status | Tidak (dan tagihan/GRN/stok TIDAK ikut dibatalkan) | `qty_po` permintaan tidak dilepas |
| Tagihan manual tanpa PO | `ap_invoices` | Ya → 1-1600 | melewati 3-way match |

## A.3 SSOT per besaran — sumber kebenaran vs duplikat yang bisa berbeda

| Besaran | Sumber kebenaran yang SEHARUSNYA | Sumber lain yang ada (bisa berbeda) | Bukti selisih |
|---|---|---|---|
| Identitas vendor | `vendors` (master, `vendor_engine.py`) | (1) string `purchase_orders.vendor`, `ap_invoices.vendor` (join berdasar NAMA: `vendor_engine.py:58,73`); (2) `subcontractors`; (3) picker UI `/reference/vendor` = daftar string dinamis dari `subcontractors`+`ap_invoices`+`purchase_orders` (`reference_groups.py:503-510`), BUKAN master | PG-08: PO via UI tanpa `vendor_id`; vendor master VND-02/03 tak muncul di picker; dua vendor sama nama → kartu usage identik, Σ "Nilai PO" ganda (Rp 109,7 jt vs aktual 61,1 jt) [TERBUKTI-UI `40-vendors.png`] |
| Harga satuan | `PO.items.unit_price` (snapshot saat PO) | `vendor_prices` (acuan; `reference_price` = MIN semua baris aktif, `vendor_engine.py:174-199`); `stock_control.average_cost` (rata-rata semua `in`); `budget_engine.material_prices` (rata-rata semua PO termasuk draft/batal, `budget_engine.py:388`) | tiga rumus "harga rata-rata" berbeda; harga acuan bisa berasal dari PO draft (PG-20) |
| Material (master) | seharusnya 1 master org-wide | `materials` PER PROYEK (`project_id`), kode unik per proyek; `vendor_prices.material_id` mengikat ke material proyek tertentu | PG-20: material sama di Proyek B → `no_reference`, daftar harga tak berlaku |
| Qty dipesan | `PO.items.qty` | `req.items.qty_po` (denormalisasi, tak dilepas saat PO batal; salah hitung paralel) | PG-21 |
| Qty diterima | `Σ grns.items.qty_received − Σ grn_returns` | `PO.items.received_qty` (ditulis absolut, rusak oleh retur paralel); `Σ material_txns in` (stok) | PG-04: retur paralel → retur 130 sak dari 100 diterima; PO.received_qty=20 (seharusnya 0) |
| Qty/nilai ditagih | `Σ ap_invoices(po_id).claimed` | `PO.billed_value` (hanya Rp, tak pernah dibalik; melebihi total PO via toleransi/override) | PO/0003 total 18.000.000 billed 18.050.000; PO/0017 total 20 jt billed 23 jt (override) |
| Nilai PO | `PO.total` | `PO.received_value`, `billed_value`; **tidak ada** nilai persediaan di ledger | PG-12: total bisa negatif/0 |
| Stok per material/proyek | `Σ material_txns` (in − out ± adjust) | `materials.consumed_qty` & `over_budget` (tersimpan, basi); `/materials/{id}/budget` (hitung live) | PG-22: list 0/False vs live 240/True |
| Nilai persediaan | seharusnya GL `1-1400` = Σ stok×harga | `stock_control.valuation` (stok × rata-rata penerimaan; negatif dibuang → Rp 0); GL `1-1400` hanya naik dari AP | GL 471.850.000 vs valuasi Rp 0 (PG-16) |
| Utang vendor | GL `2-1100` = Σ `ap_invoices` (net−paid) disetujui | `vendor_usage.bill_outstanding` (termasuk pending), `/finance/ap/aging` | **tie-out OK**: GL 731.700.000 = aging = finance/summary; kartu vendor 26.002.000 (beda definisi) |
| Retensi vendor | `2-1200` | `ap_invoices.retention_held`; `subcon_retentions` (hanya termin SPK) | retensi tagihan PO tak punya baris retensi → tak bisa dicairkan (PG-10) |
| Komitmen vs RAB | satu definisi | **5 definisi**: `/budget/summary` (budget_engine), `/boq/summary` (`boq_router.py:59-80`), `/boq/control` (opname.cost_control), PRJ-09 (`metrics/project.py:258`), `/budget/unmapped` (jumlah PO+AP) | Proyek A, RAB Rp 472 jt: komitmen 43 jt / 863,5 jt / 226 jt / 84,3 jt (PG-02) |
| Realisasi biaya proyek | ledger | `ap_invoices.project_id` (claimed termasuk pending); `PO.billed_value` prorata baris; GL **tanpa** `project_id` (0 dari semua jurnal pengadaan) | PG-02, PG-03 |
| PPN masukan | akun pajak masukan GL | `tax_engine.ppn_input` (worksheet: Σ semua tagihan × rate/(100+rate), termasuk pending) | PPN masukan Rp 119,4 jt di SPT-summary, 0 di GL (PG-15) |

## A.4 Pemetaan peristiwa → akun (hardcode `gl_engine._gl_ap_approved`)
- `po_type=material` → Dr 1-1400; `general` → Dr 6-1300; `subcon`/tanpa PO/lain → Dr 1-1600 (didahului pelunasan akrual 2-1700). **Klasifikasi ditentukan tipe PO yang diketik pengguna, bukan isi baris** (PG-17).
- Tidak ada akun/transaksi untuk: GRNI (barang diterima belum ditagih), pemakaian persediaan (1-1400 → 1-1600/5-1100), selisih opname, selisih harga (PPV), PPN masukan, uang muka vendor material, nota kredit pembelian.
- Tidak ada dimensi proyek pada jurnal (`project_id: None`, terbukti pada JV/2026/00052 dst.) → laba/WIP/HPP per proyek tidak bisa dibangun dari GL.
