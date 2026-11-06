> Laporan agen penyapu (disalin apa adanya; hanya path kerja dibersihkan). Verifikasi saya atas klaim terberat ada di `11_POLA_BUG_DAN_SAPUAN.md` bagian 8.

# Sapuan pola ronde 3 — konkurensi (P1), mesin status (P2), yatim/sisa hapus-batal (P3)

Instance uji terpisah (DB seed baru), kode cabang kerja @ 906a827. Repo read-only; data uji berawalan `AUDIT-`.
Skrip probe dan bukti: tidak disertakan di repositori (ada di area kerja sesi audit); skenario reproduksi ditulis lengkap pada tiap temuan.
Label bukti: **[TERBUKTI-API]** dijalankan lewat HTTP/DB · **[DARI-KODE]** hanya baca kode · **[HEURISTIK]** angka sapuan statis (dapat berisi positif/negatif palsu; batas galat ±5%).
Tidak mengulang ID `IN- PK- GL- KT- WA- PG- FN- EP-` maupun `PL-01…05` (docs/audit/11). Bila temuan memperluas ID lama, ditandai "memperluas X".

---------------------------------------------------------------------

## 1. Ringkasan eksekutif

1. **23 temuan baru (PK3-01…23): 10 Tinggi, 11 Sedang, 2 Rendah — semuanya TERBUKTI-API.** Yang paling berat: rekap upah dobel (Rp 2,7 jt dibayar untuk upah Rp 900 rb), satu rumah bisa dijual dua kali, pendapatan Rp 600 jt diakui atas deal yang sudah dibatalkan, pajak Rp 113 jt keluar kas untuk penjualan batal, dan pengingat tagihan WA tetap disiapkan untuk pembeli yang sudah membatalkan.
2. **Sensus P1 (530 endpoint mutasi):** hanya **95 (18%)** punya penjaga kuat (CAS/once/mutex/lock); **179 (34%)** "periksa kondisi lalu tulis" tanpa penjaga apa pun; pada 330 endpoint yang relevan secara transaksi (di luar 150 master/konfigurasi, 28 pratinjau, 22 tulis-murni) rasio terlindung/tidak = **95 : 179** (+56 parsial). Jalur uang membaik (59 kuat dari 158) tetapi stok, BAST/garansi, tugas Work Hub, izin, jadwal bangun, komplain **0 penjaga kuat**, dan tenaga kerja hanya `pay_payroll`.
3. **Sensus P2:** 171 penulisan `status/stage/state` pada `update_*` dengan `$set` literal; hanya **25 (15%)** menyertakan status pada filter (CAS). 146 menimpa tanpa syarat. Lompatan/mundur terbukti pada 11 dari 15 mesin status yang diuji (tabel §5).
4. **Sensus P3:** 36 endpoint DELETE + ±49 batal/void/tolak. `DELETE /deals` mencakup 21 dari 31 koleksi ber-`deal_id` (10 celah, satu **salah nama koleksi**: `pdc_cheques` ≠ `pdc_instruments`); hapus lead/unit/proyek tidak punya kaskade untuk 17/22/16 koleksi dan blocker-nya tidak mencakup mereka. Pembatalan kontrak formal tidak menutup tugas/komisi/fee/KPR/kupon.
5. Dua penyebab sistemik: (a) **dua jalur batal** (`deal_cancel` vs `cancellation_engine.decide`) dan **dua jalur hapus** (`force_delete` vs `master_delete`) dengan cakupan bersih-bersih berbeda; (b) status ditulis dengan `update_one({"id"})` tanpa prasyarat status, jadi pasangan aksi (setuju/tolak, selesai/tunda, cancel/approve) tidak eksklusif.
6. Terverifikasi baik: reservasi unit, booking, konversi pembeli, kuitansi identik, batal deal sederhana, persetujuan PO, GRN paralel, penomoran PO/BAST/kontrak (lihat §8).

---------------------------------------------------------------------

## 2. Cakupan

Diuji paralel (2–6 request serentak dengan barrier, `h.par`) dan/atau urutan tak lazim: stok manual/opname/permintaan material, PO (draft/cancel/approve/GRN), tenaga kerja (absensi, rekap upah, keputusan), perizinan, BAST (terbit/batal), klaim garansi, komplain, tugas Work Hub, jadwal bangun (verify/reject), kas bon/transfer kas (hanya untuk membedakan dari PL-02), fee marketing, change order, penyusutan/pelepasan aset, hapus kuitansi, impor data massal, `generate_units`, `build/schedules`, `block unit`, `finance/ar/{deal}/bast`, pajak, pengingat WA, serta 8 skenario hapus/batal (formal, sederhana, hapus paksa deal, hapus lead, hapus unit, hapus proyek, hapus kuitansi bernomor-bank, kupon).
Sensus: AST atas 112 router → 530 endpoint POST/PUT/PATCH/DELETE (cocok 530 di `/openapi.json`).

---------------------------------------------------------------------

## 3. CENSUS

### 3.1 Pola 1 — baca-lalu-tulis tanpa penjaga atomik [HEURISTIK + verifikasi manual 25 titik]

Klasifikasi tiap endpoint (penutupan transitif 3 tingkat; `emit/audit/notify` dikecualikan):
`1` penjaga kuat = `once/cas/transition/mutex/reserved/locked` · `2` parsial = hanya `client_ref` opsional / `upsert` / `DuplicateKeyError` / unique index · `3` **tidak dilindungi** = cek kondisi bisnis (`raise …sudah/hanya/harus…`) lalu tulis · `4` master/konfigurasi (last-write-wins, aman secara desain) · `5` tulis tanpa prasyarat (log, edit) · `0` tanpa tulis/pratinjau.

| Domain | Total | 1 kuat | 2 parsial | 3 TIDAK | 4 master | 5 tulis | 0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Uang/subkon/anggaran | 158 | 59 | 8 | 46 | 36 | 1 | 8 |
| Deal/unit/kontrak | 29 | 11 | 4 | 11 | 0 | 0 | 3 |
| Aset tetap/pinjaman/pajak | 14 | 5 | 0 | 9 | 0 | 0 | 0 |
| PO/GRN/pengadaan | 7 | 3 | 0 | 4 | 0 | 0 | 0 |
| **Stok & material** | 11 | **0** | 0 | **10** | 1 | 0 | 0 |
| **Tenaga kerja** | 7 | 1 | 1 | **3** | 2 | 0 | 0 |
| **BAST/garansi/klaim** | 7 | **0** | 4 | **3** | 0 | 0 | 0 |
| **Izin** | 6 | **0** | 0 | **5** | 0 | 1 | 0 |
| **Komplain** | 4 | **0** | 0 | **4** | 0 | 0 | 0 |
| **Tugas Work Hub** | 11 | **0** | 0 | **9** | 2 | 0 | 0 |
| **Jadwal bangun** | 30 | **0** | 6 | **15** | 6 | 0 | 3 |
| Lead & tahap lead | 22 | 2 | 1 | **18** | 1 | 0 | 0 |
| Agenda/survei | 5 | 0 | 3 | 1 | 1 | 0 | 0 |
| Proyek/unit/site plan | 33 | 3 | 3 | 8 | 13 | 6 | 0 |
| Impor/ekspor massal | 12 | 0 | 5 | 0 | 0 | 3 | 4 |
| Penomoran (konfigurasi) | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| Lain-lain (WA/portal/admin/master) | 171 | 8 | 21 | 33 | 88 | 11 | 10 |
| **TOTAL** | **530** | **95** | **56** | **179** | **150** | **22** | **28** |

