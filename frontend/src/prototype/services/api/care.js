// Perawatan rumah: tiket kerusakan, garansi, dokumen rumah, izin renovasi, booking fasilitas (simulasi, tanpa jaringan).
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";
import { insertTicket } from "./tickets";

export const TICKET_FLOW = ["dibuat", "diverifikasi", "dikerjakan", "selesai"];
export const RENOVATION_TYPES = ["Tambah kamar", "Kanopi dan pagar", "Ganti lantai atau keramik", "Renovasi dapur", "Lainnya"];
const MONTH_MS = 30.4375 * 86400000;
const STEP_NOTES = {
  diverifikasi: "Teknisi memeriksa lokasi.",
  dikerjakan: "Perbaikan sedang dikerjakan.",
  selesai: "Perbaikan selesai. Mohon konfirmasi dan beri nilai.",
};
const patchCare = (fn) => setState((s) => ({ ...s, care: fn(s.care) }));
const findTicket = (id) => {
  const t = getState().care.tickets.find((x) => x.id === id);
  if (!t) throw new Error("Tiket tidak ditemukan");
  return t;
};
const saveTicket = (id, fn) => {
  let out;
  patchCare((c) => ({ ...c, tickets: c.tickets.map((x) => (x.id === id ? (out = fn(x)) : x)) }));
  return out;
};
const tooShort = (d) => String(d || "").trim().length < 10;

export async function listTickets() {
  await wait();
  return [...getState().care.tickets];
}

/** Laporan baru (rusak/garansi). Deskripsi minimal 10 karakter. */
export async function createTicket({ kind = "rusak", category, description, photos = [] }) {
  await wait();
  if (tooShort(description)) throw new Error("Ceritakan kerusakannya sedikit lebih jelas");
  return insertTicket({ kind, category: category || "Lainnya", description, photos });
}

/** Langkah pengelola: dibuat › diverifikasi › dikerjakan › selesai. */
export async function advanceTicket(id) {
  await wait();
  const tk = findTicket(id);
  const next = TICKET_FLOW[TICKET_FLOW.indexOf(tk.status) + 1];
  if (!next) throw new Error("Tiket sudah selesai");
  const at = new Date(now()).toISOString();
  const out = saveTicket(id, (x) => ({
    ...x, status: next, assignee: x.assignee || "Tim Teknik Estora",
    history: [...x.history, { status: next, at, note: STEP_NOTES[next] }],
  }));
  if (next === "selesai") {
    setState((s) => ({
      ...s,
      notifications: [{ id: newId("nt", now()), tier: "info", title: "Perbaikan selesai dikerjakan", body: `${tk.category}: mohon konfirmasi dan beri nilai.`, at, read: false, link: "/app/warga/lapor" }, ...s.notifications],
    }));
  }
  return out;
}

/** Warga mengonfirmasi hasil dan memberi nilai 1–5; hanya dari `selesai`. */
export async function confirmTicket(id, rating) {
  await wait();
  const tk = findTicket(id);
  if (tk.status !== "selesai") throw new Error("Tiket belum selesai dikerjakan");
  const n = Number(rating);
  if (!Number.isInteger(n) || n < 1 || n > 5) throw new Error("Beri nilai 1 sampai 5 bintang");
  const at = new Date(now()).toISOString();
  return saveTicket(id, (x) => ({
    ...x, status: "dikonfirmasi", rating: n,
    history: [...x.history, { status: "dikonfirmasi", at, note: `Dikonfirmasi warga dengan nilai ${n} dari 5.` }],
  }));
}

const withRemaining = (w, t) => {
  const end = Date.parse(w.startedAt) + w.months * MONTH_MS;
  const remainingDays = Math.max(0, Math.ceil((end - t) / 86400000));
  return { ...w, endsAt: new Date(end).toISOString(), remainingDays, remainingMonths: Math.floor(Math.max(0, end - t) / MONTH_MS), active: end > t };
};

/** Garansi per bagian rumah, lengkap dengan sisa masa. */
export async function listWarranty() {
  await wait();
  const t = now();
  return getState().care.warranty.map((w) => withRemaining(w, t));
}

