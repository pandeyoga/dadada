# Kelanjutan 2026-09-06 (sesi 2) — sumbu varian terkonfigurasi & kain dasar

Sumber: https://github.com/pandeyoga/KNHOST (`main`), diimpor ke `/app` tanpa `.git`;
`.env` lokal dipertahankan (CORS_ORIGINS diisi eksplisit sesuai T-02).
Restore: `bash /app/.restore_env.sh` (seed_realistic gagal di ringkasan akhir `templates_created`
— KeyError kosmetik, data sudah tertulis; fondasi LENGKAP).

## Keputusan pengguna
- Sumbu varian bawaan: **Warna × Grade × Asal (Impor/Lokal)**. Ukuran/Material/Lebar tetap ada
  di kode sebagai sumbu OPSIONAL (diaktifkan lewat pengaturan). Material berbeda = induk berbeda.
- Kain dasar (base fabric) = picker dari SEMUA master data induk (popup + cari + filter woven/knit),
  ada opsi "— Tidak ada —"; ikut tersimpan ke spesifikasi R&D, induk, dan SKU (field baru).

## Implementasi
- Konfigurasi: `rnd.variant_axes_default` (list, default color/grade/origin) & `rnd.variant_axes_optional`
  (list, default []) di `config_catalog_rnd.py`; dibaca `services/variant_axes.py:axis_config`.
- `GET /api/product-catalog/meta` → `variant_axes {default, optional, catalog[{key,label,options,preset}]}`.
- Sumbu `origin` → `product.origin` (impor|lokal) via `catalog_rules.combination`; PATCH products
  menerima `origin` & `base_fabric_template_id`.
- Kain dasar: `services/base_fabric.py` (snapshot: `base_fabric_template_id/_name/_sku_prefix`;
  validasi ada & aktif; tidak boleh diri sendiri). Dipakai: create/patch template, generator varian
  (mewarisi induk), `product_variant_service.prepare` (validasi/inherit), `rnd_spec_service`
  (create/patch spec + `_product_draft`), skema `SpecInput/SpecPatch/ProductPayload/ProductTemplate*`.
- Frontend: `components/BaseFabricPicker.jsx` (Radix Dialog, testid `<prefix>-trigger/-dialog/-search/
  -type-*/-none/-option-<id>/-value`); dipakai `SpecFormModal` (`spec-base-fabric-*`, mewarisi jenis
  kain/gramasi/lebar yang kosong) & `FamilyForm` (`family-base-fabric-*`). `AxisEditor` membaca
  `axisConfig` (tombol preset dari konfigurasi, origin preset Impor/Lokal, grade preset A..BS);
  induk baru otomatis terisi sumbu bawaan. Tampilan: `SpecDetailPanel` (`spec-detail-base-fabric`),
  `CatalogWorkspace` (`catalog-family-base-fabric`, `family-base-fabric-text`), `ProductQuickView`
  (`quickview-base-fabric`), `MobileQuickView` (`mobile-quickview-base-fabric`), `VariantAxisPicker`
  label "Asal".
- Smoke test API: `python backend/tests/smoke_variant_axes_base_fabric.py` (ALL PASS).
