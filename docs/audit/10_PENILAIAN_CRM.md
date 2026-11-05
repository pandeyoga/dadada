# Penilaian CRM / Marketing / Penjualan — SIPRO / Estora

Penilai: konsultan CRM senior (perumahan Indonesia) · Tanggal: 5 Nov 2026 · Repo HEAD `d08065b` (sudah memuat perbaikan KT-01/02/07/08/09/12/13, IN-*, PK-*, WA-02/03/07/08 dari audit ronde 1).
Lingkungan: instance #9 (UI :3043, API :8043, DB `sipro_eval`), mode WhatsApp/Meta/Google/OTP = SIMULASI. Ini PENILAIAN, bukan audit bug; bug hanya disebut bila relevan terhadap tujuan CRM.
Label bukti: **TERBUKTI-UI** (browser), **TERBUKTI-API** (HTTP/DB), **DARI-KODE** (baca kode saja). Screenshot: `img/eval-crm/` (±45 berkas, awalan `sales-`, `mgr-`, `owner-`, `mkt-`, `sa-`, `mob-`, `portal-`). Skrip uji: `(tidak disertakan di repo)`.

---

## (a) Tujuan project (yardstick)

**Masalah yang hendak dipecahkan** (Dok 05 §0–1): empat outcome — (1) *tingkatkan konversi lead→booking→akad & kecepatan jual*, (2) cegah kebocoran, (3) jaga deadline, (4) amankan arus kas & kepercayaan pembeli. Untuk sisi CRM, pain bernomor SL-1..SL-7:
- SL-1 "Respons lead lambat" → *"Auto-assign instan + SLA countdown + Task 'Hubungi sekarang' + eskalasi bila lewat SLA"*.
- SL-2 "Lead bocor (hilang di WA/Excel)" → CRM terpusat, kepemilikan jelas, cadence follow-up, recycle otomatis.
- SL-3 double booking → *"Unit atomic hold + reservasi ber-expiry"*; SL-4 KPR ditolak di akhir → *"pra-skrining KPR (SLIK/DP/simulasi) sejak nurturing"*; SL-5 follow-up tak konsisten → Work Hub "Hari Saya" + Next-Best-Action; SL-6 sengketa komisi → komisi transparan; SL-7 manajer buta performa → funnel, SLA tim, leaderboard.

**Untuk siapa** (Dok 06): P1 Sales lapangan "Rina" (*"mobile-friendly"*, tahu "hari ini harus hubungi siapa"), P2 Marketing Admin / Sales Manager "Budi" (distribusi lead, SLA, approval diskon, coaching), P5 Owner (Control Tower), P6 Pembeli "Ibu Dewi" (portal), plus Finance/Collection.

**Metrik sukses yang dijanjikan:** *speed-to-lead ≤5 menit* ("telat >5 mnt → ~21x lebih kecil qualified"), lead ads masuk CRM *<30 detik*, % lead terkontak ≤30 menit, CPL/CPQL & cost-per-closing per kampanye/creative, double-booking = 0, lead tanpa tindak lanjut → 0, funnel/konversi per sumber, absorption rate, response time komplain ≤7 hari, referral 25%+.

**Spesifikasi lanjutan** (docs/v2/24, 30, 31, 47, 48): tahap `acquisition→nurturing→appointment→booking→spr→won` dengan gerbang bukti dan SLA per tahap (0,25 jam untuk acquisition) + *"pelanggaran SLA ⇒ tugas eskalasi ke supervisor"*; webhook Meta/Google/TikTok/web/WA/mitra *"REAL"* dengan *verifikasi signature*; biaya iklan manual/CSV dulu (keputusan D1); CAPI Lead/SubmitApplication/InitiateCheckout/Purchase; 63 metrik BI; pengingat WA terhitung dari data; portal pembeli.

Catatan kejujuran Dok 09: dokumen sendiri menyatakan "mode simulasi jujur" sebagai strategi karena kredensial belum ada — jadi integrasi live memang diakui belum selesai; penilaian di bawah mengukur apakah *kontrak/arsitektur siap live* dan apakah *janji non-integrasi* terpenuhi.

---

## Ringkasan eksekutif

Sebagai **sistem kerja penjualan internal** (Work Hub → pipeline → penawaran → keep unit → booking → KPR → pembeli → portal), aplikasi ini **terbukti berjalan end-to-end** dan sangat dalam untuk praktik developer perumahan Indonesia; saya menjalankan satu lead sampai menjadi pembeli lewat API dan seluruh gerbangnya menolak jalan pintas dengan pesan yang benar. Tiga janji utama proyek **belum bisa diklaim**: (1) *lead ads masuk <30 detik dari Meta/Google asli* — handler untuk format payload asli tidak ada; (2) *eskalasi SLA & respons ≤5 menit* — hanya penugasan + penanda, tanpa eskalasi dan tanpa push notification; (3) *CAPI feedback loop* — hanya Meta yang punya transport, belum teruji. Ditambah dua kebocoran lead nyata (dedup lintas kanal & re-inquiry dibuang) dan satu celah kepemilikan lead lewat impor.

