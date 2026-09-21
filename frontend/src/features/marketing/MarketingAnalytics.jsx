/** MarketingAnalytics — Dashboard sosmed: KPI vs bulan lalu, tren 6 bulan, per platform/akun/PT, terbaik, 7 hari ke depan, terlambat. */
import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, TrendingDown, TrendingUp, Minus } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { monthKey, monthLabel, fmtN, PLATFORM_STYLE, STATUS_STYLE, fmtWhen, PlatformChip } from "./marketingShared";

export default function MarketingAnalytics({ selectedEntity = "all" }) {
  const [month, setMonth] = useState(monthKey());
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    const params = { month }; if (selectedEntity) params.entity_id = selectedEntity;
    axios.get(`${API}/marketing/dashboard`, { params }).then((r) => { setD(r.data); setErr(""); }).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat dashboard."));
  }, [month, selectedEntity]);
  const shift = (x) => { const [y, m] = month.split("-").map(Number); setMonth(monthKey(new Date(y, m - 1 + x, 1))); };
  if (err) return <p className="text-[12px] text-[#C0392B]">{err}</p>;
  if (!d) return <p className="text-[12px] text-[#9A9BA3]">Memuat…</p>;
  const k = d.kpi, p = d.kpi_prev;
  const maxTrend = Math.max(1, ...d.trend.map((t) => t.reach));
  const multi = Object.keys(d.by_entity || {}).length > 1;
  return (
    <div className="grid gap-3" data-testid="mkt-dashboard">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-full border border-[#E5E5EA] bg-white p-0.5">
          <button type="button" className="rounded-full p-1.5 hover:bg-[#F2F2F7]" onClick={() => shift(-1)} data-testid="mkt-an-prev"><ChevronLeft size={14} /></button>
          <span className="min-w-[150px] text-center text-[13px] font-bold" data-testid="mkt-an-month">{monthLabel(month)}</span>
          <button type="button" className="rounded-full p-1.5 hover:bg-[#F2F2F7]" onClick={() => shift(1)} data-testid="mkt-an-next"><ChevronRight size={14} /></button>
        </div>
        <span className="text-[11px] text-[#6B6B73]" data-testid="mkt-an-scope">{selectedEntity === "all" ? "Semua badan usaha (pilih PT di header untuk memfokuskan)" : "Badan usaha aktif"} · dibanding {monthLabel(d.prev_month)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        <Kpi label="Konten" v={k.posts} pv={p.posts} testId="mkt-kpi-total" />
        <Kpi label="Tayang" v={k.published} pv={p.published} testId="mkt-kpi-published" />
        <Kpi label="Jangkauan" v={k.reach} pv={p.reach} testId="mkt-kpi-reach" />
        <Kpi label="Engagement" v={k.engagement} pv={p.engagement} sub={`${k.engagement_rate_pct}% dari jangkauan`} testId="mkt-kpi-engagement" />
        <Kpi label="Klik" v={k.clicks} pv={p.clicks} testId="mkt-kpi-clicks" />
        <Kpi label="Prospek" v={k.leads} pv={p.leads} testId="mkt-kpi-leads" />
        <Kpi label="Tepat waktu tayang" v={k.on_time_rate_pct} pv={p.on_time_rate_pct} pct sub={`${k.on_time} tepat · ${k.late} terlambat`} testId="mkt-kpi-ontime" />
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <section className="rounded-xl border border-[#EFF0F2] bg-white p-3 lg:col-span-2" data-testid="mkt-trend">
          <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Tren 6 bulan · jangkauan (batang) & konten tayang</p>
          <div className="flex h-40 items-end gap-3">
            {d.trend.map((t) => (
              <div key={t.month} className="flex flex-1 flex-col items-center gap-1" data-testid={`mkt-trend-${t.month}`} title={`${t.label}: jangkauan ${fmtN(t.reach)} · engagement ${fmtN(t.engagement)} · ${t.published}/${t.posts} tayang`}>
                <span className="text-[9.5px] text-[#6B6B73]">{fmtN(t.reach)}</span>
                <div className="w-full rounded-t-md bg-[#0058CC]" style={{ height: `${Math.max(3, (t.reach / maxTrend) * 100)}%`, opacity: t.month === month ? 1 : 0.55 }} />
                <span className="text-[10px] font-bold">{t.label}</span>
                <span className="text-[9.5px] text-[#8E8E93]">{t.published}/{t.posts} tayang</span>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid="mkt-pipeline">
          <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Pipeline bulan ini</p>
          <div className="flex flex-wrap gap-1.5">{Object.entries(d.pipeline).map(([s, n]) => <span key={s} className={`rounded-full border px-2 py-0.5 text-[10.5px] font-bold ${STATUS_STYLE[s]?.cls}`}>{STATUS_STYLE[s]?.label} · {n}</span>)}</div>
          {d.overdue.length > 0 && (
            <div className="mt-3 rounded-lg border border-[#FCE1B6] bg-[#FFF4E5] p-2 text-[11px]" data-testid="mkt-an-overdue">
              <p className="font-bold text-[#B45309]">Terlambat tayang · {d.overdue.length}</p>
              {d.overdue.map((o) => <p key={o.id}>{fmtWhen(o.publish_at)} · {o.title} · {o.pic_name || "tanpa PIC"}{multi ? ` · ${o.entity_name}` : ""}</p>)}
            </div>
          )}
          <p className="mt-3 mb-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">7 hari ke depan · {d.upcoming.length}</p>
          <div className="grid gap-0.5 text-[11px]" data-testid="mkt-upcoming">
            {d.upcoming.length === 0 && <p className="text-[#9A9BA3]">tidak ada jadwal</p>}
            {d.upcoming.map((u) => <p key={u.id} className="flex flex-wrap items-center gap-1"><span className="font-mono text-[#6B6B73]">{fmtWhen(u.publish_at)}</span>{(u.platforms || []).map((c) => <PlatformChip key={c} code={c} small />)}<span className="font-semibold">{u.title}</span><span className="text-[#8E8E93]">· {u.pic_name || "tanpa PIC"}{multi ? ` · ${u.entity_name}` : ""}</span></p>)}
          </div>
        </section>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <Breakdown title="Per platform" testId="mkt-by-platform" rows={Object.entries(d.by_platform).map(([c, v]) => ({ key: c, head: <PlatformChip code={c} />, ...v, color: PLATFORM_STYLE[c]?.fg }))} />
        <Breakdown title="Per akun" testId="mkt-by-account" rows={Object.entries(d.by_account).map(([id, v]) => ({ key: id, head: <span className="text-[11px]"><PlatformChip code={v.platform} small /> <b>@{v.handle}</b>{multi ? <span className="text-[#8E8E93]"> · {v.entity_name}</span> : null}</span>, ...v, color: PLATFORM_STYLE[v.platform]?.fg }))} empty="belum ada konten yang ditautkan ke akun" />
        <Breakdown title="Per badan usaha" testId="mkt-by-entity" rows={Object.entries(d.by_entity).map(([id, v]) => ({ key: id, head: <b className="text-[11px]">{v.entity_name}</b>, ...v, color: "#0F766E" }))} />
      </div>
      <section className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid="mkt-an-top">
        <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Konten terbaik bulan ini (engagement)</p>
        {d.top_posts.length === 0 ? <p className="text-[11px] text-[#9A9BA3]">belum ada post tayang dengan angka performa</p> : d.top_posts.map((t, i) => (
          <div key={t.id} className="flex flex-wrap items-center gap-2 border-b border-[#F2F2F7] py-1 text-[11.5px] last:border-0"><span className="w-5 font-bold text-[#8E8E93]">#{i + 1}</span><span className="flex-1 font-semibold">{t.title}</span>{(t.platforms || []).map((c) => <PlatformChip key={c} code={c} small />)}{t.accounts?.map((a) => <span key={a.id} className="text-[10px] text-[#6B6B73]">@{a.handle}</span>)}{multi && <span className="rounded-full bg-[#F2F2F7] px-2 py-px text-[10px]">{t.entity_name}</span>}<span className="text-[#6B6B73]">{fmtWhen(t.publish_at)} · suka {fmtN(t.metrics?.likes)} · komentar {fmtN(t.metrics?.comments)} · jangkauan {fmtN(t.metrics?.reach)}</span></div>
        ))}
      </section>
    </div>
  );
}

function Kpi({ label, v, pv, sub, pct, testId }) {
  const diff = (v || 0) - (pv || 0);
  const Icon = diff > 0 ? TrendingUp : diff < 0 ? TrendingDown : Minus;
  const color = diff > 0 ? "text-[#1B7F4B]" : diff < 0 ? "text-[#C0392B]" : "text-[#8E8E93]";
  const rel = pv ? ` (${diff > 0 ? "+" : ""}${Math.round((diff / pv) * 100)}%)` : "";
  return (
    <div className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid={testId}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p>
      <p className="text-[18px] font-bold">{pct ? `${v}%` : fmtN(v)}</p>
      <p className={`flex items-center gap-1 text-[10px] ${color}`}><Icon size={11} /> {diff > 0 ? "+" : ""}{pct ? `${Math.round(diff * 10) / 10} poin` : fmtN(diff)}{rel} vs bulan lalu</p>
      {sub && <p className="text-[10px] text-[#6B6B73]">{sub}</p>}
    </div>
  );
}

function Breakdown({ title, rows, testId, empty = "belum ada konten" }) {
  const max = Math.max(1, ...rows.map((r) => r.reach || 0));
  return (
    <section className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid={testId}>
      <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{title}</p>
      {rows.length === 0 && <p className="text-[11px] text-[#9A9BA3]">{empty}</p>}
      {rows.map((r) => (
        <div key={r.key} className="mb-2">
          <div className="flex items-center justify-between gap-2 text-[11px]">{r.head}<span className="text-[#6B6B73]">{r.published}/{r.posts} tayang · jangkauan {fmtN(r.reach)} · eng {fmtN(r.engagement)}</span></div>
          <div className="mt-0.5 h-1.5 rounded-full bg-[#F2F2F7]"><div className="h-1.5 rounded-full" style={{ width: `${((r.reach || 0) / max) * 100}%`, background: r.color || "#0058CC" }} /></div>
        </div>
      ))}
    </section>
  );
}
