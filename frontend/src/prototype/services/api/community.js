// Komunitas, pasar warga, dan jasa rumah (simulasi, tanpa jaringan).
import { getState, setState, now } from "../store";
import { wait } from "../latency";
import { newId } from "../ids";

export const SERVICE_SLOTS = ["08.00-10.00", "10.00-12.00", "13.00-15.00", "15.00-17.00"];

const byNewest = (a, b) => Date.parse(b) - Date.parse(a);
const patchCommunity = (fn) => setState((s) => ({ ...s, community: fn(s.community) }));
const mapBy = (list, id, fn) => list.map((x) => (x.id === id ? fn(x) : x));

// Produk/jasa milik mitra yang ditangguhkan pengelola tidak tampil bagi warga.
const hiddenIds = (s) => new Set(((s.manager && s.manager.vendors) || []).filter((v) => v.status === "ditangguhkan").flatMap((v) => [...(v.itemIds || []), ...(v.serviceIds || [])]));
const visible = (s, list) => { const h = hiddenIds(s); return list.filter((x) => !h.has(x.id)); };

/** Disematkan dulu, lalu terbaru. */
export async function listAnnouncements() {
  await wait();
  return [...getState().community.announcements].sort((a, b) => Number(b.pinned) - Number(a.pinned) || byNewest(a.at, b.at));
}

export async function listEvents() {
  await wait();
  return [...getState().community.events].sort((a, b) => a.date.localeCompare(b.date));
}

export async function getEvent(id) {
  await wait();
  return getState().community.events.find((e) => e.id === id) || null;
}

function setRsvp(id, on) {
  const ev = getState().community.events.find((e) => e.id === id);
  if (!ev) throw new Error("Acara tidak ditemukan");
  if (Boolean(ev.rsvp) === on) return ev;
  patchCommunity((c) => ({ ...c, events: mapBy(c.events, id, (e) => ({ ...e, rsvp: on, going: Math.max(0, e.going + (on ? 1 : -1)) })) }));
  return getState().community.events.find((e) => e.id === id);
}

/** Ikut acara: jumlah peserta +1 sekali saja (idempoten). */
export async function joinEvent(id) {
  await wait();
  return setRsvp(id, true);
}

export async function leaveEvent(id) {
  await wait();
  return setRsvp(id, false);
}

export async function listGroups() {
  await wait();
  return [...getState().community.groups];
}

export async function joinGroup(id) {
  await wait();
  const g = getState().community.groups.find((x) => x.id === id);
  if (!g) throw new Error("Grup tidak ditemukan");
  if (g.joined) return g;
  patchCommunity((c) => ({ ...c, groups: mapBy(c.groups, id, (x) => ({ ...x, joined: true, members: x.members + 1 })) }));
  return getState().community.groups.find((x) => x.id === id);
}

export async function listPolls() {
  await wait();
  return [...getState().community.polls];
}

/** Satu suara per polling. */
export async function vote(pollId, optionId) {
  await wait();
  const poll = getState().community.polls.find((p) => p.id === pollId);
  if (!poll) throw new Error("Polling tidak ditemukan");
  if (poll.voted) throw new Error("Anda sudah memilih");
  if (!poll.options.some((o) => o.id === optionId)) throw new Error("Pilihan tidak ada");
  patchCommunity((c) => ({
    ...c,
    polls: mapBy(c.polls, pollId, (p) => ({
      ...p,
      voted: optionId,
      options: p.options.map((o) => (o.id === optionId ? { ...o, votes: o.votes + 1 } : o)),
    })),
  }));
  return getState().community.polls.find((p) => p.id === pollId);
}

export async function listProducts() {
  await wait();
  const s = getState();
  return visible(s, s.community.market);
}

