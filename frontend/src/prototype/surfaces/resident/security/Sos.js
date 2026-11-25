import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Phone, Siren, UserCog, ShieldCheck, Loader } from "lucide-react";
import MobileShell from "../../../components/MobileShell";
import Screen from "../../../components/Screen";
import Hero from "../../../components/Hero";
import { GlassCard, FrostCard } from "../../../components/GlassCard";
import ScreenHeader from "../../../components/ScreenHeader";
import HoldToConfirm from "../../../components/HoldToConfirm";
import Stepper from "../../../components/Stepper";
import Sheet from "../../../components/Sheet";
import ListRow from "../../../components/ListRow";
import { SOS_TYPES, cancelSos, sendSos, sosLabel } from "../../../services/api/sos";
import { now } from "../../../services/store";
import { useProto } from "../../../services/useStore";
import { Msg, jam } from "./ui";

const SHOWN_AFTER_DONE_MS = 5 * 60000;
const STEPS = ["Terkirim", "Diterima", "Selesai"];
const STEP_OF = { sent: 0, accepted: 1, resolved: 2 };
const guardName = (n) => String(n || "satpam").replace(/^pak\s+/i, "");

function Contacts({ contacts }) {
  return (
    <FrostCard>
      <div className="flex items-center justify-between">
        <h2 className="text-[17px] font-extrabold">Kontak darurat</h2>
        <Link to="/app/warga/sos/kontak" className="flex items-center gap-1 text-[14px] font-bold text-rdg-forest"><UserCog size={16} aria-hidden="true" /> Kelola</Link>
      </div>
      <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
        {contacts.map((c) => (
          <li key={c.id}>
            <ListRow
              icon={Phone} title={c.name} subtitle={`${c.role} · ${c.phone}`}
              right={<a href={`tel:${c.phone.replace(/\D/g, "")}`} className="rdg-btn-ghost !min-h-[40px] !px-4 !text-[13.5px]" aria-label={`Telepon ${c.name}`}>Telepon</a>}
            />
          </li>
        ))}
      </ul>
    </FrostCard>
  );
}

function TypeSheet({ open, onClose, onSend }) {
  const [type, setType] = useState("kemalingan");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    setError("");
    try {
      await onSend(type);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };
  return (
    <Sheet open={open} onClose={onClose} title="Pilih jenis darurat">
      <div role="radiogroup" aria-label="Jenis darurat" className="grid grid-cols-2 gap-2.5">
        {SOS_TYPES.map((o) => (
          <label key={o.id} className={`rdg-type-opt ${type === o.id ? "is-on" : ""}`}>
            <input type="radio" name="sos-type" value={o.id} checked={type === o.id} onChange={() => setType(o.id)} />
            <span>{o.label}</span>
          </label>
        ))}
      </div>
      <div className="mt-4 space-y-3">
        <Msg error={error} />
        <button type="button" className="rdg-btn-sos w-full" disabled={busy} onClick={send}><Siren size={19} aria-hidden="true" /> Kirim laporan</button>
        <p className="text-center text-[12.5px] text-[color:var(--rdg-muted)]">Laporan palsu dapat dikenai sanksi pengelola</p>
      </div>
    </Sheet>
  );
}

function StatusView({ event, onDone }) {
  const [error, setError] = useState("");
  const st = event.status;
  const head = {
    sent: ["Menunggu satpam…", "Laporan Anda sudah masuk. Satpam sedang dihubungi."],
    accepted: [`Pak ${guardName(event.acceptedBy)} menuju rumah Anda`, "Tetap di tempat yang aman dan tunggu bantuan."],
    resolved: ["Selesai", "Laporan ini sudah ditangani. Terima kasih."],
  }[st];
  const cancel = async () => {
    setError("");
    try { await cancelSos(event.id); } catch (e) { setError(e.message); }
  };
  return (
    <GlassCard role="status" aria-live="polite">
      <div className="flex items-center gap-3.5">
        <span className={`grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white/15 text-rdg-lime ${st === "sent" ? "rdg-sos-pulse" : ""}`}>
          {st === "resolved" ? <ShieldCheck size={28} aria-hidden="true" /> : st === "sent" ? <Loader size={28} aria-hidden="true" /> : <Siren size={28} aria-hidden="true" />}
        </span>
        <div className="min-w-0">
          <p className="text-[13px] text-white/90">SOS {sosLabel(event.type).toLowerCase()} · {jam(event.createdAt)}</p>
          <h2 className="text-[21px] font-extrabold leading-tight">{head[0]}</h2>
        </div>
      </div>
      <p className="mt-3 text-[14px] text-white/90">{head[1]}</p>
      <div className="mt-4"><Stepper steps={STEPS} current={STEP_OF[st]} variant="dark" /></div>
      {error && <div className="mt-3 rounded-xl bg-white p-3"><Msg error={error} /></div>}
      {st === "sent" && <button type="button" className="rdg-btn-ghost mt-4 w-full" onClick={cancel}>Batalkan laporan</button>}
      {st === "resolved" && <button type="button" className="rdg-btn-ghost mt-4 w-full" onClick={onDone}>Tutup</button>}
    </GlassCard>
  );
}

export default function Sos() {
  const sos = useProto((s) => s.security.sos);
  const contacts = useProto((s) => s.security.contacts);
  const [sheet, setSheet] = useState(false);
  const [dismissed, setDismissed] = useState(null);
  const event = useMemo(() => {
    const e = sos[0];
    if (!e || e.id === dismissed) return null;
    if (e.status === "sent" || e.status === "accepted") return e;
    return e.status === "resolved" && now() - Date.parse(e.resolvedAt) < SHOWN_AFTER_DONE_MS ? e : null;
  }, [sos, dismissed]);
  const send = async (type) => {
    await sendSos(type);
    setSheet(false);
  };
  return (
    <MobileShell nav="resident">
      <Screen id="W8">
        <Hero className="pb-8">
          <ScreenHeader title="SOS darurat" back="/app/warga" />
          {event ? (
            <StatusView event={event} onDone={() => setDismissed(event.id)} />
          ) : (
            <div className="pb-2 text-center">
              <h2 className="text-[20px] font-extrabold">Butuh bantuan segera?</h2>
              <p className="mx-auto mb-4 mt-1 max-w-[290px] text-[14px] text-white/90">Tahan tombol SOS selama 3 detik. Satpam dan keluarga langsung diberi tahu.</p>
              <HoldToConfirm durationMs={3000} label="SOS" onConfirm={() => setSheet(true)} />
            </div>
          )}
          <p className="mt-4 text-center text-[12.5px] text-white/90">Laporan palsu dapat dikenai sanksi pengelola</p>
        </Hero>
        <div className="space-y-4 px-5 pt-5">
          <Contacts contacts={contacts} />
        </div>
        {sheet && <TypeSheet open onClose={() => setSheet(false)} onSend={send} />}
      </Screen>
    </MobileShell>
  );
}
