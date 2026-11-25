/** Keamanan rumah: kunci pintu, kode akses, tamu QR, gerbang. SOS dan kontak ada di sos.js. */
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";

export const AUTO_LOCK_MS = 30000;
const RESIDENT = "Rina Ayu";
const iso = (t) => new Date(t).toISOString();
const clean = (v) => String(v == null ? "" : v).trim();

/** Status pintu: terbuka hanya bila dibuka dan belum lewat 30 detik (kunci otomatis). */
export function doorStatus(state, t) {
  const door = state.security.door;
  if (door.state !== "unlocked") return "locked";
  return t - Date.parse(door.changedAt) < AUTO_LOCK_MS ? "unlocked" : "locked";
}

const sec = (s, patch) => ({ ...s, security: { ...s.security, ...patch } });

/** Buka kunci pintu; terkunci sendiri setelah 30 detik (diturunkan oleh doorStatus). */
export async function unlockDoor(method = "aplikasi") {
  await wait();
  const t = now();
  const how = method.charAt(0).toUpperCase() + method.slice(1);
  setState((s) => sec(s, {
    door: { state: "unlocked", changedAt: iso(t) },
    doorLog: [{ id: newId("dl", t), who: "Rina", how, state: "unlocked", at: iso(t) }, ...s.security.doorLog],
  }));
}

/** Kunci pintu. Idempoten: bila sudah terkunci tidak menulis apa pun. */
export async function lockDoor() {
  await wait();
  const t = now();
  const { door } = getState().security;
  if (door.state !== "unlocked") return;
  const openedAt = Date.parse(door.changedAt);
  const auto = t - openedAt >= AUTO_LOCK_MS;
  const at = auto ? openedAt + AUTO_LOCK_MS : t;
  setState((s) => sec(s, {
    door: { state: "locked", changedAt: iso(at) },
    doorLog: [
      { id: newId("dl", t), who: auto ? RESIDENT : "Rina", how: auto ? "Otomatis terkunci" : "Aplikasi", state: "locked", at: iso(at) },
      ...s.security.doorLog,
    ],
  }));
}

const pin4 = () => String(Math.floor(Math.random() * 10000)).padStart(4, "0");

/** Kode akses sementara (PIN 4 digit) untuk ART/tukang. `validUntil` = ISO atau epoch ms. */
export async function createAccessCode({ label, validUntil }) {
  await wait();
  const name = clean(label);
  if (!name) throw new Error("Nama kode belum diisi");
  const until = Date.parse(typeof validUntil === "number" ? iso(validUntil) : validUntil);
  const t = now();
  if (!Number.isFinite(until) || until <= t) throw new Error("Masa berlaku tidak valid");
  const code = { id: newId("ac", t), label: name, pin: pin4(), validUntil: iso(until), revoked: false };
  setState((s) => sec(s, { accessCodes: [code, ...s.security.accessCodes] }));
  return code;
}

export async function revokeAccessCode(id) {
  await wait();
  if (!getState().security.accessCodes.some((c) => c.id === id)) throw new Error("Kode tidak ditemukan");
  setState((s) => sec(s, { accessCodes: s.security.accessCodes.map((c) => (c.id === id ? { ...c, revoked: true } : c)) }));
}

const CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
function passCode(taken) {
  let code = "";
  do {
    code = Array.from({ length: 6 }, () => CHARS[Math.floor(Math.random() * CHARS.length)]).join("");
  } while (taken.has(code));
  return code;
}

/** Undangan tamu sekali pakai; `date` 'YYYY-MM-DD', `from`/`to` 'HH:mm' (WIB). */
export async function createGuestPass({ guestName, date, from, to }) {
  await wait();
  const name = clean(guestName);
  if (!name) throw new Error("Nama tamu belum diisi");
  if (!clean(date)) throw new Error("Tanggal kunjungan belum diisi");
  if (!clean(from) || !clean(to) || to <= from) throw new Error("Jam selesai harus setelah jam mulai");
  const t = now();
  const taken = new Set(getState().security.guestPasses.map((p) => p.code));
  const pass = { id: newId("gp", t), code: passCode(taken), guestName: name, date: clean(date), from, to, status: "active" };
  setState((s) => sec(s, { guestPasses: [pass, ...s.security.guestPasses] }));
  return pass;
}

/** Status tampilan: undangan aktif yang jamnya lewat dianggap kedaluwarsa. */
export function guestPassStatus(pass, t) {
  if (pass.status !== "active") return pass.status;
  return Date.parse(`${pass.date}T${pass.to}:00+07:00`) < t ? "expired" : "active";
}

export async function revokeGuestPass(id) {
  await wait();
  const p = getState().security.guestPasses.find((x) => x.id === id);
  if (!p) throw new Error("Undangan tidak ditemukan");
  if (p.status === "used") throw new Error("Undangan sudah dipakai");
  setState((s) => sec(s, { guestPasses: s.security.guestPasses.map((x) => (x.id === id ? { ...x, status: "revoked" } : x)) }));
}

/** Buka gerbang pintar; hanya dari dalam radius gerbang. */
export async function openGate(direction) {
  await wait();
  if (direction !== "masuk" && direction !== "keluar") throw new Error("Arah gerbang tidak valid");
  const state = getState();
  if (state.location === "outside") throw new Error("Anda di luar area gerbang");
  const t = now();
  const entry = {
    id: newId("gl", t), name: RESIDENT, plate: state.world.resident.plate || "—",
    purpose: "Penghuni", direction, at: iso(t),
  };
  setState((s) => sec(s, { gateLog: [entry, ...s.security.gateLog] }));
}
