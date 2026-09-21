# LAPORAN SESI 2026-09-05 — GELOMBANG 2026-09 (INSTRUKSI_GELOMBANG_2026-09.md)

## 0. Verifikasi catatan (semua CEK ULANG dijalankan sendiri sebelum menyentuh kode)
| Butir | Vonis | Bukti |
|---|---|---|
| P-1 tag RFID diwariskan ke potongan | **SAH** | `insert_child_roll()` tidak me-reset `rfid_tag_id`; data demo sebelum perbaikan: **3 tag kembar aktif** (×4, ×3, ×2) |
| P-2 potong butuh klaim atomik | **SAH** | `list_available_rolls()` saring saat baca saja; `atomic_claim.py` sudah ada (INV-ATOMIC-01) |
| §3-A mobile tertinggal | **SAH** | `App.js` mobile hanya `role==="sales"`; 19 layar desktop vs 8 mobile; tak ada Minta Harga; label MTO≠OD |
| §3-B harga khusus berliku | **SAH** | `scope` bawaan `standing`; modal POS tanpa unggah/scope; endpoint attachments ada tapi tak dipakai POS |
| §3-C modul sampel | **SAH** | `md_samples` = sampel dari pemasok; belum ada layar potong; **DITUNDA** (keputusan pemilik: pilihan a) — 6 jawaban tercatat di bawah |
| Varian produk (tambahan pemilik) | **SAH, lebih buruk** | router `product-templates` (F1b) hidup tetapi **0 induk di DB, 6 `template_id` yatim**, warna disimpan di 5 field berbeda |

## 1. Gelombang 0 — SELESAI
- **P-1**: `insert_child_roll()` kini `doc["rfid_tag_id"] = None` (potongan = benda fisik baru → muncul di `/rfid/untagged-rolls`).
  Penjaga baru **INV-RFID-01** `scripts/guardrails/verify_rfid_tag_unique.py` (KODE K1 + DATA D1, `--self-test` 7 kasus) masuk `gate.sh`.
  Skrip **diagnosa saja** `scripts/diagnose_rfid_duplicate_tags.py` (tidak mengubah data). Data demo di-seed ulang sesudah perbaikan → 0 tag kembar.
- **P-2**: mekanisme klaim siap (`atomic_claim.claim/finish_set/release`); dipakai saat modul potong sampel dibangun.

## 2. §3-A Mobile SEMUA peran (pilihan a: satu cangkang bersama)
- `features/mobile/MobileShell.jsx` (bottom-nav per peran, escape-hatch ke desktop, logout).
- **Gudang** (`warehouse`, `warehouse_admin`, `driver`) → `MobileWarehouseApp`: Masuk · Keluar (tugas terbuka, satu kartu per tugas) · **Pindai** (verdict besar: ikon + teks: COCOK / TERIKAT PESANAN / TAG TIDAK DIKENAL) · **Belum Tag** (`/rfid/untagged-rolls`, termasuk potongan P-1).
- **Peran lain** → `MobileOpsApp`: Persetujuan (`/approvals/my-queue`) · Ringkas (`/dashboard`) · Desktop.
- **Sales** (Tahap 1): menu Lainnya + **Minta Harga Khusus** (komponen bersama §3-B), **Kunjungan Sales** (check-in/out `/hr/visits/*`), **Status Stok** (hanya-lihat); label "Pesanan Khusus (OD)" disamakan dengan desktop.
- Routing `App.js`: `wantMobile = (isMobile || kn_force_mobile) && !kn_force_desktop` untuk semua peran.

## 3. §3-B Harga khusus — keputusan pemilik: bukti WAJIB · bawaan "order" · isyarat %
- **Satu komponen** `features/pricing/SpecialPriceRequestForm.jsx` dipakai di 4 pintu: POS (`RequestSpecialPriceModal`), detail SO (`SoApprovalsPanel`), layar Persetujuan Harga (`PriceApprovals` — pengajuan baru; edit tetap form lama), mobile.
  Alur: draf → unggah bukti → submit; "Atur lebih lanjut" menyembunyikan min qty / berlaku sampai / "jadikan harga langganan".
- Backend: `PriceApprovalCreate.scope` bawaan **`order`**; `EVIDENCE_REQUIRED=True` → `submit_now` tanpa bukti **400 EVIDENCE_REQUIRED**, `/submit` tanpa lampiran **400**.
- **Penyimpangan sadar dari "jangan buat endpoint baru"**: `GET /price-approvals/hint` (hanya-baca; % di bawah daftar + verdict "biasanya disetujui/perlu manajer"; TIDAK memuat HPP/floor). Alasannya: penilai yang sama (`price_guard.evaluate`) harus dipakai agar isyarat tidak berbohong.

## 4. §D Varian produk — INDUK WAJIB (pilihan a)
- `services/product_variant_service.py`: `ensure_parent()` (tautkan/ciptakan induk dari nama), `resolve_orphans()` (idempoten), `family_summary()` (katalog & agregasi: varian + tersedia/dipesan + roll bertag).
- `POST /products` → induk otomatis (tak ada produk yatim); `GET /product-templates/{id}/summary`; `POST /product-templates/resolve-orphans`.
- Migrasi `scripts/migrate_products_to_templates.py` + dipanggil seed → **15 induk, 20 varian, 0 yatim**. FE: `TemplateFamilySummary` di layar Template Produk.
- Belum: pembersihan 5 field warna ganda pada `products` (variant/color/color_code/color_name/variant_label) — perlu migrasi terpisah karena dipakai PDF/label.

## 5. Tiga item lama
- **Paginasi layar SDM**: `AttendanceView` & `VisitsView` memakai envelope (`page/page_size`) + `KNPager`.
- **Ratchet INV-ATOMIC-01 55 → 54**: klaim `sales-returns/{id}/quarantine/release` (precondition `quarantine_released != True`).
- **5 gate merah pra-eksisting**: `overlayDismiss` di 3 modal, `useEscapeClose` di 2 layar, `KNMonthPicker` role=listbox + aria (E2), i18n 4 label (navMeta, RoleDesk, PdfTemplateDesigner).

## 6. Bukti
- `scripts/probe_sesi6_gelombang.py` **16/16 PASS**; `verify_rfid_tag_unique` PASS; `verify_atomic_claim` 31 cek PASS; `verify_data_integrity` 247/0.
- Testing agent: lihat `test_reports/iteration_317.json`.

## 7. §3-C — jawaban pemilik (untuk sesi berikutnya)
1) Dijual; **master harga sampel terpisah** dari master produk (induk beda, tetapi tersambung ke varian produk). 2) Tanpa batas. 3) Tanpa persetujuan.
4) Sisa potongan → terserah implementasi terbaik (rekomendasi: `is_remnant=True` bila < ambang, roll biasa bila ≥). 5) Saran roll FIFO. 6) Pindai roll sah bukan saran → boleh dengan alasan.
