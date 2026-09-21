/**
 * DesignGalleryView — SHOWCASE desain yang sudah ACC (approved / final / aktif).
 * Tidak ada tombol buat/tambah: desain lahir dari Design Studio (Desain & Pattern).
 * Filter: cari · status · kategori pattern · kategori design · tag · desainer · status R&D · lini.
 */
import DesignImage from "../rnd/design/DesignImage";
import { useEffect, useMemo, useState } from "react";
import { Award, ImageOff, Palette, Search, X } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import KNSelect from "../../components/KNSelect";
import { listDesigns, designFileUrl } from "../rnd/rndApi";
import { DESIGN_STATUS_META, PROOFING_STATE_META, fmtScore } from "../rnd/rndMeta";
import DesignShowcaseModal from "./DesignShowcaseModal";

const ACC_STATUSES = ["approved", "final_submitted", "active"];
const coverOf = (g) => (g.files || []).find((f) => (f.kind || "artwork") === "artwork" && (f.version || 1) === (g.approved_version || g.version))
  || (g.files || []).find((f) => (f.kind || "artwork") === "artwork");
const uniq = (arr) => Array.from(new Set(arr.filter(Boolean))).sort();
const opts = (vals, all) => [{ value: "", label: all }, ...vals.map((v) => ({ value: v, label: v }))];

export default function DesignGalleryView({ selectedEntity }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [f, setF] = useState({ status: "", cat: "", dcat: "", tag: "", designer: "", rnd: "", line: "" });
  const [openId, setOpenId] = useState(null);
  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v }));

  useEffect(() => { load(); }, [selectedEntity]); // eslint-disable-line
  async function load() {
    setLoading(true);
    try {
      const params = selectedEntity && selectedEntity !== "all" ? { entity_id: selectedEntity } : {};
      const rows = await listDesigns(params);
      setItems((Array.isArray(rows) ? rows : []).filter((g) => ACC_STATUSES.includes(g.status)));
      setError("");
    } catch (e) { setError(e.response?.data?.detail || "Gagal memuat galeri."); }
    finally { setLoading(false); }
  }

  const options = useMemo(() => ({
    cat: uniq(items.map((g) => g.category_name || g.category_code)),
    dcat: uniq(items.map((g) => g.design_category_name || g.design_category_code)),
    tag: uniq(items.flatMap((g) => g.tags || [])),
    designer: uniq(items.map((g) => g.created_by)),
    line: uniq(items.map((g) => g.line_code)),
  }), [items]);

  const visible = useMemo(() => {
    const s = q.trim().toLowerCase();
    return items.filter((g) => (
      (!f.status || g.status === f.status)
      && (!f.cat || (g.category_name || g.category_code) === f.cat)
      && (!f.dcat || (g.design_category_name || g.design_category_code) === f.dcat)
      && (!f.tag || (g.tags || []).includes(f.tag))
      && (!f.designer || g.created_by === f.designer)
      && (!f.rnd || (g.proofing?.state || "none") === f.rnd)
      && (!f.line || g.line_code === f.line)
      && (!s || [g.title, g.code, g.story, ...(g.tags || []), ...(g.recommended_products || []).map((p) => `${p.sku} ${p.name}`)]
        .some((t) => String(t || "").toLowerCase().includes(s)))
    ));
  }, [items, q, f]);
  const activeFilters = Object.values(f).filter(Boolean).length + (q ? 1 : 0);

  return (
    <div className="grid gap-3" data-testid="design-gallery-view">
      <section className="section-card !p-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-0">
            <p className="kicker">Showcase</p>
            <h2 className="text-[15px] font-bold text-[#1C1C1E]">Galeri Desain ACC</h2>
            <p className="text-[11px] text-[#6B6B73]">Hanya desain yang sudah disetujui penilai. Desain baru dibuat & dinilai lewat tab <b>Desain &amp; Pattern</b>.</p>
          </div>
          <div className="relative ml-auto min-w-[220px] max-w-[360px] flex-1">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
            <input data-testid="gallery-search" className="field !pl-8" placeholder="Cari kode, judul, tag, produk…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        <div className="mt-2.5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7" data-testid="gallery-filters">
          <KNSelect data-testid="gallery-filter-status" className="field" value={f.status} onValueChange={set("status")}
            options={[{ value: "", label: "Semua status ACC" }, ...ACC_STATUSES.map((s) => ({ value: s, label: DESIGN_STATUS_META[s].label }))]} />
          <KNSelect data-testid="gallery-filter-category" className="field" value={f.cat} onValueChange={set("cat")} options={opts(options.cat, "Semua kategori pattern")} />
          <KNSelect data-testid="gallery-filter-dcategory" className="field" value={f.dcat} onValueChange={set("dcat")} options={opts(options.dcat, "Semua kategori design")} />
          <KNSelect data-testid="gallery-filter-tag" className="field" value={f.tag} onValueChange={set("tag")} options={opts(options.tag, "Semua tag")} />
          <KNSelect data-testid="gallery-filter-designer" className="field" value={f.designer} onValueChange={set("designer")} options={opts(options.designer, "Semua desainer")} />
          <KNSelect data-testid="gallery-filter-rnd" className="field" value={f.rnd} onValueChange={set("rnd")}
            options={[{ value: "", label: "Semua status R&D" }, ...Object.entries(PROOFING_STATE_META).map(([k, m]) => ({ value: k, label: m.label }))]} />
          <KNSelect data-testid="gallery-filter-line" className="field" value={f.line} onValueChange={set("line")} options={opts(options.line, "Semua lini")} />
        </div>
        <div className="mt-2 flex items-center justify-between text-[11px] text-[#6B6B73]">
          <span data-testid="gallery-count"><b>{visible.length}</b> dari {items.length} desain ACC</span>
          {activeFilters > 0 && (
            <button className="inline-flex items-center gap-1 text-[#0058CC]" data-testid="gallery-filter-reset"
              onClick={() => { setQ(""); setF({ status: "", cat: "", dcat: "", tag: "", designer: "", rnd: "", line: "" }); }}>
              <X size={11} /> Hapus {activeFilters} filter
            </button>
          )}
        </div>
      </section>

      {error && <ErrorNotice message={error} onRetry={load} testId="gallery-error" />}

      {loading ? (
        <div className="section-card !p-10 text-center"><p className="text-[12px] text-[#6B6B73]" data-testid="gallery-loading">Memuat galeri…</p></div>
      ) : items.length === 0 ? (
        <div className="section-card !p-12 text-center" data-testid="gallery-empty">
          <Palette size={30} className="mx-auto mb-2 text-[#C7C9CF]" />
          <p className="text-[13px] font-semibold text-[#3A3B42]">Belum ada desain yang di-ACC</p>
          <p className="mt-0.5 text-[12px] text-[#9A9BA3]">Desain tampil di sini otomatis setelah disetujui penilai di Desain &amp; Pattern.</p>
        </div>
      ) : visible.length === 0 ? (
        <div className="section-card !p-12 text-center" data-testid="gallery-filter-empty">
          <Palette size={30} className="mx-auto mb-2 text-[#C7C9CF]" />
          <p className="text-[13px] font-semibold text-[#3A3B42]">Tidak ada desain yang cocok dengan filter</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="gallery-grid">
          {visible.map((g) => <ShowcaseCard key={g.id} g={g} onOpen={() => setOpenId(g.id)} />)}
        </div>
      )}

      {openId && <DesignShowcaseModal designId={openId} onClose={() => setOpenId(null)} />}
    </div>
  );
}

