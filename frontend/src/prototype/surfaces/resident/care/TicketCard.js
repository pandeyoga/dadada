import React from "react";
import { Star } from "lucide-react";
import { FrostCard } from "../../../components/GlassCard";
import Stepper from "../../../components/Stepper";
import StatusChip from "../../../components/StatusChip";
import TicketPhoto from "./TicketPhoto";
import { TICKET_FLOW } from "../../../services/api/care";
import { tanggal } from "../../../lib/format";

const STEPS = ["Dibuat", "Diverifikasi", "Dikerjakan", "Selesai"];
const TONE = { dibuat: "warn", diverifikasi: "info", dikerjakan: "info", selesai: "ok", dikonfirmasi: "ok" };
const label = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const KIND = { rusak: "Kerusakan", garansi: "Klaim garansi" };

/** Satu tiket: ringkasan, foto, linimasa (Stepper), riwayat, dan aksi konfirmasi saat selesai. */
export default function TicketCard({ ticket, onConfirm }) {
  const current = ticket.status === "dikonfirmasi" ? STEPS.length : TICKET_FLOW.indexOf(ticket.status);
  const last = ticket.history[ticket.history.length - 1];
  return (
    <FrostCard data-ticket={ticket.id} className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">{`${KIND[ticket.kind] || "Laporan"} · ${ticket.category}`}</p>
          <h3 className="text-[15.5px] font-bold leading-snug">{ticket.description}</h3>
        </div>
        <StatusChip tone={TONE[ticket.status] || "neutral"}>{label(ticket.status)}</StatusChip>
      </div>
      {ticket.photos.length > 0 && (
        <div className="flex gap-2">
          {ticket.photos.map((p) => <TicketPhoto key={p} img={p} className="h-16 w-24 rounded-lg" />)}
        </div>
      )}
      <Stepper steps={STEPS} current={current} />
      <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{`${tanggal(last.at)} · ${last.note}`}</p>
      {ticket.assignee && <p className="text-[13px] text-[color:var(--rdg-muted)]">{`Ditangani: ${ticket.assignee}`}</p>}
      {ticket.status === "dikonfirmasi" && (
        <p className="flex items-center gap-1 text-[13.5px] font-bold" aria-label={`Nilai ${ticket.rating} dari 5`}>
          {[1, 2, 3, 4, 5].map((n) => <Star key={n} size={16} aria-hidden="true" className={n <= ticket.rating ? "fill-[#f2b705] text-[#b9741a]" : "text-[color:var(--rdg-muted)]"} />)}
        </p>
      )}
      {ticket.status === "selesai" && (
        <button type="button" className="rdg-btn-primary w-full" onClick={() => onConfirm(ticket)}>Konfirmasi selesai + beri nilai</button>
      )}
      <details className="text-[13px]">
        <summary className="cursor-pointer font-semibold text-rdg-forest">Riwayat tiket</summary>
        <ol className="mt-2 space-y-1.5 border-l-2 border-[color:var(--rdg-line)] pl-3">
          {ticket.history.map((h) => <li key={h.status + h.at}><span className="font-bold">{label(h.status)}</span>{` · ${tanggal(h.at)}`}<br /><span className="text-[color:var(--rdg-muted)]">{h.note}</span></li>)}
        </ol>
      </details>
    </FrostCard>
  );
}
