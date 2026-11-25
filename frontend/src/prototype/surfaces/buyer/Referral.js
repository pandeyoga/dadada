import React, { useCallback, useState } from "react";
import { Gift, Share2, UserPlus } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import ListRow from "../../components/ListRow";
import StatusChip from "../../components/StatusChip";
import EmptyState from "../../components/EmptyState";
import CopyButton from "../../components/pay/CopyButton";
import { getReferral, inviteFriend } from "../../services/api/buyer";
import { useProto } from "../../services/useStore";
import useLoad from "../../lib/useLoad";
import Page, { Loading } from "./Page";

const input = "mt-1 block min-h-[46px] w-full rounded-xl border border-[color:var(--rdg-line)] bg-white px-3 text-[15px]";

/** P10 (pembeli) dan W29 (warga): satu layar, menu bawah mengikuti mode. */
export default function Referral() {
  const mode = useProto((s) => s.mode);
  const resident = mode === "resident";
  const fetcher = useCallback(() => getReferral(), []);
  const { data, error } = useLoad(fetcher);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [msg, setMsg] = useState({ ok: false, text: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await inviteFriend({ name, phone });
      setName(""); setPhone("");
      setMsg({ ok: true, text: "Undangan dicatat. Bagikan kode Anda lewat WhatsApp." });
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  };
  const share = data ? `https://wa.me/?text=${encodeURIComponent(`Halo, ayo lihat rumah di Estora Residence. Pakai kode ${data.code} saat booking.`)}` : "#";
  return (
    <Page id="P10" title="Ajak teman" nav={resident ? "resident" : "buyer"} back={resident ? "/app/warga" : "/app/pembeli"}>
      {!data && <Loading error={error} />}
      {data && (
        <>
          <FrostCard>
            <div className="flex items-center gap-3">
              <span className="rdg-row-icon"><Gift size={20} aria-hidden="true" /></span>
              <p className="text-[14px] font-semibold">{data.reward}</p>
            </div>
            <p className="mt-3 text-[13px] font-semibold text-[color:var(--rdg-muted)]">Kode rujukan Anda</p>
            <p className="text-[30px] font-extrabold tracking-[0.04em]">{data.code}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <CopyButton text={data.code} label="Salin kode" />
              <a href={share} target="_blank" rel="noopener noreferrer" className="rdg-btn-ghost"><Share2 size={17} aria-hidden="true" /> Bagikan WhatsApp</a>
            </div>
          </FrostCard>
          <FrostCard>
            <h2 className="text-[16px] font-extrabold">Undang teman</h2>
            <form onSubmit={submit} className="mt-2 space-y-3">
              <label className="block text-[13.5px] font-semibold">Nama teman<input className={input} value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" /></label>
              <label className="block text-[13.5px] font-semibold">Nomor WhatsApp<input className={input} value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" placeholder="0812…" /></label>
              {msg.text && <p role={msg.ok ? "status" : "alert"} className={`text-[13.5px] font-semibold ${msg.ok ? "text-rdg-forest" : "text-[color:var(--rdg-sos-ink)]"}`}>{msg.text}</p>}
              <button type="submit" className="rdg-btn-primary w-full" disabled={busy}><UserPlus size={17} aria-hidden="true" /> Kirim undangan</button>
            </form>
          </FrostCard>
          <section aria-labelledby="p10-list">
            <h2 id="p10-list" className="mb-2 text-[17px] font-extrabold">Status rujukan</h2>
            <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
              {data.invited.length === 0 && <EmptyState title="Belum ada rujukan" body="Teman yang Anda undang akan muncul di sini." />}
              {data.invited.map((f) => <ListRow key={f.id} icon={UserPlus} title={f.name} subtitle={f.phone} right={<StatusChip tone="info">Diundang</StatusChip>} />)}
            </FrostCard>
          </section>
        </>
      )}
    </Page>
  );
}
