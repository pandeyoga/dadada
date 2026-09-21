/**
 * POCompactPanel — RINGKASAN PO di panel kanan (2026-06).
 * Dulu panel kanan memuat SEMUANYA (item, pajak, penagihan, timeline, referensi…)
 * sehingga harus di-scroll panjang. Sekarang: fakta kunci + tindakan sesuai
 * lifecycle saja; selebihnya lewat tombol "Lihat detail lengkap" (pop-up berisi
 * `PODetailPanel` yang sama — satu sumber tampilan, bukan duplikat).
 */
import { FileText, CheckCircle, XCircle, AlertCircle, Ban, FileEdit, Maximize2, PackageCheck } from "lucide-react";
import { formatCurrency } from "../../../utils/formatters";
import { can } from "../../../config/roles";
import { getStatusBadge, lateState } from "./poUtils";
import POReceiptVariancePanel from "./POReceiptVariancePanel";

export default function POCompactPanel({ po, currentUser, onClose, onOpenFull,
  onApprove, onCancel, onCloseShort, onAmend, onOpenDocument }) {
  if (!po) {
    return (
      <div className="section-card flex items-center justify-center min-h-[200px] border-dashed">
        <div className="text-center p-6">
          <FileText size={28} className="mx-auto mb-2 text-gray-300" />
          <p className="text-[12px] text-[#6B6B73]">Pilih PO untuk lihat detail</p>
        </div>
      </div>
    );
  }

  const canManage = ["admin", "manager"].includes(currentUser?.role);
  const canReceive = can(currentUser?.permissions, "wms", "view") && ["pending", "receiving", "partial"].includes(po.status);
  const goodsReceived = ["receiving", "partial", "completed", "closed_short"].includes(po.status);
  const amendable = ["waiting_approval", "pending", "receiving", "partial"].includes(po.status);
  const version = Number(po.version || 1);
  const grand = Number(po.grand_total ?? po.total_amount ?? 0);
  const billed = Number(po.billed_total ?? 0);
  const unbilled = Number(po.unbilled_total ?? Math.max(grand - billed, 0));
  const billState = billed <= 0.01 ? { label: "Belum Ditagih", cls: "bg-red-50 text-red-600 border border-red-200" }
    : unbilled <= 0.01 ? { label: "Tertagih Penuh", cls: "bg-green-50 text-green-700 border border-green-200" }
    : { label: "Tertagih Sebagian", cls: "bg-amber-50 text-amber-700 border border-amber-200" };

  // Progress terima agregat — satu bar, bukan daftar per item.
  const items = po.items || [];
  const ordered = items.reduce((s, it) => s + Number(it.quantity || 0), 0);
  const received = items.reduce((s, it) => s + Number(it.received_qty || 0), 0);
  const pct = ordered > 0 ? Math.min(100, Math.round((received / ordered) * 100)) : 0;

  return (
    <div className="section-card self-start" data-testid="po-compact-panel">
      <div className="section-head">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase text-[#0058CC]">{po.po_number}</p>
          <div className="mt-0.5 flex flex-wrap items-center gap-1">
            {getStatusBadge(po.status)}
            {version > 1 && (
              <span data-testid="po-version-badge" className="rounded bg-[#F3E8FF] px-1.5 py-0.5 text-[10px] font-semibold text-[#6B219A]">v{version}</span>
            )}
            {goodsReceived && (
              <span data-testid="po-billing-badge" className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${billState.cls}`}>{billState.label}</span>
            )}
          </div>
        </div>
        <button className="icon-button" onClick={onClose} data-testid="po-compact-close"><XCircle size={14} /></button>
      </div>

      <div className="section-body space-y-2.5">
        {/* Fakta kunci */}
        <div className="grid grid-cols-2 gap-2 text-[11.5px]">
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="text-[10px] text-[#6B6B73] uppercase font-semibold mb-0.5">Supplier</p>
            <p className="font-semibold truncate">{po.supplier_name}</p>
            <p className="text-[10.5px] text-[#6B6B73] truncate">{po.supplier_contact}</p>
          </div>
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="text-[10px] text-[#6B6B73] uppercase font-semibold mb-0.5">Gudang</p>
            <p className="font-semibold truncate">{po.warehouse_name}</p>
            <p className="text-[10.5px] text-[#6B6B73] truncate">{po.warehouse_city}</p>
          </div>
        </div>
        <div className="flex items-center justify-between rounded-md border border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-2 text-[11.5px]">
          <span className="text-[#6B6B73]">{items.length} item · Grand Total</span>
          <span data-testid="po-compact-grand" className="font-bold tabular-nums text-[#007AFF]">{formatCurrency(grand)}</span>
        </div>

        {/* Progress terima agregat (relevan setelah PO disetujui) */}
        {["pending", "receiving", "partial", "completed", "closed_short"].includes(po.status) && (
          <div data-testid="po-compact-progress">
            <div className="mb-1 flex items-center justify-between text-[10.5px] text-[#6B6B73]">
              <span>Progress terima</span>
              <span className="tabular-nums">{received}/{ordered} ({pct}%)</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#EFF0F2]">
              <div className="h-full rounded-full" style={{ width: `${pct}%`, background: pct >= 100 ? "#16A34A" : "#0058CC" }} />
            </div>
          </div>
        )}
        {(() => { const late = lateState(po); return late && (
          <div data-testid="po-compact-late" className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-[11px] text-red-700">
            <AlertCircle size={13} className="shrink-0" />
            <span>Lewat tanggal kirim yang dijanjikan supplier (<b>{late.eta}</b>) — <b>telat {late.days} hari</b>. Hubungi supplier atau tutup PO bila sisa tidak akan dikirim.</span>
          </div>
        ); })()}
        {goodsReceived && <POReceiptVariancePanel variances={po.receipt_variances} testId="po-compact-receipt-variances" compact />}
        {goodsReceived && unbilled > 0.01 && (
          <p className="text-[10.5px] text-amber-700">Belum ditagih: <b className="tabular-nums">{formatCurrency(unbilled)}</b> — kelola di menu Tagihan Supplier.</p>
        )}
        {po.status === "waiting_approval" && po.required_approval_role && (
          <div data-testid="po-approval-badge" className="flex items-center gap-2 rounded-md border border-[#FFE2B8] bg-[#FFF7EC] px-2.5 py-1.5 text-[11px] text-[#9A5B00]">
            <AlertCircle size={13} />
            <span>Butuh persetujuan peran <b className="uppercase">{po.required_approval_role}</b>
              {Array.isArray(po.approval_chain) && po.approval_chain.length > 1
                ? ` (tingkat ${po.approval_chain.filter((l) => l.status === "approved").length + 1} dari ${po.approval_chain.length})`
                : ""}.</span>
          </div>
        )}
        {po.status === "closed_short" && (
          <p className="rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-[11px] text-stone-600">
            PO ditutup-kurang. Alasan: {po.close_reason || "—"}
          </p>
        )}

        {/* Tindakan sesuai lifecycle — tetap di ringkasan supaya tak perlu buka pop-up */}
        <div className="flex flex-col gap-1.5">
          {canReceive && onOpenDocument && (
            <button data-testid="receive-goods-button" className="primary-button justify-center"
              title="Buka Operasi Gudang → Barang Masuk dengan tugas penerimaan PO ini terpilih"
              onClick={() => onOpenDocument({ view: "operations", nav_id: "wms-operations", tab: "inbound", focus_type: "purchase_order", focus_id: po.id })}>
              <PackageCheck size={13} /> Terima Barang di Gudang
            </button>
          )}
          {po.status === "waiting_approval" && canManage && (
            <button data-testid="approve-po-button" onClick={() => onApprove(po.id)} className="primary-button justify-center">
              <CheckCircle size={13} /> Setujui PO
            </button>
          )}
          {amendable && canManage && (
            <button data-testid="amend-po-button" onClick={() => onAmend?.(po)} className="secondary-button justify-center">
              <FileEdit size={13} /> Revisi / Amandemen PO
            </button>
          )}
          {["receiving", "partial", "pending"].includes(po.status) && canManage && (
            <button data-testid="close-po-button" onClick={() => onCloseShort(po.id)} className="secondary-button justify-center">
              <Ban size={13} /> Tutup PO (Kurang)
            </button>
          )}
          {["waiting_approval", "pending"].includes(po.status) && canManage && (
            <button data-testid="cancel-po-button" onClick={() => onCancel(po.id)} className="danger-button justify-center">
              Batalkan PO
            </button>
          )}
          <button data-testid="po-open-full-detail" onClick={onOpenFull}
            className="secondary-button justify-center">
            <Maximize2 size={13} /> Lihat detail lengkap
          </button>
        </div>
      </div>
    </div>
  );
}
