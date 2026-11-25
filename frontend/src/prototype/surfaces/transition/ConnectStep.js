import React, { useEffect, useState } from "react";
import { DoorClosed, Cctv, Loader2, CheckCircle2 } from "lucide-react";

const ROWS = [
  { id: "lock", icon: DoorClosed, wait: "Menghubungkan kunci pintu…", done: "Kunci pintu terhubung", at: 400 },
  { id: "cam", icon: Cctv, wait: "Menghubungkan kamera…", done: "2 kamera rumah terhubung", at: 800 },
];

/** Animasi "terhubung" simulasi; `onDone` dipanggil setelah semua perangkat terhubung. */
export default function ConnectStep({ started, onDone }) {
  const [ready, setReady] = useState([]);
  useEffect(() => {
    if (!started) return undefined;
    const timers = ROWS.map((r, i) =>
      setTimeout(() => {
        setReady((p) => [...p, r.id]);
        if (i === ROWS.length - 1) onDone();
      }, r.at)
    );
    return () => timers.forEach(clearTimeout);
  }, [started, onDone]);
  return (
    <ul className="space-y-3" aria-live="polite">
      {ROWS.map((r) => {
        const ok = ready.includes(r.id);
        const Icon = r.icon;
        return (
          <li key={r.id} className="flex items-center gap-3 rounded-2xl bg-white/80 p-3.5">
            <span className="rdg-row-icon"><Icon size={20} aria-hidden="true" /></span>
            <span className="flex-1 text-[15px] font-semibold text-rdg-ink900">
              {!started ? r.done.replace(" terhubung", "") : ok ? r.done : r.wait}
            </span>
            {started && (ok
              ? <CheckCircle2 size={22} className="text-rdg-forest" aria-hidden="true" />
              : <Loader2 size={20} className="rdg-spin text-[color:var(--rdg-muted)]" aria-hidden="true" />)}
          </li>
        );
      })}
    </ul>
  );
}
