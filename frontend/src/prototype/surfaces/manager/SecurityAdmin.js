import React, { useMemo } from "react";
import { Siren, ShieldCheck } from "lucide-react";
import ManagerPage, { Panel, Table, TH, TD } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { useProto, useNow } from "../../services/useStore";
import { activeSos, sosLabel } from "../../services/api/sos";
import { guardsOnDutyAt } from "../../services/api/resident";
import { tanggal, jam } from "../../lib/format";

const SOS_STATUS = {
  sent: ["danger", "Menunggu satpam"], accepted: ["warn", "Sedang ditangani"], resolved: ["ok", "Selesai"], cancelled: ["neutral", "Dibatalkan"],
};
const monthOf = (t) => new Date(t + 7 * 3600000).toISOString().slice(0, 7);
const stamp = (at) => `${tanggal(at)} · ${jam(at)}`;
const bare = (n) => String(n || "").trim().replace(/^pak\s+/i, "").toLowerCase();
/** Nama satpam seperti di W8/S2 ("Pak Joko"): dari data satpam bila ada, selain itu "Pak {nama}". */
const guardLabel = (guards, name) => {
  if (!bare(name)) return "satpam";
  const g = guards.find((x) => bare(x.name) === bare(name));
  return g ? g.name : `Pak ${String(name).trim().replace(/^pak\s+/i, "")}`;
};

/** K6: SOS bulan ini (hidup), satpam bertugas, log gerbang dan patroli. */
export default function SecurityAdmin() {
  const state = useProto((s) => s);
  const t = useNow(30000);
  const { security: sec, world } = state;
  const active = activeSos(state);
  const month = useMemo(() => sec.sos.filter((e) => monthOf(Date.parse(e.createdAt)) === monthOf(t)), [sec.sos, t]);
  const onDuty = guardsOnDutyAt(world, t).map((g) => g.id);
  return (
    <ManagerPage id="K6" title="Keamanan kawasan" subtitle="SOS warga masuk ke sini dan ke satpam pada saat yang sama.">
      {active ? (
        <div role="alert" className="flex items-center gap-4 rounded-2xl bg-[#c42f35] p-5 text-white">
          <Siren size={32} aria-hidden="true" />
          <div>
            <p className="text-[19px] font-extrabold">{`SOS ${sosLabel(active.type).toLowerCase()} dari ${active.unit}`}</p>
            <p className="text-[14.5px] text-white/95">{active.status === "sent" ? `Dikirim ${jam(Date.parse(active.createdAt))}. Belum diterima satpam.` : `Diterima ${guardLabel(world.guards, active.acceptedBy)}. Sedang ditangani.`}</p>
          </div>
        </div>
      ) : (
        <p role="status" className="flex items-center gap-2 rounded-2xl bg-[#e7ffef] p-4 text-[15px] font-bold text-rdg-forest"><ShieldCheck size={20} aria-hidden="true" /> Tidak ada SOS aktif</p>
      )}
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="SOS bulan ini">
          {month.length === 0 ? <p className="text-[14px] text-[color:var(--rdg-muted)]">Belum ada SOS bulan ini.</p> : (
            <Table label="SOS bulan ini">
              <thead><tr className="border-b border-[color:var(--rdg-line)]"><th className={TH}>Jenis</th><th className={TH}>Unit</th><th className={TH}>Waktu</th><th className={TH}>Status</th></tr></thead>
              <tbody>
                {month.map((e) => (
                  <tr key={e.id} className="border-b border-[color:var(--rdg-line)] last:border-0">
                    <td className={`${TD} font-bold`}>{sosLabel(e.type)}</td><td className={`${TD} whitespace-nowrap`}>{e.unit}</td><td className={TD}>{stamp(Date.parse(e.createdAt))}</td>
                    <td className={TD}><StatusChip tone={SOS_STATUS[e.status][0]}>{SOS_STATUS[e.status][1]}</StatusChip></td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Panel>
        <Panel title="Satpam bertugas">
          <ul className="divide-y divide-[color:var(--rdg-line)]">
            {world.guards.map((g) => (
              <li key={g.id} className="flex items-center justify-between gap-3 py-2.5 text-[14px]">
                <span><b>{g.name}</b><br /><span className="text-[13px] text-[color:var(--rdg-muted)]">{g.post || g.shift}</span></span>
                <StatusChip tone={onDuty.includes(g.id) ? "ok" : "neutral"}>{onDuty.includes(g.id) ? "Bertugas" : "Tidak bertugas"}</StatusChip>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Log gerbang">
          <ul className="divide-y divide-[color:var(--rdg-line)]">
            {sec.gateLog.slice(0, 6).map((l) => (
              <li key={l.id} className="flex justify-between gap-3 py-2 text-[14px]">
                <span><b>{l.name}</b> · {l.purpose}<br /><span className="text-[13px] text-[color:var(--rdg-muted)]">{l.plate ? `${l.plate} · ` : ""}{l.direction === "masuk" ? "Masuk" : "Keluar"}</span></span>
                <span className="flex-none text-[13px] text-[color:var(--rdg-muted)]">{stamp(Date.parse(l.at))}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Log patroli">
          <ul className="divide-y divide-[color:var(--rdg-line)]">
            {(sec.patrols || []).slice(0, 6).map((p) => (
              <li key={p.id} className="flex justify-between gap-3 py-2 text-[14px]">
                <span><b>{p.checkpoint}</b> · {p.by}<br /><span className="text-[13px] text-[color:var(--rdg-muted)]">{p.note}</span></span>
                <span className="flex-none text-[13px] text-[color:var(--rdg-muted)]">{stamp(Date.parse(p.at))}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </ManagerPage>
  );
}
