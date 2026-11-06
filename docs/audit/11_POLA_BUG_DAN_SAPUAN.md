# 11 — Pola bug, duplikasi, cacat logika & SSOT: penelusuran mendalam

Tanggal: 6 Nov 2026 · Kode: cabang `claude/wizardly-heisenberg-7onk5l` (sesudah 204 tes regresi ronde 1–2)
Permintaan: "dari pola-pola bug yang anda temukan — duplikasi, cacat logika, SSOT yang salah — telusuri lebih dalam."

Cara kerja: ±186 ID temuan ronde 1–3 (`IN- PK- GL- KT- WA- PG- FN- EP-`) dikelompokkan menjadi **pola**;
tiap pola dicari kemunculan lainnya di seluruh `backend/` (sapuan statis AST, alat ada di
`scripts/pattern_sweep.py`), lalu kandidat terbaik **dibuktikan lewat API/fungsi sungguhan** pada instance
terpisah. Label bukti: **TERBUKTI** (dijalankan, hasil terukur) · **KODE** (dibaca, belum dijalankan) ·
**KANDIDAT** (angka sapuan statis; bisa positif palsu).

## 1. Ringkasan

1. Hampir semua bug yang ditemukan sejauh ini adalah **segelintir pola yang berulang**, bukan bug yang berdiri sendiri.
   Perbaikan ronde 1–2 menutup *kemunculan yang ditemukan*, bukan *polanya* — pola yang sama masih muncul
   di jalur yang belum disentuh. Bukti paling jelas ada di bagian 3.1: aturan "cek saldo sebelum uang keluar"
   (PK-06) dipasang di 17 jalur, tetapi **transfer internal kas/bank tidak punya cek di titik persetujuan**
   dan 9 jalur lain mengecek tanpa kunci.
2. Akar masalahnya struktural (bagian 5): tidak ada **satu pintu transaksi uang**; tiap jalur menyusun sendiri
   gabungan `once/cas/mutex/assert_funds/SoD` dan memilih sebagian. Selama itu begitu, perbaikan per-jalur
   akan terus bocor di jalur berikutnya.
3. Lima temuan **baru** dari sapuan saya sendiri, semuanya terbukti (PL-01…PL-05, bagian 3); ditambah **dua celah Kritis keamanan** (AZ-11/AZ-12) dan 23 temuan konkurensi/status/yatim dari agen (bagian 8). Yang paling berat: saldo kas
   bisa dijebol lewat transfer internal (−Rp 12,5 jt dari Kas Besar Rp 17,5 jt) dan lewat dua pembelian aset
   bersamaan (Rekening Operasional Rp 7,75 M → **−Rp 1,55 M**).
4. Dua dugaan saya sendiri **gugur** setelah diuji (bagian 6) — dicatat supaya tidak diulang.
5. Pagar pencegah dibuat: `scripts/pattern_sweep.py` (ratchet: angka pola tak boleh naik). Rekomendasi
   pagar lain di bagian 7.

## 2. Taksonomi pola dan sensus

Angka "sapuan" = jumlah **kandidat** di seluruh backend (bukan jumlah bug). "Terbukti ulang" = ID lama yang
kemunculan barunya sudah dibuktikan.

