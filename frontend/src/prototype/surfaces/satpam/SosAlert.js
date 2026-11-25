import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Siren, ShieldCheck, Navigation, CircleCheck } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import ScreenHeader from "../../components/ScreenHeader";
import EmptyState from "../../components/EmptyState";
import { acceptSos, resolveSos, GUARD_NAME } from "../../services/api/guard";
import { sosLabel } from "../../services/api/sos";
import { jam } from "../../lib/format";
import { useProto } from "../../services/useStore";
import useActiveSos from "./useActiveSos";

function Alert({ event }) {
  const resident = useProto((s) => s.world.resident.name);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const accepted = event.status === "accepted";
  const run = async (fn) => {
    setBusy(true);
    setError("");
    try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="rdg-sos-screen" role="alert">
      <p className="flex items-center gap-2 text-[15px] font-extrabold tracking-wide"><Siren size={20} aria-hidden="true" /> DARURAT</p>
      <h1 className="mt-3 text-[40px] font-extrabold leading-none">{sosLabel(event.type)}</h1>
      <p className="mt-3 text-[24px] font-bold">{`Blok ${event.unit}`}</p>
      <p className="text-[16px]">{`${resident} · masuk pukul ${jam(event.createdAt)} WIB`}</p>
      <p className="mt-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-[14.5px] font-bold text-[color:var(--rdg-sos-ink)]">
        {accepted ? <CircleCheck size={16} aria-hidden="true" /> : <Navigation size={16} aria-hidden="true" />}
        {accepted ? `Diterima Pak ${event.acceptedBy} · ${jam(event.acceptedAt)}` : "Menunggu diterima"}
      </p>
      <div className="mt-8 space-y-3">
        {accepted && (
          <div>
            <label htmlFor="sos-note" className="block text-[14px] font-bold">Catatan (opsional)</label>
            <textarea
              id="sos-note" rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Mis. sudah dicek, situasi aman"
              className="mt-1 block w-full rounded-xl border-0 bg-white p-3 text-[15px] text-rdg-ink900"
            />
          </div>
        )}
        {error && <p role="alert" className="rounded-xl bg-white p-3 text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{error}</p>}
        {accepted ? (
          <button type="button" className="rdg-btn-light w-full" disabled={busy} onClick={() => run(() => resolveSos(event.id, note))}><ShieldCheck size={20} aria-hidden="true" /> Tandai selesai</button>
        ) : (
          <button type="button" className="rdg-btn-light w-full" disabled={busy} onClick={() => run(() => acceptSos(event.id, GUARD_NAME))}><Navigation size={20} aria-hidden="true" /> Terima &amp; menuju</button>
        )}
      </div>
    </div>
  );
}

export default function SosAlert() {
  const event = useActiveSos();
  return (
    <MobileShell nav="satpam">
      <Screen id="S2">
        {event ? (
          <Alert key={event.id} event={event} />
        ) : (
          <>
            <ScreenHeader title="Peringatan SOS" back="/app/satpam" variant="light" />
            <EmptyState icon={ShieldCheck} title="Tidak ada laporan darurat aktif" body="Laporan SOS dari warga akan muncul di sini tanpa perlu muat ulang.">
              <Link to="/app/satpam" className="rdg-btn-primary">Kembali ke pos</Link>
            </EmptyState>
          </>
        )}
      </Screen>
    </MobileShell>
  );
}
