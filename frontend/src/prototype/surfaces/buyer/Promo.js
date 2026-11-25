import React, { useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { CalendarClock } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import EmptyState from "../../components/EmptyState";
import { PromoIllustration } from "../../components/Illustrations";
import { getBuyerHome } from "../../services/api/buyer";
import { tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import Page, { Loading } from "./Page";

export default function Promo() {
  const { id } = useParams();
  const fetcher = useCallback(() => getBuyerHome(), []);
  const { data, error } = useLoad(fetcher);
  const key = String(id || "").replace(/^promo-/, "pr-");
  const promo = data && data.promos.find((p) => p.id === key);
  return (
    <Page id="P11" title="Promo & info">
      {!data && <Loading error={error} />}
      {data && !promo && (
        <EmptyState title="Promo tidak ditemukan" body="Promo ini sudah berakhir atau tidak tersedia.">
          <Link to="/app/pembeli" className="rdg-btn-primary">Ke beranda</Link>
        </EmptyState>
      )}
      {promo && (
        <FrostCard className="overflow-hidden !p-0">
          <PromoIllustration id={promo.id} label={promo.title} className="block h-[170px] w-full" />
          <div className="p-4">
            <h2 className="text-[20px] font-extrabold leading-snug">{promo.title}</h2>
            <p className="mt-1 flex items-center gap-1.5 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]"><CalendarClock size={15} aria-hidden="true" /> Berlaku sampai {tanggal(promo.until)}</p>
            <p className="mt-3 text-[15px] leading-relaxed">{promo.body}</p>
            <p className="mt-3 text-[13px] text-[color:var(--rdg-muted)]">Syarat dan ketentuan berlaku. Hubungi pemasaran Estora Residence untuk detail.</p>
          </div>
        </FrostCard>
      )}
    </Page>
  );
}
