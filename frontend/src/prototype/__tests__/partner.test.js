import React from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import "@testing-library/jest-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import {
  registerPartner, getPartnerHome, listCatalog, shareLink, simulateKpr, listReferrals, getCommission, requestPayout,
} from "@/prototype/services/api/partner";

jest.mock("@/prototype/lib/scrollTop", () => ({ scrollToTop: jest.fn() }));

const NOW = Date.parse("2026-11-25T03:00:00Z");
beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => NOW });
  setLatency(0);
});
afterAll(() => setLatency(null));

const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );

const VALID = {
  account: { phone: "081234567001", password: "rahasia1" },
  personal: { name: "Dimas Pratama", city: "Bekasi" },
  bank: { bankName: "Bank BTN", accountNumber: "1234567890", holder: "Dimas Pratama" },
  social: { instagram: "@dimas.properti" },
};

describe("simulasi KPR", () => {
  test("166 jt, DP 5 jt, 20 tahun, 5 % -> Rp1.062.500 per bulan", () => {
    expect(simulateKpr({ price: 166000000, dp: 5000000, tenorYears: 20, rate: 5 }).monthly).toBe(1062500);
  });
  test("input tidak valid ditolak dengan pesan Indonesia", () => {
    expect(() => simulateKpr({ price: 100, dp: 100, tenorYears: 20, rate: 5 })).toThrow("Uang muka harus lebih kecil dari harga");
    expect(() => simulateKpr({ price: 166000000, dp: 0, tenorYears: 3, rate: 5 })).toThrow("Tenor harus 5 sampai 30 tahun");
    expect(() => simulateKpr({ price: 166000000, dp: 0, tenorYears: 20, rate: 0 })).toThrow("Bunga harus lebih dari 0");
  });
});

describe("tautan berbagi", () => {
  test("memuat kode mitra dan unit", () => {
    const l = shareLink("C-14");
    expect(l.url).toContain("ref=MITRA-DP01");
    expect(l.url).toContain("unit=C-14");
    expect(l.qrText).toBe(l.url);
  });
  test("unit tidak dikenal", () => {
    expect(() => shareLink("Z-99")).toThrow("Unit tidak ditemukan");
  });
  test("katalog berisi C-14 tipe 36/72", async () => {
    const c = (await listCatalog()).find((u) => u.id === "C-14");
    expect(c).toMatchObject({ type: "36/72", price: 166000000, status: "tersedia" });
  });
});

describe("pendaftaran mitra", () => {
  test("rekening kurang dari 8 digit ditolak", async () => {
    await expect(registerPartner({ ...VALID, bank: { ...VALID.bank, accountNumber: "1234567" } })).rejects.toThrow("Nomor rekening belum valid");
    expect(getState().partner.registered).toBe(false);
  });
  test("berhasil menandai terdaftar dan menyimpan profil", async () => {
    await registerPartner(VALID);
    const p = getState().partner;
    expect(p.registered).toBe(true);
    expect(p.profile.name).toBe("Dimas Pratama");
    expect(p.profile.bank).toMatchObject({ bankName: "Bank BTN" });
  });
  test("nama kosong dan nomor ponsel pendek ditolak", async () => {
    await expect(registerPartner({ ...VALID, personal: { name: " " } })).rejects.toThrow("Nama lengkap belum diisi");
    await expect(registerPartner({ ...VALID, account: { phone: "0812", password: "rahasia1" } })).rejects.toThrow("Nomor WhatsApp belum valid");
  });
});

describe("beranda, rujukan, komisi", () => {
  test("beranda: poin, komisi diproses, peringkat", async () => {
    const h = await getPartnerHome();
    expect(h.points).toBe(1250);
    expect(h.commissionPending).toBe(500000);
    expect(h.rank).toBe(3);
    expect(h.leaderboard).toHaveLength(5);
    expect(h.leaderboard[0]).toMatchObject({ rank: 1, name: "Budi Santoso" });
  });
  test("rujukan dikelompokkan lead, booking, akad", async () => {
    const g = await listReferrals();
    expect(g.map((x) => [x.stage, x.count])).toEqual([["lead", 2], ["booking", 2], ["akad", 1]]);
  });
  test("belum terdaftar: pencairan ditolak", async () => {
    await expect(requestPayout(100000)).rejects.toThrow("Lengkapi pendaftaran dan rekening dulu");
    expect(getState().partner.payouts).toHaveLength(0);
  });
  test("pencairan melebihi saldo ditolak; sah mengurangi saldo", async () => {
    await registerPartner(VALID);
    expect((await getCommission()).balance).toBe(2000000);
    await expect(requestPayout(2000001)).rejects.toThrow("Saldo komisi tidak cukup");
    await expect(requestPayout(0)).rejects.toThrow("Nominal pencairan tidak valid");
    await requestPayout(750000);
    const c = await getCommission();
    expect(c.balance).toBe(1250000);
    expect(c.payouts[0]).toMatchObject({ amount: 750000, status: "diproses" });
  });
});

const typeIn = (label, value) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const click = (name) => fireEvent.click(screen.getByRole("button", { name }));

