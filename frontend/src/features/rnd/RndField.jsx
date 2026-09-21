/** RndField — label & kotak petunjuk seragam untuk semua pop-up R&D (satu ukuran font, satu jarak). */
export function Field({ label, children, testId }) {
  return (
    <label className="block" data-testid={testId}>
      <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">{label}</span>
      {children}
    </label>
  );
}

const TONES = {
  info: "bg-[#F2F7FF] text-[#004099]",
  warn: "bg-[#FFF6E5] text-[#8C4A00]",
  ok: "bg-[#EAF7EF] text-[#1A7A3A]",
  danger: "bg-[#FDEDE7] text-[#C0392B]",
};

export function Hint({ tone = "info", children, testId }) {
  return <div className={`rounded-lg px-3 py-2 text-[11.5px] leading-relaxed ${TONES[tone] || TONES.info}`} data-testid={testId}>{children}</div>;
}

/** Kaki pop-up seragam: Batal + tombol aksi utama. */
export function Footer({ onClose, onConfirm, confirmLabel, busy, disabled, icon: Icon, testId, title }) {
  return (
    <div className="flex items-center justify-end gap-2">
      <button type="button" className="secondary-button" onClick={onClose} disabled={busy}>Batal</button>
      <button type="button" className="primary-button" onClick={onConfirm} disabled={busy || disabled} data-testid={testId} title={title || ""}>
        {Icon && <Icon size={13} />} {busy ? "Memproses…" : confirmLabel}
      </button>
    </div>
  );
}
