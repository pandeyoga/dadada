// Portal mitra/agen: daftar, beranda, katalog beratribusi, simulasi KPR, rujukan, komisi (simulasi, tanpa jaringan).
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";
import { formatPhone } from "./resident";

export const STAGES = [["lead", "Calon"], ["booking", "Booking"], ["akad", "Akad"]];
const FALLBACK_BOARD = [
  { name: "Budi Santoso", listings: 14 }, { name: "Wulan Pertiwi", listings: 11 }, { name: "Dimas Pratama", listings: 8 },
  { name: "Hendra Gunawan", listings: 6 }, { name: "Siti Rahmawati", listings: 4 },
];
const text = (v) => String(v == null ? "" : v).trim();
const digits = (v) => text(v).replace(/\D/g, "");
const sum = (list) => list.reduce((n, x) => n + x.amount, 0);
const partnerOf = (s) => ({ payouts: [], commissions: [], referrals: [], catalog: [], ...s.partner });
const patch = (fn) => setState((s) => ({ ...s, partner: fn(partnerOf(s)) }));

/** Saldo yang bisa dicairkan = komisi cair dikurangi semua pencairan yang sudah diajukan. */
export const balanceOf = (p) => sum(p.commissions.filter((c) => c.status === "cair")) - sum(p.payouts);

export function checkAccount(a = {}) {
  if (digits(formatPhone(a.phone)).length < 10) throw new Error("Nomor WhatsApp belum valid");
  if (text(a.password).length < 6) throw new Error("Kata sandi minimal 6 karakter");
}
export function checkPersonal(p = {}) {
  if (text(p.name).length < 3) throw new Error("Nama lengkap belum diisi");
  if (!text(p.city)) throw new Error("Kota domisili belum diisi");
}
export function checkBank(b = {}) {
  if (!text(b.bankName)) throw new Error("Pilih nama bank");
  if (digits(b.accountNumber).length < 8 || digits(b.accountNumber).length > 16) throw new Error("Nomor rekening belum valid");
  if (text(b.holder).length < 3) throw new Error("Nama pemilik rekening belum diisi");
}

/** Daftar mitra; kata sandi hanya diperiksa, tidak disimpan. */
export async function registerPartner({ account, personal, bank, social } = {}) {
  await wait();
  checkBank(bank);
  checkAccount(account);
  checkPersonal(personal);
  patch((p) => ({
    ...p,
    registered: true,
    profile: {
      ...p.profile,
      name: text(personal.name),
      phone: formatPhone(account.phone),
      city: text(personal.city),
      bank: { bankName: text(bank.bankName), accountNumber: digits(bank.accountNumber), holder: text(bank.holder) },
      social: { instagram: text(social && social.instagram), tiktok: text(social && social.tiktok), facebook: text(social && social.facebook) },
    },
  }));
  return getState().partner.profile;
}

/** Beranda: poin, komisi diproses, peringkat dan papan peringkat (Dimas dihitung dari data). */
export async function getPartnerHome() {
  await wait();
  const p = partnerOf(getState());
  const board = (p.leaderboard && p.leaderboard.length ? p.leaderboard : FALLBACK_BOARD)
    .slice().sort((a, b) => b.listings - a.listings)
    .map((x, i) => ({ name: x.name, listings: x.listings, rank: i + 1 }));
  const me = board.find((x) => x.name === p.profile.name);
  return {
    points: p.points,
    commissionPending: sum(p.commissions.filter((c) => c.status === "diproses")),
    rank: me ? me.rank : board.length + 1,
    leaderboard: board,
    registered: !!p.registered,
    profile: p.profile,
  };
}

export async function listCatalog() {
  await wait();
  return partnerOf(getState()).catalog;
}

/** Tautan berbagi beratribusi; hanya untuk ditampilkan/disalin (tidak pernah dibuka). */
export function shareLink(unitId, state = getState()) {
  const p = partnerOf(state);
  const unit = p.catalog.find((u) => u.id === unitId);
  if (!unit) throw new Error("Unit tidak ditemukan");
  const url = `https://estora.id/u/${encodeURIComponent(unit.id)}?ref=${encodeURIComponent(p.profile.code)}&unit=${encodeURIComponent(unit.id)}`;
  return { url, qrText: url };
}

/** Simulasi angsuran anuitas, dibulatkan ke Rp500 terdekat. Simulasi, bukan penawaran bank. */
export function simulateKpr({ price, dp, tenorYears, rate } = {}) {
  const harga = Number(price);
  const uang = Number(dp);
  const tenor = Number(tenorYears);
  const bunga = Number(rate);
  if (!(harga > 0)) throw new Error("Harga belum valid");
  if (!(uang >= 0) || uang >= harga) throw new Error("Uang muka harus lebih kecil dari harga");
  if (!(tenor >= 5 && tenor <= 30)) throw new Error("Tenor harus 5 sampai 30 tahun");
  if (!(bunga > 0)) throw new Error("Bunga harus lebih dari 0");
  const principal = harga - uang;
  const r = bunga / 100 / 12;
  const n = tenor * 12;
  const exact = (principal * r) / (1 - Math.pow(1 + r, -n));
  return { monthly: Math.round(exact / 500) * 500, principal, months: n };
}

/** Rujukan per tahap: [{stage, label, count, items}] urut lead → booking → akad. */
export async function listReferrals() {
  await wait();
  const list = partnerOf(getState()).referrals;
  return STAGES.map(([stage, label]) => {
    const items = list.filter((r) => r.stage === stage);
    return { stage, label, count: items.length, items };
  });
}

/** Ringkasan komisi: saldo bisa dicairkan, sedang diproses, riwayat komisi dan pencairan. */
export async function getCommission() {
  await wait();
  const p = partnerOf(getState());
  const byDate = (a, b) => Date.parse(b.at) - Date.parse(a.at);
  return {
    balance: balanceOf(p),
    pending: sum(p.commissions.filter((c) => c.status === "diproses")),
    commissions: p.commissions.slice().sort(byDate),
    payouts: p.payouts.slice().sort(byDate),
    bank: p.profile.bank || null,
  };
}

export async function requestPayout(amount) {
  await wait();
  const n = Number(amount);
  if (!Number.isInteger(n) || n <= 0) throw new Error("Nominal pencairan tidak valid");
  if (n > balanceOf(partnerOf(getState()))) throw new Error("Saldo komisi tidak cukup");
  const payout = { id: newId("po", now()), amount: n, status: "diproses", at: new Date(now()).toISOString() };
  patch((p) => ({ ...p, payouts: [payout, ...p.payouts] }));
  return payout;
}
