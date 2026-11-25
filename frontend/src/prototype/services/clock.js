// Jam demo. Dunia contoh disusun untuk Rabu, 25 Nov 2026 (WIB): jadwal acara, jatuh tempo uang muka dan IPL
// memakai tanggal tetap. Mode 'anchored' (bawaan) menaruh jam sungguhan hari ini pada tanggal itu, jadi waktu
// tetap berjalan (hitung mundur kunci, jam SOS) tetapi tanggal selalu tanggal dunia contoh. Mode 'real' memakai
// jam dan tanggal sungguhan.
export const DEMO_DATE = "2026-11-25";
export const CLOCK_MODES = ["anchored", "real"];

const DAY = 86400000;
const WIB = 7 * 3600000;
const DEMO_MIDNIGHT = Date.parse(`${DEMO_DATE}T00:00:00+07:00`);

/** Mode jam yang sah; nilai lain dianggap 'anchored'. */
export const clockMode = (v) => (v === "real" ? "real" : "anchored");

/** Selisih (ms) yang memindahkan jam sungguhan `real` ke tanggal demo dengan jam WIB yang sama. */
export function anchoredOffset(real) {
  const timeOfDay = (((real + WIB) % DAY) + DAY) % DAY;
  return DEMO_MIDNIGHT + timeOfDay - real;
}

/** Selisih jam untuk mode: 0 untuk 'real'. */
export const offsetFor = (mode, real) => (clockMode(mode) === "real" ? 0 : anchoredOffset(real));
