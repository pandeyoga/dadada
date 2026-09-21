// REVISI SAMPEL — batas sampel per baris (cermin backend `sample_sale_service.SAMPLE_LIMITS`):
// woven maks 5 yard · knitting maks 2 kg. Default qty saat pilih "Order Sampel" = maksimum.
export const SAMPLE_LIMITS = {
  woven: { max_qty: 5, unit: "yard", label: "woven" },
  knit: { max_qty: 2, unit: "kg", label: "knitting" },
};

export function sampleLimit(product) {
  const ft = String(product?.fabric_type || "woven").toLowerCase();
  const rule = SAMPLE_LIMITS[ft] || SAMPLE_LIMITS.woven;
  return { ...rule, fabric_type: ft, base_unit: product?.base_unit || rule.unit };
}

export function clampSampleQty(product, qty) {
  const { max_qty } = sampleLimit(product);
  const n = Number(qty);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.min(max_qty, Math.round(n * 100) / 100);
}

export const isSampleCart = (cart) => cart.length > 0 && cart.every((i) => i.is_sample);
export const isRegularCart = (cart) => cart.length > 0 && cart.every((i) => !i.is_sample);

export const SAMPLE_STATUS_LABEL = {
  waiting_approval: "Menunggu ACC bayar",
  approved: "Siap ke gudang",
  confirmed: "Di gudang (potong)",
  partially_picked: "Sebagian dipotong",
  picked: "Dipotong · packing",
  partially_shipped: "Sebagian dikirim",
  shipped: "Dikirim / diambil",
  delivered: "Diterima",
  done: "Selesai",
  cancelled: "Dibatalkan",
};
