import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus, Users, Smartphone, BatteryLow, Phone, LogOut } from "lucide-react";
import Page, { Loading } from "../buyer/Page";
import { FrostCard } from "../../components/GlassCard";
import ListRow from "../../components/ListRow";
import StatusChip from "../../components/StatusChip";
import Sheet from "../../components/Sheet";
import { Msg, Field, FIELD } from "./security/ui";
import { listFamily, inviteFamily, listDevices, ACCESS_OPTIONS, ROLES } from "../../services/api/account";
import { logout } from "../../services/api/session";
import { useProto } from "../../services/useStore";
import useLoad from "../../lib/useLoad";

const fetchAll = () => Promise.all([listFamily(), listDevices()]).then(([family, devices]) => ({ family, devices }));
const accessLabel = (id) => (ACCESS_OPTIONS.find((o) => o.id === id) || { label: id }).label;
const SETTINGS = [
  { id: "darurat", label: "Darurat dan SOS", note: "Selalu aktif demi keselamatan", locked: true },
  { id: "keamanan", label: "Keamanan rumah", note: "Pintu, tamu, dan kamera" },
  { id: "tagihan", label: "Tagihan dan pembayaran", note: "Pengingat jatuh tempo" },
  { id: "komunitas", label: "Komunitas", note: "Pengumuman, event, dan polling" },
];

function InviteForm({ onDone }) {
  const [v, setV] = useState({ name: "", phone: "", role: "keluarga", access: ["pintu"] });
  const [problem, setProblem] = useState("");
  const toggle = (id) => setV((x) => ({ ...x, access: x.access.includes(id) ? x.access.filter((a) => a !== id) : [...x.access, id] }));
  const submit = async (e) => {
    e.preventDefault();
    setProblem("");
    try { await inviteFamily(v); onDone(); } catch (err) { setProblem(err.message); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <Field id="w28-nama" label="Nama"><input id="w28-nama" value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} className={FIELD} autoComplete="off" /></Field>
      <Field id="w28-wa" label="Nomor WhatsApp"><input id="w28-wa" inputMode="tel" value={v.phone} onChange={(e) => setV({ ...v, phone: e.target.value })} className={FIELD} placeholder="0812-3456-7890" /></Field>
      <Field id="w28-peran" label="Peran">
        <select id="w28-peran" value={v.role} onChange={(e) => setV({ ...v, role: e.target.value })} className={FIELD}>
          {Object.entries(ROLES).map(([id, l]) => <option key={id} value={id}>{l}</option>)}
        </select>
      </Field>
      <fieldset>
        <legend className="mb-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">Hak akses</legend>
        <div className="flex flex-wrap gap-2">
          {ACCESS_OPTIONS.map((o) => (
            <button key={o.id} type="button" aria-pressed={v.access.includes(o.id)} onClick={() => toggle(o.id)}
              className={`rdg-btn-ghost !min-h-[44px] !px-3 ${v.access.includes(o.id) ? "!border-rdg-forest !bg-[#e7ffef] font-extrabold" : ""}`}>{o.label}</button>
          ))}
        </div>
      </fieldset>
      <Msg error={problem} />
      <button type="submit" className="rdg-btn-primary w-full">Kirim undangan</button>
    </form>
  );
}

