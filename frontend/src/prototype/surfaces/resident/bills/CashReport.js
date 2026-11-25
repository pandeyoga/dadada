import React, { useCallback } from "react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import { getCashReport } from "../../../services/api/bills";
import { rupiah } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

function Bar({ label, value, max, color }) {
  return (
    <div className="flex items-center gap-2 text-[13px]">
      <span className="w-14 flex-none text-[color:var(--rdg-muted)]">{label}</span>
      <div className="rdg-progress flex-1" aria-hidden="true"><span style={{ width: `${Math.round((value / max) * 100)}%`, background: color }} /></div>
      <span className="w-[88px] flex-none text-right font-semibold">{rupiah(value)}</span>
    </div>
  );
}

/** W12: laporan kas kawasan yang transparan, per bulan (masuk, keluar, saldo, rincian). */
export default function CashReport() {
  const fetcher = useCallback(() => getCashReport(), []);
  const { data, error } = useLoad(fetcher, ["bills"]);
  const months = data ? [...data.months].reverse() : [];
  const max = data ? Math.max(...data.months.map((m) => Math.max(m.in, m.out))) : 1;
  return (
    <Page id="W12" title="Laporan kas kawasan" back="/app/warga/tagihan" nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <p className="text-[14px] leading-relaxed text-[color:var(--rdg-muted)]">
            Uang iuran IPL dipakai untuk keamanan, kebersihan, dan perawatan kawasan. Berikut catatan 6 bulan terakhir.
          </p>
          {months.map((m) => (
            <FrostCard key={m.month} data-month={m.month} className="space-y-2">
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-[16px] font-extrabold">{m.month}</h2>
                <p className="text-[13px] text-[color:var(--rdg-muted)]">Saldo <b className="text-[15px] text-rdg-ink900">{rupiah(m.balance)}</b></p>
              </div>
              <Bar label="Masuk" value={m.in} max={max} color="linear-gradient(90deg, #15874b, #0a8460)" />
              <Bar label="Keluar" value={m.out} max={max} color="linear-gradient(90deg, #b9741a, #8a5410)" />
              <ul className="space-y-1 border-t border-[color:var(--rdg-line)] pt-2 text-[13.5px]">
                {m.items.map((it) => (
                  <li key={it.label} className="flex justify-between gap-3">
                    <span>{it.label}</span>
                    <span className="flex-none font-semibold">{it.amount < 0 ? "−" : "+"}{rupiah(Math.abs(it.amount))}</span>
                  </li>
                ))}
              </ul>
            </FrostCard>
          ))}
        </>
      )}
    </Page>
  );
}