**Skor rata-rata ≈ 3,5 / 5.** Kekuatan terbesar: kedalaman domain & kejujuran data. Kelemahan terbesar: kesiapan integrasi eksternal (2/5) dan ergonomi lapangan/mobile (3,5).

---

## (b) Tabel kemampuan

Status: **Lengkap** · **Sebagian** · **Hanya-kerangka** · **Tidak ada**. "Teruji" = dicoba berjalan; semua WA/Ads/OTP berarti simulasi.

### 1. Penangkapan lead omnichannel

| Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|
| Form web / landing page (`POST /api/webhooks/web`) | **Sebagian** | TERBUKTI-API | Lead + atribusi UTM/gclid + skor + task "Hubungi ≤5 menit" tercipta seketika (`engine.py:144-211`). CORS terbuka untuk landing page. **Tanpa autentikasi/signature/rate-limit**: 15 POST beruntun semua 200, header signature palsu tetap 200 (`routers/webhooks_router.py:94-176`). |
| Meta Lead Ads | **Hanya-kerangka** | TERBUKTI-API | `/webhooks/meta-lead` hanya menerima payload sederhana `{name,phone,...}`. Payload Meta asli (`entry[].changes[].value.leadgen_id`) → HTTP 202 "phone Field required" dan masuk antrean gagal. Tidak ada `GET` verifikasi `hub.challenge` (405), tidak ada pemanggilan Graph `/{leadgen_id}`; `grep leadgen` di backend = kosong. Hanya bisa dipakai via perantara (Zapier/Make/Pabbly) yang mengubah format. |
| Google Ads lead form / TikTok Instant Form | **Hanya-kerangka** | TERBUKTI-API + DARI-KODE | Sama: payload sederhana, `google_key` tidak diverifikasi (spec §3 menandai ini harus ada). |
| WhatsApp masuk (click-to-chat / pesan nomor baru) | **Sebagian** | TERBUKTI-API | Nomor dikenal → menempel ke lead; nomor baru → antrean "Kontak WA" (`wa.auto_capture_lead` default **mati**, `settings_store.py:104`). Dengan toggle dinyalakan: pesan simulasi → lead + auto-assign + task 5 menit (terbukti, lalu saya kembalikan ke mati). Mode live tidak teruji; tanda tangan Meta (HMAC) diperiksa bila `app_secret` ada. |
| Form showroom publik (`/showroom/{token}`) | **Lengkap** | TERBUKTI-API | Token per proyek, lead `showroom_public` + minat kavling, dedup, rate-limit (12 POST → 4×200 lalu 8×429). Tanpa QR/UTM per titik (atribusi kosong). |
| Impor Excel/CSV/kontak WA | **Sebagian** | TERBUKTI-API | Pratinjau dry-run (insert/update/error per baris), duplikat dalam berkas terdeteksi. **Cacat:** sales yang mengimpor nomor milik sales lain → lead di-*update* dan **dipindah ke pengimpor + nama ditimpa** (`data_mgmt_import.py:240-243`, `routers/leads_router.py:253-270`); format `0812-2222-2222` ditolak di impor padahal diterima di webhook. |
| Partner/agen (`/webhooks/partner/{id}` + token) | **Lengkap** | TERBUKTI-API | Token per mitra (401 bila salah), mitra nonaktif ditolak, nomor sama → klaim dicatat + model atribusi (first-touch) + sengketa, tanpa lead kembar. |
| Offline / walk-in manual | **Lengkap** (online) / **Tidak ada** (tanpa sinyal) | TERBUKTI-API + DARI-KODE | Form manual dengan dedup 409 yang menyebut pemilik. Antrean offline IndexedDB hanya untuk jenis konstruksi (`offline_intake.py` KINDS: absensi, diary, punch, garansi) — bukan lead/kontak. |
| Antrean lead gagal (dead-letter) | **Lengkap** | TERBUKTI-API/UI | Tidak ada lead yang diam-diam hilang: payload cacat → antrean + tugas/notifikasi supervisor; tab "Gagal Masuk" di Automasi & Channel. Lihat kelemahan dedup di bawah. |

### 2. Dedup, penugasan, SLA, pipeline, skor

| Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|
| Deduplikasi lead | **Sebagian** | TERBUKTI-API | Baik: nomor dinormalisasi E.164, manual create 409, partner/WA menempel ke lead lama. **Rusak:** nomor yang sama masuk lewat *kanal iklan berbeda* (web → Meta) → `DuplicateKeyError uq_leads_phone` → masuk antrean gagal "transient", retry otomatis 3× gagal terus, tak ada tombol "gabungkan" (`capture_failures.py:31`). **Re-inquiry dibuang:** form kedua dari nomor yang sama dengan pesan "mau survey besok" → `duplicate:true`, tanpa pesan, aktivitas, tugas, maupun update `last_touch` (cek DB). Tidak ada merge lead; dedup hanya nomor telepon (bukan email/NIK). |
| Penugasan otomatis | **Sebagian** | TERBUKTI-API + DARI-KODE | `auto_assign_lead` = sales aktif dengan lead terbuka paling sedikit (`engine.py:122-135`): adil secara beban, tapi bukan round-robin, tanpa jam kerja/kehadiran/keahlian proyek, tanpa terima/tolak. Penugasan ulang massal ada (UI "Tugaskan ulang…"). Tugas lama tidak ikut pindah saat reassign (terlihat saat impor memindahkan lead; KT-16 audit). |
| SLA respons & eskalasi | **Sebagian** | TERBUKTI-API | Task "Hubungi lead (≤5 menit)" `urgent` dengan `sla_due_at`=+5 menit dibuat otomatis; badge "SLA lewat/Terlambat 49 menit" di Hari Saya; jam tahap per lead (SLA 0,25 jam acquisition, 2× SLA). **Setelah SLA lewat hanya penerima tugas yang diberi tahu** ("SLA task terlampaui" ke sales2); manager, owner, marketing: 0 notifikasi (`engine_sweepers.py:45-61`). Tidak ada eskalasi ke supervisor, realokasi, atau recycle otomatis, padahal label konfigurasinya sendiri menyebut "memicu eskalasi ke supervisor" (`settings_store.py:79`). |
| Tahapan pipeline & gerbang | **Lengkap** | TERBUKTI-API | acquisition→booking langsung ditolak; nurturing butuh kontak pertama; appointment butuh agenda; booking butuh survei + deal aktif; `won` tak bisa manual; lost/recycle wajib alasan; override hanya supervisor + alasan (`lead_lifecycle.py:35-44`). Selisih dari spec v2: tidak ada tahap `spr`; lead jadi `won` begitu dikonversi (booking fee saja; KT-13); tidak ada Kanban/drag-drop (hanya tabel + chip tahap; DARI-KODE `components/leads/`). |
| Lead scoring | **Lengkap** (aturan) | TERBUKTI-UI/API | Skor berbobot per sumber/tahap/aktivitas/balasan WA dengan rincian poin, band hot/warm, bobot diatur di Pusat Konfigurasi. Tidak prediktif (lihat bagian e). Skor tersimpan vs hitung ulang bisa beda (85 vs 100 pada lead demo) sampai tombol "Nilai ulang". |
| Tugas & pengingat (Work Hub) | **Lengkap** | TERBUKTI-UI | "Hari Saya": KPI strip, tugas Terlambat/Hari ini/Akan datang, rekomendasi langkah berikutnya, drawer tugas dengan bukti, papan Kanban/Umur Tahap & SLA/Papan Divisi/Rapor Mingguan/Katalog Jobdesk. Fitur khas: *"Chat lewat WA pribadi (di luar sistem)?"* — sales mengunggah tangkapan layar, tugas selesai, kontak pertama tercatat. Sangat cocok dengan praktik sales Indonesia yang memakai WA pribadi. |
| Agenda & survei lokasi | **Lengkap** | TERBUKTI-UI/API | Kalender + tabel, status, PIC; survei dengan checklist bertahap yang bisa dikonfigurasi, foto, hasil; membuat agenda menaikkan lead ke appointment (terbukti). |

### 3. Penawaran, reservasi, KPR, dokumen

| Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|
| Penawaran/quotation, diskon, kupon, persetujuan | **Lengkap** | TERBUKTI-API | Simulasi harga (+PPN/BPHTB/PPh, termin, KPR anuitas), skema diskon/promo/kupon bertarget (harga/DP/biaya), kupon kuota 50 & per-pelanggan, diskon di atas batas (2%) → status "Menunggu persetujuan" dan **tidak bisa dikirim**; sales tak bisa menyetujui sendiri (403); manajer menyetujui dengan alasan; PDF + kirim WA (simulasi); konversi ke reservasi (`PNW/2026/0001`). |
| Reservasi / keep unit | **Lengkap** | TERBUKTI-API | 5 reservasi paralel ke 1 unit → 1×200 + 4×409; reservasi kedua lead yang sama ditolak; masa tahan 7 hari + sweeper kedaluwarsa (DARI-KODE `engine_sweepers.py:13`; sisa tautan/lead tidak turun tahap = KT-25). |
| Site plan interaktif / showroom | **Lengkap** | TERBUKTI-UI | Peta SVG, 4 mode warna (siklus penjualan/progres/harga/lama tak terjual), klik kavling → kartu harga, luas, harga/m², progres, tombol "Detail Lengkap" & "Reservasi"; status ikut berubah setelah uji reservasi. Studio untuk menggambar tersedia (DARI-KODE). |
| Booking fee → booking → konversi pembeli | **Lengkap** | TERBUKTI-API | Booking diblokir sampai booking fee lunas (dicatat Finance dengan bukti; sales 403); konversi menghasilkan customer + kontrak; (konversi paralel sudah diperbaiki per git log, tidak saya ulang). |
| KPR: simulasi, pengajuan, SP3K, SLIK, pencairan | **Lengkap** (proses) / **Sebagian** (kecerdasan) | TERBUKTI-API + DARI-KODE | Tahap berurutan (berkas lengkap→diajukan→appraisal→SP3K→akad→pencairan), melompat ke SP3K ditolak; SP3K wajib berkas + plafon>0 dan plafon dibanding harga & porsi bank di AR (`kpr_engine.py:146-183`); pencairan bertahap berkuitansi/jurnal (DARI-KODE, tak dicoba). SLIK = pencatatan manual dengan bukti iDeb wajib (jujur: OJK tak punya API). **Tidak ada pra-kualifikasi kemampuan bayar** (DSR/penghasilan vs angsuran; `monthly_income` tersimpan tetapi tak dipakai) dan tak ada cek kelayakan FLPP/subsidi (hanya produk master). Master produk KPR kosong pada seed. |
| Dokumen pembeli (KYC, checklist) | **Lengkap** | TERBUKTI-API | Matriks syarat per konteks (tahap lead/skema KPR/legal/mitra), unggah → kirim → verifikasi; sales tak boleh memverifikasi (403), manajer bisa; hitungan "5 wajib, 1 terverifikasi, 4 kurang". |

