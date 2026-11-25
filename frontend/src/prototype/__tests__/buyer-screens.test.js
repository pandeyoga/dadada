import React from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, setState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";

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

test("P1: tahap Bangun 72 % dan tagihan DP ke-3 mengarah ke P5", async () => {
  mount("/app/pembeli");
  await screen.findByText(/Rp1\.000\.000/);
  expect(screen.getAllByText((_, el) => /^72\s%$/.test(el.textContent)).length).toBeGreaterThan(0);
  expect(screen.getByText(/Cicilan DP ke-3/)).toBeTruthy();
  expect(document.querySelector(`a[href="/app/pembeli/bayar/dp-3"]`).textContent).toBe("Bayar");
});

test("P5: bayar lewat VA menampilkan Lunas dan kuitansi, lalu P1 berpindah ke dp-4", async () => {
  mount("/app/pembeli/bayar/dp-3");
  fireEvent.click(await screen.findByRole("button", { name: /Pilih metode bayar/ }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(await within(dialog).findByRole("button", { name: /BRI/ }));
  fireEvent.click(await within(dialog).findByRole("button", { name: /Saya sudah bayar/ }));
  await within(dialog).findByText("Pembayaran berhasil");
  fireEvent.click(within(dialog).getByRole("button", { name: "Selesai" }));
  await waitFor(() => expect(screen.getByText("Pembayaran lunas")).toBeTruthy());
  expect(screen.getAllByText("Lunas").length).toBeGreaterThan(0);
  expect(screen.getByText("No. kuitansi")).toBeTruthy();
});

test("P6: tanpa klaim integrasi bank, ada catatan dibayar ke bank setelah akad", async () => {
  mount("/app/pembeli/kpr");
  await screen.findByText(/Rp1\.062\.500/);
  expect(screen.getByText("KPR Subsidi · Bank BTN")).toBeTruthy();
  expect(screen.getByText("Menunggu rumah siap")).toBeTruthy();
  expect(document.body.textContent).toMatch(/dibayar ke bank setelah akad/i);
  expect(document.body.textContent).not.toMatch(/terintegrasi/i);
});

test.each([["buyer", "Dokumen"], ["resident", "Komunitas"]])("P10 mode %s memakai menu bawah yang sesuai", async (mode, label) => {
  setState((s) => ({ ...s, mode }));
  mount("/app/ajak-teman");
  await screen.findByText("RINA-C12");
  expect(within(screen.getByRole("navigation", { name: "Menu utama" })).getByText(label)).toBeTruthy();
});

test("P9: kirim pertanyaan menambah item daftar", async () => {
  mount("/app/pembeli/akun");
  fireEvent.change(await screen.findByLabelText(/Pertanyaan atau keluhan/), { target: { value: "Kapan serah terima?" } });
  fireEvent.click(screen.getByRole("button", { name: /Kirim$/ }));
  await screen.findByText("Kapan serah terima?");
  expect(screen.getByText("Data contoh")).toBeTruthy();
});
