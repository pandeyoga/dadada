# Penilaian Sisi Manajemen Proyek, Pembangunan & Operasional — SIPRO / Estora

Penilai: konsultan manajemen proyek konstruksi/properti (perspektif developer perumahan Indonesia) · Tanggal: 5 Nov 2026
Objek: kode di `/home/user/dadada` (repo read-only), dijalankan di **Instance #9** (UI :3043, API :8043, DB `sipro_eval`).
Ini PENILAIAN kemampuan terhadap tujuan project, bukan audit bug keuangan/kontrak/WA (itu sudah ada di `docs/audit/`).
Label bukti: **TERBUKTI-UI** (dicoba lewat browser) · **TERBUKTI-API** (dicoba lewat HTTP/DB) · **DARI-KODE** (hanya dibaca, belum dijalankan).
Data uji buatan saya diawali `EVAL-` (daftar di Lampiran A). Screenshot: (berkas uji tidak disertakan di repo) (daftar di Lampiran B).

---

## 0. Ringkasan eksekutif

**Vonis: SIPRO paling kuat sebagai "mesin eksekusi lapangan berbukti" — jadwal per unit, gerbang urutan/curing/hold point, bukti foto anti-daur-ulang, verifikasi PM dengan pemisahan tugas, eskalasi keterlambatan, uang subkon yang mengikuti bukti, serah terima bergerbang, dan antrean offline yang benar-benar jalan. Ia paling lemah sebagai "alat peramal dan pengendali untung-rugi proyek": tidak ada EAC/EVM/critical path/forecast kas sejati, dan beberapa angka progres/biaya yang sama berbeda antar layar.**

Skor rata-rata ≈ **3,6 / 5** (rincian §C). Kelengkapan dan ketepatan alur tinggi (4/5); keandalan angka lintas layar dan kemudahan di lapangan paling perlu dikerjakan (3/5 dan 3,5/5).

Yang terbukti jalan end-to-end saat dicoba: mulai → ajukan (foto min. 3 + checklist mutu kritis) → notifikasi/tugas ke PM → verifikasi → progres unit naik 10% → 16% → rollup; eskalasi telat L1–L3 ke site/PM/owner; foto identik ditolak; PM tak bisa memverifikasi miliknya sendiri; nilai kontrak SPK terkunci (wajib Change Order); BAST ditahan 409 dengan alasan per butir; antrean offline (IndexedDB) → kirim otomatis saat sinyal kembali → penolakan server tampil tanpa menghilangkan foto.

Yang paling berbahaya bagi tujuan "PM tahu proyek untung/rugi & terlambat berapa":
1. Terlambat berapa — **terjawab baik** (deviasi hari, umur telat, analitik penyebab, laporan mingguan PDF).
2. Untung/rugi — **belum terjawab dengan jujur**: margin proyeksi tampil hijau 78–97% walau RAB baru ada untuk 1 dari 6 tipe unit dan tanpa biaya lahan; tidak ada EAC (biaya akhir), tidak ada SPI/CPI; proyeksi kas hanya AR−AP terjadwal tanpa saldo awal dan tanpa komitmen SPK/PO.

---

## A. Tujuan project (yardstick), ringkas

Sumber dibaca: `docs/analysis/03, 05, 06, 08, 09`, `memory/PRD.md`, `plan.md` (judul-judul fase), `docs/v2/28, 29, 32, 33, 42, 44, 45, 46`.

**Empat hasil bisnis (north-star), `05_PAIN_POINTS…` §0:** (1) tingkatkan konversi, (2) **cegah kebocoran** (material dicuri/over-order, komisi/retensi salah bayar, fraud), (3) **jaga deadline** (izin, konstruksi, serah terima — "70–80% proyek konstruksi ID terlambat"), (4) **amankan arus kas & kepercayaan** ("developer menengah bertahan 1–3 bulan tanpa arus kas baru"). Penilaian ini fokus pada (2), (3), (4).

**Masalah yang hendak dipecahkan (kutipan):**
- "Material dicuri / hilang … Pengawasan mandor lemah, gudang tak terkontrol, tanpa opname rutin" → solusi: requisition → GRN → issue → stok, opname terjadwal, 3-way match, alert bila permintaan > BoQ (`05` §2.1).
- "Deviasi jadwal tak terdeteksi dini … Kurva-S + deteksi deviasi + tindakan korektif" · "Progres subcon tak transparan … opname ter-verifikasi + foto + QC gate sebelum bayar termin" · "Cacat mutu … QC/inspeksi (pass/fail→qc_hold) + punch list + foto ber-lokasi" (`05` §2.2).
- "Daily log / site diary … mobile, bisa offline", "Punch list … foto dipin ke lokasi/gambar + voice note", "Audit trail semua aktivitas lapangan" (`05` §2.3).
- "Arus kas macet = pemicu utama semua sengketa"; "Subcon telat dibayar → proyek berhenti … cash-flow projection dari jadwal AR/AP"; "Sengketa retensi … jadwal pelepasan" (`05` §3).
- "Progres pembangunan tak transparan … Customer Portal: progres (kurva-S/%/foto)", "Cacat bangunan lambat ditangani … SLA perbaikan (target ≤7 hari)" (`05` §4).

**Persona:** P4 Project Manager/Site Engineer ("Andi, lapangan") — sukses = "progres nyata terverifikasi, material terkontrol (opname cocok), jadwal on-track (kurva-S), izin tepat waktu", kebutuhan "mobile + offline"; P5 Owner ("satu Control Tower: penjualan, kas, AR/AP, progres proyek, revenue diakui vs contract-liability"); P3 Finance; P6 Pembeli (portal). Prinsip desain (`06` §4): mobile-first peran lapangan, kontekstual-memandu, anti-kebocoran by design, deadline-aware.

**Metrik sukses yang dijanjikan (`06` §3) dan kenyataannya:**

