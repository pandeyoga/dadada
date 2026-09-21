/**
 * SampleRoundList — riwayat round per **supplier × JENIS** bergaya Design Studio:
 * kotak progres ronde + linimasa vertikal: judul ronde → tanggal (dikirim · tenggat · diterima)
 * → bukti (foto) → catatan hasil supplier → keputusan penilai (ACC / revisi / tolak + skor + catatan + tanggal).
 */
import { useEffect } from "react";
import { CheckCircle2, Clock, FileText, Paperclip, Plus, RotateCcw, Send, Upload, XCircle } from "lucide-react";
import { RoundBoxes, revisionLabel, sampleRoundResult } from "../../components/RevisionProgress";
import { formatCurrency } from "../../utils/formatters";
import ProofImage from "./ProofImage";
import { roundProofUrl } from "./rndApi";
import { ROUND_RESULT_META } from "./rndMeta";
import { measurementMeta, roundTypeOf, sampleTypesOf, typeLabel } from "./sampleTypeMeta";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "—");
const fmtD = (iso) => (iso ? new Date(String(iso).length <= 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—");

export default function SampleRoundList({ sample, types, measurements, canSubmit,
  canAssess, onUpload, onSubmit, onAssess, onOpenRound, busy, loading = false,
  highlightRoundId = "", onlyType = "" }) {
  const kinds = onlyType ? [onlyType] : sampleTypesOf(sample);
  const decided = sample.status === "decided" || sample.status === "cancelled";
  useEffect(() => {
    if (!highlightRoundId || loading) return;
    const el = document.querySelector(`[data-testid="round-row-${highlightRoundId}"]`);
    if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [highlightRoundId, loading, sample?.id]);

  if (loading) {
    return (
      <div className="space-y-2.5" data-testid="sample-rounds-loading">
        {[0, 1].map((i) => <div key={i} className="h-16 animate-pulse rounded-lg bg-[#F4F5F7]" />)}
        <p className="text-center text-[11.5px] text-[#6B6B73]">Memuat riwayat round…</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5" data-testid="sample-rounds">
      {(sample.participants || []).map((p) => (
        <div key={p.supplier_id} className="rounded-lg border border-[#EFF0F2]" data-testid={`sample-participant-${p.supplier_id}`}>
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#EFF0F2] bg-[#FAFBFC] px-3 py-2">
            <div>
              <p className="text-[12.5px] font-bold text-[#1C1C1E]">{p.supplier_name}</p>
              <p className="text-[10.5px] text-[#6B6B73]">
                {p.rounds || 0} round pada {Object.keys(p.types || {}).length || kinds.length} jenis{p.overdue ? " · pernah terlambat" : ""}
              </p>
            </div>
            <span className={`status-pill ${p.status === "acc" ? "pill-success" : p.status === "rejected" ? "pill-danger" : "pill-muted"}`}
              data-testid={`participant-status-${p.supplier_id}`}>
              {p.status === "acc" ? "ACC" : p.status === "rejected" ? "Ditolak" : p.status === "responded" ? "Sudah kirim hasil" : "Diundang"}
            </span>
          </div>

          {kinds.map((tc) => {
            const rounds = (sample.rounds || [])
              .filter((r) => r.supplier_id === p.supplier_id && roundTypeOf(r, sample) === tc)
              .slice().sort((a, b) => (a.round_no || 0) - (b.round_no || 0));
            const last = rounds[rounds.length - 1];
            const canOpenNext = !decided && last && last.result === "revisi";
            const prog = (p.types || {})[tc] || {};
            return (
              <div key={tc} data-testid={`sample-type-block-${p.supplier_id}-${tc}`} className="p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-[11px] font-bold text-[#0058CC]">
                    {typeLabel(tc, types)}
                    <span className="ml-2 font-normal text-[#6B6B73]">
                      {rounds.length} round{rounds.length > 1 ? ` · ${revisionLabel(rounds.length).toLowerCase()}` : ""}{prog.best_score != null ? ` · skor terbaik ${prog.best_score}` : ""}
                    </span>
                  </p>
                  {canOpenNext && canSubmit && (
                    <button className="secondary-button !px-2 !py-1 text-[10.5px]" disabled={busy} data-testid={`open-round-${p.supplier_id}-${tc}`} onClick={() => onOpenRound(p, tc)}>
                      <Plus size={12} /> Buka round berikutnya
                    </button>
                  )}
                </div>
                {rounds.length > 0 && (
                  <div className="mt-2">
                    <RoundBoxes testId={`sample-rounds-progress-${p.supplier_id}-${tc}`} testPrefix={`sample-round-box-${p.supplier_id}-${tc}`}
                      items={rounds.map((r) => ({
                        key: r.round_no, title: `rnd ${r.round_no} · ${revisionLabel(r.round_no)}`,
                        sub: `${(r.attachments || []).length} bukti${r.score != null ? ` · skor ${r.score}` : ""}`,
                        result: sampleRoundResult(r),
                      }))} />
                  </div>
                )}
                {rounds.length === 0 && (
                  <p className="mt-2 rounded-lg border border-dashed border-[#E5E5EA] px-3 py-2.5 text-[11px] text-[#6B6B73]" data-testid={`participant-no-rounds-${p.supplier_id}-${tc}`}>
                    Belum ada round {typeLabel(tc, types)} untuk mitra ini — kirim permintaannya (tombol <b>Kirim ke supplier</b>) untuk membuka round 1.
                  </p>
                )}

                {rounds.length > 0 && (
                  <ol className="relative mt-3 space-y-4 border-l-2 border-[#EFF0F2] pl-5" data-testid={`sample-round-timeline-${p.supplier_id}-${tc}`}>
                    {rounds.map((r) => (
                      <RoundBlock key={r.id} r={r} sample={sample} measurements={measurements} decided={decided}
                        highlight={r.id === highlightRoundId} canSubmit={canSubmit} canAssess={canAssess} busy={busy}
                        onUpload={onUpload} onSubmit={onSubmit} onAssess={onAssess} />
                    ))}
                  </ol>
                )}
              </div>
            );
          })}
        </div>
      ))}
      {(sample.participants || []).length === 0 && (
        <p className="rounded-lg border border-dashed border-[#E5E5EA] px-3 py-6 text-center text-[11.5px] text-[#6B6B73]" data-testid="sample-no-participants">
          Belum dikirim ke supplier. Pilih supplier lalu kirim permintaan — boleh lebih dari satu supaya hasilnya bisa dibandingkan, dan boleh beberapa jenis sekaligus.
        </p>
      )}
    </div>
  );
}

function RoundBlock({ r, sample, measurements, decided, highlight, canSubmit, canAssess, busy, onUpload, onSubmit, onAssess }) {
  const rm = ROUND_RESULT_META[r.result || ""] || ROUND_RESULT_META[""];
  const state = sampleRoundResult(r);
  const dot = { acc: "bg-[#1A7A3A]", revision: "bg-[#C62828]", rejected: "bg-[#8E1B1B]", review: "bg-[#0058CC]", draft: "bg-[#8E8E93]" }[state];
  const meas = Object.entries(r.measurements || {}).filter(([, v]) => v !== null && v !== undefined && v !== "");
  const atts = r.attachments || [];
  return (
    <li className={`relative ${highlight ? "rounded-lg bg-[#FFF8EE] p-2 ring-1 ring-inset ring-[#F5C26B]" : ""}`} data-testid={`round-row-${r.id}`} data-highlight={highlight ? "true" : undefined}>
      <span className={`absolute -left-[27px] top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${dot}`} style={highlight ? { left: "-35px" } : undefined} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-[12.5px] font-bold text-[#1C1C1E]">
          rnd {r.round_no}
          <span className="ml-1.5 rounded bg-[#F5F5F7] px-1.5 py-px text-[9.5px] font-bold text-[#6B6B73]" data-testid={`round-revision-${r.id}`}>{revisionLabel(r.round_no)}</span>
          {r.overdue && <span className="ml-1.5 rounded bg-[#FDECEC] px-1.5 py-px text-[9.5px] font-bold text-[#C0392B]">TERLAMBAT</span>}
        </h4>
        <span className="text-[11px] font-bold" style={{ color: rm.tone }} data-testid={`round-result-${r.id}`}>
          {rm.label}{r.score != null ? ` · skor ${r.score}` : ""}
        </span>
      </div>
      <p className="mt-0.5 text-[10.5px] text-[#8E8E93]">
        Dikirim {fmtD(r.sent_at)}{r.opened_by ? ` oleh ${r.opened_by}` : ""} · Tenggat <b className={r.overdue ? "text-[#C0392B]" : ""}>{fmtD(r.due_date)}</b> · Diterima {r.received_at ? <b className="text-[#1C1C1E]">{fmtAt(r.received_at)}</b> : "belum"}
      </p>

      <div className="mt-2 rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
        <p className="mb-1.5 text-[10.5px] font-bold uppercase text-[#8E8E93]">Bukti dikirim · {atts.length}</p>
        {atts.length === 0 ? (
          <p className="flex items-center justify-center gap-1 py-2 text-[10.5px] text-[#B26A00]">
            <Paperclip size={11} /> belum ada bukti{r.status === "open" ? " — wajib diunggah sebelum disetor" : ""}
          </p>
        ) : (
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
            {atts.map((a) => (
              <a key={a.id} href={roundProofUrl(sample.id, r.id, a.id)} target="_blank" rel="noreferrer" title={a.filename} data-testid={`round-file-${a.id}`}
                className="block overflow-hidden rounded-lg border border-[#E5E5EA] bg-white">
                <ProofImage url={roundProofUrl(sample.id, r.id, a.id)} attachment={a} alt={a.filename} className="aspect-square w-full" />
                <p className="truncate px-1.5 py-1 text-[9.5px] font-semibold">{a.filename}</p>
              </a>
            ))}
          </div>
        )}
        {(r.note || meas.length > 0 || Number(r.cost) > 0) && (
          <div className="mt-2 border-t border-[#EFF0F2] pt-2 text-[11px] text-[#3C3C43]" data-testid={`round-meas-${r.id}`}>
            {r.note && <p className="flex gap-1.5"><FileText size={12} className="mt-0.5 shrink-0 text-[#6B6B73]" /><span><b>Catatan hasil:</b> “{r.note}”{r.performed_by ? ` — ${r.performed_by}` : ""}</span></p>}
            {meas.length > 0 && (
              <p className="mt-1 text-[10.5px] text-[#6B6B73]">
                Hasil ukur: {meas.map(([k, v]) => { const m = measurementMeta(k, measurements); return `${m.label} ${v}${m.unit ? ` ${m.unit}` : ""}`; }).join(" · ")}
              </p>
            )}
            {Number(r.cost) > 0 && <p className="mt-1 text-[10.5px] text-[#6B6B73]">Biaya sample: {formatCurrency(r.cost)}</p>}
          </div>
        )}
      </div>

      {r.status === "assessed" && (
        <div className={`mt-2 flex gap-2 rounded-lg border px-3 py-2 ${r.result === "acc" ? "border-[#CDE9D6] bg-[#F4FCF6]" : r.result === "revisi" ? "border-[#F5C6C6] bg-[#FDF3F2]" : "border-[#E8B4B0] bg-[#FDECEC]"}`}
          data-testid={`round-qc-${r.id}`}>
          {r.result === "acc" ? <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[#1A7A3A]" /> : r.result === "revisi" ? <RotateCcw size={14} className="mt-0.5 shrink-0 text-[#C62828]" /> : <XCircle size={14} className="mt-0.5 shrink-0 text-[#8E1B1B]" />}
          <div className="text-[11.5px]" style={{ color: rm.tone }}>
            <p className="font-bold">{r.result === "acc" ? `ACC — skor ${r.score ?? "—"}` : r.result === "revisi" ? "Komentar revisi penilai" : "Ditolak — supplier tidak dilanjutkan"}</p>
            {r.assess_note && <p className="whitespace-pre-wrap text-[#3C3C43]">{r.assess_note}</p>}
            <p className="mt-0.5 text-[10px] opacity-70">{r.assessed_by || r.qc?.by || "penilai"} · {fmtAt(r.assessed_at || r.qc?.at)}{r.qc?.verdict ? ` · QC ${r.qc.verdict}` : ""}{r.result === "revisi" ? ` → ${revisionLabel(r.round_no + 1)} dibuka` : ""}</p>
          </div>
        </div>
      )}
      {r.status === "submitted" && (
        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-[#0058CC]"><Clock size={12} /> Hasil sudah disetor — menunggu penilaian (ACC / revisi / tolak).</p>
      )}

      {!decided && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {r.status === "open" && canSubmit && (
            <>
              <label className="secondary-button !px-2 !py-1 text-[10.5px] cursor-pointer" data-testid={`round-upload-label-${r.id}`}>
                <Upload size={12} /> Unggah bukti
                <input type="file" className="hidden" accept="image/*,.pdf" data-testid={`round-upload-${r.id}`}
                  onChange={(e) => { const file = e.target.files?.[0]; if (file) onUpload(r, file); e.target.value = ""; }} />
              </label>
              <button className="primary-button !px-2 !py-1 text-[10.5px]" disabled={busy} data-testid={`round-submit-${r.id}`} onClick={() => onSubmit(r)}>
                <Send size={12} /> Setor hasil
              </button>
            </>
          )}
          {r.status === "submitted" && canAssess && (
            <button className="primary-button !px-2 !py-1 text-[10.5px]" disabled={busy} data-testid={`round-assess-${r.id}`} onClick={() => onAssess(r)}>
              <CheckCircle2 size={12} /> Nilai hasil
            </button>
          )}
        </div>
      )}
    </li>
  );
}
