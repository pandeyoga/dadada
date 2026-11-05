# Audit PENGADAAN ronde 2 — laporan utama (instance #7: UI :3041, API :8041, DB sipro_proc)

Bagian terpisah: [07_PENGADAAN_1_PETA_SSOT.md]((skrip uji tidak disertakan di repo)) (peta alur, tabel peristiwa→jurnal, tabel SSOT) · [07_PENGADAAN_2_TEMUAN.md]((skrip uji tidak disertakan di repo)) (PG-01…PG-25 lengkap dengan langkah reproduksi).
Skrip uji: (skrip uji tidak disertakan di repo) · Screenshot: `img/pengadaan/`.

## Ringkasan eksekutif
1. **Pengadaan terhubung ke finance HANYA lewat satu pintu: persetujuan & pembayaran tagihan AP.** Jalur AP-nya sehat (jurnal benar, utang usaha 2-1100 = Σ tagihan = aging = ringkasan keuangan: Rp 731,7 jt, selisih 0; paralel approve/bayar aman; cek saldo kas; SoD approver≠pembayar). Tetapi seluruh sisi barang — GRN, retur, pemakaian ke pekerjaan, opname, transfer — **tidak menghasilkan satu jurnal pun** (PG-01, Kritis): `1-1400` hanya naik (GL Rp 471,85 jt vs valuasi stok Rp 0), biaya material tak pernah masuk WIP/HPP.
2. **Angka anggaran saling bertentangan di layar yang sama**: RAB Proyek A Rp 472 jt tampil "Komitmen 863,5 jt, sisa −391,5 jt" di satu tab dan "Aman 16,9%" (komitmen 43 jt) di tab lain; lima definisi komitmen (PG-02). PO/tagihan yang dibuat lewat UI nyaris tidak pernah masuk anggaran (UI tidak mengirim `boq_item_id`/`vendor_id`; `enforce_cost_ref` tidak ditegakkan) (PG-03).
3. **Master vendor bukan SSOT**: picker UI PO & AP berisi teks bebas (vendor master tak muncul; vendor nonaktif & duplikat lolos) (PG-07); material per-proyek sehingga daftar harga tak berlaku lintas proyek (PG-19).
4. **Konkurensi stok belum ditutup** (ronde 1 hanya menutup jalur uang): issue permintaan, transfer, retur paralel → stok −300/−60/−120, retur 130 sak dari 100 diterima (PG-04); retur melebihi stok & menghidupkan PO batal (PG-05); PO bisa dibatalkan setelah diterima/ditagih dan tagihannya tetap dibayar (PG-06).
5. **Kontrol bisa dilewati**: PO subkon Rp 250 jt tanpa opname/SPK (PG-08); dua akun menuntaskan PO→GRN→tagihan→bayar Rp 45 jt ke vendor fiktif (PG-09); PO dengan baris negatif melewati ambang Owner (PG-10); opname/stok manual tanpa persetujuan (PG-11).
6. Masih terbuka dari ronde 1: retensi 5% default tanpa jalur cair (PK-16 → PG-12), tanpa void/nota kredit (PK-09/GL-10 → PG-13), PPN masukan (GL-04 → PG-14), PPh dasar bebas (PK-17 → PG-23). Tertutup: PK-02 (jalur AP/PO/GRN/tagihan), PK-06, PK-08.
7. Total 25 temuan: 1 Kritis, 12 Tinggi, 11 Sedang, 1 Rendah (kumpulan).