| # | Pola | Wujud | ID lama | Sapuan statis | Bukti kemunculan baru |
|---|---|---|---|---|---|
| P1 | **Baca → hitung → tulis tanpa penjaga atomik** | dua permintaan membaca keadaan lama, sama-sama lolos | IN-01/02, PK-01/02, PG-04, GL-22, KT-02/08 | 191 fungsi baca-lalu-tulis tanpa penjaga | PL-02 |
| P2 | **Cek di tahap yang salah** (cek di pembuat, bukan di pemberi persetujuan / titik pembukuan) | maker lolos cek, checker menyetujui belakangan saat saldo sudah berubah | PK-06 | — | **PL-01** |
| P3 | **Cek dana tanpa kunci** | `assert_funds` ada, tetapi dua pengeluaran bersamaan sama-sama lolos | PK-06 | 9 fungsi `assert_funds` tanpa `cash_lock` | **PL-03** |
| P4 | **Salinan denormalisasi tak tersinkron** | nama/kode dikopi ke dokumen anak, master diganti, kopi basi | KT-15, FN-13 | 82 pasangan terdeteksi di data, **52 (63%) tak terdaftar** di `DENORM_MAP` | **PL-04** |
| P5 | **Agregat turunan yang disimpan** (`paid/outstanding/balance`) | angka tersimpan ditulis di banyak tempat → drift | GL-20, PG-15, FN-28 | `outstanding` ditulis di 10 berkas, `paid` 7, `balance` 5; rekonsiliasi hanya 7 pemeriksaan | (lihat 4.3) |
| P6 | **Konstanta bisnis ditanam** | kode akun GL, peran, tarif | GL-19, FN-05, PG-18 | 40 kode akun unik, **175 kemunculan di 26 berkas** | — |
| P7 | **Mesin status tanpa penjaga status** | status ditulis tanpa syarat status sekarang | PG-05/06, FN-09 | 115 penulisan status tanpa syarat di 60 berkas | **PL-02** |
| P8 | **Pintu ganda untuk satu operasi** (SSOT) | 3 pintu pencairan KPR, 2 kas bon, 2 model biaya, 2 resolver proyek, jalur skema lama vs baru | KT-01/03, IN-11, GL-16/25, FN-20 | 4 konsep dengan >1 implementasi (4.4) | — |
| P9 | **Kegagalan senyap** | `except Exception` tanpa log/raise; event gagal permanen | GL-09 | 41 handler di 35 berkas | KODE (4.5) |
| P10 | **Waktu: UTC vs WIB, potong string** | tanggal bisnis diambil dari UTC | GL-15, GL-06 | 31 `ts[:10]`/`now_iso()[:10]` sebagai tanggal bisnis di 20 berkas; 214 `[:10]`, 24 `[:7]` | **PL-05** |
| P11 | **Kebocoran lingkup organisasi** | query by-id tanpa `org_id` | WA-09, FN-13 | 191 query router by-id tanpa `org_id` (banyak aman: lihat 4.6) | (menunggu agen RBAC) |
| P12 | **Dedup manual find→insert** | duplikat lolos balapan | KT-16/17, PG-22 | 105 | — |
| P13 | **Hasil terpotong / pemindaian besar** | `to_list(N)` + urut naik → data terbaru hilang | WA-03/10 | 109 `sort naik + to_list(N)`; 31 pemindaian ≥50 rb | — |
| P14 | **Izin tak sepadan dengan efek** | endpoint tulis/kirim hanya `view`; penegakan hanya di UI | PG-17/18 | 13 endpoint mutasi hanya izin `view` | (menunggu agen RBAC) |
| P15 | **Hijau ≠ benar** | gerbang/tes lulus padahal invarian rusak | IN-10 (bukti saya sendiri), GL-28 | gerbang kepatuhan merah pada baseline | — |

## 3. Temuan baru yang terbukti

Semua dijalankan pada instance terpisah (DB seed baru), akun `finance@` sebagai pembuat dan `finlead@`
sebagai penyetuju.

### PL-01 — Transfer internal kas/bank: saldo hanya dicek saat DIBUAT, tidak saat DISETUJUI (Tinggi) · TERBUKTI
`cash_bank.create_transfer` mengecek saldo; `cash_bank.approve_transfer` — yang sebenarnya memposting jurnal —
**tidak memanggil `assert_funds` sama sekali** dan tidak memakai `cash_lock`.

Reproduksi: Kas Besar Rp 17.500.000. Dibuat 3 transfer × Rp 10.000.000 ke Kas Kecil: ketiganya **lolos
dibuat** (masing-masing dicek terhadap saldo penuh). `finlead` menyetujui ketiganya: `[200, 200, 200]`.
**Saldo Kas Besar akhir = −Rp 12.500.000.** Pola yang sama berlaku di semua alur maker-checker yang cek
dananya hanya di sisi pembuat (P2); `approve_transfer` adalah satu-satunya yang saya buktikan.

Perbaikan: panggil `assert_funds` + `cash_lock` di `approve_transfer` (titik pembukuan), bukan di pembuatan.
Cek di pembuatan boleh dipertahankan sebagai peringatan dini.

