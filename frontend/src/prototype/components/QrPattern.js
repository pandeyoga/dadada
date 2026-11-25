import React, { useMemo } from "react";

const N = 29; // modul per sisi
const LOGO = `${process.env.PUBLIC_URL || ""}/rdg/mark.png`;

function seedOf(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}
function mulberry(a) {
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const inFinder = (x, y) => (x < 8 && y < 8) || (x > N - 9 && y < 8) || (x < 8 && y > N - 9);
const inLogo = (x, y) => Math.abs(x - (N - 1) / 2) <= 3 && Math.abs(y - (N - 1) / 2) <= 3;

function Finder({ x, y }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="7" height="7" rx="1.6" fill="#00353b" />
      <rect x="1" y="1" width="5" height="5" rx="1" fill="#fff" />
      <rect x="2" y="2" width="3" height="3" rx="0.8" fill="#00353b" />
    </g>
  );
}

/** Pola mirip QR yang deterministik dari `value` — ilustrasi lokal, bukan QR yang bisa dipindai. */
export default function QrPattern({ value, label, size = 200 }) {
  const d = useMemo(() => {
    const rnd = mulberry(seedOf(String(value)));
    let p = "";
    for (let y = 0; y < N; y += 1) {
      for (let x = 0; x < N; x += 1) {
        if (inFinder(x, y) || inLogo(x, y)) continue;
        const timing = (x === 6 || y === 6) && (x + y) % 2 === 0;
        if (timing || rnd() < 0.48) p += `M${x} ${y}h1v1h-1z`;
      }
    }
    return p;
  }, [value]);
  const c = (N - 7) / 2;
  return (
    <svg role="img" aria-label={label} width={size} height={size} viewBox={`-2 -2 ${N + 4} ${N + 4}`} shapeRendering="crispEdges">
      <rect x="-2" y="-2" width={N + 4} height={N + 4} rx="2" fill="#fff" />
      <path d={d} fill="#00353b" />
      <Finder x={0} y={0} />
      <Finder x={N - 7} y={0} />
      <Finder x={0} y={N - 7} />
      <rect x={c} y={c} width="7" height="7" rx="1.6" fill="#fff" />
      <image href={LOGO} x={c + 1} y={c + 1} width="5" height="5" />
    </svg>
  );
}
