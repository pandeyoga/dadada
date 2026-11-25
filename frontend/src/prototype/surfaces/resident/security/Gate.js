import React, { useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, MapPin, MapPinOff } from "lucide-react";
import { FrostCard } from "../../../components/GlassCard";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import { openGate } from "../../../services/api/security";
import { setLocation } from "../../../services/api/session";
import { useNow, useProto } from "../../../services/useStore";
import { kapan } from "../../../lib/format";
import Page from "../../buyer/Page";
import { Msg } from "./ui";

export default function Gate() {
  const location = useProto((s) => s.location);
  const log = useProto((s) => s.security.gateLog);
  const t = useNow(60000);
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const inside = location !== "outside";
  const go = async (direction) => {
    setBusy(true);
    setMsg({});
    try {
      await openGate(direction);
      setMsg({ ok: `Gerbang ${direction} dibuka` });
    } catch (e) {
      setMsg({ error: e.message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <Page id="W6" title="Gerbang pintar" back="/app/warga/keamanan" nav="resident">
      <FrostCard>
        <div className="flex items-start gap-3">
          <span className="rdg-row-icon">{inside ? <MapPin size={20} aria-hidden="true" /> : <MapPinOff size={20} aria-hidden="true" />}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
              <h2 className="text-[16px] font-extrabold">Cek lokasi</h2>
              <StatusChip tone={inside ? "ok" : "danger"}>{inside ? "Di dalam area" : "Di luar area"}</StatusChip>
            </div>
            <p className="mt-0.5 text-[13.5px] text-[color:var(--rdg-muted)]">{inside ? "Anda berada di dalam radius gerbang (100 m)." : "Anda berada di luar radius gerbang (100 m)."}</p>
          </div>
        </div>
        <div role="group" aria-label="Simulasi lokasi" className="mt-3 rounded-2xl bg-[#eef6f3] p-3">
          <p className="mb-2 text-[12.5px] font-bold uppercase tracking-wide text-[color:var(--rdg-muted)]">Simulasi lokasi (untuk demo)</p>
          <div className="rdg-seg rdg-seg--light">
            <button type="button" aria-pressed={inside} className={inside ? "is-on" : ""} onClick={() => setLocation("inside")}>Di dalam area</button>
            <button type="button" aria-pressed={!inside} className={!inside ? "is-on" : ""} onClick={() => setLocation("outside")}>Di luar area</button>
          </div>
        </div>
      </FrostCard>
      <FrostCard className="space-y-3">
        <h2 className="text-[16px] font-extrabold">Buka gerbang</h2>
        <div className="grid gap-2.5">
          <button type="button" className="rdg-btn-primary" disabled={busy} onClick={() => go("masuk")}><ArrowDownToLine size={17} aria-hidden="true" /> Buka gerbang masuk</button>
          <button type="button" className="rdg-btn-primary" disabled={busy} onClick={() => go("keluar")}><ArrowUpFromLine size={17} aria-hidden="true" /> Buka gerbang keluar</button>
        </div>
        <Msg error={msg.error} ok={msg.ok} />
      </FrostCard>
      <FrostCard>
        <h2 className="text-[16px] font-extrabold">Riwayat gerbang</h2>
        <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
          {log.slice(0, 6).map((e) => (
            <li key={e.id}>
              <ListRow
                icon={e.direction === "masuk" ? ArrowDownToLine : ArrowUpFromLine}
                title={`${e.name} · ${e.direction}`}
                subtitle={`${e.purpose} · ${e.plate} · ${kapan(e.at, t)}`}
              />
            </li>
          ))}
        </ul>
      </FrostCard>
    </Page>
  );
}