Rasio transaksional (tanpa master/pratinjau/tulis-murni = 330): terlindungi kuat 95 (29%), parsial 56 (17%), **tidak 179 (54%)**.
Penomoran dokumen: seluruh ±50 pemanggil `next_number/generate` memakai `counters` + `$inc` atomik → nomor ganda **tidak** terjadi (diuji PO×6, BAST×4, UPH×3, MF×3, KG, GRN). Yang terjadi: **nomor hangus** (PK3-22).
Unique index yang menyelamatkan data tetapi mengembalikan 500 (bukan 409): `units(code)`, `labor_attendance`, `build_schedules(unit)`, `revenue_recognitions(deal)`, `asset_depreciations` (PK3-22).

Endpoint yang sudah dibuktikan bermasalah lewat uji paralel/urutan tak lazim (golongan 3 atau 5): `POST /materials/txn`, `/materials/opname`, `/materials/requisitions/{id}/issue|approve|reject`, `/labor/payrolls` (+ `submit`, `decision`), `/labor/attendance`, `/handover/issue`, `/handover/claims/{id}/decide`, `/build/items/{id}/verify|reject`, `/procurement/pos/{id}/cancel`, `/marketing/fees`, `/subcon/change-orders/{id}/approve`, `/finance/ar/receipts/{id}` (DELETE), `/complaints/{id}/respond|assign`, `/work/tasks/{id}/complete|snooze`, `/permits/alerts/scan`, `/data-mgmt/full/sessions/{id}/commit`, `/projects/{id}/units`, `/fixed-assets/assets/{id}/dispose`.

### 3.2 Pola 2 — mesin status bolong [HEURISTIK]

| Ukuran | Nilai |
|---|---:|
| Penulisan `status/stage/state/legal_stage/payment_status/construction_status` lewat `update_one/many` + `$set` literal | 171 |
| … dengan status pada FILTER (CAS) | 25 (15%) |
| … tanpa syarat status (menimpa) | **146 (85%)** di 65 dari 72 berkas |
| Terbanyak (tanpa syarat): `units` 16, `warranty_claims` 7, `tasks` 6, `build_items` 5, `contracts` 5, `cash_advances` 5, `conversations` 5, `booking_fee_invoices` 4, `payment_intakes` 4, `ar_invoices` 4 | |
| Mesin status dengan lompatan/mundur TERBUKTI (tabel §5) | 11 dari 15 yang diuji (4 lainnya sah/tidak diuji) |

(Angka koordinator di docs/audit/11 = 115; selisih karena saya ikut menghitung kolom `state/stage` dan `$set` pada engine.)

### 3.3 Pola 3 — yatim/sisa saat hapus-batal [peta rujukan koleksi + skenario]

Jumlah endpoint hapus/batal: **36 DELETE** + **±49** (cancel/void/reject/dispose/reopen/unmatch/waive/discard). Entitas induk × koleksi pemegang rujukan (hasil `refs.py`: AST insert + isi DB):

| Induk | Koleksi yang merujuk | Dicakup kaskade/blocker | Celah | Bukti |
|---|---:|---:|---:|---|
| `deal_id` — `DELETE /deals/{id}` (force) | 31 | 21 | **10**: `pdc_instruments` (nama salah `pdc_cheques`), `complaints`, `warranty_claims`, `marketing_fees`, `faktur_pajak`, `conversion_events`, `build_schedules`, `customers`, `leads`, `units`(pointer) | skenario `s_force.py`, `s_pdc.py` |
| `deal_id` — `DELETE /leads`, `DELETE unit` (deal batal dihapus MENTAH) | 31 | **0** | **31** (anak deal tak disentuh) | `s_lead.py`, `s_unit.py` |
| `lead_id` — `DELETE /leads` | 23 | 6 | **17** (`portal_users`, `wa_reminders`, `marketing_fees`, `quotations`, `coupon_redemptions`, …) | kode |
| `unit_id` — `DELETE unit` | 32 | 10 | **22** (`receipts`, `booking_fee_invoices`, `customer_deposits`, `labor_attendance`, `warranty_claims`, `wa_reminders`, …) | `s_unit.py` |
| `project_id` — `DELETE /projects` | 52 | 36 (kaskade 14 + blocker langsung/tak langsung via SPK/PO/AR) | **16**: `materials`, `material_txns`, `material_requisitions`, `boq_items`, `labor_attendance`, `labor_payrolls`, `petty_expenses`, `fixed_assets`, `cash_advances`, `site_diaries`, `withholding_docs`, … | `s_proj.py` |
| `customer_id` — `DELETE /customers` | 19 | 2 + blocker | `portal_users`, `wa_reminders`, `warranty_claims`, `unit_handovers`, … | kode |
| Pembatalan kontrak formal (`cancellation_engine.decide`) | — | menutup: AR, unit, deal, kontrak, lead | **tidak** menutup: tugas, komisi, fee marketing, KPR, `tax_records`, kupon, janji temu, dokumen, pengingat WA | `s_cancel2.py` |

Sisa berbahaya secara bisnis yang TERBUKTI: pengingat WA "DP jatuh tempo Rp 115 jt" ke pembeli batal (PK3-07), pajak batal yang bisa dibayar (PK3-06), fee marketing yang bisa disetujui untuk deal yang sudah tidak ada (PK3-09), tugas aktif ×5 (PK3-08), mutasi bank menggantung (PK3-12).

---------------------------------------------------------------------

## 4. TEMUAN BARU (urut severity)