function Toggle({ on, onChange, label, disabled }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={() => onChange(!on)}
      className={`relative h-8 w-14 flex-none rounded-full transition-colors ${on ? "bg-rdg-forest" : "bg-[#9fb5b5]"} ${disabled ? "opacity-70" : ""}`}>
      <span className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-all ${on ? "left-7" : "left-1"}`} />
    </button>
  );
}

/** W28: akun warga — profil, keluarga dan penyewa, perangkat, kontak darurat, pengaturan, keluar. */
export default function ResidentAccount() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["care"]);
  const world = useProto((s) => s.world);
  const contacts = useProto((s) => s.security.contacts);
  const [invite, setInvite] = useState(false);
  const [prefs, setPrefs] = useState({ darurat: true, keamanan: true, tagihan: true, komunitas: false });
  const navigate = useNavigate();
  const initials = world.resident.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const out = () => { logout(); navigate("/app/demo"); };
  return (
    <Page id="W28" title="Akun saya" back="/app/warga" nav="resident" right={<StatusChip tone="info" icon={null}>Data contoh</StatusChip>}>
      <FrostCard>
        <div className="flex items-center gap-3">
          <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-rdg-lime text-[18px] font-extrabold text-rdg-ink900" aria-hidden="true">{initials}</span>
          <div className="min-w-0">
            <h2 className="text-[18px] font-extrabold">{world.resident.name}</h2>
            <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{`Blok ${world.unit.block} · ${world.project.name}`}</p>
            <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{world.resident.phone}</p>
          </div>
        </div>
      </FrostCard>

      {!data && <Loading error={error} />}
      {data && (
        <>
          <section aria-labelledby="w28-kel" className="space-y-2">
            <h2 id="w28-kel" className="text-[17px] font-extrabold">Keluarga dan penyewa</h2>
            <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
              {data.family.map((f) => (
                <div key={f.id} className="flex items-start gap-3 p-3">
                  <span className="rdg-row-icon"><Users size={20} aria-hidden="true" /></span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-semibold leading-snug">{f.name}</p>
                    <p className="text-[13px] text-[color:var(--rdg-muted)]">{`${f.relation}${f.phone ? ` · ${f.phone}` : ""}`}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {f.access.length ? f.access.map((a) => <StatusChip key={a} tone="ok" icon={null}>{accessLabel(a)}</StatusChip>) : <StatusChip tone="neutral" icon={null}>Tanpa akses</StatusChip>}
                    </div>
                  </div>
                </div>
              ))}
            </FrostCard>
            <button type="button" className="rdg-btn-ghost w-full" onClick={() => setInvite(true)}><UserPlus size={16} aria-hidden="true" /> Undang anggota</button>
          </section>

          <section aria-labelledby="w28-dev" className="space-y-2">
            <h2 id="w28-dev" className="text-[17px] font-extrabold">Perangkat terhubung</h2>
            <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
              {data.devices.map((d) => (
                <ListRow key={d.id} icon={Smartphone} title={d.name} subtitle={d.battery != null ? `Baterai ${d.battery} %` : "Daya dari listrik rumah"}
                  right={d.battery != null && d.battery < 20 ? <StatusChip tone="warn" icon={BatteryLow}>Baterai rendah</StatusChip> : <StatusChip tone={d.status === "online" ? "ok" : "danger"}>{d.status === "online" ? "Terhubung" : "Terputus"}</StatusChip>} />
              ))}
            </FrostCard>
          </section>
        </>
      )}

      <FrostCard className="!p-1">
        <ListRow icon={Phone} title="Kontak darurat" subtitle={`${contacts.length} kontak tersimpan`} to="/app/warga/sos/kontak" />
      </FrostCard>

      <section aria-labelledby="w28-set" className="space-y-2">
        <h2 id="w28-set" className="text-[17px] font-extrabold">Pengaturan notifikasi</h2>
        <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
          {SETTINGS.map((s) => (
            <div key={s.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0"><p className="text-[15px] font-semibold">{s.label}</p><p className="text-[13px] text-[color:var(--rdg-muted)]">{s.note}</p></div>
              <Toggle on={prefs[s.id]} disabled={s.locked} label={s.label} onChange={(x) => setPrefs((p) => ({ ...p, [s.id]: x }))} />
            </div>
          ))}
        </FrostCard>
      </section>

      <button type="button" className="rdg-btn-ghost w-full !text-[color:var(--rdg-sos-ink)]" onClick={out}><LogOut size={17} aria-hidden="true" /> Keluar</button>

      <Sheet open={invite} onClose={() => setInvite(false)} title="Undang anggota">
        <InviteForm onDone={() => setInvite(false)} />
      </Sheet>
    </Page>
  );
}
