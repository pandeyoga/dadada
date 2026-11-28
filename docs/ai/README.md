# Estora AI Tahap 1 — Panduan Admin

Untuk owner dan super admin. Estora AI memakai Claude (Anthropic). Dua fitur utama:
**Copilot** untuk staf (menu "Estora AI", `/ai`) dan **Agen Penjualan WhatsApp** (draf atau balasan otomatis di Inbox).
Semua pengaturan ada di **Estora AI → Pengaturan AI** (`/ai/settings`). Halaman ini hanya bisa dibuka peran dengan izin
`ai_settings.manage` (owner dan super admin).

## 1. Kunci API Anthropic

1. Buka akun Anthropic Console, buat kunci API, salin.
2. Di Estora: **Pengaturan AI → Kunci API**, tempel kunci, simpan.
3. Kunci disimpan terenkripsi di server dan tidak pernah ditampilkan utuh. Layar hanya menunjukkan 4 karakter terakhir.
4. Klik **Tes koneksi**. Di mode simulasi tes akan jujur menjawab bahwa ini simulasi; di mode live tes memanggil Claude
   dengan permintaan kecil.
5. Mengganti kunci: isi kunci baru dan simpan. Kunci lama tertimpa. Jangan menaruh kunci di chat, tiket, atau berkas repo.

## 2. Mode: simulasi vs live

| Mode | Perilaku |
|---|---|
| Mati | Semua fitur AI berhenti. |
| Simulasi | Tanpa kunci. Jawaban berskrip, bertanda "Data contoh" / "mode simulasi". Alat dan kartu persetujuan tetap berjalan sehingga alur bisa dicoba. Di WhatsApp, pemilah memakai kata kunci sederhana (bukan AI) dan draf diawali "[Draf simulasi, bukan AI sungguhan]"; semua tetap berupa draf, tidak ada balasan otomatis. Tidak ada biaya. |
| Live | Memanggil Claude sungguhan. Perlu kunci API valid. |

Tanpa kunci, mode efektif tetap simulasi walau dipilih live. Mulai dari simulasi untuk melatih tim, pindah ke live setelah
kunci dites dan batas biaya diisi.

## 3. Biaya dan batas anggaran

- Atur **Batas biaya bulanan (Rp)** di kartu Biaya. Pemakaian bulan berjalan (per model) terlihat di kartu yang sama.
- Estimasi biaya dihitung dari token yang dipakai dikali harga model, dikonversi ke Rupiah dengan **kurs USD-IDR** yang
  bisa Anda ubah di pengaturan. Angka ini estimasi; tagihan resmi tetap dari Anthropic.
- 80% terpakai: admin (owner/super admin) mendapat satu notifikasi per bulan.
- 100% terpakai: balasan otomatis dan draf WhatsApp **berhenti**. Copilot tetap bisa dipakai owner dan super admin; staf lain
  melihat pesan bahwa anggaran habis. Naikkan batas atau tunggu bulan berikutnya untuk membuka kembali.
- Model dan effort (kedalaman berpikir) punya nilai bawaan yang masuk akal; ubah hanya bila perlu, karena memengaruhi biaya.

## 4. Copilot (staf)

Menu **Estora AI**. Chat bergaya Claude untuk sales, CS, manajer, owner.

Bisa:
- Menjawab pertanyaan dari data Estora: lead, unit/stok, harga, simulasi KPR, tagihan, progres, komplain, funnel.
- Membuat laporan (tabel, grafik) dengan pratinjau di panel kanan, unduh PDF dan Excel.
- Riset web, hanya bila saklar **Riset web** menyala di Pengaturan dan di komposer. Data pribadi (NIK, nomor HP) diblokir
  dari kueri web.
- Menerima lampiran gambar/PDF (maks 8 MB) untuk dibaca AI.
- Mengusulkan aksi: ubah tahap lead, jadwalkan survei, catat catatan lead, kirim pesan WhatsApp, buat komplain/balasan.

