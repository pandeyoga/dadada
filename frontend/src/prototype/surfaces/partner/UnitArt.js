import React from "react";

/* Ilustrasi unit rumah: SVG lokal berdasarkan kunci `img` fixture (mis. "unit/tipe-36"). */
const TONE = {
  "tipe-30": { sky: "#dff3ea", wall: "#f6efe0", roof: "#2f8f6b", wide: 56 },
  "tipe-36": { sky: "#e2f1f4", wall: "#fbf4e6", roof: "#007f83", wide: 68 },
  "tipe-45": { sky: "#e6f0e0", wall: "#f3ead9", roof: "#006747", wide: 84 },
};

export default function UnitArt({ img = "", label, className }) {
  const t = TONE[String(img).replace(/^unit\//, "")] || TONE["tipe-36"];
  const x = 80 - t.wide / 2;
  return (
    <svg viewBox="0 0 160 100" role="img" aria-label={label || "Ilustrasi unit"} className={className} preserveAspectRatio="xMidYMid slice">
      <rect width="160" height="100" fill={t.sky} />
      <ellipse cx="128" cy="22" rx="14" ry="8" fill="#fff" opacity="0.8" />
      <rect y="78" width="160" height="22" fill="#b5e26b" />
      <rect x={x} y="42" width={t.wide} height="38" fill={t.wall} />
      <path d={`M${x - 6} 44 L80 18 L${x + t.wide + 6} 44Z`} fill={t.roof} />
      <rect x="74" y="58" width="12" height="22" rx="2" fill="#7a4a30" />
      <rect x={x + 6} y="54" width="14" height="12" rx="2" fill="#a9d9de" />
      <rect x={x + t.wide - 20} y="54" width="14" height="12" rx="2" fill="#a9d9de" />
    </svg>
  );
}
