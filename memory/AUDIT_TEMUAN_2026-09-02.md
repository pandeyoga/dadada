# AUDIT TEMUAN — Sesi 2026-09-02 (FB-01 AI Galeri + FB-02 Logistik & turunannya)

> **Status: ✅ SELESAI (sesi #085, 2026-09-03)** — seluruh P0/P1/P2 di berkas ini dikerjakan & diverifikasi
> (POC `backend/test_audit_temuan_poc.py` 34/34; testing agent `test_reports/iteration_293.json` 19/19 backend + UI).
> Keputusan pemilik: P1-1 = sopir hanya MENULIS pada tugasnya (daftar/detail tetap seluas entitas);
> P1-3 = transisi balik `loaded→prepared` (manage, wajib alasan) + dialog konfirmasi. X-6 = konfirmasi saja (tidak diubah).
> Catatan implementasi: L-9/G-6 notifikasi in-app ke peran `sales`/`sales_admin` & `designer` per entitas (WA pelanggan tetap backlog);
> X-2 paginasi dilakukan bertahap di klien (50 baris) di atas endpoint yang sudah mendukung `page/page_size`.
> Temuan tambahan iter293 yang ikut diperbaiki: `ConfirmHost` membuang `description` (badan semua dialog konfirmasi kosong);
> bootstrap sopir tidak lagi memanggil `/document-templates` & `/uoms` (403 di console).
>
> ~~Status lama: DITAMPUNG — BELUM DIKERJAKAN.~~
> Sumber: testing agent iteration_291 (audit eksploratif, tanpa mengubah kode) + tinjauan kode mandiri.
> Sudah dikonfirmasi dan TIDAK perlu diulang: 403 bootstrap `/uoms` & `/document-templates` peran sempit; input ETA native;
> foto seed hitam; Gemini MODE DEMO (menunggu API key).

## P0 — Merusak aplikasi
| # | Modul | Temuan | Repro / RCA | Saran |
|---|---|---|---|---|
| P0-1 | Pengaturan → Master Data & Audit → tab **Audit** | Seluruh SPA **blank** saat tab Audit dibuka (semua nav hilang, harus reload). | `AdminView.jsx` merender `JSON.stringify(log.after).slice(0,240)`; 12 log seed (order_verified, ESCALATE, RESOLVE_ESCALATION, interco_transaction_invoiced, CREATE/COMPLETE/APPROVE, …) tidak punya `after` → `JSON.stringify(undefined)` = `undefined` → `.slice` melempar. Tidak ada error boundary. | `JSON.stringify(log.after ?? {})`; tambah **ErrorBoundary** di shell aplikasi agar 1 baris rusak tidak mematikan SPA. (Bug pra-eksisting, terungkap saat audit.) |

## P1 — Fungsional / keamanan data
| # | Modul | Temuan | Saran |
|---|---|---|---|
| P1-1 | Logistik · RBAC sopir | Sopir bisa **menulis** (foto, posisi, transisi) pada pengiriman yang **bukan tugasnya** (driver_user_id ≠ user), dan melihat/menyortir semua pengiriman entitas. Hanya `/my-route` yang mengecek kepemilikan. Izin hanya level peran (`logistics.update`). | Di `logistics_service`/router: bila `actor.role == "driver"` → wajib `doc.driver_user_id == actor.id` untuk photos/positions/transition/delete-photo; pertimbangkan daftar & detail sopir dibatasi ke tugasnya (atau `mine=true` paksa). |
| P1-2 | Surat Jalan / Pusat Dokumen | **Tidak ada indikasi** SJ sudah diangkut pengiriman logistik. Backend menyimpan `logistics_id/number/status` di `shipments`, frontend tidak pernah menampilkannya (0 hit). Permintaan awal FB-02 menyebut "di Surat Jalan". | Tampilkan chip `LG-xxxxx · status` pada daftar/detail SJ + tombol "Buka di Logistik" (deep-link sudah ada). |
| P1-3 | Logistik · state machine | Tidak ada jalur balik `loaded → prepared`. Salah tekan "Tandai Dimuat" (tanpa konfirmasi) hanya bisa diperbaiki lewat "Gagal kirim" → "Jadwalkan ulang" (mencemari riwayat). | Izinkan `loaded → prepared` (manage) dengan alasan; atau dialog konfirmasi sebelum "Tandai Dimuat"/"Berangkat". |

## P2 — Kualitas / UX / konsistensi
### Logistik
| # | Temuan | Saran |
|---|---|---|
| L-1 | **Tanggal "hari ini" memakai UTC** (`new Date().toISOString().slice(0,10)` di `DriverTodayPanel`, `DeliveryTable`; `now_iso()[:10]` di `summary.late`). Terbukti: header panel "2026-09-02" saat WIB sudah 03:00 tgl 03. Flag "Lewat ETA" & "terkirim hari ini" geser 1 hari pada 00:00–07:00 WIB. | Helper tanggal lokal Asia/Jakarta (FE: `toLocaleDateString("sv-SE",{timeZone:"Asia/Jakarta"})`; BE: zona waktu entitas/`ZoneInfo("Asia/Jakarta")`). |
| L-2 | `lat/lng` tanpa validasi rentang (999/−999 diterima) → marker/bounds Leaflet rusak; tidak ada endpoint hapus/koreksi posisi (posisi TEST_ dari pengujian permanen). | Validator `-90..90` / `-180..180`; endpoint `DELETE /positions/{id}` (manage) dengan audit. |
| L-3 | `/my-route` menerima id pengiriman delivered/completed → menulis `route_order` pada data mati. | Filter status aktif. |
| L-4 | Pesan error transisi `delivered`: tanpa POD & tanpa nama penerima hanya menyebut POD. Tombol "Tandai Terkirim" tidak disabled saat nama kosong. | Gabungkan pesan; disable tombol; prefill nama penerima dari `receiver_name_hint`. |
| L-5 | Pencarian hanya jalan saat **Enter** (tanpa tombol, tanpa debounce, placeholder tidak menyebut Enter). | Debounce 300 ms saat mengetik + tombol cari. |
| L-6 | Empty state hasil pencarian kosong memakai teks generik "Belum ada pengiriman — Buat pengiriman…" (menyesatkan); "Tampilkan semua" hanya saat filter status. | Empty state khusus "Tidak ada hasil untuk '…'" + tombol reset pencarian. |
| L-7 | Teks bantu "Wajib foto POD + nama penerima" berada di bawah tombol → mudah terlewat. Caption foto terpotong tanpa `title`. Tap target tombol reorder kecil di ponsel. | Pindahkan hint ke atas tombol / inline validation; `title` pada caption; tombol reorder ≥ 40px di mobile. |
| L-8 | `create_delivery` tidak memeriksa status Surat Jalan (misal belum dispatch/sudah dibatalkan). | Validasi status SJ yang boleh diangkut. |
| L-9 | Tidak ada notifikasi ke sales/admin sales saat pengiriman **gagal kirim** atau **terkirim** (mereka baru tahu bila membuka Logistik/Perjalanan Pesanan). | Notifikasi in-app (lonceng) + backlog WA pelanggan. |
| L-10 | Tidak ada konfirmasi pada aksi transisi (Dimuat/Berangkat/Terkirim/Selesai) — satu sentuhan, tidak bisa dibatalkan (lihat P1-3). | Dialog konfirmasi ringan pada aksi yang mengunci data. |
| L-11 | Escape pada modal detail juga menutup modal saat dialog `askReason` (Gagal kirim) terbuka. | Abaikan Escape saat dialog anak terbuka. |

### Galeri Desain & AI (FB-01)
| # | Temuan | Saran |
|---|---|---|
| G-1 | Hapus ilustrasi AI **tanpa konfirmasi**; seluruh "Diskusi arahan" pada ilustrasi itu ikut hilang tanpa peringatan. | ConfirmModal + peringatan jumlah komentar. |
| G-2 | Saat Integrasi AI `enabled=false`, badge `gallery-ai-status` tetap tampil "MODE DEMO/LIVE" padahal ada catatan "dinonaktifkan" → pesan bertentangan. | Badge "NONAKTIF" (abu). |
| G-3 | Panel Gemini: key dummy langsung berstatus **LIVE** tanpa validasi; tidak ada tombol **Uji koneksi**. | Endpoint `POST /admin/integrations/gemini/test` (panggil model ringan) + tombol uji; status LIVE hanya setelah lulus uji. |
| G-4 | Banner render demo (Pillow) ~kecil & caption ilustrasi terpotong tanpa tooltip; pratinjau maks 360px. | Perbesar font banner; `title` pada caption; tombol "buka ukuran penuh". |
| G-5 | Escape **tidak** menutup modal Kelola/Detail galeri (modal Logistik bisa) — inkonsistensi a11y. | Tambah handler Escape. |
| G-6 | Komentar ilustrasi tidak bisa diedit/dihapus; tidak ada badge jumlah komentar pada thumbnail; tidak ada notifikasi ke desainer saat atasan menulis arahan. | Badge jumlah komentar; hapus komentar sendiri; notifikasi in-app. |
| G-7 | Gambar sumber dikirim ke Gemini tanpa penyusutan (artwork 10 MB) & tanpa timeout; hasil selalu disimpan PNG penuh. | Resize maks 2048 px sebelum kirim; timeout 60 s; simpan JPEG/WebP bila bukan transparan. |
| G-8 | Tidak ada batas jumlah ilustrasi per desain / biaya (saat LIVE setiap klik = biaya API). | Batas per desain per hari + tampilkan estimasi biaya di panel Gemini. |

### Lintas modul / konsistensi
| # | Temuan | Saran |
|---|---|---|
| X-1 | Matriks izin (Pengaturan → Izin) menampilkan raw key kapital: "Logistics", "Makloon_order", "Process_recipe"; peran "Driver" (Inggris) padahal `roles.js` punya label "Sopir". | Peta label modul & pakai `ROLE_REGISTRY.label`. |
| X-2 | Nama aksi audit masih raw key (`logistics_status`, `design_gallery_ai_illustrate`, …) tanpa label Indonesia; `GET /audit-logs` mengembalikan 343 baris tanpa paginasi. | Peta label aksi + paginasi server. |
| X-3 | Label sidebar "Pengaturan & Maste…" terpotong tanpa tooltip. | `title` / label pendek. |
| X-4 | Lencana `new_in: "FB2"` peran sopir — konvensi lama memakai fase huruf ("D"); periksa tampilan lencana "Baru di …". | Samakan konvensi. |
| X-5 | Peran `driver` belum ada di `config_divisions` (divisi HR) → Profil Saya/HR untuk sopir mungkin tanpa divisi. | Tambah divisi "Logistik" bila HR memakainya. |
| X-6 | Beranda/landing sopir langsung ke Logistik (OK), tetapi tidak ada Beranda ringkas; menu hanya Logistik + Profil Saya (sesuai keputusan). | — (konfirmasi saja). |

## Konfirmasi positif (lulus audit)
- Alur FB-01 demo (mockup/modify), komentar, cover = artwork, blokir submit tanpa artwork — OK.
- RBAC sales/sales_admin (view only), warehouse/manager (manage), driver dibatasi entitas (403 lintas entitas) — OK.
- Tabel Logistik: sort, klik/Enter → detail, ETA terlambat, kartu mobile, deep-link dua arah Pesanan ↔ Logistik — OK.
- Peta GPS, Ambil GPS, Telepon/WA/Navigasi — OK. Tidak ada overflow horizontal pada 390 px.

## Data uji tersisa (bersihkan saat pengerjaan)
- Posisi `TEST_GPS Cikampek`, `TEST_GPS Tanpa Koordinat`, `Uji GPS Playwright`, `probe` pada KSC/LG-00007 (tidak ada API hapus posisi → via Mongo).
- Pengiriman uji KSC/LG-00004/00005/00006 (SJ-TEST01/02) boleh dipertahankan sebagai data demo.

> Catatan gate (sesi #085): `audit_config_wiring.py` kini mengenal `DEDICATED_UI` — scope `integrations` (API key Gemini/Anthropic,
> model, `daily_limit`) diedit lewat panel Integrasi AI, bukan Pusat Pengaturan; sebelumnya menyimpan konfigurasi Gemini dari UI
> membuat INV-CFG-01 merah (kunci dilaporkan HIDDEN). Self-test guardrail tetap PASS.
