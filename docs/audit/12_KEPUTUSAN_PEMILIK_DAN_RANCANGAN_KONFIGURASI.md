# 12 — Keputusan pemilik & rancangan konfigurasi ("sistem tidak kaku")

Dokumen ini mencatat jawaban pemilik atas 16 keputusan yang tertunda (06 §4 / §8) dan menerjemahkannya menjadi
**pengaturan di Pusat Konfigurasi** (`backend/settings_store.py`), bukan perilaku yang dikunci di kode.

**Prinsip dari pemilik:** *"pastikan semua opsi bisa dikonfigurasi di sistem, intinya sistem tidak kaku."*
Artinya: jawaban pemilik menjadi **nilai bawaan**; opsi lain tetap tersedia sebagai pilihan yang bisa diganti
(per organisasi, per proyek, dan bila relevan per kontrak) tanpa deploy, dengan alasan + riwayat perubahan.

## 1. Aturan rancangan (berlaku untuk semua keputusan di bawah)

1. **Satu pintu baca.** Semua modul membaca kebijakan lewat resolver tunggal (`policy.resolve(key, project_id=…, contract=…)`),
   dengan urutan: **kontrak → klaster → proyek → organisasi → bawaan kode**. `settings_store.get` sudah mendukung
   klaster/proyek/organisasi; lapisan *kontrak* ditambahkan di resolver (disimpan di dokumen kontrak, bukan di `settings`).
2. **Enum, bukan boolean tunggal.** Tiap keputusan = satu key enum (`ref_group` di registry `/api/reference`, aturan CFG-03).
3. **Tidak ada pengaturan "mati".** Pilihan yang belum dibangun **tidak muncul/ditandai "belum tersedia"** dan ditolak validasi
   server — jangan sampai pemilik memilih opsi yang diam-diam tidak berpengaruh. Setiap opsi yang ditampilkan = perilakunya sudah ada dan teruji.
4. **Perubahan kebijakan = berlaku ke depan.** Mengganti pengaturan tidak menjurnal ulang transaksi lama. Transaksi mencatat
   *kebijakan yang berlaku saat itu* (`policy_snapshot`) supaya audit bisa menjelaskan kenapa dua deal diperlakukan beda.
5. **Pengaturan sensitif** (menyentuh uang/GL) → `sensitive=True`: wajib alasan, masuk `history`, hanya peran keuangan/owner.
6. **Perubahan yang mengubah saldo GL** dijalankan lewat Posting Profile mode bayangan (`POSTING_SHADOW=1`) dulu, 0 selisih,
   baru dinyalakan — pola yang sama dengan fase 1–2 Posting Profile.
7. Tiap keputusan wajib: tes merah-di-kode-lama/hijau-di-kode-baru **untuk tiap opsi**, suite penuh, fuzz invarian, `pattern_sweep --check`.

## 2. Tabel keputusan → pengaturan

Kolom **Bawaan** = jawaban pemilik. **Override**: O=organisasi, P=proyek, K=kontrak.

### A. Akuntansi inti

| # | Keputusan | Jawaban pemilik (bawaan) | Key pengaturan (enum / tipe) | Opsi yang disediakan | Override |
|---|---|---|---|---|---|
| 1 | PPN | "Bisa dikonfigurasi & per proyek" — **nilai bawaan = perilaku sekarang (tidak berubah)** sampai pemilik menetapkan | `tax.ppn.mode` (enum), `tax.ppn.rate` (pct) | `inklusif`, `eksklusif`, `bebas_ppn` | O, P, K |
| 2 | Titik pengakuan pendapatan | **Bertahap sesuai progres** | `revenue.recognition.method` (enum), `revenue.recognition.progress_source` (enum), `revenue.recognition.require_paid_gate` (bool) | `bast` · `progress`; sumber progres: `progres_bangun` · `termin_tertagih`; gerbang lunas opsional | O, P |
| 3 | BPHTB | **Dipilih per kontrak** | `bphtb.borne_by` (enum), `bphtb.developer_share_pct` (pct) | `pembeli`, `developer`, `dibagi` | O, P, **K (utama)** |
| 4 | Komisi | **Dikapitalisasi lalu diamortisasi** | `commission.accounting` (enum), `commission.amortization_basis` (enum) | `beban_langsung` · `kapitalisasi_amortisasi`; basis amortisasi mengikuti `revenue.recognition.*` | O, P |
| 5 | Valuasi persediaan | **Rata-rata bergerak** | `inventory.valuation` (enum) | `moving_average`, `fifo`, `last_po` | O |
| 6 | Biaya kontrak | **Input bebas + invoice** | `contract.cost_model` (enum), `contract.cost_free_input_needs_approval` (bool) | `input_bebas_invoice`, `wajib_all_in`, `persetujuan` | O, P |

