import { useEffect, useState } from "react";
import { Check, X, Tag, Package } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { formatCurrency } from "../../utils/formatters";
import { askConfirm, askReason } from "../../services/confirmService";

const errText = (e, fb) => { const d = e.response?.data?.detail; return (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || fb; };

/** Inbox persetujuan HP (manajer/finance): harga khusus & pesanan khusus — setujui/tolak langsung dari HP. */
export default function MobileApprovalInbox() {
  const [prices, setPrices] = useState(null);
  const [specials, setSpecials] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState("");
  const load = () => {
    axios.get(`${API}/price-approvals`, { params: { status: "pending" } }).then((r) => setPrices((Array.isArray(r.data) ? r.data : r.data.items || []).filter((p) => p.status === "pending"))).catch(() => setPrices([]));
    axios.get(`${API}/special-orders`).then((r) => setSpecials((Array.isArray(r.data) ? r.data : r.data.items || []).filter((s) => ["pending_approval", "submitted", "pending"].includes(s.status)))).catch(() => setSpecials([]));
  };
  useEffect(load, []);
  const act = async (key, fn, okText) => { setBusy(key); setMsg(null); try { await fn(); setMsg({ ok: true, text: okText }); load(); } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal.") }); } finally { setBusy(""); } };
  const approvePrice = (p) => act(p.id, async () => { if (!(await askConfirm({ title: `Setujui harga khusus ${formatCurrency(p.requested_price)}?`, message: `${p.customer_name} · ${p.product_name}` }))) throw Object.assign(new Error("batal"), { response: { data: { detail: "Dibatalkan." } } }); await axios.post(`${API}/price-approvals/${p.id}/approve`, { decision_notes: "Disetujui dari HP" }); }, "Harga khusus disetujui.");
  const rejectPrice = (p) => act(p.id, async () => { const reason = await askReason({ title: "Alasan penolakan harga khusus" }); if (!reason) throw Object.assign(new Error("batal"), { response: { data: { detail: "Dibatalkan." } } }); await axios.post(`${API}/price-approvals/${p.id}/reject`, { decision_notes: reason }); }, "Harga khusus ditolak.");
  const approveSpecial = (s) => act(s.id, async () => { if (!(await askConfirm({ title: `Setujui pesanan khusus ${s.number || ""}?`, message: `${s.customer_name} · ${s.custom_item?.description || ""}` }))) throw Object.assign(new Error("batal"), { response: { data: { detail: "Dibatalkan." } } }); await axios.post(`${API}/special-orders/${s.id}/approve`, { notes: "Disetujui dari HP" }); }, "Pesanan khusus disetujui.");
  const rejectSpecial = (s) => act(s.id, async () => { const reason = await askReason({ title: "Alasan penolakan pesanan khusus" }); if (!reason) throw Object.assign(new Error("batal"), { response: { data: { detail: "Dibatalkan." } } }); await axios.post(`${API}/special-orders/${s.id}/reject`, { reason }); }, "Pesanan khusus ditolak.");
  const loading = prices === null || specials === null;
  return (
    <div className="space-y-2 p-3" data-testid="mo-inbox">
      {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"} text-xs`} data-testid="mo-inbox-msg">{msg.text}</div>}
      {loading && <p className="text-xs text-[#6E6E73]" data-testid="mo-inbox-loading">Memuat antrean…</p>}
      {!loading && !prices.length && !specials.length && <p className="p-6 text-center text-sm text-[#6E6E73]" data-testid="mo-inbox-empty">Tidak ada harga khusus / pesanan khusus yang menunggu.</p>}
      {(prices || []).map((p) => (
        <div key={p.id} className="m-card p-3" data-testid={`mo-price-${p.id}`}>
          <div className="flex items-center gap-2 text-[13px]"><Tag size={14} className="text-[#B25E00]" /><b className="flex-1 truncate">{p.customer_name}</b><span className="text-[10px] text-[#6E6E73]">{p.sales_name || p.requested_by_name || ""}</span></div>
          <p className="text-[12px] mt-1">{p.product_name} · min {p.min_quantity} {p.unit || ""}</p>
          <p className="text-[12px] tabular-nums"><s className="text-[#6E6E73]">{formatCurrency(p.normal_price)}</s> → <b>{formatCurrency(p.requested_price)}</b> <span className="text-[#B25E00]">({Math.round(((p.normal_price - p.requested_price) / (p.normal_price || 1)) * 100)}%)</span>{p.scope === "standing" ? " · berlaku terus" : " · pesanan ini"}</p>
          {p.reason && <p className="text-[11px] text-[#6E6E73] mt-0.5">{p.reason}</p>}
          <div className="mt-2 flex gap-2">
            <button className="primary-button flex-1 py-2 flex items-center justify-center gap-1" disabled={busy === p.id} onClick={() => approvePrice(p)} data-testid={`mo-price-approve-${p.id}`}><Check size={14} /> Setujui</button>
            <button className="secondary-button flex-1 py-2 flex items-center justify-center gap-1" disabled={busy === p.id} onClick={() => rejectPrice(p)} data-testid={`mo-price-reject-${p.id}`}><X size={14} /> Tolak</button>
          </div>
        </div>
      ))}
      {(specials || []).map((s) => (
        <div key={s.id} className="m-card p-3" data-testid={`mo-special-${s.id}`}>
          <div className="flex items-center gap-2 text-[13px]"><Package size={14} className="text-[#0058CC]" /><b className="flex-1 truncate">{s.number || s.id} · {s.customer_name}</b></div>
          <p className="text-[12px] mt-1">{s.custom_item?.description || "-"} · {s.custom_item?.quantity} {s.custom_item?.unit}{s.custom_item?.target_price ? ` · target ${formatCurrency(s.custom_item.target_price)}` : ""}</p>
          <div className="mt-2 flex gap-2">
            <button className="primary-button flex-1 py-2 flex items-center justify-center gap-1" disabled={busy === s.id} onClick={() => approveSpecial(s)} data-testid={`mo-special-approve-${s.id}`}><Check size={14} /> Setujui</button>
            <button className="secondary-button flex-1 py-2 flex items-center justify-center gap-1" disabled={busy === s.id} onClick={() => rejectSpecial(s)} data-testid={`mo-special-reject-${s.id}`}><X size={14} /> Tolak</button>
          </div>
        </div>
      ))}
    </div>
  );
}
