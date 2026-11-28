import React, { useState } from "react";
import { reviewSample, friendlyError } from "../aiApi";

/** Tinjau sampel balasan otomatis: benar / salah (mengumpan akurasi per kategori). */
export default function AiSampleReview({ draft, onDone }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(draft.sample_review || null);
  if (done) return <p className="m-0 text-xs text-[#3E5653]">Tinjauan sampel: {done === "correct" ? "benar" : "salah"}. Terima kasih.</p>;
  const go = async (verdict) => {
    setBusy(true); setErr("");
    try { await reviewSample(draft.id, verdict); setDone(verdict); onDone?.(); }
    catch (e) { setErr(friendlyError(e, "Tinjauan gagal disimpan.")); }
    finally { setBusy(false); }
  };
  return (
    <div className="rounded-lg border border-[#B9CFC8] bg-white p-3" data-testid="ai-sample-review">
      <p className="m-0 mb-2 text-[13px] font-semibold text-[#12312F]">Sampel untuk ditinjau: apakah balasan otomatis ini sudah tepat?</p>
      <p className="m-0 mb-2 whitespace-pre-wrap text-[13px] text-[#2B4744]">{draft.final_text || draft.text}</p>
      <div className="flex gap-2">
        <button type="button" disabled={busy} onClick={() => go("correct")}
          className="min-h-[40px] rounded-lg bg-[#006284] px-3 text-[13px] font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Benar</button>
        <button type="button" disabled={busy} onClick={() => go("wrong")}
          className="min-h-[40px] rounded-lg border border-[#E8C4C0] bg-white px-3 text-[13px] font-semibold text-[#9B1C1C] disabled:opacity-60">Salah</button>
      </div>
      {err ? <p role="alert" className="m-0 mt-1 text-xs text-[#9B1C1C]">{err}</p> : null}
    </div>
  );
}
