import React from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState, setState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { doorStatus } from "@/prototype/services/api/security";
import { getResidentHome, completeOnboarding } from "@/prototype/services/api/resident";
import { homePathFor, simulateBast } from "@/prototype/services/api/session";
import useLoad from "@/prototype/lib/useLoad";
import { scrollToTop } from "@/prototype/lib/scrollTop";

jest.mock("@/prototype/lib/scrollTop", () => ({ scrollToTop: jest.fn() }));

const NOW = Date.parse("2026-11-25T03:00:00Z"); // 10.00 WIB

function Where() {
  return <span data-testid="where">{useLocation().pathname}</span>;
}
const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
      <Where />
    </MemoryRouter>
  );

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => NOW });
  setLatency(0);
});
afterAll(() => setLatency(null));

const doorAt = (state, ago) => ({
  security: { door: { state, changedAt: new Date(NOW - ago).toISOString() } },
});

describe("doorStatus", () => {
  test("terbuka pada 29999 ms, terkunci pada 30000 ms", () => {
    expect(doorStatus(doorAt("unlocked", 29999), NOW)).toBe("unlocked");
    expect(doorStatus(doorAt("unlocked", 30000), NOW)).toBe("locked");
    expect(doorStatus(doorAt("locked", 0), NOW)).toBe("locked");
  });
});

describe("layanan warga", () => {
  test("completeOnboarding menandai selesai, menambah keluarga dan kontak, homePathFor ke /app/warga", async () => {
    simulateBast();
    expect(homePathFor(getState())).toBe("/app/selamat-datang");
    const before = getState().security.contacts.length;
    await completeOnboarding({
      connectDevices: true,
      invites: [{ name: "Mas Dimas", phone: "0812-3456-0000" }],
      contacts: [{ name: "Ibu Rina", phone: "0811-000-111" }],
    });
    expect(getState().onboarding.done).toBe(true);
    expect(getState().security.contacts).toHaveLength(before + 1);
    const fam = getState().care.family.find((f) => f.name === "Mas Dimas");
    expect(fam).toMatchObject({ relation: "Keluarga", access: false, phone: "0812-3456-0000" });
    expect(getState().world.family).toBeUndefined();
    expect(getState().security.contacts.at(-1).phone).toBe("0811-0001-11");
    expect(homePathFor(getState())).toBe("/app/warga");
  });

  test("getResidentHome: IPL Rp150.000, kamera aktif, satpam bertugas, energi", async () => {
    const h = await getResidentHome();
    expect(h.iplDue.amount).toBe(150000);
    expect(h.homeStatus).toMatchObject({ door: "locked", cameras: "aktif", guardsOnDuty: 1, safe: true });
    expect(h.announcement.title).toMatch(/fogging/i);
    expect(typeof h.energy.kwh).toBe("number");
  });

  test("completeOnboarding menolak nomor pendek dan melewati duplikat nama/nomor", async () => {
    await expect(completeOnboarding({ invites: [{ name: "Budi", phone: "0812" }] })).rejects.toThrow(/belum lengkap/);
    await expect(completeOnboarding({ invites: [{ name: "  ", phone: "081234567890" }] })).rejects.toThrow(/Nama belum diisi/);
    expect(getState().onboarding.done).toBe(false);
    const n = getState().care.family.length;
    await completeOnboarding({
      invites: [
        { name: "dimas pratama", phone: "081200000001" },
        { name: "Orang Baru", phone: "0812-3456-7001" },
        { name: "Tika", phone: "6281299990000" },
        { name: "Tika", phone: "081211112222" },
      ],
    });
    const fam = getState().care.family;
    expect(fam).toHaveLength(n + 1);
    expect(fam.at(-1)).toMatchObject({ name: "Tika", phone: "0812-9999-0000" });
  });

  test("getResidentHome: IPL lunas → iplDue null", async () => {
    setState((s) => ({ ...s, bills: { ...s.bills, ipl: s.bills.ipl.map((b) => ({ ...b, status: "paid" })) } }));
    expect((await getResidentHome()).iplDue).toBeNull();
  });
});

describe("reset scroll", () => {
  test("pindah rute memanggil scrollToTop", async () => {
    const spy = scrollToTop;
    setState((st) => ({ ...st, mode: "resident", onboarding: { done: true } }));
    mount("/app/warga");
    await screen.findByText("Rumah aman");
    spy.mockClear();
    fireEvent.click(screen.getByRole("link", { name: "Akun saya" }));
    await waitFor(() => expect(screen.getByTestId("where").textContent).toBe("/app/warga/akun"));
    expect(spy).toHaveBeenCalled();
  });
});

