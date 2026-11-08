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
| `w1c_titipan.js` | W1-C #12 deal batal: dialog batal menampilkan kebijakan titipan biaya (bukan kotak pengakuan), Keuangan › Pembatalan & Refund memuat permohonan refund (maker-checker, setujui, bayar, tolak beralasan, putusan basi 400), kunci kebijakan baru + opsi belum tersedia (butuh `seed_w1c.py`; sekali jalan per penyemaian) |
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
