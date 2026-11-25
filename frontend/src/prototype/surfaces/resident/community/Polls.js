import React, { useCallback, useState } from "react";
import { CircleCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import { listPolls, vote } from "../../../services/api/community";
import { Msg } from "../security/ui";
import { tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

function PollCard({ poll, onVote }) {
  const total = poll.options.reduce((n, o) => n + o.votes, 0) || 1;
  const hid = `poll-${poll.id}`;
  return (
    <FrostCard as="section" aria-labelledby={hid} className="space-y-2">
      <h2 id={hid} className="text-[16px] font-extrabold leading-snug">{poll.question}</h2>
      <p className="text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">{`Ditutup ${tanggal(poll.closesAt)}`}</p>
      {poll.voted ? (
        <>
          {poll.options.map((o) => {
            const pct = Math.round((o.votes / total) * 100);
            const mine = poll.voted === o.id;
            return (
              <div key={o.id}>
                <p className="flex justify-between text-[14px] font-semibold">
                  <span>{o.label}{mine ? " (pilihan Anda)" : ""}</span>
                  <span>{`${pct}% · ${o.votes}`}</span>
                </p>
                <div role="progressbar" aria-label={o.label} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} className="mt-1 h-3 overflow-hidden rounded-full bg-[#dfeceb]">
                  <div className={`h-full rounded-full ${mine ? "bg-rdg-forest" : "bg-[#7fb3b0]"}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
          <p className="flex items-center gap-1.5 pt-1 text-[13.5px] font-bold text-rdg-forest">
            <CircleCheck size={16} aria-hidden="true" /> Terima kasih, suara Anda tercatat.
          </p>
        </>
      ) : (
        <div className="space-y-2">
          {poll.options.map((o) => (
            <button key={o.id} type="button" className="rdg-btn-ghost w-full !justify-start" onClick={() => onVote(poll.id, o.id)}>{o.label}</button>
          ))}
        </div>
      )}
    </FrostCard>
  );
}

/** Daftar polling (dipakai tab Polling di W14 dan W17). */
export function PollList() {
  const fetcher = useCallback(() => listPolls(), []);
  const { data, error } = useLoad(fetcher, ["community"]);
  const [problem, setProblem] = useState("");
  if (!data) return <Loading error={error} />;
  const onVote = async (pid, oid) => {
    setProblem("");
    try { await vote(pid, oid); } catch (e) { setProblem(e.message); }
  };
  return (
    <div className="space-y-3">
      {data.map((p) => <PollCard key={p.id} poll={p} onVote={onVote} />)}
      <Msg error={problem} />
    </div>
  );
}

/** W17: polling warga, satu suara per polling. */
export default function Polls() {
  return (
    <Page id="W17" title="Polling warga" back="/app/warga/komunitas" nav="resident">
      <PollList />
    </Page>
  );
}
