import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, ChevronLeft, ChevronRight, Images, Layers3, Pencil, Plus, Search } from "lucide-react";
import { ProductGallery } from "../../components/ProductGallery";
import { formatCurrency } from "../../utils/formatters";
import { variantLabel } from "../../utils/variants";
import { askConfirm } from "../../services/confirmService";
import { openConfig } from "../settings/config/configDeepLink";
import { openRnd } from "../rnd/rndDeepLink";
import { catalogApi, catalogChanged, catalogError } from "./catalogApi";
import { FamilyForm } from "./FamilyForm";
import { GenerateVariants } from "./GenerateVariants";
import { VariantEditor } from "./VariantEditor";
import { VariantMedia } from "./VariantMedia";
import { ProductRelations } from "./ProductRelations";
import { LinkExistingVariant } from "./LinkExistingVariant";
import { FamilyHero } from "./FamilyHero";
import { VariantCard } from "./VariantCard";
import { FamilyInfoTab } from "./FamilyInfoTab";
import ProductColorChip from "../../components/ProductColorChip";
import "./catalog.css";

export default function CatalogWorkspace({ currentUser, selectedEntity, focus, legacyView }) {
  const [meta, setMeta] = useState(null); const [items, setItems] = useState([]); const [total, setTotal] = useState(0);
  const [query, setQuery] = useState(""); const [page, setPage] = useState(0); const [loading, setLoading] = useState(true);
  const [family, setFamily] = useState(null); const [selectedId, setSelectedId] = useState(""); const [summary, setSummary] = useState(null);
  const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [modal, setModal] = useState(""); const [tab, setTab] = useState("variants");
  const [legacy, setLegacy] = useState(false);
  const caps = meta?.permissions || {};
  const load = useCallback(async () => { setLoading(true); setError(""); try { const [m, d] = await Promise.all([catalogApi.meta(), catalogApi.list({ search: query, offset: page * 24, limit: 24, paginate: true })]); setMeta(m); setItems(d.items); setTotal(d.total); } catch (e) { setError(catalogError(e)); } finally { setLoading(false); } }, [query, page, selectedEntity]); // eslint-disable-line
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);
  const open = useCallback(async (id, pid = "") => { setError(""); setSummary(null); try { const d = await catalogApi.detail(id); setFamily(d); setSelectedId(pid || d.variants[0]?.id || ""); const s = await catalogApi.summary(id); setSummary(s); } catch (e) { setError(catalogError(e)); } }, []);
  useEffect(() => { setFamily(null); setSelectedId(""); setSummary(null); }, [selectedEntity]);
  useEffect(() => { if (focus?.templateId) open(focus.templateId, focus.productId); }, [focus, open]);
  const refresh = async () => { catalogChanged(); await load(); if (family) await open(family.id, selectedId); };
  const selected = family?.variants.find(v => v.id === selectedId) || family?.variants[0];
  const stock = summary?.variants.find(v => v.id === selected?.id);
  if (legacy && legacyView) return <div data-testid="catalog-legacy-view"><button data-testid="catalog-back-from-legacy" className="secondary-button mb-4" onClick={() => { setLegacy(false); load(); }}><ArrowLeft size={14} />Kembali ke etalase</button>{legacyView}</div>;
  return <div className="kn-catalog" data-testid="catalog-workspace">
    <header className="catalog-heading">
      <div><div data-testid="catalog-eyebrow" className="catalog-eyebrow">KAIN NUSANTARA / MASTER PRODUK</div><h1 data-testid="catalog-title">{family ? family.name : "Produk & varian"}</h1><p data-testid="catalog-subtitle">{family ? `${family.category} · ${family.fabric_type || "—"} · ${family.sku_prefix}` : `${total} induk produk · katalog bersama`}</p></div>
      <div className="flex flex-wrap gap-2">
        {family && <button data-testid="catalog-back" className="secondary-button" onClick={() => { setFamily(null); setSelectedId(""); }}><ArrowLeft size={14} />Semua produk</button>}
        {!family && legacyView && caps.update && <button data-testid="catalog-legacy" className="secondary-button" onClick={() => setLegacy(true)}>Data SKU & impor</button>}
        {caps.create && !family && <button data-testid="catalog-create" className="primary-button" onClick={() => setModal("create")}><Plus size={15} />Produk baru</button>}
        {caps.update && family && <button data-testid="catalog-edit-family" className="secondary-button" onClick={() => setModal("edit")}><Pencil size={14} />Ubah induk</button>}
        {caps.update && family && <button data-testid="catalog-link-existing" className="secondary-button" onClick={() => setModal("link")}>Tautkan SKU lama</button>}
        {caps.create && family && <button data-testid="catalog-generate" className="primary-button" onClick={() => setModal(family.axes?.length ? "generate" : "new-variant")}><Plus size={15} />Tambah varian</button>}
      </div>
    </header>
    {error && <div data-testid="catalog-error" role="alert" className="catalog-alert error">{error}<button data-testid="catalog-retry" className="secondary-button" onClick={load}>Coba lagi</button></div>}
    {notice && <div data-testid="catalog-notice" role="status" className="catalog-alert">{notice}<button data-testid="catalog-dismiss-notice" onClick={() => setNotice("")} className="text-xs underline">Tutup</button></div>}
    {!family ? <>
      <div className="catalog-toolbar"><div className="relative w-full max-w-md"><Search size={16} className="absolute left-3 top-3 text-gray-400" /><input data-testid="catalog-search" placeholder="Cari produk, kategori, atau prefix SKU" className="field !pl-9" value={query} onChange={e => { setPage(0); setQuery(e.target.value); }} /></div><span data-testid="catalog-result-count" className="text-xs text-gray-500">{items.length} dari {total} produk</span></div>
      {loading ? <div className="catalog-grid" data-testid="catalog-loading">{[0, 1, 2, 3].map(i => <div key={i} className="h-72 animate-pulse rounded-lg bg-gray-100" />)}</div> : !items.length ? <div data-testid="catalog-empty" className="catalog-empty"><Layers3 size={36} strokeWidth={1} /><h2>Belum ada produk{query ? " yang cocok" : ""}</h2>{caps.create && <button data-testid="catalog-empty-create" className="primary-button" onClick={() => setModal("create")}><Plus size={14} />Buat induk produk</button>}</div> : <div className="catalog-grid" data-testid="catalog-grid">{items.map(t => <article key={t.id} data-testid={`catalog-card-${t.id}`} className="catalog-card">
        <div className="catalog-card-media"><ProductGallery product={t.cover_product || { name: t.name, image: t.image }} compact testId={`card-gallery-${t.id}`} /><span data-testid={`catalog-variant-count-${t.id}`} className="catalog-count">{t.variant_count} varian</span></div>
        <button data-testid={`catalog-open-${t.id}`} className="catalog-card-content" onClick={() => { setTab("variants"); open(t.id); }}><span className="catalog-category" data-testid={`catalog-category-${t.id}`}>{t.category} · {t.fabric_type || "—"}</span><h2 data-testid={`catalog-name-${t.id}`}>{t.name}</h2><span className="catalog-axis-label" data-testid={`catalog-axes-${t.id}`}>{(t.axes || []).map(a => a.label).join(" × ") || "Produk satu varian"}</span><span className="catalog-card-bottom"><strong data-testid={`catalog-price-${t.id}`}>{formatCurrency(t.price_min || 0)}{t.price_max > t.price_min ? ` – ${formatCurrency(t.price_max)}` : ""}</strong><ArrowUpRight size={17} /></span></button>
      </article>)}</div>}
      <footer className="catalog-pagination"><button data-testid="catalog-prev" className="secondary-button" disabled={!page} onClick={() => setPage(page - 1)}><ChevronLeft size={14} />Sebelumnya</button><span data-testid="catalog-page">{page + 1} / {Math.max(1, Math.ceil(total / 24))}</span><button data-testid="catalog-next" className="secondary-button" disabled={(page + 1) * 24 >= total} onClick={() => setPage(page + 1)}>Berikutnya<ChevronRight size={14} /></button></footer>
    </> : <>
      <FamilyHero family={family} summary={summary} />
      <div className="catalog-tabs" role="tablist">{[["variants", "Varian & galeri", family.variant_count], ["info", "Informasi produk", null], ...(caps.rnd_view ? [["rnd", "R&D & asal desain", null]] : [])].map(([k, l, n]) => <button key={k} data-testid={`catalog-tab-${k}`} role="tab" aria-selected={tab === k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{l}{n ? <span className="tab-count">{n}</span> : null}</button>)}</div>
      {tab === "info" ? <FamilyInfoTab family={family} caps={caps} onPolicy={() => openConfig({ group: "rnd", key: "rnd.new_product_default_lifecycle" })} onArchive={async () => { if (!await askConfirm({ title: "Arsipkan induk ini?", message: family.name, confirmLabel: "Arsipkan", danger: true })) return; try { await catalogApi.archive(family.id); setFamily(null); load(); } catch (e) { setError(catalogError(e)); } }} /> : <div className="catalog-detail-grid">
        <aside className="catalog-variant-list"><div className="variant-list-head"><h2 data-testid="catalog-variant-list-title">Kombinasi varian</h2><span>{family.variants.length} SKU</span></div>{family.variants.map(v => <VariantCard key={v.id} variant={v} active={selected?.id === v.id} stock={summary?.variants.find(s => s.id === v.id)} onSelect={() => setSelectedId(v.id)} />)}{!family.variants.length && <p data-testid="catalog-no-variants" className="text-sm text-gray-500">Belum ada SKU.</p>}{caps.create && !!family.axes?.length && <button data-testid="catalog-add-single" className="secondary-button mt-1 w-full justify-center" onClick={() => setModal("new-variant")}><Plus size={13} />Satu kombinasi</button>}</aside>
        <div className="min-w-0">{selected ? <>
          <div className="catalog-variant-header"><div className="flex items-start gap-3">{selected.color_hex && <span className="variant-header-dot" style={{ background: selected.color_hex }} />}<div><span data-testid="catalog-selected-sku" className="font-mono text-xs text-gray-500">{selected.sku}</span><h2 data-testid="catalog-selected-name">{variantLabel(selected)}</h2>{(selected.supplier_codes || []).length > 0 && <p data-testid="catalog-selected-supplier-alias" className="text-xs text-[#0058CC]">Versi supplier: {selected.supplier_codes.map(c => `${c.supplier_sku}${c.supplier_item_name ? ` — ${c.supplier_item_name}` : ""}${c.supplier_name ? ` (${c.supplier_name})` : ""}`).join(" · ")}</p>}{(selected.color_ref || selected.rnd_supplier) && <div data-testid="catalog-selected-colors" className="mt-1 flex flex-wrap items-center gap-1.5 text-xs"><ProductColorChip product={selected} />{selected.rnd_supplier && <span className="text-[#6B6B73]">· supplier pemenang R&amp;D <b className="text-[#1C1C1E]">{selected.rnd_supplier.name}</b>{selected.rnd_supplier.contract_number ? ` (kontrak ${selected.rnd_supplier.contract_number})` : ""}</span>}</div>}<p data-testid="catalog-selected-stock" className="variant-header-meta">{stock ? <><b>{stock.available}</b> {family.base_unit} tersedia · dipesan {stock.reserved} · {stock.rolls} roll</> : "Memuat stok…"}<span>·</span><b>{formatCurrency(selected.price)}</b>/{family.base_unit}</p></div></div>{caps.update && <button data-testid="catalog-edit-variant" className="secondary-button" onClick={() => setModal("variant")}><Pencil size={13} />Ubah SKU</button>}</div>
          {tab === "rnd" ? <ProductRelations product={selected} caps={caps} onCreate={() => openRnd({ view: "rnd-specs", create: true, templateId: family.id, productId: selected.id })} /> : <VariantMedia key={`${selected.id}:${selectedEntity}`} product={selected} meta={meta} onChanged={refresh} />}
        </> : <div className="catalog-empty" data-testid="catalog-detail-empty"><Images size={30} strokeWidth={1} /><p>Tambahkan varian untuk mulai mengelola SKU dan fotonya.</p></div>}</div>
      </div>}
    </>}
    {["create", "edit"].includes(modal) && <FamilyForm template={modal === "edit" ? family : null} axisConfig={meta?.variant_axes} onClose={() => setModal("")} onSaved={async id => { setModal(""); setNotice("Induk produk tersimpan."); await load(); await open(id); }} />}
    {modal === "generate" && family && <GenerateVariants template={family} onClose={() => setModal("")} onDone={async r => { setModal(""); setNotice(`${r.created} SKU dibuat${r.skipped ? `; ${r.skipped} kombinasi sudah ada` : ""}.`); await refresh(); }} />}
    {modal === 'link' && family && <LinkExistingVariant template={family} onClose={() => setModal('')} onSaved={async () => { setModal(''); setNotice('SKU tertaut tanpa mengganti ID dan dokumennya.'); await refresh(); }} />}
    {["variant", "new-variant"].includes(modal) && family && <VariantEditor template={family} product={modal === "variant" ? selected : null} onClose={() => setModal("")} onSaved={async () => { setModal(""); setNotice("SKU tersimpan."); await refresh(); }} />}
  </div>;
}