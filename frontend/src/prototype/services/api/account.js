// Akun warga: keluarga/penyewa, perangkat, notifikasi berjenjang, energi (simulasi, tanpa jaringan).
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { prepare } from "./resident";

export const ACCESS_OPTIONS = [
  { id: "pintu", label: "Pintu" },
  { id: "cctv", label: "CCTV" },
  { id: "tagihan", label: "Tagihan" },
];
export const ROLES = { keluarga: "Keluarga", penyewa: "Penyewa", art: "Asisten rumah" };
const TIER_RANK = { darurat: 0, keamanan: 1, info: 2 };
const TIPS = [
  "Cabut charger dan alat yang tidak dipakai; daya siaga ikut menambah tagihan.",
  "Ganti lampu dengan LED 5-9 watt, hemat sekitar sepertiga listrik penerangan.",
  "Atur AC di 24-26 derajat dan bersihkan filter tiap bulan.",
  "Cek kran dan toilet yang menetes; satu kran bocor bisa membuang 1 m3 air per bulan.",
];

// Data lama menyimpan access sebagai boolean; selalu kembalikan daftar hak akses.
const accessOf = (a) => (Array.isArray(a) ? a : a ? ["pintu", "cctv"] : []);
const normalize = (m) => ({ ...m, role: m.role || "keluarga", access: accessOf(m.access) });

export async function listFamily() {
  await wait();
  return getState().care.family.map(normalize);
}

/** Undang anggota keluarga/penyewa/ART. Nama dan nomor divalidasi; duplikat dilewati. */
export async function inviteFamily({ name, phone, role = "keluarga", access = [] }) {
  await wait();
  if (!ROLES[role]) throw new Error("Pilih peran anggota");
  const { care } = getState();
  const [entry] = prepare([{ name, phone }], care.family);
  if (!entry) {
    // Sudah terdaftar (nama atau nomor sama): kembalikan anggota yang ada, tanpa entri baru.
    const d = (v) => String(v || "").replace(/\D/g, "");
    const same = care.family.find((m) => m.name.trim().toLowerCase() === String(name).trim().toLowerCase() || (d(m.phone) && d(m.phone) === d(phone)));
    return normalize(same);
  }
  const ids = new Set(ACCESS_OPTIONS.map((o) => o.id));
  const member = { id: `fm-${now()}-${care.family.length}`, ...entry, relation: ROLES[role], role, access: [...new Set(access)].filter((a) => ids.has(a)) };
  setState((s) => ({ ...s, care: { ...s.care, family: [...s.care.family, member] } }));
  return member;
}

export async function listDevices() {
  await wait();
  return [...getState().care.devices];
}

/** 6 bulan pemakaian (terlama dulu) + tips. Angka perkiraan simulasi, bukan meter sungguhan. */
export async function getEnergy() {
  await wait();
  return { months: getState().security.energy.months, tips: TIPS };
}

/** Penerima notifikasi untuk mode aplikasi: Mode Pembeli → 'buyer', selain itu 'resident'. */
export const audienceFor = (mode) => (mode === "buyer" ? "buyer" : "resident");
/** Notifikasi ini untuk mode `mode`? (Data tanpa `audience` dianggap untuk warga.) */
export const isForMode = (n, mode) => (n.audience || "resident") === audienceFor(mode);

/** Notifikasi mode aktif saja: darurat › keamanan › info, lalu terbaru dulu. */
export async function listNotifications() {
  await wait();
  const { notifications, mode } = getState();
  return notifications.filter((n) => isForMode(n, mode))
    .sort((a, b) => (TIER_RANK[a.tier] ?? 9) - (TIER_RANK[b.tier] ?? 9) || Date.parse(b.at) - Date.parse(a.at));
}

export async function markRead(id) {
  await wait();
  setState((s) => ({ ...s, notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)) }));
}

/** Tandai dibaca semua notifikasi mode aktif (notifikasi mode lain tidak tersentuh). */
export async function markAllRead() {
  await wait();
  setState((s) => ({ ...s, notifications: s.notifications.map((n) => (n.read || !isForMode(n, s.mode) ? n : { ...n, read: true })) }));
}
