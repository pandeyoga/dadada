# Audit PENGADAAN ronde 2 — Bagian B: Temuan (urut severity)

Instance #7 (UI http://localhost:3041, API http://localhost:8041, DB sipro_proc). Proyek uji: "Cluster Asri Blok A" (id 7e0c2dbe…) dan "AUDIT-Proyek B". Akun: pm/site/finance/finlead (manajer keuangan)/owner/superadmin. Semua uang dalam Rp.py`, `ui*.js`; screenshot (tidak disertakan di repo)
Konvensi angka GL: `GL(kode)` = saldo `trial-balance` sebelum → sesudah.

---
### [PG-01] [Severity: Kritis] Persediaan material tidak pernah berjurnal selain saat tagihan; `1-1400` hanya naik; biaya material tak pernah masuk WIP/HPP
- Label bukti: [TERBUKTI-API] + [DARI-KODE] (memverifikasi & memperdalam GL-12 ronde 1)
- Lokasi: tidak ada `post_journal`/`emit` di `routers/materials_router.py`, `routers/procurement_router.py`, `procurement_extra.py`, `stock_control.py`, `routers/stock_router.py` (grep: hanya `emit("material.overbudget")` di `materials_router.py:74`, bukan GL). Satu-satunya jurnal pengadaan: `gl_engine.py:367-398` (Dr 1-1400 saat tagihan DISETUJUI).
- Reproduksi (skrip `t3_grn.py`, `t5_ap.py`, `t6_issue.py`, `t7_opname.py`, `t8b_return.py`, `t13_transfer.py`): PO material 300 sak × 60.000.
  - GRN 100+200 sak: GL(1-1400) 325.000.000 → 325.000.000 (tak berubah); valuasi stok +Rp 18 jt.
  - Tagihan Rp 18.050.000 disetujui: GL(1-1400) → 343.050.000; GL(2-1100) 486.200.000 → 504.250.000 (JV/2026/00048).
  - Stok dikeluarkan ke pekerjaan (`/materials/requisitions/{id}/issue`, 300 sak): GL(1-1400) tetap 343.050.000, GL(1-1600) tetap 856.000.000, laba rugi tak berubah — padahal stok fisik 0.
  - Opname (fisik 0, lalu 1.000), retur 30 sak, transfer 80 m³ ke proyek lain: tidak ada jurnal sama sekali.
  - HPP saat BAST berasal dari RAB (`revrec_cogs.py:30-47`) dan hanya mengkredit `1-1600`; `1-1400` tidak pernah dikredit oleh kode mana pun.
  - Sensus jurnal (`GET /gl/journals`, 65 jurnal setelah seluruh uji): `source_type` hanya `ap_bill`(24), `receipt`, `asset_depreciation`, … — NOL jurnal bersumber GRN/retur/transfer/opname/pemakaian material.
- Dampak bisnis: untuk developer, material ±separuh biaya: aset "Persediaan Material" menggelembung terus (GL 471.850.000 di akhir uji vs stok fisik bernilai Rp 0 / negatif), biaya pokok proyek terlalu kecil → laba kotor dilaporkan terlalu besar; stok yang hilang/diopname selisih tak berdampak ke laba. Tidak ada akrual barang-diterima-belum-ditagih (GRNI): utang baru diakui saat tagihan.
- Akar & arah: stok adalah buku kuantitas tanpa ikatan nilai ke GL. Arah: jurnal pemakaian (Dr 1-1600 / Cr 1-1400 pada harga rata-rata), jurnal selisih opname & retur & transfer (dengan dimensi proyek), akrual GRNI; tie-out 1-1400 = Σ nilai stok di `/finance/reconcile`.

