# GL-3 — Koneksi CoA ↔ rekening kas/bank (Bagian B)

## 1. Desain hari ini (dari kode, dibuktikan di DB)

* `bank_accounts` = master tunggal untuk bank DAN kas (`kind: bank|cash`). Tiap rekening punya `gl_account_code` (sub-akun CoA) — dibuat otomatis `1-1201, 1-1202…` (bank, induk `1-1200`) dan `1-1101, 1-1102…` (kas, induk `1-1100`) oleh `cash_bank._ensure_sub_account` (`cash_bank.py:50-69`). Maksimum 99 per jenis. Induk `1-1100/1-1200` bertanda `is_header` dan, pada data uji, bersaldo 0.
* Penentuan akun kas saat posting: `post_journal` memanggil `cash_bank.resolve_code(org, cash_account_id, code, strict=False)` bila baris memuat `cash_account_id` ATAU kode `1-1100/1-1200` (`gl_engine.py:139-143`). Tanpa id → rekening `is_default` jenis itu (cache modul `_DEFAULT_CACHE`, dibersihkan hanya di proses yang sama). Lapis kedua: modul domain sering memanggil `resolve_code(strict=True)` lebih dulu (penerimaan, bayar AP, komisi, refund, kas bon, pengajuan dana, pajak) sehingga rekening tak ada/nonaktif ditolak dengan pesan jelas (TERBUKTI: `cash_account_id=nonexistent` → 400; rekening Escrow nonaktif → 400).
* Saldo awal: dijurnal `Dr sub-akun / Cr 3-1950` sekali (`opening_posted`); edit `opening_balance` sesudah diposting diabaikan diam-diam (TERBUKTI: PUT 999 → tetap 250.000.000, status 200 tanpa peringatan).
* Transfer internal (`/cash-bank/transfers`): pending → disetujui orang lain (SoD, TERBUKTI), cek saldo sumber (TERBUKTI: Rp 900 M ditolak), biaya admin → `6-1600` (H). Jurnal `auto=False` (manual-ish): ditolak di periode tutup.
* Migrasi startup `cash_bank._migrate_header_lines` MENGUBAH baris jurnal lama yang memakai induk menjadi rekening default saat ini (`cash_bank.py:87-104`) — riwayat bisa ditulis ulang ke rekening yang bukan rekening aslinya (dibuktikan dari kode; tidak dijalankan).
* Bukti kas BKM/BKK diterbitkan per jurnal per sub-akun (`cash_voucher.py`), turunan jurnal.
* Kunci periode per rekening (`cash_period_lock.py`): jurnal otomatis ke periode terkunci digeser, manual ditolak. Memakai `str(date)[:7]` (potongan string), berbeda dari `gl_periods.period_of` (WIB) — tiga definisi "periode" hidup berdampingan (lihat GL-15).

## 2. Jalur yang bisa memilih rekening vs tidak

| Alur | API menerima `cash_account_id`? | UI memilih rekening? | Perilaku bila kosong |
|---|---|---|---|
| Penerimaan pembeli (AR) | Ya | Ya (ReceiptDialog) | method `cash`/`tunai` → kas default; lainnya → bank default |
| Bayar AP / AP+PPh | Ya | Ya (ApPanel) | bank default |
| Refund pembatalan | Ya | Ya (CancellationPanel) | tunai→kas default; lainnya bank default |
| Kliring giro | Wajib (bank aktif) | Ya | — |
| Kas bon (Kas Bon) / Pengajuan dana | Ya | Ya | `source=kas/bank` → default |
| Setor pajak | Ya | Ya (TaxRecordsPanel) | bank default |
| Kas kecil, transfer | Wajib | Ya | — |
| **Bayar komisi** | Ya (API) | **Tidak ada tombol bayar komisi di UI sama sekali** (`CommissionsPanel.js` hanya `approve`) | bank default |
| **Booking fee, titipan (terima/kembali)** | **Tidak** (`DepositReceive/DepositRefund` tanpa field) | Tidak | **bank default — walau metode `cash`** (TERBUKTI JV/00116 → `1-1201`) |
| **Biaya all-in (invoice biaya, penyaluran)** | Tidak | Tidak | `GL_BANK` hardcode → bank default |
| **Pinjaman (cair/angsuran), aset tetap (beli/lepas), marketing fee, uang muka subkon, upah** | Tidak (hanya `source` kas/bank) | hanya dropdown "Sumber kas" kas/bank | default jenis itu |

Akibat: perusahaan dengan >1 rekening bank (mis. rekening escrow KPR terpisah dari operasional) tidak bisa menandai rekening untuk sekitar separuh arus uang; semuanya mendarat di rekening *default* dan harus dibetulkan lewat transfer internal. Rekening per proyek tidak ada: `CashAccountIn` tidak punya `project_id` (`models_p82.py`); proyek hanya DISIMPULKAN dari dokumen sumber (`gl_project_cash.project_resolver`).

## 3. Apa yang terjadi bila …