describe("useLoad", () => {
  test("fetcher yang ditolak menampilkan pesan galat, bukan Memuat…", async () => {
    const bad = () => Promise.reject(new Error("Server contoh gagal"));
    function Probe() {
      const { data, error } = useLoad(bad, ["bills"]);
      return <p>{error || (data ? "ok" : "Memuat…")}</p>;
    }
    render(<Probe />);
    await screen.findByText("Server contoh gagal");
    expect(screen.queryByText("Memuat…")).toBeNull();
  });
});

describe("T1 onboarding", () => {
  test("empat langkah sampai /app/warga dengan onboarding.done", async () => {
    simulateBast();
    mount("/app/selamat-datang");
    await screen.findByText("Selamat datang di rumah baru");
    fireEvent.click(screen.getByRole("button", { name: "Mulai" }));

    await screen.findByText("Hubungkan kunci & kamera");
    fireEvent.click(screen.getByRole("button", { name: "Hubungkan sekarang" }));
    await screen.findByText("Kunci pintu terhubung");
    await screen.findByText("2 kamera rumah terhubung");
    fireEvent.click(screen.getByRole("button", { name: "Lanjut" }));

    await screen.findByText("Undang keluarga");
    fireEvent.change(screen.getByLabelText("Nama"), { target: { value: "Mas Dimas" } });
    fireEvent.change(screen.getByLabelText("Nomor WhatsApp"), { target: { value: "081234560000" } });
    fireEvent.click(screen.getByRole("button", { name: "Tambah" }));
    await screen.findByText("Mas Dimas");
    fireEvent.click(screen.getByRole("button", { name: "Lanjut" }));

    await screen.findByText("Kontak darurat");
    fireEvent.click(screen.getByRole("button", { name: "Selesai" }));

    await waitFor(() => expect(screen.getByTestId("where").textContent).toBe("/app/warga"));
    expect(getState().onboarding.done).toBe(true);
    expect(getState().care.family.map((f) => f.name)).toContain("Mas Dimas");
    await screen.findByText("Rumah aman");
  });

  test("langkah bisa dilewati dan kembali", async () => {
    mount("/app/selamat-datang");
    fireEvent.click(await screen.findByRole("button", { name: "Mulai" }));
    fireEvent.click(await screen.findByRole("button", { name: "Lewati dulu" }));
    await screen.findByText("Undang keluarga");
    fireEvent.click(screen.getByRole("button", { name: "Kembali" }));
    await screen.findByText("Hubungkan kunci & kamera");
  });
});

describe("W1 beranda warga", () => {
  test("status rumah, IPL dengan Bayar, 8 layanan + Semua, bel dan avatar", async () => {
    setState((s) => ({ ...s, mode: "resident", onboarding: { done: true }, session: { ...s.session, persona: "resident", loggedIn: true } }));
    mount("/app/warga");
    await screen.findByText("Rumah aman");
    expect(screen.getByText("Terkunci")).toBeTruthy();
    expect(await screen.findByText("2 aktif")).toBeTruthy();
    expect(screen.getByText("1 bertugas")).toBeTruthy();
    await screen.findByText("Rp150.000");
    const bayar = screen.getByRole("link", { name: "Bayar" });
    expect(bayar.getAttribute("href")).toBe("/app/warga/tagihan");

    const grid = screen.getByRole("region", { name: "Layanan" });
    expect(within(grid).getAllByRole("link")).toHaveLength(9);
    expect(within(grid).getByText("Semua").closest("a").getAttribute("href")).toBe("/app/warga/layanan");

    expect(screen.getByRole("link", { name: "Notifikasi" }).getAttribute("href")).toBe("/app/notifikasi");
    expect(screen.getByRole("link", { name: "Akun saya" }).getAttribute("href")).toBe("/app/warga/akun");
    expect(screen.getByRole("navigation", { name: "Menu utama" })).toBeTruthy();
    expect(screen.getByText("Penyemprotan nyamuk (fogging)")).toBeTruthy();
    expect(screen.getByText((_, el) => el.tagName === "SPAN" && el.textContent === "142 kWh")).toBeTruthy();
  });

  test("semua tautan layanan ada di screens.json", async () => {
    setState((s) => ({ ...s, mode: "resident", onboarding: { done: true } }));
    mount("/app/warga");
    await screen.findByText("Rumah aman");
    const paths = require("@/prototype/screens.json").map((s) => s.path);
    document.querySelectorAll('[data-screen="W1"] a[href^="/app"]').forEach((a) => {
      expect(paths).toContain(a.getAttribute("href"));
    });
  });
});
