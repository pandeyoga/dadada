import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { rupiah } from "@/prototype/lib/format";
import screens from "@/prototype/screens.json";

const mount = (path, hostname) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/*" element={<PrototypeApp {...(hostname !== undefined ? { hostname } : {})} />} />
        <Route path="/" element={<div data-testid="home" />} />
      </Routes>
    </MemoryRouter>
  );

test.each(screens.map((s) => [s.id, s.path]))("rute %s %s menampilkan layarnya", async (id, path) => {
  mount(path);
  await waitFor(() => expect(document.querySelector(`[data-screen="${id}"]`)).not.toBeNull(), { timeout: 3000 });
});

test("inventaris lengkap: 59 rute unik, 60 id", () => {
  expect(new Set(screens.map((s) => s.path)).size).toBe(59);
  expect(screens.length).toBe(59);
  const ids = screens.flatMap((s) => [s.id, ...(s.extraIds || [])]);
  const expected = [];
  const rng = (p, n) => { for (let i = 1; i <= n; i++) expected.push(`${p}${i}`); };
  rng("U", 2); rng("P", 11); rng("T", 1); rng("W", 29); rng("S", 5); rng("K", 7); rng("M", 5);
  expect(expected.length).toBe(60);
  expect([...ids].sort()).toEqual([...expected].sort());
});

test("rute dinamis tetap memetakan layar yang sama", async () => {
  mount("/app/pembeli/bayar/dp-1");
  await waitFor(() => expect(document.querySelector('[data-screen="P5"]')).not.toBeNull());
});

test("host produksi dialihkan ke /", () => {
  const { queryByTestId } = mount("/app/warga", "hl5.estora.id");
  expect(document.querySelector("[data-screen]")).toBeNull();
  expect(queryByTestId("home")).not.toBeNull();
});

test("rupiah", () => {
  expect(rupiah(166000000)).toBe("Rp166.000.000");
});
