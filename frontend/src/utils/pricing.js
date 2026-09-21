// Fase 1B — preview pricing di sisi klien (CERMIN backend services/config_service.compute_order_pricing).
// Tujuan: tampilkan ringkasan diskon + PPN sebelum order dibuat. Backend tetap
// otoritatif saat menyimpan; util ini hanya untuk preview UX.
// F-10 Coretax — dukung DPP Nilai Lain 11/12 (PPN efektif = tarif × 11/12).

// KN-D21 — SATU cermin `compute_order_pricing` untuk keranjang, checkout, PO buat & PO ubah.
// `opts.cfgSection` ("sales" | "purchasing") memilih sakelar diskon yang dihormati server;
// `opts.taxOverride` ("non_ppn" | "ppn") = parameter tax_override server. Pembulatan
// bertahap (2 desimal per baris/tahap) mengikuti server supaya angka layar == tersimpan.
const r2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;

export function computeOrderPreview(items, orderDiscountPercent, settings, opts = {}) {
  const section = opts.cfgSection || "sales";
  const disc = (settings && settings[section]) || {};
  const tax = (settings && settings.tax) || {};
  const allowItem = disc.allow_item_discount !== false;
  const allowOrder = disc.allow_order_discount !== false;
  const isPkp = opts.taxOverride === "non_ppn" ? false : (opts.taxOverride === "ppn" ? true : tax.is_pkp !== false);
  const rate = isPkp ? Number(tax.ppn_rate || 0) : 0;
  const mode = tax.ppn_mode || "excluded";
  const useNL = rate > 0 && tax.dpp_nilai_lain === true;
  const dppFactor = useNL ? 11 / 12 : 1;
  const effRate = rate * dppFactor;

  let gross = 0;
  let itemsDisc = 0;
  (items || []).forEach((it) => {
    const price = Number((it.product && it.product.price) || it.price || 0);
    const qty = Number(it.quantity || 0);
    const subtotal = r2(price * qty);
    const dp = allowItem ? Math.max(0, Math.min(100, Number(it.discount_percent || 0))) : 0;
    gross += subtotal;
    itemsDisc += r2((subtotal * dp) / 100);
  });
  gross = r2(gross); itemsDisc = r2(itemsDisc);

  const afterItem = r2(gross - itemsDisc);
  const odp = allowOrder ? Math.max(0, Math.min(100, Number(orderDiscountPercent || 0))) : 0;
  const orderDisc = r2((afterItem * odp) / 100);
  const net = r2(afterItem - orderDisc);

  let dpp;
  let ppn;
  let grand;
  if (!isPkp || rate <= 0) {
    dpp = net; ppn = 0; grand = net;
  } else if (mode === "included") {
    const hargaJual = r2(net / (1 + effRate / 100));
    dpp = r2(hargaJual * dppFactor); ppn = r2(net - hargaJual); grand = net;
  } else {
    dpp = r2(net * dppFactor); ppn = r2((net * effRate) / 100); grand = r2(net + ppn);
  }

  return {
    gross,
    itemsDisc,
    orderDisc,
    discountTotal: itemsDisc + orderDisc,
    net,
    dpp,
    ppnRate: rate,
    effectiveRate: effRate,
    dppNilaiLain: useNL,
    ppn,
    grand,
    mode,
    isPkp,
    allowItem,
    allowOrder,
  };
}
