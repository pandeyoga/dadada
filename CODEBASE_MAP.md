<!-- DIHASILKAN OTOMATIS oleh scripts/gen_codebase_map.py — JANGAN EDIT TANGAN -->
<!-- Dihasilkan dari commit: fed03d9 pada 2026-09-07 -->
# CODEBASE MAP — Kain Nusantara (dihasilkan otomatis)

Peta ini dihitung dari kode oleh `scripts/gen_codebase_map.py`. Kalau angka di sini
tidak cocok lagi dengan kenyataan, `scripts/guardrails/verify_codebase_map.py` (INV-DOC-01)
memerah — jalankan ulang generatornya, jangan sunting tangan.

**Batas ukuran berkas (dari FRONTEND/ENGINEERING_GUARDRAILS):** `.jsx` ≤ 500 · router `.py` ≤ 800 · util `.js` ≤ 300.

## Ringkasan angka

| Ukuran | Nilai |
|---|---:|
| Router (`backend/routers/*.py`) | 127 |
| Endpoint (`@router.<method>`) | 1167 |
| Service (`backend/services/*.py`) | 205 |
| Koleksi MongoDB disentuh kode produksi | 132 |
| Direktori fitur frontend (`src/features/*`) | 33 |

## Backend — berkas inti

| Berkas | Baris |
|---|---:|
| `server.py` | 315 |
| `db.py` | 12 |
| `core_utils.py` | 383 |
| `schemas.py` | 987 |
| `schemas_purchasing.py` | 588 |
| `dependencies.py` | 174 |
| `permissions_config.py` | 509 |
| `entity_scope.py` | 554 |
| `pagination.py` | 123 |
| `indexes.py` | 377 |
| `bootstrap.py` | 1713 |

### Fungsi utilitas — JANGAN re-implementasi

**`backend/core_utils.py`**

| Fungsi | Ringkas (baris pertama docstring) |
|---|---|
| `now_iso()` |  |
| `next_doc_number()` | Generate nomor dokumen berurutan (deletion-safe). |
| `entity_code()` | Kode pendek entitas untuk nomor dokumen (doc_prefix → short_name → upper id). |
| `invalidate_entity_code()` | FASE E-1 (E1.4) — buang cache kode entitas setelah entitas dibuat/diubah. |
| `new_id()` |  |
| `parse_decimal()` | Ubah input pengguna menjadi float desimal (mendukung koma-desimal). |
| `to_cents()` | Nominal rupiah → SEN BULAT (int, pembulatan setengah-ke-atas). |
| `from_cents()` | SEN BULAT → rupiah berdesimal dua (pasangan `to_cents`). |
| `rupiah()` | Format nominal ke gaya Indonesia: `rupiah(5131200)` → `"Rp 5.131.200"`. |
| `qty_num_id()` | Angka gaya Indonesia: `540.5` → `"540,5"` · `12.0` → `"12"`. |
| `qty_dual()` | Satu kalimat untuk DUA satuan: `qty_dual(12, 540.5, "yard")` → |
| `timeline_entry()` | Entri riwayat/timeline standar (dipakai PO approval history, dll). |
| `safe_doc()` | Recursively remove _id fields and convert ObjectId to str. |
| `hash_password()` | SEC-1 — bcrypt (salt otomatis per-hash). |
| `legacy_hash_password()` | Skema lama SHA256+pepper — hanya untuk verifikasi migrasi (rehash saat login). |
| `is_legacy_hash()` |  |
| `verify_password()` |  |
| `strip_cost_fields()` | S-10 — hapus field biaya (HPP/margin) dari respons bila role bukan admin/manager. |

**`backend/dependencies.py`**

| Fungsi | Ringkas (baris pertama docstring) |
|---|---|
| `session_expiry()` |  |
| `extract_token()` | SEC-2 — HttpOnly cookie diutamakan; fallback header Bearer (kompat). |
| `current_user()` |  |
| `require_role()` |  |
| `permission_matrix()` |  |
| `require_permission()` |  |
| `require_any_permission()` | Izin "SALAH SATU dari" — untuk layar yang menyatukan beberapa domain. |
| `audit()` | Tulis satu baris jejak audit. |

**`backend/entity_scope.py`**

| Fungsi | Ringkas (baris pertama docstring) |
|---|---|
| `field_for()` | Field entitas untuk koleksi. None bila SHARED. |
| `entity_ctx()` | FastAPI dependency: resolve badan usaha aktif untuk request. |
| `apply_entity_scope()` | Suntik filter entitas ke query. |
| `stamp_entity()` | Set field entitas saat create (jika belum ada). |
| `assert_entity_access()` | Cegah akses lintas-entitas (anti-IDOR) untuk GET/{id}. |
| `assert_active_entity_access()` | Isolasi detail SEKETAT daftarnya: dokumen harus milik badan usaha AKTIF. |
| `resolve_list_scope()` | Logika scope LIST yang baku & backward-compatible. |
| `resolve_scope_ids()` | Daftar entity_id dalam cakupan baca. Dipakai koleksi yang punya record |
| `resolve_list_scope_inherit()` | Seperti `resolve_list_scope`, tetapi baris **GLOBAL tetap terlihat**. |
| `scope_value()` | Nilai siap-pakai untuk field entitas: `str` bila satu, `{"$in": [...]}` bila banyak. |
| `assert_write_entity()` | Pagar mode "Semua Entitas": TULIS wajib memilih satu entitas (tutup E4). |
| `resolve_requested_entity()` | Entitas efektif untuk PRATINJAU/TULIS bila pemanggil menyebut entitas di payload. |

**`backend/pagination.py`**

| Fungsi | Ringkas (baris pertama docstring) |
|---|---|
| `is_paged()` | True bila klien meminta paginasi (ada param page / page_size). |
| `get_page_params()` | Ambil (page, page_size, q, sort) dari query string dengan aman. |
| `build_search()` | Bangun filter `$or` regex case-insensitive untuk daftar field. |
| `merge_query()` | Gabung dua filter Mongo dengan aman (pakai $and bila keduanya isi). |
| `fetch_page()` | Hitung total + ambil satu halaman (skip/limit). Return (items, total). |
| `envelope()` | Bungkus hasil sesuai kontrak paginasi. |
| `paginate_list()` | Paginasi in-memory (untuk list yang sudah ter-enrich/di-hitung penuh). |

## Backend — router

