/**
 * SampleBoardCard — kartu papan **Permintaan Sample** (cermin `BoardCard` Permintaan Desain).
 * Nomor · jenis (labdip/handfeel/proofing) · judul · warna target · supplier · round · target.
 */
import { CalendarClock } from "lucide-react";
import { RevisionBadge, sampleRevisionCount } from "../../components/RevisionProgress";
import { formatDateId } from "../../components/KNDatePicker";
import { typeTone } from "./rndMeta";
import { sampleTypesOf, typeLabel } from "./sampleTypeMeta";

export function TypeBadge({ code, types, size = "xs", testId }) {
  const tone = typeTone(code);
  const cls = size === "xs" ? "px-1.5 py-0.5 text-[9.5px]" : "px-2 py-0.5 text-[10.5px]";
  return (
    <span data-testid={testId} className={`rounded font-semibold ${cls}`}
      style={{ background: tone.bg, color: tone.fg }}>
      {typeLabel(code, types).split(" (")[0]}
    </span>
  );
}

export default function SampleBoardCard({ s, types, onOpen }) {
  const codes = sampleTypesOf(s);
  const overdue = (s.rounds || []).some((r) => r.overdue);
  const suppliers = (s.participants || []).map((p) => p.supplier_name).filter(Boolean);
  const accCount = (s.rounds || []).filter((r) => r.result === "acc").length;
  return (
    <button type="button" data-testid={`rnd-sample-card-${s.id}`} onClick={onOpen}
      className="w-full rounded-lg border border-[#EFF0F2] bg-white p-2 text-left shadow-sm transition-[border-color,box-shadow] hover:border-[#9DBDF0] hover:shadow-md">
      <p className="flex flex-wrap items-center gap-1.5 text-[11.5px] font-bold text-[#1C1C1E]">
        {s.number}
        <RevisionBadge count={sampleRevisionCount(s)} size="xs" testId={`rnd-sample-card-revision-${s.id}`} />
        {overdue && <span className="status-pill pill-danger !text-[9px]">round terlambat</span>}
      </p>
      <p className="mt-1 flex flex-wrap gap-1" data-testid={`rnd-sample-card-types-${s.id}`}>
        {codes.map((c) => <TypeBadge key={c} code={c} types={types} />)}
        {codes.length === 0 && <span className="text-[9.5px] text-[#8E8E93]">tanpa jenis</span>}
      </p>
      <p className="mt-1 line-clamp-2 text-[10.5px] leading-snug text-[#3C3C43]">{s.title}</p>
      {(s.color_target?.name || s.design_code || s.so_number) && (
        <p className="mt-0.5 flex flex-wrap items-center gap-1 truncate text-[10px] text-[#8E8E93]">
          {s.color_target?.name && (
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full border border-[#E5E5EA]" style={{ background: s.color_target.hex || "#fff" }} />
              {s.color_target.name}
            </span>
          )}
          {s.design_code && <span>· {s.design_code}</span>}
          {s.so_number && <span>· {s.so_number}</span>}
        </p>
      )}
      <p className="mt-1.5 flex items-center gap-1.5 rounded-md bg-[#FAFBFC] px-1.5 py-1 text-[10px]" data-testid={`rnd-sample-card-progress-${s.id}`}>
        <span className="truncate font-semibold text-[#1C1C1E]">{suppliers.length ? suppliers.join(", ") : "belum ke supplier"}</span>
        <span className="ml-auto shrink-0 tabular-nums text-[#6B6B73]">{(s.rounds || []).length} rnd{accCount ? ` · ${accCount} ACC` : ""}</span>
      </p>
      <p className="mt-1.5 flex items-center justify-between gap-1 text-[10px] text-[#8E8E93]">
        <span className="flex items-center gap-1 truncate">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#E5E5EA] text-[8.5px] font-bold text-[#3C3C43]">
            {(s.created_by || "?").slice(0, 1).toUpperCase()}
          </span>
          <span className="truncate">{s.created_by || "—"}</span>
        </span>
        {s.target_date && (
          <span className={`shrink-0 ${overdue ? "font-semibold text-[#A8221A]" : ""}`}>
            <CalendarClock size={9} className="inline" /> {formatDateId(s.target_date, "dd MMM")}
          </span>
        )}
      </p>
    </button>
  );
}