### [PK3-01] [Severity: Tinggi] Rekap upah harian ganda: `POST /labor/payrolls` paralel membuat N rekap atas absensi yang sama; semuanya bisa disetujui dan DIBAYAR
- Label bukti: [TERBUKTI-API] (`t_labor.py`)
- Lokasi: `labor_engine.py:249-271` (cek `clash` lalu `insert_one` lalu `update_many payroll_id`), `routers/labor_router.py:131`; juga `labor_engine.py:169-185` (absensi: `find_one` lalu `insert_one`)
- Reproduksi: 2 pekerja × 3 hari absensi (total Rp 900.000). `POST /labor/payrolls` periode yang sama ×3 serentak → `[200,200,200]`: UPH/2026/0001, 0002, 0003, masing-masing Rp 900.000. `submit` + `decision approve` + `pay` ketiganya → 200. Jurnal `JV/2026/00048-50` masing-masing Dr WIP Rp 900.000 / Cr Bank. Total kas keluar **Rp 2.700.000 untuk upah Rp 900.000**. `labor_attendance.payroll_id` hanya menunjuk rekap terakhir. Pada absensi: `POST /labor/attendance` ×4 (pekerja+tanggal sama) → `[500,500,200,500]` (unique index `uq_labor_attendance` menahan data tetapi `DuplicateKeyError` tidak ditangkap).
- Hasil seharusnya: satu rekap per periode (409 untuk lainnya); absensi paralel → idempoten.
- Dampak bisnis: upah dibayar berlipat; selisih WIP proyek; tidak ada alarm (rekonsiliasi tidak memeriksa payroll↔absensi).
- Akar masalah & saran: dedup manual find→insert (P12). Kunci `once("labor.build", project_id, period_start, period_end)` + unique index parsial `(org, project_id, period_start, period_end)` untuk state ≠ rejected; `pay_payroll` sebaiknya memverifikasi bahwa semua `attendance_ids` masih menunjuk rekap ini.

### [PK3-02] [Severity: Tinggi] Stok manual: `out` langsung dan opname tidak atomik — stok negatif, opname ganda menggeser stok, `qty_issued` kehilangan pembaruan (memperluas PG-04/PG-11)
- Label bukti: [TERBUKTI-API] (`t_stock.py`, `t_req.py`)
- Lokasi: `routers/materials_router.py:183-206` (`create_txn`: baca stok → insert), `:209-232` (`stock_opname`: baca buku → insert `adjust`), `:347-392` (`issue_requisition`: `items` ditulis absolut)
- Reproduksi: (a) material stok 100 sak; `POST /materials/txn type=out qty=80` ×2 serentak → `[200,200]`, stok akhir **−60**. (b) stok 100, `POST /materials/opname physical_qty=60` ×2 → kedua respons "stok baru 60", stok sebenarnya **20** (dua `adjust −40`). (c) permintaan 10 sak; `issue` 6 sak ×2 serentak → `[200,200]`, total `out` **12 > 10 diminta** sementara `items.qty_issued` = 6 (lost update), status "sebagian".
- Dampak: persediaan negatif/ganda, opname salah mengoreksi, permintaan material dikeluarkan melebihi persetujuan.
- Saran: sama dengan PG-04 — satu fungsi `post_stock_txn(material, delta)` yang menjaga saldo lewat `find_one_and_update` pada dokumen `materials.stock` (atau kunci per material) dan menolak hasil < 0; opname hitung selisih DI DALAM kunci.

### [PK3-03] [Severity: Tinggi] BAST ganda untuk satu unit: `POST /handover/issue` paralel menerbitkan 4 BAST, masa garansi berlipat
- Label bukti: [TERBUKTI-API] (`t_bast.py`)
- Lokasi: `handover_engine.py:310-313` (`active_handover` lalu insert di `:354`), `routers/handover_router.py:61`; tanpa unique index "satu BAST aktif per unit" (hanya `uq_handover_number`)
- Reproduksi: unit baru `AUDIT-01`; `POST /handover/issue {unit_id, override:true, ...}` ×4 serentak → `[200×4]`, empat BAST (`BAST/2026/0001,2,3,4`, `state=issued`, `replay:false`). Docstring fungsi menjanjikan "unit yang sudah punya BAST aktif TIDAK melahirkan dokumen kedua".
- Dampak: dua tanda terima atas rumah yang sama, tujuh kategori garansi × 4 (pengingat garansi ganda), `units.handover_id` menunjuk yang terakhir menulis.
- Saran: unique index parsial `(org_id, unit_id)` dengan `state: "issued"`; `issue` lewat `once("handover.issue", unit_id)`.

### [PK3-04] [Severity: Tinggi] Unit terjual/booking bisa "dilepas" → satu rumah dijual dua kali (dua jalur)
- Label bukti: [TERBUKTI-API] (`t_unit.py`, `t_unit2.py`)
- Lokasi: (a) `masterplan.py:312-331` `toggle_unit_block` + `routers/masterplan_router.py:216` — pemeriksaan status hanya untuk `blocked=true`; untuk `blocked=false` unit berstatus apa pun dijadikan `available`. (b) `force_delete.py:109` — `delete_deal_cascade` mengembalikan unit `available` tanpa memeriksa apakah unit itu sekarang dipegang deal LAIN.
- Reproduksi (a): unit `AUDIT-S3-01` berstatus `booked` (booking fee lunas, kontrak berdiri). Akun `pm@sipro.co.id`: `POST /masterplan/units/{id}/block {blocked:false,reason}` → **200**, unit `available` (`booked_by_deal` masih menunjuk deal lama). `POST /deals/reserve` lead lain pada unit yang sama → **200**. DB: dua deal aktif pada satu unit (`booked` + `reserved`). Reproduksi (b): deal A dibatalkan → deal B mereservasi unit → `DELETE /deals/{A}` (hapus paksa, Direksi) → unit B menjadi `available` padahal deal B `reserved`; reservasi ketiga → 200 (dua `reserved` bersamaan).
- Dampak: penjualan ganda; booking fee pembeli pertama tak lagi melindungi unitnya.
- Saran: `toggle_unit_block(blocked=false)` hanya bila `status == "blocked"` (CAS `find_one_and_update` dengan filter status); `delete_deal_cascade` melepas unit hanya bila `reserved_by_deal/booked_by_deal/sold_by_deal == deal.id` (seperti `cancellation_engine._release_unit`).

### [PK3-05] [Severity: Tinggi] `POST /finance/ar/{deal}/bast` menghidupkan kembali deal BATAL dan mengakui pendapatan; juga lolos dari status `reserved` (memperluas FN-23)
- Label bukti: [TERBUKTI-API] (`s_cancel2.py` lanjutan; probe pada deal `AUDIT-C1`)
- Lokasi: `finance_engine.py:921-974` `recognize_revenue` (tanpa pemeriksaan `deal.status`/`contract.state`), `routers/ar_router.py:292`
- Reproduksi: deal dibatalkan formal (BTL/2026/0002, unit kembali `available`, refund terutang). `POST /finance/ar/{deal}/bast` ×3 serentak → `[200,500,500]` (unique `revenue_recognitions` menahan duplikat). Hasil: `deals.status: cancelled → completed`, `units.status: available → sold`, `payment_status: paid_off`; **`JV/2026/00070`: Dr 1-1300 Piutang Rp 600.000.000 / Cr 4-1100 Pendapatan Rp 600.000.000; Dr 5-1100 HPP Rp 420.000.000 / Cr 1-1600**; unit terkunci `sold` (reservasi baru → 409). Pada deal `reserved` tanpa AR/booking fee: `bast` → 200, deal `completed`, unit `sold/paid_off`.
- Dampak: laba semu Rp 180 jt; unit "terjual" selamanya padahal pembeli batal; piutang 1-1300 fiktif.
- Saran: `recognize_revenue` wajib `deal.status ∈ {booked}` + kontrak non-batal + gerbang pelunasan/BAST (FN-23); pakai `transition("deals", {"status":"booked"})`.

