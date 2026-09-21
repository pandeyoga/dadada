import { useState, useEffect } from "react";
import { Plus, Trash2, X } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { catalogError } from "./catalogApi";

// Cadangan bila konfigurasi (`rnd.variant_axes_*`) belum termuat: Warna × Grade × Asal.
export const FALLBACK_AXES = [
  { key: "color", label: "Warna", options: [], preset: true },
  { key: "grade", label: "Grade", options: ["A", "A1", "A2", "B", "BS"].map(g => ({ code: g, label: g, value: g, hex: "" })), preset: true },
  { key: "origin", label: "Asal", options: [{ code: "IMP", label: "Impor", value: "impor", hex: "" }, { code: "LOK", label: "Lokal", value: "lokal", hex: "" }], preset: true },
];
export const presetAxes = (axisConfig) => (axisConfig?.catalog?.length ? axisConfig.catalog : FALLBACK_AXES)
  .filter(a => a.preset).map(a => ({ key: a.key, label: a.label, options: (a.options || []).map(o => ({ ...o })) }));

export const AxisEditor = ({ axes, onChange, structuralLocked = false, axisConfig = null }) => {
  const [label, setLabel] = useState("");
  const [key, setKey] = useState("");
  const catalog = axisConfig?.catalog?.length ? axisConfig.catalog : FALLBACK_AXES;
  const update = (idx, patch) => onChange(axes.map((a, i) => i === idx ? { ...a, ...patch } : a));
  const add = (key0, label0, opts = []) => {
    if (axes.some(a => a.key === key0) || !key0 || !label0) return;
    onChange([...axes, { key: key0, label: label0, options: opts.map(o => ({ ...o })) }]); setKey(""); setLabel("");
  };
  return <section data-testid="catalog-axis-editor" className="space-y-4 border-t pt-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold" data-testid="axis-section-title">Atribut & pilihan varian</h3>
      {!structuralLocked && <div className="flex flex-wrap gap-1">{catalog.map(a => <button type="button" key={a.key} data-testid={`axis-add-${a.key}`} className="secondary-button" title={a.preset ? "Sumbu bawaan" : "Sumbu tambahan (opsional)"} disabled={axes.some(x => x.key === a.key) || axes.length >= 6} onClick={() => add(a.key, a.label, a.options || [])}><Plus size={12} />{a.label}</button>)}</div>}
    </div>
    {!structuralLocked && <p data-testid="axis-config-hint" className="text-xs text-[#6B6B73]">Sumbu bawaan: {catalog.filter(a => a.preset).map(a => a.label).join(" × ") || "—"}. Material yang berbeda dibuat sebagai induk master data terpisah. Daftar sumbu diatur di Pusat Pengaturan → R&D & Desain.</p>}
    {!structuralLocked && <div className="flex flex-wrap gap-2">
      <input data-testid="axis-custom-label" className="field flex-1 min-w-32" value={label} onChange={e => { setLabel(e.target.value); setKey(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/_$/, "")); }} placeholder="Nama atribut lainnya" />
      <input data-testid="axis-custom-key" className="field w-36" value={key} onChange={e => setKey(e.target.value)} placeholder="kode_atribut" />
      <button type="button" data-testid="axis-add-custom" className="secondary-button" disabled={!/^[a-z][a-z0-9_]{0,39}$/.test(key) || !label || axes.length >= 6 || axes.some(a => a.key === key)} onClick={() => add(key, label)}><Plus size={13} />Tambah atribut</button>
    </div>}
    {structuralLocked && <p data-testid="axis-structure-locked" className="text-xs text-[#6B6B73]">Struktur SKU sudah terbentuk. Pilihan baru masih dapat ditambahkan.</p>}
    {!axes.length && <p data-testid="axis-empty" className="text-xs text-[#6B6B73]">Belum ada atribut.</p>}
    {axes.map((a, idx) => <div key={a.key} data-testid={`axis-editor-${a.key}`} className="border-l-2 border-[#DCE7F7] pl-3">
      <div className="mb-2 flex items-center justify-between"><span data-testid={`axis-name-${a.key}`} className="text-sm font-semibold">{a.label} <span className="text-xs font-normal text-gray-500">{a.key === "lebar" ? "(cm)" : a.key === "origin" ? "(Impor / Lokal)" : ""}</span></span>
        {!structuralLocked && <button type="button" data-testid={`axis-remove-${a.key}`} aria-label={`Hapus atribut ${a.label}`} className="icon-button" onClick={() => onChange(axes.filter((_, i) => i !== idx))}><Trash2 size={14} /></button>}
      </div>
      <div className="flex flex-wrap gap-2 mb-2">{a.options.map((o, i) => <span key={i} data-testid={`axis-option-${a.key}-${i}`} className="inline-flex items-center gap-1 rounded border bg-[#FAFBFC] px-2 py-1 text-xs">
        {o.hex && <span className="h-3 w-3 rounded-full border" style={{ background: o.hex }} />}{o.label} <span className="text-gray-400">{o.code}</span>
        {!o.locked && <button type="button" data-testid={`axis-option-remove-${a.key}-${i}`} aria-label={`Hapus ${o.label}`} onClick={() => update(idx, { options: a.options.filter((_, j) => j !== i) })}><X size={12} /></button>}
      </span>)}</div>
      {a.key === "color" ? <ColorOptions selected={a.options} onSelect={c => { if (!a.options.some(o => o.code === c.code)) update(idx, { options: [...a.options, { label: c.name, code: c.code, value: c.code, hex: c.hex }] }); }} />
        : <OptionInput axis={a} onAdd={o => update(idx, { options: [...a.options, o] })} />}
    </div>)}
  </section>;
};
const ColorOptions = ({ selected, onSelect }) => {
  const [colors, setColors] = useState(null); const [query, setQuery] = useState(''); const [error, setError] = useState('');
  const load = () => axios.get(`${API}/color-library`).then(r => { setColors(r.data); setError(''); }).catch(e => setError(catalogError(e)));
  useEffect(() => { load(); }, []);
  return <div data-testid="axis-color-library" className="space-y-2">
    <input data-testid="axis-color-search" className="field" placeholder="Cari kode/nama di pustaka warna" value={query} onChange={e => setQuery(e.target.value)} />
    {error && <p data-testid="axis-color-error" className="text-xs text-red-700">{error}<button type="button" data-testid="axis-color-retry" className="ml-2 underline" onClick={load}>Coba lagi</button></p>}
    {!colors && !error && <p data-testid="axis-color-loading" className="text-xs text-gray-500">Memuat warna…</p>}
    <div className="grid max-h-44 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-5">{(colors || []).filter(c => `${c.code} ${c.name}`.toLowerCase().includes(query.toLowerCase())).map(c => <button type="button" key={c.id} data-testid={`axis-color-pick-${c.id}`} className="flex min-h-12 flex-col gap-1 rounded border bg-white p-2 text-left text-[10px] disabled:opacity-40" disabled={selected.some(o => o.code === c.code)} onClick={() => onSelect(c)}><span className="h-4 w-full rounded-sm border" style={{ background: c.hex }} /><b>{c.code}</b><span>{c.name}</span></button>)}</div>
    {colors && !colors.length && <p data-testid="axis-color-empty" className="text-xs text-gray-500">Pustaka warna belum memiliki pilihan.</p>}
  </div>;
};
const OptionInput = ({ axis, onAdd }) => {
  const [text, setText] = useState(""); const [code, setCode] = useState("");
  const add = () => { if (!text.trim() || !code || axis.options.some(o => o.code === code || o.label === text.trim())) return; onAdd({ label: axis.key === "lebar" ? `${text.trim()}cm` : text.trim(), code, value: axis.key === "lebar" ? Number(text.replace(",", ".")) / 100 : axis.key === "origin" ? text.trim().toLowerCase() : "", hex: "" }); setText(""); setCode(""); };
  return <div className="flex flex-wrap gap-2">
    <input data-testid={`axis-value-${axis.key}`} className="field flex-1 min-w-24" placeholder={axis.key === "lebar" ? "Lebar, contoh 150" : `Pilihan ${axis.label}`} value={text} onChange={e => { setText(e.target.value); setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 16)); }} />
    <input data-testid={`axis-code-${axis.key}`} className="field w-28" placeholder="Kode SKU" value={code} onChange={e => setCode(e.target.value.toUpperCase())} />
    <button type="button" data-testid={`axis-option-add-${axis.key}`} aria-label={`Tambah pilihan ${axis.label}`} className="secondary-button" disabled={!text || !/^[A-Z0-9][A-Z0-9_.-]{0,39}$/.test(code) || axis.options.length >= 50} onClick={add}><Plus size={14} /></button>
  </div>;
};
