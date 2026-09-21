import { Boxes, Layers3, Ruler, Scale, Sparkles, Tag } from "lucide-react";
import { mediaUrl } from "../../components/ProductGallery";
import { formatCurrency } from "../../utils/formatters";

const STAGE = { finished: "Kain jadi", greige: "Greige", yarn: "Benang", dyed: "Celup" };

/** Hero induk produk: foto utama + fakta kunci yang dibaca pemilik dalam 3 detik. */
export const FamilyHero = ({ family, summary }) => {
  const variants = family.variants || [];
  const cover = variants.find(v => v.cover_media_id && (v.media || []).some(m => m.id === v.cover_media_id && m.status === "approved"));
  const coverMedia = cover ? cover.media.find(m => m.id === cover.cover_media_id) : null;
  const src = coverMedia ? mediaUrl(coverMedia.url) : (variants.find(v => v.image)?.image || family.image);
  const prices = variants.map(v => Number(v.price || 0)).filter(Boolean);
  const min = prices.length ? Math.min(...prices) : Number(family.base_price || 0);
  const max = prices.length ? Math.max(...prices) : min;
  const totalMedia = variants.reduce((s, v) => s + (v.media || []).filter(m => m.status === "approved").length, 0);
  const available = (summary?.variants || []).reduce((s, v) => s + Number(v.available || 0), 0);
  const rolls = (summary?.variants || []).reduce((s, v) => s + Number(v.rolls || 0), 0);
  const facts = [
    { icon: Layers3, label: "Varian / SKU", value: `${family.variant_count} SKU`, testId: "hero-fact-sku" },
    { icon: Tag, label: "Harga jual", value: max > min ? `${formatCurrency(min)} – ${formatCurrency(max)}` : formatCurrency(min), testId: "hero-fact-price" },
    { icon: Scale, label: "Gramasi", value: family.gramasi ? `${family.gramasi} gsm` : "—", testId: "hero-fact-gsm" },
    { icon: Ruler, label: "Lebar kain", value: family.lebar ? `${family.lebar} m` : "—", testId: "hero-fact-width" },
    { icon: Boxes, label: "Stok entitas aktif", value: summary ? `${available} ${family.base_unit} · ${rolls} roll` : "Memuat…", testId: "hero-fact-stock" },
    { icon: Sparkles, label: "Foto & mockup", value: `${totalMedia} disetujui`, testId: "hero-fact-media" },
  ];
  return <section className="catalog-hero" data-testid="catalog-family-hero">
    <div className="catalog-hero-media">
      {src ? <img src={src} alt={family.name} data-testid="catalog-hero-image" /> : <div className="catalog-hero-empty">Belum ada foto utama</div>}
      <span className="catalog-hero-badge" data-testid="catalog-hero-stage">{STAGE[family.stage] || family.stage} · {family.fabric_type || "—"}</span>
    </div>
    <div className="catalog-hero-body">
      <div className="catalog-hero-facts">{facts.map(f => <div key={f.label} className="catalog-fact" data-testid={f.testId}><f.icon size={14} /><span><small>{f.label}</small><b>{f.value}</b></span></div>)}</div>
      <p className="catalog-hero-desc" data-testid="catalog-hero-description">{family.description || "Belum ada deskripsi produk."}</p>
      <div className="catalog-hero-swatches" data-testid="catalog-hero-swatches">
        {(family.axes || []).flatMap(a => a.options.map(o => <span key={`${a.key}-${o.code}`} className="catalog-swatch" title={`${a.label}: ${o.label}`}>{o.hex && <i style={{ background: o.hex }} />}{o.label}</span>))}
        {!family.axes?.length && <span className="text-xs text-[#737780]">Produk satu varian — belum ada atribut warna/grade.</span>}
      </div>
    </div>
  </section>;
};
