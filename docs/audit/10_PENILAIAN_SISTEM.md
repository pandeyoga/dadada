# Penilaian SIPRO/Estora terhadap tujuan project

> Tanggal: 5 Nov 2026. Dokumen ini menggabungkan: audit ronde 1 dan 2 (`01`–`08`), analisis WhatsApp (`09`), dan dua penilaian praktik (`10_PENILAIAN_CRM.md`, `10_PENILAIAN_PROYEK.md`).
> **Dasar penilaian:** aplikasi dijalankan sungguhan dan dicoba lewat UI/API oleh banyak penguji; seluruh data adalah **data demo**. Tidak diuji: beban/kinerja, penetrasi keamanan, pengguna sungguhan, integrasi live (Meta, Google, bank, notaris), kamera perangkat nyata, portofolio lebih dari satu proyek.
> **Skala skor:** 1 = tidak ada · 2 = kerangka, belum jalan · 3 = ada dan jalan tetapi bolong · 4 = jalan dan teruji pada alur utama · 5 = teruji penuh, termasuk kasus tepi dan beban. Skor penilai CRM/proyek adalah hasil penilai masing-masing; skor area lain (keuangan, pengadaan, WhatsApp, platform) adalah **penilaian saya** dari bukti audit, ditandai **[Pendapat]**.

## 1. Vonis

**SIPRO adalah sistem yang dalam dan serius untuk praktik developer perumahan Indonesia — jauh melampaui "CRM + catatan" — dengan satu kelemahan struktural: banyak kemampuannya benar di jalur normal tetapi rapuh di tepi (paralel, validasi master, pembatalan), dan sisi barang/pengadaan serta peramalan untung-rugi belum terhubung ke keuangan.**

- **Kekuatan sejati:** rantai penjualan berpagar bukti (lead → penawaran → keep unit atomik → booking fee → pembeli → KPR), jadwal pembangunan per unit dengan gerbang mutu dan eskalasi keterlambatan, uang subkon dan serah terima yang mengikuti bukti, antrean offline yang benar-benar jalan, dan kejujuran data ("belum ada data" tidak ditampilkan sebagai 0).
- **Kelemahan sejati:** (1) integrasi keluar masih kerangka (lead iklan asli, CAPI untuk WhatsApp, payment gateway, e-sign), (2) tidak ada EAC/forecast kas sejati sehingga "proyek untung atau rugi" belum terjawab jujur, (3) persediaan/GRN/pemakaian tidak berjurnal dan angka anggaran saling bertentangan, (4) beberapa angka yang sama berbeda antar layar.
- **Setelah perbaikan dalam sesi ini:** risiko terbesar — uang tercatat/keluar dua kali, jurnal kembar, jalan pintas yang menjual unit tanpa bayar — **sudah ditutup dengan bukti tes** (lihat bagian 4). Sistem kini layak untuk **pilot terkendali (UAT) pada satu proyek**; **belum layak go-live penuh multi-proyek** tanpa syarat di bagian 5.

## 2. Skor terhadap empat hasil utama project

Hasil utama menurut `docs/analysis/05_PAIN_POINTS_AND_BUSINESS_NEEDS.md`: (1) tingkatkan konversi dan kecepatan jual, (2) cegah kebocoran, (3) jaga tenggat, (4) amankan arus kas dan kepercayaan.

