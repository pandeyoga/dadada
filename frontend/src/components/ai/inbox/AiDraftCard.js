import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { sendDraft, rewriteDraft, discardDraft, friendlyError } from "../aiApi";

const MODE = { draft: "Draf", auto: "Otomatis", off: "Mati" };

/**
 * Kartu draf (garis putus-putus). draft: {id, text, category, category_label, mode, basis[], status}.
 * "Kirim" memanggil send; teks hanya dikirim bila diedit (backend mencatat edit = teks berbeda).
 */
export default function AiDraftCard({ draft, windowOpen = true, onSent, onDiscarded }) {
  const [text, setText] = useState(draft.text || "");
  const [editing, setEditing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [instr, setInstr] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { setText(draft.text || ""); setEditing(false); setRewriting(false); setErr(""); }, [draft.id, draft.text]);

  const run = async (fn, after) => {
    setBusy(true); setErr("");
    try { const r = await fn(); after?.(r); } catch (e) { setErr(friendlyError(e, "Aksi draf gagal.")); }
    finally { setBusy(false); }
  };
  const send = () => run(() => sendDraft(draft.id, text !== draft.text ? text : undefined),
    () => { toast.success("Balasan terkirim."); onSent?.(); });
  const rewrite = () => instr.trim() && run(() => rewriteDraft(draft.id, instr.trim()), (r) => {
    setText(r?.text || r?.draft?.text || text); setRewriting(false); setInstr(""); onSent?.(false);
  });
  const discard = () => run(() => discardDraft(draft.id), () => onDiscarded?.());

  const basis = Array.isArray(draft.basis) ? draft.basis : draft.basis ? [draft.basis] : [];
  const cat = draft.category_label || String(draft.category || "").replace(/_/g, " ");

  return (
    <section aria-label="Draf balasan AI" data-testid="ai-draft-card"
      className="flex flex-col gap-2.5 rounded-xl border-[1.5px] border-dashed border-[#006284] bg-[#F1F8F6] p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-[#00454D]">Draf AI · menunggu sales</span>
        <span className="text-[#3E5653]">Kategori: {cat || "—"} · mode {MODE[draft.mode] || "Draf"}</span>
      </div>
      {editing ? (
        <textarea aria-label="Edit draf balasan" rows={5} value={text} onChange={(e) => setText(e.target.value)}
          className="w-full rounded-lg border border-[#C9D8D3] bg-white p-2 text-sm text-[#12312F]" />
      ) : (
        <p className="m-0 whitespace-pre-wrap text-sm leading-relaxed text-[#12312F]">{text}</p>
      )}
      {basis.length ? <span className="text-xs text-[#3E5653]">Dasar: {basis.map((b) => (typeof b === "string" ? b : b.label || b.source)).join(" · ")}</span> : null}
      {!windowOpen ? <span className="text-xs text-[#7A3E00]">Jendela 24 jam tertutup: draf tidak bisa dikirim bebas, gunakan template.</span> : null}
      {rewriting ? (
        <div className="flex flex-wrap gap-2">
          <input aria-label="Instruksi tulis ulang" value={instr} onChange={(e) => setInstr(e.target.value)}
            placeholder="Mis. buat lebih singkat"
            className="min-h-[40px] min-w-[200px] flex-1 rounded-lg border border-[#C9D8D3] px-2 text-sm" />
          <button type="button" disabled={busy || !instr.trim()} onClick={rewrite}
            className="min-h-[40px] rounded-lg bg-[#006284] px-3 text-[13px] font-semibold text-white disabled:opacity-60">Terapkan</button>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={send} disabled={busy || !windowOpen || !text.trim()} data-testid="ai-draft-send"
          className="min-h-[40px] rounded-lg bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Kirim</button>
        <button type="button" onClick={() => setEditing((v) => !v)} disabled={busy}
          className="min-h-[40px] rounded-lg border border-[#B9CFC8] bg-white px-4 text-sm font-semibold text-[#12312F]">{editing ? "Selesai edit" : "Edit"}</button>
        <button type="button" onClick={() => setRewriting((v) => !v)} disabled={busy}
          className="min-h-[40px] rounded-lg border border-[#B9CFC8] bg-white px-4 text-sm font-semibold text-[#12312F]">Tulis ulang</button>
        <button type="button" onClick={discard} disabled={busy}
          className="min-h-[40px] rounded-lg px-3 text-sm font-semibold text-[#9B1C1C]">Buang</button>
      </div>
      {err ? <p role="alert" className="m-0 text-[13px] text-[#9B1C1C]">{err}</p> : null}
    </section>
  );
}