### [PG-02] [Severity: Tinggi] Lima definisi "komitmen/realisasi" untuk RAB yang sama; layar yang sama mengatakan "Aman 16,9%" dan "Melebihi −Rp 391,5 jt"
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `routers/boq_router.py:59-80` (`/boq/summary`: komitmen = Σ total PO approved+, aktual = Σ SEMUA `ap_invoices.claimed` proyek termasuk pending/non-RAB, `over_budget` hanya cek komitmen); `budget_engine.py:100-172,449-480` (`/budget/summary`); `opname.cost_control` (`/boq/control`); `metrics/project.py:258-283` (PRJ-09 menghitung PO draft); `budget_reports.py:106-155` (`/budget/unmapped` menjumlah PO + tagihan dokumen yang sama).
- Reproduksi: Proyek A, RAB konstruksi Rp 472.000.000. Menu RAB/BoQ (owner):
  - tab "Rincian RAB › Item RAB proyek (lama)": Komitmen Rp 863.500.000, Realisasi Rp 784.850.000, Sisa −Rp 391.500.000, banner "Komitmen PO melebihi anggaran RAB" (`img/pengadaan/13-boq-lama-A.png`);
  - tab "Realisasi RAB": Komitmen 43.000.000, Realisasi 37.000.000, Exposure 80.000.000, "Aman 16,9%" (`11-boq-realisasi-A.png`);
  - tab "Kendali Biaya": dikontrakkan 226.000.000, terbukti 30.000.000, ditagih Rp 0 (`12-boq-kendali-A.png`);
  - API `/analytics/metric/PRJ-09`: 84.322.134 (menghitung 11 PO draft, termasuk PO bernilai −10.000); `/budget/unmapped`: total 1.390.507.439 = PO + AP dokumen yang sama dijumlahkan.
- Dampak: keputusan overbudget/Change Order dibuat dari angka yang saling bertentangan; "tidak ada dua kebenaran" (klaim docstring `budget_engine.py:1-30`) tidak berlaku di luar sub-bagian konstruksi.
- Arah: satu fungsi komitmen/realisasi (budget_engine) dipakai semua layar; matikan/ganti `/boq/summary` lama; PRJ-09 hanya PO approved.

### [PG-03] [Severity: Tinggi] PO/tagihan dari UI tidak pernah masuk anggaran; kontrol anggaran preventif tidak ada; "realisasi" naik sebelum tagihan disetujui
- Label bukti: [TERBUKTI-UI] (payload) + [TERBUKTI-API] + [DARI-KODE]
- Lokasi: UI `AddPODialog.js:69-85` (item tanpa `boq_item_id`), `PODetailSheet.js:73-80` (tagihan tanpa `budget_item_id`); model `models_procurement.py:129-178` & `models.py:440-447` (tidak ada field `budget_item_id`/`cost_ref`; hanya `labor_engine.py:242`); `budget_engine.py:106-170` (PO hanya terhitung bila baris punya `boq_item_id` yang tercantum di item anggaran); `settings_store.py:327` (`budget.enforce_cost_ref` hanya dibaca untuk tampilan: `budget_router.py:319`, tidak ditegakkan); `_material_ref_docs` (`budget_engine.py:303`) tak pernah terisi karena `material_txns` tak punya `budget_item_id`.
- Reproduksi: (1) PO via UI (pm, `ui2.js`): payload `POST /api/procurement/pos` tanpa `vendor_id`/`boq_item_id` [TERBUKTI-UI]; PO 18 jt (PO/2026/0003), tagihan 18,05 jt, dan tagihan subkon 250 jt (PO/2026/0007) tidak mengubah `/budget/summary` (konstruksi komitmen 33 jt, realisasi 27 jt tetap) — muncul hanya sebagai "belum terpetakan". (2) PO dengan `boq_item_id` STR-01 Rp 20 jt: komitmen 33→53 jt; tagihan 10 jt dibuat (status pending_approval): realisasi 27→37 jt SEBELUM disetujui, GL belum bergerak. (3) `boq_item_id: "nonexistent-boq"` diterima (200). (4) PO material 300 sak (RAB `budget_qty` 100) disetujui tanpa peringatan; PO/Requisition tak dibandingkan dengan RAB — baru ditandai SESUDAH stok dikeluarkan.
- Dampak: realisasi/komitmen anggaran proyek understated untuk hampir semua pembelian nyata; overbudget baru terdeteksi setelah uang keluar.
- Arah: boq_item_id/budget_item_id wajib & divalidasi pada PO line; tagihan mewarisi dari PO; realisasi dari tagihan DISETUJUI; cek komitmen vs RAB saat PO disetujui.

