import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, Star, Check, X, Trash2, ArrowLeft, ArrowRight, Wand2, RefreshCw } from "lucide-react";
import { ProductGallery, mediaUrl } from "../../components/ProductGallery";
import KNSelect from "../../components/KNSelect";
import { askConfirm } from "../../services/confirmService";
import { catalogApi, catalogError } from "./catalogApi";
import { DesignMediaImport } from "./DesignMediaImport";

const KIND_LABEL = { photo: "Foto produk", detail: "Detail bahan", mockup: "Mockup", artwork: "Artwork" };
const STATUS_LABEL = { draft: "Menunggu tinjauan", approved: "Disetujui", rejected: "Ditolak" };
const KIND_OPTIONS = Object.entries(KIND_LABEL).map(([value, label]) => ({ value, label }));

export const VariantMedia = ({ product, meta, onChanged }) => {
  const [items, setItems] = useState([]); const [cover, setCover] = useState(""); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState("photo"); const [filter, setFilter] = useState("all"); const [source, setSource] = useState(""); const [prompt, setPrompt] = useState("");
  const [showAI, setShowAI] = useState(false); const fileRef = useRef(null);
  const caps = meta?.permissions || {};
  const load = useCallback(async () => { setLoading(true); try { const d = await catalogApi.media(product.id); setItems(d.items || []); setCover(d.cover_media_id); setError(""); } catch (e) { setError(catalogError(e)); } finally { setLoading(false); } }, [product.id]);
  useEffect(() => { setSource(""); setPrompt(""); setNotice(""); setFilter("all"); load(); }, [load]);
  const act = async fn => { setBusy(true); setError(""); try { await fn(); await load(); onChanged?.(); } catch (e) { setError(catalogError(e)); } finally { setBusy(false); } };
  const upload = async files => { const batch = Array.from(files || []); if (!batch.length) return; setBusy(true); setError(""); let done = 0; const failures = []; for (const f of batch) { try { await catalogApi.upload(product.id, f, kind); done++; } catch (e) { failures.push(`${f.name}: ${catalogError(e)}`); } } await load(); onChanged?.(); setNotice(`${done} foto tersimpan untuk ditinjau.`); setError(failures.join("; ")); setBusy(false); if (fileRef.current) fileRef.current.value = ""; };
  const counts = items.reduce((a, m) => ({ ...a, [m.kind]: (a[m.kind] || 0) + 1 }), {});
  const shown = filter === "all" ? items : items.filter(m => m.kind === filter);
  const approvedShown = shown.filter(m => m.status === "approved");
  return <section data-testid={`variant-media-${product.id}`} className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-semibold" data-testid="media-heading">Galeri varian <span className="ml-1 text-xs text-gray-500">{items.length} / {meta?.max_media || 30}</span></h3>
      <div className="flex flex-wrap items-center gap-2">
        {caps.update && <><KNSelect data-testid="media-kind" className="field !w-36" value={kind} onValueChange={setKind} options={KIND_OPTIONS} />
          <button data-testid="media-upload-button" className="primary-button" disabled={busy} onClick={() => fileRef.current?.click()}><Upload size={14} />{busy ? "Memproses…" : "Unggah"}</button>
          <input data-testid="media-file-input" ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="sr-only" disabled={busy} onChange={e => upload(e.target.files)} /></>}
        <button data-testid="media-refresh" className="icon-button" title="Muat ulang galeri" onClick={load} disabled={busy}><RefreshCw size={15} /></button>
      </div>
    </div>
    {error && <p data-testid="media-error" role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p data-testid="media-notice" role="status" className="rounded bg-green-50 p-3 text-sm text-green-800">{notice}</p>}
    {loading ? <div data-testid="media-loading" className="h-40 animate-pulse rounded-lg bg-gray-100" /> : <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)]">
      <div>
        <ProductGallery product={product} items={approvedShown.length ? approvedShown : shown} coverId={cover} testId="media-preview" />
        <p className="mt-2 text-[11px] text-[#737780]">Foto utama & urutan di sini adalah yang dilihat tim sales. Hanya foto <b>disetujui</b> yang tampil di katalog.</p>
      </div>
      <div className="space-y-3">
        <div className="media-kind-tabs" data-testid="media-kind-filter">
          {[["all", `Semua · ${items.length}`], ...Object.entries(KIND_LABEL).map(([k, l]) => [k, `${l} · ${counts[k] || 0}`])].map(([k, l]) => <button key={k} type="button" data-testid={`media-filter-${k}`} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>{l}</button>)}
        </div>
        {!shown.length && <p data-testid="media-empty" className="relation-empty">{items.length ? "Belum ada berkas untuk jenis ini." : "Belum ada foto untuk varian ini. Unggah foto produk, detail bahan, mockup, atau artwork."}</p>}
        <div className="media-grid">{shown.map(m => { const i = items.indexOf(m); return <figure data-testid={`media-item-${m.id}`} key={m.id} className={`media-tile ${m.status}`}>
          <img src={mediaUrl(m.url)} alt={m.filename} loading="lazy" />
          <span className="media-tile-kind">{KIND_LABEL[m.kind]}{m.ai ? " · AI" : ""}</span>
          {cover === m.id && <span className="media-tile-cover" title="Foto utama"><Star size={12} fill="currentColor" /></span>}
          <figcaption className="media-tile-body"><p data-testid={`media-name-${m.id}`} title={m.filename}>{m.filename}</p><small data-testid={`media-state-${m.id}`}>{STATUS_LABEL[m.status]}{cover === m.id ? " · Foto utama" : ""}</small></figcaption>
          <div className="media-tile-actions">
            {caps.review && <><button data-testid={`media-approve-${m.id}`} className="icon-button" title="Setujui untuk sales" disabled={busy || m.status === "approved"} onClick={() => act(() => catalogApi.mediaPatch(product.id, m.id, { status: "approved" }))}><Check size={14} /></button><button data-testid={`media-reject-${m.id}`} className="icon-button" title="Tarik dari katalog sales" disabled={busy || m.status === "rejected"} onClick={() => act(() => catalogApi.mediaPatch(product.id, m.id, { status: "rejected" }))}><X size={14} /></button></>}
            {caps.update && <><button data-testid={`media-cover-${m.id}`} className="icon-button" title="Jadikan foto utama" disabled={busy || m.status !== "approved" || cover === m.id} onClick={() => act(() => catalogApi.mediaPatch(product.id, m.id, { cover: true }))}><Star size={14} /></button><button data-testid={`media-left-${m.id}`} className="icon-button" title="Geser ke kiri" disabled={busy || i === 0} onClick={() => act(() => catalogApi.mediaPatch(product.id, m.id, { sort_order: i - 1 }))}><ArrowLeft size={14} /></button><button data-testid={`media-right-${m.id}`} className="icon-button" title="Geser ke kanan" disabled={busy || i === items.length - 1} onClick={() => act(() => catalogApi.mediaPatch(product.id, m.id, { sort_order: i + 1 }))}><ArrowRight size={14} /></button><button data-testid={`media-delete-${m.id}`} className="icon-button text-red-700" title="Hapus foto" disabled={busy} onClick={async () => { if (await askConfirm({ title: "Hapus foto ini?", message: m.filename, danger: true, confirmLabel: "Hapus" })) act(() => catalogApi.mediaDelete(product.id, m.id)); }}><Trash2 size={14} /></button></>}
          </div>
        </figure>; })}</div>
      </div>
    </div>}
    {caps.update && <div className="border-t pt-4">
      <button data-testid="media-ai-toggle" className="secondary-button" onClick={() => setShowAI(!showAI)}><Wand2 size={14} />Mockup dengan Gemini</button>
      {showAI && <div className="mt-3 space-y-3">
        {!meta?.ai?.enabled ? <p data-testid="media-ai-disabled" className="rounded bg-amber-50 p-3 text-sm text-amber-800">{meta?.ai?.reason || "Gemini belum dikonfigurasi. Unggahan manual tetap tersedia."}</p> : <>
          <KNSelect data-testid="media-ai-source" className="field" value={source} onValueChange={setSource} placeholder="Pilih foto/artwork acuan varian" options={items.filter(m => !m.ai).map(m => ({ value: m.id, label: m.filename }))} />
          <textarea data-testid="media-ai-prompt" className="field min-h-20" placeholder="Contoh: model mengenakan kemeja dari kain ini, tampak depan dan pencahayaan studio" value={prompt} onChange={e => setPrompt(e.target.value)} maxLength={1500} />
          <button data-testid="media-ai-generate" className="primary-button" disabled={busy || !source || prompt.trim().length < 3} onClick={() => act(() => catalogApi.mockup(product.id, { source_media_id: source, prompt: prompt.trim() }))}><Wand2 size={14} />{busy ? "Membuat mockup…" : "Buat mockup untuk ditinjau"}</button>
        </>}
      </div>}
    </div>}
    {caps.update && caps.rnd_view && <DesignMediaImport product={product} busy={busy} onImport={data => act(() => catalogApi.designMedia(product.id, data))} />}
  </section>;
};
