import React, { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import { CalendarDays, Clock, MapPin, Users, CircleCheck, CalendarX } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import EmptyState from "../../../components/EmptyState";
import { getEvent, joinEvent, leaveEvent } from "../../../services/api/community";
import { Msg } from "../security/ui";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

/** W15: detail acara dengan RSVP "Saya ikut" / "Batal ikut". */
export default function EventDetail() {
  const { id } = useParams();
  const fetcher = useCallback(() => getEvent(id).then((event) => ({ event })), [id]);
  const { data, error } = useLoad(fetcher, ["community"]);
  const ev = data && data.event;
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const toggle = async () => {
    setProblem(""); setBusy(true);
    try { await (ev.rsvp ? leaveEvent(id) : joinEvent(id)); } catch (e) { setProblem(e.message); } finally { setBusy(false); }
  };
  return (
    <Page id="W15" title="Detail acara" back="/app/warga/komunitas" nav="resident">
      {!data && <Loading error={error} />}
      {data && !ev && (
        <EmptyState icon={CalendarX} title="Acara tidak ditemukan" body="Acara ini mungkin sudah dihapus. Lihat agenda terbaru di Komunitas." />
      )}
      {ev && (
        <>
          <FrostCard className="space-y-2">
            <h2 className="text-[20px] font-extrabold leading-snug">{ev.title}</h2>
            <p className="flex items-center gap-2 text-[14px] text-[color:var(--rdg-muted)]"><CalendarDays size={16} aria-hidden="true" /> {tanggal(ev.date)}</p>
            <p className="flex items-center gap-2 text-[14px] text-[color:var(--rdg-muted)]"><Clock size={16} aria-hidden="true" /> {`${ev.time} WIB`}</p>
            <p className="flex items-center gap-2 text-[14px] text-[color:var(--rdg-muted)]"><MapPin size={16} aria-hidden="true" /> {ev.place}</p>
            <p className="pt-1 text-[15px] leading-relaxed">{ev.body}</p>
          </FrostCard>
          <FrostCard className="space-y-3">
            <p className="flex items-center gap-2 text-[15px] font-bold"><Users size={18} aria-hidden="true" /> {`${ev.going} warga ikut`}</p>
            {ev.rsvp && <p role="status" className="flex items-center gap-1.5 text-[13.5px] font-bold text-rdg-forest"><CircleCheck size={16} aria-hidden="true" /> Anda terdaftar hadir.</p>}
            <button type="button" disabled={busy} className={ev.rsvp ? "rdg-btn-ghost w-full" : "rdg-btn-primary w-full"} onClick={toggle}>
              {ev.rsvp ? "Batal ikut" : "Saya ikut"}
            </button>
            <Msg error={problem} />
          </FrostCard>
        </>
      )}
    </Page>
  );
}
