# LAPORAN PERBAIKAN — 2026-09-05 — agen E1 (Emergent)

> Mengikuti `INSTRUKSI_PERBAIKAN_2026-09.md`. Semua klaim disertai perintah + keluaran.
> Lingkungan: kontainer Emergent `/app`, repo `snakissb/KN` @ `5c76055` di-clone lalu disalin
> ke `/app` (`.git` di `/app` adalah milik platform Emergent → commit per temuan TIDAK bisa
> dibuat manual; pemilik menyetujui: pemisahan per temuan cukup di laporan ini).
> Patch auditor (`audit-temuan-2026-09.patch`) diterapkan apa adanya; skrip verifikator
> identik byte-per-byte dengan artefak (`diff` kosong), segel tidak berubah.

## 1. Baseline

```
$ git -C /tmp/KN log -1 --format="%h %ci %s" | cut -c1-60
5c76055 2026-09-05 09:29:20 +0000 ## Pemilih Waktu Seragam — selesai
$ diff /tmp/audit_temuan.py scripts/audit_temuan_2026_09.py && echo SCRIPT_IDENTICAL
SCRIPT_IDENTICAL
$ python3 scripts/audit_temuan_2026_09.py ; echo "EXIT=$?"
  TERBUKTI (masih cacat) : 9
  GUGUR (bersih/sudah)   : 1        ← T-06 GUGUR PALSU: /app/.git milik platform (1 commit, hook template Emergent)
  RALAT (tak bisa diuji) : 0
  segel: sha256:c0baaa80a82dc16a
EXIT=1
$ python3 -m compileall -q backend ; echo "COMPILE_EXIT=$?"
COMPILE_EXIT=0
$ bash scripts/gate.sh --quick 2>&1 | tail -3
  ✗ ADA GATE MERAH.  20s
```

**Penyimpangan dari baseline auditor (10/0/0):** T-06 dibaca GUGUR oleh skrip karena
`/app/.git` bukan `.git` repo asli. Di clone asli: `ls /tmp/KN/.git/hooks/pre-commit` →
tidak ada; `git rev-list --count HEAD` → 4. Jadi T-06 secara substansi **TERBUKTI**.

**Gate `--quick` sudah MERAH di HEAD 5c76055** (bukan akibat pekerjaan ini) — 5 gate:
`guard:modal_dismiss` (3 modal), `guard:escape_layers` + self-test (2 berkas),
`ux_audit --strict` (KNMonthPicker), `audit_i18n_id` (4 temuan/3 berkas). Dicatat di §5, TIDAK diperbaiki (A0-7).

## 2. Hasil verifikasi ulang per temuan

