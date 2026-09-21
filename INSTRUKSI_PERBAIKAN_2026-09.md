# INSTRUKSI PERBAIKAN — Audit Eksternal 2026-09-05

> **Untuk:** agen AI / engineer yang akan mengerjakan perbaikan di repo Kain Nusantara.
> **Sumber:** audit statik read-only atas commit `5c76055` (2026-09-05).
> **Sifat:** 11 temuan. **10 sudah diverifikasi mekanis** oleh
> `scripts/audit_temuan_2026_09.py`; **1 (T-05) sengaja TIDAK bisa diverifikasi
> statik** dan wajib Anda buktikan sendiri dengan menjalankan uji.
> **Prinsip yang dipakai** — mengikuti `memory/ENGINEERING_GUARDRAILS.md`:
> *"Dokumentasi bukan penegakan. Prosa membusuk. Guardrail yang benar = kode yang
> bisa GAGAL (exit ≠ 0)."* Karena itu dokumen ini **tidak berdiri sendiri**: ia
> ditemani satu skrip yang bisa memerah.

---

# §0 — ATURAN MAIN (BACA SAMPAI HABIS SEBELUM MENGETIK APA PUN)

Dokumen ini ditulis dengan asumsi Anda **bisa keliru tanpa menyadarinya**.
Sepuluh aturan berikut ada untuk menutup jalan itu. Melanggar satu saja =
pekerjaan Anda **tidak sah** dan harus diulang.

### A0-1. Temuan di sini adalah HIPOTESIS, bukan fakta yang harus Anda percaya
Auditor bisa salah. Tugas pertama Anda **bukan memperbaiki**, melainkan
**membuktikan atau menggugurkan**. Setiap temuan punya bagian
**"KRITERIA GUGUR"** — kalau kenyataan cocok dengan kriteria itu, Anda **WAJIB**
menulis "T-xx GUGUR" beserta buktinya dan **TIDAK BOLEH** menyentuh kodenya.
Menggugurkan temuan palsu adalah hasil kerja yang BAIK, bukan kegagalan.

### A0-2. Dilarang mengklaim tanpa keluaran perintah yang ditempel mentah
Setiap klaim status ("sudah", "sudah benar", "tidak ada masalah") **WAJIB**
disertai blok kode berisi **perintah yang Anda jalankan + keluarannya apa adanya**.
Keluaran yang diringkas, diketik ulang, atau "kurang lebih begini" = **VOID**.
Mengikuti aturan repo ini sendiri: *"Klaim tanpa receipt = void"*
(`scripts/gate.sh` baris 5).

### A0-3. Dilarang mengubah `scripts/audit_temuan_2026_09.py` untuk membuat temuan lewat
Skrip itu mencetak **segel SHA-256 dirinya sendiri** setiap kali dijalankan.
Segel pada commit ini:

```
sha256:c0baaa80a82dc16a
```

Kalau segel di keluaran Anda berbeda dan Anda tidak menjelaskan kenapa, seluruh
laporan Anda ditolak. Kalau Anda memang perlu **menambah** pemeriksa (mis. untuk
temuan baru), boleh — tapi tulis di laporan: baris apa yang ditambah, kenapa, dan
buktikan pemeriksa lama masih memberi hasil sama.

### A0-4. Dilarang mengutip `coverage_data/*.json` sebagai bukti kondisi HARI INI
Berkas itu **basi**. Bukti:

```
$ git log -1 --format="%ci" -- coverage_data/corpus_summary.json
2026-09-04 17:56:40 +0000

$ git log --format="%h %ci" | head -3
5c76055 2026-09-05 09:29:20 +0000
602e780 2026-09-05 09:10:52 +0000
46f8a1d 2026-09-04 17:56:40 +0000
```

Artinya angka "67 lulus / 55 gagal" itu diambil **dua commit sebelum HEAD**.
Sebagian mungkin sudah sembuh, sebagian mungkin baru rusak. **Jalankan ulang.**

### A0-5. Setiap perbaikan wajib punya "bukti-merah" (SELF-TEST dua arah)
Ini konvensi yang sudah hidup di repo ini (lihat `memory/INVARIANTS.md`: hampir
semua guard punya `--self-test`). Untuk setiap perbaikan, buktikan **dua arah**:

1. **SEBELUM** perbaikan, pemeriksa memberi `TERBUKTI` (merah).
2. **SESUDAH** perbaikan, pemeriksa memberi `GUGUR` (hijau).

Kalau pemeriksa hijau sebelum dan sesudah, pemeriksanya buta — perbaiki
pemeriksanya dulu, jangan lanjutkan.

Contoh bukti-merah yang sah (sudah saya lakukan untuk T-08):

```
$ sed -i 's/"SEED_DEMO_ENABLED", "true"/"SEED_DEMO_ENABLED", "false"/' backend/routers/admin.py
$ python3 scripts/audit_temuan_2026_09.py | grep -A2 "T-08"
[GUGUR   ] T-08 — SEED_DEMO_ENABLED bawaan 'true' (reset DB hidup by default)
$ git checkout backend/routers/admin.py
$ python3 scripts/audit_temuan_2026_09.py | grep -A2 "T-08"
[TERBUKTI] T-08 — SEED_DEMO_ENABLED bawaan 'true' (reset DB hidup by default)
```

### A0-6. Satu temuan = satu commit. Dilarang menggabung.
Riwayat repo ini sudah tergencet jadi 4 commit (lihat T-06) — jangan perparah.
Format pesan commit:

```
T-xx <ringkasan satu baris>

Bukti sebelum : <keluaran pemeriksa: TERBUKTI>
Bukti sesudah : <keluaran pemeriksa: GUGUR>
Berkas disentuh: <daftar>
Risiko regresi : <apa yang bisa patah + bagaimana Anda mengujinya>
```

### A0-7. Dilarang menyentuh apa pun di luar cakupan temuan yang sedang dikerjakan
"Sekalian rapikan" adalah cara paling umum sebuah perbaikan kecil menjadi
regresi besar. Kalau Anda menemukan cacat lain, **catat di §7 Temuan Baru**,
jangan diperbaiki di commit yang sama.

### A0-8. Kalau berkas/simbol yang dirujuk dokumen ini tidak ditemukan → LAPOR, JANGAN TEBAK
Pemeriksa akan mencetak `RALAT` untuk kasus ini. Jangan mencari-cari "berkas yang
mirip" lalu memperbaikinya. Nomor baris di dokumen ini mengacu commit `5c76055`
dan **akan bergeser** setelah Anda mengedit — selalu cari lewat pola teks, jangan
lompat ke nomor baris secara buta.

### A0-9. Frasa yang DILARANG muncul di laporan Anda
Frasa berikut menandakan klaim tanpa bukti dan otomatis membatalkan laporan:

- "seharusnya sudah bekerja" / "kemungkinan besar sudah benar"
- "saya sudah memverifikasi" **tanpa** blok keluaran perintah
- "semua tes lulus" **tanpa** menempelkan ringkasan runner
- "tidak ada masalah lain yang saya temukan" (tidak bisa dibuktikan — hapus saja)
- "berdasarkan pemahaman saya tentang kode" (bukan bukti — bacalah kodenya)

### A0-10. Batas wewenang
Anda **BOLEH** mengubah kode, menambah uji, menambah guardrail.
Anda **TIDAK BOLEH**, tanpa persetujuan pemilik tertulis:
- mengubah skema data / menghapus koleksi;
- menjalankan `POST /api/admin/seed-demo` di lingkungan berisi data nyata;
- mengubah matriks izin (`permission_settings`) di luar temuan yang menuntutnya;
- mengubah `.env` produksi;
- melakukan `git push --force` atau menulis ulang riwayat.

---

# §1 — LANGKAH 0: BASELINE (WAJIB, SEBELUM PERBAIKAN APA PUN)

Jalankan **persis** ini dan tempel keluarannya di laporan. Ini menjadi garis dasar
yang akan dibandingkan di akhir.

```bash
cd <akar-repo>          # di kontainer Emergent biasanya /app

# 1. Pastikan Anda di commit yang sama dengan audit ini
git log -1 --format="%h %ci %s" | cut -c1-120
git status --short

# 2. Verifikator temuan (statik, read-only, tidak menyentuh DB)
python3 scripts/audit_temuan_2026_09.py ; echo "EXIT=$?"

# 3. Kompilasi backend harus bersih
python3 -m compileall -q backend ; echo "COMPILE_EXIT=$?"

# 4. Guardrail repo sendiri (statik cepat, ~7 detik)
bash scripts/gate.sh --quick 2>&1 | tail -25
```

**Keluaran baseline yang saya dapatkan pada commit `5c76055`** — kalau punya Anda
berbeda, JANGAN lanjut; jelaskan dulu kenapa:

```
  TERBUKTI (masih cacat) : 10
  GUGUR (bersih/sudah)   : 0
  RALAT (tak bisa diuji) : 0
  segel: sha256:c0baaa80a82dc16a
EXIT=1
COMPILE_EXIT=0
```

---

# §2 — RINGKASAN 11 TEMUAN