### [PG-04] [Severity: Tinggi] Race pada stok: pengeluaran permintaan, transfer antar proyek, dan retur tidak atomik — stok negatif & retur melebihi penerimaan
- Label bukti: [TERBUKTI-API] (2 request paralel, `t6_issue.py`, `t13_transfer.py`, `t8b_return.py`)
- Lokasi: `routers/materials_router.py:346-392` (cek stok → insert → tulis `items` absolut, tanpa CAS), `stock_control.py:43-88` (tanpa kunci), `procurement_extra.py:127-197` (`create_return`: baca GRN/PO → tulis absolut). Pola PK-02 ronde 1 hanya diperbaiki untuk jalur uang (AP/PO/GRN/tagihan: terverifikasi 409 pada uji paralel).
- Reproduksi: (a) permintaan PR/2026/0004 (300 sak, stok 300) di-issue 2 request paralel oleh site → keduanya 200; stok −300 (dua `out` 300 sak), permintaan tampil "dikeluarkan 300". (b) transfer 80 m³ ×2 paralel dari stok 100 → keduanya 200; stok asal −60, proyek B mendapat +160. (c) GRN 100 sak; retur 30; lalu 2 retur paralel @50 (sisa 70) → keduanya 200: total retur 130 sak > 100 diterima, `returned_value` Rp 7.150.000 > nilai GRN Rp 5.500.000, `GRN.items.returned_qty`=80 (lost update), PO.received_qty=20, stok −120.
- Dampak: aset stok tercatat negatif/ganda; klaim retur/kredit vendor melebihi barang yang pernah diterima.
- Arah: CAS/`reserved` dan kunci per material seperti pola `idempotency.reserved`, validasi stok ≥ 0 di dalam kunci.

### [PG-05] [Severity: Tinggi] Retur boleh melebihi stok (stok negatif) dan menghidupkan kembali PO yang sudah dibatalkan
- Label bukti: [TERBUKTI-API]
- Lokasi: `procurement_extra.py:171-179` (insert `out` tanpa cek stok), `:187-192` (status PO dihitung ulang tanpa memeriksa `cancelled`).
- Reproduksi: GRN 100 sak (PO/2026/0004) → site keluarkan 90 → stok 10 → retur 30 sak → 200, stok −20. PM membatalkan PO itu (status `cancelled`), lalu retur 5 sak → 200 dan status PO menjadi `partially_received` (layar Pengadaan menampilkan "Diterima sebagian"); tagihan Rp 800.000 kemudian berhasil dibuat atas PO yang "batal" (`t9_cancel.py`, `t9b.py`).
- Dampak: status melompat tanpa jejak; PO batal dapat ditagih lagi.
- Arah: retur menolak bila stok < qty dan bila PO `cancelled`; status mesin-status eksplisit.

### [PG-06] [Severity: Tinggi] Pembatalan PO tidak memeriksa penerimaan/tagihan; tagihan atas PO "batal" tetap disetujui & dibayar
- Label bukti: [TERBUKTI-API] [DARI-KODE]
- Lokasi: `routers/procurement_router.py:210-220` (hanya menolak status received/closed/cancelled; tidak ada CAS; tidak menyentuh GRN/tagihan/stok/`qty_po`), UI `PODetailSheet.js:25-27,140-146` menawarkan "Batalkan" pada `partially_received`.
- Reproduksi: PM membatalkan PO/2026/0004 yang sudah diterima 100 sak dan PO/2026/0012 yang punya tagihan disetujui Rp 100.000.000 → 200. Tagihan tetap `approved`; finance membayarnya Rp 100.000.000 (200); GL(1-1201) 7.668.534.936 → 7.568.534.936. Stok hasil GRN tetap ada.
- Dampak: PO batal tidak membatalkan kewajiban; uang keluar atas dokumen yang secara status sudah gugur.
- Arah: cancel hanya bila `received_value=0` dan `billed_value=0`; selebihnya lewat retur + nota kredit.

