import React, { useState } from "react";
import { Route, Plus } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import EmptyState from "../../components/EmptyState";
import { logPatrol } from "../../services/api/guard";
import { useProto } from "../../services/useStore";
import { jam, tanggal } from "../../lib/format";
import Page from "../buyer/Page";
import { FIELD, Field, Msg, byRecent } from "../resident/security/ui";
import SosBanner from "./SosBanner";

function AddForm({ options }) {
  const [checkpoint, setCheckpoint] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setOk("");
    try {
      await logPatrol({ checkpoint, note });
      setCheckpoint("");
      setNote("");
      setOk("Patroli tercatat");
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <FrostCard>
      <form onSubmit={submit} className="space-y-3">
        <h2 className="text-[17px] font-extrabold">Catat patroli</h2>
        <Field id="pt-cp" label="Titik patroli">
          <input id="pt-cp" list="pt-options" className={FIELD} value={checkpoint} onChange={(e) => setCheckpoint(e.target.value)} autoComplete="off" placeholder="Mis. Gerbang utama" />
          <datalist id="pt-options">{options.map((o) => <option key={o} value={o} />)}</datalist>
        </Field>
        <Field id="pt-note" label="Catatan"><input id="pt-note" className={FIELD} value={note} onChange={(e) => setNote(e.target.value)} autoComplete="off" placeholder="Mis. situasi aman" /></Field>
        <Msg error={error} ok={ok} />
        <button type="submit" className="rdg-btn-primary w-full"><Plus size={18} aria-hidden="true" /> Catat patroli</button>
      </form>
    </FrostCard>
  );
}

export default function Patrol() {
  const patrols = useProto((s) => s.security.patrols);
  const options = useProto((s) => s.security.cameras.areaList);
  const list = byRecent(patrols || []);
  return (
    <Page id="S5" title="Log patroli" back="/app/satpam" nav="satpam">
      <SosBanner />
      <AddForm options={options} />
      <FrostCard>
        <h2 className="text-[17px] font-extrabold">Riwayat patroli</h2>
        {list.length === 0 ? (
          <EmptyState icon={Route} title="Belum ada patroli" body="Catat titik yang sudah diperiksa." />
        ) : (
          <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
            {list.map((p) => (
              <li key={p.id} className="rdg-row">
                <span className="rdg-row-icon"><Route size={20} aria-hidden="true" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-semibold text-rdg-ink900">{p.checkpoint}</span>
                  <span className="block text-[13px] text-[color:var(--rdg-muted)]">{`${tanggal(p.at)} · ${jam(p.at)} WIB · ${p.by}`}</span>
                  {p.note && <span className="block text-[13.5px]">{p.note}</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </FrostCard>
    </Page>
  );
}
