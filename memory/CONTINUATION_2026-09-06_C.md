# Kelanjutan 2026-09-06 (sesi 3) — penutupan sesi: restore + verifikasi regresi

Sumber: https://github.com/pandeyoga/KNHOST (`main`, commit 593cb1b "initial commit"),
diimpor ke `/app` tanpa `.git`; `frontend/.env` lokal dipertahankan, `backend/.env`
CORS_ORIGINS diisi eksplisit (URL preview + localhost:3000) sesuai T-02.

## Pilihan pengguna
- Tutup sesi lalu saja: restore + verifikasi regresi + update PRD/handoff. **Tanpa fitur baru.**
- Untuk pekerjaan media varian nanti: tetap wrapper disk lokal (bukan object storage).
- Mockup AI: belum, unggah manual dahulu.

## Yang dilakukan
- `bash /app/.restore_env.sh` → fondasi LENGKAP, build FE OK.
- Perbaikan lingkungan (bukan fitur):
  - `frontend/package.json`: `start` → `node static_server.js` (supervisor `yarn start` sebelumnya
    FATAL karena `craco start`; `start:dev` tetap tersedia untuk dev-server).
  - `seed_realistic.py` baris ~7125: hapus `templates_created` (KeyError kosmetik yang membuat
    `_replant_bootstrap()` tidak pernah jalan → akun `md@` hilang sampai backend di-restart).
    Sesi ini akun md@/wh.admin@ ditanam ulang lewat `_replant_bootstrap()` langsung.
- Verifikasi: `backend/tests/smoke_variant_axes_base_fabric.py` **ALL PASS**; login 4 akun OK;
  `GET /api/product-motifs` 14 item, Polos pertama, tanpa duplikat; `variant_axes.default`
  = color/grade/origin. Testing agent `iteration_7.json` **semua lolos** (FamilyForm kategori
  wajib, KNSelect MD/R&D, edit induk lama TEST_BF_print tanpa error, katalog sales tampil).

## Catatan untuk sesi berikutnya
- FE tanpa hot reload: setelah ubah `frontend/src` jalankan `bash scripts/rebuild_frontend.sh`.
- Data uji TEST_* dari smoke/testing agent sudah dibersihkan (hanya ID uji).
- Backlog berikutnya (menunggu perintah): P1 media per varian (banyak foto/SKU, cover, urutan,
  tipe foto/mockup, disk lokal) + galeri sales; P0 kontrak kelahiran SKU & pencocokan varian sales.