| Metrik janji | Kenyataan di aplikasi | Bukti |
|---|---|---|
| Deviasi kurva-S, alarm bila negatif | Ada per unit (rencana vs terverifikasi, deviasi % dan hari) + eskalasi otomatis; kurva-S proyek (fase) masih bisa diketik manual | TERBUKTI-UI/API |
| Selisih stock opname → ~0; wastage % | Selisih dihitung, tetapi langsung menimpa stok tanpa persetujuan/alert; wastage % tidak ada | TERBUKTI-API |
| Defect open vs closed sebelum BAST; rework rate | Gerbang BAST menahan bila punch terbuka; `rework_count` per langkah; laporan klaim garansi | TERBUKTI-API |
| On-time milestone / permit | Izin ber-scope + masa berlaku + pindai peringatan → notifikasi + tugas | TERBUKTI-API |
| Cash-flow projection (runway) | Ada, tetapi bukan runway sungguhan (lihat EP-01) | TERBUKTI-API + DARI-KODE |
| Waktu respons komplain/defect closure time | Laporan klaim memuat rata-rata hari tutup (jujur "belum ada data", bukan 0) | TERBUKTI-API |
| Pembeli melihat progres + foto | Endpoint portal progres/foto/garansi ada | DARI-KODE (OTP tidak dicoba) |

---

## B. Tabel per kemampuan

Status: **Lengkap** = berfungsi end-to-end dan memadai untuk praktik; **Sebagian** = ada dan jalan tetapi ada lubang berarti; **Hanya-kerangka** = ada struktur/field tetapi tidak menegakkan/menghitung; **Tidak ada**.

### B.1 Inti pembangunan

| # | Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|---|
| 1 | Master proyek → cluster → blok → unit | Lengkap | TERBUKTI-UI/API | Pohon `GET /masterplan/projects/{id}/tree`, generator unit massal (maks 200), impor CSV, blokir unit beralasan, Unit 360 (7 tab). Rollup proyek basi — lihat EP-02. |
| 1b | Site plan & Studio peta | Sebagian | TERBUKTI-UI (lihat) / DARI-KODE (edit) | Peta interaktif 18 kavling, 4 mode warna termasuk "Progres Pembangunan", konsistensi 18/18 terpetakan, bagikan tautan showroom. Edit Studio (gambar/PDF latar, undo) tidak saya coba. |
| 2 | Tipe unit, harga, add-on | Lengkap | TERBUKTI-API | 6 tipe, 11 add-on, matriks komponen harga per skema (cash keras/bertahap/KPR) dengan akun GL. Luas tanah/bangunan tipe kosong di seed (bukan cacat kode). |
| 3 | Jadwal pembangunan per unit (template, kalender kerja, hari libur) | Lengkap | TERBUKTI-UI/API | Template per tipe (RUMAH-9W: 20 langkah/60 hari kerja, RUKO-14W), `predecessors`, `wait_days` (curing), hold point, bobot, foto min. Kalender: Sabtu setengah hari, Minggu libur, 18 libur nasional bawaan (berlabel "perkiraan, WAJIB disesuaikan"). Penjadwalan massal bergelombang (`per_unit`/`per_block`, jeda hari) — preview jalan. |
| 3b | Gantt / kalender | Sebagian | TERBUKTI-UI | Ada kalender bulan/minggu/hari lintas unit dengan deteksi bentrok beban (ambang: maks 3 tenggat/pelaksana/hari, 2 pekerjaan kritis/hari) dan "geser jadwal". **Tidak ada Gantt batang** dan tidak ada critical path (EP-09). |
| 4 | Progres & verifikasi bukti foto | Lengkap | TERBUKTI-API/UI | Foto min. per langkah (3 foto: ditolak jika 1), checklist kritis wajib lulus, **foto identik (SHA-256) ditolak** walau berbeda unit, watermark unit+tanggal, EXIF dibuang, GPS terstruktur. Progres naik hanya dari langkah terverifikasi (A-02: 10% → 16%). |
| 5 | Alur mulai → ajukan → verifikasi (site ↔ PM) | Lengkap (alur) / Sebagian (efisiensi) | TERBUKTI-API/UI | Site: 403 untuk verifikasi; PM: tidak boleh verifikasi pengajuannya sendiri ("Pemisahan tugas…"); override butuh alasan berkode. Bug awal PRD (tombol tak muncul bagi Site Engineer) **sudah tertutup** — `can: {submit:true, verify:false}` dan tombol "Mulai kerjakan"/"Ambil foto & ajukan" tampil. Kelemahan: dialog verifikasi "0 bukti" (EP-05), ≥12 interaksi per langkah (EP-06), verifikasi paralel tidak atomik (EP-07). |
| 6 | Keterlambatan, eskalasi, kalibrasi jadwal | Lengkap | TERBUKTI-API/UI | `POST /build/tick` (juga terjadwal 10 mnt): 7 langkah telat → level 1/2/3 (≥1/3/7 hari), notifikasi ke site+PM, level ≥2 ke owner & super admin, tugas TK-13 "Kejar keterlambatan". Analitik per langkah (rata-rata/maks hari telat, `dominant_cause`, "tanpa penjelasan: 8"), rekomendasi kalibrasi template, laporan mingguan PDF. Kalibrasi *apply/rollback* tidak saya jalankan. Ambang L1–L3 hardcode (EP-11). |
| 7 | Inspeksi/QC & punch list | Sebagian | TERBUKTI-API/UI | 3 template QC; inspeksi gagal → punch otomatis + tugas ("Punch QC: Instalasi pipa tidak bocor") + PDF punch list. **Punch tak dipin ke denah/gambar; lokasi teks bebas**; tidak ada voice note. `qc_hold` hanya lewat jalur lama `/construction/qc` (fase proyek), bukan dari inspeksi baru (EP-08). |
| 8 | Buku harian lapangan | Lengkap | TERBUKTI-UI/API | Cuaca (manual), jumlah pekerja, material, alat, kendala, foto; ada *cross-check* buku harian vs absensi ("28 pekerja vs 1 hadir, selisih −27 — dua-duanya dibiarkan"). Cuaca tidak otomatis (BMKG). |
| 9 | Izin & perizinan | Lengkap | TERBUKTI-API/UI | Scope proyek/cluster/blok/unit dengan pewarisan, `deadline`/`expiry_at`, `reminder_days`, tab "Dokumen & Izin" di Unit 360, pindai peringatan → notifikasi+tugas (2 peringatan). Kebijakan "izin memblokir" default hanya peringatan. |

### B.2 Biaya, anggaran, pengadaan

| # | Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|---|
| 10 | RAB/BoQ per tipe unit & fasum/umum | Lengkap | TERBUKTI-API/UI | RAB menempel pada tipe (satu sumber), fasum/fasos (10 jenis), umum, alokasi biaya bersama (rata/luas tanah/harga jual), versi + salin + impor Excel, SPK dari RAB. Dicoba: RAB TIPE-45-90 Rp 505 jt/unit → ×6 unit = Rp 3,03 M, HPP per unit Rp 530,4 jt, margin per unit 37,6%. |
| 11 | Anggaran, realisasi, overbudget | Sebagian | TERBUKTI-API/UI | "Kendali Biaya": anggaran vs dikontrakkan (SPK) vs terverifikasi vs ditagih per kategori dan per kode (pemetaan ke langkah jadwal), peringatan "finishing dikontrakkan Rp 160 jt > RAB Rp 54 jt". Budget operasional dengan `cost_ref`, `match_rule`, revisi berjejak. Lubang: tiga definisi "realisasi" berbeda antar layar (EP-02), margin proyeksi menyesatkan (EP-03), tak ada EAC. |
| 12 | Target proyek (unit & pendapatan) | Lengkap | TERBUKTI-UI/API | 5 metode (linear sisa, S-curve, manual, velocity forecast, revenue-first), periode lampau terkunci, carry-over, realisasi dari deal (tidak diketik ulang). "Target pendapatan Rp 17.859.999.996" (artefak pembulatan 12 bulan vs total Rp 17,86 M). |
| 13 | Pengadaan material, stok, opname, vendor (tingkat kemampuan) | Sebagian | TERBUKTI-API | Permintaan → setuju → keluarkan/`to-po`, stok per proyek + buku besar mutasi, batas min (alert `below_min`), anggaran qty per material dari RAB + flag `over_budget` + tugas urgent ke PM saat pemakaian melewati RAB, transfer, valuasi rata-rata bergerak (jujur `missing_price`), master vendor + daftar harga + banding + cek harga 10%. Lubang kebocoran: EP-04. PO/3-way/AP detail diaudit auditor lain. |
| 14 | Subkontraktor: SPK, termin, retensi, uang muka | Lengkap (kemampuan) | TERBUKTI-API (sebagian) / DARI-KODE | SPK borongan per item pekerjaan; opname termin dihitung dari item terverifikasi ("claimable_value"); nilai kontrak/retensi terkunci setelah berjalan ("Ajukan Change Order…" — PK-11 audit **sudah tertutup**); uang muka, potongan/denda, retensi dengan gerbang masa pemeliharaan + punch + klaim garansi, evaluasi subkon berbukti. Alur finansial rinci = auditor lain. |
| 15 | Tenaga kerja harian & upah | Lengkap | TERBUKTI-API | Pekerja master (tarif harian per peran), absensi (hadir penuh/setengah/lembur 1,5×), rekap upah mingguan (dicoba: 6 orang, 12,5 hari, Rp 2.087.500), alur ajukan→setuju→bayar, `client_ref` idempoten. Absensi manual — tanpa geofence/biometrik. |

### B.3 Serah terima, layanan, aset, pajak

| # | Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|---|
| 16 | BAST, garansi, klaim pasca-huni | Lengkap | TERBUKTI-API | `GET /handover/check`: 6 pemeriksaan (pembangunan selesai, punch terbuka, inspeksi serah terima, pelunasan, dokumen wajib, BAST sudah terbit); percobaan BAST A-02 → **409** dengan 3 alasan berisi nominal ("Sisa kewajiban Rp 850.000.000"). Terobosan hanya `handover:override`. Garansi per bagian (struktur 120 bln … finishing 3 bln); klaim → punch + tugas → bukti → verifikasi; PDF BAST valid 1 halaman (meter, kunci, masa garansi). |
| 17 | Komplain / CS | Sebagian | TERBUKTI-UI (hanya daftar) | Halaman ada, terhubung ke klaim garansi (`warranty/for-complaint`). PM tidak punya akses (403, wajar: sisi penjualan). Alur penuh tidak dicoba. |
| 18 | Aset tetap & pinjaman | Sebagian | TERBUKTI-UI (hanya tampilan) | Aset tetap (susut, lepas), pembiayaan korporat (angsuran, pengingat). Hanya diperiksa keberadaan layar/endpoint. |
| 19 | Pajak PPh/PPN & kepatuhan | Sebagian | TERBUKTI-UI + DARI-KODE | SPT Masa PPN (keluaran Rp 552,3 jt − masukan Rp 90,6 jt), PPh final 4(2), BPHTB, faktur pajak + pengganti/pembatalan, ekspor **XML Coretax + CSV**, bukti potong (e-Bupot, ekspor). Disclaimer di layar jujur: "bukan e-Faktur/e-Bupot resmi DJP". Bukan integrasi langsung. |

### B.4 Work Hub, notifikasi, dokumen, administrasi

| # | Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|---|
| 20 | Work Hub: tugas, papan divisi, SLA, jobdesk | Lengkap | TERBUKTI-UI/API | Tab Tugas/Kanban/Umur Tahap & SLA/Papan Divisi/Rapor Mingguan/Katalog Jobdesk (14 jobdesk TK-xx), tugas lahir otomatis dari event (verifikasi, telat, izin, material overbudget, punch QC), SLA ter-hitung, rapor per anggota (tepat waktu 29% divisi teknis minggu ini). |
| 21 | Notifikasi | Lengkap | TERBUKTI-API/UI | Pusat notifikasi, pengelompokan, preferensi, ringkasan WA, push realtime (WebSocket → fallback SSE) — DARI-KODE untuk realtime. |
| 22 | Dokumen & template naskah (SPR/PPJB/BAST), editor | Lengkap | TERBUKTI-UI/API (+ DARI-KODE editor) | 7 template (SPR 3 skema, PPJB, AJB, SPKT), layout/skrip naskah, riwayat dokumen, tanda tangan, PDF berkop; BAST lewat mesin serah terima. Editor naskah berformat tidak saya coba. |
| 23 | Pusat Konfigurasi | Lengkap | TERBUKTI-UI | 130 aturan, 15 tab (aturan bisnis, komponen biaya, skema bayar, tahapan pembangunan, penomoran, integrasi…), tiap perubahan sensitif beralasan + riwayat. |
| 24 | RBAC & peran kustom | Lengkap | TERBUKTI-API/UI | Matriks per peran × modul × aksi, peran kustom (`POST /admin/roles`, inherit/copy), akses bagian RAB (unit/fasum/umum/ringkasan), cakupan proyek (anggota). Default terlalu terbuka untuk Site Engineer (EP-12). |
| 25 | Manajemen data | Lengkap | TERBUKTI-API | Template Excel 16 sheet, ekspor master `.xlsx` (37 KB), `backup.json` (1,5 MB), snapshot, restore + inspeksi, impor penuh bersesi + pratinjau, hapus massal dengan pratinjau. Restore/purge tidak dijalankan. |
| 26 | Multi-organisasi | Lengkap | TERBUKTI-UI | 2 tenant, beralih konteks, onboard tenant, data terisolasi. |
| 27 | Offline / PWA | Sebagian (kuat pada intinya) | TERBUKTI-UI | Service worker (shell), manifest standalone, antrean IndexedDB (8 jenis), foto lokal, kirim otomatis, penolakan server tampil + foto tersimpan, snapshot Papan Mandor offline. **Hanya Papan Mandor** yang punya data offline; halaman lain (RAB, Unit 360, tugas) kosong tanpa sinyal; verifikasi PM butuh online. |
| 28 | Laporan owner (paket bulanan, dashboard) | Sebagian | TERBUKTI-API/UI | Control Tower di Beranda owner (booking, AR, tugas telat, menunggu verifikasi, progres rumah), paket laporan bulanan (neraca, L/R, arus kas, **laba per proyek**, arus kas per proyek, rasio, status periode). Beranda owner tidak memuat kas/margin/kesehatan proyek (hanya "Pembangunan rumah"). |
| 29 | Analitik BI proyek | Sebagian | TERBUKTI-UI | 5 dasbor; "Proyek & Biaya" 16 metrik (PRJ-01…07) dengan status kelengkapan jujur ("TIDAK ditulis 0"). Angka bisa berbeda dari layar operasional (EP-02). Tanpa EVM/EAC. |
| 30 | Portal pembeli (bonus pilar kepercayaan) | Lengkap (DARI-KODE) | DARI-KODE | 28 endpoint: progres per unit sendiri (bukan fase proyek), foto sebelum/sesudah temuan, pembayaran, dokumen, klaim garansi + pengakuan pembeli. Login OTP tidak dicoba. |

