# GL-5 — Analisis kebutuhan "Konfigurasi koneksi fitur → auto-jurnal → akun/rekening" (Bagian E)

Dasar: gl-1 (peta jurnal), gl-3 (kas/bank), gl-4 (gap). Seluruh "perilaku hari ini" pada tabel adalah hasil baca kode + jurnal yang dibuktikan lewat API.

## 1. Apa yang SUDAH bisa dikonfigurasi hari ini vs hardcode

| Area | Sudah bisa diatur user | Masih hardcode | Bukti |
|---|---|---|---|
| Pusat Konfigurasi (`settings_store.py`, `/config`, 129 kunci / 22 grup) | tarif denda, toleransi, kas kecil (`petty_cash.*`), toleransi bank, tarif PPh 23/4(2), retensi bulan, DP% skema | **nol** kunci tentang akun GL, rekening default, peta jurnal, kebijakan periode/saldo negatif | `GET /settings` — kunci `tax.*`, `payment.late.*`, `petty_cash.*`, `bank.*` |
| Tarif pajak transaksi | `finance_configs` (PPN/BPHTB/PPh/NPOPTKP) lewat `/finance/config/tax` (store TERPISAH dari Pusat Konfigurasi) | akun tujuan pajak (`6-1400`/`2-1300`) | `gl_engine.py:454-485` |
| Komponen biaya all-in | `gl_expense`, `gl_liability`, `gl_ap` per komponen (dropdown dari CoA) | invoice biaya memakai `GL_TITIPAN_BIAYA` hardcode (`allin_engine.py:413`) bukan `gl_liability`; tak ada validasi backend | `routers/allin_router.py:132` |
| Add-on & komponen harga | `gl_account` (dropdown "Akun GL") | **tidak dibaca oleh satu jurnal pun**; pendapatan selalu `4-1100` | `catalog.py:28-67`, `grep gl_account` |
| Master rekening kas/bank | nama, default, aktif, saldo awal, batas imprest | tidak ada proyek, tidak ada tujuan penggunaan, dua jalur pembuatan (`/cash-bank` aman, `/bank` bebas) | gl-3 |
| Skema bayar & komisi | struktur termin, tier komisi | akun beban/utang komisi | `gl_engine.py:394-409` |
| Kategori kas bon/kas kecil | kategori tetap di `reference_p27.CASHBON_ACCOUNT` (kode, bukan data) | kategori→akun (`6-1300`, `6-1200`, `1-1600`) | `reference_p27.py:30-40` |
| Potongan termin subkon | jenis tetap | jenis→akun (`DEDUCTION_GL`) | `reference_p48.py:185` |
| Tipe PO → akun debit AP | – | `{material:1-1400, subcon:1-1600, general:6-1300}`, selain itu `1-1600` | `gl_engine.py:343` |
| Penyusutan, pinjaman, pembatalan, denda, giro, refund, jasa giro, biaya bank, saldo awal | – | semua | gl-1 matriks |
| Bagan akun (CoA) | tambah/ubah nama/nonaktif (CoA) | tak ada penanda "dipakai sistem", tak mengikat posting | GL-13 |

Kesimpulan: **pemetaan "peristiwa → akun" belum menjadi data**; yang ada hanya dua celah parsial (komponen biaya, `gl_account` dekoratif) dan master rekening. Setiap perubahan kebijakan (mis. PPN ke akun PPN Keluaran, per-proyek WIP, rekening escrow KPR) membutuhkan deploy kode.

## 2. Kebutuhan fungsional (rancangan Posting Profile / Account Mapping)