### PL-02 — Setujui dan tolak transfer bersamaan: dua-duanya sukses, status campur (Sedang) · TERBUKTI
`approve_transfer` dan `reject_transfer` membaca `status == pending` lalu menulis status **tanpa syarat**
(`update_one({"id": …})`). Uji paralel: `approve → 200`, `reject → 200`; dokumen akhir `status=posted`,
`journal_no=JV/…`, **dan** `reject_reason="tes balapan…"`. Bila urutan tulis terbalik, hasilnya `rejected`
padahal jurnal sudah terposting (uang bergerak, status berkata ditolak). Penjaga yang ada (`source_event`
unik) hanya mencegah jurnal ganda, tidak mencegah status kontradiktif.
Pola yang sama dihitung statis di `petty_cash.approve/reject/cancel_advance`, `quotation_engine.decide_discount/convert`,
`warranty_engine.decide/complete/verify`, `pdc_engine` (sebagian sudah dibungkus `locked`), `booking_fee.cancel`.
Perbaikan: `idempotency.transition(coll, {id}, {"status": "pending"}, update)`.

### PL-03 — `assert_funds` tanpa kunci: dua pengeluaran bersamaan menjebol saldo (Tinggi) · TERBUKTI
Docstring `assert_funds` sendiri mengakui batasnya, tetapi akibatnya lebih besar dari "dana pas-pasan":
Dua `POST /fixed-assets/assets` **berbeda nama** bersamaan, masing-masing 60% saldo bank (Rp 4,65 M dari
Rp 7,75 M): keduanya `200`. **Rekening Operasional: Rp 7.751.644.936 → −Rp 1.550.328.986.**
`once()` tidak menolong karena kuncinya memuat nama aset (permintaan berbeda).
Fungsi yang memanggil `assert_funds` tanpa `cash_lock`/`mutex` (dari sapuan): `finance_commission.pay_commission`,
`finance_engine.refund_deposit`, `fixed_assets.create_asset`, `fund_requests.disburse`, `labor_engine.pay_payroll`,
`marketing_fee.pay_fee`, `petty_cash.disburse_advance`, `petty_cash.settle_advance`, `routers/tax_router.update_record`.
Hanya 5 jalur yang memakai `cash_lock` per rekening (AP, subkon, pinjaman, petty expense, titipan all-in); refund pembatalan
mengunci per pengajuan, bukan per rekening. Hanya aset tetap yang saya jalankan; sisanya KODE.

### PL-04 — Ganti nama master tak menjalar ke salinan: 63% salinan tak terdaftar (Sedang) · TERBUKTI
Dua lapis masalah:
1. **Terdaftar tetapi tak pernah dipicu**: `DENORM_MAP` memuat 35 pasangan di 10 master, tetapi
   `cascade_master_change` hanya dipanggil untuk 7 master (customers, leads, projects, subcontractors,
   construction_phases, skema komisi, skema pembayaran). `units`, `spk`, `purchase_orders` (7 pasangan) tidak pernah dipicu.
2. **Tak terdaftar**: sapuan data (`scripts/denorm_audit.py <db>`) menemukan 82 pasangan "FK + salinan nama/kode"
   di data nyata; **52 tidak ada di `DENORM_MAP`** (mis. `cash_account_name` di kuitansi/voucher/kas bon,
   `vendor_name` di `vendor_prices`, `worker_name`, `campaign_name`, `unit_code` di `build_items`).
Reproduksi: ganti nama "Rekening Operasional" → **31 dokumen tetap bernama lama** (kuitansi 3, voucher kas 21,
pembayaran keluar 2, transaksi bank 3, mutasi bank 1, kas bon 1). Ganti nama vendor → 3 baris `vendor_prices`
basi. Akibat: kuitansi/voucher bernama rekening lama berdampingan dengan laporan bernama baru; pencarian
berdasarkan nama baru tidak menemukannya (gejala yang sama dengan KT-15).
Perbaikan jangka panjang: jangan menyalin — simpan FK saja dan resolusi nama saat baca (atau satu fungsi
`update_master()` yang wajib dipakai semua router, ditegakkan oleh tes yang membandingkan `DENORM_MAP` dengan
hasil sapuan data).