---

## C. Skor 1–5 per dimensi

| Dimensi | Skor | Alasan |
|---|---|---|
| **Kelengkapan fitur terhadap tujuan** | **4,0** | Hampir semua pilar punya modul nyata (30 kemampuan di §B; 867 jalur API, ±97 rb baris backend). Pilar "jaga deadline" 4,5; "arus kas & kepercayaan" 3,5 (portal + retensi ada, forecast kas lemah); "cegah kebocoran" 3,0 (subkon/foto kuat, material lemah). Kurang: EAC/EVM, critical path, MRP, RFQ, manajemen risiko, portofolio (§E). |
| **Ketepatan alur untuk praktik perumahan Indonesia** | **4,0** | RAB per tipe + fasum + umum → HPP per unit; SPK borongan per item dengan opname termin, retensi masa pemeliharaan, uang muka & denda; curing/waktu tunggu & hold point (sloof, plester); izin KRK/IMB-PBG/SLF/AMDAL/ANDALALIN ber-scope; Sabtu setengah hari + libur nasional; DP 20% sebagai gerbang mulai bangun; BAST + masa garansi per bagian; PPN/PPh final/BPHTB + Coretax. Pengurang: libur "perkiraan", satu template untuk tiga ukuran rumah (Tipe 54/105 dan 70/120 memakai RUMAH-9W), keterlambatan dihitung hari kalender. |
| **Kemudahan pakai di lapangan** | **3,5** | Positif: responsif di 390 px, tombol kamera belakang, watermark otomatis, antrean offline terbukti, banner "Mode offline" jelas, penolakan server tidak menghilangkan bukti. Negatif: ≈12–16 interaksi per langkah (buka, uraian, 3× foto, 3× pilih hasil checklist, simpan), tanpa "lulus semua"/draf/pengajuan massal; deep-link Beranda → halaman lama `/construction` (dua UI paralel); dialog verifikasi tanpa thumbnail; offline hanya Papan Mandor; header tumpang-tindih pada gulir deep-link di HP (`m-site-submit1.png`). |
| **Keandalan data** | **3,0** | Positif: "honest-null" konsisten ("belum ada data" ≠ 0), gerbang & SoD ditegakkan server, idempotensi `client_ref`, foto duplikat ditolak, fixture ronde-1 (mis. PK-11) tertutup. Negatif: rollup proyek basi (0%·0/6 unit vs 10,2%·5/18), progres resmi 38% diketik manual vs 10,2% terverifikasi, tiga definisi biaya "realisasi", lateness BI tertinggal sampai tick, verifikasi paralel menggandakan jejak, `audit_logs` pusat tidak memuat operasi lapangan, GL tak berdimensi proyek (audit GL-11). Audit lain mencatat 115 temuan (13 Kritis) pada jalur uang; gelombang-1 memperbaiki sebagian dan tidak saya verifikasi ulang. |
| **Kedalaman kontrol biaya/jadwal** | **3,5** | Jadwal **4,5** (deviasi hari, umur telat, eskalasi, kalibrasi, kalender bentrok, laporan mingguan). Biaya **2,5–3** (komitmen vs terverifikasi vs ditagih per kategori/unit/kode: baik; tapi margin proyeksi menyesatkan, tak ada EAC/cost-to-complete, tak ada SPI/CPI, laba proyek GL baru muncul setelah BAST, kas proyek tanpa forecast). Jawaban atas "untung/rugi & terlambat berapa": terlambat — ya; untung/rugi — hanya perkiraan kasar yang tampak lebih pasti daripada datanya. |
| **Keterhubungan ke keuangan (SSOT)** | **3,5** | Terhubung nyata: langkah terverifikasi → klaim subkon (earned value) → AP → retensi (gerbang punch/garansi/masa pemeliharaan); status DP dari AR menjadi pemeriksaan "mulai bangun"; pelunasan AR menjadi gerbang BAST; BAST → pengakuan pendapatan; upah → rekap → jurnal; budget dengan `cost_ref`/`match_rule`. Terputus: persediaan material tak berjurnal dan opname tanpa nilai (valuasi `missing_price`), WIP/HPP GL tingkat organisasi (layar HPP-vs-Realisasi sendiri menulis "GL tidak berdimensi proyek"), `boq/summary` lama memakai definisi lain, forecast kas tak membaca komitmen. |

Rata-rata tertimbang sederhana: **3,6**.

---

## D. Temuan penilaian (urut dampak bisnis) — dengan bukti

