# Estora AI Tahap 2a — Agen CS pembeli di portal (+ sisa tahap 1)

Tanggal: 28 Nov 2026 · Lanjutan dari `2026-11-28-estora-ai-agent-cs-crm-design.md` (tahap 1, sudah di main).

## 1. Maksud
Tahap 2 terdiri dari beberapa proyek independen yang dikerjakan berurutan (disetujui pemilik): **(2a) agen CS pembeli di portal**
→ briefing/laporan terjadwal → penjaga anggaran → cek berkas pra-KPR dari foto → progres dari foto lapangan. Voice note WA ditunda
(Claude tidak menerima audio; butuh penyedia transkripsi lain — keputusan pemilik nanti). Dokumen ini hanya untuk **2a**, ditambah
tiga sisa tahap 1 yang ditunda (biaya riset web di anggaran, ringkasan percakapan WA panjang, lampiran disimpan sebagai berkas).

Pembeli yang sudah login portal (OTP) bisa bertanya kapan saja tentang KPR, tagihan, progres rumah, dokumen, garansi, dan komplain
miliknya, dan mendapat jawaban langsung tanpa menunggu CS. CS hanya menangani yang memang butuh manusia.

## 2. Keputusan pemilik produk
- Pendekatan **A** (dipilih): widget chat "Tanya Estora" di portal; jawaban otomatis penuh; aksi (buat komplain, klaim garansi)
  dikonfirmasi sendiri oleh pembeli lewat kartu di chat; topik terkunci atau permintaan staf → tiket di modul Komplain yang ada
  dengan ringkasan percakapan. Inbox staf untuk ambil alih langsung (pendekatan B) **bukan** tahap ini.
- Urutan tahap 2 dan penundaan voice note: disetujui ("ya sesuai").
- Semua keputusan tahap 1 tetap berlaku (Claude, simulasi jujur tanpa kunci, anggaran 80/100%, UU PDP: pemberitahuan + berhenti).

## 3. Sasaran
1. **Widget "Tanya Estora"** di portal pembeli (tombol mengambang + panel chat; layar penuh di ponsel), streaming jawaban,
   langkah alat ringkas ("Membaca tagihan…"), kartu konfirmasi aksi, riwayat percakapan pembeli itu sendiri.
2. **Agen portal** (peran baru `buyer_cs`) dengan alat yang memanggil **endpoint portal yang sudah ada memakai token portal pembeli**
   (data otomatis hanya milik pembeli itu): ringkasan (`/portal/overview`), KPR (`/portal/kpr`), tagihan & bukti bayar
   (`/portal/payments`, `/portal/payments/submissions`, `/portal/receipts`), progres (`/portal/progress`), dokumen
   (`/portal/documents`), komplain (`/portal/complaints` GET), garansi (`/portal/warranty`, `/portal/warranty/claims` GET),
   serah terima (`/portal/handovers`), site plan (`/portal/site-plan`), info umum proyek/harga publik yang sudah dibaca portal
   (`/portal/reference`). Simulasi KPR memakai alat `simulasi_kpr` tahap 1 (rasio 35%, selalu "perkiraan").
3. **Aksi dengan konfirmasi pembeli**: `buat_komplain` (POST `/portal/complaints`) dan `ajukan_klaim_garansi`
   (POST `/portal/warranty/claims`). AI menyiapkan isian; kartu "Kirim komplain ini?" menampilkan isinya; hanya tombol pembeli yang
   mengeksekusi, memakai token pembeli, sekali (idempoten). Tidak ada aksi lain.
4. **Serah ke CS (tiket)**: kategori terkunci (diskon/nego, janji/komitmen, pembatalan/refund, tidak yakin) atau kata "staf/manusia/
   CS" → AI tidak menjawab substansinya, membuat **komplain kategori "Pertanyaan ke CS"** (lewat endpoint portal yang sama, tanpa
   kartu konfirmasi karena itu permintaan pembeli sendiri) berisi pertanyaan + ringkasan percakapan, lalu memberi tahu pembeli
   nomor tiketnya dan bahwa CS akan menghubungi. SLA komplain yang ada berlaku.
5. **Pengaturan AI** (halaman tahap 1): saklar "Agen portal" (default **mati** sampai pemilik menyalakan), batas pesan per pembeli
   per hari (default 30), teks pemberitahuan portal. Laporan pemakaian memisahkan biaya portal.
