import React, { useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Bell, MapPin, CalendarClock, ShieldCheck, ShieldAlert, Lock, LockOpen, Video, UserRound,
  KeyRound, Cctv, QrCode, ReceiptText, Wallet, Wrench, ShieldPlus, LayoutGrid,
  Megaphone, Zap, TrendingUp, TrendingDown, ChevronRight,
} from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import { HeaderButton } from "../../components/ScreenHeader";
import ServiceGrid from "../../components/ServiceGrid";
import Loading from "../../components/Loading";
import { getResidentHome } from "../../services/api/resident";
import { doorStatus } from "../../services/api/security";
import { useProto, useNow } from "../../services/useStore";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const SERVICES = [
  { icon: KeyRound, label: "Kunci pintu", to: "/app/warga/keamanan/kunci" },
  { icon: Video, label: "CCTV rumah", to: "/app/warga/keamanan/cctv-rumah" },
  { icon: Cctv, label: "CCTV kawasan", to: "/app/warga/keamanan/kawasan" },
  { icon: QrCode, label: "Tamu", to: "/app/warga/keamanan/tamu" },
  { icon: ReceiptText, label: "Tagihan", to: "/app/warga/tagihan" },
  { icon: Wallet, label: "Isi ulang", to: "/app/warga/isi-ulang" },
  { icon: Wrench, label: "Lapor rusak", to: "/app/warga/lapor" },
  { icon: ShieldPlus, label: "Garansi", to: "/app/warga/garansi" },
  { icon: LayoutGrid, label: "Semua", to: "/app/warga/layanan" },
];

const SLICES = ["security", "bills", "community", "world"];

function greeting(t) {
  const h = (new Date(t).getUTCHours() + 7) % 24;
  if (h < 11) return "Selamat pagi,";
  if (h < 15) return "Selamat siang,";
  if (h < 18) return "Selamat sore,";
  return "Selamat malam,";
}

function Tile({ icon: Icon, label, value, warn }) {
  return (
    <div className="rounded-2xl bg-white/12 p-3 ring-1 ring-white/15">
      <Icon size={19} aria-hidden="true" className={warn ? "text-rdg-lime" : "text-white/90"} />
      <p className="mt-2 text-[12.5px] text-white/90">{label}</p>
      <p className="text-[14.5px] font-extrabold leading-tight">{value}</p>
    </div>
  );
}

