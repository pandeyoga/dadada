# TRIASE 76 SKRIP "TIDAK TAHU" — T-05 sesi 4 (2026-09-05)

Sumber: `memory/TRIASE_KORPUS_2026-09.md` (76 baris **TIDAK TAHU**). Dijalankan ulang dua kali di seed bersih
(`coverage_data/corpus_tt_2026-09-05.json` = ringkas; log penuh per skrip di `coverage_data/tt_logs/*.log`, di-.gitignore),
lalu galat pertamanya **dibaca satu per satu**. Setiap baris kini punya vonis + bukti — tidak ada lagi TIDAK TAHU.

## Ringkasan
| Vonis | Jumlah | Arti |
|---|---|---|
| **LULUS** | 6 | rc=0 di seed bersih (audit_temuan, e7_interco, p0, sampling, fase_c_lot*, config_clear_layer*) |
| **BUG DIPERBAIKI** | 1 | `test_fase_c_lot_poc` — pagar lot 400 SESUDAH klaim saga → kunci tertinggal → GR ulang 409 (lihat §Bug) |
| **BASI → DIBETULKAN** | 9 | asersi lama dibetulkan di sesi ini, kini hijau (role_access, f6_retirement, ps21, iter292, notifications_addressing, audit_findings D1, verifikasi_sesi D1, fase_f_us3 (label qc_*), run_corpus mode config_clear_layer) |
| **ASERSI BASI (dipertahankan, ≥70%)** | 19 | aturan/seed berevolusi; sinyal uji sisanya masih berguna |
| **UJI BASI (premis berubah)** | 12 | gerbang baru (approval manajer, verifikasi kelengkapan, SoD, KEB-PDPT, alur interco lewat gudang) — kandidat hapus/tulis ulang |
| **LINGKUNGAN** | 27 | residu urutan korpus (entitas uji "PT Uji Provisioning", harga Kanda di-expire test_f1a, roll/jurnal residu), prasyarat seed (device RFID, pengiriman sopir), ingress (WS, 502) |
| **REGISTRY GAP (P2)** | 2 | `test_core_e0_isolation` L15 & `test_g0_config` — data lahir dari POC lain tetapi menyingkap registry belum lengkap |

(*) `fase_c_lot` lulus sesudah bug diperbaiki; `config_clear_layer` = skrip asyncio (rc=5 "no tests ran" di mode pytest) → `run_corpus.DIRECT_IN_TESTS`, lulus langsung.

## Bug nyata yang ditemukan korpus (diperbaiki)
`backend/routers/inbound_receiving.py` `complete_inbound_receiving`: pagar lot D-27 mode `block` (400) berada **di bawah**
`_saga.claim()` → GR pertama ditolak 400 tetapi `saga_lock` tertinggal → GR ulang yang sudah lengkap ditolak
`409 SAGA_IN_PROGRESS`. Pagar dipindah ke atas klaim. Guard INV-ATOMIC-01 kini punya aturan baru: **validasi 4xx sesudah
klaim = MERAH** (`validation_after_claim`, self-test 2 kasus) — kelas bug ini tidak bisa kembali diam-diam.

