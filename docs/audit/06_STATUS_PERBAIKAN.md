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
| WH-01 (audit CRM 10 #1) | ✔ | Webhook publik **diverifikasi bila rahasianya dikonfigurasi**: Meta Lead & WhatsApp (`X-Hub-Signature-256` = HMAC-SHA256 atas BADAN MENTAH, `compare_digest`; `GET` handshake `hub.verify_token`), Google (`google_key` konstan-waktu), TikTok (`TikTok-Signature t=,s=` toleransi 5 menit atau rahasia bersama di header). Salah/tidak ada → 401/403 seragam, **tidak** masuk antrean gagal-masuk (penyerang tak bisa membanjiri tugas/notifikasi supervisor); kontrak lama `WebhookLead` di `/webhooks/wa` ikut wajib bertanda tangan. Rahasia terenkripsi (`webhook_secrets`) atau env; `GET /webhooks/status` (`settings:view`) menandai kanal yang belum aman; `PUT /webhooks/secrets/{kanal}` (`settings:manage`) | `test_p0_webhook_aman.py` (23) |
| WH-02 | ✔ | Anti-replay: klaim atomik id peristiwa (`leadgen_id`/`lead_id`/`event_id`/`wamid`, 7 hari) + cap waktu TikTok yang ikut ditandatangani; pesan WA ganda bersamaan tidak lagi menubruk indeks unik; badan > 1 MB → 413; JSON bersarang dalam/angka raksasa → 400 (dulu 500); `google_key` & kolom rahasia disamarkan di antrean gagal-masuk | idem |
| CT-01 | ✔ | CTWA: `referral` (`ctwa_clid`, `source_id`, `source_url`, `headline`, `media_url`…) pada pesan pertama disimpan sebagai `attribution.ctwa` di percakapan DAN lead (pertama menang, atomik, idempoten, terikat org+nomor; lead yang lahir sesudahnya mewarisi; `ctwa_clid` divalidasi bentuknya) | `test_p0_ctwa_capi.py` (14) |
| CT-02 | ✔ | CAPI **Business Messaging**: lead ber-`ctwa_clid` dikirim `action_source: business_messaging`, `messaging_channel: whatsapp`, `user_data{whatsapp_business_account_id, ctwa_clid}`, `event_id` deterministik (org, event Meta, ctwa_clid, deal); pemicu tetap `capi_hooks` (Lead/SubmitApplication→QualifiedLead/InitiateCheckout/Purchase); tanpa token+dataset = simulasi yang mencatat payload final (tanpa jaringan); sisip-dulu-baru-kirim menutup kirim ganda; token via header (bukan query) | idem |
| PK3-08 | ✔ | `deal_cancel_cleanup.close_deal_dependents` dipakai KEDUA jalur batal (`deal_cancel.cancel` & `cancellation_engine.decide`): tugas aktif (deal/kontrak/KYC/lead) → `cancelled`; komisi & fee marketing belum disetujui → `cancelled`; KPR berjalan → `cancelled`/tahap `batal`; kupon dilepas; catatan pajak `pending` → `cancelled` (laporan pajak mengecualikannya, `PUT` ditolak). Idempoten. **Yang sudah disetujui/dibayar TIDAK dijurnal balik** — hanya diberi tanda `cancel_followup` + notifikasi + satu tugas ke Keuangan | `test_p0_siklus_deal.py` |
| PK3-06 (lanjutan) | ✔ | Pembersihan otomatis catatan pajak saat deal batal kini ada (lihat PK3-08) | idem |
| PK3-09 / FZ-04 | ✔ | Hapus-paksa deal: `pdc_cheques`→`pdc_instruments`; + komplain, klaim garansi, marketing fee (+ pembayaran & jurnalnya), faktur pajak, peristiwa konversi, tugas kontrak; bukti kas BKM/BKK ikut terhapus bersama jurnalnya; `customers.deal_id` dilepas; fee untuk deal yang tidak ada tidak bisa disetujui/dibayar | `test_p0_siklus_hapus.py` (pemindai yatim atas SEMUA koleksi) |
| FZ-07 / PK3-11 | ✔ | Mutex per-deal `deal_money` dipegang penerimaan (`apply_receipt` dibungkus), void kuitansi, hapus kuitansi, dan hapus-paksa deal; hapus kuitansi memakai kunci yang sama dengan void, membaca ulang kuitansi di bawah kunci (kedua → 409/404, bukan membalik dua kali) dan tidak membalik alokasi kuitansi yang sudah void | idem |
| PK3-12 | ✔ | Hapus kuitansi / void / hapus-paksa deal melepas pencocokan bank (mutasi kembali "belum cocok"); `unmatch` toleran bila kuitansinya sudah hilang/void (data warisan yang tersangkut) | idem |
| PK3-13 | ✔ | Hapus lead/unit/proyek: deal batal dibuang lewat kaskade `delete_deal_cascade` (bukan `delete_many` mentah); bila deal batal punya jejak uang (kuitansi, titipan, jurnal, refund…) → diblokir "catatan keuangan deal batal" (hanya hapus-paksa yang menghapusnya) | idem |
| PK3-14 | ✔ | Hapus proyek diblokir: mutasi stok, permintaan material, absensi/rekap upah, kas bon terbuka, kas kecil, aset tetap, klaim subkon, GRN, tagihan AP; BoQ & master material kosong ikut dihapus; hapus-paksa tidak menghapus stok/upah terutang | idem |
| PK3-15 | ✔ | BAST batal mengembalikan unit ke status SEBELUM BAST (`prev_unit_status`, bukan selalu `sold`); BAST batal tak lagi memblokir pembatalan kontrak (field `state`, bukan `status`); pembatalan BAST di-CAS (paralel → satu 200) | `test_p0_siklus_deal.py` |
| PK3-07 | ✔ | Pengingat WA hanya untuk invoice `unpaid`/`partial` dan item bukan `cancelled`, tidak untuk deal batal; "kirim pengingat penagihan" manual ditolak untuk tagihan batal/lunas | idem |
| PK3-19 | ✔ | Lead tidak bisa ditandai `lost`/`recycle` selagi punya deal `reserved`/`booked`/`completed` (batalkan dulu) | idem |
| FN-03 | ◐ | Sisi aman: pratinjau/pengajuan/penyelesaian pembatalan memuat `cost_holds` (saldo titipan biaya 2-1470 + invoice biaya terbuka); **persetujuan diblokir** selama ada, kecuali `acknowledge_costs=true` + `cost_note` ≥ 10 huruf (dicatat di keputusan & audit). Perlakuan akuntansinya (kembalikan/salurkan/void invoice) ⚖ **menunggu keputusan pemilik**; tidak ada jurnal baru | idem |

Perubahan perilaku yang akan terlihat pemakai:
- Persetujuan transfer/pembayaran dari rekening yang saldonya sudah berkurang kini ditolak dengan pesan "Saldo … tidak cukup" **pada saat disetujui**.
- Dua pembayaran dari rekening yang sama kini **antre** (maks. 8 detik); bila terlalu lama pengguna melihat 409 "Rekening/kas ini sedang dipakai transaksi lain".
- BAST pada deal yang belum booking atau sudah batal kini ditolak (400).
- Void kuitansi pada deal yang sudah batal ditolak; void kuitansi pra-BAST sesudah BAST menaikkan piutang.
- Tahap KPR pada kontrak batal ditolak. Setoran/lapor pajak untuk deal batal ditolak.
- Penambahan pengguna dengan peran Super Admin kini hanya bisa oleh Super Admin.
- Data milik organisasi lain kini dijawab 404 di semua layar/API. Sales hanya melihat KPR dari deal miliknya.
- Pemilih "tambah bank/jenis izin baru" hanya berhasil untuk peran dengan izin `settings:manage` (peran lain memakai nilai itu hanya pada formulir yang sedang diisi).
- Pembatalan kontrak/reservasi kini menutup tugas, komisi/fee yang belum disetujui, KPR, kupon, dan pajak `pending`; komisi/fee/pajak yang sudah disetujui atau dibayar tetap (ditandai & dikirim ke Keuangan sebagai tugas). Pembatalan kontrak yang masih punya titipan biaya/invoice biaya terbuka butuh pengakuan penyetuju.
- Hapus-paksa deal sekarang juga menghapus giro, komplain, klaim garansi, fee marketing, faktur pajak, bukti kas; penerimaan/void/hapus yang bersamaan pada deal yang sama kini ANTRE (maks. 15 dtk, lalu 409). Menghapus kuitansi yang sama dua kali → yang kedua 404/409.
- Hapus lead/unit/proyek yang punya deal batal berjejak uang kini ditolak; hapus proyek ditolak bila masih ada stok/permintaan material/absensi/kas bon/aset. Lead yang punya deal aktif tidak bisa ditandai Hilang/Daur Ulang.
- Berkas HTML/SVG yang diunggah kini diunduh, bukan dibuka di peramban. Kode OTP portal terkunci setelah 5 salah. Formulir web publik dibatasi 60 kiriman/10 menit per IP (naikkan lewat env bila di belakang proxy dengan lonjakan sah).
- **Webhook (WH-01/02):** begitu rahasia sebuah kanal diisi (Meta/Google/TikTok lewat `PUT /api/webhooks/secrets/{kanal}`; WhatsApp lewat Pengaturan WhatsApp), permintaan tanpa tanda tangan sah ke kanal itu ditolak (401/403). **Isi rahasia yang sama di dashboard provider SEBELUM/bersamaan** agar lead asli tidak ikut ditolak. Kanal yang belum diisi tetap menerima (mode simulasi) dan muncul sebagai peringatan di `GET /api/webhooks/status`. Penolakan tidak lagi muncul di antrean 'Gagal Masuk'.
- **CTWA/CAPI (CT-01/02):** lead dari iklan Click-to-WhatsApp kini membawa `attribution.ctwa`; baris `conversion_events` untuk lead itu berbentuk Business Messaging (lihat `payload`). Isi `META_CAPI_TOKEN` + `META_CAPI_DATASET_ID` (atau `META_PIXEL_ID`) dan WABA ID agar benar-benar terkirim.

Risiko/catatan baru: status sementara `posting` pada transfer bisa tertinggal bila proses mati tepat di tengah (jurnalnya idempoten, jadi aman dicoba ulang oleh admin setelah status dipulihkan);
`funds_guard(flush_events=True)` mengosongkan antrean event sebelum melepas kunci (komisi, refund titipan) sehingga latensi permintaan ikut naik sedikit.

### 8.G-C — Master komponen biaya, rekonsiliasi luas, lintas-organisasi keuangan

| ID | Status | Perubahan | Tes |
|---|:-:|---|---|
| FN-02 | ✔ | Master `cost_components` / skema all-in / skema pencairan KPR **divalidasi di API** (`cost_master_rules.py`): nominal ≥ 0, persen 0–100, cara hitung & perlakuan dikenal, kode unik per org (diserialkan `mutex`), akun GL harus **nyata, aktif, bertipe sesuai** di CoA (beban=expense; titipan=liability bukan akun kendali; utang usaha=2-1100 karena pembayaran AP selalu mendebet 2-1100), butir skema hanya merujuk komponen yang ada & aktif (butir lama yang kemudian dinonaktifkan tidak memblokir simpan ulang), tanpa butir ganda, proyek skema harus di org. Komponen **nonaktif tidak ikut snapshot reservasi/amandemen baru** (`resolve_scheme` sebelumnya `include_inactive=True`); komponen bernilai negatif (master lama rusak) ditolak saat snapshot; harga pratinjau negatif ditolak. Opsi `sync_schemes=false` pada pembuatan komponen (bawaan tetap menempel ke semua skema). Akun GL tak sah tidak lagi bisa melahirkan tagihan AP yatim (FN-05 dari sumbernya) | `test_p0_komponen_biaya.py` |
| FN-12c | ✔ | `PUT /finance/config/tax`: tarif 0–100%, NPOPTKP ≥ 0 (dulu −5% / 500% / −1 tersimpan) | idem |
| FN-01 | ◐ | Banner tab "Komponen Biaya" (katalog `price_components`) diperbaiki jujur: *referensi, belum mengubah tagihan/jurnal*; kebijakan yang berlaku ada di tab Biaya All-in. **SSOT satu master = ⚖ keputusan pemilik** (dua master tetap ada) | — (teks UI) |
| G3 | ✔ | `/finance/reconcile` dari 7 → **12** pemeriksaan (`finance_audit_ext.py`): 1-1300 Piutang Usaha (sisa tagih AR pasca-BAST + denda belum lunas; rincian di `sources`), 2-1470 Titipan Biaya (Σ kuitansi biaya − Σ penyaluran), 1-2100 Aset Tetap (Σ harga perolehan belum dilepas), 1-2200 Akumulasi Penyusutan (Σ `asset_depreciations` aset belum dilepas), 2-2100 Utang Bank (pokok − pokok terbayar menurut jadwal). Mekanisme `indicator` (peringatan yang tidak menggagalkan `ok`; `indicators_off`) tersedia, **belum ada pemeriksaan yang memakainya** karena kelimanya hijau pada seed baru dan setelah suite penuh. Saldo sub-akun kas/bank sengaja tidak diperiksa (dihitung dari jurnal itu sendiri) | `test_p0_rekonsiliasi_luas.py` |
| AZ-KEU | ✔ | Lingkup org koleksi keuangan: ±50 endpoint (AR/deposit/kuitansi, AP, komisi, fee marketing, bukti transfer, faktur & bukti potong, pengajuan dana, kas bon, kas kecil, bank + pencocokan + rekonsiliasi, aset, pinjaman, rekap upah, invoice biaya) kini menjawab **404** (dulu 400 "tidak ditemukan"; `spr-compare` menjawab 200 kerangka kosong) lewat `org_scope.exists_in_org`; pembuatan tagihan AP/pengajuan dana/kas bon/aset/biaya kas kecil tidak lagi menerima `project_id`/`ap_bill_id` milik org lain; mutasi bank org B tidak bisa dicocokkan ke dokumen org A | `test_p0_lintas_org_keuangan.py` |

Perubahan perilaku yang akan terlihat pemakai:
- Menyimpan komponen biaya / skema all-in / skema pencairan KPR dengan angka tak wajar atau akun GL tak sah kini **ditolak 400** dengan alasan; komponen yang dinonaktifkan **hilang dari reservasi/amandemen berikutnya** (kontrak lama tidak berubah).
- Konfigurasi pajak di luar 0–100% ditolak. Lintas-org kini 404 (bukan 400) di endpoint keuangan.
- Rekonsiliasi menampilkan 5 baris baru; selisih pada baris itu menyalakan lampu merah dasbor Finance seperti 7 baris lama.

Butuh keputusan pemilik (tidak dikerjakan): FN-01 (satu master komponen biaya?), FN-11 (ganti skema kontrak ke KPR tanpa menambah komponen KPR-only — butuh aturan hitung ulang), FN-12a/b/d–f (NPOPTKP per proyek, satu sumber tarif BPHTB, BANK_FEE dari plafon, NJOP, PPh final 1%), batas wajar nominal komponen (dipasang Rp 1 triliun sebagai pagar kewajaran, ubah bila perlu), izin `finance:update` untuk peran staf pada konfigurasi pajak.
Catatan teknis: pemeriksaan 2-1470 menjumlahkan **semua** kuitansi biaya; bila kelak pembatalan deal (perlakuan titipan pada deal batal = keputusan pemilik) menjurnal 2-1470, catatan subledgernya (`cost_receipts`/`cost_disbursements`) harus ikut diubah agar pemeriksaan tetap hijau.
### 8.G-B Mesin status & konkurensi ("set status tanpa syarat status", baca-lalu-tulis)

Pola perbaikan: **tabel transisi status** (dict) per entitas di modulnya + **CAS** (`idempotency.transition/cas/reserved/mutex`) atas status yang dibaca.
Transisi tak sah → 400 (pesan menyebut status sekarang); yang kalah balapan → 409. Tes: `test_p0_status_konkurensi.py`, `_2.py`, `_3.py` (36 tes, **semuanya merah di kode lama 6f5b6f2, hijau di kode baru**).

| ID | Status | Perubahan | Tabel transisi / alat |
|---|:-:|---|---|
| PK3-18 | ✔ | Permintaan material (setuju/tolak/keluarkan), klaim garansi (terima/tolak/selesai/periksa/tutup), item jadwal bangun (verifikasi/kembalikan/override/ajukan), komplain (selesaikan/tugaskan), rekap upah (ajukan/setuju/tolak), PO (batal ‖ setuju): satu pemenang, yang kalah 409 | `REQ_TRANSITIONS`, `warranty_engine.TRANSITIONS`, `ITEM_TRANSITIONS`, `complaints.TRANSITIONS`, `PAYROLL_TRANSITIONS`, `PO_TRANSITIONS` |
| PK3-10 | ✔ | Change order: CO diklaim `draft→approved` (CAS) lalu nilai SPK ditambah `$inc` bersyarat; 3 CO +Rp 10 jt paralel → SPK +Rp 30 jt (dulu +Rp 10 jt); setuju ganda/setuju ‖ tolak → satu pemenang | `CO_TRANSITIONS`, `_apply_value_delta` |
| PK3-16 | ✔ | Work Hub: `PUT status=done` tidak lagi melewati bukti/verifikasi; tugas `cancelled`/`done` tidak bisa di-complete/snooze/dibuka; `complete` ×3 → sekali | `workhub.TASK_TRANSITIONS`, `can_move` |
| PK3-17 | ✔ | Izin: `approved` hanya dari `submitted`; `renew` hanya dari `approved`/`expired`; `alerts/scan` paralel tidak menggandakan notifikasi (penanda harian diklaim atomik) | `PERMIT_TRANSITIONS`, `RENEWABLE` |
| PK3-20 | ✔ | Fee marketing ganda (jalur manual & otomatis mitra memakai kunci yang sama) + indeks unik parsial `uq_mfee_open_dedup` (status terbuka). Bila data lama sudah berisi kembaran, indeks dilaporkan sebagai `conflict` saat start (tidak menggagalkan, tidak ada data dihapus) dan penjagaan aplikasi tetap berlaku | `marketing_fee.fee_lock`, `indexes.PARTIAL_EXPR` |
| PK3-21 | ✔ | Impor semua data: sesi diklaim `open→committing` (CAS); `committed` tidak bisa di-commit ulang; gagal di tengah → `failed` (pulihkan dari snapshot). Impor biaya iklan: klaim `preview→committing` | `data_mgmt_full_session.commit`, `ads_router.commit_import` |
| PK3-22 | ✔ | Handler global `DuplicateKeyError → 409` (dulu 500); nomor GRN diambil SESUDAH PO diklaim (nomor tidak hangus); transfer stok mengambil nomor sesudah cek stok | `server.py` |
| PK3-23 | ✔ | Komplain hanya maju (`resolved` final); janji temu `done/cancelled` final, `no_show` boleh dijadwal ulang; janji temu identik (lead + waktu) ditolak 409 | `complaints.TRANSITIONS`, `APPT_TRANSITIONS` |
| FZ-06 / PG-04 | ✔ | Retur GRN dikunci per GRN + per material, GRN/PO dibaca ulang di dalam kunci, PO diklaim CAS; keluarkan permintaan & transfer antar proyek memakai kunci stok yang sama dengan txn manual/opname | `procurement_extra.create_return`, `stock_control.transfer` |
| PG-05 | ✔ | Retur ditolak bila melebihi stok yang ada dan bila PO `cancelled` (PO batal tidak dihidupkan) | idem |
| PG-06 | ◐ | Batal PO ditolak bila PO sudah menerima barang (`received_value>0`), punya tagihan aktif, atau berstatus diterima sebagian. **Tagihan lama atas PO yang sudah terlanjur batal tetap bisa disetujui/dibayar** (jalur AP bukan bagian stream ini) | `cancel_po` |
| PG-21 | ✔ | "Pemakaian vs RAB" tidak lagi menghitung transfer/retur sebagai pemakaian; daftar material memakai angka yang dihitung ulang (sama dengan layar anggaran) | `_consumed_qty` |
| FZ-05 | ✔ | `book` menurunkan `units.payment_status` dari AR yang sebenarnya (`paid_off`/`partial`/`booking_fee`) | `deals_router.book_deal` |

Perubahan perilaku yang akan terlihat pemakai:
- Dua orang menekan aksi pemutus yang sama/berlawanan (setuju/tolak, terima/tolak, verifikasi/kembalikan, selesaikan/tugaskan) → yang kedua melihat 409 "baru saja diubah oleh proses lain".
- Status izin tidak bisa loncat (mis. ditolak → disetujui langsung); perpanjangan hanya untuk izin yang sudah disetujui. Komplain/janji temu yang sudah selesai tidak bisa "dimundurkan".
- Tugas Work Hub yang butuh bukti tidak bisa ditandai selesai lewat PUT status; tugas selesai/batal tidak bisa ditunda/diselesaikan lagi.
- PO yang sudah menerima barang tidak bisa dibatalkan (lakukan retur dulu); retur tidak bisa melebihi stok yang ada.
- Permintaan material memiliki status sementara `issuing` selama stok dikeluarkan (bisa tertinggal bila proses mati tepat di tengah; Conflict-nya jelas, admin dapat memulihkannya ke `approved`).
- Janji temu dengan lead + waktu yang sama ditolak (409). Sesi impor yang sudah `committed` tidak bisa di-commit lagi.

### 8.H-A — Sisa siklus hidup deal (batal/kedaluwarsa/hapus) & sisa PG-06 (kode H-A)

Pola perbaikan: **satu penutup bersama** (`deal_cancel_cleanup.close_deal_dependents`) dipakai TIGA jalur — batal satu-klik, batal formal, kedaluwarsa reservasi — dan
**gerbang biaya yang sama** (`cancellation_costs`) di semua jalur batal. Tidak ada jurnal baru; perlakuan akuntansi titipan/akrual pada deal batal tetap ⚖ keputusan pemilik.
Tes: `test_p0_sisa_siklus.py` (12) + `test_p0_sisa_siklus_2.py` (9) — **seluruhnya merah di kode lama 4582e8a, hijau di kode baru**.

| ID | Status | Perubahan | Tes |
|---|:-:|---|---|
| PK3-08 (sisa) kedaluwarsa | ✔ | `deal_cancel.expire` (← `reservation_expiry_sweeper`) kini memanggil penutup bersama: komisi/fee belum disetujui → batal, KPR → batal, kupon dilepas, pajak pending → batal, tugas ditutup, yang sudah disetujui/dibayar ditandai tindak lanjut Keuangan (tanpa jurnal balik); unit tetap dilepas. Uang biaya yang menggantung (titipan 2-1470 / invoice biaya terbuka) dicatat di tugas tindak lanjut Keuangan. Satu deal bermasalah tidak lagi menghentikan seluruh sapuan | `test_kedaluwarsa_*` |
| PK3-08 (sisa) janji temu | ✔ | Penutup bersama membatalkan janji temu **mendatang** (`scheduled`) milik lead deal (+ tugas survei yang lahir darinya) bila lead tak punya deal hidup lain; `done`, `no_show`, dan yang sudah lewat tidak disentuh. Berlaku di ketiga jalur | `test_batal_manual_*`, `test_batal_formal_*`, `test_kedaluwarsa_membatalkan_*`, `test_janji_temu_lead_dengan_deal_hidup_lain_*` |
| PK3-08 (sisa) dokumen draft | ✔ | Dokumen `draft` terikat deal/kontrak batal → `status=cancelled` + penanda (`cancelled_at/by`, `cancel_reason`, `status_before_cancel`); final/ditandatangani dan BAP pembatalan tidak disentuh; tidak ada yang dihapus. Status baru `cancelled` masuk kosakata `document_status` (tanpa SLA) | idem, `test_dokumen_draft_batal_*` |
| FN-03 (sisa) gerbang batal satu-klik | ✔ | `POST /deals/{id}/cancel` menolak (400) bila deal masih punya titipan biaya 2-1470 > 0 atau invoice biaya terbuka, kecuali `acknowledge_costs=true` + `cost_note` ≥ 10 huruf; dicatat di `deals.cancel_cost_ack` dan audit log. Memakai `cancellation_costs.holds_of_deal/assert_ack` (tanpa menyalin). `cancel-preview` memuat `cost_holds` + `requires_cost_ack` | `test_batal_satu_klik_*` |
| FN-03 (sisa) uang biaya sesudah batal | ✔ | `POST /cost-invoices/{id}/pay` dan `POST /contracts/{id}/cost-disbursements` pada deal BATAL (`deal_state.is_cancelled`, atau kedaluwarsa/kontrak batal) ditolak 400; terobosan hanya `override_cancelled=true` + `override_reason` ≥ 10 huruf oleh pemegang `finance:approve` — dicatat di kuitansi/penyaluran (`cancel_override`) dan audit (`override_cancelled`). Dicek di bawah mutex deal yang sama dengan pembatalan (tak ada celah cek-lalu-bayar). Tidak ada jurnal tambahan | `test_bayar_dan_salur_*`, `test_terobosan_*`, `test_uang_biaya_ditolak_juga_*` |
| PG-06 (sisa) | ✔ | Tagihan AP atas PO `cancelled` **tidak bisa disetujui** (`approve_ap_bill`) atau **dibayar** (`pay_ap_bill`, termasuk `pay-withholding` dan pencairan pengajuan dana); tagihan baru atas PO batal ditolak dengan pesan jelas. Tagihan lama TIDAK dihapus: daftar AP (`GET /finance/ap/bills`) memberi `po_cancelled` + filter `?po_cancelled=true|false`, detail tagihan, `GET /procurement/pos/{id}` dan `/threeway` ikut bertanda. Pengecualian sadar: pembayaran dari **rekonsiliasi bank** (`skip_funds_check`, uang sudah benar-benar keluar) tetap dicatat | `test_tagihan_*po_batal*` |
| PK3-09 (sisa) hapus-paksa | ✔ | `wa_reminders` (log kirim pengingat; tak berkunci `deal_id`) ikut terhapus lewat `entity_type/entity_id` tagihan AR / booking fee / BAST dan `dedup_key` peringatan tunggakan. Tes pemindai SEMUA koleksi menemukan kebocoran lain yang kini ditutup: notifikasi/aktivitas/tugas/peristiwa yang menunjuk dokumen turunan (mis. "Pengajuan marketing fee", "Pembatalan menunggu keputusan"), dan `customers.converted_from_deal` | `test_hapus_paksa_*` |

Perubahan perilaku yang akan terlihat pemakai:
- Batal satu-klik pada deal yang masih punya titipan/invoice biaya kini **400** sampai pengakuan biaya diisi (frontend perlu kotak pengakuan di dialog batal; `cancel-preview.cost_holds` menyediakan datanya).
- Bayar invoice biaya / salurkan titipan pada deal batal **400** (terobosan: `override_cancelled` + `override_reason`, hanya `finance:approve`).
- Tagihan AP atas PO batal tidak bisa disetujui/dibayar; di daftar AP muncul `po_cancelled` (frontend belum menampilkan label/filter).
- Dokumen draft dan janji temu mendatang milik deal batal/kedaluwarsa otomatis `cancelled`; status dokumen baru `cancelled` (label "Dibatalkan").

Butuh keputusan pemilik / belum dikerjakan: perlakuan akuntansi titipan 2-1470 & invoice biaya pada deal batal (⚖, hanya diakui+dicatat); reservasi kedaluwarsa yang booking fee-nya sudah dibayar (sweeper tetap melepas unit tanpa refund — ⚖);
`record_developer_expense` (beban developer-borne) pada deal batal belum digerbang; janji temu untuk lead yang masih punya deal hidup lain sengaja dibiarkan.
### 8.H-B — Sisa mesin status (P1/P7), dedup manual (P12), `money_op` (G1)

Pola perbaikan sama dengan G-B: tabel transisi status (dict) + `transition()/cas()/reserved()` atas status yang dibaca; yang kalah balapan → 409, transisi tak sah → 400;
router tidak boleh menelan `Conflict` lewat `except ValueError → 400`. Tes: `test_p0_sisa_status.py`, `test_p0_dedup_manual.py`, `test_p0_money_op.py`.

| ID | Status | Perubahan | Alat |
|---|:-:|---|---|
| H-B1 | ✔ | `POST /deals/{id}/pricing-approval`: setuju ‖ tolak ‖ setuju ×N → satu pemenang (dulu semua 200, yang terakhir menimpa) | `transition(deals, pricing_approval.state=pending)` |
| H-B2 | ✔ | Kas bon: setuju / tolak / batal memakai `ADVANCE_TRANSITIONS` + `_move`; cairkan ‖ tolak tidak lagi menimpa `disbursing` (pemohon tidak diberi tahu "ditolak" padahal uang keluar) | `petty_cash.ADVANCE_TRANSITIONS`, `transition` |
| H-B3 | ✔ | Termin subkon: opname (lumpsum & per item) hanya dari `submitted`; tolak memakai status yang dibaca (dulu tolak menimpa `approving` lalu persetujuan menulis `approved` → pekerjaan dilepas ke daftar "siap ditagih" padahal tagihan AP sudah lahir) | `cas(progress_claims, status)` |
| H-B4 | ✔ | Penawaran: putusan diskon sekali; kirim WA sekali (kunci anti-ganda per penawaran); konversi mengklaim penawaran `→ converting` SEBELUM kupon/unit disentuh (kirim/revisi tidak lagi menimpa `converted`); revisi tidak men-supersede penawaran yang sudah/sedang dikonversi | `QUOTE_TRANSITIONS`, `transition`, `reserved`, `once` |
| H-B5 | ✔ | Amandemen all-in: pengajuan ×N → satu `pending` (kunci per kontrak + indeks unik parsial `uq_allin_amend_pending`); putusan sekali (riwayat biaya kontrak satu entri; status akhir = putusan pemenang) | `mutex`, `reserved` |
| H-B6 | ✔ | `to-po`: kunci per permintaan, permintaan dibaca ULANG di dalam kunci (4 pemanggilan paralel dulu → 4 PO + 4 nomor PO), `qty_po` ditulis per baris (tidak menimpa `qty_issued`) | `mutex` |
| H-B7 | ✔ | Kas & Bank: `set_default` / nonaktifkan rekening diserialkan per jenis (tepat satu default; tidak ada rekening nonaktif yang berstatus default); pembuatan sub-akun GL diserialkan per jenis (dulu dua rekening serentak → kode sama, 409, rekening tanpa akun GL); `ensure_setup` & bootstrap rekening bawaan diserialkan | `mutex` |
| H-B8 | ✔ | Aset tetap: penyusutan dan pelepasan diserialkan PER ASET dan aset dibaca ulang di dalam kunci (penyusutan ‖ pelepasan tidak lagi menjurnal akumulasi basi; penyusutan ×N tidak gugur di tengah putaran) | `mutex` per aset |
| H-B9 | ✔ | Denda keterlambatan: tagih/ringankan di bawah `deal_money` (dulu `_recalc` menulis ulang seluruh `items` tagihan dari salinan basi → pembayaran yang masuk di sela-sela hilang dari AR) | `deal_money` |
| H-B10 | ✔ | Batal tagihan booking fee: status & `paid` yang dibaca masuk ke filter (pembayaran yang masuk di sela-sela tidak ditimpa `cancelled`); giro (kliring/tolak/batal): sudah dikunci per giro (**positif palsu**) — ditambah syarat `status=received` di filter update | `expect_of` |
| H-B11 | ✔ | Impor mutasi bank: impor sungguhan diserialkan per rekening (dulu sebagian 409 di tengah putaran); `generate_units`, impor lead: tabrakan indeks unik → dilewati, bukan menggagalkan seluruh putaran; harga unit tidak bisa diubah bila unit baru saja booked/terjual | `mutex`, `DuplicateKeyError` per baris |
| H-B12 | ✔ | P12: pembeli (kunci identitas NIK/HP/email), lead (kunci nomor, pesan "sudah terdaftar" tetap jelas), tugas (`auto_create_task` & `workhub.create_task` satu kunci `task.src:` + indeks unik parsial `uq_task_open_source` untuk tugas terbuka), material kembar tujuan transfer, kode material kembar → 400 | `mutex`, `PARTIAL_EXPR` |
| H-B13 | ✔ | **`money_op` (G1)** `backend/money_op.py`: `once → deal_money → funds_guard → blok`, urutan tetap. Dipakai `fixed_assets.create_asset`, `marketing_fee.pay_fee`, `labor_engine.pay_payroll`, `fund_requests.disburse`, `petty_cash.disburse_advance/settle_advance` — tanpa perubahan perilaku | `money_op` |
| H-B14 | ✔ | Sapuan: pola baru `P3b_assert_funds_langsung` (fungsi di luar `cash_bank.py`/`money_op.py` yang memanggil `assert_funds`: 4 sekarang — `subcon_finance.pay_advance`, `loans.pay_installment`, `finance_ap.pay_ap_bill`, `allin_engine.disburse_titipan`); sapuan mengenali wrapper pemegang kunci (`*_locked`/`*_unlocked`/`*_claimed` yang dipanggil fungsi ber-`GUARDS`) dan `funds_guard/deal_money/money_op` sebagai penjaga | `scripts/pattern_sweep.py` |

Positif palsu / tidak diubah (telaah): `pdc_engine` (dikunci per giro), `fixed_assets.run_depreciation` ganda (dijaga indeks `uq_asset_depr` + `source_event` jurnal; kini bersih tanpa 409), `finance_reports.send_reminder` (hanya cap waktu pengingat), `routers/*update_*` (CRUD "terakhir menang" tanpa efek uang/stok), `warranty_engine` (sudah G-B). ⚖ tidak ada keputusan bisnis baru.

Perubahan perilaku yang akan terlihat pemakai:
- Dua orang menekan aksi pemutus yang sama pada potongan reservasi, kas bon, termin subkon, putusan diskon penawaran, amandemen all-in → yang kedua melihat 409 "baru saja diubah oleh proses lain".
- Mengirim penawaran dua kali dalam ±15 detik → yang kedua 409 (anti kirim WA ganda). Konversi penawaran memakai status sementara `converting` (dipulihkan otomatis bila gagal; bisa tertinggal bila proses mati tepat di tengah).
- Penawaran berstatus `superseded`/`rejected` tidak bisa dikonversi menjadi reservasi.
- Pembuat PO dari permintaan ke-2 yang bersamaan → 409/400 (tidak ada PO kembar). Pembuatan lead/pembeli dengan kunci identitas yang sama serentak → satu berhasil, sisanya 409.
- Aset tetap yang sedang disusutkan/dilepas oleh proses lain → antre (maks. 15 dtk) lalu 409. Mengubah harga unit yang baru booked → 409.
- Material dengan kode kembar yang dibuat serentak dijawab 400 (bukan 409 generik). Tugas otomatis kembar (source_event sama, status terbuka) kini mustahil.

Verifikasi H-B (kode final, DB baru): suite penuh `tests/p0` **609 lulus, 1 dilewati**; satu kegagalan awal (`test_impor_commit_serentak...`, galat `'BACKUP_DIR'`) murni lingkungan (server uji dimulai tanpa env itu) dan lulus setelah backend dimulai ulang dengan `srv.sh` terbaru. Tes baru: 23 (`test_p0_sisa_status.py`) + 12 (`test_p0_dedup_manual.py`) + 10 (`test_p0_money_op.py`). Di kode lama (4582e8a, server+DB terpisah): 16 dari 23 + 9 dari 12 (hingga 11 pada sebagian putaran) + 7 dari 10 merah; sisanya hijau (dijaga indeks/kontrol) atau soak probabilistik (lihat laporan). Sapuan: P1 165→149, P7 85→65, P12 104→90 (dari ini P1 165→157, P7 85→71, P12 104→104 murni dari perubahan kode; selisihnya karena sapuan kini mengenali wrapper pemegang kunci), P3b baru = 4 (baseline oleh orkestrator). Gerbang kepatuhan: hanya 3 pelanggaran lama.
### 8.H-D Posting Profile — Fase 1–2 (katalog + profil v0 + dry-run + resolver BAYANGAN), tanpa mengubah buku besar

Rancangan: `03_AKUNTANSI_5_KEBUTUHAN_KONFIGURASI.md` (§2.8 urutan 1–2). **Tidak ada jurnal yang berubah**: kode lama (`gl_engine._gl_*`, dst.) tetap yang memposting; profil v0 hanya dibandingkan dengan jurnal yang terbit.

| Bagian | Status | Isi |
|---|:-:|---|
| Katalog + peran akun + profil v0 | ✔ | `posting_profile_v0.py` (data deklaratif: 40 peran akun 1:1 dengan CoA standar; 49 peristiwa) + `posting_profile.py` (evaluator AST terbatas, tanpa eval). Kode akun hanya ada di tabel peran; baris peristiwa memakai nama peran. Cacat yang diketahui (GL-01/02/04/11/16/17/24 …) **disalin apa adanya** dan ditandai `defects`. |
| Cakupan jujur | ◐ | **24 dari 49 peristiwa `covered: true`** (49%) (penerimaan, void penerimaan, titipan masuk/pakai/kembali, BAST+HPP, denda & keringanan, keputusan & refund pembatalan, AP setuju/bayar/batal bayar, komisi, fee marketing, pajak akrual/setor, kas bon cair/pertanggungjawaban, aset tetap perolehan/penyusutan/pelepasan). **25 `covered: false`** (tiap peristiwa memuat `why_not`, tanpa baris): booking fee hangus, uang muka & retensi subkon, pengajuan dana, kas kecil, upah harian, pinjaman, transfer/saldo awal/biaya bank/jasa giro/batal cocok bank, all-in (4), giro (3 termasuk cair tanpa deal), tutup/buka tahun, jurnal manual. |
| Dry-run read-only | ✔ | `POST /api/gl/posting-profile/dry-run` {event, inputs} → jurnal (akun, nama, D/K, nilai), seimbang?, akun ada/aktif/tipe cocok/sub-akun kas, peringatan (cacat yang disalin). `GET /api/gl/posting-profile/catalog` (+ status peran di CoA org, cakupan). Izin `gl:view`. Tidak ada rute tulis: profil tak bisa diubah lewat API pada fase ini (metode lain → 405). |
| Resolver bayangan | ✔ | `posting_shadow.py`, dipanggil dari `gl_engine.post_journal` SESUDAH insert. Bawaan **MATI**; hidup hanya bila env `POSTING_SHADOW=1`. Mati = nol kueri. Hidup = 1 `update_one` ($inc) statistik per jurnal peristiwa `covered` + 1 upsert hanya saat ada SELISIH (koleksi `posting_shadow_diffs`: org, journal, source_event, peristiwa, selisih per (sisi, akun), masukan, waktu; `posting_shadow_stats`). Tidak pernah mengubah jurnal / melempar galat (galat dicatat lewat logger). `GET /api/gl/posting-profile/shadow-report` (ringkasan per peristiwa + selisih terbaru + cakupan jurnal 30 hari per `source_type`) dan `GET .../verify/{jurnal}` (bandingkan satu jurnal tersimpan). |
| Cap jejak + dimensi (Fase 3 sebagian) | ◐ | Jurnal BARU mendapat `profile_event` (+`profile_version: "v0"` bila dicakup) dan `dimensions` {`deal_id` dari `source_deal_id`, `cash_account_id`/`cash_account_ids` dari sub-akun kas/bank}. Tanpa kueri, tanpa backfill, laporan tak berubah. **`project_id`/`unit_id` belum diisi** (butuh +1 kueri per jurnal & keputusan backfill) — ⚖. |
| Tes | ✔ | `test_p0_posting_profile.py` (18) + `_2.py` (37) = 55 tes: API katalog/dry-run/izin/read-only; evaluator aman; pembanding mendeteksi jurnal salah (mutasi profil & mutasi kode lama keduanya merah); handler `_gl_*` NYATA pada org sementara (semua cabang: split piutang/denda, tipe PO × retensi × potongan × akrual, WIP kurang, kelebihan bayar); 11 skenario API nyata dengan `dry-run` bermasukan dari dokumen sumber + `verify` + `posting_shadow_diffs` kosong. **Seluruhnya merah di kode lama 4582e8a** (endpoint/modul belum ada), hijau di kode baru. |

Temuan ekuivalensi: **tidak ada selisih** antara profil v0 dan kode lama pada seluruh skenario di atas (24 peristiwa). Bonus: suite penuh `tests/p0` (620 lulus) dijalankan dengan `POSTING_SHADOW=1` pada DB baru — 24 peristiwa dicek (408 jurnal), `posting_shadow_diffs` = 0. Satu keterbatasan metodologi: untuk modul di luar `gl_engine` (kas bon, fee, aset, pembatalan, void, denda) resolver memakai masukan yang DITURUNKAN dari baris jurnal itu sendiri (mode `derived`): ia memeriksa akun/sisi/rumus, tetapi tidak bisa menguji kondisi yang hanya ada di dokumen sumber (mis. kategori kas bon, tipe PO). Untuk itu skenario API menyuplai masukan dari dokumen sumber lewat dry-run; handler `gl_engine` mengirim petunjuk eksplisit dari dokumennya (mode `hint`).

Langkah berikut (belum dikerjakan): ubah satu aliran per rilis memakai profil dengan feature-flag (Fase 4), maker-checker + UI editor/uji coba (Fase 5), profil koreksi (PPN, pasca-BAST, denda) berlaku ke depan (Fase 6). ⚖ Keputusan pemilik yang tetap terbuka: PPN keluaran, kapitalisasi komisi, perlakuan titipan/akrual pada deal batal, WIP per proyek — v0 sengaja tidak menyentuhnya.
### 8.H-C — Layar Keamanan Webhook + uji peramban atas layar yang berubah di ronde perbaikan

Frontend saja (plus 4 bidang tambahan read-only di `GET /api/webhooks/status`). Skrip uji peramban Playwright yang bisa diulang ada di `scripts/ui/` (lihat `scripts/ui/README.md`).

| Butir | Status | Isi |
|---|:-:|---|
| Layar "Keamanan Webhook" (Pusat Konfigurasi, tab `?tab=webhooks`) | ✔ | Tabel kanal (Meta Lead, WhatsApp, Google, TikTok) dengan lencana Aman/Belum aman, sumber rahasia (sistem/ENV/belum), statistik penolakan, peringatan; isi/ganti rahasia (input password, kolom selalu kosong, nilai lama tak pernah tampil, nama ENV alternatif), cabut dengan konfirmasi (pilih rahasia/verify token), catatan operasional ("rahasia yang sama harus dipasang di dashboard penyedia"). Ubah hanya untuk `settings:manage`; WhatsApp diarahkan ke tab Integrasi WhatsApp. Komponen: `components/config/Webhook*.js`, testIds `WEBHOOK_SEC`. |
| API status | ✔ | `GET /webhooks/status` kini juga memuat `env_secret`/`env_verify` (NAMA variabel, bukan nilai), `verify_token_source`, `managed_via`. Tes `test_p0_webhook_status_ui.py`. |
| Perbaikan UI temuan uji peramban | ✔ | Lihat tabel temuan di laporan stream H-C: tombol yang pasti ditolak server tidak lagi ditawarkan (batalkan PO diterima sebagian, "Buka Kembali" komplain selesai, void kuitansi deal batal, blokir unit dalam transaksi aktif, status izin yang tak boleh dituju), pengakuan biaya pada pembatalan menahan tombol setujui, layar menyegarkan diri sesudah 400/409 (permintaan material, izin, komplain, PO, unit, transfer kas). |

Perubahan perilaku yang akan terlihat pemakai:
- Pusat Konfigurasi punya tab baru "Keamanan Webhook"; owner/super admin dapat mengisi, mengganti, dan mencabut rahasia webhook dari layar.
- Dialog pembatalan (formal dan reservasi satu-klik) menahan tombol sampai titipan/invoice biaya yang menggantung diakui beserta catatan penanganan.
- Sesudah galat 400/409 pada aksi status, daftar/lembar dimuat ulang sehingga tombol yang sudah basi hilang.

### 8.I — Keputusan pemilik terkumpul (16 keputusan) → rancangan konfigurasi
Seluruh keputusan §4 telah dijawab pemilik; tiap jawaban menjadi **nilai bawaan pengaturan** (bukan perilaku kaku) di Pusat Konfigurasi, dengan opsi lain tetap
dapat dipilih (override organisasi/proyek/kontrak). Rincian tabel keputusan→key→opsi, risiko, dan gelombang pengerjaan W0–W3 ada di
`docs/audit/12_KEPUTUSAN_PEMILIK_DAN_RANCANGAN_KONFIGURASI.md`. **W0 selesai** (resolver kebijakan, level penimpaan, opsi "belum tersedia", UI tingkat proyek, kunci percontohan `deposit.on_cancelled_deal`) — lihat doc 12 §6. W1–W3 belum.

### 8.W1-W1A — Pemicu lead→pembeli (#7) & reservasi kedaluwarsa dengan booking fee terbayar (#13)

Kode agen **W1A** (basis W0 `4c940d9`). Tiga kunci baru + satu kunci lama yang diubah bawaannya; semua dibaca lewat `policy.resolve(..., project_id=)`.

| Kunci | Tipe / bawaan | Opsi | Override | `unavailable` |
|---|---|---|:-:|---|
| `lead.won_trigger` (kunci LAMA; bawaan diubah dari `spr_signed`) | enum / **`booking_fee_verified`** | `booking_fee_verified` · `spr_signed` · `ppjb_signed` · `ajb_signed` | org + **proyek** (baru) | tidak ada — keempatnya berperilaku |
| `reservation.expiry.paid_booking_fee` | enum / **`perpanjang`** | `perpanjang` · `antrean_refund` · `hangus` | org + proyek | tidak ada |
| `reservation.expiry.extend_days` | int 1–90 / 7 | — | org + proyek | — |
| `reservation.expiry.max_extensions` | int 0–12 / 2 | — | org + proyek | — |

**#7 — apa yang berubah.** `customer_convert.py` (dua pembaca: `preview` dan `auto_convert_if_configured`) membaca pemicu untuk PROYEK deal; `engine._h_convert_customer` memetakan peristiwa →
pemicu lewat `customer_convert.deal_and_trigger_of`: `deal.booked`→booking, `document.signed` SPR*/PPJB*/AJB* → `*_signed`, `deal.ppjb`/`deal.ajb` (tahap legal kontrak; konversinya idempoten).
**Cacat lama yang ikut tertutup:** pemicu `spr_signed` TIDAK PERNAH jalan — penangan membaca `ev["payload"]` padahal `emit()` menyimpan muatan di `ev["data"]`; `ppjb_signed`/`ajb_signed` tak punya peristiwa pemicu sama sekali.
Pratinjau konversi memuat `trigger` + `trigger_met` dan catatan umum bila peristiwa pemicu belum terjadi (konversi MANUAL tetap sah kapan pun — keputusan sadar petugas).
Bila pemicu benar tetapi konversi tertahan (data diri kosong, NIK bentrok, dst.) sales kini diberi TUGAS (`convert.auto_blocked:<deal>`, sekali; ditutup saat konversi berhasil) — dulu hanya baris log.
**Pengaman KT-21:** deal yang skemanya hanya BAWAAN sistem (`scheme_explicit` false) TIDAK dikonversi otomatis (jenis kontrak/varian SPR tidak ditebak); sales diberi tugas lalu memilih skema di 'Jadikan Pembeli'.
`deal_cancel._close_tasks_and_rewind_lead`: lead `won` hasil konversi otomatis ikut mundur ke `nurturing` bila reservasi dibatalkan/kedaluwarsa tanpa deal hidup lain (batal satu klik hanya mungkin sebelum ada pembayaran termin).

**Perubahan perilaku BAWAAN bagi org yang belum menimpa `lead.won_trigger`** (mereka ikut bawaan baru): (1) tiap booking yang dikonfirmasi (skema dipilih sales) langsung melahirkan pembeli + kontrak draft + jadwal AR + (KPR) pengajuan KPR +
tugas KYC/biaya, dan lead langsung `won` — dulu menunggu klik 'Jadikan Pembeli'; (2) NIK/NPWP tidak lagi diketik saat konversi (tugas 'Lengkapi berkas & KYC' dari konversi mengisinya); (3) batal satu klik deal yang booking fee-nya sudah dialihkan ke piutang
kini menunjuk Pembatalan Kontrak formal (kontrak sudah ada), bukan 'Jadikan Pembeli dulu'; (4) `spr_signed` yang dulu tak berfungsi kini berfungsi bila dipilih. Mengembalikan perilaku lama: setel `lead.won_trigger=spr_signed` (org atau per proyek).

**#13 — apa yang berubah.** `engine_sweepers.reservation_expiry_sweeper` kini memanggil `reservation_expiry.handle` (di bawah mutex uang per-deal `deal_money`). "Booking fee terbayar" = Σ kuitansi `booking_fee` bukan-void − Σ (refund + hangus) — bukan penanda `booking_fee_status`.
Tanpa booking fee terbayar: kedaluwarsa & dilepas persis seperti sebelumnya (`deal_cancel.expire`).
`perpanjang`: `reserved_until` += `extend_days` (dihitung dari yang lebih akhir antara jatuh tempo lama dan sekarang → putaran berikutnya tak memperpanjang lagi); hitungan di `deals.reservation_extensions` + `reservation_extension_log` (dengan `policy_snapshot`);
CAS (`idempotency.transition`) pada `reserved_until`+hitungan → dua putaran/dua worker tidak bisa memperpanjang dua kali; notifikasi + tugas ke sales (pemilik deal) dan Keuangan. Setelah `max_extensions` habis: unit TETAP ditahan, tugas tindak lanjut sales+Keuangan dibuat SEKALI
(penanda `deals.expiry_hold`), berulang-ulang sapuan tak membuat apa pun lagi; manusia memutuskan lewat jalur batal yang ada.
`antrean_refund`: unit dilepas lewat jalur yang sama (termasuk `deal_cancel_cleanup.close_deal_dependents`); uang TETAP titipan 2-1450 (tanpa jurnal baru); tugas + notifikasi refund untuk Keuangan (`deal.expiry_refund:<deal>`), yang mengeksekusi lewat `POST /booking-fee/deals/{id}/refund` yang sudah ada.
`hangus`: unit dilepas lalu `booking_fee.refund(finalize=True)` (jalur hangus yang sudah ada: Dr 2-1450 / Cr 4-1200, idempoten lewat `source_event`); bila langkah itu gagal, uang tetap titipan dan Keuangan diberi tugas refund.
Hasil tercatat di `deals.expiry_paid_fee` (mode, hasil, nilai, `policy_snapshot`).

**Perubahan perilaku BAWAAN #13:** reservasi kedaluwarsa dengan booking fee terbayar tidak lagi dilepas diam-diam: diperpanjang 7 hari (maks. 2×), lalu unit tertahan + tugas. ⚖ `hangus` memindahkan uang pembeli menjadi pendapatan tanpa keputusan manusia saat itu
(sistem tidak memeriksa klausul SPR) — hanya berlaku bila org/proyek memilihnya. ⚖ Pengaman KT-21 di atas dan mundurnya lead `won` pada batal satu klik adalah keputusan SAFE-DEFAULT agen, bukan jawaban pemilik.

**Keterbatasan jujur:** kontrak/SPR/PPJB/AJB resmi lahir DARI kontrak, jadi pemicu `spr_signed`/`ppjb_signed`/`ajb_signed` hanya bisa menjalankan konversi otomatis untuk dokumen yang ditandatangani SEBELUM kontrak ada (jalur dokumen lama) — pada alur resmi
kontrak sudah ada lebih dulu dan konversinya idempoten (tidak ada yang digandakan). Tampilan deal belum menampilkan hitungan perpanjangan (hanya notifikasi/tugas).

Tes: `test_w1a_won_trigger.py` (15) dan `test_w1a_kedaluwarsa_bf.py` (13); tes lama yang berasumsi konversi MANUAL kini menyetel `lead.won_trigger=spr_signed` eksplisit (`pemicu_spr` di `test_p0_kontrak.py`: KT-01/02/12/17/21; PK3-19 pada proyek ujinya). Uji peramban `scripts/ui/w1a_kebijakan.js` (22 pemeriksaan) + `w0_kebijakan.js` disesuaikan (jumlah aturan ber-level proyek dibandingkan dengan API).
Merah di kode lama `4c940d9`: 14 dari 15 (#7) dan 10 dari 13 (#13); yang hijau di kode lama adalah bukti "tidak berubah" (tanpa booking fee terbayar tetap kedaluwarsa), fungsi SSOT (in-process) dan rekonsiliasi.
Verifikasi W1A (kode final, DB baru): suite penuh `tests/p0` **727 lulus, 2 dilewati**; `pattern_sweep --check` tidak naik (sama dengan baseline); gerbang kepatuhan hanya 3 pelanggaran lama (`AdminPermissions.js`, `finance_engine.py`, `models.py`).

### 8.W1-W1C — Deal batal: akrual komisi/fee/pajak (#11) & titipan biaya 2-1470 / invoice biaya terbuka (#12) — kebijakan terkonfigurasi

Basis `4c940d9` (W0). Dua keputusan pemilik tentang deal yang DIBATALKAN (jalur batal satu-klik, batal formal, kedaluwarsa — penutup bersama
`deal_cancel_cleanup.close_deal_dependents`) menjadi kunci pengaturan di Pusat Konfigurasi › Aturan Bisnis › Kebijakan (level organisasi + proyek;
mengganti berlaku KE DEPAN saja, nilai yang berlaku disnapshot ke `deals.cancel_policy_snapshot` dan ke `settlement.dependents.policy_snapshot`).

| Kunci | Bawaan | Opsi (tersedia) | Opsi `unavailable` (alasan jujur) |
|---|---|---|---|
| `cancel.accrual_reversal.commission` | `manual_keuangan` | `manual_keuangan`, `balik_otomatis_yang_belum_dibayar` | `balik_otomatis_semua` — butuh akun piutang ke penerima komisi; Bagan Akun tidak punya (1-1300 dikendalikan subledger AR pembeli, 1-1500 kas bon); akun tidak dikarang |
| `cancel.accrual_reversal.marketing_fee` | `manual_keuangan` | `manual_keuangan`, `balik_otomatis_yang_belum_dibayar` | `balik_otomatis_semua` — alasan sama (piutang ke agen/mitra) |
| `cancel.accrual_reversal.tax` | `manual_keuangan` | `manual_keuangan` | kedua opsi otomatis: akrual pajak baru dijurnal saat DILAPORKAN ke negara; membaliknya = pembetulan SPT, tidak boleh otomatis. Pajak `pending` tak berjurnal dan selalu dibatalkan penutup |
| `cancel.cost_deposit.policy` | `refund_dan_batalkan_invoice` | `refund_dan_batalkan_invoice`, `manual_dengan_pengakuan`, `hangus_sebagian` | — |
| `cancel.cost_deposit.forfeit_pct` | `0` (usulan sistem, bukan dokumen legal) | pct 0–100, hanya dibaca `hangus_sebagian` | — |
| `cancel.cost_deposit.requires_approval` | `true` | bool | — |

**#11 perilaku** (`backend/cancel_accrual_reversal.py`): `manual_keuangan` = perilaku lama PERSIS (ditandai `cancel_followup` + tugas/notifikasi Keuangan, tanpa jurnal balik).
`balik_otomatis_yang_belum_dibayar`: komisi `approved` dan fee `approved` ber-`paid_amount=0` dibalik — status diklaim atomik `approved → cancelled` (`idempotency.reserved`),
jurnal koreksi = CERMIN jurnal akrual aslinya (komisi: Dr 2-1600 / Cr 6-1100; fee: Dr 2-1500 [+ Dr 2-1300 PPh] / Cr 6-1200), `source_event` unik per dokumen
(`cancel.reverse:commission:<id>`, `cancel.reverse:mfee:<id>`), antrean event dikosongkan dulu supaya jurnal akrual asli ada. Subledger (komisi/fee `approved`) dan GL (2-1600, 2-1500)
turun bersama → rekonsiliasi tetap hijau. Yang tidak bisa dibalik (sudah dibayar sebagian/penuh, jurnal asli belum terbit, kalah balapan dengan pembayaran, jurnal gagal) jatuh ke
tanda tindak lanjut manual dengan SEBAB tertulis di tugas Keuangan — pembatalan tidak pernah macet. Pajak yang sudah dilaporkan/disetor TIDAK PERNAH dibalik otomatis apa pun pengaturannya.

**#12 perilaku** (`backend/cancel_cost_settlement.py`, `routers/cost_settlement_router.py`, koleksi `cost_deposit_settlements`, nomor `RTB/…`):
`manual_dengan_pengakuan` = gerbang pengakuan lama persis (400 sampai `acknowledge_costs` + catatan ≥ 10 huruf, tanpa jurnal). Kebijakan lain MENANGANI titipan/invoice sendiri, jadi
pembatalan tidak diblok (`cancellation_costs.holds().handled_by_policy`; `cancel-preview.requires_cost_ack=false`). Penutup melahirkan PERMOHONAN (`diajukan`, satu per deal —
indeks unik parsial `uq_costsettle_inflight`). Dengan `requires_approval=true` Manajer Keuangan (`cancellation:approve`, orang lain dari pemohon) harus menyetujui; `false` = dijalankan saat batal
oleh `sistem:kebijakan`. Eksekusi di bawah `deal_money` + mutex titipan kontrak (kunci yang sama dengan bayar-invoice-biaya & salurkan-titipan), saldo dibaca ULANG:
saldo titipan = Σ kuitansi − Σ penyaluran (biaya yang sudah disalurkan ke pihak ketiga otomatis tidak ikut direfund); subledger = baris `cost_disbursements` (`kind` refund_pembatalan /
hangus_pembatalan) sehingga rekonsiliasi 2-1470 tidak berubah rumus; jurnal tunggal `costsettle:<id>:approve`: Dr 2-1470 / Cr 2-1460 refund [/ Cr 4-1200 hangus]. Invoice biaya:
`unpaid` → `void`; `partial` → `cancelled` (outstanding 0, `paid` tetap, `cancelled_outstanding` dicatat — uang yang sudah masuk ikut direfund lewat saldo titipan); `paid` tidak disentuh;
kalah balapan → dilewati + dicatat. Pembayaran refund `POST /cancel-cost-settlements/{id}/refund` memakai `money_op` (once → deal_money → funds_guard), bertahap, Dr 2-1460 / Cr kas|bank.
Laporan utang refund (`refund_debt`) menyertakan sisa refund titipan biaya dalam uji-cocok 2-1460 (`ledger.cost_refund_outstanding`). Deal batal tidak bisa menerbitkan invoice biaya baru (400).
UI: dialog batal (`CancellationCostAck`) menampilkan pemberitahuan kebijakan bukan kotak pengakuan; Keuangan › Pembatalan & Refund memuat `CostSettlementsPanel` (setujui/tolak/bayar).

Perubahan perilaku BAWAAN yang akan terlihat pemakai:
- **Batal dengan titipan biaya / invoice biaya terbuka TIDAK lagi 400** (bawaan baru `refund_dan_batalkan_invoice`): pembatalan lolos tanpa pengakuan, lahir permohonan refund yang menunggu Keuangan. Untuk gerbang lama pasang `manual_dengan_pengakuan`.
- Invoice biaya terbuka milik deal batal berstatus `void`/`cancelled` setelah permohonan disetujui; deal batal menolak penerbitan invoice biaya baru.
- Komisi/fee/pajak: bawaan `manual_keuangan` = TIDAK berubah.

⚖ Butuh keputusan pemilik: (1) akun piutang ke penerima komisi/fee bila `balik_otomatis_semua` ingin dibuka; (2) `hangus_sebagian` memposting ke 4-1200 Pendapatan Lain-lain (sama dengan potongan pembatalan & booking fee hangus) — titipan biaya
adalah uang pihak ketiga (BPHTB/notaris); klausul SPR dan perlakuan pajaknya perlu konfirmasi; (3) pembalikan akrual pajak yang sudah dilaporkan (pembetulan SPT) tetap manual.

Verifikasi (kode final, DB baru): suite penuh `tests/p0` **730 lulus, 2 dilewati**; pattern_sweep tidak naik; gerbang kepatuhan hanya 3 pelanggaran lama. Merah di kode lama `4c940d9` (server+DB terpisah): 29 dari 31 tes baru (2 kontrol hijau: fee bawaan manual, validasi persen).
Tes: `test_w1c_akrual.py` (15), `test_w1c_titipan.py` (16), UI `scripts/ui/w1c_titipan.js` (35 pemeriksaan) + `seed_w1c.py`. Tes lama gerbang pengakuan (FN-03) kini memakai dekorator `manual_cost_gate` (`test_p0_masuk_2.py`);
`ronde_a_pembatalan.js` / `ronde_f_batal_reservasi.js` memasang `manual_dengan_pengakuan` di level org dan mengembalikannya; `w0_kebijakan.js` tak lagi membatasi jumlah aturan tampilan proyek ≤ 3.
