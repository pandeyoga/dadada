import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { ReceiptText, Wrench, Siren, Home, ChevronRight } from "lucide-react";
import ManagerPage, { Panel } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { useProto } from "../../services/useStore";
import { getManagerSummary, iplOverview } from "../../services/api/manager";
import { activeSos, sosLabel } from "../../services/api/sos";

function Stat({ icon: Icon, label, value, hint, tone }) {
  return (
    <div role="group" aria-label={label} className="rdg-frost !p-5">
      <span className={`inline-flex h-10 w-10 items-center justify-center rounded-2xl ${tone}`}><Icon size={20} aria-hidden="true" /></span>
      <p className="mt-3 text-[34px] font-extrabold leading-none text-rdg-ink900">{value}</p>
      <p className="mt-1.5 text-[14px] font-semibold">{label}</p>
      <p className="text-[13px] text-[color:var(--rdg-muted)]">{hint}</p>
    </div>
  );
}

/** K1: ringkasan kawasan (IPL, tiket, SOS, hunian) — ikut berubah langsung dari aksi warga. */
export default function ManagerHome() {
  const state = useProto((s) => s);
  const sum = useMemo(() => getManagerSummary(state), [state]);
  const ipl = useMemo(() => iplOverview(state), [state]);
  const sos = activeSos(state);
  const open = state.care.tickets.filter((t) => ["dibuat", "diverifikasi", "dikerjakan"].includes(t.status));
  const late = ipl.units.filter((u) => u.status !== "lunas");
  return (
    <ManagerPage id="K1" title="Ringkasan kawasan" subtitle={`Estora Residence · Tagihan IPL ${ipl.label}`}>
      {sos && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#c42f35] p-4 text-white">
          <p className="text-[15px] font-extrabold">{`SOS ${sosLabel(sos.type).toLowerCase()} dari ${sos.unit} sedang aktif`}</p>
          <Link to="/app/pengelola/keamanan" className="rounded-full bg-white px-4 py-2 text-[14px] font-bold text-[color:var(--rdg-sos-ink)] no-underline">Lihat keamanan</Link>
        </div>
      )}
      <section aria-label="Angka ringkasan" className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Stat icon={ReceiptText} label="Tagihan IPL lunas" value={`${sum.iplPaidPct}%`} hint={`${ipl.paid} dari ${ipl.total} unit`} tone="bg-[#e7ffef] text-rdg-forest" />
        <Stat icon={Wrench} label="Tiket terbuka" value={String(sum.openTickets)} hint="Belum selesai dikerjakan" tone="bg-[#e3f4fb] text-rdg-deep" />
        <Stat icon={Siren} label="SOS bulan ini" value={String(sum.sosThisMonth)} hint={sos ? "Ada yang masih aktif" : "Tidak ada yang aktif"} tone="bg-[#fdeaea] text-[color:var(--rdg-sos-ink)]" />
        <Stat icon={Home} label="Hunian" value={`${sum.occupancy}%`} hint={`${state.manager.occupancy ? state.manager.occupancy.occupied : ipl.total} dari ${ipl.total} unit berpenghuni`} tone="bg-[#eef8d8] text-rdg-forest" />
      </section>
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Perlu ditindaklanjuti" right={<Link to="/app/pengelola/tiket" className="text-[13.5px] font-bold text-rdg-forest">Semua tiket</Link>}>
          {open.length === 0 && <p className="text-[14px] text-[color:var(--rdg-muted)]">Tidak ada tiket terbuka.</p>}
          <ul className="divide-y divide-[color:var(--rdg-line)]">
            {open.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-[14.5px] font-bold">{t.category}</p>
                  <p className="truncate text-[13px] text-[color:var(--rdg-muted)]">{t.description}</p>
                </div>
                <StatusChip tone={t.status === "dibuat" ? "warn" : "info"}>{t.status === "dibuat" ? "Dibuat" : t.status === "diverifikasi" ? "Diverifikasi" : "Dikerjakan"}</StatusChip>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Iuran belum lunas" right={<Link to="/app/pengelola/ipl" className="inline-flex items-center gap-1 text-[13.5px] font-bold text-rdg-forest">Kelola tagihan <ChevronRight size={15} aria-hidden="true" /></Link>}>
          <ul className="divide-y divide-[color:var(--rdg-line)]">
            {late.slice(0, 5).map((u) => (
              <li key={u.block} className="flex items-center justify-between gap-3 py-2.5 text-[14px]">
                <span><b>{u.block}</b> · {u.owner}</span>
                <StatusChip tone={u.status === "terlambat" ? "danger" : "warn"}>{u.status === "terlambat" ? "Terlambat" : "Belum bayar"}</StatusChip>
              </li>
            ))}
          </ul>
          {late.length > 5 && <p className="mt-2 text-[13px] text-[color:var(--rdg-muted)]">{`dan ${late.length - 5} unit lain.`}</p>}
        </Panel>
      </div>
    </ManagerPage>
  );
}
