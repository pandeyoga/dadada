// Dasbor pengelola: ringkasan, tagihan IPL, tiket, pengumuman, mitra (simulasi, tanpa jaringan).
// Status IPL C-12 dibaca dari bills.ipl (sumber tunggal); unit lain dari manager.iplPeriods.
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";

const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const TIERS = ["darurat", "keamanan", "info"];
const OPEN_TICKET = ["dibuat", "diverifikasi", "dikerjakan"];
const iso = (t) => new Date(t).toISOString();
const text = (v) => String(v == null ? "" : v).trim();
const patchManager = (fn) => setState((s) => ({ ...s, manager: fn(s.manager) }));
// Notifikasi dari pengelola selalu untuk warga (Mode Warga).
const notify = (tier, title, body, link, about) => ({
  id: newId("nt-mgr", now()), audience: "resident", tier, title, body, at: iso(now()), read: false, link, ...(about ? { about } : {}),
});

export const periodLabel = (period) => {
  const m = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(period || "");
  return m ? `${MONTHS[Number(m[2]) - 1]} ${m[1]}` : "";
};

/** Semua periode (state lama tanpa iplPeriods dianggap hanya Desember 2026), terlama dulu. */
function periodsOf(m) {
  const list = m.iplPeriods && m.iplPeriods.length ? m.iplPeriods : [{
    period: "2026-12", label: "Desember 2026",
    statuses: Object.fromEntries(m.units.map((u) => [u.block, u.ipl])),
  }];
  return [...list].sort((a, b) => a.period.localeCompare(b.period));
}
const currentPeriod = (m) => { const l = periodsOf(m); return l[l.length - 1]; };

/** Periode yang sudah terbit, terbaru dulu: [{period, label}]. */
export function listIplPeriods(state = getState()) {
  return periodsOf(state.manager).map((p) => ({ period: p.period, label: p.label || periodLabel(p.period) })).reverse();
}

function overviewOf(state, p) {
  const { manager: m, bills, world } = state;
  const bill = bills.ipl.find((b) => b.id === `ipl-${p.period}`);
  const units = m.units.map((u) => {
    const status = u.block === world.unit.block ? (bill && bill.status === "paid" ? "lunas" : "belum") : (p.statuses && p.statuses[u.block]) || "belum";
    return { block: u.block, owner: u.owner, phone: u.phone, amount: u.amount, status };
  });
  const paid = units.filter((u) => u.status === "lunas").length;
  return { period: p.period, label: p.label || periodLabel(p.period), units, paid, total: units.length, paidPct: units.length ? Math.round((paid / units.length) * 100) : 0 };
}

/** Tagihan IPL satu periode (bawaan: terbaru): {period, label, units, paid, total, paidPct, previous?}. Status C-12 dari bills.ipl. */
export function iplOverview(state = getState(), period) {
  const all = periodsOf(state.manager);
  const p = all.find((x) => x.period === period) || all[all.length - 1];
  const prev = all[all.indexOf(p) - 1];
  const out = overviewOf(state, p);
  if (prev) { const { period: pp, label, paidPct } = overviewOf(state, prev); out.previous = { period: pp, label, paidPct }; }
  return out;
}

const wibMonth = (t) => iso(t + 7 * 3600000).slice(0, 7);

/** Empat angka ringkasan K1. */
export function getManagerSummary(state = getState()) {
  const { paidPct } = iplOverview(state);
  const occ = state.manager.occupancy || { occupied: state.manager.units.length, total: state.manager.units.length };
  const month = wibMonth(now());
  return {
    iplPaidPct: paidPct,
    openTickets: state.care.tickets.filter((t) => OPEN_TICKET.includes(t.status)).length,
    sosThisMonth: state.security.sos.filter((e) => wibMonth(Date.parse(e.createdAt)) === month).length,
    occupancy: Math.round((occ.occupied / occ.total) * 100),
  };
}

export async function getIplOverview(period) {
  await wait();
  return iplOverview(getState(), period);
}