### 4. WhatsApp, atribusi, kampanye

| Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|
| Inbox WA | **Lengkap** (simulasi) | TERBUKTI-UI/API | Daftar + thread + panel konteks lead (stage, skor, intent terdeteksi, NBA), jendela 24 jam, filter Saya/Belum dibalas/Belum dibaca, pencarian, paginasi, catatan edit kontak; pembaruan otomatis ±7 detik tanpa reload. Teks bebas di luar 24 jam → 400 "gunakan template". **Cacat:** picker template **kosong untuk role sales** (403 pada `/api/wa-templates`; `rbac_matrix.py:288`) — hanya lewat tombol saran NBA. Seed: satu percakapan tertaut ke lead orang lain (data demo, bukan bug produk). |
| Template & tata kelola | **Sebagian** | TERBUKTI-API | 12 template, kategori utility/marketing, status lokal "approved" tetapi status Meta `NOT_SUBMITTED` (belum diajukan). |
| Otomasi (keyword/lead baru/no-response) | **Lengkap** (simulasi) | TERBUKTI-API | "tanya harga" → usulan naik ke appointment + template `price_info` + tugas; lead baru → template `welcome` otomatis; sapaan otomatis **tidak** dihitung sebagai kontak pertama (SLA jujur). Aturan "Aktivasi Ulang 3 Hari" ada (0 eksekusi, tak teruji). |
| Playbook per tahap (nurture) | **Sebagian** | DARI-KODE | 5 playbook (sapaan, follow-up nurturing, pengingat survei H-1, pengingat bayar, promo) — satu langkah per tahap dengan cooldown, bukan urutan multi-langkah bercabang. |
| Broadcast | **Lengkap** (simulasi) | TERBUKTI-API | Segmen (tahap, skor, sumber, kampanye, +pelanggan), pratinjau eligible/skipped, estimasi biaya (Rp 600/pesan), jendela kirim 08–20 WIB, laju 20 pesan/detik (dapat dikonfigurasi), opt-out dilewati, antrean outbox sungguhan (12 penerima, status queued karena di luar jam). |
| Pengingat tagihan/garansi WA | **Lengkap** (simulasi) | TERBUKTI-API | 6 kandidat dihitung dari AR; run kedua → 6 `skipped` (idempoten); status "simulasi" bukan "terkirim". Role finance tak bisa menjalankan manual (403, hanya manajer). |
| Kontak WA → lead | **Lengkap** | TERBUKTI-API | Pratinjau tempel kontak, deteksi duplikat vs lead/customer, tangkap massal. |
| Atribusi lead & funnel per kampanye | **Lengkap** | TERBUKTI-UI | Funnel Atribusi: lead → terkualifikasi → booking → pendapatan per sumber/kampanye/adset/creative (drill-down), kanal ads/mitra/organik, CPL; lead tanpa ID tingkat dikelompokkan "(tanpa ID)". |
| CAPI (Meta/Google conversions) | **Sebagian** | TERBUKTI-API + DARI-KODE | 24 event `Lead` tercatat dengan `event_id` deterministik + hash SHA-256 telepon/email, status jujur `simulated`; hook untuk Lead/SubmitApplication/InitiateCheckout/Purchase. Transport live hanya Meta (`capi.py:114`: Google/TikTok → "pending"); `user_data` tanpa `fbc/fbp`/lead_id Meta; semua sumber `whatsapp` dipetakan ke Meta (lead organik ikut terkirim). Tidak teruji live. |
| Kampanye, biaya iklan, CPL/CAC/ROAS | **Lengkap** (input manual/CSV) | TERBUKTI-UI/API | Master kampanye (ID platform), biaya harian manual/CSV dengan pratinjau diff sebelum/sesudah, kunci idempoten, penolakan baris + alasan; CPL Rp 316.600, CAC Rp 1.583.000, ROAS "data belum ada" dengan penjelasan. Sinkron API Meta/Google berkode (`ads_adapters/`) tapi tak teruji; `POST /ads/sync` hanya `ads:manage`. |
| Mitra/agen, fee/komisi | **Lengkap** | TERBUKTI-UI/API | 4 jenis mitra (aggregator, broker, perorangan, referral pembeli), aturan fee per lead/qualified/SPR, PPh 21/23, tagihan fee, sengketa atribusi, analitik ROI per mitra. Komisi sales transparan per deal. **Cacat label:** kartu "Komisi Saya" menampilkan komisi Andi (Rp 42,5 jt) juga kepada marketing, manager, owner (`CommissionBreakdown.js:45`; API `/finance/commissions/summary` tak ter-scope per user untuk peran view-all). |