| Hasil utama | Skor | Yang sudah terbukti | Yang menghalangi nilai lebih tinggi |
|---|---:|---|---|
| **1. Konversi & kecepatan jual** | **3,6** | Tugas SLA 5 menit otomatis, Work Hub "Hari Saya", penawaran dengan persetujuan diskon dan kupon, keep unit atomik (5 permintaan paralel → 1 menang), gerbang pipeline, KPR bertahap, portal pembeli | Lead Meta/Google asli belum bisa masuk; webhook publik tanpa tanda tangan; setelah SLA lewat hanya penerima tugas yang diberi tahu (tanpa eskalasi/push); lead langsung `won` saat konversi (corong menggelembung); tidak ada kualifikasi kelayakan bayar; ergonomi sales di HP lemah; atribusi iklan WhatsApp belum ada (`09`) |
| **2. Cegah kebocoran** | **3,0** | Anti-ganda semua jalur uang (kini teruji paralel), pemisahan tugas pembuat≠penyetuju≠pembayar, bukti foto anti-daur-ulang di lapangan, nilai SPK terkunci (wajib Change Order), retensi bergerbang, jejak audit | Persediaan tak berjurnal dan opname menimpa stok tanpa persetujuan; tidak ada MRP; stok bisa negatif lewat paralel; PO/SPK bisa dilewati; master komponen biaya tanpa validasi; beban developer tanpa batas |
| **3. Jaga tenggat** | **4,2** | Gerbang urutan/curing/hold point, eskalasi L1–L3 ke site/PM/owner dengan tugas pemulihan, deviasi hari dan analitik penyebab, laporan mingguan PDF, kalender kerja/libur, izin ber-masa-berlaku, BAST ditahan dengan alasan bernominal | Tidak ada critical path/Gantt/what-if; QC inspeksi belum menahan langkah berikutnya; progres proyek di beberapa layar basi |
| **4. Arus kas & kepercayaan** | **3,3** | AR dan AP benar pada alur normal (AR.paid = Σ item = Σ kuitansi; GL cocok subledger); model pasca-BAST dan denda diperbaiki; void resmi; pembayaran tidak ganda; portal pembeli; rekonsiliasi bank | Tidak ada forecast kas sejati (tanpa saldo awal/komitmen SPK-PO); PPN belum dibukukan benar; tidak ada payment gateway/VA (bukti transfer manual); persediaan di luar GL; angka lintas layar berbeda |

## 3. Skor per area

| Area | Skor | Sumber | Ringkas |
|---|---:|---|---|
| CRM, marketing, penjualan | **3,5** | Penilai CRM | Kelengkapan 4,0 · ketepatan alur Indonesia 4,5 · kemudahan lapangan 3,5 · keandalan data 3,0 · analitik 4,0 · integrasi eksternal **2,0** |
| Manajemen proyek, pembangunan, operasional | **3,6** | Penilai proyek | Kelengkapan 4,0 · ketepatan alur 4,0 · kemudahan lapangan 3,5 · keandalan data 3,0 · kontrol biaya/jadwal 3,5 (jadwal 4,5, biaya ±3) · keterhubungan ke keuangan 3,5 |
| Keuangan: AR, AP, buku besar | **3,5** | [Pendapat] dari `01`–`03`, `08` | Inti benar di jalur normal dan kini kebal duplikasi; kelemahan di validasi master, pajak (PPN/PPh), pembatalan, dimensi proyek pada jurnal, dan konfigurasi akun yang masih hardcode |
| Komponen biaya (all-in/BPHTB/titipan) | **3,0** | [Pendapat] dari `08` | Rumus BPHTB dan alur invoice→kuitansi→titipan→penyaluran benar dan cocok GL; master tanpa validasi, tab konfigurasi "Komponen Biaya" tak berefek, pembatalan mengabaikan titipan, BPHTB tercatat 3× |
| Pengadaan dan stok | **2,5** | [Pendapat] dari `07` | Jalur tagihan AP sehat; sisi barang tanpa jurnal, lima definisi komitmen yang bertentangan, PO/tagihan UI tak masuk anggaran, race stok, kontrol bisa dilewati |
| WhatsApp dan omnichannel | **3,0** | [Pendapat] dari `05`, `09`, penilai CRM | Inbox kini baik dan teruji; template/opt-out/jendela 24 jam sudah disiplin; **belum teruji live**, belum siap coexistence, belum ada atribusi CTWA |
| Platform: RBAC, konfigurasi, UX, keandalan | **3,5** | [Pendapat] | RBAC dengan peran kustom dan cakupan data, Pusat Konfigurasi ±130 aturan, penanda "data demo", gerbang tes ribuan baris; tetapi gerbang kepatuhan ukuran file sudah gagal di kondisi awal (5 berkas), banyak tes lama bergantung data seed lama, dan beberapa angka tidak satu sumber |

