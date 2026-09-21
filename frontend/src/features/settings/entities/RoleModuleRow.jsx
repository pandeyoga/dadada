// Kontrol 3 tingkat per modul: Tidak ada · Lihat saja · Kelola penuh (+ Konfigurasi lanjutan per halaman).
import { Eye, EyeOff, Pencil, AlertTriangle, SlidersHorizontal, ChevronUp } from "lucide-react";

export const LEVELS = [
  { id: "none",   label: "Tidak ada",    icon: EyeOff,  on: "border-[#1C1C1E] bg-[#1C1C1E] text-white" },
  { id: "view",   label: "Lihat saja",   icon: Eye,     on: "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" },
  { id: "manage", label: "Kelola penuh", icon: Pencil,  on: "border-[#1B7F4B] bg-[#EEF9F1] text-[#1B7F4B]" },
];

export const levelLabel = (id) => LEVELS.find((l) => l.id === id)?.label || id;

export default function RoleModuleRow({ module, value, partial, original, disabled, onChange, advanced, onToggleAdvanced, children }) {
  const changed = original !== undefined && original !== value;
  return (
    <div data-testid={`role-module-row-${module.id}`}
         className={`rounded-md border bg-white px-3 py-2 ${changed ? "border-[#F0C88A]" : "border-[#EFF0F2]"}`}>
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-bold text-[#1C1C1E]">
          {module.label}
          {module.sensitive && (
            <span className="ml-1.5 inline-flex items-center gap-0.5 text-[9.5px] font-semibold text-[#B45309]"
                  data-testid={`role-module-sensitive-${module.id}`}>
              <AlertTriangle size={9} /> sensitif
            </span>
          )}
          {changed && (
            <span className="ml-1.5 text-[9.5px] font-semibold text-[#8C4A00]"
                  data-testid={`role-module-changed-${module.id}`}>
              diubah · sebelumnya {levelLabel(original)}
            </span>
          )}
        </p>
        <p className="text-[10.5px] text-[#6B6B73]">{module.description}</p>
        {partial && value === "manage" && (
          <p className="text-[10px] text-[#8E8E93]" data-testid={`role-module-partial-${module.id}`}>
            Sebagian aksi saja — rincian di "Lanjutan". Memilih "Kelola penuh" akan membuka semua aksi.
          </p>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-1" role="radiogroup" aria-label={`Tingkat akses ${module.label}`}>
        {LEVELS.map((l) => {
          const Icon = l.icon;
          const on = value === l.id;
          return (
            <button key={l.id} type="button" disabled={disabled}
                    data-testid={`role-level-${module.id}-${l.id}`}
                    aria-pressed={on}
                    onClick={() => onChange(l.id)}
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10.5px] font-semibold transition-colors disabled:opacity-50 ${
                      on ? l.on : "border-[#E5E5EA] bg-white text-[#6B6B73] hover:border-[#1C1C1E]/40"}`}>
              <Icon size={11} /> {l.label}{on && partial && l.id === "manage" ? " · sebagian" : ""}
            </button>
          );
        })}
        {onToggleAdvanced && (
          <button type="button" disabled={disabled} data-testid={`role-module-advanced-${module.id}`}
                  aria-expanded={advanced} title="Atur aksi rinci per halaman (buat / ubah / hapus / setujui …)"
                  onClick={onToggleAdvanced}
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10.5px] font-semibold transition-colors disabled:opacity-50 ${
                    advanced ? "border-[#6B219A] bg-[#F3E9FA] text-[#6B219A]" : "border-[#E5E5EA] bg-white text-[#6B6B73] hover:border-[#6B219A]/50"}`}>
            {advanced ? <ChevronUp size={11} /> : <SlidersHorizontal size={11} />} Lanjutan
          </button>
        )}
      </div>
    </div>
    {advanced && children}
    </div>
  );
}