### 5. Analitik, portal, CS, retensi, notifikasi, mobile, akses, data

| Kemampuan | Status | Bukti | Catatan |
|---|---|---|---|
| Laporan & BI (funnel, konversi, kebocoran, forecast) | **Lengkap** (funnel) / **Sebagian** (forecast) | TERBUKTI-UI/API | 5 dashboard + Kamus 63 metrik; setiap kartu membawa rumus, status kelengkapan ("12 dari 22 metrik belum lengkap" — tidak ditulis 0), drill-down. Konversi per tahap dari `stage_history`, velocity per tahap, lead menganggur, speed-to-lead (median 18,5 mnt; 9 dari 22 ≤15 mnt), kohor bulanan, CPL/CAC/ROAS, kinerja per user, beban kerja. Target penjualan dengan metode `velocity_forecast`. Tidak ada forecast pipeline berbobot / prediksi konversi. Metrik demografi permanen kosong karena data tak punya jalur input (`models.py:79-100` — LeadCreate/LeadUpdate tak menerima demografi/budget). |
| Portal pembeli | **Lengkap** | TERBUKTI-UI/API | Login OTP (kode tampil di mode simulasi; OTP master `000000` berlaku di instance ini karena diisi lewat `.env` uji; kode `routers/portal_router.py:146` sudah fail-closed bila env kosong — IN-10 audit), ringkasan, pembayaran + jatuh tempo, KPR, progres pembangunan, peta kavling, dokumen/kuitansi/BAST PDF, komplain, garansi + pengakuan, pembatalan. Responsif di HP (390 px). Label mentah "in_progress"/"submitted" masih tampil. |
| CS / komplain | **Lengkap** | TERBUKTI-API | Kategori, prioritas, SLA per komplain (24 jam), penugasan, statistik "breached"; terhubung garansi. Tidak ada CSAT/NPS. |
| Retensi / referral / upsell | **Sebagian** | DARI-KODE | Referral hanya sebagai jenis mitra "referral_pembeli" (fee dibayar) — pembeli tak punya kode/tautan referral di portal. Upsell hanya katalog add-on per unit (`catalog/units/{id}/suggested-addons`). Garansi & kewajiban pasca-BAST ada. Tidak ada NPS, tidak ada "unit berikutnya". |
| Notifikasi | **Sebagian** | DARI-KODE + TERBUKTI-API | Pusat notifikasi in-app (kelompok, preferensi, SSE/WebSocket). **Tidak ada web-push, email, atau WA otomatis ke staf** (`wa-digest` hanya tautan wa.me manual; `grep pushManager` kosong). SLA 5 menit praktis bergantung pada aplikasi yang sedang terbuka. |
| Mobile / PWA / offline | **Sebagian** | TERBUKTI-UI + DARI-KODE | Layout responsif (hamburger, kartu KPI, inbox, profil lead rapi di 390 px, tanpa scroll horizontal halaman). Daftar lead di HP tetap tabel melebar (kolom Tahap/Skor/SLA di luar layar) dan daftar baru tampak setelah menggulir melewati 5 kartu KPI; tombol "Tambah Lead" terpotong. PWA ber-`start_url=/construction?tab=board` dan service-worker hanya cache shell (API tak di-cache); antrean offline tidak mencakup CRM. |
| Hak akses per peran | **Lengkap** | TERBUKTI-UI/API | Editor RBAC per peran (12 peran, lingkup data "hanya miliknya"/"proyek ditugaskan"); sales hanya lead/inbox/penawarannya sendiri (403 pada lead orang lain); SoD verifikasi dokumen/diskon/booking fee. |
| Ekspor / impor data | **Lengkap** | TERBUKTI-UI/API | CSV/ekspor terpilih di tabel, template Excel 16 sheet, ekspor/impor semua data, backup/restore, migrasi pelanggan baru, `analytics/export/{metric}`. |

---

## (c) Skor 1–5 per dimensi

