// Pembayaran generik (simulasi): satu pintu untuk cicilan, IPL, isi ulang, dan pasar warga.
// Tidak ada jaringan; kode VA/QRIS dibuat acak secara lokal.
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { rupiah } from "../../lib/format";

const DAY = 86400000;
const iso = (t) => new Date(t).toISOString();

/** Metode bayar. `prefix` = awalan nomor VA contoh per bank (+ 12 digit acak). */
export const PAY_METHODS = [
  { id: "va_bri", label: "VA BRI", kind: "va", bank: "BRI", prefix: "8800" },
  { id: "va_bni", label: "VA BNI", kind: "va", bank: "BNI", prefix: "8277" },
  { id: "va_mandiri", label: "VA Mandiri", kind: "va", bank: "Mandiri", prefix: "8908" },
  { id: "va_btn", label: "VA BTN", kind: "va", bank: "BTN", prefix: "9001" },
  { id: "va_permata", label: "VA Permata", kind: "va", bank: "Permata", prefix: "8528" },
  { id: "qris", label: "QRIS", kind: "qris" },
  { id: "ewallet", label: "Dompet digital", kind: "ewallet" },
  { id: "wa_link", label: "Kirim link bayar ke WhatsApp", kind: "wa_link" },
];

export const methodLabel = (id) => (PAY_METHODS.find((m) => m.id === id) || { label: id }).label;

// targetType -> letak daftar tagihan di state.
const TARGETS = {
  installment: ["buyer", "installments"],
  bill: ["bills", "ipl"],
  ppob: ["bills", "ppobTx"],
  market: ["community", "orders"],
};

const digits = (n) => Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join("");
let seq = 0;
const newId = (p) => `${p}-${now().toString(36)}-${(seq += 1).toString(36)}${digits(3)}`;

function listOf(state, targetType) {
  const path = TARGETS[targetType];
  if (!path) return null;
  return (state[path[0]] && state[path[0]][path[1]]) || [];
}

function findTarget(state, targetType, targetId) {
  const list = listOf(state, targetType);
  return list ? list.find((x) => x.id === targetId) || null : null;
}

function patchTarget(state, targetType, targetId, patch) {
  const [a, b] = TARGETS[targetType];
  const list = state[a][b].map((x) => (x.id === targetId ? { ...x, ...patch } : x));
  return { ...state, [a]: { ...state[a], [b]: list } };
}

function makeCode(method, { title, amount }) {
  if (method.kind === "va") return method.prefix + digits(12);
  if (method.kind === "qris") return `QR${digits(14)}`;
  if (method.kind === "ewallet") return digits(12);
  const text = `Halo, mohon bantu bayar ${title} sebesar ${rupiah(amount)}. Kode bayar: ${digits(12)}.`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

/**
 * Buat pembayaran untuk satu tagihan.
 * @returns {Promise<Payment>} {id, targetType, targetId, title, method, amount, code, expiresAt, status:'pending'}
 * Target ditandai `status: 'pending'` (menunggu pembayaran) sampai dikonfirmasi.
 */
export async function startPayment({ targetType, targetId, amount, title }, methodId) {
  await wait();
  const method = PAY_METHODS.find((m) => m.id === methodId);
  if (!method) throw new Error("Metode bayar tidak dikenal");
  // Baca-periksa-tulis tanpa await di antaranya agar tidak ada balapan.
  const target = findTarget(getState(), targetType, targetId);
  if (!target) throw new Error("Tagihan tidak ditemukan");
  if (target.status === "paid") throw new Error("Tagihan ini sudah lunas");
  if (!(Number(amount) > 0)) throw new Error("Nominal tidak valid");

  const t = now();
  const payment = {
    id: newId("pay"),
    targetType,
    targetId,
    title,
    method: method.id,
    amount: Number(amount),
    code: makeCode(method, { title, amount }),
    createdAt: iso(t),
    expiresAt: iso(t + DAY),
    status: "pending",
  };
  setState((s) => {
    const next = { ...s, bills: { ...s.bills, payments: [payment, ...s.bills.payments] } };
    return patchTarget(next, targetType, targetId, { status: "pending" });
  });
  return payment;
}

/**
 * Tandai pembayaran lunas dan terbitkan kuitansi di `bills.receipts`.
 * Idempoten: pembayaran yang sudah lunas mengembalikan kuitansi yang sama tanpa membuat baru.
 * @returns {Promise<{payment: Payment, receipt: Receipt}>}
 */
export async function confirmPayment(paymentId) {
  await wait();
  const state = getState();
  const payment = state.bills.payments.find((p) => p.id === paymentId);
  if (!payment) throw new Error("Pembayaran tidak ditemukan");
  if (payment.status === "paid") {
    return { payment, receipt: state.bills.receipts.find((r) => r.id === payment.receiptId) };
  }
  const target = findTarget(state, payment.targetType, payment.targetId);
  if (!target) throw new Error("Tagihan tidak ditemukan");
  if (target.status === "paid") throw new Error("Tagihan ini sudah lunas");

  const paidAt = iso(now());
  const receipt = {
    id: newId("rc"),
    targetType: payment.targetType,
    targetId: payment.targetId,
    title: payment.title,
    amount: payment.amount,
    method: payment.method,
    paidAt,
    paymentId: payment.id,
  };
  const paid = { ...payment, status: "paid", paidAt, receiptId: receipt.id };
  setState((s) => {
    const payments = s.bills.payments.map((p) => (p.id === paid.id ? paid : p));
    // Pengingat jatuh tempo untuk tagihan ini (`about`) tidak relevan lagi setelah lunas.
    const notifications = s.notifications.map((n) => (n.about === paid.targetId && !n.read ? { ...n, read: true } : n));
    const next = { ...s, notifications, bills: { ...s.bills, payments, receipts: [receipt, ...s.bills.receipts] } };
    return patchTarget(next, paid.targetType, paid.targetId, { status: "paid", paidAt, receiptId: receipt.id });
  });
  return { payment: paid, receipt };
}
