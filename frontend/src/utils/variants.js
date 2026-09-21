/**
 * EPIC-VAR — Pengelompokan produk berdasarkan template_id untuk tampilan katalog.
 * PRINSIP: 1 varian = 1 SKU (product_id). Pengelompokan ini HANYA presentation
 * (katalog POS). Inventory/WMS/receiving tetap per-SKU.
 *
 * Produk tanpa template_id → grup tunggal (key = product.id).
 */

export function groupByTemplate(products = []) {
  const map = new Map();
  for (const p of products) {
    const key = p.template_id || p.id;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(p);
  }
  return Array.from(map.entries()).map(([key, variants]) => {
    const prices = variants.map((v) => Number(v.price || 0));
    const totalAvailable = variants.reduce((s, v) => s + Number(v.available_qty || 0), 0);
    // F2 (UoM SSOT) — total roll tersedia lintas varian (1 produk = 1 base_unit; roll beda panjang)
    const totalRolls = variants.reduce((s, v) => s + Number(v.roll_count || 0), 0);
    // Representatif: varian dengan stok tertinggi (fallback varian pertama).
    const rep =
      [...variants].sort((a, b) => Number(b.available_qty || 0) - Number(a.available_qty || 0))[0] ||
      variants[0];
    return {
      key,
      base: rep,
      name: rep.template_name || rep.name,
      category: rep.category,
      image: rep.image,
      description: rep.description || "",  // F3 — deskripsi representatif (fallback popup)
      variants,
      isMulti: variants.length > 1,
      priceMin: prices.length ? Math.min(...prices) : 0,
      priceMax: prices.length ? Math.max(...prices) : 0,
      totalAvailable,
      totalRolls,
      anyAvailable: variants.some((v) => Number(v.available_qty || 0) > 0),
    };
  });
}

/** Label varian yang mudah dibaca: pakai variant_label bila ada, fallback warna · grade. */
export function variantLabel(p) {
  if (!p) return "";
  return (
    Object.values(p.variant_attrs || {}).filter(v => v !== null && v !== "").join(" · ") ||
    p.variant_label ||
    [p.color, p.grade ? `Grade ${p.grade}` : ""].filter(Boolean).join(" · ") ||
    p.sku ||
    ""
  );
}

export function variantAttributes(product) {
  if (!product) return {};
  const attrs = product.variant_attrs || {};
  if (Object.keys(attrs).length) return attrs;
  return Object.fromEntries(Object.entries({ color: product.color, grade: product.grade, origin: product.origin, lebar: product.lebar, quality: product.variant }).filter(([k, v]) => v !== undefined && v !== null && v !== "" && !(k === "quality" && ["Regular", "Standard"].includes(v))));
}