### [PG-07] [Severity: Tinggi] Master vendor bukan sumber kebenaran: UI PO & AP memakai teks bebas; vendor nonaktif/ganda lolos; riwayat disambung lewat NAMA
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `AddPODialog.js:124` & `ApPanel.js:211` memakai `ReferenceSelect group="vendor"` → `reference_groups.py:503-510` (string dinamis dari `subcontractors`, `ap_invoices`, `purchase_orders`; `allow_new`); `AddPODialog.js:78` tidak mengirim `vendor_id`; `procurement_router.py:100-109` (cek vendor aktif hanya bila `vendor_id` ada); `vendor_engine.py:58,73` (usage berdasar nama); `vendors_router.py:57-66` & `vendor_engine.py:29-43` (nama kembar diizinkan).
- Reproduksi: (1) PO dari UI (pm): `vendor_id=null`, picker menampilkan "AUDIT-Vendor Semen" ×2 (dengan/tanpa spasi), "audit-vendor semen", dan TIDAK menampilkan vendor master PT Baja Nusantara Perkasa/UD Sewa Alat Jaya (`03-po-vendor-picker.png`, `/api/reference/vendor`). (2) PO ke vendor nonaktif: dengan `vendor_id` → 400; hanya dengan nama → 200 (`t11_misc.py`). (3) Dua vendor master bernama sama (AUDV1, AUDV1B) diterima; keduanya menampilkan 5 PO/Rp 48.601.000/utang 8.001.000 yang sama, kartu "Nilai PO" Rp 109.723.134 (aktual Rp 61.122.134) (`40-vendors.png`). (4) Uji harga PO tanpa vendor_id memakai harga terbaik lintas vendor, bukan harga vendor itu.
- Dampak: daftar harga, evaluasi vendor, larangan vendor nonaktif, rekap utang per vendor tidak berlaku untuk PO yang dibuat lewat jalur utama UI; salah ketik menciptakan "vendor" baru.
- Arah: vendor_id wajib (picker dari master), nama hanya snapshot; unik NPWP/nama.

### [PG-08] [Severity: Tinggi] PO tipe `subcon` melewati seluruh kontrol SPK/opname/retensi; SPK tidak tahu
- Label bukti: [TERBUKTI-API]
- Lokasi: `procurement_router.py:94-99` (hanya cek subkon ada; `spk_id` tidak divalidasi), `gl_engine.py:379` (subcon → Dr 1-1600), `finance_ap.py:11-56`.
- Reproduksi (`t10_subpo.py`): PO subcon Rp 250.000.000 ke PT Instalasi Prima dengan `spk_id` milik CV Bangun Jaya (SPK/2026/0001, Rp 300 jt, progres 40%) → approve (finance), GRN 1 "ls" (site), tagihan 250 jt retensi 5% (pm), approve (finlead): GL(1-1600) 856.000.000 → 1.106.000.000, GL(2-1100) +237.500.000, GL(2-1200) +12.500.000. SPK tetap progres 40%/billed None; tidak ada opname, verifikasi lapangan, klaim, atau potongan uang muka.
- Dampak: kontrol Fase 33/48C (uang hanya mengalir mengikuti bukti pekerjaan) bisa dilewati lewat PO; pekerjaan sama dapat dibayar lewat dua jalur.
- Arah: PO subcon wajib terikat SPK (vendor = subkon SPK, Σ PO ≤ sisa kontrak) dan tagihannya lewat termin; atau larang tipe subcon di PO.

### [PG-09] [Severity: Tinggi] Pemisahan tugas pengadaan masih bocor: dua akun menuntaskan siklus ke vendor fiktif; penerima barang tak dipisah; PM menyetujui permintaannya sendiri
- Label bukti: [TERBUKTI-API]
- Lokasi: `procurement_router.py:240-243` (GRN: izin `procurement:create`, tanpa cek pembuat PO), `:352-358` (tagihan sama), `ap_router.py:93-107` (hanya approver≠payer, creator≠approver), `materials_router.py:316-328` (tanpa cek pemohon).
- Reproduksi (`t12_sod.py`): finance membuat PO Rp 45.000.000 ke "AUDIT-Vendor Fiktif CV Hantu" (teks bebas) → finance menyetujui sendiri: 400 (benar) → finlead menyetujui → **finance** mencatat GRN → **finance** membuat tagihan → finlead menyetujui → **finance** membayar (200): GL(1-1201) −45.000.000, GL(6-1300) +45.000.000. Dua akun, satu orang melakukan PO+GRN+tagihan+bayar; penyetuju tak pernah melihat barang. Juga: pm membuat dan menyetujui permintaan PR/2026/0006 sendiri (200). Satu-satunya ambang nilai tetap PO > 500 jt.
- Dampak: rantai fiktif butuh kolusi minimal 2 akun; tidak ada kontrol penerimaan barang independen (tanpa surat jalan/foto/lampiran pada `GRNCreate`).
- Arah: penerima GRN ≠ pembuat PO ≠ pembayar; lampiran bukti terima; batas wewenang bertingkat per nilai tagihan.

