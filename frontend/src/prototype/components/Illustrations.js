import React from "react";
import Photo from "./Photo";

/* Ilustrasi SVG lokal (tanpa gambar eksternal): tahap pembangunan rumah dan promo.
   Dipakai Progres, Beranda pembeli, Promo; boleh dipakai ulang layar lain. */

const SKY = ["#d8f1e6", "#bfe5e3"];
const GROUND = "#6f9a63";

function Frame({ id, label, children, className }) {
  return (
    <svg viewBox="0 0 320 180" role="img" aria-label={label} className={className} preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={SKY[0]} />
          <stop offset="1" stopColor={SKY[1]} />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#sky-${id})`} />
      <circle cx="268" cy="38" r="17" fill="#f6e7a3" />
      <path d="M0 128 Q80 112 160 124 T320 118 V180 H0Z" fill={GROUND} />
      <rect y="140" width="320" height="40" fill="#5b864f" />
      {children}
    </svg>
  );
}

const Brick = ({ x, y, w, h }) => (
  <g>
    <rect x={x} y={y} width={w} height={h} fill="#c97b5a" />
    {Array.from({ length: Math.floor(h / 10) }, (_, i) => (
      <line key={i} x1={x} x2={x + w} y1={y + 10 * (i + 1)} y2={y + 10 * (i + 1)} stroke="#a85f44" strokeWidth="1" />
    ))}
  </g>
);

const SCENES = {
  lahan: (
    <g>
      {[60, 120, 200, 260].map((x) => <rect key={x} x={x} y="126" width="3" height="24" fill="#7a5a3a" />)}
      <path d="M60 128 H260" stroke="#e9d27a" strokeWidth="2" strokeDasharray="5 4" />
      <rect x="130" y="150" width="60" height="6" rx="3" fill="#8b6b45" />
    </g>
  ),
  pondasi: (
    <g>
      <rect x="70" y="138" width="180" height="14" fill="#9aa5a3" />
      <rect x="70" y="138" width="180" height="4" fill="#b8c2c0" />
      {[80, 130, 180, 230].map((x) => <rect key={x} x={x} y="126" width="6" height="14" fill="#6b4a2a" />)}
    </g>
  ),
  dinding: (
    <g>
      <rect x="70" y="146" width="180" height="8" fill="#9aa5a3" />
      <Brick x={74} y={96} w={172} h={50} />
      <rect x="140" y="106" width="34" height="40" fill="#5b864f" opacity="0.0" />
    </g>
  ),
  atap: (
    <g>
      <Brick x={74} y={102} w={172} h={44} />
      <path d="M60 104 L160 52 L260 104Z" fill="#b8573f" />
      {[0, 1, 2, 3].map((i) => <path key={i} d={`M${80 + i * 8} ${100 - i * 6} H${240 - i * 8}`} stroke="#9c4632" strokeWidth="2" />)}
      <rect x="74" y="146" width="172" height="8" fill="#9aa5a3" />
    </g>
  ),
  plester: (
    <g>
      <rect x="74" y="102" width="172" height="44" fill="#efe6d2" />
      <path d="M60 104 L160 52 L260 104Z" fill="#b8573f" />
      <rect x="140" y="116" width="32" height="30" fill="#d8cdb4" />
      <rect x="94" y="114" width="30" height="22" fill="#d8cdb4" />
      <rect x="196" y="114" width="30" height="22" fill="#d8cdb4" />
      <rect x="74" y="146" width="172" height="8" fill="#c8c1b0" />
    </g>
  ),
  kusen: (
    <g>
      <rect x="74" y="102" width="172" height="44" fill="#f4efe0" />
      <path d="M60 104 L160 52 L260 104Z" fill="#b8573f" />
      <rect x="140" y="114" width="32" height="32" fill="#7a5233" />
      <circle cx="166" cy="131" r="2" fill="#f1d27a" />
      <rect x="92" y="114" width="32" height="22" fill="#a9d9de" stroke="#7a5233" strokeWidth="3" />
      <rect x="196" y="114" width="32" height="22" fill="#a9d9de" stroke="#7a5233" strokeWidth="3" />
      <path d="M210 40 l4 -10 l4 10z" fill="#f6e7a3" opacity="0.0" />
      <rect x="74" y="146" width="172" height="8" fill="#c8c1b0" />
      <path d="M232 100 V70" stroke="#7a5233" strokeWidth="3" />
    </g>
  ),
};

const ALIASES = { "progress/lahan": "lahan", "progress/pondasi": "pondasi", "progress/dinding": "dinding", "progress/atap": "atap", "progress/plester": "plester", "progress/kusen": "kusen" };

/** `img` = kunci dari fixture (mis. "progress/atap") atau nama adegan. */
export function StageIllustration({ img, label, className, photo = true }) {
  const key = ALIASES[img] || img;
  const scene = SCENES[key] || SCENES.lahan;
  const alt = label || `Foto progres ${key}`;
  if (!photo) return <Frame id={`st-${key}`} label={alt} className={className}>{scene}</Frame>;
  return (
    <Photo photoKey={img} alt={alt} className={className}
      fallback={<Frame id={`st-${key}`} label={alt} className={className}>{scene}</Frame>} />
  );
}

const PROMO_STYLES = {
  "pr-1": { bg: ["#0f7b56", "#006284"], icon: "M20 60 l14 14 l28 -30" },
  "pr-2": { bg: ["#209f59", "#007f83"], icon: "M14 70 V44 L40 28 L66 44 V70 M26 70 V52 H54 V70" },
  "pr-3": { bg: ["#006747", "#49ae42"], icon: "M24 62 a10 10 0 1 0 0 -1 M52 62 a10 10 0 1 0 0 -1 M10 74 q14 -14 28 0 q14 -14 28 0" },
};

/** Gambar promo: gradasi hijau + simbol sederhana, tanpa berkas gambar. */
export function PromoIllustration({ id, label, className }) {
  const st = PROMO_STYLES[id] || PROMO_STYLES["pr-1"];
  const svg = (
    <svg viewBox="0 0 160 90" role="img" aria-label={label || "Ilustrasi promo"} className={className} preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id={`pg-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={st.bg[0]} />
          <stop offset="1" stopColor={st.bg[1]} />
        </linearGradient>
      </defs>
      <rect width="160" height="90" fill={`url(#pg-${id})`} />
      <circle cx="140" cy="14" r="34" fill="#b5e26b" opacity="0.25" />
      <path d={st.icon} transform="translate(46 4)" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  return <Photo photoKey={`promo/${id}`} alt={label} className={className} fallback={svg} />;
}
