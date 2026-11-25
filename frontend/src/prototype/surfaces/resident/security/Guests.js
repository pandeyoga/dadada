import React, { useMemo, useState } from "react";
import { QrCode, Share2, Ban, UserPlus } from "lucide-react";
import { FrostCard } from "../../../components/GlassCard";
import QrPattern from "../../../components/QrPattern";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import EmptyState from "../../../components/EmptyState";
import { createGuestPass, guestPassStatus, revokeGuestPass } from "../../../services/api/security";
import { now } from "../../../services/store";
import { useNow, useProto } from "../../../services/useStore";
import { tanggal } from "../../../lib/format";
import Page from "../../buyer/Page";
import { FIELD, Field, Msg, rentangJam, wibDay } from "./ui";

const TONE = { active: ["ok", "Aktif"], used: ["info", "Sudah dipakai"], expired: ["neutral", "Kedaluwarsa"], revoked: ["neutral", "Dicabut"] };

const waLink = (p, world) => `https://wa.me/?text=${encodeURIComponent(
  `Halo ${p.guestName}, Anda diundang ke ${world.project.name} Blok ${world.unit.block} pada ${tanggal(p.date)} pukul ${rentangJam(p)} WIB. Tunjukkan kode ${p.code} ke satpam.`
)}`;

const hh = (h) => `${String(h).padStart(2, "0")}:00`;

/** Jendela bawaan: dari jam berikutnya selama 3 jam; lewat tengah malam → besok 09.00–17.00. */
function defaultWindow(t) {
  const hour = (new Date(t).getUTCHours() + 7) % 24;
  if (hour >= 20) return { date: wibDay(t + 86400000), from: "09:00", to: "17:00" };
  return { date: wibDay(t), from: hh(hour + 1), to: hh(hour + 4) };
}

function PassCard({ pass, status }) {
  const world = useProto((s) => s.world);
  return (
    <FrostCard className="text-center">
      <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Undangan untuk {pass.guestName}</p>
      <div className="mx-auto mt-3 w-[200px] rounded-2xl bg-white p-1 shadow-[var(--rdg-shadow-card)]">
        <QrPattern value={pass.code} label={`QR undangan ${pass.guestName}`} size={192} />
      </div>
      <p className="mt-3 text-[30px] font-extrabold tracking-[0.12em]">{pass.code}</p>
      <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{`${tanggal(pass.date)} · ${rentangJam(pass)} WIB · sekali pakai`}</p>
      {status === "active" ? (
        <a href={waLink(pass, world)} target="_blank" rel="noopener noreferrer" className="rdg-btn-primary mt-3 w-full"><Share2 size={17} aria-hidden="true" /> Kirim lewat WhatsApp</a>
      ) : (
        <p className="mt-3"><StatusChip tone={TONE[status][0]} icon={null}>{TONE[status][1]}</StatusChip></p>
      )}
    </FrostCard>
  );
}

function InviteForm({ onCreated }) {
  const [name, setName] = useState("");
  const [init] = useState(() => defaultWindow(now()));
  const [date, setDate] = useState(init.date);
  const [from, setFrom] = useState(init.from);
  const [to, setTo] = useState(init.to);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const p = await createGuestPass({ guestName: name, date, from, to });
      setName("");
      onCreated(p.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <FrostCard>
      <form onSubmit={submit} className="space-y-3">
        <h2 className="text-[17px] font-extrabold">Undang tamu</h2>
        <Field id="gp-name" label="Nama tamu"><input id="gp-name" className={FIELD} value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" placeholder="Mis. Pak Anto" /></Field>
        <Field id="gp-date" label="Tanggal"><input id="gp-date" type="date" className={FIELD} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field id="gp-from" label="Mulai"><input id="gp-from" type="time" className={FIELD} value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
          <Field id="gp-to" label="Sampai"><input id="gp-to" type="time" className={FIELD} value={to} onChange={(e) => setTo(e.target.value)} /></Field>
        </div>
        <Msg error={error} />
        <button type="submit" className="rdg-btn-primary w-full" disabled={busy}><UserPlus size={17} aria-hidden="true" /> Buat undangan</button>
      </form>
    </FrostCard>
  );
}

export default function Guests() {
  const passes = useProto((s) => s.security.guestPasses);
  const t = useNow(30000);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");
  const shown = useMemo(() => passes.find((p) => p.id === selected) || null, [passes, selected]);
  const revoke = async (id) => {
    setErr("");
    try { await revokeGuestPass(id); } catch (e) { setErr(e.message); }
  };
  return (
    <Page id="W7" title="Undang tamu" back="/app/warga/keamanan" nav="resident">
      {shown && <PassCard pass={shown} status={guestPassStatus(shown, t)} />}
      <InviteForm onCreated={setSelected} />
      <FrostCard>
        <h2 className="text-[17px] font-extrabold">Daftar undangan</h2>
        <Msg error={err} />
        {passes.length === 0 ? (
          <EmptyState icon={QrCode} title="Belum ada undangan" body="Buat undangan agar tamu bisa masuk lewat gerbang dengan QR." />
        ) : (
          <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
            {passes.map((p) => {
              const st = guestPassStatus(p, t);
              return (
                <li key={p.id}>
                  <ListRow
                    icon={QrCode} title={p.guestName} subtitle={`${tanggal(p.date)} · ${rentangJam(p)} · ${p.code}`}
                    right={<StatusChip tone={TONE[st][0]} icon={null}>{TONE[st][1]}</StatusChip>}
                  />
                  <div className="flex flex-wrap gap-2 pb-3 pl-[60px]">
                    <button type="button" className="rdg-btn-ghost !min-h-[40px] !px-4 !text-[13.5px]" onClick={() => setSelected(p.id)} aria-label={`Lihat QR ${p.guestName}`}>Lihat QR</button>
                    {st === "active" && (
                      <button type="button" className="rdg-btn-ghost !min-h-[40px] !px-4 !text-[13.5px]" onClick={() => revoke(p.id)} aria-label={`Cabut undangan ${p.guestName}`}><Ban size={15} aria-hidden="true" /> Cabut</button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </FrostCard>
    </Page>
  );
}
