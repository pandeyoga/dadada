# 11b — Pola otorisasi, lingkup organisasi, mass-assignment

Sumber: sapuan agen RBAC (ronde 3) + **verifikasi ulang oleh saya** pada instance terpisah. Agen terhenti sebelum
menulis laporannya sendiri, jadi dokumen ini disusun dari rekap yang ia serahkan; tiap temuan diberi label bukti:

- **[TERBUKTI-SAYA]** — saya jalankan ulang sendiri dan hasilnya sama/terukur.
- **[TERBUKTI-AGEN+KODE]** — agen menjalankannya; saya mengonfirmasi penyebabnya di kode, belum menjalankan ulang.
- **[AGEN]** — hanya klaim agen (belum saya konfirmasi).

Konteks: kode cabang kerja @ `b4608a5`; peran uji `owner@`/`finance@`/`sales@` org SIPRO dan `owner@` org Nusa (org kedua demo).
Semua uji dilakukan pada instance lokal berisi data seed (bukan data produksi).

## 1. Ringkasan

1. **Isolasi antar-organisasi tidak ditegakkan di jalur entitas dan pengguna.** Ada dua celah **Kritis** yang saya buktikan
   sendiri: pemilik (`owner`) organisasi mana pun bisa **membuat pengguna `super_admin`** (peran lintas-tenant) dan bisa
   **mengganti kata sandi pengguna organisasi lain** (pengambilalihan akun).
2. Pola akarnya sama dengan P11 di dokumen 11: query `find_one({"id": …})` **tanpa `org_id`** di helper "scoped"
   (`_get_lead_scoped`, `get_deal`, `_get_deal_editable`, `_get_doc_scoped`, `update_user`, …). Pemeriksaan "milik sendiri"
   dibuat untuk peran sales, tetapi tidak pernah untuk organisasi.
3. Faktor peredam: id berupa UUID acak, jadi untuk AZ-01/AZ-12 penyerang perlu mengetahui id sasaran (bisa bocor lewat tautan, ekspor,
   notifikasi, atau jejak audit). Faktor ini **tidak berlaku** untuk AZ-11 — membuat `super_admin` tidak memerlukan id apa pun.
4. Dugaan agen yang **tidak** bisa saya reproduksi: pembatalan deal lintas-org (`409`, ditahan CAS yang memakai `org_id`) dan
   hapus lead/deal lintas-org (membalas `200` tetapi **tidak ada data yang terhapus**; hitungan "removed" pada respons menyesatkan
   dan jejak audit tertulis atas org penyerang).

## 2. Temuan

