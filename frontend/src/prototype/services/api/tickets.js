// Penulis tiket bersama: dipakai pertanyaan pembeli (tanya), laporan kerusakan (rusak) dan klaim garansi (garansi).
import { setState, now } from "../store";
import { newId } from "../ids";

const NOTES = { rusak: "Laporan dibuat oleh Rina Ayu.", tanya: "Pertanyaan dikirim oleh Rina Ayu.", garansi: "Klaim garansi dikirim oleh Rina Ayu." };

/** Buat tiket baru berstatus `dibuat` dan simpan paling depan di `care.tickets`. */
export function insertTicket({ kind, category, description, photos = [] }) {
  const t = now();
  const ticket = {
    id: newId("tk", t),
    kind, category, description: String(description).trim(), photos: [...photos], status: "dibuat",
    history: [{ status: "dibuat", at: new Date(t).toISOString(), note: NOTES[kind] || NOTES.rusak }],
  };
  setState((s) => ({ ...s, care: { ...s.care, tickets: [ticket, ...s.care.tickets] } }));
  return ticket;
}
