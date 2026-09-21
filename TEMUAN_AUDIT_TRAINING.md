# TEMUAN AUDIT vs PANDUAN TRAINING MD/Admin Sales (2026-06)

> Sumber: `Panduan_Training_ERP_KainNusantara_MD_AdminSales_1.pdf`.
> Metode: 2 gelombang testing agent — `iteration_275` (alur Admin Sales: A/B/C/E/F,
> 44 case backend + UI) dan `iteration_276` (alur MD: D/G/H/I/J/K/L + data demo,
> 50 case backend + UI). Tes tersimpan di `backend/tests/test_iter275_*.py` &
> `test_iter276_*.py`. Status: **DITAMPUNG — belum ada perbaikan kode** (sesuai
> permintaan pemilik). Hasil ringkas: dari ±79 kasus dokumen, mayoritas
> SESUAI-DOKUMEN; di bawah ini hanya deviasinya.

## 🔴 KRITIS (perilaku sistem bertentangan dengan dokumen / kontrol bocor)

| # | Kasus | Temuan | Akar masalah | Status |
|---|-------|--------|--------------|--------|
| T1 | A4 | `POST /api/sales-orders/{id}/confirm` menerima SO yang **belum diverifikasi DAN belum disetujui manajer** (200, langsung `confirmed` + tugas gudang lahir). Bilah galat + tombol "Verifikasi sekarang" yang dijanjikan dokumen tidak pernah muncul. Persetujuan nilai/kredit manajer bisa dilewati total. | Gerbang `so_verify_service.assert_ready_to_confirm` bawaannya MATI (setting entitas), dan `confirm_order` mengizinkan transisi dari `reserved`. | ✅ **SELESAI 2026-06** — (a) default `sales_admin.require_verification_before_confirm` → **True** (`config_catalog_core.py`; tetap bisa dimatikan per entitas/global di Pusat Pengaturan); (b) `confirm_order` menolak 409 "belum disetujui manajer" bila status ≠ `approved` dan `approval_required`/ada approval menggantung — urutan gerbang: verifikasi → persetujuan → konfirmasi. FE: tombol "Verifikasi sekarang" hanya muncul bila galatnya soal verifikasi. POC `test_core_e8_desk_poc.py` disesuaikan (bawaan HIDUP). |
| T2 | Alur F | Antrean "Permintaan internal dari sales" di Meja Admin Sales menampilkan PIN + tombol **Tindak**, tetapi layar tujuannya KOSONG: list `[]`, detail & `/sources` 403, `/convert` 400. Alur F **jalan buntu** untuk Admin Sales — konversi antar-PT hanya bisa oleh manajer/admin. | `routers/internal_requests.py` `CROSS_ENTITY_ROLES`/`DECIDER_ROLES = ('admin','manager')` tanpa `sales_admin`, padahal docstring modul sendiri bilang convert pindah ke sales_admin (FASE E-8). Antrean meja (`work_desk_service`) memakai filter berbeda dari layar. | ✅ **SELESAI 2026-06** — `CROSS_ENTITY_ROLES`/`DECIDER_ROLES` += `sales_admin` di `routers/internal_requests.py`: meta `can_decide`/`can_pick_source` true, daftar memuat semua PIN entitas aktif, `/sources` 200, `/convert` lahir pasangan antar-PT. Sales tetap hanya-miliknya & tanpa rincian stok PT lain. |
| T3 | DD2 (bab 33.3) | Isolasi entitas **bocor di detail**: `GET /api/inspections/{id}` & `/pdf` membuka `KANDA/INS-00001` saat badan usaha aktif = KSC (akun multi-entitas spt manager@). Daftar sudah terisolasi, detail tidak. Akun 1-entitas benar (404). | `routers/inspections.py` memeriksa entitas yang BOLEH diakses akun, bukan `assert_entity_access` terhadap X-Entity-Id aktif (pola po_board). | ✅ **SELESAI 2026-06** — fungsi baru `entity_scope.assert_active_entity_access` (dokumen harus milik badan usaha AKTIF; mode `all` kembali ke pagar penugasan) dipakai `routers/inspections.py::_guarded` → detail & PDF `KANDA/INS-00001` dari konteks KSC = 404 untuk akun multi-entitas. |