### B. Siklus deal & persetujuan

| # | Keputusan | Bawaan | Key | Opsi | Override |
|---|---|---|---|---|---|
| 7 | Kapan lead/deal dianggap *won* | **Saat booking dikonfirmasi** | `lead.won_trigger` (kunci yang SUDAH ada; opsi `booking_fee_verified` · `spr_signed` · `ppjb_signed` · `ajb_signed`) — bawaan kode sekarang `spr_signed`, diubah ke `booking_fee_verified` di W1 | `booking_fee_verified`, `spr_signed`, `ppjb_signed`, `ajb_signed` | O |
| 8 | Persetujuan diskon | **Bertingkat menurut nilai** | memperluas `pricing.approval_min_amount` (+ ambang persen yang ada) menjadi `discount.approval_tiers` (list of `{max_amount, role}`) dan `discount.approval_mode` (enum) | mode: `bertingkat` (bawaan), `satu_level` (perilaku lama) — **hanya dua opsi** (W1-B: opsi `tanpa_persetujuan_sampai_batas` dibuang; "tanpa persetujuan di bawah batas" sudah dicakup ambang `pricing.approval_min_amount` yang tetap berlaku untuk MENENTUKAN KAPAN persetujuan perlu — mode ini hanya menentukan SIAPA yang menyetujui) | O, P |
| 9 | Ganti skema setelah ada pembayaran (IN-14) | **Manual oleh keuangan** | `payment.scheme_change.allocation` (enum) | `manual_keuangan`, `urut_termin_tertua`, `proporsional` | O, P |
| 13 | Reservasi kedaluwarsa, booking fee sudah dibayar | **Reservasi diperpanjang, unit tidak dilepas** | `reservation.expiry.paid_booking_fee` (enum), `reservation.expiry.extend_days` (int), `reservation.expiry.max_extensions` (int) | `perpanjang`, `antrean_refund`, `hangus` | O, P |
| 14 | Ganti skema KE KPR (FN-11) | **Tolak, buat kontrak baru** | `contract.scheme_change_to_kpr` (enum) | `tolak_buat_baru`, `hitung_ulang_dengan_persetujuan`, `izinkan_manual` | O, P |

### C. Perlakuan pada deal yang dibatalkan

| # | Keputusan | Bawaan | Key | Opsi | Override |
|---|---|---|---|---|---|
| 10 | Penerimaan **titipan** pada deal batal | **Boleh bebas seperti sekarang** | `deposit.on_cancelled_deal` (enum) | `bebas`, `wajib_alasan_dan_antrean_refund`, `tolak` | O |
| 11 | Akrual komisi / fee marketing / pajak yang sudah disetujui atau dibayar | **Selalu manual oleh keuangan** (per jenis) | `cancel.accrual_reversal.commission`, `.marketing_fee`, `.tax` (enum masing-masing) | `manual_keuangan`, `balik_otomatis_yang_belum_dibayar`, `balik_otomatis_semua` | O, P |
| 12 | Titipan biaya 2-1470 & invoice biaya terbuka | **Refund titipan, batalkan invoice terbuka** (dengan persetujuan keuangan) | `cancel.cost_deposit.policy` (enum), `cancel.cost_deposit.forfeit_pct` (pct), `cancel.cost_deposit.requires_approval` (bool) | `refund_dan_batalkan_invoice`, `manual_dengan_pengakuan`, `hangus_sebagian` | O, P |

### D. Master pajak & komponen biaya

| # | Keputusan | Bawaan | Key | Catatan | Override |
|---|---|---|---|---|---|
| 15 | Sumber NPOPTKP, tarif BPHTB, NJOP, PPh final 1%, BANK_FEE (FN-12) | **Satu master pajak, boleh ditimpa per proyek** | `tax.master.*` (grup baru "Master Pajak"): `npoptkp`, `bphtb_rate`, `pph_final_rate`, `njop_per_m2`, `bank_fee_pct_of_plafon` | Satu resolver `tax_master.resolve(project_id)`; semua perhitungan membaca dari sini; menimpa di proyek wajib alasan (tercatat) | O, P |
| 16 | Master komponen biaya (FN-01) | **Satukan: katalog jadi sumber, All-in jadi aturan** | katalog `price_components` (nama, akun GL, pajak, ditagih/ditalangi) + aturan `all_in_rules` (komponen mana yang berlaku per proyek/skema) | Migrasi bertahap dengan mode bayangan; dua master lama tidak dihapus sebelum selisih = 0 | O, P |