### [PG-10] [Severity: Tinggi] PO menerima qty/harga negatif, total 0, vendor kosong, tanggal sampah; ambang Owner (> Rp 500 jt) bisa dilewati; material proyek lain/ID sampah → stok hantu
- Label bukti: [TERBUKTI-API]
- Lokasi: `models_procurement.py:129-149` (`qty: float = 1`, `unit_price: int = 0`, `vendor: str`, `due_date` tanpa validasi), `procurement_router.py:110-137` (`high_value` dari total NETO), `:281-283` (material tak ditemukan → stok tak dicatat tanpa pesan).
- Reproduksi (`t11_misc.py`, `t15_misc2.py`): PO vendor "" dengan qty −10 → 200, total −10.000; PO qty 0/harga 0, due_date "garbage" → 200; PO baris A Rp 600.000.000 + baris B (diskon) −250.000.000 → total 350.000.000, `high_value=false`, disetujui finance (bukan Owner), GRN baris A → `received_value` 600.000.000 > total PO 350.000.000. PO proyek A dengan `material_id` milik Proyek B → GRN 200: `material_txns in` 10 tercatat di proyek A atas material B, tidak tampak di daftar stok proyek mana pun (stok hantu).
- Dampak: bypass persetujuan Owner; nilai terima ≠ nilai PO; stok tak terlihat.
- Arah: validasi qty>0, harga≥0, total>0, vendor wajib, material∈proyek, ambang berdasar Σ baris positif.

### [PG-11] [Severity: Tinggi] Stok manual dan opname tanpa persetujuan/validasi/nilai — melewati alur permintaan & PM
- Label bukti: [TERBUKTI-API] [DARI-KODE]
- Lokasi: `materials_router.py:182-205` (`txn in/out` oleh `materials:update`, site punya), `:208-228` (opname tanpa catatan wajib, tanpa batas), UI `MaterialsPage.js:286-330`.
- Reproduksi (`t7_opname.py`): site menyetel stok: opname fisik −50 → 200, stok −50; fisik 1.000 → stok +1.050 tanpa persetujuan; `txn in 500` tanpa PO/GRN → 200. `/materials/valuation` lalu menghitung stok 1.500 sak × rata-rata Rp 60.000 = Rp 90.000.000 (hanya 300 sak yang pernah dibeli). `txn out` manual (90) memotong stok tanpa permintaan/PM.
- Dampak: stok bisa digelembungkan/dikuras oleh satu orang lapangan tanpa jejak nilai atau persetujuan; valuasi mengarang nilai.
- Arah: opname = dokumen dengan approver, selisih berjurnal, `in` hanya dari GRN/transfer, `out` hanya dari permintaan.

### [PG-12] [Severity: Tinggi] Retensi default 5% pada tagihan PO/manual tidak punya jalur pencairan — vendor "lunas" kurang 5% selamanya (PK-16 masih terbuka)
- Label bukti: [TERBUKTI-UI] (default) + [TERBUKTI-API]
- Lokasi: `PODetailSheet.js:44,90` (retensi default "5"), `models_procurement.py:171` (default 5), `finance_ap.py:184-201` (sweeper hanya untuk `release_due_at`, tak pernah diisi/dijadwalkan: `finance_engine.py:972` hanya impor), `subcon_finance.py` (retensi hanya termin SPK).
- Reproduksi (`t17.py`): tagihan PO material Rp 10.000.000 tanpa mengubah retensi → net 9.500.000, retensi 500.000; bayar 9.500.000 → status `paid`; PO "billed 10 jt, received"; `retention` row None; 500.000 tertinggal di 2-1200. Tagihan subkon-PO 250 jt: Rp 12.500.000 di 2-1200 tanpa baris `subcon_retentions` (`GET /subcon/retentions` tak memuatnya). 2-1200 naik 4.800.000 → 17.800.000 selama uji; `/finance/reconcile` tetap hijau karena sumbernya sama (`finance_audit.py:35`).
- Dampak: utang retensi menumpuk tanpa cara bayar; vendor material dipotong 5% tanpa kontrak retensi.
- Arah: retensi hanya untuk jasa/subkon & eksplisit; baris retensi + tanggal jatuh tempo + pencairan untuk semua tagihan beretensi.

