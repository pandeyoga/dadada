# Status perbaikan hasil audit — apa yang sudah ditutup, apa yang belum

> Tanggal: 5 Nov 2026 · Cabang: `claude/wizardly-heisenberg-7onk5l` · Dasar bukti: **12 berkas tes regresi, 204 tes** di `backend/tests/p0/`, dijalankan pada backend segar dengan seluruh kode gabungan, dan **tiga suite diulang** untuk membuktikan tes dapat diulang. Tes baru ditulis agar **gagal di kode lama dan lulus di kode baru**.
> Perbaikan hanya menyentuh temuan ronde 1 (`01`–`05`). Temuan ronde 2 (`07` pengadaan, `08` finance) **belum dikerjakan**, kecuali kebetulan tertutup oleh perbaikan fondasi (ditandai).
> Legenda: ✔ tertutup dengan bukti tes · ◐ sebagian · ✘ belum · ⚖ menunggu keputusan pemilik.

## 1. Angka

| Tingkat (ronde 1) | Total | ✔ Tertutup | ◐ Sebagian | ✘/⚖ Terbuka |
|---|---:|---:|---:|---:|
| Kritis | 13 | **13** | 0 | 0 |
| Tinggi | 43 | **30** | 7 | 6 |
| Sedang dan Rendah | 59 | (lihat daftar) | | sebagian besar belum |

Tinggi yang masih terbuka: IN-14 ⚖, GL-04 ⚖ (PPN), GL-07 ⚖ (titik pengakuan pendapatan), GL-11 (dimensi proyek/unit pada jurnal), GL-12 ⚖ (persediaan), KT-03 ⚖ (model biaya kontrak vs SPR). Sebagian: PK-06, PK-07, PK-12, PK-14, PK-15, KT-12, KT-13.

## 2. Status per temuan

**Uang masuk (`01`):** IN-01 ✔ · IN-02 ✔ · IN-03 ✔ · IN-04 ✔ · IN-05 ✔ (void resmi + hapus-paksa konsisten) · IN-06 ✔ · IN-07 ✔ (penerimaan pasca-BAST; "BAST tanpa cek pelunasan" = GL-07 ⚖) · IN-08 ✔ · IN-09 ✘ · IN-10 ✔ (diturunkan ke Sedang) · IN-11 ✔ · IN-12 ✔ · IN-13 ✔ · IN-14 ⚖ · IN-15 ✔ · IN-16 ◐ (booking fee dan verifikasi generik belum) · IN-17 ✔ · IN-18 ◐ (rekening bisa dipilih di booking fee/titipan/biaya; jenis pembayaran masih satu akun 2-1400) · IN-19 ✔ · IN-20 ✔ · IN-21 ✔ · IN-22, IN-23 ✘.

**Uang keluar (`02`):** PK-01 ✔ · PK-02 ✔ · PK-03 ✔ · PK-04 ✔ · PK-05 ✔ · PK-06 ◐ (`cash_lock` baru di sebagian jalur) · PK-07 ◐ (pembuat≠penyetuju, penyetuju≠pembayar, pemohon≠pencair; batas bertingkat belum) · PK-08 ✔ · PK-09 ✔ (void pembayaran AP) · PK-10 ✔ · PK-11 ✔ · PK-12 ◐ (diblok untuk deal batal; pembatalan otomatis/clawback belum) · PK-13 ✔ · PK-14 ◐ · PK-15 ◐ (varian huruf/spasi pada nomor faktur belum, lihat PG-22) · PK-19 ◐ (pilihan rekening sumber lewat GL-17) · PK-16, 17, 18, 20, 22, 23 ✘ · PK-21 ✔ (tie-out kas bon gabungan).

**Akuntansi (`03`):** GL-01 ✔ · GL-02 ✔ · GL-03 ✔ · GL-04 ⚖ · GL-05 ✔ · GL-06 ✔ · GL-07 ⚖ · GL-08 ✔ · GL-09 ✔ · GL-10 ✔ (void kuitansi dan pembayaran AP; nota kredit vendor belum) · GL-11 ✘ · GL-12 ⚖ · GL-13 ✔ (rename akun tetap boleh) · GL-14 ✔ · GL-15 ✔ · GL-16 ✔ · GL-17 ◐ (belum: upah, pembelian aset, komisi, UI biaya all-in) · GL-18 ✔ · GL-19 ✘ (Posting Profile: proyek terpisah) · GL-20 ✘ · GL-21 ✔ · GL-22 ✔ · GL-23, 24, 25, 26, 27, 28 ✘.