## Vonis per skrip
| Skrip | Hasil | Vonis | Bukti (galat pertama, dibaca) |
|---|---|---|---|
| `tests/test_audit_findings_reproduction.py` | 5/6→6/6 | BASI→DIBETULKAN | `manager` kini ∈ `BOARD_ROLES` (papan PO custom wajib sejak 2026-06) → payload tanpa papan memang dituduh |
| `tests/test_config_clear_layer.py` | rc=5→LULUS | LULUS (mode) | skrip asyncio `main()`, bukan pytest → `DIRECT_IN_TESTS` |
| `tests/test_f0b_entity_scoping.py` | 90/91 | ASERSI BASI | kas_besar kini ter-scope per PT (10/2/12) — asersi "sama di semua konteks" lama |
| `tests/test_f0cdef_multientity.py` | 57/64 | ASERSI BASI | membaca `entity_id`/`ownerEntity`; roll/saldo/mutasi memakai `owner_entity_id` (row entity=None ≠ bocor) |
| `tests/test_f1a_pricelist.py` | 13/16 | ASERSI BASI | harga efektif kini melewati lapisan tambahan (217.628,99 vs 199.000 mentah) |
| `tests/test_f1b_product_templates.py` | 7/20 | UJI BASI | wajib jenis kain + GSM stage Finished (FASE T) — 65% gagal, kandidat tulis ulang |
| `tests/test_fb01_ai_illustration.py` | 6/13 | LINGKUNGAN | entri galeri uji 404 (prasyarat galeri/kunci Gemini) |
| `tests/test_fb02_logistics.py` | 23/29 | LINGKUNGAN | seed tanpa pengiriman ditugaskan ke sopir; SoD sopir "bukan tugas Anda" |
| `tests/test_g6_poc.py` | 17/21 | UJI BASI | netting kini dibatasi piutang balik terbuka (aturan baru G-6b) |
| `tests/test_g6b_poc.py` | 12/15 | LINGKUNGAN | prasyarat data demo (retur selesai bernilai, transaksi PPN tanpa faktur) |
| `tests/test_gelombang1_gl_integrity.py` | 8/18 | LINGKUNGAN | `suppliers[0]` = "PT Uji Provisioning" (entitas grup dari uji provisioning sebelumnya) → 409 |
| `tests/test_gelombang3_auth_ppn12.py` | 10/11 | UJI BASI | KEB-PDPT: pembayaran tidak lagi melahirkan JE pendapatan (diakui saat kirim) |
| `tests/test_interco_g6.py` | 7/13 | UJI BASI | alur antar-PT kini lewat Tugas Gudang ("Barangnya belum berpindah") |
| `tests/test_iter252_critical_cross_entity.py` | 6/9 | ASERSI BASI | angka drift seed berubah (Δ900k lama) |
| `tests/test_iter253_session_2026_06b.py` | 6/7 | UJI BASI | finance 403 boards — matriks izin dipersempit |
| `tests/test_iter258_purchase_e2e_and_recon.py` | 4/13 | LINGKUNGAN | residu "PT Uji Provisioning" (idem gelombang1) |
| `tests/test_iter266_r6_cc_r7.py` | 22/31 | LINGKUNGAN | seed tanpa device RFID (404 Device) |
| `tests/test_iter267_notif_health_multileg.py` | 8/18 | LINGKUNGAN | device key seed tidak ada (401) |
| `tests/test_iter272_blanket_unit.py` | 0/3 | LINGKUNGAN | residu "PT Uji Provisioning" |
| `tests/test_iter273_approval_rules.py` | 11/12 | ASERSI BASI | seed rules 7 (asersi ≥9) |
| `tests/test_iter275_g1_admin_sales_audit.py` | 44/46 | ASERSI BASI | Meja Finance kini 7 antrean; penugasan pelanggan seed berubah |
| `tests/test_iter276_g2_md_audit.py` | 47/50 | LINGKUNGAN+ASERSI | residu PT Uji Provisioning; OD demo 1 (asersi ≥3) |
| `tests/test_iter277_gates_pin_isolation.py` | login 502 | LINGKUNGAN | 502 ingress transien saat run |
| `tests/test_iter284_pb01_md02_md08.py` | 6/13 | ASERSI BASI | id supplier hardcoded tidak ada di seed |
| `tests/test_iter285_feedback_export_hutang.py` | 16/17 | LINGKUNGAN | jatuh tempo seed relatif tanggal (hutang_jatuh_tempo 0) |
| `tests/test_iter288_logistics_gps.py` | 6/10 | LINGKUNGAN | pengiriman uji 404 (seed) |
| `tests/test_iter289_driver_today.py` | 11/15 | LINGKUNGAN | sopir tanpa pengiriman aktif di seed |
| `tests/test_iter291_audit_probes.py` | 20/21 | ASERSI BASI | POD kini wajib `file` (422) |
| `tests/test_iter292_f01_dispatch_gl.py` | 1/2→2/2 | BASI→DIBETULKAN | KEB-PDPT tahap 2: JE per surat jalan (`shipment_revenue/cogs`) |
| `tests/test_iter298_kebpdpt_e2e.py` | 1/15 | UJI BASI | confirm butuh persetujuan manajer (gerbang nilai & kredit) |
| `tests/test_iter299_prorata_advance_report.py` | 2/20 | UJI BASI | idem |
| `tests/test_iter305_hpp_from_po.py` | 5/7 | ASERSI BASI | HPP seed 122.317,58 (asersi ≈122.387) |
| `tests/test_iter306_hpp_redaction_bootstrap.py` | 5/6 | ASERSI BASI | idem |
| `tests/test_m3_auto_elim_consolidation.py` | 9/10 | LINGKUNGAN | IC-AR ≠ IC-AP = residu transaksi interco dari uji g6 dalam run |
| `tests/test_notifications_addressing.py` | 4/5→5/5 | BASI→DIBETULKAN | peringatan KRITIS sengaja lintas konteks (batas allowed_entity_ids) |
| `tests/test_sesi_2026_06_papan_manajer.py` | 11/13 | ASERSI BASI | papan manajer kini 4 (+inspection_hold) |
| `tests/test_verifikasi_sesi_2026_08_25.py` | 8/11→9/11 | BASI→DIBETULKAN (D1) + ASERSI | roleLabel dipindah dari AdminHome; PO custom pending tak ada di seed |
| `backend_test_crm_enforcements.py` | 15/16 | ASERSI BASI | urutan gerbang MIXED_LOT sebelum CREDIT_BLOCKED (tercatat) |
| `backend_test_depth1.py` | 29/35 | ASERSI BASI | SoD manajer (tercatat) |
| `backend_test_dyelot.py` | 14/15 | ASERSI BASI | bentuk roll QC berubah (tercatat) |
| `test_audit_temuan_poc.py` | 34/34 | LULUS | — |
| `test_core_design_request_poc.py` | 54/55 | LINGKUNGAN | gate INV-APPR-01 bergantung data; HIJAU di seed bersih (239 cek) |
| `test_core_e0_isolation_poc.py` | 82/83 | REGISTRY GAP (P2) | L15: `collection_followups`, `credit_overrides`, `invoices` ber-entity_id belum di registry (data dari POC CRM/invoice) |
| `test_core_e1e2_poc.py` | 73/74 | LINGKUNGAN | 3 badan usaha aktif (residu provisioning) |
| `test_core_e4_poc.py` | 35/41 | LINGKUNGAN | harga Kanda seed `valid_until` di-expire oleh `test_f1a` (TEST_F1a) |
| `test_core_e7_interco_poc.py` | 62/62 | LULUS | — |
| `test_core_e8_desk_poc.py` | 94/97 | ASERSI BASI | 7 antrean Meja Finance; 4 sales di seed (20 ≠ 8+1) |
| `test_core_f67_workflow_poc.py` | crash | UJI BASI | `raise_for_status` finance `GET /approvals/backlog` 403 (matriks izin) |
| `test_core_f6_approval_coverage_poc.py` | 42/43 | LINGKUNGAN | INV-APPR-01 data (idem design_request) |
| `test_core_inspeksi_poc.py` | 92/93 | LINGKUNGAN | idem |
| `test_core_p0_poc.py` | 36/36 | LULUS | — |
| `test_core_po_board_poc.py` | 51/52 | LINGKUNGAN | invarian global sesudah pembersihan: 3 FAIL residu korpus |
| `test_core_rantai_retur_poc.py` | 13/14 | UJI BASI | pesanan berhenti `waiting_approval` (gerbang approval) |
| `test_core_role_access_poc.py` | 42/43→43/43 | BASI→DIBETULKAN | finance tidak punya `approval.view` → 403 benar |
| `test_core_sampling_poc.py` | 66/66 | LULUS | — |
| `test_core_sesi_2026_06_poc.py` | 64/66 | LINGKUNGAN | Δ nilai roll residu skrip lain |
| `test_core_sesi_2026_06b_poc.py` | crash | LINGKUNGAN | `IntercoError: Pasangan dokumen tidak lengkap` — pasangan interco residu uji g6 |
| `test_core_sesi_2026_06c_poc.py` | crash | LINGKUNGAN | idem |
| `test_f3_aftersales_smoke.py` | crash | UJI BASI | nota kredit kini lahir saat settlement retur, bukan saat approve |
| `test_f3_smoke.py` | crash | UJI BASI | SoD: admin pengaju tidak boleh menyetujui |
| `test_fase_c_lot_poc.py` | rc=1→0 | **BUG DIPERBAIKI** | kunci saga tertinggal sesudah 400 pagar lot (lihat §Bug) |
| `test_fase_f_rnd_poc.py` | 97/100 | LINGKUNGAN | INV-RND merah *sebelum* penyuntikan = residu |
| `test_fase_f_us3_us11_us12_poc.py` | 41/42→42/42 | BASI→DIBETULKAN | label `qc_accept`/`qc_reject_*` ditambah ke `MOV_TYPE_MAP` |
| `test_g0_config_poc.py` | 114/115 | REGISTRY GAP (P2) | kunci hidup di DB tanpa registry: `integrations.*`, `__migrations__.*` (sumber sesi lain) |
| `test_g2_payment_poc.py` | 52/54 | LINGKUNGAN | invarian awal merah = residu |
| `test_g3_variance_poc.py` | crash | LINGKUNGAN | stok entitas habis (aturan LINGKUNGAN yang sudah ada) |
| `test_g4_refs_poc.py` | 47/49 | LINGKUNGAN | idem |
| `test_g7_contrabon_poc.py` | 1 FAIL | LINGKUNGAN | `verify_data_integrity` 4 FAIL sesudah pembersihan = residu korpus |
| `test_g8_bank_poc.py` | 121/122 | LINGKUNGAN | idem |
| `test_g9_case_poc.py` | 118/119 | LINGKUNGAN | idem |
| `test_ps21_poc.py` | 42/43→43/43 | BASI→DIBETULKAN | jobs_total == 12 → ≥ 12 (registry job kini 21) |
| `tests/test_shipment_18.py` | crash | UJI BASI | confirm butuh verifikasi kelengkapan (tercatat) |
| `tests/test_tax_invoice_19.py` | 0/1 | UJI BASI | idem |
| `scripts/poc_hrd.py` | 20/21 | LINGKUNGAN | WS handshake lewat ingress → fallback polling |
| `scripts/poc_hrd_h1.py` | 17/18 | LINGKUNGAN | 4 record tanggal 2026-05-04 = residu `poc_hrd.py` (upsert per karyawan idempoten) |
| `scripts/poc_sales_revamp.py` | 34/35 | ASERSI BASI | target 400 **meter** vs `base_quantity` 437,45 **yard** (konversi UoM FASE U benar) |

## Tindak lanjut yang disarankan (keputusan pemilik)
1. **UJI BASI (12)** — hapus atau tulis ulang mengikuti gerbang baru; sinyalnya sekarang nol.
2. **Registry gap (P2)** — daftarkan `collection_followups`, `credit_overrides`, `invoices` di `entity_scope` (perlu cek
   `assert_entity_access` di router CRM/invoice) dan kunci `integrations.*` di config registry.
3. **Residu urutan** — jalankan `gate.sh --full` per-skrip di seed bersih bila ingin bukti hijau per skrip; `run_corpus.py`
   sebaiknya diberi opsi `--reseed-each` untuk menghapus kelas LINGKUNGAN ini.
