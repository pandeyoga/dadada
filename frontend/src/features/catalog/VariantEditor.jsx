import { useState } from "react";
import { Save } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import DecimalInput from "../../components/DecimalInput";
import { CatalogDialog } from "./CatalogDialog";
import { catalogApi, catalogError } from "./catalogApi";
export const VariantEditor = ({ product, template, onClose, onSaved }) => {
  const [f, setF] = useState({ name: product?.name || template.name, sku: product?.sku || "", price: product?.price ?? template.base_price ?? 0, description: product?.description || template.description || "", status: product?.status || "active" });
  const [options, setOptions] = useState(product?.variant_options || {});
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k, v) => setF(p => ({ ...p, [k]: v }));
  const save = async e => {
    e.preventDefault(); setBusy(true); setError("");
    try {
      let body = { ...f };
      if (!product?.id) body = { ...body, template_id: template.id, variant_options: options, variant_attrs: {}, fabric_type: template.fabric_type, stage: template.stage, base_unit: template.base_unit, gramasi: template.gramasi, lebar: template.lebar, category: template.category, yarn_count: template.yarn_count || "", yarn_count_system: template.yarn_count_system || "", line_code: template.line_code || "", exclusivity: template.exclusivity || "umum", owner_sales_ids: template.owner_sales_ids || [] };
      await catalogApi.product(product?.id, body); onSaved();
    } catch (e) { setError(catalogError(e)); } finally { setBusy(false); }
  };
  return <CatalogDialog title={product ? `Ubah SKU · ${product.sku}` : `SKU baru · ${template.name}`} onClose={onClose} busy={busy} testId="variant-editor-dialog"><form onSubmit={save} className="space-y-4">
    {error && <p data-testid="variant-error" role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <div className="grid gap-3 sm:grid-cols-2">{[["sku", "Kode SKU"], ["name", "Nama varian"]].map(([k, l]) => <label key={k} className="text-xs font-semibold">{l}<input data-testid={`variant-${k}`} className="field mt-1" value={f[k]} required disabled={k === "sku" && !!product} onChange={e => set(k, e.target.value)} /></label>)}</div>
    {!product && (template.axes || []).map(a => <label className="block text-xs font-semibold" key={a.key}>{a.label}<KNSelect data-testid={`variant-option-${a.key}`} className="field mt-1" value={options[a.key] || ""} options={a.options.map(o => ({ value: o.code, label: o.label }))} onValueChange={v => setOptions(p => ({ ...p, [a.key]: v }))} /></label>)}
    {product && <p data-testid="variant-identity" className="border-l-2 border-blue-200 pl-3 text-sm">{Object.values(product.variant_attrs || {}).join(" · ")}<span className="block text-xs text-gray-500">{product.spec_id ? "Identitas terkait spesifikasi R&D" : "Identitas kombinasi tetap; SKU lain dibuat sebagai kombinasi baru"}</span></p>}
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Harga jual dasar<DecimalInput data-testid="variant-price" className="field mt-1" value={f.price} min={0} onChange={v => set("price", v)} /></label><label className="text-xs font-semibold">Status<KNSelect data-testid="variant-status" className="field mt-1" value={f.status} options={[{ value: "active", label: "Aktif" }, { value: "inactive", label: "Nonaktif" }]} onValueChange={v => set("status", v)} /></label></div>
    <label className="block text-xs font-semibold">Deskripsi<textarea data-testid="variant-description" className="field mt-1 min-h-24" value={f.description} onChange={e => set("description", e.target.value)} /></label>
    <footer className="flex justify-end gap-2"><button type="button" data-testid="variant-cancel" className="secondary-button" disabled={busy} onClick={onClose}>Batal</button><button data-testid="variant-save" type="submit" className="primary-button" disabled={busy}><Save size={14} />{busy ? "Menyimpan…" : "Simpan SKU"}</button></footer>
  </form></CatalogDialog>;
};