### 2.1 Entitas
1. **Katalog Peristiwa Posting** (`posting_events`, dimiliki kode, read-only di UI): `event_code` (mis. `sales.receipt`), label, modul asal, pemicu (endpoint/event), **variabel yang tersedia** (`amount`, `net`, `retention`, `withheld`, `deduction[kind]`, `cleared`, `revenue`, `cogs`, `po_type`, `method`, `category`, `scheme`, `is_recognized`, `tax_type`…), **dimensi yang tersedia** (`project_id`, `unit_id`, `deal_id`, `cash_account_id`), dan **peran akun yang wajib terisi**.
2. **Peran Akun** (`account_roles`): lapisan indirection bermakna bisnis agar profil tidak menyebar kode literal: `CASH_DEFAULT`, `BANK_DEFAULT`, `AR_UNIT`, `CONTRACT_LIABILITY`, `CUSTOMER_DEPOSIT`, `CUSTOMER_COST_TRUST` (2-1470), `REFUND_PAYABLE`, `AP_TRADE`, `RETENTION_PAYABLE`, `TAX_PAYABLE`, `VAT_OUTPUT`, `VAT_INPUT`, `WIP`, `INVENTORY`, `COGS`, `COGS_ACCRUAL`, `REVENUE_UNIT`, `REVENUE_OTHER`, `REVENUE_PENALTY`, `COMMISSION_EXPENSE/PAYABLE`, `MKT_FEE_EXPENSE/PAYABLE`, `STAFF_ADVANCE`, `SUBCON_ADVANCE`, `FIXED_ASSET`, `ACCUM_DEPR`, `DEPR_EXPENSE`, `LOAN_PAYABLE`, `INTEREST_EXPENSE`, `OPENING_EQUITY`, `RETAINED_EARNINGS`, dll. Peran → akun default (diubah lewat versi, bukan edit langsung).
3. **Profil Posting** (`posting_profiles`): `event_code`, `name`, `condition` (JSON aman: `field op value`, mis. `po_type == "material"`, `is_recognized == true`, `method in ["cash","tunai"]`), `priority`, `scope` (organisasi | proyek | cluster — meniru lapisan `settings_store`), `effective_from/to` (berdasar TANGGAL TRANSAKSI), `status` (`draft|pending_approval|active|retired`), `version`, `created_by/approved_by/why`.
4. **Baris Profil** (`posting_profile_lines`): `seq`, `side (D/K)`, `account` = `role:<R>` | `code:<akun>` | `cash:by_context`, `amount` = nama variabel/ekspresi terbatas (mis. `amount - withheld`), `memo_template`, `dimension` (`project|unit|deal` diambil dari konteks), `optional_if_zero`.
5. **Aturan Rute Rekening** (`cash_routing_rules`): memetakan (peristiwa/kategori, metode bayar, proyek) → `cash_account_id` default; aturan `kind` yang diizinkan (kas/bank), larangan saldo negatif (`block|warn|allow`), dan apakah rekening WAJIB dipilih user.
6. **Jejak posting**: setiap jurnal otomatis menyimpan `profile_id`, `profile_version`, `inputs_hash`, dan `dimensions` (proyek/unit/deal/rekening-id) — fondasi untuk laporan per proyek tanpa resolver (GL-11/GL-25).

### 2.2 Siapa yang boleh mengubah
* Pembuat profil: Manajer Keuangan (`gl:config_draft`); penyetuju berbeda orang: Direksi/Owner (`gl:config_approve`) — maker-checker. Super admin tidak melewati checker.
* Peran akun: hanya pemilik buku (Owner/Direksi) dengan alasan tertulis ≥10 huruf (mengikuti pola `sensitive` di `settings_store`).
* Semua perubahan masuk `history` & audit log (siapa, kapan, alasan, diff).

### 2.3 Validasi saat simpan (dry-run wajib sebelum aktif)
| Validasi | Alasan |
|---|---|
| Akun ada, `is_active`, bukan header/induk | mencegah GL-13 / jurnal ke induk kas |
| Tipe akun sesuai peran (mis. `CUSTOMER_DEPOSIT` harus liability; `REVENUE_*` revenue; `CASH_*` hanya lewat rute rekening) | mencegah akun beban terpasang sebagai titipan (`gl_liability` hari ini tak divalidasi) |
| Akun kas/bank TIDAK boleh ditulis sebagai `code:` — hanya `cash:by_context` | induk 1-1100/1-1200 terkunci; saldo per rekening utuh |
| Σ debit = Σ kredit untuk SETIAP kombinasi variabel contoh (uji simbolik/contoh) | jurnal selalu seimbang |
| Tidak ada tumpang-tindih (event, kondisi, scope, periode efektif) dengan prioritas sama | satu profil menang, deterministik |
| Efektif ke depan saja; tidak boleh mengubah profil yang periodenya sudah tertutup | tidak mengubah saldo historis |
| Kondisi memakai variabel yang disediakan katalog | profil tak bisa merujuk data yang tidak ada |
| Wajib satu profil `default` per peristiwa (tak boleh dihapus, hanya diversi) | tidak pernah "tanpa profil" |

