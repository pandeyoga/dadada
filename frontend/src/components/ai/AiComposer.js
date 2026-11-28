import React, { useRef, useState } from "react";
import { Paperclip, ArrowUp, Square, X } from "lucide-react";
import { uploadAttachment, friendlyError } from "./aiApi";

export const ROLES = [
  { v: "copilot", l: "Copilot" },
  { v: "sales", l: "Agen Penjualan" },
  { v: "cs", l: "Agen CS" },
];

export default function AiComposer({
  onSend, onStop, streaming, disabled, disabledReason, webResearchAvailable,
  role, onRole, web, onWeb, initialText = "",
}) {
  const [text, setText] = useState(initialText);
  const [files, setFiles] = useState([]); // {id,name}
  const [err, setErr] = useState("");
  const fileRef = useRef(null);

  const submit = (e) => {
    e?.preventDefault();
    const t = text.trim();
    if (!t || streaming || disabled) return;
    onSend({ text: t, attachments: files.map((f) => f.id) });
    setText(""); setFiles([]);
  };

  const pick = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setErr("");
    try {
      const r = await uploadAttachment(f);
      setFiles((x) => [...x, { id: r.id || r.file_id, name: f.name }]);
    } catch (er) { setErr(friendlyError(er, "Lampiran gagal diunggah.")); }
  };

  return (
    <form onSubmit={submit} className="px-7 pb-5 pt-3">
      <div className="mx-auto flex max-w-[760px] flex-col gap-2.5 rounded-2xl border border-[#C9D8D3] bg-white px-3.5 py-3 shadow-[0_2px_10px_rgba(0,53,59,0.06)]">
        <label htmlFor="ai-ask" className="sr-only">Pesan untuk Estora AI</label>
        <textarea id="ai-ask" rows={2} value={text} disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) submit(e); }}
          placeholder={disabled ? disabledReason : "Tanya atau perintahkan Estora AI…"}
          className="resize-none border-0 bg-transparent text-[15px] text-[#12312F] outline-none" />
        {files.length ? (
          <div className="flex flex-wrap gap-1.5">
            {files.map((f) => (
              <span key={f.id} className="inline-flex items-center gap-1 rounded-full bg-[#EEF3F1] px-2.5 py-1 text-xs text-[#2B4744]">
                {f.name}
                <button type="button" aria-label={`Hapus lampiran ${f.name}`}
                  onClick={() => setFiles((x) => x.filter((y) => y.id !== f.id))}><X className="h-3 w-3" /></button>
              </span>
            ))}
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <input ref={fileRef} type="file" className="hidden" onChange={pick} data-testid="ai-file" />
          <button type="button" aria-label="Lampirkan berkas" onClick={() => fileRef.current?.click()}
            className="flex h-10 w-10 items-center justify-center rounded-[10px] border border-[#DDE7E3] bg-white text-[#2B4744]">
            <Paperclip className="h-[18px] w-[18px]" aria-hidden="true" />
          </button>
          <label className="inline-flex min-h-[40px] items-center gap-1.5 rounded-[10px] border border-[#DDE7E3] px-2.5 text-[13px] text-[#2B4744]">
            Peran
            <select value={role} onChange={(e) => onRole(e.target.value)}
              className="border-0 bg-transparent text-[13px] font-semibold text-[#12312F]">
              {ROLES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
            </select>
          </label>
          <label className={`inline-flex min-h-[40px] items-center gap-1.5 rounded-[10px] border border-[#DDE7E3] px-2.5 text-[13px] text-[#2B4744] ${webResearchAvailable ? "" : "opacity-60"}`}
            title={webResearchAvailable ? "" : "Riset web belum diaktifkan di Pengaturan AI"}>
            <input type="checkbox" checked={!!web && webResearchAvailable} disabled={!webResearchAvailable}
              onChange={(e) => onWeb(e.target.checked)} /> Riset web
          </label>
          {streaming ? (
            <button type="button" onClick={onStop} aria-label="Hentikan"
              className="ml-auto flex h-11 w-11 items-center justify-center rounded-xl bg-[#00454D] text-white">
              <Square className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : (
            <button type="submit" aria-label="Kirim" disabled={disabled || !text.trim()}
              className="ml-auto flex h-11 w-11 items-center justify-center rounded-xl bg-[#006284] text-white hover:bg-[#00454D] disabled:opacity-50">
              <ArrowUp className="h-[18px] w-[18px]" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
      {err ? <p role="alert" className="mx-auto mt-2 max-w-[760px] text-[13px] text-[#9B1C1C]">{err}</p> : null}
      <p className="mx-auto mt-2 max-w-[760px] text-center text-xs text-[#3E5653]">
        Estora AI bisa keliru. Aksi yang mengubah data selalu menampilkan kartu persetujuan dan tercatat di audit.
      </p>
    </form>
  );
}