| Dimensi | Skor | Alasan |
|---|---|---|
| **Kelengkapan fitur terhadap tujuan** | **4,0** | 867 path API (OpenAPI); hampir seluruh rantai SL-1..SL-7 ada dan hidup (SLA task, kepemilikan, keep unit atomik, KPR bertahap, Work Hub, komisi transparan, funnel manajer). Pengurang: lead ads asli, eskalasi SLA, forecast/prediksi, kualifikasi, referral self-service. |
| **Ketepatan alur untuk developer perumahan Indonesia** | **4,5** | SPR/booking fee/gerbang SLIK/SP3K/akad/pencairan KPR bertahap, BPHTB-PPN-PPh dalam penawaran, all-in komponen biaya, agen/broker dengan PPh 21/23 & sengketa atribusi, WA pribadi sebagai kenyataan lapangan, OTP WA portal, site plan kavling. Pengurang kecil: tahap `spr` & `won` terlalu dini, tanpa DSR/FLPP. |
| **Kemudahan pakai sales/manajer di lapangan** | **3,5** | Desktop sangat baik (Hari Saya, drawer tugas, NBA, inbox, site plan, tabel dengan filter + CSV). Mobile layak tetapi bukan mobile-first untuk sales: tabel lead melebar, tanpa Kanban/kartu, "Telepon" hanya `tel:` tanpa log hasil, tanpa push, PWA fokus mandor, picker template kosong bagi sales, "Komisi Saya" menyesatkan. |
| **Keandalan data** | **3,0** | Sisi positif: perbaikan ronde 1 (atomik/idempoten uang & hold unit & konversi & inbox) sudah di HEAD; BI jujur soal data tak lengkap; dead-letter tak membuang lead. Sisi negatif yang saya buktikan: dedup lintas kanal macet, re-inquiry dibuang, impor mengambil alih lead orang lain, `won` terlalu dini, tugas tak ikut reassign, skor tersimpan ≠ hitung ulang. Audit 04 punya 30 temuan (mayoritas Sedang/Rendah masih terbuka: KT-03..06, 10, 11, 14..30) dan 05 punya 11 (WA-01..04, 07, 08 diperbaiki berdasarkan git log). Rujukan: `/home/user/dadada/docs/audit/04_KONTRAK_DAN_KONVERSI_LEAD.md`, `05_WHATSAPP_INBOX.md`, `01–03_*.md` (uang masuk/keluar/GL; tidak diulang). |
| **Kedalaman analitik / pengambilan keputusan** | **4,0** | 63 metrik berumus, drill-down ke baris, penanda kelengkapan, CPL/CAC/ROAS, velocity per tahap, speed-to-lead, kohor, alasan lost, kinerja per user, partner ROI, target & forecast unit. Pengurang: tanpa forecast pipeline berbobot/prediksi, demografi tak terisi, segmentasi kustom/kohort perilaku tidak ada, banyak kartu "belum lengkap" karena data biaya/kampanye. |
| **Kesiapan integrasi eksternal** | **2,0** | Semuanya simulasi; arsitektur jujur ("mode" per integrasi, kontrak tak berubah saat live) tetapi: Meta Lead Ads/Google/TikTok asli tak punya handler (verifikasi, `leadgen`, Graph fetch), webhook publik tanpa signature/rate-limit, CAPI live hanya Meta, template WA belum disubmit, OTP/WA live tak teruji, e-sign fungsi mati (`notifications.py:65` tak dipakai), tanpa gateway pembayaran/VA, tanpa portal properti. |

**Kesimpulan terhadap tujuan:** *Siap dipakai sebagai CRM penjualan internal berbasis WA pribadi/tim kecil sekarang; belum siap sebagai mesin akuisisi iklan otomatis (<30 detik, CAPI) sampai integrasi dan pengaman webhook ditutup.* Sesuai Dok 09, ini selaras dengan status jujur "simulasi", tetapi beberapa janji (eskalasi SLA, push, merge lead) bukan soal kredensial — itu soal fitur yang belum dibangun.

---

## (d) Kekuatan, kesenjangan, kemenangan cepat

### 5 kekuatan terbesar
1. **Rantai penjualan end-to-end yang terbukti jalan dan berpagar bukti**: lead → task SLA → kontak → agenda → penawaran (diskon butuh persetujuan, kupon berkuota) → keep unit atomik (5 paralel = 1 menang) → booking fee oleh Finance → booking → pembeli → KPR bertahap. Gerbang menolak jalan pintas dengan pesan yang bisa ditindaklanjuti.
2. **Work Hub "Hari Saya" + task SLA 5 menit otomatis + catat WA pribadi berbukti**: menjawab SL-1/SL-5 dengan memahami praktik sales Indonesia (tidak memaksa WABA).
3. **Pengukuran marketing yang jujur**: biaya iklan manual/CSV dengan pratinjau diff dan idempoten, CPL/CAC/ROAS dengan penanda "data belum lengkap", funnel atribusi per kampanye/adset, event CAPI ber-hash + `event_id` anti-ganda.
4. **WhatsApp operasional lengkap (simulasi)**: inbox + jendela 24 jam, tata kelola template, otomasi intent, broadcast bersegmen (opt-out, jam kirim, biaya), pengingat tagihan idempoten, kontak WA → lead.
5. **Kedalaman domain properti Indonesia + kontrol akses**: KPR (SLIK berbukti, SP3K, akad, pencairan bertahap), mitra/agen dengan fee & sengketa atribusi, site plan interaktif, portal pembeli OTP, matriks dokumen KYC dengan SoD, RBAC per peran dengan lingkup data.

