import { formatDateWIB } from "../../utils/formatters";

export function rupiah(n) {
  const v = Math.round(Number(n) || 0);
  const s = String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${v < 0 ? "-" : ""}Rp${s}`;
}

/** "10 Des 2026" (WIB). */
export const tanggal = (t) => formatDateWIB(t == null ? t : new Date(t).toISOString());

/** "Rabu, 25 Nov 2026" (WIB). */
export function hariTanggal(t) {
  if (t == null) return "-";
  return new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date(t));
}

/** "09.41" (WIB). */
export function jam(t) {
  if (t == null) return "-";
  return new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }).format(new Date(t));
}

/** Persentase bulat yang selalu berjumlah 100 (metode sisa terbesar; seri → urutan awal). Total 0 → semua 0. */
export function persenBulat(values) {
  const total = values.reduce((a, b) => a + b, 0);
  if (!total) return values.map(() => 0);
  const raw = values.map((v) => (v / total) * 100);
  const out = raw.map(Math.floor);
  let left = 100 - out.reduce((a, b) => a + b, 0);
  raw.map((r, i) => [r - out[i], i]).sort((a, b) => b[0] - a[0] || a[1] - b[1]).forEach(([, i]) => {
    if (left > 0) { out[i] += 1; left -= 1; }
  });
  return out;
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
