import React, { useCallback } from "react";
import { FrostCard } from "../../components/GlassCard";
import StatusChip from "../../components/StatusChip";
import EmptyState from "../../components/EmptyState";
import { listReferrals } from "../../services/api/partner";
import { tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import PartnerPage, { Loading } from "./PartnerPage";

const TONE = { lead: "neutral", booking: "info", akad: "ok" };

/** M4: pipeline rujukan — Calon → Booking → Akad, lengkap dengan jumlah per tahap. */
export default function PartnerReferrals() {
  const fetcher = useCallback(() => listReferrals(), []);
  const { data, error } = useLoad(fetcher, ["partner"]);
  return (
    <PartnerPage id="M4" title="Rujukan saya">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <ul className="grid grid-cols-3 gap-2" aria-label="Ringkasan tahap">
            {data.map((g) => (
              <li key={g.stage}>
                <FrostCard className="text-center !p-3">
                  <p className="text-[24px] font-extrabold leading-none" data-testid={`count-${g.stage}`}>{g.count}</p>
                  <p className="mt-1 text-[13px] font-semibold text-[color:var(--rdg-muted)]">{g.label}</p>
                </FrostCard>
              </li>
            ))}
          </ul>
          {data.map((g) => (
            <section key={g.stage} aria-labelledby={`m4-${g.stage}`}>
              <h2 id={`m4-${g.stage}`} className="mb-2 flex items-center gap-2 text-[16px] font-extrabold">
                {g.label} <StatusChip tone={TONE[g.stage]} icon={null}>{`${g.count} orang`}</StatusChip>
              </h2>
              {g.items.length === 0 ? (
                <EmptyState title="Belum ada" body="Bagikan tautan unit untuk mendapat rujukan." />
              ) : (
                <FrostCard className="!p-2">
                  <ul className="divide-y divide-[color:var(--rdg-line)]">
                    {g.items.map((r) => (
                      <li key={r.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                        <span className="min-w-0">
                          <span className="block truncate text-[15px] font-bold">{r.name}</span>
                          <span className="block text-[13px] text-[color:var(--rdg-muted)]">{r.phone}</span>
                        </span>
                        <span className="flex-none text-[13px] text-[color:var(--rdg-muted)]">{tanggal(r.at)}</span>
                      </li>
                    ))}
                  </ul>
                </FrostCard>
              )}
            </section>
          ))}
        </>
      )}
    </PartnerPage>
  );
}