/** Klaim garansi → tiket `garansi`. */
export async function claimWarranty({ itemId, description }) {
  await wait();
  const w = getState().care.warranty.find((x) => x.id === itemId);
  if (!w) throw new Error("Bagian rumah tidak ditemukan");
  if (!withRemaining(w, now()).active) throw new Error(`Masa garansi ${w.part} sudah berakhir`);
  if (tooShort(description)) throw new Error("Ceritakan kerusakannya sedikit lebih jelas");
  return insertTicket({ kind: "garansi", category: w.part, description });
}

/** Dokumen rumah; status mengikuti perjalanan serah terima dan kuitansi. */
export async function listHomeDocuments() {
  await wait();
  const { buyer, bills, care } = getState();
  const handed = buyer.journey.current >= 5;
  const receipts = bills.receipts.length;
  return [
    { id: "hd-bast", kind: "bast", title: "Berita acara serah terima (BAST)", status: handed ? "Tersedia" : "Menunggu serah terima", tone: handed ? "ok" : "warn", note: "Tanda terima rumah dari pengembang." },
    { id: "hd-shm", kind: "sertifikat", title: "Sertifikat hak milik (SHM)", status: "Dalam proses", tone: "info", note: "Dipecah dari sertifikat induk; pantau di sini." },
    { id: "hd-pbg", kind: "pbg", title: "Persetujuan bangunan gedung (PBG)", status: "Terbit", tone: "ok", note: "Izin mendirikan bangunan Blok C." },
    { id: "hd-garansi", kind: "garansi", title: "Garansi rumah", status: `${care.warranty.length} bagian dijamin`, tone: "ok", note: "Rincian ada di menu Garansi." },
    { id: "hd-denah", kind: "denah", title: "Denah rumah tipe 36/72", status: "Tersedia", tone: "ok", note: "Ukuran ruang dan letak pintu." },
    { id: "hd-instalasi", kind: "instalasi", title: "Jalur instalasi listrik dan air", status: "Tersedia", tone: "ok", note: "Letak pipa dan kabel di dalam dinding." },
    { id: "hd-kuitansi", kind: "kuitansi", title: "Kuitansi pembayaran", status: `${receipts} kuitansi`, tone: "neutral", note: "Semua bukti bayar ada di Riwayat tagihan." },
  ];
}

export async function listRenovations() {
  await wait();
  return [...getState().care.renovations];
}

/** Ajukan izin renovasi ke pengelola. */
export async function submitRenovation({ type, startDate, endDate, contractor }) {
  await wait();
  if (!String(type || "").trim()) throw new Error("Pilih jenis renovasi");
  if (!startDate || !endDate) throw new Error("Isi tanggal mulai dan selesai");
  if (endDate < startDate) throw new Error("Tanggal selesai tidak boleh sebelum tanggal mulai");
  if (!String(contractor || "").trim()) throw new Error("Nama kontraktor belum diisi");
  const req = { id: newId("rn", now()), type, startDate, endDate, contractor: String(contractor).trim(), status: "diajukan", createdAt: new Date(now()).toISOString() };
  patchCare((c) => ({ ...c, renovations: [req, ...c.renovations] }));
  return req;
}

/** Fasilitas bersama beserta pesanan yang sudah ada (untuk menandai jam terisi). */
export async function listFacilities() {
  await wait();
  const { community, care } = getState();
  return community.facilities.map((f) => ({
    ...f, bookings: care.bookings.filter((b) => b.facilityId === f.id).map((b) => ({ id: b.id, date: b.date, slot: b.slot })),
  }));
}

export async function listFacilityBookings() {
  await wait();
  return [...getState().care.bookings];
}

/** Pesan jam fasilitas; fasilitas + tanggal + jam yang sama tidak bisa dipesan dua kali. */
export async function bookFacility({ facilityId, date, slot }) {
  await wait();
  const f = getState().community.facilities.find((x) => x.id === facilityId);
  if (!f) throw new Error("Fasilitas tidak ditemukan");
  if (!date) throw new Error("Pilih tanggal");
  if (!f.slots.includes(slot)) throw new Error("Pilih jam yang tersedia");
  if (getState().care.bookings.some((b) => b.facilityId === facilityId && b.date === date && b.slot === slot)) throw new Error("Jam ini sudah dipesan");
  const booking = { id: newId("fb", now()), facilityId, facilityName: f.name, fee: f.fee, date, slot, status: "dikonfirmasi", createdAt: new Date(now()).toISOString() };
  patchCare((c) => ({ ...c, bookings: [booking, ...c.bookings] }));
  return booking;
}