### PL-05 — Tanggal bisnis diambil dari UTC: "hari ini" ditolak sebagai "masa depan" dini hari (Sedang) · TERBUKTI (simulasi jam)
GL-15 memperbaiki tanggal **jurnal** ke WIB (`today_wib`, `to_wib_iso`), tetapi 20 berkas lain masih memakai
`ts[:10]`/`now_iso()[:10]` (UTC) sebagai tanggal bisnis: `pdc_engine`, `petty_expense`, `cash_bank` (tanggal
transfer), `labor_engine` (absensi), `kpr_engine`, `kpr_disburse`, `contract_legal`, `cancellation_engine`, dsb.
Dengan jam disimulasikan 05:00 WIB (=22:00 UTC) pada fungsi sebenarnya:
`pdc_engine._receive_locked(received_date="2026-11-07")` → **"Tanggal terima tidak boleh di masa depan."**
padahal itu hari ini menurut WIB. Antara 00:00–07:00 WIB: input "hari ini" ditolak (giro, pengeluaran kas kecil,
absensi), dan tanggal bawaan (transfer kas, SP3K, akad…) jatuh sehari lebih awal — pada tanggal 1 pukul 00–07 WIB
menjadi **bulan sebelumnya** (periode yang mungkin sudah ditutup).
Perbaikan: satu fungsi `today_wib()` untuk semua tanggal bisnis; aturan lint melarang `now_iso()[:10]`.

## 4. Penelusuran per pola

### 4.1 Pola cek-dana (P2/P3) — peta lengkap
| Jalur uang keluar | `assert_funds` | `cash_lock`/`mutex` | Catatan |
|---|:-:|:-:|---|
| AP (`finance_ap`) | ✔ | ✔ | |
| Subkon (`subcon_finance`) | ✔ | ✔ | |
| Pinjaman (`loans`) | ✔ | ✔ | |
| Kas kecil/pengeluaran (`petty_expense`) | ✔ | ✔ | |
| Penyaluran titipan all-in | ✔ | ✔ | |
| Aset tetap, komisi, upah, fee marketing, pengajuan dana, kas bon (cair & pertanggungjawaban), pajak, refund titipan | ✔ | ✘ | PL-03 |
| **Transfer internal (setujui)** | **✘** | **✘** | **PL-01** |
| Refund pembatalan (`cancellation_engine`) | ✔ | kunci **per pengajuan**, bukan per rekening | dua pengajuan berbeda dari rekening sama tetap bisa balapan (KODE) |

### 4.2 Pola status tanpa penjaga (P7) — kandidat berisiko uang/stok
`cash_bank.approve/reject_transfer` (PL-02 TERBUKTI), `petty_cash.approve/reject/cancel_advance`,
`quotation_engine.decide_discount/convert`, `warranty_engine.decide/complete/verify/close`,
`subcon_claims_router._approve_item_claim/_approve_lumpsum_claim/approve_change_order`,
`materials_router.approve/issue_requisition`, `fixed_assets.run_depreciation/dispose_asset`,
`booking_fee.cancel`, `allin_amend.decide_amendment`. (Agen konkurensi menguji sebagian; lihat bagian 8.)

### 4.3 Agregat tersimpan (P5) vs cakupan rekonsiliasi
`/finance/reconcile` punya **7 pemeriksaan**: 2-1100, 2-1200, 2-1400, 2-1450, 2-1600, 1-1500, neraca saldo.
Agregat tersimpan yang **tidak** punya pemeriksaan: AR (`ar_invoices.paid/outstanding` ↔ kuitansi ↔ 1-1300),
kas/bank (saldo GL ↔ mutasi bank), titipan biaya 2-1470, persediaan 1-1400, WIP 1-1600…, aset tetap (buku ↔ register ↔ akumulasi),
saldo pinjaman, komisi dibayar, kemajuan SPK/klaim. Setiap agregat ditulis di 5–10 berkas
(`outstanding`: allin_engine, ap_void, booking_fee, deal_cancel, finance_ap, finance_engine, force_delete, …),
sehingga tiap penulis baru adalah peluang drift tanpa alarm. *Catatan metode*: percobaan saya mencocokkan
AR↔kuitansi lewat skrip ad-hoc **gagal valid** (struktur alokasi per `item_id`, bukan per faktur) — saya tidak
mengklaim ada selisih; yang terbukti hanya bahwa pemeriksaannya **tidak ada** di rekonsiliasi.

### 4.4 Duplikasi konsep (P8)
Fungsi dengan konsep sama di banyak tempat (hasil sapuan nama): `balance_sheet` ada di `gl_engine` **dan** `gl_reports`
(dua endpoint, dua layar), `account_balance` di `cash_bank` (agregasi DB) **dan** `revrec_cogs` (loop Python),
`progress` ada ≥4 definisi (`engine.recompute_project_progress`, `build_engine.recompute_unit_progress`,
`metrics/project`, `portal_router`), komitmen 5 definisi (PG-02), `outstanding` 3 varian di `finance_engine`.
Pengecekan: kedua neraca/laba-rugi **cocok** bila rentang tanggalnya sama (Rp 268.307.439) — risiko di sini adalah
drift masa depan, bukan selisih sekarang.

