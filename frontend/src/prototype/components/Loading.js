import React from "react";
import { TriangleAlert } from "lucide-react";

/** Keadaan memuat; bila `error` terisi, tampilkan pesan galat sebagai gantinya. */
export default function Loading({ error }) {
  if (error) {
    return (
      <p className="flex items-center justify-center gap-2 py-10 text-center text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]" role="alert">
        <TriangleAlert size={16} aria-hidden="true" /> {error}
      </p>
    );
  }
  return <p className="py-10 text-center text-[14px] text-[color:var(--rdg-muted)]" role="status">Memuat…</p>;
}