| ID | Vonis saya | Bukti (perintah + keluaran) | Tindakan |
|----|-----------|------------------------------|----------|
| T-01 | **TERBUKTI** | `grep -rnE "start_session\|with_transaction\|start_transaction" backend --include=*.py \| grep -v /tests/` → kosong. `grep -n 'if not task.get("escalation")' backend/routers/outbound_picking.py` → 1 baris (244); `grep -n 'escalation.*status.*!=.*resolved'` → kosong. | Langkah 1 diperbaiki (klaim atomik) + probe runtime; Langkah 2 inventaris 87 endpoint; Langkah 3 BERHENTI → §7 |
| T-02 | **TERBUKTI** | `sed -n 111p backend/server.py` → `allow_origins=os.environ.get("CORS_ORIGINS", "*")`; `sed -n 114p backend/routers/auth.py` → `secure=False`; `find . -iname "*nginx*" -o -iname "Dockerfile*"` → kosong. | Diperbaiki (E-1, E-2, E-3) |
| T-03 | **TERBUKTI** | skrip: `to_list(>=20000): 63`, `router pakai pagination: 16/123`. `explain()` sebelum: `COLLSCAN` 65 dok. | Lapis 1–3 diperbaiki; Lapis 4 ditunda |
| T-04 | **TERBUKTI** | skrip: 95 kandidat; pemindai AST saya: 214 (superset: +async for, count_documents bersarang). | Langkah 1 tabel triase; TIDAK ada yang diperbaiki |
| T-05 | **TERBUKTI, dengan RALAT besar** | `corpus_summary.json` 122 skrip: **58 berkasnya sudah TIDAK ADA** di repo (dihapus/dipindah). Korpus nyata hari ini 220 skrip. Baseline berurutan: `total/ok/failed 220 78 142`; sesudah runner diperbaiki + urutan seed benar: `220 84 136`. | Runner permanen + triase 220 baris; 1 pemeriksa basi diperbaiki |
| T-06 | **TERBUKTI** (skrip: GUGUR palsu, lihat §1) | `ls /tmp/KN/.git/hooks/pre-commit` → tidak ada; `ls -a /tmp/KN/.github` → tidak ada; 4 commit. | `install_hooks.sh` + `.github/workflows/gate.yml` dibuat; **CI belum pernah dijalankan di GitHub** (tidak bisa dari kontainer ini) |
| T-07 | **TERBUKTI** | `ls backend/routers/*.py \| wc -l` → 124 (122 router + `__init__`/…); `grep -rhoE '@router\.(get\|post\|put\|patch\|delete)' backend/routers \| wc -l` → 1120; `grep -n SHA256 CODEBASE_MAP.md` → baris 143; `core_utils.py:336 hash_password → bcrypt`. | Generator + guard INV-DOC-01; peta digenerate |
| T-08 | **TERBUKTI** | `backend/routers/admin.py:405: os.environ.get("SEED_DEMO_ENABLED", "true")`. Pemanggil: hanya tombol Admin FE (`useAppActions.js:539`); `.restore_env.sh`/`seed_reset.sh` memakai `seed_realistic.py` langsung, BUKAN endpoint. | Diperbaiki satu baris + `.env` |
| T-09 | **TERBUKTI untuk lifecycle; GUGUR-SEBAGIAN untuk warehouse_id** | `sed -n 363p purchase_requisition_service.py` → tanpa filter lifecycle. `warehouse_id` di hilir: `schemas.py:838 PurchaseRequisitionCreate.warehouse_id: str = ""` (OPSIONAL) dan `ReorderSuggestions.jsx:78` UI sudah meminta pemilih gudang sebelum buat PR → PR dari saran **tidak** 400. Tidak ada aturan gudang default per produk (ROP global). | Lifecycle diperbaiki (3 mode); warehouse_id TIDAK diisi → §7 |
| T-10 | **TERBUKTI (runtime)** | `curl -X POST /api/ar-receipts` sebagai warehouse + `{"ngawur":1}` → `HTTP 422 {"detail":[{"type":"missing","loc":["body","customer_id"]...` | Diperbaiki (Depends) |
| T-11 | **TERBUKTI (runtime)** | SO `so_005` status `approved`; `POST /sales-orders/so_005/approve` (manager) → `HTTP 409 {"detail":{"code":"INVALID_TRANSITION",...}}` | Diperbaiki (idempoten) |

## 3. Perubahan yang dilakukan (dipisah per temuan)

