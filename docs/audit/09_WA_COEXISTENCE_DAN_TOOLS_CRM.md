# WhatsApp Coexistence dan Tool CRM Lanjutan — analisis untuk SIPRO/Estora

> Tanggal: 5 Nov 2026 · Jenis: analisis dan rekomendasi (tidak ada kode yang diubah di dokumen ini).
> Tingkat keyakinan di tiap klaim ditandai: **[Meta-asli]** teks halaman resmi Meta yang dibaca langsung · **[Meta-ringkasan]** dari halaman resmi tetapi hanya tersedia sebagai ringkasan model, perlu dicek ke halaman referensi webhook masing-masing · **[Vendor]** blog/dokumen penyedia WhatsApp (BSP), bisa tertinggal dari Meta · **[Kode]** diverifikasi dari kode repo ini · **[Pendapat]** penilaian saya.

## 1. Jawaban singkat

1. **Coexistence cocok dengan cara kerja tim sales developer** (sales memegang HP dengan WhatsApp Business app, sementara perusahaan ingin otomasi, iklan, dan pencatatan di CRM) — **tetapi SIPRO belum siap memakainya**. Ada lima celah nyata (bagian 4).
2. **Tidak bisa diaktifkan hanya dengan mengisi kredensial seperti rencana sekarang.** Coexistence mewajibkan Embedded Signup lewat pihak yang berstatus *Tech Provider/Solution Partner* **[Meta-asli]**. Alur manual di `memory/WA_META_CREDENTIALS_GUIDE.md` (buat Meta App, token System User) mensyaratkan nomor **dilepas** dari aplikasi WhatsApp biasa. Itu model kebalikan dari coexistence.
3. **Jalur tercepat: lewat BSP yang mendukung coexistence** (mis. 360dialog, WATI, SleekFlow, Respond.io menyebut dukungan **[Vendor]**; dukungan khusus Indonesia dan Qontak/Mekari **tidak terkonfirmasi** dari sumber yang saya baca — tanyakan langsung). Jalur jangka panjang: menjadi Tech Provider sendiri, masuk akal karena SIPRO sudah multi-organisasi.
4. **Temuan yang tidak berkaitan dengan coexistence tetapi lebih mendesak untuk iklan:** SIPRO belum menangkap `ctwa_clid`/`referral` dari iklan Click-to-WhatsApp dan mengirim konversi ke Meta dengan format yang salah untuk percakapan WhatsApp (bagian 4, celah 5). Tanpa itu, biaya iklan CTWA tidak bisa dihubungkan ke penjualan.

## 2. Apa itu coexistence (fakta)

Satu nomor WhatsApp Business yang **dipakai bersamaan** di aplikasi WhatsApp Business (HP) dan di Cloud API (CRM/otomasi).

