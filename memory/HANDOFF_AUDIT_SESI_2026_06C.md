# HANDOFF — AUDIT PEKERJAAN TERAKHIR (sesi 2026-06c)

> **STATUS EKSEKUSI (sesi lanjutan, atas izin pemilik: "kerjakan semua T1–T8"):**
> **T1–T8 SUDAH DIKERJAKAN & DIVALIDASI.** Bukti (preview):
> · T1 `GET /api/inventory/rolls/{id}/cost-history` kini `require_any_permission`
>   (`wms.view` / `accounting.view` / `product.view`) → **200 untuk finance,
>   sales_admin, warehouse, manager, admin**; galat pengambilan bukti TIDAK lagi
>   ditelan (`recon-suspect-cost-history-error`).
> · T2 dialog papan hanya meminta catatan bila `ACTION_META.note_field` ada
>   (transfer · kontrabon verifikasi/ACC · tagihan supplier → dialog Ya/Batal).
> · T3 catatan kosong TIDAK dikirim → `approval_reason` tetap default server
>   ("Disetujui sesuai hasil cycle count").
> · T4 `_post_bill()` memakai `updated.get("po_id")` + melewati `sync_po_billing`
>   bila kosong → tagihan tanpa PO **200**, bukan 500 `KeyError`.
> · T5 papan menerima `actor`; `_action_block_reason()` membaca
>   `approval_matrix_service` (SoD + ambang Direksi) → `action.blocked_reason`,
>   tombolnya tampil MATI beserta alasannya (server tetap 403 bila dipaksa).
> · T6 `WaitingBoardsStrip.onActed` dinaikkan ke pemilik layar (OperationsView
>   memaksa daftar Transfer & Stock Opname memuat ulang; FinanceDesk `load`).
> · T7 `roll_cost_history.record()` dipanggil SESUDAH `update_one` dan hanya bila
>   `modified_count` (interco · interco_return · landed_cost).
> · T8 kunci `cycle_count_adjustment` DIHAPUS dari `REASONS` (tidak ada penulis;
>   penyesuaian opname mengubah kuantitas, bukan HPP/unit).
> Pagar: `verify_data_integrity` 242 PASS/0 FAIL · `verify_home_kpi` 108 PASS ·
> `verify_approval_queues` 223 PASS · `verify_blocking_dialogs` · `verify_error_notice`
> 243 PASS · agen uji `iteration_255` **18/18 PASS** (`backend/tests/test_iter255_t1_t8.py`).
> T9 & T10 tetap CATATAN (belum dikerjakan sesuai keputusan pemilik).

> Dibuat: **2026-06 (audit pasca-implementasi, BELUM ADA PERBAIKAN DIJALANKAN)**
> Cakupan: tiga pekerjaan sesi terakhir — (1) nilai rupiah tagihan supplier di papan,
> (2) riwayat nilai (HPP) roll, (3) papan bisa ditindak.
> Sifat dokumen: **temuan saja**. Tidak ada satu baris kode pun diubah untuk temuan di
> bawah ini; eksekusi menunggu keputusan pemilik.
>
> Keadaan dasar saat audit: `gate.sh --full` HIJAU 395 s · `verify_data_integrity`
> 242 PASS · 0 FAIL · 0 WARN · POC `2026-06b` 35 PASS · POC `2026-06c` 21 PASS ·
> POC isolasi E-0 83 PASS · agen uji `iteration_254` nol temuan.
> Artinya: temuan di bawah ini **lolos dari semua pagar yang ada** — jadi selain
> memperbaiki kodenya, tiap temuan juga menuntut PAGAR baru (aturan emas
> `memory/BUG_REGISTRY.md`).

---

## T1 — [TINGGI] Bukti "Riwayat Nilai (HPP)" MUSTAHIL muncul di layar Keuangan (403 ditelan)

**Apa yang terjadi.** Endpoint `GET /api/inventory/rolls/{id}/cost-history`
(`routers/inventory.py`) memakai izin **`wms.view`**. Matriks izin nyata:

