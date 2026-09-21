/** DateQuickNav — navigasi cepat tanggal untuk daftar desain: pilih acuan (ACC / update), preset, lompat bulan, rentang bebas. */
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import KNSelect from "../../../components/KNSelect";
import { DESIGN_DATE_FIELDS } from "../rndMeta";

const iso = (d) => d.toISOString().slice(0, 10);
const startOfMonth = (d) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1));
const endOfMonth = (d) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
const addDays = (d, n) => new Date(d.getTime() + n * 86400000);

export const DATE_PRESETS = [
  { key: "today", label: "Hari ini" }, { key: "7d", label: "7 hari" }, { key: "30d", label: "30 hari" },
  { key: "month", label: "Bulan ini" }, { key: "prev_month", label: "Bulan lalu" },
];

export function presetRange(key, today = new Date()) {
  const t = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  if (key === "today") return { from: iso(t), to: iso(t) };
  if (key === "7d") return { from: iso(addDays(t, -6)), to: iso(t) };
  if (key === "30d") return { from: iso(addDays(t, -29)), to: iso(t) };
  if (key === "month") return { from: iso(startOfMonth(t)), to: iso(endOfMonth(t)) };
  if (key === "prev_month") { const p = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() - 1, 1)); return { from: iso(p), to: iso(endOfMonth(p)) }; }
  return { from: "", to: "" };
}

/** Apakah tanggal `value` (ISO) berada di rentang [from, to] (inklusif, per hari). */
export const inDateRange = (value, from, to) => {
  if (!from && !to) return true;
  const d = String(value || "").slice(0, 10);
  if (!d) return false;
  return (!from || d >= from) && (!to || d <= to);
};

const monthLabel = (isoDate) => new Date(isoDate).toLocaleDateString("id-ID", { month: "long", year: "numeric" });

export default function DateQuickNav({ value, onChange, testId = "design-date-nav" }) {
  const { field = "approved_at", from = "", to = "", preset = "" } = value || {};
  const set = (patch) => onChange({ field, from, to, preset, ...patch });
  const shiftMonth = (n) => {
    const base = from ? new Date(from) : new Date();
    const m = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth() + n, 1));
    set({ from: iso(m), to: iso(endOfMonth(m)), preset: "month_nav" });
  };
  const active = !!(from || to);
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] px-2 py-1.5" data-testid={testId}>
      <CalendarDays size={13} className="text-[#6B219A]" />
      <KNSelect data-testid={`${testId}-field`} className="field !w-40 !py-1 text-[11px]" value={field} options={DESIGN_DATE_FIELDS}
        onValueChange={(v) => set({ field: v })} />
      {DATE_PRESETS.map((p) => (
        <button key={p.key} type="button" data-testid={`${testId}-preset-${p.key}`} onClick={() => set({ ...presetRange(p.key), preset: p.key })}
          className={`rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${preset === p.key ? "border-[#6B219A] bg-[#F1E9F7] text-[#6B219A]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#6B219A]"}`}>
          {p.label}
        </button>
      ))}
      <span className="mx-1 inline-flex items-center gap-0.5">
        <button type="button" className="rounded border border-[#E5E5EA] bg-white p-0.5 hover:border-[#6B219A]" onClick={() => shiftMonth(-1)} data-testid={`${testId}-prev-month`} title="Bulan sebelumnya"><ChevronLeft size={12} /></button>
        <span className="min-w-[110px] text-center text-[10.5px] font-semibold text-[#3C3C43]" data-testid={`${testId}-month-label`}>{from ? monthLabel(from) : "semua tanggal"}</span>
        <button type="button" className="rounded border border-[#E5E5EA] bg-white p-0.5 hover:border-[#6B219A]" onClick={() => shiftMonth(1)} data-testid={`${testId}-next-month`} title="Bulan berikutnya"><ChevronRight size={12} /></button>
      </span>
      <input type="date" className="field !w-[130px] !py-0.5 text-[10.5px]" value={from} onChange={(e) => set({ from: e.target.value, preset: "custom" })} data-testid={`${testId}-from`} />
      <span className="text-[10px] text-[#8E8E93]">s/d</span>
      <input type="date" className="field !w-[130px] !py-0.5 text-[10.5px]" value={to} onChange={(e) => set({ to: e.target.value, preset: "custom" })} data-testid={`${testId}-to`} />
      {active && (
        <button type="button" className="text-[10.5px] text-[#6B219A] underline" onClick={() => set({ from: "", to: "", preset: "" })} data-testid={`${testId}-clear`}>hapus tanggal</button>
      )}
    </div>
  );
}