| ID | Temuan | Bobot | Status verifikasi | Jenis kerja |
|----|--------|-------|-------------------|-------------|
| **T-01** | Nol transaksi MongoDB; tulis lintas-koleksi tak atomik & tak punya penjaga ulang-jalan | **TINGGI** | TERBUKTI (mekanis) | Arsitektur + kode |
| **T-02** | CORS bawaan `*` + `allow_credentials=True`; cookie sesi `secure=False` **hardcoded** | **TINGGI** | TERBUKTI (mekanis) | Konfigurasi (cepat) |
| **T-03** | 63 `to_list(≥20000)`, paginasi cuma di 16/123 router | **SEDANG-TINGGI** | TERBUKTI (mekanis) | Kinerja, bertahap |
| **T-04** | 95 kandidat N+1 baca di dalam loop | **SEDANG** | TERBUKTI (mekanis) | Triase dulu, jangan borong |
| **T-05** | Korpus uji: 55/122 skrip gagal (data **basi 2 commit**) | **TINGGI** | ⚠️ **BELUM diverifikasi — tugas Anda** | Triase |
| **T-06** | Tak ada CI; `pre-commit` tak terpasang; riwayat git 4 commit | **TINGGI** | TERBUKTI (mekanis) | Proses |
| **T-07** | `CODEBASE_MAP.md` melenceng jauh — padahal TIER 0 mewajibkan agen membacanya | **TINGGI** | TERBUKTI (mekanis) | Dokumen + guard |
| **T-08** | `SEED_DEMO_ENABLED` bawaan `"true"` (reset DB hidup by default) | **SEDANG** | TERBUKTI (mekanis) | Satu baris |
| **T-09** | Saran reorder tak menyaring `lifecycle` & tak membawa `warehouse_id` | **SEDANG** | TERBUKTI (mekanis) | Kode terarah |
| **T-10** | `POST /ar-receipts`: 422 mendahului 403 | **RENDAH** | TERBUKTI (mekanis) | Kode terarah |
| **T-11** | `approve_order` → 409 `INVALID_TRANSITION` setelah SO auto-approved | **SEDANG** | TERBUKTI (mekanis) | Kode terarah |

> T-09, T-10, T-11 adalah temuan yang **sudah tercatat di `TEMUAN_AUDIT_TRAINING.md`
> milik Anda sendiri** sebagai belum dikerjakan. Audit ini mengonfirmasi ketiganya
> masih terbuka di `5c76055` dan menyediakan letak persisnya.

---

# §3 — TEMUAN SATU PER SATU

Format tiap temuan **selalu sama**:
**(a) Klaim · (b) Bukti auditor · (c) Buktikan sendiri · (d) Kriteria GUGUR ·
(e) Perbaikan · (f) Gerbang bukti selesai.**

---

## T-01 — Nol transaksi MongoDB; tulis lintas-koleksi tak atomik

**Bobot: TINGGI** · Jenis: arsitektural

### (a) Klaim
Di seluruh kode produksi backend **tidak ada satu pun** transaksi MongoDB.
Akibatnya operasi bisnis yang menulis ke beberapa koleksi bisa berhenti separuh
jalan. Sebagian jalur sudah dilindungi penjaga idempotensi buatan sendiri
(pola saga), tetapi **tidak semuanya** — dan yang tidak terlindungi menyentuh
stok sekaligus nilai pesanan.

### (b) Bukti auditor

```
transaksi di kode produksi (start_session|with_transaction|start_transaction): 0
```

Dua-satunya kecocokan di seluruh repo adalah **nama method uji**, bukan transaksi:

```
backend/tests/test_iter265_r3r4r5.py:347:    def test_02_start_session(self, api):
backend/tests/test_iter266_r6_cc_r7.py:206:    def test_01_start_session(self, api):
```

**Contoh konkret jalur tak terlindungi** —
`backend/routers/outbound_picking.py`, endpoint `resolve_escalation`:

| Baris | Aksi | Koleksi |
|-------|------|---------|
| 244 | penjaga: `if not task.get("escalation"):` | — |
| 287–288 | `release_order_rolls_partial(...)` | `inventory_rolls` |
| 291 | `db.sales_orders.update_one(...)` (allocations) | `sales_orders` |
| 314 | `db.sales_orders.update_one(...)` (items + repricing) | `sales_orders` |
| 338 | `db.wms_tasks.find_one_and_update(...)` | `wms_tasks` |

Penjaganya hanya memeriksa **keberadaan** objek `escalation`, **bukan**
`escalation["status"] != "resolved"`. Jendela gagalnya:

> Proses mati **setelah** baris 288 (roll sudah dilepas) tapi **sebelum** baris 338
> (task belum diperbarui). Saat dijalankan ulang, `task["quantity"]` masih nilai
> lama → `delta` dihitung ulang dengan nilai yang sama → **roll dilepas dua kali**.
> Stok fisik dan angka di pesanan berpisah, tanpa satu pun galat.

### Catatan kejujuran (BACA — ini mencegah Anda salah sasaran)
Banyak jalur lain **sudah** aman karena idempotensinya halus. Contoh:
`services/gl_service.py` `post_shipment_revenue()` memeriksa
`_already_posted("shipment_revenue", shipment_id)` **per surat jalan** (baris ~922),
sehingga perulangan posting jurnal aman diulang. **Jangan** menyimpulkan "semua
posting jurnal rusak" — tidak benar. Yang rusak adalah jalur yang menulis
**stok + dokumen** tanpa penanda ulang-jalan.

### (c) Buktikan sendiri

```bash
# 1. Nol transaksi di kode produksi
grep -rnE "start_session|with_transaction|start_transaction" backend --include="*.py" \
  | grep -v "/tests/" | grep -vE "(^|/)(test_|_test)"
# Harapan: TIDAK ADA keluaran sama sekali.

# 2. Penjaga lemah di resolve_escalation
grep -n 'if not task.get("escalation")' backend/routers/outbound_picking.py
grep -n 'escalation.*status.*!=.*resolved' backend/routers/outbound_picking.py
# Harapan: perintah pertama menemukan 1 baris; perintah kedua TIDAK menemukan apa pun.

# 3. Pemeriksa otomatis
python3 scripts/audit_temuan_2026_09.py | grep -A 6 "T-01"
```

### (d) KRITERIA GUGUR
Temuan ini **GUGUR** dan Anda harus berhenti bila salah satu benar:
- perintah (1) menemukan transaksi di kode produksi (bukan berkas uji); **atau**
- `resolve_escalation` ternyata sudah punya penjaga ulang-jalan (memeriksa
  `escalation["status"]`, memakai `find_one_and_update` bersyarat status, atau
  memakai kunci idempotensi lain) — tempel barisnya sebagai bukti.

### (e) Perbaikan

Ini temuan **arsitektural**; jangan pura-pura menyelesaikannya dalam satu commit.
Kerjakan tiga langkah berikut **berurutan**, masing-masing satu commit.

**Langkah 1 — tutup lubang konkret (WAJIB, kecil, risiko rendah).**
Buat `resolve_escalation` aman diulang. Ubah penjaga di
`backend/routers/outbound_picking.py` supaya **klaim tugas secara atomik** sebelum
menyentuh apa pun:

```python
# GANTI penjaga lama:
#   if not task.get("escalation"):
#       raise HTTPException(status_code=400, detail="Task tidak dalam status escalation")
#
# DENGAN klaim atomik — hanya SATU pemanggil yang bisa masuk:
claimed = await db.wms_tasks.find_one_and_update(
    {"id": task_id,
     "escalation": {"$exists": True},
     "escalation.status": {"$ne": "resolved"}},
    {"$set": {"escalation.status": "resolving",
              "escalation.resolving_at": now_iso()}},
    projection={"_id": 0},
    return_document=ReturnDocument.AFTER,
)
if not claimed:
    raise HTTPException(
        status_code=409,
        detail="Eskalasi sudah/sedang diselesaikan pihak lain. Muat ulang layar.")
task = safe_doc(claimed)
```

Lalu pastikan blok penutup (baris ~338) menyetel `escalation.status = "resolved"`.
Kalau proses mati di tengah, tugas tertinggal berstatus `"resolving"` — **itu
disengaja**: keadaan itu terlihat dan bisa ditangani, jauh lebih baik daripada
pelepasan roll ganda yang senyap.

**Langkah 2 — inventarisasi, jangan tebak.** Buat daftar semua endpoint yang
menulis ke **≥2 koleksi berbeda** dalam satu request. Jangan mengandalkan ingatan:

```bash
python3 - <<'PY'
import re, pathlib, collections
for f in sorted(pathlib.Path('backend/routers').glob('*.py')):
    src = f.read_text(errors='ignore'); lines = src.split('\n')
    idx = [i for i,l in enumerate(lines) if re.match(r'@router\.(post|put|patch|delete)\(', l)]
    for n,i in enumerate(idx):
        end = idx[n+1] if n+1 < len(idx) else len(lines)
        blok = '\n'.join(lines[i:end])
        cols = set(re.findall(r'await db\.(\w+)\.(?:insert_one|update_one|update_many|delete_one|find_one_and_update)', blok))
        if len(cols) >= 2:
            path = re.search(r'"([^"]*)"', lines[i])
            print(f"{len(cols)}  {f.name}:{i+1}  {path.group(1) if path else '?'}  -> {sorted(cols)}")
PY
```