| Kondisi | Hasil (bukti) |
|---|---|
| `cash_account_id` kosong | jatuh ke rekening default jenis (cache proses) |
| `cash_account_id` salah/tak ada, dipanggil lewat API domain | 400 jelas (`strict=True`) |
| …tetapi tiba di handler event (outbox) | `strict=False` → **diam-diam jatuh ke rekening default** (`cash_bank.py:183-196`); rekening nonaktif TETAP menerima posting dari event yang sudah antre |
| Rekening dinonaktifkan padahal bersaldo | DIIZINKAN (Escrow Rp 228,7 jt, TERBUKTI). `position` mengeluarkannya dari "Total" (field `inactive_balance` ada); neraca tetap memuatnya |
| Rekening default dinonaktifkan | ditolak (OK) |
| Rekening dihapus | tidak ada endpoint hapus (hanya `data_mgmt_purge` grup "mitra", menyisakan akun GL & jurnal) |
| Saldo negatif | **Tidak dicegah** pada AP, komisi, pajak, pinjaman, aset, refund, upah, dll.; hanya transfer & kas kecil memeriksa. TERBUKTI: bayar AP Rp 40 jt dari Kas Kecil bersaldo 0 → −Rp 37 jt (layar Posisi Kas menampilkan banner "Saldo buku negatif") |
| Sub-akun kas/bank dinonaktifkan lewat layar Bagan Akun | `accounts.is_active=false` TETAPI master `bank_accounts` tetap aktif, posting tetap jalan (TERBUKTI 1-1202) → dua bendera status tak sinkron |
| Akun sembarang dibuat di Bagan Akun dengan `parent_code=1-1200` (`1-1203`) | terlihat sebagai "kas" oleh arus kas (prefix `1-12`) tetapi tidak oleh Kas & Bank (tak ada master) — TERBUKTI arus kas memuat `1-1203`, Posisi Kas tidak |
| `POST /bank/accounts` (dipakai dialog "Rekonsiliasi Bank → + Rekening") | **Menerima `gl_account_code` APA PUN yang ada di CoA**: `1-1300 Piutang`, induk `1-1200`, atau sub-akun rekening lain (tanpa uji kind/induk/unik). TERBUKTI-API+UI: dropdown dialog menampilkan `1-1100…1-1800` (Piutang, Persediaan, Kas Bon, WIP…). Menunjuk `1-1201` untuk rekening kedua → saldo bank DOBEL (Posisi Kas: Total Rp 15,76 M vs kas neraca Rp 8,01 M); menunjuk `1-1300` → Piutang Rp 772,95 jt muncul sebagai "saldo bank" dan tiap jurnal piutang menerbitkan BKM/BKK (BKM/2026/0025). `PUT` dapat mengarahkan ulang ke induk `1-1200`. (GL-08) |

## 4. Angka kas di layar vs buku besar

| Sumber angka | Nilai (instance uji akhir) | Definisi |
|---|---|---|
| `/gl/reports/balance-sheet` (kas & bank, akun `1-11*,1-12*`) | Rp 8.006.942.936 | semua sub-akun ≤ as-of |
| `/gl/reports/cash-flow-projects` (`closing_cash`) | Rp 8.011.942.936 | prefix `1-11/1-12`, termasuk akun `1-1203` manual |
| `/cash-bank/position` total (setelah dialog Rekonsiliasi Bank) | Rp 15.761.930.872 | Σ rekening **aktif**, semua tanggal, akun GL kembar dihitung dobel |
| Buku kas rekening (`/cash-bank/book`) | konsisten dgn GL per sub-akun | sumber jurnal, bukan subledger |
| Rekonsiliasi bank (`bank_match.reconciliation`) | saldo buku = GL **saat ini** vs saldo mutasi terakhir | tidak "as of tanggal mutasi" (jurnal yang tanggalnya setelah mutasi terakhir ikut) |

Posting otomatis yang digeser ke 2027-01-01 (bulan berjalan sudah ditutup) hadir di Posisi Kas dan buku kas (tidak memfilter tanggal masa depan) tetapi tidak di neraca per hari ini.

## 5. Akun CoA yang tak terhubung / tak terlindungi
* Tidak pernah diposting alur normal: `1-1700`, `3-1100`.
* Tidak ada penjaga bahwa akun yang dipakai kode **ada & bertipe benar**: `post_journal` hanya menolak kode tak ada; tipe tidak diperiksa ([DARI-KODE] `comp.gl_expense/gl_liability/gl_ap` pada komponen biaya all-in disimpan apa adanya oleh `POST /cost-components`, sehingga akun beban bisa terpasang sebagai akun titipan).
* Akun yang dipakai kode tetapi bisa diubah user di layar CoA: SEMUA (nama, tipe jika belum dipakai, nonaktif, parent). Contoh nyata: `2-1400` dinonaktifkan oleh finance → penerimaan berikutnya TETAP memposting ke akun itu; `1-1700` (tak terpakai) bisa diganti tipe menjadi `revenue`; membuat akun `"2-1400 "` (spasi) dan `"ABC"`, `4-9999` bertipe asset diterima (TERBUKTI GL-13).
* Layar Bagan Akun tidak menampilkan induk/anak, status header, atau bahwa sebuah akun "dikunci sistem" (screenshot `img/gl/acc_Bagan_Akun.png`).

## 6. Terverifikasi OK
* Induk kas/bank tidak menerima saldo; posting ke induk diarahkan ke default (jurnal manual `1-1200` → `1-1201`, TERBUKTI), meski diam-diam (tidak ada pemberitahuan).
* Transfer: SoD, cek saldo, biaya admin, persetujuan hanya `bank:approve`.
* Penerimaan ke rekening nonaktif/tak ada ditolak; rekening default tak bisa dinonaktifkan.
* Bukti kas BKM/BKK terbit otomatis per jurnal yang menyentuh sub-akun kas (30+ dokumen pada uji).

## 7. Tidak bisa diverifikasi
* `cash_period_lock` (kunci rekening) end-to-end — tidak dijalankan (butuh rekonsiliasi `seimbang`).
* Perilaku `_DEFAULT_CACHE` pada >1 worker (cache per-proses; `set_default` hanya membersihkan cache proses yang melayani) — hanya dari kode.
* Migrasi `_migrate_header_lines` terhadap data lama — hanya dari kode.