export default function ResidentHome() {
  const fetcher = useCallback(() => getResidentHome(), []);
  const { data, error } = useLoad(fetcher, SLICES);
  const world = useProto((s) => s.world);
  const security = useProto((s) => s.security);
  const notifications = useProto((s) => s.notifications);
  const t = useNow();
  const door = doorStatus({ security }, t);
  const hs = data && data.homeStatus;
  const guards = hs ? hs.guardsOnDuty : 0;
  const safe = door === "locked" && (!hs || guards > 0);
  const unread = notifications.some((n) => !n.read);
  const bill = data && data.iplDue;
  const initials = world.resident.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <MobileShell nav="resident">
      <Screen id="W1">
        <Hero className="pb-12">
          <div className="flex items-center gap-3 pb-4">
            <Link to="/app/warga/akun" aria-label="Akun saya" className="grid h-12 w-12 flex-none place-items-center rounded-2xl bg-rdg-lime text-[16px] font-extrabold text-rdg-ink900">
              <span aria-hidden="true">{initials}</span>
            </Link>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] text-white/90">{greeting(t)}</p>
              <h1 className="truncate text-[22px] font-extrabold leading-tight">{world.resident.name}</h1>
            </div>
            <HeaderButton icon={Bell} label="Notifikasi" to="/app/notifikasi" badge={unread} />
          </div>
          <GlassCard>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-[12.5px] font-semibold text-white">
                <MapPin size={14} aria-hidden="true" /> {world.project.name} · Blok {world.unit.block}
              </span>
            </div>
            <div className="flex items-center gap-3.5">
              <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime">
                {safe ? <ShieldCheck size={30} aria-hidden="true" /> : <ShieldAlert size={30} aria-hidden="true" />}
              </span>
              <div>
                <h2 className="text-[24px] font-extrabold leading-tight">{safe ? "Rumah aman" : "Perlu perhatian"}</h2>
                <p className="text-[13px] text-white/90">{safe ? "Semua pantauan normal" : door === "unlocked" ? "Pintu sedang terbuka" : "Belum ada satpam bertugas"}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2.5">
              <Tile icon={door === "locked" ? Lock : LockOpen} label="Pintu" value={door === "locked" ? "Terkunci" : "Terbuka"} warn={door !== "locked"} />
              <Tile icon={Video} label="Kamera" value={hs ? `${hs.cameraCount} aktif` : "aktif"} />
              <Tile icon={UserRound} label="Satpam" value={`${guards} bertugas`} warn={hs && guards === 0} />
            </div>
          </GlassCard>
        </Hero>

        <div className="relative space-y-5 px-5">
          {!data && <Loading error={error} />}
          {data && (
            <FrostCard className="-mt-7 !bg-white/95">
              {bill ? (
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">IPL {bill.period}</p>
                    <p className="text-[26px] font-extrabold leading-tight tracking-[-0.02em]">{rupiah(bill.amount)}</p>
                    <p className="mt-0.5 flex items-center gap-1 text-[13px] font-semibold text-[color:var(--rdg-sos-ink)]">
                      <CalendarClock size={14} aria-hidden="true" /> Jatuh tempo {tanggal(bill.dueDate)}
                    </p>
                  </div>
                  <Link to="/app/warga/tagihan" className="rdg-btn-primary flex-none">Bayar</Link>
                </div>
              ) : (
                <>
                  <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Iuran IPL</p>
                  <p className="text-[17px] font-extrabold">Semua iuran lunas</p>
                  <Link to="/app/warga/tagihan/riwayat" className="mt-1 inline-block text-[14px] font-bold text-rdg-forest">Lihat riwayat</Link>
                </>
              )}
            </FrostCard>
          )}

          <section aria-labelledby="w1-svc">
            <h2 id="w1-svc" className="mb-3 text-[17px] font-extrabold">Layanan</h2>
            <ServiceGrid items={SERVICES} />
          </section>

          {data && data.announcement && (
            <Link to="/app/warga/komunitas" className="block">
              <FrostCard className="flex items-center gap-3">
                <span className="rdg-row-icon"><Megaphone size={20} aria-hidden="true" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">Pengumuman · {data.announcement.author}</span>
                  <span className="block truncate text-[15px] font-bold">{data.announcement.title}</span>
                  <span className="block truncate text-[13px] text-[color:var(--rdg-muted)]">{data.announcement.body}</span>
                </span>
                <ChevronRight size={18} aria-hidden="true" className="flex-none text-[color:var(--rdg-muted)]" />
              </FrostCard>
            </Link>
          )}

          {data && (
            <Link to="/app/warga/energi" className="block">
              <FrostCard className="flex items-center gap-3">
                <span className="rdg-row-icon"><Zap size={20} aria-hidden="true" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block whitespace-nowrap text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">Energi bulan ini</span>
                  <span className="block text-[17px] font-extrabold">{data.energy.kwh} kWh</span>
                </span>
                <span className="inline-flex flex-none items-center gap-1 text-[12.5px] font-bold text-[color:var(--rdg-sos-ink)]">
                  {data.energy.deltaPct >= 0 ? <TrendingUp size={16} aria-hidden="true" /> : <TrendingDown size={16} aria-hidden="true" />}
                  {Math.abs(data.energy.deltaPct)} % vs bulan lalu
                </span>
              </FrostCard>
            </Link>
          )}
        </div>
      </Screen>
    </MobileShell>
  );
}
