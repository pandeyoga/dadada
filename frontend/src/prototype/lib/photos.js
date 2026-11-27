import photos from "./photos.json";

/** Foto lokal dari manifes: `{ src, alt, illustrative }` atau null bila kunci tak dikenal. */
export function getPhoto(key) {
  const p = photos[key];
  return p ? { src: p.src, alt: p.alt, illustrative: Boolean(p.illustrative) } : null;
}

export const CCTV_KEYS = [
  "cctv/teras-depan", "cctv/taman-belakang", "cctv/gerbang-utama", "cctv/pos-satpam",
  "cctv/taman-bermain", "cctv/jalan-blok", "cctv/lapangan", "cctv/gerbang-belakang",
];

const RULES = [
  [/gerbang.*belakang|belakang.*gerbang/, "cctv/gerbang-belakang"],
  [/gerbang|portal/, "cctv/gerbang-utama"],
  [/teras|depan|pintu/, "cctv/teras-depan"],
  [/belakang|kebun/, "cctv/taman-belakang"],
  [/pos/, "cctv/pos-satpam"],
  [/bermain/, "cctv/taman-bermain"],
  [/jalan|blok|carport/, "cctv/jalan-blok"],
  [/lapangan/, "cctv/lapangan"],
];

function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

/** Kunci foto CCTV dari label kamera (kata kunci), lalu hash `cameraId` yang deterministik. */
export function cctvKeyFor(cameraId, label) {
  const l = String(label || "").toLowerCase();
  const hit = RULES.find(([re]) => re.test(l));
  if (hit) return hit[1];
  const seed = String(cameraId || "") || String(label || "");
  return CCTV_KEYS[hash(seed) % CCTV_KEYS.length];
}