Tidak bisa:
- Menulis langsung ke database atau melewati aturan sistem (jurnal, gerbang bukti lead, pelepasan unit).
- Menghapus data mentah. Pembatalan hanya lewat aksi resmi sistem.
- Melihat data di luar izin pengguna yang memakainya (alat memakai hak akses pengguna itu).
- Mengarang angka. Bila alat tidak memberi data, AI harus menjawab tidak tahu.

**Kartu persetujuan.** Setiap aksi tulis muncul sebagai kartu berisi daftar perubahan dan status bukti (mis. gerbang tahap
lead). Tidak terjadi apa-apa sebelum seseorang menekan **Setujui**. Bisa juga **Ubah** (hanya bidang yang aman diubah,
mis. isi pesan, catatan, waktu survei, alasan) atau **Tolak** (dengan alasan).
Aksi dijalankan dengan hak akses **penyetuju**, dan tercatat di **Audit** (pelaku AI, atas nama siapa, disetujui siapa).
Usulan dari agen WhatsApp (mis. jadwal survei) tampil di Inbox pada percakapan kontak itu ("Usulan agen WhatsApp").
Usulan kirim WhatsApp dijalankan lewat nomor **resmi**: teks bebas hanya di dalam sesi 24 jam, di luar itu wajib template;
kontak pertama lead hanya tercatat bila pesan benar-benar terkirim.
Peran yang bisa memakai Copilot diatur di Pengaturan Peran (`ai_copilot`, `ai_inbox`).

## 5. Agen Penjualan WhatsApp: kategori dan kemandirian

Tiap pesan masuk dipilah ke kategori, lalu AI menyiapkan balasan dari data Estora. Di tabel **Kemandirian** tiap kategori
punya mode:

| Mode | Arti |
|---|---|
| Draf | AI menyiapkan balasan di Inbox; sales memeriksa lalu Kirim, Edit, atau Tulis ulang. Bawaan semua kategori. |
| Otomatis | AI langsung membalas. Hanya di mode **live**, lewat kanal resmi, di dalam jendela 24 jam WhatsApp. Penolakan model, jawaban terpotong, atau galat layanan selalu diserahkan ke sales. |
| Mati | AI tidak berbuat apa-apa untuk kategori itu. |

Kategori: stok dan harga, simulasi KPR, lokasi dan fasilitas, jadwal survei, berkas KPR, tagihan dan pembayaran, progres dan
serah terima, komplain, sapaan umum. **Terkunci ke sales** (selalu diserahkan ke manusia, tidak bisa diubah): diskon dan
nego, janji dan komitmen, pembatalan dan refund, serta pesan yang AI tidak yakin.

**Syarat memilih Otomatis** (pilihan lain dinonaktifkan dengan alasannya):
- akurasi 30 hari terakhir minimal **95%** (ambang bisa diubah), dan
- minimal **50 sampel** (draf yang sudah ditinjau/dikirim).

Cara akurasi dihitung: draf terkirim tanpa ubah = benar; diedit ringan (90% atau lebih sama) = benar; ditulis ulang atau
dibuang = salah.

**Setelah Otomatis menyala:** 10% balasan otomatis diambil sebagai sampel untuk ditinjau di Inbox ("Tinjau sampel AI":
benar/salah). Kategori **turun otomatis ke Draf** dengan notifikasi bila akurasi sampel di bawah ambang, atau ada sinyal
negatif (kontak minta manusia, atau komplain soal jawaban AI). Setiap perubahan mode tercatat di riwayat pengaturan.

AI hanya melayani urusan Estora (properti, KPR, tagihan, progres). Bukan asisten umum, sesuai kebijakan Meta untuk bot WhatsApp.

## 6. Kanal WhatsApp

Tahap 1 mendukung **1 nomor resmi** (Cloud API atau Coexistence, satu mode aktif) dan **opsional 1 nomor gateway tidak resmi**.
Pilih di kartu **Kanal**. Setiap pesan ditandai kanalnya di Inbox.

**Cloud API (resmi).** Kredensial sudah ada di pengaturan WhatsApp Estora. Dipakai untuk balasan otomatis, broadcast,
playbook, dan pengingat.