**Kontrak dan konversi (`04`):** KT-01 ✔ · KT-02 ✔ · KT-03 ⚖ · KT-04 ✘ · KT-05 ✔ · KT-06 ✔ · KT-07 ✔ · KT-08 ✔ · KT-09 ✔ · KT-10 ✔ · KT-11 ✔ · KT-12 ◐ · KT-13 ◐ (hanya label) · KT-14 ✘ · KT-15 ✔ · KT-16 ✔ · KT-17 ✔ (UI konfirmasi NIK belum) · KT-18 ✔ · KT-19 ✔ · KT-20 ✔ · KT-21 ✔ · KT-22 ◐ (rentang divalidasi; alur persetujuan potongan ⚖) · KT-23 ✔ · KT-24 ✔ · KT-25 ✔ · KT-26 ✔ · KT-27 ✔ · KT-28 ✔ · KT-29 ◐ · KT-30 ✘.

**WhatsApp (`05`):** WA-01 sampai WA-11 ✔ (Inbox ditulis ulang; paginasi `/wa-capture`).

**Ditemukan dan ditutup di tengah jalan (bukan dari laporan awal):** balasan template otomatis berulang tanpa jeda; jurnal penerimaan yatim bila deal dihapus paksa sebelum event diproses (terukur Rp 677 jt selisih rekonsiliasi); paginasi Inbox yang melewatkan pesan sedetik (kursor `created_at` saja); void kuitansi yang membalik uang dua kali bila dipicu paralel.

## 3. Perubahan perilaku yang akan terlihat pemakai (sampaikan ke tim)

**Keuangan**
- Permintaan identik (dokumen, nominal, pelaku sama) dalam **15 detik** ditolak 409 — mencegah klik ganda; kirim `client_ref` bila memang ingin kirim ulang idempoten.
- Uang keluar dicek terhadap **saldo rekening**; saldo kurang ditolak. Sakelar `cash.allow_negative` (bawaan **mati**).
- **Pemisahan tugas ditegakkan di API:** pembuat tagihan/PO tidak boleh menyetujui; penyetuju tidak boleh membayar; pemohon tidak boleh mencairkan pengajuannya sendiri. Satu-satunya pengecualian `super_admin`. **Akibat praktis:** tim finance berisi satu orang tidak bisa menuntaskan tagihan sendiri (perlu Owner).
- Pencairan pengajuan wajib **foto bukti valid** (di server, bukan hanya UI), tidak boleh dipakai ulang.
- **Void resmi:** kuitansi (`finance:approve`, alasan ≥10 huruf, pencatat tidak boleh membatalkan sendiri) dan pembayaran AP; hapus-paksa kini juga menurunkan kewajiban kontrak. Kuitansi void ditandai DIBATALKAN, hilang dari portal pembeli dan total laporan.
- Kuitansi manual `method=kpr` ditolak (dana bank dicatat lewat tab KPR); kuitansi bernominal sama dua kali ditolak kecuali `allow_duplicate`; mutasi bank harus sama nominal dengan bukti yang dicocokkan.
- Pencairan KPR hanya `financing:approve` (sales tidak lagi); refund/verifikasi booking fee `finance:approve`; `sales_manager` boleh membatalkan tetapi refund **ditunda** menunggu Finance.
- Tanggal jurnal manual divalidasi (tidak boleh rusak/masa depan); jurnal manual langsung ke akun kendali (1-1300, 2-1400, 2-1100, 2-1450) atau induk kas butuh Manajer Keuangan/Direksi + alasan; tutup bulan yang belum berakhir ditolak; kode akun baru wajib `N-NNNN`.
- Kuitansi manual dan pembayaran AP punya **tanggal bayar nyata** (`value_date`).
- Penerimaan pasca-BAST mengurangi piutang `1-1300` (bukan menambah kewajiban kontrak); pelunasan denda ke piutang denda, pendapatan unit saat BAST tidak lagi memuat denda.
- Tutup tahun → buka → tutup lagi kini menerbitkan jurnal penutup baru. Event GL yang gagal dicoba ulang berjeda (30/120/600/1800 dtk) dan terlihat di health/banner; ada endpoint ulang manual.
- Nomor faktur vendor (opsional) unik per vendor; `retention_pct` dibatasi 0–100.