/** Tambah ke keranjang; jumlah tidak boleh melebihi stok. */
export async function addToCart(productId, qty = 1) {
  await wait();
  const st = getState();
  const { cart } = st.community;
  const p = visible(st, st.community.market).find((x) => x.id === productId);
  if (!p) throw new Error("Produk tidak ditemukan");
  const n = Math.floor(Number(qty));
  if (!(n >= 1)) throw new Error("Jumlah tidak valid");
  const have = (cart.find((x) => x.productId === productId) || { qty: 0 }).qty;
  if (have + n > p.stock) throw new Error(`Stok ${p.name} tersisa ${p.stock}`);
  patchCommunity((c) => ({
    ...c,
    cart: have ? c.cart.map((x) => (x.productId === productId ? { ...x, qty: x.qty + n } : x)) : [...c.cart, { productId, qty: n }],
  }));
  return getState().community.cart;
}

export async function removeFromCart(productId) {
  await wait();
  patchCommunity((c) => ({ ...c, cart: c.cart.filter((x) => x.productId !== productId) }));
  return getState().community.cart;
}

/** Baris keranjang bergabung dengan data produk. */
export function cartLines(state) {
  const { cart, market } = state.community;
  const shown = visible(state, market); // produk mitra ditangguhkan keluar dari keranjang, total, dan checkout
  return cart.map((l) => ({ ...l, product: shown.find((m) => m.id === l.productId) })).filter((l) => l.product);
}

export function cartTotal(state) {
  return cartLines(state).reduce((sum, l) => sum + l.product.price * l.qty, 0);
}

/** Buat pesanan (belum dibayar) lalu kembalikan target pembayaran. Keranjang dikosongkan setelah lunas. */
export async function checkout() {
  await wait();
  const st = getState();
  const lines = cartLines(st);
  if (!lines.length) throw new Error("Keranjang masih kosong");
  const amount = cartTotal(st);
  const count = lines.reduce((n, l) => n + l.qty, 0);
  const order = {
    id: newId("ord", now()),
    items: lines.map((l) => ({ productId: l.productId, name: l.product.name, seller: l.product.seller, price: l.product.price, qty: l.qty })),
    amount,
    title: `Pesanan pasar warga · ${count} barang`,
    status: "unpaid",
    createdAt: new Date(now()).toISOString(),
  };
  patchCommunity((c) => ({ ...c, orders: [order, ...c.orders] }));
  return { targetType: "market", targetId: order.id, amount, title: order.title };
}

/** Dipanggil setelah pembayaran pasar lunas: kosongkan keranjang dan kurangi stok. */
export async function completeOrder(orderId) {
  await wait();
  const order = getState().community.orders.find((o) => o.id === orderId);
  if (!order) throw new Error("Pesanan tidak ditemukan");
  patchCommunity((c) => ({
    ...c,
    cart: [],
    market: c.market.map((m) => {
      const it = order.items.find((i) => i.productId === m.id);
      return it ? { ...m, stock: Math.max(0, m.stock - it.qty) } : m;
    }),
  }));
  return order;
}

export async function listServices() {
  await wait();
  const s = getState();
  return visible(s, s.community.services);
}

export async function listBookings() {
  await wait();
  return [...getState().community.bookings];
}

/** Pesan jasa: wajib pilih jam kedatangan. */
export async function bookService({ serviceId, date, slot, note = "" }) {
  await wait();
  const st = getState();
  const sv = visible(st, st.community.services).find((x) => x.id === serviceId);
  if (!sv) throw new Error("Jasa tidak ditemukan");
  if (!slot) throw new Error("Pilih jam kedatangan");
  if (!date) throw new Error("Pilih tanggal kunjungan");
  const booking = {
    id: newId("bk", now()), serviceId, serviceName: sv.name, provider: sv.provider, date, slot,
    note: String(note || "").trim(), status: "dijadwalkan", createdAt: new Date(now()).toISOString(),
  };
  patchCommunity((c) => ({ ...c, bookings: [booking, ...(c.bookings || [])] }));
  return booking;
}
