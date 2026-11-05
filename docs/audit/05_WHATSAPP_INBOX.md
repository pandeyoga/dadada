# Audit UI — Percakapan WhatsApp (menu CRM › Percakapan (WA), rute `/inbox`)

> Tanggal audit: 5 Nov 2026 · Mode: aplikasi dijalankan sungguhan (backend + MongoDB + frontend build produksi), dibuka lewat browser (Chromium/Playwright) seperti user.
> Data uji: 223 percakapan + 1 percakapan berisi 621 pesan, dibuat lewat endpoint simulasi webhook yang sama dengan jalur Meta (`POST /api/wa/simulate/inbound`).
> Label bukti: **[TERBUKTI-UI]** direproduksi di browser · **[TERBUKTI-API]** direproduksi lewat HTTP · **[DARI-KODE]** hanya dari membaca kode.

## Kesimpulan

**Keluhan Anda benar dan sudah direproduksi.** Penyebabnya bukan satu bug, melainkan desain halaman: daftar percakapan tidak punya wadah gulir sendiri dan tidak punya paginasi, sehingga halaman memanjang mengikuti jumlah chat; panel percakapan dan panel konteks lead tidak menempel (sticky) sehingga hilang dari layar saat daftar di-scroll; dan setiap aksi men-scroll halaman secara otomatis. Selain masalah tampilan, ada **tiga cacat data yang lebih serius**: chat di atas 50 tidak bisa dijangkau, pesan terbaru di percakapan panjang hilang, dan tombol "Kirim sbg Pesan Masuk" memungkinkan staf memalsukan pesan pelanggan.

| ID | Tingkat | Ringkasan |
|---|---|---|
| WA-01 | Tinggi | Daftar chat memanjang tanpa batas, panel kanan menghilang saat scroll |
| WA-02 | Tinggi | Hanya 50 chat pertama yang bisa dibuka; tidak ada "muat lagi" atau pencarian |
| WA-03 | Tinggi | Percakapan > 500 pesan: pesan terbaru tidak pernah tampil |
| WA-04 | Tinggi | Halaman mendarat dalam keadaan ter-scroll; klik chat melempar posisi scroll |
| WA-05 | Sedang | Setiap kirim/refresh membongkar seluruh layar (kedip skeleton) |
| WA-06 | Sedang | Tidak real-time: pesan masuk tidak muncul tanpa reload |
| WA-07 | Sedang | Chat teratas otomatis "dibaca" saat halaman dibuka; badge basi |
| WA-08 | Tinggi | Tombol "Kirim sbg Pesan Masuk" memalsukan pesan pelanggan & membuka kembali jendela 24 jam |
| WA-09 | Sedang | Akses percakapan tidak difilter per organisasi |
| WA-10 | Rendah | `/wa-capture`: 22 dari 222 kontak tak terjangkau; 200 baris dirender sekaligus |
| WA-11 | Rendah | Filter minim; hitungan per filter tidak dipakai |

---

## Temuan

### WA-01 · Tinggi · Daftar chat memanjang tanpa batas; panel kanan menghilang saat scroll
- **Bukti:** [TERBUKTI-UI]. Pada 50 kartu (tiap kartu 110 px) tinggi konten `<main>` = **5.979 px** (tinggi layar 835 px). Di layar 390 px (HP) tinggi konten = **6.735 px** dan panel percakapan baru mulai di y = **6.080 px**, jadi di HP harus melewati seluruh daftar dulu. Screenshot: `docs/audit/img/wa-inbox-scrolled-list-empty-right.png` (kolom kanan kosong saat daftar di-scroll) dan `docs/audit/img/wa-inbox-mobile-landing.png`.
- **Akar masalah:** `frontend/src/pages/InboxPage.js:130-154` — grid 4 kolom, kolom daftar `space-y-2` tanpa `max-height`/`overflow-y-auto`. Panel percakapan (`:157`, `h-[560px]`) dan panel konteks (`:228`) berada di baris grid yang sama tetapi tidak `sticky`, jadi keluar layar begitu daftar di-scroll. Hanya pesan di dalam panel yang punya scroll sendiri (`:183`).
- **Dampak:** makin banyak chat, makin jauh scroll; petugas kehilangan konteks percakapan yang sedang dibalas.

### WA-02 · Tinggi · Hanya 50 chat pertama yang bisa dijangkau; tidak ada pencarian
- **Bukti:** [TERBUKTI-UI]+[TERBUKTI-API]. Server memiliki 223 percakapan; halaman hanya merender **50 kartu**. `GET /api/inbox?limit=500` mengembalikan 200 dari 223 (server membatasi 200).
- **Akar masalah:** `InboxPage.js:48` memanggil `api.get("/inbox", { params: { filter } })` tanpa `skip`/`limit`, dan tidak membaca `total` dari respons. Tidak ada tombol "muat lagi", tidak ada infinite scroll. Backend `routers/inbox_router.py:55-73` tidak punya parameter pencarian `q` sama sekali (hanya `filter`, `status`, `channel`), dan `core_utils.py:44-46` membatasi `limit` ≤ 200.
- **Dampak:** chat yang lebih lama dari 50 percakapan terbaru **tidak bisa dibuka** dari menu ini; cara satu-satunya lewat profil lead.

