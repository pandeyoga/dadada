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

const hariWib = (t) => new Date(new Date(t).getTime() + 7 * 3600000).toISOString().slice(0, 10);

/** Waktu riwayat relatif hari ini (WIB): "09.41", "Kemarin · 21.42", atau "23 Nov · 21.42". */
export function kapan(t, nowT) {
  if (t == null) return "-";
  const day = hariWib(t);
  if (day === hariWib(nowT)) return jam(t);
  if (day === hariWib(new Date(nowT).getTime() - 86400000)) return `Kemarin · ${jam(t)}`;
  const tgl = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", timeZone: "Asia/Jakarta" }).format(new Date(t));
  return `${tgl.replace(/\.$/, "")} · ${jam(t)}`;
}
