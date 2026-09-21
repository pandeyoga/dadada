/** VersionsPanel — setiap ronde: berkas, catatan revisi penilai, dan nilai akhir HANYA pada ronde yang di-ACC. */
import { designFileUrl } from "../rndApi";
import { roundLabel } from "../rndMeta";
import { ScoreBadge } from "./ScoreInput";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "");

export default function VersionsPanel({ design }) {
  const versions = [...(design.versions || [])].sort((a, b) => b.version - a.version);
  const filesOf = (v) => (design.files || []).filter((f) => (f.kind || "artwork") === "artwork" && (f.version || 1) === v);
  return (
    <div className="space-y-2" data-testid="design-versions-panel">
      <p className="rounded-lg bg-[#F2F7FF] px-3 py-2 text-[11px] text-[#004099]" data-testid="design-versions-score-note">
        Nilai desain diberikan <b>sekali, di akhir saat ACC</b> — ronde revisi tidak dinilai.
      </p>
      {versions.map((v) => {
        const files = filesOf(v.version);
        const isCur = v.version === design.version;
        return (
          <div key={v.version} data-testid={`design-version-${v.version}`}
            className={`rounded-lg border p-3 ${isCur ? "border-[#6B219A] bg-[#FBF8FE]" : "border-[#EFF0F2] bg-white"}`}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-[12.5px] font-bold">{roundLabel(v.version)} <span className="font-mono text-[10px] text-[#8E8E93]">v{v.version}</span>
                  {isCur && <span className="ml-1 rounded bg-[#6B219A] px-1.5 py-0.5 text-[9px] text-white">ronde berjalan</span>}
                  {v.acc && <span className="ml-1 rounded bg-[#1A7A3A] px-1.5 py-0.5 text-[9px] text-white">ACC FINAL</span>}</p>
                <p className="text-[10.5px] text-[#6B6B73]">{v.revision_note ? <><b>Catatan revisi:</b> {v.revision_note}</> : (v.note || "—")} · {v.by} · {fmtAt(v.at)}</p>
              </div>
              {v.acc ? (
                <div className="text-right">
                  <ScoreBadge value={v.score} acc size="lg" testId={`design-version-score-${v.version}`} />
                  {v.score_by && <p className="mt-0.5 text-[9.5px] text-[#8E8E93]">oleh {v.score_by} · {fmtAt(v.score_at)}</p>}
                </div>
              ) : <span className="text-[10px] text-[#9A9BA3]" data-testid={`design-version-score-${v.version}`}>tanpa nilai (bukan ronde ACC)</span>}
            </div>
            {v.acc && v.score_note && (
              <p className="mt-2 rounded bg-white/80 px-2 py-1 text-[11px] text-[#3C3C43]" data-testid={`design-version-scorenote-${v.version}`}>
                <b>Catatan penilai:</b> {v.score_note}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {files.map((f) => (
                <a key={f.id} href={designFileUrl(design.id, f.id)} target="_blank" rel="noreferrer" title={f.filename}
                  className="block h-14 w-14 overflow-hidden rounded border border-[#E5E5EA] bg-[#F5F5F7]">
                  {f.content_type?.startsWith("image/")
                    ? <img src={designFileUrl(design.id, f.id)} alt={f.filename} className="h-full w-full object-cover" />
                    : <span className="flex h-full items-center justify-center text-[9px]">PDF</span>}
                </a>
              ))}
              {files.length === 0 && <span className="text-[10.5px] text-[#9A9BA3]">belum ada berkas untuk ronde ini</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