/** Terbitkan tagihan IPL satu periode ('2027-01') untuk semua unit; periode ganda ditolak. */
export async function issueIplBills(period) {
  await wait();
  const label = periodLabel(period);
  if (!label) throw new Error("Periode tidak valid");
  const state = getState();
  const issued = (state.manager.iplPeriods || []).some((p) => p.period === period) || state.bills.ipl.some((b) => b.id === `ipl-${period}`)
    || currentPeriod(state.manager).period === period;
  if (issued) throw new Error("Tagihan periode ini sudah diterbitkan");
  const t = now();
  const amount = state.manager.units[0] ? state.manager.units[0].amount : 150000;
  const bill = { id: `ipl-${period}`, kind: "ipl", period: label, amount, dueDate: `${period}-10`, status: "unpaid" };
  const rec = { period, label, issuedAt: iso(t), statuses: Object.fromEntries(state.manager.units.map((u) => [u.block, "belum"])) };
  const note = notify("info", `Tagihan IPL ${label}`, `Iuran Rp${String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, ".")} jatuh tempo 10 ${MONTHS[Number(period.slice(5)) - 1].slice(0, 3)}.`, "/app/warga/tagihan", bill.id);
  setState((s) => ({
    ...s,
    bills: { ...s.bills, ipl: [bill, ...s.bills.ipl] },
    manager: { ...s.manager, iplPeriods: [...(s.manager.iplPeriods || [currentPeriod(s.manager)]), rec] },
    notifications: [note, ...s.notifications],
  }));
  return { created: Object.keys(rec.statuses).length };
}

/** Kirim pengingat ke unit (blok) yang belum lunas; mengembalikan jumlah terkirim. */
export async function sendIplReminders(unitIds, period) {
  await wait();
  const state = getState();
  const ov = iplOverview(state, period);
  const targets = ov.units.filter((u) => (unitIds || []).includes(u.block) && u.status !== "lunas");
  if (targets.some((u) => u.block === state.world.unit.block)) {
    const note = notify("info", "Pengingat iuran IPL", `Iuran IPL ${ov.label} belum lunas. Bayar lewat aplikasi agar tercatat otomatis.`, "/app/warga/tagihan");
    setState((s) => ({ ...s, notifications: [note, ...s.notifications] }));
  }
  return { sent: targets.length };
}

/** Tugaskan teknisi ke tiket (status tidak berubah); catat di riwayat. */
export async function assignTicket(id, technician) {
  await wait();
  const name = text(technician);
  if (!name) throw new Error("Pilih teknisi");
  if (!getState().care.tickets.some((t) => t.id === id)) throw new Error("Tiket tidak ditemukan");
  const step = (x) => ({ ...x, assignee: name, history: [...x.history, { status: x.status, at: iso(now()), note: `Ditugaskan ke ${name}.` }] });
  setState((s) => ({ ...s, care: { ...s.care, tickets: s.care.tickets.map((x) => (x.id === id ? step(x) : x)) } }));
  return getState().care.tickets.find((x) => x.id === id);
}

/** Kirim pengumuman ke warga (community.announcements) + notifikasi sesuai jenjang. */
export async function postAnnouncement({ title, body, tier = "info" } = {}) {
  await wait();
  const ttl = text(title);
  const msg = text(body);
  if (!ttl) throw new Error("Judul pengumuman belum diisi");
  if (!msg) throw new Error("Isi pengumuman belum diisi");
  if (!TIERS.includes(tier)) throw new Error("Jenjang pengumuman tidak dikenal");
  const at = iso(now());
  const ann = { id: newId("an", now()), title: ttl, body: msg, author: "Pengelola", at, pinned: true, tier };
  setState((s) => ({
    ...s,
    community: { ...s.community, announcements: [ann, ...s.community.announcements] },
    manager: { ...s.manager, announcements: [{ id: ann.id, title: ttl, body: msg, tier, at }, ...(s.manager.announcements || [])] },
    notifications: [notify(tier, ttl, msg, "/app/warga/komunitas"), ...s.notifications],
  }));
  return ann;
}

export async function listVendors() {
  await wait();
  return [...(getState().manager.vendors || [])];
}

/** Aktifkan atau tangguhkan mitra; mitra ditangguhkan disembunyikan dari warga (community.js). */
export async function setVendorStatus(id, status) {
  await wait();
  if (!["aktif", "ditangguhkan"].includes(status)) throw new Error("Status mitra tidak dikenal");
  if (!(getState().manager.vendors || []).some((v) => v.id === id)) throw new Error("Mitra tidak ditemukan");
  patchManager((m) => ({ ...m, vendors: m.vendors.map((v) => (v.id === id ? { ...v, status } : v)) }));
  return getState().manager.vendors.find((v) => v.id === id);
}
