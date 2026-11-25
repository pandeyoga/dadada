import React, { useMemo, useState } from "react";
import { BellRing, Radio, Video } from "lucide-react";
import MobileShell from "../../../components/MobileShell";
import Screen from "../../../components/Screen";
import Hero from "../../../components/Hero";
import { GlassCard, FrostCard } from "../../../components/GlassCard";
import ScreenHeader from "../../../components/ScreenHeader";
import CameraView from "../../../components/CameraView";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import { useNow } from "../../../services/useStore";

const CAMERAS = [
  { id: "home-teras", label: "Teras depan", note: "Menghadap pintu dan jalan" },
  { id: "home-taman", label: "Taman belakang", note: "Menghadap pintu belakang" },
];

const two = (n) => String(n).padStart(2, "0");
const wibHour = (t) => (new Date(t).getUTCHours() + 7) % 24;

// Rekaman per jam (simulasi): jumlah gerakan diturunkan dari jam agar stabil.
const motions = (h, cam) => (h * 7 + cam * 3) % 5;

export default function HomeCctv() {
  const t = useNow(60000);
  const [camIdx, setCamIdx] = useState(0);
  const [hour, setHour] = useState(null); // null = siaran langsung
  const [alertOn, setAlertOn] = useState(true);
  const cam = CAMERAS[camIdx];
  const hours = useMemo(() => {
    const h = wibHour(t);
    return Array.from({ length: 6 }, (_, i) => (h - i + 24) % 24);
  }, [t]);
  const live = hour == null;
  return (
    <MobileShell nav="resident">
      <Screen id="W4">
        <Hero className="pb-6">
          <ScreenHeader title="CCTV rumah" back="/app/warga/keamanan" />
          <GlassCard className="!p-2.5">
            <div className="overflow-hidden rounded-2xl"><CameraView cameraId={cam.id} label={cam.label} live={live} /></div>
            <div className="flex items-center justify-between gap-2 px-2 pb-1 pt-3">
              <div className="min-w-0">
                <h2 className="text-[17px] font-extrabold leading-tight">{cam.label}</h2>
                <p className="text-[13px] text-white">{live ? "Siaran langsung (simulasi)" : `Rekaman ${two(hour)}.00–${two((hour + 1) % 24)}.00`}</p>
              </div>
              {!live && (
                <button type="button" className="rdg-btn-ghost !min-h-[40px] !px-3.5 !text-[13.5px]" onClick={() => setHour(null)}>
                  <Radio size={16} aria-hidden="true" /> Kembali ke langsung
                </button>
              )}
            </div>
          </GlassCard>
        </Hero>
        <div className="space-y-4 px-5 pt-5">
          <FrostCard>
            <h2 className="text-[17px] font-extrabold">Kamera rumah</h2>
            <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
              {CAMERAS.map((c, i) => (
                <li key={c.id}>
                  <ListRow
                    icon={Video} title={c.label} subtitle={c.note}
                    onClick={() => { setCamIdx(i); setHour(null); }}
                    right={<StatusChip tone={i === camIdx ? "ok" : "neutral"} icon={null}>{i === camIdx ? "Dilihat" : "Aktif"}</StatusChip>}
                  />
                </li>
              ))}
            </ul>
          </FrostCard>
          <FrostCard>
            <h2 className="text-[17px] font-extrabold">Rekaman per jam</h2>
            <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
              {hours.map((h) => {
                const n = motions(h, camIdx);
                return (
                  <li key={h}>
                    <ListRow
                      icon={Video} title={`${two(h)}.00–${two((h + 1) % 24)}.00`}
                      subtitle={n ? `${n} gerakan terdeteksi` : "Tidak ada gerakan"}
                      onClick={() => setHour(h)}
                      right={<StatusChip tone={hour === h ? "info" : "neutral"} icon={null}>{hour === h ? "Diputar" : "Putar"}</StatusChip>}
                    />
                  </li>
                );
              })}
            </ul>
          </FrostCard>
          <FrostCard>
            <label className="flex items-center gap-3">
              <span className="rdg-row-icon"><BellRing size={20} aria-hidden="true" /></span>
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-semibold text-rdg-ink900">Notifikasi gerakan</span>
                <span className="block text-[13px] text-[color:var(--rdg-muted)]">{alertOn ? "Aktif: kami beri tahu bila ada gerakan di teras" : "Mati"}</span>
              </span>
              <input type="checkbox" role="switch" className="h-6 w-6 accent-[#01916f]" checked={alertOn} onChange={(e) => setAlertOn(e.target.checked)} aria-label="Notifikasi gerakan" />
            </label>
          </FrostCard>
        </div>
      </Screen>
    </MobileShell>
  );
}
