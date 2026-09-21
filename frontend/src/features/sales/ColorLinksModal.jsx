/** ColorLinksModal — detail keterkaitan satu warna: Warna internal ↔ Versi supplier (dilabeli supplier) ↔ Master produk ↔ Sample R&D. */
import { useEffect, useState } from "react";
import { ArrowRight, ExternalLink, Factory, FlaskConical, Package, Palette } from "lucide-react";
import DetailModal from "../../components/DetailModal";
import ErrorNotice from "../../components/ErrorNotice";
import axios, { API } from "../../services/apiClient";
import { openRnd } from "../rnd/rndDeepLink";
import { lifecycleMeta, SAMPLE_STATUS_META } from "../rnd/rndMeta";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—");

export default function ColorLinksModal({ colorId, focusSupplierId = "", onClose }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    axios.get(`${API}/color-library/${colorId}/links`).then((r) => setD(r.data))
      .catch((e) => setErr(e.response?.data?.detail || "Gagal memuat keterkaitan warna."));
  }, [colorId]);
  const c = d?.color;
  const goSample = (id, number) => { openRnd({ view: "rnd-samples", sampleId: id, sampleNumber: number }); onClose?.(); };

  return (
    <DetailModal open onClose={onClose} size="xl" label="Keterkaitan warna" testId="color-links-modal" framed>
      {err && <ErrorNotice message={err} testId="color-links-error" />}
      {!d ? <div className="h-40 animate-pulse rounded-lg bg-[#F5F5F7]" /> : (
        <div className="grid gap-4" data-testid="color-links-panel">
          <div className="flex items-start gap-3">
            <span className="h-14 w-14 shrink-0 rounded-lg border border-[#E5E5EA]" style={{ background: c.hex }} />
            <div className="min-w-0">
              <p className="kicker">Pustaka Warna · keterkaitan</p>
              <h2 className="text-[15px] font-bold text-[#1C1C1E]" data-testid="color-links-title">{c.code} · {c.name}</h2>
              <p className="text-[11px] text-[#6B6B73]">{c.system} · {c.family || "—"} · <span className="font-mono">{c.hex}</span>{c.factory_name ? ` · nama pabrik utama: ${c.factory_name}` : ""}</p>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-[1fr_auto_1.2fr_auto_1.2fr] lg:items-start">
            <Column icon={Palette} title="Warna internal" tone="#0058CC" testId="color-links-internal">
              <div className="rounded-lg border border-[#EFF0F2] p-2.5 text-[11.5px]">
                <p className="font-bold">{c.code}</p>
                <p className="text-[#6B6B73]">{c.name}</p>
                <p className="mt-1 text-[10.5px] text-[#6B6B73]">{d.supplier_variants.length} versi supplier · {d.products.length} produk · {d.samples.length} sample</p>
              </div>
            </Column>
            <Arrow />
            <Column icon={Factory} title={`Versi supplier · ${d.supplier_variants.length}`} tone="#6B219A" testId="color-links-suppliers">
              {d.supplier_variants.length === 0 && <Empty>belum ada — terisi saat labdip warna ini ACC</Empty>}
              {d.supplier_variants.map((v) => (
                <div key={v.supplier_id} data-testid={`color-links-supplier-${v.supplier_id}`}
                  className={`rounded-lg border p-2.5 text-[11.5px] ${v.supplier_id === focusSupplierId ? "border-[#6B219A] bg-[#FAF5FF]" : "border-[#EFF0F2]"}`}>
                  <p className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[#6B219A]"><Factory size={10} /> {v.supplier_name}</p>
                  <p className="mt-0.5 font-bold">{v.supplier_color_name || "—"} <span className="font-mono text-[10.5px] font-normal text-[#6B6B73]">{v.supplier_color_code || ""}</span></p>
                  <button type="button" className="mt-1 inline-flex items-center gap-1 text-[10.5px] text-[#0058CC] hover:underline" data-testid={`color-links-sample-${v.supplier_id}`}
                    onClick={() => goSample(v.sample_id, v.sample_number)}>
                    <FlaskConical size={10} /> asal {v.sample_number} · ACC {fmtAt(v.at)} <ExternalLink size={9} />
                  </button>
                  {v.products.length > 0 && <p className="mt-1 text-[10.5px] text-[#1A7A3A]">→ produk {v.products.map((p) => p.sku).join(", ")}</p>}
                </div>
              ))}
            </Column>
            <Arrow />
            <Column icon={Package} title={`Master produk · ${d.products.length}`} tone="#1A7A3A" testId="color-links-products">
              {d.products.length === 0 && <Empty>belum ada produk — lahir saat spesifikasi ber-warna ini di-ACC</Empty>}
              {d.products.map((p) => {
                const lm = lifecycleMeta(p.lifecycle);
                const via = d.supplier_variants.find((v) => v.products.some((x) => x.id === p.id));
                return (
                  <div key={p.id} className="rounded-lg border border-[#EFF0F2] p-2.5 text-[11.5px]" data-testid={`color-links-product-${p.id}`}>
                    <p className="font-mono font-bold">{p.sku}</p>
                    <p className="text-[#3C3C43]">{p.name}</p>
                    <p className="mt-0.5 text-[10.5px] text-[#6B6B73]">
                      {p.template_name ? `varian induk ${p.template_name} · ` : ""}dari {p.spec_number} · lifecycle <b style={{ color: lm.tone }}>{lm.label}</b>
                    </p>
                    {via && <p className="mt-0.5 text-[10.5px] text-[#6B219A]">warna supplier: {via.supplier_name} — {via.supplier_color_name}</p>}
                  </div>
                );
              })}
            </Column>
          </div>

          <div data-testid="color-links-samples">
            <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Sample R&amp;D memakai warna ini · {d.samples.length}</p>
            {d.samples.length === 0 ? <Empty>belum ada permintaan sample</Empty> : (
              <ul className="divide-y divide-[#F4F5F7] rounded-lg border border-[#EFF0F2]">
                {d.samples.map((s) => {
                  const sm = SAMPLE_STATUS_META[s.status] || { label: s.status, cls: "pill-muted" };
                  return (
                    <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 text-[11.5px]" data-testid={`color-links-sample-row-${s.id}`}>
                      <button type="button" className="inline-flex min-w-0 items-center gap-1 text-left hover:underline" onClick={() => goSample(s.id, s.number)}>
                        <b className="font-mono">{s.number}</b> <span className="truncate text-[#3C3C43]">· {s.title}</span> <ExternalLink size={9} className="text-[#0058CC]" />
                      </button>
                      <span className="flex items-center gap-2 text-[10.5px] text-[#6B6B73]">
                        {s.decision?.supplier_name && <span>pemenang <b>{s.decision.supplier_name}</b>{s.decision.product_sku ? ` → ${s.decision.product_sku}` : ""}</span>}
                        <span className={`status-pill ${sm.cls}`}>{sm.label}</span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </DetailModal>
  );
}

function Column({ icon: Icon, title, tone, children, testId }) {
  return (
    <div className="grid content-start gap-1.5" data-testid={testId}>
      <p className="flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wide" style={{ color: tone }}><Icon size={12} /> {title}</p>
      {children}
    </div>
  );
}
function Arrow() { return <ArrowRight size={16} className="hidden self-center text-[#C7C9CF] lg:block" />; }
function Empty({ children }) { return <p className="rounded-lg border border-dashed border-[#D9D9DE] px-3 py-3 text-center text-[11px] text-[#9A9BA3]">{children}</p>; }
