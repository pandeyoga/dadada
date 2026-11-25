import React, { useCallback, useState } from "react";
import { Trophy, Landmark, Users, TreePine, CalendarCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import Sheet from "../../../components/Sheet";
import { Msg, Field, FIELD } from "../security/ui";
import { listFacilities, bookFacility } from "../../../services/api/care";
import { now } from "../../../services/store";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const ICONS = { "facility/lapangan": Trophy, "facility/musala": Landmark, "facility/balai": Users, "facility/taman": TreePine };
const fetchAll = () => listFacilities();
const tomorrow = () => new Date(now() + 86400000).toISOString().slice(0, 10);

function BookingForm({ facility, onDone }) {
  const [date, setDate] = useState(tomorrow());
  const [slot, setSlot] = useState("");
  const [problem, setProblem] = useState("");
  const taken = new Set(facility.bookings.filter((b) => b.date === date).map((b) => b.slot));
  const submit = async (e) => {
    e.preventDefault();
    setProblem("");
    try { await bookFacility({ facilityId: facility.id, date, slot }); onDone(); } catch (err) { setProblem(err.message); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <p className="text-[14px] text-[color:var(--rdg-muted)]">{`${facility.about} Biaya ${facility.fee}.`}</p>
      <Field id="w25-tgl" label="Tanggal">
        <input id="w25-tgl" type="date" min={tomorrow()} value={date} onChange={(e) => { setDate(e.target.value); setSlot(""); }} className={FIELD} />
      </Field>
      <fieldset>
        <legend className="mb-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">Pilih jam (jam yang pudar sudah dipesan)</legend>
        <div className="grid grid-cols-3 gap-2">
          {facility.slots.map((s) => (
            <button key={s} type="button" disabled={taken.has(s)} aria-pressed={slot === s} onClick={() => setSlot(s)}
              className={`rdg-btn-ghost !px-2 ${slot === s ? "!border-rdg-forest !bg-[#e7ffef] font-extrabold" : ""}`}>
              {s}
              {taken.has(s) && <span aria-hidden="true" className="ml-1 text-[11px] font-semibold">Terisi</span>}
            </button>
          ))}
        </div>
      </fieldset>
      <Msg error={problem} />
      <button type="submit" className="rdg-btn-primary w-full">Pesan jam</button>
    </form>
  );
}

/** W25: booking fasilitas bersama (lapangan, musala, balai warga). */
export default function Facilities() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["care", "community"]);
  const [target, setTarget] = useState(null);
  const mine = data ? data.flatMap((f) => f.bookings.map((b) => ({ ...b, name: f.name }))).sort((a, b) => a.date.localeCompare(b.date)) : [];
  return (
    <Page id="W25" title="Booking fasilitas" back="/app/warga/layanan" nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <>
          {mine.length > 0 && (
            <section aria-labelledby="w25-saya" className="space-y-2">
              <h2 id="w25-saya" className="text-[16px] font-extrabold">Pesanan saya</h2>
              <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
                {mine.map((b) => <ListRow key={b.id} icon={CalendarCheck} title={b.name} subtitle={`${tanggal(b.date)} · ${b.slot}`} right={<StatusChip tone="ok">Dikonfirmasi</StatusChip>} />)}
              </FrostCard>
            </section>
          )}
          <section aria-labelledby="w25-daftar" className="space-y-2">
            <h2 id="w25-daftar" className="text-[16px] font-extrabold">Pilih fasilitas</h2>
            {data.map((f) => {
              const Icon = ICONS[f.img] || Users;
              return (
                <FrostCard key={f.id} className="flex items-center gap-3">
                  <span className="rdg-row-icon"><Icon size={20} aria-hidden="true" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-bold">{f.name}</span>
                    <span className="block text-[13px] text-[color:var(--rdg-muted)]">{f.about}</span>
                    <span className="block text-[13px] font-semibold">{f.fee}</span>
                  </span>
                  {f.slots.length > 0
                    ? <button type="button" className="rdg-btn-ghost !min-h-[44px] !px-3 flex-none" aria-label={`Pesan ${f.name}`} onClick={() => setTarget(f)}>Pesan</button>
                    : <StatusChip tone="neutral" icon={null}>Tanpa pesanan</StatusChip>}
                </FrostCard>
              );
            })}
          </section>
        </>
      )}
      <Sheet open={Boolean(target)} onClose={() => setTarget(null)} title={target ? `Pesan ${target.name}` : "Pesan fasilitas"}>
        {target && <BookingForm facility={data.find((f) => f.id === target.id) || target} onDone={() => setTarget(null)} />}
      </Sheet>
    </Page>
  );
}
