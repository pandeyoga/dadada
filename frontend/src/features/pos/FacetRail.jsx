import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { SlidersHorizontal, RotateCcw, Building2, X } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { useEscapeClose } from "@/utils/escapeLayers";

export const DEFAULT_FACETS = {
  categories: [], grades: [], colors: [],
  priceMin: "", priceMax: "", availability: "all", sort: "relevance",
};

const SORT_OPTIONS = [
  { value: "relevance", label: "Relevansi" },
  { value: "price_asc", label: "Harga ↑" },
  { value: "price_desc", label: "Harga ↓" },
  { value: "avail_desc", label: "Ketersediaan ↓" },
  { value: "name_asc", label: "Nama A-Z" },
];

const AVAIL_OPTIONS = [
  { value: "all", label: "Semua" },
  { value: "available", label: "Tersedia (ATP > 0)" },
  { value: "low", label: "Stok rendah" },
];

// UI/UX 2026-06 — rel filter hanya menampilkan CUPLIKAN chip per grup; katalog kain
// punya belasan kategori & puluhan warna, dan dulu semuanya digelar ke bawah sampai
// rel-nya sendiri harus di-scroll. Selebihnya dibuka lewat pop-up "Semua Filter".
const CHIP_PREVIEW = 8;

function uniq(arr) { return [...new Set(arr.filter(Boolean))].sort(); }

