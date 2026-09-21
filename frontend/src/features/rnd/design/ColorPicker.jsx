/** ColorPicker — palet warna WAJIB dari Pustaka Warna (master); tidak ada ketik bebas. */
import { useEffect, useMemo, useState } from "react";
import { Palette, Search, X } from "lucide-react";
import { listColors } from "../rndApi";

export default function ColorPicker({ value = [], onChange, testId = "design-colors", compact = false }) {
  const [all, setAll] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    listColors().then((rows) => setAll(Array.isArray(rows) ? rows : [])).catch(() => setAll([]));
  }, []);

  const chosen = new Set(value.map((c) => c.color_id));
  const options = useMemo(() => {
    const s = q.trim().toLowerCase();
    return all.filter((c) => !chosen.has(c.id) && (!s || `${c.code} ${c.name} ${c.family} ${c.hex}`.toLowerCase().includes(s))).slice(0, 40);
  }, [all, q, value]); // eslint-disable-line react-hooks/exhaustive-deps

  const add = (c) => {
    onChange([...value, { color_id: c.id, code: c.code, name: c.name, hex: c.hex, role: "" }]);
    setQ("");
  };

  return (
    <div data-testid={testId}>
      <div className="flex flex-wrap gap-1.5">
        {value.map((c, i) => (
          <span key={c.color_id} data-testid={`${testId}-chip-${c.code}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E5EA] bg-white py-0.5 pl-1 pr-2 text-[11px]">
            <span className="h-4 w-4 rounded-full border border-black/10" style={{ background: c.hex }} />
            <span className="font-semibold">{c.code}</span>
            {!compact && <span className="text-[#6B6B73]">{c.name}</span>}
            {!compact && (
              <input value={c.role || ""} placeholder="peran" data-testid={`${testId}-role-${c.code}`}
                onChange={(e) => onChange(value.map((x, j) => (j === i ? { ...x, role: e.target.value } : x)))}
                className="w-16 border-b border-dashed border-[#C7C7CC] bg-transparent text-[10px] outline-none" />
            )}
            <button type="button" onClick={() => onChange(value.filter((x) => x.color_id !== c.color_id))}
              className="text-[#9A9BA3] hover:text-red-500" aria-label="hapus warna"><X size={11} /></button>
          </span>
        ))}
        <button type="button" data-testid={`${testId}-add`} onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1 rounded-full border border-dashed border-[#6B219A] px-2 py-0.5 text-[11px] text-[#6B219A] hover:bg-[#F1E9F7]">
          <Palette size={11} /> {open ? "Tutup" : "Pilih warna dari master"}
        </button>
      </div>
      {open && (
        <div className="mt-2 rounded-lg border border-[#E5E5EA] bg-white p-2" data-testid={`${testId}-panel`}>
          <div className="relative mb-2">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} data-testid={`${testId}-search`}
              className="field !py-1 !pl-7 text-[11.5px]" placeholder="Cari kode / nama / hex…" />
          </div>
          {all.length === 0 ? (
            <p className="text-[11px] text-[#9A9BA3]">Pustaka Warna kosong — tambahkan warna di Master → Pustaka Warna.</p>
          ) : (
            <div className="grid max-h-48 grid-cols-2 gap-1 overflow-auto sm:grid-cols-3">
              {options.map((c) => (
                <button key={c.id} type="button" onClick={() => add(c)} data-testid={`${testId}-option-${c.code}`}
                  className="flex items-center gap-2 rounded px-1.5 py-1 text-left text-[11px] hover:bg-[#F5F5F7]">
                  <span className="h-6 w-6 shrink-0 rounded border border-black/10" style={{ background: c.hex }} />
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{c.code}</span>
                    <span className="block truncate text-[10px] text-[#6B6B73]">{c.name} · {c.hex}</span>
                  </span>
                </button>
              ))}
              {options.length === 0 && <p className="col-span-full text-[11px] text-[#9A9BA3]">Tidak ada warna yang cocok.</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
