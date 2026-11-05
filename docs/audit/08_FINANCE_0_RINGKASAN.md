# Audit Ronde 2 — Finance: AR, AP, dan KOMPONEN BIAYA — Ringkasan

Auditor: instance #8 (UI :3042, API :8042, DB `sipro_fin`), kode terbaru pasca-perbaikan gelombang 1. Rincian: `08_FINANCE_1_KOMPONEN_BIAYA.md` (FN-01…16), `08_FINANCE_2_AR.md` (FN-20…30), `08_FINANCE_3_AP.md` (FN-40…45) di folder yang sama. Skrip uji & screenshot: `(tidak disertakan di repo)`, `(tidak disertakan di repo)`.

## Jawaban singkat untuk pemilik
**"AR dan AP sudah benar?"** Inti-nya **ya, untuk alur normal**: AR.paid = Σ item = Σ kuitansi pada 17 deal; GL 2-1400/2-1450/2-1470/1-1300 cocok dengan subledger; pembayaran paralel menjadi satu efek; pemisahan tugas AP (buat ≠ setuju ≠ bayar) bekerja; jurnal denda/pasca-BAST/void benar. **Tetapi** ada sembilan cacat bernilai tinggi di tepi: skema pembayaran lewat jalur lama tidak divalidasi (menagih 70% harga atau DP 150%), aging/dasbor AR menghitung deal batal (Rp 845 jt), toleransi denda 7 hari tidak pernah berlaku, BAST mengakui pendapatan tanpa pelunasan, Faktur Pajak bisa terbit atas deal batal, PPN masukan SPT dihitung dari semua tagihan AP, tarif PPh bebas diketik, retensi tagihan manual tidak punya jalur cair, dan tagihan "beban developer" memintas pemisahan tugas.

**"Komponen biaya sudah dicek lebih detail?"** Sudah — dan hasilnya: sistem biaya all-in **berfungsi untuk alur normal tetapi belum aman dan belum tersambung penuh** (rincian di bawah).

## Komponen biaya: apa yang BENAR, SALAH, dan BELUM TERHUBUNG
**Benar**
- Rumus BPHTB `5% × (harga − NPOPTKP)` tepat (batas 80 jt, 850 jt); NOTARY/BANK/INSURANCE sesuai master; komponen kpr_only tersaring pada skema non-KPR; snapshot terkunci ke kontrak.
- Invoice biaya (INB) terbit otomatis saat booking/kontrak; kuitansi (KWB) → titipan 2-1470 = Σ kuitansi − Σ penyaluran (GL cocok subledger); biaya 0/negatif/lebih-bayar ditolak; paralel aman; komponen BOOKING konsisten; PDF invoice/kuitansi terbit; amandemen: pengaju ≠ pemutus.

**Salah**
- Master tanpa validasi: nominal negatif, persen 500%, akun GL sembarang, enum "xyz"; komponen baru otomatis ke semua skema; **komponen nonaktif tetap ditagih** pada reservasi baru (FN-02). Peran PM & sales manager bisa menambah komponen penagihan.
- Beban developer: nominal bebas (Rp 99 jt vs komponen 38,5 jt), disetujui otomatis & dibayar satu akun (FN-04); akun GL salah → tagihan AP tanpa jurnal berulang (FN-05); penyaluran titipan ke komponen fiktif / melebihi komponen (FN-06).
- Pembatalan kontrak mengabaikan titipan 2-1470 & invoice biaya; biaya masih bisa dibayar/disalurkan sesudah batal (FN-03); tak ada void kuitansi/penyaluran → amandemen buntu (FN-09).
- BPHTB dicatat ganda di komponen, `tax_records`, dan field legacy; catatan pajak yang sudah dibayar terhapus saat regenerasi AR lalu bisa dibayar lagi (FN-07).
- KT-03/04/05/22 belum tertutup: SPR kontrak non-all-in tak bisa ditandatangani, PPh penjual masuk total tagihan (Rp 928,75 jt dari 850 jt), potongan Rp 900 jt diterima, ganti skema ke KPR menghilangkan BANK_FEE/INSURANCE (FN-10/11).
- BANK_FEE dihitung dari harga, bukan plafon; NPOPTKP per-proyek tak bisa diisi (layar menjanjikan); tarif pajak ditulis −5%/500% diterima oleh peran finance (FN-12).

**Belum terhubung ke GL/Finance**
- Layar *Pusat Konfigurasi › "Komponen Biaya"* (katalog `price_components`) **tidak dibaca logika mana pun** padahal bertulis "menentukan jurnal" (FN-01).
- `gl_liability` komponen dan metode pembayaran/rekening tidak dipakai: semua titipan ke 2-1470, tunai tetap ke bank (FN-08). (`gl_expense`/`gl_ap` dipakai pada beban developer.)
- 2-1470 tidak ada di `/finance/reconcile`; kuitansi biaya (Rp 118,8 jt) tidak muncul di Laporan Penerimaan; penyaluran tak muncul di riwayat pembayaran keluar; invoice biaya tanpa jatuh tempo & tak masuk aging; tidak terlihat di portal pembeli (FN-14).
- PPN keluaran/masukan, PPh penjual, BPHTB tidak dijurnal dengan benar (6-1400 untuk semuanya); tidak ada komponen PBB/BBN/pendaftaran BPN di master.

