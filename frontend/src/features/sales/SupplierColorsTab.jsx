/** SupplierColorsTab — sub-tab "Warna Supplier": semua versi warna supplier (dilabeli supplier), terpisah dari warna internal. */
import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Factory, Link2, Search } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import KNSelect from "../../components/KNSelect";
import axios, { API } from "../../services/apiClient";
import { openRnd } from "../rnd/rndDeepLink";
import { lifecycleMeta } from "../rnd/rndMeta";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—");

export default function SupplierColorsTab({ onOpenLinks }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [supplier, setSupplier] = useState("");
  const [linked, setLinked] = useState("");

  const load = () => {
    setLoading(true);
    axios.get(`${API}/color-library/supplier-variants`).then((r) => { setRows(Array.isArray(r.data) ? r.data : []); setError(""); })
      .catch((e) => setError(e.response?.data?.detail || "Gagal memuat warna supplier.")).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const suppliers = useMemo(() => {
    const m = new Map(); rows.forEach((r) => m.set(r.supplier_id, r.supplier_name)); return [...m.entries()];
  }, [rows]);
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return rows.filter((r) => (!supplier || r.supplier_id === supplier)
      && (!linked || (linked === "yes" ? r.products.length > 0 : r.products.length === 0))
      && (!s || `${r.supplier_color_name} ${r.supplier_color_code} ${r.supplier_name} ${r.color_code} ${r.color_name} ${r.products.map((p) => p.sku).join(" ")}`.toLowerCase().includes(s)));
  }, [rows, q, supplier, linked]);

  return (
    <div data-testid="supplier-colors-tab">
      <div className="section-head flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
          <input data-testid="supplier-color-search" className="field w-full pl-8" placeholder="Cari nama/kode warna supplier, supplier, warna internal, SKU…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <KNSelect data-testid="supplier-color-supplier-filter" className="field w-[220px]" value={supplier} onValueChange={setSupplier}
          options={[{ value: "", label: "Semua supplier" }, ...suppliers.map(([id, name]) => ({ value: id, label: name }))]} />
        <KNSelect data-testid="supplier-color-linked-filter" className="field w-[190px]" value={linked} onValueChange={setLinked}
          options={[{ value: "", label: "Semua keterkaitan" }, { value: "yes", label: "Sudah jadi produk" }, { value: "no", label: "Belum jadi produk" }]} />
      </div>
      <div className="section-body">
        <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="supplier-color-error" />
        <p className="mb-2 text-[11px] text-[#6B6B73]" data-testid="supplier-color-count">
          <b>{filtered.length}</b> versi warna supplier dari <b>{suppliers.length}</b> supplier. Setiap baris lahir otomatis saat labdip <b>ACC</b> (dialog Pilih pemenang) — bukan diketik manual.
        </p>
        {loading ? <div className="h-24 animate-pulse rounded-lg bg-[#F5F5F7]" /> : filtered.length === 0 ? (
          <div className="py-14 text-center text-[12px] text-[#8E8E93]" data-testid="supplier-color-empty"><Factory size={28} className="mx-auto mb-2 text-gray-300" />Belum ada warna supplier yang cocok.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[#EFF0F2]">
            <table className="w-full min-w-[860px] text-[11.5px]">
              <thead className="bg-[#FAFBFC] text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">
                <tr>
                  <th className="px-3 py-2 text-left">Supplier</th>
                  <th className="px-3 py-2 text-left">Warna supplier</th>
                  <th className="px-3 py-2 text-left">↔ Warna internal</th>
                  <th className="px-3 py-2 text-left">↔ Master produk</th>
                  <th className="px-3 py-2 text-left">Asal sample</th>
                  <th className="px-3 py-2 text-right">ACC</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F4F5F7]">
                {filtered.map((r) => (
                  <tr key={`${r.color_id}-${r.supplier_id}`} className="hover:bg-[#FAFBFC]" data-testid={`supplier-color-row-${r.color_id}-${r.supplier_id}`}>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1 rounded bg-[#F1E9F7] px-1.5 py-0.5 text-[10.5px] font-bold text-[#6B219A]"><Factory size={10} /> {r.supplier_name}</span>
                    </td>
                    <td className="px-3 py-2">
                      <p className="font-bold text-[#1C1C1E]">{r.supplier_color_name || "—"}</p>
                      <p className="font-mono text-[10.5px] text-[#6B6B73]">{r.supplier_color_code || "—"}</p>
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-4 w-4 rounded border border-[#E5E5EA]" style={{ background: r.hex }} />
                        <span><b>{r.color_code}</b> <span className="text-[#6B6B73]">{r.color_name}</span></span>
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {r.products.length === 0 ? <span className="text-[10.5px] text-[#9A9BA3]">belum jadi produk{r.color_products_count ? ` · warna ini punya ${r.color_products_count} produk lain` : ""}</span>
                        : r.products.map((p) => (
                          <p key={p.id} className="leading-tight"><b className="font-mono">{p.sku}</b> <span className="text-[10px]" style={{ color: lifecycleMeta(p.lifecycle).tone }}>{lifecycleMeta(p.lifecycle).label}</span></p>
                        ))}
                    </td>
                    <td className="px-3 py-2">
                      <button type="button" className="inline-flex items-center gap-1 font-mono text-[11px] text-[#0058CC] hover:underline" data-testid={`supplier-color-sample-${r.color_id}-${r.supplier_id}`}
                        onClick={() => openRnd({ view: "rnd-samples", sampleId: r.sample_id, sampleNumber: r.sample_number })}>
                        {r.sample_number || "—"} <ExternalLink size={9} />
                      </button>
                    </td>
                    <td className="px-3 py-2 text-right text-[10.5px] text-[#6B6B73]">{fmtAt(r.at)}</td>
                    <td className="px-2 py-2 text-right">
                      <button type="button" className="secondary-button !px-2 !py-1 text-[10.5px]" data-testid={`supplier-color-links-${r.color_id}-${r.supplier_id}`}
                        onClick={() => onOpenLinks(r.color_id, r.supplier_id)}><Link2 size={11} /> Keterkaitan</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
