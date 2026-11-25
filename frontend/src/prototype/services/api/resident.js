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

const clean = (list) => (list || []).map((x) => ({ name: String(x.name || "").trim(), phone: String(x.phone || "").replace(/\D/g, "") })).filter((x) => x.name);

/** Selesaikan onboarding: simpan undangan keluarga dan kontak darurat baru. */
export async function completeOnboarding({ connectDevices = true, invites = [], contacts = [] } = {}) {
  await wait();
  const t = now();
  const fam = clean(invites).map((x, i) => ({ id: `fam-${t}-${i}`, ...x, status: "diundang" }));
  const cts = clean(contacts).map((x, i) => ({ id: `ct-${t}-${i}`, ...x, role: "Keluarga" }));
  setState((s) => ({
    ...s,
    onboarding: { ...s.onboarding, done: true, connectDevices: !!connectDevices },
    world: { ...s.world, family: [...(s.world.family || []), ...fam] },
    security: { ...s.security, contacts: [...s.security.contacts, ...cts] },
  }));
}
