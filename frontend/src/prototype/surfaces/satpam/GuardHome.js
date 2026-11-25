import React from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ScanQrCode, Cctv, Route, UserCheck } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import ScreenHeader from "../../components/ScreenHeader";
import StatusChip from "../../components/StatusChip";
import { guestPassStatus } from "../../services/api/security";
import { useNow, useProto } from "../../services/useStore";
import { wibDay } from "../resident/security/ui";
import useActiveSos from "./useActiveSos";
import SosCard from "./SosCard";

const LINKS = [
  { to: "/app/satpam/tamu", label: "Pindai tamu", icon: ScanQrCode },
  { to: "/app/satpam/cctv", label: "CCTV", icon: Cctv },
  { to: "/app/satpam/patroli", label: "Patroli", icon: Route },
];

export default function GuardHome() {
  const world = useProto((s) => s.world);
  const passes = useProto((s) => s.security.guestPasses);
  const event = useActiveSos();
  const t = useNow(30000);
  const me = world.guards.find((g) => g.id === "g-4") || { name: "Pak Joko", post: "Pos gerbang utama" };
  const today = passes.filter((p) => p.date === wibDay(t));
  const waiting = today.filter((p) => guestPassStatus(p, t) === "active").length;
  const used = today.filter((p) => p.status === "used").length;
  return (
    <MobileShell nav="satpam">
      <Screen id="S1">
        <Hero className="pb-6">
          <ScreenHeader title="Pos satpam" />
          <GlassCard className="flex items-center gap-3.5">
            <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime"><ShieldCheck size={28} aria-hidden="true" /></span>
            <div className="min-w-0">
              <h2 className="text-[20px] font-extrabold leading-tight">Pak Joko</h2>
              <p className="text-[13px] text-white/90">{me.post || "Pos gerbang utama"}</p>
              <p className="mt-1.5"><StatusChip tone="ok" icon={null}>Bertugas</StatusChip></p>
            </div>
          </GlassCard>
        </Hero>
        <div className="space-y-4 px-5 pb-6 pt-5">
          {event ? (
            <SosCard event={event} />
          ) : (
            <FrostCard className="flex items-center gap-3">
              <span className="rdg-row-icon"><ShieldCheck size={20} aria-hidden="true" /></span>
              <div>
                <p className="text-[15px] font-bold">Tidak ada laporan darurat</p>
                <p className="text-[13px] text-[color:var(--rdg-muted)]">Laporan SOS warga akan muncul di sini langsung.</p>
              </div>
            </FrostCard>
          )}
          <FrostCard>
            <h2 className="flex items-center gap-2 text-[17px] font-extrabold"><UserCheck size={18} aria-hidden="true" /> Tamu hari ini</h2>
            <div className="mt-2 grid grid-cols-2 gap-2.5 text-center">
              <div className="rounded-2xl bg-white p-3"><p className="text-[26px] font-extrabold leading-none">{waiting}</p><p className="mt-1 text-[13px] text-[color:var(--rdg-muted)]">Menunggu masuk</p></div>
              <div className="rounded-2xl bg-white p-3"><p className="text-[26px] font-extrabold leading-none">{used}</p><p className="mt-1 text-[13px] text-[color:var(--rdg-muted)]">Sudah masuk</p></div>
            </div>
          </FrostCard>
          <div className="grid grid-cols-3 gap-2.5">
            {LINKS.map((l) => (
              <Link key={l.to} to={l.to} className="rdg-btn-ghost flex-col !gap-1 !px-1 !py-3 !text-[13.5px]"><l.icon size={20} aria-hidden="true" />{l.label}</Link>
            ))}
          </div>
        </div>
      </Screen>
    </MobileShell>
  );
}
