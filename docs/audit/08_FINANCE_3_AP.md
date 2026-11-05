# Audit Ronde 2 — UTANG (AP) — SIPRO/Estora

Auditor: stream "finance AR/AP + komponen biaya" (instance #8, UI :3042, API :8042, DB `sipro_fin`). Kode terbaru pasca-perbaikan gelombang 1. Angka Rupiah. Data uji `AUDIT-*`. Skrip: (berkas uji tidak disertakan di repo) · Screenshot: `(tidak disertakan di repo)`.
Batas: PO/GRN/3-way match dan termin SPK ber-opname dipegang auditor pengadaan (instance #7); di sini hanya sisi keuangan AP (tagihan, persetujuan, pembayaran, PPh, retensi, aging, tie-out).

## Ringkasan eksekutif
1. **Inti AP dan pemisahan tugas ronde 1 bekerja:** pembuat tagihan tidak bisa menyetujui (400), penyetuju tidak bisa membayar (400), pembayar lain bisa (200), bayar melebihi sisa ditolak, retensi dibatasi 0–100%, potongan PPh membuat jurnal Dr 2-1100 / Cr Bank / Cr 2-1300 yang benar, pelepasan retensi subkon menjurnal Dr 2-1200 / Cr 2-1100 dan cocok dengan kontrol 2-1200, dan `/finance/reconcile` **mendeteksi** tagihan yatim (2-1100 selisih −Rp 2 jt).
2. **Masalah paling serius ada di pajak:** rekap SPT Masa PPN mengambil "PPN masukan" dari **semua** tagihan AP dengan rumus 12/112 (termasuk pembayaran BPHTB ke KPP, tagihan belum disetujui dan tagihan yatim) → uji: PPN masukan Rp 101,46 jt, "lebih bayar Rp 101,46 jt" (FN-40).
3. Tarif & dasar PPh bebas diketik (PPh 23 dengan 50%, PPh 4(2) konstruksi dengan 0,01% diterima), hanya satu tarif konstruksi global 1,75%, tak ada penanganan non-NPWP, dasar pemotongan = nominal bayar (kemungkinan inklusif PPN), dan tidak ada jalur menyetor PPh potongan (FN-41).
4. Validasi tagihan manual lemah: klaim Rp 10^15, vendor kosong, proyek fiktif, jatuh tempo "bukan-tanggal" diterima; duplikasi nomor faktur lolos dengan huruf kecil/spasi; tagihan tanpa jatuh tempo tak pernah menua di aging (FN-42). Retensi 5% bawaan pada tagihan manual tak punya jalur pencairan (FN-43).
5. Dua jalur lain membuat tagihan AP dengan SoD longgar: "Catat beban developer" (FN-04 di laporan komponen biaya — dibuat+disetujui+dibayar satu akun) dan tagihan yatim akibat akun GL salah (FN-05).

## Cakupan
Pembuatan tagihan (API+UI: klaim 0/negatif/10^15, vendor kosong, proyek fiktif, jatuh tempo rusak, retensi −5/100/150, faktur kembar), persetujuan & pembayaran (SoD per peran: finance, finlead, owner, pm), parsial/lebih/paralel, pembayaran dengan potongan PPh (tarif 0,01–50%, dasar > tagihan), jurnal AP (setuju/bayar/retensi/potongan), pelepasan retensi subkon (seed RET/2026/0002), aging AP (API vs DB vs GL 2-1100), tie-out `/finance/reconcile`, PPN masukan & rekap SPT, bukti potong, dasbor Utang (UI), verifikasi ulang PK-07/08/15/16/17/18.

---
## Temuan (urut severity)

### [FN-40] [Severity: Tinggi] "PPN masukan" (dan rekap SPT Masa PPN) dihitung dari SEMUA tagihan AP, termasuk yang bukan objek PPN
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- Lokasi: `tax_engine.ppn_input:32-52` (iterasi semua `ap_invoices`, `dpp = claimed×100/(100+rate)`), `tax_faktur_export.py:281-303` (`net = keluaran − masukan`), `GET /tax/ppn-input`, `GET /tax/compliance/vat-return`.
- Reproduksi: pada data uji ada tagihan "AUDIT KPP Pratama" Rp 99.000.000 (beban BPHTB ke kantor pajak), 2 tagihan yatim Rp 1 jt, tagihan `pending_approval`. `GET /tax/ppn-input` → baris KPP: DPP 88.392.857, **PPN 10.607.143**; total 10 tagihan: DPP 845.535.714, PPN **101.464.286**. `GET /tax/compliance/vat-return?period=2026-11` → `ppn_keluaran 0, ppn_masukan 101.464.286, net −101.464.286` → "Rp 101.464.286 lebih bayar".
- Seharusnya: PPN masukan hanya dari faktur pajak masukan yang sah (nomor faktur, vendor PKP) dan tagihan yang disetujui; BPHTB/PPh/biaya pemerintah bukan objek PPN masukan.
- Dampak: SPT yang direkonstruksi dari modul ini memuat kredit pajak masukan fiktif (kurang bayar tersamar menjadi lebih bayar); angka juga tidak masuk jurnal (GL-04 ronde 1: PPN masukan tidak dibukukan). Rekap diberi label "worksheet" tetapi diekspor ke SPT.
- Saran: tambah `ppn_amount`, `faktur_pajak_no`, `vendor_pkp` pada tagihan; hitung dari data itu; jurnal PPN masukan.

### [FN-41] [Severity: Sedang — PK-17 belum tertutup] Tarif & dasar PPh potongan bebas; tak ada penanganan non-NPWP; tak ada setor PPh potongan
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- Lokasi: `routers/ap_router.py:130-190` (`rate` bebas 0<r≤100, `base` bebas), `models_p49.BillPayWithholding`, `withholding_engine.RATE_KEYS` (satu `tax.pph4_2_konstruksi_rate=1,75`), `withholding_engine._vendor_identity` (NPWP hanya dicetak, tidak mempengaruhi tarif).
- Reproduksi: bayar tagihan Rp 10 jt dengan `pph4_2_konstruksi` `rate:0.01` → potongan Rp 100, bukti potong `0100000002` terbit; `pph23` `rate:50` → potongan **Rp 500.000 dari Rp 1 jt**, bukti potong terbit; `pph23` `rate:2` → Rp 20.000 (benar). Tarif di Pusat Konfigurasi hanya default tampilan, tidak ditegakkan. Dasar default = nominal bayar (`payload.base or payload.amount`) sedangkan modul PPN mengasumsikan tagihan **inklusif** PPN (FN-40): dasar PPh seharusnya DPP tanpa PPN.
- Regulasi (menurut pengetahuan auditor; mohon konfirmasi konsultan pajak): PPh 4(2) jasa konstruksi berbeda per kualifikasi (kecil 1,75%, menengah/besar 2,65%, tanpa kualifikasi 4%, perencana/pengawas 3,5%/6%); PPh 23 tarif 2% naik 100% bila tidak ber-NPWP. Modul hanya punya satu tarif per jenis dan tidak mengenal kualifikasi vendor.
- Jalur setor: `2-1300` menampung potongan (uji: −Rp 1,3 jt → bertambah 520.100) tetapi tak ada endpoint/layar menyetor PPh potongan vendor ke kas negara (hanya `tax_records` ppn/pph/bphtb penjualan). Bukti potong terbit tanpa pasangan setoran.
- Terverifikasi OK: potongan ≥ nilai bayar ditolak (dasar Rp 900 jt × 2% pada bayar Rp 1 jt → 400); jurnal pembayaran dengan potongan seimbang (Dr 2-1100 1.000.000 / Cr 1-1201 980.000 / Cr 2-1300 20.000).

### [FN-42] [Severity: Sedang — PK-15 sebagian] Validasi tagihan manual: nilai/vendor/proyek/jatuh tempo rusak diterima; duplikasi faktur lolos; tanpa jatuh tempo tak pernah menua
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (`f03-utang.png` — tiga tagihan "AUDIT Vendor AP1" kembar; dasbor menampilkan "8 menunggu approval (Rp 1.000.000.287.850.000)")
- Reproduksi: `POST /finance/ap/bills`: `claimed 10^15` → 200; `vendor ""` → 200; `project_id:"proyek-fiktif-xxx"` → 200; `due_date:"bukan-tanggal"` → 200. Faktur: `vendor_invoice_no "INV-AUDIT-001"` lalu `"inv-audit-001"` dan vendor `"AUDIT Vendor AP1 "` (spasi) → keduanya 200 (cek duplikat peka huruf/spasi) → tiga tagihan untuk satu faktur (UI API `ap-bill-invoice-no` hanya mengandalkan ini).
- Aging: `_days_overdue(None|rusak)` = 0 → tagihan tanpa jatuh tempo selalu "Lancar" (seed: tagihan CV Alat Berat Nusantara Rp 385 jt tanpa jatuh tempo menempati kolom "Lancar" Rp 490,7 jt). Jatuh tempo tidak diturunkan dari termin pembayaran vendor.
- Tagihan manual tidak wajib PO → tidak ada 3-way match (PK-15 sisi ini tetap). Tagihan manual selalu didebit **WIP 1-1600** (`gl_engine._gl_ap_approved:360-378`): biaya non-konstruksi (jasa umum, notaris) tak pernah menjadi beban kecuali lewat PO `general`; uji `JV/2026/00089` Dr 2-1700 (akrual HPP dilunasi lebih dulu) Rp 10 jt.
- Saran: normalisasi (trim/upper) nomor faktur; wajibkan vendor terdaftar, proyek valid, jatuh tempo valid (default dari termin vendor); batas atas wajar atau persetujuan bertingkat (belum ada batas wewenang, PK-07 butir kedua).

### [FN-43] [Severity: Sedang — PK-16 belum tertutup] Retensi bawaan 5% pada tagihan manual/PO tidak punya jalur pencairan
- Label bukti: [DARI-KODE] + [TERBUKTI-API]
- Lokasi: `models.ApBillCreate.retention_pct = 5`, UI `ApPanel.js:168` default "5"; `finance_ap.ap_retention_release_sweeper` memerlukan `release_due_at` yang **tidak pernah diisi siapa pun** (grep seluruh backend); pencairan retensi resmi hanya untuk retensi termin subkon (`/subcon/retentions/{id}/release`).
- Reproduksi: tagihan uji Rp 10 jt retensi 5% → `JV` Cr 2-1200 Rp 500.000; tidak ada endpoint/layar mencairkannya; `retention_released` tetap false. Akun 2-1200 menumpuk (kontrol 2-1200 hijau karena subledger memuat retensi yang sama).
- Catatan kode: bila `release_due_at` kelak diisi, sweeper menandai dilepas dan menulis `payments_out` **tanpa jurnal dan tanpa kas keluar** — pencairan fiktif.
- Dampak: utang retensi vendor tak pernah lunas; vendor tidak pernah menerima haknya lewat sistem.

### [FN-44] [Severity: Sedang] Tagihan AP "yatim" dari kegagalan jurnal dan dari pintu otomatis memintas persetujuan
- Lihat 08_FINANCE_1_KOMPONEN_BIAYA.md FN-04 (beban developer disetujui otomatis oleh pembuat dan dibayar akun yang sama) dan FN-05 (tagihan `approved` tanpa jurnal bila akun GL salah). Keduanya menghasilkan `ap_invoices.kind="sales_cost"` yang melewati `approve_ap_bill` (tidak lewat `reserved()`/maker-checker) sehingga pemeriksaan `_assert_payer_separate` dilewati (`approved_by == created_by`).

### [FN-45] [Severity: Rendah] Lain-lain
- Tidak ada tanggal bayar pada pembayaran AP (`ApPay` tanpa tanggal) — jurnal bertanggal waktu input (padanan IN-19); transfer yang dibayar kemarin dan dicatat hari ini jatuh ke tanggal/periode berikutnya.
- `DEDUCTION_GL.get(kind, "4-1200")`: jenis potongan tak dikenal dikredit ke Pendapatan Lain-lain (`gl_engine.py:395`).
- Tabel Utang di 1440 px: kolom Sisa/Jatuh tempo/Status tertutup kolom Aksi sticky (finance-ar FN-29).
- Tombol "Setujui" tampil abu-abu (disabled) untuk pembuat tagihan — selaras SoD (positif); tombol "Bayar" tidak diberi penjelasan bila penyetuju = pengguna (hanya ditolak saat diklik, 400).

---
## Verifikasi ulang klaim ronde 1 (area AP)
| ID | Status | Bukti |
|---|---|---|
| PK-01/02 (pembayaran ganda paralel) | **Tertutup** untuk jalur AP/cost (uji 2 pembayaran paralel: 409+200); AP: bayar melebihi sisa 400 | `finance_ap.pay_ap_bill` `once`+`reserved` |
| PK-07 (SoD) | **Tertutup untuk alur tagihan biasa**; bocor via beban developer | FN-04 |
| PK-08 (retensi 0–100) | **Tertutup** | −5 → 422, 150 → 422, 100 → 200 |
| PK-15 (faktur kembar, vendor/proyek fiktif) | **Sebagian**: ada pencegahan faktur kembar persis sama; varian huruf/spasi lolos; vendor/proyek fiktif lolos | FN-42 |
| PK-16 (retensi tanpa pencairan) | **Belum** | FN-43 |
| PK-17 (tarif/dasar PPh bebas; tak ada setor) | **Belum** | FN-41 |
| PK-18 (PPN keluaran sebagai beban pajak) | **Belum** (BPHTB juga) | finance-komponen-biaya FN-07, finance-ar FN-24 |
| GL-04 (PPN tidak dipisah) | **Belum** | FN-40 |

## Terverifikasi OK
- Alur: buat (finance) → setujui oleh pembuat → 400 "Pemisahan tugas…"; setujui oleh finlead → 200 + `JV/2026/00089` Dr 2-1700 10.000.000 / Cr 2-1100 9.500.000 / Cr 2-1200 500.000 (seimbang); bayar oleh penyetuju → 400; oleh finance lain → 200 (`2-1100` Dr / bank Cr); bayar melebihi sisa → 400 dengan angka; paralel → satu efek.
- Retensi subkon: `request-release` (PM) lalu `release` hanya `finance:manage` (PM 403, finlead 200); jurnal Dr 2-1200 / Cr 2-1100 Rp 1.200.000; tagihan pencairan retensi tercatat; tie-out 2-1200 tetap cocok (5.300.000 → 4.100.000).
- Tie-out: 2-1100 GL = Σ tagihan disetujui belum lunas (kecuali tagihan yatim FN-05: **terdeteksi** `diff −2.000.000`, banner di dasbor); 2-1200 cocok; aging AP = Σ outstanding tagihan disetujui.
- Bukti potong: terbit bernomor berurutan per pembayaran; `withholding_total` tagihan akurat.
- Retensi 0 dan 100% tidak menimbulkan jurnal tak seimbang.

## Tidak bisa diverifikasi
- PO → GRN → tagihan (3-way), termin SPK ber-opname dan potongan uang muka/denda/bon (dipegang auditor pengadaan; seed memiliki retensi/termin demo yang dipakai hanya untuk uji pencairan retensi).
- Penyetoran PPh potongan ke kas negara (tidak ada fitur) dan e-Bupot/XML (di luar cakupan).
- Perilaku multi-worker.

## Pertanyaan terbuka
1. Tagihan vendor biasanya sudah termasuk PPN (inklusif) atau terpisah? Menentukan dasar PPh dan PPN masukan.
2. Perlu kualifikasi vendor (kecil/menengah/besar, PKP, NPWP) pada master vendor untuk tarif PPh?
3. Batas wewenang bertingkat untuk persetujuan/pembayaran tagihan berdasarkan nilai?
