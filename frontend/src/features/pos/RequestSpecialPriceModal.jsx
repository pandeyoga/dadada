import { X, BadgePercent } from "lucide-react";
import SpecialPriceRequestForm from "../pricing/SpecialPriceRequestForm";
import { overlayDismiss } from "../../utils/overlayDismiss";
import { useEscapeClose } from "../../utils/escapeLayers";

/** §3-B — pintu POS memakai komponen bersama (satu jalan untuk 4 pintu). */
export default function RequestSpecialPriceModal({ open, onClose, product, customer, entityId = "", defaultQty = 0, onSubmitted }) {
  useEscapeClose(open, onClose, false);
  if (!open || !product) return null;
  return (
    <div className="modal-overlay" style={{ zIndex: 200 }} data-testid="request-special-price-modal" {...overlayDismiss(onClose)}>
      <div className="modal-card" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div className="modal-title flex items-center gap-2"><BadgePercent size={16} /> Minta Harga Khusus</div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Tutup" data-testid="request-special-price-close"><X size={16} /></button>
        </div>
        <SpecialPriceRequestForm product={product} customer={customer} entityId={entityId} defaultQty={defaultQty}
          onSubmitted={(doc) => onSubmitted?.({ productId: product.id, applied: false, approvalId: doc.id,
            message: `Pengajuan harga khusus ${doc.number || ""} terkirim — menunggu persetujuan.` })} onCancel={onClose} />
      </div>
    </div>
  );
}