### T-05 — runner + triase korpus (Gelombang 1)
- Berkas: `scripts/run_corpus.py` (baru, runner berurutan; mengisi `REACT_APP_BACKEND_URL` dari `frontend/.env`), `scripts/triase_korpus.py` (baru, vonis berdasar `RULES` tertulis), `memory/TRIASE_KORPUS_2026-09.md` (220 baris, nol sel kosong), `coverage_data/corpus_run_2026-09-05{,_baseline}.json` (yang lama TIDAK ditimpa), `scripts/verify_data_integrity.py` (pemeriksa **INV-GL-REV-01** basi diperbaiki).
- Hasil: LULUS 84 · LINGKUNGAN 58 · UJI BASI 2 · TIDAK TAHU 76.
- **Pemeriksa basi yang diperbaiki (bukan kode aplikasi):** `INV-GL-REV-01` hanya melihat JE `source_type=sales_order`, padahal KEB-PDPT tahap 2 (iter298/299) mengakui pendapatan per surat jalan (`shipment_revenue`, `ref.order_id`). Bukti-merah: gate `--full` di seed bersih → `[FAIL] INV-GL-REV-01: 3 SO terkirim TANPA jurnal pendapatan ['SO-0001','SO-0003','SO-0002']`, padahal `db.journal_entries.find({source_type:'shipment_revenue'})` → `{'source_id':'shp_166366082bfc','ref':{'order_id':'so_002'}}`. Kegagalan ini **berantai** ke ~14 POC (`invarian global tetap HIJAU` = memanggil pemeriksa yang sama). Sesudah: gate `--full` → `verify_data_integrity` PASS (lihat §6).
- Kegagalan korpus terbesar (LINGKUNGAN): **55 skrip** meng-hardcode URL preview lama (bukan env) → 404 ingress; **akun `md@`/`wh.admin@` hanya lahir dari bootstrap saat START**, `seed_realistic.py` menghapus `users` → tes iter295/301/302 gagal kecuali backend di-restart SESUDAH seed (dibuktikan: sesudah restart 3 berkas itu lulus 100%); blueprint gudang (`SRG-01`, `RCM-RETUR`) hanya ada via `POST /warehouse-sites/seed-blueprint`.
- UJI BASI (2): `test_price_approvals_supersede.py`, `test_price_approval_supersede_notification.py` — 403 "Pemisahan tugas: pengaju harga tidak boleh menyetujui pengajuannya sendiri" (aturan SoD approval harga). **Ujinya belum saya ubah** — butuh keputusan apakah uji harus memakai penyetuju lain atau mematikan sakelar (§7).
- BUG NYATA: **tidak ada yang bisa saya nyatakan** — 76 TIDAK TAHU belum dibaca satu per satu.

### T-06 — hook + CI
- `scripts/install_hooks.sh` (baru), `.github/workflows/gate.yml` (baru: `gate.sh --ci --quick` + verifikator + 2 guard baru + artefak receipt). **Hook tidak bisa dipasang/dibuktikan di sini** (`.git` milik platform). CI belum pernah hijau — belum ada run.

### T-02 — CORS + cookie + `.env.example`
- `backend/server.py` (gagal berisik tanpa `CORS_ORIGINS`; `*` dilarang), `backend/routers/auth.py` (`COOKIE_SECURE`/`COOKIE_SAMESITE` dari env, bawaan Secure), `backend/.env.example` (baru), `backend/.env` dev: `CORS_ORIGINS=<preview>,http://localhost:3000`, `SESSION_COOKIE_SECURE=false`.
- Bukti sesudah: `CORS_ORIGINS=" " python3 -c "import server"` → `RuntimeError: CORS_ORIGINS wajib di-set…`; `CORS_ORIGINS='*'` → `RuntimeError: CORS_ORIGINS='*' dilarang…`; login dev → `HTTP/1.1 200 OK` + `set-cookie: session_token=…; HttpOnly; Max-Age=86400; Path=/; SameSite=lax` (tanpa Secure karena env dev=false); preflight `Origin: https://evil.example` → tidak ada `access-control-allow-origin`. Verifikator: `[GUGUR] T-02`.

### T-08 — `SEED_DEMO_ENABLED`
- `backend/routers/admin.py:405` bawaan `"false"`; `.env` + `.env.example` `SEED_DEMO_ENABLED=true`. Bukti: dengan env true + token salah → `HTTP 400 Confirm token tidak sesuai` (flag lolos); tanpa env → cabang 403. Verifikator: `[GUGUR] T-08`.

