import React, { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Bottom sheet modal TANPA portal: dirender di tempat (di dalam `.rdg`) agar
 * gaya ber-scope tetap berlaku. Tutup dengan Esc, klik latar, atau tombol ×.
 * Klik latar hanya menutup bila pointerdown-nya juga di latar: di layar sentuh,
 * sheet yang terbuka saat jari masih menahan tombol (SOS) menerima klik susulan
 * ketika jari diangkat, dan klik itu tidak boleh menutupnya.
 */
export default function Sheet({ open, onClose, title, children }) {
  const panel = useRef(null);
  const downOnBackdrop = useRef(false);
  const closeRef = useRef(onClose);
  const titleId = useId();
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.activeElement;
    panel.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") closeRef.current?.();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prev && typeof prev.focus === "function" && document.contains(prev)) prev.focus();
    };
  }, [open]);

  if (!open) return null;

  const onBackdropClick = () => {
    const started = downOnBackdrop.current;
    downOnBackdrop.current = false;
    if (started) onClose?.();
  };

  // Jaga fokus Tab tetap di dalam sheet.
  const trap = (e) => {
    if (e.key !== "Tab") return;
    const els = [...panel.current.querySelectorAll(FOCUSABLE)];
    if (!els.length) return;
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="rdg-sheet-root" onPointerDownCapture={(e) => { downOnBackdrop.current = e.target.hasAttribute("data-sheet-backdrop"); }}>
      <div className="rdg-sheet-backdrop" data-sheet-backdrop="" aria-hidden="true" onClick={onBackdropClick} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="rdg-sheet"
        onKeyDown={trap}
      >
        <div className="rdg-sheet-grabber" aria-hidden="true" />
        <div className="rdg-sheet-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="rdg-sheet-close" aria-label="Tutup" onClick={() => onClose?.()}>
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        <div className="rdg-sheet-body">{children}</div>
      </div>
    </div>
  );
}
