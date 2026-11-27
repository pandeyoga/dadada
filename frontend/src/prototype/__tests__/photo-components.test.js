import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { StageIllustration, PromoIllustration } from "@/prototype/components/Illustrations";
import MarketIllustration from "@/prototype/components/MarketIllustration";
import UnitArt from "@/prototype/surfaces/partner/UnitArt";
import TicketPhoto from "@/prototype/surfaces/resident/care/TicketPhoto";
import CameraView from "@/prototype/components/CameraView";
import { getPhoto, cctvKeyFor, CCTV_KEYS } from "@/prototype/lib/photos";

const CASES = [
  ["progres", () => <StageIllustration img="progress/atap" label="Foto tahap atap" />, true],
  ["promo", () => <PromoIllustration id="pr-2" label="Promo" />, true],
  ["pasar", () => <MarketIllustration img="market/telur" label="Foto Telur" />, false],
  ["unit", () => <UnitArt img="unit/tipe-36" label="Ilustrasi unit" />, true],
  ["tiket", () => <TicketPhoto img="ticket/bocor-dapur" />, true],
];

describe.each(CASES)("foto %s", (_n, make, chip) => {
  test("img lokal, alt, chip, dan cadangan SVG saat error", () => {
    const { container } = render(make());
    const img = container.querySelector("img");
    expect(img.getAttribute("src")).toMatch(/^\/rdg\/foto\//);
    expect(img.getAttribute("src")).not.toMatch(/http/);
    expect(img.getAttribute("alt")).toBeTruthy();
    expect(img.getAttribute("alt")).not.toBe("Foto contoh: Foto laporan");
    expect(img.getAttribute("loading")).toBe("lazy");
    expect(Boolean(screen.queryByText("Foto ilustrasi"))).toBe(chip);
    expect(container.querySelector("svg")).toBeNull();
    fireEvent.error(img);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).not.toBeNull();
    expect(screen.queryByText("Foto ilustrasi")).toBeNull();
  });
});

test("kunci tak dikenal memakai SVG cadangan", () => {
  const { container } = render(<StageIllustration img="nama-adegan" label="x" />);
  expect(container.querySelector("img")).toBeNull();
  expect(container.querySelector("svg")).not.toBeNull();
});

describe("CCTV", () => {
  test("CameraView memakai foto, LIVE, jam, dan cadangan SVG", () => {
    const { container } = render(<CameraView cameraId="cam-1" label="Gerbang utama" />);
    const img = container.querySelector("img");
    expect(img.getAttribute("src")).toBe("/rdg/foto/cctv/gerbang-utama.jpg");
    expect(screen.getByText("LIVE")).toBeTruthy();
    expect(container.querySelector(".rdg-cam-sim").textContent).toBe("Simulasi");
    expect(container.querySelector(".rdg-cam-clock").textContent).toMatch(/^\d\d:\d\d:\d\d$/);
    expect(container.querySelector(".rdg-cam-scan")).not.toBeNull();
    fireEvent.error(img);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg.rdg-cam-scene")).not.toBeNull();
  });

  test("REKAMAN tetap tampil dan berlabel simulasi", () => {
    render(<CameraView cameraId="c" label="Teras depan" live={false} />);
    expect(screen.getByText("REKAMAN")).toBeTruthy();
    expect(screen.getByText("Simulasi")).toBeTruthy();
  });

  test("gagal muat tidak menempel saat pindah kamera", () => {
    const { container, rerender } = render(<CameraView cameraId="a" label="Gerbang utama" />);
    fireEvent.error(container.querySelector("img"));
    expect(container.querySelector("img")).toBeNull();
    rerender(<CameraView cameraId="b" label="Lapangan" />);
    expect(container.querySelector("img").getAttribute("src")).toBe("/rdg/foto/cctv/lapangan.jpg");
  });

  test("Photo: gagal muat direset saat kunci berganti", () => {
    const { container, rerender } = render(<MarketIllustration img="market/telur" label="Telur" />);
    fireEvent.error(container.querySelector("img"));
    expect(container.querySelector("img")).toBeNull();
    rerender(<MarketIllustration img="market/kopi" label="Kopi" />);
    expect(container.querySelector("img")).not.toBeNull();
  });

  test("cctvKeyFor: pos sebagai kata utuh", () => {
    expect(cctvKeyFor("a", "Pos jaga")).toBe("cctv/pos-satpam");
    expect(cctvKeyFor("a", "Kamera posisi atas")).not.toBe("cctv/pos-satpam");
    const k = cctvKeyFor("x", "Kamera posisi atas");
    expect(CCTV_KEYS).toContain(k);
  });

  test("cctvKeyFor: kata kunci dan hash deterministik", () => {
    expect(cctvKeyFor("a", "Gerbang belakang")).toBe("cctv/gerbang-belakang");
    expect(cctvKeyFor("a", "Gerbang utama")).toBe("cctv/gerbang-utama");
    expect(cctvKeyFor("a", "Teras rumah")).toBe("cctv/teras-depan");
    expect(cctvKeyFor("a", "Taman bermain")).toBe("cctv/taman-bermain");
    expect(cctvKeyFor("a", "Kebun")).toBe("cctv/taman-belakang");
    expect(cctvKeyFor("a", "POS satpam")).toBe("cctv/pos-satpam");
    expect(cctvKeyFor("a", "Carport blok C")).toBe("cctv/jalan-blok");
    expect(cctvKeyFor("a", "Lapangan")).toBe("cctv/lapangan");
    const k = cctvKeyFor("x", "Kamera ruang tamu");
    expect(CCTV_KEYS).toContain(k);
    expect(cctvKeyFor("x", "Kamera ruang tamu")).toBe(k);
    expect(CCTV_KEYS).toContain(cctvKeyFor("", "Kamera ruang tamu"));
  });

  test("getPhoto", () => {
    expect(getPhoto("tidak/ada")).toBeNull();
    expect(getPhoto("market/telur")).toMatchObject({ illustrative: false });
  });
});

test("W25 menampilkan foto fasilitas", async () => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
  const { container } = render(
    <MemoryRouter initialEntries={["/app/warga/fasilitas"]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );
  await screen.findByRole("button", { name: "Pesan Lapangan serbaguna" });
  const srcs = [...container.querySelectorAll("img")].map((i) => i.getAttribute("src"));
  expect(srcs.some((s) => s.startsWith("/rdg/foto/facility/"))).toBe(true);
  srcs.forEach((s) => expect(s).not.toMatch(/http/));
  expect(screen.getByText(/Foto ilustrasi — bukan foto fasilitas Estora sebenarnya/)).toBeTruthy();
});
afterAll(() => setLatency(null));

test("W21: foto contoh tanpa chip per ubin, dengan satu keterangan", async () => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
  const { container } = render(
    <MemoryRouter initialEntries={["/app/warga/lapor"]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole("button", { name: "Lapor kerusakan baru" }));
  await screen.findByRole("button", { name: "Foto Atap dan plafon" });
  expect(screen.getByText(/Foto contoh — ilustrasi, bukan foto rumah Anda/)).toBeTruthy();
  expect(container.querySelectorAll(".rdg-photo-tag").length).toBe(0);
});
