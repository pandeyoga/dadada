import { useEffect, useRef, useState } from "react";
import KNSelect from "../../components/KNSelect";
import { catalogApi, catalogError } from "./catalogApi";

const emptySelection = (invalid = "") => ({ template_id: "", target_product_id: "", variant_attrs: {}, variant_options: {}, color_target: null, invalid });

export const SpecVariantFields = ({ initial, onChange, onInherit }) => {
  const [families, setFamilies] = useState([]);
  const [family, setFamily] = useState(null);
  const [tid, setTid] = useState(initial?.templateId || "");
  const [choices, setChoices] = useState({});
  const [loading, setLoading] = useState(!!initial?.templateId);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const callbacks = useRef({ onChange, onInherit });
  callbacks.current = { onChange, onInherit };

  useEffect(() => {
    let live = true;
    setListLoading(true);
    catalogApi.list().then(rows => { if (live) { setFamilies(rows.filter(t => t.status === "active")); setError(""); } })
      .catch(e => { if (live) setError(catalogError(e)); })
      .finally(() => { if (live) setListLoading(false); });
    return () => { live = false; };
  }, [retry]);

  const resolve = (tpl, options) => {
    const axes = tpl.axes || [];
    const variants = tpl.variants || [];
    const attrs = Object.fromEntries(axes.flatMap(a => {
      const o = a.options.find(o => o.code === options[a.key]);
      return o ? [[a.key, o.label]] : [];
    }));
    const existing = variants.find(v => axes.length && axes.every(a => v.variant_options?.[a.key] === options[a.key]));
    const target = initial?.productId ? variants.find(v => v.id === initial.productId) : existing;
    const invalid = initial?.productId && !target ? "SKU tujuan tidak ditemukan dalam induk ini."
      : axes.some(a => !a.options.some(o => o.code === options[a.key])) ? "Pilih seluruh atribut varian."
      : target && (target.spec_id || target.lifecycle === "produksi" || !target.lifecycle)
        ? "Kombinasi ini sudah memiliki SKU yang dirilis/terhubung R&D. Pilih kombinasi baru." : "";
    const option = key => axes.find(a => a.key === key)?.options.find(o => o.code === options[key]);
    const color = option("color"), width = option("lebar"), grade = option("grade");
    callbacks.current.onChange({ template_id: tpl.id, target_product_id: target?.id || "", variant_attrs: attrs,
      variant_options: options, invalid, color_target: color ? { code: color.value || color.code } : null });
    callbacks.current.onInherit({
      ...(width ? { lebar: String(Number(width.value) * 100) } : {}),
      ...(grade ? { grade: grade.value || grade.code } : {}),
    });
  };

  useEffect(() => {
    let live = true;
    setFamily(null); setChoices({}); setError("");
    if (!tid) { setLoading(false); callbacks.current.onChange(emptySelection()); return; }
    setLoading(true);
    callbacks.current.onChange(emptySelection("Memuat kombinasi induk…"));
    catalogApi.detail(tid).then(tpl => {
      if (!live) return;
      const target = (tpl.variants || []).find(v => v.id === initial?.productId);
      const opts = target?.variant_options || {};
      setFamily(tpl); setChoices(opts);
      callbacks.current.onInherit({ stage: tpl.stage, fabric_type: tpl.fabric_type, gramasi: target?.gramasi ?? tpl.gramasi ?? "",
        lebar: String(Number(target?.lebar ?? tpl.lebar ?? 0) * 100), base_unit: tpl.base_unit, category: tpl.category,
        title: target?.name || tpl.name, sku_hint: target?.sku || "", line_code: tpl.line_code || "", grade: target?.grade || "" });
      resolve(tpl, opts);
    }).catch(e => {
      if (live) { setError(catalogError(e)); callbacks.current.onChange(emptySelection("Induk belum berhasil dimuat.")); }
    }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [tid, initial?.productId, retry]); // eslint-disable-line react-hooks/exhaustive-deps

  const chooseFamily = value => {
    callbacks.current.onChange(emptySelection(value ? "Memuat kombinasi induk…" : ""));
    setFamily(null); setChoices({}); setTid(value);
  };
  return <section data-testid="spec-variant-link" aria-busy={loading} className="space-y-3 rounded-md border border-blue-100 bg-blue-50/40 p-3">
    <div className="text-xs font-semibold"><span data-testid="spec-family-label">Induk produk</span>
      <KNSelect data-testid="spec-family-select" aria-label="Induk produk" className="field mt-1" searchable
        value={tid} onValueChange={chooseFamily} disabled={!!initial?.productId || listLoading}
        options={[{ value: "", label: "Induk baru saat persetujuan" }, ...families.map(t => ({ value: t.id, label: t.name }))]} />
    </div>
    {loading && <p data-testid="spec-family-loading" role="status" className="text-xs text-blue-700">Memuat kombinasi induk…</p>}
    {error && <div role="alert"><p data-testid="spec-family-error" className="text-sm text-red-700">{error}</p>
      <button type="button" data-testid="spec-family-retry" className="secondary-button mt-2" onClick={() => setRetry(n => n + 1)}>Coba lagi</button></div>}
    {family && <div className="grid gap-2 sm:grid-cols-2">{(family.axes || []).map(a => <div key={a.key} className="text-xs font-semibold">
      <span data-testid={`spec-axis-label-${a.key}`}>{a.label}</span>
      <KNSelect data-testid={`spec-axis-${a.key}`} aria-label={a.label} className="field mt-1" value={choices[a.key] || ""}
        disabled={!!initial?.productId} options={a.options.map(o => ({ value: o.code, label: o.label }))}
        onValueChange={v => { const next = { ...choices, [a.key]: v }; setChoices(next); resolve(family, next); }} />
    </div>)}</div>}
  </section>;
};