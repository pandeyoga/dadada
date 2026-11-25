import React, { useCallback } from "react";
import { Landmark } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import StatusChip from "../../components/StatusChip";
import { getKpr } from "../../services/api/buyer";
import { rupiah } from "../../lib/format";
import useLoad from "./useLoad";
import Page, { Loading } from "./Page";

export default function Kpr() {
  const fetcher = useCallback(() => getKpr(), []);
  const { data: k } = useLoad(fetcher);
  const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
  return (
    <Page id="P6" title="Status KPR">
      {!k && <Loading />}
      {k && (
        <>
          <FrostCard>
            <div className="flex items-center gap-3">
              <span className="rdg-row-icon"><Landmark size={20} aria-hidden="true" /></span>
              <div className="min-w-0 flex-1">
                <p className="text-[15px] font-bold">{k.product}</p>
                <p className="text-[13px] text-[color:var(--rdg-muted)]">Pokok {rupiah(k.principal)} · bunga {k.rate} % per tahun</p>
              </div>
            </div>
            <div className="mt-3"><StatusChip tone="warn">{cap(k.status)}</StatusChip></div>
            <p className="mt-2 text-[13.5px] leading-relaxed text-[color:var(--rdg-muted)]">Pengajuan KPR diproses setelah rumah selesai dan siap akad.</p>
          </FrostCard>
          <FrostCard>
            <h2 className="text-[16px] font-extrabold">Simulasi angsuran</h2>
            <p className="mt-2 text-[32px] font-extrabold leading-none tracking-[-0.02em]">{rupiah(k.monthly)}<span className="text-[15px] font-bold text-[color:var(--rdg-muted)]"> /bulan</span></p>
            <p className="mt-1 text-[14px] font-semibold">× {k.tenorYears} tahun ({k.totalMonths} bulan)</p>
            <p className="mt-1 text-[13.5px] text-[color:var(--rdg-muted)]">{k.note}.</p>
            <dl className="mt-3 divide-y divide-[color:var(--rdg-line)] text-[14px]">
              {[["Harga rumah", "Rp166.000.000"], ["Uang muka (dibayar ke developer)", "Rp5.000.000"], ["Pokok KPR", rupiah(k.principal)], ["Tenor", `${k.tenorYears} tahun`]].map(([a, b]) => (
                <div key={a} className="flex justify-between gap-3 py-2"><dt className="text-[color:var(--rdg-muted)]">{a}</dt><dd className="font-bold text-right">{b}</dd></div>
              ))}
            </dl>
            <p className="mt-3 text-[12.5px] text-[color:var(--rdg-muted)]">Angka di atas adalah simulasi, bukan penawaran bank.</p>
          </FrostCard>
        </>
      )}
    </Page>
  );
}