### [PK3-06] [Severity: Tinggi] Catatan pajak deal batal tetap `pending` dan dapat dibayar — Rp 113 jt keluar dari bank untuk penjualan yang tidak ada
- Label bukti: [TERBUKTI-API] (`s_cancel3.py` + `PUT /tax/records/{id}`)
- Lokasi: `routers/tax_router.py:62-134` (`update_record` tidak memeriksa `deal.status`), tidak ada pembersihan di `cancellation_engine.decide`/`deal_cancel`
- Reproduksi: deal `AUDIT-C2` (harga Rp 600 jt) dibatalkan formal; `tax_records` PPN Rp 72 jt, BPHTB Rp 26 jt, PPh Rp 15 jt tetap `pending`. `PUT /tax/records/{id} {status:"paid", ntpn:"…"}` ×3 → 200. Jurnal `JV/2026/00074-79`: Dr 6-1400 beban pajak / Cr 2-1300, lalu Dr 2-1300 / **Cr 1-1201 Bank** (total Rp 113.000.000).
- Dampak: kas keluar & beban untuk transaksi batal; SPT PPN memuat objek yang tidak ada.
- Saran: batalkan (`status: cancelled`) `tax_records` saat deal/kontrak batal; `update_record` menolak deal batal; setor hanya untuk record bersumber deal aktif/BAST.

### [PK3-07] [Severity: Tinggi] Pengingat WhatsApp "termin jatuh tempo" tetap disiapkan/dikirim ke pembeli yang kontraknya sudah DIBATALKAN
- Label bukti: [TERBUKTI-API] (`GET /reminders/candidates`, `POST /reminders/run`)
- Lokasi: `wa_reminder_engine.py:201-203` (`ar_invoices.find({"status": {"$ne": "paid"}})` — ikut menyertakan `cancelled`) dan `:209` (item `cancelled` hanya dilewati bila `status=="paid"`)
- Reproduksi: deal `AUDIT-C1` dibatalkan formal → `ar_invoices.status=cancelled`, semua item `cancelled` namun `amount−paid_amount>0`. `GET /reminders/candidates` memuat `installment_due` "DP 20% Rp 115.000.000 jatuh tempo 2026-11-06 (H-0)" ke lead `AUDIT-C1`, `blocked_reason: null`. `POST /reminders/run {kinds:["installment_due"]}` → 3 kandidat, 3 "simulasi" (di produksi: terkirim), satu di antaranya untuk invoice AR yang BATAL.
- Dampak: pembeli yang sudah batal (dan berhak refund) ditagih DP lewat WA; risiko sengketa/reputasi.
- Saran: filter `status ∈ {unpaid, partial}` dan item `status ∉ {paid, cancelled}`; sama untuk `arrears_warning` dan `warning_letters`.

### [PK3-08] [Severity: Tinggi] Pembatalan kontrak formal tidak menutup turunannya (tugas aktif, komisi, fee, KPR, kupon, janji temu) — beda dengan jalur batal sederhana
- Label bukti: [TERBUKTI-API] (`s_cancel2.py`; kupon `SIPRO2026`)
- Lokasi: `cancellation_engine.py:395-492` `decide` — tidak memanggil `_close_tasks_and_rewind_lead` maupun `release_coupon`/pembatalan komisi/fee/pajak/KPR (bandingkan `deal_cancel.py:184-209`)
- Reproduksi: setelah BTL/2026/0002 disetujui: `tasks` 4 `open` (PPJB, KYC pembeli, komponen biaya kontrak, hubungi lead) + 1 janji temu; `commissions.status=pending` (Rp 15 jt), `marketing_fees.status=submitted`, `financing_apps.status=draft`, `tax_records` 3 `pending` (lihat PK3-06), `documents` `draft`. Kupon: deal ber-kupon `SIPRO2026` (kuota 1 terpakai) → setelah pembatalan formal `coupons.used_count` tetap 1 dan `coupon_redemptions.state` tetap `used`; pada jalur sederhana kuota dikembalikan [DARI-KODE `deal_cancel.py:191`]. Jalur sederhana (`/deals/{id}/cancel`) menutup tugas (`cancelled`) — tetapi pun meninggalkan tugas lead "Hubungi lead baru" `open`.
- Dampak: sales mengerjakan PPJB untuk penjualan batal, kuota kupon hangus, antrean komisi/pajak/KPR kotor.
- Saran: satu fungsi `close_deal_dependents(deal)` dipakai kedua jalur batal (tugas, komisi, fee, kupon, KPR, pajak, janji temu, pengingat).

### [PK3-09] [Severity: Tinggi] Hapus paksa deal meninggalkan yatim — PDC (nama koleksi kaskade salah), komplain, klaim garansi, fee marketing yang masih bisa DISETUJUI
- Label bukti: [TERBUKTI-API] (`s_force.py`, `s_pdc.py`)
- Lokasi: `force_delete.py:21-27` (`"pdc_cheques"`; koleksi nyata `pdc_instruments` — `pdc_engine.py:34`), tidak ada `complaints`, `warranty_claims`, `marketing_fees`, `faktur_pajak`, `conversion_events`; `marketing_fee.py:84-88` `_assert_deal_active(None)` lolos
- Reproduksi: deal lengkap `AUDIT-F1` (pembeli, kontrak, kuitansi, fee, komplain, faktur, BAST, klaim) → `DELETE /deals/{id}?reason=…` → 200. Sisa: `complaints` 1 (`open`), `warranty_claims` 1 (`diajukan`, BAST-nya sudah terhapus; keputusan klaim → 400), `marketing_fees` 1 → `POST /marketing/fees/{id}/approve` **200** (jurnal akrual Dr beban / Cr utang fee Rp 6 jt untuk deal yang tidak ada), `faktur_pajak` 1 (`issued`), `tasks` 4 `open`, `events` 2 `pending`, `customers.deal_id` menunjuk deal hilang. PDC (`cek`, Rp 10 jt) pada deal yang dihapus: `pdc_instruments` tetap `received`, jurnal `JV/2026/00085` (Dr 1-1350 / Cr 2-1480) tetap; `clear` → 400 "Jadwal AR belum dibuat".
- Dampak: utang fee fiktif bisa dibentuk; giro/cek tercatat diterima untuk transaksi hilang; KPI komplain/garansi mengandung baris tanpa induk.
- Saran: ganti `pdc_cheques`→`pdc_instruments`; tambah `complaints, warranty_claims, marketing_fees, conversion_events` (+ jurnal PDC); `_assert_deal_active` menolak deal `None`; tes yang membandingkan daftar kaskade dengan `refs.json` (sapuan kolom `deal_id`).

