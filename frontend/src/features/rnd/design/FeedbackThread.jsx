/** FeedbackThread — percakapan dua arah desainer ↔ penilai per desain (tercatat di timeline). */
import { useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import { addDesignFeedback } from "../rndApi";
import { errMsg } from "../rndMeta";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "");

export default function FeedbackThread({ design, currentUser, canWrite, onDone, onError }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const rows = [...(design.feedback || [])].sort((a, b) => (a.at < b.at ? -1 : 1));

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try { await addDesignFeedback(design.id, { text, version: design.version }); setText(""); onDone?.(); }
    catch (e) { onError?.(errMsg(e, "Umpan balik gagal dikirim.")); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-2" data-testid="design-feedback-thread">
      {design.reject_reason && ["revision", "draft"].includes(design.status) && (
        <div className="rounded-lg border border-[#F5C6C6] bg-[#FDEDED] px-3 py-2 text-[11.5px] text-[#8E1B1B]" data-testid="design-revision-banner">
          <b>Kenapa belum ACC:</b> {design.reject_reason} <span className="text-[10px] opacity-70">— {design.rejected_by}, {fmtAt(design.rejected_at)}</span>
        </div>
      )}
      <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
        {rows.length === 0 && <p className="text-[11.5px] text-[#9A9BA3]" data-testid="design-feedback-empty">Belum ada umpan balik. Mulai percakapan di bawah.</p>}
        {rows.map((f) => {
          const mine = f.user_id === currentUser?.id;
          const designerSide = f.side === "designer";
          return (
            <div key={f.id} className={`flex ${mine ? "justify-end" : "justify-start"}`} data-testid={`design-feedback-${f.id}`}>
              <div className={`max-w-[80%] rounded-xl px-3 py-2 text-[11.5px] ${designerSide ? "bg-[#F1E9F7] text-[#2B1240]" : "bg-[#EEF4FF] text-[#0B2A5C]"}`}>
                <p className="mb-0.5 text-[9.5px] font-semibold opacity-70">
                  {f.by} · {designerSide ? "desainer" : "penilai"} · v{f.version} · {fmtAt(f.at)}
                </p>
                <p className="whitespace-pre-wrap">{f.text}</p>
              </div>
            </div>
          );
        })}
      </div>
      {canWrite && (
        <div className="flex gap-2">
          <textarea className="field flex-1" rows={2} value={text} onChange={(e) => setText(e.target.value)} data-testid="design-feedback-input"
            placeholder={currentUser?.role === "designer" ? "Tanya / jelaskan revisi ke penilai…" : "Arahan / catatan untuk desainer…"}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(); }} />
          <button className="primary-button self-end" disabled={busy || !text.trim()} onClick={send} data-testid="design-feedback-send">
            <Send size={13} /> Kirim
          </button>
        </div>
      )}
      {!canWrite && <p className="flex items-center gap-1 text-[10.5px] text-[#9A9BA3]"><MessageSquare size={11} /> Hanya desainer & penilai yang bisa menulis.</p>}
    </div>
  );
}
