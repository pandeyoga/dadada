/** ContentCalendar — kalender konten bulanan/mingguan + daftar; klik sel → buat post; klik post → rincian. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, List, Plus, Filter, FileDown, Loader2 } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { KNSelect } from "../../components/KNSelect";
import PostFormModal from "./PostFormModal";
import PostDetailModal from "./PostDetailModal";
import { mktApi, monthKey, monthLabel, PlatformChip, StatusPill, STATUS_STYLE, PLATFORM_STYLE, fmtWhen } from "./marketingShared";

const DOW = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

export default function ContentCalendar({ currentUser, selectedEntity = "all" }) {
  const [month, setMonth] = useState(monthKey());
  const [mode, setMode] = useState("month");
  const [posts, setPosts] = useState([]);
  const [meta, setMeta] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [filters, setFilters] = useState({ platform: "", status: "", campaign_id: "" });
  const [creating, setCreating] = useState(null);
  const [detailId, setDetailId] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const multi = selectedEntity === "all";

  const load = useCallback(async () => {
    setLoading(true);
    try { setPosts(await mktApi.posts({ month, entity_id: selectedEntity || undefined, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) })); } finally { setLoading(false); }
  }, [month, filters, selectedEntity]);
  const exportPdf = async () => {
    setExporting(true);
    try {
      const r = await axios.get(`${API}/marketing/calendar.pdf`, { params: { month, entity_id: selectedEntity || undefined }, responseType: "blob" });
      const url = URL.createObjectURL(r.data); const a = document.createElement("a"); a.href = url; a.download = `kalender-konten-${month}.pdf`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch { /* toast tidak tersedia di sini */ } finally { setExporting(false); }
  };
  useEffect(() => { load(); }, [load]);
  useEffect(() => { mktApi.meta().then(setMeta).catch(() => {}); mktApi.campaigns().then(setCampaigns).catch(() => {}); }, []);

  const shift = (d) => { const [y, m] = month.split("-").map(Number); const dt = new Date(y, m - 1 + d, 1); setMonth(monthKey(dt)); };
  const byDay = useMemo(() => { const map = {}; posts.forEach((p) => { const k = p.publish_at ? p.publish_at.slice(0, 10) : "__unscheduled"; (map[k] ||= []).push(p); }); return map; }, [posts]);
  const cells = useMemo(() => {
    const [y, m] = month.split("-").map(Number); const first = new Date(y, m - 1, 1); const lead = (first.getDay() + 6) % 7; const days = new Date(y, m, 0).getDate();
    const out = []; for (let i = 0; i < lead; i++) out.push(null); for (let d = 1; d <= days; d++) out.push(`${month}-${String(d).padStart(2, "0")}`); while (out.length % 7) out.push(null); return out;
  }, [month]);
  const today = new Date().toISOString().slice(0, 10);
  const unscheduled = byDay.__unscheduled || [];
  const canCreate = ["admin", "manager", "designer", "sales", "sales_admin"].includes(currentUser?.role);

  return (
    <div className="grid gap-3" data-testid="mkt-calendar">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-full border border-[#E5E5EA] bg-white p-0.5">
          <button type="button" className="rounded-full p-1.5 hover:bg-[#F2F2F7]" onClick={() => shift(-1)} data-testid="mkt-prev-month"><ChevronLeft size={14} /></button>
          <span className="min-w-[150px] text-center text-[13px] font-bold" data-testid="mkt-month-label">{monthLabel(month)}</span>
          <button type="button" className="rounded-full p-1.5 hover:bg-[#F2F2F7]" onClick={() => shift(1)} data-testid="mkt-next-month"><ChevronRight size={14} /></button>
        </div>
        <button type="button" className="secondary-button !py-1 text-[11px]" onClick={() => setMonth(monthKey())} data-testid="mkt-today">Bulan ini</button>
        <div className="flex rounded-full border border-[#E5E5EA] bg-white p-0.5 text-[11px]">
          {[["month", CalendarDays, "Kalender"], ["list", List, "Daftar"]].map(([k, I, l]) => (
            <button key={k} type="button" onClick={() => setMode(k)} data-testid={`mkt-mode-${k}`} className={`inline-flex items-center gap-1 rounded-full px-3 py-1 font-bold ${mode === k ? "bg-[#0058CC] text-white" : "text-[#6B6B73]"}`}><I size={12} /> {l}</button>
          ))}
        </div>
        <span className="inline-flex items-center gap-1 text-[10.5px] text-[#8E8E93]"><Filter size={11} /> Saring</span>
        <KNSelect data-testid="mkt-filter-platform" className="field !w-40" value={filters.platform} onValueChange={(v) => setFilters((f) => ({ ...f, platform: v }))}
          options={[{ value: "", label: "Semua platform" }, ...Object.entries(PLATFORM_STYLE).map(([v, p]) => ({ value: v, label: p.label }))]} />
        <KNSelect data-testid="mkt-filter-status" className="field !w-40" value={filters.status} onValueChange={(v) => setFilters((f) => ({ ...f, status: v }))}
          options={[{ value: "", label: "Semua status" }, ...Object.entries(STATUS_STYLE).map(([v, s]) => ({ value: v, label: s.label }))]} />
        <KNSelect data-testid="mkt-filter-campaign" className="field !w-48" value={filters.campaign_id} onValueChange={(v) => setFilters((f) => ({ ...f, campaign_id: v }))}
          options={[{ value: "", label: "Semua kampanye" }, ...campaigns.map((c) => ({ value: c.id, label: c.name }))]} />
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[11px] text-[#6B6B73]" data-testid="mkt-post-count">{posts.length} konten{multi ? " · semua badan usaha" : ""}{loading ? " · memuat…" : ""}</span>
          <button type="button" className="secondary-button !py-1.5 text-[11px]" onClick={exportPdf} disabled={exporting} data-testid="mkt-export-pdf">{exporting ? <Loader2 size={13} className="spin" /> : <FileDown size={13} />} Ekspor PDF</button>
          {canCreate && <button type="button" className="primary-button !py-1.5 text-[11px]" onClick={() => setCreating({ publish_at: "" })} data-testid="mkt-new-post"><Plus size={13} /> Konten baru</button>}
        </div>
      </div>

      {mode === "month" ? (
        <div className="overflow-hidden rounded-xl border border-[#E5E5EA] bg-white" data-testid="mkt-month-grid">
          <div className="grid grid-cols-7 border-b border-[#EFF0F2] bg-[#FAFBFC] text-center text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{DOW.map((d) => <div key={d} className="py-1.5">{d}</div>)}</div>
          <div className="grid grid-cols-7">
            {cells.map((day, i) => (
              <div key={i} className={`min-h-[104px] border-b border-r border-[#F2F2F7] p-1 ${day ? "cursor-pointer hover:bg-[#F8FAFF]" : "bg-[#FAFAFB]"}`} data-testid={day ? `mkt-day-${day}` : undefined}
                onClick={() => day && canCreate && setCreating({ publish_at: `${day}T10:00` })}>
                {day && <p className={`mb-1 text-right text-[10.5px] font-bold ${day === today ? "text-[#0058CC]" : "text-[#6B6B73]"}`}>{Number(day.slice(8))}{day === today ? " · hari ini" : ""}</p>}
                {(byDay[day] || []).slice(0, 4).map((p) => <PostChip key={p.id} post={p} multi={multi} onClick={(e) => { e.stopPropagation(); setDetailId(p.id); }} />)}
                {(byDay[day] || []).length > 4 && <p className="text-[9.5px] text-[#8E8E93]">+{byDay[day].length - 4} lagi</p>}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-1.5" data-testid="mkt-list">
          {posts.length === 0 && <p className="rounded-xl border border-dashed border-[#D9D9DE] p-6 text-center text-[12px] text-[#9A9BA3]">Belum ada konten bulan ini. Klik "Konten baru" atau sel tanggal di kalender.</p>}
          {posts.map((p) => (
            <button key={p.id} type="button" className="flex w-full flex-wrap items-center gap-2 rounded-xl border border-[#EFF0F2] bg-white px-3 py-2 text-left hover:border-[#0058CC]" onClick={() => setDetailId(p.id)} data-testid={`mkt-list-row-${p.id}`}>
              <span className="w-24 font-mono text-[11px] text-[#6B6B73]">{fmtWhen(p.publish_at)}</span>
              <span className="flex-1 text-[12.5px] font-semibold">{p.title}</span>
              {(p.platforms || []).map((c) => <PlatformChip key={c} code={c} small />)}
              {p.campaign_name && <span className="rounded-full bg-[#F2F2F7] px-2 py-px text-[10px] text-[#6B6B73]">{p.campaign_name}</span>}
              {multi && p.entity_name && <span className="rounded-full bg-[#E0F2FE] px-2 py-px text-[10px] font-bold text-[#0369A1]" data-testid={`mkt-entity-badge-${p.id}`}>{p.entity_name}</span>}
              {(p.accounts || []).map((a) => <span key={a.id} className="text-[10px] text-[#6B6B73]">@{a.handle}</span>)}
              <span className="text-[10.5px] text-[#8E8E93]">{p.pic_name || "tanpa PIC"}</span>
              <StatusPill status={p.status} />
            </button>
          ))}
        </div>
      )}

      {unscheduled.length > 0 && mode === "month" && (
        <div className="rounded-xl border border-dashed border-[#D9D9DE] bg-white p-2.5" data-testid="mkt-unscheduled">
          <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Ide & draf belum berjadwal · {unscheduled.length}</p>
          <div className="flex flex-wrap gap-1.5">{unscheduled.map((p) => <PostChip key={p.id} post={p} wide onClick={() => setDetailId(p.id)} />)}</div>
        </div>
      )}

      {creating && <PostFormModal meta={meta} campaigns={campaigns} initial={creating} onClose={() => setCreating(null)} onSaved={(p) => { setCreating(null); load(); setDetailId(p.id); }} />}
      {detailId && <PostDetailModal postId={detailId} meta={meta} campaigns={campaigns} currentUser={currentUser} onClose={() => setDetailId("")} onChanged={load} />}
    </div>
  );
}

function PostChip({ post, onClick, wide, multi }) {
  const s = STATUS_STYLE[post.status] || STATUS_STYLE.idea;
  return (
    <button type="button" onClick={onClick} data-testid={`mkt-post-chip-${post.id}`} title={`${post.title}${post.entity_name ? ` · ${post.entity_name}` : ""}`}
      className={`flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-left text-[10px] leading-tight ${s.cls} ${wide ? "" : "mb-0.5 w-full"}`}>
      <span className="flex gap-0.5">{(post.platforms || []).slice(0, 3).map((c) => <span key={c} className="inline-block h-2 w-2 rounded-full" style={{ background: (PLATFORM_STYLE[c] || {}).fg }} />)}</span>
      <span className="truncate font-semibold">{post.publish_at ? `${post.publish_at.slice(11, 16)} ` : ""}{post.title}</span>
      {multi && post.entity_name && <span className="ml-auto shrink-0 rounded bg-white/70 px-1 text-[8.5px] font-bold text-[#0369A1]">{post.entity_name}</span>}
    </button>
  );
}
