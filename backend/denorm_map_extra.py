"""Pasangan salinan denormalisasi TAMBAHAN (audit PL-04).

Ditemukan dengan menyapu DATA nyata (`scripts/denorm_audit.py`): 82 pasangan "FK + salinan nama/kode" ada di database,
hanya 30 yang terdaftar di `denorm.DENORM_MAP`. Sisanya (rekening, vendor, pekerja, mitra, kampanye, kode unit di banyak
koleksi, dst.) dulu basi begitu master diganti nama. Berkas ini memuat pasangan tambahan itu; `denorm.py` menggabungkannya
ke `DENORM_MAP`. Tes `test_p0_zzz_denorm_cakupan.py` gagal bila sapuan data menemukan pasangan yang belum terdaftar.
"""
# master -> [(koleksi anak, field FK, field kopi di anak, field sumber di master)]
EXTRA_PAIRS: dict = {
    "agents": [
        ("marketing_fees", "agent_id", "agent_name", "name"),
    ],
    "bank_accounts": [
        ("bank_statements", "account_id", "account_name", "name"),
        ("bank_transactions", "account_id", "account_name", "name"),
        ("cash_advances", "cash_account_id", "cash_account_name", "name"),
        ("cash_vouchers", "cash_account_id", "cash_account_name", "name"),
        ("commissions", "cash_account_id", "cash_account_name", "name"),
        ("cost_receipts", "cash_account_id", "cash_account_name", "name"),
        ("fund_requests", "cash_account_id", "cash_account_name", "name"),
        ("payments_out", "cash_account_id", "cash_account_name", "name"),
        ("pdc_instruments", "cash_account_id", "cash_account_name", "name"),
        ("petty_expenses", "cash_account_id", "cash_account_name", "name"),
        ("receipts", "cash_account_id", "cash_account_name", "name"),
    ],
    "build_templates": [
        ("build_schedules", "template_id", "template_code", "code"),
        ("build_schedules", "template_id", "template_name", "name"),
    ],
    "campaigns": [
        ("ad_spend", "campaign_id", "campaign_name", "name"),
    ],
    "clusters": [
        ("blocks", "cluster_id", "cluster_code", "code"),
        ("units", "cluster_id", "cluster_code", "code"),
    ],
    "contracts": [
        ("cancellations", "contract_id", "contract_number", "number"),
    ],
    "coupons": [
        ("coupon_redemptions", "coupon_id", "coupon_code", "code"),
    ],
    "customers": [
        ("build_schedules", "customer_id", "customer_name", "name"),
        ("cancellations", "customer_id", "customer_name", "name"),
        ("cost_invoices", "customer_id", "customer_name", "name"),
        ("payment_intakes", "customer_id", "customer_name", "name"),
    ],
    "document_templates": [
        ("documents", "template_id", "template_code", "code"),
    ],
    "fixed_assets": [
        ("asset_depreciations", "asset_id", "asset_code", "code"),
        ("asset_depreciations", "asset_id", "asset_name", "name"),
    ],
    "inspection_templates": [
        ("inspections", "template_id", "template_code", "code"),
    ],
    "kpr_disbursement_schemes": [
        ("financing_apps", "disbursement_scheme_id", "disbursement_scheme_code", "code"),
        ("financing_apps", "disbursement_scheme_id", "disbursement_scheme_name", "name"),
    ],
    "leads": [
        ("build_schedules", "lead_id", "lead_name", "name"),
        ("coupon_redemptions", "lead_id", "lead_name", "name"),
        ("quotations", "lead_id", "lead_name", "name"),
    ],
    "payment_schemes": [
        ("contracts", "payment_scheme_id", "payment_scheme_name", "name"),
    ],
    "progress_claims": [
        ("subcon_retentions", "claim_id", "claim_number", "claim_number"),
    ],
    "projects": [
        ("budget_items", "project_id", "project_name", "name"),
        ("build_weekly_reports", "project_id", "project_name", "name"),
        ("contracts", "project_id", "project_name", "name"),
        ("labor_attendance", "project_id", "project_name", "name"),
        ("labor_payrolls", "project_id", "project_name", "name"),
        ("unit_handovers", "project_id", "project_name", "name"),
        ("warranty_claims", "project_id", "project_name", "name"),
    ],
    "purchase_orders": [
        ("ap_invoices", "po_id", "po_number", "po_number"),
    ],
    "spk": [
        ("spk_scope_items", "spk_id", "spk_number", "spk_number"),
        ("subcon_advances", "spk_id", "spk_number", "spk_number"),
        ("subcon_deductions", "spk_id", "spk_number", "spk_number"),
        ("subcon_retentions", "spk_id", "spk_number", "spk_number"),
    ],
    "subcontractors": [
        ("spk_scope_items", "subcontractor_id", "subcontractor_name", "name"),
        ("subcon_advances", "subcontractor_id", "subcontractor_name", "name"),
        ("subcon_deductions", "subcontractor_id", "subcontractor_name", "name"),
        ("subcon_retentions", "subcontractor_id", "subcontractor_name", "name"),
    ],
    "unit_handovers": [
        ("units", "handover_id", "handover_number", "number"),
        ("warranty_claims", "handover_id", "handover_number", "number"),
    ],
    "unit_types": [
        ("units", "unit_type_id", "unit_type_code", "code"),
    ],
    "units": [
        ("booking_fee_invoices", "unit_id", "unit_code", "code"),
        ("build_items", "unit_id", "unit_code", "code"),
        ("build_schedules", "unit_id", "unit_code", "code"),
        ("cancellations", "unit_id", "unit_code", "code"),
        ("contracts", "unit_id", "unit_code", "code"),
        ("cost_invoices", "unit_id", "unit_code", "code"),
        ("coupon_redemptions", "unit_id", "unit_code", "code"),
        ("customer_deposits", "unit_id", "unit_code", "code"),
        ("inspections", "unit_id", "unit_code", "code"),
        ("payment_intakes", "unit_id", "unit_code", "code"),
        ("punch_items", "unit_id", "unit_code", "code"),
        ("quotations", "unit_id", "unit_code", "code"),
        ("receipts", "unit_id", "unit_code", "code"),
        ("spk_scope_items", "unit_id", "unit_code", "code"),
        ("unit_handovers", "unit_id", "unit_code", "code"),
        ("wa_reminders", "unit_id", "unit_code", "code"),
        ("warranty_claims", "unit_id", "unit_code", "code"),
    ],
    "vendors": [
        ("vendor_prices", "vendor_id", "vendor_name", "name"),
    ],
    "workers": [
        ("labor_attendance", "worker_id", "worker_name", "name"),
    ],
}
