import React from "react";
import { Loader2, Check, Ticket } from "lucide-react";
import PortalAiConfirmCard from "./PortalAiConfirmCard";

const fmtDue = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const s = d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" });
  return `${s} WIB`; // sama dengan teks chat (WIB), apa pun zona waktu peramban pembeli
};

export function TicketCard({ ticket }) {
  const due = fmtDue(ticket.due_at);
  return (
    <div data-testid="portal-ai-ticket" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
      <Ticket className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>Diteruskan ke CS · No. {ticket.number || ticket.id}{due ? ` · dibalas paling lambat ${due}` : ""}</span>
    </div>
  );
}

export default function PortalAiMessage({ message, onActionChanged }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="m-0 max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-indigo-600 px-3 py-2 text-sm text-white">{message.text}</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {(message.steps || []).length ? (
        <ul className="m-0 flex list-none flex-col gap-0.5 p-0 text-xs text-slate-500">
          {message.steps.map((s) => (
            <li key={s.id} className="flex items-center gap-1.5">
              {s.status === "running" ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : <Check className="h-3 w-3" aria-hidden="true" />}
              {s.label}
            </li>
          ))}
        </ul>
      ) : null}
      {message.text ? (
        <p className="m-0 max-w-[90%] whitespace-pre-wrap rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2 text-sm text-slate-800">{message.text}</p>
      ) : message.streaming && !(message.steps || []).length ? (
        <p className="m-0 text-xs text-slate-500">Mengetik…</p>
      ) : null}
      {(message.actions || []).map((a) => <PortalAiConfirmCard key={a.id} action={a} onChanged={onActionChanged} />)}
      {message.ticket ? <TicketCard ticket={message.ticket} /> : null}
      {message.error ? <p role="alert" className="m-0 text-sm text-rose-700">{message.error}</p> : null}
    </div>
  );
}