**Penjualan dan kontrak**
- **Sales tidak bisa lagi menandatangani PPJB/AJB** dari dialog Legal lama (kini hanya-baca + tautan ke Kontrak & Legal); tahap legal hanya lewat kontrak oleh manajer.
- Sales hanya melihat **pembeli miliknya** sendiri.
- Jadikan Pembeli aman terhadap klik ganda/dua tab; satu pembeli per lead; NIK 16 digit, NPWP 15–16 digit, penghasilan ≥ 0; telepon/email kembar ditolak 409.
- **Ganti PIC lead memindahkan** deal, kontrak, AR, booking fee, pembeli, percakapan WA.
- Cicilan jatuh pada **tanggal 7 dengan toleransi 13 hari**, dasar jatuh tempo = tanggal **aktivasi kontrak** (mengikuti `payment.staged.*`/`payment.cash.*`); skema bawaan lama yang belum pernah disunting **diperbarui otomatis saat server start**; aktivasi ulang tidak menyusun ulang jadwal.
- Penawaran melebihi batas unit aktif per lead kini ditolak; lead lost/recycle tidak bisa memesan unit.

**WhatsApp dan portal**
- Inbox: 3 panel setinggi layar, cari, filter belum dibaca, paginasi, real-time ±10 detik.
- "Kirim sbg Pesan Masuk" hanya mode simulasi; balasan template otomatis ber-jeda 24 jam.
- Master OTP portal **mati** kecuali `PORTAL_MASTER_OTP` diisi eksplisit; kode kosong selalu ditolak.

## 4. Menunggu keputusan pemilik

1. Harga jual **inklusif atau eksklusif PPN** (GL-04). 2. **Titik pengakuan pendapatan** (GL-07). 3. **BPHTB** titipan pembeli/ditanggung/campuran. 4. Komisi **dikapitalisasi atau dibeban**. 5. **Metode valuasi persediaan** dan perlakuan opname (GL-12, PG-01). 6. Model biaya kontrak vs SPR (KT-03: izinkan input biaya bebas + invoice, atau wajibkan skema all-in). 7. Kapan lead menjadi `won` (KT-13). 8. Alur persetujuan potongan/biaya di atas harga (KT-22). 9. Pemetaan alokasi saat ganti skema setelah ada pembayaran (IN-14). 10. Apakah penerimaan **titipan** pada deal batal tetap diizinkan (sekarang diizinkan sengaja, jalur sah untuk uang nyasar lalu refund).

## 5. Risiko dan catatan teknis

- **Dua mekanisme kunci** (`money_lock.locked` fail-cepat dan `idempotency.mutex` antre) hasil dua agen berbeda; sebaiknya disatukan.
- **Status sementara** (`disbursing`, `settling`, `approving`, `paying`, `voiding`) bisa tertinggal bila proses mati tepat di tengah; perlu penyapu.
- `once()` memblok pembayaran persis sama 15 detik (disengaja). `cash_lock` baru di sebagian jalur; dua pengeluaran berbeda bersamaan dari rekening pas-pasan masih bisa lolos.
- Indeks unik baru (`journal_entries(org,source_event)`, `customers(org,lead_id)`, `customer_deposits`, `contract_liabilities`, `ap_invoices` vendor+nomor faktur) **hanya mencatat peringatan** bila data lama sudah duplikat; periksa log startup dan bereskan duplikat.
- **Data lama tidak ditulis ulang:** jurnal/kuitansi yang terlanjur salah akun (pasca-BAST, denda) tetap; koreksi dengan jurnal penyesuaian oleh akuntan. Jurnal lama bertanggal UTC tetap.
- Gate kepatuhan ukuran file **sudah gagal sebelum sesi ini** (5 berkas); kini 4 (`finance_engine.py` 1068, `models.py` 820, `portal_router.py` 830, `AdminPermissions.js` 564). `contracts_engine.py` turun di bawah batas.
- Beberapa tes lama disesuaikan karena perilaku **sengaja** berubah (`backend_test.py`, `backend_test_phase25.py`, `test_ar_bank_portion…`, `test_iter30`, `test_p84`, dll.); tes lama yang bergantung login `superadmin@sipro.co.id` atau data seed lama tidak dapat dijalankan di lingkungan ini.
- Ketiga skrip lama (`backend_test_phase20.py`, `scripts/verify_29b.py`, `scripts/verify_partner.py`) memakai jalur booking-only/PPJB lama dan akan merah secara sah.

## 6. Cara menjalankan tes regresi

