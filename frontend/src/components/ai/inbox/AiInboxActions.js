import React, { useState } from "react";
import { ShieldCheck, MessageCircleQuestion } from "lucide-react";
import AiActionCard from "../AiActionCard";
import { requestUnofficialOptin, friendlyError } from "../aiApi";

/**
 * Panel AI di Inbox untuk satu kontak:
 * - usulan aksi agen WhatsApp yang menunggu persetujuan (Setujui / Ubah / Tolak lewat endpoint aksi yang sama);
 * - "Minta izin kanal kedua": pertanyaan opt-in dikirim lewat nomor RESMI; balasan YA mencatat persetujuan.
 * `ai` = data `GET /ai/inbox/conversations/{id}`.
 */
export default function AiInboxActions({ ai, conversationId, windowOpen, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  if (!ai) return null;
  const actions = ai.actions || [];  // pending + beberapa yang terakhir diputuskan (status & alasan gagal)
  const anyPending = actions.some((a) => a.status === "pending");
  const showOptin = ai.unofficial_enabled && !ai.optin_unofficial;
  if (!actions.length && !showOptin) return null;

  const ask = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      await requestUnofficialOptin(conversationId);
      setMsg("Pertanyaan izin terkirim lewat nomor resmi. Menunggu balasan YA dari pelanggan.");
      onChanged?.();
    } catch (e) { setErr(friendlyError(e, "Permintaan izin gagal dikirim.")); }
    finally { setBusy(false); }
  };

  return (
    <aside aria-label="Tindakan Estora AI" data-testid="ai-inbox-actions"
      className="flex flex-col gap-3 rounded-xl border border-[#D5E0DC] bg-white p-4 shadow-[var(--shadow-card)]">
      {actions.length ? (
        <>
          <h2 className="m-0 flex items-center gap-1.5 font-['Space_Grotesk',Inter,sans-serif] text-base">
            <ShieldCheck className="h-4 w-4 text-[#006284]" aria-hidden="true" /> Usulan agen WhatsApp
          </h2>
          {anyPending ? <p className="m-0 text-xs text-[#3E5653]">Usulan baru belum dijalankan. Periksa lalu setujui atau tolak.</p> : null}
          {actions.map((a) => <AiActionCard key={a.id} action={a} onChanged={() => onChanged?.()} />)}
        </>
      ) : null}
      {showOptin ? (
        <div className="flex flex-col gap-1.5 text-[13px]" data-testid="ai-optin-unofficial">
          <span className="font-semibold text-[#3E5653]">Kanal kedua (gateway tidak resmi)</span>
          <span className="text-[#12312F]">
            {ai.optin_pending ? "Pertanyaan izin sudah dikirim; menunggu pelanggan membalas YA."
              : "Pelanggan belum memberi izin dihubungi lewat nomor kedua."}
          </span>
          <button type="button" onClick={ask} disabled={busy || !windowOpen}
            title={windowOpen ? "" : "Sesi 24 jam tertutup: pertanyaan izin hanya bisa dikirim saat sesi aktif."}
            className="inline-flex min-h-[40px] w-fit items-center gap-1.5 rounded-lg border border-[#B9CFC8] bg-white px-3 text-[13px] font-semibold text-[#006284] hover:text-[#00454D] disabled:opacity-60">
            <MessageCircleQuestion className="h-4 w-4" aria-hidden="true" />
            {ai.optin_pending ? "Kirim ulang permintaan izin" : "Minta izin kanal kedua"}
          </button>
          {msg ? <p role="status" className="m-0 text-xs text-[#14532D]">{msg}</p> : null}
          {err ? <p role="alert" className="m-0 text-xs text-[#9B1C1C]">{err}</p> : null}
        </div>
      ) : null}
    </aside>
  );
}
