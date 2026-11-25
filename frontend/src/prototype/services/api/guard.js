/** Aplikasi satpam: terima SOS, pindai tamu, patroli. Logika SOS ada di sos.js (satu sumber). */
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";
import { guestPassStatus } from "./security";

export { acceptSos, resolveSos } from "./sos";

export const GUARD_NAME = "Joko";
const iso = (t) => new Date(t).toISOString();
const sec = (s, patch) => ({ ...s, security: { ...s.security, ...patch } });

export const normalizeCode = (code) => String(code == null ? "" : code).trim().toUpperCase();

/** Alasan tampilan untuk hasil pemeriksaan tamu yang tidak valid. */
export const GUEST_REASONS = {
  "tidak-ditemukan": "Kode tidak ditemukan. Periksa kembali kode tamu.",
  "sudah-dipakai": "Kode ini sudah dipakai. Undangan hanya berlaku sekali.",
  kedaluwarsa: "Undangan sudah kedaluwarsa (di luar tanggal atau jam kunjungan).",
  dicabut: "Undangan sudah dibatalkan oleh penghuni.",
};

/** Periksa kode tamu; berhasil → status 'used', tercatat di log gerbang, warga diberi tahu. */
export async function checkInGuest(code) {
  await wait();
  const c = normalizeCode(code);
  const t = now();
  const pass = getState().security.guestPasses.find((p) => p.code === c);
  if (!c || !pass) return { ok: false, reason: "tidak-ditemukan" };
  if (pass.status === "used") return { ok: false, reason: "sudah-dipakai" };
  if (pass.status === "revoked") return { ok: false, reason: "dicabut" };
  if (guestPassStatus(pass, t) !== "active") return { ok: false, reason: "kedaluwarsa" };
  const used = { ...pass, status: "used", usedAt: iso(t) };
  const { unit } = getState().world;
  const entry = { id: newId("gl", t), name: pass.guestName, plate: "—", purpose: `Tamu ${unit.block}`, direction: "masuk", at: iso(t) };
  const note = {
    id: newId("nt-tamu", t), tier: "keamanan", title: `Tamu ${pass.guestName} sudah masuk`,
    body: `${pass.guestName} melewati gerbang pukul ${new Date(t + 7 * 3600000).toISOString().slice(11, 16).replace(":", ".")} WIB.`,
    at: iso(t), read: false, link: "/app/warga/keamanan/tamu",
  };
  setState((s) => ({
    ...sec(s, {
      guestPasses: s.security.guestPasses.map((p) => (p.id === pass.id ? used : p)),
      gateLog: [entry, ...s.security.gateLog],
    }),
    notifications: [note, ...s.notifications],
  }));
  return { ok: true, pass: used };
}

/** Catat titik patroli (titik wajib diisi). */
export async function logPatrol({ checkpoint, note }) {
  await wait();
  const cp = String(checkpoint == null ? "" : checkpoint).trim();
  if (!cp) throw new Error("Titik patroli belum diisi");
  const t = now();
  const entry = { id: newId("pt", t), checkpoint: cp, note: String(note == null ? "" : note).trim(), by: `Pak ${GUARD_NAME}`, at: iso(t) };
  setState((s) => sec(s, { patrols: [entry, ...(s.security.patrols || [])] }));
  return entry;
}
