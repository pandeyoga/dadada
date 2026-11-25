import React, { useCallback, useState } from "react";
import { Wrench, Star, CalendarCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import Sheet from "../../../components/Sheet";
import { Msg, Field, FIELD } from "../security/ui";
import { listServices, listBookings, bookService, SERVICE_SLOTS } from "../../../services/api/community";
import { now } from "../../../services/store";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const fetchAll = () => Promise.all([listServices(), listBookings()]).then(([services, bookings]) => ({ services, bookings }));
const tomorrow = () => new Date(now() + 86400000).toISOString().slice(0, 10);

function BookingForm({ service, onDone }) {
  const [date, setDate] = useState(tomorrow());
  const [slot, setSlot] = useState("");
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setProblem("");
    try { await bookService({ serviceId: service.id, date, slot, note }); onDone(); } catch (err) { setProblem(err.message); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <p className="text-[14px] text-[color:var(--rdg-muted)]">{`${service.provider} · ${service.price}`}</p>
      <Field id="w19-tgl" label="Tanggal">
        <input id="w19-tgl" type="date" min={tomorrow()} value={date} onChange={(e) => setDate(e.target.value)} className={FIELD} />
      </Field>
      <fieldset>
        <legend className="mb-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">Jam kedatangan</legend>
        <div className="grid grid-cols-2 gap-2">
          {SERVICE_SLOTS.map((s) => (
            <button key={s} type="button" aria-pressed={slot === s} onClick={() => setSlot(s)}
              className={`rdg-btn-ghost ${slot === s ? "!border-rdg-forest !bg-[#e7ffef] font-extrabold" : ""}`}>{s}</button>
          ))}
        </div>
      </fieldset>
      <Field id="w19-cat" label="Catatan (opsional)">
        <textarea id="w19-cat" rows={2} value={note} onChange={(e) => setNote(e.target.value)} className={`${FIELD} py-2`} placeholder="Contoh: AC kamar utama kurang dingin" />
      </Field>
      <Msg error={problem} />
      <button type="submit" className="rdg-btn-primary w-full">Pesan jadwal</button>
      <p className="text-[12.5px] text-[color:var(--rdg-muted)]">Biaya dibayar langsung ke penyedia jasa setelah pekerjaan selesai.</p>
    </form>
  );
}

/** W19: jasa rumah dari tetangga — pilih jasa, jadwal, lalu lihat pesanan saya. */
export default function HomeServices() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["community"]);
  const [target, setTarget] = useState(null);
  return (
    <Page id="W19" title="Jasa rumah" back="/app/warga/komunitas" nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <section aria-labelledby="w19-pesanan" className="space-y-2">
            <h2 id="w19-pesanan" className="text-[16px] font-extrabold">Pesanan jasa saya</h2>
            {data.bookings.length === 0 ? (
              <p className="text-[14px] text-[color:var(--rdg-muted)]">Belum ada pesanan. Pilih jasa di bawah untuk membuat jadwal.</p>
            ) : (
              <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
                {data.bookings.map((b) => (
                  <ListRow key={b.id} icon={CalendarCheck} title={`${b.serviceName} · ${b.provider}`} subtitle={`${tanggal(b.date)} · ${b.slot}${b.note ? ` · ${b.note}` : ""}`} right={<StatusChip tone="info">Dijadwalkan</StatusChip>} />
                ))}
              </FrostCard>
            )}
          </section>
          <section aria-labelledby="w19-daftar" className="space-y-2">
            <h2 id="w19-daftar" className="text-[16px] font-extrabold">Pilih jasa</h2>
            {data.services.map((s) => (
              <FrostCard key={s.id} className="flex items-center gap-3">
                <span className="rdg-row-icon"><Wrench size={20} aria-hidden="true" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-bold">{s.name}</span>
                  <span className="block text-[13px] text-[color:var(--rdg-muted)]">{`${s.provider} · ${s.price}`}</span>
                  <span className="flex items-center gap-1 text-[12.5px] font-semibold text-[color:var(--rdg-muted)]"><Star size={13} aria-hidden="true" /> {s.rating}</span>
                </span>
                <button type="button" className="rdg-btn-ghost !min-h-[44px] !px-3" aria-label={`Pesan ${s.name}`} onClick={() => setTarget(s)}>Pesan</button>
              </FrostCard>
            ))}
          </section>
        </>
      )}
      <Sheet open={Boolean(target)} onClose={() => setTarget(null)} title={target ? `Pesan ${target.name}` : "Pesan jasa"}>
        {target && <BookingForm service={target} onDone={() => setTarget(null)} />}
      </Sheet>
    </Page>
  );
}