function ShowcaseCard({ g, onOpen }) {
  const cover = coverOf(g);
  const st = DESIGN_STATUS_META[g.status] || DESIGN_STATUS_META.approved;
  const pm = PROOFING_STATE_META[g.proofing?.state || "none"] || PROOFING_STATE_META.none;
  const prods = g.recommended_products || [];
  return (
    <button type="button" onClick={onOpen} data-testid={`gallery-card-${g.id}`}
      className="section-card flex flex-col overflow-hidden !p-0 text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#6B219A]/40">
      <div className="relative aspect-[4/3] bg-[#F2F3F5]">
        {cover ? <DesignImage src={designFileUrl(g.id, cover.id)} alt={g.title} className="h-full w-full object-cover" loading="lazy" />
          : <div className="flex h-full w-full flex-col items-center justify-center text-[#C7C9CF]"><ImageOff size={26} /><span className="mt-1 text-[11px]">Tanpa gambar</span></div>}
        <span className={`status-pill absolute left-2 top-2 ${st.cls}`} data-testid={`gallery-card-status-${g.id}`}>{st.label}</span>
        {g.final_score != null && (
          <span className="absolute right-2 top-2 inline-flex items-center gap-1 rounded bg-white/95 px-1.5 py-0.5 text-[10px] font-bold text-[#1A7A3A]" data-testid={`gallery-card-score-${g.id}`}>
            <Award size={10} /> {fmtScore(g.final_score)}/2
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <p className="font-mono text-[10.5px] text-[#6B6B73]">{g.code}</p>
        <h3 className="truncate text-[13px] font-bold leading-tight">{g.title}</h3>
        <p className="text-[10.5px] text-[#6B6B73]">
          {g.category_name || g.category_code || "—"} · {g.design_category_name || g.design_category_code || "—"} · {g.created_by}
        </p>
        <div className="flex flex-wrap gap-1">
          {(g.tags || []).slice(0, 4).map((t) => <span key={t} className="rounded bg-[#F1E9F7] px-1.5 py-0.5 text-[10px] text-[#6B219A]">{t}</span>)}
          {(g.tags || []).length > 4 && <span className="text-[10px] text-[#9A9BA3]">+{g.tags.length - 4}</span>}
        </div>
        <div className="mt-auto flex flex-wrap items-center justify-between gap-1 pt-1.5 text-[10.5px]">
          <span className="rounded px-1.5 py-0.5 font-semibold" style={{ background: pm.bg, color: pm.fg }} data-testid={`gallery-card-rnd-${g.id}`}>{pm.label}</span>
          <span className="text-[#6B6B73]">{prods.length ? `${prods.length} produk` : "belum ada produk"}</span>
        </div>
      </div>
    </button>
  );
}