### 4.5 Kegagalan senyap (P9)
41 handler `except Exception` tanpa log/raise. Yang berdampak uang (KODE): `finance_engine.py` jadwal tagihan —
tanggal dasar tak terbaca → **jatuh tempo dipasang dari "sekarang"** tanpa peringatan; `days_overdue` — jatuh
tempo tak terbaca → **0 hari terlambat, denda hilang** tanpa jejak; `deal_cancel._release_unit` — sinkronisasi
ikatan unit gagal ditelan. Masukannya divalidasi di router sehingga probabilitasnya rendah; yang berbahaya adalah
**tidak adanya jejak** bila terjadi.

### 4.6 Lingkup organisasi & izin (P11/P14)
Sapuan: 191 query router by-id tanpa `org_id` di 48 berkas — sebagian besar aman (id UUID + akses diperiksa di
tempat lain, mis. `assert_project_access`), jadi **bukan** angka kebocoran. 13 endpoint mutasi hanya meminta
izin `view`: contoh `POST /documents/send-wa` (mengirim PDF ke WhatsApp pembeli dengan izin `documents:view`),
`partners/refresh_stats`, `*/preview`. `PUT /build-ops/policy` meminta `view` tetapi memeriksa peran admin di
badan fungsi — benar, tetapi pola "peran ditanam di kode" (P6). Hasil matriks lengkap: bagian 8.

## 5. Akar masalah (mengapa polanya berulang)

1. **Tidak ada pintu transaksi uang tunggal.** Tiap jalur (±17) merakit sendiri: kunci idempotensi, CAS, cek saldo,
   SoD, jurnal, event. Hasilnya tiap jalur punya himpunan bagian yang berbeda (4.1). Perbaikan per-jalur menurunkan
   jumlah celah tetapi tidak pernah menutup kelasnya.
2. **MongoDB tanpa transaksi multi-dokumen** + pola saga manual (`reserved`/undo best-effort, event outbox).
   Setiap "tulis subledger → posting jurnal → emit" adalah jendela keadaan setengah jadi; status sementara
   (`disbursing`, `settling`, `approving`, `paying`, `voiding`) bisa menggantung bila proses mati.
3. **Invarian tidak ditulis sebagai kode.** Rekonsiliasi hanya 7 pemeriksaan, jadi pelanggaran invarian (saldo
   negatif, jurnal tak seimbang per sumber, agregat ≠ rincian) hanya ketahuan oleh auditor manual.
4. **Pertumbuhan per-fase (Fase 57A … 98D)**: modul paralel menyelesaikan masalah yang sama dengan cara berbeda
   (dua kas bon, dua model biaya, dua neraca) tanpa ada yang memensiunkan yang lama.
5. **Konfigurasi dekoratif & konstanta tertanam**: 175 literal kode akun di 26 berkas; Pusat Konfigurasi tidak
   benar-benar mengendalikan perilaku (FN-01, GL-19).
6. **Ukuran kualitas yang salah**: gerbang kepatuhan sudah merah di baseline (4 berkas >800 baris); tes hijau
   tidak berarti invarian bisnis terjaga (P15).

## 6. Dugaan yang gugur (jangan diulang)
- "Laba rugi `/gl/reports/income-statement` membuang akun 6-1600 (Rp 144,7 jt)": **salah** — selisih hanya karena
  periode bawaan (bulan berjalan vs seluruh waktu). Dengan rentang sama keduanya Rp 268.307.439.
- "Selisih AR↔kuitansi di seed": **tidak valid** (struktur data saya salah baca) — tidak diklaim.

## 7. Pagar sistemik yang direkomendasikan (urut manfaat/biaya)