**Coexistence (resmi).** Nomor yang sama dipakai di aplikasi WhatsApp Business di HP dan lewat API.
1. Onboarding dilakukan **di luar Estora**, di Meta Business atau lewat BSP Anda.
2. Isi kredensial (token, phone ID, WABA ID) di formulir WhatsApp Estora, lalu pilih mode Coexistence di kartu Kanal.
3. Pesan yang dikirim sales dari HP ikut tercatat di Inbox (label "Coexistence"), sehingga riwayat utuh.
4. Onboarding otomatis (Embedded Signup) belum ada di Tahap 1.

**Gateway tidak resmi (berisiko).** Untuk follow-up sales berbiaya rendah lewat layanan pihak ketiga. Ini **melanggar
ketentuan WhatsApp**: nomor bisa diblokir dan risiko ditanggung pemilik. Pengaman yang berlaku dan tidak bisa dimatikan:
- **tanpa balasan otomatis AI**; hanya pesan yang ditulis dan dikirim manusia (dari Inbox atau kartu persetujuan);
- tanpa broadcast, playbook, atau pengingat otomatis;
- batas kirim **20 pesan per jam** (bawaan, bisa diturunkan atau dinaikkan; pesan di atas batas ditolak dan dicatat);
- hanya ke kontak yang sudah **opt-in** (balas YA, lihat bagian 7). Minta izinnya dari Inbox: tombol
  **Minta izin kanal kedua** mengirim pertanyaan lewat nomor resmi (saat sesi 24 jam aktif); balasan YA mencatat opt-in;
- tombol **Matikan** menghentikan semua pengiriman seketika;
- setiap pengiriman dicatat dengan penanda kanal tidak resmi.

Pengaturan teknis gateway (URL dasar, token, format payload, rahasia webhook) disimpan terenkripsi dan tidak pernah
ditampilkan ulang. Gateway menerima pesan masuk di alamat webhook bertanda rahasia yang tampil di kartu Kanal.

## 7. Persetujuan dan privasi

- Kontak yang menghubungi lebih dulu dianggap setuju pesannya diproses.
- **Balasan AI pertama** ke tiap kontak memuat pemberitahuan singkat (teks bisa diubah di kartu Privasi) dan cara berhenti:
  balas **STOP** untuk berhenti, atau **manusia** untuk dialihkan ke sales. Opt-out yang sudah ada tetap dihormati.
- Persetujuan **eksplisit (balas YA)** wajib untuk: (a) dihubungi lewat nomor gateway tidak resmi, dan (b) pemrosesan
  berkas/dokumen. Persetujuan tersimpan per kontak dan per jenis.
- Data pribadi (NIK, nomor rekening) dimasking di hasil alat bila tidak diperlukan. Data pribadi tidak dikirim ke pencarian web.
- Isi pesan WhatsApp, catatan, dan hasil web diperlakukan sebagai data tak tepercaya, bukan perintah, untuk menahan
  prompt injection. Aksi tulis tetap butuh persetujuan manusia.
- Riwayat percakapan Copilot hanya terlihat oleh pemiliknya.

## 8. Verifikasi identitas pembeli di WhatsApp

Data pribadi pembeli (virtual account, tagihan, status KPR, progres unit) hanya dijawab bila pembeli terverifikasi:
1. nomor pengirim sama dengan nomor yang terdaftar di sistem, **dan**
2. pembeli menyebut **4 digit terakhir NIK** yang cocok dengan data.

OTP lewat WhatsApp ke nomor yang sama tidak menambah keamanan di dalam chat WhatsApp, jadi tidak dipakai. **3 kali salah**
mengunci verifikasi 24 jam dan CS diberi tahu. Verifikasi berlaku **30 hari** (bisa diatur). Sebelum lolos, AI menawarkan
verifikasi atau tautan portal pembeli. Setelah lolos, AI hanya bisa membaca data kontak itu sendiri, tidak pernah data orang lain.
Agen WhatsApp memakai peran layanan terbatas (`ai_agent`, tanpa login manusia, hanya izin baca yang perlu, tanpa hapus).

## 9. Kelayakan KPR

