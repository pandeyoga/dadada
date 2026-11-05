# Audit: Pembuatan Kontrak & Konversi Lead → Customer (Instance #5: UI :3005, API :8005, DB sipro_ct)

Auditor: stream "kontrak + lead→cust". Semua data uji diawali `AUDIT-`. Repo tidak diubah. Skrip probe: `(skrip probe tidak disertakan di repo)` (h.py = helper, f*/t*/c* = skenario). Screenshot: `img/kontrak/` (disebut per temuan).
Catatan jujur tentang alat: satu uji (sweeper kedaluwarsa) dijalankan lewat harness Python pada DB scratch baru `sipro_ct_scratch_audit` (sudah dihapus lagi; tidak menyentuh DB instance lain) karena `reservation.hold_days` minimum 1 hari dan DB dilarang diubah langsung. Pengaturan `lead.won_trigger` sempat diubah lewat API untuk uji dan sudah dikembalikan ke `spr_signed`.

---------------------------------------------------------------------------------------------------
## Ringkasan eksekutif
1. Keluhan pemilik **terbukti benar di dua titik inti**: (a) konversi lead→customer **tidak aman terhadap permintaan paralel** (HTTP 500, customer ganda/yatim, nomor kontrak hangus), dan (b) ada **dua jalur legal paralel** yang saling bertabrakan (jalur lama `/deals/{id}/ppjb|ajb` vs jalur kontrak).
2. **Kritis [KT-01]**: peran *sales* bisa menjadikan unit **TERJUAL (SOLD)** lewat jalur legal lama dengan hanya Rp 5 jt booking fee dibayar dari Rp 720–850 jt — melewati semua gerbang kontrak (DP, pelunasan, BAST, pemisahan tugas manajer). Kontrak tetap `draft/belum`, AR masih piutang 845 jt, lead `won`.
3. **Tinggi**: pengisian komponen biaya kontrak (tugas yang dibuat konversi sendiri) membuat SPR **tidak mungkin ditandatangani** [KT-03]; `set_scheme` membuat kontrak tidak bisa menerbitkan SPR apa pun [KT-05]; re-aktivasi kontrak mengacak alokasi pembayaran [KT-06]; `POST /finance/ar/{deal}/schedule` menghidupkan piutang hantu pada deal batal [KT-07]; kupon kuota-1 terpakai dua kali + 500 dengan deal tertinggal [KT-08]; sales bisa membaca kontrak/harga/AR/NIK milik sales lain lewat `/customers/{id}/…` [KT-09].
4. Konfigurasi Pusat Konfigurasi `payment.staged.*`/`payment.cash.*` **tidak berlaku** pada skema bawaan; teks "x hari setelah kontrak diaktifkan" tercetak di SPR padahal tanggal dihitung dari tanggal booking [KT-10, KT-11].
5. Pembatalan deal `booked` yang baru bayar booking fee **buntu** (pesan saling merujuk) [KT-12]; lead jadi `won` begitu dikonversi (UI menulis "akad/AJB selesai") [KT-13]; pemicu konfigurasi `ppjb_signed`/`ajb_signed` tidak pernah menjalankan konversi [KT-14].
6. Sinkronisasi data lead↔customer↔deal↔kontrak↔WA setelah konversi bocor di banyak titik (nama/telepon/PIC) [KT-15, KT-16].
7. Terverifikasi OK: hold unit atomik (tidak ada double-booking), gerbang PPJB di jalur kontrak, SPR vs tagihan memblokir tanda tangan bila beda, pembulatan termin, tanpa placeholder `None/undefined` di SPR, klik ganda UI hanya 1 request.
Jumlah temuan: 30 (1 Kritis, 10 Tinggi, 14 Sedang, 5 Rendah).

---------------------------------------------------------------------------------------------------
## Cakupan (apa yang diuji)
- Alur penuh sebagai sales/manager/finance/owner/superadmin lewat API (±28 skrip) dan UI Playwright (8 skrip, 14 screenshot): buat lead AUDIT- → kontak pertama → agenda survei → reservasi (tanpa/dengan skema, kupon, penawaran) → bayar booking fee (finance) → booking → "Jadikan Pembeli" → biaya kontrak → aktivasi → SPR (generate/finalize/sign) → PPJB/AJB (jalur kontrak & jalur lama) → pembatalan (satu-klik & formal) → konversi ulang.
- Kasus tepi: konversi paralel (3–4 request), reservasi paralel (unit sama; lead sama dua unit; kupon kuota 1), klik ganda UI, NIK format/invalid, customer manual vs lead (dedup), edit kontak setelah konversi, reassign PIC, scoping sales2, ganti skema kontrak, re-aktivasi, PPJB paralel, tanda tangan ganda, SPR ganda, lead `lost` memesan unit, deal batal vs gerbang stage, penawaran vs batas unit, pemicu `lead.won_trigger`, expiry sweeper (harness), KPR (app ganda/plafon), nomor kontrak berlubang.
- Kode dibaca: customer_convert.py, contracts_engine.py, routers/contracts_router.py, deals_router.py, deal_cancel.py, cancellation_engine.py, lead_lifecycle.py, leads_router.py, customers_router.py, customer_hub_router.py, payment_scheme_engine.py, finance_engine.create_ar_for_deal, sales_reserve.py, quotation_engine.convert, docgen.py, documents_router.py, engine_sweepers.py, denorm.py, kpr_engine.py, ConvertToCustomerDialog.js, LeadUnitsTab.js, DealsListTab.js, DealLegalDialog.js, CostsDialog.js, FinancingDialogs.js.

---------------------------------------------------------------------------------------------------
## TEMUAN (urut severity)