### [PG-13] [Severity: Tinggi] Tidak ada void/nota kredit/koreksi untuk PO, GRN, tagihan (PK-09/GL-10 masih terbuka); retur setelah ditagih buntu
- Label bukti: [TERBUKTI-API]
- Lokasi: `POST /finance/ap/bills/{id}/{void|cancel|reject|reverse}` → 404; `/finance/ap/credit-notes`, `/procurement/credit-notes` → 404; tidak ada rute ubah PO/GRN; `procurement_extra.py:154-158` menyuruh "terbitkan nota koreksi/kredit" yang tidak ada.
- Reproduksi: retur 10 sak atas GRN yang sudah ditagih (PO/0003) → 400 "Terbitkan nota koreksi/kredit atas tagihan vendor lebih dulu".
- Dampak: PO salah harga/qty yang sudah diterima tidak dapat diperbaiki; tagihan keliru tidak dapat dibatalkan (hanya dibayar).
- Arah: dokumen pembalik bersumber PO/tagihan (nota kredit pembelian, void sebelum bayar).

### [PG-14] [Severity: Sedang] PPN masukan tak dibukukan; worksheet PPN masukan menghitung semua tagihan termasuk pending (GL-04 masih terbuka)
- Label bukti: [TERBUKTI-API] [DARI-KODE]
- Lokasi: `tax_engine.py:32-55` (Σ semua `ap_invoices` × rate/(100+rate), tanpa filter status/PKP/jenis), `gl_engine.py:385` (seluruh klaim masuk 1-1400/1-1600/6-1300).
- Reproduksi: `/tax/ppn-input`: rate 12%, DPP 995.404.465, PPN 119.448.535, 13 tagihan; per status: pending_approval 30.086.035, approved 78.321.429, partial 6.428.571, paid 4.612.500. `/tax/summary`: `ppn_net` 336.551.465 "kurang_bayar". GL tak punya akun/baris PPN masukan.
- Dampak: SPT Masa PPN estimasi memakai tagihan yang belum sah & non-PPN; GL membebankan PPN sebagai biaya/persediaan.

### [PG-15] [Severity: Sedang] Nilai persediaan: GL ≠ subledger tanpa tie-out; valuasi mengabaikan stok negatif; saldo awal 300 jt tanpa subledger
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `stock_control.py:151-205` (rata-rata atas seluruh `in`, `max(0, value)`), `finance_audit.py:21-60` (reconcile hanya 2-1100, 2-1200, 2-1400, 2-1450, 2-1600, TB — tak mencakup 1-1400/1-1600/1-1800).
- Reproduksi: GL(1-1400) 471.850.000 (termasuk saldo awal 300.000.000 JV/2026/00004 tanpa subledger) vs `/materials/valuation` total_value Rp 0 (6 dari 7 material tanpa harga; MAT-001 stok −125 sak bernilai −Rp 7.343.750 ditampilkan tetapi dibuang dari total); layar Material › Kendali Stok: kartu "Nilai persediaan Rp 0", baris "Stok habis" untuk stok negatif (`20-materials-tab3.png`).
- Arah: tie-out 1-1400 ↔ valuasi; stok negatif ditandai kesalahan data.

### [PG-16] [Severity: Sedang] Klasifikasi akun ditentukan `po_type` ketikan, tak sesuai isi baris: PO "general" bermaterial menaikkan stok tapi membebani 6-1300
- Label bukti: [TERBUKTI-API]
- Lokasi: `gl_engine.py:376-379` vs `procurement_router.py:281-292` (stok mengikuti `material_id` baris).
- Reproduksi: PO general 20 m³ kerikil Rp 4.000.000 → GRN → tagihan disetujui: stok +20, GL(6-1300) 46.270.000 → 50.270.000, GL(1-1400) tak berubah.
- Dampak: stok & GL menghitung barang yang sama berbeda; pemakaian kelak tak ada pasangan akun.