## 🟠 TINGGI

| # | Kasus | Temuan |
|---|-------|--------|
| T4 | B6 | UI menjanjikan "memutuskan ulang akan menambah jejak baru", tetapi ketiga jalur pemenuhan dijawab 400 setelah keputusan pertama (reorder: PR terbuka; wait: tak ada barang masuk; interco: butuh sumber). Kartu Reorder tetap `available:true` walau pasti gagal. API juga hanya menyimpan 1 keputusan terakhir — klaim "jejak lama tidak dihapus" tak terbukti. |
| T5 | G7 | Dokumen: baris PO yang barangnya sudah diterima **terkunci dari revisi**. Kenyataan: amandemen baris ber-`received_qty` diterima (200) selama qty baru ≥ qty diterima; hanya qty < diterima yang ditolak. **✅ SELESAI 2026-09-02 (iter279)** — `_assert_received_line_locked` di `po_amendment_service.py`: qty/satuan/harga/diskon baris ber-penerimaan berubah → 400 "terkunci dari revisi"; UI `POAmendModal` menonaktifkan kolom baris tsb + ikon gembok. 16/16 pytest + UI PASS. |

## 🟡 SEDANG

| # | Kasus | Temuan |
|---|-------|--------|
| T6 | H5 | Pagar lini bekerja (papan menyusut, PATCH lini lain 403 ber-pesan benar), tetapi lencana **"akses lini terbatas" tidak tampil**: API mengirim `line_restricted` ARRAY, layar menunggu boolean (`po-board-line-restricted`). |
| T7 | L4b | Makloon hasil KURANG dari estimasi tetap menutup order (`completed`), bukan "Sebagian" — status dihitung dari tahap diterima, bukan kuantitas. Klaim selisihnya sendiri terbuka otomatis dengan hitungan benar.  **✅ SELESAI 2026-09-02 (iter280)** — `_recompute_status_and_costing`: klaim open/pending_approval menahan status `partially_received` + `completion_hold`; keputusan klaim (`_save`) membuka ke `completed`. Bonus: IssueModal tampilkan stok per gudang, 409 menuntun bila bahan kurang. |
| T8 | L5/PP | `GET /api/approvals/my-queue` tidak memuat `makloon_claim` (dan jenis lain yang ada di `/approvals/backlog`) — manajer bisa melewatkan klaim bila hanya memantau "Persetujuan Saya".  **✅ SELESAI 2026-09-02 (iter280)** — stage `makloon_claim` di APPROVER_MATRIX + `my_queue`; kartu "Klaim Selisih Makloon" di Persetujuan Saya dengan approve/reject per `step_seq`. |
| T9 | G2 | Saran Reorder memuat produk R&D yang PASTI ditolak saat dibuat PR ("belum dirilis ke produksi") dan tidak membawa `warehouse_id` yang diwajibkan PR/realize-PO. |

## 🟢 MINOR (kode)

| # | Temuan |
|---|--------|
| T10 | `POST /api/ar-receipts` menjawab 422 (validasi payload) sebelum cek izin — bentuk skema bocor ke peran tak berwenang; seharusnya 403 dulu. |
| T11 | Setelah approval kredit/harga diputuskan, SO auto-naik `approved`; tombol "Setujui nilai" manajer berikutnya menjawab 409 INVALID_TRANSITION — membingungkan. |

## 📘 TEMUAN DATA DEMO / DOKUMEN (bukan bug kode — pilih: perbaiki seed ATAU revisi dokumen)

