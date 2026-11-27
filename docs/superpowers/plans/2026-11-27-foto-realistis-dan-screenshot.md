# Foto realistis, screenshot rapi, dan deck lampiran — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ganti semua gambar placeholder prototipe (termasuk CCTV) dengan foto realistis lokal, ambil ulang screenshot semua halaman dengan nama jelas per peran, dan susun PowerPoint gabungan pitch deck Canva + Lampiran screenshot.

**Architecture:** Foto Pexels disimpan di `frontend/public/rdg/foto/`, dipetakan oleh satu manifest JSON dan satu komponen `Photo` (fallback ke SVG lama). Skrip screenshot yang ada diperluas (halaman penuh + layar pertama, folder per peran, deskripsi per layar dari `screens.json`). Deck dibangun pptxgenjs di `reports/deck_src/` dari gambar halaman PDF Canva + screenshot.

**Tech Stack:** React 19 (CRA/craco, Jest 27), Playwright global, Node, pptxgenjs (`/tmp/claude-0/-home-user-dadada/4c43c2dd-1aa7-553c-9e9f-59508645de56/scratchpad/deckbuild/node_modules`), pdftoppm, LibreOffice (`soffice`), Python PIL.

**Spec:** `docs/superpowers/specs/2026-11-27-foto-realistis-dan-screenshot-design.md`

## Global Constraints
- Semua gambar dimuat dari berkas lokal `/rdg/foto/...`; tidak ada URL gambar luar di kode prototipe.
- Sumber foto hanya Pexels (lisensi Pexels); kredit tiap berkas dicatat di `docs/prototype/FOTO-KREDIT.md`.
- Foto: sisi panjang ≤ 900 px (CCTV 960×540, 16:9), JPEG kualitas ±78, ≤ 150 KB per berkas, total ≤ 6 MB.
- Tanpa wajah orang yang dikenali, tanpa logo/merek dagang terbaca, tanpa papan nama perumahan lain.
- Foto rumah/progres/unit/promo/fasilitas berlabel "Foto ilustrasi"; CCTV tetap berlabel simulasi/LIVE.
- Aturan prototipe lama tetap: teks Bahasa Indonesia, kontras ≥ 4,5:1, tidak ada kata "Ningrat", "Data contoh" hanya di U1/P9/W28, file `.js` ≤ 500 baris, `/services/` ≤ 300, CSS ≤ 400.
- Gerbang: `cd frontend && CI=true npx craco test --watchAll=false src/prototype` lulus; kepatuhan `sed 's#^ROOT = "/app"#ROOT = "/home/user/dadada"#' scripts/validate_compliance.py | python3 -` hanya 5 kegagalan lama di luar prototipe; `REACT_APP_BACKEND_URL=http://127.0.0.1:9 yarn build` (tanpa `CI=true`); skrip screenshot `59 layar, 0 overflow`.
- Commit diakhiri trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` dan `Claude-Session: https://claude.ai/code/session_01WetgRXmuAJkoYLhyp3fN6g`; jangan commit `yarn.lock`/`frontend/build`.

## Review Focus
1. Foto gagal dimuat (berkas hilang/salah ketik) → komponen menampilkan SVG lama, tidak kosong/rusak — Task 2 test `fireEvent.error`.
2. Kamera dengan label tak dikenal (mis. "Kamera ruang tamu") tetap mendapat foto CCTV yang konsisten — Task 2 test `cctvKeyFor`.
3. Halaman sangat panjang (W28, K2) di mode halaman penuh tidak terpotong dan bilah navigasi tidak menimpa konten — Task 3 cek tinggi PNG ≥ scrollHeight × skala.
4. Nama berkas screenshot unik dan stabil (W29 dan P10 berbagi rute) — Task 3 test slug/nama unik.
5. Deck: label tiap screenshot cocok dengan gambarnya (urutan tidak bergeser) — Task 4 cek lembar kontak PDF.

---

### Task 1: Kurasi foto realistis

**Files:**
- Create: `frontend/public/rdg/foto/{pasar,progres,unit,promo,cctv,fasilitas,tiket}/*.jpg`
- Create: `frontend/src/prototype/lib/photos.json`
- Create: `docs/prototype/FOTO-KREDIT.md`
- Test: `frontend/src/prototype/__tests__/photos.test.js`

