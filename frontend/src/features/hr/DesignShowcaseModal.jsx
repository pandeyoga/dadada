/** DesignShowcaseModal — rincian showcase satu desain ACC: foto, file asli, mockup, info desain & pattern, produk pemakai + status R&D. */
import DesignImage from "../rnd/design/DesignImage";
import { useEffect, useState } from "react";
import { Award, CheckCircle2, Clock, Download, ExternalLink, FileArchive, PackageCheck } from "lucide-react";
import DetailModal from "../../components/DetailModal";
import ErrorNotice from "../../components/ErrorNotice";
import { designFileUrl, getDesign } from "../rnd/rndApi";
import { DESIGN_STATUS_META, PROOFING_STATE_META, errMsg, fmtScore, roundLabel } from "../rnd/rndMeta";
import { openRnd } from "../rnd/rndDeepLink";

const fmtD = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—");
const fmtBytes = (n) => { const b = Number(n) || 0; return b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`; };

export default function DesignShowcaseModal({ designId, onClose }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [hero, setHero] = useState(null);
  useEffect(() => {
    getDesign(designId).then((x) => {
      setD(x);
      const art = (x.files || []).filter((f) => (f.kind || "artwork") === "artwork" && (f.version || 1) === (x.approved_version || x.version));
      setHero(art[0] || (x.files || []).find((f) => (f.kind || "artwork") === "artwork") || null);
    }).catch((e) => setErr(errMsg(e, "Gagal memuat desain.")));
  }, [designId]);

  return (
    <DetailModal open onClose={onClose} size="xl" label="Rincian desain" testId="gallery-showcase-modal" framed>
      {err && <ErrorNotice message={err} testId="gallery-showcase-error" />}
      {!d ? <div className="h-40 animate-pulse rounded-lg bg-[#F5F5F7]" /> : <Body d={d} hero={hero} setHero={setHero} onClose={onClose} />}
    </DetailModal>
  );
}

function Body({ d, hero, setHero, onClose }) {
  const files = d.files || [];
  const artwork = files.filter((f) => (f.kind || "artwork") === "artwork");
  const mockups = files.filter((f) => f.kind === "mockup");
  const sources = files.filter((f) => f.kind === "source");
  const st = DESIGN_STATUS_META[d.status] || DESIGN_STATUS_META.approved;
  const p = d.proofing || { state: "none", samples: [] };
  const pm = PROOFING_STATE_META[p.state] || PROOFING_STATE_META.none;
  const isImg = (f) => f?.content_type?.startsWith("image/");

  return (
    <div className="grid gap-4" data-testid="gallery-showcase">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="kicker">Showcase · Desain ACC</p>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-mono text-[16px] font-bold" data-testid="gallery-showcase-code">{d.code}</h2>
            <span className={`status-pill ${st.cls}`} data-testid="gallery-showcase-status">{st.label}</span>
            {d.final_score != null && (
              <span className="inline-flex items-center gap-1 rounded border border-[#1A7A3A] bg-white px-1.5 py-0.5 text-[11px] font-bold text-[#1A7A3A]" data-testid="gallery-showcase-score">
                <Award size={11} /> {fmtScore(d.final_score)}/2 ACC
              </span>
            )}
          </div>
          <p className="text-[13px] font-semibold text-[#1C1C1E]" data-testid="gallery-showcase-title">{d.title}</p>
        </div>
        <button className="secondary-button !py-1.5 text-[11.5px]" data-testid="gallery-showcase-open-studio"
          onClick={() => { openRnd({ view: "rnd-designs", designId: d.id }); onClose?.(); }}>
          <ExternalLink size={13} /> Buka di Desain &amp; Pattern
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,1fr)]">
        <div className="grid gap-3">
          <div className="overflow-hidden rounded-lg border border-[#E5E5EA] bg-[#F5F5F7]">
            <div className="flex aspect-[4/3] items-center justify-center" data-testid="gallery-showcase-hero">
              {hero ? (isImg(hero)
                ? <DesignImage src={designFileUrl(d.id, hero.id)} alt={hero.filename} className="h-full w-full object-contain" />
                : <a href={designFileUrl(d.id, hero.id)} target="_blank" rel="noreferrer" className="text-[12px] font-bold text-[#0058CC]">Buka PDF {hero.filename}</a>)
                : <span className="text-[11px] text-[#9A9BA3]">tanpa gambar</span>}
            </div>
            {hero && <p className="border-t border-[#EFF0F2] bg-white px-3 py-1.5 text-[10.5px] text-[#6B6B73]">{hero.filename} · {hero.kind === "mockup" ? "Mockup" : roundLabel(hero.version || 1)} · {hero.uploaded_by}</p>}
          </div>

          <Section title={`Foto desain · ${artwork.length}`} testId="gallery-showcase-artwork">
            <Thumbs d={d} files={artwork} hero={hero} setHero={setHero} label={(f) => roundLabel(f.version || 1)} />
          </Section>
          <Section title={`Foto mockup · ${mockups.length}`} testId="gallery-showcase-mockup">
            {mockups.length === 0 ? <Empty>belum ada mockup</Empty> : <Thumbs d={d} files={mockups} hero={hero} setHero={setHero} label={() => "Mockup"} />}
          </Section>
          <Section title={`File desain asli · ${sources.length}`} testId="gallery-showcase-source">
            {sources.length === 0 ? <Empty>belum ada file asli</Empty> : (
              <ul className="divide-y divide-[#F4F5F7] rounded-lg border border-[#EFF0F2]">
                {sources.map((f) => (
                  <li key={f.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2" data-testid={`gallery-source-${f.id}`}>
                    <span className="flex min-w-0 items-center gap-2 text-[11.5px]">
                      <FileArchive size={14} className="shrink-0 text-[#6B219A]" />
                      <span className="min-w-0"><p className="truncate font-semibold">{f.filename}</p><p className="text-[10px] text-[#8E8E93]">{fmtBytes(f.size)} · {fmtD(f.uploaded_at)}</p></span>
                    </span>
                    <a className="secondary-button !py-1 text-[10.5px]" href={`${designFileUrl(d.id, f.id)}?download=1`} download={f.filename} data-testid={`gallery-source-download-${f.id}`}>
                      <Download size={12} /> Unduh
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>

        <div className="grid content-start gap-3">
          <div className="section-card !p-3">
            <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Info desain &amp; pattern</p>
            <Row label="Kategori pattern">{d.category_name || d.category_code || "—"}</Row>
            <Row label="Kategori design">{d.design_category_name || d.design_category_code || "—"}</Row>
            <Row label="Desainer">{d.created_by || "—"}</Row>
            <Row label="Tanggal ACC">{fmtD(d.approved_at)}</Row>
            <Row label="Nilai ACC">{d.final_score != null ? `${fmtScore(d.final_score)} / 2` : "—"}</Row>
            <Row label="Ronde">{d.revision_count || 0}× revisi · ACC pada {roundLabel(d.approved_version || d.version)}</Row>
            <Row label="Lini">{d.line_code || "semua lini"}</Row>
            <Row label="Spesifikasi cetak">Repeat {d.repeat_cm ? `${d.repeat_cm} cm` : "—"} · {d.screen_count || 0} screen</Row>
            <div className="pt-1.5">
              <p className="text-[11px] text-[#6B6B73]">Tag</p>
              <div className="mt-0.5 flex flex-wrap gap-1" data-testid="gallery-showcase-tags">
                {(d.tags || []).map((t) => <span key={t} className="rounded bg-[#F1E9F7] px-1.5 py-0.5 text-[10.5px] text-[#6B219A]">{t}</span>)}
                {!(d.tags || []).length && <span className="text-[11px] text-[#9A9BA3]">—</span>}
              </div>
            </div>
            {d.story && <p className="mt-2 whitespace-pre-wrap border-t border-[#F2F2F5] pt-2 text-[11.5px] text-[#3C3C43]" data-testid="gallery-showcase-story">{d.story}</p>}
          </div>

          <div className="section-card !p-3">
            <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Produk yang memakai desain ini</p>
            <div data-testid="gallery-showcase-products">
              {(d.recommended_products || []).length === 0
                ? <Empty>belum ada produk ditetapkan</Empty>
                : (
                  <ul className="grid gap-1">
                    {d.recommended_products.map((pr) => (
                      <li key={pr.id} className="flex items-center justify-between gap-2 rounded-lg border border-[#EFF0F2] px-2.5 py-1.5 text-[11.5px]">
                        <span className="min-w-0 truncate"><b className="font-mono">{pr.sku}</b> {pr.name}</span>
                      </li>
                    ))}
                  </ul>
                )}
            </div>
            {p.master_product && (
              <div className="mt-2 rounded-lg border border-[#BFD7FF] bg-[#F2F7FF] px-2.5 py-2 text-[11.5px]" data-testid="gallery-showcase-master">
                <p className="flex items-center gap-1 text-[10px] font-bold uppercase text-[#0058CC]"><PackageCheck size={11} /> Master produk R&amp;D</p>
                <p><b className="font-mono">{p.master_product.sku}</b>{p.master_product.name ? ` — ${p.master_product.name}` : ""}</p>
                <p className="text-[10.5px] text-[#3C3C43]">lifecycle <b>{p.master_product.lifecycle || "—"}</b>{p.master_product.spec_number ? ` · dari ${p.master_product.spec_number}` : ""}</p>
              </div>
            )}
          </div>

          <div className="section-card !p-3">
            <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Status R&amp;D (proofing)</p>
            <span className="inline-block rounded px-2 py-1 text-[11.5px] font-bold" style={{ background: pm.bg, color: pm.fg }} data-testid="gallery-showcase-rnd">{pm.label}</span>
            {p.detail && <p className="mt-1 text-[11px] text-[#6B6B73]">{p.detail}</p>}
            {(p.samples || []).length > 0 && (
              <ul className="mt-2 grid gap-1">
                {p.samples.map((s) => (
                  <li key={s.id}>
                    <button type="button" data-testid={`gallery-showcase-sample-${s.id}`}
                      onClick={() => { openRnd({ view: "rnd-samples", sampleId: s.id }); onClose?.(); }}
                      className="flex w-full flex-wrap items-center justify-between gap-1 rounded-lg border border-[#EFF0F2] px-2.5 py-1.5 text-left text-[11px] hover:border-[#6B219A]">
                      <span className="min-w-0 truncate"><b className="font-mono">{s.number}</b> · {s.title}</span>
                      <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ${s.finished ? "bg-[#EAF7EF] text-[#1A7A3A]" : "bg-[#F1E9F7] text-[#6B219A]"}`}>
                        {s.finished ? <CheckCircle2 size={10} /> : <Clock size={10} />} {s.finished ? "Selesai" : "On progress"} · {s.status_label}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children, testId }) {
  return (
    <div data-testid={testId}>
      <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{title}</p>
      {children}
    </div>
  );
}
function Empty({ children }) { return <p className="rounded-lg border border-dashed border-[#D9D9DE] px-3 py-3 text-center text-[11px] text-[#9A9BA3]">{children}</p>; }
function Row({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[#F2F2F5] py-1.5 text-[11.5px] last:border-0">
      <span className="text-[#6B6B73]">{label}</span><span className="text-right font-semibold text-[#1C1C1E]">{children}</span>
    </div>
  );
}
function Thumbs({ d, files, hero, setHero, label }) {
  return (
    <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
      {files.map((f) => (
        <button key={f.id} type="button" onClick={() => setHero(f)} title={f.filename} data-testid={`gallery-thumb-${f.id}`}
          className={`relative aspect-square overflow-hidden rounded-lg border bg-[#F5F5F7] ${hero?.id === f.id ? "border-[#6B219A] ring-2 ring-[#6B219A]/30" : "border-[#E5E5EA]"}`}>
          {f.content_type?.startsWith("image/")
            ? <DesignImage src={designFileUrl(d.id, f.id)} alt={f.filename} className="h-full w-full object-cover" loading="lazy" />
            : <span className="flex h-full items-center justify-center text-[10px] font-bold">PDF</span>}
          <span className="absolute left-1 top-1 rounded bg-white/90 px-1 py-0.5 text-[8.5px] font-bold text-[#6B219A]">{label(f)}</span>
        </button>
      ))}
    </div>
  );
}
