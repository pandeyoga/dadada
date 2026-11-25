import React, { useCallback, useState } from "react";
import { ArrowRight, Star } from "lucide-react";
import ManagerPage, { Loading, FIELD } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { listTickets, advanceTicket, TICKET_FLOW } from "../../services/api/care";
import { assignTicket } from "../../services/api/manager";
import { useProto } from "../../services/useStore";
import { tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const COLUMNS = [
  { key: "dibuat", label: "Dibuat", match: ["dibuat"] },
  { key: "diverifikasi", label: "Diverifikasi", match: ["diverifikasi"] },
  { key: "dikerjakan", label: "Dikerjakan", match: ["dikerjakan"] },
  { key: "selesai", label: "Selesai", match: ["selesai", "dikonfirmasi"] },
];
const LABEL = { dibuat: "Dibuat", diverifikasi: "Diverifikasi", dikerjakan: "Dikerjakan", selesai: "Selesai" };

function Card({ t, unit, technicians, onAdvance, onAssign }) {
  const next = TICKET_FLOW[TICKET_FLOW.indexOf(t.status) + 1];
  const last = t.history[t.history.length - 1];
  return (
    <article className="rounded-2xl border border-[color:var(--rdg-line)] bg-white p-3.5 shadow-sm" data-ticket={t.id}>
      <div className="flex flex-wrap items-center gap-1.5">
        <StatusChip tone="neutral" icon={null}>{t.kind === "tanya" ? "Pertanyaan" : t.kind === "garansi" ? "Garansi" : "Kerusakan"}</StatusChip>
        {t.status === "dikonfirmasi" && <StatusChip tone="ok">{`Dikonfirmasi · ${t.rating} dari 5`}</StatusChip>}
        {t.rating && t.status === "dikonfirmasi" && <Star size={14} className="text-[#b9741a]" aria-hidden="true" />}
      </div>
      <h3 className="mt-2 text-[15px] font-extrabold">{t.category}</h3>
      <p className="mt-0.5 text-[13.5px] leading-snug">{t.description}</p>
      <p className="mt-2 text-[12.5px] text-[color:var(--rdg-muted)]">{`${unit} · ${last ? tanggal(last.at) : ""}`}</p>
      {t.status !== "dikonfirmasi" && (
        <label className="mt-2 block text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">
          Teknisi
          <select className={`${FIELD} !min-h-[38px] !text-[13.5px]`} aria-label={`Teknisi untuk ${t.category}`} value={t.assignee || ""} onChange={(e) => onAssign(t.id, e.target.value)}>
            <option value="" disabled>Pilih teknisi</option>
            {technicians.map((n) => <option key={n} value={n}>{n}</option>)}
            {t.assignee && !technicians.includes(t.assignee) && <option value={t.assignee}>{t.assignee}</option>}
          </select>
        </label>
      )}
      {next && (
        <button type="button" className="rdg-btn-primary mt-3 !min-h-[38px] w-full !px-3 !text-[13.5px]" onClick={() => onAdvance(t.id)}>
          {`Majukan ke ${LABEL[next]}`} <ArrowRight size={15} aria-hidden="true" />
        </button>
      )}
    </article>
  );
}

/** K3: antrean tiket gaya kanban. Alur memakai care.advanceTicket (satu sumber). */
export default function TicketsAdmin() {
  const fetcher = useCallback(() => listTickets(), []);
  const { data, error } = useLoad(fetcher, ["care"]);
  const technicians = useProto((s) => s.manager.technicians) || ["Tim Teknik Estora"];
  const unit = useProto((s) => s.world.unit.block);
  const [err, setErr] = useState("");
  const act = (fn) => async (...a) => {
    try { await fn(...a); setErr(""); } catch (e) { setErr(e.message); }
  };
  return (
    <ManagerPage id="K3" title="Tiket dan keluhan" subtitle="Laporan warga masuk dari aplikasi. Majukan tiket agar warga ikut melihat perkembangannya.">
      {err && <p role="alert" className="text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{err}</p>}
      {!data && <Loading error={error} />}
      {data && (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {COLUMNS.map((c) => {
            const items = data.filter((t) => c.match.includes(t.status));
            return (
              <section key={c.key} aria-label={c.label} className="rounded-3xl bg-white/60 p-3 ring-1 ring-[color:var(--rdg-line)]">
                <h2 className="mb-3 flex items-center justify-between px-1 text-[15px] font-extrabold">
                  {c.label}
                  <span className="rounded-full bg-[#e7ffef] px-2.5 py-0.5 text-[13px] text-rdg-forest" aria-label={`${items.length} tiket`}>{items.length}</span>
                </h2>
                <div className="space-y-3">
                  {items.length === 0 && <p className="px-1 py-4 text-center text-[13.5px] text-[color:var(--rdg-muted)]">Kosong</p>}
                  {items.map((t) => <Card key={t.id} t={t} unit={unit} technicians={technicians} onAdvance={act(advanceTicket)} onAssign={act(assignTicket)} />)}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </ManagerPage>
  );
}
