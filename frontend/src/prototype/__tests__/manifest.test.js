import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import fs from "fs";
import nodePath from "path";

const mount = (path, hostname) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/*" element={<PrototypeApp {...(hostname !== undefined ? { hostname } : {})} />} />
        <Route path="/" element={<div data-testid="home" />} />
      </Routes>
    </MemoryRouter>
  );

const link = () => document.querySelector("link[rel=manifest]");
const theme = () => document.querySelector('meta[name="theme-color"]');

beforeEach(() => {
  setLatency(0);
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  document.head.innerHTML =
    '<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#000000">';
});
afterAll(() => setLatency(null));

test("manifest dan theme-color prototipe dipasang lalu dikembalikan saat dilepas", () => {
  const view = mount("/app/warga");
  expect(link().getAttribute("href")).toBe("/rdg/manifest.json");
  expect(theme().getAttribute("content")).toBe("#00454D");
  view.unmount();
  expect(link().getAttribute("href")).toBe("/manifest.json");
  expect(theme().getAttribute("content")).toBe("#000000");
});

test("tanpa tag bawaan: tag dibuat sementara lalu dihapus", () => {
  document.head.innerHTML = "";
  const view = mount("/app/warga");
  expect(link().getAttribute("href")).toBe("/rdg/manifest.json");
  expect(theme().getAttribute("content")).toBe("#00454D");
  view.unmount();
  expect(link()).toBeNull();
  expect(theme()).toBeNull();
});

test("host produksi tidak mengganti manifest staf", () => {
  mount("/app/warga", "hl5.estora.id");
  expect(link().getAttribute("href")).toBe("/manifest.json");
});

test("isi manifest Rumah Dalam Genggaman", () => {
  const file = nodePath.join(__dirname, "../../../public/rdg/manifest.json");
  const manifest = JSON.parse(fs.readFileSync(file, "utf8"));
  expect(manifest).toMatchObject({
    name: "Rumah Dalam Genggaman · Estora",
    short_name: "Rumahku",
    start_url: "/app",
    scope: "/app",
    theme_color: "#00454D",
    background_color: "#E7FFEF",
  });
  expect(manifest.icons.map((i) => i.src)).toEqual(["/rdg/icon-192.png", "/rdg/icon-512.png"]);
});
