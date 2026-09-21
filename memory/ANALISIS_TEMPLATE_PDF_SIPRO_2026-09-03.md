# ANALISIS — Konfigurasi Template Dokumen PDF: `daseady/sipro` vs Kain Nusantara (sesi #086, 2026-09-03)

Permintaan pemilik: *"lihat mekanisme pengaturan dokumen/konfigurasi PDF di sipro, jangan diubah — analisis
dan improve minimal seperti yang ada di sipro."* Repo sipro di-clone (read-only) dan dipelajari:
`backend/doc_layout.py`, `doc_script.py`, `pdf_layout.py`, `routers/doc_layout_router.py`,
`frontend/src/components/master/DocLayoutPanel.js` (Fase 60/61/62/66 di `CODEBASE_MAP.md`).

## 1. Mekanisme sipro (ringkas)

| Aspek | sipro |
|---|---|
| **Lapisan konfigurasi** | Satu dokumen `document_layouts` per (organisasi, kode). Kode `__default__` = identitas & gaya bawaan SEMUA dokumen; kode template (`SPR_KPR`, `BAST`, `PO`, …) hanya menyimpan **yang berbeda** (`_merge` per kelompok `brand/options/table` + `sections/money_rows/signatures`). Ganti logo sekali → semua dokumen berubah; kolom TTD SPR tetap boleh berbeda dari BAST. |
| **Reset** | `DELETE /doc-layouts/{code}` membuang **override-nya saja**; dokumen terbit tidak berubah. `version/updated_at/updated_by` per kode. |
| **Naskah (script)** | `doc_script.py`: naskah per JENIS dokumen dengan placeholder `{{token}}`; kosakata diturunkan dari konteks mesin penerbit (bukan token bebas), `unknown_tokens()` menolak token liar saat simpan, `sample_script()` untuk pratinjau, chip placeholder + peringatan token asing **hidup saat mengetik** (`ScriptForm.js`). |
| **Kop/footer** | `header_mode`/`footer_mode` = `system` (dirakit dari identitas) atau `image` (kop buatan desainer); logo, footer text, `show_page_numbers`, watermark (teks/gambar + `opacity`), kertas & margin. |
| **Tabel** | `_table_default()`: `grid full|horizontal|none` (transparan untuk kertas berkop), `show_header`, `header_fill`, `zebra`, `total_highlight`, `font_size`, `grid_color`. |
| **Bagian & baris** | `sections[].visible/order`, `money_rows[]` (label/urutan/`hide_if_zero`/`manual`) — angka tetap milik mesin. |
| **Tanda tangan** | Judul/nama/jabatan, `show_stamp` + gambar cap, gambar TTD, `auto_from_issuer`; opsi `show_materai`/`materai_note`, `show_place_date`/`place`, `closing_note`, `show_generated_note`. |
| **Pratinjau** | Mesin cetak yang SAMA; `POST …/preview` menerima rancangan yang belum disimpan (+ `script` draf), opsional `document_id` = data nyata. |
| **RBAC & audit** | Baca = `documents:view`; ubah & pratinjau draf = `settings:update`; `audit_log` tiap simpan/reset. |

## 2. Kondisi KN sebelum sesi ini

Sudah ada `PdfTemplateDesigner` (6 tab) + `/api/pdf/*`: kertas/margin/font/warna, branding per **entitas** (nama/alamat/telp/NPWP/logo),
field tambahan & sembunyi, slot TTD, footer/watermark, pratinjau **data nyata** (lebih baik dari sipro), e-sign & QR jejak dokumen.
**Celah** vs sipro: (a) tidak berlapis — tiap jenis menyimpan konfigurasi penuh, tidak ada `__default__`, "reset" hanya lokal;
(b) tidak ada naskah ber-placeholder tervalidasi; (c) gaya tabel mati di kode; (d) tidak ada mode kop gambar / tanpa kop;
(e) tidak ada nomor halaman, tempat-tanggal, meterai, cap, catatan sistem; (f) bagian dokumen tidak bisa dimatikan; (g) tanpa versi/audit.

## 3. Yang diimplementasikan di KN (parity + tetap memakai mesin & desainer KN yang ada)

| sipro | KN sekarang |
|---|---|
| `__default__` + override per kode, `_merge` | `pdf_templates.doc_type="__default__"` menyimpan konfigurasi penuh; jenis dokumen menyimpan **diff** (`diff_cfg`) → efektif = bawaan kode → `__default__` → override (`merge_cfg`, kelompok bersarang `sections`/`table` digabung per kunci). |
| `list_targets()` (customized/version) | `GET /api/pdf/templates` → semua jenis + `customized/version/updated_at/updated_by`; `GET /templates/{code}` juga membawa `meta.override_keys` & `default_effective` (UI menandai kunci yang **menimpa**). |
| `DELETE` reset override | `DELETE /api/pdf/templates/{code}` + dialog konfirmasi ("Ikuti Bawaan" / "Setelan Pabrik"). |
| `doc_script` + `unknown_tokens` | `intro_text` & `closing_note` dengan `PLACEHOLDERS` dari konteks dokumen nyata (`{{nomor}} {{tanggal}} {{judul}} {{status}} {{perusahaan}} {{alamat_perusahaan}} {{npwp_perusahaan}} {{pihak}} {{alamat_pihak}} {{grand_total}} {{terbilang}} {{jumlah_baris}} {{hari_ini}}`); token asing → **400** saat simpan; tab **Naskah** dengan chip (klik = sisip di kursor) + peringatan hidup; `POST /templates/validate-script`. |
| header/footer mode | `header_mode system|image|none`, `footer_mode text|image|none`; branding + `header_image_b64`, `footer_image_b64`, `stamp_b64`, `tagline`, `email`, `website`. |
| `_table_default` | `cfg.table` {grid, show_header, header_fill, zebra, total_highlight, font_size, grid_color} → tab **Tabel**. |
| sections visible | `cfg.sections` {parties, meta, items, totals, notes, signatures, refs} — hanya tampil/sembunyi, nilai tidak diubah. |
| show_stamp / materai / place_date / closing / generated note / page numbers / watermark opacity | `signature_slots[].show_stamp` (cap dari branding), `show_materai`+`materai_note`, `show_place_date`+`place`, `show_generated_note`, `show_page_numbers` (`@bottom-right counter(page)/counter(pages)`), `watermark_opacity`. |
| audit | `audit("pdf_template_saved"/"pdf_template_reset")`, `version` naik tiap simpan. |

Tidak diubah dari KN (sudah lebih kuat dari sipro): pratinjau memakai **dokumen nyata** per entitas, branding **per PT**, e-sign/QR, unduh PDF.
Yang **belum** diambil dari sipro (tidak relevan/lebih besar): `money_rows` manual (KN: total dihitung resolver per dokumen), `auto_from_issuer`, watermark gambar, urutan bagian (drag-order).

## 4. Bukti
`backend/test_sesi086_poc.py` (layering, diff, token asing 400, pratinjau HTML mengandung naskah/tempat-tanggal/meterai/kop-none/zebra, PDF `%PDF`, reset);
gate `verify_data_integrity.py` 248 PASS (baru: INV-NUM-01/02); testing agent `test_reports/iteration_294.json`.
