/**
 * SOCompactPanel — RINGKASAN pesanan di panel kanan daftar SO (2026-06).
 * Pola yang sama dengan POCompactPanel: panel samping = fakta kunci tanpa scroll;
 * seluruh detail + tombol aksi lifecycle dibuka lewat "Lihat detail & aksi"
 * (pop-up berisi `OrderDetailPanel` yang sama — satu sumber tampilan & aksi).
 */
import { toast } from "@/hooks/use-toast";
import { copyDocLink, waShareLink } from "../../utils/docLink";
import { useState } from "react";
import { Link2, Maximize2, Share2, Wand2, XCircle } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import { StagePill, SubStatusChips } from "../../components/SoStatusBadges";
import PaymentBadge from "../../components/PaymentBadge";
import EntityBadge from "../../components/EntityBadge";
import FulfillmentWizard from "./FulfillmentWizard";

export default function SOCompactPanel({ order, onClose, onOpenFull }) {
  const [showWizard, setShowWizard] = useState(false);
  if (!order) return null;
  const its = order.items || [];
  const qty = its.reduce((s, it) => s + Number(it.qty ?? it.quantity ?? 0), 0);
  const units = [...new Set(its.map((it) => it.unit).filter(Boolean))];
  const advanceHeld = ["shipped", "partially_shipped", "done"].includes(order.status) ? 0
    : (order.payments || []).filter((p) => p.gl_bucket === "advance").reduce((s, p) => s + Number(p.amount || 0), 0);

  return (
    <div className="section-card self-start" data-testid="so-compact-panel">
      <div className="section-head">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-[#0058CC]">
            {order.number} <EntityBadge entityId={order.entity_id} />
          </p>
          <div className="mt-1 flex flex-col items-start gap-0.5">
            <StagePill order={order} testId="so-compact-stage" />
            <SubStatusChips order={order} testIdPrefix="so-compact-substatus" />
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" className="icon-button" title="Salin tautan dokumen (?doc=)" data-testid="so-compact-copy-link"
            onClick={async () => { const ok = await copyDocLink(order.number); toast({ title: ok ? `Tautan ${order.number} disalin` : "Gagal menyalin tautan", description: ok ? "Tempel di WhatsApp/chat — penerima langsung dibawa ke dokumen ini." : "", variant: ok ? undefined : "destructive" }); }}>
            <Link2 size={14} />
          </button>
          <a className="icon-button" title="Bagikan lewat WhatsApp" data-testid="so-compact-share-wa"
            href={waShareLink(order.number, "Pesanan")} target="_blank" rel="noreferrer"><Share2 size={14} /></a>
          <button className="icon-button" onClick={onClose} data-testid="so-compact-close"><XCircle size={14} /></button>
        </div>
      </div>

      <div className="section-body space-y-2.5">
        <div className="grid grid-cols-2 gap-2 text-[11.5px]">
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="mb-0.5 text-[10px] font-semibold uppercase text-[#6B6B73]">Pelanggan</p>
            <p className="truncate font-semibold">{order.customer_name}</p>
            <p className="truncate text-[10.5px] text-[#6B6B73]">{order.sales_name ? `Sales: ${order.sales_name}` : ""}</p>
          </div>
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="mb-0.5 text-[10px] font-semibold uppercase text-[#6B6B73]">Qty Pesan</p>
            <p className="font-semibold tabular-nums">{new Intl.NumberFormat("id-ID").format(qty)} {units.length === 1 ? units[0] : ""}</p>
            <p className="text-[10.5px] text-[#6B6B73]">{its.length} item{units.length > 1 ? " · unit campuran" : ""}</p>
          </div>
        </div>

        <div className="flex items-center justify-between rounded-md border border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-2 text-[11.5px]">
          <span className="text-[#6B6B73]">Grand Total</span>
          <span data-testid="so-compact-total" className="font-bold tabular-nums text-[#007AFF]">
            {formatCurrency(order.grand_total != null ? order.grand_total : order.total_amount)}
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-1 text-[11px]">
          <span className="inline-flex items-center gap-1">
            <PaymentBadge order={order} showRemaining testId="so-compact-payment" />
            {order.payment_terms ? <span className="text-[#6B6B73]">· {order.payment_terms}</span> : null}
          </span>
          <span className="text-[#6B6B73]">
            {order.created_at ? new Date(order.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }) : ""}
          </span>
        </div>
        {order.payment_status === "partial" && (
          <p data-testid="so-compact-paid-detail" className="text-[10.5px] text-[#6B6B73]">
            Sudah dibayar <span className="font-semibold text-[#1B7F4B]">{formatCurrency(order.paid_total)}</span>
            {" "}dari {formatCurrency(order.grand_total != null ? order.grand_total : order.total_amount)}
          </p>
        )}
        {advanceHeld > 0 && (
          <p data-testid="so-compact-advance-note" className="rounded-md border border-[#CFE0FF] bg-[#EFF4FF] px-2.5 py-1.5 text-[10.5px] text-[#0B3D91]">
            Uang muka <span className="font-semibold">{formatCurrency(advanceHeld)}</span> tercatat sebagai kewajiban — pendapatan diakui saat dikirim.
          </p>
        )}
        {order.has_backorder && (
          <p className="rounded-md border border-[#F6D3C4] bg-[#FFF1EA] px-2.5 py-1.5 text-[11px] font-semibold text-[#B23B14]">
            Ada backorder — sebagian qty menunggu stok.
          </p>
        )}

        <button type="button" data-testid="so-open-wizard" onClick={() => setShowWizard(true)}
          className="flex w-full items-center justify-center gap-1 rounded-lg border border-[#D9C2EC] bg-[#FBF7FE] px-3 py-2 text-[12px] font-semibold text-[#6B219A] hover:bg-[#F3E9FA]">
          <Wand2 size={13} /> Wizard Pemenuhan
        </button>
        <button type="button" data-testid="so-open-full-detail" onClick={onOpenFull}
          className="secondary-button w-full justify-center">
          <Maximize2 size={13} /> Lihat detail &amp; aksi
        </button>
      </div>
      {showWizard && <FulfillmentWizard orderId={order.id} onClose={() => setShowWizard(false)} />}
    </div>
  );
}