| peran | `wms` | `product` | `accounting` |
|---|---|---|---|
| finance | **(tidak ada)** | view | view |
| sales_admin | view | view | — |
| warehouse · manager · admin | view … | view | — / manage |

Jadi pengguna **finance** — orang yang pekerjaannya membuka *Buku Besar → Rekonsiliasi
Persediaan* — dijawab **403 `Permission ditolak: wms.view`**. Terbukti lewat HTTP:

```
finance@ → GET /api/inventory/rolls/<id>/cost-history  →  403 {"detail":"Permission ditolak: wms.view"}
finance@ → GET /api/inventory/rolls?page=1&page_size=1 →  200   (jadi bukti ROLL tetap tampil)
```

**Kenapa TENANG (dan karena itu mahal).** Di `InventoryReconTab.openEvidence()`
pengambilan riwayat dibungkus `try/catch` kosong ("bukti tambahan bersifat opsional"),
sehingga blok `recon-suspect-cost-history` **tidak pernah dirender tanpa satu pun pesan**.
Layar terlihat "belum jadi", padahal justru inilah permintaan pemilik: *"ikut sebagai
bukti di tuduhan selisih"*. Yang paling sering terjadi bukan galat — melainkan orang
menyimpulkan fiturnya tidak ada.

**Kenapa lolos pagar.** POC `2026-06c` N2 menguji endpoint sebagai **admin** dan menguji
403 hanya untuk **badan usaha lain**; tak ada satu pun kasus "peran yang layarnya memakai
data ini". Agen uji juga membuka layar sebagai admin.

**Arah perbaikan (usul, belum dijalankan).**
1. Izin endpoint diganti "SALAH SATU dari" (`require_any_permission`) —
   `("wms","view")` **atau** `("accounting","view")` **atau** `("product","view")`:
   nilai persediaan adalah urusan akuntansi, bukan hanya gudang.
2. Galat pengambilan bukti **jangan ditelan**: tampilkan satu baris
   "riwayat nilai tidak bisa dibaca dengan izin Anda" (kelas regresi B5 —
   kegagalan tidak boleh tampil sebagai kabar baik).
3. Pagar: tambahkan ke POC `2026-06c` matriks *peran × layar* — setiap layar yang
   MENAMPILKAN data harus punya minimal satu peran non-admin yang bisa membacanya.

---

## T2 — [SEDANG] Catatan yang ditulis orang DIBUANG diam-diam pada 4 dari 9 papan

**Apa yang terjadi.** `ACTION_META` (`services/approval_backlog_service.py`) memberi
`note_field: ""` untuk `transfer`, `contra_bon_verify`, `contra_bon_approve`,
`vendor_bill` — endpoint tujuannya memang tak punya field catatan. Tetapi dialognya
SELALU meminta "Catatan (opsional)" (`WaitingQueueBoard.act()`), dan pada
`frontend/src/components/WaitingQueueBoard.jsx:79`:

```js
if (a.note_field) body[a.note_field] = note || "";   // ← tanpa note_field: catatan HILANG
```

Orang mengetik alasan/catatan, menekan **Setujui**, dokumen disetujui — dan catatannya
tidak tersimpan di mana pun (tidak di dokumen, tidak di audit). Untuk keputusan yang
menahan uang (kontrabon, tagihan supplier) ini persis kelas "salah tetapi tenang".

**Arah perbaikan (usul).** Pilih satu, jangan dua-duanya:
(a) sembunyikan isian catatan bila `note_field` kosong (dialog jadi Ya/Batal murni), atau
(b) kirim catatannya ke jejak audit endpoint tersebut (menambah field ber-arti di
    dokumen = mengubah kontrak endpoint, jadi butuh keputusan pemilik).
Pagar: uji "apa yang diketik pengguna ikut tersimpan" untuk tiap kunci `ACTION_META`
yang menampilkan isian.

---

## T3 — [SEDANG] Menyetujui stock opname dari papan MENGHAPUS alasan bawaannya

