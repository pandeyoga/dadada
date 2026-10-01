# SIPRO — Property Development OS (lanjutan)

## Problem Statement (dari user)
Melanjutkan development dari repo https://github.com/pandeyoga/dadada. Tiga hal:
1. BUG hak akses/role: user biasa (mis. Site Engineer) yang sudah diberi akses tetap tidak
   melihat tombol "Mulai kerjakan"/"Ajukan hasil + bukti" pada jadwal pembangunan unit,
   sementara Admin melihatnya.
2. Hak akses per-halaman lebih detail: khusus RAB/BoQ, ada peran yang hanya boleh melihat
   sebagian bagian (mis. hanya "Umum", atau "Fasum/Fasos" saja, atau beberapa).
3. UI konfigurasi hak akses lebih ramah: pilih SATU peran lalu atur peran itu saja dengan
   grouping per modul + toggle (bukan matriks besar). Backward-compatible dengan data
   produksi hak akses yang sudah ada.

## Arsitektur
- Backend FastAPI (router modular), MongoDB (Motor). RBAC matrix di `rbac.py` +
  `rbac_matrix.py` (DEFAULT_PERMISSIONS) + peran kustom (koleksi `roles`).
- Frontend React + Tailwind + shadcn/ui. Auth JWT (Bearer); `AuthContext.can()` membaca
  izin efektif dari `/auth/me`.
- Preview env: `SEED_DEMO_USERS=true`, `JWT_SECRET`, `SUPERADMIN_*` di backend/.env.

## User Personas
Super Admin/Owner (akses penuh), Sales/Manager/Marketing, Finance/Finance Manager,
Project Manager (verifikator), Site Engineer (pelaksana), + peran kustom.

## Core Requirements (statis)
- Hint UI harus = penegakan backend (`require_permission`).
- RBAC dapat dikonfigurasi admin & mendukung peran kustom.
- Backward compatible dengan data produksi.

## Implemented (2026-06)
- FIX tombol build: `build_router._can()` async & diturunkan dari matriks RBAC
  (`rbac.can`): submit=construction:update, verify=construction:approve,
  configure=construction:create. `BuildItemCard.canWork` mengizinkan item yang BELUM
  ditugaskan (mine || !assigned_to || verify) + hint saat item milik orang lain.
- FITUR akses BAGIAN RAB granular: `backend/rab_sections.py` (key `rab_section_access`,
  bagian: unit/fasum/umum/summary). Default tanpa entri = semua bagian (backward compatible).
  Ditegakkan di `boq_router.list_items` (scope), `rab_router` (templates=unit, summary),
  disurface ke `/auth/me` (`rab_sections`). Frontend `BoQPage` menyembunyikan sub-tab.
  Endpoint admin: GET/PUT `/api/admin/rab-sections`.
- FITUR UI per-peran: `RolePermissionEditor.js` + mode "Per Peran"/"Matriks" di
  `AdminPermissions.js`. Pilih 1 peran → toggle aksi per modul + kartu akses bagian RAB.
  Matriks lama tetap tersedia. Satu tombol Simpan menyimpan matriks + akses RAB.
- Diverifikasi testing agent: 11/11 backend PASS, frontend PASS.

## Backlog / P1-P2
- P2: Sub-akses granular untuk halaman lain (di luar RAB) bila diminta.
- P2: Preset akses bagian RAB (template cepat) & bulk apply antar-peran.
- P2: Ringkasan akses bagian RAB di layar Profil pengguna.

## Test Credentials
Lihat `/app/memory/test_credentials.md`.

## Next Tasks
- Menunggu review user atas 3 perubahan; lanjut per feedback.


## 2026-06 — Impor Leads via Excel (bug fix)
- Template migrasi master kini punya sheet **Leads** (kunci: No. HP) → handler `h_leads` (stage acquisition, auto-assign sales, skor, HP +62, upsert per HP).
- Impor mentah "Semua Data" (sheet `leads`, id kosong) kini mengisi default lead (`_lead_defaults` di data_mgmt_full_session.py).
- `BACKUP_DIR` ditambahkan ke backend/.env (preview). Di VPS sudah diset lewat docker-compose.
- Diverifikasi testing agent: 7/7 pytest lulus (/app/test_reports/iteration_42.json).

## 2026-06 — Impor Leads langsung di halaman Leads
- Tombol **Impor Excel** (/leads, izin leads:create) → dialog unduh template, unggah .xlsx/.csv, pratinjau dry-run (Baris/Baru/Diperbarui/Error), commit.
- Endpoint: `GET /api/leads/import-template.xlsx`, `POST /api/leads/import-file` (multipart, dry_run). Sales cakupan-sendiri → lead ditugaskan ke dirinya.
- Menerima template Leads, CSV (Nama;No. HP), dan sheet `leads` dari ekspor Semua Data.
- Diverifikasi testing agent (iteration_43): backend 8/8 + UI superadmin & sales lulus.
