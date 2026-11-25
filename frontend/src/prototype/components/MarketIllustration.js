import React from "react";

/* Ilustrasi produk pasar warga: SVG lokal berdasarkan kunci `img` fixture (mis. "market/brownies"). */
const ART = {
  "nasi-kuning": { bg: "#fff1c2", art: <><ellipse cx="80" cy="62" rx="40" ry="26" fill="#f2c230" /><ellipse cx="80" cy="52" rx="26" ry="18" fill="#f7d65a" /><circle cx="62" cy="64" r="4" fill="#49ae42" /><circle cx="98" cy="64" r="4" fill="#e5484d" /><path d="M44 76 H116" stroke="#c9a227" strokeWidth="4" strokeLinecap="round" /></> },
  brownies: { bg: "#f1e1d6", art: <><rect x="40" y="46" width="80" height="40" rx="6" fill="#5a3320" /><rect x="40" y="46" width="80" height="12" rx="6" fill="#7a4a30" /><path d="M54 70 H106" stroke="#f1e1d6" strokeWidth="3" strokeDasharray="6 5" /></> },
  keripik: { bg: "#ffe3c9", art: <>{[[52, 56], [78, 44], [104, 60], [66, 76], [94, 80]].map(([x, y]) => <ellipse key={x} cx={x} cy={y} rx="16" ry="10" fill="#e8a24a" stroke="#c9772a" strokeWidth="2" />)}</> },
  kopi: { bg: "#e5f1ee", art: <><rect x="62" y="30" width="36" height="62" rx="8" fill="#a9d9de" /><rect x="62" y="52" width="36" height="40" rx="8" fill="#7a4a30" /><rect x="72" y="22" width="16" height="10" rx="3" fill="#007f83" /></> },
  "kopi-aren": { bg: "#f5ead8", art: <><path d="M88 8 L82 46" stroke="#209f59" strokeWidth="5" strokeLinecap="round" /><path d="M58 36 H102 L96 96 H64Z" fill="#f3faf9" stroke="#9cc5c1" strokeWidth="2" /><path d="M59.4 50 H100.6 L97.4 82 H62.6Z" fill="#c8996b" /><path d="M62.6 82 H97.4 L96 96 H64Z" fill="#6b3b22" /><rect x="66" y="55" width="12" height="10" rx="2" fill="#fff" opacity="0.55" /><rect x="82" y="61" width="11" height="9" rx="2" fill="#fff" opacity="0.45" /><path d="M60 35 q20 -18 40 0" fill="#e3f1ef" stroke="#9cc5c1" strokeWidth="2" /><path d="M54 36 H106" stroke="#9cc5c1" strokeWidth="4" strokeLinecap="round" /></> },
  cabai: { bg: "#e4f4d8", art: <><path d="M50 92 H110 L104 70 H56Z" fill="#b8573f" /><path d="M80 70 V40" stroke="#209f59" strokeWidth="4" /><path d="M80 52 q-22 -10 -26 8 q20 4 26 -8Z M80 46 q22 -12 26 6 q-20 6 -26 -6Z" fill="#49ae42" /><ellipse cx="80" cy="36" rx="5" ry="9" fill="#e5484d" /></> },
  pot: { bg: "#f6e4d4", art: <><path d="M48 50 H112 L102 94 H58Z" fill="#c97b5a" /><rect x="44" y="44" width="72" height="10" rx="4" fill="#a85f44" /><path d="M80 44 q-18 -22 -4 -30 q10 12 4 30Z M80 44 q18 -22 4 -30 q-10 12 -4 30Z" fill="#49ae42" /></> },
  sprei: { bg: "#e3ecf9", art: <><rect x="34" y="40" width="92" height="52" rx="6" fill="#3b6ea5" /><path d="M34 56 H126 M34 72 H126" stroke="#a9c7e8" strokeWidth="3" /><circle cx="60" cy="48" r="4" fill="#f6e7a3" /><circle cx="100" cy="64" r="4" fill="#f6e7a3" /></> },
  telur: { bg: "#f3ead9", art: <>{[48, 72, 96].map((x, i) => <ellipse key={x} cx={x + 8} cy={i === 1 ? 60 : 68} rx="14" ry="19" fill="#f4e3c3" stroke="#d7b98a" strokeWidth="2" />)}</> },
  beras: { bg: "#f3ead9", art: <><path d="M48 40 H112 L118 92 H42Z" fill="#e9dcc0" stroke="#c9b88a" strokeWidth="2" /><rect x="58" y="54" width="44" height="22" rx="4" fill="#209f59" /><path d="M66 65 H94" stroke="#fff" strokeWidth="4" strokeLinecap="round" /></> },
  laundry: { bg: "#e3f2f7", art: <><rect x="44" y="26" width="72" height="68" rx="8" fill="#fff" stroke="#7fb3b0" strokeWidth="3" /><circle cx="80" cy="62" r="22" fill="#a9d9de" stroke="#007f83" strokeWidth="4" /><path d="M66 62 q7 -8 14 0 t14 0" stroke="#fff" strokeWidth="3" fill="none" /><circle cx="58" cy="36" r="3" fill="#007f83" /></> },
  rajut: { bg: "#fde4ee", art: <><circle cx="80" cy="64" r="24" fill="#e6639b" /><path d="M62 54 q18 14 36 0 M60 66 q20 14 40 0 M66 78 q14 8 28 0" stroke="#fbb7d1" strokeWidth="3" fill="none" /><circle cx="80" cy="30" r="6" fill="none" stroke="#7a7a7a" strokeWidth="3" /></> },
};

export default function MarketIllustration({ img = "", label, className }) {
  const key = String(img).replace(/^market\//, "");
  const a = ART[key] || ART.brownies;
  return (
    <svg viewBox="0 0 160 110" role="img" aria-label={label || "Foto produk"} className={className} preserveAspectRatio="xMidYMid slice">
      <rect width="160" height="110" fill={a.bg} />
      {a.art}
    </svg>
  );
}
