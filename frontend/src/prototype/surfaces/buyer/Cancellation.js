import React, { useCallback } from "react";
import { ShieldCheck } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import EmptyState from "../../components/EmptyState";
import { getCancellation } from "../../services/api/buyer";
import useLoad from "./useLoad";
import Page, { Loading } from "./Page";

export default function Cancellation() {
  const fetcher = useCallback(() => getCancellation(), []);
  const { data } = useLoad(fetcher);
  return (
    <Page id="P7" title="Pembatalan & refund" back="/app/pembeli/akun">
      {!data && <Loading />}
      {data && (
        <>
          <FrostCard><EmptyState icon={ShieldCheck} title="Tidak ada pengajuan" body={data.message} /></FrostCard>
          <FrostCard>
            <h2 className="text-[16px] font-extrabold">Aturan pembatalan</h2>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-[14px] leading-relaxed text-[color:var(--rdg-muted)]">
              {data.rules.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </FrostCard>
        </>
      )}
    </Page>
  );
}