### EP-01 [Tinggi] Tidak ada peramalan: EAC, EVM (SPI/CPI), forecast kas proyek sungguhan
- Label: TERBUKTI-API (cashflow) + DARI-KODE (pencarian kata kunci).
- Lokasi: `backend/finance_reports.py:223-276` (`cashflow_projection`); `GET /api/finance/cashflow`; pencarian `critical path|earned value|EAC|forecast.*cost` di backend/frontend = kosong.
- Yang terjadi: outflow hanya `ap_invoices` belum lunas + pelepasan retensi; inflow hanya sisa `ar_invoices`. Tidak ada saldo awal kas (kolom "kumulatif" mulai dari 0 sehingga "ending Rp 1,48 M" adalah net arus, bukan saldo), tidak membaca sisa komitmen SPK/PO yang belum ditagih, upah, atau budget operasional. Hasilnya: Des 2026 outflow Rp 266 jt, Jan–Apr 2027 outflow Rp 0 padahal RAB belum terealisasi mayoritas.
- Dampak: tujuan inti #4 ("developer bertahan 1–3 bulan … kas terprediksi") terancam: proyeksi tampak sehat padahal belanja mendatang tidak ikut. Tidak ada angka "biaya akhir proyek" untuk PM/owner.
- Arah: kurva belanja dari RAB × jadwal terverifikasi (bahan sudah ada: `planned_progress`, `verified_value`, `committed`), saldo awal dari Kas & Bank, komitmen SPK sebagai outflow terjadwal.

### EP-02 [Tinggi] Angka progres/biaya yang sama berbeda antar layar
- Label: TERBUKTI-UI + TERBUKTI-API.
- (a) **Master Proyek** (`pm-projects_ad036fac…png`): "Progres konstruksi (fase berbobot) 38%" dan "Rata-rata progres unit 0% · 0/6 unit terjadwal". **Pembangunan** (`site-build.png`): 5/18 unit terjadwal, 10,2% terverifikasi, rencana 19,6%. Akar: `engine.py:213-275 recompute_project_progress` hanya dipanggil dari `construction_router.py`, `phase_templates.py`, `seed.py`; tidak dari `build_engine` saat verifikasi (docstring `build_engine.py:5` menyebutnya tetapi tidak memanggilnya). `projects.units_total=6` basi (unit sebenarnya 18). Fase demo tak punya `work_category`, jadi 38% adalah angka ketikan manual (Persiapan 100, Pondasi 80, Struktur 40) yang tak tersinkron dengan bukti.
- (b) **BI "Proyek & Biaya"**: PRJ-02 "Langkah terlambat 0" sementara papan menampilkan 7 telat; PRJ-02 membaca `late_days` yang baru diisi oleh tick 10 menit (setelah `POST /build/tick`, 7 terisi). PRJ-05 "Item overbudget 0" sementara Kendali Biaya menandai kategori finishing −Rp 106 jt (`over_commit: true`).
- (c) **Tiga "realisasi"**: `GET /boq/summary` → `actual` Rp 461 jt (seluruh `ap_invoices.claimed`, `boq_router.py:59-80`), `committed` hanya PO sehingga `over_budget:false`; `GET /budget/summary` → konstruksi realized Rp 33 jt; Kendali Biaya → terverifikasi Rp 36 jt.
- Dampak: owner melihat dua angka progres proyek yang saling bertentangan; kepercayaan ke dasbor turun.
- Arah: satu fungsi progres resmi dari jadwal unit; panggil rollup setelah verifikasi/tahan/jadwal; tandai tab "Item RAB lama".

### EP-03 [Tinggi] Margin proyeksi tampak pasti padahal RAB belum lengkap
- Label: TERBUKTI-UI/API.
- Sebelum saya memasukkan RAB: `GET /rab/projects/{id}/summary` → margin Rp 17,39 M (**97,4%**); `GET /budget/margin` → margin proyeksi 95%. Setelah RAB 1 tipe (6 unit): 80,4% / 78,1% (`pmrab-Ringkasan_HPP.png` kartu hijau "Margin RAB (80,4%)"). 12 dari 18 unit tetap dihitung harga jualnya tanpa biaya; budget tak memuat lahan; hanya badge kecil "12 unit bertipe tanpa RAB tipe". Margin realisasi memang `null` (jujur karena belum ada pendapatan diakui) tetapi proyeksinya tidak diperlakukan sama.
- Dampak: keputusan harga/diskon/penjualan berdasarkan margin 80–97% yang fiktif.
- Arah: sembunyikan atau beri status "tidak bermakna" bila cakupan RAB < 100% unit atau kategori lahan/prasarana kosong; tampilkan rentang.

### EP-04 [Tinggi] Pengendalian kebocoran material lemah di titik paling rawan
- Label: TERBUKTI-API + DARI-KODE.
- Reproduksi: `POST /api/materials/opname` (site) Semen: buku 700, fisik 650 → `variance −50`, stok langsung 650. Tidak ada persetujuan, notifikasi/tugas ke PM/finance, `audit_logs`, nilai rupiah (`valuation` = `missing_price`), maupun jurnal. Hanya satu baris activity feed (`materials_router.py:205-232`).
- Tambahan: konsumsi tercatat per proyek/fase, bukan per unit (`RequisitionCreate` hanya `project_id/phase_id/task_id`); alert "melebihi RAB" baru menyala saat barang dikeluarkan (`_check_material_budget` dipanggil saat `out`/`issue`), bukan saat permintaan; tidak ada MRP otomatis dari RAB × jadwal (budget qty per material diisi manual); tidak ada QR/label.
- Dampak: tujuan #2 "selisih opname → 0" tercapai dengan cara menyembunyikan selisih, bukan menekannya.
- Arah: selisih > ambang (Pusat Konfigurasi) → tugas persetujuan PM + nilai Rp + tanda tangan 2 orang; tampilkan "susut kumulatif" per proyek/material.

### EP-05 [Sedang] Verifikator memutuskan "buta" dan ada dua UI paralel
- Label: TERBUKTI-UI.
- `pm-verify-dialog.png`: dialog "Verifikasi pekerjaan" menulis "diajukan site@sipro.co.id dengan **0 bukti**" padahal kartu yang sama menunjukkan "bukti 3/3 foto" dan data berisi 3 evidence. Tidak ada thumbnail foto, hasil checklist, atau lokasi GPS di dialog. Kartu yang sama muncul dua kali di tab Lapangan (antrean + daftar).
- Deep-link tugas/Beranda "Buka & ajukan hasil" mendarat di `/construction?tab=board` (halaman lama 8 tab: Papan Mandor, Monitoring Unit, Antrean Kerja, Infrastruktur Kawasan, QC & Inspeksi, Laporan & Analitik, Template Jadwal, Garansi & Klaim), bukan hub `/build`. Referensi: `TaskCard.js:99`, `TaskDetailSheet.js:207`, `RetentionsPanel.js:183`. Spesifikasi 29 menyatakan "6 menu → 1 hub".
- Dampak: kontrol mutu bergantung pada kebiasaan PM membuka detail; hitungan "0 bukti" membingungkan.

