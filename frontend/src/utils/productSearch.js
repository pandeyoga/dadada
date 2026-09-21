/**
 * MD-08 — kode/nama produk GANDA (KN ↔ supplier) untuk pencarian.
 * `supplier_codes` datang dari GET /api/products (katalog versi supplier).
 */
export function supplierKeywords(p) {
  return (p?.supplier_codes || []).flatMap((c) => [c.supplier_sku, c.supplier_item_name, c.supplier_name]).filter(Boolean);
}

export function supplierCodesLabel(p) {
  const codes = (p?.supplier_codes || []).map((c) => c.supplier_sku).filter(Boolean);
  return codes.length ? ` · pabrik: ${codes.join(", ")}` : "";
}

/** Opsi KNSelect produk: label KN + kata kunci supplier (dicari di kedua sisi). */
export function productOption(p, label) {
  return { value: p.id, label: label ?? `${p.sku} · ${p.name}`, keywords: supplierKeywords(p) };
}

export function productMatches(p, q) {
  const s = (q || "").trim().toLowerCase();
  if (!s) return true;
  return `${p.sku || ""} ${p.name || ""} ${p.category || ""} ${supplierKeywords(p).join(" ")}`.toLowerCase().includes(s);
}