### WA-03 · Tinggi · Percakapan panjang: pesan TERBARU tidak pernah ditampilkan
- **Bukti:** [TERBUKTI-API]+[TERBUKTI-UI]. Percakapan berisi 621 pesan: API mengembalikan 500 pesan dari "pesan ke-1" sampai "pesan ke-500"; UI merender tepat **500 bubble** dengan bubble terakhir "pesan ke-500". 121 pesan terbaru tidak ada.
- **Akar masalah:** `routers/inbox_router.py:88` — `.sort("created_at", 1).to_list(500)` (urut naik lalu dipotong 500 → yang terpotong justru yang terbaru). Pola yang benar sudah ada di `routers/wa_router.py:232-234` (urut turun + limit, lalu dibalik).
- **Dampak:** setelah petugas membalas, balasannya **tidak muncul** di thread (karena posisinya > 500) sehingga terlihat seperti gagal terkirim, memicu kirim ganda ke pelanggan.

### WA-04 · Tinggi · Halaman mendarat dalam keadaan ter-scroll; klik chat melempar posisi scroll
- **Bukti:** [TERBUKTI-UI]. Tanpa ada scroll dari user, `main.scrollTop` = **454 px** saat halaman selesai dimuat (di HP **5.977 px**), sehingga judul percakapan dan sebagian pesan terpotong (`docs/audit/img/wa-inbox-landing-desktop.png`). Dengan daftar di-scroll ke kartu ke-36 (scrollTop 3.830) lalu diklik, scrollTop melompat ke **232**: posisi di daftar hilang, panel percakapan yang tadinya di y = −3.685 px tiba-tiba ada di layar.
- **Akar masalah:** `InboxPage.js:62` — `endRef.current?.scrollIntoView({ behavior: "smooth" })`. `scrollIntoView` menggulung **semua** elemen induk, termasuk `<main>`, bukan hanya kotak pesan. Ditambah `:51` yang otomatis memilih percakapan pertama saat halaman dibuka.
- **Perbaikan:** gulung hanya wadah pesan (`el.scrollTop = el.scrollHeight`), jangan `scrollIntoView`.

### WA-05 · Sedang · Setiap kirim/refresh membongkar seluruh layar
- **Bukti:** [TERBUKTI-UI]. Setelah satu kali kirim pesan, daftar+thread **hilang dan dibangun ulang** (MutationObserver mencatat 2 kejadian DOM saat tidak ada satu pun kartu di layar) dan `main.scrollTop` bergeser (128 → 306).
- **Akar masalah:** `InboxPage.js:46` — `loadConvs()` selalu `setLoading(true)`, dan `:125` mengganti seluruh grid dengan `<LoadingCards/>` selama loading. `refresh()` (`:75`) dan `send()` (`:85`) memanggil `loadConvs()`.
- **Perbaikan:** muat ulang diam-diam (tanpa mengganti layar dengan skeleton) setelah load pertama.

### WA-06 · Sedang · Tidak real-time
- **Bukti:** [TERBUKTI-UI]. Pesan masuk baru dari pelanggan simulasi masuk ke server; halaman Inbox yang sedang terbuka **tidak menampilkannya** setelah 20 detik, dan tidak ada satu pun request ke `/api/inbox` selama itu.
- **Akar masalah:** `InboxPage.js` tidak memakai polling maupun WebSocket (padahal WS notifikasi sudah ada di `components/layout/TopBar.js:112`).

### WA-07 · Sedang · Chat teratas otomatis "terbaca"; badge belum dibaca basi
- **Bukti:** [TERBUKTI-UI] (permintaan `GET /api/inbox/{id}` terjadi tepat setelah daftar dimuat, tanpa klik) + [DARI-KODE].
- **Akar masalah:** `InboxPage.js:51` memilih `rows[0]` otomatis → `routers/inbox_router.py:89` mengubah `unread = 0` pada `GET`. Pesan yang belum pernah dilihat petugas tercatat sudah dibaca. Sebaliknya badge di daftar tidak di-refresh setelah dibuka (`:60-62` hanya memuat thread).