### T-07 — generator peta + INV-DOC-01
- `scripts/gen_codebase_map.py` (baru), `scripts/guardrails/verify_codebase_map.py` (baru, self-test 6 kasus dua arah), `CODEBASE_MAP.md` digenerate (122 router · 1120 endpoint · 189 service · 124 koleksi; `hash_password() | SEC-1 — bcrypt`), `memory/INVARIANTS.md`, `scripts/gate.sh`.
- **Catatan verifikator:** pemeriksa T-07 di `audit_temuan_2026_09.py` TERBUKTI selamanya karena `aktual_router > 60` → tidak bisa hijau untuk repo ini (pemeriksa buta ke arah hijau). Saya TIDAK mengubahnya (A0-3); bukti hijau/merah dipindah ke INV-DOC-01 (`--self-test` HIJAU 0 gagal; peta lama v1.0 → MERAH).

### T-11 — approve idempoten
- `backend/routers/sales_orders_extra.py` `approve_order`. Sesudah: `POST /sales-orders/so_005/approve` → `HTTP 200 {'status':'approved'}`; gerbang tetap: `so_001` (done) → `HTTP 409 INVALID_TRANSITION`; roll `so_005` tidak berubah. `waiting_stock` di jalur manual **tidak** disamakan (belum dipahami alasannya → §7).

### T-09 — saran reorder sadar-mode
- `backend/services/purchase_requisition_service.py` (`rnd_gate.enforcement_mode` · `is_orderable` · field `lifecycle`, `lifecycle_warning`), `frontend/src/features/purchasing/ReorderSuggestions.jsx` (lencana `reorder-lifecycle-badge-*`), probe `backend/tests/iter313_t09_reorder_lifecycle_probe.py`.
- Bukti: `mode=block labdip_muncul=False produksi_muncul=True → PASS` · `mode=warn labdip_muncul=True warning=True → PASS` · `mode=off labdip_muncul=True warning=False → PASS`; mode dipulihkan, produk uji dihapus.

### T-10 — 403 sebelum 422
- `backend/routers/ar_receipts.py` (`Depends(_perm_ar_receipt_create)`). Sesudah: warehouse+ngawur → `HTTP 403 {"detail":"Permission ditolak: ar_receipt.create"}`; finance+ngawur → `HTTP 422` (validasi tetap); `INV-AUTH-01` tetap PASS (1112 cek). Daftar saudara (459 endpoint sepola) **tidak** saya saring tiga syarat — belum dikerjakan.

### T-03 — Lapis 1–3
- `backend/services/stock_analytics_service.py` (2 query: filter `movement_type` dipindah ke query + proyeksi; **filter tanggal SENGAJA tetap di Python** karena `last_sale_days` dihitung dari seluruh riwayat — memindahkannya mengubah hasil), `scripts/guardrails/verify_to_list_bound.py` (INV-PERF-01, ratchet, self-test 11 kasus), `INVARIANTS.md`, `gate.sh`.
- Bukti: `explain()` SEBELUM `stage=COLLSCAN dokumen=65` → SESUDAH `IXSCAN index=kn_movement_type_1__timestamp_-1 dokumen=6`; hasil `product_sales_velocity` lama vs baru `identik=True` untuk None/ent_ksc/ent_kanda. Guard: MERAH sebelum (`stock_analytics_service.py:75,128,148`) → HIJAU sesudah; 18 lokasi warisan di ALLOWLIST ber-alasan "hutang T-03".

### T-04 — triase
- `scripts/triase_nplus1.py` + `memory/TRIASE_NPLUS1_2026-09.md`: 214 kandidat · PERBAIKI 2 (`reporting.py:44`, `admin.py:160` — dibaca manusia) · BIARKAN (sengaja) 5 · BIARKAN (loop kecil) 3 · **TIDAK TAHU 204**. Nol perbaikan.

