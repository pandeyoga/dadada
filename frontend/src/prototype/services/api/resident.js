import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { doorStatus } from "./security";

// "Pagi 06.00-14.00" → [6, 14]; shift malam melewati tengah malam.
function onDuty(shift, hour) {
  const m = /(\d{2})\.\d{2}-(\d{2})\.\d{2}/.exec(shift);
  if (!m) return false;
  const from = Number(m[1]);
  const to = Number(m[2]);
  return from < to ? hour >= from && hour < to : hour >= from || hour < to;
}

const wibHour = (t) => (new Date(t).getUTCHours() + 7) % 24;

/** Satpam yang sedang bertugas pada waktu `t`. */
export function guardsOnDutyAt(world, t) {
  return world.guards.filter((g) => onDuty(g.shift, wibHour(t)));
}

/** Data Beranda warga. */
export async function getResidentHome() {
  await wait();
  const state = getState();
  const t = now();
  const door = doorStatus(state, t);
  const guardsOnDuty = state.world.guards.filter((g) => onDuty(g.shift, wibHour(t))).length;
  const anns = [...state.community.announcements].sort((a, b) => Number(b.pinned) - Number(a.pinned) || Date.parse(b.at) - Date.parse(a.at));
  const { kwh, deltaPct } = state.security.energy;
  return {
    homeStatus: {
      door,
      cameras: "aktif",
      cameraCount: state.security.cameras.home,
      guardsOnDuty,
      safe: door === "locked" && guardsOnDuty > 0,
    },
    iplDue: state.bills.ipl.find((b) => b.status !== "paid") || null,
    announcement: anns[0] || null,
    energy: { kwh, deltaPct },
  };
}

const digitsOf = (v) => String(v == null ? "" : v).replace(/\D/g, "");

/** 0812-3456-7001 (gaya fixture); 62… → 0…. */
export function formatPhone(v) {
  let d = digitsOf(v);
  if (d.startsWith("62")) d = `0${d.slice(2)}`;
  return d.length > 8 ? `${d.slice(0, 4)}-${d.slice(4, 8)}-${d.slice(8)}` : d;
}

// Validasi (tolak seluruh panggilan bila ada entri tidak valid), lalu lewati duplikat nama/nomor.
function prepare(list, existing) {
  const seenName = new Set(existing.map((x) => x.name.trim().toLowerCase()));
  const seenPhone = new Set(existing.map((x) => digitsOf(x.phone)).filter(Boolean));
  const out = [];
  (list || []).forEach((x) => {
    const name = String((x && x.name) || "").trim();
    if (!name) throw new Error("Nama belum diisi");
    if (digitsOf(x.phone).length < 10) throw new Error(`Nomor WhatsApp ${name} belum lengkap`);
    const phone = formatPhone(x.phone);
    if (seenName.has(name.toLowerCase()) || seenPhone.has(digitsOf(phone))) return;
    seenName.add(name.toLowerCase());
    seenPhone.add(digitsOf(phone));
    out.push({ name, phone });
  });
  return out;
}

/** Selesaikan onboarding: simpan undangan keluarga (care.family) dan kontak darurat baru. */
export async function completeOnboarding({ connectDevices = true, invites = [], contacts = [] } = {}) {
  await wait();
  const t = now();
  const { care, security } = getState();
  const fam = prepare(invites, care.family).map((x, i) => ({ id: `fm-${t}-${i}`, ...x, relation: "Keluarga", access: false }));
  const cts = prepare(contacts, security.contacts).map((x, i) => ({ id: `ct-${t}-${i}`, ...x, role: "Keluarga" }));
  setState((s) => ({
    ...s,
    onboarding: { ...s.onboarding, done: true, connectDevices: !!connectDevices },
    care: { ...s.care, family: [...s.care.family, ...fam] },
    security: { ...s.security, contacts: [...s.security.contacts, ...cts] },
  }));
}
