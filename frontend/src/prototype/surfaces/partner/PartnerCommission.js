import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { FrostCard } from "../../components/GlassCard";
import StatusChip from "../../components/StatusChip";
import { Field, FIELD, Msg } from "../resident/security/ui";
import { getCommission, requestPayout } from "../../services/api/partner";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import PartnerPage, { Loading } from "./PartnerPage";

/** M5: saldo komisi, riwayat komisi, pengajuan pencairan ke rekening terdaftar (simulasi). */
export default function PartnerCommission() {
  const fetcher = useCallback(() => getCommission(), []);
  const { data, error } = useLoad(fetcher, ["partner"]);
  const [amount, setAmount] = useState("");
  const [problem, setProblem] = useState("");
  const [ok, setOk] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setProblem(""); setOk("");
    try {
      await requestPayout(Number(String(amount).replace(/\D/g, "")));
      setAmount("");
      setOk("Pencairan diajukan dan sedang diproses.");
    } catch (err) { setProblem(err.message); }
  };

  return (
    <PartnerPage id="M5" title="Komisi & pencairan">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <FrostCard>
            <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Saldo bisa dicairkan</p>
            <p className="text-[30px] font-extrabold leading-tight tracking-[-0.02em]" data-testid="balance">{rupiah(data.balance)}</p>
            <p className="mt-1 text-[13px] text-[color:var(--rdg-muted)]">{`Komisi sedang diproses: ${rupiah(data.pending)}`}</p>
          </FrostCard>
          <FrostCard>
            <h2 className="text-[16px] font-extrabold">Ajukan pencairan</h2>
            {!data.registered || !data.bank ? (
              <>
                <p className="mt-1 text-[13.5px] text-[color:var(--rdg-muted)]">Lengkapi pendaftaran dan rekening dulu sebelum mengajukan pencairan.</p>
                <Link to="/app/mitra/daftar" className="rdg-btn-primary mt-3 w-full">Lengkapi pendaftaran</Link>
              </>
            ) : (
              <>
                <p className="mt-1 text-[13.5px] text-[color:var(--rdg-muted)]">{`Ke ${data.bank.bankName} · ${data.bank.accountNumber} a.n. ${data.bank.holder}`}</p>
                <form onSubmit={submit} className="mt-3 space-y-3" noValidate>
                  <Field id="m5-amt" label="Nominal (Rp)">
                    <input id="m5-amt" className={FIELD} inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="500000" />
                  </Field>
                  <Msg error={problem} ok={ok} />
                  <button type="submit" className="rdg-btn-primary w-full">Ajukan pencairan</button>
                </form>
                <p className="mt-2 text-[12.5px] text-[color:var(--rdg-muted)]">Simulasi: tidak ada uang yang benar-benar dipindahkan.</p>
              </>
            )}
          </FrostCard>
          <section aria-labelledby="m5-po">
            <h2 id="m5-po" className="mb-2 text-[16px] font-extrabold">Pencairan</h2>
            <FrostCard className="!p-2">
              {data.payouts.length === 0 && <p className="px-3 py-3 text-[14px] text-[color:var(--rdg-muted)]">Belum ada pencairan.</p>}
              <ul className="divide-y divide-[color:var(--rdg-line)]" aria-label="Daftar pencairan">
                {data.payouts.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                    <span><span className="block text-[15px] font-bold">{rupiah(p.amount)}</span><span className="block text-[13px] text-[color:var(--rdg-muted)]">{tanggal(p.at)}</span></span>
                    <StatusChip tone="warn">Diproses</StatusChip>
                  </li>
                ))}
              </ul>
            </FrostCard>
          </section>
          <section aria-labelledby="m5-cm">
            <h2 id="m5-cm" className="mb-2 text-[16px] font-extrabold">Riwayat komisi</h2>
            <FrostCard className="!p-2">
              <ul className="divide-y divide-[color:var(--rdg-line)]">
                {data.commissions.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                    <span className="min-w-0"><span className="block text-[14.5px] font-bold leading-snug">{c.title}</span><span className="block text-[13px] text-[color:var(--rdg-muted)]">{tanggal(c.at)}</span></span>
                    <span className="flex-none text-right"><span className="block text-[15px] font-extrabold">{rupiah(c.amount)}</span><StatusChip tone={c.status === "cair" ? "ok" : "warn"} icon={null}>{c.status === "cair" ? "Cair" : "Diproses"}</StatusChip></span>
                  </li>
                ))}
              </ul>
            </FrostCard>
          </section>
        </>
      )}
    </PartnerPage>
  );
}
