/**
 * poUtils.jsx — shared helpers untuk PurchaseOrderManagement sub-komponen.
 */

export function getStatusBadge(status) {
  const statusMap = {
    waiting_approval: { label: "Menunggu Persetujuan", cls: "bg-amber-100 text-amber-700" },
    pending:          { label: "Menunggu Barang",      cls: "bg-yellow-100 text-yellow-700" },
    receiving:        { label: "Penerimaan",         cls: "bg-blue-100 text-blue-700" },
    completed:        { label: "Selesai",         cls: "bg-green-100 text-green-700" },
    partial:          { label: "Terima Sebagian",     cls: "bg-orange-100 text-orange-700" },
    cancelled:        { label: "Dibatalkan",         cls: "bg-gray-200 text-gray-500" },
    rejected:         { label: "Ditolak",          cls: "bg-red-100 text-red-700" },
    closed_short:     { label: "Ditutup-Kurang",      cls: "bg-stone-200 text-stone-600" },
  };
  const b = statusMap[status] || { label: status, cls: "bg-gray-200 text-gray-700" };
  return (
    <span data-testid={`po-status-badge-${status}`} className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-semibold ${b.cls}`}>
      {b.label}
    </span>
  );
}

/** Ringkasan penagihan PO (dari `sync_po_billing`) — dipakai daftar, panel ringkas, & detail. */
export function billingState(po) {
  if (!["receiving", "partial", "completed", "closed_short"].includes(po?.status)) return null;
  const grand = Number(po.grand_total ?? po.total_amount ?? 0);
  const billed = Number(po.billed_total ?? 0);
  const unbilled = Number(po.unbilled_total ?? Math.max(grand - billed, 0));
  if (billed <= 0.01) return { label: "Belum Ditagih", cls: "bg-red-50 text-red-600 border border-red-200" };
  if (unbilled <= 0.01) return { label: "Tertagih Penuh", cls: "bg-green-50 text-green-700 border border-green-200" };
  return { label: "Tertagih Sebagian", cls: "bg-amber-50 text-amber-700 border border-amber-200" };
}

/** Keterlambatan kirim PO — status masih menunggu barang & lewat tanggal janji supplier.
 *  Perbandingan pakai 10 huruf pertama (YYYY-MM-DD) karena data lama menyimpan ISO
 *  datetime penuh dan data baru date-only — konvensi yang sama dengan po_board_service. */
export function lateState(po) {
  if (!["pending", "receiving", "partial"].includes(po?.status)) return null;
  const eta = String(po.expected_delivery_date || "").slice(0, 10);
  if (!eta) return null;
  const today = new Date().toISOString().slice(0, 10);
  if (eta >= today) return null;
  const days = Math.max(1, Math.round((Date.parse(today) - Date.parse(eta)) / 86400000));
  return { eta, days, label: `Telat ${days} hari`, cls: "bg-red-50 text-red-600 border border-red-200" };
}

export function getPaymentBadge(status) {
  const map = {
    unpaid:  { label: "Belum Bayar", cls: "bg-red-50 text-red-600 border border-red-200" },
    partial: { label: "Sebagian",    cls: "bg-amber-50 text-amber-700 border border-amber-200" },
    paid:    { label: "Lunas",       cls: "bg-green-50 text-green-700 border border-green-200" },
  };
  const b = map[status] || { label: status || "—", cls: "bg-gray-100 text-gray-600" };
  return (
    <span data-testid={`po-payment-badge-${status}`} className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${b.cls}`}>
      {b.label}
    </span>
  );
}
