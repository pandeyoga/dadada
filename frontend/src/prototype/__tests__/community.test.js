import React from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { startPayment, confirmPayment } from "@/prototype/services/api/payments";
import {
  listAnnouncements, listEvents, getEvent, joinEvent, leaveEvent, listGroups, joinGroup, listPolls, vote,
  listProducts, addToCart, removeFromCart, cartTotal, checkout, listServices, bookService,
} from "@/prototype/services/api/community";

const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
});
afterAll(() => setLatency(null));

test("pengumuman: yang disematkan lebih dulu", async () => {
  const list = await listAnnouncements();
  expect(list[0].pinned).toBe(true);
  expect(list.length).toBeGreaterThan(1);
});

test("joinEvent menaikkan peserta 1 dan idempoten; leaveEvent membatalkan", async () => {
  const before = (await getEvent("ev-1")).going;
  await joinEvent("ev-1");
  await joinEvent("ev-1");
  const ev = await getEvent("ev-1");
  expect(ev.going).toBe(before + 1);
  expect(ev.rsvp).toBe(true);
  await leaveEvent("ev-1");
  await leaveEvent("ev-1");
  expect(await getEvent("ev-1")).toMatchObject({ going: before, rsvp: false });
  expect(await getEvent("nope")).toBeNull();
  expect((await listEvents()).length).toBeGreaterThan(0);
});

test("joinGroup idempoten", async () => {
  const before = (await listGroups()).find((g) => g.id === "gr-3").members;
  await joinGroup("gr-3");
  await joinGroup("gr-3");
  expect((await listGroups()).find((g) => g.id === "gr-3")).toMatchObject({ joined: true, members: before + 1 });
});

test("vote: suara kedua melempar pesan persis", async () => {
  const [poll] = await listPolls();
  const votes = poll.options[0].votes;
  await vote(poll.id, poll.options[0].id);
  const [after] = await listPolls();
  expect(after.voted).toBe(poll.options[0].id);
  expect(after.options[0].votes).toBe(votes + 1);
  await expect(vote(poll.id, poll.options[1].id)).rejects.toThrow("Anda sudah memilih");
});

test("keranjang: total = jumlah harga, hapus, batas stok", async () => {
  const [a, b] = await listProducts();
  await addToCart(a.id);
  await addToCart(b.id, 2);
  expect(cartTotal(getState())).toBe(a.price + 2 * b.price);
  await removeFromCart(a.id);
  expect(cartTotal(getState())).toBe(2 * b.price);
  await expect(addToCart(b.id, b.stock)).rejects.toThrow(/Stok/);
});

test("checkout: keranjang kosong melempar; berisi membuat pesanan lalu bisa dibayar", async () => {
  await expect(checkout()).rejects.toThrow("Keranjang masih kosong");
  const [a, b] = await listProducts();
  await addToCart(a.id);
  await addToCart(b.id);
  const target = await checkout();
  expect(target).toMatchObject({ targetType: "market", amount: a.price + b.price });
  expect(getState().community.orders[0]).toMatchObject({ id: target.targetId, status: "unpaid" });
  const p = await startPayment(target, "qris");
  await confirmPayment(p.id);
  expect(getState().community.orders[0].status).toBe("paid");
});

test("bookService: tanpa slot melempar; dengan slot tersimpan", async () => {
  const names = (await listServices()).map((s) => s.name).join("|");
  ["Tukang", "Kebersihan", "galon", "Servis AC", "Sedot WC", "taman"].forEach((k) => expect(names).toMatch(new RegExp(k, "i")));
  await expect(bookService({ serviceId: "sv-1", date: "2026-12-01", note: "" })).rejects.toThrow("Pilih jam kedatangan");
  const bk = await bookService({ serviceId: "sv-1", date: "2026-12-01", slot: "08.00-10.00", note: "AC kamar" });
  expect(getState().community.bookings[0]).toMatchObject({ id: bk.id, serviceName: "Servis AC", slot: "08.00-10.00" });
});

