// Konstanta + helper untuk Approval Rules — skema MESIN (doc_type/min/max/required_role).
export function fmtNum(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

export const DOC_TYPES = [
  { value: "sales_order", label: "Pesanan Penjualan (SO)" },
  { value: "purchase_order", label: "Pesanan Pembelian (PO)" },
  { value: "purchase_requisition", label: "Permintaan Pembelian (PR)" },
  { value: "discount", label: "Diskon (%)" },
];

export const ROLES = [
  { value: "", label: "Tanpa persetujuan (lolos otomatis)" },
  { value: "manager", label: "Manager" },
  { value: "admin", label: "Admin" },
  { value: "owner", label: "Owner" },
];

export function docTypeLabel(v) {
  return DOC_TYPES.find((t) => t.value === v)?.label || v;
}

export function roleLabel(v) {
  return ROLES.find((r) => r.value === (v || ""))?.label || v;
}

export function fmtRange(rule) {
  const pct = rule.is_percent || rule.doc_type === "discount";
  const unit = pct ? "%" : "Rp ";
  const lo = pct ? `${fmtNum(rule.min_amount)}${unit}` : `${unit}${fmtNum(rule.min_amount)}`;
  if (rule.max_amount === null || rule.max_amount === undefined) return `≥ ${lo}`;
  const hi = pct ? `${fmtNum(rule.max_amount)}${unit}` : `${unit}${fmtNum(rule.max_amount)}`;
  return `${lo} s/d < ${hi}`;
}
