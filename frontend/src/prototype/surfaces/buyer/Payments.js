import React, { useCallback } from "react";
import { Link } from "react-router-dom";
import { Receipt, CircleCheck } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import ScreenHeader from "../../components/ScreenHeader";
import StatusChip from "../../components/StatusChip";
import ListRow from "../../components/ListRow";
import { listInstallments } from "../../services/api/buyer";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "./useLoad";
import { Loading } from "./Page";

const CHIP = { paid: ["ok", "Lunas"], pending: ["warn", "Menunggu pembayaran"], unpaid: ["neutral", "Belum dibayar"] };

export default function Payments() {
  const fetcher = useCallback(() => listInstallments(), []);
  const { data } = useLoad(fetcher);
  const dps = data ? data.filter((i) => i.id.startsWith("dp-")) : [];
  const total = dps.reduce((a, i) => a + i.amount, 0);
  const paid = dps.filter((i) => i.status === "paid").reduce((a, i) => a + i.amount, 0);
  const pct = total ? Math.round((paid / total) * 100) : 0;
  const next = data && data.find((i) => i.status !== "paid");
  const history = data ? data.filter((i) => i.status === "paid").sort((a, b) => Date.parse(b.paidAt) - Date.parse(a.paidAt)) : [];
  return (
    <MobileShell nav="buyer">
      <Screen id="P4">
        <Hero className="pb-10">
          <ScreenHeader title="Bayar" back="/app/pembeli" />
          <GlassCard className="mt-1">
            <p className="text-[13.5px] font-semibold text-white/90">Uang muka terbayar</p>
            <p className="text-[30px] font-extrabold leading-tight tracking-[-0.02em]">{rupiah(paid)}</p>
            <p className="text-[13.5px] text-white/90">dari {rupiah(total)} · dibayar ke developer</p>
            <div className="rdg-stepper--dark mt-3">
              <div className="rdg-progress" role="progressbar" aria-label="Uang muka terbayar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
                <span style={{ width: `${pct}%` }} />
              </div>
            </div>
            {next && (
              <Link to={`/app/pembeli/bayar/${next.id}`} className="rdg-btn-primary mt-4 w-full">
                Bayar {next.label.split(" dari")[0].toLowerCase()} · {rupiah(next.amount)}
              </Link>
            )}
          </GlassCard>
        </Hero>
        <div className="space-y-5 px-5 pt-5">
          {!data && <Loading />}
          {data && (
            <>
              <section aria-labelledby="p4-jadwal">
                <h2 id="p4-jadwal" className="mb-2 text-[17px] font-extrabold">Jadwal cicilan</h2>
                <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
                  {data.map((i) => {
                    const [tone, text] = CHIP[i.status] || CHIP.unpaid;
                    return (
                      <ListRow
                        key={i.id}
                        icon={i.status === "paid" ? CircleCheck : Receipt}
                        title={i.label}
                        subtitle={`${rupiah(i.amount)} · ${i.status === "paid" ? tanggal(i.paidAt) : `tempo ${tanggal(i.dueDate)}`}`}
                        right={<StatusChip tone={tone}>{text}</StatusChip>}
                        to={i.status !== "paid" ? `/app/pembeli/bayar/${i.id}` : undefined}
                      />
                    );
                  })}
                </FrostCard>
              </section>
              <section aria-labelledby="p4-riwayat">
                <h2 id="p4-riwayat" className="mb-2 text-[17px] font-extrabold">Riwayat pembayaran</h2>
                <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
                  {history.length === 0 && <p className="p-4 text-[14px] text-[color:var(--rdg-muted)]">Belum ada pembayaran.</p>}
                  {history.map((i) => (
                    <ListRow
                      key={i.id}
                      icon={Receipt}
                      title={i.label}
                      subtitle={`${tanggal(i.paidAt)}${i.receipt ? " · ada kuitansi" : ""}`}
                      right={<span className="text-[14px] font-bold">{rupiah(i.amount)}</span>}
                    />
                  ))}
                </FrostCard>
              </section>
            </>
          )}
        </div>
      </Screen>
    </MobileShell>
  );
}
