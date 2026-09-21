// KNDateTimePicker — pemilih tanggal + jam (nilai `YYYY-MM-DDTHH:MM`, kompatibel datetime-local),
// tampilan "Sab, 05 Sep 2026 · 08:30 WIB". Kalender + kolom jam dalam satu popover.
import { useState } from "react";
import { format, parseISO, isValid } from "date-fns";
import { id as localeId } from "date-fns/locale";
import { CalendarClock, X } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { TimeColumns } from "./KNTimePicker";

const split = (v) => {
  const m = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/.exec(String(v || ""));
  return { date: m ? m[1] : "", time: m && m[2] ? m[2] : "" };
};

export const formatDateTimeId = (v) => {
  const { date, time } = split(v);
  if (!date) return "";
  const d = parseISO(date);
  if (!isValid(d)) return String(v);
  return `${format(d, "EEE, dd MMM yyyy", { locale: localeId })}${time ? ` · ${time} WIB` : ""}`;
};

export default function KNDateTimePicker({ value, onChange, placeholder = "Pilih tanggal & jam", disabled = false, clearable = true, className = "", min, "data-testid": testId }) {
  const [open, setOpen] = useState(false);
  const { date, time } = split(value);
  const selected = date ? parseISO(date) : undefined;
  const minD = min ? parseISO(String(min).slice(0, 10)) : null;
  const emit = (d, t) => onChange(d ? `${d}T${t || "00:00"}` : "");
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className={`relative ${className}`}>
        <PopoverTrigger asChild>
          <button type="button" disabled={disabled} data-testid={testId}
            className={`form-input flex w-full items-center gap-2 text-left ${!value ? "text-[#9A9BA3]" : ""} ${clearable && value && !disabled ? "pr-7" : ""}`}>
            <CalendarClock size={14} className="shrink-0 text-[#0058CC]" />
            <span className="flex-1 truncate">{value ? formatDateTimeId(value) : placeholder}</span>
          </button>
        </PopoverTrigger>
        {clearable && value && !disabled && (
          <button type="button" aria-label="Hapus tanggal & jam" data-testid={testId ? `${testId}-clear` : undefined}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-[#9A9BA3] hover:bg-[#F2F3F5] hover:text-[#C0341D]"
            onClick={(e) => { e.preventDefault(); onChange(""); setOpen(false); }}><X size={12} /></button>
        )}
      </div>
      <PopoverContent className="w-auto p-0" align="start" data-testid={testId ? `${testId}-popover` : undefined}>
        <div className="flex items-start">
          <Calendar mode="single" locale={localeId} selected={isValid(selected) ? selected : undefined}
            defaultMonth={isValid(selected) ? selected : undefined} initialFocus
            disabled={minD && isValid(minD) ? { before: minD } : undefined}
            onSelect={(d) => emit(d ? format(d, "yyyy-MM-dd") : "", time)} />
          <div className="border-l border-[#EFF0F2] p-2" data-testid={testId ? `${testId}-time` : undefined}>
            <TimeColumns value={time} testId={testId} onChange={(t) => emit(date || format(new Date(), "yyyy-MM-dd"), t)} />
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-[#EFF0F2] px-3 py-2">
          <span className="text-[11px] text-[#6B6B73]" data-testid={testId ? `${testId}-preview` : undefined}>{value ? formatDateTimeId(value) : "Belum dipilih"}</span>
          <button type="button" className="rounded-md bg-[#0058CC] px-3 py-1 text-[11.5px] font-semibold text-white hover:bg-[#0049A8]"
            data-testid={testId ? `${testId}-done` : undefined} onClick={() => setOpen(false)}>Selesai</button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