6. **Sisa tahap 1**: (a) anggaran menghitung biaya `server_tool_use` riset web dan memakai tarif model yang benar-benar menjawab
   (fallback), dan mencatat pemakaian dari stream yang gagal di tengah; (b) percakapan WA > 30 pesan mendapat ringkasan (Haiku)
   yang disimpan dan dikirim sebagai awal riwayat; (c) lampiran Copilot disimpan sebagai berkas (`storage.save_file`) dan dirujuk
   per id, bukan base64 di dalam pesan; batas total 8 MB per pesan.

## 4. Bukan sasaran
Inbox staf ambil-alih langsung; unggah bukti bayar lewat chat; pembayaran; mengubah data pembeli (alamat, ahli waris, dsb.);
notifikasi push/WA dari chat portal; tahap 2 lain (briefing, anggaran, OCR, foto progres, voice note).

## 5. Anti-sasaran (gagal walau jalan)
- Pembeli melihat **data pembeli lain** (alat portal hanya boleh memakai token pembeli itu; tidak ada `api_get`, tidak ada token staf
  atau `ai_agent` di percakapan portal).
- AI **menjanjikan** diskon, refund, pembatalan, tanggal serah terima, atau persetujuan KPR.
- Aksi dieksekusi **tanpa** tombol konfirmasi pembeli, atau dua kali.
- Angka (tagihan, cicilan, progres) **karangan** — fakta hanya dari alat; bila alat tidak memberi, AI bilang tidak tahu dan
  menawarkan tiket CS.
- Biaya portal lolos dari batas anggaran bulanan atau batas harian per pembeli.
- Agen portal menjadi asisten serba-bisa (resep, PR sekolah, dsb.) — hanya urusan rumah/akun Estora pembeli itu.
- Data pribadi pembeli terkirim ke riset web (riset web **tidak tersedia** di agen portal).

## 6. Batasan
Sama dengan tahap 1 §6 (FastAPI/Motor, ukuran berkas `.py` ≤ 800 / `.js` ≤ 500, gate kepatuhan, aturan Claude: adaptive thinking,
effort eksplisit, tanpa `tool_choice` paksa, fallback refusal, cek `stop_reason`, prompt caching, simulasi jujur, FakeClaude di tes).
Tambahan:
- Riwayat aman untuk *preserved thinking* seperti hasil perbaikan tahap 1 (pemikiran giliran lama dibuang secara deterministik,
  system + tools tetap selama satu giliran).
- Token portal (`portal_security.get_portal_user`) berbeda dari JWT staf; agen portal memanggil endpoint portal in-process dengan
  token itu. Endpoint baru agen portal berada di bawah `/api/portal/ai/...` dan memakai dependensi auth portal.
- `portal_router.py` sudah melewati batas 800 baris (pelanggaran lama) — **jangan menambah** isinya; router baru terpisah.
- Frontend portal: `frontend/src/pages/portal/PortalApp.js` + `frontend/src/components/portal/`; ikuti gaya portal yang ada.

## 7. Pendekatan yang dipertimbangkan
| | Pendekatan | Untung | Rugi |
|---|---|---|---|
| **A (dipilih)** | Widget chat portal; serah ke CS lewat tiket Komplain | Cepat, aman (data dibatasi token pembeli), memakai alur SLA yang ada | CS tidak bisa menyela chat secara langsung |
| B | A + inbox staf untuk ambil alih real-time | Terasa "live" | ± 2× pekerjaan: layar staf baru, notifikasi real-time |
| C | Chat portal masuk Inbox WhatsApp | Memakai layar yang ada | Inbox terikat aturan WA (jendela 24 jam, template); janggal & rawan salah |

## 8. Rancangan (garis besar; detail diserahkan ke builder)
- Backend: `backend/ai/portal_tools.py` (alat portal + 2 aksi), `backend/ai/portal_agent.py` (konteks/prompt/peran `buyer_cs`,
  batas harian, serah ke CS), `backend/routers/portal_ai_router.py` (`/api/portal/ai/conversations`, `/messages` SSE,
  `/actions/{id}/confirm|cancel`); memakai `ai.agent.run_turn`, `ai.conversations` (pemilik = `portal_user.id`, kanal `portal`),
  `ai.budget` (konteks `channel: "portal"`).
- `ToolContext`: kanal `portal`, `token` = token portal pembeli, `user` = portal user, `verified = True` (login OTP), tanpa alat staf.
- Klasifikasi topik terkunci memakai pemilah tahap 1 (`ai.triage`) atau aturan di prompt + alat `serahkan_ke_cs`; pilihan di builder,
  asalkan topik terkunci tidak pernah dijawab substansinya (ada uji). Arah dan pemisahan tiket: lihat §10.