Pada commit `5c76055` skrip ini mengembalikan **18 endpoint**. Contoh keluarannya:

```
4  inbound_receiving.py:265  /inbound/tasks/{task_id}/complete  -> ['inventory_movements', 'inventory_rolls', 'purchase_orders', 'wms_tasks']
3  invoices.py:35   /sales-orders/{order_id}/simulate-payment  -> ['cash_transactions', 'invoices', 'sales_orders']
2  landed_cost.py:303  /landed-costs/{voucher_id}/pay  -> ['cash_transactions', 'landed_cost_vouchers']
```

⚠️ **ANGKA 18 ITU UNDERCOUNT — JANGAN PERLAKUKAN SEBAGAI DAFTAR LENGKAP.**
Skrip ini hanya melihat `await db.X.<op>` yang ditulis **langsung di berkas router**.
Di repo ini mayoritas tulisan justru terjadi di **service** (190 berkas), sehingga
endpoint seperti `resolve_escalation` — yang memanggil
`release_order_rolls_partial()` di `roll_service.py` — **tidak muncul** di daftar itu.

Karena itu, perluas penelusuran satu tingkat: untuk tiap endpoint, telusuri juga
service yang dipanggilnya. Kalau Anda tidak sempat menelusuri semuanya, **katakan
demikian di laporan** ("saya menelusuri N dari M; sisanya belum") — jangan
menyajikan daftar parsial seolah lengkap.

Tempel keluarannya di laporan. Untuk **setiap** baris hasil, klasifikasikan:
`AMAN (ada penjaga idempotensi — sebutkan barisnya)` / `PERLU PENJAGA` /
`TIDAK RELEVAN (koleksi log/audit saja)`. **Jangan memperbaiki apa pun di langkah ini** —
hasilnya adalah tabel, dan tabel itulah yang diputuskan pemilik.

**Langkah 3 — keputusan pemilik (JANGAN putuskan sendiri).** Sajikan dua opsi:
- **Opsi A — replica set + transaksi.** MongoDB butuh replica set (walau simpul
  tunggal) agar transaksi bisa dipakai. Perubahan infrastruktur; paling benar
  secara semantik.
- **Opsi B — pola saga eksplisit.** Pertahankan single-node, tapi wajibkan setiap
  operasi multi-koleksi punya kunci idempotensi + penjaga klaim atomik seperti
  Langkah 1, ditegakkan guard baru `INV-ATOMIC-01`.

Tulis konsekuensi tiap opsi (biaya, risiko, waktu) lalu **berhenti dan tanya**.

### (f) Gerbang bukti selesai
- [ ] Keluaran pemeriksa Langkah 1: `T-01` masih `TERBUKTI` untuk aspek "nol
      transaksi" (wajar — belum diputuskan), tetapi tunjukkan penjaga baru dengan
      `grep -n 'escalation.status' backend/routers/outbound_picking.py`.
- [ ] Uji ulang-jalan: panggil endpoint yang sama **dua kali** dengan
      `adjusted_qty` yang sama; panggilan kedua **harus** 409, dan
      `inventory_rolls` yang dilepas **tidak boleh** bertambah. Tempel angka
      sebelum/sesudah.
- [ ] Tabel inventarisasi Langkah 2 lengkap dan terklasifikasi.
- [ ] `bash scripts/gate.sh` HIJAU (tempel receipt).

---

## T-02 — CORS bawaan `*` + cookie sesi non-Secure

**Bobot: TINGGI** · Jenis: konfigurasi keamanan · **Perbaikan < 1 jam**

### (a) Klaim
Bila `CORS_ORIGINS` tidak di-set di lingkungan, aplikasi menerima **semua asal**
sambil mengizinkan kredensial. Terpisah dari itu, cookie sesi ditulis dengan
`secure=False` yang **dipaku di kode** — tidak bisa dinyalakan lewat env, jadi
walaupun CORS-nya benar, cookie tetap boleh melintas HTTP polos.

### (b) Bukti auditor

`backend/server.py` baris 109–115:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),   # ← baris 111
    allow_credentials=True,                                          # ← baris 112
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`backend/routers/auth.py` baris 114:

```python
response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=False, samesite="lax",
                    max_age=SESSION_TTL_HOURS * 3600, path="/")
```

Tidak ada nginx/ingress/Dockerfile di repo yang menutupi ini:

```
$ find . -iname "*nginx*" -o -iname "*ingress*" -o -iname "Dockerfile*" -o -iname "*.conf" | grep -v node_modules
(kosong)
```

### Catatan kejujuran (proporsi risiko)
- `samesite="lax"` **sudah** menahan sebagian besar CSRF: peramban tidak mengirim
  cookie ini pada `fetch`/POST lintas-situs. Jadi ini **bukan** "situs Anda sedang
  dibobol".
- `docs/KN_12_DEVELOPMENT_PROTOCOLS.md` menyebut produksi masih *"TBD"*. Maka
  klasifikasikan ini sebagai **penghalang sebelum go-live**, bukan insiden aktif.
- Yang paling nyata adalah `secure=False` yang **hardcoded**: begitu aplikasi
  dilayani lewat HTTPS, cookie sesi tetap boleh dikirim lewat HTTP polos.

### (c) Buktikan sendiri

```bash
sed -n '109,115p' backend/server.py
sed -n '114,115p' backend/routers/auth.py
find . -iname "*nginx*" -o -iname "*ingress*" -o -iname "Dockerfile*" | grep -v node_modules
python3 scripts/audit_temuan_2026_09.py | grep -A 4 "T-02"
```

### (d) KRITERIA GUGUR
- `allow_origins` **tidak** ber-default `"*"` (mis. ber-default daftar spesifik, atau
  aplikasi menolak start bila env kosong); **atau**
- `secure=` sudah dibaca dari env / sudah `True`; **atau**
- ditemukan lapisan proxy **di dalam repo** yang menimpa header CORS — tempel
  berkas + barisnya.

### (e) Perbaikan

**E-1. Hilangkan default permisif.** Di `backend/server.py`:

```python
_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if not _origins:
    # Gagal BERISIK, bukan diam-diam permisif. Kelas jebakan yang sama dengan
    # .restore_env.sh: lingkungan separuh jadi lebih mahal daripada mati di awal.
    raise RuntimeError(
        "CORS_ORIGINS wajib di-set (daftar asal dipisah koma). "
        "Contoh dev: CORS_ORIGINS=http://localhost:3000")
if "*" in _origins:
    raise RuntimeError("CORS_ORIGINS='*' dilarang bersama allow_credentials=True.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**E-2. Jadikan flag cookie bisa dikonfigurasi, aman secara bawaan.** Di
`backend/routers/auth.py` — dan **cari juga tempat lain** yang menulis cookie ini:

```bash
grep -rn "set_cookie\|delete_cookie" backend --include="*.py"
```

```python
# taruh dekat SESSION_COOKIE
COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() not in ("false", "0", "no")
COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "lax")

response.set_cookie(SESSION_COOKIE, token, httponly=True,
                    secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
                    max_age=SESSION_TTL_HOURS * 3600, path="/")
```

⚠️ **Peringatan pengembangan lokal:** dengan `COOKIE_SECURE=true`, login lewat
`http://localhost` akan **berhenti bekerja** karena peramban menolak menyimpan
cookie Secure di HTTP. Karena itu **wajib** Anda tambahkan ke berkas `.env`
pengembangan (dan tulis di laporan bahwa Anda sudah melakukannya):

```
SESSION_COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
```

**E-3. Buat `.env.example`** (repo ini belum punya — sudah saya periksa). Isi
minimal: `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `SESSION_COOKIE_SECURE`,
`SESSION_COOKIE_SAMESITE`, `SEED_DEMO_ENABLED` (lihat T-08). Jangan masukkan nilai
rahasia apa pun; `.gitignore` sudah benar memblokir `.env`.

### (f) Gerbang bukti selesai
- [ ] Backend **menolak start** tanpa `CORS_ORIGINS` — tempel jejak galatnya.
- [ ] Backend start normal dengan `CORS_ORIGINS` di-set — tempel log start.
- [ ] Login berhasil di lingkungan dev (dengan `SESSION_COOKIE_SECURE=false`) —
      tempel status HTTP dan header `Set-Cookie` dari respons.
- [ ] `.env.example` ada dan **tidak** memuat rahasia.
- [ ] `bash scripts/gate.sh` HIJAU.

---

## T-03 — `to_list(≥20000)` dan paginasi belum merata

**Bobot: SEDANG-TINGGI** · Jenis: kinerja/skalabilitas · **bertahap, jangan diborong**

### (a) Klaim
312 pemanggilan `to_list(≥1000)`, **63 di antaranya ≥20.000**, sementara hanya
**16 dari 123** router memakai helper paginasi yang sudah tersedia
(`backend/pagination.py`). Beberapa memuat seluruh koleksi ke memori lalu menyaring
di Python.

### (b) Bukti auditor

```
to_list(>=1000)          : 312
to_list(>=20000)         : 63
router pakai pagination  : 16 / 123
```

**Contoh terburuk** — `backend/services/stock_analytics_service.py:73`, memuat
**seluruh** `inventory_movements` lalu menyaring jendela waktu di Python:

```python
mv = await db.inventory_movements.find(
    resolve_list_scope("inventory_movements", {}, ctx, entity_id), {"_id": 0}
).to_list(100000)
out: Dict[str, Dict[str, Any]] = {}
for m in mv:
    if m.get("movement_type") not in SALE_MOVEMENT_TYPES:
        continue
