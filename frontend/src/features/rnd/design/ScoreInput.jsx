/** ScoreInput — nilai 0–2 kelipatan 0,25 (9 pilihan), tampilan segmen. */
import { SCORE_STEPS, fmtScore } from "../rndMeta";

export default function ScoreInput({ value, onChange, disabled = false, testId = "score-input", minAcc }) {
  return (
    <div data-testid={testId} className="space-y-1">
      <div className="flex flex-wrap gap-1">
        {SCORE_STEPS.map((s) => {
          const active = Number(value) === s;
          const pass = minAcc !== undefined && s >= Number(minAcc);
          return (
            <button key={s} type="button" disabled={disabled} onClick={() => onChange(s)}
              data-testid={`${testId}-${String(s).replace(".", "_")}`}
              className={`min-w-[40px] rounded-md border px-2 py-1 text-[11.5px] font-semibold tabular-nums transition-colors ${active
                ? (pass ? "border-[#1A7A3A] bg-[#1A7A3A] text-white" : "border-[#B26A00] bg-[#B26A00] text-white")
                : `border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#6B219A] ${pass ? "" : "opacity-80"}`}`}>
              {fmtScore(s)}
            </button>
          );
        })}
      </div>
      {minAcc !== undefined && (
        <p className="text-[10px] text-[#8E8E93]">Ambang ACC: <b>{fmtScore(minAcc)}</b> · skala 0 – 2, kelipatan 0,25</p>
      )}
    </div>
  );
}

export function ScoreBadge({ value, acc = false, size = "sm", testId }) {
  if (value === null || value === undefined) {
    return <span data-testid={testId} className="rounded bg-[#F5F5F7] px-1.5 py-0.5 text-[10px] text-[#9A9BA3]">belum dinilai</span>;
  }
  const v = Number(value);
  const tone = acc ? "#1A7A3A" : v >= 1.5 ? "#1A7A3A" : v >= 1 ? "#B26A00" : "#C62828";
  return (
    <span data-testid={testId} style={{ color: tone, borderColor: tone }}
      className={`inline-flex items-center gap-1 rounded border bg-white px-1.5 py-0.5 font-bold tabular-nums ${size === "lg" ? "text-[15px]" : "text-[11px]"}`}>
      {fmtScore(v)}<span className="font-normal opacity-70">/2</span>{acc && <span className="text-[9px] uppercase">ACC</span>}
    </span>
  );
}
