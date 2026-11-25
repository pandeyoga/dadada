import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Megaphone, Pin, CalendarDays, MapPin, Store, Wrench } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import EmptyState from "../../../components/EmptyState";
import { GroupList } from "./Groups";
import { PollList } from "./Polls";
import { listAnnouncements, listEvents } from "../../../services/api/community";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const TABS = ["Pengumuman", "Agenda", "Hobi", "Polling"];
const fetchAll = () => Promise.all([listAnnouncements(), listEvents()]).then(([announcements, events]) => ({ announcements, events }));

/** W14: pusat komunitas (tab Pengumuman · Agenda · Hobi · Polling) + pintu ke pasar dan jasa. */
export default function Community() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["community"]);
  const [tab, setTab] = useState("Pengumuman");
  return (
    <Page id="W14" title="Komunitas" back="/app/warga" nav="resident">
      <div role="tablist" aria-label="Isi komunitas" className="grid grid-cols-4 gap-1 rounded-2xl bg-white/80 p-1 shadow-sm">
        {TABS.map((t) => (
          <button
            key={t} type="button" role="tab" id={`w14-tab-${t}`} aria-selected={tab === t} aria-controls="w14-panel"
            onClick={() => setTab(t)}
            className={`min-h-[44px] rounded-xl px-0.5 text-[12.5px] font-bold ${tab === t ? "bg-rdg-forest text-white" : "text-rdg-ink900"}`}
          >
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="w14-panel" aria-labelledby={`w14-tab-${tab}`} className="space-y-3">
        {!data && tab !== "Hobi" && tab !== "Polling" && <Loading error={error} />}
        {data && tab === "Pengumuman" && (data.announcements.length ? data.announcements.map((a) => (
          <FrostCard key={a.id} className="space-y-1">
            <p className="flex items-center gap-2 text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">
              <Megaphone size={15} aria-hidden="true" /> {`${a.author} · ${tanggal(a.at)}`}
              {a.pinned && <StatusChip tone="info" icon={Pin}>Disematkan</StatusChip>}
            </p>
            <h2 className="text-[16px] font-extrabold leading-snug">{a.title}</h2>
            <p className="text-[14px] leading-relaxed text-[color:var(--rdg-muted)]">{a.body}</p>
          </FrostCard>
        )) : <EmptyState icon={Megaphone} title="Belum ada pengumuman" body="Pengumuman dari pengelola muncul di sini." />)}
        {data && tab === "Agenda" && (data.events.length ? (
          <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
            {data.events.map((e) => (
              <ListRow
                key={e.id} icon={CalendarDays} to={`/app/warga/komunitas/event/${e.id}`} title={e.title}
                subtitle={`${tanggal(e.date)} · ${e.time} · ${e.place}`}
                right={e.rsvp ? <StatusChip tone="ok">Ikut</StatusChip> : <span className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">{`${e.going} ikut`}</span>}
              />
            ))}
          </FrostCard>
        ) : <EmptyState icon={MapPin} title="Belum ada acara" />)}
        {tab === "Hobi" && <GroupList />}
        {tab === "Polling" && <PollList />}
      </div>
      <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
        <ListRow icon={Store} title="Pasar warga" subtitle="Jual beli antar tetangga" to="/app/warga/pasar" />
        <ListRow icon={Wrench} title="Jasa rumah" subtitle="Tukang, kebersihan, galon, dan lainnya" to="/app/warga/jasa" />
      </FrostCard>
      <p className="flex justify-center gap-4 text-[14px] font-bold text-rdg-forest">
        <Link to="/app/warga/komunitas/hobi">Halaman grup hobi</Link>
        <Link to="/app/warga/komunitas/polling">Halaman polling</Link>
      </p>
    </Page>
  );
}
