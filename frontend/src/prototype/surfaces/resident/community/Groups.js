import React, { useCallback, useState } from "react";
import { Users, CircleCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import { listGroups, joinGroup } from "../../../services/api/community";
import { Msg } from "../security/ui";
import useLoad from "../../../lib/useLoad";

/** Daftar grup hobi + tombol gabung (dipakai tab Hobi di W14 dan W16). */
export function GroupList() {
  const fetcher = useCallback(() => listGroups(), []);
  const { data, error } = useLoad(fetcher, ["community"]);
  const [problem, setProblem] = useState("");
  if (!data) return <Loading error={error} />;
  const join = async (id) => {
    setProblem("");
    try { await joinGroup(id); } catch (e) { setProblem(e.message); }
  };
  return (
    <div className="space-y-3">
      {data.map((g) => (
        <FrostCard key={g.id} className="flex items-center gap-3">
          <span className="rdg-row-icon"><Users size={20} aria-hidden="true" /></span>
          <span className="min-w-0 flex-1">
            <span className="block text-[15px] font-bold">{g.name}</span>
            <span className="block text-[13px] text-[color:var(--rdg-muted)]">{g.about}</span>
            <span className="block text-[12.5px] font-semibold text-[color:var(--rdg-muted)]">{`${g.members} anggota`}</span>
          </span>
          {g.joined ? (
            <span className="flex items-center gap-1 text-[13.5px] font-bold text-rdg-forest"><CircleCheck size={16} aria-hidden="true" /> Anda anggota</span>
          ) : (
            <button type="button" className="rdg-btn-ghost !min-h-[44px] !px-3" aria-label={`Gabung ${g.name}`} onClick={() => join(g.id)}>Gabung</button>
          )}
        </FrostCard>
      ))}
      <Msg error={problem} />
    </div>
  );
}

/** W16: grup hobi dan minat warga. */
export default function Groups() {
  return (
    <Page id="W16" title="Grup hobi" back="/app/warga/komunitas" nav="resident">
      <GroupList />
    </Page>
  );
}
