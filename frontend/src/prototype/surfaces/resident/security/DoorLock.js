import React, { useCallback, useMemo, useState } from "react";
import { KeyRound, Share2, Trash2 } from "lucide-react";
import MobileShell from "../../../components/MobileShell";
import Screen from "../../../components/Screen";
import Hero from "../../../components/Hero";
import { FrostCard } from "../../../components/GlassCard";
import ScreenHeader from "../../../components/ScreenHeader";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import { createAccessCode, revokeAccessCode } from "../../../services/api/security";
import { useNow, useProto } from "../../../services/useStore";
import { tanggal } from "../../../lib/format";
import useDoor from "./useDoor";
import DoorCard from "./DoorCard";
import DoorLog from "./DoorLog";
import { FIELD, Field, Msg, byRecent } from "./ui";

const DURATIONS = [
  { id: "1j", label: "1 jam", ms: 3600000 },
  { id: "1h", label: "1 hari", ms: 86400000 },
  { id: "7h", label: "7 hari", ms: 7 * 86400000 },
  { id: "30h", label: "30 hari", ms: 30 * 86400000 },
];

const waLink = (c, block) => `https://wa.me/?text=${encodeURIComponent(`Kode akses pintu rumah ${block} untuk ${c.label}: ${c.pin}. Berlaku hingga ${tanggal(c.validUntil)}.`)}`;

function CodeForm({ t }) {
  const [label, setLabel] = useState("");
  const [dur, setDur] = useState("1h");
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMsg({});
    try {
      const ms = DURATIONS.find((d) => d.id === dur).ms;
      const c = await createAccessCode({ label, validUntil: t + ms });
      setLabel("");
      setMsg({ ok: `Kode ${c.pin} untuk ${c.label} sudah dibuat` });
    } catch (err) {
      setMsg({ error: err.message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="mt-3 space-y-3 border-t border-[color:var(--rdg-line)] pt-3">
      <h3 className="text-[15px] font-extrabold">Buat kode baru</h3>
      <Field id="ac-label" label="Untuk siapa">
        <input id="ac-label" className={FIELD} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Mis. Tukang AC" autoComplete="off" />
      </Field>
      <Field id="ac-dur" label="Berlaku selama">
        <select id="ac-dur" className={FIELD} value={dur} onChange={(e) => setDur(e.target.value)}>
          {DURATIONS.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
        </select>
      </Field>
      <Msg error={msg.error} ok={msg.ok} />
      <button type="submit" className="rdg-btn-primary w-full" disabled={busy}><KeyRound size={17} aria-hidden="true" /> Buat kode</button>
    </form>
  );
}

export default function DoorLock() {
  const door = useDoor();
  const codes = useProto((s) => s.security.accessCodes);
  const log = useProto((s) => s.security.doorLog);
  const block = useProto((s) => s.world.unit.block);
  const t = useNow(30000);
  const recent = useMemo(() => byRecent(log).slice(0, 8), [log]);
  const [err, setErr] = useState("");
  const revoke = useCallback(async (id) => {
    setErr("");
    try { await revokeAccessCode(id); } catch (e) { setErr(e.message); }
  }, []);
  const stateOf = (c) => (c.revoked ? ["neutral", "Dicabut"] : Date.parse(c.validUntil) <= t ? ["neutral", "Kedaluwarsa"] : ["ok", "Aktif"]);
  return (
    <MobileShell nav="resident">
      <Screen id="W3">
        <Hero className="pb-8">
          <ScreenHeader title="Kunci pintu" back="/app/warga/keamanan" />
          <DoorCard door={door} />
        </Hero>
        <div className="space-y-4 px-5 pt-5">
          <FrostCard>
            <h2 className="text-[17px] font-extrabold">Kode akses sementara</h2>
            <p className="text-[13.5px] text-[color:var(--rdg-muted)]">PIN 4 digit untuk ART, tukang, atau keluarga. Bisa dicabut kapan saja.</p>
            <ul className="mt-2 divide-y divide-[color:var(--rdg-line)]">
              {codes.map((c) => {
                const [tone, word] = stateOf(c);
                return (
                  <li key={c.id}>
                    <ListRow
                      icon={KeyRound}
                      title={c.label}
                      subtitle={<>PIN <b className="tracking-[0.12em]">{c.pin}</b> · sampai {tanggal(c.validUntil)}</>}
                      right={<StatusChip tone={tone} icon={null}>{word}</StatusChip>}
                    />
                    {word === "Aktif" && (
                      <div className="flex flex-wrap gap-2 pb-3 pl-[60px]">
                        <a href={waLink(c, block)} target="_blank" rel="noopener noreferrer" className="rdg-btn-ghost !min-h-[40px] !px-4 !text-[13.5px]"><Share2 size={15} aria-hidden="true" /> WhatsApp</a>
                        <button type="button" className="rdg-btn-ghost !min-h-[40px] !px-4 !text-[13.5px]" onClick={() => revoke(c.id)} aria-label={`Cabut kode ${c.label}`}><Trash2 size={15} aria-hidden="true" /> Cabut</button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {!codes.length && <p className="py-3 text-[14px] text-[color:var(--rdg-muted)]">Belum ada kode akses.</p>}
            <Msg error={err} />
            <CodeForm t={t} />
          </FrostCard>
          <FrostCard>
            <h2 className="text-[17px] font-extrabold">Riwayat akses</h2>
            <DoorLog entries={recent} />
          </FrostCard>
        </div>
      </Screen>
    </MobileShell>
  );
}
