import React, { act } from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { setPersona } from "@/prototype/services/api/session";
import screens from "@/prototype/screens.json";

const Where = () => <div data-testid="where">{useLocation().pathname}</div>;
const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Where />
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );
const click = (el) => fireEvent.click(el);
const type = (el, v) => fireEvent.change(el, { target: { value: v } });
const where = () => screen.getByTestId("where").textContent;

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
});
afterAll(() => setLatency(null));

test("indeks /app belum masuk -> peluncur; sudah masuk -> beranda persona", async () => {
  const a = mount("/app");
  await waitFor(() => expect(where()).toBe("/app/demo"));
  a.unmount();
  act(() => setPersona("satpam"));
  mount("/app");
  await waitFor(() => expect(where()).toBe("/app/satpam"));
});

test("peluncur: label, persona, daftar layar per kelompok", () => {
  mount("/app/demo");
  expect(screen.getByText("Data contoh")).toBeTruthy();
  ["Rina · Pembeli", "Rina · Warga", "Pak Joko · Satpam", "Pengelola kawasan", "Dimas · Mitra"].forEach((n) =>
    expect(screen.getByRole("button", { name: new RegExp(n) })).toBeTruthy());
  ["Demo", "Pembeli", "Transisi", "Warga", "Satpam", "Pengelola", "Mitra"].forEach((g) =>
    expect(screen.getAllByText(g).length).toBeGreaterThan(0));
  expect(document.querySelectorAll("details a").length).toBe(screens.length);
});

test("kartu persona masuk ke beranda; BAST ke selamat datang; sakelar lokasi; reset", async () => {
  mount("/app/demo");
  click(screen.getByRole("button", { name: /Rina · Warga/ }));
  await waitFor(() => expect(where()).toBe("/app/warga"));
  expect(getState().session.loggedIn).toBe(true);
});

test("peluncur: tombol BAST, lokasi, reset", async () => {
  mount("/app/demo");
  click(screen.getByRole("button", { name: "Di luar kawasan" }));
  expect(getState().location).toBe("outside");
  click(screen.getByRole("button", { name: "Di dalam kawasan" }));
  expect(getState().location).toBe("inside");
  click(screen.getByRole("button", { name: /Simulasikan BAST/ }));
  await waitFor(() => expect(where()).toBe("/app/selamat-datang"));
  expect(getState().buyer.journey.current).toBe(5);
});

test("reset mengembalikan data contoh", async () => {
  mount("/app/demo");
  act(() => setPersona("resident"));
  click(screen.getByRole("button", { name: /Reset data contoh/ }));
  expect(getState().session.loggedIn).toBe(false);
  expect(getState().mode).toBe("buyer");
});

test("masuk: nomor pendek ditolak, lalu OTP 6 angka masuk", async () => {
  mount("/app/masuk");
  const input = screen.getByLabelText("Nomor WhatsApp");
  type(input, "0812");
  click(screen.getByRole("button", { name: /Kirim kode/ }));
  expect((await screen.findByRole("alert")).textContent).toBe("Nomor WhatsApp belum lengkap");
  type(input, "0812-3456-7890");
  click(screen.getByRole("button", { name: /Kirim kode/ }));
  const otp = await screen.findByLabelText("Kode OTP 6 angka");
  expect(document.querySelectorAll('[data-testid="otp-slot"]').length).toBe(6);
  type(otp, "123456");
  await waitFor(() => expect(getState().session.loggedIn).toBe(true));
  await waitFor(() => expect(where()).toBe("/app/pembeli"));
});

test("window.__rdgDemo dipasang dan dilepas", () => {
  const { unmount } = mount("/app/demo");
  expect(Object.keys(window.__rdgDemo).sort()).toEqual(["acceptSos", "createGuestPass", "reset", "resolveSos", "sendSos", "setLocation", "setPersona", "simulateBast"]);
  act(() => window.__rdgDemo.setPersona("mitra"));
  expect(getState().session.persona).toBe("mitra");
  unmount();
  expect(window.__rdgDemo).toBeUndefined();
});