### T-01 — Langkah 1 + 2
- `backend/routers/outbound_picking.py`: tolak 409 bila `escalation.status ∈ {resolved, resolving}`; klaim atomik `find_one_and_update(... escalation.status $nin [...] → resolving)` SETELAH semua validasi 400 dan SEBELUM pelepasan roll; penutup bersyarat `escalation.status != resolved`.
- Bukti runtime (`backend/tests/iter313_t01_resolve_escalation_probe.py`, snapshot/restore eksak): `panggilan 1 HTTP 200 held 25→20` · `panggilan 2 HTTP 409 held 20 (tidak berubah)` · `escalation.status=resolved, task packing` → PASS 5/5. **Bukti-merah SEBELUM hanya statik** (verifikator + baca kode) — probe tidak dijalankan pada kode lama.
- Langkah 2: `scripts/inventaris_multi_koleksi.py` → `memory/INVENTARIS_MULTI_KOLEKSI_2026-09.md`: **87 endpoint** (router + 1 tingkat service; >1 tingkat TIDAK ditelusuri → masih undercount). Klasifikasi: AMAN 1 (resolve-escalation) · TIDAK RELEVAN 4 · **BELUM DITINJAU 82**.

## 4. Yang TIDAK saya kerjakan dan kenapa
- T-01 Langkah 3 (replica set vs saga) — keputusan pemilik (§7). `inbound_receiving.py resolve-escalation` berpola sama — di luar cakupan Langkah 1, tercatat §5.
- T-03 Lapis 4 (paginasi `product_traceability`/`hr_attendance`/`hr_tracking`) — satu per commit, belum.
- T-04 Langkah 2 (perbaikan `PERBAIKI`) — sengaja tidak, sesuai instruksi "tabel dulu".
- T-05: 76 skrip `TIDAK TAHU` belum dibaca satu per satu; 55 skrip URL-hardcoded tidak saya ubah (index `tests/INDEX.md` menyebut "arsip bukti fase — jangan dihapus"; mengubah 55 berkas = keputusan pemilik); 2 UJI BASI belum disesuaikan.
- T-06: hook & CI tidak bisa dibuktikan berjalan dari kontainer ini.
- T-09 `warehouse_id` — tidak diisi (tidak ada aturan gudang default; hilir tidak mewajibkan).
- T-10 daftar saudara — populasi 459 tidak disaring.
- 5 gate `--quick` merah pra-eksisting — di luar 11 temuan.

## 5. Temuan BARU (dicatat, TIDAK diperbaiki)
1. `seed_realistic.py` membersihkan 89 koleksi tetapi meninggalkan **42 koleksi berisi** (mis. `invoices`, `logistics_deliveries`, `entity_prices`, `rfid_*`, `penalties`, `special_orders`, `config_values`, `hr_*`). Akibat terukur: gate `--full` sesudah korpus berjalan → `audit_entity_isolation KEBOCORAN: 1 (/api/invoices)`, POC E-4 "Kanda memakai harga sendiri: None", 20 gate merah; di DB yang **di-drop** lalu di-seed → hanya 5 merah pra-eksisting. Gate `--full` harus dijalankan di DB drop-bersih, bukan sekadar `seed_realistic`.
2. Urutan `.restore_env.sh` [4] restart backend → [5] seed: bootstrap membuat `md@`/`wh.admin@` dan `config_values`/aturan approval, lalu seed **menghapus** `users` → akun itu hilang sampai restart berikutnya (`seed_realistic.py:52` daftar clear memuat `users`; `bootstrap.py:1529–1536`).
3. `backend/routers/inbound_receiving.py:210` `resolve-escalation` inbound: penjaga yang sama lemahnya dengan T-01 (belum diperiksa lebih jauh).
4. Pemeriksa T-07 di `scripts/audit_temuan_2026_09.py:287` (`or aktual_router > 60`) tidak pernah bisa GUGUR.
5. Gate statik merah pra-eksisting di 5c76055: `FeedbackFormModal.jsx:59`, `ReleaseRollsModal.jsx:39`, `PrLineQtyModal.jsx:31` (INV-UI-01); `SalesForceDashboard.jsx`, `DeliveryCreateModal.jsx` (INV-UI-10); `KNMonthPicker.jsx` (INV-UX-01); `audit_i18n_id` 4 temuan/3 berkas.
6. `scripts/verify_data_integrity.py:4542` `F402` shadowing `field` (lint, pra-eksisting).
7. Ingress preview Kubernetes MENIMPA `Set-Cookie` (menambah `Secure; SameSite=None; Partitioned`) dan memaksa `Access-Control-Allow-Origin: *` pada preflight — perilaku aplikasi T-02 hanya bisa diamati langsung di `http://localhost:8001` (temuan testing agent iteration_313). Di produksi tanpa ingress itu, kode aplikasi yang berlaku.
8. `backend/test_audit_temuan_poc.py:49` crash `TypeError: 'NoneType'` bila tidak ada shipment `dispatched` tersisa — POC bergantung urutan.