### [PG-17] [Severity: Sedang] 3-way match: toleransi menutupi selisih sebagai "Cocok"; terobosan tak ditegakkan dan hanya lewat API; GRN pada tagihan hanya informasi
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `procurement_extra.py:222-230` (toleransi 0,5% dari NILAI PO/terima, kumulatif), `procurement_router.py:367-412`, `PODetailSheet.js:73-80,162-170` (tak ada input override; cabang "DITANDAI" tak pernah tercapai), `ap_router.py:109` (tak membaca `requires_senior_approval`).
- Reproduksi: PO/2026/0003 Rp 18.000.000, diterima 18.000.000 → tagihan Rp 18.050.000 lolos "matched"; tab 3-Way Match menampilkan "Rp 18.050.000 · Cocok" tanpa varians (`30-threeway.png`); jurnal Dr 1-1400 18.050.000 sementara stok bernilai 18.000.000 (selisih harga tak dipisah). Override finlead + alasan → tagihan Rp 5 jt di atas PO 20 jt sehingga billed 23.000.000; finance (non-senior) menyetujuinya (200) walau `requires_senior_approval=true`.
- Arah: tampilkan varians, selisih ke akun PPV, tegakkan persetujuan senior, tambah input override di UI.

### [PG-18] [Severity: Sedang] Layar PO: peringatan harga tersembunyi bagi penyetuju; persetujuan tanpa alasan; daftar peran hardcode; label menyesatkan
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `PODetailSheet.js:23-25` (APPROVE/CREATE/CANCEL hardcode: `finance_manager` tak melihat "Setujui" padahal API mengizinkan — `06-po-detail-finlead.png` vs `…-finance.png`), tidak ada render `price_checks` (hanya `ReqToPoDialog.js:75`), `POPanel.js:57` (kartu "Menunggu/Approve" = `summary.approved` = PO yang SUDAH disetujui terbuka; PO menunggu = `draft`), `POPanel.js` "Nilai PO" menjumlah PO draft.
- Reproduksi: PO/2026/0008 harga Rp 150.000 vs acuan 95.000 (`di_atas_acuan 57,89%`, tersimpan di `price_checks`) — detail PO untuk finance tidak menampilkan apa pun (`06-po-detail-finance.png`); `POST …/approve` → 200 tanpa alasan padahal pesan sistem berkata "lampirkan alasan sebelum PO disetujui".

### [PG-19] [Severity: Sedang] Daftar harga: acuan = MIN semua baris aktif; tanpa persetujuan; tanggal tak divalidasi; acuan ikut PO draft; material per-proyek
- Label bukti: [TERBUKTI-API]
- Lokasi: `vendor_engine.py:174-199`, `models_p48.py:85-95` (`valid_from` hanya panjang 10), `vendors_router.py:78-88` (izin `vendors:update` termasuk PM).
- Reproduksi: harga 60.000 (2026-01-01, tanpa akhir) + harga baru 72.000 (2026-06-01) → keduanya "aktif", acuan 60.000, PO 72.000 ditandai +20%; PM menambah harga 999 → acuan 999, PO 60.000 ditandai +5906%; `valid_from="garbage-AB"` & `valid_until<valid_from` → 200; acuan tanpa daftar harga = harga PO terakhir (termasuk PO draft, `vendor_engine.py:190-198`); material sama di Proyek B → `no_reference`, 0 baris harga (material per proyek).

### [PG-20] [Severity: Sedang] Permintaan→PO: hitungan kekurangan salah, `qty_po` tak dilepas saat PO batal, `to-po` & buat PO tidak anti-ganda
- Label bukti: [TERBUKTI-API]
- Lokasi: `procurement_extra.py:37-38` (kekurangan = diminta − stok − qty_po; barang yang sudah diterima terhitung dua kali), `:111-121`, `procurement_router.py:87-147`.
- Reproduksi: permintaan 100 kerikil → PO 100 → GRN 100 → site pakai 90 (stok 10): kekurangan = 0, "Seluruh kebutuhan sudah tercukupi" (seharusnya 90). Batalkan PO dari permintaan → kekurangan tetap 0 (permintaan tak bisa dipesan ulang). `to-po` 2 request paralel → 2 PO (PO/2026/0005 & 0006 @ Rp 3,8 jt, `qty_po`=40); `POST /procurement/pos` 2 paralel → 2 PO (0014 & 0015).