### [KT-01] [Severity: Kritis] Jalur legal lama `/deals/{id}/ppjb` + `/ajb` menjual unit tanpa pembayaran dan melewati semua gerbang kontrak
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `backend/routers/deals_router.py:506-534` (`sign_ppjb`, izin hanya `deals:update`) dan `:537-564` (`sign_ajb`); UI: Deal & Unit › tab Deal › baris › tombol "Legal" (`frontend/src/components/sales/DealLegalDialog.js:60-80,150-165`, dipasang di `DealsListTab.js:179-184`).
- Reproduksi: login sales@sipro.co.id → lead baru → reservasi A-04 skema cash keras (Rp 850 jt) → finance bayar booking fee Rp 5 jt → sales "Konfirmasi Booking" → "Jadikan Pembeli" (kontrak KTR/2026/0007). `POST /api/contracts/{id}/legal/ppjb` (manager) → 400 "DP Rp 680.000.000 belum terbayar" (gerbang benar). Lalu sebagai SALES `POST /api/deals/{id}/ppjb {}` → 200, `POST /api/deals/{id}/ajb {"notary":"…"}` → 200 (probe `t1.py`). UI sama: sales buka "Legal" pada deal C-04 → "Tandatangani AJB" → toast "AJB ditandatangani — unit SOLD", dialog menunjukkan Pembayaran Rp 5.000.000 / Rp 720.000.000 (1%).
- Hasil nyata: deal `completed`, unit `sold` (+`sold_by_deal`), nomor AJB terbit; kontrak tetap `state=draft`, `legal_stage=belum`, `legal={}`; AR `partial` outstanding Rp 845 jt; lead `won`; layar Unit menampilkan "Terjual (lunas/akad)" + Bayar "Sebagian". Hasil seharusnya: PPJB butuh DP terbayar, AJB butuh pelunasan+BAST (skema tunai) / akad (KPR), dan hanya manajer (`contracts:manage`).
- Dampak: unit bisa dinyatakan terjual oleh sales tanpa uang; laporan penjualan/stok, pengakuan pendapatan dan serah terima membaca status palsu; pemisahan tugas ("tahap legal wewenang manajer") bisa dilompati. Dua sumber kebenaran legal (deals.legal_stage vs contracts.legal) saling bertentangan.
- Akar masalah: jalur pra-Fase-53 tidak dihapus/diarahkan ke `contracts_engine.legal_advance`; tidak ada gerbang DP/pelunasan/izin. Saran: matikan kedua endpoint (atau jadikan pembungkus tipis `legal_advance`), dan sembunyikan tombol Legal lama.
- Screenshot: `img/kontrak/ui5-legal-dialog-before-ajb.png`, `ui5-legal-dialog-after-ajb.png`, `ui5-unit-list-A04-terjual-sebagian.png`, `ui7-legacyAJB-contract-tab.png`.

### [KT-02] [Severity: Tinggi] Konversi paralel (klik ganda/dua tab/dua request): HTTP 500, customer ganda/yatim, nomor kontrak hangus
- Label bukti: [TERBUKTI-API] (UI tidak terpengaruh dobel-klik biasa: lihat Terverifikasi OK)
- Lokasi: `backend/customer_convert.py:228-231` (cek kontrak lalu insert, tidak atomik), `:260-300` (cari-lalu-insert customer; tidak ada index unik `lead_id`/`phone`), `:303` → `contracts_engine.py:359-392` (nomor `seq.next_number` diambil sebelum `insert_one`; index `uq_contract_deal` menolak yang kedua → `DuplicateKeyError` tidak ditangkap).
- Reproduksi: `POST /api/deals/{id}/convert` ×4 serentak (probe `t25.py`) pada deal booked baru: respons [500, 200, 500, 200]. DB: 2 baris `customers` untuk satu lead & satu telepon (`974fd3ec` terhubung kontrak KTR/2026/0014, `4e62de11` yatim tanpa kontrak). Dengan NIK diketik (`f5.py`) customer tunggal tapi 2 dari 3 request tetap 500. Nomor kontrak melompat (0004 → 0007; 0014 → 0017) karena nomor terpakai di request yang gagal. Log backend: `DuplicateKeyError … uq_contract_deal`.
- Hasil seharusnya: semua permintaan sama-deal mengembalikan kontrak & customer yang sama (idempoten), tanpa 500, tanpa customer kembar, tanpa lubang nomor.
- Dampak: customer kembar untuk satu orang (KYC/portal/tagihan terpecah), customer yatim tanpa kontrak, nomor kontrak berlubang (audit trail legal), pesan "Internal Server Error" generik.
- Akar masalah: urutan "cek lalu tulis" tanpa kunci; DuplicateKeyError kontrak tidak ditangani; nomor diambil sebelum insert. Saran: jadikan `convert` di bawah kunci per-deal (findOneAndUpdate/`$setOnInsert` pada kontrak, atau lock dokumen), tangkap DuplicateKeyError kontrak → kembalikan yang ada, ambil nomor kontrak setelah klaim, index unik parsial `customers(org_id, lead_id)`.
- Screenshot: `img/kontrak/ui8-customers-duplicate-race.png`.

### [KT-03] [Severity: Tinggi] Mengisi komponen biaya kontrak (tugas bawaan konversi) membuat SPR tidak mungkin ditandatangani (deadlock)
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI] (kotak "JANGAN tandatangani")
- Lokasi: `customer_convert.py:342-347` (membuat tugas "Isi komponen biaya kontrak … BPHTB, notaris"), `contracts_engine.py:612-643` (`set_costs` menulis `costs.bphtb/notary_fee/pph_seller`), `contracts_engine.py:407-411` + `allin_engine.issue_cost_invoice` (hanya tagih bila ada `costs.components` dari skema all-in), `routers/documents_router.py:165-169` + `spr_compare.py:184-196` (blokir tanda tangan bila SPR ≠ Finance).
- Reproduksi (probe `c1,c2,c5,c6,c7`): finance `POST /contracts/{id}/costs {"bphtb":42500000,"notary_fee":15000000,"pph_seller":21250000}` → 200. Sales terbitkan SPR_CASH_STAGED, finalize, lalu manager `POST /documents/{id}/sign {"role":"buyer",…}` → 400 "SPR … berbeda dengan tagihan Finance pada 5 baris (Biaya · BPHTB, Biaya · Biaya notaris / akad, Biaya · PPh penjual…). Terbitkan ulang SPR dari kontrak". Terbit ulang (0002) → tetap 400. `POST /contracts/{id}/cost-invoices` (finance) → 400 "Tidak ada komponen biaya yang ditagih ke pembeli…" sehingga Finance tidak bisa menyamakan. Panel kontrak: "5 baris BERBEDA — JANGAN tandatangani … TOTAL dibayar pembeli SPR Rp 928.750.000 vs FINANCE Rp 850.000.000".
- Hasil seharusnya: biaya yang diisi di kontrak ikut menjadi tagihan Finance, atau layar melarang mengisi biaya manual untuk kontrak tanpa skema all-in.
- Dampak: kontrak baru (tanpa skema all-in) yang mengikuti instruksi sistem tidak pernah bisa menandatangani SPR; jalan keluar hanya mengosongkan biaya (SPR menulis "belum ditetapkan") atau memilih all-in saat reservasi. Beberapa SPR draft menumpuk.
- Akar masalah: dua model biaya (field legacy `costs.*` vs snapshot `costs.components`); `set_costs` tidak menerbitkan/menyelaraskan invoice biaya. Saran: `set_costs` pada kontrak non-all-in harus memanggil jalur legacy (`legacy_components`) + `issue_cost_invoice`, atau tombol "Komponen biaya" disembunyikan dan tugas bawaan diganti "pilih skema all-in".
- Screenshot: `img/kontrak/ui7-spr-compare-mismatch.png`.