AI memakai rasio cicilan maksimum **35% dari penghasilan** (pengaturan `ai.kpr_max_installment_ratio`, bisa diubah) dan
selalu menyebut hasilnya **perkiraan**, bukan keputusan bank. Angka cicilan berasal dari simulasi KPR sistem.

## 10. UU PDP dan DPIA

Dokumen ini bukan nasihat hukum dan **tidak menyatakan Estora patuh UU PDP**. Yang disediakan adalah fitur pendukung:
pemberitahuan, opt-in/opt-out, masking, pembatasan akses, dan jejak audit. Rekomendasi:
- **Konsultasikan dengan penasihat hukum** sebelum live, terutama soal dasar pemrosesan, transfer data ke penyedia AI di luar
  negeri, masa simpan, dan hak subjek data (akses, koreksi, hapus).
- Susun dan simpan **DPIA** (penilaian dampak pelindungan data pribadi) untuk pemrosesan percakapan pembeli, NIK, dan berkas
  KPR oleh AI. Catat tujuan, data yang diproses, penyedia (Anthropic, operator WhatsApp), risiko, dan mitigasi.
- Perbarui kebijakan privasi perusahaan dan teks pemberitahuan di kartu Privasi agar sesuai hasil tinjauan hukum.
- Tinjau Audit berkala untuk aksi AI dan kirim tanpa persetujuan (kanal tidak resmi).

## 11. Ringkasan pengaturan penting

| Kunci | Fungsi |
|---|---|
| `ai.mode` | mati / simulasi / live |
| `ai.budget_idr_month`, `ai.usd_idr` | batas bulanan dan kurs estimasi |
| `ai.accuracy_threshold`, `ai.accuracy_min_samples`, `ai.accuracy_window_days` | syarat Otomatis (95%, 50, 30 hari) |
| `ai.auto_sample_rate` | porsi balasan otomatis yang disampel (10%) |
| `ai.verification_ttl_days` | masa berlaku verifikasi pembeli (30) |
| `ai.kpr_max_installment_ratio` | rasio cicilan maksimum KPR (35%) |
| `ai.web_research_enabled` | izinkan riset web di Copilot |
| `ai.privacy_notice` | teks pemberitahuan di balasan AI pertama |

## 12. Menjalankan uji AI

Uji berjalan in-process tanpa jaringan dan tanpa kunci Anthropic (memakai klien Claude palsu). Perlu MongoDB lokal.
Langkah lengkap (pasang MongoDB, dependensi) ada di `backend/tests_ai/README.md`. Intinya:

```bash
export MONGO_URL=mongodb://127.0.0.1:27017
cd backend && python -m pytest tests_ai -q
```

Uji frontend: `cd frontend && yarn test --watchAll=false src/components/ai`.
Gerbang invarian AI: `MONGO_URL=mongodb://127.0.0.1:27017 python3 scripts/verify_ai.py` (in-process, DB `estora_ai_gate`
di-drop tiap run). Memeriksa delapan hal: (1) AI tidak mengubah data bisnis tanpa aksi `executed`, (2) tidak ada balasan
otomatis lewat kanal tidak resmi, (3) anggaran 100% menghentikan balasan otomatis, (4) data pembeli tidak lintas kontak,
(5) setiap aksi `executed` punya entri Audit, (6) aksi kanal portal hanya dieksekusi pemiliknya (pembeli, bukan staf), (7) saklar portal mati berarti nol panggilan model dan nol biaya kanal portal, (8) tiket chat portal tidak masuk statistik komplain. Gerbang ini juga terdaftar di `scripts/run_all_gates.sh`. Tanpa `MONGO_URL`
gerbang ini **dilewati** (mencetak `SKIPPED`, exit 3) dan `run_all_gates.sh` menampilkannya sebagai `SKIP`, bukan lulus:
ekspor `MONGO_URL` sebelum menjalankan semua gerbang.

Tangkapan layar mode simulasi ada di `docs/ai/screens/` (Copilot, persetujuan, Inbox, Pengaturan AI).

**Uji manual live** (hanya setelah kunci diisi): jalankan Tes koneksi, tanya satu pertanyaan stok di Copilot, minta satu aksi
dan cek kartu persetujuan serta entri Audit, lalu kirim satu pesan uji dari nomor sendiri ke nomor resmi dan lihat drafnya
di Inbox. Biarkan semua kategori di Draf sampai akurasi terbukti.