| ID | Sev | Ringkas | Bukti |
|---|---|---|---|
| **AZ-11** | **Kritis** | `POST /admin/users` mengizinkan peran `super_admin` (peran apa pun yang dikenal) tanpa pembatasan. `owner` org SIPRO membuat pengguna `super_admin`, login dengannya, lalu `GET /admin/orgs` menampilkan **2 organisasi** (lintas-tenant). | TERBUKTI-SAYA |
| **AZ-12** | **Kritis** | `PUT /admin/users/{id}` mencari pengguna dengan `find_one({"id"})` tanpa `org_id`. `owner` org Nusa mengubah nama **dan kata sandi** pengguna org SIPRO → login dengan sandi baru **berhasil**. Mencakup `super_admin` (agen: owner dapat `PUT` pada akun superadmin). | TERBUKTI-SAYA |
| **AZ-01** | Tinggi | Lead/deal/dokumen org A dapat **dibaca** dan sebagian **diubah** oleh pengguna org B: `GET/PUT /leads/{id}` (nama lead berubah, org A melihat perubahan), `GET /deals/{id}`, `POST /deals/{id}/book` (deal org A menjadi `booked` oleh org B). Tidak terjadi: batal deal (`409`), hapus (no-op). | TERBUKTI-SAYA (baca, ubah lead, book); dokumen = AGEN+KODE |
| **AZ-02** | Tinggi | Pola sistemik ±20 fungsi pencari-by-id tanpa `org_id`: `activity_router.reply_comment`, `customers_router._attach_files`, `files_router._derive_context`, `financing_router._create_financing_locked`, `lead_score_router.lead_rescore`, `portal_router._customer/_find_portal_user`, `site_plan_router._buyer_for`, `subcon_router.create_spk_from_rab`, serta tiga di AZ-01. `workhub._get_task` aman (positif palsu AST). | KODE (agen+AST) |
| **AZ-04** | Tinggi | Sales mengubah KPR milik sales lain: `PUT /financing/{id}` dan `POST /financing/{id}/slik` memakai `_get(fid, org)` yang hanya memfilter org, tanpa cek `assigned_to`; agen mengubah status SLIK menjadi `rejected` dan DP milik sales lain. | AGEN + KODE (`_get` org-only terkonfirmasi) |
| **AZ-10** | Tinggi | OTP portal pembeli tanpa kunci percobaan: kolom `attempts` hanya diisi `0` saat OTP dibuat dan **tidak pernah ditambah/dicek**. Agen: 800 tebakan salah beruntun (~470/dtk) tidak memicu penolakan; ruang 10⁶ kombinasi, masa berlaku 10 menit. | AGEN + KODE |
| **AZ-06** | Tinggi | (a) `POST /doc-history/send-wa` hanya meminta `documents:view` dan tidak memeriksa kepemilikan lead/customer tujuan → sales dapat mengirim WhatsApp resmi ke pelanggan sales lain dengan caption bebas. (b) `PUT /master/doc-templates/{id}` tidak membatasi pembuat → sales dapat mengubah template dokumen buatan orang lain. | AGEN (+KODE: izin `view`) |
| AZ-05 | Sedang | `POST /reference/{group}/values` hanya `get_current_user`: peran apa pun (dm, site, sales) menambah nilai "Bank KPR"/"Jenis Izin" ke master organisasi tanpa persetujuan/log. | AGEN + KODE (`Depends(get_current_user)` terkonfirmasi) |
| AZ-07 | Sedang | Unggahan `.html`/`.svg` disajikan `Content-Disposition: inline` dengan tipe asli, tanpa `nosniff`/CSP → skrip tersimpan berjalan (diuji di browser oleh agen); diperparah token di query `?auth=`. | AGEN + KODE (`inline` terkonfirmasi) |
| AZ-08 | Sedang | Pencarian `q` memasukkan regex mentah ke `$regex` tanpa `re.escape` di `permits`, `subcon`, `gl/journals`, `fund-requests`, `bank`, `vendors`, `contracts`, `masterplan` → `q=[` menghasilkan **HTTP 500**. Modul lain (inbox, aktivitas) sudah meng-escape. | AGEN + KODE (pola tanpa escape terkonfirmasi) |
| AZ-09 | Rendah | `POST /webhooks/web` tanpa pembatas laju (25 permintaan → 25 lead); pembatas laju hanya di showroom publik & permintaan hapus data. | AGEN + KODE (tidak ada rate-limit di `webhooks_router`) |
| AZ-03 | Rendah | `financing_router._create_financing_locked` mencari tanpa `org_id` (jalur utama sudah ber-`org_id`). Diturunkan agen dari "Kritis". | KODE |

### Positif (agar tidak berat sebelah) — dari agen
Token tanpa/rusak/kedaluwarsa/`alg=none`/secret salah/token refresh dipakai sebagai access: **selalu 401** (980 kombinasi); token portal
tidak diterima di endpoint staf dan sebaliknya; pembeli A tidak dapat membaca kuitansi/BAST/garansi/KYC pembeli B; `admin/orgs`
(list/create/update/switch) benar-benar `super_admin`-only **selama tidak ada pengguna `super_admin` palsu (AZ-11)**; SoD kas bon/pengajuan
dana tegak; mass-assignment `costs_manual` ditolak 403 untuk sales. Sensus: 1028 rute, ±530 mutasi, ±940 berizin; ~38 tanpa izin
(publik/webhook/showroom/legal/OTP) dan memang dimaksudkan publik.

