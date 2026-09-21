/**
 * ContractStatusPill — pil status kontrak blanket PO. File terpisah supaya
 * BlanketPOView ⇄ BlanketPODetailPanel tidak saling impor (impor melingkar
 * = TDZ "Cannot access X before initialization" di bundle produksi).
 */
export function ContractStatusPill({ status }) {
  const map = {
    active: ["pill-success", "Aktif"],
    exhausted: ["pill-info", "Habis"],
    expired: ["pill-warning", "Kadaluarsa"],
    closed: ["pill-muted", "Ditutup"],
  };
  const [cls, label] = map[status] || ["pill-muted", status || "—"];
  return <span className={`status-pill ${cls}`} data-testid={`blanket-status-${status}`}>{label}</span>;
}
