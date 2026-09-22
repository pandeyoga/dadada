/** ProofingPanel — rincian proofing R&D untuk satu desain: status tiap permintaan sample, hasil, dan master produk yang lahir. */
import { CheckCircle2, Clock, FlaskConical, PackageCheck, Trophy } from "lucide-react";
import { PROOFING_STATE_META } from "../rndMeta";
import { openRnd } from "../rndDeepLink";

const openRndSample = (id) => openRnd({ view: "rnd-samples", sampleId: id });

const fmtD = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—");

export default function ProofingPanel({ design }) {
  const p = design.proofing || { state: "none", samples: [], specs: [] };
  const m = PROOFING_STATE_META[p.state] || PROOFING_STATE_META.none;
  return (
    <div className="space-y-3" data-testid="design-proofing-panel">
      <div className="rounded-lg border px-3 py-2" style={{ background: m.bg, borderColor: m.fg + "55" }} data-testid="design-proofing-state">
        <p className="flex items-center gap-1.5 text-[12.5px] font-bold" style={{ color: m.fg }}>
          {p.state === "master" ? <PackageCheck size={14} /> : <FlaskConical size={14} />} {m.label}
        </p>
        <p className="text-[11px] text-[#3C3C43]" data-testid="design-proofing-detail">{p.detail}</p>
        {design.on_hold && (
          <p className="mt-1 text-[10.5px] font-semibold text-[#B24A00]" data-testid="design-proofing-hold-note">
            Desain sedang DITAHAN — permintaan proofing baru ditolak sampai penahanan dilepas.
          </p>
        )}
      </div>

      {p.master_product && (
        <div className="rounded-lg border border-[#BFD7FF] bg-[#F2F7FF] p-3" data-testid="design-master-product">
          <p className="text-[10.5px] font-bold uppercase text-[#0058CC]">Master produk</p>
          <p className="text-[13px] font-bold text-[#1C1C1E]">
            <span className="font-mono">{p.master_product.sku}</span>{p.master_product.name ? ` — ${p.master_product.name}` : ""}
          </p>
          <p className="text-[10.5px] text-[#3C3C43]">
            {p.master_product.spec_number ? <>dari spesifikasi <b>{p.master_product.spec_number}</b> · </> : null}
            lifecycle <b>{p.master_product.lifecycle === "produksi" ? "Produksi (boleh dijual)" : p.master_product.lifecycle === "disetujui" ? "Disetujui (belum rilis)" : p.master_product.lifecycle || "—"}</b>
            {p.master_product.since ? <> · sejak {fmtD(p.master_product.since)}</> : null}
          </p>
        </div>
      )}

      <div>
        <p className="mb-1 text-[10.5px] font-bold uppercase text-[#8E8E93]">Permintaan proofing R&D · {(p.samples || []).length}</p>
        {(p.samples || []).length === 0 ? (
          <p className="text-[11.5px] text-[#9A9BA3]" data-testid="design-proofing-empty">Belum ada permintaan proofing yang merujuk desain ini.</p>
        ) : (
          <div className="space-y-1.5">
            {p.samples.map((s) => (
              <button key={s.id} type="button" onClick={() => openRndSample?.(s.id)} data-testid={`design-proofing-sample-${s.id}`}
                className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg border border-[#EFF0F2] bg-white px-3 py-2 text-left hover:border-[#6B219A]">
                <span className="min-w-0">
                  <span className="font-mono text-[11.5px] font-bold">{s.number}</span>
                  <span className="ml-1 truncate text-[11px] text-[#3C3C43]">{s.title}</span>
                  <p className="text-[10px] text-[#8E8E93]">{s.rounds} round · {s.acc_rounds} ACC{s.winner ? ` · pemenang ${s.winner}` : ""}</p>
                </span>
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ${s.finished ? "bg-[#EAF7EF] text-[#1A7A3A]" : "bg-[#F1E9F7] text-[#6B219A]"}`}
                  data-testid={`design-proofing-sample-status-${s.id}`}>
                  {s.finished ? <CheckCircle2 size={11} /> : <Clock size={11} />}
                  {s.finished ? `Finished · ${s.status_label}${s.finished_at ? ` · jadi ${fmtD(s.finished_at)}` : ""}` : `On progress · ${s.status_label}`}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {(p.specs || []).length > 0 && (
        <div>
          <p className="mb-1 text-[10.5px] font-bold uppercase text-[#8E8E93]">Spesifikasi terkait · {p.specs.length}</p>
          <div className="space-y-1">
            {p.specs.map((sp) => (
              <div key={sp.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#EFF0F2] px-3 py-1.5 text-[11px]" data-testid={`design-proofing-spec-${sp.id}`}>
                <span><b className="font-mono">{sp.number}</b> · {sp.title}</span>
                <span className="text-[#6B6B73]">
                  {sp.product_sku ? <><Trophy size={10} className="mr-1 inline" />produk <b>{sp.product_sku}</b></> : `status ${sp.status}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