## 13. Agen portal (Tanya Estora)

Asisten AI untuk pembeli di Portal Pembeli (tombol "Tanya Estora"). Ia menjawab tagihan, progres rumah, dokumen, dan status
komplain, dan hanya membaca data pembeli yang sedang login (dipaksa ulang per transaksi/unit, bukan hanya oleh model).

- **Saklar**: Pengaturan AI > "Asisten portal pembeli" (`ai.portal_enabled`). **Default mati.** Saat mati, portal menampilkan
  "Asisten belum tersedia", tidak ada panggilan model dan tidak ada biaya. Mengubahnya meminta alasan (tercatat di Audit).
- **Batas harian**: 30 pesan per pembeli per hari (`ai.portal_daily_limit`, 1-500, hitungan hari WIB). Sisa kuota tampil di
  panel. Pesan "Bicara dengan CS" tetap dihitung agar tiket tidak bisa dibanjiri.
- **Anggaran bersama**: biaya portal masuk anggaran AI bulanan yang sama dengan Copilot dan WhatsApp (kartu Anggaran;
  rincian per kanal web/wa/portal di `GET /api/ai/usage` > `by_channel`, dalam rupiah). Di 100% asisten berhenti menjawab,
  tetapi permintaan bicara dengan CS tetap membuat tiket (tanpa model, tanpa biaya).
- **Serah ke CS (tiket chat)**: pertanyaan biasa atau permintaan bicara dengan staf menjadi tiket untuk sales unit tersebut
  (sales pemilik transaksi). Topik sensitif (diskon/negosiasi harga, janji/komitmen, pembatalan/pengembalian dana) tidak
  dijawab AI dan diteruskan ke Manajer Penjualan, atau owner bila tidak ada manajer; selain pemilah, penahan kata kunci
  (diskon, nego, potongan, refund, batal, uang kembali, janji, jamin) ikut memastikan arah ini. Pembeli menerima nomor tiket dan batas
  balasan **24 jam**; satu tugas SM-09 dan notifikasi staf dibuat. Tiket ini berjenis `pertanyaan_chat` (lencana "Pertanyaan
  dari chat" di Komplain, filter Jenis) dan **tidak dihitung** di statistik/hitungan komplain maupun pengingat SLA komplain.
- **Rumah pembeli**: BAST, masa garansi, dan klaim garansi hanya dari transaksi yang tidak batal. Unit dari transaksi
  batal bisa sudah dijual ke pembeli lain; pembeli lama tetap bisa membaca refund-nya di Pembatalan.
- **Konfirmasi pembeli**: membuat komplain atau mengajukan klaim garansi selalu lewat kartu "Kirim ... ini?" dan baru
  berjalan saat pembeli menekan Kirim (sekali saja, memakai token pembeli sendiri; staf tidak bisa menyetujuinya).
- **Privasi**: pemberitahuan penggunaan AI tampil sekali pada pembukaan pertama (teksnya bisa diubah di kartu pengaturan).
  Pembeli dapat memilih "Berhenti pakai asisten" (dan "Pakai asisten lagi"), serta "Hapus riwayat chat" untuk menghapus semua
  percakapan portalnya. Persetujuan disimpan di `ai_consents` dengan kunci `portal:<id pengguna portal>`.

Sisa pekerjaan tahap 1 yang sudah ditutup bersamaan: biaya riset web (model sonnet + pencarian web dihitung dan
memicu peringatan anggaran), ringkasan percakapan WhatsApp, dan lampiran Copilot diperlakukan sebagai rujukan (tiga lampiran
terakhir diperluas, maksimal 16 MB per permintaan dengan yang terbaru didahulukan; berkas > 8 MB ditolak 413).

Tangkapan layar (mode simulasi, saklar portal dinyalakan): `screens/05-portal-tanya-estora.png`, `05b-portal-ponsel.png`,
`06-portal-konfirmasi.png`, `07-portal-tiket-cs.png`, `08-pengaturan-portal.png`.
