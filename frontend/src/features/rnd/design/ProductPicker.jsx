/** ProductPicker — rekomendasi/peruntukan produk (OPSIONAL, boleh lebih dari satu). */
import { useEffect, useMemo, useState } from "react";
import { Package, Search, X } from "lucide-react";
import { listProductsLite } from "../rndApi";

export default function ProductPicker({ value = [], onChange, testId = "design-products" }) {
  const [all, setAll] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => { listProductsLite().then(setAll).catch(() => setAll([])); }, []);

  const chosen = new Set(value.map((p) => p.id));
  const options = useMemo(() => {
    const s = q.trim().toLowerCase();
    return all.filter((p) => !chosen.has(p.id) && (!s || `${p.sku} ${p.name}`.toLowerCase().includes(s))).slice(0, 30);
  }, [all, q, value]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div data-testid={testId}>
      <div className="flex flex-wrap gap-1.5">
        {value.map((p) => (
          <span key={p.id} data-testid={`${testId}-chip-${p.sku}`}
            className="inline-flex items-center gap-1 rounded-full bg-[#EEF4FF] px-2 py-0.5 text-[11px] text-[#0058CC]">
            <Package size={10} /> <b>{p.sku}</b> <span className="text-[#3C3C43]">{p.name}</span>
            <button type="button" onClick={() => onChange(value.filter((x) => x.id !== p.id))}
              className="text-[#0058CC]/60 hover:text-red-500" aria-label="hapus produk"><X size={11} /></button>
          </span>
        ))}
        <button type="button" data-testid={`${testId}-add`} onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1 rounded-full border border-dashed border-[#0058CC] px-2 py-0.5 text-[11px] text-[#0058CC] hover:bg-[#EEF4FF]">
          <Package size={11} /> {open ? "Tutup" : "Pilih produk (opsional)"}
        </button>
      </div>
      {open && (
        <div className="mt-2 rounded-lg border border-[#E5E5EA] bg-white p-2">
          <div className="relative mb-2">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} data-testid={`${testId}-search`}
              className="field !py-1 !pl-7 text-[11.5px]" placeholder="Cari SKU / nama produk…" />
          </div>
          <div className="max-h-44 overflow-auto">
            {options.map((p) => (
              <button key={p.id} type="button" data-testid={`${testId}-option-${p.sku}`}
                onClick={() => { onChange([...value, { id: p.id, sku: p.sku, name: p.name }]); setQ(""); }}
                className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[11px] hover:bg-[#F5F5F7]">
                <b className="shrink-0">{p.sku}</b><span className="truncate text-[#6B6B73]">{p.name}</span>
              </button>
            ))}
            {options.length === 0 && <p className="text-[11px] text-[#9A9BA3]">Tidak ada produk yang cocok.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