### EP-06 [Sedang] Beban interaksi di lapangan
- Label: TERBUKTI-UI (skrip Playwright `ui_off3.js`, 390×… px).
- Pengajuan satu langkah (3 foto + 3 butir checklist): buka dialog → ketik uraian → ambil/pilih foto ×N → pilih "Lulus" ×3 (dropdown: 2 ketukan masing-masing) → simpan ≈ 12–16 interaksi (+ konfirmasi kamera OS). Tidak ada "Semua sesuai", tidak ada draf tersimpan, tidak ada pengajuan massal lintas unit. Seorang site engineer dengan 13 rumah × 20 langkah menghadapi ±260 pengajuan.
- Arah: tombol "Semua butir lulus" + pengecualian, foto dikelompokkan per langkah, pre-isi uraian dari instruksi kerja.

### EP-07 [Sedang] Verifikasi paralel tidak atomik; jejak audit terpusat tidak memuat operasi lapangan
- Label: TERBUKTI-API.
- Tiga `POST /build/items/{id}/verify` paralel → ketiganya **200**; progres tetap benar (2,0, dihitung ulang) tetapi `history` memuat `verify` 3× dan activity feed "DIVERIFIKASI" 3×. Pola sama dengan akar masalah A di `docs/audit/00_RINGKASAN_EKSEKUTIF.md` (baca-status-lalu-tulis tanpa syarat atomik).
- `audit_logs` (layar Admin → Jejak Audit) tidak memuat start/submit/verify, opname, simpan RAB; jejaknya hanya `history` per langkah dan activity feed. Kebutuhan "audit trail semua aktivitas lapangan" (`05` §2.3) terpenuhi sebagian.

### EP-08 [Sedang] Gerbang mutu tidak menahan kerja berikutnya
- Label: TERBUKTI-API (punch otomatis) + DARI-KODE (`qc_hold`).
- Inspeksi QC/2026/0002 A-02 dengan satu butir gagal → status `failed`, punch `open` + tugas "Punch QC". `qc_hold` hanya diset oleh `routers/construction_router.py:129-131` (QC fase lama); inspeksi baru tidak menahan langkah berikutnya. Penahan nyata yang ada: hold point di template, retensi subkon (punch terbuka), dan BAST. Janji `05` §2.2 "QC gate sebelum bayar termin" hanya terpenuhi tidak langsung.

### EP-09 [Sedang] Tidak ada critical path, Gantt, atau penyeimbangan sumber daya
- Label: DARI-KODE + TERBUKTI-UI.
- Ada: `predecessors` + `wait_days` per langkah (finish-to-start dengan jeda) dan deteksi bentrok beban dengan ambang tetap. Tidak ada: perhitungan jalur kritis, float/slack, Gantt batang lintas unit, simulasi "bagaimana jika" (geser fase → dampak serah terima), resource leveling. Pencarian "gantt|critical path|leveling" = kosong. Untuk 13+ rumah paralel dengan satu kru, ini yang menentukan tanggal serah terima.

### EP-10 [Sedang] Verifikasi lokasi dan visual terbatas
- Label: DARI-KODE.
- `build_policy.py`: GPS hanya direkam + batas akurasi (200 m); tidak dibandingkan dengan koordinat proyek (proyek tidak punya koordinat/poligon) — bukan geofence. Absensi manual per pekerja. Punch: lokasi teks, tanpa pin pada denah (`AddPunchDialog.js`: field `location` teks). Tidak ada integrasi drone/foto 360/BIM.

### EP-11 [Rendah] Parameter operasional yang masih hardcode atau perkiraan
- Label: DARI-KODE + TERBUKTI-API.
- Ambang eskalasi `LEVELS = [(7,3),(3,2),(1,1)]` di `build_monitor.py:26` (spesifikasi 33 §2: "tidak ada angka bisnis hard-code"). `late_days` hari kalender. Kalender libur nasional "perkiraan" (harus disesuaikan admin). Penjadwalan massal memakai RUMAH-9W untuk Tipe 70/120 dan 54/105 (`/build/bulk/schedules/preview`). Kandidat jadwal massal memuat unit yang sudah `handed_over` (B-01).

### EP-12 [Rendah] Default RBAC terlalu terbuka bagi peran lapangan
- Label: TERBUKTI-API.
- `site_engineer`: `boq/budget/subcon view_all` → `GET /boq/summary`, `/budget/summary`, `/subcon/spk` (nilai kontrak) berhasil; PM punya `delete` pada units/projects/boq/budget. Blueprint `03` §1.3 ("progressive disclosure: biaya/HPP disembunyikan dari peran yang tak butuh") hanya terpenuhi bila admin mengonfigurasi akses bagian RAB/peran. Konfigurasi tersedia (matriks + akses bagian RAB), hanya default-nya.

---

## E. Kekuatan, kesenjangan, kemenangan cepat

### 5 kekuatan terbesar
1. **Jadwal per unit yang berbukti dan berurutan** — template, `predecessors`+curing+hold point, foto minimum + checklist kritis + SHA-256 anti-daur-ulang + watermark, verifikasi PM dengan SoD; terbukti E2E (progres 10→16%).
2. **Manajemen keterlambatan yang benar-benar menutup loop** — tick 10 menit, eskalasi L1–L3 ke site/PM/owner, tugas pemulihan, analitik penyebab + rekomendasi kalibrasi + laporan mingguan PDF + kalender bentrok/libur.
3. **Uang subkon dan serah terima mengikuti bukti** — termin dari langkah terverifikasi, nilai SPK terkunci (wajib Change Order), retensi bergerbang punch/garansi, BAST ditahan 409 dengan alasan bernominal, garansi per bagian, klaim → punch → verifikasi.
4. **Offline/PWA yang nyata** — antrean IndexedDB dengan foto, kirim otomatis, penolakan server tampil tanpa kehilangan bukti, snapshot papan offline, `client_ref` idempoten.
5. **Kejujuran data + konfigurabilitas** — "belum ada data ≠ 0", Pusat Konfigurasi 130 aturan, RBAC peran kustom + akses bagian RAB, RAB per tipe → HPP per unit, multi-organisasi.