### 2.4 Perilaku saat konfigurasi hilang/tidak valid (disarankan: FAIL-CLOSED untuk transaksi uang)
* Profil resolusi gagal / akun tidak lagi valid → **transaksi sumber DITOLAK sinkron dengan pesan jelas** ("peristiwa X belum punya profil posting yang berlaku pada tanggal Y"), bukan lolos lalu `failed` asinkron seperti GL-09.
* Tidak ada fallback diam-diam ke akun lain (hari ini `strict=False` jatuh ke rekening default — lihat gl-3 §3). Satu-satunya "default" adalah profil sistem bawaan versi 0 yang di-seed dari tabel §5 (tak bisa dihapus).
* Event yang terlanjur antre → status `menunggu_profil` (terlihat di layar Kesehatan, bisa diproses ulang), bukan `failed` permanen.
* Operasi administrasi (CoA nonaktif pada akun yang dirujuk profil aktif) → ditolak.

### 2.5 Jejak audit & versi
* Versi immutable; aktivasi versi baru menutup versi lama pada `effective_from − 1 hari`; diff antarversi terlihat.
* Setiap jurnal otomatis dapat ditelusuri ke versi profilnya; laporan "jurnal yang memakai profil X v3".
* Perubahan profil tidak pernah mengubah jurnal terposting; koreksi memakai jurnal pembalik (butuh fitur void GL-10).

### 2.6 Migrasi dari hardcode tanpa mengubah saldo historis
1. **Fase 0 (bayangan)** — bangun resolver + seed profil versi 0 = tabel §5 (persis perilaku hari ini). `post_journal` tetap memakai kode lama; resolver dijalankan paralel dan mencatat selisih (log `shadow_mismatch`). Tidak ada perubahan saldo.
2. **Fase 1** — alihkan satu aliran per rilis (mulai yang sederhana & terisolasi: biaya bank/jasa giro, transfer, aset tetap, pinjaman), dengan feature-flag per peristiwa; stempel jurnal lama `profile_id=legacy-v0` lewat skrip idempoten (hanya menambah metadata, tidak menyentuh baris debit/kredit).
3. **Fase 2** — aliran inti (penerimaan, titipan, AP, komisi, pajak).
4. **Fase 3** — profil koreksi (versi 2) untuk GL-01/02/04/14 sebagai profil terpisah yang efektif mulai tanggal tertentu (tidak ada penulisan ulang historis).
5. **Fase 4** — matikan konstanta kode (`GL_BANK`, `DEDUCTION_GL`, `CASHBON_ACCOUNT`, dst.), hapus jalur `/bank/accounts` pembuat rekening, ubah dropdown rekening.
* Dampak seed/test: `seed*.py` memanggil `post_journal` dengan kode literal → ganti ke pemanggilan melalui resolver (atau tetap, karena profil v0 identik); `backend_test*.py`/`verify_*.py` yang menegaskan kode akun tetap lulus karena v0 = hardcode; tambahkan uji "profil v0 ≡ jurnal lama" per peristiwa; seed harus menyemai profil v0 + peran akun SEBELUM seed transaksi.

