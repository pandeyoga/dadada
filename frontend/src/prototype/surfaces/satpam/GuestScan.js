import React, { useState } from "react";
import { ScanQrCode, CircleCheck, CircleX, QrCode } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import ListRow from "../../components/ListRow";
import { checkInGuest, GUEST_REASONS } from "../../services/api/guard";
import { guestPassStatus } from "../../services/api/security";
import { useNow, useProto } from "../../services/useStore";
import Page from "../buyer/Page";
import { FIELD, Field, rentangJam, wibDay } from "../resident/security/ui";
import SosBanner from "./SosBanner";

function Result({ result }) {
  const ok = result.ok;
  const block = useProto((s) => s.world.unit.block);
  return (
    <FrostCard role="status" aria-live="polite" className={`border-2 ${ok ? "border-[color:var(--rdg-green)]" : "border-[color:var(--rdg-sos)]"}`}>
      <div className="flex items-start gap-3">
        <span className={ok ? "text-rdg-forest" : "text-[color:var(--rdg-sos-ink)]"}>{ok ? <CircleCheck size={30} aria-hidden="true" /> : <CircleX size={30} aria-hidden="true" />}</span>
        <div>
          <h2 className="text-[20px] font-extrabold">{ok ? "Tamu valid" : "Tamu tidak valid"}</h2>
          {ok ? (
            <p className="mt-0.5 text-[14.5px]">{`${result.pass.guestName} · tujuan Blok ${block}. Silakan izinkan masuk.`}</p>
          ) : (
            <p className="mt-0.5 text-[14.5px] text-[color:var(--rdg-sos-ink)]">{GUEST_REASONS[result.reason]}</p>
          )}
        </div>
      </div>
    </FrostCard>
  );
}

export default function GuestScan() {
  const passes = useProto((s) => s.security.guestPasses);
  const t = useNow(30000);
  const [scanning, setScanning] = useState(false);
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const today = passes.filter((p) => p.date === wibDay(t) && guestPassStatus(p, t) === "active");
  const check = async (value) => {
    setBusy(true);
    try { setResult(await checkInGuest(value)); } finally { setBusy(false); }
  };
  return (
    <Page id="S3" title="Pindai tamu" back="/app/satpam" nav="satpam">
      <SosBanner />
      <FrostCard>
        <div className="rdg-scan-frame" aria-hidden="true"><ScanQrCode size={56} strokeWidth={1.6} /></div>
        <p className="mt-2 text-center text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">Simulasi pemindai · kamera perangkat tidak dipakai</p>
        <button type="button" className="rdg-btn-primary mt-3 w-full" aria-expanded={scanning} onClick={() => setScanning((v) => !v)}><ScanQrCode size={18} aria-hidden="true" /> Pindai QR</button>
        {scanning && (
          <div className="mt-3">
            <h2 className="text-[15px] font-extrabold">Undangan hari ini — ketuk untuk memindai</h2>
            {today.length === 0 ? (
              <p className="mt-1 text-[14px] text-[color:var(--rdg-muted)]">Belum ada undangan aktif untuk hari ini.</p>
            ) : (
              <ul className="divide-y divide-[color:var(--rdg-line)]">
                {today.map((p) => (
                  <li key={p.id}><ListRow icon={QrCode} title={p.guestName} subtitle={`${rentangJam(p)} WIB · ${p.code}`} onClick={() => check(p.code)} /></li>
                ))}
              </ul>
            )}
          </div>
        )}
      </FrostCard>
      {result && <Result result={result} />}
      <FrostCard>
        <form onSubmit={(e) => { e.preventDefault(); check(code); }} className="space-y-3">
          <Field id="gs-code" label="Kode tamu (6 karakter)">
            <input id="gs-code" className={`${FIELD} uppercase tracking-[0.15em]`} value={code} maxLength={6} autoComplete="off" onChange={(e) => { setCode(e.target.value); setResult(null); }} placeholder="Mis. K7P2QX" />
          </Field>
          <button type="submit" className="rdg-btn-ghost w-full" disabled={busy}>Periksa kode</button>
        </form>
      </FrostCard>
    </Page>
  );
}