```

Tidak ada penyaring tanggal di query, padahal `window_days` sudah dihitung tepat
di atasnya. Fungsi ini dipanggil dari saran reorder (lihat T-09), jadi ia berjalan
di jalur yang dipakai orang setiap hari.

### (c) Buktikan sendiri

```bash
python3 scripts/audit_temuan_2026_09.py | grep -A 16 "T-03"
sed -n '66,80p' backend/services/stock_analytics_service.py
grep -rl "from pagination import" backend/routers/*.py | wc -l
ls backend/routers/*.py | wc -l
```

### (d) KRITERIA GUGUR
- Jumlah `to_list(≥20000)` = 0; **atau**
- setiap pemanggilan besar itu terbukti sudah dibatasi penyaring yang menjamin
  hasil kecil (tempel querynya, bukan asumsi).

Perhatikan: `to_list(2000)` untuk koleksi master kecil (mis. `products`) **wajar**.
Jangan laporkan itu sebagai cacat.

### (e) Perbaikan

**Jangan** menyapu 312 lokasi. Kerjakan berlapis:

**Lapis 1 — perbaiki yang menyaring-di-Python (paling untung, risiko rendah).**
Kandidat pasti: `stock_analytics_service.py:73` dan `:148`. Pindahkan penyaring ke
query:

```python
from datetime import datetime, timezone, timedelta
batas = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
q = resolve_list_scope("inventory_movements", {}, ctx, entity_id)
q["movement_type"] = {"$in": list(SALE_MOVEMENT_TYPES)}
q["timestamp"] = {"$gte": batas}          # ← sesuaikan nama field; VERIFIKASI dulu
mv = await db.inventory_movements.find(q, {"_id": 0}).to_list(20000)
```

⚠️ **Verifikasi nama field tanggal sebelum mengetik** — jangan tebak:

```bash
grep -n "timestamp\|created_at\|movement_date" backend/services/inventory_service.py | head
python3 - <<'PY'
import re
s = open('backend/indexes.py').read()
m = re.search(r'"inventory_movements":\s*\[(.*?)\]\s*,\n', s, re.S)
print(m.group(1) if m else 'TIDAK ADA index inventory_movements')
PY
```

**Kabar baik yang sudah saya verifikasi:** indeks pendukungnya **sudah ada**.
`backend/indexes.py` mendaftarkan untuk `inventory_movements`:

```python
[("product_id", A), ("warehouse_id", A), ("timestamp", D)],
[("owner_entity_id", A), ("timestamp", D)],
[("movement_type", A), ("timestamp", ...)],
```

Jadi query yang menyaring `movement_type` + `timestamp` akan langsung ditopang
indeks — itulah kenapa perbaikan ini murah. Tetap **buktikan dengan `explain()`**,
jangan percaya kalimat ini. Kalau indeks yang Anda butuhkan ternyata belum ada,
**tambahkan ke `backend/indexes.py`** (berkas itu idempoten dan dipanggil saat
startup lewat `bootstrap.run_bootstrap()`).

**Lapis 2 — buktikan untungnya dengan angka, bukan perasaan.** Untuk setiap
perbaikan, tempel `explain()`:

```python
plan = await db.inventory_movements.find(q).explain()
print(plan["queryPlanner"]["winningPlan"]["stage"])   # harapan: IXSCAN, bukan COLLSCAN
```

**Lapis 3 — cegah kemunduran.** Tambahkan guard baru (ikuti pola berkas di
`scripts/guardrails/`) bernama **`INV-PERF-01`**: `to_list(n)` dengan `n > 20000`
**dilarang**, kecuali terdaftar di daftar-kecuali ber-alasan tertulis ≥20 karakter
(persis pola yang dipakai `INV-UI-07`/`INV-UI-08`). Sertakan `--self-test` dua arah.
Daftarkan di `memory/INVARIANTS.md` dan di `scripts/gate.sh`.

**Lapis 4 — paginasi router terpanas** (kerjakan **satu per commit**, jangan borong):
`product_traceability.py`, `hr_attendance.py`, `hr_tracking.py`. Pakai helper yang
sudah ada di `backend/pagination.py` — jangan bikin kontrak baru. Kontrak yang
berlaku sudah tertulis di `PERF_UX_AUDIT.md` §FASE P2. Setiap daftar berhalaman
baru **wajib** punya tombol unduh CSV, kalau tidak `INV-UI-07` akan memerah.

### (f) Gerbang bukti selesai (per commit)
- [ ] `explain()` sebelum & sesudah: `COLLSCAN` → `IXSCAN`.
- [ ] Jumlah dokumen yang dikembalikan endpoint **tidak berubah** (tempel
      keduanya) — kalau berubah, penyaring Anda salah.
- [ ] Guard `INV-PERF-01` ada, ber-`--self-test`, dan terdaftar di gate.
- [ ] `bash scripts/gate.sh` HIJAU.

---

## T-04 — Kandidat N+1: query baca di dalam loop

**Bobot: SEDANG** · ⚠️ **TEMUAN INI PALING MUDAH MEMBUAT ANDA MERUSAK SESUATU**

### (a) Klaim
95 lokasi menjalankan query **baca** (`find_one`/`find`/`count_documents`/
`aggregate`) di dalam loop atas data.

### (b) Bukti auditor

```
kandidat N+1 (baca)      : 95
find_one_and_update loop : 5   <- SENGAJA, JANGAN diubah jadi bulk
```

Contoh yang jelas N+1 — `backend/routers/reporting.py:44` (query di dalam loop
baris 35), `backend/routers/admin.py:160` (di dalam loop baris 155).

### ⚠️ PERINGATAN KERAS — kenapa angka mentah menyesatkan
Analisis awal saya menemukan **221** "hit", lalu menyusut jadi **95** setelah
dipilah. Yang dibuang, dan **kenapa Anda tidak boleh menyentuhnya**:

| Pola | Jumlah | Kenapa BUKAN N+1 |
|------|--------|------------------|
| `find_one_and_update` dalam loop | 5 | **Sengaja atomik per dokumen.** Ini pengaman balapan pada alokasi roll (`roll_service.py` baris 1062, 1288, 1642). Mengubahnya jadi `bulk_write` **MENGHAPUS** perlindungan itu dan melahirkan kelas bug `INV-CONC-01` yang sudah pernah dibayar mahal di Sesi #077. |
| `for _ in range(200)` | 1 | Loop percobaan bernilai unik (`roll_no`), terbatas dan bukan atas data. |
| `insert_one`/`update_one` dalam loop | 126 | Ini soal **atomisitas (T-01)**, bukan kecepatan baca. Jangan dicampur ke sini. |

### (c) Buktikan sendiri

```bash
python3 scripts/audit_temuan_2026_09.py | grep -A 16 "T-04"
sed -n '35,50p' backend/routers/reporting.py
sed -n '1058,1070p' backend/services/roll_service.py   # contoh yang HARUS dibiarkan
```

### (d) KRITERIA GUGUR (per lokasi, bukan borongan)
Sebuah lokasi **GUGUR** bila salah satu benar — dan Anda **wajib** menilai
satu-per-satu, bukan menyimpulkan semuanya sekaligus:
- loopnya terbatas kecil (`range(n)` kecil, atau atas daftar ≤ ~20 yang dijamin);
- querynya `find_one_and_update` (atomisitas disengaja);
- sudah ada cache/peta di luar loop dan query di dalam loop hanya cadangan.

### (e) Perbaikan

**Langkah 1 — triase, JANGAN perbaiki.** Buat tabel dari 95 kandidat:

| Berkas:baris | Ukuran loop (dari mana datanya?) | Vonis | Alasan |
|---|---|---|---|

Vonis hanya boleh salah satu: `PERBAIKI` · `BIARKAN (sengaja)` · `BIARKAN (loop kecil)`.
Kolom "ukuran loop" wajib menyebut **sumber datanya** (mis. "atas `order['items']`,
biasanya <20 baris" vs "atas seluruh `products`, 2000 baris"). Kalau Anda tidak
bisa menyebut sumbernya, tulis `TIDAK TAHU` — jangan mengarang.

**Langkah 2 — perbaiki HANYA yang bervonis `PERBAIKI`, satu commit per berkas.**
Pola yang dipakai: satu query batch di luar loop, lalu peta di dalam:

```python
# SEBELUM
for b in balances:
    rolls = await db.inventory_rolls.find({"product_id": b["product_id"]}).to_list(500)

# SESUDAH
pids = list({b["product_id"] for b in balances})
semua = await db.inventory_rolls.find({"product_id": {"$in": pids}}).to_list(20000)
peta = {}
for r in semua:
    peta.setdefault(r["product_id"], []).append(r)
for b in balances:
    rolls = peta.get(b["product_id"], [])
```

⚠️ Perhatikan: pola `$in` ini memindahkan batas ke `to_list` tunggal — pastikan
tidak melahirkan pelanggaran T-03 yang baru.

### (f) Gerbang bukti selesai (per commit)
- [ ] Tabel triase lengkap untuk 95 kandidat (boleh dicicil, tapi harus utuh
      untuk berkas yang Anda sentuh).
- [ ] Untuk tiap perbaikan: hasil endpoint **identik** sebelum/sesudah — tempel
      diff JSON-nya (`diff <(curl ... ) <(curl ...)`), bukan kesan.
- [ ] Nol berkas dengan `find_one_and_update` dalam loop yang Anda ubah.
- [ ] `bash scripts/gate.sh` HIJAU (khususnya `INV-CONC-01` bila runtime aktif).

---

## T-05 — Korpus uji: 55/122 gagal ⚠️ **BELUM DIVERIFIKASI — INI TUGAS ANDA**

**Bobot: TINGGI** · Jenis: kepercayaan pada sinyal uji

### (a) Klaim
Menurut `coverage_data/corpus_summary.json`, dari 122 skrip uji: **67 lulus, 55
gagal**. Dugaan saya (dari membaca ekor galatnya) **mayoritas bukan bug baru**,
melainkan ekspektasi uji yang basi. **Dugaan ini belum terbukti.**

### (b) Bukti auditor — dan batasnya

```
total/ok/failed: 122 67 55
```

Kategori kasar dari ekor galat: 27 tak terkategori · 12 `403` (matriks izin lama)
· 5 `409` (aturan bisnis yang memang diperketat kemudian) · 5 login · 4 `404` ·
1 exception · 1 `500`.

**BATAS BUKTI — INI PENTING:** berkas itu **basi dua commit** (lihat §A0-4).
Angka di atas **tidak boleh** Anda kutip sebagai kondisi hari ini. Selain itu
banyak "gagal" sebenarnya skrip yang lulus 13/14 — kegagalan parsial dilaporkan
sebagai skrip gagal.

### (c) Buktikan sendiri — **WAJIB, ini inti temuan ini**

Repo **tidak punya** runner korpus (sudah saya cek: tak ada skrip yang menulis
`corpus_summary.json`). Jadi Anda harus menjalankannya sendiri.

```bash
# 0. Siapkan lingkungan LEBIH DULU — ini bukan opsional.
#    .restore_env.sh punya catatan pelajaran penting: mongo bisa MATI saat kontainer
#    datang, dan bootstrap hanya jalan saat backend START. Urutan salah = gate merah
#    yang BUKAN bug.
bash .restore_env.sh 2>&1 | tail -30

# 1. Uji pytest (yang benar-benar pytest)
cd backend
python3 -m pytest tests/ -p no:randomly -n 0 -q 2>&1 | tail -40
```

⚠️ **Dua jebakan yang sudah tercatat di `SESSION_HANDOFF.md` — jangan diulang:**
1. **POC N dan POC M tidak boleh berjalan bersamaan.** POC N sementara mencabut
   `permission_settings/default` lalu memulihkannya; POC lain yang paralel akan
   melihat keadaan tercabut itu dan gagal **transien**. Karena itu `-p no:randomly -n 0`
   di atas: **berurutan, tanpa acak**.
2. **Jangan menjalankan `gate.sh` atau `verify_*` bersamaan dengan POC.**

```bash
# 2. Skrip POC berbasis HTTP (bukan pytest) — jalankan SATU PER SATU, catat hasilnya.
#    JANGAN paralel. Contoh:
cd /app
for f in backend/test_core_e8_desk_poc.py backend/test_g7_contrabon_poc.py ; do
  echo "=== $f ==="
  timeout 300 python3 "$f" 2>&1 | tail -12
  echo "RC=$?"
done
```

**Hasilkan berkas triase baru** (JANGAN timpa `coverage_data/corpus_summary.json`
yang lama — biarkan sebagai jejak sejarah). Tulis ke
`memory/TRIASE_KORPUS_2026-09.md` dengan tabel:

| Skrip | RC | Lulus/Total | Vonis | Bukti |
|---|---|---|---|---|

Vonis hanya boleh salah satu:
- **`BUG NYATA`** — kode salah. → buka entri di `memory/BUG_REGISTRY.md`.
- **`UJI BASI`** — perilaku sistem sengaja berubah, ujinya yang harus disesuaikan.
  Wajib sebut **commit/fase mana** yang mengubah perilaku itu.
- **`LINGKUNGAN`** — gagal karena seed/urutan/DB, bukan kode.
- **`TIDAK TAHU`** — belum bisa disimpulkan. **Ini vonis yang SAH**; jauh lebih
  baik daripada menebak.

### (d) KRITERIA GUGUR
- Jalankan ulang menunjukkan ≤5 kegagalan → temuan **GUGUR**, korpusnya sehat dan
  hanya berkasnya yang basi. Tempel ringkasan runner.

### (e) Perbaikan
1. Selesaikan tabel triase di atas.
2. Untuk vonis **`UJI BASI`**: perbaiki **ujinya**, jangan kodenya. Setiap
   perubahan uji wajib memuat komentar satu baris yang menyebut **kenapa perilaku
   berubah** dan **fase mana** yang mengubahnya — supaya sesi berikutnya tidak
   mengira ini regresi.
3. Untuk vonis **`BUG NYATA`**: **jangan diperbaiki sekarang.** Daftarkan di
   `memory/BUG_REGISTRY.md` dengan bobot, lalu tanyakan urutannya ke pemilik.
   Perbaikan bug fungsional adalah keputusan bisnis, bukan keputusan Anda.
4. Setelah triase selesai, tulis runner-nya jadi skrip permanen
   (`scripts/run_corpus.py`) supaya angka ini bisa dihasilkan ulang kapan saja —
   dan sambungkan ke T-06.

### (f) Gerbang bukti selesai
- [ ] `memory/TRIASE_KORPUS_2026-09.md` lengkap: **122 baris**, nol sel kosong.
- [ ] Nol vonis "lulus" tanpa keluaran runner yang ditempel.
- [ ] `scripts/run_corpus.py` ada dan bisa dijalankan ulang.
- [ ] Semua vonis `BUG NYATA` sudah punya entri `BUG_REGISTRY.md`.

---

## T-06 — Tak ada CI; riwayat git tergencet

**Bobot: TINGGI** · Jenis: proses

### (a) Klaim
Repo punya perangkat guardrail yang bagus (`gate.sh` bertingkat, 15+ invarian),
tetapi **tak ada yang memaksa menjalankannya**. Ditambah, seluruh sejarah
tergencet ke satu commit "Initial commit".

### (b) Bukti auditor

```
.github/                 : TIDAK ADA
.git/hooks/pre-commit    : TIDAK terpasang
jumlah commit            : 4
scripts/gate.sh          : ADA (tapi manual)
```

Akibat yang bisa diukur: `git bisect` dan `git blame` **tidak berguna** — saat
regresi muncul, tidak ada cara mempersempit penyebabnya.

### (c) Buktikan sendiri

```bash
ls -a .github 2>/dev/null || echo "TIDAK ADA"
ls .git/hooks/pre-commit 2>/dev/null || echo "TIDAK terpasang"
git rev-list --count HEAD
git log --format="%h %ci %s" | cut -c1-100
```

### (d) KRITERIA GUGUR
- `.github/workflows/` ada dan memuat langkah yang menjalankan `gate.sh`; **atau**
- CI dijalankan di platform lain — tunjukkan konfigurasinya.

### (e) Perbaikan

**E-1. Pre-commit hook (paling cepat berdampak).** Buat
`scripts/install_hooks.sh` yang memasang `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "[pre-commit] gate --quick + verifikator temuan"
bash scripts/gate.sh --quick || { echo "GATE MERAH — commit dibatalkan"; exit 1; }
python3 scripts/audit_temuan_2026_09.py >/tmp/temuan.txt 2>&1 || true
awk '/TERBUKTI \(masih cacat\)/{print "[pre-commit] " $0}' /tmp/temuan.txt
```

Hook **tidak** menggagalkan commit karena temuan lama (itu akan memblokir semua
pekerjaan) — ia hanya menggagalkan bila gate statik memerah, dan **melaporkan**
jumlah temuan supaya angkanya terlihat setiap commit.

**E-2. GitHub Actions.** `.github/workflows/gate.yml` — jalankan
`bash scripts/gate.sh --ci` (mode ini sudah ada dan menulis
`memory/GATE_RECEIPT.json`) plus `python3 scripts/audit_temuan_2026_09.py`.
Mulai dari `--quick`/`--ci` saja; mode `--full` butuh Mongo dan seed, tambahkan
belakangan sebagai job terpisah.

**E-3. Riwayat.** Sejarah lama **tidak bisa dipulihkan** — jangan berpura-pura
bisa. Yang bisa dilakukan mulai sekarang: satu temuan = satu commit (§A0-6),
pesan commit deskriptif, **dan jangan pernah `--force`**.

### (f) Gerbang bukti selesai
- [ ] `bash scripts/install_hooks.sh` lalu tempel bukti hook aktif (buat commit
      percobaan yang sengaja memerah, tunjukkan ia tertolak, lalu batalkan).
- [ ] Workflow CI hijau — tempel tautan/keluaran run.
- [ ] `memory/GATE_RECEIPT.json` terbit dari CI, bukan dari laptop.

---

## T-07 — `CODEBASE_MAP.md` melenceng jauh dari kenyataan

**Bobot: TINGGI** — dan lebih tinggi dari yang terlihat. Baca alasannya.

### (a) Klaim
`CODEBASE_MAP.md` (v1.0, **28 Mei 2026**) menggambarkan sistem yang sudah tidak
ada. Ini bukan sekadar dokumen usang: `memory/ENGINEERING_GUARDRAILS.md`
mendaftarkannya sebagai **TIER 0 — WAJIB dibaca tiap sesi** (butir 4). Artinya
**setiap agen baru diperintahkan membaca peta yang salah** sebagai sumber orientasi.

### (b) Bukti auditor

| Klaim di peta | Kenyataan di `5c76055` | Selisih |
|---|---|---|
| `dependencies.py` 58 baris | 169 baris | +111 |
| `schemas.py` 214 baris | 941 baris | +727 |
| `server.py` 272 baris | 290 baris | +18 |
| ~25 router terdaftar | **123** berkas router | +98 |
| 106 endpoint terdaftar | **1.120** endpoint | +1.014 |

Peta juga masih menulis:

```
hash_password(pw) → SHA256 dengan salt "kain-nusantara::"
```

padahal `routers/auth.py` sudah memakai **bcrypt** dengan migrasi transparan
SHA256→bcrypt (baris 1–8 docstring modul). Seorang agen yang mempercayai peta ini
bisa menulis kode hashing yang salah.

### (c) Buktikan sendiri

```bash
python3 scripts/audit_temuan_2026_09.py | grep -A 6 "T-07"
ls backend/routers/*.py | wc -l
grep -rhoE '@router\.(get|post|put|patch|delete)' backend/routers | wc -l
grep -n "TIER 0" -A 8 memory/ENGINEERING_GUARDRAILS.md
grep -n "SHA256" CODEBASE_MAP.md
grep -n "bcrypt" backend/core_utils.py | head -3
```

### (d) KRITERIA GUGUR
- Angka di peta cocok dengan kenyataan (selisih < 20%); **atau**
- peta sudah ditandai usang secara eksplisit **dan** dicabut dari daftar TIER 0.

### (e) Perbaikan

**Jangan menulis ulang peta dengan tangan.** Prosa akan membusuk lagi dalam dua
minggu; itu persis yang sudah terjadi. Buat **generator**.

**E-1.** `scripts/gen_codebase_map.py` — hasilkan `CODEBASE_MAP.md` dari kode:
daftar router + jumlah endpoint + jumlah baris, daftar service, daftar koleksi,
inventaris komponen frontend. Beri penanda di kepala berkas:

```markdown
<!-- DIHASILKAN OTOMATIS oleh scripts/gen_codebase_map.py — JANGAN EDIT TANGAN -->
<!-- Dihasilkan dari commit: <sha> pada <tanggal> -->
```

**E-2.** Tambah guard **`INV-DOC-01`**: `CODEBASE_MAP.md` dianggap **MERAH** bila
angka di dalamnya menyimpang >10% dari hasil hitung ulang. Ikuti pola berkas guard
lain di `scripts/guardrails/`, sertakan `--self-test` dua arah, daftarkan di
`memory/INVARIANTS.md` dan `scripts/gate.sh`.

**E-3.** Perbaiki entri `hash_password` supaya menyebut bcrypt — **verifikasi dulu**
implementasi sebenarnya di `backend/core_utils.py`, jangan salin dari dokumen ini.

**E-4.** Konsolidasi dokumen (usulkan, jangan lakukan sendiri). `SESSION_HANDOFF.md`
2.975 baris + `plan.md` 2.554 baris + `ENTITY_REGISTRY.md` 3.202 baris = beban baca
yang besar. Usulkan ke pemilik: arsipkan sesi >3 bulan ke `memory/arsip/`, sisakan
ringkasan. **Jangan hapus apa pun tanpa persetujuan.**

### (f) Gerbang bukti selesai
- [ ] `python3 scripts/gen_codebase_map.py` menghasilkan peta; `git diff` menunjukkan
      angka berubah ke nilai nyata.
- [ ] Guard `INV-DOC-01` memerah saat peta sengaja dirusak (bukti-merah), hijau
      setelah digenerate ulang.
- [ ] Entri bcrypt benar dan cocok dengan `core_utils.py`.

---

## T-08 — `SEED_DEMO_ENABLED` bawaan `"true"`

**Bobot: SEDANG** · **Perbaikan: satu baris**

### (a) Klaim
Endpoint destruktif `POST /api/admin/seed-demo` (menghapus seluruh koleksi
operasional lalu mengisi ulang) **hidup secara bawaan**. Ia sudah dijaga izin +
token konfirmasi, tetapi bawaannya harus **mati**, bukan hidup.

### (b) Bukti auditor

```
backend/routers/admin.py:405: enabled = os.environ.get("SEED_DEMO_ENABLED", "true").lower()
```

Penjaga yang **sudah ada** (jangan dihapus, ini bagus):
`require_permission(request, "permission", "update")` di baris 402, dan token
konfirmasi `YES_CLEAR_AND_SEED_DEMO_DATA` di baris 413.

### (c) Buktikan sendiri

```bash
grep -rn "SEED_DEMO_ENABLED" backend --include="*.py"
sed -n '396,420p' backend/routers/admin.py
python3 scripts/audit_temuan_2026_09.py | grep -A 2 "T-08"
```

### (d) KRITERIA GUGUR
- Bawaannya sudah `"false"`; **atau** endpointnya hanya terdaftar saat flag
  lingkungan pengembangan aktif.

### (e) Perbaikan

```python
# backend/routers/admin.py:405
enabled = os.environ.get("SEED_DEMO_ENABLED", "false").lower()
```

Lalu **wajib** tambahkan `SEED_DEMO_ENABLED=true` ke `.env` pengembangan dan ke
`.env.example` (T-02 E-3), karena `scripts/seed_reset.sh` dan beberapa POC
memanggil jalur ini. **Periksa dulu siapa saja yang memanggilnya sebelum
mengubah**, jangan sampai memutus alur kerja sendiri:

```bash
grep -rn "seed-demo\|seed_demo\|SEED_DEMO" scripts/ backend/ .restore_env.sh --include="*" | grep -v node_modules
```

### (f) Gerbang bukti selesai
- [ ] Tanpa env: endpoint menjawab **403** — tempel respons.
- [ ] Dengan `SEED_DEMO_ENABLED=true`: seed berjalan — tempel ringkasannya.
- [ ] `bash .restore_env.sh` tetap hijau (ia memakai jalur seed).

---

## T-09 — Saran reorder: tanpa filter `lifecycle`, tanpa `warehouse_id`

**Bobot: SEDANG** · Sudah tercatat sebagai **T9** di `TEMUAN_AUDIT_TRAINING.md`

### (a) Klaim
`GET /api/purchase-requisitions/reorder-suggestions` menyarankan produk yang
**pasti akan ditolak** saat dijadikan PR, dan tidak membawa `warehouse_id` yang
diwajibkan hilir.

### (b) Bukti auditor

Di `backend/services/purchase_requisition_service.py`:

- baris **364** — query produk **tanpa** penyaring lifecycle:
  ```python
  products = await db.products.find({"status": "active"}, {"_id": 0}).to_list(2000)
  ```
- baris **~452–470** — `rows.append({...})` **tidak memuat** kunci `"warehouse_id"`.
- Padahal di berkas **yang sama**, baris **119**, pembuatan PR memakai gerbangnya:
  ```python
  await rnd_gate.assert_orderable(..., where="Purchase Requisition")
  ```

Jadi saran dan validasi memakai aturan berbeda. Gerbang yang benar sudah ada:
`backend/services/rnd_gate.py` — `ORDERABLE = {"produksi"}` (baris 23),
`is_orderable(product)` (baris 75), dan penegakannya **configurable** lewat
`rnd.lifecycle_enforcement`.

### (c) Buktikan sendiri

```bash
python3 scripts/audit_temuan_2026_09.py | grep -A 8 "T-09"
sed -n '357,366p' backend/services/purchase_requisition_service.py
sed -n '112,124p' backend/services/purchase_requisition_service.py
grep -n "ORDERABLE\|def is_orderable\|def lifecycle_of\|enforcement_mode" backend/services/rnd_gate.py
```

### (d) KRITERIA GUGUR
- `reorder_suggestions()` sudah memanggil `rnd_gate` / menyaring `lifecycle`;
  **atau** baris saran sudah memuat `warehouse_id`.

### (e) Perbaikan

**E-1. Samakan aturan dengan hilirnya.** Di `reorder_suggestions()`, hormati mode
penegakan yang sama seperti pembuatan PR — **jangan** menyaring keras tanpa melihat
`enforcement_mode`, karena penegakan itu memang bisa dimatikan/dilunakkan per entitas.

Setelan `rnd.lifecycle_enforcement` (`backend/config_catalog_rnd.py` baris 21–24)
punya **TIGA** nilai, bukan dua — bawaannya `block`:

| Nilai | Arti | Yang harus dilakukan saran reorder |
|-------|------|-----------------------------------|
| `off` | "Abaikan (semua produk boleh dipesan)" | tampilkan apa adanya, tanpa penanda |
| `warn` | "Peringatkan saja (tetap boleh lanjut)" | **tetap tampilkan**, beri penanda |
| `block` | "Tolak (barang belum jadi tidak boleh dipesan)" | sembunyikan dari saran |

Menyaring keras pada mode `warn` adalah **salah** — hilirnya masih mengizinkan PR,
jadi saran yang menyembunyikan barangnya justru memutus alur yang sah:

```python
from services import rnd_gate
mode = await rnd_gate.enforcement_mode(entity_id if entity_id and entity_id != "all" else "")
# di dalam `for p in products:` — sebelum perhitungan apa pun
boleh = rnd_gate.is_orderable(p)
if mode == "block" and not boleh:
    continue
# ... lalu pada rows.append({...}) sertakan penanda supaya layar bisa memberi rambu:
#     "lifecycle": rnd_gate.lifecycle_of(p),
#     "lifecycle_warning": (mode == "warn" and not boleh),
```

⚠️ **Verifikasi sendiri ketiga nilai itu sebelum mengetik** — jangan percaya tabel
di atas begitu saja:

```bash
grep -rn -A 8 "lifecycle_enforcement" backend/config_catalog_rnd.py
grep -n "def enforcement_mode" -A 6 backend/services/rnd_gate.py
```

**E-2. Bawa `warehouse_id`.** Tentukan gudang default yang bermakna — jangan asal
comot yang pertama. Periksa dulu apa yang diwajibkan hilir:

```bash
grep -n "warehouse_id" backend/schemas_purchasing.py | head
grep -rn "warehouse_id" backend/services/purchase_requisition_service.py | head
```

Kalau tidak ada aturan yang jelas, **tanya pemilik** — memilih gudang yang salah
untuk penerimaan barang lebih buruk daripada tidak mengisinya.

**E-3. Perbaiki juga sumber lambatnya** — `product_sales_velocity()` yang dipanggil
fungsi ini adalah lokasi `to_list(100000)` dari T-03. Kerjakan bersamaan **bila
Anda sudah menyelesaikan T-03 Lapis 1**; kalau belum, jangan digabung.

### (f) Gerbang bukti selesai
Buat satu produk uji ber-`lifecycle` non-produksi (mis. `labdip`) yang memenuhi
syarat reorder, lalu uji **ketiga** mode. Tempel respons endpoint untuk masing-masing:

- [ ] `rnd.lifecycle_enforcement = block` → produk itu **TIDAK** muncul di saran.
- [ ] `rnd.lifecycle_enforcement = warn`  → produk itu **MUNCUL**, dengan penanda
      peringatan. (Ini yang membuktikan Anda tidak memasang saringan keras yang
      mengabaikan konfigurasi.)
- [ ] `rnd.lifecycle_enforcement = off`   → produk itu **MUNCUL**, tanpa penanda.
- [ ] Produk ber-`lifecycle = produksi` **selalu** muncul di ketiga mode
      (bukti anti-tuduh-palsu: saringan Anda tidak memakan yang sah).
- [ ] Baris saran memuat `warehouse_id` yang valid; PR yang dibuat dari saran itu
      **berhasil** (bukan 400). Tempel keduanya.

---

## T-10 — `POST /ar-receipts`: 422 mendahului 403

**Bobot: RENDAH** · Sudah tercatat sebagai **T10** di `TEMUAN_AUDIT_TRAINING.md`

### (a) Klaim
Pemanggil **tanpa izin** yang mengirim payload salah menerima **422** berisi
rincian skema, bukan **403**. Bentuk skema bocor ke peran yang tak berwenang.

### (b) Bukti auditor

`backend/routers/ar_receipts.py` baris 65–67:

```python
@router.post("/ar-receipts")
async def create_receipt(payload: ReceiptPayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "ar_receipt", "create")
```

`payload: ReceiptPayload` adalah parameter model, jadi FastAPI **memvalidasi body
lebih dulu**; badan fungsi (tempat `require_permission` berada) baru berjalan bila
validasi lolos. Ini perilaku framework, bukan dugaan.

### (c) Buktikan sendiri

Bukti terbaik adalah **runtime**, bukan pembacaan kode:

```bash
# Login sebagai peran TANPA izin ar_receipt.create (mis. warehouse), lalu:
curl -s -o /tmp/r.txt -w "%{http_code}\n" -X POST "$BASE/api/ar-receipts" \
  -H "Content-Type: application/json" -b "$COOKIE" -d '{"ngawur": 1}'
cat /tmp/r.txt
# Harapan bila temuan BENAR : 422 + rincian field skema
# Harapan bila temuan GUGUR : 403
```

⚠️ Cari peran yang benar-benar tak berizin dulu — jangan asumsikan:

```bash
grep -n "ar_receipt" backend/permissions_config.py
```

### (d) KRITERIA GUGUR
- Percobaan di atas mengembalikan **403** → temuan GUGUR.

### (e) Perbaikan
Pindahkan pemeriksaan izin ke **dependency** sehingga berjalan sebelum validasi
body, **atau** terima `Request` mentah lalu urai body sesudah cek izin. Yang paling
selaras dengan gaya repo ini adalah dependency:

```python
async def _perm_create(request: Request) -> Dict[str, Any]:
    return await require_permission(request, "ar_receipt", "create")

@router.post("/ar-receipts")
async def create_receipt(payload: ReceiptPayload, request: Request,
                         actor: Dict[str, Any] = Depends(_perm_create)) -> Dict[str, Any]:
    ...
```

⚠️ **Peringatan:** urutan eksekusi dependency vs validasi body di FastAPI bergantung
versi. **Jangan percaya potongan kode di atas** — buktikan dengan `curl` bahwa
hasilnya benar-benar 403. Kalau ternyata tetap 422, pakai jalan kedua: ubah
tanda tangan menjadi `request: Request` saja, cek izin, lalu
`payload = ReceiptPayload(**await request.json())` di dalam `try`.

⚠️ **Cari saudaranya — TAPI BACA PERINGATAN INI DULU.** Skrip di bawah
mengembalikan **459 endpoint** pada commit `5c76055`. **459 BUKAN daftar cacat.**
Untuk endpoint yang pemanggilnya memang berwenang, menjawab 422 atas payload rusak
adalah perilaku yang **BENAR** dan harus dipertahankan.

Sebuah endpoint baru layak masuk daftar bila **ketiganya** benar:
1. izinnya sempit (bukan sesuatu yang hampir semua peran punya), **dan**
2. bentuk skemanya memang sensitif (menyingkap struktur uang/pajak/kredit), **dan**
3. Anda sudah membuktikan dengan `curl` bahwa peran tak berwenang menerima 422.

Kalau Anda melaporkan "459 endpoint bermasalah", itu tanda Anda menjalankan skrip
tanpa menilai. Sajikan hasil skrip sebagai **populasi awal**, lalu daftar pendek
hasil penyaringan tiga syarat di atas — dan **jangan perbaiki satu pun** di commit
T-10 selain `/ar-receipts`:

```bash
python3 - <<'PY'
import re, pathlib
for f in sorted(pathlib.Path('backend/routers').glob('*.py')):
    s = f.read_text(errors='ignore')
    for m in re.finditer(r'@router\.(post|put|patch)\("([^"]+)"\)\s*\nasync def \w+\(([^)]*)\)', s):
        sig = m.group(3)
        if re.search(r'\w+\s*:\s*\w*(Payload|Input|Request$|Model)\w*', sig) and 'Depends' not in sig:
            print(f"{f.name}  {m.group(2)}")
PY
```

### (f) Gerbang bukti selesai
- [ ] `curl` tanpa izin + payload ngawur → **403** (tempel).
- [ ] `curl` dengan izin + payload ngawur → **422** (tempel) — validasi tetap jalan.
- [ ] `curl` dengan izin + payload benar → **200** (tempel) — tidak ada regresi.
- [ ] Daftar endpoint sepola (jangan diperbaiki dulu) terlampir.

---

## T-11 — `approve_order` → 409 `INVALID_TRANSITION` setelah SO auto-approved

**Bobot: SEDANG** · Sudah tercatat sebagai **T11** di `TEMUAN_AUDIT_TRAINING.md`

### (a) Klaim
Ketika persetujuan kredit/harga terakhir diputuskan, SO **otomatis** naik ke
`approved`. Manajer yang lalu menekan "Setujui nilai" menerima **409
INVALID_TRANSITION** — pesan yang membingungkan untuk aksi yang sebenarnya sudah
tercapai.

### (b) Bukti auditor

Auto-transisi di `backend/routers/so_approvals.py` baris 221–226:

```python
if new_status == "approved" and so_approvals.all_approved(result):
    if result.get("status") in ("reserved", "waiting_approval", "waiting_stock"):
        result = await _transition(order_id, ["reserved", "waiting_approval", "waiting_stock"],
                                   "approved", actor["name"], "order_approved", ...)
```

Endpoint manual di `backend/routers/sales_orders_extra.py` baris 397, jatuh ke:

```python
result = await _transition(order_id, ["reserved", "waiting_approval"], "approved", ...)
```

`expected_from` **tidak memuat** `"approved"`. Karena status sudah `approved`,
`so_transition` (`backend/services/sales_order_helpers.py` baris ~166) melempar
409 `INVALID_TRANSITION`.

Perhatikan juga ketidakcocokan daftar: jalur otomatis menerima `"waiting_stock"`,
jalur manual **tidak**. Selidiki apakah itu disengaja — **jangan langsung
disamakan** tanpa memahami alasannya.

### (c) Buktikan sendiri

```bash
python3 scripts/audit_temuan_2026_09.py | grep -A 5 "T-11"
sed -n '218,228p' backend/routers/so_approvals.py
sed -n '419,432p' backend/routers/sales_orders_extra.py
sed -n '160,172p' backend/services/sales_order_helpers.py
```

Reproduksi runtime (lebih kuat dari membaca kode):
1. Buat SO yang memicu approval kredit **dan** approval nilai.
2. Putuskan approval kredit lewat Pusat Persetujuan → amati SO naik `approved`.
3. Panggil `POST /api/sales-orders/{id}/approve` sebagai manajer.
4. Harapan bila temuan benar: **409** dengan `"code": "INVALID_TRANSITION"`.

### (d) KRITERIA GUGUR
- Langkah 3 mengembalikan 200, atau 409 dengan pesan yang **menjelaskan** bahwa
  pesanan sudah disetujui (bukan `INVALID_TRANSITION` mentah).

### (e) Perbaikan

Jadikan `approve_order` **idempoten**. Di `backend/routers/sales_orders_extra.py`,
sebelum memanggil `_transition`:

```python
# Sesudah pending_approvals 'nilai' ditandai approved dan advance_so_if_all_approved
# mengembalikan None: pesanan mungkin SUDAH naik ke approved lewat jalur otomatis
# (so_approvals.py). Itu bukan galat — hasilnya sudah tercapai.
if result is None:
    kini = safe_doc(await db.sales_orders.find_one({"id": order_id}, {"_id": 0}))
    if kini and kini.get("status") == "approved":
        return kini                      # idempoten: 200, bukan 409
    result = await _transition(order_id, ["reserved", "waiting_approval"], "approved",
                               actor["name"], "order_approved", {"approved_by": actor["name"]})
    await set_order_rolls_status(order_id, "committed")
```

⚠️ **Jangan lewatkan `set_order_rolls_status`.** Kalau jalur otomatis sudah
menjalankannya (baris 225 `so_approvals.py` memang menjalankannya), maka melewatkan
di jalur idempoten **benar**. **Buktikan** itu: periksa status roll pesanan setelah
jalur otomatis — harus sudah `committed`.

```bash
grep -n "set_order_rolls_status" backend/routers/so_approvals.py backend/routers/sales_orders_extra.py
```

⚠️ Sebelum mengubah, jalankan POC yang menyentuh alur ini supaya Anda punya
garis dasar: `backend/test_core_e8_desk_poc.py` (POC Meja, 97 kasus menurut
`SESSION_HANDOFF.md`).

### (f) Gerbang bukti selesai
- [ ] Reproduksi 4 langkah di atas: sekarang **200**, dan isi pesanan yang
      dikembalikan benar (tempel JSON).
- [ ] Roll pesanan berstatus `committed` **tepat satu kali** — tunjukkan tidak ada
      efek ganda.
- [ ] SO yang belum layak disetujui **tetap** 409 (jangan sampai Anda melonggarkan
      gerbangnya) — tempel buktinya.
- [ ] `backend/test_core_e8_desk_poc.py` hijau sebelum & sesudah.

---

# §4 — URUTAN KERJA YANG DIWAJIBKAN

Kerjakan berurutan. Jangan lompat; tiap gelombang membuka gelombang berikutnya.

**Gelombang 1 — pulihkan kepercayaan pada sinyal (tanpa ini semua langkah lain menebak)**
1. **T-05** — triase korpus uji. *Ini yang pertama.* Selama 55 kegagalan belum
   diklasifikasi, Anda tidak bisa tahu apakah perbaikan Anda merusak sesuatu.
2. **T-06** — pasang pre-commit hook + CI. Setelah T-05, sinyalnya layak dijaga.

**Gelombang 2 — murah, risiko rendah, hasil langsung**
3. **T-02** — CORS + cookie + `.env.example`. (<1 jam, bobot tertinggi per menit.)
4. **T-08** — satu baris; kerjakan bersama T-02 karena sama-sama menyentuh `.env.example`.
5. **T-07** — generator peta + `INV-DOC-01`. Menghentikan agen berikutnya membaca peta salah.

**Gelombang 3 — cacat fungsional yang sudah Anda catat sendiri**
6. **T-11** → 7. **T-09** → 8. **T-10**. Berurutan menurut bobot.

**Gelombang 4 — kinerja, bertahap dan terukur**
9. **T-03** Lapis 1–3 (perbaiki saring-di-Python, `explain()`, guard `INV-PERF-01`).
10. **T-04** triase (tabel dulu, perbaikan belakangan).

**Gelombang 5 — arsitektural, butuh keputusan pemilik**
11. **T-01** Langkah 1 (tutup lubang `resolve_escalation`) → Langkah 2 (inventarisasi)
    → **BERHENTI dan tanya** untuk Langkah 3.

---

# §5 — YANG DILARANG (RINGKASAN)

| # | Larangan | Kenapa |
|---|---|---|
| 1 | Mengubah `scripts/audit_temuan_2026_09.py` agar temuan lewat | Segel SHA-256 dicetak tiap jalan |
| 2 | Mengklaim status tanpa menempel keluaran perintah | "Klaim tanpa receipt = void" |
| 3 | Mengutip `coverage_data/*.json` sebagai kondisi hari ini | Basi 2 commit (§A0-4) |
| 4 | Mengubah `find_one_and_update` dalam loop jadi `bulk_write` | Menghapus pengaman balapan `INV-CONC-01` |
| 5 | Menjalankan POC N dan POC M bersamaan | Kegagalan transien; tercatat di `SESSION_HANDOFF.md` |
| 6 | Menjalankan `gate.sh`/`verify_*` bersamaan dengan POC | Sumber "hijau lalu merah" palsu |
| 7 | Memperbaiki bug fungsional temuan T-05 tanpa persetujuan | Urutan bug = keputusan bisnis |
| 8 | Menggabung >1 temuan dalam satu commit | Riwayat sudah tergencet (T-06) |
| 9 | "Sekalian merapikan" di luar cakupan | Sumber regresi paling umum |
| 10 | Menebak nama field/enum/status | Semua contoh kode di sini bertanda ⚠️ = **verifikasi dulu** |
| 11 | Menghapus dokumen/koleksi tanpa persetujuan tertulis | Tak bisa dibatalkan |
| 12 | `git push --force` / menulis ulang riwayat | Sisa riwayat tinggal sedikit |

---

# §6 — FORMAT LAPORAN AKHIR (WAJIB)

Tulis ke `memory/LAPORAN_PERBAIKAN_2026-09.md`. Struktur **wajib** persis ini:

```markdown
# LAPORAN PERBAIKAN — <tanggal> — agen <nama/model>

## 1. Baseline
<keluaran §1 apa adanya, termasuk baris segel sha256>

## 2. Hasil verifikasi ulang per temuan
| ID | Vonis saya | Bukti (perintah + keluaran) | Tindakan |
|----|-----------|------------------------------|----------|
| T-01 | TERBUKTI / GUGUR / TIDAK BISA DIUJI | <blok kode> | diperbaiki / ditunda / tidak berlaku |
...

## 3. Perubahan yang dilakukan
Per commit: sha · temuan · berkas · bukti-merah SEBELUM · bukti-hijau SESUDAH.

## 4. Yang TIDAK saya kerjakan dan kenapa
(Wajib diisi. "Tidak ada" hanya sah bila 11 temuan benar-benar tuntas.)

## 5. Temuan BARU yang saya jumpai
(Dicatat saja — TIDAK diperbaiki. Sertakan berkas:baris.)

## 6. Verifikasi akhir
<keluaran audit_temuan_2026_09.py>
<keluaran gate.sh>
<ringkasan runner korpus uji>

## 7. Pertanyaan untuk pemilik
(Keputusan yang saya TIDAK ambil sendiri — mis. T-01 Opsi A vs B.)
```

**Aturan penutup — baca sekali lagi sebelum Anda menyatakan selesai:**

> Laporan yang jujur menyebut apa yang **gagal** dan apa yang **belum dipahami**.
> Laporan yang seluruhnya hijau, tanpa satu pun `TIDAK TAHU`, tanpa satu pun
> pertanyaan untuk pemilik, dan tanpa satu pun temuan yang GUGUR — bukan tanda
> pekerjaan yang baik. Itu tanda verifikasi yang tidak benar-benar dilakukan.
> Sebelas temuan ini ditulis oleh auditor yang **bisa keliru**; kalau tidak ada
> satu pun yang Anda gugurkan atau ralat, kemungkinan besar Anda tidak memeriksa,
> melainkan menyetujui.

---

**Berkas pendamping:** `scripts/audit_temuan_2026_09.py` (segel `sha256:c0baaa80a82dc16a`)
**Commit acuan:** `5c76055` · **Tanggal audit:** 2026-09-05