### 8 kesenjangan terbesar (urut dampak bisnis)
1. **Tak ada peramalan** (EAC/EVM/forecast kas): proyeksi kas tanpa saldo awal & komitmen (EP-01).
2. **Angka progres/biaya tidak satu kebenaran** antar Master Proyek, Pembangunan, BI, BoQ (EP-02).
3. **Margin proyeksi 78–97% menyesatkan** saat RAB/lahan belum lengkap (EP-03).
4. **Kebocoran material**: opname menimpa stok tanpa persetujuan/nilai, tanpa MRP, konsumsi tak per unit (EP-04).
5. **Tak ada critical path/Gantt/resource leveling/what-if** (EP-09).
6. **Verifikator buta + dua UI paralel + beban 12–16 interaksi per langkah** (EP-05, EP-06).
7. **Integritas jejak & gerbang mutu**: verifikasi paralel menggandakan jejak, `audit_logs` tanpa operasi lapangan, QC inspeksi tidak menahan (EP-07, EP-08).
8. **Verifikasi lokasi/visual terbatas**: tanpa geofence, denah-pin, 360/drone/BIM (EP-10).

### Kemenangan cepat (≤ 2 minggu, bahan datanya sudah ada)
1. Panggil `recompute_project_progress` setelah verifikasi/tahan/jadwal; perbaiki `units_total`; satu angka "progres resmi" di Master Proyek (EP-02a). *(½–1 hari)*
2. Dialog verifikasi: tampilkan thumbnail bukti + hasil checklist + hitungan bukti benar; arahkan deep-link ke `/build` (EP-05). *(2–3 hari)*
3. Tombol "Semua butir lulus" + draf tersimpan di dialog pengajuan (EP-06). *(2 hari)*
4. Opname: ambang selisih di Pusat Konfigurasi → tugas persetujuan PM + nilai Rp (rata-rata bergerak sudah ada) + `audit_logs` (EP-04). *(3–4 hari)*
5. Margin proyeksi: status "tidak bermakna" bila ada unit tanpa RAB atau kategori lahan kosong; jangan tampilkan persentase hijau (EP-03). *(1–2 hari)*
6. SPI sederhana (`progress / planned_progress`, sudah ada per unit) dan CPI proksi (terverifikasi ÷ realisasi) sebagai kartu di BI "Proyek & Biaya"; EAC = realisasi + sisa RAB ÷ CPI (EP-01). *(4–5 hari)*
7. Forecast kas: tambah saldo awal dari Kas & Bank + sisa komitmen SPK/PO sebagai outflow (EP-01). *(3–4 hari)*
8. Syarat atomik pada verifikasi/ajukan (filter `status` pada `update_one`) + tulis ke `audit_logs` (EP-07). *(1–2 hari)*
9. Pindahkan `LEVELS` eskalasi dan ambang bentrok ke Pusat Konfigurasi; setujui daftar libur nasional (EP-11). *(1 hari)*

---

## F. Kemampuan manajemen proyek lanjutan yang tidak ada / terbatas, dan nilainya