### 2.7 Sketsa UI
**Menu**: Akuntansi → "Pemetaan Jurnal" (izin `gl:config_*`). Tab:
1. **Peristiwa** — tabel: kode, nama, modul, profil aktif (versi, efektif sejak), jumlah jurnal 30 hari, status (✔ lengkap / ⚠ tanpa profil / ⛔ konflik). Filter per modul.
2. **Editor profil** — kolom baris: `No`, `Sisi (D/K)`, `Akun (peran/kode)`, `Nilai (variabel)`, `Memo`, `Dimensi`. Panel kondisi (`po_type = material`) dan efektivitas. Tombol: *Simpan draft*, *Uji coba*, *Ajukan persetujuan*.
3. **Uji coba (dry-run)** — pilih peristiwa, isi contoh (`amount`, `method`, `po_type`, `is_recognized`, proyek, tanggal) → tampilkan **jurnal hasil** (akun, nama, D/K, nilai), cek seimbang, cek akun valid/aktif/tipe, perbandingan "jurnal hari ini (kode lama) vs profil baru" (Δ per akun), dan bayangan neraca (saldo akun terdampak). Tidak menulis apa pun.
4. **Koneksi Rekening** — matriks: (peristiwa/kategori × metode bayar × proyek) → rekening/kas default, jenis yang diizinkan, kebijakan saldo negatif; menandai peristiwa yang HARUS memilih rekening.
5. **Peran Akun** — peran → akun, riwayat versi, "dipakai oleh N profil".
6. **Riwayat & Audit** — versi, diff, siapa/kapan/alasan, jurnal yang memakai versi.
7. **Kesehatan** — event `menunggu_profil`/`failed` (dengan tombol proses ulang), tie-out per akun (menggantikan `reconcile` lima akun), cakupan: akun CoA yang tak dirujuk profil mana pun.

### 2.8 Urutan implementasi & risiko
| Urut | Isi | Risiko utama | Mitigasi |
|---|---|---|---|
| 0 | Perbaiki cacat blokir dulu yang tak memerlukan profil: GL-06 (validasi tanggal), GL-08 (jalur `/bank`), GL-09 (validasi retensi), GL-22 (idempotensi) | Mengubah perilaku API | uji regresi |
| 1 | Katalog peristiwa + peran akun + profil v0 + dry-run (read-only) | Salah salin perilaku | uji ekuivalensi per peristiwa terhadap jurnal lama (skrip uji audit (tidak disertakan di repo) dapat dijadikan kasus) |
| 2 | Resolver bayangan di `post_journal` + stempel jejak | Performa (≥1 query) | cache dengan invalidasi versi |
| 3 | Dimensi jurnal (proyek/unit/deal/rekening-id) | Migrasi besar | tambah field opsional, backfill dari resolver lama |
| 4 | Alihkan peristiwa bertahap + feature flag | Selisih saldo | mode bayangan dulu |
| 5 | Maker-checker + UI Editor/Uji coba | Beban pelatihan | profil v0 nyaman dipakai tanpa perubahan |
| 6 | Profil koreksi (PPN, pasca-BAST, denda, arus kas) | Efek ke laporan berjalan | `effective_from`, komunikasi ke auditor |
| 7 | Matikan hardcode, hapus `/bank/accounts` pembuat | Seed/test lama | v0 = hardcode |

Risiko lintas: (a) profil salah mengubah laporan keuangan — maker-checker + dry-run + efektif ke depan; (b) kinerja resolver per jurnal; (c) kompleksitas kondisi — batasi ekspresi ke variabel katalog (tanpa kode bebas); (d) race pembuatan profil aktif ganda — kunci unik (event, scope, periode); (e) event yang sudah antre saat profil berubah — resolusi memakai tanggal transaksi + versi saat event dibuat.

## 3. Tabel PEMETAAN AWAL USULAN (profil versi 0 = perilaku hari ini, persis)

Konvensi: `K*` = `cash:by_context` (rekening terpilih, atau default jenis). "Cacat" menunjuk temuan di gl-4; baris cacat TETAP disalin apa adanya sebagai v0 agar saldo & laporan lama tak berubah, lalu diberi profil koreksi pada fase 3.