### [PK3-10] [Severity: Tinggi] Change order paralel: nilai kontrak SPK kehilangan pembaruan (3 CO +Rp 30 jt, SPK hanya +Rp 10 jt)
- Label bukti: [TERBUKTI-API] (probe CO pada SPK/2026/0002)
- Lokasi: `routers/subcon_claims_router.py:499-529` (`new = old + value_delta` lalu `$set contract_value` absolut; status CO tidak di-CAS)
- Reproduksi: SPK `SPK/2026/0002` Rp 150 jt; tiga CO draft masing-masing +Rp 10 jt; `approve` ketiganya serentak → `[200,200,200]`, ketiganya `approved` (`original 150 jt → new 160 jt`), **`spk.contract_value` = Rp 160 jt** (seharusnya Rp 180 jt). Persetujuan CO yang sama dua kali paralel juga lolos (cek `status != draft` lalu tulis).
- Dampak: nilai kontrak subkon dan basis termin/retensi lebih kecil dari yang disetujui; penolakan/penyesuaian manual tak terlacak.
- Saran: `update_one({"id": spk, "contract_value": old}, ...)` atau `$inc` + `transition` CO `draft→approved`.

### [PK3-11] [Severity: Sedang] Hapus kuitansi paksa dua kali paralel: saldo kewajiban kontrak jadi −Rp 170 jt
- Label bukti: [TERBUKTI-API]
- Lokasi: `force_delete.py:133-180` `delete_receipt` (`$inc balance −x` tanpa memastikan kuitansi masih ada), `routers/ar_router.py:314`
- Reproduksi: `DELETE /finance/ar/receipts/{KWT/2026/0001}?reason=…` ×2 serentak → `[200,200]`; `contract_liabilities.balance` 170.000.000 → **−170.000.000**; respons kedua `removed:{receipts:1}` saja.
- Dampak: tie-out 2-1400 merah; bukan hanya "hapus fisik" (GL-05) tetapi juga dobel pembalikan.
- Saran: klaim kuitansi dulu (`find_one_and_delete`) lalu balikkan efeknya hanya bila hasilnya ada.

### [PK3-12] [Severity: Sedang] Hapus kuitansi paksa meninggalkan mutasi bank `matched` ke kuitansi hantu dan TIDAK bisa di-unmatch
- Label bukti: [TERBUKTI-API] (`s_bank.py`)
- Lokasi: `force_delete.py:133-180` tidak menyentuh `bank_transactions`; `bank_match.py` `unmatch` mencari kuitansi
- Reproduksi: mutasi seed Rp 212,5 jt `match` ke deal (membuat kuitansi) → `DELETE` kuitansi itu → `bank_transactions.match_state` tetap `matched` dengan `match_id` lama; `POST /bank/transactions/{id}/unmatch` → **400 "Kuitansi tidak ditemukan."** Mutasi tak dapat dicocokkan ulang maupun diabaikan.
- Dampak: rekonsiliasi bank tersangkut permanen (hanya bisa dibereskan lewat DB).
- Saran: hapus-paksa kuitansi harus melepas `match` (atau menolak bila ada match aktif); `unmatch` toleran terhadap target hilang.

### [PK3-13] [Severity: Sedang] Hapus lead/unit membuang deal batal secara mentah — kuitansi, tagihan booking fee, titipan, jurnal jadi yatim
- Label bukti: [TERBUKTI-API] (`s_lead.py`, `s_unit.py`)
- Lokasi: `master_delete.py:38-55` (`delete_lead`) dan `:103-127` (`delete_unit`): `db["deals"].delete_many(...)` — hanya deal aktif yang menjadi blocker
- Reproduksi: deal batal sederhana (booking fee refund penuh / hangus) → `DELETE /leads/{id}` atau `DELETE /projects/{p}/units/{u}` → 200 `removed:{deals:1}`. Sisa: `booking_fee_invoices` (`refunded`/`forfeited`), `customer_deposits`, `receipts` ×2 (kuitansi booking + kuitansi refund), `journal_entries` ×1 (pendapatan booking fee hangus), `tasks cancelled`, `audit_logs` — semua merujuk `deal_id` yang sudah tidak ada. Pada unit: `labor_attendance`, `warranty_claims`, `wa_reminders`, `quotations` dst. juga tidak disentuh (22 koleksi).
- Dampak: jejak keuangan putus; laporan per deal/lead tak bisa menelusuri; audit tak bisa merekonstruksi.
- Saran: blocker harus menghitung deal berapa pun statusnya bila punya dokumen keuangan; atau gunakan `force_delete.delete_deal_cascade` (dan perluas). Lebih baik "arsip" (soft-delete) daripada hapus fisik.

### [PK3-14] [Severity: Sedang] Hapus proyek tidak diblokir oleh stok, permintaan material, BoQ, absensi upah (dan — dari peta rujukan, [DARI-KODE] — kas bon, kas kecil, aset tetap) — semuanya menjadi yatim
- Label bukti: [TERBUKTI-API] (`s_proj.py`)
- Lokasi: `master_delete.py:131-190` (`project_blockers` hanya unit aktif/deal/kontrak/AR/SPK/PO/jurnal; `PROJECT_CHILD_COLLECTIONS` 14 koleksi)
- Reproduksi: proyek `AUDIT-Proyek-Hapus` dengan material + mutasi masuk 50 sak + permintaan material + item BoQ + absensi pekerja + izin; `GET …/delete-check` → `can_delete:true, blockers:{}`; `DELETE /projects/{id}` → 200 `removed:{permits:1}`. Sisa: `materials` 1, `material_txns` 1 (stok 50 sak), `material_requisitions` 1, `boq_items` 1, `labor_attendance` 1 (upah belum dibayar; `build_payroll` kini gagal "Proyek tidak ditemukan" sehingga upah tak bisa dibayar). Peta: 16 koleksi ber-`project_id` tanpa kaskade maupun blocker.
- Dampak: persediaan berharga & upah terutang hilang dari semua tampilan namun tetap di buku.
- Saran: tambahkan koleksi itu ke blocker (stok > 0, permintaan terbuka, absensi belum direkap, kas bon terbuka, aset aktif) dan ke kaskade bila kosong.

### [PK3-15] [Severity: Sedang] BAST dibatalkan: unit `booked` melompat jadi `sold`, dan BAST yang sudah batal tetap memblokir pembatalan kontrak
- Label bukti: [TERBUKTI-API] (`t_bast2.py` + skenario unit A-01)
- Lokasi: `handover_engine.py:406-409` (`prev = "sold" if deal_id else "available"`), `cancellation_engine.py:174-176` (`unit_handovers.find_one({"status": {"$ne": "cancelled"}})` — field BAST adalah `state`, bukan `status`)
- Reproduksi: unit A-01 `booked` (deal `booked`) → `POST /handover/issue` (override) → `POST /handover/{id}/cancel` → unit **`sold`** (seharusnya kembali `booked`); `POST /cancellations {contract_id}` → 400 "Rumah sudah diserahterimakan (BAST/2026/0006). Batalkan BAST lebih dahulu…" padahal BAST itu sudah `cancelled` — jalan buntu. `cancel` tiga kali paralel → `[200,200,200]` (tidak ada CAS).
- Dampak: harga/komisi terkunci karena status `sold` palsu; pembatalan kontrak tak bisa diajukan.
- Saran: simpan status unit sebelum BAST di dokumen BAST dan pulihkan dari sana; periksa `state`.

