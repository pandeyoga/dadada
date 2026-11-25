import React, { useCallback } from "react";
import { Zap, Droplets, Lightbulb, TrendingUp, TrendingDown, Info } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import { getEnergy } from "../../../services/api/account";
import useLoad from "../../../lib/useLoad";

const fetchEnergy = () => getEnergy();
const fmt = (n) => String(n).replace(".", ",");

function Bars({ months, field, unit, label }) {
  const max = Math.max(...months.map((m) => m[field]));
  return (
    <figure aria-label={label}>
      <div className="flex h-36 items-end gap-2" role="list">
        {months.map((m, i) => {
          const last = i === months.length - 1;
          return (
            <div key={m.month} role="listitem" aria-label={`${m.month}: ${fmt(m[field])} ${unit}`} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[11.5px] font-bold text-rdg-ink900">{fmt(m[field])}</span>
              <span className="w-full rounded-t-lg" style={{ height: `${Math.max(8, (m[field] / max) * 100)}%`, background: last ? "linear-gradient(180deg, #209f59, #01916f)" : "#b9d8d3" }} />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex gap-2" aria-hidden="true">
        {months.map((m) => <span key={m.month} className="flex-1 text-center text-[12px] font-semibold text-[color:var(--rdg-muted)]">{m.month}</span>)}
      </div>
    </figure>
  );
}

/** W26: pemakaian listrik dan air 6 bulan terakhir (perkiraan simulasi) + tips hemat. */
export default function Energy() {
  const fetcher = useCallback(fetchEnergy, []);
  const { data, error } = useLoad(fetcher, ["security"]);
  const m = data && data.months;
  const cur = m && m[m.length - 1];
  const prev = m && m[m.length - 2];
  const delta = cur && prev ? Math.round(((cur.kwh - prev.kwh) / prev.kwh) * 100) : 0;
  return (
    <Page id="W26" title="Energi rumah" back="/app/warga/layanan" nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <FrostCard>
            <p className="flex items-center gap-1.5 text-[13px] font-semibold text-[color:var(--rdg-muted)]"><Zap size={15} aria-hidden="true" /> Listrik bulan ini</p>
            <p className="text-[32px] font-extrabold leading-tight tracking-[-0.02em]">{cur.kwh} kWh</p>
            <p className="flex items-center gap-1.5 text-[13.5px] font-semibold">
              {delta >= 0 ? <TrendingUp size={16} aria-hidden="true" className="text-[color:var(--rdg-sos-ink)]" /> : <TrendingDown size={16} aria-hidden="true" className="text-rdg-forest" />}
              {`${Math.abs(delta)} % ${delta >= 0 ? "lebih banyak" : "lebih hemat"} dari bulan lalu (${prev.kwh} kWh)`}
            </p>
            <div className="mt-4"><Bars months={m} field="kwh" unit="kWh" label="Pemakaian listrik 6 bulan (kWh)" /></div>
          </FrostCard>
          <FrostCard>
            <p className="flex items-center gap-1.5 text-[13px] font-semibold text-[color:var(--rdg-muted)]"><Droplets size={15} aria-hidden="true" /> Air bulan ini</p>
            <p className="text-[26px] font-extrabold leading-tight">{fmt(cur.waterM3)} m3</p>
            <div className="mt-3"><Bars months={m} field="waterM3" unit="m3" label="Pemakaian air 6 bulan (m3)" /></div>
          </FrostCard>
          <p className="flex items-start gap-1.5 text-[12.5px] text-[color:var(--rdg-muted)]"><Info size={14} aria-hidden="true" className="mt-0.5 flex-none" /> Perkiraan dari meter pintar (simulasi). Angka contoh, belum tersambung ke meter sungguhan.</p>
          <section aria-labelledby="w26-tips" className="space-y-2">
            <h2 id="w26-tips" className="text-[16px] font-extrabold">Tips hemat</h2>
            <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
              {data.tips.map((t) => (
                <div key={t} className="flex items-start gap-3 p-3"><span className="rdg-row-icon"><Lightbulb size={18} aria-hidden="true" /></span><p className="text-[14px] leading-snug">{t}</p></div>
              ))}
            </FrostCard>
          </section>
        </>
      )}
    </Page>
  );
}
