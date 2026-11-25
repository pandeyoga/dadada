import React from "react";

/* Pratinjau dokumen rumah: SVG lokal berdasarkan jenis, tanpa berkas eksternal. Isi hanya contoh. */
const LINES = [58, 70, 82, 94];

const BODY = {
  bast: <><circle cx="130" cy="118" r="14" fill="none" stroke="#209f59" strokeWidth="3" /><path d="M123 118 l5 5 l9 -10" stroke="#209f59" strokeWidth="3" fill="none" /></>,
  sertifikat: <><circle cx="80" cy="118" r="14" fill="#f2c230" /><path d="M72 132 l-4 14 l12 -6 l12 6 l-4 -14" fill="#e5484d" /></>,
  pbg: <><rect x="60" y="106" width="40" height="28" fill="#c8c1b0" /><path d="M54 108 L80 88 L106 108Z" fill="#b8573f" /></>,
  garansi: <path d="M80 102 l22 8 v14 q0 14 -22 22 q-22 -8 -22 -22 v-14Z" fill="#209f59" />,
  denah: <><rect x="52" y="96" width="76" height="52" fill="none" stroke="#006284" strokeWidth="3" /><path d="M90 96 V126 H52 M90 126 V148" stroke="#006284" strokeWidth="3" fill="none" /></>,
  instalasi: <><path d="M52 104 H100 V126 H132" stroke="#e5484d" strokeWidth="3" fill="none" /><path d="M52 124 H72 V146 H132" stroke="#0a7fb0" strokeWidth="3" fill="none" /></>,
  kuitansi: <><rect x="60" y="102" width="60" height="6" rx="3" fill="#9aa5a3" /><rect x="60" y="116" width="40" height="6" rx="3" fill="#9aa5a3" /><text x="60" y="146" fontSize="16" fontWeight="800" fill="#006747">LUNAS</text></>,
};

export default function DocIllustration({ kind, title, className }) {
  return (
    <svg viewBox="0 0 160 200" role="img" aria-label={`Pratinjau ${title} (contoh)`} className={className}>
      <rect x="6" y="6" width="148" height="188" rx="8" fill="#fff" stroke="#b9cfcf" strokeWidth="2" />
      <rect x="22" y="22" width="70" height="10" rx="3" fill="#006747" />
      <circle cx="132" cy="28" r="10" fill="#b5e26b" />
      {LINES.map((y) => <rect key={y} x="22" y={y - 14} width={y % 24 === 10 ? 96 : 116} height="5" rx="2.5" fill="#d6e4e3" />)}
      <g transform="translate(18 0)">{BODY[kind] || BODY.bast}</g>
      <text x="22" y="184" fontSize="9" fill="#3f6166">Contoh tampilan, bukan dokumen asli</text>
    </svg>
  );
}
