import React, { useRef, useState } from "react";
import { ShieldCheck, Loader2 } from "lucide-react";
import { approveAction, rejectAction, friendlyError } from "./aiApi";

const STATUS_TEXT = {
  executed: "Sudah dijalankan dan tercatat di Audit dengan label \"Estora AI\".",
  failed: "Aksi gagal dijalankan.",
  rejected: "Ditolak.",
  executing: "Sedang dijalankan…",
};

const asChange = (c) => (typeof c === "string" ? { title: c } : c || {});
const asCheck = (c) => (typeof c === "string" ? { label: c, ok: true } : c || {});

/**
 * Kartu persetujuan (mockup Confirm). `action.preview` = { changes: [string | {title, detail, check}],
 * checks: [{ok, label}], on_behalf_of }. Approve dijaga `useRef` agar klik ganda cepat hanya sekali.
 */
export default function AiActionCard({ action, onChanged }) {
  const [status, setStatus] = useState(action.status || "pending");
  const [result, setResult] = useState(action.result || null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [mode, setMode] = useState(null); // null | "edit" | "reject"
  const [note, setNote] = useState("");
  const inflight = useRef(false);

  const preview = action.preview || {};
  const changes = (preview.changes || []).map(asChange);
  const checks = (preview.checks || []).map(asCheck);
  const pending = status === "pending";

  const run = async (fn, okStatus) => {
    if (inflight.current) return;
    inflight.current = true;
    setBusy(true); setErr("");
    try {
      const r = await fn();
      const st = r?.status || okStatus;
      setStatus(st); setResult(r?.result || null);
      onChanged?.({ ...action, status: st });
    } catch (e) {
      setErr(friendlyError(e, "Aksi tidak dapat diproses."));
    } finally { inflight.current = false; setBusy(false); }
  };

  const approve = () => run(
    () => approveAction(action.id, mode === "edit" && note.trim() ? { note: note.trim() } : undefined),
    "executed");
  const reject = () => run(() => rejectAction(action.id, note.trim()), "rejected");

  return (
    <section aria-label="Usulan aksi" data-testid="ai-action-card"
      className="overflow-hidden rounded-[14px] border border-[#B9CFC8] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#D5E0DC] bg-[#EEF6F3] px-4 py-3">
        <span className="inline-flex items-center gap-2 text-sm font-semibold">
          <ShieldCheck className="h-4 w-4 text-[#006284]" aria-hidden="true" />
          {pending ? `Perlu persetujuan · ${changes.length || 1} perubahan` : "Usulan aksi"}
        </span>
        {preview.on_behalf_of ? (
          <span className="text-xs text-[#3E5653]">Atas nama: {preview.on_behalf_of}</span>
        ) : null}
      </div>
      {changes.length ? (
        <ol className="m-0 list-none p-0">
          {changes.map((c, i) => (
            <li key={i} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2.5 border-b border-[#EEF3F1] px-4 py-3 text-sm last:border-b-0">
              <span>
                <b>{c.title}</b>
                {c.detail ? <><br /><span className="text-[#3E5653]">{c.detail}</span></> : null}
              </span>
              {c.check ? <CheckChip check={asCheck(c.check)} /> : null}
            </li>
          ))}
        </ol>
      ) : null}
      {checks.length ? (
        <div className="flex flex-wrap gap-1.5 border-t border-[#EEF3F1] px-4 py-2.5">
          {checks.map((c, i) => <CheckChip key={i} check={c} />)}
        </div>
      ) : null}

      {pending && mode ? (
        <div className="border-t border-[#D5E0DC] px-4 py-3">
          <label className="text-xs font-semibold text-[#3E5653]" htmlFor={`note-${action.id}`}>
            {mode === "edit" ? "Catatan perubahan sebelum disetujui" : "Alasan penolakan (opsional)"}
          </label>
          <textarea id={`note-${action.id}`} rows={2} value={note} onChange={(e) => setNote(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[#C9D8D3] p-2 text-sm text-[#12312F] outline-none focus:border-[#006284]" />
        </div>
      ) : null}

      {pending ? (
        <div className="flex flex-wrap gap-2 border-t border-[#D5E0DC] px-4 py-3">
          {mode === "reject" ? (
            <button type="button" onClick={reject} disabled={busy}
              className="min-h-[44px] rounded-[10px] border border-[#E8C4C0] bg-white px-4 text-sm font-semibold text-[#9B1C1C] disabled:opacity-60">
              Konfirmasi tolak
            </button>
          ) : (
            <button type="button" onClick={approve} disabled={busy} data-testid="ai-approve"
              className="inline-flex min-h-[44px] items-center gap-2 rounded-[10px] bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {mode === "edit" ? "Setujui dengan perubahan" : "Setujui"}
            </button>
          )}
          <button type="button" disabled={busy} onClick={() => setMode(mode === "edit" ? null : "edit")}
            className="min-h-[44px] rounded-[10px] border border-[#B9CFC8] bg-white px-4 text-sm font-semibold text-[#12312F] disabled:opacity-60">
            Ubah
          </button>
          <button type="button" disabled={busy} onClick={() => setMode(mode === "reject" ? null : "reject")}
            className="min-h-[44px] rounded-[10px] border border-[#E8C4C0] bg-white px-4 text-sm font-semibold text-[#9B1C1C] disabled:opacity-60">
            Tolak
          </button>
        </div>
      ) : (
        <p className="m-0 border-t border-[#D5E0DC] px-4 py-3 text-[13px] text-[#3E5653]" role="status">
          {STATUS_TEXT[status] || status}
          {status === "failed" && typeof result === "string" ? ` ${result}` : ""}
        </p>
      )}
      {err ? <p role="alert" className="m-0 px-4 pb-3 text-[13px] text-[#9B1C1C]">{err}</p> : null}
    </section>
  );
}

function CheckChip({ check }) {
  const ok = check.ok !== false;
  return (
    <span className={`self-center rounded-md px-2 py-0.5 text-xs font-semibold ${ok ? "bg-[#E3F2EA] text-[#14532D]" : "bg-[#FFF4E5] text-[#7A3E00]"}`}>
      {check.label}
    </span>
  );
}
