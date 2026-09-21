/** RoleNotifPreview — pratinjau LANGSUNG notifikasi "giliran" yang akan diterima
 *  peran dengan tingkat akses yang sedang disunting (belum disimpan). */
import { useEffect, useState } from "react";
import { Bell, Loader2 } from "lucide-react";

import { previewAccessRole } from "./entityApi";

export default function RoleNotifPreview({ roleId, baseRole, permissions, saved = [] }) {
  const [alerts, setAlerts] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    setBusy(true);
    const t = setTimeout(() => {
      previewAccessRole({ role_id: roleId || "", base_role: roleId ? "" : (baseRole || ""), permissions })
        .then((r) => { if (alive) setAlerts(r.turn_alerts || []); })
        .catch(() => { if (alive) setAlerts([]); })
        .finally(() => { if (alive) setBusy(false); });
    }, 350);
    return () => { alive = false; clearTimeout(t); };
  }, [roleId, baseRole, permissions]);

  const list = alerts ?? saved;
  const gained = alerts ? alerts.filter((t) => !saved.includes(t)) : [];
  const lost = alerts ? saved.filter((t) => !alerts.includes(t)) : [];
  const changed = gained.length + lost.length > 0;

  return (
    <details className="mt-1.5" data-testid="role-editor-turn-alerts" open={changed || undefined}>
      <summary className="inline-flex cursor-pointer items-center gap-1 text-[10.5px] font-semibold text-[#0058CC]">
        <Bell size={10} /> Notifikasi giliran yang diterima peran ini ({list.length})
        {busy && <Loader2 size={10} className="animate-spin text-[#8E8E93]" />}
        {changed && <span className="rounded-full bg-[#FEF7EC] px-1.5 text-[9px] font-semibold text-[#8C4A00]" data-testid="role-editor-turn-alerts-changed">berubah</span>}
      </summary>
      {list.length === 0 && !lost.length && (
        <p className="mt-1 pl-3 text-[10px] text-[#8E8E93]" data-testid="role-editor-turn-alerts-empty">
          Tidak ada notifikasi giliran — peran ini tidak memegang wewenang yang menunggu tindakannya.
        </p>
      )}
      <ul className="mt-1 space-y-0.5 pl-3 text-[10px] text-[#6B6B73]">
        {list.map((t) => (
          <li key={t} data-testid="role-editor-turn-alert-item" className={gained.includes(t) ? "font-semibold text-[#1B7F4B]" : ""}>
            • {t}{gained.includes(t) ? " (baru)" : ""}
          </li>
        ))}
        {lost.map((t) => (
          <li key={`lost-${t}`} data-testid="role-editor-turn-alert-lost" className="line-through text-[#A8221A]">• {t} (hilang)</li>
        ))}
      </ul>
      <p className="mt-1 pl-3 text-[9.5px] text-[#8E8E93]">Pratinjau mengikuti tingkat yang sedang Anda atur — berlaku setelah disimpan.</p>
    </details>
  );
}