## Daftar ID temuan
| ID | Severity | Judul |
|---|---|---|
| FN-01 | Tinggi | "Komponen Biaya" di Pusat Konfigurasi tidak berpengaruh |
| FN-02 | Tinggi | Master komponen/skema all-in tanpa validasi; nonaktif tetap ditagih |
| FN-03 | Tinggi | Pembatalan kontrak mengabaikan titipan biaya & invoice biaya |
| FN-04 | Tinggi | Beban developer: nominal bebas, auto-approve, SoD AP terlewati |
| FN-05 | Tinggi | Akun GL salah → tagihan AP tanpa jurnal, berulang |
| FN-06 | Tinggi | Penyaluran titipan: komponen fiktif/melebihi komponen, tanpa bukti |
| FN-07 | Tinggi | BPHTB tercatat 3× ; catatan pajak dibayar ganda setelah regenerasi AR |
| FN-10 | Tinggi | KT-03/04/22 belum tertutup (model biaya ganda, PPh penjual dalam tagihan) |
| FN-11 | Tinggi | KT-05 belum tertutup; komponen KPR hilang saat ganti skema |
| FN-08 | Sedang | gl_liability & metode bayar tak dipakai; tunai masuk bank |
| FN-09 | Sedang | Amandemen: buntu setelah ada kuitansi; efek samping tak ditangani |
| FN-12 | Sedang | NPOPTKP per-proyek tak bisa diisi; BANK_FEE dari harga; konfigurasi pajak tanpa validasi |
| FN-13 | Sedang | IDOR ledger biaya & amandemen terbaca sales lain |
| FN-14 | Sedang | Biaya tidak ada di laporan/arus kas/portal/reconcile |
| FN-15 | Sedang | Bukti bayar palsu/berulang diterima (IN-17 belum) |
| FN-16 | Rendah | Label mentah & dokumen biaya |
| FN-20 | Tinggi | Skema pembayaran jalur lama tanpa validasi (Σ≠100%, DP 150%) |
| FN-21 | Tinggi | Aging/dasbor AR menghitung deal batal (Rp 845 jt) |
| FN-22 | Tinggi | Toleransi denda 7 hari tak pernah berlaku |
| FN-23 | Tinggi | BAST tanpa gerbang pelunasan (GL-07 belum) |
| FN-24 | Tinggi | Faktur Pajak atas deal batal; PPN tak di AR/GL |
| FN-25 | Sedang | Ganti skema memutus tautan alokasi kuitansi (IN-14 belum) |
| FN-26 | Sedang | Konfigurasi jatuh tempo diabaikan (KT-10/11 belum) |
| FN-27 | Sedang | Booking fee KPR tanpa termin pembeli tertahan di titipan |
| FN-28 | Sedang | Tak ada kontrol rekonsiliasi AR/2-1470; aging tak ditie-out |
| FN-29 | Sedang | Kolom penting tabel AP/AR tertutup kolom Aksi sticky |
| FN-30 | Rendah | Tanpa tanggal bayar (IN-19), pembulatan, memo jurnal |
| FN-40 | Tinggi | PPN masukan/SPT dari semua tagihan AP (Rp 101,46 jt "lebih bayar") |
| FN-41 | Sedang | Tarif/dasar PPh bebas; tak ada setor PPh potongan |
| FN-42 | Sedang | Validasi tagihan manual lemah; faktur kembar; tanpa jatuh tempo tak menua |
| FN-43 | Sedang | Retensi manual 5% tanpa jalur cair (PK-16 belum) |
| FN-44 | Sedang | Pintu otomatis memintas persetujuan AP (rujuk FN-04/05) |
| FN-45 | Rendah | Tanpa tanggal bayar AP; fallback 4-1200; UX |

Total: Tinggi 15 (FN-01..07, 10, 11, 20..24, 40) · Sedang 15 · Rendah 3 = 33 butir (FN-44 adalah rujukan silang ke FN-04/05).

## Klaim ronde 1 yang diverifikasi ulang
Tertutup: IN-01/02, IN-05/GL-10 (void), IN-06/07 (GL-01/02), IN-12, IN-13, IN-15, KT-07, PK-01/02, PK-07 (alur biasa), PK-08, anti-ganda semua jalur uang yang diuji. **Belum tertutup:** GL-07, IN-14, IN-17, IN-19, KT-03/04/05/10/11/22, PK-15 (sebagian), PK-16, PK-17, GL-04, GL-19 (sebagian: `gl_liability` & katalog price-component dekoratif; `gl_expense/gl_ap` dipakai).

## Catatan lingkungan uji
Data uji mengotori instance #8 (komponen/skema `AUDIT_*` dinonaktifkan dan dilepas dari skema; 2 tagihan AP yatim Rp 1 jt membuat `/finance/reconcile` 2-1100 merah −Rp 2 jt; AR C-03 dan C-06 berskema rusak; deal A-03 dibatalkan). Seharusnya diabaikan oleh audit lain di instance yang sama.
