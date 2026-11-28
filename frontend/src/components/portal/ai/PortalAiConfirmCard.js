import React, { useRef, useState } from "react";
import { confirmAction, cancelAction, portalAiError } from "./portalAiApi";

const STATUS_TEXT = {
  executed: "Sudah dikirim. Terima kasih.",
  failed: "Gagal dikirim. Silakan coba lagi atau bicara dengan CS.",
  rejected: "Dibatalkan.",
  cancelled: "Dibatalkan.",
};

/** Kartu "Kirim komplain ini?" — konfirmasi dijaga useRef agar klik ganda hanya sekali. */
export default function PortalAiConfirmCard({ action, onChanged }) {
  const [status, setStatus] = useState(action.status || "pending");
  const [failure, setFailure] = useState(action.error || "");
  const [summary, setSummary] = useState(action.summary || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const inflight = useRef(false);
  const pending = status === "pending";
  const payload = action.payload?.json || action.payload || {};
  const changes = (action.preview?.changes || []).map((c) => (typeof c === "string" ? { title: c } : c));

  const run = async (fn, fallbackStatus) => {
    if (inflight.current) return;
    inflight.current = true;
    setBusy(true); setErr("");
    try {
      const r = await fn(action.id);
      const a = r?.action || r || {};
      const st = a.status || fallbackStatus;
      setStatus(st); setFailure(a.error || ""); setSummary(a.summary || "");
      onChanged?.({ ...action, status: st, summary: a.summary || null, error: a.error || null });
    } catch (e) {
      setErr(portalAiError(e, "Tidak dapat diproses."));
      inflight.current = false;
    } finally { setBusy(false); }
  };

  return (
    <section aria-label="Konfirmasi" data-testid="portal-ai-confirm"
      className="rounded-xl border border-indigo-200 bg-white p-3 text-sm">
      <p className="m-0 font-semibold text-slate-800">{pending ? (action.preview?.title || "Kirim komplain ini?") : "Komplain"}</p>
      <div className="mt-1.5 text-slate-600">
        {payload.subjek || payload.subject ? (
          <p className="m-0"><b>{payload.subjek || payload.subject}</b></p>
        ) : null}
        {payload.pesan || payload.message ? <p className="m-0 mt-1 whitespace-pre-wrap">{payload.pesan || payload.message}</p> : null}
        {changes.map((c, i) => <p key={i} className="m-0 mt-1">{c.title}{c.detail ? ` — ${c.detail}` : ""}</p>)}
      </div>
      {pending ? (
        <div className="mt-3 flex gap-2">
          <button type="button" data-testid="portal-ai-confirm-send" disabled={busy}
            onClick={() => run(confirmAction, "executed")}
            className="min-h-[40px] rounded-lg bg-indigo-600 px-4 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">Kirim</button>
          <button type="button" data-testid="portal-ai-confirm-cancel" disabled={busy}
            onClick={() => run(cancelAction, "rejected")}
            className="min-h-[40px] rounded-lg border px-4 text-slate-700 hover:bg-slate-100 disabled:opacity-60">Batal</button>
        </div>
      ) : (
        <p role="status" className="m-0 mt-2 text-slate-600">
          {/* ringkasan dari respons konfirmasi, mis. klaim garansi yang tercatat namun DITOLAK */}
          {status === "executed" && summary && summary !== action.preview?.title ? summary : (STATUS_TEXT[status] || status)}
          {failure ? ` ${failure}` : ""}
        </p>
      )}
      {err ? <p role="alert" className="m-0 mt-2 text-rose-700">{err}</p> : null}
    </section>
  );
}