## 3. Catatan per keputusan yang berisiko

- **#2 Pengakuan pendapatan bertahap** adalah perubahan GL terbesar: butuh sumber progres tepercaya (`progres_bangun` dari modul proyek
  harus lolos validasi 0–100%, monoton naik, tidak boleh turun tanpa koreksi). Hubungannya dengan `contract_liabilities` dan gerbang BAST
  (`deal_state.assert_can_recognize_revenue`) perlu didefinisikan ulang: pada mode `progress`, BAST **tidak lagi** menjadi satu-satunya
  pemicu; pada mode `bast` perilaku sekarang dipertahankan 100%. Mulai dengan bayangan + `require_paid_gate=true`.
- **#4 Kapitalisasi komisi** bergantung pada #2 (basis amortisasi). Jika pengakuan pendapatan `bast`, amortisasi jatuh sekaligus saat BAST;
  jika `progress`, mengikuti persentase progres. Pembalikan saat batal diatur #11 (`cancel.accrual_reversal.commission`).
- **#1 PPN & #3 BPHTB** memengaruhi kuitansi/invoice/pajak dan kontrak lama: nilai bawaan harus **identik dengan perilaku sekarang**
  agar tidak ada selisih pada data yang sudah ada; kontrak lama diberi `policy_snapshot` hasil migrasi (nilai efektif saat ini).
- **#5 Persediaan**: `moving_average` butuh biaya rata-rata per item per gudang yang dihitung ulang pada tiap penerimaan; `fifo`/`last_po`
  hanya boleh dipilih bila lapisan biaya (`cost_layers`) tersedia — sebelum itu, opsi ditandai "belum tersedia" (aturan 3).
  Mengganti metode di tengah periode **hanya berlaku mulai periode berikutnya** (validasi server).
- **#7 `won`**: mengganti pemicu tidak mengubah deal yang sudah `won`; hanya deal baru/yang belum mencapai pemicu.
- **#8 Persetujuan bertingkat**: batas nominal dan peran bisa diatur; tidak boleh ada celah (rentang nominal harus menutup 0..∞, validasi server);
  pemohon tidak boleh menyetujui permintaannya sendiri.
- **#10 Titipan pada deal batal = bebas**: tetap dicatat sebagai titipan (2-1450) dan **tidak dapat dipakai menagih apa pun**; antrean refund
  hanya disarankan, tidak otomatis. Opsi lebih ketat tersedia bila pemilik berubah pikiran.
- **#11 manual**: bawaan sekarang = perilaku sekarang (tanda + tugas keuangan). Opsi `balik_otomatis_*` memposting jurnal koreksi lewat
  `money_op`/`deal_money` (idempoten, `source_event` unik) dan harus lolos rekonsiliasi.
- **#12 refund titipan biaya**: dikurangi biaya yang sudah benar-benar disalurkan ke pihak ketiga; refund memakai jalur uang keluar yang sudah
  digerbang (`money_op`), invoice biaya terbuka dibatalkan lewat `transition()` dengan syarat status.
- **#13 perpanjangan**: sweeper tidak melepas unit bila booking fee terbayar; perpanjangan berbatas (`max_extensions`) supaya unit tidak "mati"
  selamanya; setelah batas habis, perilaku jatuh ke tugas tindak lanjut ke sales/keuangan (bukan pelepasan diam-diam).

## 4. Urutan pengerjaan yang diusulkan (gelombang)