| Berkas | Endpoint | Baris | Path |
|---|---:|---:|---|
| `access_review.py` | 2 | 87 | `/access/role-reality`, `/access/role-reality/{user_id}/apply` |
| `admin.py` | 10 | 466 | `/admin/seed-demo`, `/master-data/export-customers`, `/master-data/export-products`, `/master-data/export-warehouses`, `/master-data/export-yarn`, `/master-data/import-customers` … |
| `amendments.py` | 9 | 144 | `/amendment-reasons`, `/amendments`, `/amendments/doc/{doc_type}/{doc_id}`, `/amendments/preview`, `/amendments/stats/summary`, `/amendments/{amd_id}` … |
| `approval_rules.py` | 5 | 138 | `/approval-rules`, `/approval-rules/{rule_id}` |
| `approvals_matrix.py` | 3 | 77 | `/approvals/matrix`, `/approvals/matrix-log`, `/approvals/my-queue` |
| `ar_aging.py` | 4 | 103 | `/ar/advance-report`, `/ar/aging`, `/ar/aging/{customer_id}`, `/ar/aging/{customer_id}/accrue-penalties` |
| `ar_receipts.py` | 6 | 121 | `/ar-receipts`, `/ar-receipts/deposit`, `/ar-receipts/open-orders`, `/ar-receipts/{receipt_id}`, `/ar-receipts/{receipt_id}/void` |
| `audit.py` | 1 | 52 | `/audit-logs` |
| `auth.py` | 5 | 174 | `/auth/context`, `/auth/login`, `/auth/logout`, `/auth/me`, `/roles` |
| `bank.py` | 5 | 90 | `/bank-accounts`, `/bank-accounts/{account_id}`, `/bank-accounts/{account_id}/ledger`, `/cash-transactions/{txn_id}/reconcile` |
| `bank_reconciliation.py` | 23 | 431 | `/bank-reconciliation/auto-match`, `/bank-reconciliation/formats`, `/bank-reconciliation/formats/{format_id}`, `/bank-reconciliation/holding`, `/bank-reconciliation/import`, `/bank-reconciliation/import-file` … |
| `budgets.py` | 9 | 174 | `/finance/budget-check`, `/finance/budget-keys`, `/finance/budget-rules`, `/finance/budget-vs-actual`, `/finance/budgets`, `/finance/budgets/{budget_id}` |
| `cash.py` | 4 | 169 | `/cash-transactions`, `/cash-transactions/summary`, `/cash-transactions/{txn_id}/void` |
| `cash_advances.py` | 17 | 145 | `/cash-advance-settlements`, `/cash-advance-settlements/{stl_id}`, `/cash-advance-settlements/{stl_id}/approve`, `/cash-advance-settlements/{stl_id}/reject`, `/cash-advance-settlements/{stl_id}/submit`, `/cash-advances` … |
| `categories.py` | 5 | 165 | `/product-categories`, `/product-categories/{category_id}`, `/product-motifs` |
| `closing.py` | 6 | 114 | `/finance/closing`, `/finance/closing/close`, `/finance/closing/preview`, `/finance/closing/status`, `/finance/closing/{closing_id}/reclose`, `/finance/closing/{closing_id}/reopen` |
| `color_library.py` | 5 | 72 | `/color-library`, `/color-library/nearest`, `/color-library/{color_id}` |
| `config.py` | 12 | 305 | `/effective`, `/explain`, `/health`, `/history`, `/impact-apply`, `/impact-preview` … |
| `consolidation.py` | 7 | 133 | `/consolidation/sync-g6`, `/finance/consolidation/eliminations`, `/finance/consolidation/eliminations/sync-from-pairs`, `/finance/consolidation/eliminations/{elim_id}`, `/finance/consolidation/ic-candidates`, `/finance/consolidation/summary` |
| `contra_bons.py` | 24 | 329 | `/contra-bons`, `/contra-bons/bank-line-candidates/{line_id}`, `/contra-bons/exchange-schedules`, `/contra-bons/meta`, `/contra-bons/prepare`, `/contra-bons/run-reminder` … |
| `costing.py` | 2 | 27 | `/wac`, `/wac/{product_id}` |
| `crm.py` | 21 | 416 | `/collection-reminders`, `/collection-reminders/mark`, `/collection-worklist`, `/credit-overrides`, `/credit-overrides/{override_id}/decision`, `/customers/{customer_id}/360` … |
| `crm_omnichannel.py` | 10 | 204 | `/crm/interactions`, `/crm/interactions/{intx_id}`, `/crm/leads`, `/crm/leads/board`, `/crm/leads/{lead_id}`, `/crm/leads/{lead_id}/convert` … |
| `customer_feedback.py` | 5 | 95 | `/customer-feedback`, `/customer-feedback/meta`, `/customer-feedback/summary`, `/customer-feedback/{fb_id}` |
| `customer_prices.py` | 9 | 219 | `/customer-prices`, `/customer-prices/export`, `/customer-prices/floor`, `/customer-prices/import`, `/customer-prices/quote`, `/customer-prices/records` … |
| `customers.py` | 4 | 219 | `/customers`, `/customers/{customer_id}`, `/customers/{customer_id}/addresses` |
| `cycle_count.py` | 8 | 248 | `/cycle-count/sessions`, `/cycle-count/sessions/{session_id}`, `/cycle-count/sessions/{session_id}/approve`, `/cycle-count/sessions/{session_id}/items`, `/cycle-count/sessions/{session_id}/items/{item_id}`, `/cycle-count/sessions/{session_id}/reject` … |
| `dashboard.py` | 1 | 119 | `/dashboard` |
| `data_hygiene.py` | 9 | 82 | `/data-hygiene/location/{collection}/{doc_id}`, `/data-hygiene/log`, `/data-hygiene/log/{log_id}/revert`, `/data-hygiene/preview`, `/data-hygiene/run`, `/data-hygiene/summary` … |
| `deliveries.py` | 9 | 119 | `/whatsapp/recipient/{doc_type}/{source_id}`, `/whatsapp/rules`, `/whatsapp/rules/{rule_id}`, `/whatsapp/send`, `/whatsapp/settings`, `/{doc_type}/{source_id}` |
| `design_gallery.py` | 19 | 348 | `/design-gallery`, `/design-gallery-ai/status`, `/design-gallery/{gallery_id}`, `/design-gallery/{gallery_id}/ai-illustrate`, `/design-gallery/{gallery_id}/approve`, `/design-gallery/{gallery_id}/autotag` … |
| `design_requests.py` | 15 | 306 | `/design-requests`, `/design-requests-for-so/{so_id}`, `/design-requests/meta`, `/design-requests/{req_id}`, `/design-requests/{req_id}/approve`, `/design-requests/{req_id}/assign` … |
| `documents.py` | 15 | 363 | `/document-templates`, `/document-templates/{template_id}`, `/documents/barcode`, `/documents/generate`, `/documents/preview/{order_id}`, `/documents/ref-types` … |
| `entities.py` | 11 | 232 | `/entities`, `/entities/count`, `/entities/{entity_id}`, `/entities/{entity_id}/archive`, `/entities/{entity_id}/audit`, `/entities/{entity_id}/deactivation-impact` … |
| `entity_masters.py` | 7 | 99 | `/entity-masters`, `/entity-masters/{kind}`, `/entity-masters/{kind}/effective`, `/entity-masters/{kind}/{row_id}`, `/entity-masters/{kind}/{row_id}/override` |
| `enums.py` | 5 | 124 | `/enums`, `/enums/products/validate`, `/enums/stage-transitions`, `/enums/stage-transitions/validate`, `/enums/{name}` |
| `esign.py` | 4 | 69 | `/request`, `/signatures/{doc_type}/{source_id}`, `/verify`, `/verify/{code}` |
| `finance_analytics.py` | 3 | 66 | `/finance/cashflow-forecast`, `/finance/profitability`, `/finance/tower` |
| `finance_bi.py` | 1 | 36 | `/finance/bi` |
| `finance_cases.py` | 13 | 191 | `/finance-cases`, `/finance-cases/playbooks`, `/finance-cases/policy`, `/finance-cases/reasons`, `/finance-cases/scan`, `/finance-cases/stats` … |
| `financial_statements.py` | 8 | 261 | `/finance/balance-sheet`, `/finance/balance-sheet/export.csv`, `/finance/cash-flow`, `/finance/cash-flow/export.csv`, `/finance/equity-changes`, `/finance/equity-changes/export.csv` … |
| `fixed_assets.py` | 10 | 196 | `/fixed-assets`, `/fixed-assets/meta`, `/fixed-assets/run-depreciation`, `/fixed-assets/summary`, `/fixed-assets/{asset_id}`, `/fixed-assets/{asset_id}/dispose` … |
| `fulfillment.py` | 3 | 49 | `/fulfillment/wizard/{so_id}`, `/fulfillment/wizard/{so_id}/create-interco`, `/fulfillment/wizard/{so_id}/create-pr` |
| `gl.py` | 19 | 298 | `/gl/accounts`, `/gl/accounts/{code}`, `/gl/accounts/{code}/ledger`, `/gl/cash-accounts`, `/gl/consolidation`, `/gl/inventory-drift-explain` … |
| `home.py` | 5 | 98 | `/admin`, `/finance`, `/manager`, `/sales`, `/warehouse` |
| `hr.py` | 15 | 479 | `/hr/employees`, `/hr/employees/me`, `/hr/employees/{employee_id}`, `/hr/employees/{employee_id}/360`, `/hr/org-units`, `/hr/org-units/tree` … |
| `hr_analytics.py` | 1 | 23 | `/hr/analytics/summary` |
| `hr_attendance.py` | 21 | 514 | `/hr/attendance`, `/hr/attendance/clock-in`, `/hr/attendance/clock-out`, `/hr/attendance/import`, `/hr/attendance/ingest`, `/hr/attendance/manual` … |
| `hr_kpi.py` | 5 | 107 | `/hr/kpi`, `/hr/kpi/me`, `/hr/kpi/{kpi_id}` |
| `hr_leave.py` | 17 | 257 | `/hr/leave-balance/me`, `/hr/leave-balances`, `/hr/leave-balances/set`, `/hr/leave-calendar`, `/hr/leave-requests`, `/hr/leave-requests/me` … |
| `hr_payroll.py` | 15 | 217 | `/hr/payroll/runs`, `/hr/payroll/runs/preview`, `/hr/payroll/runs/{run_id}`, `/hr/payroll/runs/{run_id}/approve`, `/hr/payroll/runs/{run_id}/pay`, `/hr/payroll/runs/{run_id}/post-gl` … |
| `hr_tracking.py` | 9 | 251 | `/hr/field-tracks`, `/hr/field-tracks/latest`, `/hr/visits`, `/hr/visits/check-in`, `/hr/visits/me`, `/hr/visits/mine` … |
| `inbound_receiving.py` | 5 | 731 | `/inbound/tasks`, `/inbound/tasks/{task_id}/complete`, `/inbound/tasks/{task_id}/escalate`, `/inbound/tasks/{task_id}/resolve-escalation`, `/inbound/tasks/{task_id}/scan-receive` |
| `inbound_receiving_extra.py` | 7 | 269 | `/inbound/po/{po_id}/receiving-goods-document`, `/inbound/qc/queue`, `/inbound/tasks/{task_id}/preview-uom`, `/inbound/tasks/{task_id}/qc-decision`, `/inbound/tasks/{task_id}/uom-options`, `/receiving/uom-settings` |
| `incentive_rates.py` | 4 | 105 | `/incentive-rates`, `/incentive-rates/{rate_id}` |
| `input_tax.py` | 6 | 194 | `/input-tax-invoices`, `/input-tax-invoices/eligible-bills`, `/input-tax-invoices/{fpm_id}`, `/input-tax-invoices/{fpm_id}/cancel`, `/tax/vat-summary` |
| `inspections.py` | 14 | 391 | `/inspections`, `/inspections/export`, `/inspections/meta`, `/inspections/meta/ref-docs`, `/inspections/queue/qc-tasks`, `/inspections/{ins_id}` … |
| `integrations.py` | 3 | 61 | `/admin/integrations`, `/admin/integrations/gemini/test` |
| `interco.py` | 34 | 477 | `/interco/accounts`, `/interco/accounts/{from_entity_id}/{to_entity_id}`, `/interco/accounts/{payer_entity_id}/{payee_entity_id}/remind`, `/interco/contracts`, `/interco/margin-by-product`, `/interco/margin-report` … |
| `interco_loans.py` | 8 | 130 | `/interco/loans`, `/interco/loans/meta`, `/interco/loans/{loan_id}`, `/interco/loans/{loan_id}/cancel`, `/interco/loans/{loan_id}/disburse`, `/interco/loans/{loan_id}/repay` … |
| `internal_requests.py` | 9 | 225 | `/internal-requests`, `/internal-requests-availability/{product_id}`, `/internal-requests/meta`, `/internal-requests/{req_id}`, `/internal-requests/{req_id}/cancel`, `/internal-requests/{req_id}/convert` … |
| `inventory.py` | 12 | 393 | `/history/{product_id}`, `/inventory/balances`, `/inventory/initial-stock`, `/inventory/movements`, `/inventory/putaway`, `/inventory/putaway/queue` … |
| `invoices.py` | 3 | 153 | `/invoices`, `/sales-orders/{order_id}/invoices`, `/sales-orders/{order_id}/simulate-payment` |
| `label_printer.py` | 2 | 144 | `/labels/generate`, `/labels/preview` |
| `landed_cost.py` | 10 | 391 | `/landed-costs`, `/landed-costs/payables/summary`, `/landed-costs/{voucher_id}`, `/landed-costs/{voucher_id}/approve`, `/landed-costs/{voucher_id}/cancel`, `/landed-costs/{voucher_id}/pay` … |
| `logistics.py` | 15 | 198 | `/deliveries`, `/deliveries/{delivery_id}`, `/deliveries/{delivery_id}/photos`, `/deliveries/{delivery_id}/photos/{photo_id}`, `/deliveries/{delivery_id}/positions`, `/deliveries/{delivery_id}/positions/{pos_id}` … |
| `lots.py` | 17 | 353 | `/lots`, `/lots/merge`, `/lots/settings`, `/lots/stats`, `/lots/unassigned-rolls`, `/lots/{lot_id}` … |
| `makloon_orders.py` | 15 | 256 | `/makloon-orders`, `/makloon-orders/claims`, `/makloon-orders/claims/stats`, `/makloon-orders/estimate`, `/makloon-orders/{mko_id}`, `/makloon-orders/{mko_id}/cancel` … |
| `makloons.py` | 6 | 149 | `/makloons`, `/makloons/{makloon_id}`, `/makloons/{makloon_id}/scorecard` |
| `notifications.py` | 5 | 118 | `/notifications`, `/notifications/generate`, `/notifications/read-all`, `/notifications/unread-count`, `/notifications/{notification_id}/read` |
| `onboarding.py` | 3 | 84 | `/onboarding`, `/onboarding/reset`, `/onboarding/{task_id}/complete` |
| `outbound_picking.py` | 11 | 472 | `/outbound/loading-check/{session_id}/complete`, `/outbound/loading-check/{session_id}/scan`, `/outbound/so/{order_id}/loading-check`, `/outbound/so/{order_id}/loading-check/start`, `/outbound/tasks`, `/outbound/tasks/{task_id}/dispatch` … |
| `outbound_picking_extra.py` | 3 | 311 | `/outbound/so/{order_id}/surat-jalan`, `/shipments`, `/shipments/{shipment_id}/surat-jalan` |
| `payment_plans.py` | 14 | 261 | `/payment-plans`, `/payment-plans/by-doc/{doc_type}/{doc_id}`, `/payment-plans/meta`, `/payment-plans/preview`, `/payment-plans/{plan_id}`, `/payment-plans/{plan_id}/accrue` … |
| `payment_variance.py` | 8 | 179 | `/payment-variances`, `/payment-variances/assess`, `/payment-variances/meta`, `/payment-variances/pending`, `/payment-variances/receipt/{receipt_id}`, `/payment-variances/receipt/{receipt_id}/decide` … |
| `pdf.py` | 12 | 270 | `/branding/{entity_id}`, `/doc-types`, `/documents/{doc_type}`, `/preview`, `/render/{doc_type}/{source_id}`, `/sample/{doc_type}` … |
| `pegging.py` | 3 | 120 | `/inventory/rolls/{roll_id}/earmark`, `/pegging/rolls` |
| `period_unlocks.py` | 6 | 107 | `/finance/period-unlocks`, `/finance/period-unlocks/active`, `/finance/period-unlocks/reclose-expired`, `/finance/period-unlocks/{plu_id}/approve`, `/finance/period-unlocks/{plu_id}/reject` |
| `po_board.py` | 2 | 90 | `/purchase-orders/board`, `/purchase-orders/{po_id}/stage` |
| `pos.py` | 3 | 44 | `/pos/best-sellers`, `/pos/frequently-bought-together`, `/pos/substitutes` |
| `price_approvals.py` | 15 | 584 | `/price-approvals`, `/price-approvals/effective`, `/price-approvals/hint`, `/price-approvals/stats/summary`, `/price-approvals/{approval_id}`, `/price-approvals/{approval_id}/approve` … |
| `pricelist.py` | 8 | 163 | `/pricelist`, `/pricelist/export`, `/pricelist/import`, `/pricelist/override/{product_id}`, `/pricelist/records`, `/pricelist/{price_id}` |
| `process_recipes.py` | 5 | 142 | `/process-recipes`, `/process-recipes/forecast`, `/process-recipes/{recipe_id}` |
| `product_media.py` | 9 | 186 | `/product-catalog/meta`, `/products/{product_id}/catalog-relations`, `/products/{product_id}/media`, `/products/{product_id}/media/from-design`, `/products/{product_id}/media/generate-mockup`, `/products/{product_id}/media/{media_id}` … |
| `product_templates.py` | 10 | 135 | `/product-templates`, `/product-templates/detach`, `/product-templates/resolve-orphans`, `/product-templates/{template_id}`, `/product-templates/{template_id}/assign`, `/product-templates/{template_id}/generate-variants` … |
| `product_traceability.py` | 1 | 238 | `/products/{product_id}/purchase-history` |
| `production.py` | 12 | 228 | `/production/boms`, `/production/boms/{bom_id}`, `/production/summary`, `/production/work-orders`, `/production/work-orders/{wo_id}`, `/production/work-orders/{wo_id}/cancel` … |
| `products.py` | 6 | 331 | `/products`, `/products/sales-owners`, `/products/{product_id}`, `/products/{product_id}/stock-breakdown` |
| `purchase_orders.py` ⚠️>800 | 7 | 847 | `/purchase-orders`, `/purchase-orders/resolve-sourcing`, `/purchase-orders/{po_id}`, `/purchase-orders/{po_id}/amend`, `/purchase-orders/{po_id}/approve`, `/purchase-orders/{po_id}/reject` |
| `purchase_orders_extra.py` | 8 | 211 | `/purchase-orders/blanket`, `/purchase-orders/payables/summary`, `/purchase-orders/{blanket_id}/call-off`, `/purchase-orders/{blanket_id}/close-contract`, `/purchase-orders/{po_id}/cancel`, `/purchase-orders/{po_id}/close` … |
| `purchase_requisitions.py` | 14 | 256 | `/purchase-requisitions`, `/purchase-requisitions/reorder-suggestions`, `/purchase-requisitions/{pr_id}`, `/purchase-requisitions/{pr_id}/approve`, `/purchase-requisitions/{pr_id}/cancel`, `/purchase-requisitions/{pr_id}/convert-to-po` … |
| `purchase_returns.py` | 14 | 240 | `/purchase-returns`, `/purchase-returns/source-rolls`, `/purchase-returns/status-counts`, `/purchase-returns/{return_id}`, `/purchase-returns/{return_id}/approve`, `/purchase-returns/{return_id}/goods-back` … |
| `putaway_orders.py` | 7 | 95 | `/putaway-orders`, `/putaway-orders/suggest`, `/putaway-orders/{order_id}/confirm-arrival`, `/putaway-orders/{order_id}/dispatch`, `/putaway-orders/{order_id}/resolve-exception`, `/wms/health-dashboard` |
| `qc_inspection.py` | 5 | 119 | `/inbound/qc/tasks/{task_id}/rolls`, `/inbound/rolls/{roll_id}/inspect`, `/inventory/rolls/{roll_id}/grade-history`, `/inventory/rolls/{roll_id}/grade-override`, `/qc/grade-thresholds` |
| `reporting.py` | 6 | 261 | `/reports/order-velocity`, `/reports/reservation-funnel`, `/reports/stock-aging`, `/reports/summary`, `/reports/top-customers`, `/reports/warehouse-utilization` |
| `return_policies.py` | 6 | 220 | `/sales-return-policies`, `/sales-return-policies/eligibility`, `/sales-return-policies/{policy_id}` |
| `rfid.py` | 43 | 610 | `/rfid/cycle-count/start`, `/rfid/cycle-count/{session_id}/complete`, `/rfid/cycle-counts`, `/rfid/cycle-counts/{cc_id}`, `/rfid/device-health`, `/rfid/device-jobs/pending` … |
| `rfq.py` | 8 | 216 | `/rfqs`, `/rfqs/{rfq_id}`, `/rfqs/{rfq_id}/award`, `/rfqs/{rfq_id}/cancel`, `/rfqs/{rfq_id}/compare`, `/rfqs/{rfq_id}/quote` … |
| `rnd.py` | 35 | 722 | `/rnd/labdip-history`, `/rnd/lifecycle-board`, `/rnd/meta`, `/rnd/reports/designer-kpi`, `/rnd/reports/designer-kpi/export`, `/rnd/reports/designer-kpi/report` … |
| `rnd_org.py` | 3 | 72 | `/rnd/divisions`, `/rnd/divisions/members` |
| `saga_locks.py` | 2 | 38 | `/saga-locks`, `/saga-locks/{collection}/{doc_id}/release` |
| `sales_orders.py` | 3 | 590 | `/sales-orders`, `/sales-orders/{order_id}` |
| `sales_orders_extra.py` ⚠️>800 | 17 | 805 | `/sales-orders`, `/sales-orders/frequent-products`, `/sales-orders/preview-allocation`, `/sales-orders/preview-lots`, `/sales-orders/preview-roll-reconcile`, `/sales-orders/stats/summary` … |
| `sales_returns.py` | 26 | 726 | `/credit-notes`, `/credit-notes/{cn_id}`, `/returns/chain/{doc_id}`, `/sales-returns`, `/sales-returns/meta/complaint-reasons`, `/sales-returns/status-counts` … |
| `sample_sales.py` | 8 | 127 | `/sample-prices`, `/sample-prices/{template_id}`, `/sample-requests`, `/sample-requests/quote`, `/sample-requests/{request_id}`, `/sample-requests/{request_id}/cancel` … |
| `scheduler.py` | 10 | 215 | `/scheduler/digest-preview`, `/scheduler/jobs`, `/scheduler/jobs/{job_id}/run`, `/scheduler/runs`, `/scheduler/settings`, `/scheduler/summary` … |
| `settings.py` | 10 | 161 | `/payment-terms`, `/payment-terms/{term_id}`, `/payment-terms/{term_id}/override`, `/settings`, `/settings/compute-tax`, `/settings/effective` … |
| `so_approvals.py` | 8 | 407 | `/approvals/backlog`, `/approvals/queue`, `/approvals/queue-board/{key}`, `/sales-orders/{order_id}/approvals/{approval_id}/decide`, `/sales-orders/{order_id}/approvals/{approval_id}/evidence`, `/sales-orders/{order_id}/approvals/{approval_id}/evidence/{att_id}/download` … |
| `special_orders.py` | 11 | 726 | `/special-orders`, `/special-orders/{order_id}`, `/special-orders/{order_id}/approve`, `/special-orders/{order_id}/convert-to-so`, `/special-orders/{order_id}/create-pr`, `/special-orders/{order_id}/create-sku` … |
| `stock_buckets.py` | 9 | 105 | `/stock/atp`, `/stock/buckets`, `/stock/hold`, `/stock/hold/{hold_id}/release`, `/stock/holds`, `/stock/pending-so` … |
| `store_credit.py` | 7 | 138 | `/store-credit`, `/store-credit/adjust`, `/store-credit/balance`, `/store-credit/entries/{entry_id}/reverse`, `/store-credit/ledger`, `/store-credit/open-orders` … |
| `supplier_contracts.py` | 12 | 200 | `/makloon-partners/scorecard`, `/supplier-contracts`, `/supplier-contracts/policy`, `/supplier-contracts/resolve`, `/supplier-contracts/stats`, `/supplier-contracts/tariff-preview` … |
| `supplier_items.py` | 10 | 196 | `/supplier-items`, `/supplier-items/import`, `/supplier-items/import-file`, `/supplier-items/import-template`, `/supplier-items/lookup`, `/supplier-items/stats` … |
| `suppliers.py` | 13 | 384 | `/supplier-price-list/resolve`, `/supplier-price-list/{entry_id}`, `/suppliers`, `/suppliers/{supplier_id}`, `/suppliers/{supplier_id}/360`, `/suppliers/{supplier_id}/price-list` … |
| `tax_center.py` | 4 | 83 | `/tax/pph-records`, `/tax/pph-records/{record_id}`, `/tax/summary` |
| `tax_invoices.py` | 7 | 97 | `/sales-orders/{order_id}/tax-invoice`, `/tax-invoices`, `/tax-invoices/{fkt_id}`, `/tax-invoices/{fkt_id}/cancel`, `/tax-invoices/{fkt_id}/document`, `/tax-invoices/{fkt_id}/nsfp` … |
| `transfers.py` | 8 | 659 | `/transfers`, `/transfers/inter-company`, `/transfers/{transfer_id}`, `/transfers/{transfer_id}/approve`, `/transfers/{transfer_id}/reject`, `/transfers/{transfer_id}/status` |
| `uom_conversions.py` | 10 | 226 | `/uom-conversions/catalog`, `/uom-conversions/check-variance`, `/uom-conversions/convert`, `/uom-conversions/rules`, `/uom-conversions/rules/{rule_id}`, `/uom-conversions/rules/{rule_id}/status` … |
| `uoms.py` | 5 | 163 | `/uoms`, `/uoms/vocab`, `/uoms/{uom_id}` |
| `users.py` | 10 | 206 | `/hr-employees-available`, `/users`, `/users/count`, `/users/{user_id}`, `/users/{user_id}/reactivate`, `/users/{user_id}/reset-password` … |
| `vehicle_logs.py` | 9 | 214 | `/vehicle-usage-logs`, `/vehicle-usage-logs/summary`, `/vehicle-usage-logs/{log_id}`, `/vehicles`, `/vehicles/{veh_id}` |
| `vendor_bills.py` | 11 | 611 | `/purchase-orders/{po_id}/billing-context`, `/vendor-bills`, `/vendor-bills/payables/summary`, `/vendor-bills/status-counts`, `/vendor-bills/{bill_id}`, `/vendor-bills/{bill_id}/approve` … |
| `warehouse_sites.py` | 5 | 77 | `/warehouse-sites`, `/warehouse-sites/seed-blueprint`, `/warehouse-sites/{site_id}` |
| `warehouses.py` | 7 | 223 | `/warehouses`, `/warehouses/{warehouse_id}`, `/warehouses/{warehouse_id}/locations`, `/warehouses/{warehouse_id}/occupancy`, `/warehouses/{warehouse_id}/structure` |
| `wilayah.py` | 8 | 55 | `/wilayah/countries`, `/wilayah/districts`, `/wilayah/postal-code/{code}`, `/wilayah/provinces`, `/wilayah/regencies`, `/wilayah/search` … |
| `wms.py` | 5 | 215 | `/wms/tasks`, `/wms/tasks/outbound-from-order/{order_id}`, `/wms/tasks/{task_id}/advance`, `/wms/tasks/{task_id}/scan` |
| `work_desks.py` | 9 | 196 | `/desks/me`, `/finance/desk`, `/md/desk`, `/sales-admin/desk`, `/sales-admin/orders/{order_id}/fulfillment`, `/sales-admin/orders/{order_id}/fulfillment-decision` … |

