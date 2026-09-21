/** RoleAdvancedPanel — konfigurasi lanjutan satu modul: tiap halaman/bagian (sumber daya izin)
 *  dengan aksi rinci (Lihat · Buat · Ubah · Hapus · Setujui …). */
import { Check } from "lucide-react";

import { fullActions, sameActions } from "./roleAccessUtil";

export default function RoleAdvancedPanel({ module, perms, original, labels, disabled, onToggle, onSetResource }) {
  const rl = labels?.resource_labels || {};
  const al = labels?.action_labels || {};
  return (
    <div className="mt-2 space-y-1.5 rounded-md border border-dashed border-[#C9DBF7] bg-[#F7FAFF] p-2.5"
         data-testid={`role-advanced-panel-${module.id}`}>
      <p className="text-[10px] text-[#6B6B73]">
        Atur aksi per halaman. Memilih aksi apa pun otomatis menyalakan <b>Lihat</b>; mencabut Lihat mematikan semua aksi halaman itu.
      </p>
      {module.resources.map((res) => {
        const full = fullActions(module, res);
        const have = new Set(perms[res] || []);
        const allOn = full.length > 0 && full.every((a) => have.has(a));
        const changed = original && !sameActions(perms[res], original[res]);
        return (
          <div key={res} className={`rounded-md border bg-white px-2.5 py-2 ${changed ? "border-[#F0C88A]" : "border-[#EFF0F2]"}`}
               data-testid={`role-resource-row-${res}`}>
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              <p className="text-[11px] font-bold text-[#1C1C1E]" data-testid={`role-resource-label-${res}`}>{rl[res] || res}</p>
              <span className="text-[9.5px] text-[#8E8E93]">{have.size}/{full.length} aksi</span>
              {changed && <span className="text-[9.5px] font-semibold text-[#8C4A00]" data-testid={`role-resource-changed-${res}`}>diubah</span>}
              <span className="ml-auto flex gap-1">
                <button type="button" disabled={disabled} data-testid={`role-resource-all-${res}`}
                        onClick={() => onSetResource(res, true)}
                        className={`rounded-full border px-2 py-0.5 text-[9.5px] font-semibold ${allOn ? "border-[#1B7F4B] text-[#1B7F4B]" : "border-[#E5E5EA] text-[#6B6B73] hover:border-[#1C1C1E]/40"}`}>
                  Semua
                </button>
                <button type="button" disabled={disabled} data-testid={`role-resource-none-${res}`}
                        onClick={() => onSetResource(res, false)}
                        className={`rounded-full border px-2 py-0.5 text-[9.5px] font-semibold ${!have.size ? "border-[#1C1C1E] text-[#1C1C1E]" : "border-[#E5E5EA] text-[#6B6B73] hover:border-[#1C1C1E]/40"}`}>
                  Tidak ada
                </button>
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {full.map((a) => {
                const on = have.has(a);
                return (
                  <button key={a} type="button" disabled={disabled} aria-pressed={on}
                          data-testid={`role-action-${res}-${a}`}
                          onClick={() => onToggle(res, a)}
                          className={`inline-flex items-center gap-0.5 rounded-md border px-1.5 py-0.5 text-[10px] font-semibold transition-colors disabled:opacity-50 ${
                            on ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] bg-white text-[#8E8E93] hover:border-[#1C1C1E]/40"}`}>
                    {on && <Check size={9} />} {al[a] || a}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
