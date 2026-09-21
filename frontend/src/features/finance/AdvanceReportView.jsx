/**
 * AdvanceReportView (KEB-PDPT, S#090) — Laporan Uang Muka Pelanggan.
 * Saldo 2-1400 per pelanggan: uang muka pesanan yang belum dikirim (+umur) dan deposit.
 * Sumber: GET /api/ar/advance-report?entity_id=
 */
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Search, Wallet, Clock3, Users, ChevronDown, ChevronRight, PackageOpen } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import ErrorNotice from "../../components/ErrorNotice";
import { formatCurrency } from "../../utils/formatters";
import { formatDateId } from "../../components/KNDatePicker";

const BUCKETS = [
  { key: "0_30", label: "≤ 30 hari", tone: "#1B7F4B", bg: "#E6F6EC" },
  { key: "31_60", label: "31–60 hari", tone: "#B45309", bg: "#FDF3E7" },
  { key: "61_90", label: "61–90 hari", tone: "#C0392B", bg: "#FCEBEA" },
  { key: "90_plus", label: "> 90 hari", tone: "#7F1D1D", bg: "#FCEBEA" },
];

const STATUS_LABEL = {
  draft: "Draf", waiting_approval: "Menunggu persetujuan", approved: "Disetujui", confirmed: "Dikonfirmasi",
  partially_picked: "Sebagian diambil", picked: "Diambil", partially_shipped: "Dikirim sebagian",
};

