/** Fase 4 OD — pengiriman otomatis: SO OD → tugas Surat Jalan lahir saat barang PO diterima → SJ → OD Dikirim/Selesai. */
import { useState } from "react";
import { Loader2, Truck } from "lucide-react";
import axios, { API } from "../../services/apiClient";

const TASK_LABEL = { created: "Menunggu picking", scheduled: "Terjadwal", picking: "Picking", packing: "Packing", staging: "Staging", partially_shipped: "Terkirim sebagian", dispatched: "Surat Jalan terbit", escalated: "Eskalasi", cancelled: "Batal" };

export default function SpecialOrderShippingPanel({ order, currentUser, onUpdated }) {
  const ch = order.chain || {};
  const tasks = ch.outbound_tasks || [];
  const ships = ch.shipments || [];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const show = ["in_production", "ready", "shipped", "done"].includes(order.status) && !!order.linked_po_id;
  if (!show) return null;
  const canPrepare = ["admin", "manager", "sales_admin", "warehouse_admin"].includes(currentUser?.role) && order.status === "ready" && tasks.length === 0;
  const prepare = async () => {
    setBusy(true); setErr("");
    try { const r = await axios.post(`${API}/special-orders/${order.id}/prepare-shipment`); onUpdated?.(r.data.special_order); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyiapkan pengiriman."); } finally { setBusy(false); }
  };
  return (
    <section className="section-card !p-3" data-testid="od-shipping">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]"><Truck size={12} /> Pengiriman ke pelanggan</p>
        {canPrepare && <button type="button" className="primary-button !py-1 text-[11px]" disabled={busy} onClick={prepare} data-testid="od-prepare-shipment-button">{busy ? <Loader2 size={12} className="spin" /> : <Truck size={12} />} Siapkan pengiriman</button>}
      </div>
      <p className="text-[11px] text-[#6B6B73]">
        Alur otomatis: PO diterima gudang → stok direservasi ke SO {ch.so?.order_number || ch.so?.number || "(belum ada)"} → tugas Surat Jalan lahir → gudang pick &amp; dispatch → OD <b>Dikirim</b> → bukti terima → <b>Selesai</b>.
      </p>
      {order.shipping_error && <p className="mt-1 text-[11px] text-[#C0392B]" data-testid="od-shipping-error">{order.shipping_error}</p>}
      {err && <p className="mt-1 text-[11px] text-[#C0392B]">{err}</p>}
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-[#EFF0F2] p-2 text-[11px]" data-testid="od-outbound-tasks">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Tugas Surat Jalan · {tasks.length}</p>
          {tasks.length === 0 ? <p className="text-[#9A9BA3]">{order.status === "ready" ? "belum lahir — tekan Siapkan pengiriman" : "lahir otomatis saat barang PO diterima gudang"}</p>
            : tasks.map((t) => <p key={t.id} data-testid={`od-task-${t.id}`}>{t.warehouse_name || "Gudang"} · {t.quantity} ({t.shipped_qty || 0} terkirim) · <b>{TASK_LABEL[t.status] || t.status}</b></p>)}
        </div>
        <div className="rounded-lg border border-[#EFF0F2] p-2 text-[11px]" data-testid="od-shipments">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Surat Jalan terbit · {ships.length}</p>
          {ships.length === 0 ? <p className="text-[#9A9BA3]">belum ada</p>
            : ships.map((s) => <p key={s.id} data-testid={`od-shipment-${s.id}`}><b className="font-mono">{s.shipment_no}</b> · {s.status}{s.logistics_status ? ` · logistik ${s.logistics_status}` : ""}</p>)}
        </div>
      </div>
    </section>
  );
}
