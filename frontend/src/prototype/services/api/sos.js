/** SOS darurat dan kontak darurat. Dipakai juga oleh aplikasi satpam (acceptSos/resolveSos). */
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";
import { formatPhone } from "./resident";

export const SOS_TYPES = [
  { id: "kemalingan", label: "Kemalingan" },
  { id: "kebakaran", label: "Kebakaran" },
  { id: "medis", label: "Medis" },
  { id: "lainnya", label: "Lainnya" },
];
export const sosLabel = (id) => (SOS_TYPES.find((t) => t.id === id) || { label: id }).label;

const iso = (t) => new Date(t).toISOString();
const ACTIVE = ["sent", "accepted"];
const sec = (s, patch) => ({ ...s, security: { ...s.security, ...patch } });

/** SOS terbaru yang masih berjalan (sent/accepted), atau null. */
export function activeSos(state) {
  return state.security.sos.find((e) => ACTIVE.includes(e.status)) || null;
}

/** Kirim SOS (satu laporan aktif sekaligus) dan tambahkan notifikasi tingkat darurat. */
export async function sendSos(type) {
  await wait();
  if (!SOS_TYPES.some((x) => x.id === type)) throw new Error("Jenis darurat tidak dikenal");
  if (activeSos(getState())) throw new Error("Masih ada laporan darurat yang aktif");
  const t = now();
  const event = { id: newId("sos", t), type, unit: getState().world.unit.block, status: "sent", createdAt: iso(t) };
  const note = {
    id: newId("nt-sos", t), audience: "resident", tier: "darurat", title: `SOS ${sosLabel(type).toLowerCase()} terkirim`,
    body: `Laporan dari ${event.unit} sudah diteruskan ke satpam. Tetap tenang dan tunggu bantuan.`,
    at: iso(t), read: false, link: "/app/warga/sos",
  };
  setState((s) => ({ ...sec(s, { sos: [event, ...s.security.sos] }), notifications: [note, ...s.notifications] }));
  return event;
}

function change(id, allowed, fail, patch, notify) {
  const e = getState().security.sos.find((x) => x.id === id);
  if (!e) throw new Error("Laporan tidak ditemukan");
  if (!allowed.includes(e.status)) throw new Error(fail);
  setState((s) => ({
    ...sec(s, { sos: s.security.sos.map((x) => (x.id === id ? { ...x, ...patch } : x)) }),
    notifications: notify ? [notify, ...s.notifications] : s.notifications,
  }));
}

/** Batalkan laporan hanya selama belum diterima satpam. */
export async function cancelSos(id) {
  await wait();
  change(id, ["sent"], "Laporan sudah diterima satpam dan tidak bisa dibatalkan", { status: "cancelled" });
}

/** Satpam menerima laporan (hanya dari 'sent'); warga diberi tahu. */
export async function acceptSos(id, guardName = "Joko") {
  await wait();
  const t = now();
  const name = String(guardName || "").trim() || "Joko";
  const note = {
    id: newId("nt-sosok", t), audience: "resident", tier: "keamanan", title: `Pak ${name.replace(/^pak\s+/i, "")} menuju rumah Anda`,
    body: "Satpam sudah menerima laporan darurat Anda. Tetap di tempat yang aman.",
    at: iso(t), read: false, link: "/app/warga/sos",
  };
  change(id, ["sent"], "Laporan ini sudah tidak menunggu", { status: "accepted", acceptedBy: name, acceptedAt: iso(t) }, note);
}

/** Satpam menandai selesai (hanya dari 'accepted'), dengan catatan opsional. */
export async function resolveSos(id, note) {
  await wait();
  const text = String(note == null ? "" : note).trim();
  change(id, ["accepted"], "Terima laporan lebih dulu sebelum menandai selesai", {
    status: "resolved", resolvedAt: iso(now()), ...(text ? { note: text } : {}),
  });
}

export async function listContacts() {
  await wait();
  return [...getState().security.contacts];
}

const digits = (v) => String(v == null ? "" : v).replace(/\D/g, "");

/** Simpan kontak darurat; `relation` disimpan sebagai `role`. */
export async function saveContact({ name, phone, relation }) {
  await wait();
  const n = String(name || "").trim();
  if (!n) throw new Error("Nama belum diisi");
  if (digits(phone).length < 10) throw new Error(`Nomor ${n} belum lengkap`);
  const formatted = formatPhone(phone);
  const { contacts } = getState().security;
  if (contacts.some((c) => digits(c.phone) === digits(formatted))) throw new Error("Nomor ini sudah ada di kontak darurat");
  const contact = { id: newId("ct", now()), name: n, phone: formatted, role: String(relation || "").trim() || "Lainnya" };
  setState((s) => sec(s, { contacts: [contact, ...s.security.contacts] }));
  return contact;
}

export async function removeContact(id) {
  await wait();
  setState((s) => sec(s, { contacts: s.security.contacts.filter((c) => c.id !== id) }));
}
