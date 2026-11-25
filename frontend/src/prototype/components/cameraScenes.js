import React from "react";

// Ilustrasi kamera 320×180, warna redup ala kamera malam. `u` = awalan id unik per instans.
const C = { wall: "#93aaa2", roof: "#718c84", dark: "#4b6760", lit: "#d6dfbf", fence: "#bccbc3", grass: "#58756b", far: "#5f7f75" };

function Sky({ u, moon = true }) {
  return (
    <>
      <defs>
        <linearGradient id={`${u}sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#36544f" />
          <stop offset="1" stopColor="#7e9b91" />
        </linearGradient>
        <radialGradient id={`${u}glow`}>
          <stop offset="0" stopColor="#eef3cf" stopOpacity="0.6" />
          <stop offset="1" stopColor="#eef3cf" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#${u}sky)`} />
      {moon && <circle cx="262" cy="36" r="34" fill={`url(#${u}glow)`} />}
      {moon && <circle cx="262" cy="36" r="13" fill="#d3dcbb" />}
      <g className="rdg-cam-drift" opacity="0.35" fill="#a9beb3">
        <ellipse cx="54" cy="30" rx="36" ry="6" />
        <ellipse cx="150" cy="18" rx="24" ry="4" />
      </g>
    </>
  );
}

const Fence = ({ x0, x1, y = 84, h = 36 }) => {
  const posts = [];
  for (let x = x0; x <= x1; x += 17) posts.push(<rect key={x} x={x} y={y} width="5" height={h} rx="1" />);
  return (
    <g fill={C.fence}>
      {posts}
      <rect x={x0 - 4} y={y + 5} width={x1 - x0 + 13} height="4" />
      <rect x={x0 - 4} y={y + h - 12} width={x1 - x0 + 13} height="4" />
    </g>
  );
};

function Teras({ u }) {
  return (
    <>
      <Sky u={u} />
      <rect y="116" width="320" height="64" fill={C.grass} />
      <rect y="112" width="320" height="7" fill="#6c897f" />
      <polygon points="22,66 96,24 170,66" fill={C.roof} />
      <rect x="32" y="64" width="128" height="50" fill={C.wall} />
      <rect x="80" y="76" width="26" height="38" rx="2" fill={C.dark} />
      <circle cx="101" cy="96" r="1.6" fill={C.lit} />
      <rect x="118" y="76" width="30" height="20" rx="2" fill={C.lit} opacity="0.85" />
      <path d="M133 76v20M118 86h30" stroke={C.wall} strokeWidth="2" />
      <ellipse cx="60" cy="112" rx="14" ry="9" fill="#55736a" />
      <Fence x0={190} x1={306} />
    </>
  );
}

function Jalan({ u }) {
  return (
    <>
      <Sky u={u} />
      <rect y="70" width="320" height="110" fill={C.grass} />
      <g fill={C.far}>
        <polygon points="96,70 106,60 116,70" /><rect x="98" y="64" width="16" height="8" />
        <polygon points="200,70 212,58 224,70" /><rect x="203" y="63" width="18" height="9" />
      </g>
      <polygon points="138,70 182,70 320,180 0,180" fill="#4c665f" />
      <g fill="#a9bdb4" opacity="0.8">
        <polygon points="159,76 161,76 162,86 158,86" />
        <polygon points="158,96 162,96 164,114 156,114" />
        <polygon points="156,128 164,128 167,156 153,156" />
      </g>
      <polygon points="0,96 52,74 52,112 0,140" fill={C.wall} />
      <polygon points="0,90 58,68 52,62 0,80" fill={C.roof} />
      <rect x="18" y="98" width="16" height="22" fill={C.lit} opacity="0.75" transform="skewY(-22)" />
      <rect x="252" y="58" width="4" height="86" fill="#3f5953" />
      <path d="M254 60 q-10 -6 -20 0" stroke="#3f5953" strokeWidth="3" fill="none" />
      <circle cx="234" cy="64" r="26" fill={`url(#${u}glow)`} />
      <rect x="228" y="60" width="12" height="5" rx="2" fill="#e5ecc6" />
    </>
  );
}

function Gerbang({ u }) {
  const bars = [];
  for (let x = 70; x < 226; x += 11) bars.push(<rect key={x} x={x} y="74" width="4" height="52" />);
  return (
    <>
      <Sky u={u} />
      <rect y="124" width="320" height="56" fill="#5a776d" />
      <polygon points="96,180 120,124 196,124 226,180" fill="#4c665f" />
      <rect x="42" y="58" width="24" height="70" fill={C.wall} /><rect x="38" y="52" width="32" height="8" fill={C.roof} />
      <rect x="228" y="58" width="24" height="70" fill={C.wall} /><rect x="224" y="52" width="32" height="8" fill={C.roof} />
      <g fill={C.fence}>{bars}<rect x="66" y="74" width="162" height="5" /><rect x="66" y="112" width="162" height="4" /></g>
      <rect x="264" y="86" width="48" height="40" fill={C.wall} />
      <polygon points="258,88 288,72 318,88" fill={C.roof} />
      <rect x="272" y="96" width="22" height="14" rx="2" fill={C.lit} opacity="0.9" />
      <circle cx="283" cy="94" r="24" fill={`url(#${u}glow)`} />
    </>
  );
}

function Taman({ u }) {
  const tree = (x, s) => (
    <g key={x}>
      <rect x={x - 3} y={92 - 10 * s} width="6" height={34 + 10 * s} fill="#4a645d" />
      <circle cx={x} cy={84 - 12 * s} r={20 + 6 * s} fill="#5c7d72" />
      <circle cx={x + 12} cy={92 - 10 * s} r={14 + 4 * s} fill="#668a7e" />
    </g>
  );
  return (
    <>
      <Sky u={u} moon={false} />
      <rect y="112" width="320" height="68" fill={C.grass} />
      <ellipse cx="170" cy="150" rx="120" ry="16" fill="#678679" opacity="0.6" />
      {[tree(40, 1), tree(118, 0), tree(276, 1)]}
      <g fill={C.fence}>
        <rect x="168" y="118" width="52" height="5" rx="2" /><rect x="168" y="110" width="52" height="4" rx="2" />
        <rect x="172" y="122" width="4" height="10" /><rect x="212" y="122" width="4" height="10" />
      </g>
      <polygon points="228,132 238,92 244,92 270,132 262,132 241,100 236,132" fill="#a7b9b0" />
      <rect x="236" y="88" width="10" height="5" fill={C.roof} />
    </>
  );
}

const SCENES = { teras: Teras, jalan: Jalan, gerbang: Gerbang, taman: Taman };
const KEYWORDS = [
  [/teras|pintu|depan|rumah/, "teras"],
  [/gerbang|pos|portal/, "gerbang"],
  [/jalan|carport|garasi|blok/, "jalan"],
  [/taman|lapangan|bermain|kebun|belakang/, "taman"],
];

function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

/** Pilih ilustrasi dari id/label kamera; hash menentukan cermin agar dua kamera sejenis tetap berbeda. */
export function pickScene(cameraId = "", label = "") {
  const key = `${cameraId} ${label}`.toLowerCase();
  const h = hash(String(cameraId));
  const found = KEYWORDS.find(([re]) => re.test(key));
  const name = found ? found[1] : Object.keys(SCENES)[h % 4];
  return { name, Scene: SCENES[name], mirror: h % 2 === 1 };
}
