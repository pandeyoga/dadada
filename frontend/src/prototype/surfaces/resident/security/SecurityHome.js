import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, QrCode, Video, Cctv, ChevronRight } from "lucide-react";
import MobileShell from "../../../components/MobileShell";
import Screen from "../../../components/Screen";
import Hero from "../../../components/Hero";
import { GlassCard, FrostCard } from "../../../components/GlassCard";
import ScreenHeader from "../../../components/ScreenHeader";
import CameraView from "../../../components/CameraView";
import ListRow from "../../../components/ListRow";
import { guardsOnDutyAt } from "../../../services/api/resident";
import { guestPassStatus } from "../../../services/api/security";
import { useNow, useProto } from "../../../services/useStore";
import useDoor from "./useDoor";
import DoorCard from "./DoorCard";
import DoorLog from "./DoorLog";
import AreaCameras from "./AreaCameras";
import { byRecent, wibDay } from "./ui";

const TABS = ["Rumah", "Kawasan"];

function Tabs({ tab, onChange }) {
  return (
    <div role="tablist" aria-label="Lokasi pantauan" className="rdg-seg mb-4">
      {TABS.map((name) => (
        <button
          key={name} role="tab" type="button" id={`sec-tab-${name}`} aria-selected={tab === name}
          aria-controls="sec-panel" onClick={() => onChange(name)}
          className={tab === name ? "is-on" : ""}
        >
          {name}
        </button>
      ))}
    </div>
  );
}

function HomePanel() {
  const security = useProto((s) => s.security);
  const t = useNow(60000);
  const today = useMemo(() => byRecent(security.doorLog).filter((e) => wibDay(e.at) === wibDay(t)).slice(0, 4), [security.doorLog, t]);
  const codes = security.accessCodes.filter((c) => !c.revoked && Date.parse(c.validUntil) > t);
  const passes = security.guestPasses.filter((p) => guestPassStatus(p, t) === "active");
  return (
    <>
      <FrostCard className="!p-3">
        <div className="overflow-hidden rounded-2xl"><CameraView cameraId="home-teras" label="Teras depan" /></div>
        <Link to="/app/warga/keamanan/cctv-rumah" className="mt-2 flex items-center justify-between px-1 text-[14px] font-bold text-rdg-forest">
          <span className="flex items-center gap-2"><Video size={17} aria-hidden="true" /> Semua kamera rumah ({security.cameras.home})</span>
          <ChevronRight size={18} aria-hidden="true" />
        </Link>
      </FrostCard>
      <FrostCard>
        <h2 className="text-[17px] font-extrabold">Kode tamu</h2>
        <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
          <li><ListRow icon={KeyRound} title={`${codes.length} kode akses aktif`} subtitle="PIN sementara untuk ART atau tukang" to="/app/warga/keamanan/kunci" /></li>
          <li><ListRow icon={QrCode} title={`${passes.length} undangan tamu aktif`} subtitle="QR sekali pakai untuk tamu" to="/app/warga/keamanan/tamu" /></li>
        </ul>
      </FrostCard>
      <FrostCard>
        <h2 className="text-[17px] font-extrabold">Riwayat hari ini</h2>
        <DoorLog entries={today} />
        <Link to="/app/warga/keamanan/kunci" className="mt-1 inline-block text-[14px] font-bold text-rdg-forest">Lihat semua riwayat</Link>
      </FrostCard>
    </>
  );
}

export default function SecurityHome() {
  const [tab, setTab] = useState("Rumah");
  const door = useDoor();
  const world = useProto((s) => s.world);
  const cameras = useProto((s) => s.security.cameras);
  const t = useNow(60000);
  const guards = guardsOnDutyAt(world, t).length;
  return (
    <MobileShell nav="resident">
      <Screen id="W2">
        <Hero className="pb-8">
          <ScreenHeader title="Keamanan" back="/app/warga" />
          <Tabs tab={tab} onChange={setTab} />
          {tab === "Rumah" ? (
            <DoorCard door={door} />
          ) : (
            <GlassCard className="flex items-center gap-3.5">
              <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime"><Cctv size={28} aria-hidden="true" /></span>
              <div>
                <h2 className="text-[20px] font-extrabold leading-tight">{cameras.area} kamera aktif</h2>
                <p className="text-[13px] text-white/90">{guards} satpam bertugas sekarang</p>
              </div>
            </GlassCard>
          )}
        </Hero>
        <div id="sec-panel" role="tabpanel" aria-labelledby={`sec-tab-${tab}`} className="space-y-4 px-5 pt-5">
          {tab === "Rumah" ? <HomePanel /> : <AreaCameras />}
        </div>
      </Screen>
    </MobileShell>
  );
}
