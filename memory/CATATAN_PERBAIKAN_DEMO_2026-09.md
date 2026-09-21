# Catatan Perbaikan ERP Kain Nusantara — Hasil Sesi Demo (15 butir)

Sumber: `Catatan_Perbaikan_ERP_KainNusantara.pdf` (diunggah pemilik 2026-09-02).
Status pengerjaan dicatat di kolom terakhir; butir "Perlu diputuskan" JANGAN masuk sprint sebelum dijawab.

| Kode | Butir | Sifat | Perlu diputuskan | Status |
|---|---|---|---|---|
| AS-01 | Persetujuan manajer setelah Admin Sales dihapus (matikan `sales.require_so_validation`, tetapkan ambang) | Pengaturan | Hanya persetujuan nilai, atau juga kredit & harga khusus? (saran: kredit & harga khusus tetap) | ✅ SELESAI (iter281) |
| AS-02 | PR dari keputusan pemenuhan boleh naik ke MOQ supplier; simpan qty-untuk-pesanan & qty-kelebihan-stok | Sedang | Otomatis atau ditawarkan ke Admin Sales? (saran: ditawarkan) | ✅ SELESAI 2026-09-02 (sesi #073) — `PATCH /purchase-requisitions/{id}/lines/{line_no}` naikkan qty beli (order_qty/extra_qty/qty_history), UI "ubah qty" di detail PR |
| AS-03 | Buka kunci reservasi SEBAGIAN pada SO pendingan: lepas roll, status SO tetap, tolak bila ATP tak cukup, catat siapa/kapan/alasan | Sedang | Wewenang Admin Sales atau manajer? Per baris atau seluruh SO? (saran: Admin Sales, per baris) | ✅ SELESAI 2026-09-02 (sesi #073) — `POST /sales-orders/{id}/items/{pid}/release-rolls` (izin inventory.pegging, alasan wajib, status SO tetap, jejak `reservation_releases`), UI "Lepas Roll" |
| MD-01 | Jenis barang **Benang** di spesifikasi R&D (isian khas benang, bukan gramasi/lebar) | Sedang | — (rancang bersama MD-02) | ✅ SELESAI 2026-09-02 (sesi #074) — SpecTarget stage `yarn` + isian khas benang (nomor/sistem/bahan/ply/puntiran/celup) di `SpecFormModal`; gramasi/lebar/EPI/PPI disembunyikan |
| MD-02 | Master data Benang (kategori jenis bahan: katun/poliester/rayon/campuran, dst.) | Sedang | Atribut lain: nomor benang & sistem (Ne/Nm/Denier/Tex), ply, arah puntiran, warna/status celup, supplier, satuan simpan? | ✅ SELESAI 2026-09-02 (sesi #074) — enum `yarn_material/yarn_twist/yarn_dye_status` + `yarn_ply` di `domain_registry`/`ProductPayload`; form Master Produk stage Benang menampilkan isian khas benang |
| MD-03 | Pratinjau gambar artwork & kotak warna saat memilih desain/warna di R&D | Ringan | — | ✅ SELESAI (iter281 + fix KNSelect Radix `opt.render` + artwork seed 480×360, 2026-09-02) |
| MD-04 | Hapus kolom target harga jual dari formulir spesifikasi R&D (data lama tetap) | Ringan | — | ✅ SELESAI (iter281) |
| MD-05 | Proofing: hasil cukup foto & catatan; labdip/handfeel tetap kolom ukur | Ringan | — | ✅ SELESAI (iter281; seed KPI & POC S disesuaikan 2026-09-02) |
| MD-06 | Riwayat labdip per barang/warna + kolom tanggal butuh + navigasi ke detail putaran | Sedang | "Tanggal butuh" per permintaan sample atau per putaran? | ✅ SELESAI 2026-09-02 (sesi #073) — `GET /rnd/labdip-history` + modal Riwayat Labdip (Pustaka Warna & detail sample), tanggal butuh per putaran (`due_date`), deep-link ke putaran |
| MD-07 | Nama warna ganda (nama pabrik + nama KN) di Pustaka Warna, pencarian kenali keduanya | Ringan | — | ✅ SELESAI (iter281; 5 warna seed ber-`factory_name` demo) |
| MD-08 | Kode/nama produk ganda (supplier ↔ KN) dipakai di pencarian katalog, PR/PO, penerimaan | Sedang | — | ✅ SELESAI 2026-09-02 (sesi #074) — `supplier_codes[]` (dari `supplier_items`) ikut di GET /products & /dashboard; kotak cari Master Produk + KNSelect `keywords` di PR/PO/amandemen mencari kode supplier |
| PB-01 | Blanket PO & Kontrak: termin, jatuh tempo, jenis bayar, PPN, harga include/exclude PPN → turun ke PO | Sedang | — | ✅ SELESAI 2026-09-02 (sesi #074) — kontrak blanket menyimpan `payment_term_code/payment_term`, `tax_mode`, `price_includes_ppn` → call-off/PO mewarisi + `payment_due_date` (ETA + net_days); `compute_tax(mode_override)` |
| PB-02 | Rekening bank supplier (bank, no. rek, pemilik, SWIFT, mata uang) + tampil di pembayaran | Ringan | — | ✅ SELESAI (iter281) |
| FB-01 | AI Galeri Desain: mockup & modifikasi artwork (versi baru, lewat pengesahan) | Besar | Layanan AI & biaya; siapa boleh; wajib disahkan? | ✅ SELESAI 2026-09-02 — Gemini Nano Banana Pro (`google-genai` langsung, `gemini-3-pro-image-preview`), MODE DEMO (render lokal) bila key kosong. KEPUTUSAN PEMILIK: hasil AI = berkas `kind: ai_illustration` (ILUSTRASI ARAHAN) pada desain yang sama — BUKAN versi baru & BUKAN artwork; tidak lewat pengesahan; desainer me-rework. `POST /design-gallery/{id}/ai-illustrate`, `GET /design-gallery-ai/status`, key di Pengaturan → Integrasi AI (`gemini_*`) atau env `GEMINI_API_KEY` |
| FB-02 | Delivery tracking: ekspedisi, resi, ETA, riwayat posisi di Surat Jalan & Perjalanan Pesanan | Besar | Manual atau integrasi ekspedisi? (saran: manual dulu) | ✅ SELESAI 2026-09-02 (sesi #077) — dikembangkan jadi **MODUL LOGISTIK** (`logistics_deliveries`, LG-): manual (ekspedisi+resi ATAU armada sendiri plat+sopir), tahapan Disiapkan→Dimuat(WAJIB foto muat)→Dalam perjalanan(posisi)→Terkirim(WAJIB foto POD+penerima)→Selesai / Gagal kirim; peran ke-8 `driver`; tampil di Perjalanan Pesanan (`journey.logistics`) |

## Urutan yang disarankan dokumen
1. AS-01 (pengaturan) · 2. MD-03, MD-04, MD-05, MD-07, PB-02 (ringan) · 3. AS-02, AS-03, MD-06, PB-01 (inti, setelah dijawab) · 4. MD-01, MD-02, MD-08 (master baru) · 5. FB-01, FB-02 (modul baru).

## Keputusan pemilik (2026-09-02)
- Mulai: Gelombang 1+2 (AS-01 + MD-03, MD-04, MD-05, MD-07, PB-02).
- AS-01: hanya persetujuan NILAI manajer yang dihapus; persetujuan KREDIT & HARGA KHUSUS tetap.
- AS-02: BUKAN kenaikan ke MOQ otomatis/ditawarkan — MD/pembelian boleh langsung MENAIKKAN qty beli pada PR/PO
  yang lahir dari SO (tidak di-lock ke qty SO), ditambah sesuai kebutuhan.
- AS-03: wewenang Admin Sales, bisa dipilih per baris.
- MD-06: "tanggal butuh" per PUTARAN labdip.
