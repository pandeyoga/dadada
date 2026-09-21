import { useEffect, useState } from 'react';
import { Link2 } from 'lucide-react';
import axios, { API } from '../../services/apiClient';
import KNSelect from '../../components/KNSelect';
import { CatalogDialog } from './CatalogDialog';
import { catalogApi, catalogError } from './catalogApi';

export const LinkExistingVariant = ({ template, onClose, onSaved }) => {
  const [products, setProducts] = useState([]); const [id, setId] = useState(''); const [options, setOptions] = useState({}); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { axios.get(`${API}/products`).then(r => setProducts(r.data.filter(p => p.template_id !== template.id && !p.spec_id && p.fabric_type === template.fabric_type && p.stage === template.stage && p.base_unit === template.base_unit))).catch(e => setError(catalogError(e))); }, [template.id]); // eslint-disable-line
  const save = async () => { setBusy(true); setError(''); try { await catalogApi.product(id, { template_id: template.id, variant_options: options, variant_attrs: {} }); onSaved(); } catch (e) { setError(catalogError(e)); } finally { setBusy(false); } };
  return <CatalogDialog title="Tautkan SKU lama dengan pemetaan atribut" testId="link-variant-dialog" onClose={onClose} busy={busy}><div className="space-y-4">
    {error && <p data-testid="link-variant-error" role="alert" className="text-sm text-red-700">{error}</p>}
    <KNSelect data-testid="link-variant-product" className="field" placeholder="Pilih SKU yang sesuai jenis kain/tahap/satuan" value={id} onValueChange={setId} options={products.map(p => ({ value: p.id, label: `${p.sku} · ${p.name}` }))} />
    {(template.axes || []).map(a => <label key={a.key} className="block text-xs font-semibold">{a.label}<KNSelect data-testid={`link-variant-axis-${a.key}`} className="field mt-1" value={options[a.key] || ''} onValueChange={v => setOptions(p => ({ ...p, [a.key]: v }))} options={a.options.map(o => ({ value: o.code, label: o.label }))} /></label>)}
    <p data-testid="link-variant-warning" className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">SKU, ID, stok, harga dan dokumen tetap sama. Pilih atribut yang benar-benar sesuai barang; hanya pengelompokan katalog yang dipindahkan. SKU terkait R&D tidak dapat dipindahkan lewat form ini.</p>
    <div className="flex justify-end gap-2"><button data-testid="link-variant-cancel" className="secondary-button" onClick={onClose} disabled={busy}>Batal</button><button data-testid="link-variant-save" className="primary-button" disabled={busy || !id || (template.axes || []).some(a => !options[a.key])} onClick={save}><Link2 size={14} />{busy ? 'Menyimpan…' : 'Tautkan SKU'}</button></div>
  </div></CatalogDialog>;
};