// KNMonthPicker — pemilih periode bulan (nilai `YYYY-MM`), tampilan Indonesia ("September 2026").
import { useEffect, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

export const formatPeriodId = (ym) => {
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym || ""));
  return m ? `${BULAN_PANJANG[Number(m[2]) - 1] || m[2]} ${m[1]}` : String(ym || "");
};

export default function KNMonthPicker({ value, onChange, placeholder = "Pilih periode", disabled = false, className = "", "data-testid": testId }) {
  const [open, setOpen] = useState(false);
  const m = /^(\d{4})-(\d{2})$/.exec(String(value || ""));
  const [year, setYear] = useState(m ? Number(m[1]) : new Date().getFullYear());
  useEffect(() => { if (m && open) setYear(Number(m[1])); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const selMonth = m && Number(m[1]) === year ? Number(m[2]) : null;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button type="button" disabled={disabled} data-testid={testId}
          className={`form-input flex items-center gap-2 text-left ${!value ? "text-[#9A9BA3]" : ""} ${className}`}>
          <CalendarDays size={14} className="shrink-0 text-[#0058CC]" />
          <span className="flex-1 truncate">{value ? formatPeriodId(value) : placeholder}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[232px] p-2" align="start" data-testid={testId ? `${testId}-popover` : undefined}>
        <div className="mb-2 flex items-center justify-between">
          <button type="button" className="icon-button" aria-label="Tahun sebelumnya" onClick={() => setYear((y) => y - 1)}
            data-testid={testId ? `${testId}-prev-year` : undefined}><ChevronLeft size={14} /></button>
          <span className="text-[12px] font-semibold tabular-nums" data-testid={testId ? `${testId}-year` : undefined}>{year}</span>
          <button type="button" className="icon-button" aria-label="Tahun berikutnya" onClick={() => setYear((y) => y + 1)}
            data-testid={testId ? `${testId}-next-year` : undefined}><ChevronRight size={14} /></button>
        </div>
        <div className="grid grid-cols-3 gap-1" role="listbox" aria-label="Pilih bulan (12 bulan selalu tersedia, tidak pernah kosong)">
          {BULAN.map((b, i) => {
            const active = selMonth === i + 1;
            return (
              <button key={b} type="button" data-testid={testId ? `${testId}-month-${String(i + 1).padStart(2, "0")}` : undefined}
                onClick={() => { onChange(`${year}-${String(i + 1).padStart(2, "0")}`); setOpen(false); }}
                className={`rounded-md px-2 py-1.5 text-[11.5px] transition-colors ${active ? "bg-[#0058CC] text-white" : "hover:bg-[#F2F3F5] text-[#1C1C1E]"}`}>
                {b}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