## 4. Apa yang berubah dalam sesi ini

**Temuan:** ronde 1 = 115 (13 kritis, 43 tinggi, 47 sedang, 12 rendah); ronde 2 = 58 lagi (pengadaan 25, finance 33; 1 kritis dan 27 tinggi), plus kesenjangan dari dua penilaian.

| | Sebelum | Sesudah (dengan bukti tes pada backend segar) |
|---|---|---|
| Kritis ronde 1 (13) | Pembayaran/penerimaan ganda, jurnal kembar, unit terjual tanpa bayar, pasca-BAST/denda salah akun, tutup tahun gagal | **13 dari 13 ditutup** |
| Tinggi ronde 1 (43) | — | **30 tertutup penuh, 7 sebagian, 6 terbuka**: IN-14, GL-04, GL-07, GL-11, GL-12, dan KT-03. Lima di antaranya butuh keputusan pemilik lebih dulu (IN-14, GL-04, GL-07, GL-12, KT-03). Rincian per ID di `06_STATUS_PERBAIKAN.md` |
| Kritis ronde 2 | — | PG-01 (persediaan tak berjurnal) **terbuka**, butuh keputusan metode valuasi |
| Tes regresi | Tidak ada untuk area ini | **204 tes lulus** di 12 berkas `backend/tests/p0/` (tiga suite diulang untuk membuktikan dapat diulang); tes baru gagal di kode lama dan lulus di kode baru |

Cacat fondasi yang ditutup: dispatcher event tidak mengklaim event (jurnal kembar), indeks `source_event` tidak unik, pola baca-lalu-tulis tanpa penjagaan di hampir semua jalur uang, dua jalur legal (PPJB/AJB lama menjual unit tanpa gerbang), Inbox WA yang memanjang tanpa batas dan menghilangkan pesan terbaru, master OTP portal aktif diam-diam.

## 5. Syarat sebelum dipakai untuk uang sungguhan

**Wajib (go-live penuh):**
1. **Keputusan pemilik** yang menentukan pembukuan: harga jual inklusif atau eksklusif **PPN**; titik pengakuan pendapatan (BAST/AJB/lunas); BPHTB titipan atau ditanggung; komisi dikapitalisasi atau dibeban; metode valuasi persediaan; model biaya kontrak (KT-03).
2. **Jurnal persediaan** (PG-01) atau keputusan resmi untuk tidak memakai stok sebagai angka akuntansi, plus peraturan persetujuan selisih opname.
3. **Validasi master komponen biaya** (FN-02) dan pembatalan kontrak yang menangani titipan/invoice biaya (FN-03).
4. **Keamanan integrasi:** tanda tangan HMAC dan *rate-limit* di semua webhook publik, master OTP dimatikan/diacak di produksi, rotasi kredensial, backup dan **uji pemulihan**, pemantauan.
5. **Rekonsiliasi data nyata:** jalankan `/finance/reconcile` dan kontrol serupa pada **salinan data produksi**; koreksi data historis dengan jurnal penyesuaian (perbaikan tidak menulis ulang jurnal lama).
6. **UAT 2–4 minggu** pada satu proyek dengan peran sungguhan (sales, PM, site, finance, owner) dan kamera/jaringan lapangan nyata.
7. **Satu sumber angka** untuk progres dan biaya proyek di semua layar (EP-02, PG-02) sebelum angka dipakai untuk keputusan.

**Sangat disarankan:** eskalasi SLA ke supervisor + web-push; handler Meta Lead Ads asli; payment gateway/Virtual Account; pilot WA coexistence (`09`); forecast kas dan EAC sederhana; persetujuan selisih opname dengan ambang nilai.

## 6. Pemetaan: masalah yang dijanjikan → terselesaikan?