| # | Pagar | Menutup | Biaya |
|---|---|---|---|
| G1 | **`money_op()` — satu pintu uang keluar**: dekorator/konteks yang selalu menjalankan `cash_lock` → `assert_funds` → `once` → blok → catat; semua `post_journal` ke akun kas wajib lewat sini (lint). | P1–P3, PL-01/03 | Sedang; bisa bertahap per jalur |
| G2 | **Ratchet sapuan** `scripts/pattern_sweep.py --check` di CI (sudah ada, baseline tersimpan). | semua pola statis; mencegah kemunculan baru | Selesai |
| G3 | **Invarian sebagai tes**: `/finance/reconcile` diperluas ke AR, kas↔mutasi, titipan biaya, persediaan, aset, pinjaman; dijalankan sebagai fixture di akhir tiap suite tes. | P5, P15 | Sedang |
| G4 | **Fuzz invarian** lintas entitas (alat agen fuzz) dijalankan malam hari terhadap seed. | P1, P7, P15 | Rendah (alat ada) |
| G5 | **`update_master()` tunggal + tes DENORM**: tiap router master memakainya; tes membandingkan `DENORM_MAP` ↔ sapuan data. | P4 | Rendah–sedang |
| G6 | **Satu `today_wib()`**; lint melarang `now_iso()[:10]`; `period_of()` untuk periode. | P10 | Rendah |
| G7 | **Mesin status deklaratif** (tabel transisi sah + `transition()` wajib) untuk entitas uang/stok. | P7 | Sedang |
| G8 | **Pensiun pintu ganda**: daftar pintu lama + tanggal matinya; flag `legacy_*` dipantau. | P8 | Sedang |

## 8. Hasil penyapu dinamis (agen)

Ketiga agen sudah melapor; laporan lengkap: `11a_…` (konkurensi/status/yatim), `11b_…` (otorisasi/lingkup org), `11c_…` (fuzz invarian).
**Klaim agen bukan fakta sampai saya verifikasi** — hasil
verifikasi saya:

### 8.1 Otorisasi & lingkup organisasi (`11b`)
| Klaim agen | Hasil verifikasi saya |
|---|---|
| Owner dapat membuat `super_admin` → akses lintas-tenant (AZ-11) | **Terbukti** — pengguna baru login dan melihat 2 org |
| Owner org lain mengganti sandi pengguna org SIPRO (AZ-12) | **Terbukti** — login dengan sandi baru berhasil |
| Lead/deal org A terbaca & terubah oleh org B (AZ-01) | **Terbukti** untuk baca, ubah lead, dan booking deal; **tidak** terbukti untuk batal (409) dan hapus (no-op 200) |
| OTP portal tanpa kunci percobaan (AZ-10) | Sebab terkonfirmasi di kode (`attempts` tidak pernah ditambah) |
| 8 temuan lain (AZ-02…09) | Penyebab terkonfirmasi di kode; skenario penuh = klaim agen |

### 8.2 Konkurensi, mesin status, yatim (`11a`) — 23 temuan baru, semua diklaim terbukti lewat API
Yang saya konfirmasi di kode: `recognize_revenue` tidak memeriksa status deal (PK3-05, deal batal bisa "completed" dan menjurnal
pendapatan Rp 600 jt); `materials_router.create_txn` baca-stok→insert tanpa penjaga (PK3-02); `toggle_unit_block(blocked=false)` tanpa syarat
status (PK3-04). Pola yang diperluas oleh laporan ini:

- **P1/P7 lebih luas dari dugaan statis saya**: dari 530 endpoint mutasi hanya **95 (18%)** punya penjaga atomik kuat, **179 (34%)** tanpa penjaga;
  146 dari 171 penulisan status menimpa tanpa syarat; 11 dari 15 mesin status yang diuji bisa melompat/mundur.
- **Dua jalur batal** (`deal_cancel` vs `cancellation_engine.decide`) dan **dua jalur hapus** (`force_delete` vs `master_delete`) dengan cakupan
  pembersihan berbeda → yatim (P8 + P12 "orphan"): hapus deal menjangkau 21 dari 31 koleksi ber-`deal_id`, dan salah nama koleksi
  (`pdc_cheques` ≠ `pdc_instruments`).
- Paling berdampak uang: rekap upah ganda (Rp 2,7 jt keluar untuk upah Rp 900 rb), pajak deal batal terbayar Rp 113 jt, pendapatan semu Rp 600 jt,
  satu unit terjual dua kali, stok negatif.
- Dugaan gugur: persetujuan transfer ×3 **tidak** menjurnal ganda (jurnal 1×) — konsisten dengan PL-01: masalahnya cek dana, bukan jurnal ganda.

