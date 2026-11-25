import { formatDateWIB } from "../../utils/formatters";

export function rupiah(n) {
  const v = Math.round(Number(n) || 0);
  const s = String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${v < 0 ? "-" : ""}Rp${s}`;
}

/** "10 Des 2026" (WIB). */
export const tanggal = (t) => formatDateWIB(t == null ? t : new Date(t).toISOString());

/** "09.41" (WIB). */
export function jam(t) {
  if (t == null) return "-";
  return new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }).format(new Date(t));
}