/** EPIC5 — facet rail Discover: Kategori/Grade/Warna/Harga/Ketersediaan/Entitas + sort. */
export function FacetRail({ products = [], facets, setFacets, selectedEntity = "all", entityName, loading = false }) {
  const [showAll, setShowAll] = useState(false);
  const opts = useMemo(() => ({
    categories: uniq(products.map((p) => p.category)),
    grades: uniq(products.map((p) => p.grade)),
    colors: uniq(products.map((p) => p.color)),
    colorHex: products.reduce((m, p) => { if (p.color && p.color_hex && !m[p.color]) m[p.color] = p.color_hex; return m; }, {}),
  }), [products]);

  const toggle = (key, val) => setFacets((f) => {
    const set = new Set(f[key]);
    set.has(val) ? set.delete(val) : set.add(val);
    return { ...f, [key]: [...set] };
  });

  const activeCount = facets.categories.length + facets.grades.length + facets.colors.length
    + (facets.priceMin ? 1 : 0) + (facets.priceMax ? 1 : 0) + (facets.availability !== "all" ? 1 : 0);

  const moreCount = Math.max(0, opts.categories.length - CHIP_PREVIEW)
    + Math.max(0, opts.grades.length - CHIP_PREVIEW)
    + Math.max(0, opts.colors.length - CHIP_PREVIEW);

  const groups = (limit) => (
    <>
      <FacetGroup label="Kategori" testid="facet-categories">
        <Chips options={opts.categories} selected={facets.categories} onToggle={(v) => toggle("categories", v)}
          group="category" limit={limit} onMore={() => setShowAll(true)} />
      </FacetGroup>
      <FacetGroup label="Grade" testid="facet-grades">
        <Chips options={opts.grades} selected={facets.grades} onToggle={(v) => toggle("grades", v)}
          group="grade" limit={limit} onMore={() => setShowAll(true)} />
      </FacetGroup>
      <FacetGroup label="Warna" testid="facet-colors">
        <Chips options={opts.colors} selected={facets.colors} onToggle={(v) => toggle("colors", v)}
          group="color" hexMap={opts.colorHex} limit={limit} onMore={() => setShowAll(true)} />
      </FacetGroup>
    </>
  );

  return (
    <aside data-testid="facet-rail"
      className="section-card self-start lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:!overflow-y-auto">
      <div className="section-head">
        <div className="flex items-center gap-2"><SlidersHorizontal size={14} className="text-[#0058CC]" /><h2 className="text-[13px]">Filter</h2></div>
        {activeCount > 0 && (
          <button data-testid="facet-reset" className="ml-auto inline-flex items-center gap-1 text-[11px] font-semibold text-[#0058CC]" onClick={() => setFacets(DEFAULT_FACETS)}>
            <RotateCcw size={12} /> Reset ({activeCount})
          </button>
        )}
      </div>
      <div className="section-body space-y-3">
        {loading && <p data-testid="facet-loading" className="animate-pulse text-[11px] text-[#6B6B73]">Memuat opsi filter…</p>}
        <div>
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Urutkan</label>
          <KNSelect data-testid="facet-sort" className="field" value={facets.sort} onValueChange={(v) => setFacets((f) => ({ ...f, sort: v }))} options={SORT_OPTIONS} />
        </div>

        {groups(CHIP_PREVIEW)}

        <div>
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Rentang Harga (Rp)</label>
          <div className="grid grid-cols-2 gap-2">
            <input data-testid="facet-price-min" type="number" min="0" className="field" placeholder="Min" value={facets.priceMin} onChange={(e) => setFacets((f) => ({ ...f, priceMin: e.target.value }))} />
            <input data-testid="facet-price-max" type="number" min="0" className="field" placeholder="Max" value={facets.priceMax} onChange={(e) => setFacets((f) => ({ ...f, priceMax: e.target.value }))} />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Ketersediaan</label>
          <KNSelect data-testid="facet-availability" className="field" value={facets.availability} onValueChange={(v) => setFacets((f) => ({ ...f, availability: v }))} options={AVAIL_OPTIONS} />
        </div>

        {moreCount > 0 && (
          <button type="button" data-testid="facet-open-all"
            onClick={() => setShowAll(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-[#C9D6E8] bg-[#F8FAFD] px-3 py-2 text-[11.5px] font-semibold text-[#0058CC] transition-colors hover:bg-[#EFF4FF]">
            <SlidersHorizontal size={12} /> Semua Filter{activeCount > 0 ? ` (${activeCount} aktif)` : ""}
          </button>
        )}

        <div data-testid="facet-entity" className="rounded-md border border-[#E5E5EA] bg-[#FAFBFC] p-2">
          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]"><Building2 size={12} /> Entitas</div>
          <p className="mt-1 text-[12px] font-semibold text-[#1C1C1E]" data-testid="facet-entity-name">
            {selectedEntity === "all" ? "Semua entitas" : (entityName || "Entitas aktif")}
          </p>
          <p className="text-[10px] text-[#9A9BA3]">Ketersediaan dihitung per entitas aktif (ubah via pemilih entitas di header).</p>
        </div>
      </div>

      {showAll && (
        <AllFiltersModal onClose={() => setShowAll(false)} activeCount={activeCount}
          facets={facets} setFacets={setFacets} opts={opts} toggle={toggle} />
      )}
    </aside>
  );
}

/** Pop-up "Semua Filter" — seluruh chip tanpa potongan + harga + ketersediaan.
 *  Di-portal ke <body> dengan z-[120] (tangga z-index POS: drawer 110-130) — kartu
 *  produk memakai transform sehingga membuat stacking context yang menutup overlay
 *  biasa. */
function AllFiltersModal({ onClose, facets, setFacets, opts, toggle, activeCount }) {
  useEscapeClose(true, onClose);
  return createPortal(
    <div className="modal-overlay fixed inset-0 z-[120] flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center"
      style={{ zIndex: 120 }}
      data-testid="facet-modal-overlay" {...overlayDismiss(onClose)}>
      <div role="dialog" aria-modal="true" data-testid="facet-modal"
        className="my-auto w-full max-w-xl rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 rounded-t-xl border-b border-[#EFF0F2] bg-white px-4 py-3">
          <h3 className="flex items-center gap-2 text-[13.5px] font-bold text-[#1C1C1E]">
            <SlidersHorizontal size={15} className="text-[#0058CC]" /> Semua Filter
            {activeCount > 0 && (
              <span className="rounded-full bg-[#EFF4FF] px-2 py-0.5 text-[10.5px] font-bold tabular-nums text-[#0058CC]">
                {activeCount} aktif
              </span>
            )}
          </h3>
          <button type="button" className="icon-button" aria-label="Tutup"
            data-testid="facet-modal-close" onClick={onClose}><X size={14} /></button>
        </div>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto px-4 py-3">
          <FacetGroup label={`Kategori (${opts.categories.length})`} testid="facet-modal-categories">
            <Chips options={opts.categories} selected={facets.categories} onToggle={(v) => toggle("categories", v)} group="m-category" />
          </FacetGroup>
          <FacetGroup label={`Grade (${opts.grades.length})`} testid="facet-modal-grades">
            <Chips options={opts.grades} selected={facets.grades} onToggle={(v) => toggle("grades", v)} group="m-grade" />
          </FacetGroup>
          <FacetGroup label={`Warna (${opts.colors.length})`} testid="facet-modal-colors">
            <Chips options={opts.colors} selected={facets.colors} onToggle={(v) => toggle("colors", v)} group="m-color" hexMap={opts.colorHex} />
          </FacetGroup>
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Rentang Harga (Rp)</label>
            <div className="grid grid-cols-2 gap-2">
              <input data-testid="facet-modal-price-min" type="number" min="0" className="field" placeholder="Min" value={facets.priceMin} onChange={(e) => setFacets((f) => ({ ...f, priceMin: e.target.value }))} />
              <input data-testid="facet-modal-price-max" type="number" min="0" className="field" placeholder="Max" value={facets.priceMax} onChange={(e) => setFacets((f) => ({ ...f, priceMax: e.target.value }))} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Ketersediaan</label>
            <KNSelect data-testid="facet-modal-availability" className="field" value={facets.availability} onValueChange={(v) => setFacets((f) => ({ ...f, availability: v }))} options={AVAIL_OPTIONS} />
          </div>
        </div>

        <div className="sticky bottom-0 flex items-center justify-between gap-2 rounded-b-xl border-t border-[#EFF0F2] bg-[#FAFBFC] px-4 py-2.5">
          <button type="button" data-testid="facet-modal-reset"
            className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#6B6B73] hover:text-[#C62828]"
            onClick={() => setFacets(DEFAULT_FACETS)}>
            <RotateCcw size={12} /> Reset semua
          </button>
          <button type="button" data-testid="facet-modal-apply" className="primary-button" onClick={onClose}>
            Terapkan
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

function FacetGroup({ label, testid, children }) {
  return (
    <div data-testid={testid}>
      <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">{label}</label>
      {children}
    </div>
  );
}

function Chips({ options, selected, onToggle, group, hexMap = {}, limit = 0, onMore }) {
  // FASE P5 — dulu hanya "—": pengguna tidak tahu apakah penyaring ini memang kosong
  // untuk katalog saat ini, atau datanya gagal dimuat.
  if (!options.length) {
    return (
      <p className="text-[11px] text-[#9A9BA3]" data-testid={`facet-empty-${group}`}>
        Tidak ada pilihan untuk katalog ini.
      </p>
    );
  }
  // Cuplikan chip: yang SEDANG terpilih selalu ikut tampil walau di luar batas,
  // supaya filter aktif tidak pernah "hilang" dari rel.
  let shown = options;
  let hidden = 0;
  if (limit > 0 && options.length > limit) {
    const head = options.slice(0, limit);
    const extraSelected = options.slice(limit).filter((o) => selected.includes(o));
    shown = [...head, ...extraSelected];
    hidden = options.length - shown.length;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((o) => {
        const on = selected.includes(o);
        const hex = group.endsWith("color") ? hexMap[o] : null;
        return (
          <button key={o} data-testid={`facet-${group}-${o}`} onClick={() => onToggle(o)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${on ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#0058CC]"}`}>
            {hex && <span className="h-3 w-3 rounded-full border border-black/10" style={{ backgroundColor: hex }} />}
            {o}
          </button>
        );
      })}
      {hidden > 0 && (
        <button type="button" data-testid={`facet-more-${group}`} onClick={onMore}
          className="inline-flex items-center rounded-full border border-dashed border-[#C9D6E8] bg-[#F8FAFD] px-2.5 py-1 text-[11px] font-semibold text-[#0058CC] hover:bg-[#EFF4FF]">
          +{hidden} lagi…
        </button>
      )}
    </div>
  );
}
