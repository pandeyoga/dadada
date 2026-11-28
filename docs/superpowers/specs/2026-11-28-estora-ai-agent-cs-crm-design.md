# Estora AI — Agen CS + CRM (Tahap 1) — Rancangan

Tanggal: 28 Nov 2026 · Sistem: Estora (FastAPI + MongoDB/Motor + React/Tailwind/shadcn) · Mockup UI yang disetujui:
https://claude.ai/artifact/8oQwkwRuk1Z5audwJyTRwz (4 layar: Copilot, Kartu persetujuan, Inbox WA + draf AI, Pengaturan).

## 1. Maksud
Pemilik produk ingin Estora punya **agentic AI** berbasis **Claude** yang menjadi *killer feature*: agen **CS + CRM** yang
memahami percakapan pelanggan dan **bertindak di sistem** (bukan sekadar chatbot). Pembeda dari Qontak/Sleekflow/respond.io:
jawaban berasal dari data ERP Estora yang benar (stok, harga, skema bayar, KPR, progres, tagihan), aksi tertahan gerbang
bukti yang sudah ada, satu riwayat dari chat pertama sampai akad, dan kemandirian yang bisa diatur per jenis pesan.

Visi jangka panjang (bukan tahap ini): akses penuh ke seluruh modul, laporan apa pun, riset eksternal, otomasi lintas modul.

## 2. Keputusan pemilik produk
- AI = **Claude** (Anthropic). Model utama `claude-opus-5-5`; pemilah pesan bervolume tinggi `claude-haiku-5-5`.
- Fokus: kemampuan agentic + alur otomasi; killer feature: **AI Agent CS + CRM**.
- **Putaran agen berjalan di server Estora** (Claude Messages API dari backend FastAPI), bukan Managed Agents.
- **Kemandirian bertahap** dan **diatur di UI Pengaturan** (kapan suatu jenis pesan boleh otomatis).
- **UI bergaya Claude dengan warna Estora** sesuai mockup 4 layar.
- **WhatsApp tiga jalur**: Cloud API resmi (sudah ada), **Coexistence** resmi (nomor sama dipakai di aplikasi WA Business + API),
  dan **gateway tidak resmi** (alasan: biaya) — dengan pengaman.

## 3. Sasaran Tahap 1
1. **Copilot staf** (layar 1–2 mockup): chat bergaya Claude untuk sales/CS/manajer/owner — tanya data, analisis, laporan
   (grafik + PDF + Excel di panel kanan), riset web opsional, dan **aksi tulis lewat kartu persetujuan**.
2. **Agen Penjualan WhatsApp** (layar 3): setiap pesan masuk dari lead/pembeli dipilah, lalu AI menyiapkan balasan berbasis data
   Estora. Mode per kategori: **Otomatis / Draf / Mati** (+ kategori terkunci ke sales). Ringkasan lead AI di panel kanan inbox.
3. **Pengaturan AI** (layar 4): kemandirian per kategori + ambang akurasi, kanal WhatsApp, batas biaya bulanan, kunci API, privasi.
4. **Fondasi**: klien Claude, katalog alat, putaran agen, persetujuan aksi, audit, pelacakan biaya, mode simulasi tanpa kunci.
5. **Adapter WhatsApp** baru: Coexistence dan Gateway tidak resmi di `wa_gateway` (kontrak adapter yang sama).

## 4. Bukan sasaran Tahap 1 (Tahap 2+)
Agen CS pembeli otomatis penuh di portal; briefing pagi/laporan mingguan terjadwal; intel pasar terjadwal; perluasan ke modul
keuangan/pembangunan (penjaga anggaran, progres dari foto lapangan); voice note; cek berkas pra-KPR dari foto (OCR) — **Tahap 2**.
Tidak ada fitur baru di luar AI.

## 5. Anti-sasaran (gagal walau jalan)
- AI menulis **langsung ke MongoDB** atau melewati mesin domain (jurnal, gerbang bukti lead, pelepasan unit).
- AI mengubah/menghapus data **tanpa persetujuan** manusia, atau "hapus" yang bukan aksi resmi (batal/void).
- AI menjawab angka/harga/stok **karangan** — setiap fakta harus berasal dari alat; bila alat tidak memberi, AI bilang tidak tahu.
- Data pribadi (NIK, nomor HP, gaji, berkas) **terkirim ke pencarian web**.
- Bot menjadi "asisten serba-bisa" di WhatsApp (melanggar kebijakan Meta sejak 15 Jan 2026) — agen WA hanya urusan Estora.
- Balasan **otomatis** atau blast lewat **gateway tidak resmi**.
- Biaya AI melewati batas bulanan tanpa berhenti.
- Riwayat percakapan atau kunci API bocor ke peran yang tidak berhak.