### 8 kesenjangan terbesar (urut dampak bisnis)
1. **Lead iklan asli tidak bisa masuk & webhook publik tak terlindungi** — format Meta `leadgen`/verifikasi/Graph fetch tidak ada; Google/TikTok tak diverifikasi; 15 POST palsu semua 200 → lead sampah mengisi antrean sales dan mencemari CPL & CAPI. [TERBUKTI-API] (`webhooks_router.py:94-176`)
2. **Kebocoran lead di dedup** — nomor sama lewat kanal berbeda macet di antrean gagal tanpa merge; pesan re-inquiry ("mau survey besok") dibuang tanpa jejak. [TERBUKTI-API] (`engine.py:149-153`, `capture_failures.py:31`)
3. **SLA tanpa eskalasi dan tanpa push** — hanya penerima tugas yang diberi tahu; manager/owner 0 notifikasi; tak ada realokasi/recycle; tak ada web-push/WA/email ke staf. [TERBUKTI-API + DARI-KODE] (`engine_sweepers.py:45-61`)
4. **Impor Excel/CSV mengambil alih lead milik sales lain** (reassign + timpa nama, tanpa persetujuan/jejak). [TERBUKTI-API] (`data_mgmt_import.py:240-243`)
5. **Funnel menggelembung/tidak akurat** — `won` saat konversi (booking fee saja), tak ada tahap `spr`, reservasi kedaluwarsa tak menurunkan lead, tugas tak ikut reassign (KT-13/16/25).
6. **Tidak ada kualifikasi & kelayakan bayar** — lead tak punya input budget/penghasilan/DP/tujuan/timeline (metrik demografi permanen kosong), tak ada DSR/FLPP; pra-skrining KPR (SL-4) hanya SLIK manual. [DARI-KODE `models.py:79-100`]
7. **Ergonomi lapangan sales** — daftar lead HP berupa tabel melebar, tanpa Kanban, "Telepon" tanpa log hasil/rekaman, picker template kosong untuk sales, PWA & offline hanya untuk mandor, "Komisi Saya" bukan milik sendiri bagi non-sales. [TERBUKTI-UI]
8. **Integrasi keluar belum teruji/terputus** — CAPI live hanya Meta tanpa `fbc/fbp`/lead_id, Google/TikTok "pending"; template WA belum diajukan ke Meta; e-sign fungsi mati; tanpa payment gateway/VA/portal properti.

### Kemenangan cepat (≤ 2 minggu kerja)
| # | Pekerjaan | Perkiraan | Efek |
|---|---|---|---|
| 1 | Handler Meta Lead Ads asli: `GET` verifikasi + parse `leadgen` + fetch Graph + HMAC `X-Hub-Signature-256` untuk SEMUA webhook lead + rate-limit per IP/token | 4–5 hari | Menutup #1; membuka janji "<30 detik" |
| 2 | Dedup lintas kanal: tangkap `DuplicateKeyError` → perlakukan sebagai "sentuhan ulang" (aktivitas + pesan + tugas "lead kembali" + update `last_touch`), bukan antrean gagal; impor tak boleh reassign lead milik orang lain (kembalikan sebagai "dilewati — milik X") | 2 hari | Menutup #2, #4 |
| 3 | Eskalasi SLA: `sla_breach_check` → notifikasi + tugas ke supervisor divisi pada 1× dan 2× SLA; opsi realokasi otomatis | 1–2 hari | Menutup sebagian #3 |
| 4 | Web-push (VAPID) memakai service-worker yang sudah ada untuk lead baru, SLA lewat, pesan WA masuk | 3–4 hari | Menutup sisa #3 |
| 5 | Beri sales hak lihat template terpakai (endpoint daftar template approved) + scope "Komisi Saya" per user | 1 hari | Memperbaiki sebagian #7 |
| 6 | Kartu lead di mobile + Kanban sederhana (tahap sebagai kolom, tanpa drag dulu) + tombol "Telepon" yang mencatat panggilan & hasil | 4–5 hari | #7, dan menyiapkan call-log |
| 7 | Field kualifikasi lead (budget_band, penghasilan, DP siap, tujuan, jadwal beli) + pre-check DSR sederhana di penawaran KPR | 3 hari | #6; mengisi metrik demografi |

---

## (e) Kemampuan lanjutan yang hilang & nilainya