### [PK3-16] [Severity: Sedang] Siklus tugas Work Hub bolong: `PUT status` melewati bukti, tugas batal bisa "diselesaikan", tugas selesai bisa "ditunda" (dibuka lagi)
- Label bukti: [TERBUKTI-API] (`t_task.py`)
- Lokasi: `routers/work_router.py:250-263` (`update_task` menerima `status` bebas), `:266-294` (`complete_task`: tanpa cek status), `:297-303` (`snooze_task`: tanpa cek status)
- Reproduksi: tugas ber-`verify_mode=supervisor`/`proof_kind=note` (TK-06): `POST …/complete` → 400; `PUT /work/tasks/{id} {"status":"done"}` → 200, `status=done`, `proof=[]`, tanpa verifikasi. Tugas `cancelled` → `complete` → 200 `done`. Tugas `done` → `snooze` → `snoozed`. `complete` ×3 → 3 aktivitas & `outcome/completed_at` ditimpa.
- Dampak: gerbang bukti/verifikasi Work Hub dapat dilewati; tugas deal batal (ditutup `cancelled`) dihidupkan kembali.
- Saran: tabel transisi (`open→in_progress→submitted→done|in_progress`, `*→cancelled` sekali jalan) + `transition()`; hapus `status` dari `TaskUpdate`.

### [PK3-17] [Severity: Sedang] Perizinan: status bebas (rejected→approved langsung), `renew` menyetujui izin apa pun, `alerts/scan` paralel melipatgandakan notifikasi
- Label bukti: [TERBUKTI-API] (`t_permit.py`)
- Lokasi: `routers/permits_router.py:195-212` (`permit_status` menerima semua status), `:215-235` (`renew_permit` memaksa `status:"approved"`), `permit_alerts.py:56-96` (notifikasi lalu tandai `expiry_notified_on`)
- Reproduksi: izin baru → `rejected` → `approved` (200, `approved_at` terisi) → `not_started` (200); izin `rejected` + `POST …/renew {expiry_at}` → `status=approved`. `POST /permits/alerts/scan` ×3 serentak → masing-masing "3 peringatan", notifikasi **+9**, tugas +4.
- Dampak: gerbang izin (kebijakan pemblokiran pekerjaan/serah terima) bisa dipenuhi tanpa persetujuan instansi.
- Saran: graf `not_started→in_progress→submitted→approved|rejected`, `approved→expired`; `renew` hanya dari `approved|expired`; tandai `expiry_notified_on` dengan `find_one_and_update` sebelum mengirim.

### [PK3-18] [Severity: Sedang] Pasangan aksi yang seharusnya eksklusif (setuju/tolak, terbit/tolak, keputusan klaim, verifikasi/kembalikan, batal/setujui) sama-sama sukses dan meninggalkan status campur (memperluas PL-02)
- Label bukti: [TERBUKTI-API] (semua paralel 2–3 request)
- Hasil per jalur:
  | Jalur | Hasil paralel | Keadaan akhir |
  |---|---|---|
  | `materials/requisitions/{id}/approve` ×2 | `[200,200]` | 2 notifikasi |
  | `…/approve` ‖ `…/reject` | `[200,200]` | `status=approved`, `approved_by` **dan** `rejected_by` terisi |
  | `…/issue` ‖ `…/reject` | `[200,200]` | `issued` + `rejected_by`; stok berkurang |
  | `procurement/pos/{id}/cancel` ‖ `approve` (draft) | `[200,200]` | `cancelled` dengan `approved_by` terisi (cancel menimpa; `routers/procurement_router.py:211-222`) |
  | `handover/claims/{id}/decide` terima ×3 | `[200×3]` | **3 punch item**, 2 tugas untuk satu klaim (`warranty_engine.py:145-205`) |
  | `decide` terima ‖ tolak | `[200,200]` | `state=dikerjakan` + `reject_reason` terisi |
  | `build/items/{id}/verify` ×2 + `reject` | `[200×3]` | `status=rework`, event `build.item_verified` terbit **2×** + notifikasi |
  | `complaints/{id}/respond(resolve)` ‖ `assign` | `[200,200]` | 2 dari 6 percobaan berakhir `in_progress` padahal pembeli diberi tahu "selesai" |
  | `labor/payrolls/{id}/submit` ×3 | `[200×3]` | 3 notifikasi Keuangan |
  | `labor/payrolls/{id}/decision` approve ‖ reject | `[200,200]` | `rejected` (absensi dilepas) |
  Kandidat serupa [DARI-KODE]: `deals/{id}/pricing-approval` (`deals_router.py:354`), `petty_cash.approve/reject/cancel_advance` (`petty_cash.py:63-123`), `subcon_claims.verify/reject`, `quotation_engine.decide_discount` (`:506`), `allin_amend.decide_amendment` (`:94`).
- Dampak: audit "siapa yang memutuskan" kontradiktif; efek samping (event, stok, notifikasi) terjadi untuk keputusan yang akhirnya kalah.
- Saran: `idempotency.transition(coll, {id}, {"status": <asal>}, update)` pada semua pasangan; satu tabel transisi per entitas (G7 di docs/audit/11).

### [PK3-19] [Severity: Sedang] Lead dapat ditandai `lost` (lalu `recycle`/`nurturing`) saat deal-nya `booked` dengan booking fee lunas
- Label bukti: [TERBUKTI-API]
- Lokasi: `lead_lifecycle.py:30-39` (`"booking": ["lost"]` dan `gate()` untuk `CLOSED` selalu `True`), `routers/leads_router.py:441-478`
- Reproduksi: lead Ibu Maya (deal `booked`, unit A-02): `POST /leads/{id}/stage {stage:"lost",note}` → 200; `recycle` → 200; `nurturing` → 200. Deal tetap `booked`, unit `booked`, AR berjalan; funnel melaporkan lead hilang/nurturing. Override supervisor memungkinkan `acquisition→won` tanpa deal [TERBUKTI, perilaku desain "wajib alasan"].
- Dampak: pipeline & KPI konversi salah; penagihan dan komisi tetap berjalan atas lead "hilang".
- Saran: `lost/recycle` ditolak bila ada deal ber-status aktif (batalkan deal dulu); `nurturing` dari `recycle` hanya bila tak ada deal aktif.