### [KT-04] [Severity: Sedang] SPR: total pembeli memuat PPh penjual (pajak keluar) dan baris SPR tidak menjumlah ke total tercetak
- Label bukti: [TERBUKTI-API] (teks SPR 0001/SPR-CASHB/CAA/XI/2026 via `GET /documents/{id}`)
- Lokasi: `contracts_engine.py:235-262` (`costs_total` menjumlah semua baris `biaya` kecuali developer_borne → ikut `PPH_SELLER` ber-`finance_treatment=tax_out`; `total_bill = nett + costs_total`), `docgen.py:495`. Padahal `docgen.buyer_incomplete_labels` (docgen.py:~320) menyatakan PPh penjual "bukan urusan total pembeli".
- Reproduksi: set biaya BPHTB 42,5 jt, notaris 15 jt, PPh 21,25 jt (booking fee 5 jt). SPR mencetak berurutan: Harga 850.000.000; Booking fee 5.000.000; BPHTB 42.500.000; notaris 15.000.000; PPh penjual 21.250.000; **Sub Total 928.750.000** (tidak termasuk booking fee: penjumlahan baris = 933.750.000); Promo −50.000.000; **Total 878.750.000**.
- Dampak: pembeli diminta total yang memuat pajak penjual; angka dokumen legal tidak "foot".
- Akar masalah: `tax_out` tidak dikecualikan; booking fee dicetak sebagai baris tapi tidak dijumlah. Saran: kecualikan `tax_out` dari `total_bill`, cetak booking fee sebagai catatan terpisah.

### [KT-05] [Severity: Tinggi] `POST /contracts/{id}/scheme` mengubah jenis kontrak tanpa menyelaraskan deal/AR/KPR → tidak ada SPR yang bisa diterbitkan
- Label bukti: [TERBUKTI-API]
- Lokasi: `contracts_engine.py:646-675` (`set_scheme`: hanya set `contract.scheme`; `create_ar_for_deal` tanpa `replace`/`scheme_id`; tidak memanggil `ensure_kpr_app`; tidak menghormati `deals.scheme_explicit` yang dijaga `customer_convert.py:249-256`), `routers/contracts_router.py:157-167` (izin `contracts:update` = finance).
- Reproduksi (`t16.py`): kontrak KTR/2026/0011 (deal cash keras eksplisit) → finance `POST …/scheme {"scheme":"kpr"}` → 200. Sesudah itu: `contract.scheme=kpr` tetapi `payment_scheme_name` & AR tetap "Cash keras (DP 80%…)", `deal.scheme_id` tetap cash keras, tidak ada `financing_apps`; `activate` tidak merapikan. `GET …/documents/available`: SPR_CASH, SPR_CASH_STAGED, SPR_KPR semua `can_generate=false` (kontrak KPR vs deal cash → blok `skema_deal_beda`); `contract-pricing.sync` = "Kontrak berskema KPR sedangkan reservasi memilih Cash keras".
- Dampak: kontrak buntu (tak ada SPR, gerbang akad kredit tanpa aplikasi KPR), AR/legal/dokumen beda jenis.
- Akar masalah: dua jalur penggantian skema (`set_scheme` vs `payment_scheme_engine.set_for_contract`) dengan aturan berbeda. Saran: `set_scheme` memanggil `set_for_contract` + `_repoint_deal_scheme` atau ditolak bila deal eksplisit.

### [KT-06] [Severity: Tinggi] Re-aktivasi kontrak / regenerasi jadwal mengalokasikan ulang pembayaran (FIFO) → kuitansi ≠ AR
- Label bukti: [TERBUKTI-API]
- Lokasi: `contracts_engine.py:678-707` (`activate` tanpa guard state; boleh berkali-kali, juga pada kontrak `completed`/`cancelled`), `finance_engine.py:354-361` (alokasi ulang `_allocate(items, carried_paid)` mengabaikan `targets` kuitansi), `routers/ar_router.py:165-181`.
- Reproduksi (`c9.py`): AR 3 termin; finance bayar Rp 100 jt dengan alokasi eksplisit ke "Termin 40%" (`KWT/2026/0006`, allocations → Termin 40%). Panggil `POST /contracts/{id}/activate` lagi → 200. AR kini: DP 30% dibayar 105 jt, Termin 40% 0; sementara kuitansi tetap menyebut alokasi Termin 40% 100 jt. Event `ar.schedule_created` + notifikasi finance terbit ulang tiap klik.
- Dampak: laporan umur piutang/tunggakan per termin salah; pembeli ditagih ulang termin yang ia bayar; pemicu tahap legal (DP terbayar) bisa berubah.
- Akar masalah: `replace=True` membangun ulang item dan memutar ulang FIFO; `activate` tidak idempoten. Saran: tolak `activate` bila sudah `active`; saat replace pertahankan alokasi per kuitansi.