Dari `backend/`, server hidup pada DB segar, lalu per berkas:

```bash
API_BASE=http://localhost:8020/api DB_NAME=<db> MONGO_URL=<uri> REACT_APP_BACKEND_URL=http://localhost:8020 \
  python -m pytest tests/p0/<berkas>.py -n 0 --noconftest -q
```

Berkas: `test_p0_kontrak`, `test_p0_kontrak2`, `test_p0_lead_customer`, `test_p0_masuk`, `test_p0_masuk_2`, `test_p0_keluar`, `test_p0_keluar_lanjutan`, `test_p0_gl`, `test_p0_gl_bast`, `test_p0_void_receipt`, `test_p0_inbox`, `test_p0_akuntansi2` (jumlah tes: 14, 28, 8, 18, 25, 35, 26, 5, 3, 6, 7, 29).

## 7. Sebelum deploy ke produksi

1. **Backup** database dan uji pemulihan. 2. Jalankan di salinan data produksi, perhatikan log indeks unik dan migrasi skema bawaan. 3. Jalankan `/finance/reconcile` sebelum dan sesudah. 4. Pastikan `PORTAL_MASTER_OTP` acak/kosong di server dan variabel lingkungan baru dibaca (`EVENT_RETRY_BACKOFF` opsional). 5. Sampaikan perubahan perilaku (bagian 3) ke finance, sales, dan manajer **sebelum** go-live terutama pemisahan tugas dan jeda 15 detik.

## 8. Ronde 3 — perbaikan berbasis POLA (dokumen 11, 11a–11c)

Konteks: penelusuran pola menemukan celah yang sama di jalur yang belum disentuh ronde 1–2. Tiap perbaikan di bawah punya tes regresi yang
**merah pada kode lama dan hijau pada kode baru** (dibuktikan dengan mengembalikan kode lama sementara).

| ID | Status | Perubahan | Tes |
|---|:-:|---|---|
| AZ-11 | ✔ | `super_admin` hanya boleh diberikan/diubah oleh `super_admin` (pemilik organisasi tidak bisa lagi membuat pengendali lintas-tenant) | `test_p0_otorisasi.py` |
| AZ-12 | ✔ | `PUT /admin/users/{id}` dibatasi `org_id`; perubahan sandi dicatat di audit (tanpa nilai) | idem |
| PL-01 | ✔ | Transfer internal: dana dicek (dan rekening dikunci) saat **disetujui**, bukan hanya saat dibuat | `test_p0_dana_kas.py` |
| PL-02 | ✔ | Setuju/tolak transfer atomik (CAS); yang kalah balapan mendapat 409; status sementara `posting` | idem |
| PL-03 | ✔ | `cash_bank.funds_guard` (kunci per rekening + cek dana + tahan sampai jurnal terposting) dipasang di 10 jalur uang keluar: komisi, refund titipan, aset tetap, pencairan pengajuan dana, upah, fee marketing, pencairan & penggantian kas bon, setoran pajak, refund pembatalan | idem |
| PL-05 | ✔ | Tanggal bisnis dari WIB (`today_wib`) di 20 berkas; dini hari WIB "hari ini" tidak lagi ditolak sebagai "masa depan" | `test_p0_waktu.py` |
| PK3-05 / FZ-03 | ✔ | `deal_state.py` (satu predikat "batal" untuk semua jalur): BAST hanya untuk deal `booked`/`completed` tidak batal | `test_p0_status_deal.py` |
| FZ-01 | ✔ | Void kuitansi **sesudah BAST** menaikkan piutang 1-1300 (bukan membalik 2-1400 yang sudah nol) | idem |
| FZ-02 | ✔ | Void kuitansi pada deal batal ditolak (koreksi lewat pengajuan pembatalan/refund) | idem |
| FZ-08 | ✔ | Tahap KPR (SP3K/akad…) ditolak pada kontrak/deal batal | idem |
| PK3-06 | ◐ | Catatan pajak milik deal batal tidak bisa dilaporkan/disetor (**pembersihan otomatis catatan pajak saat batal belum dikerjakan**) | idem |
| PK3-04 | ✔ | "Buka blokir" hanya untuk unit yang diblokir; hapus-paksa deal tidak melepas unit yang kini dipegang deal lain | idem |
| PK3-01 | ✔ | Pembuatan rekap upah diserialkan per proyek (rekap kedua ditolak "bertumpang") | — (belum ada tes khusus) |
| PK3-02 | ✔ | Stok keluar & opname diserialkan per material | `test_p0_konkurensi3.py` |
| PK3-03 | ✔ | Penerbitan BAST diserialkan per unit (permintaan serentak mendapat dokumen yang sama) | idem |
| AZ-01 / AZ-02 | ✔ | Lingkup organisasi: `org_scope.py` (`get_in_org`, `org_filter`) dipakai di ±170 pencari-by-id di 40 router; lintas-org dijawab **404** (bukan 403). Sapuan `P11` turun 188→17 (sisanya sah: `/auth/*` dan koleksi `orgs`) | `test_p0_otorisasi_org.py` (30) |
| AZ-04 | ✔ | KPR: scope sales (sales hanya KPR dari deal yang ditugaskan kepadanya) | `test_p0_otorisasi_lain.py` |
| AZ-05 | ✔ | Menambah nilai referensi master butuh `settings:manage` | idem |
| AZ-06 | ✔ | `send-wa`: lead/customer tujuan wajib di org pemanggil dan (untuk sales) miliknya; sales hanya boleh mengubah/mengarsipkan template buatannya | idem |
| AZ-07 | ✔ | Berkas non-gambar/PDF disajikan `attachment`; `X-Content-Type-Options: nosniff` selalu | idem |
| AZ-08 | ✔ | `re.escape(q)` di 10 pembangun `$regex`; `q=[` tidak lagi 500 | idem |
| AZ-09 | ✔ | `/webhooks/web` dibatasi laju per IP (bawaan 60/10 menit, `WEB_FORM_RATE_MAX`) | idem |
| AZ-10 | ✔ | OTP portal: maks 5 percobaan per kode (atomik), kode dikunci setelahnya; permintaan kode baru dibatasi per pembeli | idem |