| Kemampuan | Status | Yang ada sekarang | Nilai bila ditambahkan |
|---|---|---|---|
| Critical path & dependensi tugas | Sebagian (dependensi) / Tidak ada (CPM) | `predecessors`+`wait_days` per langkah unit | Menentukan tanggal serah terima nyata dan langkah yang harus dikebut; dasar denda keterlambatan ke pembeli |
| Resource leveling | Tidak ada | Peringatan bentrok beban (ambang tetap) | Menghindari satu mandor/kru dijadwalkan di 5 rumah serentak; menurunkan telat berantai |
| Earned Value (EVM: SPI/CPI) | Tidak ada | Bahan lengkap: `progress`, `planned_progress`, `verified_value`, `committed` | Indikator dini proyek rugi/telat dalam satu angka; bahasa yang dipahami owner dan bank |
| Prakiraan biaya selesai (EAC) | Tidak ada | `margin_projected` kasar | Jawaban langsung "proyek ini akhirnya untung/rugi berapa" |
| Forecast arus kas proyek | Sebagian | AR−AP terjadwal (`/finance/cashflow`), arus kas per proyek aktual (GL) | Mencegah proyek mangkrak karena kas (tujuan #4) |
| Dasbor portofolio multi-proyek | Sebagian | Filter proyek di BI; laba per proyek di paket owner; data uji hanya 1 proyek (tidak bisa diuji) | Owner dengan >1 proyek melihat progres/margin/kas berdampingan |
| Change-order penuh | Sebagian | CO subkon (nilai/lingkup, disetujui Keuangan); revisi anggaran berjejak | Belum ada CO dari pembeli/owner → revisi RAB + jadwal + harga otomatis; penting saat pembeli minta tambah spek |
| Manajemen risiko | Tidak ada | — | Register risiko (cuaca, perizinan, pasokan) terkait jadwal; relevan karena izin & curing sudah dilacak |
| E-procurement / RFQ banding vendor | Sebagian | Master vendor, daftar harga, banding harga, cek harga 10% | Penawaran tertulis multi-vendor memperkuat anti-markup |
| MRP (kebutuhan material dari RAB × jadwal) | Tidak ada | Budget qty manual per material | Mencegah over-order dan material mepet (tujuan #2) |
| Geofence / absensi lokasi | Hanya-kerangka | GPS direkam saat ajukan, absensi manual | Menutup klaim kehadiran/lokasi fiktif |
| Drone / foto 360 / BIM | Tidak ada | Foto biasa + watermark | Nilai tinggi untuk proyek besar; bukan prioritas rumah tapak |
| Punch list berpin denah + suara | Tidak ada | Lokasi teks bebas | Mempercepat perbaikan dan memperjelas bukti sengketa |
| Integrasi akuntansi/pajak | Sebagian | GL internal; ekspor XML Coretax + CSV; ekspor e-Bupot | Cukup untuk tahap ini; integrasi langsung API bukan keharusan |
| Cuaca otomatis, QR material | Tidak ada | Cuaca manual di buku harian | Rendah |

---

## G. Terverifikasi OK (agar tidak berat sebelah)

- Alur lapangan lengkap: `POST /build/items/{id}/start` → submit ditolak (1 foto dari 3; checklist kritis kosong) → submit sukses → notifikasi + tugas ke PM → verify → progres A-02 10% → 16%, deviasi −12 → −6 [TERBUKTI-API].
- Hak akses: Site 403 pada verify; PM 403 memverifikasi pengajuannya sendiri; override butuh `reason_code` dari daftar [TERBUKTI-API].
- Foto identik dengan bukti lain ditolak ("IDENTIK dengan bukti pekerjaan … unit A-02") — terjadi saat antrean offline mengirim ulang [TERBUKTI-UI].
- Antrean offline end-to-end: offline → "Simpan & kirim nanti" → toast "Tersimpan di perangkat" → online → upload 2 foto + submit → status `submitted`, 2 evidence; saat ditolak server: banner "1 pengajuan ditolak server … bukti fotonya masih tersimpan" [TERBUKTI-UI].
- Reload offline: aplikasi terbuka dengan banner "Mode offline" dan cuplikan Papan Mandor (`m-site-offline-reload.png`) [TERBUKTI-UI].
- Eskalasi: `POST /build/tick` → 7 langkah level 1–3, notifikasi "PERINGATAN KRITIS" ke site, PM, super admin, owner [TERBUKTI-API].
- Gerbang BAST: 409 + 3 alasan bernominal; PDF BAST/laporan mingguan/punch list valid [TERBUKTI-API].
- Nilai kontrak SPK tidak bisa dinaikkan PM ("Ajukan Change Order …") — menutup PK-11 [TERBUKTI-API].
- RAB tipe → HPP per unit, `units_without_template` dihitung jujur, `missing[]` pada margin [TERBUKTI-API].
- Rekap upah dari absensi (lembur 1,5×) + pemeriksaan silang buku harian vs absensi [TERBUKTI-API].
- Izin ber-scope + pemindai peringatan [TERBUKTI-API].
- Multi-organisasi, backup.json 1,5 MB, ekspor xlsx, template impor [TERBUKTI-UI/API].
- Tanpa error konsol/HTTP 4xx-5xx tak terduga pada 40+ halaman yang dibuka kecuali 403 sah (PM → Komplain).

## H. Tidak bisa diverifikasi

- Kamera nyata di perangkat (Playwright memakai `input[type=file]`; atribut `capture="environment"` hanya dibaca di kode).
- Portal pembeli (login OTP), WebSocket/SSE realtime, WA live (simulasi — di luar cakupan).
- Dashboard portofolio dengan ≥2 proyek (data hanya 1 proyek di instance; pembuatan proyek kedua tidak dilakukan agar tidak mengganggu penilai CRM).
- Penerapan/rollback kalibrasi jadwal, komit penjadwalan massal/geser massal, editor template jadwal, edit Studio Site Plan, alur komplain/CS penuh, alur klaim garansi penuh, aset tetap/pinjaman/pajak (hanya keberadaan/tampilan), alur retensi/termin subkon penuh (area auditor lain).
- Performa/beban dan penggunaan sungguhan di lokasi bersinyal buruk.
- Semua temuan audit 115 butir di `docs/audit/` tidak diverifikasi ulang kecuali PK-11 dan SoD verifikasi.

## I. Pertanyaan terbuka untuk pemilik

1. Apakah "progres proyek resmi" yang ingin diwakili owner = rata-rata unit terverifikasi, atau fase kawasan berbobot (infrastruktur jalan/drainase ikut)? Dua-duanya perlu, tetapi harus diberi nama berbeda.
2. Apakah QC inspeksi harus **menahan** langkah/termin berikutnya (qc_hold) atau cukup menjadi punch?
3. Siapa yang berwenang menyetujui selisih opname, dan berapa ambangnya (persen/Rp)?
4. Apakah biaya lahan/prasarana akan dimasukkan ke anggaran proyek sehingga margin bermakna?

---

## Lampiran A — Data uji buatan penilai (awalan EVAL-, tersimpan di sipro_eval)

- Langkah A-02 "Pembesian & bekisting sloof + kolom praktis": start → submit (3 foto, 1 butir checklist non-kritis gagal) → verified oleh PM.
- Langkah A-05 "Pekerjaan persiapan": start → submit lewat antrean offline (2 foto `uniq*.jpg`) → `submitted` (belum diverifikasi).
- Langkah A-04 "Pekerjaan tanah & pondasi": start + submit oleh PM sendiri (uji SoD; verifikasi ditolak) → `submitted`.
- RAB tipe `TIPE-45-90` diisi 3 baris `EVAL-` (Rp 505 jt/unit) → mengubah angka margin proyek di instance bersama.
- Inspeksi `QC/2026/0002` (A-02, QC-MEP, 1 gagal) + punch otomatis + tugas.
- Opname Semen Portland: buku 700 → fisik 650.
- Absensi Dedi 2026-11-05 (lembur 2 jam) dan rekap upah draf `UPH/2026/0001`.
- `POST /build/tick` (2×), `POST /permits/alerts/scan`, unduhan `backup.json`/`export.xlsx` (tanpa restore/purge).
- Berkas foto & skrip di (berkas uji tidak disertakan di repo) (`h.sh` pembantu API, `shoot.js`, `tabs.js`, `ui_off3.js`, `ui_verify.js`, `offline.js`, `openapi.json`).

## Lampiran B — Screenshot kunci (`.../shots/eval-proyek/`)

- Site engineer: `site-home.png`, `site-build.png`, `site-field.png`, `site-materials.png`, `m-site-home.png`, `m-site-build.png`, `m-site-submit1.png`, `m-site-offline-reload.png`, `site-offline-dialog.png`, `site-after-reconnect.png`.
- Project manager: `pm-home.png`, `pm-projects_ad036fac_8b7b_4c17_a7ef_30582e60ba50.png` (EP-02), `pmbuild-Kalender.png`, `pmbuild-Lapangan.png`, `pmbuild-Mutu_Inspeksi.png`, `pmbuild-Analitik_Kalibrasi.png`, `pm-verify-dialog.png` (EP-05), `pmboq-Kendali_Biaya.png`, `pmboq-Target_Budget.png`, `pmrab-Ringkasan_HPP.png` (EP-03), `pmrab-HPP_vs_Realisasi_per_Unit.png`, `pmunit-Pembangunan.png`, `pm-subcon.png`.
- Owner: `owner-home.png`, `owner-bi.png`, `ownerbi-Proyek_Biaya.png` (EP-02b).
- Finance: `fin-home.png`; Super admin: `sa-tasks.png`, `sa-site_plan.png`, `sa-config.png`, `sa-admin_data_management.png`, `sa-admin_organizations.png`, `sa-tax.png`, `sa-documents.png`.