### [KT-07] [Severity: Tinggi] `POST /finance/ar/{deal_id}/schedule` pada deal BATAL menghidupkan piutang hantu
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/ar_router.py:165-181` + `finance_engine.py:319-333` (`create_ar_for_deal` tanpa pemeriksaan `deal.status`).
- Reproduksi (`t20.py`): lead "AUDIT-Live Gate", unit C-03 reserved → dibatalkan (`/deals/{id}/cancel` 200, AR dibatalkan). Finance `POST /api/finance/ar/{deal}/schedule {"scheme_id":…}` → 200, AR kini `unpaid`, total Rp 1.550.000.000 outstanding Rp 1.550.000.000 untuk deal `cancelled` dengan unit `available`; tampil di `GET /finance/ar`.
- Dampak: piutang & pajak tercatat (tax_records dibuat ulang) atas unit yang sudah dilepas; laporan AR menggelembung.
- Saran: tolak bila deal bukan `booked/completed`.

### [KT-08] [Severity: Tinggi] Kupon kuota 1 terpakai dua kali; satu request 500 tetapi deal-nya tetap ada dengan diskon
- Label bukti: [TERBUKTI-API]
- Lokasi: `deals_router.py:279-306` (deal dibuat di `sr.reserve` baris 280 dulu; `pe.redeem_coupon` baris 302 sesudahnya; `ValueError` kuota tidak ditangkap) dan `quotation_engine.py:593-598` (pola sama).
- Reproduksi (`t18.py`): kupon `AUDIT-ONCE` (quota_total=1). Dua lead reservasi serentak di unit berbeda: satu 500 "Internal Server Error", satu 200. DB: `used_count=1/1`, `coupon_redemptions=1`, tetapi **dua deal** (C-05 dan C-06) sama-sama `discount=3.000.000` dan harga dipotong; deal yang 500 tidak punya penebusan.
- Dampak: diskon kupon melebihi kuota, unit terkunci oleh request yang tampak gagal, sales mencoba ulang dan terbentur 409 unit sendiri.
- Akar masalah: efek samping kupon setelah reservasi tanpa rollback. Saran: tebus kupon (atomik) sebelum/di dalam reservasi, dan batalkan deal bila gagal.

### [KT-09] [Severity: Tinggi] Sales membaca kontrak/harga/AR/NIK milik sales lain lewat `/customers/{id}/…`
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `routers/customer_hub_router.py:136-144` (`contract-pricing`), `:198-212` (`units-construction`), `routers/customers_router.py:147-150,153-252` (detail & timeline) — tidak memakai `is_scoped_sales`; bandingkan `contracts_router.py:42-54` yang benar.
- Reproduksi (`t9.py`,`t10.py`): kontrak KTR/2026/0004 milik sales@. Login sales2@: `GET /contracts/{id}` → 403, `GET /contracts?customer_id=` → "di luar lingkup data Anda", tetapi `GET /customers/{cid}/contract-pricing` → 200 dengan nomor kontrak, harga Rp 850 jt, AR total/terbayar, dan komponen biaya; `GET /customers/{cid}` → NIK, alamat; `…/timeline` → 31 baris; `GET /customers` → 16 pembeli semua sales.
- Dampak: kebocoran harga/komisi/KYC antar-sales; kontradiksi dengan janji "hanya miliknya".
- Saran: terapkan scoping (assigned_to deal/kontrak) pada seluruh endpoint customer; atau putuskan eksplisit customer tidak ber-scope dan sembunyikan harga/AR.
- Screenshot: `img/kontrak/ui8-sales2-sees-other-sales-contract.png`.

### [KT-10] [Severity: Tinggi] Konfigurasi `payment.staged.*` / `payment.cash.*` diabaikan oleh skema bawaan; teks jatuh tempo di SPR salah
- Label bukti: [TERBUKTI-API] (nilai config + isi `payment_schemes` + SPR)
- Lokasi: `contracts_engine.py:310-324` (`_builtin_spec` menyusun "tanggal 7 tiap bulan · toleransi s/d tanggal 20", `event: True`, offset), `contracts_engine.py:336-355` → `payment_scheme_engine.py:74-96` (`normalize_terms` MENIMPA `due_rule` dari `due_mode` yang tidak ada, `event = (due_mode=="event")` = False).
- Reproduksi: `GET /settings/effective` → `payment.staged.due_day=7`, `grace_day=20`, `payment.cash.payoff_days_after_completion=30`, `payoff_grace_days=7`. Skema tersimpan otomatis (`source=DOC, created_by=system`): "Cash keras — Pelunasan 20% — **180 hari setelah kontrak diaktifkan**, event=False"; "Cash bertahap — Cicilan n/6 — **30n hari setelah kontrak diaktifkan**" (bukan tanggal 7/toleransi 20; pelunasan bukan "30 hari sejak bangunan 100%"). Teks ini tercetak di SPR (mis. `Cicilan 1/6 : 22.833.105 — jatuh tempo 2026-12-05`).
- Dampak: dokumen yang ditandatangani pembeli memuat aturan bayar yang tidak sama dengan kebijakan owner; tolok keterlambatan/denda memakai tanggal salah.
- Saran: lewatkan `due_mode/due_day/month_index/event_code/grace_days` dari `_builtin_spec` ke baris sebelum `normalize_terms`.

### [KT-11] [Severity: Sedang] Jatuh tempo termin dihitung dari tanggal booking, bukan dari aktivasi kontrak, padahal teksnya "setelah kontrak diaktifkan"
- Label bukti: [TERBUKTI-API]
- Lokasi: `finance_engine.py:333` (`base_date = booked_at or reserved_at`), `:109-148`, `contracts_engine.py:694` (`activate` memakai ulang `create_ar_for_deal` → basis tetap `booked_at`).
- Reproduksi (`c8.py`): booking 19:15:46, aktivasi 19:19:31. Item AR `due_date` = booking + offset persis (`…T19:15:46`; DP "saat kontrak diaktifkan" jatuh tempo pada hari booking, sebelum kontrak/SPR ada). Kalimat aturan di AR/SPR: "45 hari setelah kontrak diaktifkan".
- Dampak: bila aktivasi terjadi berhari-hari sesudah booking, tanggal tertulis ≠ janji; DP sudah "jatuh tempo" sebelum SPR terbit.
- Saran: basis tanggal = `activated_at` (atau ubah kalimat menjadi "setelah booking").

### [KT-12] [Severity: Tinggi] Pembatalan deal `booked` yang baru membayar booking fee buntu (pesan saling merujuk)
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `deal_cancel.py:33-48` (`ar_paid = ar.paid` ikut menghitung booking fee yang otomatis dialihkan ke termin → blokir "Sudah ada pembayaran termin"), `cancellation_engine.py:146-153` (blokir `kontrak_belum_ada`: "Pembatalan reservasi/booking dilakukan dari daftar deal").
- Reproduksi (`t2.py`, UI `ui6.js`): deal booked, hanya booking fee Rp 5 jt (preview sendiri: refundable 5 jt, `ar_paid` 5 jt). `POST /deals/{id}/cancel` oleh sales dan manager → 400 "Sudah ada pembayaran termin (DP/cicilan)… Gunakan Pembatalan Kontrak formal di Kontrak & Legal". Pembatalan formal butuh kontrak (belum ada) dan menyuruh kembali ke daftar deal. Satu-satunya jalan keluar: "Jadikan Pembeli" dulu lalu ajukan pembatalan (`/cancellations`, diputuskan owner; finance 403). Tombol "Batalkan Reservasi" tetap tampil untuk deal booked.
- Dampak: unit booked tidak dapat dilepas untuk calon yang belum bayar apa pun selain booking fee, kecuali dipaksa menjadi customer+kontrak dulu (menambah data kotor); lalu potongan 35% diterapkan pada booking fee (refund Rp 3,25 jt dari 5 jt).
- Saran: hitung `ar_paid` tanpa dana asal booking fee/titipan; atau izinkan pembatalan formal untuk deal tanpa kontrak.
- Screenshot: `img/kontrak/ui6-cancel-dialog-booked.png`.

### [KT-13] [Severity: Tinggi] Lead langsung `won` saat konversi (Rp 5 jt dari 850 jt), UI menulis "akad/AJB selesai", skor 100; pembatalan → `lost`
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `customer_convert.py:325-333` (memanggil `lc.record(lead,"won")` langsung, melewati `lead_lifecycle.requirements["won"]` yang menuntut AJB/serah terima); `lead_lifecycle.py:29,41`; skor `lead_scoring` (+40 "Tahap: Menang"); `cancellation_engine` (lead dipaksa `lost`).
- Reproduksi: konversi deal booked (`f5.py`): `stage_history` = booking → won (source=deal). Profil lead menulis "Lead sudah menang (akad/AJB selesai)", skor 100/Hot. Ajukan pembatalan formal (`t3.py`) → lead `lost`; `won` tidak punya jalan keluar manual (`MANUAL_FLOW["won"]=[]`).
- Dampak: funnel/atribusi/komisi/CAPI menghitung "menang" pada booking+KYC; pesan UI keliru; lead `won→lost` menyalahi grafik tahap.
- Saran: konversi menghasilkan status "pembeli" terpisah; `won` tetap dari AJB; atau ubah label.
- Screenshot: `img/kontrak/ui1-lead-after-convert.png`.

### [KT-14] [Severity: Sedang] Pemicu konfigurasi `ppjb_signed`/`ajb_signed` tidak pernah mengonversi; default `spr_signed` tak terjangkau
- Label bukti: [TERBUKTI-API] (ppjb) + [DARI-KODE] (ajb, spr)
- Lokasi: `reference_p100.py:7-15` (opsi), `engine.py:526-538` (hanya `deal.booked` dan `document.signed` SPR), `customer_convert.py:48,367-383`; `routers/documents_router.py:79-87` (SPR generik ditutup → SPR hanya lahir dari kontrak yang butuh customer).
- Reproduksi (`t22.py`): set `lead.won_trigger=ppjb_signed`; booking lalu `POST /deals/{id}/ppjb` → deal `legal_stage=ppjb` tetapi `contract_id/customer_id=None`. `booking_fee_verified` berfungsi (konversi otomatis, lead won).
- Dampak: dua dari empat opsi konfigurasi tidak berfungsi; default (SPR ditandatangani) mustahil karena SPR membutuhkan kontrak (customer) lebih dulu → satu-satunya jalan tetap tombol manual.
- Saran: sambungkan event `deal.ppjb`/`deal.ajb` atau hapus opsi; jelaskan SPR-dulu-vs-kontrak-dulu.

### [KT-15] [Severity: Sedang] Edit kontak setelah konversi tidak tersinkron (lead ↔ customer ↔ deal ↔ unit ↔ kontrak ↔ WA)
- Label bukti: [TERBUKTI-API]
- Lokasi: `denorm.py:36-60` (peta "leads": hanya ar_invoices/appointments/surveys; "customers": hanya complaints/financing_apps — tidak ada deals.lead_name, units.lead_name, booking_fee_invoices.lead_name, contracts.customer_name, customers↔leads), `routers/leads_router.py:334-371` (hanya `contact_name` percakapan; telepon percakapan tidak), `routers/customers_router.py:302-312`.
- Reproduksi (`t8.py`,`t23.py`): ganti nama/telepon/email lead pasca-konversi → `customers.*` tidak berubah; `deals.lead_name`, `units.lead_name`, `booking_fee_invoices.lead_name` tetap nama lama sementara `ar_invoices.lead_name` berubah (tidak konsisten); `conversations.contact_phone` tetap nomor lama (WA keluar ke nomor lama). Ganti nama customer → `contracts.customer_name` lama; `GET /contracts?q=<nama baru>` = 0 hasil, `q=<nama lama>` = 1.
- Dampak: nama/telepon salah di dokumen turunan, pencarian kontrak gagal, WA terkirim ke nomor usang.
- Saran: sumber tunggal (customer sebagai master setelah konversi) + perluas DENORM_MAP.

### [KT-16] [Severity: Sedang] Reassign PIC lead tidak memindahkan deal/kontrak/AR/customer → PIC baru terkunci, PIC lama masih akses
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/leads_router.py:435-450` (hanya `leads.assigned_to`); scoping memakai `assigned_to` pada deals/contracts (`contracts_router.py:42,52`, `deals_router.py:125`).
- Reproduksi (`t9.py`): manager assign lead (sudah punya deal+kontrak) ke sales2. sales2: `GET /leads/{id}` 200, `GET /deals/{deal}` 403, `GET /contracts/{id}` 403, list deal lead = 0. sales (PIC lama): lead 403 tetapi deal & kontrak masih 200.
- Dampak: PIC baru tak bisa menangani transaksi; PIC lama tetap melihat/mengubah.
- Saran: cascade `assigned_to` ke deals/contracts/ar/booking_fee/customers/documents saat assign.

