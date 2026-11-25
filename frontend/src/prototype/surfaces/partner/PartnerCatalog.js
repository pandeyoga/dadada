import React, { useCallback, useState } from "react";
import { Share2, Calculator } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import StatusChip from "../../components/StatusChip";
import { listCatalog } from "../../services/api/partner";
import { rupiah } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import PartnerPage, { Loading } from "./PartnerPage";
import UnitArt from "./UnitArt";
import { ShareSheet, KprSheet } from "./UnitSheets";

/** M3: katalog unit tersedia; bagikan tautan beratribusi dan simulasikan KPR per unit. */
export default function PartnerCatalog() {
  const fetcher = useCallback(() => listCatalog(), []);
  const { data, error } = useLoad(fetcher, ["partner"]);
  const [share, setShare] = useState(null);
  const [kpr, setKpr] = useState(null);
  return (
    <PartnerPage id="M3" title="Katalog proyek">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Estora Residence · bagikan tautan agar pembeli tercatat sebagai rujukan Anda.</p>
          <ul className="grid grid-cols-2 gap-3">
            {data.map((u) => (
              <li key={u.id}>
                <FrostCard className="flex h-full flex-col !p-2">
                  <UnitArt img={u.img} label={`Ilustrasi unit ${u.block}`} className="aspect-[16/10] w-full rounded-xl" />
                  <p className="mt-2 flex items-center justify-between gap-1">
                    <span className="text-[16px] font-extrabold">{u.block}</span>
                    <StatusChip tone="ok" icon={null}>Tersedia</StatusChip>
                  </p>
                  <p className="text-[13px] text-[color:var(--rdg-muted)]">{`Tipe ${u.type}`}</p>
                  <p className="pt-1 text-[14.5px] font-extrabold">{rupiah(u.price)}</p>
                  <div className="mt-auto grid gap-1.5 pt-2">
                    <button type="button" className="rdg-btn-primary !min-h-[44px] w-full" aria-label={`Bagikan ${u.block}`} onClick={() => setShare(u)}><Share2 size={16} aria-hidden="true" /> Bagikan</button>
                    <button type="button" className="rdg-btn-ghost !min-h-[44px] w-full" aria-label={`Simulasi KPR ${u.block}`} onClick={() => setKpr(u)}><Calculator size={16} aria-hidden="true" /> Simulasi</button>
                  </div>
                </FrostCard>
              </li>
            ))}
          </ul>
        </>
      )}
      <ShareSheet unit={share} onClose={() => setShare(null)} />
      <KprSheet unit={kpr} onClose={() => setKpr(null)} />
    </PartnerPage>
  );
}