## Cakupan
Dijalankan nyata di instance #7 (API + UI Playwright 1440×900, peran superadmin/owner/finlead/finance/pm/site): master vendor & harga (duplikat, nonaktif, tanggal, MIN-acuan), material, permintaan→shortage→PO, PO (material/general/subcon, validasi, ambang Owner, harga vs acuan), approve, GRN penuh/parsial/lebih/negatif/paralel, retur (sisa, stok, paralel, setelah batal), tagihan PO (sesuai/lebih/override/paralel/default retensi/dup faktur), approve/bayar/bayar+PPh/lebih-bayar/paralel/cek saldo, retensi & potongan, SoD rantai penuh, pembatalan PO (draft/diterima/ditagih), issue/opname/txn manual/transfer (paralel), anggaran (budget, boq summary/control, unmapped, PRJ-09, PO ber-`boq_item_id`), PPN masukan, reconcile, aging; layar ProcurementPage (PO, 3-Way, Retur, Vendor, Harga, Evaluasi), MaterialsPage (Stok, Permintaan, Anggaran, Kendali Stok), BoQ (Item lama, Realisasi, Kendali), Finance › Utang. Skrip: t1…t17.py, ui1…ui10.js.

## Bagian C — verifikasi klaim ronde 1 (PK-xx, GL-xx) yang menyangkut pengadaan
| ID ronde 1 | Klaim | Status sekarang | Bukti |
|---|---|---|---|
| PK-02 pembayaran/persetujuan ganda (AP, PO, GRN, tagihan PO) | benar | **TERTUTUP** untuk approve PO, approve AP, bayar AP, GRN, tagihan PO (paralel → 1×200 + 409/400; 1 jurnal) | `t3_grn.py`, `t16_c.py`, uji parallel approve (Δ2-1100 = 8.000.000 tepat) |
| PK-02 pola yang sama pada stok (issue, transfer, retur, to-po, buat PO) | – | **TERBUKA / baru** → PG-04, PG-20 | `t6_issue.py`, `t13_transfer.py`, `t8b_return.py`, `t9b.py` |
| PK-06 cek saldo kas | benar | **TERTUTUP** utk AP (bayar 237,5 jt dari Kas Besar 17,5 jt → 400 "kurang Rp 220.000.000") | `t16_c.py` |
| PK-07 SoD rantai PO→bayar satu akun | benar | **SEBAGIAN**: pembuat≠penyetuju PO/AP & penyetuju≠pembayar tertutup (400); penerima GRN tak dipisah, dua akun cukup (Rp 45 jt), PM approve sendiri permintaan, ambang nilai hanya PO>500 jt & bisa dilewati → PG-09, PG-10 | `t12_sod.py`, `t11_misc.py` |
| PK-08 retensi tak berbatas | benar | **TERTUTUP** (0–100: 400 untuk 150 dan −5) | `t16_c.py` |
| PK-09 tak ada void/nota kredit | benar | **TERBUKA** (`void/cancel/reject/reverse` → 404; tak ada credit-note) → PG-13 | `t16_c.py` |
| PK-15 faktur ganda & tagihan manual | benar | **SEBAGIAN**: `vendor_invoice_no` ada tetapi opsional, persis-sama saja (huruf/spasi lolos), tak ada di form tagihan PO; manual tanpa vendor/proyek valid masih 200 → PG-22 | `t5_ap.py` |
| PK-16 retensi PO/manual tanpa jalur cair | benar | **TERBUKA** (default UI 5%; baris retensi tak ada; sweeper tak dijadwalkan) → PG-12 | `t17.py`, `ui10.js` |
| PK-17 PPh dasar/tarif bebas | benar | **TERBUKA** (dasar 10× → potongan 20%) → PG-23 | `pph rate 2 base 10x` |
| GL-04 PPN masukan tak dibukukan | benar | **TERBUKA**; worksheet menghitung tagihan pending → PG-14 | `/tax/ppn-input` |
| GL-10 retur setelah tagihan buntu / nota kredit | benar | **TERBUKA** → PG-13 | retur ditolak 400 |
| GL-11 jurnal tanpa dimensi proyek | benar | **TERBUKA** (`project_id: None` pada JV/2026/00052 dst.) → PG-01/PG-02 | `t16_c.py` |
| GL-12 persediaan tak berjurnal | [DARI-KODE] ronde 1 | **BENAR & lebih buruk dari klaim**: sekarang TERBUKTI via saldo GL sebelum/sesudah tiap langkah (GRN, issue, opname, retur, transfer = 0 jurnal; 1-1400 hanya naik; HPP tak memuat material) → PG-01 (Kritis) | `t3`–`t8b`, sensus 65 jurnal |
| GL-12 "budget_engine membaca material_txns sedangkan GL membaca AP" | – | **Tidak akurat untuk kode terbaru**: material_txns tidak dihitung kecuali bertaut `budget_item_id` (tak pernah terisi → jalur mati); masalah sebenarnya: PO/AP dari UI tak bertaut anggaran sama sekali → PG-03 | `budget_engine.py:303-344` |

