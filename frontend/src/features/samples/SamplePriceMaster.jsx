import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { formatCurrency } from "../../utils/formatters";
import MoneyInput from "@/components/MoneyInput";

/** §3-C — master harga sampel per INDUK produk (terpisah dari harga daftar varian; 0 = pakai harga daftar). */
export default function SamplePriceMaster({ canEdit }) {
  const [rows, setRows] = useState(null); const [edit, setEdit] = useState({}); const [err, setErr] = useState("");
  const load = () => axios.get(`${API}/sample-prices`).then((r) => setRows(r.data || [])).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat master harga sampel."));
  useEffect(() => { load(); }, []);
  const save = async (tid) => {
    try { await axios.put(`${API}/sample-prices/${tid}`, { price_per_unit: parseFloat(edit[tid]) || 0 }); setEdit((e) => ({ ...e, [tid]: undefined })); load(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan."); }
  };
  return (
    <div className="section-card" data-testid="sample-price-master">
      <div className="section-head"><h2 className="font-bold text-[14px]">Master Harga Sampel (per induk, per satuan roll)</h2></div>
      <div className="section-body">
        {err && <div className="notice-bar danger">{String(err)}</div>}
        {rows === null ? <div className="py-6 text-center text-[12px] text-[#6B6B73] animate-pulse" data-testid="sample-price-loading">Memuat…</div>
          : rows.length === 0 ? <div className="py-8 text-center text-[12px] text-[#6B6B73]" data-testid="sample-price-empty">Belum ada induk produk.</div>
          : (
            <table className="data-table text-[12px]">
              <thead><tr><th>Induk produk</th><th>Satuan</th><th className="text-right">Harga daftar</th><th className="text-right">Harga sampel</th>{canEdit && <th />}</tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.template_id} data-testid={`sample-price-row-${r.template_id}`}>
                  <td>{r.template_name}</td><td>{r.unit}</td><td className="text-right tabular-nums">{formatCurrency(r.list_price)}</td>
                  <td className="text-right tabular-nums">
                    {canEdit && edit[r.template_id] !== undefined
                      ? <MoneyInput value={edit[r.template_id]} onChange={(v) => setEdit((e) => ({ ...e, [r.template_id]: v }))} testId={`sample-price-input-${r.template_id}`} />
                      : (r.price_per_unit > 0 ? formatCurrency(r.price_per_unit) : <span className="text-[#9A9BA3]">pakai harga daftar</span>)}
                  </td>
                  {canEdit && <td className="text-right">
                    {edit[r.template_id] !== undefined
                      ? <button className="primary-button btn-xs" onClick={() => save(r.template_id)} data-testid={`sample-price-save-${r.template_id}`}>Simpan</button>
                      : <button className="secondary-button btn-xs" onClick={() => setEdit((e) => ({ ...e, [r.template_id]: String(r.price_per_unit || "") }))} data-testid={`sample-price-edit-${r.template_id}`}>Ubah</button>}
                  </td>}
                </tr>))}</tbody>
            </table>
          )}
      </div>
    </div>
  );
}