## 3. Reproduksi yang saya jalankan (ringkas)

AZ-11: `POST /admin/users {role:"super_admin"}` oleh `owner@` org SIPRO → `200 role=super_admin`; login pengguna baru berhasil;
`GET /admin/orgs` → `200`, 2 organisasi (pemilik biasa hanya melihat 1).
AZ-12: pengguna dummy org SIPRO dibuat; `PUT /admin/users/{id} {name, password}` oleh `owner@` org Nusa → `200`; login dummy dengan
sandi baru → berhasil.
AZ-01: lead org SIPRO dibuat; `owner@` org Nusa: `GET` → `200`, `PUT {name}` → `200` (org SIPRO melihat nama baru), daftar lead org Nusa
tidak memuatnya (hanya akses langsung per-id yang bocor), `POST /deals/{id}/book` pada deal `reserved` org SIPRO → `200`, status DB `booked`.
Batal: `409`; hapus: `200` tanpa efek.

## 4. Perbaikan yang disarankan (urut)

1. **Segera (Kritis, kecil):** `update_user`/`create_user` — tambahkan `org_id` pada pencarian; `super_admin` hanya boleh diberikan/diubah oleh
   `super_admin`; larang `owner` mengubah pengguna dengan peran lebih tinggi/di luar organisasinya; catat audit tiap perubahan peran/sandi.
2. **Satu helper org-scope** `get_scoped(coll, id, user)` yang SELALU memasukkan `org_id` (dan scope sales) — ganti ±20 pencari-by-id; tambahkan
   tes regresi lintas-tenant (leads, deals, documents, contracts, customers, tasks, financing, users) yang dijalankan di CI.
3. OTP: hitung percobaan per OTP (maks 5), kunci per nomor+IP, tidak ada hitung-ulang saat OTP baru diminta berulang.
4. `financing_router._get`: terapkan scope sales; `send-wa`: validasi kepemilikan entitas tujuan; template dokumen: batasi ubah ke `documents:update`.
5. `reference_router`: izin `settings:manage`; unggahan non-gambar/PDF → `attachment` + `nosniff`; `re.escape(q)` seragam + tangkap `re.error` → 400;
   rate-limit `webhooks/web`.
6. Sapuan lanjutan yang belum sempat: pola AZ-01 pada koleksi keuangan (`ar_invoices`, `ap_invoices`, `commissions`, `receipts`) — **belum diuji**.

## 5. Catatan metode & pembersihan
Agen mencatat data uji berawalan `AUDIT-` tertinggal di DB instance ketiga; tidak ada data produksi tersentuh. Pengguna `pat.*` yang saya buat berada di
DB uji saya. CORS `allow_origins=*` + `allow_credentials=true` dicatat agen tetapi tidak diangkat sebagai temuan (autentikasi berbasis header Bearer).

## 6. Status perbaikan
Semua temuan di bagian 2 sudah diperbaiki dan punya tes regresi yang **merah pada kode lama dan hijau pada kode baru**
(`backend/tests/p0/test_p0_otorisasi.py` AZ-11/12; `test_p0_otorisasi_org.py` AZ-01/02; `test_p0_otorisasi_lain.py` AZ-04…10).
Pengecualian yang disengaja: 17 pencari-by-id yang tersisa pada sapuan adalah `/auth/*` (pengguna sendiri) dan koleksi `orgs` (dokumen organisasi,
dijaga peran `super_admin`/organisasi sendiri). Belum diuji: pola yang sama pada koleksi keuangan (`ar_invoices`, `ap_invoices`, `commissions`,
`receipts`) lewat HTTP lintas-org — pencarinya sudah ber-`org_id` menurut sapuan statis, tetapi belum dibuktikan dengan tes lintas-org.