**Apa yang terjadi.** `CycleCountApprove.reason` punya default berarti
(`"Disetujui sesuai hasil cycle count"`) yang tersimpan sebagai
`cycle_count_sessions.approval_reason` + audit. Aksi papan mengirim
`reason: ""` saat catatan dikosongkan (lihat kutipan di T2) — nilai kosong **menimpa**
default, sehingga penyesuaian stok yang MENGUBAH kuantitas persediaan tercatat
**tanpa alasan apa pun**.

**Arah perbaikan (usul).** Jangan kirim field catatan bila pengguna mengosongkannya
(biarkan default server bekerja): `if (a.note_field && note) body[a.note_field] = note;`
Pagar: uji nilai `approval_reason` sesudah persetujuan dari papan tanpa catatan.

---

## T4 — [SEDANG] `POST /api/vendor-bills/{id}/approve` bisa 500 (bukan 4xx) — `KeyError: 'po_id'`

**Apa yang terjadi.** `routers/vendor_bills.py:359` → `await sync_po_billing(updated["po_id"])`
membaca kunci dengan `[]`, bukan `.get()`. Tagihan tanpa `po_id` (mis. tagihan makloon
yang dibuat jalur lain / dokumen impor lama) membuat pintu persetujuan menjawab
**HTTP 500 Internal Server Error** — dan di papan yang baru, 500 itu muncul sebagai
"Gagal setujui …" tanpa sebab yang bisa dibaca siapa pun.

**Bukti.** Terjadi NYATA saat penulisan POC `2026-06c` (tagihan uji tanpa `po_id` →
500, jejak `KeyError: 'po_id'` di `/var/log/supervisor/backend.err.log`). Data demo
sekarang **0 dari 12** tagihan tanpa `po_id`, jadi cacatnya laten — tidak berarti tidak ada.

**Arah perbaikan (usul).** `po_id = updated.get("po_id")`; lewati `sync_po_billing` bila
kosong (tagihan makloon memang tak punya PO), dan uji satu tagihan tanpa PO.
Pagar: kasus "tagihan tanpa PO" di POC kontrabon/tagihan.

---

## T5 — [SEDANG] Tombol papan hanya diperiksa dengan IZIN PERAN — aturan lain baru terasa setelah diklik

**Apa yang terjadi.** `_row_action()` memberi tombol berdasarkan matriks izin peran saja.
Aturan lain (pemisahan tugas pembuat≠penyetuju, ambang nilai butuh Direksi, tahap
berjenjang, mode "Semua Entitas") baru ditegakkan **oleh endpoint** setelah tombol
ditekan → pengguna melihat tombol yang untuk dokumen ITU pasti gagal (403/409).

Ini **bukan lubang keamanan** (server tetap menolak) tetapi janji yang tak bisa ditepati.
Paling terasa pada: PO custom di atas ambang Direksi, dokumen yang dibuat sendiri, dan
konteks *Semua Entitas*.

**Arah perbaikan (usul).** Sertakan alasan-tak-boleh dari server (`action: null` +
`action_blocked_reason`) untuk minimal dua aturan yang paling sering: SoD dan ambang
nilai. Pagar: uji "pembuat dokumen tidak melihat tombol atas dokumennya sendiri".

---

## T6 — [RENDAH] Daftar di bawah papan tidak ikut menyegar sesudah keputusan dari papan

`WaitingBoardsStrip` memuat ulang **dirinya sendiri** (`onActed=load`), sedangkan tab di
bawahnya (mis. daftar Transfer di layar Operasi, antrean Meja Finance) tetap memakai data
lama. Baris hilang dari papan, tetapi dokumen yang sama masih tampil "menunggu ACC" di
tabel di bawahnya sampai layar dimuat ulang manual — dua angka berbeda di SATU layar,
kelas yang justru diperangi INV-HOME-01.

**Arah perbaikan (usul).** Naikkan `onActed` ke pemilik layar (OperationsView /
FinanceDesk) supaya ia memuat ulang daftarnya juga.

---

## T7 — [RENDAH] Jejak nilai roll ditulis SEBELUM nilainya benar-benar berubah