| Gelombang | Isi | Risiko GL | Bukti |
|---|---|---|---|
| **W0 Fondasi** | Resolver kebijakan (kontrak→klaster→proyek→org→kode), snapshot kebijakan, validasi "opsi belum tersedia", grup baru di Pusat Konfigurasi + UI (daftar, ubah, riwayat), semua key di atas terdaftar dengan bawaan = jawaban pemilik, tanpa mengubah perilaku | tidak ada | tes unit resolver, tes API CRUD + riwayat + validasi, UI Playwright |
| **W1 Deal & pembatalan** | #7, #8, #9, #10, #11 (manual + otomatis), #12, #13, #14 | rendah–sedang | tes tiap opsi (merah-lama/hijau-baru), fuzz, rekonsiliasi hijau |
| **W2 Pajak & biaya** | #15 master pajak + resolver, #16 satu master komponen (bayangan), #1 PPN, #3 BPHTB per kontrak, #6 model biaya kontrak | sedang | selisih bayangan = 0, kontrak lama tak berubah |
| **W3 Akuntansi inti** | #5 persediaan (rata-rata bergerak), #4 kapitalisasi + amortisasi komisi, #2 pengakuan bertahap | tinggi | Posting Profile bayangan 0 selisih, migrasi saldo, fuzz invarian baru (liabilitas kontrak ≥ 0, amortisasi ≤ kapitalisasi, persediaan nilai = Σ lapisan) |

Tiap gelombang diselesaikan, diverifikasi, dan di-push sebelum gelombang berikutnya; W3 hanya setelah W0–W2 stabil.

## 5. Yang BELUM diputuskan / diasumsikan

- Nilai bawaan #1 (PPN): pemilik meminta dapat diatur per proyek tetapi belum memilih mode bawaan → bawaan = perilaku sekarang. **Mohon konfirmasi mode & tarif per proyek.**
- Daftar tingkat persetujuan diskon (#8): batas nominal & peran belum disebut → disemai dari kebijakan persetujuan yang berlaku sekarang; **angka perlu diisi pemilik di UI**.
- `forfeit_pct` (#12) dan `extend_days`/`max_extensions` (#13): disemai 0 / 7 hari / 2 kali sebagai usulan sistem (`src="SISTEM"`), bukan dokumen legal.
- Belum ada kebijakan akuntansi untuk pembalikan **PPN** pada deal batal (di luar 16 keputusan ini) — dicatat untuk W2.

## 6. Status pengerjaan

### W0 — Fondasi (selesai; tanpa perubahan perilaku bawaan)
- `backend/policy.py`: resolver tunggal (`resolve`, `resolve_with_origin`, `snapshot`) — kontrak → klaster → proyek → organisasi → bawaan kode; tingkat kontrak
  hanya untuk kunci yang `levels`-nya memuat `"contract"`, nilai usang/tak sah diabaikan (jatuh ke tingkat berikutnya, tidak diam-diam berlaku).
- `settings_store.py`: `get_with_origin`; `levels` (tingkat penimpaan yang sah — `set_value` menolak tingkat lain); `unavailable` (opsi belum dibangun
  ditolak server); grup baru **"Kebijakan Akuntansi & Pembatalan"**; `settings_policy.py` = modul kebijakan (pola `settings_p88`), `reference_p102.py` = kosakata enum,
  asal nilai `cluster`/`contract` ditambahkan ke `setting_origin`.
- Kunci percontohan end-to-end: **`deposit.on_cancelled_deal`** (keputusan #10; bawaan `bebas` = perilaku lama) — dibaca di `deposit_policy.py` oleh
  `POST /finance/ar/{deal}/deposit`; opsi `tolak` dan `wajib_alasan_dan_antrean_refund` (alasan ≥ 10 karakter + tugas & notifikasi Keuangan) berlaku nyata.
- UI Pusat Konfigurasi › Aturan Bisnis: **pemilih tingkat proyek** (sebelumnya UI hanya bisa mengubah tingkat organisasi); di tampilan proyek hanya aturan yang
  mendeklarasikan `levels` memuat `project` yang ditawarkan (aturan lama tidak diam-diam tak berpengaruh); simpan/reset sadar-tingkat; opsi `unavailable` nonaktif + label.
- Keputusan desain: **kunci baru didaftarkan bersama pembacanya** di tiap gelombang (bukan semua di muka) — kunci tanpa pembaca = pengaturan mati, melanggar prinsip.
- Tes: `backend/tests/p0/test_w0_kebijakan.py` (12 tes: resolver, level, opsi belum tersedia, API, perilaku titipan; 7 tes HTTP merah di kode lama `7f31394`,
  5 tes resolver memanggil modul yang tidak ada di kode lama), `scripts/ui/w0_kebijakan.js` (17 pemeriksaan peramban).
- Belum: endpoint penimpaan tingkat kontrak (dikirim bersama kunci kontrak pertama, BPHTB, di W2); backend belum menolak penimpaan tingkat proyek untuk kunci LAMA yang tidak
  mendeklarasikan `levels` (UI sudah tidak menawarkannya).
