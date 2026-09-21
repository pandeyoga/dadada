# TRIASE KORPUS UJI — 2026-09 (T-05)

- Sumber: `coverage_data/corpus_run_2026-09-05.json` (dihasilkan `scripts/run_corpus.py`, berurutan, commit `bb8f8c8`, 2026-09-05T12:43:56)
- Skrip: **220** · LINGKUNGAN: **58** · LULUS: **84** · TIDAK TAHU: **76** · UJI BASI: **2**
- Catatan: korpus lama `coverage_data/corpus_summary.json` (122 skrip) TIDAK bisa direproduksi — 58 dari 122 berkasnya sudah tidak ada di repo. Korpus di bawah = semua skrip uji/POC yang ADA hari ini (220).
- Vonis mengikuti aturan tertulis di `scripts/triase_korpus.py` (`RULES`). `TIDAK TAHU` = belum disimpulkan, bukan lulus.

| # | Skrip | Mode | RC | Lulus/Total | Vonis | Bukti (galat pertama / aturan) |
|---|---|---|---|---|---|---|
| 1 | `backend/tests/test_audit_findings_reproduction.py` | pytest | 1 | 5/6 | **TIDAK TAHU** | `FAILED tests/test_audit_findings_reproduction.py::test_D1_pagar_menuduh_saat_papan_hilang` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 2 | `backend/tests/test_config_clear_layer.py` | pytest | 5 | ? | **TIDAK TAHU** | galat belum diklasifikasi — perlu dibaca satu per satu |
| 3 | `backend/tests/test_f0b_entity_scoping.py` | pytest | 1 | 90/91 | **TIDAK TAHU** | `FAILED tests/test_f0b_entity_scoping.py::test_cash_kas_besar_visible_in_all_contexts` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 4 | `backend/tests/test_f0cdef_multientity.py` | pytest | 1 | 57/64 | **TIDAK TAHU** | `FAILED tests/test_f0cdef_multientity.py::TestF0C_OperationalIsolation::test_header_ent_kanda[/inventory/rolls]` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 5 | `backend/tests/test_f1a_pricelist.py` | pytest | 1 | 13/16 | **TIDAK TAHU** | `FAILED tests/test_f1a_pricelist.py::TestCreatePrice::test_create_then_grid_shows_entity_only_for_ksc` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 6 | `backend/tests/test_f1b_product_templates.py` | pytest | 1 | 7/20 | **TIDAK TAHU** | `FAILED tests/test_f1b_product_templates.py::test_create_template_ok - Asserti...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 7 | `backend/tests/test_f2_stock_buckets.py` | pytest | 0 | 20/20 | **LULUS** | rc=0 |
| 8 | `backend/tests/test_fb01_ai_illustration.py` | pytest | 1 | 6/13 | **TIDAK TAHU** | `FAILED tests/test_fb01_ai_illustration.py::TestIllustrateMockup::test_mockup_creates_ai_illustration_file` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 9 | `backend/tests/test_fb02_logistics.py` | pytest | 1 | 23/29 | **TIDAK TAHU** | `FAILED tests/test_fb02_logistics.py::TestLogisticsRead::test_list_deliveries` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 10 | `backend/tests/test_g5_poc.py` | pytest | 0 | 12/12 | **LULUS** | rc=0 |
| 11 | `backend/tests/test_g6_poc.py` | pytest | 1 | 17/21 | **TIDAK TAHU** | `FAILED tests/test_g6_poc.py::test_US6_netting_dua_transaksi - AssertionError:...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 12 | `backend/tests/test_g6b_poc.py` | pytest | 1 | 12/15 | **TIDAK TAHU** | `FAILED tests/test_g6b_poc.py::test_a2_siklus_faktur_pajak_internal_penuh - As...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 13 | `backend/tests/test_gelombang1_gl_integrity.py` | pytest | 1 | 8/18 | **TIDAK TAHU** | `FAILED tests/test_gelombang1_gl_integrity.py::TestFlow2_GoodsReceipt_GL::test_a_create_po` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 14 | `backend/tests/test_gelombang3_auth_ppn12.py` | pytest | 1 | 10/11 | **TIDAK TAHU** | `FAILED tests/test_gelombang3_auth_ppn12.py::TestSalesOrderGL::test_payment_creates_balanced_je_with_revenue_equals_grand_minus_ppn` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 15 | `backend/tests/test_home_boards_and_drift.py` | pytest | 0 | 5/5 | **LULUS** | rc=0 |
| 16 | `backend/tests/test_interco_g6.py` | pytest | 1 | 7/13 | **TIDAK TAHU** | `FAILED tests/test_interco_g6.py::test_05_fixed_price_without_contract_rejected` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 17 | `backend/tests/test_iter251_drift_and_isolation.py` | pytest | 0 | 7/7 | **LULUS** | rc=0 |
| 18 | `backend/tests/test_iter252_critical_cross_entity.py` | pytest | 1 | 6/9 | **TIDAK TAHU** | `FAILED tests/test_iter252_critical_cross_entity.py::test_recon_shows_kanda_drift_900k` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 19 | `backend/tests/test_iter253_session_2026_06b.py` | pytest | 1 | 6/7 | **TIDAK TAHU** | `FAILED tests/test_iter253_session_2026_06b.py::test_finance_home_boards - ass...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 20 | `backend/tests/test_iter254_session_2026_06c.py` | pytest | 0 | 8/8 | **LULUS** | rc=0 |
| 21 | `backend/tests/test_iter255_t1_t8.py` | pytest | 0 | 18/18 | **LULUS** | rc=0 |
| 22 | `backend/tests/test_iter256_e2e_flow_sweep.py` | pytest | 0 | 53/53 | **LULUS** | rc=0 |
| 23 | `backend/tests/test_iter258_purchase_e2e_and_recon.py` | pytest | 1 | 4/13 | **TIDAK TAHU** | `FAILED tests/test_iter258_purchase_e2e_and_recon.py::TestRantaiBeli::test_03_create_po` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 24 | `backend/tests/test_iter260_board_returns.py` | pytest | 0 | 10/10 | **LULUS** | rc=0 |
| 25 | `backend/tests/test_iter261_pipeline_eligibility.py` | pytest | 0 | 15/15 | **LULUS** | rc=0 |
| 26 | `backend/tests/test_iter263_wms_rfid_r0r1r2.py` | pytest | 1 | 19/27 | **LINGKUNGAN** | `FAILED tests/test_iter263_wms_rfid_r0r1r2.py::TestR0Sites::test_list_sites_seeded` — prasyarat: blueprint gudang (`POST /warehouse-sites/seed-blueprint`) belum dijalankan di DB uji |
| 27 | `backend/tests/test_iter264_putaway_fixes.py` | pytest | 1 | 2/3 | **LINGKUNGAN** | `FAILED tests/test_iter264_putaway_fixes.py::TestSuggestGradeAware::test_grade_b_group_includes_retur` — prasyarat: blueprint gudang (`POST /warehouse-sites/seed-blueprint`) belum dijalankan di DB uji |
| 28 | `backend/tests/test_iter265_r3r4r5.py` | pytest | 1 | 22/33 | **LINGKUNGAN** | `FAILED tests/test_iter265_r3r4r5.py::TestR3DeviceIngest::test_01_api_key_issue_and_idempotent` — prasyarat: blueprint gudang (`POST /warehouse-sites/seed-blueprint`) belum dijalankan di DB uji |
| 29 | `backend/tests/test_iter266_r6_cc_r7.py` | pytest | 1 | 22/31 | **TIDAK TAHU** | `FAILED tests/test_iter266_r6_cc_r7.py::TestR6Incidents::test_01_ingest_red_creates_incident` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 30 | `backend/tests/test_iter267_notif_health_multileg.py` | pytest | 1 | 8/18 | **TIDAK TAHU** | `FAILED tests/test_iter267_notif_health_multileg.py::TestHealthDashboard::test_shape_and_totals` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 31 | `backend/tests/test_iter268_order_preview.py` | pytest | 0 | 8/8 | **LULUS** | rc=0 |
| 32 | `backend/tests/test_iter270_reallocate_extra.py` | pytest | 0 | 3/3 | **LULUS** | rc=0 |
| 33 | `backend/tests/test_iter272_blanket_unit.py` | pytest | 1 | 0/3 | **TIDAK TAHU** | `FAILED tests/test_iter272_blanket_unit.py::TestBlanketUnitValidation::test_bogus_unit_rejected` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 34 | `backend/tests/test_iter273_approval_rules.py` | pytest | 1 | 11/12 | **TIDAK TAHU** | `FAILED tests/test_iter273_approval_rules.py::TestListContract::test_list_has_engine_schema_and_sorted` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 35 | `backend/tests/test_iter274_regresi_ringan.py` | pytest | 0 | 9/9 | **LULUS** | rc=0 |
| 36 | `backend/tests/test_iter275_g1_admin_sales_audit.py` | pytest | 1 | 44/46 | **TIDAK TAHU** | `FAILED tests/test_iter275_g1_admin_sales_audit.py::TestOrientasi::test_desk_finance_5_antrean` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 37 | `backend/tests/test_iter276_g2_md_audit.py` | pytest | 1 | 47/50 | **TIDAK TAHU** | `FAILED tests/test_iter276_g2_md_audit.py::TestAlurG::test_G3_setujui_pr_lalu_realisasikan_jadi_po` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 38 | `backend/tests/test_iter277_gates_pin_isolation.py` | pytest | 1 | 14/15 | **TIDAK TAHU** | `FAILED tests/test_iter277_gates_pin_isolation.py::TestT2_InternalRequests::test_T2c_convert_creates_interco_pair` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 39 | `backend/tests/test_iter278_fulfillment_whguard.py` | pytest | 0 | 10/10 | **LULUS** | rc=0 |
| 40 | `backend/tests/test_iter279_po_line_lock.py` | pytest | 0 | 16/16 | **LULUS** | rc=0 |
| 41 | `backend/tests/test_iter280_makloon_partial_queue.py` | pytest | 0 | 6/6 | **LULUS** | rc=0 |
| 42 | `backend/tests/test_iter281_demo_wave12.py` | pytest | 0 | 5/5 | **LULUS** | rc=0 |
| 43 | `backend/tests/test_iter284_pb01_md02_md08.py` | pytest | 1 | 6/13 | **TIDAK TAHU** | `FAILED tests/test_iter284_pb01_md02_md08.py::test_pb01_blanket_create_ok - As...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 44 | `backend/tests/test_iter285_feedback_export_hutang.py` | pytest | 1 | 16/17 | **TIDAK TAHU** | `FAILED tests/test_iter285_feedback_export_hutang.py::test_finance_desk_hutang_jatuh_tempo` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 45 | `backend/tests/test_iter288_logistics_gps.py` | pytest | 1 | 6/10 | **TIDAK TAHU** | `FAILED tests/test_iter288_logistics_gps.py::TestPositionGps::test_delivery_precondition` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 46 | `backend/tests/test_iter289_driver_today.py` | pytest | 1 | 11/15 | **TIDAK TAHU** | `FAILED tests/test_iter289_driver_today.py::TestMine::test_driver_only_own - A...` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 47 | `backend/tests/test_iter291_audit_probes.py` | pytest | 1 | 20/21 | **TIDAK TAHU** | `FAILED tests/test_iter291_audit_probes.py::TestDriverRbac::test_driver_can_act_on_delivery_not_assigned_to_him` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 48 | `backend/tests/test_iter292_audit_fixes.py` | pytest | 0 | 14/14 | **LULUS** | rc=0 |
| 49 | `backend/tests/test_iter292_f01_dispatch_gl.py` | pytest | 1 | 1/2 | **TIDAK TAHU** | `FAILED tests/test_iter292_f01_dispatch_gl.py::test_f01_dispatch_posts_revenue_and_cogs` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 50 | `backend/tests/test_iter293_audit_backlog.py` | pytest | 0 | 19/19 | **LULUS** | rc=0 |
| 51 | `backend/tests/test_iter294_numbering_pdf.py` | pytest | 0 | 6/6 | **LULUS** | rc=0 |
| 52 | `backend/tests/test_iter295_role_desks_bridge.py` | pytest | 0 | 9/9 | **LULUS** | rc=0 |
| 53 | `backend/tests/test_iter297_revenue_policy.py` | pytest | 0 | 5/5 | **LULUS** | rc=0 |
| 54 | `backend/tests/test_iter298_kebpdpt_e2e.py` | pytest | 1 | 1/15 | **TIDAK TAHU** | `FAILED tests/test_iter298_kebpdpt_e2e.py::TestAdvanceBeforeShipment::test_01_create_order_and_advance_receipt` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 55 | `backend/tests/test_iter299_prorata_advance_report.py` | pytest | 1 | 2/20 | **TIDAK TAHU** | `FAILED tests/test_iter299_prorata_advance_report.py::TestPartialDispatchProrata::test_01_order_and_advance` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 56 | `backend/tests/test_iter301_rbac_pricing_uom.py` | pytest | 0 | 24/24 | **LULUS** | rc=0 |
| 57 | `backend/tests/test_iter302_approval_rbac.py` | pytest | 0 | 16/16 | **LULUS** | rc=0 |
| 58 | `backend/tests/test_iter303_doc_resolve.py` | pytest | 0 | 12/12 | **LULUS** | rc=0 |
| 59 | `backend/tests/test_iter305_hpp_from_po.py` | pytest | 1 | 4/7 | **TIDAK TAHU** | `FAILED tests/test_iter305_hpp_from_po.py::TestHppEnrich::test_btk_mega_hpp_from_roll` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 60 | `backend/tests/test_iter306_hpp_redaction_bootstrap.py` | pytest | 1 | 5/6 | **TIDAK TAHU** | `FAILED tests/test_iter306_hpp_redaction_bootstrap.py::TestDashboardHpp::test_admin_dashboard_products_have_hpp` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 61 | `backend/tests/test_m3_auto_elim_consolidation.py` | pytest | 1 | 9/10 | **TIDAK TAHU** | `FAILED tests/test_m3_auto_elim_consolidation.py::TestConsolidationSummary::test_consolidation_impact_matches_ic_total` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 62 | `backend/tests/test_m3_coa_per_pt_and_ic_transfer.py` | pytest | 0 | 17/17 | **LULUS** | rc=0 |
| 63 | `backend/tests/test_notifications_addressing.py` | pytest | 1 | 4/5 | **TIDAK TAHU** | `FAILED tests/test_notifications_addressing.py::test_entity_isolation_on_notifications` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 64 | `backend/tests/test_price_approval_supersede_notification.py` | pytest | 1 | 10/13 | **UJI BASI** | `FAILED tests/test_price_approval_supersede_notification.py::test_supersede_creates_notification_for_sales_owner` — aturan pemisahan tugas approval harga (sakelar Pusat Pengaturan → Persetujuan & Ambang, FASE PS-20/approval matrix) — uji masih memakai admin sebagai pengaju+penyetuju |
| 65 | `backend/tests/test_price_approvals_supersede.py` | pytest | 1 | 9/16 | **UJI BASI** | `FAILED tests/test_price_approvals_supersede.py::test_lifecycle_create_submit_approve` — aturan pemisahan tugas approval harga (sakelar Pusat Pengaturan → Persetujuan & Ambang, FASE PS-20/approval matrix) — uji masih memakai admin sebagai pengaju+penyetuju |
| 66 | `backend/tests/test_roll_pick_and_reallocate.py` | pytest | 0 | 8/8 | **LULUS** | rc=0 |
| 67 | `backend/tests/test_sesi_2026_06_papan_manajer.py` | pytest | 1 | 11/13 | **TIDAK TAHU** | `FAILED tests/test_sesi_2026_06_papan_manajer.py::TestWaitingBoardsPayload::test_boards_shape[manager]` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 68 | `backend/tests/test_uom_1_13.py` | pytest | 0 | 12/12 | **LULUS** | rc=0 |
| 69 | `backend/tests/test_verifikasi_sesi_2026_08_25.py` | pytest | 1 | 9/11 | **TIDAK TAHU** | `FAILED tests/test_verifikasi_sesi_2026_08_25.py::test_C1_C2_label_peran_dan_entitas` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 70 | `backend/backend_test.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://subcon-preview.preview.emergentagent.com |
| 71 | `backend/backend_test_18.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `  ❌ Login failed: 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 72 | `backend/backend_test_360_panels.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login failed: 404 - 404 page not found` — URL preview basi hardcoded: https://kn-doc-esign-wire.preview.emergentagent.com |
| 73 | `backend/backend_test_bi_finance.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login failed: Login failed: 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 74 | `backend/backend_test_crm_enforcements.py` | direct | 1 | 15/16 | **TIDAK TAHU** | `❌ FAILED - Create SO with credit blocked (409): Expected CREDIT_BLOCKED code, got MIXED_LOT_CONFIRMATION_REQUIRED` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 75 | `backend/backend_test_depth1.py` | direct | 1 | 29/35 | **TIDAK TAHU** | `  ❌ [FAIL] Create PO failed: 403 {"detail":"Permission ditolak: purchase_order.create"}` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 76 | `backend/backend_test_depth3_enhancements.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL - Expected 200, got 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 77 | `backend/backend_test_dyelot.py` | direct | 1 | 14/15 | **TIDAK TAHU** | `  ❌ [FAIL] QC decision: roll with correct grade + defects not found` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 78 | `backend/backend_test_e0_isolation.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login gagal: 404 - 404 page not found` — URL preview basi hardcoded: https://code-forward-6.preview.emergentagent.com |
| 79 | `backend/backend_test_e4.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://kn-entity-scoped.preview.emergentagent.com |
| 80 | `backend/backend_test_epic7b_bank.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 81 | `backend/backend_test_equity_changes.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `  ❌ [FAIL] Login failed: 404 404 page not found` — URL preview basi hardcoded: https://kn123-backend-fixes.preview.emergentagent.com |
| 82 | `backend/backend_test_f0a_entity_context.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ CRITICAL ERROR: Login failed for admin@kainnusantara.id: 404 - 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 83 | `backend/backend_test_f3_mto_rma.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 84 | `backend/backend_test_f6_approval_retirement.py` | direct | 1 | 0/22 | **LINGKUNGAN** | `❌ GET /api/approval-requests returns 404` — URL preview basi hardcoded: https://warehouse-ops-launch.preview.emergentagent.com |
| 85 | `backend/backend_test_fase4.py` | direct | 1 | ? | **LINGKUNGAN** | `❌   FAILED - Expected 200, got 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 86 | `backend/backend_test_fase_b.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `❌ FAILED - Expected 200, got 404` — URL preview basi hardcoded: https://warehouse-fase-b.preview.emergentagent.com |
| 87 | `backend/backend_test_fase_b_uom.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404` — URL preview basi hardcoded: https://grade-registry-qa.preview.emergentagent.com |
| 88 | `backend/backend_test_fase_c_lot.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://kn-lot-tracking.preview.emergentagent.com |
| 89 | `backend/backend_test_fase_f_closure.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login warehouse@kainnusantara.id — Status 404` — URL preview basi hardcoded: https://nusantara-staging-1.preview.emergentagent.com |
| 90 | `backend/backend_test_fase_f_endpoints.py` | direct | 0 | 1/11 | **LULUS** | rc=0 |
| 91 | `backend/backend_test_fase_f_final.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404` — URL preview basi hardcoded: https://wms-inventory-dev.preview.emergentagent.com |
| 92 | `backend/backend_test_fase_f_write_flows.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login as admin@kainnusantara.id` — URL preview basi hardcoded: https://kn-supplier-verify.preview.emergentagent.com |
| 93 | `backend/backend_test_finance_analytics.py` | direct | 1 | ? | **LINGKUNGAN** | `[12:50:40] ❌ Login failed: Login failed: 404 404 page not found` — URL preview basi hardcoded: https://kn123-backend-fixes.preview.emergentagent.com |
| 94 | `backend/backend_test_g4_comprehensive.py` | direct | 0 | 0/0 | **LULUS** | rc=0 |
| 95 | `backend/backend_test_g6.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://supplier-contract-ui.preview.emergentagent.com |
| 96 | `backend/backend_test_g6_iter192.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `  ❌ [FAIL] Login failed: 404 404 page not found` — URL preview basi hardcoded: https://supplier-contract-ui.preview.emergentagent.com |
| 97 | `backend/backend_test_h1.py` | direct | 1 | ? | **LINGKUNGAN** | `❌   FAILED - Expected 200, got 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 98 | `backend/backend_test_ica_directional.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Failed - Expected 200, got 404` — URL preview basi hardcoded: https://g6b-reminders.preview.emergentagent.com |
| 99 | `backend/backend_test_iteration_183.py` | direct | 2 | ? | **LINGKUNGAN** | `FATAL ERROR: HTTPError: 404 Client Error: Not Found for url: https://nusantara-staging-1.preview.emergentagent.com/api/auth/login` — URL preview basi hardcoded: https://nusantara-staging-1.preview.emergentagent.com |
| 100 | `backend/backend_test_landed_cost.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login admin: FAILED - Status 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 101 | `backend/backend_test_m0_color.py` | direct | 1 | 0/20 | **LINGKUNGAN** | `❌ FAILED: Admin login failed` — URL preview basi hardcoded: https://subcon-preview.preview.emergentagent.com |
| 102 | `backend/backend_test_p4.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed: 404 404 page not found` — URL preview basi hardcoded: https://warehouse-ops-launch.preview.emergentagent.com |
| 103 | `backend/backend_test_p5_p2.py` | direct | 1 | 0/1 | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://kn-form-gateway.preview.emergentagent.com |
| 104 | `backend/backend_test_pdf_fase3.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL — Login admin@kainnusantara.id (expected 200, got 404)` — URL preview basi hardcoded: https://static-bundle-2.preview.emergentagent.com |
| 105 | `backend/backend_test_phase2_forms.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ Login admin — status=404` — URL preview basi hardcoded: https://nav-validated.preview.emergentagent.com |
| 106 | `backend/backend_test_po_timeline_approval.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Expected 200, got 404 - FAILED` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 107 | `backend/backend_test_qc.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 108 | `backend/backend_test_qc_4point.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: Admin login` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 109 | `backend/backend_test_r1_05_06.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login failed: 404 - 404 page not found` — URL preview basi hardcoded: https://kn123-backend-fixes.preview.emergentagent.com |
| 110 | `backend/backend_test_r5_4b.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Admin login successful - ` — URL preview basi hardcoded: https://return-reversals.preview.emergentagent.com |
| 111 | `backend/backend_test_r6_3_budget.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAILED - Expected 200, got 404` — URL preview basi hardcoded: https://po-budget-warn.preview.emergentagent.com |
| 112 | `backend/backend_test_sales_returns.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Admin login failed: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 113 | `backend/backend_test_tax_invoices.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed for admin@kainnusantara.id: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 114 | `backend/test_audit_2026_09_02_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 115 | `backend/test_audit_temuan_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `Traceback (most recent call last):` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 116 | `backend/test_core_approval_reminder_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 117 | `backend/test_core_design_request_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [PASS] gate `check_nav_map` PASS (dulu CRASH `KeyError: 'designer'`)  [2mexit 0 · m======================================================` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 118 | `backend/test_core_dua_satuan_poc.py` | direct | 0 | 63/63 | **LULUS** | rc=0 |
| 119 | `backend/test_core_e0_isolation_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[92mPASS[0m] L1 BUKTI-MERAH: ada notifications milik ent_ksc di DB  (122 baris)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 120 | `backend/test_core_e1e2_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[92mPASS[0m] E1.1c — BUKTI-MERAH: non-PKP TANPA NPWP tetap boleh (bukan asal blokir)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 121 | `backend/test_core_e3_write_guard_poc.py` | direct | 0 | 26/26 | **LULUS** | rc=0 |
| 122 | `backend/test_core_e4_master_layers_poc.py` | direct | 0 | 56/56 | **LULUS** | rc=0 |
| 123 | `backend/test_core_e4_poc.py` | direct | 1 | 35/41 | **TIDAK TAHU** | `  [FAIL] Kanda memakai harga sendiri: None (asal: entity)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 124 | `backend/test_core_e5_visibility_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 125 | `backend/test_core_e7_interco_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[92mPASS[0m] BUKTI-MERAH: pemasok bertipe 'Entitas grup' memang ada di daftar` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 126 | `backend/test_core_e8_desk_poc.py` | direct | 1 | 89/95 | **TIDAK TAHU** | `  [[91mFAIL[0m] jumlah keduanya = jumlah Admin Sales (tidak ada pesanan hilang)  (8+1 vs 28)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 127 | `backend/test_core_e8_roles_poc.py` | direct | 0 | 64/64 | **LULUS** | rc=0 |
| 128 | `backend/test_core_f67_workflow_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `Traceback (most recent call last):` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 129 | `backend/test_core_f6_approval_coverage_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `[1m▶ G5 — BUKTI-MERAH: suntik 1 transfer menunggu → angka WAJIB bergerak[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 130 | `backend/test_core_group_cash_migration_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 131 | `backend/test_core_inspeksi_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `[93mI8 · Gate INV-QC-01..03 dijalankan sungguhan — dan dibuktikan BISA MEMERAH[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 132 | `backend/test_core_lini_poc.py` | direct | 0 | 40/40 | **LULUS** | rc=0 |
| 133 | `backend/test_core_makloon_lini_poc.py` | direct | 0 | 35/35 | **LULUS** | rc=0 |
| 134 | `backend/test_core_notifikasi_alamat_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 135 | `backend/test_core_p0_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [PASS] `INV-ORIG-01 --self-test` membuktikan gate BISA memerah (bukti-merah)  [2mexit 0 · K][0m R5 arah balik (PR→PO) hilang → MERAH` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 136 | `backend/test_core_papan_po_custom_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 137 | `backend/test_core_po_board_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [PASS] gate `INV-STAGE-01 --self-test (bukti-merah)` HIJAU  [2mexit 0 · luar urutan lini → MERAH` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 138 | `backend/test_core_rantai_retur_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  ❌ [FAIL] Pesanan tidak sampai status yang bisa diretur (status waiting_approval)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 139 | `backend/test_core_role_access_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[91mFAIL[0m] finance     GET /approvals/backlog 200 [91m→ 403[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 140 | `backend/test_core_role_reality_poc.py` | direct | 0 | 48/48 | **LULUS** | rc=0 |
| 141 | `backend/test_core_sampling_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [FAIL] permintaan dua jenis dibuat` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 142 | `backend/test_core_sesi_2026_06_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[91mFAIL[0m] sesudah dibersihkan: buku kembali seperti sebelum POC (nol residu nilai) [91mΔ3,219,000[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 143 | `backend/test_core_sesi_2026_06b_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[91mFAIL[0m] keadaan awal: roll bernilai Rp 900.000 ada di gudang penjual TANPA jurnal [91mΔ-860,000[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 144 | `backend/test_core_sesi_2026_06c_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `Traceback (most recent call last):` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 145 | `backend/test_core_tahapan_poc.py` | direct | 0 | 57/57 | **LULUS** | rc=0 |
| 146 | `backend/test_f0c_scoping_leak_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 147 | `backend/test_f3_aftersales_smoke.py` | direct | 1 | ? | **TIDAK TAHU** | `Traceback (most recent call last):` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 148 | `backend/test_f3_smoke.py` | direct | 1 | ? | **TIDAK TAHU** | `Traceback (most recent call last):` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 149 | `backend/test_fase_a_poc.py` | direct | 0 | 53/53 | **LULUS** | rc=0 |
| 150 | `backend/test_fase_b_uom_poc.py` | direct | 0 | 49/49 | **LULUS** | rc=0 |
| 151 | `backend/test_fase_c_lot_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  ❌ [FAIL] Migrasi masih menemukan pekerjaan: {'dry_run': True, 'rolls_without_lot': 0, 'lots_created': 0, 'rolls_linked': 0, 'movements_lin` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 152 | `backend/test_fase_d_makloon_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 153 | `backend/test_fase_e_contracts_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 154 | `backend/test_fase_f1_receiving_uom_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 155 | `backend/test_fase_f_rnd_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `TEST 13 — BUKTI-MERAH: invarian INV-RND benar-benar MEMERAH saat dilanggar` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 156 | `backend/test_fase_f_us3_us11_us12_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [FAIL] SEMUA tipe mutasi pada data punya label Indonesia di peta UI — tanpa label: ['hold', 'hold_release', 'qc_accept', 'wip_complete', '` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 157 | `backend/test_forms_poc.py` | direct | 0 | 32/32 | **LULUS** | rc=0 |
| 158 | `backend/test_g0_config_api_test.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Failed - Expected 200, got 404` — URL preview basi hardcoded: https://kn-deep-link.preview.emergentagent.com |
| 159 | `backend/test_g0_config_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  PASS 114 / FAIL 1  (total 115)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 160 | `backend/test_g1_amendment_poc.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 161 | `backend/test_g2_payment_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `TEST 12 — BUKTI-MERAH: invarian G-2 benar-benar bisa MEMERAH` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 162 | `backend/test_g3_variance_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `TEST 13 — BUKTI-MERAH: invarian INV-VAR memerah saat dilanggar` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 163 | `backend/test_g4_refs_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `TEST 8 — BUKTI-MERAH: invarian INV-REF benar-benar bisa MEMERAH` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 164 | `backend/test_g7_contrabon_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `[96m[1m── 14 · INVARIAN INV-CB-01..04 + BUKTI-MERAH (US11) ──[0m` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 165 | `backend/test_g8_bank_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[92mPASS[0m] BUKTI-MERAH (KN-G8-FORMAT-DUP): admin 2 PT melihat tiap template bawaan SEKALI — dulu preset dipasang per-entitas sehingga` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 166 | `backend/test_g9_case_poc.py` | direct | 1 | ? | **TIDAK TAHU** | `  [[92mPASS[0m] BUKTI-MERAH (idempoten): pemindai dijalankan 2x TIDAK menggandakan kasus  (3 → 4 → 4 · dilewati 2)` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 167 | `backend/test_makloon_core_poc.py` | direct | 0 | 19/19 | **LULUS** | rc=0 |
| 168 | `backend/test_makloon_order_api.py` | direct | 0 | 36/37 | **LULUS** | rc=0 |
| 169 | `backend/test_ps21_poc.py` | direct | 1 | 40/43 | **TIDAK TAHU** | `❌ US-4b Goods Receipt diselesaikan (peristiwa nyata: scan → complete)  ·  scan HTTP 200 · complete HTTP 400 · {"detail":"Roll ?: tak bisa me` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 170 | `backend/test_rfid_comprehensive.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAILED - Login Admin (Expected 200, got 404)` — URL preview basi hardcoded: https://warehouse-fase-b.preview.emergentagent.com |
| 171 | `backend/test_roll_ssot.py` | direct | 1 | ? | **LINGKUNGAN** | `  ❌ [FAIL] Login failed: 404 404 page not found` — URL preview basi hardcoded: https://epic-cannon-6.preview.emergentagent.com |
| 172 | `backend/test_sales_returns_r1.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: Auth - Login` — URL preview basi hardcoded: https://inventory-refund.preview.emergentagent.com |
| 173 | `backend/test_store_credit.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: Auth - Login` — URL preview basi hardcoded: https://supplier-rma-portal.preview.emergentagent.com |
| 174 | `backend/test_store_credit_comprehensive.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: Auth - Login` — URL preview basi hardcoded: https://supplier-rma-portal.preview.emergentagent.com |
| 175 | `backend/fase3_purchasing_test.py` | direct | 1 | 0/3 | **LINGKUNGAN** | `❌ Failed - Expected 200, got 404` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 176 | `backend/hr_analytics_test.py` | direct | 1 | 0/5 | **LINGKUNGAN** | `  ❌ [FAIL] Login admin@kainnusantara.id failed: 404 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 177 | `backend/r0_return_policy_test.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: API Health Check` — URL preview basi hardcoded: https://inventory-refund.preview.emergentagent.com |
| 178 | `tests/agent_e7_fe_iteration_219.py` | direct | 1 | ? | **LINGKUNGAN** | `Traceback (most recent call last):` — URL preview basi hardcoded: https://nusantara-erp-test.preview.emergentagent.com |
| 179 | `tests/backend_g9_test.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Failed to login as admin` — URL preview basi hardcoded: https://textile-erp-finance.preview.emergentagent.com |
| 180 | `tests/backend_test_catch_weight.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ Login` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 181 | `tests/backend_test_f2_f3_sales_team_delivery.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ FAIL: Login failed: 404 - 404 page not found` — URL preview basi hardcoded: https://kainnusantara-stage.preview.emergentagent.com |
| 182 | `tests/backend_test_p2_bugfixes.py` | direct | 1 | ? | **LINGKUNGAN** | `  [91m[FAIL][0m Login — Status 404` — URL preview basi hardcoded: https://bug-fix-sprint-27.preview.emergentagent.com |
| 183 | `tests/backend_test_security.py` | direct | 1 | ? | **LINGKUNGAN** | `❌ CRITICAL: Admin login failed. Cannot proceed with tests.` — URL preview basi hardcoded: https://bug-fix-sprint-27.preview.emergentagent.com |
| 184 | `tests/backend_test_special_orders.py` | direct | 1 | 0/17 | **LINGKUNGAN** | `❌ FAILED: Authentication for all roles - Login failed: 404 - 404 page not found` — URL preview basi hardcoded: https://po-pdf-sender.preview.emergentagent.com |
| 185 | `tests/fase5_poc.py` | direct | 0 | 15/15 | **LULUS** | rc=0 |
| 186 | `tests/t1_verifikasi_A2.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 187 | `tests/test_allocation_policy_17.py` | direct | 0 | 19/19 | **LULUS** | rc=0 |
| 188 | `tests/test_pegging_17.py` | direct | 0 | 11/11 | **LULUS** | rc=0 |
| 189 | `tests/test_shipment_18.py` | direct | 1 | ? | **TIDAK TAHU** | `FAIL - confirm → 200 :: {"detail":"Verifikasi kelengkapan dulu (alamat · syarat bayar · isi pesanan) sebelum pesanan ini dikonfirmasi — buka` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 190 | `tests/test_tax_invoice_19.py` | direct | 1 | 0/1 | **TIDAK TAHU** | `FAIL - buat SO PKP (ent_ksc) terkonfirmasi :: approved` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 191 | `forensic/fa_ar_ap.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 192 | `forensic/fa_costing.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 193 | `forensic/fa_coverage_gap.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 194 | `forensic/fa_dark_sweep.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 195 | `forensic/fa_e2e.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 196 | `forensic/fa_edge_branches.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 197 | `forensic/fa_error_branch_500.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 198 | `forensic/fa_fuzz.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 199 | `forensic/fa_idor.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 200 | `forensic/fa_idor_confirm.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 201 | `forensic/fa_idor_matrix.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 202 | `forensic/fa_import_fuzz.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 203 | `forensic/fa_landed_cost_value.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 204 | `forensic/fa_mutation.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 205 | `forensic/fa_nplus1.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 206 | `forensic/fa_race.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 207 | `forensic/fa_runtime.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 208 | `forensic/fa_s074_errorpath.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 209 | `forensic/fa_s074_semantic.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 210 | `forensic/fa_s075_verify.py` | direct | 0 | 22/27 | **LULUS** | rc=0 |
| 211 | `forensic/fa_session.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 212 | `forensic/fa_static.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 213 | `forensic/fa_sweep.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 214 | `forensic/fa_write_idor.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 215 | `scripts/poc_document_platform.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 216 | `scripts/poc_hrd.py` | direct | 1 | 20/21 | **TIDAK TAHU** | `  [FAIL] WS handshake lewat ingress  -> GAGAL: ConnectionClosedOK: received 1000 (OK); then sent 1000 (OK) -> FALLBACK POLLING` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 217 | `scripts/poc_hrd_h1.py` | direct | 1 | 17/18 | **TIDAK TAHU** | `  [FAIL] Clock-out → work_min>0  -> work_min=0` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 218 | `scripts/poc_sales_revamp.py` | direct | 1 | 27/30 | **TIDAK TAHU** | `RESULT: 27 PASS / 3 FAIL` — galat belum diklasifikasi — perlu dibaca satu per satu |
| 219 | `scripts/health_check.py` | direct | 0 | ? | **LULUS** | rc=0 |
| 220 | `scripts/audit_endpoint_sweep.py` | direct | 0 | ? | **LULUS** | rc=0 |