describe("M1 wizard", () => {
  test("4 langkah, rekening pendek menampilkan galat, selesai mendarat di M2", async () => {
    const { container } = mount("/app/mitra/daftar");
    await waitFor(() => expect(container.querySelector('[data-screen="M1"]')).toBeTruthy());
    expect(screen.getByRole("heading", { name: /Langkah 1: Akun/ })).toBeInTheDocument();
    typeIn(/Nomor WhatsApp/, "081234567001");
    typeIn(/Kata sandi/, "rahasia1");
    click("Lanjut");
    expect(screen.getByRole("heading", { name: /Langkah 2: Data pribadi/ })).toBeInTheDocument();
    typeIn("Nama lengkap", "Dimas Pratama");
    typeIn("Kota domisili", "Bekasi");
    click("Lanjut");
    expect(screen.getByRole("heading", { name: /Langkah 3: Rekening/ })).toBeInTheDocument();
    typeIn("Nama bank", "Bank BTN");
    typeIn("Nomor rekening", "12345");
    typeIn("Nama pemilik rekening", "Dimas Pratama");
    click("Lanjut");
    expect(await screen.findByRole("alert")).toHaveTextContent("Nomor rekening belum valid");
    typeIn("Nomor rekening", "1234567890");
    click("Lanjut");
    expect(screen.getByRole("heading", { name: /Langkah 4: Media sosial/ })).toBeInTheDocument();
    click("Selesai & daftar");
    await waitFor(() => expect(container.querySelector('[data-screen="M2"]')).toBeTruthy());
    expect(getState().partner.registered).toBe(true);
    expect(screen.queryByText("Belum terdaftar")).not.toBeInTheDocument();
  });
});

describe("M2 beranda", () => {
  test("belum terdaftar: tetap tampil dengan ajakan mendaftar dan papan peringkat", async () => {
    const { container } = mount("/app/mitra");
    await waitFor(() => expect(container.querySelector('[data-screen="M2"]')).toBeTruthy());
    expect(screen.getByText("Belum terdaftar")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Daftar sekarang" })).toHaveAttribute("href", "/app/mitra/daftar");
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.getByText("1250")).toBeInTheDocument();
  });
});

describe("M3 katalog", () => {
  test("bagikan menampilkan tautan ref= dan QR; simulasi menampilkan Rp1.062.500", async () => {
    mount("/app/mitra/katalog");
    fireEvent.click(await screen.findByRole("button", { name: "Bagikan C-14" }));
    const dlg = await screen.findByRole("dialog");
    expect(within(dlg).getByTestId("share-url").textContent).toMatch(/ref=MITRA-DP01&unit=C-14/);
    expect(within(dlg).getByRole("img", { name: /Kode QR tautan unit C-14/ })).toBeInTheDocument();
    expect(within(dlg).getByRole("link", { name: /Bagikan lewat WhatsApp/ }).getAttribute("href")).toMatch(/^https:\/\/wa\.me\//);
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Simulasi KPR C-14" }));
    const k = await screen.findByRole("dialog");
    expect(within(k).getByTestId("kpr-monthly").textContent).toBe("Rp1.062.500/bulan");
    expect(within(k).getByText("Simulasi, bukan penawaran bank.")).toBeInTheDocument();
    fireEvent.change(within(k).getByLabelText("Tenor (tahun)"), { target: { value: "2" } });
    expect(within(k).getByRole("alert")).toHaveTextContent("Tenor harus 5 sampai 30 tahun");
  });
});

describe("M4 rujukan", () => {
  test("jumlah per tahap", async () => {
    mount("/app/mitra/rujukan");
    expect(await screen.findByText("Fajar Nugroho")).toBeInTheDocument();
    expect(screen.getByTestId("count-lead")).toHaveTextContent("2");
    expect(screen.getByTestId("count-akad")).toHaveTextContent("1");
  });
});

describe("M5 komisi", () => {
  test("belum terdaftar: formulir diganti ajakan mendaftar, saldo tetap tampil", async () => {
    mount("/app/mitra/komisi");
    await waitFor(() => expect(screen.getByTestId("balance")).toHaveTextContent("Rp2.000.000"));
    expect(screen.queryByRole("button", { name: "Ajukan pencairan" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Lengkapi pendaftaran" })).toHaveAttribute("href", "/app/mitra/daftar");
  });
  test("pencairan melebihi saldo ditolak; yang sah muncul di daftar dan saldo turun", async () => {
    await registerPartner(VALID);
    mount("/app/mitra/komisi");
    await waitFor(() => expect(screen.getByTestId("balance")).toHaveTextContent("Rp2.000.000"));
    typeIn("Nominal (Rp)", "2500000");
    click("Ajukan pencairan");
    expect(await screen.findByRole("alert")).toHaveTextContent("Saldo komisi tidak cukup");
    typeIn("Nominal (Rp)", "750000");
    click("Ajukan pencairan");
    await waitFor(() => expect(screen.getByTestId("balance")).toHaveTextContent("Rp1.250.000"));
    const list = screen.getByRole("list", { name: "Daftar pencairan" });
    expect(within(list).getByText("Rp750.000")).toBeInTheDocument();
    expect(within(list).getByText("Diproses")).toBeInTheDocument();
  });
});
