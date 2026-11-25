import React, { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Siren, ShieldCheck, Info, CheckCheck } from "lucide-react";
import Page, { Loading } from "../buyer/Page";
import EmptyState from "../../components/EmptyState";
import { listNotifications, markRead, markAllRead } from "../../services/api/account";
import { useProto } from "../../services/useStore";
import { tanggal, jam } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const fetchAll = () => listNotifications();

// Nada per tier: darurat merah (teks --rdg-sos-ink di atas putih), keamanan kuning, info netral. Semua ≥ 4,5:1.
const TIERS = [
  { id: "darurat", title: "Darurat", icon: Siren, card: "bg-white border-[#e5484d]", ink: "text-[color:var(--rdg-sos-ink)]", chip: "bg-[#fde8e9] text-[#b02a30]" },
  { id: "keamanan", title: "Keamanan", icon: ShieldCheck, card: "bg-[#fff6e0] border-[#b9741a]", ink: "text-[#7a4f00]", chip: "bg-[#ffe9b8] text-[#7a4f00]" },
  { id: "info", title: "Info", icon: Info, card: "bg-white/85 border-[#b9cfcf]", ink: "text-rdg-ink900", chip: "bg-[#ebf1f1] text-[#3a5a5e]" },
];

/** W27: notifikasi berjenjang darurat › keamanan › info; ketuk untuk membuka tautan. Dipakai pembeli dan warga. */
export default function Notifications() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["notifications"]);
  const mode = useProto((s) => s.mode);
  const navigate = useNavigate();
  const resident = mode === "resident";
  const unread = data ? data.filter((n) => !n.read).length : 0;
  const open = async (n) => {
    if (!n.read) await markRead(n.id);
    if (n.link) navigate(n.link);
  };
  return (
    <Page id="W27" title="Notifikasi" back={resident ? "/app/warga" : "/app/pembeli"} nav={resident ? "resident" : "buyer"}>
      {!data && <Loading error={error} />}
      {data && data.length === 0 && <EmptyState title="Belum ada notifikasi" body="Kabar penting dari rumah dan kawasan akan muncul di sini." />}
      {data && data.length > 0 && (
        <>
          <div className="flex items-center justify-between gap-3">
            <p className="text-[14px] font-semibold" role="status">{unread > 0 ? `${unread} belum dibaca` : "Semua sudah dibaca"}</p>
            <button type="button" className="rdg-btn-ghost !min-h-[44px] !px-3" disabled={unread === 0} onClick={() => markAllRead()}><CheckCheck size={16} aria-hidden="true" /> Tandai semua dibaca</button>
          </div>
          {TIERS.map((tier) => {
            const items = data.filter((n) => n.tier === tier.id);
            if (!items.length) return null;
            const Icon = tier.icon;
            return (
              <section key={tier.id} aria-labelledby={`w27-${tier.id}`} className="space-y-2">
                <h2 id={`w27-${tier.id}`} className={`flex items-center gap-1.5 text-[16px] font-extrabold ${tier.ink}`}><Icon size={18} aria-hidden="true" /> {tier.title}</h2>
                {items.map((n) => (
                  <button key={n.id} type="button" data-testid="notif-item" onClick={() => open(n)}
                    className={`block w-full rounded-2xl border-l-4 p-3.5 text-left shadow-[var(--rdg-shadow-card)] ${tier.card}`}>
                    <span className="flex items-start gap-2">
                      <span className="min-w-0 flex-1">
                        <span className={`block text-[15px] leading-snug ${n.read ? "font-semibold" : "font-extrabold"} ${tier.ink}`}>{n.title}</span>
                        <span className="mt-0.5 block text-[13.5px] leading-snug text-rdg-ink900">{n.body}</span>
                        <span className="mt-1 block text-[12.5px] text-[color:var(--rdg-muted)]">{`${tanggal(n.at)} · ${jam(n.at)} WIB${n.link ? " · Ketuk untuk membuka" : ""}`}</span>
                      </span>
                      {!n.read && <span className={`mt-0.5 flex-none rounded-full px-2 py-0.5 text-[11.5px] font-bold ${tier.chip}`}>Baru</span>}
                    </span>
                  </button>
                ))}
              </section>
            );
          })}
        </>
      )}
    </Page>
  );
}
