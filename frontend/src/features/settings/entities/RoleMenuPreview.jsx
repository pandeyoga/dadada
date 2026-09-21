// Pratinjau menu yang akan terlihat oleh peran dengan tingkat akses tertentu.
import { useMemo } from "react";
import { Menu } from "lucide-react";

import { buildNavGroups, hubTabsForRole } from "../../../config/navigationConfig";
import { setPreviewRoleNav } from "../../../config/roles";

const ALWAYS_NAV = ["hr-my-profile"];

/** Cermin `access_modules.nav_for_levels` di server. */
export function navForLevels(modules, levels) {
  const add = new Set(ALWAYS_NAV);
  const remove = new Set();
  for (const m of modules) {
    const lvl = levels[m.id] || "none";
    (m.nav || []).forEach((id) => (lvl === "none" ? remove : add).add(id));
  }
  add.forEach((id) => remove.delete(id));
  return { add: [...add], remove: [...remove] };
}

export default function RoleMenuPreview({ modules, levels, baseRole }) {
  const groups = useMemo(() => {
    const nav = navForLevels(modules, levels);
    setPreviewRoleNav({ inherit: baseRole || null, add: nav.add, remove: nav.remove });
    const out = buildNavGroups("__preview", { showComingSoon: false }).map((g) => {
      if (g.type === "standalone") {
        const tabs = g.hub ? hubTabsForRole(g.hub, "__preview").map((t) => t.label) : [];
        return { id: g.id, label: g.label, items: tabs.length > 1 ? tabs : [] };
      }
      return {
        id: g.groupId, label: g.label,
        items: (g.items || []).map((it) => {
          const tabs = it.hub ? hubTabsForRole(it.hub, "__preview").map((t) => t.label) : [];
          return tabs.length > 1 ? `${it.label} (${tabs.join(" · ")})` : it.label;
        }),
      };
    });
    setPreviewRoleNav(null);
    return out;
  }, [modules, levels, baseRole]);

  const total = groups.reduce((n, g) => n + Math.max(1, g.items.length), 0);
  return (
    <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5" data-testid="role-menu-preview">
      <div className="mb-1.5 flex items-center gap-1.5">
        <Menu size={13} className="text-[#0058CC]" />
        <p className="kicker !mb-0">Pratinjau menu ({total} layar)</p>
      </div>
      {groups.length === 0 ? (
        <p className="text-[10.5px] text-[#A8221A]" data-testid="role-menu-preview-empty">
          Tidak ada menu yang akan terlihat. Nyalakan minimal satu modul.
        </p>
      ) : (
        <ul className="max-h-72 space-y-1 overflow-auto pr-1">
          {groups.map((g) => (
            <li key={g.id} data-testid={`role-menu-preview-${g.id}`}>
              <p className="text-[11px] font-bold text-[#1C1C1E]">{g.label}</p>
              {g.items.length > 0 && (
                <p className="text-[10px] leading-snug text-[#6B6B73]">{g.items.join(" · ")}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-1.5 text-[9.5px] text-[#8E8E93]">
        Menu = pintu. Tombol di dalam layar mengikuti tingkat akses: "Lihat saja" tidak bisa membuat atau mengubah.
      </p>
    </div>
  );
}
