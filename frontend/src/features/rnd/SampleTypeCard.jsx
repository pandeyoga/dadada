/**
 * SampleTypeCard — kartu galeri sampel per jenis (cermin `DesignCard` Desain & Pattern):
 * sampul = foto bukti terbaru untuk jenis itu, nomor mono, judul, supplier, status, skor.
 */
import { Droplets } from "lucide-react";
import { RevisionBadge, sampleRevisionCount } from "../../components/RevisionProgress";
import { formatDateId } from "../../components/KNDatePicker";
import ProofImage from "./ProofImage";
import { roundProofUrl } from "./rndApi";
import { ROUND_RESULT_META, SAMPLE_STATUS_META, typeTone } from "./rndMeta";
import { roundTypeOf } from "./sampleTypeMeta";

export function typeRoundsOf(sample, code) {
  return (sample.rounds || []).filter((r) => roundTypeOf(r, sample) === code);
}

export default function SampleTypeCard({ s, code, onOpen }) {
  const meta = SAMPLE_STATUS_META[s.status] || SAMPLE_STATUS_META.draft;
  const tone = typeTone(code);
  const rounds = typeRoundsOf(s, code);
  const withProof = [...rounds].reverse().find((r) => (r.attachments || []).length > 0);
  const cover = withProof ? withProof.attachments[withProof.attachments.length - 1] : null;
  const proofs = rounds.reduce((a, r) => a + (r.attachments || []).length, 0);
  const best = rounds.reduce((a, r) => (r.score != null ? Math.max(a ?? 0, Number(r.score)) : a), null);
  const acc = rounds.some((r) => r.result === "acc");
  const last = rounds[rounds.length - 1];
  const lastMeta = last ? (ROUND_RESULT_META[last.result || ""] || ROUND_RESULT_META[""]) : null;
  const suppliers = (s.participants || []).map((p) => p.supplier_name).filter(Boolean);
  const winner = s.decision?.supplier_name;
  const overdue = rounds.some((r) => r.overdue);
  const hex = s.color_target?.hex;

  return (
    <button type="button" onClick={onOpen} data-testid={`sample-type-card-${s.id}`}
      className="overflow-hidden rounded-lg border border-[#E5E5EA] bg-white text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2"
      style={{ "--tw-ring-color": `${tone.fg}55` }}>
      <div className="relative flex h-28 items-center justify-center bg-[#F5F5F7]">
        {cover ? (
          <ProofImage url={roundProofUrl(s.id, withProof.id, cover.id)} attachment={cover} alt={s.title} className="h-full w-full" testId={`sample-type-cover-${s.id}`} />
        ) : hex ? (
          <span className="h-full w-full" style={{ background: hex }} data-testid={`sample-type-swatch-${s.id}`} />
        ) : (
          <span className="text-[10.5px] text-[#9A9BA3]">belum ada bukti</span>
        )}
        <span className="absolute left-1.5 top-1.5">
          <RevisionBadge count={sampleRevisionCount(s)} testId={`sample-type-rev-${s.id}`} />
        </span>
        {overdue && <span className="absolute right-1.5 top-1.5 rounded bg-[#C4361D] px-1.5 py-0.5 text-[9px] font-bold text-white">terlambat</span>}
        {winner && !overdue && (
          <span className="absolute right-1.5 top-1.5 rounded bg-white/90 px-1.5 py-0.5 text-[9px] font-bold" style={{ color: tone.fg }}>pemenang · {winner}</span>
        )}
      </div>
      <div className="space-y-1 p-2">
        <div className="flex items-center justify-between gap-1">
          <span className="truncate font-mono text-[11.5px] font-bold" data-testid={`sample-type-number-${s.id}`}>{s.number}</span>
          <span className={`shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-bold tabular-nums ${acc ? "border-[#1A7A3A] text-[#1A7A3A]" : "border-[#E5E5EA] text-[#6B6B73]"}`}
            data-testid={`sample-type-score-${s.id}`}>
            {best == null ? "belum dinilai" : <>{best}{acc ? " · ACC" : ""}</>}
          </span>
        </div>
        <p className="truncate text-[11px] text-[#1C1C1E]">{s.title}</p>
        <p className="truncate text-[9.5px] font-semibold text-[#0058CC]" data-testid={`sample-type-spec-${s.id}`}>
          {s.spec_summary
            ? [s.spec_summary.template_name && `Induk ${s.spec_summary.template_name}`, s.spec_summary.fabric_type, s.spec_summary.gramasi && `${s.spec_summary.gramasi} gsm`,
              s.spec_summary.lebar && `lebar ${s.spec_summary.lebar} cm`, s.spec_summary.product_sku && `SKU ${s.spec_summary.product_sku}`].filter(Boolean).join(" · ") || s.spec_summary.number
            : <span className="text-[#B26A00]">⚠ belum ada spesifikasi</span>}
        </p>
        <p className="flex items-center gap-1 truncate text-[9.5px] text-[#9A9BA3]">
          {hex && <span className="inline-block h-2.5 w-2.5 rounded-sm border border-black/10" style={{ background: hex }} />}
          {s.color_target?.name && <span className="truncate">{s.color_target.name} · </span>}
          {s.design_code && <span className="truncate">{s.design_code} · </span>}
          <span className="truncate">{suppliers.length ? suppliers.join(", ") : "belum ada supplier"}</span>
        </p>
        <div className="flex items-center justify-between">
          <span className={`status-pill ${meta.cls}`} data-testid={`sample-type-status-${s.id}`}>{meta.label}</span>
          <span className="text-[9.5px] text-[#8E8E93]">{rounds.length} round · {proofs} bukti</span>
        </div>
        <p className="flex items-center justify-between text-[9.5px] text-[#8E8E93]">
          <span>{lastMeta ? <span style={{ color: lastMeta.tone }} className="font-semibold">{lastMeta.label}</span> : "belum ada round"}</span>
          {s.target_date && <span className="inline-flex items-center gap-1"><Droplets size={9} /> {formatDateId(s.target_date, "dd MMM")}</span>}
        </p>
      </div>
    </button>
  );
}
