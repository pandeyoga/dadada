import { useEffect, useState } from "react";
import { FlaskConical, ArrowUpRight, GitBranch, Palette } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { openRnd } from "../rnd/rndDeepLink";
import { catalogError } from "./catalogApi";

const STATUS_CLS = { approved: "pill-success", active: "pill-success", draft: "pill-muted", review: "pill-info", revision: "pill-warning" };

/** Tab "R&D & asal desain": spesifikasi terkait, hitungan sampel, jejak desain. */
export const ProductRelations = ({ product, caps, onCreate }) => {
  const [rows, setRows] = useState(null); const [error, setError] = useState("");
  useEffect(() => { let live = true; setRows(null); setError(""); axios.get(`${API}/products/${product.id}/catalog-relations`).then(r => { if (live) setRows(r.data); }).catch(e => { if (live) setError(catalogError(e)); }); return () => { live = false; }; }, [product.id]);
  const artworks = (product.media || []).filter(m => m.kind === "artwork" && m.status === "approved");
  return <section data-testid="catalog-relations" className="relations-grid">
    <div className="info-card">
      <h2 className="flex items-center gap-2"><GitBranch size={15} className="text-[#0058CC]" />Spesifikasi R&D terkait</h2>
      {error && <p data-testid="relations-error" role="alert" className="text-sm text-red-700">{error}</p>}
      {!rows && !error && <p data-testid="relations-loading" className="text-sm text-[#737780]">Memuat hubungan…</p>}
      {rows?.specs.map(s => <button data-testid={`relations-spec-${s.id}`} key={s.id} className="relation-row" onClick={() => openRnd({ view: "rnd-specs", specId: s.id })}><span><strong>{s.number}</strong><span>{s.title}</span></span><span className="flex items-center gap-2"><span className={`status-pill ${STATUS_CLS[s.status] || "pill-muted"}`}>{s.status}</span><span className="status-pill pill-muted">{s.lifecycle}</span><ArrowUpRight size={15} /></span></button>)}
      {rows && !rows.specs.length && <p data-testid="relations-empty" className="relation-empty">Belum ada spesifikasi R&D terkait varian ini.</p>}
      {rows && <p data-testid="relations-sample-count" className="mt-3 text-xs text-[#737780]"><b className="text-[#1c1c1e]">{rows.sample_count}</b> permintaan sampel dalam entitas aktif.</p>}
      {caps.rnd_create && !product.spec_id && product.lifecycle && product.lifecycle !== "produksi" && <button data-testid="relations-create-spec" className="primary-button mt-3" onClick={onCreate}><FlaskConical size={14} />Buat spesifikasi untuk varian ini</button>}
    </div>
    <div className="info-card">
      <h2 className="flex items-center gap-2"><Palette size={15} className="text-[#0058CC]" />Asal desain & artwork</h2>
      <dl className="spec-list">
        <div className="spec-row"><dt>Desain sumber</dt><dd>{product.design_id ? <code>{product.design_id}</code> : "Belum ditautkan ke Design Studio"}</dd></div>
        <div className="spec-row"><dt>Motif</dt><dd>{product.motif || "—"}</dd></div>
        <div className="spec-row"><dt>Warna master</dt><dd className="flex items-center gap-2">{product.color_hex && <i className="inline-block h-3 w-3 rounded-full border" style={{ background: product.color_hex }} />}{product.color_name || product.color || "—"}{product.color_code && <code>{product.color_code}</code>}</dd></div>
        <div className="spec-row"><dt>Siklus hidup</dt><dd>{product.lifecycle || "produksi"}</dd></div>
      </dl>
      {artworks.length ? <div className="artwork-strip" data-testid="relations-artworks">{artworks.map(a => <figure key={a.id}><img src={`${API.replace(/\/api$/, "")}${a.url}`} alt={a.filename} /><figcaption>{a.filename}</figcaption></figure>)}</div> : <p className="relation-empty">Belum ada artwork disetujui pada varian ini.</p>}
    </div>
  </section>;
};
