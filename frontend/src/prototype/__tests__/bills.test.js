import React from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { rupiah } from "@/prototype/lib/format";
import { setLatency } from "@/prototype/services/latency";
import { startPayment, confirmPayment } from "@/prototype/services/api/payments";
import { getResidentHome } from "@/prototype/services/api/resident";
import { listBills, listReceipts, getCashReport, getTopUpCatalog, createTopUp, topUpResult } from "@/prototype/services/api/bills";
import { issueIplBills } from "@/prototype/services/api/manager";

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

async function payTarget(target, method = "va_bri") {
  const p = await startPayment(target, method);
  return confirmPayment(p.id);
}

test("listBills: IPL Desember belum lunas ada di urutan pertama", async () => {
  const bills = await listBills();
  expect(bills[0]).toMatchObject({ id: "ipl-2026-12", status: "unpaid", amount: 150000 });
  expect(bills.slice(1).every((b) => b.status === "paid")).toBe(true);
});

test("tagihan Januari baru terbit: Desember (terlama) tetap ditagih lebih dulu di W1 dan W10", async () => {
  await issueIplBills("2027-01");
  const bills = await listBills();
  expect(bills.slice(0, 2).map((b) => b.id)).toEqual(["ipl-2026-12", "ipl-2027-01"]);
  expect(bills.slice(2).every((b) => b.status === "paid")).toBe(true);
  expect(bills.slice(2).map((b) => b.id)).toEqual(["ipl-2026-11", "ipl-2026-10", "ipl-2026-09"]);
  expect((await getResidentHome()).iplDue.id).toBe("ipl-2026-12");
});

test("bayar IPL: lunas, kuitansi bertambah 1, bayar ulang ditolak, W1 tidak menagih lagi", async () => {
  const before = (await listReceipts()).length;
  expect((await getResidentHome()).iplDue.id).toBe("ipl-2026-12");
  const [b] = await listBills();
  await payTarget({ targetType: "bill", targetId: b.id, amount: b.amount, title: `IPL ${b.period}` });
  expect((await listBills()).find((x) => x.id === b.id).status).toBe("paid");
  expect((await listReceipts()).length).toBe(before + 1);
  expect((await getResidentHome()).iplDue).toBeNull();
  await expect(startPayment({ targetType: "bill", targetId: b.id, amount: b.amount, title: "x" }, "qris")).rejects.toThrow("Tagihan ini sudah lunas");
});

test("listReceipts: terbaru dulu, memuat kuitansi tagihan dan cicilan rumah", async () => {
  const r = await listReceipts();
  expect(r.map((x) => Date.parse(x.paidAt))).toEqual([...r.map((x) => Date.parse(x.paidAt))].sort((a, b) => b - a));
  expect(new Set(r.map((x) => x.targetType))).toEqual(new Set(["bill", "installment"]));
});

test("getCashReport: 6 bulan, saldo = saldo sebelumnya + masuk - keluar", async () => {
  const { months, opening } = await getCashReport();
  expect(months).toHaveLength(6);
  let bal = opening;
  months.forEach((m) => {
    bal += m.in - m.out;
    expect(m.balance).toBe(bal);
    expect(m.items.length).toBeGreaterThan(0);
  });
});

test("getTopUpCatalog: pulsa, data, pln, pdam punya pilihan", async () => {
  const c = await getTopUpCatalog();
  ["pulsa", "data", "pln", "pdam"].forEach((k) => expect(c[k].options.length).toBeGreaterThan(0));
});

test("createTopUp: validasi nomor", async () => {
  await expect(createTopUp({ product: "pln", target: "1234", nominal: 50000 })).rejects.toThrow("Nomor meter belum valid");
  await expect(createTopUp({ product: "pulsa", target: "0812", nominal: 25000 })).rejects.toThrow("Nomor HP belum valid");
  await expect(createTopUp({ product: "pdam", target: "12", nominal: 87500 })).rejects.toThrow("Nomor pelanggan belum valid");
  await expect(createTopUp({ product: "pln", target: "12345678901", nominal: 12345 })).rejects.toThrow("Nominal belum dipilih");
  expect(getState().bills.ppobTx).toHaveLength(0);
});