| Hal | Fakta | Keyakinan |
|---|---|---|
| Syarat aplikasi | WhatsApp Business app **versi 2.24.17 atau lebih tinggi** | Meta-asli |
| Syarat integrator | Harus Solution Partner atau **Tech Provider**, memakai **Embedded Signup** dengan session logging dan webhook yang bisa menerima payload | Meta-asli |
| Cara onboarding | Pelanggan memasukkan nomor Business app, menyalin kode verifikasi, menekan "Connect to the Business Platform", **menyetujui berbagi riwayat chat**, lalu menempel kode. Parameter: `featureType: "whatsapp_business_app_onboarding"` (+ `sessionInfoVersion: "3"`); di **Embedded Signup v5 fitur ini aktif secara bawaan** | Meta-asli |
| Versi Embedded Signup | v2 dan v3 **dijadwalkan deprecated 15 Okt 2026** (sudah lewat per hari ini); pakai v4/v5 | Meta-asli |
| Akun | Akun Business app dikonversi menjadi akun Messaging dengan `waba_id` yang sama; langkah registrasi nomor dilewati | Meta-asli |
| Cek status | `GET /{phone-number-id}?fields=is_on_biz_app,platform_type` → `true` / `CLOUD_API` | Meta-asli |
| Sinkron riwayat | **6 bulan terakhir** pesan 1:1 + semua kontak. Grup tidak ikut. Dimulai segera setelah onboarding, via `POST /{phone}/smb_app_data` (`sync_type`: `smb_app_state_sync` lalu `history`); **harus dilakukan dalam 24 jam setelah onboarding**, **masing-masing hanya sekali** (ulang = offboard lalu onboard lagi). Pelanggan boleh **menolak** berbagi riwayat (webhook `history` berkode error 2593109) | Meta-asli (batas 24 jam, sekali, menolak) · Meta-ringkasan (fase 0–2: hari 0–1, 1–90, 90–180; media hanya 14 hari terakhir) |
| Webhook wajib | `account_update`, `history`, `smb_app_state_sync`, **`smb_message_echoes`** (pesan yang dikirim dari Business app/companion) | Meta-asli (daftar langganan) · Meta-ringkasan (bentuk payload) |
| Jendela 24 jam | Berlaku untuk pesan **Cloud API**. Pesan dari Business app **tidak** kena jendela dan **tidak** membuat/memperpanjang jendela API, tidak memengaruhi harga API. Bila pelanggan menulis sebelum onboarding, balasan via API hanya bisa template | Meta-asli |
| Harga | Pesan dari Business app tetap **gratis**; pesan via API mengikuti tarif Cloud API | Meta-asli |
| Throughput | Nomor yang dipakai di app dan API: **tetap 20 pesan/detik** | Meta-asli |
| Tidak didukung | Grup; pesan sementara (dimatikan untuk chat 1:1); view-once; live location; **daftar siaran (broadcast list) dinonaktifkan** (yang ada jadi read-only); panggilan suara/video; katalog/pesanan/status; sebagian alat bisnis (pesan pemasaran, sapaan, away message, quick replies, label — tabel Meta menandainya tidak didukung); profil bisnis; Channels | Meta-asli (tabel fitur) |
| Perangkat tertaut | Hingga 4 companion. Semua didukung **kecuali WhatsApp untuk Windows dan WearOS**. **Semua companion diputus (unlink) saat onboarding**. Pesan dari companion yang tidak didukung tidak memicu webhook | Meta-asli |
| Putus otomatis | `account_update` → `PARTNER_REMOVED` dengan alasan, antara lain **`PRIMARY_INACTIVITY` (perangkat utama tidak aktif ±14 hari)** dan `COMPANION_INACTIVITY` (±30 hari) | Meta-asli |
| Putus manual | Settings › Account › Business Platform › Disconnect Account | Meta-asli |
| Edit/hapus pesan | Edit dalam 15 menit, hapus-untuk-semua dalam 2 hari ikut tercermin di webhook `messages` | Meta-asli |

Catatan yang **tidak** saya temukan: daftar negara yang didukung/tidak didukung (halaman Meta tidak menyebut Indonesia; satu vendor menyatakan Indonesia didukung sejak awal tetapi mengakui Meta tidak menerbitkan daftar bertanggal). **Konfirmasi ke BSP/Meta sebelum berkomitmen.** Tarif Indonesia yang beredar di blog BSP saling bertentangan; gunakan *rate card* resmi Meta saat menghitung anggaran.

## 3. Kenapa ini penting untuk developer perumahan

Hasil utama project (docs/analysis/05): konversi lead (kecepatan respons), cegah kebocoran, jaga tenggat, amankan arus kas. Dalam praktik, **sales properti membangun hubungan lewat WhatsApp pribadi di HP**. Dua pilihan yang ada sekarang sama-sama buruk:
- Nomor khusus untuk API (model SIPRO sekarang): sales tidak bisa memakai aplikasi di HP; adopsi sulit dan riwayat chat lama hilang.
- Sales tetap di HP, CRM hanya diisi manual: SLA respons, "belum dibalas", skor lead, dan atribusi iklan tidak akurat (itu keadaan sebelum SIPRO).

Coexistence menutup keduanya: chat tetap bisa dibalas dari HP, tetapi **setiap pesan, dua arah, tercatat di lead di SIPRO**, dan otomasi/iklan/penagihan berjalan lewat API pada nomor yang sama.