### [KT-17] [Severity: Sedang] Dedup & validasi customer lemah (telepon/email/NIK)
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/customers_router.py:119-137` (`create_customer` hanya cek NIK, tanpa telepon/email), `customer_convert.py:262-265,157-174` (NIK/NPWP/penghasilan dari payload tidak dinormalisasi/divalidasi; dedup hanya NIK exact & telepon exact; tidak ada email).
- Reproduksi (`t5.py`): `POST /customers` dua kali dengan telepon 0812-9900-0010/+6281299000010 dan email sama → 2 baris. Konversi dengan `nik:"3174-0101-0101-0077"` tersimpan apa adanya; `POST /customers` dengan NIK `3174010101010077` (dinormalisasi) lolos → NIK sama jadi dua customer (index unik terlewati). Konversi dengan `nik:"123"`, `npwp:"abc"`, `monthly_income:-5000` → 200 tersimpan. NIK yang diketik di dialog menautkan customer lama secara senyap (preview tidak memperhitungkannya), tanpa konfirmasi nama berbeda.
- Dampak: customer kembar; NIK tak valid; potensi merge dua orang berbeda tanpa peringatan.
- Saran: normalisasi+validasi (16 digit) di `convert`; dedup telepon/email di `create_customer`; tampilkan konfirmasi saat NIK mengenai customer lain.

### [KT-18] [Severity: Sedang] Batas `reservation.max_active_per_lead` dapat dilampaui (paralel & via penawaran)
- Label bukti: [TERBUKTI-API]
- Lokasi: `deals_router.py:166-179` (hitung lalu reservasi, tidak atomik; hanya di router), `quotation_engine.py:548-610` (docstring mengklaim aturan tetap di router, tetapi `sales_reserve.reserve` tidak memeriksa).
- Reproduksi (`t6.py`,`t27.py`): dua `POST /deals/reserve` serentak untuk satu lead di unit berbeda → keduanya 200 (lead memegang B-05 & B-06, batas 1); ketiga berurutan 409 (sehingga pemeriksaan hanya bocor di paralel). `POST /quotations/{id}/convert` untuk lead yang sudah menahan 1 unit → 200, lead memegang 2 unit.
- Saran: letakkan pemeriksaan di `sales_reserve.reserve` dengan penghitungan atomik.

### [KT-19] [Severity: Sedang] Gerbang tahap lead menganggap deal BATAL masih "live" (typo `canceled` vs `cancelled`)
- Label bukti: [TERBUKTI-API]
- Lokasi: `lead_lifecycle.py:57` (`not in ("canceled","expired","failed")`; status sebenarnya `cancelled` — `deal_cancel.py:108`).
- Reproduksi (`t20.py`): satu-satunya deal dibatalkan → lead mundur ke nurturing; `GET /leads/{id}/lifecycle` syarat booking "Ada SPR/reservasi unit (deal aktif)" = met; `POST /leads/{id}/stage {"stage":"booking"}` → 200 (lead `booking` tanpa deal hidup).
- Saran: samakan ejaan (gunakan satu konstanta status).

### [KT-20] [Severity: Sedang] Lead `lost`/`recycle` bisa memesan unit; stage lead tidak ikut, deal hidup pada lead `lost`
- Label bukti: [TERBUKTI-API]
- Lokasi: `deals_router.py:158-179` (tidak memeriksa stage), `lead_lifecycle.py:209-212` (`advance_on_deal(booking)` diam bila stage bukan acquisition/nurturing/appointment).
- Reproduksi (`t4.py`): lead yang tadinya dibatalkan formal (stage `lost`) → `POST /deals/reserve` 200, stage tetap `lost`; booking+konversi → stage `won` (lost→won tanpa jejak sah). Customer lama ditautkan ulang (baik).
- Saran: tolak/wajibkan alasan pada lead `lost/recycle`; atau naikkan stage secara eksplisit.

### [KT-21] [Severity: Sedang] Dialog "Jadikan Pembeli" mengunci skema default KPR dan menyebutnya "dipilih saat reservasi"
- Label bukti: [TERBUKTI-UI] + [TERBUKTI-API]
- Lokasi: `frontend/src/components/contracts/ConvertToCustomerDialog.js:125,136-141` (Select `disabled={!!pre?.deal_scheme}`), `customer_convert.py:62-69,249-256` (backend mengizinkan ganti bila `scheme_explicit=False`), `deals_router.py:288` (`scheme_explicit = bool(payload.scheme_id)`), default skema = "Standar KPR (DP 20%)" (`is_default`).
- Reproduksi (`t11.py`, `ui3.js`): reservasi tanpa memilih skema → `scheme_id=kpr_dp20`, `scheme_explicit=false`. Dialog menampilkan "KPR (Kredit Pemilikan Rumah)" **nonaktif** + "Mengikuti skema … yang dipilih saat reservasi: Standar KPR (DP 20%)". Konversi → kontrak KPR + pengajuan KPR kosong (KTR/2026/0012) untuk pembeli yang tak pernah memilih KPR.
- Dampak: pembeli tunai ikut ke kontrak KPR (SPR KPR terkena gerbang SLIK, tahap legal akad kredit).
- Saran: kunci hanya bila `scheme_explicit`; selain itu biarkan memilih.
- Screenshot: `img/kontrak/ui3-convert-dialog-default-kpr.png`.

### [KT-22] [Severity: Sedang] Biaya kontrak tanpa batas/persetujuan: potongan Rp 900 jt di atas harga Rp 850 jt diterima
- Label bukti: [TERBUKTI-API]
- Lokasi: `contracts_engine.py:612-643` (`set_costs`: tanpa validasi rentang untuk `promo_discount`, `dp_percent`, `plafon_kredit`; −1 = hapus), `contracts_engine.py:131-150` (`costs.promo_discount` menimpa `pricing.discount_amount`), `routers/contracts_router.py:140-154` (izin `contracts:update` termasuk finance; tak ada alur persetujuan `pricing:approve`), `frontend/.../CostsDialog.js:46-48` (`Number(raw.replace(/[^\d-]/g,""))`: "1.500.000,50" → 150000050; "-5" diam-diam berarti "kosongkan").
- Reproduksi (`c1.py`): `{"promo_discount":900000000}` → 200, `nett_price=-50.000.000`, `total_bill=28.750.000`; `{"dp_percent":150}` dan `{"plafon_kredit":99999999999}` (kontrak tunai) tersimpan; `{"bphtb":0}` = Rp 0 (bukan "belum diisi"). Potongan Rp 50 jt di kontrak muncul di SPR sementara AR tetap Rp 850 jt (mismatch, memblokir tanda tangan seperti KT-03) — memotong harga di luar workflow persetujuan diskon.
- Saran: validasi 0 ≤ promo ≤ harga, 0 ≤ dp% ≤ 100; jalankan lewat approval; larang `plafon_kredit` pada non-KPR.

### [KT-23] [Severity: Sedang] KPR: `POST /financing` menggandakan pengajuan & menimpa tampilan kontrak; plafon kontrak tak tersinkron
- Label bukti: [TERBUKTI-API] + [DARI-KODE] (dialog)
- Lokasi: `routers/financing_router.py:41-80` (tanpa cek app yang sudah ada, tanpa `contract_id`/`kpr_stage`), `kpr_engine.py:34-37,59-76` (`_kpr_app`/`kpr_of` ambil app TERBARU), `kpr_engine.py:84-100` (`plafon` diambil dari biaya kosong saat konversi; `set_costs` tidak menyinkronkan), `frontend/.../FinancingDialogs.js:62-69` (`setDeals(mine.length ? mine : all)` → bila tak ada deal lead, semua deal org (≤50) ditawarkan).
- Reproduksi (`t12.py`,`t19.py`): kontrak KPR KTR/2026/0012 punya app BTN (tahap `diajukan_ke_bank`). `set_costs plafon_kredit=1 M` → `financing_apps.plafon` tetap 0. Finance buat "Ajukan KPR" BNI → 2 app; `GET /contracts/{id}/kpr` kini menampilkan app BNI, `stage=None`, tahap selesai [] (progres BTN hilang dari layar); `POST …/kpr/stage/diajukan_ke_bank` → 400 "Tahap sebelumnya belum selesai: Berkas lengkap".
- Saran: satu app per deal (index unik/guard), tautkan ke kontrak, sinkronkan plafon.

### [KT-24] [Severity: Sedang] PPJB/tahap legal kontrak paralel → nomor ganda, riwayat ganda, tugas ganda; tanda tangan & SPR ganda
- Label bukti: [TERBUKTI-API]
- Lokasi: `contracts_engine.py:711-811` (`legal_advance`: cek lalu tulis; nomor `seq.next_number` per panggilan; `$push legal_history`; tugas AJB), `routers/documents_router.py:159-189` (tanda tangan tanpa dedup), `docgen.py:664-690` (`generate` tidak menggantikan SPR lama).
- Reproduksi: dua `POST /contracts/{id}/legal/ppjb` serentak (`t13.py`) → keduanya 200 (nomor PPJB/2026/0003), `legal_history` berisi PPJB/2026/0002 **dan** 0003, 2 tugas "Jadwalkan AJB". `sign` dua kali oleh peran/nama sama → `signatures` = 2 entri identik; dua SPR_CASH untuk satu kontrak sama-sama `signed` (`t28.py`); `GET /documents` `counts.final=0` padahal dokumen `finalized` (kunci ≠ nilai status, `documents_router.py:60`).
- Saran: guard atomik per tahap (`update_one` dengan kondisi `legal.<stage>` tidak ada), supersede SPR lama, dedup penanda tangan.

### [KT-25] [Severity: Sedang] Sweeper kedaluwarsa reservasi meninggalkan sisa tautan, lead tetap `booking`, kupon tak dilepas
- Label bukti: [DARI-KODE] (fungsi dijalankan di DB scratch terisolasi, lihat catatan alat)
- Lokasi: `engine_sweepers.py:15-26`.
- Hasil harness: deal → `expired`; unit → `available` TETAPI `reserved_by_deal/deal_id/lead_id/lead_name/payment_status=booking_fee` masih terisi; lead tetap `booking`; `coupon_redemptions.state=used`, `used_count` tetap; tugas "Konfirmasi booking fee" tetap `open`. Bandingkan `deal_cancel._release_unit` yang membersihkan semuanya. Ini varian lain dari "tautan basi" milik catatan repo.
- Saran: pakai satu rutin pelepasan (`deal_cancel._release_unit` + `release_coupon` + tutup tugas + mundurkan lead).

### [KT-26] [Severity: Rendah] `GET /deals/{id}/delete-check` tidak punya dekorator route → 404; UI menulis "Tidak bisa dihapus: Not Found"
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `deals_router.py:364-365` (fungsi `deal_delete_check` tanpa `@router.get`, menempel sesudah `return` `decide_pricing`); dipakai `DealsListTab.js:193`.
- Reproduksi: owner `GET /api/deals/{id}/delete-check` → 404; UI owner klik hapus deal → dialog "Hapus deal C-03? … Tidak bisa dihapus: Not Found" (menyesatkan; "Hapus paksa" tetap muncul).
- Screenshot: `img/kontrak/ui6-delete-deal-owner.png`.

### [KT-27] [Severity: Rendah] Daftar kontrak untuk sales: `total` = jumlah baris halaman; `counts` org-wide bocor
- Label bukti: [TERBUKTI-API]
- Lokasi: `routers/contracts_router.py:93-117` (filter `assigned_to` setelah paginasi; `out["total"]=len(milik)`; `counts` tidak difilter).
- Reproduksi (`t14.py`): sales `limit=3` → `total=3` (sebenarnya 10), skip=3 → 3 baris; sales2 (0 kontrak) melihat `counts` {draft:8,active:1,cancelled:1} dan pesan "10 kontrak tidak ditampilkan".

### [KT-28] [Severity: Rendah] `POST /leads/import` (JSON) tanpa normalisasi telepon & dedup
- Label bukti: [TERBUKTI-API]
- Lokasi: `leads_router.py:218-240` (bandingkan `create_lead:175-182`). Reproduksi (`t7.py`): impor `"0812 9900 0031"` tersimpan mentah; `POST /leads` nomor sama (`081299000031`) → 200 (dua lead untuk satu nomor; customer hasil konversi juga bisa bernomor mentah dan lolos dedup telepon). UI memakai `/leads/import-file` (tidak diuji).

### [KT-29] [Severity: Rendah] Tugas & agenda tidak ditutup setelah booking/konversi
- Label bukti: [TERBUKTI-API]
- Lokasi: `sales_reserve.py` (tugas `deal.bookingfee`), `deals_router.py:404-436` (`book_deal` tidak menutup tugas), `customer_convert.py` (tidak menutup tugas lead). Reproduksi (`q2.py`): setelah booking+konversi, tugas "Konfirmasi booking fee … / unit A-03", "Follow-up lead", "Survey/janji temu" tetap `open` dan agenda survei `scheduled`.

### [KT-30] [Severity: Rendah] Field lead tidak terbawa ke customer; tidak ada tautan balik lead↔customer
- Label bukti: [TERBUKTI-API] + [TERBUKTI-UI]
- Lokasi: `customer_convert.py:277-285` (hanya name/phone/email/source/assigned_to), `ConvertToCustomerDialog.js:58-64` mengirim `note` yang diabaikan backend (`customer_convert.py` tidak membaca `note`).
- Hasil: `notes`, `campaign`, `interest_unit_type`, `partner_id` (dasar fee mitra), skor, tidak ada di customer; `leads` tidak punya `customer_id`/`converted_at`; profil lead tidak punya tautan ke customer (hanya dari tombol saat konversi) dan sebaliknya. Dokumen lead terverifikasi diwarisi (tidak diuji dengan data).
- Screenshot: `img/kontrak/ui2-cust-summary.png`.

---------------------------------------------------------------------------------------------------
## Terverifikasi OK
- Hold unit atomik: dua lead memesan unit sama serentak → satu 200, satu 409 (`t6.py`); `sales_reserve.reserve` memakai `find_one_and_update` kondisi `status=available`.
- Booking: konversi/booking sebelum booking fee lunas ditolak dengan alasan jelas (400); `book` menolak booking fee belum lunas.
- Konversi idempoten sekuensial: panggilan ulang mengembalikan kontrak yang sama; lead yang sama dengan deal kedua menaut ke customer yang sama (`lead_ids`).
- Gerbang PPJB di jalur kontrak benar (DP harus terbayar); pemisahan tugas legal (sales 403, manager OK).
- SPR vs tagihan Finance: sistem memblokir tanda tangan bila angka beda (perilaku benar; masalahnya di KT-03/22).
- Pembulatan termin: 6× cicilan atas harga 685 jt dan 850 jt menjumlah tepat harga (sisa dibebankan ke cicilan terakhir; Rp 22.833.105 ×5 + 22.834.475); skema `monthly_day` menolak tanggal >28.
- SPR tanpa placeholder `None/undefined/{{…}}`; data kosong ditulis "belum ditetapkan".
- Klik ganda UI pada "Jadikan Pembeli": hanya 1 request POST, 1 customer, 1 kontrak (`ui4.js`).
- Normalisasi telepon lead E.164 dan 409 pada nomor ganda pada pembuatan lead; tiga POST /leads paralel menghasilkan 1 lead.
- Pembatalan formal: pengaju (manager) ≠ pemutus (finance 403 / owner OK); unit kembali ke stok dengan seluruh tautan dibersihkan; lead ikut `lost`. Pembatalan reservasi (belum booking) satu klik: unit tersedia, AR/BF ditutup, lead → nurturing.
- Scoping langsung `/deals/{id}`, `/contracts/{id}`, `/deals/{id}/convert` untuk sales lain: 403.

## Tidak bisa diverifikasi
- Sweeper kedaluwarsa pada server hidup (hanya via harness DB scratch; `hold_days` min 1 hari, sweeper tiap 300 dtk).
- Alur KPR penuh sampai SP3K → akad → pencairan, amandemen all-in (`allin_amend.py`), BAST/serah terima, dan pembukuan/jurnal angka kontrak (domain stream lain).
- Pewarisan dokumen lead→customer (`_inherit_documents`) dengan berkas terverifikasi nyata; impor Excel `/leads/import-file`; kegagalan parsial `convert` setelah customer terbuat (tidak ada input yang bisa memaksa error di langkah akhir selain race KT-02).
- Perilaku tombol Back/refresh di tengah dialog (hanya klik ganda yang diuji); pemicu `ajb_signed` (hanya dari kode).
- Duplikasi percakapan WA per telepon (kode `leads_lifecycle_router.py:152-163` mencari percakapan per `lead_id`, inbound per `contact_phone` → berpotensi dua percakapan; tidak direproduksi karena jendela 24 jam WA tertutup pada mode simulasi).

## Pertanyaan terbuka
1. Apakah jalur legal lama (`/deals/{id}/ppjb|ajb`, dialog "Legal") memang masih dimaksudkan? Bila ya, harus lewat gerbang yang sama dengan kontrak.
2. Apakah `won` memang dimaksudkan lahir saat konversi (booking) — atau tetap saat AJB? Dua dokumen repo mengatakan hal berbeda.
3. Apakah daftar/detail Customer sengaja tidak ber-scope per sales? Bila ya, endpoint `contract-pricing` seharusnya menyembunyikan harga/AR.
4. Apakah PPh penjual (`tax_out`) boleh masuk "total ditagihkan ke pembeli"?
5. Apakah DP "saat kontrak diaktifkan" memang harus jatuh tempo pada hari booking?