## Backend — service

| Berkas | Baris | Ringkas |
|---|---:|---|
| `advance_report_service.py` | 111 | KEB-PDPT (Sesi #090) — Laporan Uang Muka Pelanggan. |
| `alert_ops_service.py` | 335 | PS-21 — Generator ALERT OPERASIONAL (quick win di atas mesin R6.5/R6.6). |
| `alert_service.py` | 319 | R6.5 — Generator ALERT untuk Scheduler & Notifikasi (Kain Nusantara). |
| `amendment_service.py` | 752 | FASE G-1 — **FONDASI AMANDEMEN**: tidak ada lagi perubahan angka secara diam-diam. |
| `app_url.py` | 79 | app_url — SATU sumber kebenaran **URL publik aplikasi** (untuk QR & tautan cetak). |
| `approval_backlog_service.py` | 695 | services/approval_backlog_service.py — SATU sumber "apa yang menunggu keputusan". |
| `approval_matrix_service.py` | 512 | PS-20 (D-14) — **Penegakan matriks persetujuan divisi** + antrean "Persetujuan Saya". |
| `approval_reminder.py` | 133 | services/approval_reminder.py — PENGINGAT HARIAN "keputusan yang menunggu Anda". |
| `approval_service.py` | 138 | services/approval_service.py — **ATURAN AMBANG PERSETUJUAN** (`approval_rules`). |
| `ar_aging_service.py` | 460 | EPIC7-A — AR / Piutang Aging (read/derived report). |
| `ar_receipt_service.py` | 648 | AR Receipt service (EPIC3B) — Penerimaan pembayaran customer + aplikasi ke SO. |
| `atomic_claim.py` | 61 | Klaim atomik dokumen induk untuk endpoint tulis multi-koleksi (T-01 Opsi B — saga). |
| `backorder_service.py` | 128 | Backorder service (Sub-fase 1.6) — auto-fulfill lifecycle. |
| `bank_recon_service.py` | 1347 | FASE G-8 — REKONSILIASI BANK OTOMATIS (skor berbobot · split · aturan · titipan). |
| `bank_service.py` | 131 | Bank/Cash Accounts service (EPIC7-B) — multi-akun kas & bank + rekonsiliasi. |
| `bank_statement_parser.py` | 512 | FASE G-8 — PARSER MUTASI BANK MULTI-FORMAT. |
| `base_fabric.py` | 26 | Kain dasar — rujukan induk master data (mis. kain polos woven yang menjadi bahan printing). |
| `blanket_po_service.py` | 348 | Blanket / Contract PO service (P2 — call-off). |
| `budget_service.py` | 519 | R6.3 — Budget Control penuh: Anggaran vs Komitmen vs Realisasi + enforcement. |
| `cash_advance_service.py` | 482 | Service — Cash Advance (Form PD) + Pertanggungjawaban (Settlement) + Expense Categories. |
| `cash_entity_service.py` | 98 | FASE E-7 (E7.4 · keputusan pemilik 3a) — **KAS TINGKAT GRUP DIHAPUS**. |
| `cash_flow_service.py` | 124 | FINANCE — Laporan Arus Kas (Cash Flow Statement) metode TAK LANGSUNG. |
| `cash_ledger.py` | 73 | R5.3 — Cash ledger helper untuk refund retur (sales & purchase). |
| `cashflow_forecast_service.py` | 138 | FINANCE — Proyeksi Arus Kas (Cash Flow Forecast) (EPIC P1-3). |
| `catalog_access.py` | 53 | Pagar bersama template, SKU, media dan relasi R&D. Produk tetap SHARED. |
| `catalog_rules.py` | 102 | Kontrak murni induk/axis/SKU; digunakan R&D, generator, editor dan impor. |
| `closing_service.py` | 421 | FINANCE — Tutup Buku (Period Closing) bulanan & tahunan. |
| `color_service.py` | 173 | M0 — Color Library service (Pantone-style master warna). |
| `config_currency.py` | 64 | FASE G-0 — Konsumen nyata untuk `finance.base_currency` & `finance.fiscal_year_end_month`. |
| `config_health.py` | 116 | FASE G-0 — KESEHATAN KONFIGURASI: apakah setiap setting benar-benar tersambung? |
| `config_impact_service.py` | 258 | FASE G-0 — DAFTAR DAMPAK (Blast-Radius Picker). |
| `config_resolver.py` | 577 | FASE G-0 — CONFIG RESOLVER: nilai efektif berlapis + jejak "kenapa begini" + berlaku-sejak. |
| `config_service.py` | 545 | Config service (Fase 1A) — Configuration Foundation. |
| `config_simulator.py` | 598 | FASE G-0 — SIMULATOR KONFIGURASI ("Coba dulu"). |
| `consolidation_service.py` | 751 | FINANCE — Konsolidasi Grup + Eliminasi Intercompany. |
| `contra_bon_reminder.py` | 231 | FASE G-7 — **JADWAL TUKAR FAKTUR** per supplier + pengingat otomatis. |
| `contra_bon_scan.py` | 244 | FASE G-7 — Pemeriksa invarian **KONTRABON** (INV-CB-01..04). |
| `contra_bon_service.py` | 1376 | FASE G-7 — KONTRABON ADVANCED (siklus tukar faktur supplier). |
| `contract_service.py` | 591 | FASE D — KONTRAK MITRA/SUPPLIER (`supplier_contracts`) + MESIN TARIF CONFIGURABLE. |
| `costing_service.py` | 133 | Costing service (EPIC3A) — Weighted Average Cost (WAC) per produk/entitas. |
| `crm_omnichannel_service.py` | 247 | CRM Omnichannel (MVP manual) — Lead pipeline + timeline interaksi. |
| `csv_money.py` | 39 | SATU definisi “cara membaca angka rupiah dari CSV” untuk seluruh sistem. |
| `customer_feedback_service.py` | 153 | FEEDBACK / KOMPLAIN PELANGGAN per Sales Order (2026-09, sesi #075). |
| `customer_price_service.py` | 557 | F1b (D-14) — **Daftar Harga per Pelanggan** (customer pricelist) dengan histori, |
| `customer_service.py` | 437 | Customer/CRM service (KN_17 CRM-lite). |
| `cycle_count_service.py` | 115 | CYCLE COUNT RFID — stock opname kilat via sweep handheld. |
| `data_hygiene_service.py` | 204 | Kebersihan Data (K-1/K-2 otomatis) — normalisasi EYD nama & nomor telepon pada data LAMA. |
| `delivery_service.py` | 267 | delivery_service.py — Pengiriman dokumen via WhatsApp (mode simulasi default) + |
| `demo_seed_service.py` | 97 | Demo Seed Service |
| `design_gallery_service.py` | 549 | HRD H5 services — Design Gallery (motif kain) + upload gambar (storage lokal). |
| `design_request_service.py` | 561 | FASE D — **PERMINTAAN DESAIN** (`<ENT>/DSR-#####`) + rapor desainer. |
| `digest_service.py` | 217 | R6.6 — RINGKASAN HARIAN (Daily Digest) untuk kanal WhatsApp. |
| `doc_refs_service.py` | 868 | FASE G-4 — **RELASI DOKUMEN TERSIMPAN** (`refs[]` dua arah) + Jejak Dokumen. |
| `document_relations_service.py` | 285 | EPIC 6 — Document Relations / Process Timeline service. |
| `dual_qty_service.py` | 314 | FASE U — DUA SATUAN (jumlah roll + ukuran) · satu pintu untuk semua dokumen. |
| `entity_context_service.py` | 165 | F0-A — Entity identity & context helper (Multi-Entity foundation). |
| `entity_lifecycle_service.py` | 571 | FASE E-1 — SIKLUS HIDUP BADAN USAHA (satu pintu untuk semua pagar). |
| `entity_master_service.py` | 583 | entity_master_service (FASE E-4 · E4a) — MASTER BERLAPIS: **global → badan usaha**. |
| `entity_provisioning_service.py` | 193 | F0-F + FASE E-1 — Provisioning & VALIDASI badan usaha (SATU JALUR). |
| `entity_readiness_service.py` | 135 | FASE E-1 (E1.9) — DAFTAR KESIAPAN BADAN USAHA. |
| `equity_statement_service.py` | 59 | FINANCE — Laporan Perubahan Ekuitas (Statement of Changes in Equity). |
| `escalation_service.py` | 166 | R6.6 — ESKALASI BERTINGKAT alert yang belum ditindak. |
| `esign_service.py` | 193 | esign_service.py — Logika e-sign: request OTP, verifikasi + simpan tanda tangan, |
| `finance_bi_service.py` | 133 | FINANCE — BI Keuangan (dashboard analitik) diturunkan dari GL. |
| `finance_case_actions.py` | 529 | FASE G-9 — EKSEKUTOR AKSI PLAYBOOK KASUS KEUANGAN. |
| `finance_case_playbooks.py` | 245 | FASE G-9 — REGISTRY 11 PLAYBOOK KASUS KEUANGAN. |
| `finance_case_scan.py` | 259 | FASE G-9 — PEMINDAI KASUS OTOMATIS + PEMERIKSA INVARIAN. |
| `finance_case_service.py` | 527 | FASE G-9 — PUSAT KASUS KEUANGAN (Finance Exception Desk). |
| `finance_tower_service.py` | 118 | FINANCE — Control Tower (Dashboard Keuangan terpadu) (EPIC P1-5). |
| `financial_statement_service.py` | 287 | FINANCE — Laporan Keuangan (Laba-Rugi & Neraca) diturunkan dari GL. |
| `fixed_asset_service.py` | 505 | R6.2 — Fixed Assets & Depresiasi (straight-line) + disposal gain/loss. |
| `fulfillment_decision_service.py` | 286 | FASE E-8 (E8.10b#4 · US16) — **KEPUTUSAN PEMENUHAN** milik Admin Sales. |
| `fulfillment_service.py` | 358 | Fulfillment & ATP service (Fase 1 / Sub-fase 1.4 — ATP & Fulfillment Modes). |
| `fulfillment_status.py` | 117 | Fulfillment status engine (Sub-fase 1.8). |
| `fulfillment_wizard_service.py` | 163 | FASE R7 — FULFILLMENT WIZARD: matriks skenario S1–S8 menjadi aksi terpandu. |
| `gemini_image_service.py` | 193 | FB-01 — Ilustrasi AI Galeri Desain via Google Gemini "Nano Banana Pro" (SDK google-genai LANGSUNG). |
| `gl_service.py` | 3254 | EPIC7-C — General Ledger & Chart of Accounts (akuntansi inti). |
| `grade_service.py` | 161 | Grade governance service — Fase A · PS-09 · D-01/D-19/D-23. |
| `group_partner_service.py` | 311 | FASE E-7 (E7.2 + E7.7) — **PAGAR "LAWAN TRANSAKSI TERNYATA PT SENDIRI"**. |
| `home_service.py` | 394 | EPIC 1 — Agregasi Home/landing per role (Control Tower / Performa Saya). |
| `hr_ai_service.py` | 117 | H5 service — AI auto-tag motif via Anthropic Claude (SDK LANGSUNG, bukan Emergent). |
| `hr_analytics_service.py` | 200 | HRD H6 service — HR Analytics (Dashboard BI SDM). |
| `hr_attendance_service.py` | 262 | HRD H1 services — Absensi (attendance). |
| `hr_kpi_service.py` | 122 | HRD H5 services — KPI Design (input manual per karyawan/periode + rekap). |
| `hr_leave_service.py` | 337 | HRD H3 services — Cuti, Izin & Lembur (Leave/Permit & Overtime). |
| `hr_payroll_pdf.py` | 111 | HRD H4 — Payslip PDF (reportlab). Slip gaji ringkas, profesional, Bahasa Indonesia. |
| `hr_payroll_service.py` | 457 | HRD H4 — Payroll & Payslip engine + run lifecycle. |
| `hr_service.py` | 176 | HRD services (FASE H0) — helper murni-orchestration untuk modul HR. |
| `input_tax_service.py` | 173 | Faktur Pajak Masukan (tax_invoices_in) service — Fase 5.5 / P0-3. |
| `inspection_service.py` | 943 | FASE I — **INSPEKSI & QC SEBAGAI DOKUMEN** (`<ENT>/INS-#####`). |
| `integrations_service.py` | 105 | H5 service — Integrasi pihak ketiga (config runtime di system_settings). |
| `interco_loan_service.py` | 274 | FASE E-7 (E7f) — **PINJAMAN UANG ANTAR-PT** (`<ENT>/ICL-#####`). |
| `interco_margin.py` | 423 | FASE G-6b — **RAPOR MARGIN GRUP** antar-PT (realized vs unrealized). |
| `interco_money_service.py` | 213 | FASE E-7 (E7f + E7g) — **UANG & ASET ANTAR-PT** yang bukan jual-beli. |
| `interco_reminder.py` | 179 | FASE G-6b — **PENGINGAT SETTLEMENT** saldo antar-PT yang menganggur. |
| `interco_return_service.py` | 855 | FASE G-6b — **RETUR ANTAR-PT** (jalan resmi setelah barangnya sudah berpindah). |
| `interco_service.py` | 1697 | FASE G-6 — Layanan **TRANSAKSI ANTAR ENTITAS** (jual-beli antar-PT dalam grup). |
| `interco_tax_service.py` | 387 | FASE G-6b — **FAKTUR PAJAK INTERNAL** untuk transaksi antar-PT ber-PPN. |
| `internal_request_service.py` | 486 | FASE E-7 (E7.1 · gelombang 2 “E7d”) — **PERMINTAAN INTERNAL** (`<ENT>/PIN-#####`). |
| `inventory_drift_watch.py` | 127 | services/inventory_drift_watch.py — PEMANTAU DRIFT PERSEDIAAN (INV-GL-DRIFT). |
| `inventory_service.py` | 207 | Inventory service: reservation expiry projections & document rendering. |
| `label_printer_service.py` | 198 | Label printer service: Generate ZPL and ESC/POS commands for barcode labels. |
| `landed_cost_service.py` | 238 | Landed Cost service (Fase 5.4 — P0-5). |
| `line_scope.py` | 434 | FASE L — PAGAR LINI PRODUK (woven · knit · printing · dan lini baru berikutnya). |
| `loading_check_service.py` | 115 | FASE R4 — FINAL LOADING CHECK: sweep handheld vs manifest SO sebelum naik mobil. |
| `location_service.py` | 188 | Location (Zone→Rack→Level→Bin) & Putaway — Fase 5 (KN_15 §3.1 / KN_16 I11). |
| `logistics_service.py` | 391 | FB-02 — Modul Logistik (koleksi `logistics_deliveries`, SCOPED, nomor LG-). |
| `lot_migration.py` | 132 | FASE C — Migrasi & backfill lot (IDEMPOTEN). |
| `lot_service.py` | 627 | FASE C — LOT KELAS SATU (`inventory_lots`) · SSOT identitas batch & genealogi. |
| `lot_trace_service.py` | 248 | FASE C — Silsilah (genealogi), Recall, dan Label lot. |
| `makloon_calc_service.py` | 215 | FASE D — ESTIMASI OUTPUT MAKLOON BERBASIS GSM (PS-03) + EVALUASI SELISIH (PS-11). |
| `makloon_claim_service.py` | 348 | FASE D — SELISIH & KLAIM MAKLOON (PS-11 · keputusan **D-09**). |
| `makloon_order_service.py` | 1412 | M3 + FASE D — Makloon Order service: orkestrasi transaksi subkontrak (Procure→Process→Pay). |
| `makloon_service.py` | 150 | M1 — Makloon service: Makloon 360 + scorecard proses (dari data nyata). |
| `master_registry.py` | 466 | master_registry (FASE L, diperluas FASE T) — JEMBATAN master ↔ `domain_registry`. |
| `movement_label_service.py` | 269 | movement_label_service — nomor dokumen yang LAYAK DIBACA pada mutasi stok. |
| `notification_audience.py` | 189 | notification_audience — SATU penyelesai "siapa yang harus diberi tahu". |
| `notification_service.py` | 412 | Notification service — pembuatan notifikasi + generator dari event REAL. |
| `order_journey_service.py` | 258 | FASE E-8 (E8.14 · US12) — **PERJALANAN PESANAN** (read-only, untuk sales lapangan). |
| `payment_plan_service.py` | 655 | FASE G-2 — **RENCANA PEMBAYARAN FLEKSIBEL** (`payment_plans`). |
| `payment_variance_service.py` | 1238 | FASE G-3 — **SELISIH PEMBAYARAN: LEBIH & KURANG BAYAR** (`payment_variance_decisions`). |
| `pdf_engine.py` | 292 | pdf_engine.py — Mesin render PDF asli (server-side) untuk semua dokumen bisnis. |
| `pdf_resolvers.py` | 1053 | pdf_resolvers.py — Ubah dokumen sumber (per doc_type) menjadi CONTEXT ternormalisasi |
| `pdf_service.py` | 424 | pdf_service.py — Orkestrasi render dokumen: template config + branding entitas + |
| `penalty_service.py` | 595 | FASE G-2 — **DENDA KETERLAMBATAN SEBAGAI DOKUMEN** (`penalties`). |
| `period_unlock_service.py` | 278 | FASE G-5 — UNLOCK PERIODE BEROTORITAS ("wajib dua orang & menutup sendiri"). |
| `po_amendment_service.py` | 314 | Phase 7.2 — PO Amendment / Version History (logic extracted from router). |
| `po_board_service.py` | 621 | FASE P — **PAPAN PO PER LINI** (progres tahap seperti kertas kerja MD). |
| `pos_recommendation_service.py` | 116 | F-4b — POS advanced recommendations, dihitung dari histori `sales_orders` (TANPA AI, TANPA koleksi baru). |
| `pr_sourcing_service.py` | 722 | FASE E — SOURCING PR: routing `purchase|makloon` + realisasi PR → PO / Order Makloon. |
| `price_approval_service.py` | 267 | Sub-fase 1.7 + F1b — bagian **BERSAMA** alur Harga Khusus (`price_approvals`). |
| `price_guard_service.py` | 171 | F1b — SATU definisi **batas bawah harga jual** (price floor) untuk seluruh sistem. |
| `pricelist_service.py` | 418 | F1a — Pricelist per-entitas (harga jual per-PT) dengan histori & tanggal efektif. |
| `printer_stuck_watch.py` | 60 | Sesi 15 — label tertahan: antrean label menunggu > N menit tanpa printer online di gudang itu. |
| `process_recipe_service.py` | 114 | M1 — Process Recipe service: CRUD helper + forecast konversi (aman). |
| `product_exclusivity.py` | 109 | PS-20 — Produk eksklusif per sales ("PO sendiri"). |
| `product_media_service.py` | 108 | Media per SKU, lokal, ber-versi CAS. Foto nyata/mockup ditinjau sebelum sales melihat. |
| `product_template_service.py` | 341 | F1b — Product Templates & Variants (pendekatan ADDITIVE/non-destruktif). |
| `product_variant_service.py` | 226 | Satu induk, SKU tetap: jalur bersama untuk seluruh penulis produk. |
| `production_service.py` | 452 | R6.4 — Produksi In-House (BOM + Work Order). |
| `profitability_service.py` | 191 | FINANCE — Analisis Profitabilitas / Margin (EPIC P0-2 · R5.6). |
| `purchase_requisition_service.py` | 504 | Depth #2 — Purchase Requisition (PR) service + Reorder/Replenishment. |
| `purchase_return_service.py` | 832 | Depth #1 — Retur Beli (Purchase Return / Nota Debit). |
| `purchase_return_state.py` | 66 | R4 — Supplier RMA lifecycle untuk Retur Beli (Purchase Return). |
| `putaway_order_service.py` | 268 | FASE R2 — PUTAWAY ORDER (PA): dokumen pemindahan roll dari gedung transit ke |
| `qc_inspection_service.py` | 249 | QC 4-Point Inspection service — Fase 6.2 (P1). |
| `qc_service.py` | 308 | Depth #3a — QC Hold / Quarantine saat Goods Receipt. |
| `receiving_uom_service.py` | 502 | FASE F-1 — PENERIMAAN BERBASIS **SATUAN SUPPLIER** (lanjutan Fase B & Fase E). |
| `restock_service.py` | 274 | PS-21(a) — Repeat/Restock 1-klik dari Sales Order → Purchase Requisition. |
| `return_chain_service.py` | 323 | FASE E-9 (E9.6) — **JEJAK RANTAI RETUR**. |
| `return_policy_service.py` | 349 | R0 — Return Policy Engine (Master Data). |
| `return_service.py` | 1582 | Sub-fase 1.11 — Returns & Barang Sisa |
| `return_state.py` | 96 | R1 — State machine retur jual (Sales Return). |
| `rfid_incident_service.py` | 168 | FASE R6 — Insiden gate MERAH: alarm → acknowledge operator → resolve, |
| `rfid_ingest_service.py` | 164 | FASE R3 — Device Ingest API (kontrak hardware: gate Chainway UR300 / handheld / |
| `rfid_print_service.py` | 282 | FASE R1 — Print job tag RFID (bulk dari GR/roll transit) + sesi verifikasi handheld. |
| `rfid_service.py` | 403 | RFID service (Fase 5 — SIMULATOR). |
| `rfq_service.py` | 382 | RFQ / Quotation service — Fase 6.1 (P1 Sourcing). |
| `rnd_catalog_validation.py` | 55 | Validate source relations before saving any R&D specification. |
| `rnd_gate.py` | 130 | FASE F (PS-12) — **Penjaga lifecycle produk** + resolver kebijakan R&D. |
| `rnd_kpi_export.py` | 544 | PS-18 — **EKSPOR LAPORAN KPI DESAINER** (CSV · Excel · PDF). |
| `rnd_kpi_service.py` | 573 | PS-18 — Layanan **KPI DESAINER** (kinerja pelaksana R&D yang terhitung sendiri). |
| `rnd_org_service.py` | 95 | PS-17 — Layanan Organisasi R&D (divisi + anggota). |
| `rnd_sample_service.py` | 1178 | FASE F · PS-12/13/14/18/19 — Layanan **PERMINTAAN SAMPLE** (`md_samples`), |
| `rnd_sla_service.py` | 176 | PS-18 — **ESKALASI SLA SAMPLE R&D** (dari papan pasif menjadi pengingat aktif). |
| `rnd_spec_service.py` | 410 | FASE F · PS-12 — Layanan **SPESIFIKASI PRODUK versi R&D** (`md_specs`). |
| `role_desk_service.py` | 159 | U-2 (2026-09) — Meja kerja untuk 6 peran tersisa: admin, manager, sales, warehouse, designer, driver. |
| `role_reality_service.py` | 677 | **CEK KENYATAAN PERAN** — utang migrasi (ii) FASE E-8/E-6. |
| `roll_cost_history.py` | 88 | services/roll_cost_history.py — JEJAK setiap perubahan HPP satu roll. |
| `roll_service.py` | 1827 | Roll service (Fase 0.5) — Roll-as-SSOT inventory engine. |
| `roll_timeline_service.py` | 133 | JEJAK BARANG (Item Passport) — timeline satu roll lintas SEMUA dokumen. |
| `saga_lock_watch.py` | 93 | services/saga_lock_watch.py — PEMANTAU KUNCI SAGA MENGGANTUNG (T-01 Opsi B). |
| `sales_force_service.py` | 437 | Sales Force service (KN_17 §6) — KPI per salesperson + komisi (pencairan + tiered). |
| `sales_order_helpers.py` | 249 | Helper functions extracted from routers/sales_orders.py. |
| `sales_ownership.py` | 121 | FASE E-8 (E8.4 · US11) — **SATU definisi "Pesanan Saya"**. |
| `sample_sale_service.py` | 189 | §3-C Jual Sampel (keputusan pemilik 2026-09): harga per satuan roll (yard/meter) dari master |
| `scheduler_service.py` | 505 | R6.5 — Scheduler (APScheduler) untuk alert & notifikasi terjadwal. |
| `shipment_service.py` | 109 | Shipment service (Sub-fase 1.8) — partial/multi shipment, SSOT-safe. |
| `so_approvals.py` | 159 | F5 — Unified Approval SSOT pada Sales Order (`pending_approvals[]`). |
| `so_status.py` | 159 | F4 — SSOT Status SO 2-level: STAGE (induk, linear) + SUB-STATUS (anak, kontekstual). |
| `so_verify_service.py` | 306 | FASE E-8 (E8.13) — **VERIFIKASI ADMINISTRATIF** pesanan oleh Admin Sales. |
| `special_order_service.py` | 415 | Special Order Service - Sub-fase 1.12 |
| `status_history.py` | 50 | SSOT bentuk satu entri `status_history[]` — dipakai SEMUA koleksi. |
| `stock_analytics_service.py` | 260 | Stock Analytics service (Fase 5) — klasifikasi Fast/Slow/Dead + aging + kecepatan jual. |
| `stock_bucket_service.py` | 573 | F2 — Multi-bucket Stock: operasi WIP & Hold (Pending SO) + papan bucket. |
| `storage_service.py` | 107 | Local filesystem storage wrapper (FASE 5 — keputusan owner: storage LOKAL). |
| `store_credit_service.py` | 474 | R5.2 — Store Credit (Saldo Kredit Pelanggan) ledger service. |
| `supplier_item_service.py` | 442 | FASE E — SERVICE `supplier_items` (Barang Supplier / katalog versi supplier). |
| `supplier_service.py` | 485 | Depth #3 — Supplier Intelligence: Price-List resolution + Scorecard. |
| `tax_center_service.py` | 204 | EPIC 7 — Pusat Pajak (PPN + PPh) service. |
| `tax_invoice_service.py` | 321 | Faktur Pajak Jual (tax_invoices) service — Sub-fase 1.9. |
| `text_normalize.py` | 88 | K-1/K-2 (feedback klien 2026-09) — normalisasi penulisan (EYD) & nomor telepon/WhatsApp. |
| `tracking_service.py` | 113 | HRD H2 services — Live Field Tracking (WebSocket). |
| `turn_notification_service.py` | 181 | Notifikasi "giliran Anda" — setiap dokumen berpindah tahap, peran yang harus bertindak |
| `uom_rules_service.py` | 500 | FASE B — REGISTRY KONVERSI SATUAN **GLOBAL** + TOLERANSI (D-06/D-07). |
| `uom_service.py` | 503 | Sub-fase 1.13 — UOM Conversion Engine (Multi-UOM). |
| `user_admin_service.py` | 379 | FASE E-2 — AKUN PENGGUNA TERTAUT BADAN USAHA (via HR) & PENEGAKAN AKSES. |
| `variant_axes.py` | 41 | Sumbu varian yang dapat dikonfigurasi pemilik (rnd.variant_axes_default / _optional). |
| `vendor_bill_service.py` | 247 | Vendor Bill service (Fase 5.2 — P0-2) — 3-Way Matching PO ↔ GR ↔ Bill. |
| `wa_alert_service.py` | 278 | R6.5 — Kanal WhatsApp untuk notifikasi/alert (Kain Nusantara). |
| `warehouse_profile_service.py` | 188 | FASE R0 — Profil gudang: site (lokasi), peran gedung, rules penyimpanan, gate config. |
| `warehouse_scope_service.py` | 266 | FASE E-4 (E4.1) — GUDANG BERSAMA vs GUDANG KHUSUS BADAN USAHA. |
| `wilayah_service.py` | 213 | Wilayah (2026-09) — registry wilayah Indonesia (Kepmendagri 300.2.2-2138/2025 + kode pos) dan |
| `wms_health_service.py` | 95 | DASHBOARD KESEHATAN GUDANG — satu layar ringkas per gudang: |
| `work_desk_service.py` | 676 | FASE E-8 (E8.7/E8.15/E8.20) — **MEJA KERJA BERBASIS ANTREAN** (Admin Sales & Finance). |

## Koleksi MongoDB (dari pola `db.<nama>.<op>` di kode produksi)

`amendment_reasons`, `approval_rules`, `ar_receipts`, `audit_logs`, `bank_accounts`, `bank_match_rules`, `bank_statement_formats`, `bank_statement_lines`, `budgets`, `business_entities`, `cash_advance_settlements`, `cash_transactions`, `collection_followups`, `color_library`, `credit_notes`, `credit_overrides`, `crm_interactions`, `crm_leads`, `customers`, `cycle_count_sessions`, `data_hygiene_log`, `data_hygiene_runs`, `design_gallery`, `design_requests`, `document_branding`, `document_deliveries`, `document_signatures`, `document_templates`, `entity_prices`, `esign_requests`, `fin_depreciation_entries`, `fin_fixed_assets`, `generated_documents`, `gl_accounts`, `hr_attendance`, `hr_devices`, `hr_employees`, `hr_field_tracks`, `hr_geofences`, `hr_kpi`, `hr_leave_balances`, `hr_leave_requests`, `hr_org_units`, `hr_overtime`, `hr_payroll_runs`, `hr_payslips`, `hr_shifts`, `hr_visits`, `idempotency_keys`, `incentive_rates`, `inspections`, `integration_settings`, `interco_accounts`, `interco_loans`, `interco_returns`, `interco_transactions`, `intercompany_eliminations`, `internal_requests`, `inventory_balances`, `inventory_lots`, `inventory_movements`, `inventory_rolls`, `invoices`, `journal_entries`, `landed_cost_vouchers`, `login_attempts`, `logistics_deliveries`, `makloon_orders`, `makloons`, `md_samples`, `md_specs`, `mfg_boms`, `mfg_work_orders`, `migrations`, `notifications`, `number_sequences`, `payment_terms`, `pdf_templates`, `penalties`, `period_closings`, `permission_settings`, `price_approvals`, `process_recipes`, `process_stages`, `product_categories`, `product_lines`, `product_templates`, `products`, `purchase_orders`, `purchase_requisitions`, `purchase_returns`, `putaway_orders`, `rfid_cycle_counts`, `rfid_devices`, `rfid_incidents`, `rfid_print_jobs`, `rfid_reads`, `rfid_tags`, `rfid_verify_sessions`, `rfqs`, `rnd_person_divisions`, `roll_scans`, `sales_incentives`, `sales_orders`, `sales_return_policies`, `sales_returns`, `sales_targets`, `sample_price_master`, `sample_requests`, `sessions`, `shipments`, `special_orders`, `store_credit_ledger`, `store_credit_redemptions`, `supplier_contracts`, `supplier_price_lists`, `suppliers`, `sys_scheduler_runs`, `sys_wa_outbox`, `system_settings`, `tax_invoices`, `tax_invoices_in`, `tax_pph_records`, `turn_marks`, `uoms`, `user_onboarding`, `users`, `vendor_bills`, `warehouse_sites`, `warehouse_transfers`, `warehouses`, `wms_tasks`

## Frontend

| Fitur (`src/features/`) | Berkas | Baris |
|---|---:|---:|
| `admin` | 24 | 5731 |
| `approvals` | 4 | 1485 |
| `catalog` | 12 | 474 |
| `costing` | 1 | 146 |
| `crm` | 15 | 3195 |
| `design` | 6 | 1103 |
| `designer` | 7 | 1275 |
| `desks` | 1 | 134 |
| `documents` | 18 | 2514 |
| `finance` | 74 | 18432 |
| `home` | 3 | 1020 |
| `hr` | 29 | 5110 |
| `inspections` | 5 | 1305 |
| `internal_requests` | 3 | 836 |
| `inventory` | 14 | 3316 |
| `logistics` | 9 | 782 |
| `manager` | 2 | 732 |
| `mobile` | 6 | 509 |
| `orders` | 14 | 3075 |
| `pdf` | 4 | 793 |
| `pettycash` | 8 | 1419 |
| `pos` | 16 | 1955 |
| `pricing` | 1 | 111 |
| `production` | 3 | 724 |
| `purchasing` | 71 | 16137 |
| `rfid` | 8 | 1390 |
| `rnd` | 21 | 4195 |
| `sales` | 42 | 8388 |
| `sales_admin` | 6 | 1355 |
| `samples` | 3 | 160 |
| `settings` | 28 | 7175 |
| `transfers` | 1 | 277 |
| `wms` | 35 | 6677 |

**Komponen bersama (`src/components/*.jsx`, 68):** `BaseFabricPicker.jsx`, `CartPanel.jsx`, `CartPanelBanners.jsx`, `Collapse.jsx`, `CommandPalette.jsx`, `ConfirmHost.jsx`, `ConfirmModal.jsx`, `CoreWidgets.jsx`, `CustomerPanel.jsx`, `DecimalInput.jsx`, `DetailDrawer.jsx`, `DetailModal.jsx`, `DetailPopup.jsx`, `EntityBadge.jsx`, `EntitySwitcher.jsx`, `ErrorBoundary.jsx`, `ErrorNotice.jsx`, `FormModal.jsx`, `FulfillmentInfo.jsx`, `GroupEntityBadge.jsx`, `GuidedActionPanel.jsx`, `GuidedTour.jsx`, `HubTabs.jsx`, `KNDatePicker.jsx`, `KNDateTimePicker.jsx`, `KNMonthPicker.jsx`, `KNPager.jsx`, `KNSelect.jsx`, `KNTimePicker.jsx`, `LabelPrinterModal.jsx`, `LineFilter.jsx`, `LocationFields.jsx`, `LoginScreen.jsx`, `MakloonSelect.jsx`, `MixedLotConfirmModal.jsx`, `MoneyInput.jsx`, `NotificationCenter.jsx`, `OnboardingPanel.jsx`, `PaginationBar.jsx`, `PantoneFinder.jsx`, `PaymentBadge.jsx`, `PeggingModal.jsx`, `PeriodUnlockBanner.jsx`, `PeriodUnlockCard.jsx`, `PrinterStatusWidget.jsx`, `ProductCard.jsx`, `ProductDetail.jsx`, `ProductGallery.jsx`, `ProductQuickView.jsx`, `ProductSelect.jsx`, `QtyDual.jsx`, `ReturnPolicyEditor.jsx`, `ReturnTimeline.jsx`, `RollLabelActions.jsx`, `RollPicker.jsx`, `RollReconcileSheet.jsx`, `ScopeReadOnlyBanner.jsx`, `SeeAllModal.jsx`, `SoStatusBadges.jsx`, `StarRating.jsx`, `StoreCreditBadge.jsx`, `TourMenu.jsx`, `UomConvertHint.jsx`, `UomInputConvert.jsx`, `VariantAxisPicker.jsx`, `WaitingBoardsStrip.jsx`, `WaitingQueueBoard.jsx`, `WarehouseModeBadge.jsx`

**Hooks (`src/hooks/`):** `use-toast.js`, `useAppActions.js`, `useCaseDeepLink.js`, `useCatalogMasters.js`, `useConfigDeepLink.js`, `useDeepLinks.js`, `useDomainEnums.js`, `useEffectivePrices.js`, `useIsMobile.js`, `useLogisticsDeepLink.js`, `usePagedList.js`, `useProcessTypes.js`, `useReceivingUom.js`, `useRndDeepLink.js`, `useTraceDeepLink.js`, `useUomConversions.js`, `useViewDeepLink.js`

**Utils (`src/utils/`):** `apiError.js`, `cleanText.js`, `csvExport.js`, `decimalInput.js`, `docLink.js`, `docPrint.js`, `entityLabel.js`, `escapeLayers.js`, `feedback.js`, `formatters.js`, `fulfillment.js`, `lifecycle.js`, `offlineQueue.js`, `overlayDismiss.js`, `pricing.js`, `productImage.js`, `productSearch.js`, `qtyDualCsv.js`, `rollLabels.js`, `sirenAlarm.js`, `soStatus.js`, `text.js`, `uom.js`, `uomCatalog.js`, `variants.js`, `writeScope.js`

## Berkas melewati batas ukuran

15 berkas.

| Berkas | Baris | Batas |
|---|---:|---:|
| `backend/routers/purchase_orders.py` | 847 | 800 |
| `backend/routers/sales_orders_extra.py` | 805 | 800 |
| `frontend/src/features/purchasing/MakloonOrderDetailPanel.jsx` | 668 | 500 |
| `frontend/src/features/orders/OrderDetailPanel.jsx` | 616 | 500 |
| `frontend/src/features/sales/PricelistView.jsx` | 589 | 500 |
| `frontend/src/features/purchasing/PurchaseReturns.jsx` | 572 | 500 |
| `frontend/src/features/internal_requests/InternalRequestsView.jsx` | 535 | 500 |
| `frontend/src/features/purchasing/makloon/MakloonWizard.jsx` | 525 | 500 |
| `frontend/src/features/approvals/MyApprovalsView.jsx` | 522 | 500 |
| `frontend/src/features/settings/config/SettingsHub.jsx` | 515 | 500 |
| `frontend/src/features/wms/InventoryStockView.jsx` | 514 | 500 |
| `frontend/src/features/admin/PurchaseOrderManagement.jsx` | 512 | 500 |
| `frontend/src/features/settings/masters/EntityMastersView.jsx` | 511 | 500 |
| `frontend/src/features/wms/warehouses/WarehouseMasterView.jsx` | 505 | 500 |
| `frontend/src/features/sales/ReturnQuarantinePanel.jsx` | 503 | 500 |