## 4. Kesiapan SIPRO hari ini (dari kode)

| # | Celah | Bukti di kode | Dampak |
|---|---|---|---|
| 1 | **Tidak ada Embedded Signup / jalur Tech Provider.** Kredensial dimasukkan manual (`token`, `phone_id`, `waba_id`, `app_secret`, `verify_token`) | `backend/wa_gateway.py:27-28` (`CRED_KEYS`), `memory/WA_META_CREDENTIALS_GUIDE.md` (nomor harus "dilepas" dari app) | Coexistence tidak bisa dihubungkan; tidak ada layar "Hubungkan nomor" |
| 2 | **Webhook coexistence tidak ditangani.** Hanya `messages`, `statuses`, dan beberapa event akun (`message_template_status_update`, `phone_number_quality_update`, `phone_number_name_update`). Field lain → dicatat ke `capture_failures` sebagai "belum ditangani" | `backend/wa_inbound.py:197-207` | `smb_message_echoes`, `history`, `smb_app_state_sync` dan `account_update` (termasuk `PARTNER_REMOVED`) **tidak masuk Inbox**. Balasan dari HP tidak tercatat |
| 3 | **Satu channel/nomor per organisasi** (`channel_accounts.wa_main`) | `backend/wa_gateway.py` (`CHANNEL_CODE`) | Tidak bisa satu nomor per proyek/tim sales; coexistence per-nomor butuh model multi-channel |
| 4 | **Model data mengira semua pesan keluar berasal dari API**: jendela 24 jam, status kirim, `last_direction` dihitung dari pesan yang SIPRO kirim | `routers/inbox_router.py` (`window_open`, `last_direction`), `wa_gateway.window_open` | Chat yang dibalas dari HP tetap tampil "Belum dibalas"; SLA respons dan skor lead salah; otomasi bisa membalas pelanggan yang sedang dilayani manusia di HP |
| 5 | **Atribusi iklan Click-to-WhatsApp tidak ada, dan format CAPI tidak cocok.** Webhook tidak menyimpan `referral`/`ctwa_clid`. `capi.py` mengirim ke endpoint **Pixel** dengan `action_source: "system_generated"` | `backend/capi.py:117-130`; tidak ada `ctwa_clid`/`referral`/`business_messaging` di seluruh backend | Percakapan dari iklan tidak bisa dikaitkan ke kampanye; Meta tidak diberi sinyal "lead berkualitas"/"pembelian" untuk percakapan WhatsApp; CPL/CAC/ROAS di dasbor tidak berdasar |

Yang **sudah baik** dan bisa dipakai ulang: tata kelola template (`wa_template_governance.py`, `wa_templates_meta.py`), opt-out dan jam kirim (`wa_compliance.py`), antrean kirim dengan batas laju (`wa_outbox.py`), deduplikasi `wamid` dan nomor, antrean **Kontak WA → Lead** (`wa_contacts.py`, `/wa-capture`) yang cocok sebagai muara kontak hasil sinkronisasi, simulasi webhook berbentuk payload Meta asli (`wa_inbound.build_meta_payload`) sehingga pengembangan bisa diuji tanpa kredensial live, dan Inbox yang kini sudah diperbaiki (paginasi, real-time, tanpa kedip).

## 5. Opsi arsitektur

| Opsi | Cara | Usaha | Biaya/risiko | Cocok bila |
|---|---|---|---|---|
| **A. Status quo** | Nomor khusus API, dilepas dari app | Nol | Adopsi sales rendah; riwayat lama hilang | Hanya untuk pilot teknis |
| **B. Coexistence lewat BSP** | BSP (yang mendukung coexistence) mengurus Embedded Signup dan App Review; SIPRO terhubung ke API/webhook BSP lewat adapter | Sedang (adapter + handler webhook bagian 6) | Biaya langganan BSP + tarif pesan; data lewat pihak ketiga; **ketersediaan di Indonesia perlu dikonfirmasi** | **Rekomendasi tahap pertama**: tercepat, risiko rendah |
| **C. Tech Provider sendiri** | Daftar app, Business Verification, App Review (izin `whatsapp_business_management`/`messaging`), Embedded Signup v5 di Pusat Konfigurasi | Besar (proses Meta berminggu-minggu + engineering) | Kontrol penuh, tanpa biaya BSP; beban kepatuhan dan operasional | Bila SIPRO dijual/dipakai multi-perusahaan (SaaS) |
| **D. Dua nomor** | Nomor A API-only (otomasi, iklan CTWA, tagihan), nomor B app untuk sales | Kecil | Pelanggan melihat dua nomor; riwayat terpecah | Jalan keluar bila coexistence tidak tersedia/menyulitkan |

**[Pendapat] Rekomendasi:** kerjakan **bagian 6 lebih dulu** (tidak bergantung penyedia, bisa diuji dengan payload simulasi), lalu pilot **Opsi B** pada satu tim sales, dan evaluasi Opsi C setelah ada bukti nilai.

## 6. Spesifikasi perubahan di SIPRO (urut prioritas)

**P1 — penangkapan data coexistence (tanpa bergantung penyedia)**
1. `smb_message_echoes` → simpan sebagai pesan keluar bertanda `source: "business_app"`, `mode: "coexistence"`; **tidak** membuka/memperpanjang jendela 24 jam; perbarui `last_direction=out` dan `last_message_at`; catat "kontak pertama" dan waktu respons di lifecycle lead atas nama pemilik percakapan (echo tidak membawa identitas staf); deduplikasi per `id`.
2. `history` → impor per potongan (`chunk_order`, `progress`) secara idempoten per `wamid`, dengan bendera `imported=true`: **tidak memicu otomasi, skor, notifikasi, atau tugas**. Jangan membuat lead untuk setiap kontak enam bulan; masukkan ke antrean **Kontak WA → Lead** untuk diputuskan manusia.
3. `smb_app_state_sync` → kontak ditambah/dihapus → antrean kontak WA (status `new`), dengan deteksi duplikat lead/customer yang sudah ada.
4. `account_update` → notifikasi ke admin dan panel kesehatan; untuk `PRIMARY_INACTIVITY` tampilkan peringatan dini ("buka WhatsApp Business app di HP minimal tiap ~13 hari agar tidak terputus"), karena putus berarti API berhenti.
5. Inbox: lencana "dikirim dari HP", aturan **anti tabrakan** (bila ada echo dalam N menit terakhir, tunda otomasi balasan pada percakapan itu), dan hitung "belum dibalas" dari pesan keluar apa pun (API **atau** app).

**P2 — onboarding dan model channel**
6. Layar Pusat Konfigurasi › WhatsApp: tombol "Hubungkan nomor WhatsApp Business app" (Embedded Signup v5 atau konektor BSP), status `is_on_biz_app`/`platform_type`, tombol sinkronisasi 24 jam dengan penghitung waktu, dan jejak persetujuan berbagi riwayat.
7. Model **multi-channel**: satu organisasi dapat memiliki beberapa nomor (per proyek/tim), dengan pemilik tiap nomor dan pengarahan percakapan.
8. Kebijakan pemakaian: siapa membalas di mana (aturan serah-terima HP ↔ SIPRO), larangan broadcast dari aplikasi (daftar siaran dinonaktifkan Meta) sehingga siaran lewat template SIPRO dengan opt-in, dan penyesuaian batas laju **20 pesan/detik** pada antrean `wa_outbox`.

**P3 — iklan dan atribusi (berlaku walau tanpa coexistence)**
9. Simpan `referral` (termasuk `ctwa_clid`, `source_id`, judul/URL iklan) dari **pesan pertama** setelah klik iklan — sumber saya menyebut Meta hanya mengirimnya pada pesan pertama, jadi harus disimpan saat itu.
10. Kirim konversi dengan **Conversions API for Business Messaging**: `action_source: "business_messaging"`, `messaging_channel: "whatsapp"`, `ctwa_clid` di `user_data`, peristiwa Lead / QualifiedLead / Purchase, ke *dataset* yang terhubung (panduan onboarding Meta diperbarui 5 Mei 2026 **[Vendor+Meta, perlu dicek]**). Petakan: lead → `Lead`; survei/KPR lolos → `QualifiedLead`; akad/lunas → `Purchase` dengan nilai.

