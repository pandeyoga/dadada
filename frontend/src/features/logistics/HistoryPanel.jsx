import { useEffect, useState } from "react";
import { History, Search, Download } from "lucide-react";
import KNDatePicker, { formatDateId } from "../../components/KNDatePicker";
import KNSelect from "../../components/KNSelect";
import ErrorNotice from "../../components/ErrorNotice";
import { formatCurrency } from "../../utils/formatters";
import { logisticsHistory, MODE_LABEL, MODE_PILL, STATUS_PILL, carrierText } from "./logisticsApi";

// Riwayat pengiriman (terkirim / selesai / gagal): saring tanggal, moda, status, kata kunci.
const SIZE = 25;
export default function HistoryPanel({ params, onOpen, refreshKey }) {
  const [f, setF] = useState({ date_from: "", date_to: "", mode: "", status: "", q: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try { setData(await logisticsHistory({ ...params, ...f, page, size: SIZE })); setErr(""); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memuat riwayat."); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [params, f.date_from, f.date_to, f.mode, f.status, page, refreshKey]); // eslint-disable-line
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [f.q]); // eslint-disable-line

  const rows = data?.rows || [];
  const st = data?.stats || {};
  const pages = Math.max(1, Math.ceil((data?.total || 0) / SIZE));
  const when = (r) => String(r.completed_at || r.delivered_at || r.created_at || "").slice(0, 10);

  function exportCsv() {
    const head = ["Nomor", "Tanggal", "Pesanan", "Pelanggan", "Moda", "Pengangkut", "Surat Jalan", "Biaya kirim", "Status", "Penerima"];
    const lines = rows.map((r) => [r.number, when(r), r.order_number, r.customer_name, r.mode_label, carrierText(r), (r.shipment_nos || []).join(" "), r.shipping_cost || 0, r.status_label, r.pod?.receiver_name || ""].map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","));
    const blob = new Blob([[head.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `riwayat-pengiriman-${f.date_from || "awal"}-${f.date_to || "kini"}.csv`; a.click(); URL.revokeObjectURL(a.href);
  }

  return (
    <div className="grid gap-3" data-testid="history-panel">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2" data-testid="history-stats">
        <Stat id="total" label="Total riwayat" v={st.total} />
        <Stat id="delivered" label="Terkirim / selesai" v={st.delivered} tone="#1A7A3A" />
        <Stat id="failed" label="Gagal kirim" v={st.failed} tone={st.failed ? "#C62828" : undefined} />
        <Stat id="lead" label="Rata-rata hari kirim" v={st.avg_lead_days == null ? "—" : st.avg_lead_days} />
        <Stat id="cost" label="Biaya ekspedisi" v={formatCurrency(st.shipping_cost_total || 0)} small />
      </div>
      <section className="section-card !p-3">
        <div className="grid gap-2 sm:grid-cols-6 items-end">
          <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Dari</label><KNDatePicker data-testid="history-from" value={f.date_from} onChange={(v) => { setPage(1); setF({ ...f, date_from: v }); }} placeholder="Tgl awal" /></div>
          <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Sampai</label><KNDatePicker data-testid="history-to" value={f.date_to} onChange={(v) => { setPage(1); setF({ ...f, date_to: v }); }} placeholder="Tgl akhir" /></div>
          <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Moda</label>
            <KNSelect data-testid="history-mode" value={f.mode} onValueChange={(v) => { setPage(1); setF({ ...f, mode: v }); }} className="field" options={[{ value: "", label: "Semua moda" }, ...Object.entries(MODE_LABEL).map(([value, label]) => ({ value, label }))]} /></div>
          <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Status</label>
            <KNSelect data-testid="history-status" value={f.status} onValueChange={(v) => { setPage(1); setF({ ...f, status: v }); }} className="field" options={[{ value: "", label: "Semua" }, { value: "delivered", label: "Terkirim / Diserahkan" }, { value: "completed", label: "Selesai" }, { value: "failed", label: "Gagal kirim" }]} /></div>
          <div className="grid gap-1 sm:col-span-2"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Cari</label>
            <div className="flex gap-2"><div className="relative flex-1"><Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" /><input data-testid="history-search" className="form-input !pl-8" placeholder="Nomor, pesanan, pelanggan, resi, plat…" value={f.q} onChange={(e) => { setPage(1); setF({ ...f, q: e.target.value }); }} /></div>
              <button data-testid="history-export" className="secondary-button" onClick={exportCsv} disabled={!rows.length} title="Unduh CSV halaman ini"><Download size={13} /> CSV</button></div></div>
        </div>
      </section>
      {err && <ErrorNotice message={err} onRetry={load} testId="history-error" />}
      {loading && !data ? <div className="section-card !p-10 text-center"><p className="text-[12px] text-[#6B6B73]" data-testid="history-loading">Memuat riwayat…</p></div>
        : rows.length === 0 ? (
          <div className="section-card !p-12 text-center" data-testid="history-empty"><History size={30} className="mx-auto text-[#C7C9CF] mb-2" /><p className="text-[13px] font-semibold text-[#3A3B42]">Belum ada riwayat pengiriman{f.date_from || f.date_to || f.mode || f.q ? " untuk saringan ini" : ""}</p><p className="text-[12px] text-[#9A9BA3] mt-0.5">Pengiriman yang terkirim, selesai, atau gagal akan tercatat di sini.</p></div>
        ) : (
          <div className="section-card !p-0 overflow-x-auto">
            <table className="data-table w-full" data-testid="history-table">
              <thead><tr><th>Tanggal</th><th>Nomor</th><th>Pesanan / Pelanggan</th><th>Moda</th><th>Pengangkut / Pengambil</th><th>Surat Jalan</th><th className="text-right">Biaya</th><th>Status</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} data-testid={`history-row-${r.id}`} className="cursor-pointer hover:bg-[#F0F5FF]" onClick={() => onOpen(r.id)}>
                    <td className="text-[11.5px] tabular-nums">{when(r) ? formatDateId(when(r), "dd MMM yyyy") : "—"}</td>
                    <td className="font-mono text-[11.5px] font-bold text-[#0058CC]">{r.number}</td>
                    <td><div className="text-[12px] font-semibold">{r.order_number}</div><div className="text-[10.5px] text-[#6B6B73]">{r.customer_name}</div></td>
                    <td><span className={`status-pill ${MODE_PILL[r.mode]}`}>{r.mode_label}</span></td>
                    <td className="text-[11.5px]">{carrierText(r)}{r.pod?.receiver_name && r.mode !== "self_pickup" ? <div className="text-[10.5px] text-[#1A7A3A]">Diterima {r.pod.receiver_name}</div> : null}{r.fail_reason ? <div className="text-[10.5px] text-[#C62828]">{r.fail_reason}</div> : null}</td>
                    <td className="text-[11px]">{(r.shipment_nos || []).join(", ")}</td>
                    <td className="text-[11.5px] tabular-nums text-right">{r.shipping_cost ? formatCurrency(r.shipping_cost) : "—"}</td>
                    <td><span className={`status-pill ${STATUS_PILL[r.status]}`}>{r.status_label}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between px-3 py-2 text-[10.5px] text-[#9A9BA3] border-t border-[#F0F1F3]">
              <span data-testid="history-count">{data.total} pengiriman · halaman {page}/{pages}</span>
              <span className="flex gap-1.5"><button className="secondary-button !py-0.5 !px-2" data-testid="history-prev" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Sebelumnya</button><button className="secondary-button !py-0.5 !px-2" data-testid="history-next" disabled={page >= pages} onClick={() => setPage(page + 1)}>Berikutnya ›</button></span>
            </div>
          </div>
        )}
    </div>
  );
}

function Stat({ id, label, v, tone, small }) {
  return <div className="section-card !p-2.5" data-testid={`history-stat-${id}`}><p className="text-[10px] font-bold uppercase text-[#8E8E93]">{label}</p><p className={`${small ? "text-[14px]" : "text-[20px]"} font-bold tabular-nums`} style={{ color: tone }}>{v ?? 0}</p></div>;
}