| Masalah (dokumen 05) | Status | Catatan |
|---|---|---|
| Respons lead lambat (SL-1) | **Sebagian** | Tugas SLA dan penugasan ada; eskalasi, realokasi, dan push belum |
| Lead bocor (SL-2) | **Sebagian-kuat** | CRM terpusat, kepemilikan, recycle; dedup lintas kanal macet di antrean tanpa gabung |
| Double booking (SL-3) | **Terselesaikan** | Keep unit atomik terbukti (5 paralel → 1) |
| KPR ditolak di akhir (SL-4) | **Sebagian** | Checklist/pencairan bertahap ada; pra-skrining kelayakan (DSR/penghasilan) belum |
| Follow-up tidak konsisten (SL-5) | **Terselesaikan** | Work Hub, NBA, tugas terpandu |
| Sengketa komisi (SL-6) | **Sebagian-kuat** | Mesin komisi transparan; jalur pembayaran komisi kini aman, tetapi UI belum punya tombol bayar |
| Manajer tak lihat performa (SL-7) | **Sebagian-kuat** | Funnel/leaderboard ada; corong menggelembung karena `won` terlalu dini |
| Material hilang/dicuri | **Lemah** | Opname menimpa stok tanpa persetujuan, tidak ada nilai Rp, tidak berjurnal |
| Over-order | **Lemah** | Tidak ada MRP; PO tidak dipaksa ke RAB lewat UI |
| Markup/fraud biaya, 3-way match | **Sebagian** | Match ada, toleransi/override tak ditegakkan; kontrol PO bisa dilewati |
| Perizinan lambat | **Terselesaikan** | Tracker berscope, masa berlaku, peringatan |
| Deviasi jadwal tak terdeteksi | **Terselesaikan** | Deviasi hari, eskalasi, analitik, kalibrasi (belum critical path) |
| Progres subkon tak transparan | **Terselesaikan** | Termin dari langkah terverifikasi; SPK terkunci |
| Cacat mutu | **Sebagian** | Inspeksi/punch ada; belum menahan langkah berikutnya, punch tak dipin ke denah |
| Arus kas macet | **Sebagian** | AR/AP tertib; forecast kas dan VA belum |
| Pembayaran subkon tertib / anti-fraud | **Sebagian-kuat** | SoD dan anti-ganda kini ditegakkan di API; jejak audit lapangan belum di pusat |

## 7. Prioritas 90 hari (ringkas)

1. **Minggu 1–2:** keputusan pemilik (bagian 5.1); gabung dan verifikasi gelombang 2 akuntansi; kemenangan cepat CRM/proyek (HMAC webhook, eskalasi SLA, thumbnail di dialog verifikasi, panggil ulang rollup proyek).
2. **Minggu 3–6:** jurnal persediaan + persetujuan opname; validasi master komponen biaya + pembatalan titipan; satu sumber progres/biaya; handler Meta Lead Ads; simpan `ctwa_clid` dan CAPI Business Messaging.
3. **Minggu 6–12:** UAT satu proyek; pilot WA coexistence lewat BSP; Virtual Account; forecast kas/EAC sederhana; baru kemudian evaluasi Posting Profile (konfigurasi akun) sebagai proyek tersendiri.

## 8. Keterbatasan penilaian ini

- Penilaian CRM/proyek dan skor yang saya beri berbasis bukti dari instance demo; **belum ada pengguna sungguhan**. Skor "kemudahan pakai" adalah perkiraan, bukan hasil uji kegunaan dengan sales/mandor.
- Perbaikan diverifikasi dengan tes regresi buatan sendiri dan pada data uji; suite lama repo yang bergantung data seed lama sebagian tidak dapat dijalankan di lingkungan ini.
- Angka seperti "30 dari 43 tinggi tertutup" dihitung dari laporan agen dan tes regresi buatan sendiri, bukan dari audit independen ulang; temuan Sedang/Rendah dan seluruh temuan ronde 2 (`07`, `08`) sebagian besar belum dikerjakan.
- Tidak ada pengujian beban, keamanan penetrasi, atau integrasi live.
