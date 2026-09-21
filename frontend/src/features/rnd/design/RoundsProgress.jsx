/** RoundsProgress — kotak progres per ronde Design Studio: Pengajuan awal → Revisi 1 → … → ACC → Final. */
import { FileImage } from "lucide-react";
import { RevisionBadge, ROUND_RESULT_STYLE, RoundBoxes } from "../../../components/RevisionProgress";
import { fmtScore } from "../rndMeta";

export function RoundBadge({ design, testId }) {
  const n = design.revision_count ?? Math.max(0, (design.version || 1) - 1);
  return <RevisionBadge count={n} testId={testId} title={`Ronde berjalan: ${design.round_label || (n ? `Revisi ${n}` : "Pengajuan awal")}`} />;
}

export default function RoundsProgress({ design }) {
  const fin = design.final || {};
  const finalState = ["final_submitted", "active"].includes(design.status) ? "acc"
    : design.status === "approved" ? (fin.complete ? "review" : "draft") : null;
  const items = (design.rounds || []).map((r) => ({
    key: r.version, title: r.label, result: r.result,
    sub: `${r.file_count} berkas${r.score !== null && r.score !== undefined ? ` · nilai ${fmtScore(r.score)}` : ""}`,
  }));
  const trailing = finalState && (
    <div className={`min-w-[150px] rounded-lg border px-2.5 py-1.5 ${ROUND_RESULT_STYLE[finalState].cls}`} data-testid="design-round-final">
      <p className="flex items-center gap-1 text-[10.5px] font-bold"><FileImage size={11} /> Final</p>
      <p className="text-[9.5px] opacity-90">
        {fin.mockup_files}/1 mockup · {fin.source_files ?? 0}/1 file asli
        {design.status === "active" ? " · Aktif" : design.status === "final_submitted" ? " · diserahkan" : fin.complete ? " · siap serah" : ""}
      </p>
    </div>
  );
  return <RoundBoxes items={items} testPrefix="design-round" trailing={trailing} testId="design-rounds-progress" />;
}