| Event code | Kondisi (v0) | Debit | Kredit | Rute rekening | Dimensi dicatat | Cacat → profil koreksi (v2) |
|---|---|---|---|---|---|---|
| `sales.receipt` | semua | K* (`method` ∈ {cash,tunai} → jenis kas; selain → bank) | `2-1400` | wajib pilih bila >1 rekening jenis itu | deal, unit, proyek | GL-01: bila `is_recognized` → Cr `1-1300`; GL-02: alokasi denda → Cr `1-1300` |
| `sales.deposit_in` | titipan bebas / kelebihan bayar / booking fee | K* (default bank — **bug**: tunai ke bank) | `2-1450` | v2: ikuti `method` | deal | GL-17 |
| `sales.deposit_apply` | – | `2-1450` | `2-1400` | – | deal | GL-01 (pasca-BAST → `1-1300`) |
| `sales.deposit_refund` | – | `2-1450` | K* (default bank) | pilih rekening | deal | GL-17 |
| `sales.booking_forfeit` | – | `2-1450` | `4-1200` | – | deal | – |
| `sales.revrec` | – | `2-1400` (= `cleared`) + `1-1300` (= `revenue−cleared`, bila > 0); `5-1100` (= `cogs`) | `4-1100` (= `revenue` — v2: tanpa item denda); `2-1450` (= `cleared−revenue` bila >0); `1-1600` (= min(cogs, saldo WIP)); `2-1700` (= sisa) | – | deal, unit, proyek | GL-02, GL-11 (WIP per proyek/unit), GL-07 (gerbang) |
| `sales.late_fee` | – | `1-1300` | `4-1400` | – | deal | GL-02 |
| `sales.late_fee_waive` | – | `4-1400` | `1-1300` | – | deal | – |
| `sales.receipt_void` | – | `2-1400` | K* kuitansi asal | akun kuitansi | deal | GL-01 |
| `cancel.decision` | – | `2-1400` (=diterima) ; `2-1450` (=saldo titipan) | `4-1200` (=potongan) ; `2-1460` (=refund) | – | deal | GL-23 (komisi/fee/pajak) |
| `cancel.refund_pay` | – | `2-1460` | K* (tunai→kas) | boleh pilih | deal | – |
| `allin.booking_to_cost_trust` | – | `2-1450` | role `CUSTOMER_COST_TRUST` (= `comp.gl_liability`, default `2-1470`) | – | deal | – |
| `allin.cost_receipt` | – | K* (default bank) | `2-1470` (v2: `comp.gl_liability`) | pilih rekening | deal | GL-19 |
| `allin.cost_disburse` | – | `2-1470` | K* (default bank) | pilih rekening | deal | GL-19 |
| `allin.dev_expense` | `treatment=developer_borne` | `comp.gl_expense` (6-1700) | `comp.gl_ap` (2-1100) + AP bill | – | deal | validasi akun (GL-19) |
| `pdc.receive` | – | `1-1350` | `2-1480` | – | deal | GL-26 (opsional: memorandum di luar neraca) |
| `pdc.reverse` (kliring/tolak/batal) | – | `2-1480` | `1-1350` | – | – | – |
| `pdc.clear_no_deal` | tanpa deal | bank terpilih | `2-1450` | wajib bank | – | – |
| `ap.approve` | `po_type=material` | `1-1400` | `2-1100` (net) + `2-1200` (retensi) + potongan | – | proyek, PO, bill | GL-12 |
| | `po_type=general` | `6-1300` | idem | | | |
| | `po_type=subcon` / tanpa PO / lain | `1-1600` (didahului `2-1700` s.d. saldo akrual) | idem | | | GL-11 |
| `ap.deduction` (kredit tambahan pada `ap.approve`) | `kind=advance` / `material` / `penalty` / `other` | – | `1-1800` / `1-1400` / `4-1200` / `4-1200` | – | – | – |
| `ap.pay` | – | `2-1100` (= `amount`) | K* (`amount−withheld`) + `2-1300` (`withheld`) | pilih rekening | proyek, bill | GL-18 (cek saldo) |
| `subcon.advance_pay` | – | `1-1800` | K* (default bank) | v2: pilih | proyek, SPK | – |
| `subcon.retention_release` | – | `2-1200` | `2-1100` (+AP bill) | – | proyek, SPK | – |
| `commission.approve` | – | `6-1100` | `2-1600` | – | deal, proyek | PSAK 72 (kapitalisasi) — pertanyaan terbuka |
| `commission.pay` | – | `2-1600` | K* | pilih rekening | deal | UI pembayaran (GL-17) |
| `mktfee.approve` | – | `6-1200` (= bruto) | `2-1500` (= neto) + `2-1300` (= PPh) | – | proyek, deal | – |
| `mktfee.pay` | – | `2-1500` | K* (source kas/bank) | v2: pilih | proyek | – |
| `tax.accrue` | semua jenis | `6-1400` | `2-1300` | – | deal | GL-04: PPN keluaran → `VAT_OUTPUT`; BPHTB → titipan bila pass-through; PPh final → beban |
| `tax.deposit` | – | `2-1300` | K* | pilih rekening | deal | – |
| `staff.advance_disburse` (Kas Bon & Pengajuan advance) | – | `1-1500` | K* | pilih | proyek | GL-16 (satu modul) |
| `staff.advance_settle` | kategori | akun kategori: transport/konsumsi/ATK/perizinan/perbaikan/lainnya `6-1300`; pemasaran `6-1200`; `biaya_proyek`/`upah_harian` `1-1600` | `1-1500` (+K* untuk sisa/penggantian) | – | proyek | GL-11 |
| `fund.expense_disburse` | kategori (sama) | akun kategori (default `6-1300`) | K* | pilih | proyek | – |
| `petty.expense` / `petty.void` | kategori | akun kategori / K* kas kecil | K* kas kecil / akun kategori | rekening kas kecil | proyek (di dokumen) | simpan proyek di jurnal |
| `fixed_asset.acquire` | `funding` kas/bank/utang | `1-2100` | K* (kas/bank) atau `2-1100` + AP bill | v2: pilih | proyek | GL-24 (tanah → persediaan lahan) |
| `fixed_asset.depreciate` | – | `6-1500` | `1-2200` | – | proyek | GL-24 (alat proyek → WIP) |
| `fixed_asset.dispose` | – | K* + `1-2200` + `6-1800` (rugi) | `1-2100` + `4-1300` (laba) | pilih | proyek | – |
| `loan.disburse` | – | K* (neto) + `6-1600` (provisi) | `2-2100` | v2: pilih | proyek | GL-24 (amortisasi/kapitalisasi) |
| `loan.installment` | – | `2-2100` (pokok) + `6-1600` (bunga) | K* | pilih | proyek | GL-24 (akrual) |
| `labor.pay` | – | `1-1600` | K* (default bank) | v2: pilih | proyek | – |
| `cash.transfer` | – | rekening tujuan (+ `6-1600` biaya) | rekening asal | – | – | – |
| `cash.opening` | – | sub-akun rekening | `3-1950` | – | – | – |
| `bank.fee` / `bank.interest` | – | `6-1600` / rekening | rekening / `4-1200` | rekening mutasi | – | – |
| `year.close` / `year.reopen` | – | pendapatan→D; beban→K; selisih `3-1900` | cermin | – | – | GL-03 (kunci bersiklus) |
| `manual` | – | bebas | bebas | – | – | maker-checker (GL-21) |

