import React, { useState } from "react";
import { Link } from "react-router-dom";
import { DoorOpen, QrCode, UserRound } from "lucide-react";
import { FrostCard } from "../../../components/GlassCard";
import CameraView from "../../../components/CameraView";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import { guardsOnDutyAt } from "../../../services/api/resident";
import { useNow, useProto } from "../../../services/useStore";

/** Grid kamera kawasan (6), satpam bertugas, dan tautan gerbang & tamu. Dipakai W2 (tab Kawasan) dan W5. */
export default function AreaCameras() {
  const cameras = useProto((s) => s.security.cameras);
  const world = useProto((s) => s.world);
  const t = useNow(60000);
  const [focus, setFocus] = useState(null);
  const onDuty = guardsOnDutyAt(world, t).map((g) => g.id);
  return (
    <div className="space-y-5">
      <section aria-labelledby="area-cam">
        <h2 id="area-cam" className="mb-3 text-[17px] font-extrabold">Kamera kawasan</h2>
        <div className="grid grid-cols-2 gap-2.5">
          {cameras.areaList.map((label, i) => {
            const id = `area-${i + 1}`;
            const big = focus === id;
            return (
              <button
                key={id} type="button" aria-pressed={big}
                aria-label={`${big ? "Perkecil" : "Perbesar"} kamera ${label}`}
                onClick={() => setFocus(big ? null : id)}
                className={`block overflow-hidden rounded-2xl text-left shadow-[var(--rdg-shadow-card)] ${big ? "col-span-2" : ""}`}
              >
                <CameraView cameraId={id} label={label} />
              </button>
            );
          })}
        </div>
      </section>
      <FrostCard>
        <h2 className="text-[17px] font-extrabold">Satpam bertugas</h2>
        <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
          {world.guards.map((g) => (
            <li key={g.id}>
              <ListRow
                icon={UserRound}
                title={g.name}
                subtitle={`Shift ${g.shift}`}
                right={<StatusChip tone={onDuty.includes(g.id) ? "ok" : "neutral"} icon={null}>{onDuty.includes(g.id) ? "Bertugas" : "Istirahat"}</StatusChip>}
              />
            </li>
          ))}
        </ul>
      </FrostCard>
      <div className="grid grid-cols-2 gap-2.5">
        <Link to="/app/warga/keamanan/gerbang" className="rdg-btn-ghost justify-center !px-2 !text-[14px] whitespace-nowrap"><DoorOpen size={18} aria-hidden="true" /> Gerbang pintar</Link>
        <Link to="/app/warga/keamanan/tamu" className="rdg-btn-ghost justify-center !px-2 !text-[14px] whitespace-nowrap"><QrCode size={18} aria-hidden="true" /> Undang tamu</Link>
      </div>
    </div>
  );
}