test("PLN: token 20 digit dikelompokkan 4 hanya setelah lunas", async () => {
  const t = await createTopUp({ product: "pln", target: "12345678901", nominal: 50000 });
  expect(t).toMatchObject({ targetType: "ppob", amount: 52500 });
  expect(topUpResult(t.targetId).token).toBeUndefined();
  await payTarget(t);
  const r = topUpResult(t.targetId);
  expect(r.token).toMatch(/^(\d{4}-){4}\d{4}$/);
  expect(r.struk).toMatchObject({ target: "12345678901", status: "paid" });
  expect(topUpResult(t.targetId).token).toBe(r.token);
  expect((await listReceipts())[0]).toMatchObject({ targetType: "ppob" });
});

test("W10: bayar IPL Desember (ada opsi WhatsApp) berujung Lunas + kuitansi", async () => {
  mount("/app/warga/tagihan");
  await screen.findByText("Jatuh tempo 10 Des 2026");
  fireEvent.click(await screen.findByRole("button", { name: /Bayar sekarang/ }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByRole("button", { name: /WhatsApp/ })).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: /BRI/ }));
  fireEvent.click(await within(dialog).findByRole("button", { name: /Saya sudah bayar/ }));
  await within(dialog).findByText("Pembayaran berhasil");
  // Tagihan di belakang sheet sudah lunas dan dimuat ulang; sheet harus tetap terbuka dengan kuitansinya.
  await waitFor(() => expect(document.body.textContent).toContain("Semua tagihan lunas"));
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(within(screen.getByRole("dialog")).getByText("No. kuitansi")).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Selesai" }));
  await waitFor(() => expect(screen.getByText("Semua tagihan lunas")).toBeTruthy());
  expect(screen.getAllByText("Lunas").length).toBeGreaterThan(0);
  expect(screen.getByText("No. kuitansi")).toBeTruthy();
  expect(getState().bills.ipl[0].status).toBe("paid");
});

test("W12: enam bulan dengan saldo bulan terakhir terhitung", async () => {
  mount("/app/warga/tagihan/kas");
  await screen.findByText("November 2026");
  const { months } = await getCashReport();
  expect(document.querySelectorAll("[data-month]")).toHaveLength(6);
  const last = rupiah(months[5].balance);
  expect(document.body.textContent).toContain(last);
  expect(document.body.textContent).not.toMatch(/terintegrasi/i);
});

test("W11: riwayat memuat kuitansi dengan label jenis", async () => {
  mount("/app/warga/tagihan/riwayat");
  await screen.findByText("IPL November 2026");
  expect(screen.getAllByText("Uang muka 1 dari 5").length).toBeGreaterThan(0);
});

test("W13: isi token PLN, bayar, token tampil terkelompok", async () => {
  mount("/app/warga/isi-ulang");
  fireEvent.click(await screen.findByRole("button", { name: /Token listrik/ }));
  fireEvent.change(await screen.findByLabelText(/Nomor meter/), { target: { value: "12345678901" } });
  fireEvent.click(screen.getByRole("button", { name: /Token PLN 50rb/ }));
  fireEvent.click(screen.getByRole("button", { name: /Lanjut bayar/ }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(await within(dialog).findByRole("button", { name: /BRI/ }));
  fireEvent.click(await within(dialog).findByRole("button", { name: /Saya sudah bayar/ }));
  await within(dialog).findByText("Pembayaran berhasil");
  await waitFor(() => expect(getState().bills.ppobTx[0].status).toBe("paid"));
  expect(screen.getByRole("dialog")).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Selesai" }));
  const tok = await screen.findByTestId("pln-token");
  expect(tok.textContent).toMatch(/^(\d{4}-){4}\d{4}$/);
});

test("W13: nomor meter pendek menampilkan pesan galat", async () => {
  mount("/app/warga/isi-ulang");
  fireEvent.click(await screen.findByRole("button", { name: /Token listrik/ }));
  fireEvent.change(await screen.findByLabelText(/Nomor meter/), { target: { value: "1234" } });
  fireEvent.click(screen.getByRole("button", { name: /Token PLN 50rb/ }));
  fireEvent.click(screen.getByRole("button", { name: /Lanjut bayar/ }));
  expect((await screen.findByRole("alert")).textContent).toBe("Nomor meter belum valid");
});