**Interfaces:**
- Produces: `photos.json` = `{ "<kunci>": { "src": "/rdg/foto/<kategori>/<nama>.jpg", "alt": "<Bahasa Indonesia>", "illustrative": <bool>, "credit": { "photographer": "<nama>", "url": "https://www.pexels.com/photo/...-<id>/" } } }` dengan **37 kunci persis**:
  - `market/`: `nasi-kuning, brownies, keripik, kopi, kopi-aren, cabai, pot, sprei, telur, rajut, beras, laundry` (illustrative false)
  - `progress/`: `lahan, pondasi, dinding, kusen, atap, plester` (true)
  - `unit/`: `tipe-30, tipe-36, tipe-45` (true)
  - `promo/`: `pr-1` (tanda tangan dokumen, tangan saja), `pr-2` (kanopi & pagar rumah), `pr-3` (serah kunci rumah, tanpa wajah) (true)
  - `cctv/`: `teras-depan, taman-belakang, gerbang-utama, pos-satpam, taman-bermain, jalan-blok, lapangan, gerbang-belakang` (false) — sudut pandang tinggi ala kamera pengawas, siang hari
  - `facility/`: `lapangan, musala, balai, taman` (true)
  - `ticket/bocor-dapur` (plafon/dinding rembes) (true)

- [ ] **Step 1: Tulis tes `photos.test.js`** — `REQUIRED_KEYS` (37 kunci di atas) sama persis dengan `Object.keys(photos)`; tiap `src` cocok `/^\/rdg\/foto\/[a-z]+\/[a-z0-9-]+\.jpg$/`, berkasnya ada di `frontend/public` dan ≤ 150 KB; `alt` tidak kosong; `credit.url` diawali `https://www.pexels.com/photo/`; total ukuran ≤ 6 MB; setiap kunci `img` di fixture (`services/fixtures/*.js` dibangun lewat `buildInitialState`) ada di manifest.
- [ ] **Step 2: Jalankan, pastikan FAIL** (`photos.json` belum ada).
- [ ] **Step 3: Cari dan unduh foto.** Cari halaman foto Pexels lewat pencarian web (ID numerik di URL halaman), unduh dari `https://images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg?auto=compress&cs=tinysrgb&w=1200`, potong/ubah ukuran dengan PIL sesuai batasan, simpan. Utamakan nuansa Indonesia (makanan, rumah tapak sederhana, konstruksi bata merah, gerbang perumahan). **Lihat setiap foto** (lembar kontak) untuk memastikan cocok, tanpa wajah/merek. Tulis `photos.json` dan `FOTO-KREDIT.md` (tabel: berkas, deskripsi, fotografer, URL Pexels, lisensi Pexels).
- [ ] **Step 4: Jalankan tes, PASS.**
- [ ] **Step 5: Commit** `feat(prototype): kurasi 37 foto realistis lokal (Pexels) + kredit`.

### Task 2: Integrasi foto ke prototipe

**Files:**
- Create: `frontend/src/prototype/lib/photos.js`, `frontend/src/prototype/components/Photo.js`
- Modify: `components/Illustrations.js` (`StageIllustration`, `PromoIllustration`), `components/MarketIllustration.js`, `surfaces/partner/UnitArt.js`, `surfaces/resident/care/TicketPhoto.js`, `components/CameraView.js`, `surfaces/resident/care/Facilities.js`, CSS tema (kelas `.rdg-photo`, `.rdg-photo-tag`, filter CCTV)
- Test: `frontend/src/prototype/__tests__/photo-components.test.js`

**Interfaces:**
- Consumes: `photos.json` (Task 1).
- Produces: `getPhoto(key: string) → { src, alt, illustrative } | null`; `cctvKeyFor(cameraId: string, label: string) → string` (kunci `cctv/*`, pemetaan kata kunci label: teras/depan/pintu→`teras-depan`, belakang/kebun→`taman-belakang`, gerbang+belakang→`gerbang-belakang`, gerbang/portal→`gerbang-utama`, pos→`pos-satpam`, bermain→`taman-bermain`, jalan/blok/carport→`jalan-blok`, lapangan→`lapangan`; tak dikenal → salah satu dari 8 berdasar hash `cameraId`, deterministik); `Photo({ photoKey, alt?, className?, fallback, tag = true })` merender `<img>` (lazy, object-cover) + chip "Foto ilustrasi" bila `illustrative && tag`, dan merender `fallback` bila kunci tak ada atau `onError`.

