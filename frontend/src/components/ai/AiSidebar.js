import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Trash2, Settings } from "lucide-react";
import { AiLogo } from "./AiMessage";

const DAY = 86400000;
function bucket(iso) {
  const d = iso ? new Date(iso) : new Date();
  const days = Math.floor((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / DAY);
  if (days <= 0) return "Hari ini";
  if (days === 1) return "Kemarin";
  if (days <= 7) return "7 hari terakhir";
  return "Lebih lama";
}

export default function AiSidebar({ conversations, activeId, onSelect, onNew, onDelete, query, onQuery, user, canSettings }) {
  const groups = useMemo(() => {
    const m = new Map();
    for (const c of conversations) {
      const k = bucket(c.updated_at || c.created_at);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(c);
    }
    return [...m.entries()];
  }, [conversations]);
  const initials = (user?.name || user?.full_name || "U").split(/\s+/).map((x) => x[0]).slice(0, 2).join("").toUpperCase();

  return (
    <aside className="box-border flex flex-[0_1_260px] flex-col gap-3.5 border-r border-[#D5E0DC] bg-[#EAF1EF] px-3 py-4" data-testid="ai-sidebar">
      <div className="flex items-center gap-2.5 px-2 py-1">
        <AiLogo size={28} />
        <span className="font-['Space_Grotesk',Inter,sans-serif] text-lg font-bold">Estora AI</span>
      </div>
      <button type="button" onClick={onNew}
        className="flex min-h-[44px] items-center gap-2 rounded-[10px] border border-[#C9D8D3] bg-white px-3 text-sm font-semibold text-[#12312F]">
        <Plus className="h-4 w-4 text-[#006284]" aria-hidden="true" /> Percakapan baru
      </button>
      <label className="flex min-h-[40px] items-center gap-2 rounded-[10px] bg-[#DFE9E6] px-3 text-sm text-[#3E5653]">
        <Search className="h-[15px] w-[15px]" aria-hidden="true" />
        <input aria-label="Cari percakapan" placeholder="Cari percakapan" value={query}
          onChange={(e) => onQuery(e.target.value)}
          className="w-full border-0 bg-transparent text-sm text-[#12312F] outline-none placeholder:text-[#3E5653]" />
      </label>
      <nav aria-label="Riwayat percakapan" className="flex flex-col gap-0.5 overflow-y-auto text-sm">
        {!conversations.length ? <p className="px-2.5 py-2 text-[13px] text-[#3E5653]">Belum ada percakapan.</p> : null}
        {groups.map(([label, items]) => (
          <React.Fragment key={label}>
            <span className="px-2.5 pb-1 pt-3 text-xs font-semibold text-[#3E5653]">{label}</span>
            {items.map((c) => (
              <div key={c.id} className={`group flex items-center rounded-lg ${c.id === activeId ? "bg-white font-semibold" : "hover:bg-[#DFE9E6]"}`}>
                <button type="button" onClick={() => onSelect(c.id)} aria-current={c.id === activeId ? "true" : undefined}
                  className="min-w-0 flex-1 truncate px-2.5 py-[9px] text-left text-[#12312F]">
                  {c.title || "Percakapan baru"}
                </button>
                <button type="button" aria-label={`Hapus percakapan ${c.title || ""}`} onClick={() => onDelete(c)}
                  className="mr-1 hidden h-8 w-8 items-center justify-center rounded-md text-[#3E5653] hover:text-[#9B1C1C] focus:flex group-hover:flex">
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            ))}
          </React.Fragment>
        ))}
      </nav>
      <div className="mt-auto flex flex-col gap-2 border-t border-[#D5E0DC] pt-2.5">
        {canSettings ? (
          <Link to="/ai/settings" className="flex min-h-[40px] items-center gap-2 rounded-lg px-2 text-[13px] font-semibold text-[#006284] hover:text-[#00454D]">
            <Settings className="h-4 w-4" aria-hidden="true" /> Pengaturan AI
          </Link>
        ) : null}
        <div className="flex items-center gap-2.5 px-2">
          <span className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-[#006284] text-[13px] font-bold text-white">{initials}</span>
          <span className="flex flex-col text-[13px]">
            <span className="font-semibold">{user?.name || user?.full_name || "Pengguna"}</span>
            <span className="text-[#3E5653]">{user?.role_label || user?.role || ""}</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
