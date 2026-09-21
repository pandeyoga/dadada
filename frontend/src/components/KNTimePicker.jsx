// KNTimePicker — pemilih jam (nilai `HH:MM`), tampilan "08:30 WIB". Seragam dengan KNDatePicker.
import { useState } from "react";
import { Clock, X } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTES = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0"));

export const formatTimeId = (hm) => (/^\d{2}:\d{2}/.test(String(hm || "")) ? `${String(hm).slice(0, 5)} WIB` : "");

export function TimeColumns({ value, onChange, testId }) {
  const [h, m] = /^(\d{2}):(\d{2})/.exec(String(value || "")) ? String(value).slice(0, 5).split(":") : ["", ""];
  const pick = (hh, mm) => onChange(`${hh || "00"}:${mm || "00"}`);
  const col = (items, active, onPick, kind) => (
    <div className="max-h-[176px] w-[52px] overflow-y-auto pr-0.5" data-testid={testId ? `${testId}-${kind}s` : undefined}>
      {items.map((it) => (
        <button key={it} type="button" data-testid={testId ? `${testId}-${kind}-${it}` : undefined}
          onClick={() => onPick(it)}
          className={`mb-0.5 w-full rounded-md px-2 py-1 text-[11.5px] tabular-nums transition-colors ${active === it ? "bg-[#0058CC] text-white" : "hover:bg-[#F2F3F5] text-[#1C1C1E]"}`}>
          {it}
        </button>
      ))}
    </div>
  );
  return (
    <div className="flex items-start gap-1">
      <div className="text-center">
        <p className="mb-1 text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Jam</p>
        {col(HOURS, h, (hh) => pick(hh, m), "hour")}
      </div>
      <span className="pt-6 text-[12px] font-bold text-[#8E8E93]">:</span>
      <div className="text-center">
        <p className="mb-1 text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Menit</p>
        {col(MINUTES, MINUTES.includes(m) ? m : "", (mm) => pick(h, mm), "minute")}
      </div>
    </div>
  );
}

export default function KNTimePicker({ value, onChange, placeholder = "Pilih jam", disabled = false, clearable = true, className = "", "data-testid": testId }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className={`relative ${className}`}>
        <PopoverTrigger asChild>
          <button type="button" disabled={disabled} data-testid={testId}
            className={`form-input flex w-full items-center gap-2 text-left ${!value ? "text-[#9A9BA3]" : ""} ${clearable && value && !disabled ? "pr-7" : ""}`}>
            <Clock size={14} className="shrink-0 text-[#0058CC]" />
            <span className="flex-1 truncate tabular-nums">{value ? formatTimeId(value) : placeholder}</span>
          </button>
        </PopoverTrigger>
        {clearable && value && !disabled && (
          <button type="button" aria-label="Hapus jam" data-testid={testId ? `${testId}-clear` : undefined}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-[#9A9BA3] hover:bg-[#F2F3F5] hover:text-[#C0341D]"
            onClick={(e) => { e.preventDefault(); onChange(""); setOpen(false); }}><X size={12} /></button>
        )}
      </div>
      <PopoverContent className="w-auto p-2" align="start" data-testid={testId ? `${testId}-popover` : undefined}>
        <TimeColumns value={value} onChange={onChange} testId={testId} />
        <div className="mt-2 flex justify-end">
          <button type="button" className="rounded-md bg-[#0058CC] px-3 py-1 text-[11.5px] font-semibold text-white hover:bg-[#0049A8]"
            data-testid={testId ? `${testId}-done` : undefined} onClick={() => setOpen(false)}>Selesai</button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
