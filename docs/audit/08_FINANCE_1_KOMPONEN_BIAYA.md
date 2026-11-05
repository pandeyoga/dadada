# Audit Ronde 2 — KOMPONEN BIAYA (all-in / biaya pembeli) — SIPRO/Estora

Auditor: stream "finance AR/AP + komponen biaya" (instance #8: UI :3042, API :8042, DB `sipro_fin`). Kode yang diuji = kode terbaru pasca-perbaikan gelombang 1.
Semua angka Rupiah. Data uji berawalan `AUDIT-`. Skrip uji: (berkas uji tidak disertakan di repo) (lib.py, flow1.py, mkdeal.py, snap.py, archeck.py, ui_*.js). Screenshot: `img/finance/`.

## Ringkasan eksekutif
1. Jawaban untuk pemilik: sistem biaya all-in **berfungsi untuk alur normal** (skema → snapshot → invoice biaya INB → kuitansi KWB → titipan 2-1470 → penyaluran; angka GL 2-1470 cocok 100% dengan subledger), tetapi **belum aman dan belum terhubung penuh**: master tanpa validasi, tiga catatan BPHTB yang saling tidak tahu, pembatalan kontrak mengabaikan titipan biaya, beban developer bisa dicatat tanpa batas oleh satu orang, dan satu layar "Komponen Biaya" di Pusat Konfigurasi ternyata **tidak mempengaruhi apa pun**.
2. Ada **dua master berbeda** bernama "komponen biaya": tab *Pusat Konfigurasi › Komponen Biaya* (katalog `price_components`, 12 baris, dengan kolom "Perlakuan keuangan"/akun GL dan banner "menentukan jurnal") **tidak dibaca oleh logika mana pun** (FN-01); master yang sungguhan ada di tab *Biaya All-in* (`cost_components`).
3. Master sungguhan menerima nominal negatif, persen 500%, kode akun sembarang, cara hitung "xyz"; komponen baru **otomatis masuk semua skema**; komponen **nonaktif tetap ditagih** pada reservasi baru (FN-02). Kode akun salah menghasilkan **tagihan AP `approved` tanpa jurnal** yang bertambah di tiap percobaan ulang (FN-05).
4. Pembatalan kontrak tidak menyentuh titipan biaya (Rp 4 jt tertinggal di 2-1470, invoice biaya sisa Rp 26 jt tetap "partial", masih bisa dibayar/disalurkan sesudah batal) dan tidak ada fitur void kuitansi/penyaluran biaya (FN-03, FN-09).
5. BPHTB hidup di **tiga tempat** (komponen all-in, `tax_records`, field legacy `costs.bphtb`); bila Finance menandai catatan pajak BPHTB "disetor" → beban 6-1400 + kas keluar, **tambahan** atas titipan/penyaluran atau beban developer; ganti skema AR menghapus catatan pajak yang sudah `paid` sehingga bisa disetor lagi (FN-07).
6. Klaim ronde 1 yang dicek ulang: KT-03, KT-04, KT-05, KT-22 **belum tertutup** (FN-10/11); anti-ganda paralel, penolakan biaya negatif/lebih-bayar **berfungsi**.

## Cakupan
Master (`allin_engine.py`, `routers/allin_router.py`, `allin_amend.py`, `catalog.py`, `models`), UI Pusat Konfigurasi (tab Komponen Biaya & Biaya All-in), UI Customer & Kontrak › Kontrak & Legal › "Biaya transaksi & titipan", API+UI end-to-end pada 11 deal uji (skema EXCLUDE, ALLIN_STD, legacy tanpa skema, BOOKING, KPR 80%): reservasi → bayar booking fee → book → konversi → invoice biaya → bayar parsial/lebih/nol/negatif/paralel → salurkan titipan → beban developer → amandemen → pembatalan kontrak; jurnal diverifikasi per aksi (`journal_entries` sejak timestamp aksi); rekonsiliasi Σ komponen = invoice = Σ kuitansi = GL 2-1470; PDF invoice & kuitansi biaya; rumus BPHTB/BANK_FEE/INSURANCE pada harga 0, 1, 79.999.999, 80.000.000, 80.000.001, 850.000.001, 10^15, −5; RBAC master 6 peran; Pusat Konfigurasi terkait pajak.

## Komponen yang ada di master (diperiksa satu per satu)
| Kode | Cara hitung | Perlakuan default | Hasil pada harga Rp 850 jt | Catatan |
|---|---|---|---|---|
| BPHTB | `rumus_bphtb` 5% × (harga − NPOPTKP 80 jt) | pass-through | 38.500.000 (benar menurut rumus); harga ≤ 80 jt → 0 | NPOPTKP global (per-proyek tak bisa diisi, FN-12); NJOP tidak dimodelkan |
| NOTARY_FEE | nominal 7,5 jt | pass-through | 7.500.000 | tetap, tak tergantung harga/tipe |
| BANK_FEE (KPR saja) | 1% × **harga** | pass-through | 8.500.000 | provisi bank lazimnya % dari **plafon**, bukan harga (FN-12) |
| INSURANCE (KPR saja) | nominal 3 jt | pass-through | 3.000.000 | tak tergantung plafon/tenor |
| LEGACY | nominal 0 | pass-through | — | hanya untuk migrasi |
| BOOKING | = booking fee deal | pass-through | 5 jt/10 jt | berfungsi: BF → titipan 2-1450 → 2-1470 (diuji, jurnal benar) |
Tidak ada di master: PPN, PPh penjual (hanya field legacy/`tax_records`), PBB, BBN/balik nama, pendaftaran BPN (roya/APHT/SKMHT), IPL/sambung listrik-air. Semua komponen master default aktif; akun GL default 6-1700 / 2-1470 / 2-1100 (semua ada di CoA).

---
## Temuan (urut severity)

### [FN-01] [Severity: Tinggi] "Pusat Konfigurasi › Komponen Biaya" tidak berpengaruh apa pun, padahal layarnya berjanji menentukan jurnal
- Label bukti: [TERBUKTI-API] + [DARI-KODE] (+ UI `img/finance/c01-komponen-biaya-tab.png`)
- Lokasi: UI Pusat Konfigurasi › tab "Komponen Biaya" (`PriceComponentPanel`, API `/catalog/price-components`, `catalog.py:30-67`); pembaca koleksi `price_components` di seluruh backend: hanya `catalog.py`, `catalog_router.py`, `indexes.py`, `masterplan.py:213`, `data_mgmt_purge.py` — **tidak ada** di `contracts_engine.py`, `finance_engine.py`, `gl_engine.py`, `allin_engine.py`.
- Reproduksi: `PUT /catalog/price-components/{BPHTB}` `{"finance_treatment":"revenue","gl_account":"4-1100","applies_schemes":["kpr"],"active":false}` → 200. `GET /contracts/{cid}` (kontrak legacy A-05) sebelum & sesudah: BPHTB tetap `pass_through`, Rp 42.500.000, total_bill 928.750.000 — identik. Banner layar: "Perlakuan keuangan menentukan jurnal … Ubah di sini bila kebijakan akuntansi berbeda — tidak perlu ubah kode."
- Seharusnya: konfigurasi yang bisa diubah harus berefek, atau layar disembunyikan/ditandai "referensi".
- Dampak: admin/pemilik menyangka kebijakan akuntansi BPHTB/notaris/PPh bisa diubah dari layar ini (justru layar yang bernama "Komponen Biaya"); yang sungguhan ada di tab "Biaya All-in". Kebijakan salah dipercaya "sudah dikonfigurasi".
- Akar masalah: dua master hasil dua fase (39 dan 76) tak disatukan; breakdown kontrak (`contracts_engine.build_breakdown`) menulis `treatment` hardcode. Saran: pensiunkan `price_components` atau jadikan satu-satunya sumber (SSOT) dan baca di `build_breakdown`.

### [FN-02] [Severity: Tinggi] Master `cost_components` & skema all-in tanpa validasi; nonaktif tetap ditagih; komponen baru otomatis masuk semua skema
- Label bukti: [TERBUKTI-API] (+ UI tab "Biaya All-in" menampilkan baris sampah, `c02-biaya-allin-tab.png`)
- Lokasi: `routers/allin_router.py:124-151` (create), `154-168` (update tanpa validasi `calc_method/default_treatment/pct/amount`), `191-221` (skema tak memvalidasi `component_code`/`override_amount`), `allin_engine.py:147` (`resolve_scheme` memakai `include_inactive=True`).
- Reproduksi (`superadmin`): `POST /cost-components` `amount:-5000000` → 200; `calc_method:persen_harga, pct:500` → 200; `pct:-10, gl_expense:"9-9999", gl_liability:"XYZ", gl_ap:"1-1300"` → 200. Seluruhnya otomatis `$push` ke ALLIN_STD dan EXCLUDE. `GET /allin-schemes/{EXCLUDE}/preview?price=850000000` → `AUDIT_NEG −5.000.000`, `AUDIT_PCT 4.250.000.000`, `AUDIT_NEGPCT −85.000.000`. Setelah `is_active=false` pada ketiganya, preview **tetap** menampilkan nilai yang sama. `PUT /cost-components/{id}` `{"calc_method":"xyz","default_treatment":"foo","pct":-3,"amount":-1}` → 200 (tersimpan; layar menampilkan "undefined · -3%"). Skema: `POST /allin-schemes` dengan item `TIDAK_ADA` (diam-diam dilewati), `override_amount:-7500000` (notaris −7,5 jt) dan `override_amount:900000000000` (BPHTB 900 M) → 200. Preview harga −5 / 0 diterima.
- RBAC (peran yang berhasil membuat komponen penagihan): finance, sales_manager, owner, **pm**, superadmin (sales 403) — `catalog:update` dipakai bersama master unit/tipe.
- Seharusnya: nominal ≥ 0, persen 0–100, akun harus ada di CoA & bertipe sesuai, enum divalidasi di PUT, komponen nonaktif tidak ikut skema baru, komponen baru tidak otomatis menempel ke skema yang sedang dijual.
- Dampak: satu salah ketik di master mengubah tagihan semua reservasi baru (Rp 4,25 M per unit pada uji). Kontrak lama aman karena snapshot. UI Pusat Konfigurasi tertulis "Komponen nonaktif tidak mengubah kontrak yang sudah terbit" — benar untuk kontrak lama, **salah** untuk reservasi baru.
- Saran: validasi di model Pydantic + tolak `update` yang mengubah komponen yang dipakai kontrak aktif tanpa persetujuan; `resolve_scheme` hanya komponen aktif; sinkronisasi ke skema jadi opsi eksplisit.

### [FN-03] [Severity: Tinggi] Pembatalan kontrak tidak menyentuh titipan biaya (2-1470) maupun invoice biaya; biaya tetap bisa dibayar & disalurkan setelah batal
- Label bukti: [TERBUKTI-API]
- Lokasi: `cancellation_engine.py:111-146` (`compute` hanya `contract_liabilities` + `customer_deposits`), jurnal batal hanya 2-1400/4-1200/2-1460; `allin_engine.pay_cost_invoice:410` & `disburse_titipan:457` tanpa cek status kontrak/deal (beda dengan AR yang kini dijaga `_deal_closed_reason`).
- Reproduksi (deal A-03): invoice biaya Rp 46 jt; bayar Rp 20 jt; salurkan Rp 16 jt (sisa titipan Rp 4 jt). Ajukan batal (manager) → setujui (finlead): BAP menghitung `payable_total` Rp 3.250.000 (hanya dari Rp 5 jt booking fee). Jurnal batal `JV/2026/00058`: Dr 2-1400 5.000.000 / Cr 4-1200 1.750.000 / Cr 2-1460 3.250.000. Sesudahnya: `costs-ledger` titipan_balance **Rp 4.000.000**, GL 2-1470 kredit 4.000.000, invoice `INB/2026/0001` **status partial, sisa Rp 26.000.000**. `POST /cost-invoices/{id}/pay` 1 jt → **200**; `POST /contracts/{cid}/cost-disbursements` 1 jt → **200** (kontrak berstatus cancelled). `/finance/reconcile` tetap hijau (tidak ada kontrol 2-1470).
- Seharusnya: BAP memuat titipan biaya yang belum disalurkan (dikembalikan penuh, bukan potongan), invoice biaya tak terbayar di-void, penerimaan/penyaluran baru ditolak.
- Dampak: uang pembeli tertahan tanpa tuan di 2-1470 dan tidak tampil di refund; piutang hantu di invoice biaya.

### [FN-04] [Severity: Tinggi] "Catat beban (AP)" developer-borne: nominal bebas, disetujui otomatis oleh pembuatnya → pemisahan tugas AP terlewati
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (`k02-catat-beban-90jt.png`, `k03-catat-beban-hasil.png`)
- Lokasi: `allin_engine.py:499-530` (`amount = int(amount or comp.amount)` tanpa batas atas; tagihan langsung `status=approved, approved_by=actor` + jurnal), `routers/allin_router.py:277-284` (izin hanya `finance:create`), `routers/ap_router.py:91-106` (`_assert_payer_separate` dilewati bila `approved_by == created_by`).
- Reproduksi: kontrak ALLIN_STD (BPHTB developer-borne Rp 38.500.000). `finance` `POST /contracts/{cid}/cost-expenses` `{"component_code":"BPHTB","amount":99000000,"vendor":"AUDIT KPP Pratama"}` → 200, jurnal `JV/2026/00054` Dr 6-1700 99.000.000 / Cr 2-1100 99.000.000, `ap_invoices.status=approved, approved_by=created_by=finance`. Lalu **akun yang sama** `POST /finance/ap/bills/{id}/pay` Rp 10 jt → 200 (kas keluar, `JV/2026/00055`). UI: panel "Ditanggung developer" komponen Rp 32.000.000 → "DIBEBANKAN RP 90.000.000" diterima.
- Seharusnya: nominal ≤ nilai komponen (atau butuh persetujuan), tagihan masuk antrian approval AP biasa (maker ≠ checker ≠ payer).
- Dampak: satu staf Finance dapat membuat beban + utang Rp tak terbatas dan membayarnya sendiri — melewati SoD PK-07 yang diperbaiki di ronde 1.

### [FN-05] [Severity: Tinggi] Komponen dengan akun GL tak valid → tagihan AP `approved` tanpa jurnal; tiap percobaan ulang menambah tagihan yatim
- Label bukti: [TERBUKTI-API]
- Lokasi: `allin_engine.py:514-528` (AP bill dibuat & di-set `approved` **sebelum** `post_journal`; tidak ada rollback), `routers/allin_router.py:132` (akun tidak divalidasi).
- Reproduksi: komponen `AUDIT_GL` (developer-borne, `gl_expense:"9-9999"`) → deal baru → `POST /contracts/{cid}/cost-expenses` → **400** "Akun 9-9999 tidak ada dalam CoA." tetapi `ap_invoices` +1 (status approved, net 1 jt, tanpa jurnal). Ulangi → 400 lagi, tagihan yatim kedua (guard `cost_expenses.find_one` hanya terisi saat sukses). `/finance/reconcile`: `2-1100 gl=579.899.999 vs subledger=581.899.999 diff −2.000.000, ok:false`; Dashboard Finance menampilkan banner "1 akun kendali SELISIH dengan subledger".
- Dampak: utang usaha di subledger lebih besar dari GL; tagihan yatim bisa dibayar (Dr 2-1100 tanpa Cr sebelumnya).
- Catatan: lampu merah `/finance/reconcile` **berhasil mendeteksi** — kontrol itu berfungsi.
- Saran: validasi akun saat simpan master; buat tagihan + jurnal secara atomik atau hapus tagihan bila jurnal gagal.

### [FN-06] [Severity: Tinggi] Penyaluran titipan: komponen fiktif & nominal melebihi komponen diterima; tanpa bukti, persetujuan, atau pembatalan
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (`k04-salurkan-14jt-hasil.png`)
- Lokasi: `allin_engine.py:457-496` (hanya membandingkan dengan **total** titipan, `component_code` tidak diperiksa), `routers/allin_router.py:265-274`; kuitansi tidak menyimpan `component_code` sehingga saldo per komponen tidak ada.
- Reproduksi: titipan Rp 20 jt (BPHTB 38,5 jt + notaris 7,5 jt, baru dibayar parsial). `POST …/cost-disbursements` `component_code:"FOO_BAR", amount:1.000.000` → 200 (`JV/2026/00051`); `NOTARY_FEE 15.000.000` (komponen hanya 7,5 jt) → 200 (`JV/2026/00052`). UI: "Salurkan" komponen notaris Rp 7,5 jt → ketik 14.000.000 → "Disalurkan Rp 14.000.000 ke AUDIT-UI Notaris Z (NOTARY_FEE)". Tidak ada lampiran bukti penyaluran; tidak ada endpoint pembatalan.
- Dampak: dana BPHTB bisa dipakai membayar notaris (atau penerima lain) melebihi hak masing-masing; uang keluar ke penerima teks bebas tanpa bukti. Beda dengan jalur uang keluar lain yang sudah wajib bukti (PK-13).

### [FN-07] [Severity: Tinggi] BPHTB tercatat di tiga tempat yang tidak saling tahu; catatan pajak BPHTB bisa disetor ganda
- Label bukti: [TERBUKTI-API]
- Lokasi: (a) komponen all-in `allin_engine.compute_amount` (pct komponen + NPOPTKP proyek/global); (b) `finance_engine.create_ar_for_deal:391-399` menulis `tax_records` {ppn, bphtb, pph} (tarif dari `finance_configs`, bukan dari komponen); (c) `contracts.costs.bphtb` (legacy). `gl_engine.post_tax_accrual/post_tax_payment` (Dr 6-1400 / Cr 2-1300; Dr 2-1300 / Cr Bank); `finance_engine.py:391` `db.tax_records.delete_many` **tanpa syarat status**.
- Reproduksi (deal B, KPR ALLIN_STD, BPHTB developer-borne 38,5 jt): `PUT /tax/records/{bphtb}` `{"status":"paid","ntpn":…}` → `JV/00061` Dr 6-1400 38,5 jt / Cr 2-1300; `JV/00062` Dr 2-1300 / Cr 1-1201 38,5 jt (beban 6-1400 + kas keluar), **di luar** beban developer 6-1700 (Rp 99 jt, FN-04) dan titipan 2-1470. Lalu `POST /finance/ar/{deal}/schedule` (ganti/regenerasi skema) → `tax_records` BPHTB kembali `pending` (NTPN hilang) → `PUT …paid` lagi → `JV/00063-64` (kas keluar kedua Rp 38,5 jt).
- Seharusnya: BPHTB pembeli (skema exclude) tidak pernah menjadi beban developer di modul pajak; BPHTB developer-borne dicatat sekali; `tax_records` yang sudah `reported/paid` tidak dihapus oleh regenerasi AR.
- Dampak: beban/kas keluar ganda; catatan pajak tidak bisa dipercaya; di skema exclude BPHTB pembeli muncul sebagai kewajiban pajak developer.
- Pertanyaan ke pemilik (BPHTB titipan/ditanggung/campuran — sudah ada di ringkasan ronde 1) tetap menentukan perbaikannya.

### [FN-08] [Severity: Sedang] Akun & rekening pada jalur biaya tidak mengikuti konfigurasi: `gl_liability` dekoratif; metode "cash" tetap ke bank
- Label bukti: [TERBUKTI-API]
- Lokasi: `allin_engine.py:444-445` & `491-493` (konstanta `GL_BANK="1-1200"`, `GL_TITIPAN_BIAYA`), `:294` (hanya `apply_booking_deposit` membaca `comp.gl_liability`); `PayIn` tanpa `cash_account_id`.
- Reproduksi: komponen `AUDIT_LIAB` `gl_liability:"2-1300"` (valid); kontrak snapshot memuat `2-1300`; bayar invoice Rp 64,5 jt → `JV/2026/00112` Dr 1-1201 / Cr **2-1470** 64,5 jt (bukan 2-1300). `method:"cash"` Rp 5 jt → `JV/2026/00067` Dr **1-1201 (bank)**, bukan kas 1-1100. Rekening tujuan uang tidak bisa dipilih.
- Catatan: `gl_expense` & `gl_ap` **dipakai** pada beban developer (FN-04/05) — jadi klaim ronde 1 GL-19 "dekoratif" benar untuk `gl_liability` dan price-component (FN-01), tidak untuk dua akun lain.
- Dampak: konfigurasi akun menipu; kas tunai tercatat di bank (rekonsiliasi bank akan selisih).

### [FN-09] [Severity: Sedang] Amandemen skema: jalan buntu, efek samping tak ditangani
- Label bukti: [TERBUKTI-API]
- Lokasi: `allin_amend.py:41-43, 80-117`.
- Reproduksi: (1) kontrak dengan 1 kuitansi biaya → `POST …/allin-amendments` → 400 "batalkan kuitansi dulu lewat finance" — **tidak ada endpoint** membatalkan kuitansi/invoice biaya (`/cost-receipts/{id}/void`, `/cost-invoices/{id}/void` → 404); skema terkunci permanen. (2) kontrak ALLIN_STD dengan beban developer BPHTB sudah dicatat (AP Rp 99 jt) diamandemen ke EXCLUDE: disetujui, invoice lama di-void, **BPHTB kini ditagih ke pembeli Rp 38,5 jt** sementara beban developer & AP tetap ada. (3) invoice biaya baru **tidak** terbit otomatis (`uninvoiced` 57,5 jt; AR menampilkan 0 piutang biaya sampai Finance menekan tombol). (4) `deals.costs` (snapshot reservasi) tidak diperbarui — dua sumber kebenaran (`deal.costs` vs `contract.costs`); `deal_as_contract` & `ar_breakdown` masih membaca versi lama.
- Dampak: perubahan skema yang sah tidak bisa dilakukan setelah ada pembayaran; bila bisa, pembukuan beban developer & tagihan pembeli tidak disesuaikan.
- Terverifikasi OK: pengaju ≠ pemutus ditegakkan (finance 403, finlead 200); paralel 3 pemutus → satu efek.

### [FN-10] [Severity: Tinggi — klaim ronde 1 belum tertutup] KT-03 / KT-04 / KT-22: model biaya ganda, PPh penjual masuk total tagihan, potongan melebihi harga
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (`k05-legacy-rincian.png`: "Total ditagihkan Rp 928.750.000")
- Reproduksi (kontrak A-05 tanpa skema all-in): `POST /contracts/{id}/costs {"bphtb":42500000,"notary_fee":15000000,"pph_seller":21250000}` → 200; `POST /contracts/{id}/cost-invoices` → 400 "Tidak ada komponen biaya yang ditagih…" (KT-03). Breakdown: `costs_total 78.750.000`, `total_bill 928.750.000` = 850 jt + 42,5 + 15 + **21,25 PPh penjual** (KT-04); `spr-compare` `all_match:false, mismatch_count:5`. KT-22: `promo_discount:900000000` → `nett_price −180.000.000`, `total_bill −162.500.000`; `dp_percent:150`, `plafon_kredit:99999999999` tersimpan. Pada kontrak yang **sudah punya komponen**, `bphtb:123` tersimpan di `costs` tetapi diabaikan breakdown (komponen 32 jt tetap) — dua nilai BPHTB pada satu kontrak.
- Dampak: SPR kontrak "tanpa all-in" tak bisa ditandatangani; pembeli diminta menanggung pajak penjual; total tagihan bisa negatif.

### [FN-11] [Severity: Tinggi — KT-05 belum tertutup + dampak baru] Ganti skema kontrak ke KPR tidak menambah komponen KPR-only dan tidak menyelaraskan AR
- Label bukti: [TERBUKTI-API]
- Lokasi: `contracts_engine.set_scheme:663-690`; `allin_engine.resolve_scheme:154` (komponen `kpr_only` hanya disertakan bila skema saat reservasi = KPR).
- Reproduksi: deal EXCLUDE + Cash bertahap, konversi cash_bertahap; `POST /contracts/{id}/scheme {"scheme":"kpr"}` → 200. Kontrak: `scheme=kpr`, komponen tetap `[BPHTB, NOTARY_FEE]` (BANK_FEE 1% = 6,85 jt dan INSURANCE 3 jt **tidak pernah ditagih**), AR tetap 7 cicilan pembeli (tanpa porsi bank).
- Dampak: biaya bank/asuransi KPR hilang dari tagihan; AR & jenis kontrak tidak sinkron (KT-05).
- Terverifikasi OK: `POST /deals/{id}/convert` menolak mengganti skema bila skema dipilih sales saat reservasi (pesan jelas).

### [FN-12] [Severity: Sedang] Dasar hitung & konfigurasi pajak: NPOPTKP per proyek tidak bisa diisi; BANK_FEE dari harga; nilai gila diterima
- Label bukti: [TERBUKTI-API] + [DARI-KODE]; regulasi = pengetahuan auditor, mohon konfirmasi konsultan pajak.
- (a) UI menyebut "BPHTB memakai NPOPTKP per proyek (kolom `npoptkp` proyek)", tetapi `PUT /projects/{id} {"npoptkp":60000000}` → 200 dan nilai **tidak tersimpan**; tidak ada kolom/formulir; `allin_engine.npoptkp_for` selalu jatuh ke NPOPTKP global Rp 80 jt (default Jakarta; mayoritas daerah Rp 60 jt, ditentukan Perda — proyek di Bogor pada data uji).
- (b) Dua sumber tarif BPHTB: komponen `pct` vs `finance_configs.bphtb_rate` (hanya NPOPTKP yang dibagi). Uji: `PUT /finance/config/tax {bphtb_rate:2.5, npoptkp:60000000}` → komponen berubah ke 39.500.000 (NPOPTKP ikut, tarif tidak).
- (c) `PUT /finance/config/tax` menerima `ppn_rate:-5, bphtb_rate:500, pph_rate:999, npoptkp:-1`; boleh dilakukan peran **finance** (staf), bukan hanya manajer; ini mengubah komponen BPHTB semua reservasi baru dan catatan pajak.
- (d) BANK_FEE = 1% × harga (deal KPR uji: invoice 9,8 jt dari harga 980 jt; plafon SP3K 784 jt → 1% plafon = 7,84 jt; invoice tidak dihitung ulang setelah SP3K). INSURANCE tetap Rp 3 jt.
- (e) NPOP = harga bersih setelah diskon; tidak ada pembanding NJOP (regulasi BPHTB memakai nilai terbesar antara harga transaksi dan NJOP).
- (f) PPh final penjual: satu `pph_rate` 2,5% untuk semua unit; PP 34/2016 membedakan rumah sederhana/rusun sederhana (1%); tidak ada pembeda per proyek/tipe. PPN: `ppn_rate` 12% × harga penuh (lihat finance-ar FN-24).
- (g) Pembulatan: `round()` Python = banker's rounding (harga 850.000.050 → BANK_FEE 8.500.000, bukan 8.500.001; 850.000.150 → 8.500.002). Selisih ≤ Rp 1, Rendah.

### [FN-13] [Severity: Sedang] IDOR: ledger biaya & amandemen kontrak terbaca sales lain
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/allin_router.py:239-242, 381-384` (`_contract()` tanpa cek `assigned_to`).
- Reproduksi: kontrak milik `sales@`; `sales2@` `GET /contracts/{cid}` → 403, `/contracts/{cid}/spr-compare` → 403, tetapi `GET /contracts/{cid}/costs-ledger` → **200** (invoice, kuitansi, penerima penyaluran, nama pembeli) dan `GET /contracts/{cid}/allin-amendments` → 200. (Pola yang sama dengan KT-09.)

### [FN-14] [Severity: Sedang] Biaya transaksi tidak muncul di laporan, arus kas, portal, dan rekonsiliasi
- Label bukti: [TERBUKTI-API] + [DARI-KODE]
- Laporan penerimaan (`/finance/reports/receipts`): 33 baris, **0 kuitansi KWB**; DB punya 10 kuitansi biaya Rp 118.800.000. Riwayat pembayaran keluar (`/finance/ap/payments`) tidak memuat penyaluran titipan. Grep `cost_invoices|cost_receipts` di `portal_router`, `payment_intake`, `customer_hub_router`: tidak ada → pembeli tak melihat/menagih invoice biaya di portal. Invoice biaya tidak punya jatuh tempo dan tidak masuk aging/dasbor AR (hanya kolom "Piutang biaya" di daftar). `/finance/reconcile` tidak punya kontrol 2-1470 (diuji manual: GL 34.000.000 = Σ kuitansi − Σ penyaluran, cocok — tetapi tidak dijaga otomatis).
- Dampak: Finance melihat penerimaan lebih kecil dari kas bank; titipan tidak terkendali sampai ada orang membuka tab kontrak per pembeli.

### [FN-15] [Severity: Sedang — IN-17 belum tertutup] "Bukti bayar wajib" hanya kosmetik pada invoice biaya & kuitansi AR
- Label bukti: [TERBUKTI-API]
- Reproduksi: `POST /cost-invoices/{id}/pay` dengan `proof_file_ids:["id-palsu-xyz"]` → 200; berkas yang sama dipakai di dua kuitansi biaya → 200; `POST /finance/ar/receipts` dengan id palsu → 200. (Jalur uang keluar sudah menolak id palsu — PK-13; jalur uang masuk belum.)

### [FN-16] [Severity: Rendah] Kebersihan layar & dokumen
- UI "Rincian harga & biaya" menampilkan kode mesin mentah `pass_through`, `revenue`, `discount`, `deposit`, `tax_out` di kolom "Perlakuan keuangan" (`k01-kontrak.png`).
- PDF invoice biaya tanpa jatuh tempo, tanpa petunjuk rekening pembayaran; kuitansi biaya tidak memuat sisa invoice. Teks tetap "Dihasilkan otomatis"; memo jurnal pembayaran denda/biaya memakai label "(uang muka)" salah.

---
## Terverifikasi OK (agar laporan tidak berat sebelah)
- Σ komponen pass-through = total invoice biaya = Σ kuitansi biaya; GL 2-1470 = Σ kuitansi − Σ penyaluran (cocok pada 5 deal uji; tidak dijaga otomatis, lihat FN-14).
- Rumus BPHTB `5% × (harga − NPOPTKP)` benar pada batas 79.999.999 / 80.000.000 / 80.000.001 (0) dan 850 jt (38,5 jt); pembulatan ≤ Rp 1.
- Pembayaran biaya 0, negatif, melebihi sisa invoice → 400; dua pembayaran biaya paralel → 409 + 200 (satu efek); dua beban developer paralel → 409 + 200; tiga persetujuan amandemen paralel → satu efek.
- Komponen kpr_only tersaring pada skema non-KPR (reservasi); skema nonaktif ditolak pada reservasi baru; amandemen: pengaju ≠ pemutus ditegakkan.
- Alur komponen BOOKING konsisten: booking fee → 2-1450 → dialihkan ke 2-1470 (`JV/2026/00071-72`), tidak mengurangi termin unit.
- Invoice biaya diterbitkan otomatis saat booking/kontrak lahir dan tersambung ke kontrak (`link_cost_docs_to_contract`); PDF invoice/kuitansi biaya terbit (`%PDF`).
- Beban developer lewat AP: jurnal Dr 6-1700 / Cr 2-1100 seimbang; pembayaran AP-nya Dr 2-1100 / Cr bank tanpa penggandaan.

## Tidak bisa diverifikasi
- Penyesuaian biaya terhadap perubahan regulasi tahun berjalan (tarif BPHTB daerah, PPh final, PPN DTP) — hanya ditandai sebagai pertanyaan.
- Alur biaya di portal pembeli (tidak ada referensi kode; tidak diuji dengan OTP).
- Perilaku multi-worker / skala besar.

## Pertanyaan terbuka untuk pemilik
1. Satu master saja? (`price_components` vs `cost_components`) — mana yang menjadi SSOT?
2. BPHTB: pembeli (titipan), developer (all-in, beban penjualan atau pengurang harga menurut PSAK 72), atau campuran? Tentukan sebelum FN-07 diperbaiki.
3. Apakah beban developer-borne dibukukan saat dicatat (kini) atau mengikuti pengakuan pendapatan (BAST)?
4. NPOPTKP & tarif BPHTB per daerah/proyek; PPh final 1% untuk rumah sederhana — apakah ada unit seperti itu?
