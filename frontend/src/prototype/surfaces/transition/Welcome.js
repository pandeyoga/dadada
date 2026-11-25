import React, { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Home, Link2, Users, PhoneCall } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import BrandMark from "../../components/BrandMark";
import { FrostCard } from "../../components/GlassCard";
import { useProto } from "../../services/useStore";
import { completeOnboarding } from "../../services/api/resident";
import PeopleStep from "./PeopleStep";
import ConnectStep from "./ConnectStep";

const STEPS = [
  { icon: Home, title: "Selamat datang di rumah baru", lead: "Serah terima selesai. Mari siapkan rumah Anda dalam 4 langkah singkat." },
  { icon: Link2, title: "Hubungkan kunci & kamera", lead: "Sambungkan kunci pintu pintar dan kamera rumah ke aplikasi." },
  { icon: Users, title: "Undang keluarga", lead: "Anggota keluarga bisa ikut membuka pintu dan menerima kabar rumah." },
  { icon: PhoneCall, title: "Kontak darurat", lead: "Orang yang dihubungi saat SOS. Kontak pos satpam sudah tersimpan." },
];

export default function Welcome() {
  const navigate = useNavigate();
  const world = useProto((s) => s.world);
  const contacts = useProto((s) => s.security.contacts);
  const family = useProto((s) => s.care.family);
  const [step, setStep] = useState(0);
  const [started, setStarted] = useState(false);
  const [connected, setConnected] = useState(false);
  const [skipped, setSkipped] = useState(false);
  const [invites, setInvites] = useState([]);
  const [extra, setExtra] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const people = useRef(null);
  const onDone = useCallback(() => setConnected(true), []);
  const s = STEPS[step];
  const Icon = s.icon;

  // Isian yang diketik tapi belum ditambahkan ikut disimpan (atau ditahan dengan pesan bila tidak lengkap).
  const flush = (fallback) => (people.current ? people.current.flush() : fallback);
  const finish = async () => {
    const contacts = flush(extra);
    if (!contacts) return;
    setBusy(true);
    try {
      await completeOnboarding({ connectDevices: connected && !skipped, invites, contacts });
      navigate("/app/warga", { replace: true });
    } catch (e) {
      setError(e.message || "Gagal menyimpan");
      setBusy(false);
    }
  };
  const next = () => setStep((n) => n + 1);

  return (
    <MobileShell>
      <Screen id="T1">
        <Hero className="pb-10">
          <BrandMark variant="dark" />
          <div className="mt-6 flex items-center gap-4">
            <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15"><Icon size={28} aria-hidden="true" /></span>
            <div className="min-w-0">
              <p className="text-[13px] font-semibold text-white/90">Langkah {step + 1} dari {STEPS.length}</p>
              <h1 className="text-[24px] font-extrabold leading-tight">{s.title}</h1>
            </div>
          </div>
          <div className="mt-4 flex gap-1.5" aria-hidden="true">
            {STEPS.map((_, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-rdg-lime" : "bg-white/25"}`} />)}
          </div>
        </Hero>

        <div className="space-y-4 px-5 pb-8 pt-5">
          <p className="text-[15px] leading-relaxed text-[color:var(--rdg-muted)]">{s.lead}</p>
          {step === 0 && (
            <FrostCard>
              <p className="text-[14.5px] leading-relaxed">
                Rumah <b>{world.unit.block}</b> di <b>{world.project.name}</b> kini milik Anda, {world.resident.name}. Setelah ini Anda bisa mengunci pintu, melihat kamera, membayar iuran, dan memanggil satpam dari satu aplikasi.
              </p>
            </FrostCard>
          )}
          {step === 1 && <ConnectStep started={started} onDone={onDone} />}
          {step === 2 && <PeopleStep ref={people} idPrefix="fam" items={invites} existing={family} onChange={setInvites} addLabel="Tambah" />}
          {step === 3 && <PeopleStep ref={people} idPrefix="ct" items={extra} existing={contacts} onChange={setExtra} addLabel="Tambah" />}
          {error && <p role="alert" className="text-[13px] font-semibold text-[color:var(--rdg-sos-ink)]">{error}</p>}

          <div className="space-y-2.5 pt-2">
            {step === 0 && <button type="button" className="rdg-btn-primary w-full" onClick={next}>Mulai</button>}
            {step === 1 && !started && (
              <>
                <button type="button" className="rdg-btn-primary w-full" onClick={() => setStarted(true)}>Hubungkan sekarang</button>
                <button type="button" className="rdg-btn-ghost w-full" onClick={() => { setSkipped(true); next(); }}>Lewati dulu</button>
              </>
            )}
            {step === 1 && started && <button type="button" className="rdg-btn-primary w-full" disabled={!connected} onClick={next}>Lanjut</button>}
            {step === 2 && <button type="button" className="rdg-btn-primary w-full" onClick={() => { if (flush(invites)) next(); }}>Lanjut</button>}
            {step === 3 && <button type="button" className="rdg-btn-primary w-full" disabled={busy} onClick={finish}>Selesai</button>}
            {step > 0 && <button type="button" className="rdg-btn-ghost w-full" onClick={() => setStep((n) => n - 1)}>Kembali</button>}
          </div>
        </div>
      </Screen>
    </MobileShell>
  );
}
