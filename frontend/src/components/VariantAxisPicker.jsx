import { useMemo, useState, useEffect } from "react";
import { Check } from "lucide-react";
import { variantLabel, variantAttributes } from "../utils/variants";

/** Semua dimensi yang ada dipilih secara eksplisit; tidak pernah fallback ke SKU lain. */
export default function VariantAxisPicker({ variants = [], selectedId, onSelect, testIdPrefix = "axis" }) {
  const selected = variants.find(v => v.id === selectedId);
  const [choices, setChoices] = useState(() => variantAttributes(selected));
  useEffect(() => { if (selected) setChoices(variantAttributes(selected)); }, [selectedId]); // eslint-disable-line
  const axes = useMemo(() => {
    const keys = [...new Set(variants.flatMap(v => Object.keys(variantAttributes(v))))];
    return keys.map(key => ({ key, values: [...new Set(variants.map(v => String(variantAttributes(v)[key] ?? "")))].sort() }));
  }, [variants]);
  const pick = (key, value) => {
    const next = { ...choices, [key]: value };
    setChoices(next);
    const matches = variants.filter(v => axes.every(a => String(variantAttributes(v)[a.key] ?? "") === String(next[a.key] ?? "")));
    onSelect(matches.length === 1 ? matches[0] : null);
  };
  const labels = { color: "Warna", grade: "Grade", origin: "Asal", lebar: "Lebar", size: "Ukuran", material: "Material", quality: "Kualitas" };
  return <div data-testid={`${testIdPrefix}-axes`} className="space-y-3">
    {axes.filter(a => a.values.length > 1).map(a => <fieldset key={a.key}>
      <legend className="mb-1.5 text-xs font-semibold" data-testid={`${testIdPrefix}-label-${a.key}`}>{labels[a.key] || a.key.replaceAll("_", " ")}</legend>
      <div className="flex flex-wrap gap-2">{a.values.map((value, i) => {
        const active = String(choices[a.key] ?? "") === value;
        const sample = variants.find(v => String(variantAttributes(v)[a.key] ?? "") === value);
        return <button type="button" data-testid={`${testIdPrefix}-${a.key}-${i}`} key={value} onClick={() => pick(a.key, value)} aria-pressed={active}
          className={`min-h-10 inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors ${active ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] hover:bg-gray-50"}`}>
          {a.key === "color" && sample?.color_hex && <span className="h-4 w-4 rounded-full border" style={{ background: sample.color_hex }} />}
          {value || "Standar"}{active && <Check size={12} />}
        </button>;
      })}</div>
    </fieldset>)}
    {!selected && <p role="status" data-testid={`${testIdPrefix}-unavailable`} className="rounded-md bg-amber-50 p-2 text-xs text-amber-800">Kombinasi tidak tersedia atau belum unik. Pilih kombinasi lain.</p>}
    {selected && <p data-testid={`${testIdPrefix}-selection`} className="text-xs text-[#6B6B73]">{variantLabel(selected)} · <span className="font-mono">{selected.sku}</span></p>}
  </div>;
}