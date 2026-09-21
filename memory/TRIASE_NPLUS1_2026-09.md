# Triase kandidat N+1 (T-04 Langkah 1) — dihasilkan `scripts/triase_nplus1.py`

Total kandidat: **214** · BIARKAN (loop kecil): **3** · BIARKAN (sengaja): **5** · PERBAIKI: **2** · TIDAK TAHU: **204**

Vonis `PERBAIKI` hanya diberikan untuk lokasi yang sudah dibaca manusia (`VONIS_MANUAL`). `TIDAK TAHU` adalah vonis yang SAH — bukan tebakan. Tidak ada satu pun yang diperbaiki di langkah ini.

| # | Berkas:baris | Query | Loop (baris) atas | Vonis | Alasan |
|---|---|---|---|---|---|
| 1 | `backend/bootstrap.py:379` | `db.uoms.find_one` | `UOM_SEED_ROWS` (377) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 2 | `backend/bootstrap.py:522` | `db.products.find_one` | `enumerate(names)` (521) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 3 | `backend/bootstrap.py:688` | `db.cash_transactions.count_documents` | `receipts` (684) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 4 | `backend/bootstrap.py:719` | `db.purchase_requisitions.find` | `async for` (719) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 5 | `backend/bootstrap.py:804` | `db.purchase_orders.find` | `async for` (804) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 6 | `backend/bootstrap.py:922` | `db.hr_org_units.count_documents` | `entities` (920) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 7 | `backend/bootstrap.py:949` | `db.hr_employees.find` | `async for` (949) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 8 | `backend/bootstrap.py:953` | `db.users.find` | `await db.users.find({"status": "active"}, {"_id": 0}).to_list(500)` (953) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 9 | `backend/bootstrap.py:959` | `db.hr_org_units.find_one` | `await db.users.find({"status": "active"}, {"_id": 0}).to_list(500)` (953) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 10 | `backend/bootstrap.py:1021` | `db.hr_shifts.count_documents` | `entities` (1019) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 11 | `backend/bootstrap.py:1028` | `db.hr_geofences.count_documents` | `entities` (1019) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 12 | `backend/bootstrap.py:1043` | `db.hr_employees.find` | `entities` (1037) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 13 | `backend/bootstrap.py:1050` | `db.hr_employees.find` | `entities` (1037) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 14 | `backend/bootstrap.py:1039` | `db.hr_shifts.find_one` | `entities` (1037) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 15 | `backend/bootstrap.py:1175` | `db.hr_leave_balances.find_one` | `emps` (1174) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 16 | `backend/bootstrap.py:1536` | `db.users.find_one` | `({"id": "user_md_01", "name": "Rina Merchandiser", "email": "md@kainnu` (1531) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 17 | `backend/routers/admin.py:160` | `db.products.find_one` | `enumerate(rows)` (155) | PERBAIKI | atas `rows` CSV impor produk (bisa ribuan baris); find_one by sku per baris → satu find {sku: {$in: [...]}} lalu peta |
| 18 | `backend/routers/admin.py:212` | `db.customers.find_one` | `enumerate(rows)` (202) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 19 | `backend/routers/admin.py:272` | `db.warehouses.find_one` | `enumerate(rows)` (265) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 20 | `backend/routers/admin.py:278` | `db.warehouses.find_one` | `enumerate(rows)` (265) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 21 | `backend/routers/categories.py:50` | `db.products.count_documents` | `rows` (48) | BIARKAN (loop kecil) | atas `rows` kategori master (puluhan baris); count per kategori — bisa jadi satu aggregate, tapi bukan jalur panas |
| 22 | `backend/routers/contra_bons.py:160` | `db.wms_tasks.find` | `dec.get("bills", [])` (157) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 23 | `backend/routers/entities.py:70` | `db.users.count_documents` | `rows` (68) | BIARKAN (loop kecil) | atas `rows` badan usaha (≤ puluhan, berhalaman `limit`); count user per entitas |
| 24 | `backend/routers/hr_attendance.py:467` | `db.hr_employees.find_one` | `parsed` (464) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 25 | `backend/routers/hr_tracking.py:44` | `db.hr_field_tracks.aggregate` | `async for` (44) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 26 | `backend/routers/purchase_orders.py:136` | `db.wms_tasks.find_one` | `po.get("items", [])` (134) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 27 | `backend/routers/reporting.py:44` | `db.inventory_movements.find_one` | `balances` (35) | PERBAIKI | atas `balances` (seluruh inventory_balances ter-scope, ratusan–ribuan baris); find_one mutasi terakhir per baris → satu aggregate $group product+warehouse $max timestamp |
| 28 | `backend/routers/reporting.py:203` | `db.inventory_balances.find` | `warehouses` (195) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 29 | `backend/routers/reporting.py:209` | `db.products.find` | `warehouses` (195) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 30 | `backend/routers/sales_orders_extra.py:545` | `db.inventory_rolls.find_one` | `payload.roll_lines` (541) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 31 | `backend/routers/special_orders.py:114` | `db.special_orders.aggregate` | `async for` (114) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 32 | `backend/routers/transfers.py:198` | `db.products.find_one` | `payload.items` (197) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 33 | `backend/routers/transfers.py:293` | `db.products.find_one` | `payload.items` (292) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 34 | `backend/services/advance_report_service.py:80` | `db.customers.find` | `async for` (80) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 35 | `backend/services/approval_matrix_service.py:379` | `db.md_specs.find` | `await db.md_specs.find({**base, "status": "review"}, {"_id": 0} ).sort` (379) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 36 | `backend/services/approval_matrix_service.py:411` | `db.purchase_requisitions.find` | `await db.purchase_requisitions.find( {**base, "status": "pending_appro` (411) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 37 | `backend/services/approval_matrix_service.py:423` | `db.special_orders.find` | `await db.special_orders.find({**base, "status": "pending_approval"}, {` (423) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 38 | `backend/services/ar_aging_service.py:124` | `db.users.find` | `await db.users.find({"id": {"$in": list(sales_ids)}}, {"_id": 0, "id":` (124) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 39 | `backend/services/ar_aging_service.py:270` | `db.business_entities.find` | `async for` (270) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 40 | `backend/services/ar_receipt_service.py:302` | `db.sales_orders.find_one` | `applied` (296) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 41 | `backend/services/ar_receipt_service.py:557` | `db.sales_orders.find_one` | `r.get("allocations") or []` (555) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 42 | `backend/services/bank_recon_service.py:202` | `db.bank_statement_formats.find_one` | `parser.BUILTIN_FORMATS` (201) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 43 | `backend/services/bank_recon_service.py:584` | `db.cash_transactions.find_one` | `allocations` (583) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 44 | `backend/services/bank_recon_service.py:600` | `db.cash_transactions.find_one` | `line.get("allocations") or []` (599) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 45 | `backend/services/bank_recon_service.py:664` | `db.bank_statement_lines.find_one` | `sorted(lines, key=lambda x: (x.get("stmt_date") or "", -_round(x.get("` (636) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 46 | `backend/services/bank_recon_service.py:746` | `db.cash_transactions.find_one` | `allocations` (742) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 47 | `backend/services/bank_recon_service.py:1117` | `db.sales_orders.find_one` | `allocations` (1108) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 48 | `backend/services/bank_recon_service.py:1296` | `db.cash_transactions.find` | `await db.cash_transactions.find( _book_query(acc, entity_ids), {"_id":` (1296) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 49 | `backend/services/bank_recon_service.py:1271` | `db.cash_transactions.find` | `await db.cash_transactions.find({"id": {"$in": tids}}, {"_id": 0}).to_` (1271) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 50 | `backend/services/budget_service.py:244` | `db.journal_entries.find` | `async for` (244) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 51 | `backend/services/budget_service.py:263` | `db.cash_advance_settlements.find` | `async for` (263) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 52 | `backend/services/budget_service.py:301` | `db.purchase_orders.find` | `async for` (301) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 53 | `backend/services/budget_service.py:315` | `db.cash_advance_settlements.find` | `async for` (315) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 54 | `backend/services/cash_entity_service.py:83` | `db.cash_transactions.find` | `async for` (83) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 55 | `backend/services/closing_service.py:184` | `db.journal_entries.find` | `async for` (184) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 56 | `backend/services/color_service.py:73` | `db.md_samples.find` | `async for` (73) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 57 | `backend/services/config_impact_service.py:188` | `db.sales_orders.find_one` | `plan["editable_documents"]` (185) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 58 | `backend/services/config_impact_service.py:222` | `db.sales_orders.find_one` | `before.items()` (219) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 59 | `backend/services/consolidation_service.py:462` | `db.journal_entries.find_one` | `seller_docs` (458) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 60 | `backend/services/consolidation_service.py:470` | `db.journal_entries.find_one` | `seller_docs` (458) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 61 | `backend/services/consolidation_service.py:731` | `db.interco_transactions.count_documents` | `by_pair.items()` (728) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 62 | `backend/services/contra_bon_reminder.py:136` | `db.suppliers.find` | `async for` (136) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 63 | `backend/services/contra_bon_reminder.py:179` | `db.suppliers.find` | `async for` (179) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 64 | `backend/services/contra_bon_scan.py:52` | `db.vendor_bills.find_one` | `per_bill.items()` (51) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 65 | `backend/services/contra_bon_scan.py:111` | `db.vendor_bills.find_one` | `async for` (102) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 66 | `backend/services/contra_bon_scan.py:178` | `db.purchase_returns.find_one` | `await _live_contra_bons()` (172) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 67 | `backend/services/contra_bon_scan.py:182` | `db.cash_transactions.find_one` | `await _live_contra_bons()` (172) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 68 | `backend/services/contra_bon_scan.py:224` | `db.journal_entries.find_one` | `async for` (219) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 69 | `backend/services/contra_bon_service.py:392` | `db.purchase_returns.find` | `async for` (392) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 70 | `backend/services/contra_bon_service.py:478` | `db.wms_tasks.find_one` | `pos` (454) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 71 | `backend/services/contra_bon_service.py:621` | `db.vendor_bills.find_one` | `picks` (618) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 72 | `backend/services/contra_bon_service.py:922` | `db.vendor_bills.find_one` | `cb.get("bills", [])` (921) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 73 | `backend/services/contra_bon_service.py:1108` | `db.vendor_bills.find_one` | `cb.get("bills", [])` (1088) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 74 | `backend/services/contra_bon_service.py:414` | `db.cash_transactions.find` | `async for` (414) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 75 | `backend/services/customer_service.py:83` | `db.users.find_one` | `team or []` (80) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 76 | `backend/services/cycle_count_service.py:65` | `db.rfid_tags.find_one` | `extra_epcs` (64) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 77 | `backend/services/cycle_count_service.py:69` | `db.inventory_rolls.find_one` | `extra_epcs` (64) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 78 | `backend/services/cycle_count_service.py:71` | `db.warehouses.find_one` | `extra_epcs` (64) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 79 | `backend/services/design_gallery_service.py:50` | `db.design_gallery.find` | `async for` (50) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 80 | `backend/services/design_request_service.py:148` | `db.users.find` | `async for` (148) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 81 | `backend/services/design_request_service.py:155` | `db.rnd_person_divisions.find` | `async for` (155) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 82 | `backend/services/design_request_service.py:461` | `db.design_gallery.find` | `async for` (461) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 83 | `backend/services/digest_service.py:175` | `db.sys_wa_outbox.find_one` | `recipients` (173) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 84 | `backend/services/doc_refs_service.py:644` | `db.landed_cost_vouchers.find` | `async for` (644) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 85 | `backend/services/doc_refs_service.py:652` | `db.ar_receipts.find` | `async for` (652) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 86 | `backend/services/entity_context_service.py:135` | `db.business_entities.find` | `async for` (135) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 87 | `backend/services/entity_context_service.py:152` | `db.users.find` | `async for` (152) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 88 | `backend/services/entity_lifecycle_service.py:196` | `db.business_entities.find` | `async for` (196) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 89 | `backend/services/finance_case_actions.py:266` | `db.bank_accounts.find_one` | `(from_acc, to_acc)` (265) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 90 | `backend/services/finance_case_actions.py:389` | `db.journal_entries.find_one` | `[c.get("id") for c in (rec.get("cash_transactions") or [])] + \ [rec.g` (385) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 91 | `backend/services/finance_case_actions.py:406` | `db.sales_orders.find_one` | `order_ids` (405) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 92 | `backend/services/finance_case_scan.py:246` | `db.journal_entries.find_one` | `async for` (234) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 93 | `backend/services/fixed_asset_service.py:221` | `db.fin_depreciation_entries.find_one` | `assets` (206) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 94 | `backend/services/fulfillment_wizard_service.py:20` | `db.inventory_balances.find` | `async for` (20) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 95 | `backend/services/gl_service.py:760` | `db.journal_entries.find` | `async for` (760) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 96 | `backend/services/gl_service.py:1250` | `db.journal_entries.find` | `async for` (1250) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 97 | `backend/services/gl_service.py:1345` | `db.journal_entries.find_one` | `entries` (1341) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 98 | `backend/services/gl_service.py:1787` | `db.journal_entries.find` | `async for` (1787) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 99 | `backend/services/gl_service.py:2010` | `db.journal_entries.find` | `async for` (2010) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 100 | `backend/services/gl_service.py:2024` | `db.journal_entries.find` | `async for` (2024) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 101 | `backend/services/gl_service.py:2459` | `db.sales_orders.find` | `async for` (2459) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 102 | `backend/services/gl_service.py:2836` | `db.inventory_rolls.find` | `ents` (2835) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 103 | `backend/services/gl_service.py:2929` | `db.journal_entries.find` | `async for` (2929) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 104 | `backend/services/gl_service.py:3120` | `db.journal_entries.count_documents` | `recon["rows"]` (3114) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 105 | `backend/services/group_partner_service.py:94` | `db.suppliers.find` | `async for` (94) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 106 | `backend/services/group_partner_service.py:99` | `db.suppliers.count_documents` | `async for` (94) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 107 | `backend/services/group_partner_service.py:133` | `db.suppliers.find_one` | `active` (128) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 108 | `backend/services/group_partner_service.py:176` | `db.suppliers.find` | `async for` (176) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 109 | `backend/services/hr_leave_service.py:97` | `db.hr_leave_requests.find` | `async for` (97) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 110 | `backend/services/interco_money_service.py:80` | `db.cash_transactions.find_one` | `(("out", out_entity), ("in", in_entity))` (79) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 111 | `backend/services/interco_money_service.py:184` | `db.gl_accounts.find` | `async for` (184) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 112 | `backend/services/interco_service.py:1294` | `db.journal_entries.find_one` | `("seller", "cogs", "buyer", "receipt")` (1292) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 113 | `backend/services/interco_service.py:1347` | `db.journal_entries.find_one` | `settlements` (1345) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 114 | `backend/services/interco_service.py:1375` | `db.journal_entries.find_one` | `sorted(seen_rp)` (1373) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 115 | `backend/services/internal_request_service.py:91` | `db.inventory_balances.find` | `async for` (91) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 116 | `backend/services/landed_cost_service.py:167` | `db.inventory_rolls.find_one` | `allocations` (164) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 117 | `backend/services/line_scope.py:351` | `db.products.find` | `async for` (351) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 118 | `backend/services/line_scope.py:419` | `db.md_specs.find` | `async for` (419) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 119 | `backend/services/line_scope.py:422` | `db.md_samples.find` | `async for` (422) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 120 | `backend/services/location_service.py:52` | `db.inventory_rolls.find` | `async for` (52) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 121 | `backend/services/logistics_service.py:64` | `db.sales_orders.find_one` | `rows` (63) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 122 | `backend/services/lot_migration.py:48` | `db.products.find_one` | `groups.items()` (45) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 123 | `backend/services/lot_trace_service.py:107` | `db.wms_tasks.find_one` | `nodes` (100) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 124 | `backend/services/lot_trace_service.py:113` | `db.purchase_orders.find_one` | `nodes` (100) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 125 | `backend/services/lot_trace_service.py:118` | `db.makloon_orders.find_one` | `nodes` (100) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 126 | `backend/services/lot_trace_service.py:123` | `db.mfg_work_orders.find_one` | `nodes` (100) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 127 | `backend/services/makloon_order_service.py:257` | `db.process_recipes.find_one` | `enumerate(steps_in, start=1)` (253) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 128 | `backend/services/makloon_order_service.py:358` | `db.products.find_one` | `enumerate(steps_in, start=1)` (253) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 129 | `backend/services/makloon_order_service.py:359` | `db.products.find_one` | `enumerate(steps_in, start=1)` (253) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 130 | `backend/services/payment_plan_service.py:409` | `db.ar_receipts.find` | `async for` (409) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 131 | `backend/services/payment_variance_service.py:222` | `db.sales_orders.find_one` | `wanted` (218) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 132 | `backend/services/payment_variance_service.py:411` | `db.sales_orders.find_one` | `order_ids` (408) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 133 | `backend/services/payment_variance_service.py:428` | `db.sales_orders.find_one_and_update` | `order_ids` (408) | BIARKAN (sengaja) | find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk |
| 134 | `backend/services/payment_variance_service.py:1155` | `db.ar_receipts.find` | `async for` (1155) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 135 | `backend/services/payment_variance_service.py:1203` | `db.ar_receipts.find` | `async for` (1203) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 136 | `backend/services/payment_variance_service.py:1225` | `db.ar_receipts.find_one` | `async for` (1222) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 137 | `backend/services/payment_variance_service.py:822` | `db.sales_orders.find_one` | `d.get("orders") or []` (818) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 138 | `backend/services/payment_variance_service.py:850` | `db.sales_orders.find_one` | `d.get("orders") or []` (846) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 139 | `backend/services/penalty_service.py:297` | `db.sales_orders.find` | `async for` (297) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 140 | `backend/services/penalty_service.py:559` | `db.journal_entries.find_one` | `async for` (558) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 141 | `backend/services/period_unlock_service.py:120` | `db.period_closings.find` | `async for` (120) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 142 | `backend/services/po_board_service.py:413` | `db.wms_tasks.find` | `async for` (413) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 143 | `backend/services/po_board_service.py:419` | `db.inventory_rolls.find` | `async for` (419) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 144 | `backend/services/po_board_service.py:429` | `db.products.find` | `async for` (429) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 145 | `backend/services/po_board_service.py:438` | `db.sales_orders.find` | `async for` (438) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 146 | `backend/services/pr_sourcing_service.py:372` | `db.products.find_one` | `lines` (371) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 147 | `backend/services/purchase_requisition_service.py:371` | `db.inventory_balances.find` | `async for` (371) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 148 | `backend/services/purchase_requisition_service.py:379` | `db.purchase_orders.find` | `async for` (379) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 149 | `backend/services/purchase_requisition_service.py:394` | `db.purchase_requisitions.find` | `async for` (394) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 150 | `backend/services/purchase_return_service.py:96` | `db.inventory_rolls.find` | `payload.items` (84) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 151 | `backend/services/purchase_return_service.py:367` | `db.inventory_rolls.find_one` | `ret.get("items", [])` (365) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 152 | `backend/services/purchase_return_service.py:434` | `db.inventory_rolls.find_one` | `ret.get("items", [])` (432) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 153 | `backend/services/purchase_return_service.py:720` | `db.inventory_rolls.find_one` | `{m.get("roll_id") for m in movements if m.get("roll_id")}` (719) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 154 | `backend/services/purchase_return_service.py:205` | `db.interco_returns.find_one` | `pairs` (203) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 155 | `backend/services/purchase_return_service.py:532` | `db.purchase_orders.find_one` | `{r.get("product_id") for r in rolls}` (531) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 156 | `backend/services/putaway_order_service.py:106` | `db.rfid_tags.find_one` | `rolls` (96) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 157 | `backend/services/restock_service.py:207` | `db.products.find_one` | `raw` (188) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 158 | `backend/services/return_service.py:67` | `db.wms_tasks.find` | `async for` (67) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 159 | `backend/services/return_service.py:88` | `db.sales_returns.find` | `async for` (88) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 160 | `backend/services/return_service.py:800` | `db.products.find_one` | `items` (771) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 161 | `backend/services/return_service.py:961` | `db.journal_entries.find_one` | `q_rolls` (909) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 162 | `backend/services/return_service.py:1548` | `db.warehouses.find_one` | `from_ids` (1547) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 163 | `backend/services/rfid_incident_service.py:116` | `db.rfid_reads.aggregate` | `async for` (116) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 164 | `backend/services/rfid_incident_service.py:121` | `db.rfid_incidents.aggregate` | `async for` (121) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 165 | `backend/services/rfid_incident_service.py:129` | `db.inventory_rolls.aggregate` | `async for` (129) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 166 | `backend/services/rfid_ingest_service.py:100` | `db.rfid_tags.find_one` | `list(dict.fromkeys(e.strip().upper() for e in epcs if e and e.strip())` (99) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 167 | `backend/services/rfid_ingest_service.py:101` | `db.inventory_rolls.find_one` | `list(dict.fromkeys(e.strip().upper() for e in epcs if e and e.strip())` (99) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 168 | `backend/services/rfid_print_service.py:79` | `db.rfid_tags.find_one` | `rolls` (70) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 169 | `backend/services/rfid_service.py:242` | `db.rfid_devices.find_one` | `whs` (234) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 170 | `backend/services/rfid_service.py:325` | `db.inventory_rolls.find_one` | `tags` (324) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 171 | `backend/services/rfq_service.py:71` | `db.suppliers.find_one` | `supplier_ids` (67) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 172 | `backend/services/rfq_service.py:336` | `db.suppliers.find_one` | `grouped.items()` (330) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 173 | `backend/services/rnd_kpi_service.py:74` | `db.users.find` | `async for` (74) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 174 | `backend/services/rnd_org_service.py:27` | `db.users.find` | `async for` (27) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 175 | `backend/services/roll_service.py:85` | `db.inventory_rolls.find_one` | `range(200)` (83) | BIARKAN (loop kecil) | loop terbatas `range` |
| 176 | `backend/services/roll_service.py:261` | `db.inventory_rolls.find` | `balances` (258) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 177 | `backend/services/roll_service.py:1067` | `db.inventory_rolls.find_one_and_update` | `rolls` (1062) | BIARKAN (sengaja) | find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk |
| 178 | `backend/services/roll_service.py:1293` | `db.inventory_rolls.find_one_and_update` | `rolls` (1288) | BIARKAN (sengaja) | find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk |
| 179 | `backend/services/roll_service.py:57` | `db.inventory_rolls.find` | `async for` (57) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 180 | `backend/services/roll_service.py:1627` | `db.inventory_rolls.find_one` | `roll_lines or []` (1622) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 181 | `backend/services/roll_service.py:1642` | `db.inventory_rolls.find_one_and_update` | `roll_lines or []` (1622) | BIARKAN (sengaja) | find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk |
| 182 | `backend/services/roll_service.py:1653` | `db.inventory_rolls.find_one_and_update` | `roll_lines or []` (1622) | BIARKAN (sengaja) | find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk |
| 183 | `backend/services/roll_timeline_service.py:50` | `db.rfid_print_jobs.find` | `async for` (50) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 184 | `backend/services/roll_timeline_service.py:63` | `db.putaway_orders.find` | `async for` (63) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 185 | `backend/services/roll_timeline_service.py:83` | `db.inventory_movements.find` | `async for` (83) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 186 | `backend/services/roll_timeline_service.py:93` | `db.rfid_reads.find` | `async for` (93) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 187 | `backend/services/sales_order_helpers.py:88` | `db.inventory_rolls.find_one` | `roll_lines or []` (85) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 188 | `backend/services/scheduler_service.py:230` | `db.sys_scheduler_runs.find_one` | `JOBS` (229) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 189 | `backend/services/so_approvals.py:137` | `db.sales_orders.find` | `async for` (137) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 190 | `backend/services/so_verify_service.py:180` | `db.inventory_balances.find` | `async for` (180) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 191 | `backend/services/store_credit_service.py:57` | `db.store_credit_ledger.find` | `async for` (57) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 192 | `backend/services/store_credit_service.py:66` | `db.store_credit_ledger.find` | `async for` (66) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 193 | `backend/services/store_credit_service.py:98` | `db.store_credit_ledger.aggregate` | `async for` (98) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 194 | `backend/services/store_credit_service.py:280` | `db.credit_notes.find` | `async for` (280) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 195 | `backend/services/store_credit_service.py:284` | `db.store_credit_ledger.find_one` | `async for` (280) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 196 | `backend/services/store_credit_service.py:289` | `db.journal_entries.find_one` | `async for` (280) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 197 | `backend/services/store_credit_service.py:188` | `db.sales_orders.find_one` | `allocations` (184) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 198 | `backend/services/tax_center_service.py:62` | `db.sales_orders.find` | `async for` (62) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 199 | `backend/services/tracking_service.py:101` | `db.hr_field_tracks.aggregate` | `async for` (101) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 200 | `backend/services/vendor_bill_service.py:35` | `db.vendor_bills.find` | `async for` (35) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 201 | `backend/services/vendor_bill_service.py:190` | `db.vendor_bills.find` | `async for` (190) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 202 | `backend/services/wa_alert_service.py:196` | `db.sys_wa_outbox.find_one` | `recipients` (194) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 203 | `backend/services/warehouse_profile_service.py:77` | `db.warehouses.find` | `async for` (77) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 204 | `backend/services/warehouse_profile_service.py:149` | `db.warehouse_sites.find_one` | `BLUEPRINT_SITES` (148) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 205 | `backend/services/warehouse_profile_service.py:161` | `db.warehouses.find_one` | `BLUEPRINT_WH` (160) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 206 | `backend/services/wms_health_service.py:26` | `db.rfid_incidents.aggregate` | `async for` (26) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 207 | `backend/services/wms_health_service.py:31` | `db.rfid_reads.aggregate` | `async for` (31) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 208 | `backend/services/wms_health_service.py:37` | `db.inventory_rolls.aggregate` | `async for` (37) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 209 | `backend/services/wms_health_service.py:43` | `db.putaway_orders.aggregate` | `async for` (43) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 210 | `backend/services/wms_health_service.py:49` | `db.inventory_rolls.aggregate` | `async for` (49) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 211 | `backend/services/wms_health_service.py:55` | `db.inventory_rolls.aggregate` | `async for` (55) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 212 | `backend/services/wms_health_service.py:63` | `db.rfid_cycle_counts.aggregate` | `async for` (63) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 213 | `backend/services/wms_health_service.py:73` | `db.rfid_devices.find` | `async for` (73) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
| 214 | `backend/services/work_desk_service.py:276` | `db.tax_invoices.find` | `async for` (276) | TIDAK TAHU | ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia |
