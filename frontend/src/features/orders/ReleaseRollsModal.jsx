import { useMemo, useState } from "react";
import { Unlock, X, AlertTriangle } from "lucide-react";
import { overlayDismiss } from "../../utils/overlayDismiss";
import axios, { API } from "../../services/apiClient";
import { formatQty } from "../../utils/formatters";

/**
 * ReleaseRollsModal (AS-03) — Admin Sales MELEPAS SEBAGIAN roll ter-reserve pada 1 baris
 * SO pendingan. Status SO tetap; kekurangan jadi backorder; alasan wajib (jejak audit).
 * Submit → POST /sales-orders/{id}/items/{product_id}/release-rolls (izin inventory.pegging).
 */
export default function ReleaseRollsModal({ order, item, onClose, onDone }) {
  const rolls = useMemo(() => (order.allocations || [])
    .filter((a) => a.product_id === item.product_id)
    .flatMap((a) => (a.rolls || []).map((r) => ({
      id: r.roll_id, roll_no: r.roll_no, lot: r.lot, length: Number(r.length || 0),
      warehouse_name: a.warehouse_name,
    }))), [order, item]);
  const [sel, setSel] = useState([]);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const relQty = sel.reduce((s, id) => s + (rolls.find((r) => r.id === id)?.length || 0), 0);
  const toggle = (id) => setSel((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const canSubmit = sel.length > 0 && reason.trim().length >= 5 && !saving;

  const submit = async () => {
    setSaving(true); setError("");
    try {
      await axios.post(`${API}/sales-orders/${order.id}/items/${item.product_id}/release-rolls`,
        { roll_ids: sel, reason: reason.trim() });
      onDone?.();
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal melepas reservasi.");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 180 }} data-testid="release-rolls-modal" {...overlayDismiss(onClose)}>
      <div className="modal-card" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="modal-title flex items-center gap-2"><Unlock size={15} className="text-[#B26A00]" /> Lepas Reservasi Sebagian</p>
            <p className="modal-subtitle">{item.product_name} · {order.number} — pilih roll yang dilepas; status pesanan tetap, kekurangan tercatat sebagai backorder.</p>
          </div>
          <button className="icon-button" onClick={onClose} data-testid="release-rolls-close"><X size={16} /></button>
        </div>
        {error && <div className="notice-bar danger mt-2" data-testid="release-rolls-error"><span>{error}</span></div>}
        <div className="mt-3 max-h-[40vh] overflow-y-auto rounded-md border border-[#EFF0F2]">
          {rolls.length === 0 && <p className="px-3 py-4 text-center text-[12px] text-[#9A9BA3]" data-testid="release-rolls-empty">Tidak ada roll ter-reserve pada baris ini.</p>}
          {rolls.map((r) => (
            <label key={r.id} className="flex cursor-pointer items-center gap-2 border-b border-[#F4F5F7] px-3 py-2 text-[11.5px] last:border-0 hover:bg-[#FAFBFC]">
              <input type="checkbox" checked={sel.includes(r.id)} onChange={() => toggle(r.id)} data-testid={`release-roll-${r.id}`} />
              <span className="flex-1 font-semibold">{r.roll_no || r.id}<span className="ml-1 font-normal text-[#6B6B73]">· lot {r.lot || "—"} · {r.warehouse_name}</span></span>
              <span className="tabular-nums">{formatQty(r.length)} {item.unit}</span>
            </label>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between text-[11.5px]">
          <span className="text-[#6B6B73]">Dilepas: <b data-testid="release-rolls-qty">{formatQty(relQty)} {item.unit}</b> dari {formatQty(item.reserved_qty)} ter-reserve</span>
          {sel.length > 0 && <span className="flex items-center gap-1 text-[#B26A00]"><AlertTriangle size={12} /> sisa jadi backorder {formatQty(Math.max(0, (item.backorder_qty || 0) + relQty))}</span>}
        </div>
        <div className="mt-3 grid gap-1.5">
          <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Alasan (wajib, min. 5 huruf)</label>
          <textarea className="form-input" rows="2" value={reason} onChange={(e) => setReason(e.target.value)}
            data-testid="release-rolls-reason" placeholder="Mis. pelanggan menunda; roll dibutuhkan pesanan lain yang lebih mendesak." />
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} data-testid="release-rolls-cancel">Batal</button>
          <button className="btn-primary" onClick={submit} disabled={!canSubmit} data-testid="release-rolls-confirm">
            {saving ? "Memproses…" : `Lepas ${sel.length} roll`}
          </button>
        </div>
      </div>
    </div>
  );
}
