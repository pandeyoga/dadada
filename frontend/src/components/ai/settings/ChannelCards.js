import React, { useState } from "react";
import { ShieldAlert } from "lucide-react";
import { saveChannels, disableUnofficial, friendlyError } from "../aiApi";

const Badge = ({ tone, children }) => (
  <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${tone === "warn" ? "bg-[#FFF4E5] text-[#7A3E00]" : "bg-[#E3F2EA] text-[#14532D]"}`}>{children}</span>
);

/** `channels` = { official: {mode:"cloud"|"coexistence", phone}, unofficial: {enabled, hourly_limit, phone} } */
export default function ChannelCards({ channels, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const official = channels?.official || {};
  const un = channels?.unofficial || {};

  const run = async (fn) => {
    setBusy(true); setErr("");
    try { await fn(); onChanged?.(); } catch (e) { setErr(friendlyError(e, "Perubahan kanal gagal.")); }
    finally { setBusy(false); }
  };

  const OfficialCard = ({ mode, title, text }) => {
    const on = official.mode === mode;
    return (
      <div className={`flex flex-col gap-2 rounded-xl border p-4 ${on ? "border-[#006284] bg-[#F1F8F6]" : "border-[#D5E0DC] bg-white"}`}>
        <span className="flex items-center gap-2 text-sm"><b>{title}</b><Badge>Resmi</Badge>{on ? <span className="text-xs font-semibold text-[#006284]">Aktif</span> : null}</span>
        <span className="text-[13px] text-[#2B4744]">{text}{official.phone && on ? ` Nomor ${official.phone}.` : ""}</span>
        {!on ? (
          <button type="button" disabled={busy} onClick={() => run(() => saveChannels({ official_mode: mode }))}
            className="min-h-[40px] w-fit rounded-lg border border-[#B9CFC8] bg-white px-3 text-[13px] font-semibold text-[#12312F] disabled:opacity-60">Pakai mode ini</button>
        ) : null}
      </div>
    );
  };

  return (
    <section id="kanal" aria-labelledby="h-kanal" className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <h2 id="h-kanal" className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">Kanal WhatsApp</h2>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <OfficialCard mode="cloud" title="Cloud API" text="Bot AI, template, blast." />
        <OfficialCard mode="coexistence" title="Coexistence" text="Sales tetap membalas dari aplikasi WA Business di HP; AI lewat API di nomor yang sama." />
        <div data-testid="gateway-card" className="flex flex-col gap-2 rounded-xl border border-[#E7B96B] bg-[#FFF8EC] p-4">
          <span className="flex items-center gap-2 text-sm">
            <ShieldAlert className="h-4 w-4 text-[#7A3E00]" aria-hidden="true" />
            <b>Gateway tidak resmi</b><Badge tone="warn">Risiko blokir</Badge>
          </span>
          <span className="text-[13px] text-[#4A2A00]">Hemat biaya. Hanya follow-up personal ke kontak yang sudah setuju. Bot AI otomatis &amp; blast dimatikan.</span>
          <p className="m-0 text-[13px] font-semibold text-[#4A2A00]">Status: {un.enabled ? "Aktif" : "Mati"}</p>
          {un.enabled ? (
            <>
              <label className="flex flex-wrap items-center gap-2 text-[13px] text-[#4A2A00]">
                Batas kirim
                <select value={String(un.hourly_limit || 20)} disabled={busy}
                  onChange={(e) => run(() => saveChannels({ unofficial: { hourly_limit: Number(e.target.value) } }))}
                  className="min-h-[40px] rounded-lg border border-[#E7B96B] bg-white px-2 text-[13px] font-semibold">
                  {[10, 20, 30].map((n) => <option key={n} value={n}>{n} pesan/jam</option>)}
                </select>
              </label>
              <button type="button" disabled={busy}
                onClick={() => { if (window.confirm("Matikan kanal tidak resmi? Pesan lewat gateway ini akan berhenti.")) run(disableUnofficial); }}
                className="min-h-[40px] w-fit rounded-lg border border-[#E8C4C0] bg-white px-3 text-[13px] font-semibold text-[#9B1C1C] disabled:opacity-60">Matikan kanal ini</button>
            </>
          ) : null}
        </div>
      </div>
      {err ? <p role="alert" className="mt-2 text-[13px] text-[#9B1C1C]">{err}</p> : null}
    </section>
  );
}
