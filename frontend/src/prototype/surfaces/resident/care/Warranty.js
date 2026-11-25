import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import StatusChip from "../../../components/StatusChip";
import Sheet from "../../../components/Sheet";
import { Msg, Field, FIELD } from "../security/ui";
import { listWarranty, claimWarranty } from "../../../services/api/care";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const fetchAll = () => listWarranty();

export function remainingText(w) {
  if (!w.active) return "Masa garansi berakhir";
  const m = w.remainingMonths;
  if (m >= 12) return `Sisa ${Math.floor(m / 12)} tahun${m % 12 ? ` ${m % 12} bulan` : ""}`;
  return m >= 1 ? `Sisa ${m} bulan` : `Sisa ${w.remainingDays} hari`;
}

function ClaimForm({ item, onDone }) {
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");
  const [sent, setSent] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setProblem("");
    try { await claimWarranty({ itemId: item.id, description: text }); setSent(true); } catch (err) { setProblem(err.message); }
  };
  if (sent) {
    return (
      <div className="space-y-3">
        <Msg ok="Klaim terkirim. Teknisi akan memeriksa; pantau perkembangannya di Lapor kerusakan." />
        <Link to="/app/warga/lapor" className="rdg-btn-primary w-full">Lihat tiket saya</Link>
        <button type="button" className="rdg-btn-ghost w-full" onClick={onDone}>Tutup</button>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <p className="text-[14px] text-[color:var(--rdg-muted)]">{item.note}</p>
      <Field id="w22-desk" label="Ceritakan kerusakannya">
        <textarea id="w22-desk" rows={3} value={text} onChange={(e) => setText(e.target.value)} className={`${FIELD} py-2`} placeholder="Contoh: Genteng bocor di kamar belakang saat hujan" />
      </Field>
      <Msg error={problem} />
      <button type="submit" className="rdg-btn-primary w-full">Kirim klaim</button>
    </form>
  );
}

/** W22: garansi per bagian rumah dan klaim. */
export default function Warranty() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["care"]);
  const [target, setTarget] = useState(null);
  return (
    <Page id="W22" title="Garansi rumah" back="/app/warga/layanan" nav="resident">
      {!data && <Loading error={error} />}
      {data && data.map((w) => (
        <FrostCard key={w.id} className="space-y-2">
          <div className="flex items-start gap-3">
            <span className="rdg-row-icon"><ShieldCheck size={20} aria-hidden="true" /></span>
            <div className="min-w-0 flex-1">
              <h2 className="text-[15.5px] font-extrabold leading-snug">{w.part}</h2>
              <p className="text-[13px] text-[color:var(--rdg-muted)]">{w.note}</p>
            </div>
            <StatusChip tone={w.active ? "ok" : "danger"}>{w.active ? "Aktif" : "Berakhir"}</StatusChip>
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="text-[13.5px] font-semibold">{remainingText(w)}<span className="font-normal text-[color:var(--rdg-muted)]">{` · sampai ${tanggal(w.endsAt)}`}</span></p>
            <button type="button" className="rdg-btn-ghost !min-h-[44px] !px-3 flex-none" disabled={!w.active} aria-label={`Klaim ${w.part}`} onClick={() => setTarget(w)}>Klaim</button>
          </div>
        </FrostCard>
      ))}
      <Sheet open={Boolean(target)} onClose={() => setTarget(null)} title={target ? `Klaim ${target.part}` : "Klaim garansi"}>
        {target && <ClaimForm item={target} onDone={() => setTarget(null)} />}
      </Sheet>
    </Page>
  );
}
