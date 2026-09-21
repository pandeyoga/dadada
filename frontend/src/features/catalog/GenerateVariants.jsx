import { useState } from "react";
import { Layers3 } from "lucide-react";
import { CatalogDialog } from "./CatalogDialog";
import { catalogApi, catalogError } from "./catalogApi";
import DecimalInput from "../../components/DecimalInput";

export const GenerateVariants = ({ template, onClose, onDone }) => {
  const [axes, setAxes] = useState(template.axes || []);
  const [price, setPrice] = useState(template.base_price || 0);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const count = axes.length ? axes.reduce((n, a) => n * a.options.length, 1) : 0;
  const toggle = (key, opt) => setAxes(axes.map(a => a.key !== key ? a : { ...a, options: a.options.some(o => o.code === opt.code) ? a.options.filter(o => o.code !== opt.code) : [...a.options, opt] }));
  let rows = [{}];
  for (const a of axes) { rows = rows.flatMap(r => a.options.map(o => ({ ...r, [a.key]: o }))).slice(0, 201); }
  const run = async () => { setBusy(true); setError(""); try { const res = await catalogApi.generate(template.id, { axes, base_price: Number(String(price).replace(",", ".")) }); onDone(res); } catch (e) { setError(catalogError(e)); } finally { setBusy(false); } };
  return <CatalogDialog title={`Buat kombinasi · ${template.name}`} onClose={onClose} busy={busy} testId="generate-variants-dialog">
    <div className="space-y-4">
      {error && <p data-testid="generate-error" role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {(template.axes || []).map(a => <fieldset key={a.key}><legend data-testid={`generate-label-${a.key}`} className="mb-2 text-sm font-semibold">{a.label}</legend><div className="flex flex-wrap gap-2">{a.options.map(o => { const selected = axes.find(x => x.key === a.key)?.options.some(x => x.code === o.code); return <button type="button" key={o.code} data-testid={`generate-option-${a.key}-${o.code}`} aria-pressed={selected} onClick={() => toggle(a.key, o)} className={`rounded-md border px-3 py-2 text-xs ${selected ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-gray-200"}`}>{o.label}</button>; })}</div></fieldset>)}
      <div className="flex flex-wrap items-end justify-between gap-3"><label className="space-y-1 text-xs font-semibold">Harga dasar per SKU<DecimalInput data-testid="generate-price" className="field" min={0} value={price} onChange={setPrice} /></label><p data-testid="generate-count" className="font-semibold">{count} kombinasi</p></div>
      {count > 200 && <p data-testid="generate-limit" className="text-sm text-red-700">Maksimal 200 kombinasi per proses. Persempit pilihan.</p>}
      {count > 0 && count <= 200 && <div className="max-h-56 overflow-y-auto border-y"><div className="divide-y">{rows.map((r, i) => <div data-testid={`generate-preview-${i}`} key={i} className="flex flex-wrap justify-between gap-2 py-2 text-xs"><span>{Object.values(r).map(o => o.label).join(" · ")}</span><span className="font-mono text-gray-500">{template.sku_prefix}-{Object.values(r).map(o => o.code).join("-")}</span></div>)}</div></div>}
      <footer className="flex justify-end gap-2"><button data-testid="generate-cancel" className="secondary-button" onClick={onClose} disabled={busy}>Batal</button><button data-testid="generate-submit" className="primary-button" disabled={busy || !count || count > 200} onClick={run}><Layers3 size={14} />{busy ? "Membuat…" : `Buat ${count} kombinasi`}</button></footer>
    </div>
  </CatalogDialog>;
};