describe("layar", () => {
  test("W14: tab berpindah", async () => {
    mount("/app/warga/komunitas");
    await screen.findByText("Penyemprotan nyamuk (fogging)");
    fireEvent.click(screen.getByRole("tab", { name: "Agenda" }));
    await screen.findByText("Kerja bakti Minggu, 7 Des");
    fireEvent.click(screen.getByRole("tab", { name: "Hobi" }));
    await screen.findByText("Ibu-ibu Estora");
    fireEvent.click(screen.getByRole("tab", { name: "Polling" }));
    await screen.findByText(/Jam ronda malam/);
  });

  test("W15: RSVP menambah dan mengurangi hitungan", async () => {
    mount("/app/warga/komunitas/event/ev-1");
    await screen.findByText(/14 warga ikut/);
    fireEvent.click(screen.getByRole("button", { name: /Saya ikut/ }));
    await screen.findByText(/15 warga ikut/);
    fireEvent.click(screen.getByRole("button", { name: /Batal ikut/ }));
    await screen.findByText(/14 warga ikut/);
  });

  test("W15: id tidak dikenal menampilkan EmptyState", async () => {
    mount("/app/warga/komunitas/event/xxx");
    await screen.findByText("Acara tidak ditemukan");
  });

  test("W17: pilih opsi menampilkan hasil dan mengunci pilihan", async () => {
    mount("/app/warga/komunitas/polling");
    const card = (await screen.findByText(/Jam ronda malam/)).closest("section");
    fireEvent.click(within(card).getByRole("button", { name: /22\.00/ }));
    await within(card).findByText("Terima kasih, suara Anda tercatat.");
    expect(within(card).getAllByRole("progressbar").length).toBe(3);
    expect(within(card).queryByRole("button", { name: /23\.00/ })).toBeNull();
  });

  test("W18: dua produk -> keranjang -> bayar -> pesanan lunas dan keranjang kosong", async () => {
    mount("/app/warga/pasar");
    await screen.findByText("Nasi kuning komplit");
    fireEvent.click(screen.getByRole("button", { name: /Tambah Nasi kuning komplit/ }));
    await waitFor(() => expect(getState().community.cart.length).toBe(1));
    fireEvent.click(screen.getByRole("button", { name: /Tambah Kue brownies kukus/ }));
    await waitFor(() => expect(getState().community.cart.length).toBe(2));
    fireEvent.click(screen.getByRole("button", { name: /Keranjang/ }));
    const dlg = await screen.findByRole("dialog");
    expect(within(dlg).getByTestId("cart-total").textContent).toMatch(/50\.000/);
    fireEvent.click(within(dlg).getByRole("button", { name: /Bayar/ }));
    fireEvent.click(await screen.findByRole("button", { name: /BRI/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Saya sudah bayar/ }));
    await screen.findByText("Pembayaran berhasil");
    fireEvent.click(screen.getByRole("button", { name: "Selesai" }));
    await waitFor(() => expect(getState().community.orders[0].status).toBe("paid"));
    await waitFor(() => expect(getState().community.cart).toEqual([]));
  });

  test("W19: pesan tanpa jam menampilkan galat; dengan jam muncul di Pesanan jasa saya", async () => {
    mount("/app/warga/jasa");
    await screen.findByText("Servis AC");
    fireEvent.click(screen.getByRole("button", { name: /Pesan Servis AC/ }));
    const dlg = await screen.findByRole("dialog");
    fireEvent.change(within(dlg).getByLabelText("Tanggal"), { target: { value: "2026-12-02" } });
    fireEvent.click(within(dlg).getByRole("button", { name: "Pesan jadwal" }));
    await within(dlg).findByText("Pilih jam kedatangan");
    fireEvent.click(within(dlg).getByRole("button", { name: "10.00-12.00" }));
    fireEvent.click(within(dlg).getByRole("button", { name: "Pesan jadwal" }));
    const sec = (await screen.findByText("Pesanan jasa saya")).closest("section");
    await within(sec).findByText(/Servis AC/);
  });
});

test("menu bawah: Komunitas aktif di pasar/jasa, Tagihan aktif di isi ulang", async () => {
  const { unmount } = mount("/app/warga/pasar");
  await screen.findByText("Nasi kuning komplit");
  expect(screen.getByRole("link", { name: "Komunitas" }).className).toMatch(/is-active/);
  unmount();
  mount("/app/warga/isi-ulang");
  await waitFor(() => expect(screen.getByRole("link", { name: "Tagihan" }).className).toMatch(/is-active/));
  expect(screen.getByRole("link", { name: "Komunitas" }).className).not.toMatch(/is-active/);
});

test("W18: grid memuat produk warga dan tenant; filter bekerja", async () => {
  mount("/app/warga/pasar");
  await screen.findByText("Nasi kuning komplit");
  expect(screen.getByText("Beras premium 5 kg")).toBeTruthy();
  expect(screen.getAllByText("Tenant").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "Tenant" }));
  expect(screen.queryByText("Nasi kuning komplit")).toBeNull();
  expect(screen.getByText("Kopi susu gula aren")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Warga" }));
  expect(screen.queryByText("Beras premium 5 kg")).toBeNull();
  expect(screen.getByText("Nasi kuning komplit")).toBeTruthy();
});