### [PK3-20] [Severity: Sedang] Fee marketing ganda: `POST /marketing/fees` paralel membuat 3 pengajuan identik
- Label bukti: [TERBUKTI-API]
- Lokasi: `marketing_fee.py:109-117` (dedup `find_one` lalu `insert_one`; tanpa unique index)
- Reproduksi: agen aktif + deal booked; `POST /marketing/fees {agent, deal, basis:percent, value:1.0, trigger:booking}` ×3 → `[200×3]`: MF/2026/0003, 0004, 0005 masing-masing Rp 8.500.000, `submitted`.
- Dampak: tiga utang fee untuk satu penjualan bila ketiganya disetujui/dibayar (approve/pay sudah ber-CAS per dokumen, tetapi tidak antar-dokumen).
- Saran: unique index parsial `(org, agent_id, deal_id, trigger)` untuk status terbuka, atau `once("mfee.create", agent, deal, trigger)`.

### [PK3-21] [Severity: Sedang] Impor semua data: `commit` paralel menulis dokumen ber-`id` ganda; sesi yang sudah `committed` bisa di-commit lagi
- Label bukti: [TERBUKTI-API] (`t_import2.py`)
- Lokasi: `data_mgmt_full_session.py:160-244` (`commit` tidak mengklaim/memeriksa `data_import_sessions.status`; status baru ditulis di akhir `:228`)
- Reproduksi: ekspor `activities`, tambah satu baris ber-`id` baru, buat sesi, `commit {mode:update, confirm:IMPOR}` ×3 serentak → `[200×3]`, setiap respons "inserted 1"; `activities.count({id})` = **3**. Commit ulang berurutan juga 200 (sesi `committed`).
- Dampak: kunci primer ganda pada koleksi mana pun yang tak punya unique index `id`; `mode=replace` paralel dapat saling menghapus.
- Saran: klaim sesi lewat `transition(data_import_sessions, {status:"open"} → "committing")`; unique index `id` untuk koleksi tulis.

### [PK3-22] [Severity: Rendah] Jalur yang dilindungi unique index menjawab 500 (bukan 409/idempoten) dan menghanguskan nomor dokumen
- Label bukti: [TERBUKTI-API]
- Bukti: `POST /projects/{id}/units` ×3 → `[500,200,500]` (`projects_router.py:92-119`, `find_one` lalu `insert_one`); `POST /labor/attendance` ×4 → `[500,500,200,500]`; `POST /build/schedules` ×3 → `[200,500,500]`; `POST /finance/ar/{deal}/bast` ×3 → `[200,500,500]` (PK3-05). Nomor hangus: `GRN` paralel ×5 → satu menang dan empat 409 setelah `_next_number` dipanggil → nomor `GRN/2026/0019-0021` hilang (daftar GRN: 0001, 0005-0010, 0012-0018, 0022); pola sama pada `create_po` dan `transfer` (nomor diambil sebelum CAS). 
- Dampak: pengalaman buruk (500), lubang nomor pada dokumen berurutan (audit).
- Saran: tangkap `DuplicateKeyError` → 409/replay; ambil nomor setelah klaim sukses.

### [PK3-23] [Severity: Rendah] Komplain dan janji temu bisa mundur status bebas; janji temu identik tak dideduplikasi
- Label bukti: [TERBUKTI-API] (`t_compl.py`)
- Lokasi: `routers/complaints_router.py:235-255` (`update_status` menerima semua status), `:205-232` (`respond` pada komplain `resolved` mengirim WA lagi dan menimpa `resolved_at`), `routers/leads_router.py:683-691` (`appointment_status` tanpa graf)
- Reproduksi: komplain `resolved → open` 200; `respond(resolve)` ×2 pada komplain selesai → 2 WA & 2 respons; janji temu `cancelled` dst. bebas; `POST /appointments` ×3 (lead+waktu sama) → 3 janji temu.
- Saran: graf status + kunci dedup `(lead, scheduled_at)`.

---------------------------------------------------------------------

## 5. Tabel mesin status (sah = dari kode/dokumen; diterima = hasil uji server)

| Entitas | Transisi sah (sumber) | Yang SEBENARNYA diterima server (bukti) |
|---|---|---|
| **Lead** `lead_stage` | `acq→nurt\|lost\|recycle; nurt→appt\|booking\|lost\|recycle; appt→booking\|nurt\|lost\|recycle; booking→lost; recycle→nurt\|acq\|lost; lost→recycle; won` hanya dari event deal (`lead_lifecycle.py:30-39`) | `booking→lost` saat deal `booked` berbayar (200), lalu `recycle→nurturing` (PK3-19). Override supervisor `acq→won` tanpa deal & `won→acq` (200; desain, wajib alasan). |
| **Deal** `status` | `reserved→booked→completed`; `reserved\|booked→cancelled` (CAS di `deal_cancel`/`book`) | `reserved→completed` dan **`cancelled→completed`** lewat `POST /finance/ar/{deal}/bast` (PK3-05); `cancelled` dapat dibuat lewat dua jalur dengan bersih-bersih berbeda (PK3-08). Pembatalan formal ‖ hapus paksa tidak diuji. |
| **Unit** `status` | `available→reserved→booked→sold→handed_over`; `blocked↔available`; dilepas oleh batal/hapus deal | `booked→available` lewat `block {blocked:false}` (PK3-04); `booked→sold` lewat BAST-batal (PK3-15); `reserved(B)→available` lewat hapus deal A (PK3-04); `cancelled→sold` lewat BAST (PK3-05). 16 penulis `units.status`, 3 di antaranya tanpa filter status. |
| **Kontrak** `state` | `draft→active→…→cancelled` (`contract_ops.activate`, `cancellation_engine.decide`) | aktivasi kontrak batal ditolak (400, sah); `costs` pada kontrak batal ditolak (400, sah). `legal`/KPR-stage pada kontrak batal tertahan gerbang lain (DP/tahap sebelumnya) sehingga cek "batal"-nya tidak terbukti. Dokumen kontrak `draft` tetap tersisa (PK3-08). |
| **Dokumen** (`documents`) `status` | `draft→final→signed` | `finalize`/`sign` tidak diuji secara urutan tak lazim (lihat §9). `sign` memakai `mutex` (kuat). |
| **PO** `status` | `draft→approved→partially_received→received→closed`; `cancelled` dari `draft\|approved` | `draft+approved ‖ cancel` → `cancelled` dengan `approved_by` (PK3-18); `cancel` dari `partially_received` (PG-06); retur menghidupkan PO batal (PG-05). `approve` ×2, `GRN` ×5 → CAS bekerja. |
| **GRN** | tanpa status; qty ≤ sisa PO | CAS `reserved` pada PO mencegah over-receipt (1 menang, 4 kalah 409) — OK; nomor hangus (PK3-22). |
| **Tagihan AP** | `pending_approval→approved→paid\|void` | tidak diuji ulang (ronde 1: CAS+`once`); `procurement.create_bill` ber-`reserved`. |
| **Tugas** `status` | `open→in_progress→submitted→done`; `submitted→in_progress` (tolak); `snoozed`; `cancelled` | `PUT status=done` melewati bukti+verifikasi; `cancelled→done` (`complete`); `done→snoozed` (`snooze`) (PK3-16). |
| **Izin** `status` | `not_started→in_progress→submitted→approved\|rejected→expired` | semua status ke semua status (200), `renew`→`approved` dari `rejected/not_started` (PK3-17). |
| **BAST** `state` | `issued→cancelled` | 4 BAST aktif per unit (PK3-03); `cancel` ×3 semuanya 200; BAST batal masih memblokir pembatalan kontrak (PK3-15). |
| **Klaim garansi** `state` | `diajukan→dikerjakan\|ditolak→selesai→diverifikasi→ditutup` | `decide` terima ×3 → 3 punch; terima‖tolak → hibrida (PK3-18). Transisi sequential `complete/verify/close` ber-cek status (sah). |
| **Jadwal bangun/langkah** `status` | `blocked→ready→in_progress→submitted→done\|rework`; `hold/resume` | `verify` ×2 dan `reject` bersamaan semua 200 → akhir `rework` dengan 2 event `verified` (PK3-18). Transisi sequential ber-cek (sah). |
| **Rekap upah** `state` | `draft→submitted→approved→paying→paid`; `rejected` | N rekap per periode (PK3-01); `submit` ×3, `decision` bersamaan (PK3-18). `pay` ber-CAS (sah). |
| **Komplain / janji temu** | `open→in_progress→resolved` | `resolved→open`, janji temu bebas (PK3-23). |
| **Transfer kas / kas bon / fee** | lihat PL-02 | `fee` approve‖reject → CAS memenangkan satu (409 untuk approve) — OK; transfer = PL-02. |

