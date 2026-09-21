import { useEffect, useMemo, useState } from "react";
import { Search, ChevronRight, ArrowLeft, Phone, MapPin, Wallet, Receipt } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { formatCurrency } from "../../../utils/formatters";
import MobileArReceipt from "./MobileArReceipt";

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "2-digit" }) : "-");
const STATUS_ID = { unpaid: "Belum bayar", partial: "Sebagian", paid: "Lunas", overdue: "Jatuh tempo" };

/** Pelanggan versi HP: daftar kartu + detail 360 satu layar (piutang, pesanan, kwitansi, sampel). */
export default function MobileCustomers({ selectedEntity }) {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/customers`, { params: selectedEntity && selectedEntity !== "all" ? { entity_id: selectedEntity } : {} })
      .then((r) => setRows(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => setErr("Gagal memuat pelanggan.")).finally(() => setLoading(false));
  }, [selectedEntity]);
  const list = useMemo(() => (rows || []).filter((c) => !q || `${c.name} ${c.phone || ""} ${c.city || ""}`.toLowerCase().includes(q.toLowerCase())), [rows, q]);
  if (sel) return <MobileCustomerDetail customer={sel} onBack={() => setSel(null)} />;
  return (
    <div className="space-y-2 p-3" data-testid="m-customers">
      <div className="m-card flex items-center gap-2 px-3 py-2"><Search size={15} className="m-muted" /><input className="w-full bg-transparent text-sm outline-none" placeholder="Cari nama / kota / telepon" value={q} onChange={(e) => setQ(e.target.value)} data-testid="m-customers-search" /></div>
      {err && <div className="notice-bar danger text-xs">{err}</div>}
      {loading && <p className="text-xs m-muted" data-testid="m-customers-loading">Memuat pelanggan…</p>}
      {rows && list.length === 0 && <p className="text-xs m-muted" data-testid="m-customers-empty">Tidak ada pelanggan.</p>}
      {list.map((c) => (
        <button key={c.id} className="m-card m-press w-full p-3 text-left" onClick={() => setSel(c)} data-testid={`m-customer-${c.id}`}>
          <div className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13.5px] font-bold">{c.name}</p>
              <p className="truncate text-[11px] m-muted">{c.city || "-"} · {c.phone || "-"}{c.sales_name ? ` · ${c.sales_name}` : ""}</p>
            </div>
            <ChevronRight size={16} className="text-[#C7C7CC]" />
          </div>
        </button>
      ))}
    </div>
  );
}

export function MobileCustomerDetail({ customer, onBack }) {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState("ar");
  const [pay, setPay] = useState(false);
  const [err, setErr] = useState("");
  const load = () => axios.get(`${API}/customers/${customer.id}/360`).then((r) => setD(r.data)).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat detail."));
  useEffect(() => { load(); }, [customer.id]); // eslint-disable-line
  const open = (d?.order_history || []).filter((o) => Number(o.grand_total || o.total_amount || 0) - Number(o.paid || 0) > 0.01);
  const outstanding = open.reduce((s, o) => s + Number(o.grand_total || o.total_amount || 0) - Number(o.paid || 0), 0);
  const overdue = open.filter((o) => o.payment_status === "overdue" || (o.due_date && new Date(o.due_date) < new Date()));
  return (
    <div className="space-y-2 p-3" data-testid="m-customer-detail">
      <button className="m-subpage-back" onClick={onBack} data-testid="m-customer-back"><ArrowLeft size={17} /> Pelanggan</button>
      <div className="m-card p-4">
        <p className="text-[15px] font-bold">{customer.name}</p>
        <p className="text-[11.5px] m-muted flex items-center gap-1"><MapPin size={11} /> {customer.city || "-"} · <Phone size={11} /> {customer.phone || "-"}</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-[#FFF4E5] p-2.5" data-testid="m-customer-outstanding"><p className="text-[10px] m-muted">Piutang terbuka</p><p className="text-[14px] font-bold tabular-nums">{formatCurrency(outstanding)}</p><p className="text-[10px] m-muted">{open.length} pesanan{overdue.length ? ` · ${overdue.length} jatuh tempo` : ""}</p></div>
          <div className="rounded-xl bg-[#EAF2FF] p-2.5"><p className="text-[10px] m-muted">Total pesanan</p><p className="text-[14px] font-bold tabular-nums">{d?.stats?.total_orders ?? (d?.order_history || []).length}</p></div>
        </div>
        <button className="primary-button mt-3 w-full py-3 flex items-center justify-center gap-2" disabled={!open.length} onClick={() => setPay(true)} data-testid="m-customer-receipt-btn"><Wallet size={16} /> Catat pembayaran</button>
      </div>
      {err && <div className="notice-bar danger text-xs">{String(err)}</div>}
      <div className="flex gap-1 text-xs">
        {[["ar", "Tagihan"], ["orders", "Pesanan"], ["receipts", "Kwitansi"], ["samples", "Sampel"]].map(([id, l]) => (
          <button key={id} className={`flex-1 rounded-lg py-2 font-semibold ${tab === id ? "bg-[#0058CC] text-white" : "bg-[#F2F3F5]"}`} onClick={() => setTab(id)} data-testid={`m-customer-tab-${id}`}>{l}</button>
        ))}
      </div>
      {!d && !err && <p className="text-xs m-muted">Memuat…</p>}
      {d && tab === "ar" && (open.length === 0 ? <p className="text-xs m-muted p-2" data-testid="m-customer-ar-empty">Tidak ada tagihan terbuka.</p> :
        open.map((o) => { const sisa = Number(o.grand_total || o.total_amount || 0) - Number(o.paid || 0); const late = o.payment_status === "overdue" || (o.due_date && new Date(o.due_date) < new Date()); return (
          <div key={o.id || o.order_id} className={`m-card p-3 ${late ? "border-[#C0392B]/40" : ""}`} data-testid={`m-customer-ar-${o.id || o.order_id}`}>
            <div className="flex justify-between text-[12.5px]"><b>{o.number}</b><span className={late ? "text-[#C0392B] font-semibold" : "m-muted"}>{late ? "Jatuh tempo" : STATUS_ID[o.payment_status] || o.payment_status}</span></div>
            <div className="flex justify-between text-[11px] m-muted"><span>{fmtDate(o.created_at)}{o.due_date ? ` · tempo ${fmtDate(o.due_date)}` : ""}</span><span className="tabular-nums font-bold text-[#1B1B1F]">sisa {formatCurrency(sisa)}</span></div>
          </div>); }))}
      {d && tab === "orders" && (d.order_history || []).slice(0, 30).map((o) => (
        <div key={o.id || o.order_id} className="m-card p-3 text-[12px]" data-testid={`m-customer-order-${o.id || o.order_id}`}><div className="flex justify-between"><b>{o.number}</b><span className="tabular-nums">{formatCurrency(o.grand_total || o.total_amount)}</span></div><div className="flex justify-between text-[11px] m-muted"><span>{fmtDate(o.created_at)}</span><span>{o.status} · {STATUS_ID[o.payment_status] || o.payment_status || "-"}</span></div></div>
      ))}
      {d && tab === "receipts" && ((d.payments || []).length === 0 ? <p className="text-xs m-muted p-2">Belum ada kwitansi.</p> : (d.payments || []).slice(0, 30).map((p) => (
        <div key={p.id} className="m-card p-3 text-[12px] flex items-center gap-2" data-testid={`m-customer-receipt-${p.id}`}><Receipt size={14} className="text-[#1B7F4B]" /><div className="flex-1"><b>{p.number}</b><p className="text-[11px] m-muted">{fmtDate(p.created_at)} · {p.method || ""}</p></div><span className="tabular-nums font-bold">{formatCurrency(p.amount)}</span></div>
      )))}
      {d && tab === "samples" && ((d.sample_history || []).length === 0 ? <p className="text-xs m-muted p-2">Belum ada sampel.</p> : (d.sample_history || []).map((s) => (
        <div key={s.id || s.number} className="m-card p-3 text-[12px]" data-testid={`m-customer-sample-${s.id || s.number}`}><div className="flex justify-between"><b>{s.number}</b><span>{s.status}</span></div><p className="text-[11px] m-muted">{s.product_name} · {s.length} {s.unit}{s.child_roll_no ? ` · ${s.child_roll_no}` : ""}</p></div>
      )))}
      {pay && <MobileArReceipt customer={customer} onClose={() => setPay(false)} onDone={() => { setPay(false); load(); }} />}
    </div>
  );
}