### [PG-21] [Severity: Sedang] "Pemakaian vs RAB" material salah: transfer/retur dihitung sebagai pemakaian; field tersimpan basi
- Label bukti: [TERBUKTI-UI] [TERBUKTI-API]
- Lokasi: `materials_router.py:31-35,111-138` (semua `type=out`), `stock_control.py:66-72`, `procurement_extra.py:172-179`.
- Reproduksi: MAT-002 (RAB 50 m³): hanya transfer 3×80 → "240/50 Melebihi RAB" (`20-materials-tab2.png`); MAT-001 "825/100" termasuk retur ke vendor (130) dan issue ganda. `GET /materials/project/{id}` mengembalikan `consumed_qty=0, over_budget=False` sementara `/budget` menghitung 240/True.

### [PG-22] [Severity: Sedang] Deteksi faktur ganda lolos oleh huruf besar/kecil & spasi; PO-bill di UI tak punya nomor faktur; tagihan manual tanpa vendor/proyek valid (sisa PK-15)
- Label bukti: [TERBUKTI-API] [TERBUKTI-UI]
- Lokasi: `finance_ap.py:32-50` (pencocokan persis, nama vendor teks), `PODetailSheet.js:73-80` (tanpa `vendor_invoice_no`), `ap_router.py:39-51`.
- Reproduksi: faktur `AUD-INV-TOL` dicatat; `aud-inv-tol`, vendor "audit-vendor semen", dan "AUDIT-Vendor Semen␠" (spasi) → 200 ×3; tagihan manual `vendor:""`, `project_id:"nonexistent"` → 200; tagihan manual melewati 3-way match.

### [PG-23] [Severity: Sedang] PPh: dasar potongan bebas (PK-17 masih terbuka)
- Label bukti: [TERBUKTI-API] — `ap_router.py:146-196`: bill Rp 800.000, `base` 8.000.000 × 2% → PPh 160.000 (20% efektif), kas keluar 640.000, bukti potong terbit; tarif tak dikaitkan jenis.

### [PG-24] [Severity: Sedang] Tagihan tanpa jatuh tempo tak pernah menua; `payment_terms_days` vendor tak dipakai
- Label bukti: [TERBUKTI-UI] [DARI-KODE] — `finance_engine.py:977-1011` (`due None` → `current`), `payment_terms_days` hanya di model/impor (grep). Semua tagihan PO uji ("-" jatuh tempo) tampil "Lancar" di Utang › Aging (`32-ap-tab.png`).

### [PG-25] [Severity: Rendah] Hal kecil
- Penomoran GRN bolong: nomor diambil sebelum validasi (`procurement_router.py:256`) → GRN/2026/0002,0003,0006 hilang [TERBUKTI-API].
- Material berkode berbeda tetapi bernama sama diterima di satu proyek (MAT-001 & MAT-003) [TERBUKTI-API].
- Buku besar material menulis "KELUAR … +80 m3" (`MaterialsPage.js:168`) [TERBUKTI-UI `20-materials-tab0.png`]; stok negatif tampil biasa.
- Izin `vendors:manage` tidak ditegakkan: finance & PM menonaktifkan/mengaktifkan vendor via `PUT /vendors/{id}` (`vendors_router.py:146-154`) dan dapat mengganti rekening bank vendor tanpa persetujuan [TERBUKTI-API].
- `material_book_stock`/`_consumed_qty` `to_list(5000)`, `average_cost` 2000, `ap_aging` 2000, `reconcile` 5000: terpotong diam-diam bila lebih banyak [DARI-KODE].
- `vendor_usage.bill_outstanding` menyertakan tagihan pending (beda dari GL 2-1100) [DARI-KODE].
- Retensi memakai `round()` bawaan Python (pembulatan bankir) [DARI-KODE].
- Layar tanpa proyek tersimpan memilih proyek lain secara default: tab Retur (finance) & RAB/BoQ (owner) langsung memilih "AUDIT-Proyek B" sehingga tab Retur menampilkan "Belum ada retur / Rp 0" padahal ada 4 retur di proyek A [TERBUKTI-UI `31-returns.png`, `10-boq-page.png`].
