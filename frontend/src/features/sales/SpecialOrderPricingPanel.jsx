/** Fase 2 OD — harga final = harga kontrak supplier pemenang + margin (Sales dapat mengubah) → kunci → Confirmed. */
import { useEffect, useState } from "react";
import { Lock, Unlock, Loader2, Percent } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { askReason } from "@/services/confirmService";
import { fmtNum, fmtDate } from "./SpecialOrderShared";

export default function SpecialOrderPricingPanel({ order, currentUser, onUpdated }) {
  const saved = (order.chain || {}).pricing || {};
  const locked = !!saved.locked;
  const accd = order.customer_decision === "acc";
  const role = currentUser?.role;
  const canLock = ["sales", "sales_admin", "manager", "admin"].includes(role) && accd && !locked && order.status !== "cancelled";
  const [margin, setMargin] = useState(saved.margin_pct ?? 30);
  const [pv, setPv] = useState(saved);
  const [note, setNote] = useState("");
  const [warehouses, setWarehouses] = useState([]);
  const [warehouseId, setWarehouseId] = useState("");
  const [autoPo, setAutoPo] = useState(true);
  useEffect(() => {
    if (locked || !accd) return;
    axios.get(`${API}/warehouses`).then((r) => { const rows = Array.isArray(r.data) ? r.data : r.data?.items || []; setWarehouses(rows); if (!warehouseId && rows[0]) setWarehouseId(rows[0].id); }).catch(() => {});
  }, [locked, accd]); // eslint-disable-line
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { setPv(saved); if (saved.margin_pct != null) setMargin(saved.margin_pct); }, [saved.locked, saved.margin_pct, saved.cost_price]); // eslint-disable-line

  useEffect(() => {
    if (locked || !accd) return undefined;
    const t = setTimeout(async () => {
      try { const r = await axios.get(`${API}/special-orders/${order.id}/pricing`, { params: { margin_pct: margin } }); setPv(r.data); } catch { /* biarkan */ }
    }, 250);
    return () => clearTimeout(t);
  }, [margin, order.id, locked, accd]);

  const lock = async () => {
    setBusy(true); setErr("");
    try { const r = await axios.post(`${API}/special-orders/${order.id}/lock-price`, { margin_pct: Number(margin), note, warehouse_id: warehouseId, auto_po: autoPo }); onUpdated?.(r.data.special_order); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal mengunci harga."); } finally { setBusy(false); }
  };
  const unlock = async () => {
    const reason = await askReason({ title: `Buka kunci harga ${order.number}?`, danger: true, testId: "od-price-unlock-confirm" });
    if (!reason) return;
    setBusy(true); setErr("");
    try { const r = await axios.post(`${API}/special-orders/${order.id}/unlock-price`, { reason }); onUpdated?.(r.data); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal membuka kunci."); } finally { setBusy(false); }
  };

  const procure = async () => {
    setBusy(true); setErr("");
    try { const r = await axios.post(`${API}/special-orders/${order.id}/procure`, { warehouse_id: order.procurement_warehouse_id || "" }); onUpdated?.(r.data.special_order); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal membuat PR/PO."); } finally { setBusy(false); }
  };
  const po = ((order.chain || {}).po || [])[0];

  if (!accd && !locked) {
    return (
      <section className="section-card !p-3" data-testid="od-pricing">
        <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Harga final &amp; confirmed</p>
        <p className="rounded-lg border border-dashed border-[#D9D9DE] px-3 py-3 text-[11px] text-[#9A9BA3]" data-testid="od-pricing-waiting">
          Menunggu ACC pelanggan. Harga final dihitung dari kontrak supplier pemenang{pv.cost_price ? ` (Rp ${fmtNum(pv.cost_price)}/${pv.unit})` : ""} + margin.
        </p>
      </section>
    );
  }
  return (
    <section className="section-card !p-3" data-testid="od-pricing">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Harga final &amp; confirmed</p>
        {locked ? <span className="inline-flex items-center gap-1 rounded-full bg-[#E9F7EF] px-2 py-0.5 text-[10.5px] font-bold text-[#1B7F4B]" data-testid="od-price-locked"><Lock size={10} /> Dikunci {saved.locked_by} · {fmtDate(saved.locked_at)}</span>
          : <span className="rounded-full bg-[#FFF4E5] px-2 py-0.5 text-[10.5px] font-bold text-[#B45309]" data-testid="od-price-open">Belum dikunci</span>}
      </div>
      <div className="grid gap-2 text-[11.5px] sm:grid-cols-4">
        <Cell label="Harga kontrak supplier" testId="od-price-cost"><b>Rp {fmtNum(pv.cost_price)}</b>/{pv.unit}<span className="block text-[10px] text-[#6B6B73]">{pv.supplier_name || "—"}{pv.contract_number ? ` · ${pv.contract_number}` : ""}{pv.sample_number ? ` · ${pv.sample_number}` : ""}</span></Cell>
        <Cell label="Margin" testId="od-price-margin-cell">
          {locked ? <b>{fmtNum(pv.margin_pct, 1)}%</b> : (
            <span className="inline-flex items-center gap-1"><input type="number" min="0" max="500" step="0.5" className="input !w-20 !py-0.5 text-right" value={margin} onChange={(e) => setMargin(e.target.value)} disabled={!canLock} data-testid="od-price-margin" /><Percent size={12} /></span>
          )}
          <span className="block text-[10px] text-[#6B6B73]">bawaan {fmtNum(pv.default_margin_pct ?? 30, 1)}%{pv.target_price ? ` · target pelanggan Rp ${fmtNum(pv.target_price)}` : ""}</span>
        </Cell>
        <Cell label="Harga final / satuan" testId="od-price-final"><b className="text-[13px] text-[#0058CC]">Rp {fmtNum(pv.final_unit_price)}</b>/{pv.unit}</Cell>
        <Cell label={`Total (${fmtNum(pv.quantity)} ${pv.unit})`} testId="od-price-total"><b className="text-[13px]">Rp {fmtNum(pv.total)}</b></Cell>
      </div>
      {pv.product_sku && <p className="mt-1.5 text-[10.5px] text-[#6B6B73]">SKU eksklusif <b className="font-mono">{pv.product_sku}</b> → harga jual master produk ikut harga final saat dikunci.</p>}
      {err && <p className="mt-1 text-[11px] text-[#C0392B]" data-testid="od-price-error">{err}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {canLock && (<>
          <select className="input !w-56 !py-1 text-[11px]" value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} data-testid="od-price-warehouse" title="Gudang tujuan PO">
            {warehouses.length === 0 && <option value="">gudang utama (bawaan)</option>}
            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.code ? `${w.code} · ` : ""}{w.name}</option>)}
          </select>
          <label className="inline-flex items-center gap-1 text-[11px]" data-testid="od-price-autopo-label"><input type="checkbox" checked={autoPo} onChange={(e) => setAutoPo(e.target.checked)} data-testid="od-price-autopo" /> PR/PO otomatis ke supplier pemenang</label>
        </>)}
      </div>
      {locked && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]" data-testid="od-procurement">
          {po ? <span className="rounded-full bg-[#E9F7EF] px-2 py-0.5 font-bold text-[#1B7F4B]" data-testid="od-po-chip">PO <span className="font-mono">{po.po_number}</span> · {po.supplier_name} · {po.status}{po.expected_delivery_date ? ` · tiba ${po.expected_delivery_date}` : ""}</span>
            : <span className="text-[#B45309]" data-testid="od-po-missing">PO ke supplier belum terbentuk{order.procurement_error ? ` — ${order.procurement_error}` : ""}</span>}
          {!po && ["admin", "manager", "sales_admin", "purchasing"].includes(role) && (
            <button type="button" className="secondary-button !py-1 text-[11px]" disabled={busy} onClick={procure} data-testid="od-procure-button">{busy ? <Loader2 size={12} className="spin" /> : null} Buat PR/PO sekarang</button>
          )}
        </div>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {canLock && (<>
          <input className="input !w-64 !py-1 text-[11px]" placeholder="catatan (opsional)" value={note} onChange={(e) => setNote(e.target.value)} data-testid="od-price-note" />
          <button type="button" className="primary-button !py-1 text-[11px]" disabled={busy || !pv.cost_price} onClick={lock} data-testid="od-price-lock-button">{busy ? <Loader2 size={12} className="spin" /> : <Lock size={12} />} Kunci harga &amp; Confirm OD</button>
        </>)}
        {locked && role === "admin" && !order.linked_pr_id && !order.linked_sales_order_id && !order.linked_po_id && (
          <button type="button" className="secondary-button !py-1 text-[11px]" disabled={busy} onClick={unlock} data-testid="od-price-unlock-button"><Unlock size={12} /> Buka kunci (admin)</button>
        )}
        {saved.unlocked_at && !locked && <span className="text-[10.5px] text-[#B45309]">dibuka {saved.unlocked_by} · {saved.unlock_reason}</span>}
      </div>
    </section>
  );
}

function Cell({ label, children, testId }) {
  return <div className="rounded-lg border border-[#EFF0F2] bg-white p-2" data-testid={testId}><p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p><div className="mt-0.5">{children}</div></div>;
}