## 6. Batasan
- Backend Python/FastAPI, MongoDB (Motor), RBAC `rbac.require_permission(resource, action)` + `can(role, ...)`; konfigurasi lewat
  `settings_store` (`cfg.get/set_value`, berkas `settings_store.py` + definisi `_d(...)`); kredensial terenkripsi seperti
  `wa_gateway` (Fernet dari `JWT_SECRET`, koleksi `channel_accounts`).
- Batas ukuran berkas (gate `scripts/validate_compliance.py`): `.py` ≤ 800 baris, `.js` ≤ 500 baris; jalankan gate dengan ROOT
  yang benar (`sed 's#^ROOT = "/app"#ROOT = "/home/user/dadada"#' scripts/validate_compliance.py | python3 -`). Ada 5 pelanggaran lama
  di luar fitur ini (AdminPermissions.js, contracts_engine.py, finance_engine.py, models.py, portal_router.py) — jangan bertambah.
- SDK: `anthropic` (Python, versi terbaru di PyPI saat ini 2.x) — ikuti dokumentasi SDK, jangan menebak API.
- Claude: `thinking: {type: "adaptive"}` (tidak bisa dimatikan di Opus 5.5), `output_config.effort` diatur eksplisit (default Opus 5.5
  `medium`), `tool_choice` paksa (`any`/`tool`) **tidak didukung** di Opus 5.5 (pakai `auto` + `strict: true`), aktifkan
  **refusal fallback** sisi server (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`) dan periksa `stop_reason`
  sebelum membaca konten; streaming untuk balasan panjang; prompt caching untuk system prompt + daftar alat.
- Web: `web_search_20260209` / `web_fetch_20260209` (server tool) hanya bila riset web dinyalakan.
- WhatsApp: teks bebas hanya dalam **24 jam** sejak pesan terakhir pelanggan; di luar itu template disetujui (aturan sudah ada di
  `inbox_router`/`wa_compliance`). Gateway tidak resmi melanggar ToS WhatsApp → risiko blokir ditanggung pemilik; UI wajib jujur.
- UU PDP: pemberitahuan + persetujuan pada pesan AI pertama ke kontak; data minimal; DPIA dicatat di dokumentasi; masking NIK/
  nomor rekening di hasil alat sebelum dikirim ke Claude bila tidak diperlukan untuk tugasnya.
- Semua teks UI Bahasa Indonesia. Kontras ≥ 4,5:1. Mengikuti pola komponen yang ada (shadcn/ui, Tailwind).
- Tidak ada kunci API di lingkungan pengembangan: semua dibangun dengan **mode simulasi jujur** (seperti WA) dan **klien Claude
  palsu** di tes; mode `live` aktif bila kunci diisi di Pengaturan.

## 7. Pendekatan yang dipertimbangkan
| Aspek | Pilihan | Diputuskan |
|---|---|---|
| Hosting putaran agen | (a) server Estora + Messages API; (b) Managed Agents (Anthropic menjalankan putaran + sandbox; beta; biaya runtime sesi; riwayat sesi disimpan Anthropic) | **(a)** — alat = API Estora sendiri dengan hak akses pengguna, riwayat per kontak berbulan-bulan di MongoDB, persetujuan & audit di sistem sendiri, pertimbangan UU PDP |
| Akses alat | (a) alat terkurasi; (b) seluruh ~1.000 endpoint via katalog + tool search; (c) campuran | **(c)**: ±20 alat terkurasi (baca + usulan tulis) + 1 alat baca generik `api_get` atas endpoint GET yang di-allowlist dari OpenAPI, dicari lewat `tool_search` / katalog. Tulis **hanya** lewat alat terkurasi |
| Cara memanggil sistem | (a) panggil fungsi Python internal; (b) panggil HTTP API Estora sendiri dengan JWT pengguna | **(b)** via `httpx.AsyncClient` ke `ASGITransport(app)` (tanpa jaringan) membawa token pengguna/peran agen → RBAC & mesin domain identik dengan manusia |
| Laporan | (a) dibuat lokal (matplotlib + openpyxl + reportlab yang sudah ada); (b) code execution Claude + Files API | **(a)** untuk laporan standar (deterministik, data tetap di server). (b) tidak di Tahap 1 |
| WhatsApp tambahan | Coexistence; BSP; gateway tidak resmi | **Coexistence + gateway tidak resmi** (keputusan pemilik), BSP tidak di Tahap 1 |

## 8. Rancangan

### 8.1 Komponen backend (paket baru `backend/ai/`, tiap berkas ≤ 800 baris)
- `ai/config.py` — baca pengaturan (`settings_store` grup `ai`): `ai.mode` (`off|simulation|live`), model utama/pemilah, effort,
  batas biaya bulanan (Rupiah), kurs USD→IDR untuk estimasi, ambang akurasi default (95%), masa uji akurasi (30 hari),
  riset web aktif?, teks pemberitahuan privasi. Kunci API disimpan terenkripsi di `channel_accounts` (`code: "anthropic"`) seperti
  kredensial WA; endpoint simpan/tes koneksi khusus admin.
- `ai/client.py` — pembungkus SDK Anthropic: `messages.stream` dengan thinking adaptif, effort, fallbacks, prompt caching; mencatat
  `usage` per panggilan ke koleksi `ai_usage` (token, model, biaya USD & Rp, konteks: user/percakapan/kanal). Mode simulasi →
  `SimulatedClaude` (respons berskrip yang jujur menyebut "mode simulasi", tetap memanggil alat agar UI & alur bisa diuji).
- `ai/budget.py` — total biaya bulan berjalan; ≥80% → notifikasi admin sekali; ≥100% → agen otomatis & draf WA berhenti
  (Copilot tetap untuk `super_admin`/`owner`), status terlihat di Pengaturan.
- `ai/tools/` — registri alat: nama, deskripsi Bahasa Indonesia, `input_schema` (`strict: true`), jenis (`read|propose`),
  resource+action RBAC yang dibutuhkan, fungsi pelaksana (HTTP internal). Alat awal:
  - baca: `cari_lead`, `detail_lead` (termasuk riwayat tahap & skor + alasan), `cari_unit` (stok, tipe, harga, status),
    `daftar_harga`, `simulasi_kpr` (pakai `kpr_schedule`), `skema_bayar`, `status_kpr_kontrak`, `tagihan_pembeli`,
    `progres_unit`, `daftar_komplain`, `riwayat_percakapan_wa`, `funnel_penjualan` (analitik yang ada), `api_get` (generik,
    allowlist GET dari OpenAPI aplikasi; daftar dicari lewat alat `cari_endpoint`).
  - usulan tulis (selalu jadi **kartu persetujuan**): `ubah_tahap_lead` (lewat endpoint lifecycle yang menegakkan gerbang bukti),
    `jadwalkan_survei` (appointments), `catat_catatan_lead`, `kirim_pesan_wa` (teks dalam jendela 24 jam / template di luar),
    `buat_komplain_atau_balasan`.
  - laporan: `buat_laporan` (judul, bagian, tabel, grafik spesifikasi → PNG matplotlib + PDF reportlab + XLSX openpyxl, disimpan
    lewat `storage.py`, dikembalikan sebagai *artefak* untuk panel kanan).
  - riset: server tool `web_search`/`web_fetch` ditambahkan ke permintaan hanya jika saklar riset web menyala; system prompt
    melarang data pribadi masuk kueri, dan filter memblokir kueri yang berisi pola NIK/nomor HP.
- `ai/agent.py` — putaran agen manual (`stop_reason == "tool_use"` → jalankan alat baca langsung, **alat propose** →
  simpan `ai_actions` status `pending` dan kembalikan `tool_result` "menunggu persetujuan pengguna", lalu agen menutup giliran).
  Batas langkah per giliran (mis. 12), batas token per giliran, `pause_turn` ditangani, alat paralel dijalankan bersamaan dan
  semua hasil dikirim dalam satu pesan, kegagalan alat → `is_error: true`. Mengalirkan event ke frontend (SSE):
  `step_started/step_done` (nama alat + ringkasan manusiawi), `text_delta`, `action_proposed`, `artifact`, `done`, `error`.
- `ai/actions.py` — menyetujui/menolak/mengubah `ai_actions`: eksekusi lewat HTTP internal dengan token **penyetuju**
  (bukan token agen), hasil dicatat, `audit_logs` dengan `actor_type: "ai"`, `on_behalf_of`, `approved_by`. Hapus hanya lewat
  aksi resmi (tidak ada alat hapus mentah di Tahap 1).
- `ai/conversations.py` — koleksi `ai_conversations` (pemilik, judul otomatis, peran: copilot/penjualan/cs, kanal: web/wa,
  `contact_id/lead_id` untuk WA) dan `ai_messages` (blok konten Claude apa adanya — termasuk blok thinking yang harus dikirim balik
  utuh — langkah, artefak, aksi). Riwayat WA per kontak panjang → kompaksi ringkas (ringkasan + N pesan terakhir).
- `ai/wa_agent.py` — dipicu setelah `wa_inbound._handle_message` menyimpan pesan masuk (antrian `ai_jobs`, diproses scheduler/
  task latar): (1) **pemilah Haiku** → kategori (lihat 8.3) + niat + keberatan + sentimen; (2) bila kategori `Mati` → selesai;
  (3) agen Opus peran *penjualan* membuat **draf** berbasis alat baca (tanpa alat tulis kecuali usulan jadwal survei/catatan);
  (4) mode kategori `Otomatis` **dan** kanal resmi **dan** akurasi ≥ ambang **dan** jendela 24 jam terbuka → kirim lewat
  `wa_gateway`; selain itu simpan sebagai draf di percakapan inbox. (5) Perbarui ringkasan lead AI (skor saran, yang diketahui,
  niat & keberatan, langkah berikutnya) — skor resmi tetap dari `lead_scoring`, AI hanya menambah event kustom yang sudah ada
  mekanismenya bila disetujui.
- `ai/accuracy.py` — per kategori: draf dikirim tanpa ubah = benar; diedit ringan (≥90% sama) = benar sebagian (dihitung benar);
  ditulis ulang/ditolak = salah. Akurasi 30 hari bergulir + jumlah sampel minimum (mis. 50) sebelum Otomatis bisa dipilih.
- Router: `routers/ai_router.py` (`/api/ai/...`: percakapan CRUD, kirim pesan [SSE], aksi setujui/tolak/ubah, artefak unduh,
  pengaturan & tes kunci, penggunaan & biaya, akurasi), `routers/ai_inbox_router.py` (`/api/ai/inbox/...`: draf per percakapan,
  kirim/edit/tulis ulang, ringkasan lead). Didaftarkan di `server.py`.
- RBAC (`rbac_matrix.py`): resource baru `ai_copilot` (`use`), `ai_inbox` (`use`), `ai_settings` (`manage`); bawaan: owner/super
  admin penuh; sales_manager/marketing_admin `ai_copilot`+`ai_inbox`; sales `ai_inbox` + `ai_copilot` (data tetap tersaring oleh
  izin `view_own` mereka karena alat memakai token mereka); finance `ai_copilot`.
- Pengaman prompt injection: isi pesan WA, catatan, dokumen dan hasil web dibungkus sebagai **data tak tepercaya** dengan pembatas
  acak; system prompt menegaskan instruksi hanya dari operator; alat tulis tetap butuh persetujuan manusia.

### 8.2 WhatsApp: adapter baru di `wa_gateway`
- `CoexistenceAdapter`: memakai Graph API Cloud yang sama dengan `MetaCloudAdapter` (nomor yang ter-onboard via Embedded Signup
  coexistence); tambahan: webhook `smb_message_echoes` (pesan yang dikirim sales dari HP) dicatat ke percakapan agar riwayat utuh;
  label kanal "Coexistence (resmi)". Batas 20 pesan/detik API.
- `UnofficialGatewayAdapter`: HTTP generik terkonfigurasi (URL dasar, token, format payload kirim teks/media, webhook masuk)
  agar cocok dengan layanan lokal bergaya Fonnte/Wablas atau gateway self-hosted. Pengaman wajib: batas kirim per jam (default 20),
  hanya kontak yang sudah setuju (`consent`), **tidak boleh** kirim otomatis oleh AI, **tidak boleh** broadcast/playbook otomatis,
  tombol matikan instan, label "Risiko blokir" di UI, setiap kirim dicatat dengan `mode: "unofficial"`.
- Pilihan kanal per nomor/percakapan disimpan di `channel_accounts`; kode yang ada (broadcast, playbook, pengingat) tetap memakai
  kanal resmi.

### 8.3 Kategori pesan & kemandirian (Pengaturan)
Kategori awal: `stok_harga`, `simulasi_kpr`, `lokasi_fasilitas`, `jadwal_survei`, `berkas_kpr`, `tagihan_pembayaran`,
`progres_serah_terima`, `komplain`, `sapaan_umum`, dan **terkunci-ke-sales**: `diskon_nego`, `janji_komitmen`,
`pembatalan_refund`, `lainnya_tidak_yakin`. Mode per kategori: `auto` | `draft` | `off`; default semua `draft` (terkunci =
selalu `handoff`). `auto` hanya bisa dipilih bila akurasi 30 hari ≥ ambang dan sampel ≥ minimum (UI menonaktifkan pilihan lain
dengan alasan). Perubahan tercatat di riwayat `settings_store`.

### 8.4 Frontend (React; tiap berkas ≤ 500 baris)
- Halaman `/ai` **Estora AI Copilot** (layar 1–2 mockup): sidebar percakapan (cari, kelompok hari ini/kemarin/7 hari), kolom chat
  (pesan pengguna dalam gelembung, jawaban tanpa gelembung dengan markdown aman, blok "N langkah selesai · X detik" bisa dibuka),
  kartu persetujuan aksi (daftar perubahan + status bukti + Setujui/Ubah/Tolak), panel artefak kanan (Pratinjau/Data, grafik,
  tabel, Unduh PDF/Excel, Kirim ke WhatsApp), komposer (lampiran berkas [Tahap 1: gambar/PDF dikirim sebagai konten ke Claude],
  pilihan peran, saklar riset web, kirim). Streaming SSE. Penanda "Data contoh" bila mode simulasi.
- **Inbox** (`/inbox`, layar 3): label per percakapan (Dibalas otomatis / Draf AI siap / Butuh sales), kartu draf AI (kategori,
  mode, dasar data, Kirim/Edit/Tulis ulang), panel **Ringkasan AI** (skor, tahap, yang diketahui, niat & keberatan, langkah
  berikutnya + tombol aksi), label kanal di kepala percakapan.
- **Pengaturan AI** (`/config` grup baru atau `/ai/settings`, layar 4): kemandirian per kategori + ambang, kanal WhatsApp (3 kartu,
  gateway tidak resmi bergaya peringatan), batas biaya + pemakaian bulan ini, kunci API + tes koneksi + mode, teks privasi.
- Navigasi: item "Estora AI" di sidebar (ikon), terlihat sesuai izin `ai_copilot`.

### 8.5 Data (koleksi baru)
`ai_conversations`, `ai_messages`, `ai_actions` (pending/approved/rejected/executed/failed, payload, hasil, siapa), `ai_jobs`
(antrian WA), `ai_usage`, `ai_drafts` (per percakapan WA: kategori, teks, dasar data, status sent/edited/rewritten/discarded,
dipakai `accuracy`), `ai_lead_insights` (ringkasan AI per lead). Indeks untuk query per org/pengguna/percakapan/tanggal.
Semua dokumen membawa `org_id` (multi-tenant seperti koleksi lain).

### 8.6 Pengujian
- Unit/integrasi tanpa jaringan: `FakeClaude` yang memutar skenario (teks, tool_use, refusal, max_tokens, pause_turn) untuk menguji
  putaran agen, persetujuan, budget, akurasi, pemilah, adapter WA (gateway tiruan), dan masking PII.
- Mode simulasi end-to-end di UI (tanpa kunci).
- Gate repo: kepatuhan ukuran berkas, `verify_rbac.py`/`verify_api_contract.py` bila endpoint baru perlu didaftarkan, dan sebuah
  gate baru `scripts/verify_ai.py` (invarian: AI tidak pernah menulis tanpa `ai_actions` approved; kanal tidak resmi tidak pernah
  `auto`; biaya ≥100% menghentikan otomatis).
- Uji manual live hanya bila pemilik mengisi kunci API (dicatat sebagai langkah serah terima, bukan syarat selesai).

## 9. Keputusan setelah tinjauan builder (28 Nov 2026)

**Dari pemilik produk:**
1. **Verifikasi identitas di WhatsApp**: data pribadi pembeli (VA, tagihan, status KPR, progres unit) hanya dijawab bila nomor
   pengirim = nomor pembeli di sistem **dan** kontak sudah lolos **OTP WhatsApp** (memakai mekanisme OTP portal pembeli yang ada),
   berlaku 30 hari (dapat diatur). Sebelum lolos, AI menawarkan verifikasi atau tautan portal.
2. **Jumlah nomor Tahap 1**: **1 nomor resmi** (Cloud API *atau* Coexistence — satu mode aktif) **+ opsional 1 nomor gateway tidak
   resmi** untuk follow-up sales. Tidak ada multi-nomor; cukup penanda kanal pada pesan keluar/masuk dan rute webhook gateway sendiri.
3. **Persetujuan (UU PDP)**: kontak yang menghubungi lebih dulu dianggap setuju diproses; **balasan AI pertama** ke kontak memuat
   pemberitahuan singkat + cara berhenti (`STOP` / `manusia`). Persetujuan **eksplisit (balas YA)** wajib untuk: dihubungi lewat
   nomor tidak resmi, dan pemrosesan berkas/dokumen. Penyimpanan persetujuan baru (opt-in per kontak, per jenis), opt-out yang ada
   tetap dihormati. Rekomendasi konsultasi hukum dicatat di dokumentasi.
4. **Kelayakan KPR**: rasio cicilan maksimum **35% dari penghasilan** (pengaturan `ai.kpr_max_installment_ratio`, bisa diubah);
   AI selalu menyebutnya *perkiraan*, bukan keputusan bank; cicilan dari `kpr_schedule`/`simulasi_kpr`.

**Keputusan builder (bisa dikoreksi pemilik):**
5. **Identitas alat agen WhatsApp**: peran layanan baru **`ai_agent`** (bukan login manusia) dengan izin baca terbatas
   (leads/units/pricing/kpr/projects/complaints/appointments sesuai kebutuhan alat) didaftarkan lewat `ALL_ROLES` + migrasi matriks
   (`ROLE_GRANTS`/`MATRIX_MIGRATIONS`) agar tabel izin di DB ikut. Di giliran WhatsApp, alat data pribadi **dibatasi ke kontak itu
   sendiri** (lead/pembeli yang cocok nomor + sudah OTP) di lapisan alat — bukan hanya lewat prompt. `api_get` generik **tidak**
   tersedia untuk agen WhatsApp (hanya Copilot staf, dengan token staf). Usulan tulis dari WA (jadwal survei, catatan) masuk
   `ai_actions` dan disetujui sales/pemilik lead.
6. **Akurasi saat Otomatis**: syarat ambang dicek saat menyalakan `auto`; setelah itu **10% balasan otomatis diambil sampel**
   untuk ditinjau di Inbox ("Tinjau sampel AI": benar/salah); akurasi bergulir 30 hari memakai draf + sampel. Turun otomatis ke
   `draft` bila akurasi sampel < ambang atau ada sinyal negatif (kontak meminta manusia/komplain soal jawaban AI) — dengan notifikasi.
7. **Onboarding Coexistence**: nomor didaftarkan di luar Estora (Meta Business/BSP); Estora menerima `token`, `phone_id`,
   `waba_id` lewat formulir kredensial seperti `wa_setup` + panduan; Embedded Signup = Tahap 2.

## 10. Diserahkan ke builder
Struktur kode rinci di dalam `backend/ai/`, nama endpoint persis, desain prompt sistem (Bahasa Indonesia, gaya Estora), format SSE,
komponen React persis (mengikuti shadcn yang ada), pilihan pustaka markdown aman yang sudah ada di frontend, detail kompaksi riwayat,
format payload gateway tidak resmi bawaan (generik + contoh pemetaan untuk satu layanan populer bila dokumentasinya publik),
skema skenario `FakeClaude`, dan cara terbaik menyiapkan MongoDB + backend lokal untuk uji (repo memakai uji e2e ke backend berjalan).