## Terverifikasi OK
- Tie-out kewajiban: GL 2-1100 Rp 731.700.000 = Σ tagihan disetujui belum lunas = `/finance/ap/aging` = `/finance/summary.ap_outstanding`; `/finance/reconcile` seimbang (kecuali yang disebut PG-12/15).
- Jurnal AP benar & seimbang: Dr 1-1400 18.050.000 / Cr 2-1100; bayar Dr 2-1100 / Cr bank; bayar+PPh 2%: Cr bank 3.920.000, Cr 2-1300 80.000, bukti potong terbit; lebih-bayar ditolak.
- Anti-ganda jalur uang: approve PO paralel (1×200), approve tagihan paralel (1 jurnal), bayar paralel (409), GRN paralel (409, stok tepat 300), tagihan PO paralel (409); UI "Simpan PO" klik ganda → 1 POST.
- Kontrol 3-way: tagihan Rp 19 jt atas barang diterima Rp 18 jt ditolak (400); override hanya finance_manager/Owner dengan alasan ≥10 huruf (403/400 untuk yang lain); GRN > sisa PO ditolak; qty ≤ 0 ditolak; PO ke `vendor_id` nonaktif ditolak; retur dibatasi ≤ sisa GRN & ≤ nilai ditagih.
- SoD: pembuat PO/tagihan tak bisa menyetujui sendiri (400); penyetuju tagihan tak bisa membayar (400); finance/site tak bisa membatalkan PO (403); site tak bisa menyetujui permintaan (403); PO>500 jt perlu Owner (kode).
- Penomoran dokumen atomik (PO paralel 0014/0015 tak kembar); cek saldo kas sebelum bayar; validasi retensi 0–100; `min_qty` negatif ditolak; PO tak ada endpoint ubah (immutable).
- Tampilan: tab 3-Way Match & Utang (AP) sesuai data API (nilai klaim/status); RBAC UI tidak menampilkan "Setujui/Batalkan" untuk site; angka stok sama antara tab Stok & Buku Besar dan Kendali Stok; tombol "Simpan PO" aman dari klik ganda.

## Tidak bisa diverifikasi
- Perilaku multi-proses (>1 worker uvicorn) untuk paralel: uji pakai 2 thread ke satu server; kunci in-memory (`money_lock`, `idempotency.once`) tidak diuji lintas proses.
- Pemotongan diam-diam `to_list(5000/2000)` (butuh >5.000 mutasi/2.000 tagihan) — hanya dari kode.
- PDF PO (`/procurement/pos/{id}/pdf`), kirim WA, import vendor/material (Excel), skor Evaluasi Vendor (angka tidak dihitung ulang), penutupan periode dengan stok.
- Apakah `finance_manager` memang diharapkan menyetujui PO di UI (API mengizinkan, UI menyembunyikan) — keputusan produk.
- Sweeper retensi: tak dijadwalkan menurut grep; tidak diuji jalan runtime.

