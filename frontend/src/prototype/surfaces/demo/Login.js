import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, MessageCircle } from "lucide-react";
import Screen from "../../components/Screen";
import MobileShell from "../../components/MobileShell";
import Hero from "../../components/Hero";
import BrandMark from "../../components/BrandMark";
import { FrostCard } from "../../components/GlassCard";
import { getState } from "../../services/store";
import { requestOtp, verifyOtp, homePathFor } from "../../services/api/session";

/** 6 kotak tampilan di atas satu input asli (tempel, isi otomatis SMS, dan pembaca layar tetap jalan). */
function OtpBoxes({ value, onChange, onComplete, disabled }) {
  const [focused, setFocused] = useState(true);
  const set = (raw) => {
    const v = raw.replace(/\D/g, "").slice(0, 6);
    onChange(v);
    if (v.length === 6) onComplete(v);
  };
  return (
    <div className="relative flex justify-between gap-2">
      {Array.from({ length: 6 }, (_, i) => {
        const active = focused && i === Math.min(value.length, 5);
        return (
          <div
            key={i}
            data-testid="otp-slot"
            aria-hidden="true"
            className="grid h-14 w-12 place-items-center rounded-2xl bg-white text-[22px] font-extrabold"
            style={{ border: `2px solid ${active ? "var(--rdg-teal)" : "rgba(0,103,71,0.22)"}`, color: "var(--rdg-ink900)" }}
          >
            {value[i] || ""}
          </div>
        );
      })}
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]*"
        maxLength={6}
        autoFocus
        value={value}
        disabled={disabled}
        aria-label="Kode OTP 6 angka"
        onChange={(e) => set(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="absolute inset-0 h-full w-full cursor-text opacity-0"
        style={{ caretColor: "transparent" }}
      />
    </div>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("");
  const [sentTo, setSentTo] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode memasang ulang efek
    return () => { alive.current = false; };
  }, []);

  const send = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const r = await requestOtp(phone);
      if (!alive.current) return;
      setSentTo(r.sentTo);
      setStep("otp");
    } catch (err) {
      if (alive.current) setError(err.message);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const verify = async (value) => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await verifyOtp(value);
      if (alive.current) navigate(homePathFor(getState()), { replace: true });
    } catch (err) {
      if (alive.current) { setError(err.message); setBusy(false); }
    }
  };

  return (
    <MobileShell>
      <Screen id="U2">
        <Hero height={220}>
          <BrandMark variant="dark" />
          <h1 className="mt-8 mb-1 text-[26px] font-extrabold leading-tight tracking-[-0.02em]">Masuk ke rumah Anda</h1>
          <p className="m-0 text-[14px] text-white/90">Kami kirim kode lewat WhatsApp.</p>
        </Hero>
        <div className="px-5 pb-10 pt-5">
          <FrostCard className="p-5">
            {step === "phone" ? (
              <form onSubmit={send} noValidate>
                <label htmlFor="rdg-phone" className="mb-2 block text-[14px] font-bold">Nomor WhatsApp</label>
                <input
                  id="rdg-phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="0812-3456-7890"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  aria-describedby={error ? "rdg-login-err" : undefined}
                  aria-invalid={error ? "true" : undefined}
                  className="min-h-[52px] w-full rounded-2xl bg-white px-4 text-[17px] font-semibold"
                  style={{ border: "2px solid rgba(0,103,71,0.22)", color: "var(--rdg-ink900)" }}
                />
                {error && <p id="rdg-login-err" role="alert" className="mt-2 mb-0 text-[13px] font-semibold" style={{ color: "var(--rdg-sos-ink)" }}>{error}</p>}
                <button type="submit" disabled={busy} className="rdg-btn-primary mt-4 w-full">
                  <MessageCircle size={18} aria-hidden="true" /> Kirim kode
                </button>
              </form>
            ) : (
              <div>
                <p className="m-0 mb-4 text-[14px]">Masukkan 6 angka yang dikirim ke <strong>{sentTo}</strong>. Kode apa pun diterima di demo ini.</p>
                <OtpBoxes value={code} onChange={setCode} onComplete={verify} disabled={busy} />
                {error && <p role="alert" className="mt-3 mb-0 text-[13px] font-semibold" style={{ color: "var(--rdg-sos-ink)" }}>{error}</p>}
                <button type="button" disabled={busy || code.length < 6} className="rdg-btn-primary mt-4 w-full" onClick={() => verify(code)}>
                  Masuk
                </button>
                <button type="button" className="rdg-btn-ghost mt-2 w-full" onClick={() => { setStep("phone"); setCode(""); setError(""); }}>
                  <ArrowLeft size={17} aria-hidden="true" /> Ganti nomor
                </button>
              </div>
            )}
          </FrostCard>
        </div>
      </Screen>
    </MobileShell>
  );
}
