import React, { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2, ChevronRight, Handshake, Home, KeyRound, MapPin, RotateCcw, ShieldCheck, UserRound, Wand2,
} from "lucide-react";
import Screen from "../../components/Screen";
import MobileShell from "../../components/MobileShell";
import Hero from "../../components/Hero";
import BrandMark from "../../components/BrandMark";
import StatusChip from "../../components/StatusChip";
import { FrostCard } from "../../components/GlassCard";
import { useProto } from "../../services/useStore";
import { getState, resetState } from "../../services/store";
import { setPersona, simulateBast, setLocation, homePathFor } from "../../services/api/session";
import screens from "../../screens.json";

const PERSONAS = [
  { id: "buyer", name: "Rina · Pembeli", note: "Rumah sedang dibangun, 72 %", icon: Home },
  { id: "resident", name: "Rina · Warga", note: "Sudah tinggal di Blok C-12", icon: KeyRound },
  { id: "satpam", name: "Pak Joko · Satpam", note: "Pos gerbang utama", icon: ShieldCheck },
  { id: "pengelola", name: "Pengelola kawasan", note: "Dasbor operasional", icon: Building2 },
  { id: "mitra", name: "Dimas · Mitra", note: "Agen rujukan: katalog, tautan, komisi", icon: Handshake },
];

const GROUPS = [
  ["demo", "Demo"], ["buyer", "Pembeli"], ["transition", "Transisi"], ["resident", "Warga"],
  ["satpam", "Satpam"], ["manager", "Pengelola"], ["partner", "Mitra"],
];

export default function Launcher() {
  const navigate = useNavigate();
  const location = useProto((s) => s.location);
  const session = useProto((s) => s.session);
  const mode = useProto((s) => s.mode);
  const grouped = useMemo(
    () => GROUPS.map(([key, label]) => [label, screens.filter((s) => s.surface === key)]),
    []
  );

  const enter = (persona) => {
    setPersona(persona);
    navigate(homePathFor(getState()));
  };
  const bast = () => {
    simulateBast();
    navigate(homePathFor(getState()));
  };

  return (
    <MobileShell>
      <Screen id="U1">
        <Hero>
          <div className="flex items-center justify-between">
            <BrandMark variant="dark" />
            <StatusChip tone="info" icon={Wand2}>Data contoh</StatusChip>
          </div>
          <h1 className="mt-6 mb-1 text-[26px] font-extrabold leading-tight tracking-[-0.02em]">Estora Residence</h1>
          <p className="m-0 mb-2 text-[14px] text-white/90">
            Panel demo. Pilih peran untuk melihat aplikasi dari sudut pandangnya.
          </p>
        </Hero>

        <div className="space-y-5 px-5 pb-10 pt-5">
          <section aria-labelledby="l-persona">
            <h2 id="l-persona" className="mb-2 text-[15px] font-bold">Masuk sebagai</h2>
            <ul className="m-0 grid list-none gap-2.5 p-0">
              {PERSONAS.map((p) => {
                const Icon = p.icon;
                const active = session.loggedIn && (session.persona === p.id);
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => enter(p.id)}
                      className="rdg-frost flex w-full cursor-pointer items-center gap-3 p-3.5 text-left"
                      aria-label={`${p.name}, ${p.note}`}
                    >
                      <span className="rdg-brand-tile grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-white" style={{ background: "var(--rdg-grad-btn)" }}>
                        <Icon size={22} strokeWidth={2.1} aria-hidden="true" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[15px] font-bold text-rdg-ink900">{p.name}</span>
                        <span className="block text-[13px]" style={{ color: "var(--rdg-muted)" }}>{p.note}</span>
                      </span>
                      {active ? <StatusChip tone="ok">Aktif</StatusChip> : <ChevronRight size={20} aria-hidden="true" color="var(--rdg-muted)" />}
                    </button>
                  </li>
                );
              })}
            </ul>
            <Link to="/app/masuk" className="mt-3 inline-flex min-h-[44px] items-center gap-2 text-[14px] font-bold" style={{ color: "var(--rdg-forest)" }}>
              <UserRound size={18} aria-hidden="true" /> Coba masuk dengan nomor WhatsApp
            </Link>
          </section>

          <FrostCard className="space-y-4">
            <div>
              <h2 className="m-0 mb-1 text-[15px] font-bold">Skenario</h2>
              <p className="m-0 mb-3 text-[13px]" style={{ color: "var(--rdg-muted)" }}>
                Mode sekarang: {mode === "resident" ? "Warga" : "Pembeli"}.
              </p>
              <button type="button" className="rdg-btn-primary w-full" onClick={bast}>
                <Wand2 size={18} aria-hidden="true" /> Simulasikan BAST
              </button>
            </div>
            <div role="group" aria-labelledby="l-lokasi">
              <h2 id="l-lokasi" className="m-0 mb-2 flex items-center gap-1.5 text-[15px] font-bold">
                <MapPin size={17} aria-hidden="true" /> Lokasi
              </h2>
              <div className="grid grid-cols-2 gap-1 rounded-2xl p-1" style={{ background: "rgba(0,69,77,0.08)" }}>
                {[["inside", "Di dalam kawasan"], ["outside", "Di luar kawasan"]].map(([v, label]) => (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={location === v}
                    onClick={() => setLocation(v)}
                    className="min-h-[44px] cursor-pointer rounded-xl border-0 text-[13px] font-bold"
                    style={location === v
                      ? { background: "var(--rdg-grad-btn)", color: "#fff" }
                      : { background: "transparent", color: "var(--rdg-ink900)" }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="m-0 mt-2 text-[13px]" style={{ color: "var(--rdg-muted)" }}>
                Lokasi: {location === "inside" ? "di dalam" : "di luar"} kawasan
              </p>
            </div>
            <button
              type="button"
              className="rdg-btn-ghost w-full"
              onClick={() => { resetState(); navigate("/app/demo"); }}
            >
              <RotateCcw size={17} aria-hidden="true" /> Reset data contoh
            </button>
          </FrostCard>

          <section aria-labelledby="l-layar">
            <h2 id="l-layar" className="mb-1 text-[15px] font-bold">Semua layar ({screens.length})</h2>
            <p className="m-0 mb-2 text-[13px]" style={{ color: "var(--rdg-muted)" }}>Untuk juri: buka layar mana pun langsung.</p>
            <div className="grid gap-2">
              {grouped.map(([label, list]) => (
                <details key={label} className="rdg-frost px-4 py-1">
                  <summary className="flex min-h-[48px] cursor-pointer items-center justify-between text-[14px] font-bold">
                    <span>{label}</span>
                    <span className="text-[12px] font-semibold" style={{ color: "var(--rdg-muted)" }}>{list.length} layar</span>
                  </summary>
                  <ul className="m-0 list-none p-0 pb-2">
                    {list.map((s) => (
                      <li key={s.id}>
                        <Link to={s.path} className="flex min-h-[44px] items-center gap-3 text-[14px] no-underline" style={{ color: "var(--rdg-ink900)" }}>
                          <span className="w-9 shrink-0 text-[12px] font-extrabold" style={{ color: "var(--rdg-forest)" }}>{s.id}</span>
                          <span className="flex-1">{s.title}</span>
                          <ChevronRight size={16} aria-hidden="true" color="var(--rdg-muted)" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          </section>
        </div>
      </Screen>
    </MobileShell>
  );
}
