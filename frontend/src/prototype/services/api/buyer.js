import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { insertTicket } from "./tickets";

const iso = (t) => new Date(t).toISOString();
const STATUSES = ["tersedia", "dipesan", "terjual", "milik-anda"];

// Siteplan contoh: 5 blok (A–E) × 6 kavling. Status tetap (data contoh) kecuali C-12.
const BLOCK_ROWS = ["A", "B", "C", "D", "E"];
const PER_BLOCK = 12;
const TAKEN = new Set(["A-03", "A-07", "A-11", "B-02", "B-05", "B-09", "C-01", "C-04", "C-08", "C-15", "D-02", "D-06", "E-01", "E-05"]);
const RESERVED = new Set(["A-05", "B-07", "C-06", "D-04", "E-03", "E-08"]);

function buildPlots(neighborBlocks) {
  const plots = [];
  BLOCK_ROWS.forEach((b, row) => {
    for (let n = 1; n <= PER_BLOCK; n += 1) {
      const id = `${b}-${String(n).padStart(2, "0")}`;
      let status = "tersedia";
      if (id === "C-12") status = "milik-anda";
      else if (TAKEN.has(id) || neighborBlocks.has(id)) status = "terjual";
      else if (RESERVED.has(id)) status = "dipesan";
      plots.push({ id, block: b, number: n, row, col: n - 1, status });
    }
  });
  return plots;
}

const nextOf = (installments) => installments.find((i) => i.status !== "paid") || null;

/** Data Beranda pembeli. */
export async function getBuyerHome() {
  await wait();
  const { buyer } = getState();
  const photos = buyer.progressPhotos;
  return {
    journey: buyer.journey,
    nextInstallment: nextOf(buyer.installments),
    progress: { percent: buyer.journey.progress, stage: buyer.journey.steps[buyer.journey.current] },
    latestPhoto: photos[photos.length - 1] || null,
    promos: buyer.promos,
  };
}

export async function listInstallments() {
  await wait();
  const { buyer, bills } = getState();
  return buyer.installments.map((i) => ({
    ...i,
    receipt: i.receiptId ? bills.receipts.find((r) => r.id === i.receiptId) || null : null,
  }));
}

export async function getProgress() {
  await wait();
  const { buyer } = getState();
  const est = new Date(now());
  est.setMonth(est.getMonth() + 3);
  return {
    percent: buyer.journey.progress,
    stage: buyer.journey.steps[buyer.journey.current],
    photos: buyer.progressPhotos,
    handoverEstimate: new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(est),
  };
}

export async function getPlotMap() {
  await wait();
  const { world } = getState();
  const nb = new Set(world.neighbors.map((n) => n.block));
  return { project: world.project.name, unit: world.unit.block, plots: buildPlots(nb), statuses: STATUSES };
}

export async function getKpr() {
  await wait();
  const { buyer } = getState();
  return { ...buyer.kpr, totalMonths: buyer.kpr.tenorYears * 12 };
}

const CANCEL_RULES = [
  "Pembatalan sebelum akad KPR: biaya booking tidak dikembalikan, uang muka yang sudah dibayar dikembalikan setelah dipotong biaya administrasi sesuai PPJB.",
  "Pembatalan karena KPR ditolak bank: uang muka dikembalikan penuh dalam 30 hari kerja.",
  "Pengajuan pembatalan dilakukan lewat pemasaran proyek; layar ini hanya menampilkan status dan aturan.",
];

export async function getCancellation() {
  await wait();
  const { buyer } = getState();
  return { status: "none", message: "Tidak ada pengajuan pembatalan.", rules: CANCEL_RULES, record: buyer.cancellation };
}

export async function listDocuments() {
  await wait();
  const { buyer, bills } = getState();
  return {
    files: buyer.documents,
    contracts: [
      { id: "ct-ppjb", title: "Perjanjian pengikatan jual beli (PPJB)", status: "menunggu akad" },
      { id: "ct-bast", title: "Berita acara serah terima (BAST)", status: "menunggu rumah siap" },
    ],
    receipts: bills.receipts.filter((r) => r.targetType === "installment"),
  };
}

export async function getReferral() {
  await wait();
  const { buyer } = getState();
  return { ...buyer.referral, reward: "Poin 500 per teman yang booking" };
}

export async function inviteFriend({ name, phone }) {
  await wait();
  const digits = String(phone || "").replace(/\D/g, "");
  if (!String(name || "").trim()) throw new Error("Nama teman belum diisi");
  if (digits.length < 10) throw new Error("Nomor WhatsApp belum lengkap");
  const t = now();
  const entry = { id: `inv-${t}`, name: String(name).trim(), phone: digits, status: "diundang", at: iso(t) };
  setState((s) => ({ ...s, buyer: { ...s.buyer, referral: { ...s.buyer.referral, invited: [entry, ...s.buyer.referral.invited] } } }));
  return getReferral();
}

export async function listQuestions() {
  await wait();
  return getState().care.tickets.filter((t) => t.kind === "tanya");
}

export async function askQuestion({ category, description }) {
  await wait();
  if (!String(description || "").trim()) throw new Error("Tulis pertanyaan atau keluhan Anda");
  return insertTicket({ kind: "tanya", category: category || "Umum", description });
}
