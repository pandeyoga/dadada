# Uji peramban SIPRO (Playwright)

Skrip Node yang membuka UI seperti pengguna sungguhan (login lewat formulir, klik, isi form), menjalankan aksi,
mengambil tangkapan layar, dan memeriksa: pesan galat server (400/409) tampil sebagai toast yang terbaca, tombol yang
tak berlaku tidak ditawarkan, layar menyegarkan diri sesudah galat, dan tidak ada error konsol.

| Skrip | Layar yang diuji |
|---|---|
| `webhook_security.js` | Pusat Konfigurasi › Keamanan Webhook (isi/ganti/cabut rahasia, izin, 409 palsu) |
| `ronde_a_pembatalan.js` | Pembatalan kontrak: kotak pengakuan biaya (`acknowledge_costs`/`cost_note`) |
| `ronde_bc_banner.js` | Banner tab Komponen Biaya + `GlReconcileBanner` (12 pemeriksaan + `indicator`) |
| `ronde_d_void.js` | `ArDetailSheet`: void kuitansi + penolakan pada deal batal |
| `ronde_f_batal_reservasi.js` | Batal reservasi satu-klik: pengakuan titipan/invoice biaya (butuh backend dengan `cost_holds`; dilewati bila belum ada) |
| `w0_kebijakan.js` | Pusat Konfigurasi › Aturan Bisnis: kebijakan terkonfigurasi (kelompok Kebijakan, alasan wajib, pemilih tingkat proyek, opsi "belum tersedia" nonaktif) |
| `w1a_kebijakan.js` | Pusat Konfigurasi › Aturan Bisnis: kunci reservasi kedaluwarsa (enum + angka bertetapan batas), `lead.won_trigger` kini bisa ditimpa per proyek dan bawaannya "Booking fee terverifikasi" |
| `w1b_diskon_bertingkat.js` | W1-B #8: editor tabel tingkat persetujuan diskon (validasi celah/tumpang tindih/peran menurun, alasan wajib, tingkat proyek) |
| `w1b_alokasi_skema.js` | W1-B #9: panel 'ganti skema ditahan' di lembar AR — pemetaan alokasi per kuitansi oleh Keuangan (menyemai sendiri lewat `seed_w1b.py`; butuh `PYTHON` berisi requests+pytest) |
| `w1c_titipan.js` | W1-C #12 deal batal: dialog batal menampilkan kebijakan titipan biaya (bukan kotak pengakuan), Keuangan › Pembatalan & Refund memuat permohonan refund (maker-checker, setujui, bayar, tolak beralasan, putusan basi 400), kunci kebijakan baru + opsi belum tersedia (butuh `seed_w1c.py`; sekali jalan per penyemaian) |
| `w2a_master_pajak.js` | W2-A #15/#1: Pusat Konfigurasi › Aturan Bisnis › kelompok "Master Pajak & PPN" (7 kunci, bawaan = perilaku lama; pemilih proyek, alasan wajib, riwayat); Keuangan › Konfigurasi › Pajak (lapisan kompatibilitas + pemilih proyek + mode PPN) untuk Manajer Keuangan, hanya-baca bagi staf; tab Biaya All-in menunjuk Master Pajak (menyemai sendiri lewat API; tidak butuh `seed_*.py`) |
| `w2c_master_biaya.js` | W2-C #16: Pusat Konfigurasi › Komponen Biaya — banner jujur (bayangan/katalog sumber), laporan selisih katalog vs aturan All-in (selisih nyata, migrasi idempoten, selaraskan beralasan), dialog baris biaya vs baris harga, pindah ke `katalog_sumber` lewat Aturan Bisnis (opsi nonaktif + alasan saat selisih ≠ 0), tulis tembus, kunci `cost.component_max_amount` / `contract.cost_model` / `contract.cost_free_input_needs_approval` |
| `w2c_biaya_kontrak.js` | W2-C #6: isian bebas biaya kontrak DITAHAN (202) → kotak permohonan di panel kontrak; pemohon≠penyetuju (setujui/tolak beralasan/batalkan), kunci persetujuan nonaktif = langsung berlaku (butuh `seed_w2c.py`; sekali jalan per penyemaian) |
| `w2b_kebijakan_kontrak.js` | W2-B #3: panel "Kebijakan kontrak" di Customer › Kontrak & Legal (BPHTB per kontrak): nilai efektif + asal (bawaan mengikuti skema all-in), ringkasan pembeli/developer, ubah per kontrak (alasan ≥ 10 karakter), Dibagi + porsi developer, kembali mengikuti proyek/organisasi, riwayat, pesan 400 server (uang sudah bergerak) tampil sebagai toast terbaca + alasan terkunci, staf Keuangan hanya-baca (menyemai sendiri lewat API; tidak butuh `seed_*.py`) |
| `ronde_e_aksi_409.js` | Setujui/tolak permintaan material, status izin, status komplain, batal PO `partially_received`, buka-blokir unit, setujui/tolak transfer kas |

## Menjalankan

1. Backend hidup (mis. `uvicorn server:app --port 8073`) dengan akun demo (`SEED_DEMO_USERS=true`).
2. Bangun frontend satu-origin: `cd frontend && DISABLE_ESLINT_PLUGIN=true BUILD_PATH=/tmp/ui_build yarn build`
   (`apiClient` memakai origin halaman bila `REACT_APP_BACKEND_URL` kosong. `frontend/.env` memasang nilai bawaan, jadi kosongkan EKSPLISIT:
   `REACT_APP_BACKEND_URL= DISABLE_ESLINT_PLUGIN=true BUILD_PATH=/tmp/ui_build yarn build` — tanpa itu login peramban menembak `localhost:8001` dan menggantung).
3. Sajikan: `node scripts/ui/serve.js /tmp/ui_build 3073 8073` (statis + proksi `/api`).
4. Jalankan semuanya (menyemai data baru lewat API lalu semua skrip):
   ```
   SIPRO_UI_BASE=http://localhost:3073 NODE_PATH=<folder node_modules berisi playwright> \
   PYTHON=<python backend (butuh requests + pytest)> SIPRO_UI_SHOTS=/tmp/ui-shots bash scripts/ui/run_all.sh
   ```
   atau satu skrip: `node scripts/ui/webhook_security.js` (yang bergantung data butuh `python3 scripts/ui/seed_hc.py`
   dulu; satu penyemaian hanya cukup untuk SATU kali jalan karena skenarionya mengubah data).

Lingkungan: `SIPRO_UI_BASE` (bawaan `http://localhost:3073`), `SIPRO_API_BASE`, `SIPRO_UI_SHOTS` (folder
tangkapan layar; **jangan** di dalam repo), `SIPRO_UI_SEED_OUT` (berkas JSON hasil `seed_hc.py`). Kode keluar
non-nol bila ada pemeriksaan yang gagal. Jangan menjalankan `playwright install`; skrip memakai Chromium bawaan.

Catatan: keadaan "merah", indikator, dan jurnal gagal pada `GlReconcileBanner` tidak bisa dibuat lewat API tanpa
merusak buku, jadi `ronde_bc_banner.js` memalsukan respons `/finance/reconcile` di sisi peramban (`page.route`);
keadaan hijau memakai data nyata.
