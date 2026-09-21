import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { formatCurrency } from "../../utils/formatters";

/** §D — induk = katalog & agregasi: varian + stok tersedia/dipesan + roll (bertag) per varian. */
export default function TemplateFamilySummary({ templateId }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!templateId) return;
    setD(null);
    axios.get(`${API}/product-templates/${templateId}/summary`).then((r) => setD(r.data))
      .catch((e) => setErr(e.response?.data?.detail || "Ringkasan induk tidak bisa dimuat."));
  }, [templateId]);
  if (err) return <div className="notice-bar danger mt-2" data-testid="tpl-family-error">{String(err)}</div>;
  if (!d) return <div className="text-[12px] text-[#9A9BA3] p-3 animate-pulse">Memuat ringkasan induk…</div>;
  const t = d.totals || {};
  return (
    <div className="mt-2" data-testid="tpl-family-summary">
      <div className="grid grid-cols-4 gap-2 mb-2">
        {[["Varian", t.variants], ["Tersedia", t.available], ["Dipesan", t.reserved], ["Roll", t.rolls]].map(([l, v]) => (
          <div key={l} className="metric-tile"><div className="text-[11px] text-[#6E6E73]">{l}</div><div className="text-lg font-bold tabular-nums" data-testid={`tpl-family-${l.toLowerCase()}`}>{v ?? 0}</div></div>
        ))}
      </div>
      {!d.variants?.length ? (
        <div className="text-[12px] text-[#6B6B73] p-3" data-testid="tpl-family-empty">Belum ada varian pada induk ini — buat varian (warna/grade) lewat tombol "Buat Varian".</div>
      ) : (
        <table className="data-table text-[12px]">
          <thead><tr><th>SKU</th><th>Varian</th><th className="text-right">Harga</th><th className="text-right">Tersedia</th><th className="text-right">Dipesan</th><th className="text-right">Roll (bertag)</th></tr></thead>
          <tbody>
            {d.variants.map((v) => (
              <tr key={v.id} data-testid={`tpl-variant-${v.id}`}>
                <td className="font-mono">{v.sku}</td><td>{v.variant_label || v.name}</td>
                <td className="text-right tabular-nums">{formatCurrency(v.price || 0)}</td>
                <td className="text-right tabular-nums">{v.available}</td><td className="text-right tabular-nums">{v.reserved}</td>
                <td className="text-right tabular-nums">{v.rolls} ({v.rolls_tagged})</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
