/**
 * SampleOrdersView — REVISI SAMPEL: daftar Pesanan Sampel (SOS-) TERPISAH dari SO roll biasa.
 * Sales melihat pesanan sampelnya sendiri; admin/manajer/Admin Sampel/Finance melihat semua.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Scissors, RefreshCw, Gift, Banknote, XCircle, CheckCircle2, Truck, PackageCheck } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { apiErrorText } from "../../utils/apiError";
import { formatCurrency, formatQty } from "../../utils/formatters";
import { SAMPLE_STATUS_LABEL } from "../../utils/sampleOrder";
import { listSampleOrders, sampleStats, cancelSampleOrder, approveSamplePayment, confirmSampleOrder } from "./sampleApi";

const FILTERS = [
  { id: "all", label: "Semua" },
  { id: "waiting_approval", label: "Menunggu ACC bayar" },
  { id: "approved", label: "Siap ke gudang" },
  { id: "confirmed,partially_picked,picked", label: "Di gudang" },
  { id: "partially_shipped,shipped,delivered", label: "Dikirim / diambil" },
  { id: "done", label: "Selesai" },
  { id: "cancelled", label: "Dibatalkan" },
];

const CUT = { requested: "menunggu potong", cut: "sudah dipotong" };

export default function SampleOrdersView({ user, selectedEntity = "all", focusDoc, onClearFocus }) {
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState("");
  const role = user?.role || "";
  const canPay = ["finance", "sample_admin", "manager", "admin"].includes(role);
  const canConfirm = ["sample_admin", "manager", "admin"].includes(role);
  const canCancel = ["sales", "sample_admin", "manager", "admin"].includes(role);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedEntity && selectedEntity !== "all") params.entity_id = selectedEntity;
      if (filter !== "all") params.status = filter;
      const [rows, st] = await Promise.all([listSampleOrders(params), sampleStats(params.entity_id ? { entity_id: params.entity_id } : {})]);
      setOrders(rows); setStats(st); setError("");
    } catch (e) { setError(apiErrorText(e, "Gagal memuat pesanan sampel.")); }
    finally { setLoading(false); }
  }, [selectedEntity, filter]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (focusDoc?.focus_type === "sample_order" && focusDoc?.focus_id) { setFilter("all"); setSelectedId(focusDoc.focus_id); onClearFocus?.(); }
  }, [focusDoc]); // eslint-disable-line

  const sel = useMemo(() => orders.find((o) => o.id === selectedId) || null, [orders, selectedId]);
  const flash = (m) => { setToast(m); setTimeout(() => setToast(""), 5000); };
  const run = async (fn, okMsg) => {
    setBusy(sel.id); setError("");
    try { await fn(); flash(okMsg); await load(); } catch (e) { setError(apiErrorText(e, "Aksi gagal.")); } finally { setBusy(""); }
  };

  const bs = stats?.by_status || {};
  return (
    <div data-testid="sample-orders-view" className="grid gap-4">
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="sample-orders-error" />
      {toast && <div data-testid="sample-orders-toast" className="rounded-md border border-[#A7D8B0] bg-[#EAF7EE] px-3 py-2 text-[12px] text-[#126E2C]">{toast}</div>}
      <section className="section-card">
        <div className="section-head">
          <div className="flex min-w-0 items-center gap-2">
            <Scissors size={15} className="text-[#9A5B00]" />
            <span className="kicker">Penjualan</span>
            <h2 data-testid="sample-orders-title">Pesanan Sampel (SOS)</h2>
          </div>
          <button data-testid="sample-orders-refresh" className="icon-button" onClick={load} aria-label="Muat ulang"><RefreshCw size={14} className={loading ? "animate-spin" : ""} /></button>
        </div>
        <p className="px-3 pt-2 text-[11.5px] text-[#6B6B73]">Pesanan sampel <b>terpisah</b> dari pesanan roll/yard biasa (SO). Gratis → langsung ke Admin Sampel; berbayar → disetujui Finance/Admin Sampel dulu → diteruskan ke gudang untuk dipotong dari roll (RFID) → dikirim / diambil.</p>
        <div data-testid="sample-orders-metrics" className="grid gap-3 p-3 sm:grid-cols-4">
          <Metric label="Total" value={stats?.total ?? "—"} testId="sample-metric-total" />
          <Metric label="Gratis / Berbayar" value={stats ? `${stats.free} / ${stats.paid}` : "—"} testId="sample-metric-billing" />
          <Metric label="Menunggu ACC bayar" value={bs.waiting_approval || 0} testId="sample-metric-waiting" tone="#FFF3D6" />
          <Metric label="Nilai berbayar" value={formatCurrency(stats?.paid_value || 0)} testId="sample-metric-value" />
        </div>
        <div data-testid="sample-orders-filters" className="flex flex-wrap gap-1.5 px-3 pb-3">
          {FILTERS.map((f) => (
            <button key={f.id} data-testid={`sample-filter-${f.id.split(",")[0]}`} onClick={() => setFilter(f.id)}
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${filter === f.id ? "border-[#9A5B00] bg-[#FFF3D6] text-[#9A5B00]" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`}>{f.label}</button>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <section className="section-card overflow-hidden">
          {loading && orders.length === 0 ? <p className="p-6 text-center text-[12px] text-[#6B6B73]">Memuat…</p>
            : orders.length === 0 ? <p data-testid="sample-orders-empty" className="p-8 text-center text-[12px] text-[#6B6B73]">Belum ada pesanan sampel untuk saringan ini.</p>
            : (
              <table className="w-full text-[12px]">
                <thead><tr className="border-b border-[#EFF0F2] text-left text-[10px] uppercase tracking-wide text-[#8E8E93]"><th className="px-3 py-2">Nomor</th><th className="px-3 py-2">Pelanggan</th><th className="px-3 py-2">Skema</th><th className="px-3 py-2">Item</th><th className="px-3 py-2">Status</th><th className="px-3 py-2 text-right">Nilai</th></tr></thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id} data-testid={`sample-order-row-${o.id}`} onClick={() => setSelectedId(o.id)}
                      className={`cursor-pointer border-b border-[#F2F3F5] hover:bg-[#FFF9EC] ${sel?.id === o.id ? "bg-[#FFF3D6]" : ""}`}>
                      <td className="px-3 py-2 font-bold text-[#9A5B00]">{o.number}</td>
                      <td className="px-3 py-2"><p className="font-semibold">{o.customer_name}</p><p className="text-[10.5px] text-[#8E8E93]">{o.sales_name || "—"}</p></td>
                      <td className="px-3 py-2"><Billing b={o.sample_billing} /></td>
                      <td className="px-3 py-2 text-[#3C3C43]">{(o.items || []).map((i) => `${i.product_name} ${formatQty(i.quantity)} ${i.base_unit || i.unit}`).join(" · ")}</td>
                      <td className="px-3 py-2"><span className={`status-pill status-${o.status}`}>{SAMPLE_STATUS_LABEL[o.status] || o.status}</span></td>
                      <td className="px-3 py-2 text-right tabular-nums">{o.sample_billing === "free" ? "Gratis" : formatCurrency(o.grand_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </section>

        <aside className="section-card" data-testid="sample-order-detail">
          {!sel ? <p className="p-6 text-center text-[12px] text-[#6B6B73]">Pilih pesanan sampel untuk melihat detail & tindakan.</p> : (
            <div className="p-3 space-y-3 text-[12px]">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Pesanan Sampel</p>
                <p data-testid="sample-detail-number" className="text-[16px] font-bold text-[#9A5B00]">{sel.number}</p>
                <p className="font-semibold">{sel.customer_name}</p>
                <p className="text-[#6B6B73]">{sel.fulfillment_method === "ambil" ? <><PackageCheck size={11} className="inline" /> Diambil di gudang {sel.pickup_date}</> : <><Truck size={11} className="inline" /> Dikirim ke {sel.shipping_city || sel.customer_city}</>}</p>
                <div className="mt-1 flex items-center gap-2"><Billing b={sel.sample_billing} /><span className={`status-pill status-${sel.status}`}>{SAMPLE_STATUS_LABEL[sel.status] || sel.status}</span></div>
              </div>
              <ul data-testid="sample-detail-items" className="divide-y divide-[#F2F3F5] rounded-md border border-[#EFF0F2]">
                {(sel.items || []).map((i) => (
                  <li key={i.product_id} className="px-2.5 py-1.5">
                    <p className="font-semibold">{i.product_name} <span className="text-[#8E8E93]">{i.sku}</span></p>
                    <p className="text-[11px] text-[#3C3C43]">{formatQty(i.quantity)} {i.base_unit || i.unit} · {CUT[i.sample_cut_status] || i.sample_cut_status || "—"}{i.child_roll_no ? ` · potongan ${i.child_roll_no} dari ${i.cut_roll_no}` : i.suggested_roll_no ? ` · saran roll ${i.suggested_roll_no}` : ""}</p>
                    {sel.sample_billing === "paid" && <p className="text-[11px] tabular-nums">{formatCurrency(i.price)}/{i.base_unit || i.unit} → {formatCurrency(i.line_total ?? i.subtotal ?? i.price * i.quantity)}</p>}
                  </li>
                ))}
              </ul>
              {sel.sample_billing === "paid" && <p className="text-right text-[13px] font-bold tabular-nums">Total {formatCurrency(sel.grand_total)}</p>}
              {sel.sample_billing === "paid" && (
                <p data-testid="sample-detail-payment" className={`rounded-md px-2.5 py-1.5 text-[11px] ${sel.sample_payment_status === "approved" ? "bg-[#EAF7EE] text-[#126E2C]" : "bg-[#FFF3D6] text-[#9A5B00]"}`}>
                  {sel.sample_payment_status === "approved" ? <><CheckCircle2 size={11} className="inline" /> Pembayaran disetujui {sel.sample_payment_approved_by}</> : "Pembayaran belum disetujui Finance/Admin Sampel."}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {canPay && sel.status === "waiting_approval" && sel.sample_billing === "paid" && (
                  <button data-testid="sample-detail-approve-payment" className="primary-button" disabled={busy === sel.id} onClick={() => run(() => approveSamplePayment(sel.id), `${sel.number}: pembayaran disetujui.`)}><Banknote size={13} /> Setujui Pembayaran</button>
                )}
                {canConfirm && sel.status === "approved" && (
                  <button data-testid="sample-detail-confirm" className="primary-button" disabled={busy === sel.id} onClick={() => run(() => confirmSampleOrder(sel.id), `${sel.number} diteruskan ke gudang — tugas potong lahir.`)}><Scissors size={13} /> Teruskan ke Gudang</button>
                )}
                {canCancel && ["waiting_approval", "approved"].includes(sel.status) && (
                  <button data-testid="sample-detail-cancel" className="secondary-button" disabled={busy === sel.id} onClick={() => run(() => cancelSampleOrder(sel.id, "Dibatalkan dari daftar pesanan sampel"), `${sel.number} dibatalkan.`)}><XCircle size={13} /> Batalkan</button>
                )}
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Riwayat</p>
                <ul data-testid="sample-detail-timeline" className="mt-1 space-y-1 text-[11px] text-[#3C3C43]">
                  {(sel.timeline || []).slice().reverse().slice(0, 8).map((t, i) => <li key={i}>• {t.label || t.event || t.action} <span className="text-[#8E8E93]">— {t.actor} · {String(t.at || t.timestamp || "").slice(0, 16).replace("T", " ")}</span></li>)}
                </ul>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Billing({ b }) {
  return b === "free"
    ? <span data-testid="sample-billing-free" className="inline-flex items-center gap-1 rounded-full bg-[#EAF7EE] px-2 py-0.5 text-[10px] font-bold text-[#126E2C]"><Gift size={10} /> GRATIS</span>
    : <span data-testid="sample-billing-paid" className="inline-flex items-center gap-1 rounded-full bg-[#FFF3D6] px-2 py-0.5 text-[10px] font-bold text-[#9A5B00]"><Banknote size={10} /> BERBAYAR</span>;
}

function Metric({ label, value, testId, tone = "#F5F5F7" }) {
  return (
    <div data-testid={testId} className="rounded-md p-2.5" style={{ background: tone }}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p>
      <p className="text-[15px] font-bold tabular-nums">{value}</p>
    </div>
  );
}
