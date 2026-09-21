/**
 * DetailPopup — cangkang pop-up "Lihat detail lengkap" (2026-06).
 * Panel samping daftar (PO, dsb.) kini hanya RINGKASAN tanpa scroll; seluruh isi
 * panjangnya pindah ke sini. Portal ke <body> + z-[120] (kartu produk/daftar bisa
 * punya stacking context sendiri — pelajaran dari bug modal filter POS).
 */
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { useEscapeClose } from "@/utils/escapeLayers";

export default function DetailPopup({
  open, onClose, title, subtitle = "", badges = null,
  testId = "detail-popup", maxWidth = "max-w-3xl", children,
}) {
  useEscapeClose(open, onClose);
  if (!open) return null;
  return createPortal(
    <div className="modal-overlay fixed inset-0 z-[120] flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center"
      style={{ zIndex: 120 }}
      data-testid={`${testId}-overlay`} {...overlayDismiss(onClose)}>
      <div role="dialog" aria-modal="true" aria-label={title} data-testid={testId}
        className={`my-auto w-full ${maxWidth} rounded-xl bg-white shadow-2xl`}
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 rounded-t-xl border-b border-[#EFF0F2] bg-white px-4 py-3">
          <div className="min-w-0">
            <h3 className="flex flex-wrap items-center gap-2 text-[13.5px] font-bold text-[#1C1C1E]"
              data-testid={`${testId}-title`}>
              <span className="truncate">{title}</span>{badges}
            </h3>
            {subtitle && <p className="mt-0.5 text-[11px] text-[#6B6B73]">{subtitle}</p>}
          </div>
          <button type="button" className="icon-button shrink-0" aria-label="Tutup"
            data-testid={`${testId}-close`} onClick={onClose}><X size={14} /></button>
        </div>
        <div className="max-h-[calc(100dvh-9rem)] overflow-y-auto p-3" data-testid={`${testId}-body`}>
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}
