/** RoundsTimeline — Ringkasan vertikal per ronde: judul ronde → berkas yang dikirim → komentar revisi / ACC + nilai di akhir. */
import DesignImage from "./DesignImage";
import { CheckCircle2, Clock, Download, MessageSquareText, RotateCcw, Upload } from "lucide-react";
import { designFileUrl, uploadDesignKindFile, deleteDesignFile } from "../rndApi";
import { errMsg, fmtScore, roundLabel } from "../rndMeta";
import { ScoreBadge } from "./ScoreInput";
import { Trash2 } from "lucide-react";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "—");

export default function RoundsTimeline({ design, canEdit, onDone, onError }) {
  const versions = [...(design.versions || [])].sort((a, b) => a.version - b.version);
  const filesOf = (v) => (design.files || []).filter((f) => (f.kind || "artwork") === "artwork" && (f.version || 1) === v);
  const cur = design.version;
  const inReview = ["pending_approval", "in_review"].includes(design.status);

  const uploadAll = async (list) => {
    let ok = 0;
    for (const file of list) {
      try { await uploadDesignKindFile(design.id, "artwork", file); ok += 1; }
      catch (e) { onError?.(errMsg(e, `Unggah "${file.name}" gagal.`)); }
    }
    if (ok) onDone?.(`${ok} berkas desain terunggah pada ${roundLabel(cur)}.`);
  };

  return (
    <ol className="relative space-y-4 border-l-2 border-[#EFF0F2] pl-5" data-testid="design-rounds-timeline">
      {versions.map((v) => {
        const files = filesOf(v.version);
        const isCur = v.version === cur;
        const revNote = versions.find((x) => x.version === v.version + 1)?.revision_note || "";
        const state = v.acc ? "acc" : revNote ? "revision" : isCur && inReview ? "review" : "open";
        const dot = { acc: "bg-[#1A7A3A]", revision: "bg-[#C62828]", review: "bg-[#0058CC]", open: "bg-[#8E8E93]" }[state];
        return (
          <li key={v.version} className="relative" data-testid={`design-round-block-${v.version}`}>
            <span className={`absolute -left-[27px] top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${dot}`} />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-[13px] font-bold text-[#1C1C1E]">
                {roundLabel(v.version)}
                <span className="ml-2 font-mono text-[10px] font-normal text-[#8E8E93]">v{v.version}</span>
                {isCur && !v.acc && <span className="ml-2 rounded bg-[#6B219A] px-1.5 py-0.5 text-[9px] font-semibold text-white">ronde berjalan</span>}
              </h3>
              <span className="text-[10.5px] text-[#8E8E93]">{v.by ? `${v.by} · ` : ""}{fmtAt(v.at)}</span>
            </div>
            {v.note && v.version > 1 && <p className="mt-0.5 text-[11px] text-[#6B6B73]">Catatan ronde: {v.note}</p>}

            <div className="mt-2 rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
              <div className="mb-1.5 flex items-center justify-between">
                <p className="text-[10.5px] font-bold uppercase text-[#8E8E93]">Berkas dikirim · {files.length}</p>
                {isCur && canEdit && (
                  <label className="secondary-button cursor-pointer !py-1 text-[11px]" data-testid="design-upload-artwork-label">
                    <Upload size={12} /> Unggah berkas desain
                    <input type="file" className="hidden" accept="image/*,.pdf" multiple data-testid="design-upload-artwork"
                      onChange={(e) => { uploadAll(Array.from(e.target.files || [])); e.target.value = ""; }} />
                  </label>
                )}
              </div>
              {files.length === 0 ? (
                <p className="py-3 text-center text-[11px] text-[#9A9BA3]">belum ada berkas untuk ronde ini</p>
              ) : (
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
                  {files.map((f) => (
                    <div key={f.id} className="group relative overflow-hidden rounded-lg border border-[#E5E5EA] bg-white" data-testid={`design-file-${f.id}`}>
                      <a href={designFileUrl(design.id, f.id)} target="_blank" rel="noreferrer" className="block aspect-square bg-[#F5F5F7]">
                        {f.content_type?.startsWith("image/")
                          ? <DesignImage src={designFileUrl(design.id, f.id)} alt={f.filename} className="h-full w-full object-cover" loading="lazy" />
                          : <span className="flex h-full items-center justify-center text-[10px] font-bold text-[#6B6B73]">PDF</span>}
                      </a>
                      <div className="px-1.5 py-1 text-[9.5px] leading-tight">
                        <p className="truncate font-semibold" title={f.filename}>{f.filename}</p>
                        <p className="text-[#8E8E93]">{f.uploaded_by || ""}</p>
                      </div>
                      {isCur && canEdit && (
                        <button className="absolute right-1 top-1 hidden rounded bg-white/90 p-1 text-red-500 shadow group-hover:block" title="Hapus berkas"
                          data-testid={`design-file-delete-${f.id}`}
                          onClick={() => deleteDesignFile(design.id, f.id).then(() => onDone?.("Berkas dihapus.")).catch((e) => onError?.(errMsg(e)))}>
                          <Trash2 size={11} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {revNote && (
              <div className="mt-2 flex gap-2 rounded-lg border border-[#F5C6C6] bg-[#FDF3F2] px-3 py-2" data-testid={`design-round-comment-${v.version}`}>
                <RotateCcw size={14} className="mt-0.5 shrink-0 text-[#C62828]" />
                <div className="text-[11.5px] text-[#8E1B1B]">
                  <p className="font-bold">Komentar revisi penilai</p>
                  <p className="whitespace-pre-wrap">{revNote}</p>
                  <p className="mt-0.5 text-[10px] opacity-70">{design.rejected_by || "penilai"} · {fmtAt(versions.find((x) => x.version === v.version + 1)?.at)} → dibuka {roundLabel(v.version + 1)}</p>
                </div>
              </div>
            )}
            {v.acc && (
              <div className="mt-2 flex flex-wrap items-start justify-between gap-2 rounded-lg border border-[#CDE9D6] bg-[#F4FCF6] px-3 py-2" data-testid={`design-round-acc-${v.version}`}>
                <div className="flex gap-2 text-[11.5px] text-[#1A5C2E]">
                  <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[#1A7A3A]" />
                  <div>
                    <p className="font-bold">ACC — nilai akhir {fmtScore(v.score)}/2</p>
                    {v.score_note && <p className="whitespace-pre-wrap">{v.score_note}</p>}
                    <p className="mt-0.5 text-[10px] opacity-70">{v.score_by || "penilai"} · {fmtAt(v.score_at)}</p>
                  </div>
                </div>
                <ScoreBadge value={v.score} acc size="lg" testId={`design-version-score-${v.version}`} />
              </div>
            )}
            {!v.acc && !revNote && isCur && (
              <p className="mt-2 flex items-center gap-1.5 text-[11px] text-[#6B6B73]" data-testid="design-round-waiting">
                {inReview ? <><Clock size={12} /> Menunggu keputusan penilai (ACC / revisi).</>
                  : <><MessageSquareText size={12} /> Unggah berkas ronde ini lalu <b>Ajukan untuk review</b>.</>}
              </p>
            )}
          </li>
        );
      })}
      {["approved", "final_submitted", "active"].includes(design.status) && (
        <li className="relative" data-testid="design-round-block-final">
          <span className={`absolute -left-[27px] top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${design.final?.complete ? "bg-[#0058CC]" : "bg-[#B26A00]"}`} />
          <h3 className="text-[13px] font-bold text-[#1C1C1E]">Berkas final</h3>
          <p className="text-[11px] text-[#6B6B73]">
            <Download size={11} className="mr-1 inline" />
            Mockup {design.final?.mockup_files ?? 0}/1 · File desain asli {design.final?.source_files ?? 0}/1
            {design.status === "active" ? " · Aktif untuk produksi" : design.status === "final_submitted" ? " · diserahkan, menunggu aktivasi" : design.final?.complete ? " · lengkap, siap diserahkan" : " · lengkapi di tab Final"}
          </p>
        </li>
      )}
    </ol>
  );
}
