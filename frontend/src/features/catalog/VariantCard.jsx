import { ImageOff, Lock } from "lucide-react";
import { mediaUrl } from "../../components/ProductGallery";
import { formatCurrency } from "../../utils/formatters";
import { variantLabel } from "../../utils/variants";
import ProductColorChip from "../../components/ProductColorChip";

const LIFECYCLE = { produksi: ["Produksi", "pill-success"], sampling: ["Sampling", "pill-warning"], konsep: ["Konsep", "pill-muted"], arsip: ["Arsip", "pill-muted"] };

/** Kartu varian bergambar untuk daftar "Kombinasi varian". */
export const VariantCard = ({ variant: v, active, stock, onSelect }) => {
  const approved = (v.media || []).filter(m => m.status === "approved" && !m.deleted);
  const cover = approved.find(m => m.id === v.cover_media_id) || approved[0];
  const src = cover ? mediaUrl(cover.url) : v.image;
  const [lcLabel, lcCls] = v.status === "inactive" ? ["Nonaktif", "pill-danger"] : (LIFECYCLE[v.lifecycle] || LIFECYCLE.produksi);
  const kinds = approved.reduce((acc, m) => ({ ...acc, [m.kind]: (acc[m.kind] || 0) + 1 }), {});
  return <button type="button" data-testid={`catalog-select-${v.id}`} className={`variant-card${active ? " active" : ""}`} onClick={onSelect} aria-pressed={active}>
    <span className="variant-card-thumb">{src ? <img src={src} alt={variantLabel(v)} loading="lazy" /> : <ImageOff size={18} strokeWidth={1.2} />}
      {v.color_hex && <i className="variant-card-dot" style={{ background: v.color_hex }} title={v.color_name || v.color} />}</span>
    <span className="variant-card-body">
      <span className="variant-card-sku">{v.sku}</span>
      {v.color_ref && <ProductColorChip product={v} compact className="mt-0.5" />}
      {v.exclusive_customer_id && <span className="mt-0.5 inline-flex w-fit items-center gap-1 rounded-full bg-[#B45309] px-1.5 py-px text-[9.5px] font-bold text-white" data-testid={`catalog-customer-exclusive-${v.id}`}><Lock size={9} /> Eksklusif: {v.exclusive_customer_name || "pelanggan OD"}</span>}
      <strong>{variantLabel(v)}</strong>
      <span className="variant-card-meta">
        <b>{formatCurrency(v.price)}</b>
        <span className={`status-pill ${lcCls}`}>{lcLabel}</span>
      </span>
      <span className="variant-card-foot">
        {stock ? <span data-testid={`catalog-variant-stock-${v.id}`}>{stock.available} tersedia · {stock.rolls} roll</span> : <span>Stok memuat…</span>}
        <span className="variant-card-kinds">{kinds.photo ? `${kinds.photo} foto` : "tanpa foto"}{kinds.mockup ? ` · ${kinds.mockup} mockup` : ""}{kinds.artwork ? ` · ${kinds.artwork} artwork` : ""}</span>
      </span>
      {(v.supplier_codes || []).length > 0 && <span data-testid={`catalog-supplier-alias-${v.id}`} className="variant-card-alias">pabrik: {v.supplier_codes.map(c => c.supplier_sku).join(", ")}</span>}
    </span>
  </button>;
};