## 7. Tool CRM lanjutan yang layak dipertimbangkan

Prinsip: **beli yang komoditas, bangun yang menjadi keunggulan**. Keunggulan SIPRO adalah logika domain developer (booking → kontrak → AR/AP/GL → serah terima) yang tidak dimiliki CRM umum; konektivitas WhatsApp, pembayaran, dan tanda tangan elektronik adalah komoditas. Penilaian dampak dibaca terhadap empat hasil utama project. Klaim spesifik penyedia ditandai perlu diverifikasi.

| Kemampuan | Dampak utama | Beli / integrasi / bangun | Prioritas | Catatan |
|---|---|---|---|---|
| **Konektor WA via BSP + coexistence** | Konversi, SLA | Beli (BSP), adapter di SIPRO | Tinggi | Bagian 5–6. Inbox tetap di SIPRO (melekat ke lead dan lifecycle). |
| **CTWA + CAPI Business Messaging** | Konversi, biaya iklan | Bangun (kecil, ±1–2 minggu) | **Tinggi** | Bagian 6 P3. Paling jelas hubungan ke ROI iklan. |
| **Virtual Account / QRIS per tagihan** (Xendit, Midtrans, DOKU, atau VA bank) | Arus kas | Integrasi payment gateway | **Tinggi** | Booking fee dan termin dibayar via VA, rekonsiliasi **otomatis** ke kuitansi (menutup banyak kasus bukti transfer manual dan celah kuitansi ganda). Perlu pemetaan ke `payment_intake`/`bank_match` yang sudah ada. |
| **Lapisan AI percakapan** (mis. model Claude via API) | Konversi, SLA | Bangun di atas Inbox | Tinggi | (a) kualifikasi awal di WA (anggaran, rencana KPR, lokasi) dengan eskalasi ke manusia, (b) ringkasan percakapan dan usulan langkah berikutnya (sudah ada heuristik NBA), (c) draf balasan (sudah ada saran heuristik), (d) ekstraksi KTP/NPWP/slip gaji untuk KYC dengan persetujuan manusia. **Pagar:** AI tidak menjawab harga/hukum/janji tanpa persetujuan; persetujuan pelanggan; UU PDP. |
| **Nurture otomatis multi-langkah** (journey/sequence dengan syarat tunggu) | Konversi | Bangun di `wa_playbooks`/otomasi | Sedang | Fondasi playbook dan template sudah ada; perlu penjadwal langkah dan kondisi keluar. |
| **Lead dari portal properti** (Rumah123, 99.co, dll.) dan **Meta Lead Ads / Google lead form** | Konversi | Integrasi webhook/email-parser | Sedang | Kerangka Ads ada tetapi belum teruji live (kredensial kosong). Syarat API tiap portal perlu dicek. |
| **Tanda tangan elektronik + e-Meterai** (penyelenggara tersertifikasi, mis. PrivyID, VIDA, Peruri) | Tenggat, kepercayaan | Integrasi | Sedang | Cocok untuk SPR/dokumen internal. **PPJB dan AJB tetap akta notaris/PPAT** — jangan menjanjikan penggantian. Verifikasi keabsahan per jenis dokumen dengan notaris. |
| **Telepon**: klik-untuk-telepon dan catatan panggilan | Konversi | Integrasi | Sedang | Banyak lead properti sebenarnya ditelepon; panggilan perlu tercatat ke lead. Penyedia belum saya telusuri. |
| **Pra-skrining KPR** (DSR, plafon, daftar periksa SLIK) | Konversi (deal gugur akhir) | Bangun, sebagian ada (`kpr_plafon`, `kpr_engine`) | Sedang | SLIK dikelola OJK/bank; bangun daftar periksa dan pelacakan status, bukan akses langsung. |
| **Analitik/BI** (Metabase atau Looker Studio pada salinan baca) | Keputusan | Beli/pasang | Sedang | BI bawaan ada; alat luar membantu analisis bebas tanpa membebani aplikasi. |
| **WhatsApp Flows** (formulir dalam chat, mis. simulasi cicilan, penjadwalan survei) | Konversi | Bangun/BSP | Rendah-sedang | Fitur Cloud API; ketersediaan dan batasan per akun perlu diverifikasi. |
| **Survei kepuasan (NPS) dan program referral pembeli** | Retensi, biaya akuisisi | Bangun kecil | Rendah | Marketing fee referral sudah ada; NPS belum. |