### 8.3 Fuzz invarian (`11c`, alat di `scripts/fuzz/`)
Alat baru: 74 invarian (65 keras) dan 49 jenis operasi acak, mode berurutan dan serentak, pengecil otomatis. Dijalankan 1.797 operasi
berurutan + 192 putaran serentak: 0 HTTP 5xx, 8 temuan baru. **Jalur uang masuk utama dan AP lolos semua invarian di bawah beban acak** —
kuitansi, titipan, konversi, reservasi, kupon, giro, komisi, AP. Yang bocor adalah **pinggiran siklus hidup** (sesudah BAST/pembatalan/hapus):

| ID | Sev | Ringkas | Verifikasi saya |
|---|---|---|---|
| FZ-01 | Tinggi | Void kuitansi **sesudah BAST** membalik Dr 2-1400 yang sudah nol → kewajiban kontrak −Rp 495 jt | KODE: `_void_receipt_locked` tidak memeriksa pengakuan pendapatan/pembatalan |
| FZ-02 | Tinggi | Void kuitansi sesudah pembatalan disetujui menghidupkan AR deal batal | AGEN |
| FZ-03 | Tinggi | `POST /finance/ar/{deal}/bast` tanpa gerbang: deal `reserved`/**batal** diakui pendapatan Rp 500 jt | KODE + **dua agen independen** (sama dengan PK3-05) |
| FZ-08 | Tinggi | SP3K/akad KPR diterima pada kontrak yang sudah dibatalkan; AR batal hidup lagi | AGEN |
| FZ-04 | Sedang | Hapus-paksa deal: giro tertinggal (salah nama koleksi) dan BKM/BKK yatim | sama dengan PK3-09 |
| FZ-06 | Sedang | Dua retur GRN serentak sama-sama lolos (stok −100) | KODE: `create_return` baca `returned_qty` lalu tulis |
| FZ-07 | Sedang | Hapus-paksa serentak dengan kuitansi/void → jurnal/kuitansi yatim (3/20 dan 2/10 percobaan) | AGEN (probabilistik) |
| FZ-05 | Rendah | `book` selalu menulis `payment_status="booking_fee"` meski AR sudah lunas | AGEN |

**Pola gabungan dari tiga agen:** hampir semua temuan berat berpusat pada satu akar — **tidak ada aturan "keadaan deal/kontrak" yang dibaca bersama oleh
semua jalur uang**. BAST, void kuitansi, SP3K/akad, pajak, upah, komisi, dan fee masing-masing memeriksa (atau tidak memeriksa) status deal dengan cara
sendiri. Satu fungsi `deal_state(deal) → {boleh_terima_uang, boleh_BAST, boleh_void, boleh_KPR, …}` yang dipakai semua jalur akan menutup
kelasnya (G7 + G8 di bagian 7).


## 9. Status perbaikan (diperbarui)

Dikerjakan dan **terbukti** (tes regresi merah pada kode lama, hijau pada kode baru; suite penuh 232 lulus): AZ-11, AZ-12, PL-01, PL-02, PL-03,
PL-05, AZ-01…10, PK3-05/FZ-03, FZ-01, FZ-02, FZ-08, PK3-04, PK3-01, PK3-02, PK3-03; PK3-06 sebagian (setor pajak deal batal ditolak). Rincian dan perubahan
perilaku: `06_STATUS_PERBAIKAN.md` bagian 8. Ratchet sapuan (`scripts/pattern_sweep.py`) turun: tanggal-UTC 31→0, cek-dana-tanpa-kunci 9→0,
set-status-tanpa-syarat 115→112, baca-lalu-tulis 191→188, kode akun literal 175→174.

Lingkup organisasi dan celah otorisasi lain (AZ-01/02/04/05/06/07/08/09/10, `11b`) juga sudah dikerjakan dan terbukti (sapuan `P11` 188→17; suite penuh bertambah 49 tes).

Belum dikerjakan: PL-04 (salinan nama tak tersinkron; 52 pasangan tak terdaftar), pembersihan otomatis dependen saat deal batal (tugas, komisi, fee
marketing, KPR, kupon, catatan pajak — PK3-08), hapus-paksa deal yang bocor (PK3-09, FZ-04, FZ-07), retur GRN serentak (FZ-06), FN-02/03, HMAC/rate-limit
webhook, invarian rekonsiliasi tambahan (G3), dan `money_op()` sebagai pintu tunggal (G1; `funds_guard` adalah langkah pertamanya).
Perlu keputusan pemilik: PG-01 (metode valuasi persediaan) dan 10 keputusan di `06_STATUS_PERBAIKAN.md` bagian 4.