Perubahan perilaku yang akan terlihat pemakai:
- Persetujuan transfer/pembayaran dari rekening yang saldonya sudah berkurang kini ditolak dengan pesan "Saldo … tidak cukup" **pada saat disetujui**.
- Dua pembayaran dari rekening yang sama kini **antre** (maks. 8 detik); bila terlalu lama pengguna melihat 409 "Rekening/kas ini sedang dipakai transaksi lain".
- BAST pada deal yang belum booking atau sudah batal kini ditolak (400).
- Void kuitansi pada deal yang sudah batal ditolak; void kuitansi pra-BAST sesudah BAST menaikkan piutang.
- Tahap KPR pada kontrak batal ditolak. Setoran/lapor pajak untuk deal batal ditolak.
- Penambahan pengguna dengan peran Super Admin kini hanya bisa oleh Super Admin.
- Data milik organisasi lain kini dijawab 404 di semua layar/API. Sales hanya melihat KPR dari deal miliknya.
- Pemilih "tambah bank/jenis izin baru" hanya berhasil untuk peran dengan izin `settings:manage` (peran lain memakai nilai itu hanya pada formulir yang sedang diisi).
- Berkas HTML/SVG yang diunggah kini diunduh, bukan dibuka di peramban. Kode OTP portal terkunci setelah 5 salah. Formulir web publik dibatasi 60 kiriman/10 menit per IP (naikkan lewat env bila di belakang proxy dengan lonjakan sah).

Risiko/catatan baru: status sementara `posting` pada transfer bisa tertinggal bila proses mati tepat di tengah (jurnalnya idempoten, jadi aman dicoba ulang oleh admin setelah status dipulihkan);
`funds_guard(flush_events=True)` mengosongkan antrean event sebelum melepas kunci (komisi, refund titipan) sehingga latensi permintaan ikut naik sedikit.

### 8.G-C — Master komponen biaya, rekonsiliasi luas, lintas-organisasi keuangan