## 8. Peta jalan (usulan)

- **0–30 hari:** P1 bagian 6 (penangkapan echo, riwayat, kontak, `account_update`), penyimpanan `referral/ctwa_clid`, perbaikan CAPI. Semuanya diuji dengan payload simulasi. Paralel: tanya 2–3 BSP tentang coexistence di Indonesia, harga, dan batas.
- **30–60 hari:** pilot coexistence pada satu tim sales lewat BSP; aturan serah-terima HP ↔ SIPRO; Virtual Account untuk booking fee dan termin.
- **60–90 hari:** lapisan AI kualifikasi dan KYC (dengan persetujuan manusia), nurture multi-langkah, evaluasi Opsi C (Tech Provider) berdasarkan hasil pilot.

## 9. Risiko dan kepatuhan

- **Putus tak sengaja:** perangkat utama tidak aktif ±14 hari memutus coexistence (API berhenti). Pasang peringatan dini dan SOP.
- **Kualitas nomor dan batas pesan Meta:** pesan promosi massal tanpa opt-in menurunkan kualitas nomor; sudah ada opt-out dan jam kirim, pertahankan dan perluas.
- **Pelindungan data pribadi (UU No. 27/2022):** impor riwayat enam bulan memuat data pribadi; perlu dasar persetujuan/kepentingan sah, kebijakan retensi, dan pembatasan akses per sales (Inbox sudah membatasi sales ke percakapan miliknya). **[Pendapat]** — konfirmasikan ke konsultan hukum.
- **Biaya:** tarif pesan Indonesia di blog BSP saling bertentangan; hitung dengan rate card resmi Meta.
- **Kebergantungan penyedia:** adapter `wa_gateway` sudah memisahkan transport, sehingga pindah BSP atau ke Tech Provider sendiri relatif murah — pertahankan batas itu.
- **Fitur yang hilang dari aplikasi** (daftar siaran, pesan sementara, view-once, live location, panggilan) harus disosialisasikan ke sales sebelum pilot.

## 10. Sumber

- Meta — [Onboarding WhatsApp Business app users (coexistence)](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users) (versi `.md` dibaca langsung; sebagian isi hanya tersedia sebagai ringkasan model)
- Meta — [Conversions API for Business Messaging](https://developers.facebook.com/documentation/ads-commerce/conversions-api/business-messaging) dan [panduan onboarding](https://developers.facebook.com/docs/marketing-api/conversions-api/business-messaging) (dari hasil pencarian; tidak dibaca penuh)
- 360dialog — [WhatsApp Coexistence](https://docs.360dialog.com/docs/hub/embedded-signup/whatsapp-coexistence)
- WATI — [Coexistence untuk SMB](https://www.wati.io/en/blog/coexistence-for-smbs/) · Respond.io — [Business app dan API bersamaan](https://respond.io/blog/how-to-use-whatsapp-business-app-and-api-at-the-same-time) · SleekFlow — [Coexistence (ID)](https://sleekflow.io/id-id/blog/whatsapp-coexistence-sleekflow)
- Qontak — [Daftar harga pesan WhatsApp](https://help-center.qontak.com/hc/en-us/articles/48430892733465-Latest-WhatsApp-Message-Prices-October-2026) (angka tarif berbeda antar sumber; verifikasi ke Meta)
- Repo: `backend/wa_gateway.py`, `wa_inbound.py`, `capi.py`, `routers/inbox_router.py`, `memory/WA_INTEGRATION_PLAN.md`, `memory/WA_META_CREDENTIALS_GUIDE.md`, `docs/analysis/05_PAIN_POINTS_AND_BUSINESS_NEEDS.md`
