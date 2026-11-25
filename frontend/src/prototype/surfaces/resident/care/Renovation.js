import React, { useCallback, useState } from "react";
import { Hammer } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import { Msg, Field, FIELD } from "../security/ui";
import { listRenovations, submitRenovation, RENOVATION_TYPES } from "../../../services/api/care";
import { now } from "../../../services/store";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const fetchAll = () => listRenovations();
const today = () => new Date(now()).toISOString().slice(0, 10);

function RenovationForm() {
  const [v, setV] = useState({ type: "", startDate: today(), endDate: today(), contractor: "" });
  const [problem, setProblem] = useState("");
  const [ok, setOk] = useState("");
  const set = (k) => (e) => setV((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    setProblem(""); setOk("");
    try {
      await submitRenovation(v);
      setV({ type: "", startDate: today(), endDate: today(), contractor: "" });
      setOk("Pengajuan terkirim. Pengelola akan memeriksa dan memberi kabar.");
    } catch (err) { setProblem(err.message); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <Field id="w24-jenis" label="Jenis renovasi">
        <select id="w24-jenis" value={v.type} onChange={set("type")} className={FIELD}>
          <option value="">Pilih jenis renovasi</option>
          {RENOVATION_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="w24-mulai" label="Mulai"><input id="w24-mulai" type="date" min={today()} value={v.startDate} onChange={set("startDate")} className={FIELD} /></Field>
        <Field id="w24-selesai" label="Selesai"><input id="w24-selesai" type="date" min={v.startDate} value={v.endDate} onChange={set("endDate")} className={FIELD} /></Field>
      </div>
      <Field id="w24-kontraktor" label="Kontraktor atau tukang">
        <input id="w24-kontraktor" value={v.contractor} onChange={set("contractor")} className={FIELD} placeholder="Contoh: CV Karya Mandiri" />
      </Field>
      <Msg error={problem} ok={ok} />
      <button type="submit" className="rdg-btn-primary w-full">Ajukan izin</button>
      <p className="text-[12.5px] text-[color:var(--rdg-muted)]">Pekerjaan hanya boleh dimulai setelah izin disetujui pengelola. Jam kerja tukang 08.00-17.00.</p>
    </form>
  );
}

/** W24: ajukan izin renovasi dan lihat statusnya. */
export default function Renovation() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["care"]);
  return (
    <Page id="W24" title="Izin renovasi" back="/app/warga/layanan" nav="resident">
      <FrostCard><RenovationForm /></FrostCard>
      <section aria-labelledby="w24-riwayat" className="space-y-2">
        <h2 id="w24-riwayat" className="text-[16px] font-extrabold">Pengajuan saya</h2>
        {!data && <Loading error={error} />}
        {data && data.length === 0 && <p className="text-[14px] text-[color:var(--rdg-muted)]">Belum ada pengajuan.</p>}
        {data && data.length > 0 && (
          <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
            {data.map((r) => (
              <ListRow key={r.id} icon={Hammer} title={r.type} subtitle={`${tanggal(r.startDate)} - ${tanggal(r.endDate)} · ${r.contractor}`} right={<StatusChip tone="warn">Diajukan</StatusChip>} />
            ))}
          </FrostCard>
        )}
      </section>
    </Page>
  );
}