| ID | Status | Perubahan | Tes |
|---|:-:|---|---|
| FN-02 | ✔ | Master `cost_components` / skema all-in / skema pencairan KPR **divalidasi di API** (`cost_master_rules.py`): nominal ≥ 0, persen 0–100, cara hitung & perlakuan dikenal, kode unik per org (diserialkan `mutex`), akun GL harus **nyata, aktif, bertipe sesuai** di CoA (beban=expense; titipan=liability bukan akun kendali; utang usaha=2-1100 karena pembayaran AP selalu mendebet 2-1100), butir skema hanya merujuk komponen yang ada & aktif (butir lama yang kemudian dinonaktifkan tidak memblokir simpan ulang), tanpa butir ganda, proyek skema harus di org. Komponen **nonaktif tidak ikut snapshot reservasi/amandemen baru** (`resolve_scheme` sebelumnya `include_inactive=True`); komponen bernilai negatif (master lama rusak) ditolak saat snapshot; harga pratinjau negatif ditolak. Opsi `sync_schemes=false` pada pembuatan komponen (bawaan tetap menempel ke semua skema). Akun GL tak sah tidak lagi bisa melahirkan tagihan AP yatim (FN-05 dari sumbernya) | `test_p0_komponen_biaya.py` |
| FN-12c | ✔ | `PUT /finance/config/tax`: tarif 0–100%, NPOPTKP ≥ 0 (dulu −5% / 500% / −1 tersimpan) | idem |
| FN-01 | ◐ | Banner tab "Komponen Biaya" (katalog `price_components`) diperbaiki jujur: *referensi, belum mengubah tagihan/jurnal*; kebijakan yang berlaku ada di tab Biaya All-in. **SSOT satu master = ⚖ keputusan pemilik** (dua master tetap ada) | — (teks UI) |
| G3 | ✔ | `/finance/reconcile` dari 7 → **12** pemeriksaan (`finance_audit_ext.py`): 1-1300 Piutang Usaha (sisa tagih AR pasca-BAST + denda belum lunas; rincian di `sources`), 2-1470 Titipan Biaya (Σ kuitansi biaya − Σ penyaluran), 1-2100 Aset Tetap (Σ harga perolehan belum dilepas), 1-2200 Akumulasi Penyusutan (Σ `asset_depreciations` aset belum dilepas), 2-2100 Utang Bank (pokok − pokok terbayar menurut jadwal). Mekanisme `indicator` (peringatan yang tidak menggagalkan `ok`; `indicators_off`) tersedia, **belum ada pemeriksaan yang memakainya** karena kelimanya hijau pada seed baru dan setelah suite penuh. Saldo sub-akun kas/bank sengaja tidak diperiksa (dihitung dari jurnal itu sendiri) | `test_p0_rekonsiliasi_luas.py` |
| AZ-13 | ✔ | Lingkup org koleksi keuangan: ±50 endpoint (AR/deposit/kuitansi, AP, komisi, fee marketing, bukti transfer, faktur & bukti potong, pengajuan dana, kas bon, kas kecil, bank + pencocokan + rekonsiliasi, aset, pinjaman, rekap upah, invoice biaya) kini menjawab **404** (dulu 400 "tidak ditemukan"; `spr-compare` menjawab 200 kerangka kosong) lewat `org_scope.exists_in_org`; pembuatan tagihan AP/pengajuan dana/kas bon/aset/biaya kas kecil tidak lagi menerima `project_id`/`ap_bill_id` milik org lain; mutasi bank org B tidak bisa dicocokkan ke dokumen org A | `test_p0_lintas_org_keuangan.py` |

Perubahan perilaku yang akan terlihat pemakai:
- Menyimpan komponen biaya / skema all-in / skema pencairan KPR dengan angka tak wajar atau akun GL tak sah kini **ditolak 400** dengan alasan; komponen yang dinonaktifkan **hilang dari reservasi/amandemen berikutnya** (kontrak lama tidak berubah).
- Konfigurasi pajak di luar 0–100% ditolak. Lintas-org kini 404 (bukan 400) di endpoint keuangan.
- Rekonsiliasi menampilkan 5 baris baru; selisih pada baris itu menyalakan lampu merah dasbor Finance seperti 7 baris lama.

Butuh keputusan pemilik (tidak dikerjakan): FN-01 (satu master komponen biaya?), FN-11 (ganti skema kontrak ke KPR tanpa menambah komponen KPR-only — butuh aturan hitung ulang), FN-12a/b/d–f (NPOPTKP per proyek, satu sumber tarif BPHTB, BANK_FEE dari plafon, NJOP, PPh final 1%), batas wajar nominal komponen (dipasang Rp 1 triliun sebagai pagar kewajaran, ubah bila perlu), izin `finance:update` untuk peran staf pada konfigurasi pajak.
Catatan teknis: pemeriksaan 2-1470 menjumlahkan **semua** kuitansi biaya; bila kelak pembatalan deal (perlakuan titipan pada deal batal = keputusan pemilik) menjurnal 2-1470, catatan subledgernya (`cost_receipts`/`cost_disbursements`) harus ikut diubah agar pemeriksaan tetap hijau.
