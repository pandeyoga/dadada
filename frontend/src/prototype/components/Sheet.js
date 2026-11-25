import React, { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Bottom sheet modal TANPA portal: dirender di tempat (di dalam `.rdg`) agar
 * gaya ber-scope tetap berlaku. Tutup dengan Esc, klik latar, atau tombol ×.
 */
export default function Sheet({ open, onClose, title, children }) {
  const panel = useRef(null);
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
    <div className="rdg-sheet-root">
      <div className="rdg-sheet-backdrop" data-sheet-backdrop="" aria-hidden="true" onClick={() => onClose?.()} />
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
