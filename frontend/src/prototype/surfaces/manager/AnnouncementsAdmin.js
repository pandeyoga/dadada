import React, { useCallback, useState } from "react";
import { Send } from "lucide-react";
import ManagerPage, { Panel, Loading, FIELD } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { postAnnouncement } from "../../services/api/manager";
import { listAnnouncements, listEvents } from "../../services/api/community";
import { tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const TIERS = [
  { id: "info", label: "Info biasa", tone: "info" },
  { id: "keamanan", label: "Keamanan", tone: "warn" },
  { id: "darurat", label: "Darurat", tone: "danger" },
];
const load = async () => ({ anns: await listAnnouncements(), events: await listEvents() });

/** K4: tulis pengumuman untuk warga + lihat agenda kawasan. */
export default function AnnouncementsAdmin() {
  const { data, error } = useLoad(useCallback(load, []), ["community"]);
  const [form, setForm] = useState({ title: "", body: "", tier: "info" });
  const [msg, setMsg] = useState({ ok: "", err: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await postAnnouncement(form);
      setForm({ title: "", body: "", tier: "info" });
      setMsg({ ok: "Pengumuman terkirim ke semua warga.", err: "" });
    } catch (x) { setMsg({ ok: "", err: x.message }); }
    setBusy(false);
  };
  return (
    <ManagerPage id="K4" title="Pengumuman dan agenda" subtitle="Pengumuman tampil di Komunitas warga dan masuk ke notifikasi sesuai jenjangnya.">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <Panel title="Tulis pengumuman">
          <form onSubmit={submit} noValidate className="space-y-3">
            <label className="block text-[13.5px] font-semibold">Judul<input className={FIELD} value={form.title} onChange={set("title")} autoComplete="off" /></label>
            <label className="block text-[13.5px] font-semibold">Isi pengumuman<textarea className={`${FIELD} min-h-[120px] py-2`} value={form.body} onChange={set("body")} /></label>
            <label className="block text-[13.5px] font-semibold">Jenjang
              <select className={FIELD} value={form.tier} onChange={set("tier")}>
                {TIERS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </label>
            <div aria-live="polite">
              {msg.err && <p role="alert" className="text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{msg.err}</p>}
              {msg.ok && <p role="status" className="text-[14px] font-semibold text-rdg-forest">{msg.ok}</p>}
            </div>
            <button type="submit" className="rdg-btn-primary" disabled={busy}><Send size={17} aria-hidden="true" /> Kirim pengumuman</button>
          </form>
        </Panel>
        <div className="space-y-5">
          {!data && <Loading error={error} />}
          {data && (
            <>
              <Panel title="Pengumuman terkirim">
                <ul className="divide-y divide-[color:var(--rdg-line)]">
                  {data.anns.map((a) => {
                    const t = TIERS.find((x) => x.id === a.tier);
                    return (
                      <li key={a.id} className="py-2.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-[14.5px] font-bold">{a.title}</h3>
                          {t && t.id !== "info" && <StatusChip tone={t.tone}>{t.label}</StatusChip>}
                        </div>
                        <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{a.body}</p>
                        <p className="mt-0.5 text-[12.5px] text-[color:var(--rdg-muted)]">{`${a.author} · ${tanggal(a.at)}`}</p>
                      </li>
                    );
                  })}
                </ul>
              </Panel>
              <Panel title="Agenda kawasan">
                <ul className="divide-y divide-[color:var(--rdg-line)]">
                  {data.events.map((e) => (
                    <li key={e.id} className="flex items-center justify-between gap-3 py-2.5 text-[14px]">
                      <span><b>{e.title}</b><br /><span className="text-[13px] text-[color:var(--rdg-muted)]">{`${tanggal(`${e.date}T00:00:00+07:00`)} · ${e.time} · ${e.place}`}</span></span>
                      <span className="flex-none text-[13px] font-semibold">{`${e.going} ikut`}</span>
                    </li>
                  ))}
                </ul>
              </Panel>
            </>
          )}
        </div>
      </div>
    </ManagerPage>
  );
}