## 6. Verifikasi akhir
Lihat blok `VERIFIKASI AKHIR` yang ditempel di bawah (diisi dari keluaran perintah).

### Uji independen (testing agent, `test_reports/iteration_313.json`)
`backend/tests/test_iter313_audit_fixes.py` 17/17 PASS + probe T-01 PASS + probe T-09 PASS · nol regresi pada endpoint yang disentuh · nol data tertinggal.

## 7. Pertanyaan untuk pemilik
1. **T-01 Langkah 3:** Opsi A (replica set single-node + transaksi Mongo — perubahan infrastruktur `MONGO_URL`, semantik paling benar, biaya: setup replSet di semua lingkungan + refactor 82 endpoint bertahap) vs Opsi B (saga eksplisit: kunci idempotensi + klaim atomik seperti Langkah 1, ditegakkan guard baru `INV-ATOMIC-01`; tanpa perubahan infra, tapi 82 endpoint harus ditinjau satu per satu). Mana?
2. **T-05:** bolehkah 55 skrip berURL-hardcoded diubah membaca `REACT_APP_BACKEND_URL` (perubahan mekanis 55 berkas), atau dipindah ke `scripts/_legacy/`?
3. **T-05 UJI BASI:** untuk 2 uji approval harga — ubah uji memakai penyetuju berbeda (`manager@`) atau matikan sakelar SoD di awal uji?
4. **T-09:** apakah saran reorder harus membawa `warehouse_id`? Jika ya, aturannya apa (gudang dengan saldo terbanyak? gudang default badan usaha?).
5. **T-11:** jalur otomatis menerima `waiting_stock`, jalur manual tidak — disengaja?
6. **Temuan baru 1–2:** apakah `seed_realistic.py` boleh membersihkan 42 koleksi sisa dan menanam ulang akun bootstrap (`md@`, `wh.admin@`), atau `.restore_env.sh` diubah ke urutan seed → restart?

### VERIFIKASI AKHIR (ditempel apa adanya)

