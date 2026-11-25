import React, { useMemo } from "react";
import { Lock, LockOpen, Timer } from "lucide-react";
import { GlassCard } from "../../../components/GlassCard";
import SlideToConfirm from "../../../components/SlideToConfirm";
import { useNow, useProto } from "../../../services/useStore";
import { kapan } from "../../../lib/format";
import { Msg, byRecent, doorLogText } from "./ui";

/** Kartu kunci pintu di atas hero: status, geser untuk buka, hitung mundur kunci otomatis. */
export default function DoorCard({ door }) {
  const log = useProto((s) => s.security.doorLog);
  const block = useProto((s) => s.world.unit.block);
  const t = useNow(60000);
  const open = door.status === "unlocked";
  const last = useMemo(() => byRecent(log)[0], [log]);
  return (
    <GlassCard>
      <div className="flex items-center gap-3.5">
        <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime">
          {open ? <LockOpen size={28} aria-hidden="true" /> : <Lock size={28} aria-hidden="true" />}
        </span>
        <div className="min-w-0">
          <p className="text-[13px] text-white/90">{`Pintu depan ${block}`}</p>
          <h2 className="text-[24px] font-extrabold leading-tight">{open ? "Terbuka" : "Terkunci"}</h2>
          {last && <p className="truncate text-[13px] text-white/90">{`${doorLogText(last)} · ${kapan(last.at, t)}`}</p>}
        </div>
      </div>
      <div className="mt-4">
        {open ? (
          <div className="space-y-3 rounded-2xl bg-white/12 p-3 ring-1 ring-white/20">
            <p className="flex items-center gap-2 text-[14px] font-bold" role="timer" aria-live="off">
              <Timer size={18} aria-hidden="true" className="text-rdg-lime" />
              {`Terkunci otomatis dalam ${door.remaining} detik`}
            </p>
            <button type="button" className="rdg-btn-ghost !min-h-[44px] w-full" onClick={door.lock}>Kunci sekarang</button>
          </div>
        ) : (
          <SlideToConfirm label="Geser untuk buka" onConfirm={door.unlock} />
        )}
      </div>
      {door.error && <div className="mt-3 rounded-xl bg-white p-3"><Msg error={door.error} /></div>}
    </GlassCard>
  );
}
