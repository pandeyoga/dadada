/**
 * LinkedDesignsPanel — desain Design Studio yang tertaut ke satu Permintaan Desain.
 * Di sinilah kedua alur bertemu: desainer MEMBUAT desain dari permintaan (kode otomatis,
 * kategori ikut) atau MENAUTKAN desain yang sudah ada; status permintaan lalu mengikuti
 * siklus hidup desain (ajukan → Review, minta revisi → Revisi, ACC → ACC).
 */
import { useEffect, useState } from "react";
import { ExternalLink, Link2, Plus, Sparkles } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import { openRnd } from "../rnd/rndDeepLink";
import { designFileUrl } from "../rnd/rndApi";
import { DESIGN_STATUS_META, fmtScore } from "../rnd/rndMeta";
import { createDesignFromRequest, linkDesignToRequest, linkableDesigns } from "./designRequestsApi";

export function DesignMiniCard({ d, testId }) {
  const meta = DESIGN_STATUS_META[d.status] || DESIGN_STATUS_META.draft;
  return (
    <div data-testid={testId} className="flex items-center gap-2.5 rounded-lg border border-[#EFF0F2] bg-white p-2">
      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-md bg-[#F5F5F7]">
        {d.cover_file_id
          ? <img src={designFileUrl(d.id, d.cover_file_id)} alt={d.title} className="h-full w-full object-cover" loading="lazy" />
          : <span className="flex h-full items-center justify-center px-1 text-center text-[9px] text-[#9A9BA3]">belum ada berkas</span>}
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-[11.5px] font-bold text-[#1C1C1E]">{d.code || "tanpa kode"}</span>
          <span className={`status-pill ${meta.cls}`}>{meta.label}</span>
        </p>
        <p className="truncate text-[11px] text-[#3C3C43]">{d.title}</p>
        <p className="text-[10px] text-[#8E8E93]">
          {d.round_label} · {d.artwork_count || 0} berkas
          {d.final_score !== null && d.final_score !== undefined ? ` · nilai ACC ${fmtScore(d.final_score)}` : " · belum ACC (nilai diberikan saat ACC)"}
          {d.created_by ? ` · ${d.created_by}` : ""}
        </p>
      </div>
      <button type="button" data-testid={`${testId}-open`} className="secondary-button !py-1 text-[10.5px]"
        onClick={() => openRnd({ view: "rnd-designs", designId: d.id })}>
        <ExternalLink size={11} /> Buka
      </button>
    </div>
  );
}

export default function LinkedDesignsPanel({ doc, canWork, onChanged, onError }) {
  const designs = doc.designs || [];
  const canStart = canWork && ["assigned", "in_progress", "revision"].includes(doc.status);
  const [title, setTitle] = useState((doc.brief || "").slice(0, 80));
  const [pick, setPick] = useState("");
  const [choices, setChoices] = useState([]);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("create");
  const hasCats = !!doc.category_code && !!doc.design_category_code;

  useEffect(() => {
    if (!canStart || mode !== "link") return;
    linkableDesigns().then((rows) => setChoices(rows.map((g) => ({
      value: g.id, label: `${g.code || "(tanpa kode)"} · ${g.title || ""} · ${(DESIGN_STATUS_META[g.status] || {}).label || g.status}` }))))
      .catch(() => setChoices([]));
  }, [canStart, mode]);

  async function run(fn, goto) {
    setBusy(true);
    try {
      const fresh = await fn();
      onChanged?.(fresh, goto ? fresh?.design?.id : null);
    } catch (e) { onError?.(e); } finally { setBusy(false); }
  }

  return (
    <div className="section-card" data-testid="dsr-linked-designs">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Desain di Design Studio</p>
        <span className="text-[10.5px] text-[#8E8E93]">{designs.length} tertaut</span>
      </div>

      {designs.length > 0 ? (
        <div className="grid gap-1.5">
          {designs.map((d) => <DesignMiniCard key={d.id} d={d} testId={`dsr-design-${d.id}`} />)}
        </div>
      ) : (
        <p data-testid="dsr-designs-empty" className="rounded-lg bg-[#FAFBFC] px-3 py-2 text-[11px] text-[#6B6B73]">
          Belum ada desain. {canStart ? "Mulai dari sini — kode desain terbentuk otomatis dari kategori permintaan."
            : doc.status === "submitted" ? "Desainer bisa mulai setelah ditugaskan." : "Desainer yang ditugaskan akan membuatnya di Design Studio."}
        </p>
      )}

      {canStart && (
        <div className="mt-3 rounded-xl border border-dashed border-[#C9B3DB] bg-[#FBF7FE] p-3" data-testid="dsr-start-work">
          <div className="mb-2 flex gap-1.5">
            <button type="button" data-testid="dsr-mode-create" onClick={() => setMode("create")}
              className={`status-pill ${mode === "create" ? "pill-info" : "pill-muted"}`}><Plus size={10} className="inline" /> Buat desain baru</button>
            <button type="button" data-testid="dsr-mode-link" onClick={() => setMode("link")}
              className={`status-pill ${mode === "link" ? "pill-info" : "pill-muted"}`}><Link2 size={10} className="inline" /> Tautkan yang sudah ada</button>
          </div>
          {mode === "create" ? (
            <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="block">
                <span className="field-label">Judul desain</span>
                <input data-testid="dsr-new-design-title" className="field" value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder="mis. Salur Pelangi Senja" />
              </label>
              <button type="button" data-testid="dsr-create-design-button" className="primary-button" disabled={busy || !title.trim() || !hasCats}
                onClick={() => run(() => createDesignFromRequest(doc.id, title), true)}>
                <Sparkles size={13} /> Buat & buka desain
              </button>
              <p className="text-[10.5px] text-[#6B6B73] sm:col-span-2">
                {hasCats
                  ? <>Kategori <b>{doc.category_name || doc.category_code}</b> · <b>{doc.design_category_name || doc.design_category_code}</b>, brief{(doc.references || []).length ? <>, dan <b>{doc.references.length} gambar referensi</b></> : ""} ikut ke desain; permintaan menjadi <b>Dikerjakan</b>. Unggah berkas lalu <b>Ajukan</b> di halaman desain — status di sini mengikuti otomatis.</>
                  : <span className="text-[#A8221A]">Permintaan ini belum punya Kategori Pattern & Design — minta atasan melengkapinya (panel kanan) sebelum membuat desain.</span>}
              </p>
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="block">
                <span className="field-label">Desain yang masih berjalan & belum tertaut</span>
                <KNSelect data-testid="dsr-link-design-select" value={pick} onValueChange={setPick} options={choices}
                  className="field" placeholder={choices.length ? "Pilih desain…" : "Tidak ada desain yang bisa ditautkan"} searchable />
              </label>
              <button type="button" data-testid="dsr-link-design-button" className="primary-button" disabled={busy || !pick}
                onClick={() => run(() => linkDesignToRequest(doc.id, pick))}>
                <Link2 size={13} /> Tautkan
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