- [ ] **Step 1: Tes gagal** — untuk `StageIllustration img="progress/atap"`, `PromoIllustration id="pr-2"`, `MarketIllustration img="market/telur"`, `UnitArt img="unit/tipe-36"`, `TicketPhoto img="ticket/bocor-dapur"`: ada `img` dengan `src` diawali `/rdg/foto/` dan alt tidak kosong; chip "Foto ilustrasi" ada untuk progres/promo/unit/tiket, tidak ada untuk pasar; `fireEvent.error(img)` → `img` hilang dan `svg` cadangan tampil. `CameraView label="Gerbang utama"` → `img` dengan `src` `/rdg/foto/cctv/gerbang-utama.jpg`, LIVE dan jam tetap ada; `cctvKeyFor("x","Kamera ruang tamu")` mengembalikan salah satu 8 kunci CCTV dan sama pada pemanggilan kedua; W25 menampilkan foto fasilitas. Tidak ada `src` berisi `http`.
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Implementasi.** Komponen lama mendelegasikan ke `Photo` dengan SVG lama sebagai `fallback` (tanda tangan prop tidak berubah, pemanggil tidak perlu diubah). CCTV: `filter: saturate(.7) contrast(1.08) brightness(.92)` + garis pindai yang sudah ada.
- [ ] **Step 4: PASS + suite prototipe penuh lulus** (tes lama yang mencari `svg` pada komponen ini disesuaikan).
- [ ] **Step 5: Cek visual** cepat (Playwright 390×844) P2, W2, W4, W5, W18, W21, W25, S4, M3 ke scratchpad; tidak ada overflow, chip terbaca (kontras ≥ 4,5:1).
- [ ] **Step 6: Commit** `feat(prototype): foto realistis di progres, promo, pasar, unit, CCTV, fasilitas`.

### Task 3: Screenshot semua halaman, nama jelas per peran

**Files:**
- Modify: `frontend/src/prototype/screens.json` (tambah `desc` tiap entri), `frontend/scripts/prototype-screens.js`, `docs/prototype/README.md`
- Create: `docs/prototype/screens/README.md`, `docs/prototype/screens/<NN-peran>/*.png`
- Delete: `docs/prototype/screens/*.png` (berkas datar lama)
- Test: `frontend/src/prototype/__tests__/screens-meta.test.js`

**Interfaces:**
- Produces (untuk Task 4): untuk setiap entri `screens.json` → `docs/prototype/screens/<folder>/<ID2>-<slug>.png` (halaman penuh) dan `<ID2>-<slug>--layar.png` (layar pertama: ponsel 390×844 @2x, pengelola 1366×900 @1x). `folder` per awalan ID: U→`01-demo`, P→`02-pembeli`, T→`03-serah-terima`, W→`04-warga`, S→`05-satpam`, K→`06-pengelola`, M→`07-mitra`. `ID2` = huruf + nomor dua digit (`W18`, `P02`, `U01`). `slug` = judul huruf kecil, aksen dibuang, "&"→"dan", karakter lain → "-", maks 40 karakter. Juga `docs/prototype/screens/index.json` = `[{ id, id2, title, desc, route, role, folder, full, first }]`.

