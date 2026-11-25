// Tagihan, kuitansi, laporan kas, dan isi ulang (PPOB simulasi — tanpa jaringan).
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";

const digitsOf = (v) => String(v == null ? "" : v).replace(/\D/g, "");
const byNewest = (a, b) => Date.parse(b) - Date.parse(a);

/** Tagihan IPL + air: belum lunas dulu, lalu yang terbaru. */
export async function listBills() {
  await wait();
  const { bills } = getState();
  return [...bills.ipl, ...bills.air].sort(
    (a, b) => Number(a.status === "paid") - Number(b.status === "paid") || byNewest(a.dueDate, b.dueDate)
  );
}

/** Semua kuitansi (tagihan, isi ulang, dan cicilan rumah), terbaru dulu. */
export async function listReceipts() {
  await wait();
  return [...getState().bills.receipts].sort((a, b) => byNewest(a.paidAt, b.paidAt));
}

/** Laporan kas kawasan: saldo per bulan = saldo sebelumnya + masuk − keluar. */
export async function getCashReport() {
  await wait();
  const { cashReport, cashOpening = 0 } = getState().bills;
  let balance = cashOpening;
  const months = cashReport.map((m) => {
    balance += m.in - m.out;
    return { ...m, balance };
  });
  return { opening: cashOpening, months };
}

const PRODUCTS = {
  pulsa: { key: "pulsa", noun: "Pulsa", field: "Nomor HP", min: 10, max: 13, err: "Nomor HP belum valid" },
  data: { key: "data", noun: "Paket data", field: "Nomor HP", min: 10, max: 13, err: "Nomor HP belum valid" },
  pln: { key: "listrik", noun: "Token PLN", field: "Nomor meter", min: 11, max: 12, err: "Nomor meter belum valid" },
  pdam: { key: "pdam", noun: "Air PDAM", field: "Nomor pelanggan", min: 8, max: 12, err: "Nomor pelanggan belum valid" },
};

/** {pulsa, data, pln, pdam}: masing-masing {label, field, options[{id,label,nominal,price}]}. */
export async function getTopUpCatalog() {
  await wait();
  const cat = getState().bills.ppobCatalog;
  const out = {};
  Object.entries(PRODUCTS).forEach(([id, p]) => {
    const c = cat.find((x) => x.id === p.key);
    out[id] = { id, label: c.label, field: p.field, options: c.options };
  });
  return out;
}

/** Buat transaksi isi ulang (belum dibayar) lalu kembalikan target untuk PayFlow. */
export async function createTopUp({ product, target, nominal }) {
  await wait();
  const p = PRODUCTS[product];
  if (!p) throw new Error("Produk tidak dikenal");
  const no = digitsOf(target);
  if (no.length < p.min || no.length > p.max) throw new Error(p.err);
  const option = getState().bills.ppobCatalog.find((x) => x.id === p.key).options.find((o) => o.nominal === Number(nominal));
  if (!option) throw new Error("Nominal belum dipilih");
  const title = `${option.label} · ${no}`;
  const tx = { id: newId("ppob", now()), product, target: no, label: option.label, nominal: option.nominal, amount: option.price, title, status: "unpaid", createdAt: new Date(now()).toISOString() };
  setState((s) => ({ ...s, bills: { ...s.bills, ppobTx: [tx, ...s.bills.ppobTx] } }));
  return { targetType: "ppob", targetId: tx.id, amount: tx.amount, title };
}

// Token PLN contoh: 20 digit deterministik dari id transaksi (hash FNV sederhana).
function tokenFor(id) {
  let h = 2166136261;
  let out = "";
  for (let i = 0; out.length < 20; i += 1) {
    h = Math.imul(h ^ id.charCodeAt(i % id.length), 16777619) >>> 0;
    out += String(h % 100000).padStart(5, "0");
  }
  return out.slice(0, 20).match(/.{4}/g).join("-");
}

/** Hasil isi ulang. Token PLN hanya ada setelah lunas. */
export function topUpResult(txId) {
  const { ppobTx, receipts } = getState().bills;
  const tx = ppobTx.find((x) => x.id === txId);
  if (!tx) throw new Error("Transaksi tidak ditemukan");
  const paid = tx.status === "paid";
  const struk = {
    id: tx.id, product: tx.product, label: tx.label, target: tx.target, nominal: tx.nominal, amount: tx.amount,
    status: tx.status, paidAt: tx.paidAt, receipt: receipts.find((r) => r.id === tx.receiptId) || null,
  };
  return paid && tx.product === "pln" ? { token: tokenFor(tx.id), struk } : { struk };
}
