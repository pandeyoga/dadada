import { useState } from "react";
import { Pencil, X } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { formatQty } from "../../utils/formatters";
import { overlayDismiss } from "../../utils/overlayDismiss";

/**
 * PrLineQtyModal (AS-02) — MD/pembelian mengubah qty beli satu baris PR. Qty boleh NAIK
 * di atas kebutuhan pesanan (SO); tidak boleh turun di bawah kebutuhan pesanan / yang
 * sudah terealisasi. PATCH /purchase-requisitions/{id}/lines/{line_no}.
 */
export default function PrLineQtyModal({ pr, line, onClose, onDone }) {
  const [qty, setQty] = useState(String(line.quantity ?? ""));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const orderQty = line.order_qty ?? (["so_repeat", "so"].includes(pr.source) || line.source_ref_id ? line.quantity : null);
  const n = Number(qty);
  const canSave = n > 0 && reason.trim().length >= 5 && !busy && Math.abs(n - Number(line.quantity)) > 0.0005;

  const save = async () => {
    setBusy(true); setErr("");
    try {
      await axios.patch(`${API}/purchase-requisitions/${pr.id}/lines/${line.line_no}`, { quantity: n, reason: reason.trim() });
      onDone?.();
    } catch (e) {
      setErr(e.response?.data?.detail || "Gagal mengubah qty.");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" data-testid="pr-line-qty-modal" {...overlayDismiss(onClose)}>
      <div className="modal-card small" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="modal-title flex items-center gap-2"><Pencil size={14} className="text-[#0058CC]" /> Ubah Qty Beli — baris {line.line_no}</p>
            <p className="modal-subtitle">{line.product_name || line.description} · {pr.number}</p>
          </div>
          <button className="icon-button" onClick={onClose} data-testid="pr-line-qty-close"><X size={16} /></button>
        </div>
        {err && <div className="notice-bar danger mt-2" data-testid="pr-line-qty-error"><span>{err}</span></div>}
        <div className="mt-2 grid gap-3">
          <div className="grid grid-cols-2 gap-2 text-[11.5px]">
            <div className="rounded-md bg-[#FAFBFC] p-2"><p className="text-[9.5px] font-bold uppercase text-[#8E8E93]">Qty sekarang</p><p className="font-bold tabular-nums">{formatQty(line.quantity)} {line.unit}</p></div>
            <div className="rounded-md bg-[#FAFBFC] p-2" data-testid="pr-line-qty-order">
              <p className="text-[9.5px] font-bold uppercase text-[#8E8E93]">Kebutuhan pesanan (SO)</p>
              <p className="font-bold tabular-nums">{orderQty != null ? `${formatQty(orderQty)} ${line.unit}` : "— (bukan dari SO)"}</p>
            </div>
          </div>
          <div className="grid gap-1.5">
            <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Qty beli baru ({line.unit}) *</label>
            <input type="number" min="0" step="0.01" className="form-input" value={qty} onChange={(e) => setQty(e.target.value)} data-testid="pr-line-qty-input" />
            {orderQty != null && n > orderQty && (
              <p className="text-[10.5px] text-[#126E2C]" data-testid="pr-line-qty-extra">Kelebihan untuk stok: +{formatQty(n - orderQty)} {line.unit} di atas kebutuhan pesanan.</p>
            )}
            {orderQty != null && n > 0 && n < orderQty && (
              <p className="text-[10.5px] text-[#C0392B]">Di bawah kebutuhan pesanan — akan ditolak server.</p>
            )}
          </div>
          <div className="grid gap-1.5">
            <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Alasan (wajib, min. 5 huruf) *</label>
            <textarea className="form-input" rows="2" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="pr-line-qty-reason"
              placeholder="Mis. MOQ supplier 200 m; tambah stok penyangga untuk repeat order." />
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} data-testid="pr-line-qty-cancel">Batal</button>
          <button className="btn-primary" onClick={save} disabled={!canSave} data-testid="pr-line-qty-confirm">{busy ? "Menyimpan…" : "Simpan Qty"}</button>
        </div>
      </div>
    </div>
  );
}