export default function AdvanceReportView({ selectedEntity, onOpenDocument }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedEntity && selectedEntity !== "all") params.entity_id = selectedEntity;
      if (q.trim()) params.q = q.trim();
      const res = await axios.get(`${API}/ar/advance-report`, { params });
      setData(res.data || null);
      setError("");
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal memuat laporan uang muka.");
    } finally {
      setLoading(false);
    }
  }, [selectedEntity, q]);

  useEffect(() => { load(); }, [load]);

  const t = data?.totals || {};
  const rows = data?.rows || [];

  return (
    <div className="space-y-4" data-testid="advance-report">
      <section className="section-card p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold md:text-lg" data-testid="advance-report-title">Laporan Uang Muka Pelanggan</h2>
            <p className="max-w-2xl text-[12px] text-[#6B6B73]">
              Kas yang sudah diterima tetapi barangnya belum keluar gudang — kewajiban di akun
              <b> 2-1400 Uang Muka Pelanggan</b>. Berkurang otomatis (pro-rata) setiap surat jalan terbit.
              Deposit = kelebihan bayar yang belum dialokasikan ke pesanan.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="relative">
              <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
              <input data-testid="advance-report-search" className="form-input pl-7 text-[12px]" placeholder="Cari pelanggan / no. pesanan"
                value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
            <button data-testid="advance-report-refresh" className="btn-secondary btn-xs" onClick={load} disabled={loading}>
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Muat ulang
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3" data-testid="advance-report-metrics">
          <Metric icon={Wallet} label="Total Kewajiban 2-1400" value={formatCurrency(t.liability || 0)} tone="rgba(0,88,204,.14)" testId="advance-metric-liability" />
          <Metric icon={PackageOpen} label="Uang Muka Pesanan" value={formatCurrency(t.advance_orders || 0)} sub={`${t.orders || 0} pesanan belum dikirim`} tone="rgba(255,149,0,.16)" testId="advance-metric-orders" />
          <Metric icon={Users} label="Deposit / Kelebihan Bayar" value={formatCurrency(t.deposit_balance || 0)} sub={`${t.customers || 0} pelanggan`} tone="rgba(52,199,89,.16)" testId="advance-metric-deposit" />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="advance-report-buckets">
          {BUCKETS.map((b) => (
            <div key={b.key} data-testid={`advance-bucket-${b.key}`} className="rounded-lg px-3 py-2" style={{ background: b.bg }}>
              <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: b.tone }}>
                <Clock3 size={10} className="mr-1 inline" />{b.label}
              </p>
              <p className="text-[13px] font-bold" style={{ color: b.tone }}>{formatCurrency((t.buckets || {})[b.key] || 0)}</p>
            </div>
          ))}
        </div>
      </section>

      {error && <ErrorNotice message={error} onRetry={load} />}

      <section className="section-card overflow-hidden">
        {loading && !data ? (
          <p className="py-12 text-center text-[12px] text-[#6B6B73]" data-testid="advance-report-loading">Memuat…</p>
        ) : rows.length === 0 ? (
          <div className="py-12 text-center" data-testid="advance-report-empty">
            <Wallet size={28} className="mx-auto mb-2 text-[#C7C7CC]" />
            <p className="text-[13px] font-semibold text-[#6B6B73]">Tidak ada uang muka yang tertahan</p>
            <p className="text-[11px] text-[#8E8E93]">Semua kas pelanggan sudah menjadi pelunasan piutang atau belum ada uang muka.</p>
          </div>
        ) : (
          <table className="w-full text-[12px]">
            <thead className="bg-[#FAFBFC] text-left text-[10.5px] uppercase tracking-wide text-[#6B6B73]">
              <tr>
                <th className="px-3 py-2">Pelanggan</th>
                <th className="px-3 py-2 text-right">Uang Muka Pesanan</th>
                <th className="px-3 py-2 text-right">Deposit</th>
                <th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2 text-right">Umur Tertua</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <CustomerRows key={c.customer_id} c={c} open={!!open[c.customer_id]}
                  onToggle={() => setOpen((s) => ({ ...s, [c.customer_id]: !s[c.customer_id] }))}
                  onOpenDocument={onOpenDocument} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function CustomerRows({ c, open, onToggle, onOpenDocument }) {
  const hasOrders = (c.orders || []).length > 0;
  return (
    <>
      <tr data-testid={`advance-customer-${c.customer_id}`} className="border-t border-[#EFF0F2] hover:bg-[#FAFBFC]">
        <td className="px-3 py-2">
          <button type="button" data-testid={`advance-customer-toggle-${c.customer_id}`}
            className="inline-flex items-center gap-1.5 font-semibold text-[#1C1C1E] disabled:opacity-60"
            onClick={onToggle} disabled={!hasOrders}>
            {hasOrders ? (open ? <ChevronDown size={13} /> : <ChevronRight size={13} />) : <span className="w-[13px]" />}
            {c.customer_name}
            <span className="rounded-full bg-[#F2F3F5] px-1.5 text-[10px] font-semibold text-[#6B6B73]">{c.orders.length} pesanan</span>
          </button>
        </td>
        <td className="px-3 py-2 text-right font-semibold text-[#B45309]">{formatCurrency(c.advance_orders)}</td>
        <td className="px-3 py-2 text-right text-[#1B7F4B]">{formatCurrency(c.deposit_balance)}</td>
        <td className="px-3 py-2 text-right font-bold" data-testid={`advance-customer-total-${c.customer_id}`}>{formatCurrency(c.total)}</td>
        <td className="px-3 py-2 text-right text-[#6B6B73]">{c.oldest_days > 0 ? `${c.oldest_days} hari` : (hasOrders ? "hari ini" : "—")}</td>
      </tr>
      {open && c.orders.map((o) => {
        const b = BUCKETS.find((x) => x.key === o.bucket) || BUCKETS[0];
        return (
          <tr key={o.order_id} data-testid={`advance-order-${o.order_id}`} className="border-t border-dashed border-[#EFF0F2] bg-[#FCFCFD]">
            <td className="px-3 py-1.5 pl-9">
              <button type="button" data-testid={`advance-order-open-${o.order_id}`}
                className="font-semibold text-[#0058CC] hover:underline"
                onClick={() => onOpenDocument?.({ view: "orders", nav_id: "sales-orders", focus_type: "sales_order", focus_id: o.order_id, number: o.order_number })}>
                {o.order_number}
              </button>
              <span className="ml-2 text-[10.5px] text-[#6B6B73]">
                {STATUS_LABEL[o.status] || o.status} · pendapatan diakui {o.revenue_recognized_pct}% · kwitansi {o.receipts.map((r) => r.receipt_number).filter(Boolean).join(", ") || "—"}
              </span>
            </td>
            <td className="px-3 py-1.5 text-right text-[#B45309]">{formatCurrency(o.advance_unrecognized)}</td>
            <td className="px-3 py-1.5 text-right text-[#9A9BA3]">—</td>
            <td className="px-3 py-1.5 text-right text-[#6B6B73]">dari {formatCurrency(o.grand_total)}</td>
            <td className="px-3 py-1.5 text-right">
              <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold" style={{ background: b.bg, color: b.tone }}>
                {o.age_days} hari · sejak {o.oldest_receipt_date ? formatDateId(o.oldest_receipt_date, "dd MMM yyyy") : "—"}
              </span>
            </td>
          </tr>
        );
      })}
    </>
  );
}

function Metric({ icon: Icon, label, value, sub, tone, testId }) {
  return (
    <div data-testid={testId} className="flex items-center gap-3 rounded-xl border border-[#EFF0F2] bg-white p-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ background: tone }}>
        <Icon size={16} className="text-[#1C1C1E]" />
      </span>
      <div className="min-w-0">
        <p className="text-[10.5px] font-semibold uppercase tracking-wide text-[#6B6B73]">{label}</p>
        <p className="truncate text-[15px] font-bold text-[#1C1C1E]">{value}</p>
        {sub && <p className="text-[10.5px] text-[#8E8E93]">{sub}</p>}
      </div>
    </div>
  );
}