---------------------------------------------------------------------

## 6. Verifikasi arah-berlawanan: apa yang BENAR

Terverifikasi OK (dijalankan paralel/urutan tak lazim):
- `POST /deals/reserve` ×3 lead berbeda ke satu unit → `[409,200,409]`, 1 deal.
- `POST /deals/{id}/book` ×3 → `[409,409,200]` (CAS); `POST /deals/{id}/convert` ×3 NIK sama → `[200×3]`, 1 kontrak (KT-02 tertutup).
- `POST /finance/ar/receipts` identik ×3 → `[200,409,409]` (`once`); `POST /deals/{id}/cancel` ×3 → `[200,409,409]` (CAS IN-04).
- `POST /procurement/pos/{id}/approve` dan `…/grns` paralel: 1 menang, sisanya 409; tidak ada over-receipt/stok ganda.
- Penomoran: PO×6, BAST×4, UPH×3, MF×3, KG, GRN semuanya unik (counter `$inc`); gerbang BAST tanpa `override` pada unit belum dibangun → 409 (daftar periksa bekerja).
- `approve` fee marketing ber-CAS (`approve‖reject` → `[409,200]`), `deals/{id}/cancel` pasca-termin diarahkan ke pembatalan formal (400 sah), `commission/approve` pada deal batal ditolak (400), `receipt` pada deal batal ditolak (400), `kontrak batal` tidak bisa diaktifkan/diberi biaya (400).
- Kupon: kuota total atomik (`find_one_and_update` dengan `used_count < quota`).
- Sequential `complete/verify/close` klaim garansi, `verify/reject` jadwal bangun, `approve/pay` payroll mengecek status dengan benar.

---------------------------------------------------------------------

## 7. Bukti ringkas untuk ID yang sudah tercatat

- PG-04: `POST /materials/txn type=out` dan `/materials/opname` adalah dua titik tambahan dengan akar sama (PK3-02). Klaim "permintaan di-issue 2×" di PG-04 tetap berlaku; kini terukur pula `out` > diminta.
- PG-05/06: PO `cancelled` dapat dihidupkan; kini terbukti juga lewat `cancel` yang menimpa `approve` (PK3-18).
- FN-23: BAST tanpa gerbang → terbukti lebih luas: deal `cancelled` dan `reserved` (PK3-05).
- FN-24: faktur pajak untuk deal batal → melengkapi dengan `tax_records` yang dibayar (PK3-06).
- PL-02: transfer approve‖reject — diverifikasi ulang `status=posted` + `reject_reason`; jurnal terbit 1×.
- Dugaan gugur: "double-approve transfer menjurnal dua kali" → salah (jurnal terbit sekali; `source_event` unik menyelamatkan).

---------------------------------------------------------------------

## 8. Tidak bisa diverifikasi / tidak sempat

- Pasangan CAS tidak diuji (hanya [DARI-KODE]): `pricing-approval`, `petty_cash` (approve/reject/cancel vs `disburse`), `subcon_claims.verify/reject`, `quotation.decide_discount`, `allin_amend.decide_amendment`, `fund_request.approve/reject`, `financing.slik/disburse`, `documents.finalize/sign` urutan tak lazim, `inspections.finalize`, `construction.progress`.
- Race `reject_advance` vs `disburse_advance` (jendela baca–tulis sangat sempit; [DARI-KODE] bahwa `reject` menimpa `disbursed` bila membaca sebelum klaim) — tidak berhasil dibuktikan paralel.
- Aliran WA nyata (mode simulasi): dampak PK3-07 di produksi diturunkan dari hasil "simulasi".
- Urutan pengingat tunggakan (`arrears_warning`) pada deal batal: tak bisa diuji tanpa memajukan jam; filter pada baris 294 (`unpaid|partial`) tampaknya benar.
- Kaskade `DELETE /customers` dan `portal_users`: hanya dari peta rujukan; blocker (kontrak/AR/KPR) menutup sebagian besar skenario.
- Uji pada multi-worker (satu instance uvicorn). `data_mgmt_full_session` menyimpan sesi di disk lokal; perilaku multi-proses tak diuji.
- `PUT /fixed-assets/assets/{id}/dispose` paralel dengan nominal berbeda: respons ganda 200, satu jurnal; nilai `disposal_proceeds` pada dokumen dapat berbeda dari jurnal (tidak terbukti beda).

## 9. Pertanyaan terbuka

1. Apakah `block {blocked:false}` pada unit non-blokir memang dimaksudkan sebagai "lepas paksa unit"? Jika ya, perlu alasan+persetujuan dan pembatalan deal terkait.
2. Pembatalan kontrak formal vs sederhana: apakah kupon dan komisi memang berbeda perlakuannya? (PK3-08 mengandaikan harus sama.)
3. Siapa pemilik keputusan untuk hapus fisik deal batal oleh `DELETE /leads`/`unit` — apakah soft-delete/arsip dapat menggantikannya?
4. Apakah satu BAST per unit memang aturan bisnis (docstring `handover_engine.issue` berkata ya)? Bila ada kasus BAST kedua sah, perlu konsep "BAST pengganti".