| # | Temuan |
|---|--------|
| D1 | `sales@` (Ayu) hanya memiliki 1 pelanggan: **Toko Kain Sejahtera yang justru terblokir kredit**. Alur A "normal" tak bisa dijalankan persis dokumen dengan akun sales@ (Butik Bali dkk milik sales lain). |
| D2 | **Butik Bali Indah** disebut "aman untuk alur normal", tetapi setiap SO baru memicu approval kredit (proyeksi AR Rp203jt > limit Rp30jt). Tidak ada pelanggan KSC yang benar-benar bersih kredit. |
| D3 | Tidak ada produk demo ber-**minimum potong** → kasus A6 tidak dapat diuji/didemokan. |
| D4 | **Moda Surabaya Fashion** milik entitas KANDA — tidak terlihat dari KSC (isolasi benar), tetapi bab 33.4 tidak menyebutnya; trainer bisa bingung. |
| D5 | Galeri desain berisi **4 karya** (1 disahkan, 1 menunggu, 2 draf); dokumen bab 33.2 menyebut "2 artwork". |
| D6 | Dokumen tidak menyebut **pemisahan tugas**: pengaju PR/Spesifikasi R&D tidak boleh menyetujui dokumennya sendiri (403) — MD tunggal di demo harus memakai 2 akun. |
| D7 | OD di bawah ambang (Rp10jt) berhenti di `draft` tanpa antrean; dokumen tidak menjelaskan langkah lanjutannya. Status OD disetujui = `confirmed` (dokumen: "Disetujui" — beda label). |

## ✅ YANG TERBUKTI SESUAI DOKUMEN (ringkas)
- Orientasi & landing per peran (Meja Admin Sales 8 antrean + kotak batas wewenang, Meja Finance 5 antrean, Dasbor Manajer, Operasi Gudang, Performa Saya).
- Mode "Semua Entitas" hanya-baca dengan pesan menuntun (409).
- Alur A1 end-to-end (SO→verifikasi→ACC→konfirmasi→picking→SJ→diterima) — dengan catatan D1/D2.
- B1–B3 (backorder, dialog 3 jalan + alasan kartu), jalur reorder→PR.
- C1/C4/C5/C6 (harga khusus, kredit blokir, verifikasi "tidak menghalangi", tolak ACC nilai saat persetujuan menggantung).
- E (retur: alasan wajib, salesadmin tanpa tombol setujui) — minus jumlah retur demo.
- G1–G6 (saran reorder, PR→PO, alasan amandemen, sales 403).
- H1–H4, H6 (papan PO, chip gembok Inspect, nama sales runutan, tab knit kosong, urutan master).
- I1–I7 (spec, sample, lampiran wajib, supplier wajib, urutan jadi→kirim).
- J1–J6 (DSR 4 status, 4-vs-3 MD/desainer, alasan revisi wajib, so_id wajib).
- K1–K7 (tahanan warna, hanya manajer melepas, ambang 15 huruf di semua titik, gudang tanpa tombol SPK, rambu "sudah ada SPK").
- L1–L3, L5 (5 order, estimasi, klaim selisih + potong bon + skor mitra), D1–D6 OD.
- DD3 (produk eksklusif ENK-BALI-001 tersaring server) & DD4 (3 rantai SO→PR→PO ber-nama sales).

## Urutan pengerjaan
1. ~~T1 (gerbang confirm)~~ — SELESAI: gerbang default ON + gerbang persetujuan manajer.
2. ~~T2 (PIN sales_admin) + T3 (isolasi detail inspeksi)~~ — SELESAI.
3. ~~T4~~ (iter278) · ~~T5~~ (iter279) · ~~T7–T8~~ (iter280) — SELESAI. **BERIKUTNYA:** T9 (saran reorder R&D/warehouse_id), T10–T11; T6 sudah array-aware di `PoBoardView`.
4. Paket seed demo (D1–D5) supaya sesi training bisa mengikuti dokumen apa adanya.