## Pertanyaan terbuka
1. Apakah material diharapkan dibebankan ke WIP saat dipakai (perpetual) atau saat dibeli (Dr 1-1600 langsung)? Dua-duanya butuh keputusan sebelum PG-01 diperbaiki, karena menentukan GRNI & akun PPV.
2. Apakah vendor master wajib untuk semua PO (PG-07)? Subkontraktor punya master sendiri (`subcontractors`) — satu master vendor+subkon?
3. Retensi tagihan PO material memang dikehendaki (default 5%) atau hanya untuk jasa?
4. Ambang persetujuan: hanya PO > Rp 500 jt (PO)? Perlu matriks wewenang untuk tagihan manual & retur?

## Daftar temuan (ringkas)
| ID | Severity | Judul |
|---|---|---|
| PG-01 | Kritis | Persediaan tak berjurnal; 1-1400 hanya naik; biaya material tak masuk WIP/HPP |
| PG-02 | Tinggi | Lima definisi komitmen/realisasi; layar sama kontradiktif |
| PG-03 | Tinggi | PO/tagihan UI tak masuk anggaran; tak ada kontrol komitmen vs RAB; realisasi naik saat tagihan pending |
| PG-04 | Tinggi | Race stok: issue, transfer, retur → stok negatif, retur > terima |
| PG-05 | Tinggi | Retur > stok; retur menghidupkan PO batal |
| PG-06 | Tinggi | Batal PO tanpa cek GRN/tagihan; tagihan "PO batal" dibayar |
| PG-07 | Tinggi | Master vendor bukan SSOT (picker teks bebas, vendor_id kosong, duplikat, join nama) |
| PG-08 | Tinggi | PO subkon melewati SPK/opname/retensi |
| PG-09 | Tinggi | SoD: 2 akun tuntaskan siklus, GRN tak dipisah, PM self-approve permintaan |
| PG-10 | Tinggi | Validasi PO: negatif/0/kosong; ambang Owner dilewati; stok hantu |
| PG-11 | Tinggi | Stok manual & opname tanpa persetujuan/validasi/nilai |
| PG-12 | Tinggi | Retensi default 5% tanpa jalur cair (PK-16) |
| PG-13 | Tinggi | Tak ada void/nota kredit (PK-09/GL-10) |
| PG-14 | Sedang | PPN masukan tak dibukukan; worksheet termasuk pending (GL-04) |
| PG-15 | Sedang | Valuasi persediaan ≠ GL; reconcile tak mencakup 1-1400/1-1600 |
| PG-16 | Sedang | Akun GL mengikuti po_type ketikan, bukan isi baris |
| PG-17 | Sedang | 3-way: toleransi "Cocok", override tak ditegakkan & hanya API |
| PG-18 | Sedang | Layar PO: peringatan harga tersembunyi, role hardcode, label menyesatkan |
| PG-19 | Sedang | Daftar harga: MIN-acuan, tanpa approval, material per-proyek |
| PG-20 | Sedang | Shortage salah, qty_po tak dilepas, to-po/PO tak anti-ganda |
| PG-21 | Sedang | Pemakaian vs RAB: transfer/retur dihitung; field basi |
| PG-22 | Sedang | Faktur ganda lolos (huruf/spasi); form tagihan PO tanpa no. faktur; AP manual longgar |
| PG-23 | Sedang | PPh dasar bebas (PK-17) |
| PG-24 | Sedang | Tanpa jatuh tempo = "Lancar" selamanya; payment_terms tak dipakai |
| PG-25 | Rendah | Penomoran GRN bolong, material kembar, tanda "+" KELUAR, vendor manage tak ditegakkan, truncation limit |

Data uji tertinggal di `sipro_proc` (awalan AUDIT-): vendor AUDV1/AUDV1B/AUDV2/AUDV3, material MAT-001..004 + kerikil (proyek A) & MAT-001 (AUDIT-Proyek B), PO/2026/0003–0022, GRN/2026/0004–0012+, RTN/2026/0001–0004, TRF/2026/0001–0003, tagihan uji (sebagian dibayar; saldo bank operasional turun ±Rp 110 jt), proyek "AUDIT-Proyek B".
