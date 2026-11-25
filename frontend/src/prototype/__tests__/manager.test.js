import React from "react";
import { render, screen, waitFor, within, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import "@testing-library/jest-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState, setState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { startPayment, confirmPayment } from "@/prototype/services/api/payments";
import { sendSos } from "@/prototype/services/api/sos";
import { listAnnouncements, listProducts, listServices } from "@/prototype/services/api/community";
import { listTickets } from "@/prototype/services/api/care";
import {
  getManagerSummary, issueIplBills, sendIplReminders, assignTicket, postAnnouncement, listVendors, setVendorStatus,
} from "@/prototype/services/api/manager";

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

async function payDecember() {
  const t = { targetType: "bill", targetId: "ipl-2026-12", amount: 150000, title: "IPL Desember 2026" };
  const p = await startPayment(t, "qris");
  await confirmPayment(p.id);
}

describe("ringkasan", () => {
  test("empat angka ringkasan dan iplPaidPct berubah setelah warga membayar", async () => {
    const before = getManagerSummary();
    expect(Object.keys(before).sort()).toEqual(expect.arrayContaining(["iplPaidPct", "occupancy", "openTickets", "sosThisMonth"]));
    expect(before.openTickets).toBe(1); // tk-1 dikerjakan; tk-2 selesai
    expect(before.sosThisMonth).toBe(0);
    expect(before.occupancy).toBeGreaterThan(80);
    await payDecember();
    const after = getManagerSummary();
    expect(after.iplPaidPct).toBeGreaterThan(before.iplPaidPct);
  });

  test("sosThisMonth menghitung SOS bulan ini", async () => {
    await sendSos("medis");
    expect(getManagerSummary().sosThisMonth).toBe(1);
  });

  test("state lama tanpa field baru tidak membuat ringkasan gagal", () => {
    setState((s) => ({ ...s, manager: { units: s.manager.units, announcements: s.manager.announcements } }));
    expect(getManagerSummary().iplPaidPct).toBeGreaterThanOrEqual(0);
  });
});

describe("tagihan IPL", () => {
  test("issueIplBills periode baru membuat 20 tagihan; kedua kali melempar pesan persis", async () => {
    await expect(issueIplBills("2027-01")).resolves.toEqual({ created: 20 });
    await expect(issueIplBills("2027-01")).rejects.toThrow("Tagihan periode ini sudah diterbitkan");
    const bill = getState().bills.ipl.find((b) => b.id === "ipl-2027-01");
    expect(bill).toMatchObject({ period: "Januari 2027", amount: 150000, dueDate: "2027-01-10", status: "unpaid" });
    expect(getState().notifications[0]).toMatchObject({ tier: "info", link: "/app/warga/tagihan" });
  });

  test("periode yang sudah ada (Desember 2026) juga ditolak, periode tak valid ditolak", async () => {
    await expect(issueIplBills("2026-12")).rejects.toThrow("Tagihan periode ini sudah diterbitkan");
    await expect(issueIplBills("januari")).rejects.toThrow("Periode tidak valid");
  });

  test("sendIplReminders hanya menghitung unit yang belum lunas", async () => {
    const units = getState().manager.units;
    const lunas = units.find((u) => u.ipl === "lunas").block;
    const belum = units.find((u) => u.ipl === "belum" && u.block !== "C-12").block;
    await expect(sendIplReminders([lunas, belum])).resolves.toEqual({ sent: 1 });
    await expect(sendIplReminders(["C-12"])).resolves.toEqual({ sent: 1 });
    expect(getState().notifications[0]).toMatchObject({ tier: "info", link: "/app/warga/tagihan" });
    await payDecember();
    await expect(sendIplReminders(["C-12"])).resolves.toEqual({ sent: 0 });
  });
});

describe("tiket dan pengumuman", () => {
  test("assignTicket mengisi teknisi dan riwayat; teknisi kosong ditolak", async () => {
    await assignTicket("tk-1", "Pak Anto");
    const tk = (await listTickets()).find((t) => t.id === "tk-1");
    expect(tk.assignee).toBe("Pak Anto");
    expect(tk.history[tk.history.length - 1].note).toContain("Pak Anto");
    await expect(assignTicket("tk-1", " ")).rejects.toThrow("Pilih teknisi");
    await expect(assignTicket("nope", "Pak Anto")).rejects.toThrow("Tiket tidak ditemukan");
  });

  test("postAnnouncement tampil pertama di listAnnouncements + notifikasi bertingkat", async () => {
    const n0 = getState().notifications.length;
    await postAnnouncement({ title: "Kerja bakti", body: "Minggu pagi di lapangan.", tier: "keamanan" });
    expect((await listAnnouncements())[0].title).toBe("Kerja bakti");
    expect(getState().notifications).toHaveLength(n0 + 1);
    expect(getState().notifications[0]).toMatchObject({ tier: "keamanan", title: "Kerja bakti", link: "/app/warga/komunitas" });
    expect(getState().manager.announcements[0].title).toBe("Kerja bakti");
  });

  test("postAnnouncement memvalidasi judul, isi, dan jenjang", async () => {
    await expect(postAnnouncement({ title: " ", body: "x", tier: "info" })).rejects.toThrow("Judul pengumuman belum diisi");
    await expect(postAnnouncement({ title: "x", body: "", tier: "info" })).rejects.toThrow("Isi pengumuman belum diisi");
    await expect(postAnnouncement({ title: "x", body: "y", tier: "lain" })).rejects.toThrow("Jenjang pengumuman tidak dikenal");
  });
});

describe("mitra", () => {
  test("menangguhkan mitra menyembunyikan produk dan jasanya dari warga", async () => {
    const vendors = await listVendors();
    const tenant = vendors.find((v) => v.kind === "tenant");
    const jasa = vendors.find((v) => v.kind === "jasa");
    expect(tenant.status).toBe("aktif");
    await setVendorStatus(tenant.id, "ditangguhkan");
    await setVendorStatus(jasa.id, "ditangguhkan");
    expect((await listProducts()).some((p) => tenant.itemIds.includes(p.id))).toBe(false);
    expect((await listServices()).some((s) => jasa.serviceIds.includes(s.id))).toBe(false);
    await setVendorStatus(tenant.id, "aktif");
    expect((await listProducts()).some((p) => tenant.itemIds.includes(p.id))).toBe(true);
    await expect(setVendorStatus(tenant.id, "hilang")).rejects.toThrow("Status mitra tidak dikenal");
    await expect(setVendorStatus("zzz", "aktif")).rejects.toThrow("Mitra tidak ditemukan");
  });
});

describe("layar K1–K7", () => {
  test("K1 menampilkan empat angka ringkasan", async () => {
    mount("/app/pengelola");
    await waitFor(() => expect(document.querySelector('[data-screen="K1"]')).toBeInTheDocument());
    const s = getManagerSummary();
    expect(await screen.findByLabelText("Tagihan IPL lunas")).toHaveTextContent(`${s.iplPaidPct}%`);
    expect(screen.getByLabelText("Tiket terbuka")).toHaveTextContent(String(s.openTickets));
    expect(screen.getByLabelText("SOS bulan ini")).toHaveTextContent(String(s.sosThisMonth));
    expect(screen.getByLabelText("Hunian")).toHaveTextContent(`${s.occupancy}%`);
  });

  test("K1 ikut berubah saat warga membayar (tanpa muat ulang)", async () => {
    mount("/app/pengelola");
    const before = getManagerSummary().iplPaidPct;
    expect(await screen.findByLabelText("Tagihan IPL lunas")).toHaveTextContent(`${before}%`);
    await act(async () => { await payDecember(); });
    await waitFor(() => expect(screen.getByLabelText("Tagihan IPL lunas")).toHaveTextContent(`${getManagerSummary().iplPaidPct}%`));
    expect(getManagerSummary().iplPaidPct).toBeGreaterThan(before);
  });

  test("K2: Terbitkan tagihan lalu galat saat diulang", async () => {
    mount("/app/pengelola/ipl");
    const input = await screen.findByLabelText("Periode tagihan");
    fireEvent.change(input, { target: { value: "2027-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Terbitkan tagihan" }));
    expect(await screen.findByText("20 tagihan periode Januari 2027 diterbitkan.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Terbitkan tagihan" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tagihan periode ini sudah diterbitkan");
  });

  test("K3: memajukan tiket memindahkan kartu ke kolom berikutnya", async () => {
    mount("/app/pengelola/tiket");
    const col = (name) => screen.getByRole("region", { name });
    await waitFor(() => expect(within(col("Dikerjakan")).getByText(/Atap dapur merembes/)).toBeInTheDocument());
    fireEvent.click(within(col("Dikerjakan")).getByRole("button", { name: /Majukan/ }));
    await waitFor(() => expect(within(col("Selesai")).getByText(/Atap dapur merembes/)).toBeInTheDocument());
    expect(within(col("Dikerjakan")).queryByText(/Atap dapur merembes/)).toBeNull();
    expect(getState().care.tickets.find((t) => t.id === "tk-1").status).toBe("selesai");
  });

  test("K4: kirim pengumuman muncul di daftar terkirim dan listAnnouncements", async () => {
    mount("/app/pengelola/pengumuman");
    fireEvent.change(await screen.findByLabelText("Judul"), { target: { value: "Jalan ditutup" } });
    fireEvent.change(screen.getByLabelText("Isi pengumuman"), { target: { value: "Jalan Blok C ditutup sore ini." } });
    fireEvent.click(screen.getByRole("button", { name: "Kirim pengumuman" }));
    await waitFor(() => expect(getState().community.announcements[0].title).toBe("Jalan ditutup"));
    expect((await listAnnouncements())[0].title).toBe("Jalan ditutup");
    expect(await screen.findAllByText("Jalan ditutup")).not.toHaveLength(0);
  });

  test("K4: judul kosong menampilkan galat", async () => {
    mount("/app/pengelola/pengumuman");
    fireEvent.click(await screen.findByRole("button", { name: "Kirim pengumuman" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Judul pengumuman belum diisi");
  });

  test("K5: laporan kas menampilkan saldo bulan terakhir", async () => {
    mount("/app/pengelola/kas");
    expect(await screen.findByText("November 2026")).toBeInTheDocument();
    expect(document.querySelector('[data-screen="K5"]')).toBeInTheDocument();
  });

  test("K6: SOS aktif tampil merah setelah sendSos", async () => {
    mount("/app/pengelola/keamanan");
    await screen.findByText("Tidak ada SOS aktif");
    await act(async () => { await sendSos("kebakaran"); });
    expect(await screen.findByRole("alert")).toHaveTextContent(/SOS kebakaran/i);
    expect(screen.queryByText("Tidak ada SOS aktif")).toBeNull();
  });

  test("K7: tangguhkan mitra mengubah status dan menyembunyikan produk", async () => {
    mount("/app/pengelola/mitra");
    const btn = await screen.findByRole("button", { name: "Tangguhkan Minimarket Estora" });
    fireEvent.click(btn);
    await waitFor(() => expect(screen.getByRole("button", { name: "Aktifkan Minimarket Estora" })).toBeInTheDocument());
    expect((await listProducts()).some((p) => p.id === "mk-10")).toBe(false);
  });
});
