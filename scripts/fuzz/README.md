# Penguji invarian + penjalan operasi acak (SIPRO / Estora)

Alat audit PERMANEN untuk menangkap kelas bug "angka yang sama berbeda antar tempat" (agregat tersimpan menyimpang dari
sumber, salinan basi, status tak selaras, jurnal tak berpasangan) secara sistematis, bukan lewat skenario tunggal.

* **Menulis hanya lewat API** (data uji berawalan `AUDIT-FZ`, proyek khusus per run). **DB hanya dibaca** (pymongo).
* Dua lapis: (1) **katalog invarian** (`fz/invariants/*.py`, fungsi → daftar pelanggaran) dan (2) **penjalan operasi acak**
  (`fz/ops.py`, `fz/conc.py`) yang menjalankan 49 jenis operasi dengan peran yang sesuai lalu mengecek invarian.
* Pelanggaran dihitung sebagai **BARU** bila belum ada pada pengecekan sebelumnya (atau nilai selisih agregatnya berubah) —
  jadi sisa data lama/demo di DB tidak memalsukan hasil. Keadaan awal dicatat sebagai `baseline`.

## Menjalankan
```
cd scripts/fuzz
python fuzz_invariants.py --list                                   # katalog invarian
python fuzz_invariants.py --api http://localhost:8052 --seed 11 --ops 300 --mode seq --shrink
python fuzz_invariants.py --api http://localhost:8052 --seed 21 --rounds 100 --mode conc
python fuzz_invariants.py --check-only                              # evaluasi invarian pada DB sekarang
python fuzz_invariants.py --replay runs/repro_<tag>_<INV>.json      # putar ulang reproduksi minimal
python fuzz_invariants.py --shrink-file runs/run_seq_seedN_*.json --inv M12   # kecilkan temuan lama
python statsum.py runs/run_seq_seedN_*.json 40                      # statistik operasi + alasan penolakan
python showrepro.py runs/repro_*.json                               # cetak urutan reproduksi
```
Opsi: `--db sipro_s2 --mongo mongodb://127.0.0.1:27017`, `--only M01,G01`, `--skip O13`, `--no-nudge`,
`--check-every N` (invarian non-GL), `--settle-every N` (invarian GL: menunggu dispatcher event kosong).
**Seed dicetak di baris pertama**; urutan operasi = fungsi `random.Random(seed*1000+run)`; urutan tersimpan lengkap (dengan argumen
simbolik `lead#2`, `unit#11`, …) di `runs/run_*.json` sehingga bisa diputar ulang walau DB berbeda.

## Mode
* **seq**: N operasi acak berurutan; invarian non-GL dicek tiap operasi, invarian GL tiap 5 operasi setelah antrean event kosong
  ("nudge" = `POST /leads` AUDIT-FZ memicu `dispatch_pending`). Pelanggaran baru → **shrink** (ddmin: buang langkah ditolak API,
  lalu blok langkah) → `runs/repro_<tag>_<INV>.json` (skrip yang bisa diulang).
* **conc**: tiap putaran = persiapan sekuensial + satu letusan 2–4 operasi **serentak** (thread + barrier) pada entitas yang sama
  (39 pasangan di `fz/conc.py`: kuitansi‖kuitansi, kuitansi‖void, titipan pakai‖kembali, batal‖bayar, konversi‖batal, hapus-paksa‖bayar,
  reservasi unit sama, GRN‖batal PO, bayar AP‖void, …). Antrean event dibiarkan diproses dispatcher alami.

## Menambah invarian
Di `fz/invariants/inv_*.py`:
```python
@invariant("M99", "AR", "judul singkat", settled=False, known="IN-xx", level="hard")   # settled=True bila butuh jurnal GL terbit
def m99(s):                       # s = Snap: s.rows('koleksi'), s.idx('koleksi'), s.grp('koleksi','field'), s.gl_cr('2-1400'), s.api(role, path)
    return [V("M99", kunci_subjek, "pesan", selisih_opsional)]
```
`known` = ID temuan audit lama bila pelanggaran = varian temuan itu. `level="soft"` = indikator (bukan bukti kerugian; tidak di-shrink).

## Menambah operasi
Di `fz/ops.py`: pasangan `gen(w, rng, focus)` → argumen JSON (hanya label simbolik + angka acak) atau `None`; `run(w, args)` →
`res(code, json)`; daftarkan dengan `reg(nama, bobot, gen, run)`. Label (`lead#1`, `deal#2`, …) membuat urutan bisa diputar ulang.

## Membedakan bug aplikasi vs artefak alat
* galat Python di invarian → `tool_errors` pada ringkasan (bukan pelanggaran);
* langkah ditolak API (4xx) bukan pelanggaran; HTTP 5xx dicatat di `http_500`;
* invarian bertingkat `soft` hanya indikator; semua temuan resmi diverifikasi ulang dengan skrip HTTP eksplisit (lihat laporan).

## Berkas pendukung
`verify_fz.py` (skenario HTTP eksplisit tiap temuan FZ-xx; `python verify_fz.py FZ-01 FZ-02 …`), `triage.py` (kelompokkan temuan dari `runs/run_*.json`), `statsum.py`,
`showrepro.py`, `inspect_replay.py <repro.json>` (putar ulang + cetak keadaan deal/unit/AR), `catalog_status.py`, `catalog_md.py`, `stats_final.py`, `build_report.py`.
Repro minimal temuan ada di `runs/repro_*.json` (format: `{seed, inv, msg, steps}`; putar ulang: `--replay`).