- Frontend: `components/portal/ai/` (tombol, panel, pesan, kartu konfirmasi, stream SSE dengan token portal), label "Mode simulasi"
  bila tanpa kunci, pemberitahuan privasi pada pembukaan pertama, tombol "Bicara dengan CS".
- Koleksi: memakai `ai_conversations`/`ai_messages`/`ai_actions`/`ai_usage` (kanal `portal`); kuota harian di `ai_usage` atau
  koleksi kecil `ai_portal_quota`.
- Pengujian: FakeClaude; uji wajib: (1) pembeli A tidak bisa membaca data pembeli B lewat alat apa pun, (2) aksi hanya jalan setelah
  konfirmasi dan tepat sekali, (3) topik terkunci → tiket CS tanpa janji, (4) batas harian & anggaran 100% menghentikan agen,
  (5) agen mati di Pengaturan → widget menampilkan "belum tersedia", (6) sisa tahap 1: biaya web dihitung, ringkasan WA dibuat,
  lampiran sebagai berkas. Gate `scripts/verify_ai.py` ditambah invarian portal (tidak ada token staf/`ai_agent` di giliran portal).

## 10. Keputusan setelah tinjauan builder (28 Nov 2026)
Keputusan pemilik:
1. **Arah tiket serah-ke-CS**: pertanyaan biasa / "minta staf" → **sales pemegang unit** pembeli; topik sensitif (diskon/nego,
   pembatalan/refund, janji/komitmen) → **Manajer Penjualan** (pengguna aktif ber-peran `sales_manager` di org; bila tidak ada →
   `owner`).
2. **Tiket dari chat dipisah dari komplain**: tetap tampil di modul Komplain dengan label **"Pertanyaan dari chat"** dan filter
   sendiri, tenggat **1×24 jam**, **tidak** masuk statistik mutu komplain dan eskalasi komplain.
3. **Biaya**: memakai **anggaran AI bulanan bersama** (berhenti di 100% seperti kanal lain) + **30 pesan per pembeli per hari**.

Keputusan builder (bisa dikoreksi pemilik):
4. Tidak menambah kategori referensi baru: tiket memakai kategori `layanan` yang sudah ada + penanda `source: "ai_portal"` dan
   `kind: "pertanyaan_chat"`; statistik/eskalasi komplain mengecualikan penanda ini.
5. Tiket serah-ke-CS dibuat oleh kode sistem (bukan isian bebas AI) lewat jalur pembuatan komplain yang sama dengan portal
   (helper diekstrak dari `portal_router.py` ke modul sendiri bila perlu — memindahkan baris keluar diperbolehkan, menambah tidak),
   dengan penimpaan tenggat/penugasan di atas; **tanpa** pesan WA ke pembeli (nomor tiket sudah ditampilkan di chat).
   Komplain/klaim garansi yang dikonfirmasi pembeli lewat kartu tetap memakai endpoint portal apa adanya (termasuk notifikasinya).
6. **Tepat sekali**: kartu konfirmasi memakai mesin `ai_actions` tahap 1 (klaim atomik `pending → executing`); bila panggilan
   berhasil tetapi pencatatan gagal, aksi ditandai `executed` dengan catatan, tidak diulang.
7. Pembeli dengan **lebih dari satu unit**: alat menerima `deal_id` opsional; bila pertanyaan menyangkut unit tertentu dan pembeli
   punya > 1 unit, agen menanyakan unit yang dimaksud (daftar dari ringkasan) dan selalu mengirim `deal_id` saat membuat komplain/
   klaim (tidak memakai fallback `deals[0]`).
8. **Privasi**: pemberitahuan pada pembukaan pertama widget (tercatat di `ai_consents` kanal `portal`) + tombol "Berhenti pakai
   asisten" dan "Hapus riwayat chat"; tidak perlu opt-in "YA" karena pembeli sendiri yang memulai chat. Riwayat disimpan selama
   akun portal aktif kecuali dihapus pembeli.
9. Panggilan in-process ke endpoint portal memakai header `Authorization` berisi token portal pembeli (cara `get_portal_user`
   membaca token diverifikasi builder); `ToolContext` diperluas dengan kanal `portal` dan peran `buyer_cs`; pemilik percakapan =
   `portal_user.id`.
10. Model: Opus 5.5 effort `medium` untuk jawaban (perkiraan Rp500–800 per pertanyaan), Haiku 5.5 untuk ringkasan WA.

## 11. Diserahkan ke builder
Nama berkas/komponen persis, bentuk respons API, desain visual widget (mengikuti gaya portal), cara deteksi topik terkunci,
penyimpanan kuota harian, model per tugas (default: Opus 5.5 effort `medium` untuk jawaban, Haiku 5.5 untuk ringkasan WA).
