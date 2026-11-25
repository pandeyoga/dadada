import { setState, now } from "../store";
import { wait } from "../latency";

const digits = (v) => String(v == null ? "" : v).replace(/\D/g, "");

/** Nomor lokal: 62812… → 0812…; selain itu hanya digit. */
function normalizePhone(v) {
  const d = digits(v);
  return d.startsWith("62") ? `0${d.slice(2)}` : d;
}

/** Simulasi kirim OTP WhatsApp; tidak ada jaringan. */
export async function requestOtp(phone) {
  await wait();
  const p = normalizePhone(phone);
  if (digits(phone).length < 10) throw new Error("Nomor WhatsApp belum lengkap");
  setState((s) => ({ ...s, session: { ...s.session, phone: p } }));
  return { sentTo: `${p.slice(0, 4)}-****-${p.slice(-4)}` };
}

/** Kode 6 digit apa pun diterima (simulasi). */
export async function verifyOtp(code) {
  await wait();
  if (!/^\d{6}$/.test(String(code))) throw new Error("Kode harus 6 angka");
  setState((s) => ({ ...s, session: { ...s.session, loggedIn: true } }));
}

/** Pintasan presenter: pilih persona dan tandai sudah masuk. */
export function setPersona(persona) {
  setState((s) => ({
    ...s,
    session: { ...s.session, persona, loggedIn: true },
    mode: persona === "resident" ? "resident" : persona === "buyer" ? "buyer" : s.mode,
    onboarding: persona === "resident" ? { ...s.onboarding, done: true } : s.onboarding,
  }));
}

export function logout() {
  setState((s) => ({ ...s, session: { ...s.session, loggedIn: false } }));
}

/** Serah terima (BAST): pembeli menjadi warga baru yang belum onboarding. */
export function simulateBast() {
  const t = now();
  setState((s) => ({
    ...s,
    session: { ...s.session, persona: "resident", loggedIn: true },
    mode: "resident",
    onboarding: { ...s.onboarding, done: false },
    buyer: { ...s.buyer, journey: { ...s.buyer.journey, current: 5, progress: 100 } },
    notifications: [
      {
        id: `nt-bast-${t}`, audience: "resident", tier: "info", title: "Selamat, rumah Anda resmi diserahterimakan",
        body: "Rumah C-12 Estora Residence kini milik Anda. Mulai kenali fitur warga.",
        at: new Date(t).toISOString(), read: false, link: "/app/selamat-datang",
      },
      ...s.notifications,
    ],
  }));
}

export function setLocation(location) {
  setState((s) => ({ ...s, location }));
}

const HOME = { buyer: "/app/pembeli", satpam: "/app/satpam", pengelola: "/app/pengelola", mitra: "/app/mitra" };

export function homePathFor(state) {
  const { persona, loggedIn } = state.session;
  if (!loggedIn) return "/app/demo";
  if (persona === "resident") return state.onboarding.done ? "/app/warga" : "/app/selamat-datang";
  return HOME[persona] || "/app/demo";
}

