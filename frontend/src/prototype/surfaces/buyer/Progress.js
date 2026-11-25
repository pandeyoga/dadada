import React, { useCallback } from "react";
import { CalendarCheck } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import ScreenHeader from "../../components/ScreenHeader";
import { StageIllustration } from "../../components/Illustrations";
import { getProgress } from "../../services/api/buyer";
import { tanggal } from "../../lib/format";
import useLoad from "./useLoad";
import { Loading } from "./Page";

export default function Progress() {
  const fetcher = useCallback(() => getProgress(), []);
  const { data } = useLoad(fetcher);
  return (
    <MobileShell nav="buyer">
      <Screen id="P2">
        <Hero className="pb-10">
          <ScreenHeader title="Progres rumah" back="/app/pembeli" />
          <GlassCard className="mt-1">
            <p className="text-[13.5px] font-semibold text-white/90">Tahap {data ? data.stage : "…"}</p>
            <p className="text-[40px] font-extrabold leading-none tracking-[-0.03em]">{data ? data.percent : "--"} %</p>
            <div className="rdg-stepper--dark mt-3"><div className="rdg-progress" role="progressbar" aria-label="Progres pembangunan" aria-valuemin={0} aria-valuemax={100} aria-valuenow={data ? data.percent : 0}>
              <span style={{ width: `${data ? data.percent : 0}%` }} />
            </div></div>
            {data && (
              <p className="mt-3 flex items-center gap-2 text-[13.5px] font-semibold text-white/90">
                <CalendarCheck size={16} aria-hidden="true" /> Estimasi serah terima: {data.handoverEstimate}
              </p>
            )}
          </GlassCard>
        </Hero>
        <div className="px-5 pt-5">
          <h2 className="mb-3 text-[17px] font-extrabold">Linimasa foto</h2>
          {!data && <Loading />}
          {data && (
            <ol className="relative space-y-4 border-l-2 border-[color:var(--rdg-line)] pl-5">
              {[...data.photos].reverse().map((p, i) => (
                <li key={p.stage} className="relative">
                  <span className={`absolute -left-[29px] top-1 h-4 w-4 rounded-full border-[3px] border-white ${i === 0 ? "bg-rdg-green" : "bg-rdg-teal"}`} aria-hidden="true" />
                  <FrostCard className="overflow-hidden !p-0">
                    <StageIllustration img={p.img} label={`Foto tahap ${p.stage}`} className="block h-[132px] w-full" />
                    <div className="p-3.5">
                      <p className="text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">{tanggal(p.date)}{i === 0 ? " · Terbaru" : ""}</p>
                      <p className="text-[15.5px] font-bold">{p.stage}</p>
                      <p className="mt-0.5 text-[13.5px] leading-snug text-[color:var(--rdg-muted)]">{p.caption}</p>
                    </div>
                  </FrostCard>
                </li>
              ))}
            </ol>
          )}
        </div>
      </Screen>
    </MobileShell>
  );
}
