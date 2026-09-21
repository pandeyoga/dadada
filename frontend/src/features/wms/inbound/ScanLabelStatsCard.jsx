import { useEffect, useState } from "react";
import { BarChart3, ChevronDown, ChevronUp } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { apiErrorText } from "../../../utils/apiError";

const pctCls = (p) => (p >= 20 ? "text-red-700 bg-red-50 border-red-200" : p >= 5 ? "text-amber-700 bg-amber-50 border-amber-200" : "text-emerald-700 bg-emerald-50 border-emerald-200");

/** FASE SL P2 — laporan % label tidak terbaca (input manual) & selisih label vs aktual per supplier. */
export default function ScanLabelStatsCard() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || rows) return;
    setLoading(true);
    axios.get(`${API}/inbound/scan-label/stats`)
      .then((r) => setRows(r.data || []))
      .catch((e) => setError(apiErrorText(e, "Gagal memuat statistik label.")))
      .finally(() => setLoading(false));
  }, [open, rows]);

  return (
    <div data-testid="scan-label-stats-card" className="rounded-xl border border-[#EFF0F2] bg-white overflow-hidden">
      <button type="button" data-testid="scan-label-stats-toggle" onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-[#FAFBFC]">
        <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">
          <BarChart3 size={13} /> Kualitas Label Supplier (scan)
        </span>
        {open ? <ChevronUp size={14} className="text-[#6B6B73]" /> : <ChevronDown size={14} className="text-[#6B6B73]" />}
      </button>
      {open && (
        <div className="border-t border-[#EFF0F2]">
          {error && <p className="px-3 py-2 text-[11px] text-red-700" data-testid="scan-label-stats-error">{error}</p>}
          {!error && loading && <p className="px-3 py-3 text-[11.5px] text-[#6B6B73]" data-testid="scan-label-stats-loading">Memuat…</p>}
          {rows && rows.length === 0 && (
            <p className="px-3 py-3 text-[11.5px] text-[#6B6B73]" data-testid="scan-label-stats-empty">Belum ada roll hasil scan label.</p>
          )}
          {rows && rows.length > 0 && (
            <table className="w-full text-[11px]">
              <thead className="bg-[#FAFBFC] text-[10px] uppercase text-[#6B6B73]">
                <tr>
                  <th className="px-3 py-1.5 text-left">Supplier</th>
                  <th className="px-2 py-1.5 text-right">Roll scan</th>
                  <th className="px-2 py-1.5 text-right">Tak terbaca</th>
                  <th className="px-2 py-1.5 text-right">Label ≠ aktual</th>
                  <th className="px-2 py-1.5 text-right">Dikonfirmasi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFF0F2]">
                {rows.map((r) => (
                  <tr key={r.supplier_id || r.supplier_name} data-testid={`scan-label-stats-row-${r.supplier_id || "none"}`}>
                    <td className="px-3 py-1.5 font-semibold">{r.supplier_name || "—"}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{r.total_rolls}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      <span className={`rounded border px-1.5 py-0.5 font-semibold ${pctCls(r.manual_pct)}`}>{r.manual_pct}%</span>
                      <span className="ml-1 text-[#8E8E93]">({r.manual_override})</span>
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      <span className={`rounded border px-1.5 py-0.5 font-semibold ${pctCls(r.variance_pct)}`}>{r.variance_pct}%</span>
                      <span className="ml-1 text-[#8E8E93]">({r.variance_flagged})</span>
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums text-[#6B6B73]">{r.confirmed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
