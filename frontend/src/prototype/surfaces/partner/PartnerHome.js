import React, { useCallback } from "react";
import { Link } from "react-router-dom";
import { Star, Trophy, Wallet, Building2, UserPlus, Coins, UserCheck } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import StatusChip from "../../components/StatusChip";
import ServiceGrid from "../../components/ServiceGrid";
import { getPartnerHome } from "../../services/api/partner";
import { useProto } from "../../services/useStore";
import { rupiah } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import { Loading } from "./PartnerPage";

const SERVICES = [
  { icon: Building2, label: "Katalog", to: "/app/mitra/katalog" },
  { icon: UserPlus, label: "Rujukan", to: "/app/mitra/rujukan" },
  { icon: Coins, label: "Komisi", to: "/app/mitra/komisi" },
  { icon: UserCheck, label: "Daftar", to: "/app/mitra/daftar" },
];

/** M2: beranda mitra — poin, peringkat, komisi diproses, papan peringkat. */
export default function PartnerHome() {
  const fetcher = useCallback(() => getPartnerHome(), []);
  const { data, error } = useLoad(fetcher, ["partner"]);
  const profile = useProto((s) => s.partner.profile);
  const registered = useProto((s) => s.partner.registered);
  return (
    <MobileShell nav="partner">
      <Screen id="M2">
        <Hero className="pb-6">
          <div className="pb-4">
            <p className="text-[13px] text-white/90">Mitra Estora</p>
            <h1 className="text-[22px] font-extrabold leading-tight">{profile.name}</h1>
            <p className="mt-1 text-[13px] text-white/90">{`Kode ${profile.code} · Tingkat ${profile.tier}`}</p>
          </div>
          <GlassCard>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div><Star size={18} className="mx-auto" aria-hidden="true" /><p className="mt-1 text-[22px] font-extrabold leading-none">{data ? data.points : "–"}</p><p className="mt-1 text-[12.5px] text-white/90">Poin</p></div>
              <div><Trophy size={18} className="mx-auto" aria-hidden="true" /><p className="mt-1 text-[22px] font-extrabold leading-none">{data ? `#${data.rank}` : "–"}</p><p className="mt-1 text-[12.5px] text-white/90">Peringkat</p></div>
              <div><Wallet size={18} className="mx-auto" aria-hidden="true" /><p className="mt-1 text-[16px] font-extrabold leading-[22px]">{data ? rupiah(data.commissionPending) : "–"}</p><p className="mt-1 text-[12.5px] text-white/90">Komisi diproses</p></div>
            </div>
          </GlassCard>
        </Hero>
        <div className="space-y-5 px-5 pt-4">
          {!registered && (
            <FrostCard>
              <StatusChip tone="warn">Belum terdaftar</StatusChip>
              <p className="mt-2 text-[15px] font-bold">Lengkapi pendaftaran mitra Anda</p>
              <p className="mt-1 text-[13.5px] text-[color:var(--rdg-muted)]">Isi data diri dan rekening agar komisi bisa dicairkan.</p>
              <Link to="/app/mitra/daftar" className="rdg-btn-primary mt-3 w-full">Daftar sekarang</Link>
            </FrostCard>
          )}
          <section aria-labelledby="m2-svc">
            <h2 id="m2-svc" className="mb-3 text-[17px] font-extrabold">Menu mitra</h2>
            <ServiceGrid items={SERVICES} />
          </section>
          <section aria-labelledby="m2-lb">
            <h2 id="m2-lb" className="mb-2 text-[17px] font-extrabold">Papan peringkat mitra</h2>
            {!data && <Loading error={error} />}
            {data && (
              <FrostCard className="!p-2">
                <ol className="divide-y divide-[color:var(--rdg-line)]">
                  {data.leaderboard.map((x) => {
                    const me = x.name === profile.name;
                    return (
                      <li key={x.name} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ${me ? "bg-[#e7ffef]" : ""}`} aria-current={me ? "true" : undefined}>
                        <span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-rdg-ink900 text-[14px] font-extrabold text-white">{x.rank}</span>
                        <span className="min-w-0 flex-1 truncate text-[15px] font-bold">{me ? `${x.name} (Anda)` : x.name}</span>
                        <span className="text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">{`${x.listings} unit`}</span>
                      </li>
                    );
                  })}
                </ol>
              </FrostCard>
            )}
          </section>
        </div>
      </Screen>
    </MobileShell>
  );
}
