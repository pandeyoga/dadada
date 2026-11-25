import React, { useCallback } from "react";
import { Link } from "react-router-dom";
import { Bell, MapPin, CalendarClock, ChevronRight, Gift, FileText, Landmark, Map as MapIcon } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import { HeaderButton } from "../../components/ScreenHeader";
import Stepper from "../../components/Stepper";
import StatusChip from "../../components/StatusChip";
import ServiceGrid from "../../components/ServiceGrid";
import { StageIllustration, PromoIllustration } from "../../components/Illustrations";
import { getBuyerHome } from "../../services/api/buyer";
import { useProto } from "../../services/useStore";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const SERVICES = [
  { icon: MapIcon, label: "Peta kavling", to: "/app/pembeli/kavling" },
  { icon: Landmark, label: "Status KPR", to: "/app/pembeli/kpr" },
  { icon: Gift, label: "Ajak teman", to: "/app/ajak-teman" },
  { icon: FileText, label: "Dokumen", to: "/app/pembeli/dokumen" },
];

function NextBill({ item }) {
  if (!item) {
    return (
      <FrostCard className="-mt-7 !bg-white/95">
        <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Tagihan berikutnya</p>
        <p className="mt-1 text-[17px] font-extrabold">Semua cicilan uang muka lunas</p>
        <Link to="/app/pembeli/bayar" className="mt-2 inline-block text-[14px] font-bold text-rdg-forest">Lihat riwayat bayar</Link>
      </FrostCard>
    );
  }
  const pending = item.status === "pending";
  return (
    <FrostCard className="-mt-7 !bg-white/95">
      <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Tagihan berikutnya</p>
      <div className="mt-1 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[15px] font-bold leading-snug">{`Cicilan DP ke-${item.id.split("-")[1] || ""}`}</p>
          <p className="text-[26px] font-extrabold leading-tight tracking-[-0.02em]">{rupiah(item.amount)}</p>
          <p className="mt-0.5 flex items-center gap-1 text-[13px] font-semibold text-[color:var(--rdg-sos-ink)]">
            <CalendarClock size={14} aria-hidden="true" /> Jatuh tempo {tanggal(item.dueDate)}
          </p>
        </div>
        <Link to={`/app/pembeli/bayar/${item.id}`} className="rdg-btn-primary flex-none">
          {pending ? "Lanjut bayar" : "Bayar"}
        </Link>
      </div>
      {pending && <div className="mt-2"><StatusChip tone="warn">Menunggu pembayaran</StatusChip></div>}
    </FrostCard>
  );
}

export default function BuyerHome() {
  const fetcher = useCallback(() => getBuyerHome(), []);
  const { data } = useLoad(fetcher);
  const world = useProto((s) => s.world);
  const unreadBell = useProto((s) => s.notifications).some((n) => !n.read);
  const j = data && data.journey;
  return (
    <MobileShell nav="buyer">
      <Screen id="P1">
        <Hero className="pb-12">
          <div className="flex items-center gap-3 pb-4">
            <span className="grid h-12 w-12 flex-none place-items-center rounded-2xl bg-rdg-lime text-[16px] font-extrabold text-rdg-ink900" aria-hidden="true">RA</span>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] text-white/90">Selamat datang,</p>
              <h1 className="truncate text-[22px] font-extrabold leading-tight">{world.resident.name}</h1>
            </div>
            <HeaderButton icon={Bell} label="Notifikasi" to="/app/notifikasi" badge={unreadBell} />
          </div>
          <GlassCard>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-[12.5px] font-semibold text-white">
                <MapPin size={14} aria-hidden="true" /> {world.project.name} · Blok {world.unit.block}
              </span>
              <span className="rounded-full bg-rdg-lime px-3 py-1 text-[12.5px] font-bold text-rdg-ink900">Tipe {world.unit.type}</span>
            </div>
            <h2 className="text-[19px] font-extrabold leading-tight">Perjalanan rumah Anda</h2>
            <p className="mb-4 mt-0.5 text-[13.5px] text-white/90">Rumah sedang dibangun, tinggal menunggu serah terima.</p>
            {j && <Stepper variant="dark" steps={j.steps} current={j.current} progress={j.progress} />}
          </GlassCard>
        </Hero>

        <div className="relative space-y-5 px-5">
          {data && <NextBill item={data.nextInstallment} />}

          {data && data.latestPhoto && (
            <section aria-labelledby="p1-prog">
              <div className="mb-2 flex items-center justify-between">
                <h2 id="p1-prog" className="text-[17px] font-extrabold">Progres pembangunan</h2>
                <Link to="/app/pembeli/progres" className="flex items-center text-[13.5px] font-bold text-rdg-forest">Lihat foto <ChevronRight size={16} aria-hidden="true" /></Link>
              </div>
              <FrostCard className="overflow-hidden !p-0">
                <StageIllustration img={data.latestPhoto.img} label={`Foto terbaru: ${data.latestPhoto.stage}`} className="block h-[150px] w-full" />
                <div className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-bold">{data.latestPhoto.stage}</p>
                    <p className="text-[13px] text-[color:var(--rdg-muted)]">Foto {tanggal(data.latestPhoto.date)}</p>
                  </div>
                  <span className="text-[22px] font-extrabold text-rdg-forest">{data.progress.percent} %</span>
                </div>
              </FrostCard>
            </section>
          )}

          <section aria-labelledby="p1-svc">
            <h2 id="p1-svc" className="mb-3 text-[17px] font-extrabold">Layanan</h2>
            <ServiceGrid items={SERVICES} />
          </section>

          {data && (
            <section aria-labelledby="p1-promo">
              <h2 id="p1-promo" className="mb-2 text-[17px] font-extrabold">Info dan promo</h2>
              <ul className="-mx-5 flex snap-x gap-3 overflow-x-auto px-5 pb-2">
                {data.promos.map((p) => (
                  <li key={p.id} className="w-[236px] flex-none snap-start">
                    <Link to={`/app/pembeli/promo/${p.id}`} className="block overflow-hidden rounded-[18px] bg-white/85 shadow-[var(--rdg-shadow-card)]">
                      <PromoIllustration id={p.id} className="block h-[96px] w-full" />
                      <span className="block p-3">
                        <span className="block text-[14.5px] font-bold leading-snug">{p.title}</span>
                        <span className="mt-0.5 block text-[12.5px] text-[color:var(--rdg-muted)]">Sampai {tanggal(p.until)}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </Screen>
    </MobileShell>
  );
}
