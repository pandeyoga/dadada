import React from "react";
import { TriangleAlert, CircleCheck } from "lucide-react";
import { jam } from "../../../lib/format";

export const FIELD = "mt-1 block min-h-[46px] w-full rounded-xl border border-[color:var(--rdg-line)] bg-white px-3 text-[15px] text-rdg-ink900";

/** Kolom formulir berlabel. */
export function Field({ id, label, children }) {
  return (
    <div>
      <label htmlFor={id} className="block text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">{label}</label>
      {children}
    </div>
  );
}

/** Pesan hasil: galat (role=alert) atau sukses (role=status). */
export function Msg({ error, ok }) {
  if (error) {
    return (
      <p role="alert" className="flex items-start gap-1.5 text-[13.5px] font-semibold text-[color:var(--rdg-sos-ink)]">
        <TriangleAlert size={16} aria-hidden="true" className="mt-0.5 flex-none" /> {error}
      </p>
    );
  }
  if (ok) {
    return (
      <p role="status" className="flex items-start gap-1.5 text-[13.5px] font-semibold text-rdg-forest">
        <CircleCheck size={16} aria-hidden="true" className="mt-0.5 flex-none" /> {ok}
      </p>
    );
  }
  return null;
}

/** Teks satu entri riwayat pintu, mis. "Dibuka · Rina (aplikasi)". */
export function doorLogText(e) {
  if (e.state === "unlocked") return `Dibuka · ${e.who} (${String(e.how).toLowerCase()})`;
  if (/^otomatis/i.test(e.how)) return "Otomatis terkunci";
  return `Dikunci · ${e.who} (${String(e.how).toLowerCase()})`;
}

/** Hari WIB 'YYYY-MM-DD' dari epoch/ISO. */
export const wibDay = (t) => new Date(new Date(t).getTime() + 7 * 3600000).toISOString().slice(0, 10);

export { jam };

/** Riwayat terbaru dulu (urut menurut waktu, bukan urutan simpan). */
export const byRecent = (list) => [...list].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
