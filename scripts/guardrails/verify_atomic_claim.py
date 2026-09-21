#!/usr/bin/env python3
"""INV-ATOMIC-01 — endpoint tulis multi-koleksi memakai klaim atomik (T-01 Opsi B, saga).

Keputusan 2026-09: TANPA replica set/transaksi Mongo. Endpoint yang menulis ≥2 koleksi
substantif wajib (a) `atomic_claim.claim()` sebelum tulisan turunan + tulisan akhir
mencabut `saga_lock` (`finish_set` / `$unset`), ATAU (b) CAS: `find_one_and_update`
induk berprasyarat `status` + tulisan turunan idempoten, ATAU (c) alasan tertulis di
`REVIEWED` (≥20 huruf). Sisanya "BELUM DITINJAU" — angkanya RATCHET: hanya boleh turun
dari `BASELINE_UNREVIEWED`; entri `REVIEWED` yang fungsinya tak lagi berpola → MERAH.

Pakai:  python3 scripts/guardrails/verify_atomic_claim.py
        python3 scripts/guardrails/verify_atomic_claim.py --self-test
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import Guard, BACKEND, G, R, X  # noqa: E402
import inventaris_multi_koleksi as inv  # noqa: E402

# Baseline "BELUM DITINJAU" saat penjaga lahir (2026-09-05). Turunkan angka ini setiap
# kali satu endpoint selesai ditinjau — jangan pernah dinaikkan.
BASELINE_UNREVIEWED = 0

# (berkas router, potongan path) → (mekanisme, alasan). mekanisme ∈ {claim, cas, service, log}
REVIEWED: dict[tuple[str, str], tuple[str, str]] = {
    ("outbound_picking.py", "/resolve-escalation"): ("cas", "T-01 Langkah 1: find_one_and_update berprasyarat escalation.status $nin [resolved,resolving] → resolving (2026-09-05)"),
    ("inbound_receiving.py", "/inbound/tasks/{task_id}/complete"): ("claim", "klaim wms_tasks sebelum roll/mutasi/PO ditulis; tulisan akhir $unset saga_lock"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/cancel"): ("claim", "klaim sales_orders sebelum roll dilepas; so_transition CAS + $unset"),
    ("so_approvals.py", "/approvals/{approval_id}/decide"): ("claim", "klaim sales_orders per entri approval ($elemMatch pending); release di akhir"),
    ("transfers.py", "/transfers/{transfer_id}/approve"): ("claim", "klaim warehouse_transfers sebelum kepemilikan roll + jurnal; finish_set"),
    ("transfers.py", "/transfers/{transfer_id}/reject"): ("claim", "klaim warehouse_transfers sebelum roll dilepas; finish_set"),
    ("transfers.py", "/transfers/{transfer_id}/status"): ("claim", "klaim warehouse_transfers sebelum dispatch/receive roll; finish_set"),
    ("cycle_count.py", "/cycle-count/sessions/{session_id}/approve"): ("claim", "klaim cycle_count_sessions sebelum selisih diterapkan ke roll; finish_set"),
    ("purchase_orders_extra.py", "/purchase-orders/{po_id}/close"): ("cas", "find_one_and_update induk berprasyarat status; wms_tasks update_many idempoten"),
    ("purchase_orders_extra.py", "/purchase-orders/{po_id}/cancel"): ("cas", "find_one_and_update induk berprasyarat status; wms_tasks update_many idempoten"),
    ("vendor_bills.py", "/vendor-bills/{bill_id}/pay"): ("cas", "find_one_and_update vendor_bills berprasyarat status posted + $inc amount_paid atomik (pra-eksisting)"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/approve"): ("cas", "so_transition CAS status $in expected_from; set_order_rolls_status idempoten"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/submit-for-approval"): ("cas", "so_transition CAS status $in expected_from; set_order_rolls_status idempoten"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/confirm"): ("cas", "so_transition CAS; create_outbound_tasks_for_order dedupe per order+product"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/release-reservation"): ("claim", "klaim sales_orders sebelum roll dilepas; tulisan akhir finish_set (draft)"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/items/{product_id}/reallocate"): ("claim", "klaim sales_orders sesudah validasi, sebelum roll baru direservasi/roll lama dilepas; release bila reserve gagal; finish_set"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/items/{product_id}/release-rolls"): ("claim", "klaim sales_orders sebelum roll dilepas + mutasi ditulis; tulisan akhir finish_set (+$push reservation_releases)"),
    ("vendor_bills.py", "/vendor-bills/{bill_id}/cancel"): ("claim", "klaim vendor_bills berprasyarat status+amount_paid sebelum jurnal dibalik; mark_failed bila reversal gagal; finish_set status cancelled"),
    ("payment_variance.py", "/payment-variances/{decision_id}/reverse"): ("service", "klaim payment_variance_decisions (status != reversed) di service sebelum payments SO/deposit/kas/JE dibalik; finish_set", "payment_variance_service.reverse_decision"),
    ("purchase_returns.py", "/purchase-returns/{return_id}/reverse"): ("service", "klaim purchase_returns di service sesudah guard, sebelum JE/roll/AP/kas; finish_set", "purchase_return_service.reverse_settlement"),
    ("sales_returns.py", "/sales-returns/{return_id}/reverse"): ("service", "klaim sales_returns di service sesudah guard, sebelum JE/roll/kas/CN; finish_set", "return_service.reverse_settlement"),
    ("sales_returns.py", "/sales-returns/{return_id}/reverse-writeoff"): ("service", "klaim sales_returns sesudah target roll scrap ditentukan, sebelum JE write-off dibalik/roll dipulihkan/mutasi; finish_set", "return_service.reverse_writeoff"),
    ("sales_returns.py", "/sales-returns/{return_id}/relocate"): ("service", "klaim sales_returns sesudah roll karantina ditentukan, sebelum roll/tag/mutasi ditulis; finish_set + $push relocation_legs", "return_service.relocate_return_rolls"),
    ("sales_returns.py", "/sales-returns/{return_id}/quarantine/release"): ("service", "klaim sales_returns (quarantine_released != True) sesudah roll karantina & keputusan ditentukan, sebelum roll/JE write-off/mutasi; finish_set quarantine_released", "return_service.release_quarantine"),
    ("sample_sales.py", "/sample-requests/{request_id}/cut"): ("service", "klaim sample_requests (status requested) sesudah roll & alasan divalidasi, sebelum roll dipotong/SO/kwitansi; release bila CAS roll kalah; finish_set status done", "sample_sale_service.cut_sample"),
    ("sample_sales.py", "/sample-requests/{request_id}/cancel"): ("cas", "find_one_and_update sample_requests berprasyarat status requested → 409 bila kalah; wms_tasks hanya ikut ditandai cancelled sesudah CAS menang"),
    ("crm_omnichannel.py", "/crm/leads/{lead_id}/convert"): ("service", "klaim crm_leads (customer_id kosong) sesudah validasi lead/pelanggan tujuan, sebelum customers/interaksi ditulis; finish_set customer_id+stage won", "crm_omnichannel_service.convert_lead"),
    ("purchase_returns.py", "/purchase-returns/{return_id}/goods-back"): ("service", "klaim purchase_returns (supplier_status != goods_back) sesudah assert_transition, sebelum roll/mutasi/balance; finish_set supplier_status", "purchase_return_service.goods_back"),
    ("putaway_orders.py", "/putaway-orders/{order_id}/resolve-exception"): ("service", "klaim putaway_orders sesudah target item exception ditentukan, sebelum roll/tag/jejak/balance/BTG; finish_set status", "putaway_order_service.resolve_exception"),
    ("purchase_returns.py", "/purchase-returns/{return_id}/ship-to-supplier"): ("service", "klaim purchase_returns (supplier_status != shipped) sesudah assert_transition, sebelum roll dikarantina/balance; finish_set supplier_status", "purchase_return_service.ship_to_supplier"),
    ("invoices.py", "/sales-orders/{order_id}/simulate-payment"): ("claim", "klaim sales_orders sesudah validasi outstanding, sebelum invoices ditulis; finish_set + $inc paid_total + $push payments dalam satu update"),
    ("closing.py", "/finance/closing/{closing_id}/reopen"): ("service", "klaim period_closings (status closed) sebelum JE penutup di-void; finish_set status reopened", "closing_service.reopen_period"),
    ("closing.py", "/finance/closing/{closing_id}/reclose"): ("service", "klaim period_closings (status closed) sebelum JE lama di-void & JE baru dibuat; finish_set angka penutup", "closing_service.reclose_period"),
    ("transfers.py", "/transfers/{transfer_id}"): ("claim", "DELETE: klaim warehouse_transfers (status hidup) sesudah guard, SEBELUM roll dilepas; finish_set status cancelled dalam find_one_and_update"),
    ("ar_receipts.py", "/ar-receipts/{receipt_id}/void"): ("service", "klaim ar_receipts (status != void) sebelum keputusan selisih/payments SO/kas/deposit dibalik; release bila reverse_decision gagal; finish_set status void", "ar_receipt_service.void_receipt"),
    ("inventory.py", "/inventory/initial-stock"): ("compensate", "roll baru per permintaan (tak ada dokumen bersama); mutasi+rebuild di try, except → rollback_initial_stock menghapus roll & mutasi yang lahir"),
    ("inbound_receiving.py", "/inbound/tasks/{task_id}/resolve-escalation"): ("cas", "find_one_and_update wms_tasks berprasyarat escalation.status != resolved → 409 bila kalah (pola outbound)"),
    ("putaway_orders.py", "/putaway-orders/{order_id}/confirm-arrival"): ("service", "klaim putaway_orders di service sebelum bulk roll/tag/mutasi; finish_set", "putaway_order_service.confirm_arrival"),
    ("sales_orders.py", "/sales-orders"): ("compensate", "id SO baru per permintaan (tak ada dokumen bersama); roll direservasi lebih dulu dan DILEPAS (release_order_rolls) di except bila insert gagal — kompensasi saga"),
    ("rfid.py", "/rfid/ingest"): ("service", "rfid_reads append-only (id baru per baca) + rfid_tags.last_seen idempoten + rfid_devices.status; tidak ada saldo/stok/status dokumen — aman diulang, tak butuh kunci"),
    ("sales_returns.py", "/sales-returns/{return_id}/rolls/{roll_id}/transfer-ownership"): ("service", "klaim sales_returns sesudah semua validasi (roll/entitas/E9.3), sebelum roll direservasi/ownership dipindah/JE; release bila CAS roll kalah atau engine gagal; finish_set + $push ownership_transfers", "return_service.transfer_return_roll_ownership"),
    ("transfers.py", "/transfers"): ("compensate", "POST: id transfer baru per permintaan; reservasi roll + insert dokumen dalam satu try, except → release_wh_transfer_rolls melepas reservasi parsial (kompensasi saga)"),
    ("wms.py", "/wms/tasks"): ("compensate", "POST: id tugas baru per permintaan; inbound manual → create_inbound_roll dalam try, except → rollback_task_shell menghapus tugas tanpa roll (kompensasi saga)"),
    ("outbound_picking.py", "/outbound/tasks/{task_id}/scan-pick"): ("cas", "find_one_and_update wms_tasks berprasyarat status hidup + picked_qty sama seperti saat dibaca → 409 STATE_CHANGED bila kalah; SO status diturunkan sesudahnya (idempoten)"),
    ("outbound_picking.py", "/outbound/tasks/{task_id}/dispatch"): ("service", "klaim wms_tasks (status dispatchable) sesudah validasi qty, sebelum roll dikirim/surat jalan; release bila ship_order_rolls gagal; finish_set status+shipped_qty", "shipment_service.dispatch_task"),
    ("inbound_receiving_extra.py", "/inbound/tasks/{task_id}/qc-decision"): ("service", "klaim wms_tasks (status qc_pending) sesudah validasi qty/grade/disposisi, sebelum roll karantina dikonsumsi/retur/balance; mark_failed bila gagal; finish_set status+jejak QC", "qc_service.process_qc_decision"),
    ("rfid.py", "/rfid/tags/encode"): ("service_cas", "insert rfid_tags lalu CAS inventory_rolls (find_one_and_update rfid_tag_id kosong → tag); kalah → tag baru dihapus (kompensasi) + 409 STATE_CHANGED", "rfid_service.encode_tag"),
    ("rfid.py", "/rfid/tags/{tag_id}"): ("service_cas", "DELETE: find_one_and_update rfid_tags berprasyarat status active → retired; kalah → 409; roll dilepas hanya bila rfid_tag_id masih menunjuk tag ini (idempoten)", "rfid_service.retire_tag"),
    ("wms.py", "/wms/tasks/{task_id}/advance"): ("cas", "find_one_and_update wms_tasks berprasyarat status == status saat dibaca → 409 STATE_CHANGED; jalur dispatched didelegasikan ke dispatch_task (klaim sesi 12)"),
    ("rfid.py", "/rfid/verify-sessions/{session_id}/complete"): ("service", "klaim rfid_verify_sessions (status open) sesudah validasi scope/status, sebelum print job & journey ditulis; mark_failed bila gagal; finish_set status completed", "rfid_print_service.complete_verify"),
    ("rfid.py", "/rfid/cycle-count/{session_id}/complete"): ("service", "klaim rfid_verify_sessions (status open) sesudah validasi; insert rfid_cycle_counts lalu finish_set sesi → klik ganda/balapan hanya satu CC", "cycle_count_service.complete"),
    ("transfers.py", "/transfers/inter-company"): ("compensate", "POST: id transfer baru per permintaan; reservasi roll + validasi interco + insert dokumen dalam satu try, except → release_transfer_rolls (kompensasi saga)"),
    ("rfid.py", "/rfid/roll-scans"): ("service", "POST: roll_scans append-only (id baru per pindai) + inventory_rolls.last_scan CAS 'hanya maju' (last_scan.at < at) — idempoten via Idempotency-Key; tak ada saldo/status dokumen"),
    ("bank_reconciliation.py", "/bank-reconciliation/lines/{line_id}/book-charge"): ("service", "klaim bank_statement_lines (status bukan matched/holding) sesudah validasi jenis/nominal, sebelum kas+jurnal+link; mark_failed bila gagal; finish_set", "bank_recon_service.book_charge"),
    ("bank_reconciliation.py", "/bank-reconciliation/lines/{line_id}/holding"): ("service", "POST: klaim bank_statement_lines (bukan matched/holding) sesudah validasi arah/status, sebelum kas titipan+jurnal; finish_set status holding", "bank_recon_service.to_holding"),
    ("bank_reconciliation.py", "/bank-reconciliation/lines/{line_id}/holding/allocate"): ("service", "klaim bank_statement_lines (status holding) sesudah validasi Σ alokasi, AR+jurnal per alokasi di dalam klaim; mark_failed bila gagal; finish_set holding_remaining", "bank_recon_service.allocate_holding"),
    ("bank_reconciliation.py", "/bank-reconciliation/lines/{line_id}/holding/cancel"): ("service", "klaim bank_statement_lines (status holding) sesudah validasi, sebelum kas void + jurnal balik; finish_set status unmatched", "bank_recon_service.cancel_holding"),
    ("access_review.py", "/access/role-reality/{user_id}/apply"): ("service", "dua tulisan idempoten: users.role (update_user) + sesi dicabut (delete_many); pengulangan → 400 'peran sudah sama'; tidak ada saldo/stok"),
    ("entities.py", "/entities"): ("service", "POST: id badan usaha baru per permintaan; insert lalu seed COA (idempoten) + upsert system_settings; sinkron partner grup best-effort — tak ada saldo bersama, aman diulang"),
    ("entities.py", "/entities/{entity_id}/archive"): ("service_cas", "find_one_and_update business_entities berprasyarat status ≠ archived → 409 STATE_CHANGED; sesi pengguna dicabut idempoten (delete_many)", "entity_lifecycle_service.archive_entity"),
    ("entities.py", "/entities/{entity_id}"): ("service_cas", "DELETE (=archive): CAS status ≠ archived di lifecycle.archive_entity → 409 bila kalah", "entity_lifecycle_service.archive_entity"),
    ("config.py", "/impact-apply"): ("service", "klaim products sesudah validasi alasan/cakupan (ImpactError), master + SO ditulis ulang di dalam klaim; mark_failed bila gagal; release di finally", "config_impact_service.apply"),
    ("auth.py", "/auth/login"): ("service", "login_attempts + sessions + users(last_login): tulisan independen, tidak ada saldo/stok — aman diulang"),
    ("categories.py", "/product-categories/{category_id}"): ("claim", "PATCH: klaim product_categories sesudah validasi nama/duplikat, sebelum products.update_many (rename kaskade); mark_failed bila gagal; finish_set"),
    ("special_orders.py", "/special-orders/{order_id}/convert-to-so"): ("claim", "klaim special_orders (linked_sales_order_id kosong) sesudah validasi status/SKU, sebelum SO lahir; release bila create_order gagal; finish_set tautan SO"),
    ("wms.py", "/wms/tasks/outbound-from-order/{order_id}"): ("claim", "klaim sales_orders sesudah validasi status, sebelum tugas outbound lahir (cek 'belum ada tugas' + insert tak lagi bisa balapan); release di finally"),
    # ── Sesi 18 — ratchet ke 0 ──
    ("esign.py", "/request"): ("service", "POST: hanya esign_requests yang ditulis (id baru per permintaan); sample_requests/wms_tasks cuma DIBACA untuk hash dokumen — tak ada saldo/status bersama"),
    ("esign.py", "/verify"): ("service", "klaim esign_requests (status pending) sesudah OTP tervalidasi, sebelum document_signatures ditulis; mark_failed bila hash gagal; finish_set status verified", "esign_service.verify_and_sign"),
    ("fixed_assets.py", "/fixed-assets/run-depreciation"): ("service_cas", "per aset: find_one_and_update berprasyarat status + depreciation_periods $ne periode ($addToSet) — kalah → dilewati; entri+JE hanya oleh pemenang", "fixed_asset_service.run_depreciation"),
    ("hr_payroll.py", "/hr/payroll/runs"): ("service", "POST: run baru per permintaan; balapan run kedua untuk entitas+periode sama → run milik permintaan ini dihapus & run lain dikembalikan; slip gagal → rollback_run (kompensasi saga)"),
    ("input_tax.py", "/input-tax-invoices"): ("claim", "POST: klaim vendor_bills (input_faktur_status bukan aktif) sesudah validasi NSFP/dedupe, sebelum tax_invoices_in lahir; release bila insert gagal; finish_set penanda bill"),
    ("input_tax.py", "/input-tax-invoices/{fpm_id}/cancel"): ("claim", "klaim tax_invoices_in (status != cancelled) sesudah validasi alasan, sebelum bill dilepas; finish_set status cancelled"),
    ("inventory.py", "/inventory/putaway"): ("service", "putaway_roll: roll.bin_id di-set idempoten + inventory_movements putaway qty 0 (jejak, bukan saldo) — aman diulang, tak butuh kunci"),
    ("landed_cost.py", "/landed-costs/{voucher_id}/approve"): ("claim", "klaim landed_cost_vouchers (status pending) sesudah validasi peran/roll target, sebelum HPP roll ditulis; mark_failed bila alokasi gagal; finish_set applied"),
    ("landed_cost.py", "/landed-costs/{voucher_id}/pay"): ("claim", "klaim landed_cost_vouchers (status applied) sesudah validasi sisa, sebelum kas+GL lahir; mark_failed bila kas gagal; finish_set + $inc amount_paid"),
    ("makloon_orders.py", "/makloon-orders/{mko_id}/receive"): ("service", "klaim makloon_orders sesudah validasi qty/lot, sebelum roll input dikonsumsi/tagihan jasa/lot output; replace_one tanpa saga_lock + release", "makloon_order_service.receive_step"),
    ("makloon_orders.py", "/makloon-orders/{mko_id}/record-service"): ("service", "klaim makloon_orders sesudah validasi biaya, sebelum vendor_bills jasa lahir; replace_one tanpa saga_lock + release", "makloon_order_service.record_service_step"),
    ("outbound_picking.py", "/outbound/loading-check/{session_id}/complete"): ("service", "klaim rfid_verify_sessions (status open) sesudah validasi jenis/scope, sebelum sales_orders.loading_check ditulis; finish_set completed", "loading_check_service.complete"),
    ("product_templates.py", "/product-templates/{template_id}"): ("service", "DELETE: klaim product_templates sebelum varian dilepas (update_many); release bila detach gagal; delete_one mencabut dokumen beserta kuncinya", "product_template_service.delete_template"),
    ("rfq.py", "/rfqs/{rfq_id}/award"): ("service", "klaim rfqs (status open) sesudah validasi mode/harga, sebelum PO lahir; release bila belum ada PO, mark_failed bila PO parsial; finish_set awarded", "rfq_service.award_rfq"),
    ("rnd.py", "/rnd/samples/{sample_id}/issue-material"): ("service_cas", "find_one_and_update inventory_rolls berprasyarat status + length_remaining sama seperti saat dibaca → kalah = RndError; JE gagal → mutasi & roll dipulihkan (kompensasi pra-eksisting)", "rnd_sample_service.issue_material"),
    ("sales_orders_extra.py", "/sales-orders/{order_id}/mark-delivered"): ("cas", "_transition CAS status shipped → done (409 bila kalah); deliver_order_rolls idempoten (set status delivered pada roll order)"),
    ("sales_returns.py", "/sales-returns/{return_id}/create-purchase-return"): ("service", "klaim sales_returns (linked_purchase_return_id kosong) sesudah validasi roll/supplier, sebelum purchase_returns lahir; release bila gagal; finish_set tautan", "purchase_return_service.create_from_sales_return"),
    ("sample_sales.py", "/sample-requests"): ("service", "POST: id permintaan baru per permintaan; wms_tasks gagal ditulis → sample_requests yang baru lahir dihapus (kompensasi saga); tak ada saldo bersama"),
    ("so_approvals.py", "/sales-orders/{order_id}/request-credit-approval"): ("claim", "klaim sales_orders sesudah validasi status/duplikat pending, sebelum credit_overrides lahir; finish_set credit_hold"),
    ("special_orders.py", "/special-orders/{order_id}/create-pr"): ("claim", "klaim special_orders (linked_pr_id kosong) sesudah validasi status/gudang, sebelum PR lahir; release bila create_requisition gagal; finish_set tautan PR"),
    ("special_orders.py", "/special-orders/{order_id}/create-sku"): ("service", "klaim special_orders (linked_product_id kosong) sesudah validasi, sebelum products lahir; release bila insert gagal; finish_set tautan SKU", "special_order_service.create_sku_from_special_order"),
    ("users.py", "/users"): ("service", "POST: users baru per permintaan; hr_employees.user_id gagal → akun yang baru lahir dihapus (kompensasi saga); tak ada saldo bersama"),
    ("users.py", "/users/{user_id}"): ("service", "PATCH: users $set + hr_employees.user_id (idempoten, tautan satu arah) + sesi dicabut (delete_many) — tulisan independen tanpa saldo/stok, aman diulang"),
    ("warehouse_sites.py", "/warehouse-sites/seed-blueprint"): ("service", "POST seed: warehouses/warehouse_sites di-upsert per kode (idempoten) — pengulangan tidak menggandakan; tak ada saldo"),
}

# `family_lock(` = context manager di product_variant_service yang MEMBUNGKUS
# atomic_claim.claim() + release() (klaim per keluarga produk). Diakui sebagai klaim
# + pencabut kunci yang sah — bukan allowlist per fungsi.
RE_CLAIM = re.compile(r"atomic_claim|_saga\.claim\(|family_lock\(")
RE_FINISH = re.compile(r"finish_set\(|\$unset\"?\s*:\s*\{\s*\"saga_lock\"|so_transition|_transition\(|_saga\.release\(|family_lock\(")
RE_CAS = re.compile(r"find_one_and_update\(\s*\{[^}]*\"(status|escalation\.status|rfid_tag_id)\"|_transition\(|find_one_and_update\(\s*\n?\s*\{\"id\": bill_id, \"status\"")
RE_COMP = re.compile(r"except[^\n]*:\s*\n\s*await (release_|_release|rollback|compensate)")
# Validasi 400/404/422 SESUDAH klaim meninggalkan saga_lock → percobaan ulang yang benar ditolak 409
# (bukti: inbound complete × pagar lot mode block, sesi 4). Klaim wajib SESUDAH semua validasi.
RE_LATE_VALIDATION = re.compile(r"raise HTTPException\(\s*status_code=4(00|04|22)")
RE_RELEASE_BEFORE = re.compile(r"await _saga\.release\(|await atomic_claim\.release\(|await _saga\.mark_failed\(|await atomic_claim\.mark_failed\(")


def validation_after_claim(src: str) -> str | None:
    """Baris pertama `raise HTTPException(status_code=400/404/422)` sesudah `_saga.claim(`; None bila bersih.
    Raise yang didahului `release(` atau `mark_failed(` (≤3 baris sebelumnya) dianggap sudah menangani kunci
    (dilepas, atau sengaja dibiarkan dengan alasan tercatat karena tulisan turunan sudah terjadi) → bukan pelanggaran."""
    lines = src.splitlines()
    idx = next((i for i, l in enumerate(lines) if "_saga.claim(" in l or "atomic_claim.claim(" in l), None)
    if idx is None:
        return None
    for j in range(idx + 1, len(lines)):
        l = lines[j]
        if RE_LATE_VALIDATION.search(l):
            if any(RE_RELEASE_BEFORE.search(p) for p in lines[max(idx + 1, j - 3):j]):
                continue
            return l.strip()
    return None


def service_function_source(ref: str) -> str | None:
    """'modul.fungsi' → sumber fungsi di backend/services/modul.py (None bila tak ada)."""
    mod, _, fn = ref.rpartition(".")
    f = BACKEND / "services" / f"{mod}.py"
    if not f.exists():
        return None
    src = f.read_text(errors="ignore")
    tree = ast.parse(src)
    lines = src.splitlines()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn:
            return "\n".join(lines[n.lineno - 1:n.end_lineno])
    return None


def endpoint_sources() -> dict[tuple[str, str], str]:
    """{(router file, path): source fungsi} untuk semua endpoint tulis di backend/routers."""
    out: dict[tuple[str, str], str] = {}
    for f in sorted((BACKEND / "routers").glob("*.py")):
        src = f.read_text(errors="ignore")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for n in tree.body:
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for d in n.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ("post", "put", "patch", "delete") and d.args:
                    p = d.args[0]
                    if isinstance(p, ast.Constant):
                        out[(f.name, str(p.value))] = "\n".join(lines[n.lineno - 1:n.end_lineno])
    return out


def unreviewed_rows() -> list[tuple[str, str]]:
    """Endpoint ≥2 koleksi substantif (dari inventaris) yang belum masuk REVIEWED."""
    rows = inv.collect_rows()
    out = []
    for fn, _ln, path, _direct, _via, allc in rows:
        if len([c for c in allc if c not in inv.LOG_ONLY]) < 2:
            continue
        if not any(fn == rf and frag in path for (rf, frag) in REVIEWED):
            out.append((fn, path))
    return out


def check(sources: dict[tuple[str, str], str], reviewed=REVIEWED, unreviewed: list | None = None,
          baseline: int = BASELINE_UNREVIEWED) -> Guard:
    g = Guard("INV-ATOMIC-01", "endpoint tulis multi-koleksi memakai klaim atomik / CAS (saga, tanpa transaksi)")
    for (rf, frag), entry in sorted(reviewed.items()):
        mech, reason = entry[0], entry[1]
        svc_ref = entry[2] if len(entry) > 2 else None
        g.bump()
        hit = [(k, s) for k, s in sources.items() if k[0] == rf and frag in k[1]]
        if not hit:
            g.add(f"REVIEWED {rf} {frag}: endpoint tidak lagi ada di kode — hapus entrinya (ratchet).")
            continue
        src = hit[0][1]
        if len(reason.strip()) < 20:
            g.add(f"{rf} {frag}: alasan REVIEWED terlalu pendek (<20 huruf).")
        if mech == "claim" and not RE_CLAIM.search(src):
            g.add(f"backend/routers/{rf} {frag}: dicatat 'claim' tetapi tidak memanggil atomic_claim.claim(). Pasang klaim atau ubah mekanisme.")
        if mech == "claim" and not RE_FINISH.search(src):
            g.add(f"backend/routers/{rf} {frag}: klaim tanpa pencabut kunci (finish_set / $unset saga_lock / so_transition / release).")
        if mech == "claim" and (late := validation_after_claim(src)):
            g.add(f"backend/routers/{rf} {frag}: validasi 4xx SESUDAH klaim (`{late[:70]}`) — kunci tertinggal; pindahkan ke atas klaim atau release() dulu.")
        if mech == "cas" and not RE_CAS.search(src):
            g.add(f"backend/routers/{rf} {frag}: dicatat 'cas' tetapi find_one_and_update induk tidak berprasyarat status.")
        if mech == "compensate" and not RE_COMP.search(src):
            g.add(f"backend/routers/{rf} {frag}: dicatat 'compensate' tetapi tidak ada `except → await release_/rollback` (kompensasi hilang).")
        if mech == "service" and svc_ref:
            ssrc = service_function_source(svc_ref)
            if ssrc is None:
                g.add(f"{rf} {frag}: rujukan service '{svc_ref}' tidak ditemukan di backend/services.")
            elif not RE_CLAIM.search(ssrc) or not RE_FINISH.search(ssrc):
                g.add(f"backend/services/{svc_ref}: dicatat klaim di service tetapi tidak ada atomic_claim.claim() + finish_set/release.")
            elif (late := validation_after_claim(ssrc)):
                g.add(f"backend/services/{svc_ref}: validasi 4xx SESUDAH klaim (`{late[:70]}`) — kunci tertinggal.")
        if mech == "service_cas":
            ssrc = service_function_source(svc_ref or "")
            if ssrc is None:
                g.add(f"{rf} {frag}: rujukan service '{svc_ref}' tidak ditemukan di backend/services.")
            elif not RE_CAS.search(ssrc):
                g.add(f"backend/services/{svc_ref}: dicatat 'service_cas' tetapi find_one_and_update di service tidak berprasyarat status/rfid_tag_id.")
    if unreviewed is not None:
        g.bump()
        if len(unreviewed) > baseline:
            g.add(f"BELUM DITINJAU = {len(unreviewed)} > baseline {baseline}. Endpoint multi-koleksi BARU wajib memakai "
                  "atomic_claim.claim()/CAS dan dicatat di REVIEWED: " +
                  "; ".join(f"{a} {b}" for a, b in unreviewed[:5]))
        elif len(unreviewed) < baseline:
            g.add(f"BELUM DITINJAU = {len(unreviewed)} < baseline {baseline}: turunkan BASELINE_UNREVIEWED ke {len(unreviewed)} (ratchet hanya turun).")
    return g


def self_test() -> int:
    fails = 0

    def case(name, sources, reviewed, expect_red, unreviewed=None, baseline=0):
        nonlocal fails
        red = bool(check(sources, reviewed, unreviewed, baseline).violations)
        ok = red == expect_red
        fails += 0 if ok else 1
        print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] {name} → {'MERAH' if red else 'hijau'}")

    good_claim = "async def f():\n    await _saga.claim('x', i, 'a')\n    await db.x.find_one_and_update({'id': i}, _saga.finish_set({'status': 'b'}))\n"
    no_finish = "async def f():\n    await _saga.claim('x', i, 'a')\n    await db.x.update_one({'id': i}, {'$set': {'status': 'b'}})\n"
    no_claim = "async def f():\n    await db.x.update_one({'id': i}, {'$set': {'status': 'b'}})\n"
    cas_ok = "async def f():\n    u = await db.x.find_one_and_update({'id': i, \"status\": {'$in': ['a']}}, {'$set': {}})\n"
    R1 = {("r.py", "/x/{id}/go"): ("claim", "alasan yang cukup panjang untuk lolos uji")}
    R2 = {("r.py", "/x/{id}/go"): ("cas", "alasan yang cukup panjang untuk lolos uji")}
    case("claim + finish_set → hijau", {("r.py", "/x/{id}/go"): good_claim}, R1, False)
    case("claim tanpa pencabut kunci → MERAH", {("r.py", "/x/{id}/go"): no_finish}, R1, True)
    case("dicatat claim tapi tak memanggil claim() → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R1, True)
    late_400 = "async def f():\n    await _saga.claim('x', i, 'a')\n    if bad:\n        raise HTTPException(status_code=400, detail='x')\n    await db.x.find_one_and_update({'id': i}, _saga.finish_set({'status': 'b'}))\n"
    early_400 = "async def f():\n    if bad:\n        raise HTTPException(status_code=400, detail='x')\n    await _saga.claim('x', i, 'a')\n    await db.x.find_one_and_update({'id': i}, _saga.finish_set({'status': 'b'}))\n"
    case("validasi 400 SESUDAH klaim (kunci tertinggal) → MERAH", {("r.py", "/x/{id}/go"): late_400}, R1, True)
    case("validasi 400 SEBELUM klaim → hijau", {("r.py", "/x/{id}/go"): early_400}, R1, False)
    released_400 = "async def f():\n    await _saga.claim('x', i, 'a')\n    try:\n        await sub()\n    except Err:\n        await _saga.release('x', i)\n        raise HTTPException(status_code=400, detail='x')\n    await db.x.find_one_and_update({'id': i}, _saga.finish_set({'status': 'b'}))\n"
    case("validasi 400 sesudah klaim TAPI release() dulu → hijau", {("r.py", "/x/{id}/go"): released_400}, R1, False)
    case("cas berprasyarat status → hijau", {("r.py", "/x/{id}/go"): cas_ok}, R2, False)
    case("dicatat cas tapi tanpa prasyarat status → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R2, True)
    comp_ok = "async def f():\n    try:\n        await reserve()\n    except HTTPException:\n        await release_order_rolls(i)\n        raise\n"
    R3 = {("r.py", "/x/{id}/go"): ("compensate", "alasan yang cukup panjang untuk lolos uji")}
    case("compensate dengan except→release → hijau", {("r.py", "/x/{id}/go"): comp_ok}, R3, False)
    case("dicatat compensate tanpa kompensasi → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R3, True)
    R4 = {("r.py", "/x/{id}/go"): ("service", "alasan yang cukup panjang untuk lolos uji", "modul_tidak_ada.fungsi")}
    case("service merujuk fungsi yang tak ada → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R4, True)
    R5 = {("r.py", "/x/{id}/go"): ("service", "alasan yang cukup panjang untuk lolos uji", "putaway_order_service.confirm_arrival")}
    case("service nyata berklaim (putaway confirm_arrival) → hijau", {("r.py", "/x/{id}/go"): no_claim}, R5, False)
    R6 = {("r.py", "/x/{id}/go"): ("service", "alasan yang cukup panjang untuk lolos uji", "putaway_order_service.dispatch")}
    case("service nyata TANPA klaim → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R6, True)
    R7 = {("r.py", "/x/{id}/go"): ("service_cas", "alasan yang cukup panjang untuk lolos uji", "rfid_service.retire_tag")}
    case("service_cas nyata berprasyarat status (retire_tag) → hijau", {("r.py", "/x/{id}/go"): no_claim}, R7, False)
    R8 = {("r.py", "/x/{id}/go"): ("service_cas", "alasan yang cukup panjang untuk lolos uji", "putaway_order_service.dispatch")}
    case("service_cas nyata TANPA find_one_and_update berprasyarat → MERAH", {("r.py", "/x/{id}/go"): no_claim}, R8, True)
    case("entri REVIEWED basi (endpoint hilang) → MERAH", {}, R1, True)
    case("alasan pendek → MERAH", {("r.py", "/x/{id}/go"): good_claim}, {("r.py", "/x/{id}/go"): ("claim", "pendek")}, True)
    case("BELUM DITINJAU naik di atas baseline → MERAH", {}, {}, True, unreviewed=[("a.py", "/b")], baseline=0)
    case("BELUM DITINJAU turun di bawah baseline → MERAH (turunkan baseline)", {}, {}, True, unreviewed=[], baseline=1)
    case("BELUM DITINJAU == baseline → hijau", {}, {}, False, unreviewed=[("a.py", "/b")], baseline=1)
    real = check(endpoint_sources(), REVIEWED, unreviewed_rows())
    ok = not real.violations
    fails += 0 if ok else 1
    print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] kode nyata saat ini HIJAU ({len(real.violations)} pelanggaran)")
    for v in real.violations:
        print(f"    ✗ {v[:200]}")
    print(f"{G if not fails else R}  SELF-TEST {'HIJAU' if not fails else 'MERAH'} ({fails} gagal).{X}")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    return check(endpoint_sources(), REVIEWED, unreviewed_rows()).finish()


if __name__ == "__main__":
    sys.exit(main())