Catatan: "K*" di sini WAJIB menyelesaikan rekening dengan urutan: rekening yang dipilih user → aturan rute (proyek × metode) → default jenis; jika tak ada satupun → tolak (fail-closed).

## 4. Dampak ke komponen yang ada
* `gl_engine.post_journal`: tetap pintu tunggal; ditambah `profile_ref` & dimensi; `_gl_*` handler menjadi pemanggil resolver.
* `cash_bank.resolve_code`: menjadi bagian resolver rute rekening (hilangkan `strict=False` diam-diam).
* `settings_store`: bisa menampung kebijakan umum (saldo negatif, tanggal wajib), tetapi profil memerlukan koleksi sendiri (versi, maker-checker).
* `reference_p47/p48/p27` (`GL_*`, `DEDUCTION_GL`, `CASHBON_ACCOUNT`): pindah menjadi data profil v0.
* UI Config Cost Component/Add-on: dropdown "Akun GL" diganti menjadi "Peran akun/Profil" supaya tidak ada konfigurasi dekoratif (GL-19).
* Laporan: arus kas membaca "aktivitas" per peran akun (GL-14); L/R per proyek membaca dimensi (GL-25).
* Tie-out (`finance_audit.reconcile`, `closing_engine._check_tieout`): dibangkitkan otomatis dari profil (setiap akun yang dirujuk profil + sumber subledger terdaftar).