```
$ python3 scripts/audit_temuan_2026_09.py
[TERBUKTI] T-01 — Tidak ada transaksi MongoDB (atomisitas lintas dokumen)
[GUGUR   ] T-02 — CORS default '*' + cookie sesi non-Secure (hardcoded)
[TERBUKTI] T-03 — to_list(>=20000) & paginasi belum merata
[TERBUKTI] T-04 — Kandidat N+1: query BACA di dalam loop atas data
[GUGUR   ] T-06 — Tidak ada CI otomatis + riwayat git tergencet
[TERBUKTI] T-07 — CODEBASE_MAP.md melenceng dari kenyataan
[GUGUR   ] T-08 — SEED_DEMO_ENABLED bawaan 'true' (reset DB hidup by default)
[TERBUKTI] T-09 — Saran reorder: tanpa filter lifecycle + tanpa warehouse_id
[GUGUR   ] T-10 — POST /ar-receipts: 422 mendahului 403 (bentuk skema bocor)
[TERBUKTI] T-11 — approve_order -> 409 INVALID_TRANSITION setelah SO auto-approved
  TERBUKTI (masih cacat) : 6
  GUGUR (bersih/sudah)   : 4
  RALAT (tak bisa diuji) : 0
  segel: sha256:c0baaa80a82dc16a

$ bash scripts/gate.sh --full   # DB di-DROP → restart backend → seed_realistic → restart backend → gate
merah di 5c76055 (DB bersih, SEBELUM perbaikan) : 21 gate
merah SESUDAH perbaikan (DB bersih)             : 13 gate — semuanya subset dari daftar sebelum (nol regresi)
sembuh (8): POC FASE F · G-2 · G-4 · G-7 · G-8 · G-9 · verify_data_integrity ×2 (akar: pemeriksa INV-GL-REV-01 basi)
masih merah (pra-eksisting): POC F-2 Akses & UI/UX per peran ·POC FASE E-8 G2/G3 ·POC FASE F-6.7 ·POC FASE G-3 ·POC FASE G-6 ·POC FASE G-6b ·POC FASE P ·audit_i18n_id ·audit_sales_roles_ux ·guard:escape_layers ·guard:escape_layers SELF-TEST ·guard:modal_dismiss ·ux_audit --strict ·
guard baru: guard:to_list_bound PASS · guard:codebase_map PASS (+ self-test keduanya PASS)

$ bash scripts/gate.sh --quick | tail -2
  HIJAU — penjaga terbukti menuduh endpoint tanpa auth dan menerima ketiga enforcer keras.  ✓ guard:auth_c
→ Perbaiki sesuai INVARIANT INV-UI-01 (detail: memory/INVARIANTS.md).  ✗ guard:modal_dismiss (INV-UI-01, m
  HIJAU — penjaga terbukti menuduh form yang menyelip.  ✓ guard:create_modal SELF-TEST (bukti-merah penjag
  HIJAU — penjaga terbukti menuduh dialog peramban DAN tidak menuduh palsu string/komentar/fungsi senama.  ·
  HIJAU — penjaga terbukti menuduh pager tanpa Unduh, tidak menuduh palsu komentar/string/komponen senama, D
  HIJAU — penjaga menangkap panel yang diselipkan di bawah daftar (termasuk dua kasus yang PERNAH ia lewatka
  HIJAU — penjaga menangkap pop-up yang lahir di dalam <label> (3 bentuk render) tanpa menuduh pop-up murni,
    ✗ features/logistics/DeliveryCreateModal.jsx: memasang pendengar `keydown` + `"Escape"` sendiri. Pakai `
→ Perbaiki sesuai INVARIANT INV-UI-10 (detail: memory/INVARIANTS.md).  ✗ guard:escape_layers (INV-UI-10, E
  HIJAU — audit terbukti menangkap gap nyata tanpa menuduh komponen penampil.  ✓ ux_audit SELF-TEST (bukti
    · components/KNMonthPicker.jsx  ✗ ux_audit --strict (INV-UX-01, loading/empty/chart baseline) FAIL (rc=
  ✗ 4 temuan di 3 berkas.  ✗ audit_i18n_id (label antarmuka Bahasa Indonesia) FAIL (rc=1) (1s)
  ✓ SELF-TEST HIJAU — guardrail terbukti bisa memerah.  ✓ audit_i18n_id SELF-TEST (bukti-merah guardrail
  ✓ SELF-TEST HIJAU — codemod hanya menyentuh teks pengguna.  ✓ fix_i18n_id SELF-TEST (codemod tak boleh
  HIJAU — pagar terbukti bisa memerah.  ✓ guard:write_scope SELF-TEST (INV-ENTITY-02, mode gabungan hanya-
  HIJAU — semua endpoint tulis pemilih gudang berpagar.
  HIJAU — gate terbukti bisa memerah.  ✓ guard:warehouse_scope SELF-TEST (E4.1, gudang khusus badan usaha)
  ✗ ADA GATE MERAH.  21s · Lihat detail di atas & memory/GATE_RECEIPT.md

$ python3 scripts/run_corpus.py   (berurutan, DB bersih + restart sesudah seed)
total/ok/failed/timeouts: 220 84 136 0
triase: LULUS 84 · LINGKUNGAN 58 · UJI BASI 2 · TIDAK TAHU 76  → memory/TRIASE_KORPUS_2026-09.md
```
