import React, { act } from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import "@testing-library/jest-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { createGuestPass, revokeGuestPass } from "@/prototype/services/api/security";
import { sendSos, activeSos } from "@/prototype/services/api/sos";
import { acceptSos, resolveSos, checkInGuest, logPatrol } from "@/prototype/services/api/guard";

jest.mock("@/prototype/lib/scrollTop", () => ({ scrollToTop: jest.fn() }));

const NOW = Date.parse("2026-11-25T03:00:00Z"); // 10.00 WIB
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
const today = { date: "2026-11-25", from: "09:00", to: "17:00" };

describe("SOS sisi satpam", () => {
  test("accept → accepted oleh Joko + notifikasi keamanan; resolve → tidak aktif", async () => {
    const e = await sendSos("kemalingan");
    await acceptSos(e.id);
    expect(activeSos(getState())).toMatchObject({ status: "accepted", acceptedBy: "Joko" });
    expect(getState().notifications[0]).toMatchObject({ tier: "keamanan", link: "/app/warga/sos" });
    await resolveSos(e.id, "Aman, hanya kucing.");
    expect(activeSos(getState())).toBeNull();
    expect(getState().security.sos[0]).toMatchObject({ status: "resolved", note: "Aman, hanya kucing." });
  });
  test("transisi tidak valid ditolak", async () => {
    const e = await sendSos("medis");
    await expect(resolveSos(e.id)).rejects.toThrow(/Terima laporan lebih dulu/);
    await acceptSos(e.id);
    await expect(acceptSos(e.id)).rejects.toThrow(/tidak menunggu/);
    await expect(acceptSos("nope")).rejects.toThrow(/tidak ditemukan/);
  });
});

describe("checkInGuest", () => {
  test("pertama ok, kedua sudah-dipakai; log gerbang + notifikasi", async () => {
    const p = await createGuestPass({ guestName: "Bu Ani", ...today });
    const r = await checkInGuest(` ${p.code.toLowerCase()} `);
    expect(r.ok).toBe(true);
    expect(getState().security.guestPasses[0]).toMatchObject({ status: "used" });
    expect(getState().security.gateLog[0]).toMatchObject({ direction: "masuk", purpose: "Tamu C-12", name: "Bu Ani" });
    expect(getState().notifications[0]).toMatchObject({ tier: "keamanan", title: "Tamu Bu Ani sudah masuk", link: "/app/warga/keamanan/tamu" });
    expect(await checkInGuest(p.code)).toEqual({ ok: false, reason: "sudah-dipakai" });
  });
  test("kode acak, kemarin, dicabut", async () => {
    expect(await checkInGuest("ZZZZZZ")).toEqual({ ok: false, reason: "tidak-ditemukan" });
    expect(await checkInGuest("  ")).toEqual({ ok: false, reason: "tidak-ditemukan" });
    const old = await createGuestPass({ guestName: "Pak Lama", date: "2026-11-24", from: "09:00", to: "17:00" });
    expect(await checkInGuest(old.code)).toEqual({ ok: false, reason: "kedaluwarsa" });
    const rv = await createGuestPass({ guestName: "Dicabut", ...today });
    await revokeGuestPass(rv.id);
    expect(await checkInGuest(rv.code)).toEqual({ ok: false, reason: "dicabut" });
  });
});

describe("logPatrol", () => {
  test("menambah di depan; titik wajib", async () => {
    const before = getState().security.patrols.length;
    expect(before).toBeGreaterThanOrEqual(3);
    await expect(logPatrol({ checkpoint: " ", note: "x" })).rejects.toThrow(/Titik patroli belum diisi/);
    await logPatrol({ checkpoint: "Gerbang belakang", note: "Aman" });
    expect(getState().security.patrols[0]).toMatchObject({ checkpoint: "Gerbang belakang", note: "Aman", by: "Pak Joko" });
    expect(getState().security.patrols).toHaveLength(before + 1);
  });
});

describe("layar satpam", () => {
  test("S1 menampilkan kartu SOS aktif setelah sendSos", async () => {
    mount("/app/satpam");
    expect(await screen.findByText(/Pak Joko/)).toBeInTheDocument();
    expect(screen.queryByText(/Tidak ada laporan darurat/)).toBeInTheDocument();
    await act(async () => { await sendSos("kebakaran"); });
    const link = await screen.findByRole("link", { name: /Laporan darurat Kebakaran/ });
    expect(link).toHaveAttribute("href", "/app/satpam/sos");
  });

  test("S2: Terima & menuju → accepted → Tandai selesai → resolved", async () => {
    await sendSos("kemalingan");
    mount("/app/satpam/sos");
    fireEvent.click(await screen.findByRole("button", { name: /Terima & menuju/ }));
    await waitFor(() => expect(getState().security.sos[0].status).toBe("accepted"));
    fireEvent.change(await screen.findByLabelText(/Catatan/), { target: { value: "Sudah dicek" } });
    fireEvent.click(await screen.findByRole("button", { name: /Tandai selesai/ }));
    await waitFor(() => expect(getState().security.sos[0].status).toBe("resolved"));
    expect(getState().security.sos[0].note).toBe("Sudah dicek");
    expect(await screen.findByText("Tidak ada laporan darurat aktif")).toBeInTheDocument();
  });

  test("S2 tanpa SOS menampilkan keadaan kosong", async () => {
    const { container } = mount("/app/satpam/sos");
    expect(await screen.findByText("Tidak ada laporan darurat aktif")).toBeInTheDocument();
    expect(container.querySelector('[data-screen="S2"]')).toBeTruthy();
  });

  test("S3: ketuk undangan → valid; kode yang sama lagi → sudah dipakai", async () => {
    const p = await createGuestPass({ guestName: "Bu Ani", ...today });
    mount("/app/satpam/tamu");
    fireEvent.click(await screen.findByRole("button", { name: /Pindai QR/ }));
    const row = await screen.findByRole("button", { name: /Bu Ani/ });
    fireEvent.click(row);
    expect(await screen.findByText("Tamu valid")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Kode tamu/), { target: { value: p.code } });
    fireEvent.click(screen.getByRole("button", { name: /Periksa kode/ }));
    expect(await screen.findByText("Tamu tidak valid")).toBeInTheDocument();
    expect(screen.getByText(/sudah dipakai/i)).toBeInTheDocument();
  });

  test("S4 menampilkan 6 kamera", async () => {
    mount("/app/satpam/cctv");
    expect(await screen.findAllByLabelText(/Perbesar kamera/)).toHaveLength(6);
  });

  test("S5: tambah patroli muncul di log", async () => {
    mount("/app/satpam/patroli");
    fireEvent.change(await screen.findByLabelText(/Titik patroli/), { target: { value: "Gerbang belakang" } });
    fireEvent.change(screen.getByLabelText(/Catatan/), { target: { value: "Gembok aman" } });
    fireEvent.click(screen.getByRole("button", { name: /Catat patroli/ }));
    expect(await screen.findByText("Gembok aman")).toBeInTheDocument();
    expect(getState().security.patrols[0].checkpoint).toBe("Gerbang belakang");
  });
});