`roll_cost_history.record()` dipanggil sebelum `inventory_rolls.update_one(...)` di
`interco_return_service`, `interco_service`, dan `landed_cost_service`. Bila pembaruan
roll gagal (atau proses mati di antaranya), jejaknya sudah mengaku ada perubahan yang tak
pernah terjadi. Peluangnya kecil, akibatnya membingungkan: jejak yang seharusnya menjadi
alat bukti justru berbohong.

**Arah perbaikan (usul).** Tulis jejak SESUDAH pembaruan berhasil (nilai lama sudah
dipegang di variabel), atau catat hasil `modified_count`.

---

## T8 — [RENDAH] Alasan `cycle_count_adjustment` terdaftar tanpa satu pun penulis

`roll_cost_history.REASONS` memuat `"cycle_count_adjustment"` tetapi tidak ada satu pun
pemanggil (`grep` = nol hasil). Padahal penyesuaian stock opname **memang bisa** mengubah
nilai persediaan lewat `apply_cycle_count_adjustment`. Dua kemungkinan, keduanya perlu
diputuskan: (a) sambungkan pencatatnya di jalur penyesuaian opname, atau (b) hapus
kuncinya. Nama yang hidup di registry tanpa penulis membuat agen berikutnya percaya
jejaknya sudah ada — kelas drift D2 yang sudah pernah menggigit repo ini.

---

## T9 — [CATATAN, bukan cacat] Riwayat nilai roll dimulai dari kosong

Tidak ada backfill historis: roll yang nilainya berubah SEBELUM sesi ini menampilkan
"Belum ada perubahan HPP tercatat". Ini keputusan sadar (jejak tidak boleh dikarang dari
tebakan), tetapi perlu disebut supaya tidak dilaporkan sebagai bug. Bila diinginkan,
backfill hanya boleh dari sumber yang benar-benar ada (`cost_basis.previous_unit_cost`,
`landed_cost_refs`) dan WAJIB ditandai `reason: "backfill_dari_jejak_dokumen"`.

---

## T10 — [CATATAN pengujian] POC tidak boleh dijalankan berbarengan dengan pemeriksa lain

Terjadi dua kali saat sesi lalu: `verify_data_integrity` dijalankan bersamaan dengan POC
(yang memakai snapshot/restore basis data) → 4–5 FAIL palsu ("stats None",
"reserved 220 != Σbalances 0"). Bukan cacat produk, tetapi jebakan yang memakan waktu.
Usul: `gate.sh`/POC memasang **kunci berkas** (`memory/.poc.lock`) dan pemeriksa lain
menolak jalan selagi kunci itu ada.

---

## Ringkasan prioritas

| # | Temuan | Tingkat | Kelas |
|---|---|---|---|
| T1 | Riwayat nilai 403 untuk peran finance, galat ditelan | **TINGGI** | fitur mustahil terlihat oleh penggunanya |
| T2 | Catatan pengguna dibuang pada 4 papan | SEDANG | janji layar tidak ditepati |
| T3 | Alasan bawaan stock opname terhapus jadi kosong | SEDANG | jejak keputusan hilang |
| T4 | `vendor-bills/{id}/approve` bisa 500 (`po_id`) | SEDANG | galat 5xx untuk keadaan sah |
| T5 | Tombol hanya cek izin peran (SoD/ambang belakangan) | SEDANG | tombol yang pasti gagal |
| T6 | Daftar di bawah papan tidak ikut segar | RENDAH | dua angka di satu layar |
| T7 | Jejak nilai ditulis sebelum perubahan | RENDAH | bukti bisa berbohong |
| T8 | Alasan terdaftar tanpa penulis | RENDAH | drift registry |
| T9 | Riwayat mulai dari kosong | catatan | keputusan sadar |
| T10 | POC vs pemeriksa lain berbenturan | catatan | jebakan pengujian |

**Belum ada yang dieksekusi.** Usul urutan bila diizinkan: T1 → T3 → T2 → T4 → T5,
masing-masing beserta pagarnya, lalu T6–T8 sebagai satu rapikan kecil.