### WA-08 · Tinggi · "Kirim sbg Pesan Masuk" memalsukan pesan pelanggan
- **Bukti:** [TERBUKTI-API]. Sebagai peran **sales** pada percakapan dengan jendela 24 jam tertutup (pelanggan terakhir menulis 3 hari lalu): (1) balasan bebas ditolak dengan benar ("Sesi 24 jam tertutup…"); (2) `POST /api/inbox/{id}/messages {"direction":"in"}` **berhasil** dan dicatat sebagai pesan dari kontak; (3) balasan bebas yang sama sekarang **lolos**.
- **Akar masalah:** UI `InboxPage.js:209-212` menampilkan tombol permanen untuk semua peran (tidak dibatasi mode simulasi, `waMode` hanya dipakai untuk lencana). Backend `routers/inbox_router.py:169-176` menerima `direction:"in"` tanpa memeriksa mode live/simulasi dan tanpa izin khusus (sales punya `inbox: create`), lalu `:180-181` membuka ulang jendela 24 jam, `:193-196` menulis "WhatsApp masuk (SIMULASI)" ke timeline lead, dan `:201-203` memicu `message.received` (aturan otomasi dapat mengirim balasan otomatis ke pelanggan sungguhan).
- **Dampak:** data CRM tercemar pesan palsu; metrik "Belum dibalas" salah; aturan kebijakan jendela 24 jam WhatsApp hanya ditegakkan di aplikasi sendiri sehingga mudah dilanggar (risiko kualitas nomor WA di Meta pada mode live). Perilaku live tidak bisa diuji di sini (kredensial Meta tidak ada) — bagian ini [DARI-KODE].
- **Perbaikan:** sembunyikan tombol kecuali mode `simulation` dan izin khusus; tolak `direction:"in"` di backend bila `effective_mode == live`.

### WA-09 · Sedang · Akses percakapan tidak difilter per organisasi
- **Bukti:** [DARI-KODE]. `routers/inbox_router.py:47` `db.conversations.find_one({"id": conv_id})` tanpa `org_id`; `send_message` memakai `org` dari user (`:133`), bukan dari percakapan. Dengan fitur multi-organisasi (switch org), user organisasi lain yang mengetahui `id` percakapan dapat membaca/menulis. Eksploitasi memerlukan id UUID, jadi risikonya sedang.

### WA-10 · Rendah · `/wa-capture`: sebagian kontak tak terjangkau dan 200 baris dirender sekaligus
- **Bukti:** [TERBUKTI-UI]. KPI menyatakan 222 kontak menunggu, tabel hanya memuat **200 baris** (tinggi konten 16.765 px); tidak ada paginasi. `frontend/src/pages/WaCapturePage.js:51` menetapkan `limit: 200`, `routers/wa_router.py:123` membatasi 200.

### WA-11 · Rendah · Filter minim
- **Bukti:** [DARI-KODE]. Hanya Semua / Saya / Belum dibalas (`InboxPage.js:22-26`). Endpoint `/api/inbox/stats` (`inbox_router.py:76-82`) tidak dipakai UI sehingga tombol filter tanpa hitungan; filter `status`/`channel` ada di backend tetapi tidak ada di UI; tidak ada filter "belum dibaca", "sesi tertutup", atau per sales.

---

## Terverifikasi OK
- Balasan bebas pada sesi tertutup ditolak backend (pesan "Sesi 24 jam tertutup") — [TERBUKTI-API].
- Satu nomor telepon = satu percakapan (3–5 pesan ke nomor yang sama tidak membuat percakapan ganda) — [TERBUKTI-API].
- Urutan daftar menurut `last_message_at` terbaru; sales hanya melihat percakapan miliknya (2 dari 2 pada data demo) — [TERBUKTI-API].
- Panel kecil "balas cepat" di `/wa-capture` memakai pola ambil-12-terbaru yang benar (`wa_router.py:232-234`).

## Tidak bisa diverifikasi
- Perilaku mode LIVE (Meta Cloud API): kredensial tidak ada, seluruh pengujian di mode simulasi.
- Kinerja pada ribuan percakapan (hanya 223 + 621 pesan yang diuji).

## Arah perbaikan (rancangan, belum dikerjakan)
1. **Tata letak 2 panel setinggi layar** (`h-[calc(100vh-<header>)]`): daftar kiri `overflow-y-auto` sendiri, panel tengah dan panel konteks tetap di tempat; di HP gunakan pola master–detail (daftar ATAU percakapan, tombol kembali).
2. **Daftar:** infinite scroll memakai `skip/limit` + `total`, kolom cari (nama/HP) — tambahkan `q` di `list_conversations`; filter tambahan (belum dibaca, sesi aktif/tertutup, per sales); hitungan dari `/inbox/stats`; virtualisasi bila > 200 item.
3. **Thread:** muat 50 pesan terbaru, "muat pesan sebelumnya" saat scroll ke atas (kursor `before=created_at`); perbaiki `inbox_router.py:88` (urut turun + limit + balik); gulung hanya wadah pesan.
4. **Pembaruan langsung:** pakai WebSocket notifikasi yang sudah ada atau polling ringan 10–15 dtk; muat ulang tanpa skeleton.
5. **Tombol simulasi:** hanya mode simulasi + izin khusus; backend menolak `direction:"in"` di mode live.
6. **Tandai terbaca** hanya saat user membuka/klik percakapan, bukan saat auto-select; refresh badge setelahnya.
7. Tambahkan `org_id` ke `_get_conv_scoped`.
