import React, { useEffect, useRef, useState } from "react";
import { Copy, Check } from "lucide-react";

/** Salin teks ke papan klip bila peramban mengizinkan; tampil "Tersalin" sebentar. */
export default function CopyButton({ text, label = "Salin" }) {
  const [done, setDone] = useState(false);
  const t = useRef(null);
  useEffect(() => () => clearTimeout(t.current), []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      clearTimeout(t.current);
      t.current = setTimeout(() => setDone(false), 1800);
    } catch (e) {
      /* papan klip tidak tersedia: teks tetap bisa dipilih manual */
    }
  };
  return (
    <button type="button" className="rdg-copy" onClick={copy} aria-live="polite">
      {done ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
      {done ? "Tersalin" : label}
    </button>
  );
}