- [ ] **Step 1: Tes gagal** — setiap entri `screens.json` punya `desc` 20–110 karakter, Bahasa Indonesia, tanpa "Ningrat"; fungsi `screenFileName(entry)` (ekspor dari modul kecil `frontend/scripts/screen-names.js`, dipakai skrip) menghasilkan nama unik untuk 59 entri (termasuk P10 vs W29) dan cocok `/^[A-Z]\d{2}-[a-z0-9-]+$/`.
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: Isi `desc`** dari tabel inventaris spek prototipe §7.3 (`docs/superpowers/specs/2026-11-25-aplikasi-penghuni-prototype-design.md`) — satu kalimat apa yang ditampilkan/dilakukan pengguna.
- [ ] **Step 4: Perluas skrip.** Halaman penuh: setel tinggi viewport = `document.documentElement.scrollHeight` (maks 8000 px) sebelum memotret agar elemen `fixed` tetap di bawah; layar pertama: viewport normal. Tetap ukur overflow di 360 px. Buat `00-lembar-kontak.png` per folder (render halaman HTML grid sementara di Playwright, label "ID · Judul" di atas tiap layar). Tulis `index.json` dan `screens/README.md` (tabel per peran: ID, Halaman, Penjelasan, Rute, tautan berkas).
- [ ] **Step 5: Build + jalankan skrip** → `59 layar, 0 overflow`; hapus PNG datar lama; perbarui tautan di `docs/prototype/README.md`; optimalkan PNG lossless; total `docs/prototype/screens` ≤ 40 MB.
- [ ] **Step 6: Lihat setiap lembar kontak** (foto realistis tampil, tidak ada konten terpotong/bertumpuk).
- [ ] **Step 7: Commit** `docs(prototype): screenshot halaman penuh + layar pertama per peran dengan nama jelas`.

### Task 4: PowerPoint gabungan deck Canva + Lampiran

**Files:**
- Create: `reports/deck_src/deck_lampiran.js`, `reports/deck_src/assets/canva/page-01.jpg … page-13.jpg`
- Create: `reports/Estora pitch deck + lampiran prototipe.pptx`, `reports/Estora pitch deck + lampiran prototipe.pdf`
- Modify: `reports/deck_src/README.md` (cara membangun)

**Interfaces:**
- Consumes: `docs/prototype/screens/index.json` + PNG `--layar` (Task 3); PDF Canva `/root/.claude/uploads/4c43c2dd-1aa7-553c-9e9f-59508645de56/8cf6efe0-Ini_hanya_sebagian_kecil_masalah_sederhana_yang_jarang_diperhatikan_developer..pdf` (13 halaman, 1440×810 pt); `reports/deck_src/lib.js` (`newDeck`, `txt`, `card`, `THEME`).

- [ ] **Step 1: Render PDF** → `pdftoppm -jpeg -r 96 -scale-to-x 1920 -scale-to-y 1080` ke `assets/canva/page-NN.jpg` (≤ 450 KB per halaman).
- [ ] **Step 2: Bangun deck (16:9, `LAYOUT_WIDE` 13,33×7,5 in).** Slide 1–12 = halaman Canva 1–12 gambar penuh (tanpa elemen lain). Halaman Canva 13 ("DRAFT LAMPIRAN") diganti **sampul Lampiran** bergaya Estora: judul "Lampiran — Prototipe Aplikasi Rumah Dalam Genggaman", subjudul "59 halaman · 7 peran · data contoh, tanpa backend", daftar kode lampiran A–G. Per peran: slide pembatas ("Lampiran D · Warga", kalimat peran, rentang ID) lalu slide isi: **3 layar ponsel per slide** (gambar `--layar`, sudut membulat, bayangan tipis) masing-masing dengan label di bawah: baris 1 tebal "W18 · Pasar warga", baris 2 penjelasan (`desc`), baris 3 kecil rute (`/app/warga/pasar`); judul slide "Lampiran D · Warga — W16–W18". Pengelola (K) **1 layar per slide** lebar penuh dengan label yang sama. Kode: A Demo & masuk (U), B Pembeli (P), C Serah terima (T), D Warga (W), E Satpam (S), F Pengelola (K), G Mitra (M). Penutup: slide "Daftar halaman" (tabel ID · Halaman · Lampiran-slide) bila muat, atau dipecah 2 slide.
- [ ] **Step 3: Ekspor PDF** `soffice --headless --convert-to pdf`; buat lembar kontak dari PDF (pdftoppm + PIL) dan **lihat semuanya**: label cocok dengan gambar, tidak ada teks terpotong/bertumpuk, halaman Canva utuh.
- [ ] **Step 4: Commit** `docs(reports): pitch deck Canva + lampiran screenshot prototipe (pptx & pdf)`.
