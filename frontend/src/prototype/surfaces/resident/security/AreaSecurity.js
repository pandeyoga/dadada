import React from "react";
import { Cctv } from "lucide-react";
import MobileShell from "../../../components/MobileShell";
import Screen from "../../../components/Screen";
import Hero from "../../../components/Hero";
import { GlassCard } from "../../../components/GlassCard";
import ScreenHeader from "../../../components/ScreenHeader";
import { guardsOnDutyAt } from "../../../services/api/resident";
import { useNow, useProto } from "../../../services/useStore";
import AreaCameras from "./AreaCameras";

export default function AreaSecurity() {
  const cameras = useProto((s) => s.security.cameras);
  const world = useProto((s) => s.world);
  const t = useNow(60000);
  const guards = guardsOnDutyAt(world, t).length;
  return (
    <MobileShell nav="resident">
      <Screen id="W5">
        <Hero className="pb-6">
          <ScreenHeader title="Keamanan kawasan" back="/app/warga/keamanan" />
          <GlassCard className="flex items-center gap-3.5">
            <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime"><Cctv size={28} aria-hidden="true" /></span>
            <div>
              <h2 className="text-[20px] font-extrabold leading-tight">{cameras.area} kamera aktif</h2>
              <p className="text-[13px] text-white/90">{world.project.name} · {guards} satpam bertugas</p>
            </div>
          </GlassCard>
        </Hero>
        <div className="px-5 pt-5"><AreaCameras /></div>
      </Screen>
    </MobileShell>
  );
}