| Kemampuan | Status di sini | Nilai bagi developer perumahan ID |
|---|---|---|
| Percakapan AI / chatbot kualifikasi (WA 24/7) | Tidak ada (`grep llm/openai/chatbot` hanya kebetulan non-AI) | Respons <1 menit di luar jam kerja, kualifikasi budget/lokasi/KPR otomatis → naikkan % lead ads yang terkualifikasi; paling besar kaitannya dengan aturan 5-menit. |
| Rekomendasi unit otomatis (cocokkan budget/tipe/lokasi/ketersediaan) | Tidak ada (hanya saran add-on per unit) | Memangkas waktu sales menyusun penawaran; menaikkan konversi appointment→booking. |
| Prediksi konversi / skor prediktif / forecast pipeline berbobot | Tidak ada (skor aturan; target `velocity_forecast` untuk unit) | Prioritas follow-up lebih tajam, proyeksi kas penjualan untuk owner. |
| Sequence/nurture multi-langkah bercabang | Sebagian (playbook 1 langkah per tahap) | Mengurangi lead "diam" tanpa kerja manual; bandingkan A/B pesan. |
| Dialer / call logging & rekaman | Tidak ada (`tel:`; metrik `calls_logged` diakui "belum punya jejak") | Sales ID mengandalkan telepon; tanpa log, speed-to-lead dan kualitas follow-up tak terukur, coaching tak berdasar. |
| Integrasi portal properti (Rumah123, 99.co, OLX, Lamudi) | Tidak ada | Sumber lead volume tinggi; bisa memakai webhook partner sebagai jembatan awal. |
| E-sign tersertifikasi (Privy/VIDA/Peruri/Tilaka) | Hanya-kerangka (fungsi tak dipanggil; "sign" = catat nama) | Menghilangkan putaran cetak-tanda tangan-pindai SPR/PPJB; mempercepat booking→SPR. |
| VA / payment gateway (Midtrans/Xendit/Doku) | Tidak ada (bukti transfer diunggah, diverifikasi Finance) | Booking fee online 24/7, rekonsiliasi otomatis, menutup celah salah-input bukti. |
| WhatsApp Flows / katalog / tombol interaktif | Tidak ada | Form kualifikasi & pilih jadwal survei di dalam WA; konversi lebih tinggi dari form web. |
| Uji A/B kampanye/landing/pesan | Tidak ada | Menurunkan CPL berdasarkan data, bukan firasat. |
| Segmentasi & kohort lanjutan (segmen tersimpan, demografi/perilaku) | Sebagian (segmen broadcast tahap/skor/sumber/kampanye; kohor bulanan) | Retargeting dan reaktivasi lead `recycle`/`lost` yang tertarget. |
| Referral/loyalty pembeli self-service, NPS/CSAT, upsell unit berikutnya | Sebagian (mitra "referral_pembeli", tanpa kode referral di portal; tanpa NPS) | Referral 14–25% (Dok 06) tidak tertagih tanpa kanal mudah; NPS pasca-BAST menjaga reputasi. |
| Penugasan lanjutan (jam kerja, kehadiran, kapasitas, proyek, terima/tolak) | Sebagian (beban lead terbuka) | Distribusi yang adil dan tidak menumpuk pada sales yang sedang cuti/luar kota. |
| Pembangun form/landing + QR showroom ber-UTM | Tidak ada | Atribusi event/pameran/billboard; showroom publik saat ini atribusinya kosong. |

---

## Terverifikasi OK (agar tidak berat sebelah)
- Gerbang tahap lead menolak lompat tahap, `won` manual, `lost` tanpa alasan, override oleh sales (403).
- Hold unit atomik (5 paralel → 1×200 + 4×409); batas 1 reservasi aktif per lead.
- Penawaran: diskon di atas batas butuh persetujuan manajer; tak bisa dikirim sebelum disetujui; sales tak bisa menyetujui.
- Booking fee wajib lunas oleh Finance sebelum booking; KPR tahap tak bisa dilompati.
- Teks bebas WA di luar 24 jam ditolak; auto-sapaan tidak dihitung sebagai kontak pertama.
- Pengingat WA idempoten; impor biaya iklan idempoten dengan pratinjau diff; antrean gagal tidak membuang payload.
- Partner webhook: token, status mitra, dan atribusi tanpa lead kembar; showroom publik ber-rate-limit.
- Portal pembeli bekerja lengkap di HP; sales tak dapat membaca lead milik sales lain.

## Tidak bisa diverifikasi
- Seluruh mode LIVE: WA Cloud API (kirim/terima, tanda tangan HMAC, template approval), Meta Lead Ads, Google Ads, CAPI (Meta live path ditulis di kode, tidak dijalankan), sinkron kampanye/biaya API, OTP via WA sungguhan.
- Pencairan KPR bertahap, penjadwalan sweeper kedaluwarsa/no-response (0 eksekusi di data), notifikasi pada volume besar, performa dengan ribuan lead (data demo ±86 lead, 18 unit).
- Perilaku PWA offline untuk sales (tidak dirancang; hanya dibaca dari kode).

## Pertanyaan terbuka untuk pemilik
1. Apakah lead iklan akan masuk via perantara (Zapier/Make) atau handler Meta langsung? Menentukan prioritas kemenangan cepat #1.
2. Apakah `wa.auto_capture_lead` akan dinyalakan di produksi (default mati membuat chat baru menunggu klik manual)?
3. Siapa penerima eskalasi SLA (manajer divisi? marketing admin?) dan berapa tenggat realokasi?
4. Apakah tahap `spr` (spec v2) dan penundaan `won` sampai SPR ditandatangani akan dikerjakan?

## Jejak data uji di instance #9 (awalan EVAL-)
±38 lead `EVAL-*` (termasuk uji banjir webhook & uji balapan), penawaran `PNW/2026/0001` (lead EVAL-Stage) + deal A-04 yang sudah dikonversi menjadi pembeli, reservasi A-05 (EVAL-Race*), showroom proyek CAA diaktifkan (token `[token-dihapus]`), **token webhook mitra "Portal Properti Nusantara" dirotasi** (token lama tak berlaku), lead `4c94f5c7…` dipindah ke `sales@` oleh uji impor, broadcast `EVAL-broadcast` (12 penerima, antre), 6 pengingat WA simulasi, 1 dokumen KTP terverifikasi pada lead Ibu Dewi Kartika, pratinjau impor biaya iklan `EVAL-spend.csv`. Setelan `wa.auto_capture_lead` sudah dikembalikan ke bawaan.
