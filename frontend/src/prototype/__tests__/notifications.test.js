import React, { act } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState, setState, STORAGE_KEY, STATE_VERSION } from "@/prototype/services/store";
import { buildInitialState } from "@/prototype/services/initialState";
import { setLatency } from "@/prototype/services/latency";
import { listNotifications, markAllRead, markRead } from "@/prototype/services/api/account";
import { startPayment, confirmPayment } from "@/prototype/services/api/payments";
import { simulateBast } from "@/prototype/services/api/session";
import { sendSos, acceptSos } from "@/prototype/services/api/sos";
import { checkInGuest } from "@/prototype/services/api/guard";
import { createGuestPass } from "@/prototype/services/api/security";
import { advanceTicket } from "@/prototype/services/api/care";
import { askQuestion } from "@/prototype/services/api/buyer";
import { issueIplBills, sendIplReminders, postAnnouncement } from "@/prototype/services/api/manager";

jest.mock("@/prototype/lib/scrollTop", () => ({ scrollToTop: jest.fn() }));

const NOW = Date.parse("2026-11-25T03:00:00Z"); // 10.00 WIB
const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );
const asResident = () => setState((s) => ({ ...s, mode: "resident", onboarding: { done: true }, session: { ...s.session, persona: "resident", loggedIn: true } }));
const byId = (id) => getState().notifications.find((n) => n.id === id);

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => NOW });
  setLatency(0);
});
afterAll(() => setLatency(null));

describe("penerima notifikasi per mode", () => {
  test("fixture: setiap notifikasi punya audience; tautan pembeli tetap di /app/pembeli", () => {
    const list = buildInitialState(NOW).notifications;
    list.forEach((n) => expect(["buyer", "resident"]).toContain(n.audience));
    const buyer = list.filter((n) => n.audience === "buyer");
    expect(buyer.map((n) => n.id).sort()).toEqual(["nt-5", "nt-6"]);
    buyer.filter((n) => n.link).forEach((n) => expect(n.link).toMatch(/^\/app\/pembeli/));
    list.filter((n) => n.audience === "resident" && n.link).forEach((n) => expect(n.link).toMatch(/^\/app\/warga/));
  });

  test("listNotifications mengikuti state.mode", async () => {
    expect((await listNotifications()).map((n) => n.id).sort()).toEqual(["nt-5", "nt-6"]);
    asResident();
    const ids = (await listNotifications()).map((n) => n.id);
    expect(ids).toEqual(expect.arrayContaining(["nt-1", "nt-2", "nt-3", "nt-4"]));
    expect(ids).not.toContain("nt-6");
  });

  test("markAllRead hanya menandai notifikasi mode yang sedang aktif", async () => {
    asResident();
    await markAllRead();
    expect(getState().notifications.filter((n) => n.audience === "resident").every((n) => n.read)).toBe(true);
    expect(byId("nt-6").read).toBe(false);
  });

  test("membayar uang muka ke-3 menandai notifikasi jatuh temponya sudah dibaca", async () => {
    expect(byId("nt-6").read).toBe(false);
    const p = await startPayment({ targetType: "installment", targetId: "dp-3", amount: 1000000, title: "Uang muka 3 dari 5" }, "va_bri");
    await confirmPayment(p.id);
    expect(byId("nt-6").read).toBe(true);
    expect(byId("nt-4").read).toBe(false);
  });

  test("semua penulis notifikasi mengisi audience", async () => {
    asResident();
    await simulateBast();
    const sos = await sendSos("medis");
    await acceptSos(sos.id);
    const pass = await createGuestPass({ guestName: "Bu Ani", date: "2026-11-25", from: "09:00", to: "12:00" });
    await checkInGuest(pass.code);
    await advanceTicket("tk-1");
    await issueIplBills("2027-01");
    await sendIplReminders(["C-12"], "2027-01");
    await postAnnouncement({ title: "Kerja bakti", body: "Minggu pagi.", tier: "info" });
    const added = getState().notifications.filter((n) => !/^nt-\d$/.test(n.id));
    expect(added.length).toBe(8);
    added.forEach((n) => expect(n.audience).toBe("resident"));
  });

  test("pertanyaan pembeli yang selesai memberi tahu pembeli, bukan warga", async () => {
    const q = await askQuestion({ category: "KPR", description: "Kapan jadwal akad KPR saya?" });
    for (let i = 0; i < 3; i += 1) await advanceTicket(q.id);
    const n = getState().notifications[0];
    expect(n).toMatchObject({ audience: "buyer", link: "/app/pembeli/akun" });
    expect(n.title).not.toMatch(/Perbaikan/);
  });
});

describe("layar", () => {
  test("W27 mode pembeli: hanya kabar pembeli (tanpa pintu, tamu, IPL)", async () => {
    mount("/app/notifikasi");
    const items = await screen.findAllByTestId("notif-item");
    const text = items.map((i) => i.textContent).join(" | ");
    expect(text).toContain("Uang muka ke-3 jatuh tempo");
    expect(text).not.toMatch(/Pintu depan|Tamu tiba|Tagihan IPL|banjir/);
  });

  test("P1: titik bel hanya untuk notifikasi pembeli", async () => {
    setState((s) => ({ ...s, session: { ...s.session, persona: "buyer", loggedIn: true } }));
    mount("/app/pembeli");
    await waitFor(() => expect(screen.getByRole("link", { name: "Notifikasi" }).hasAttribute("data-badge")).toBe(true));
    await act(() => markRead("nt-6"));
    await waitFor(() => expect(screen.getByRole("link", { name: "Notifikasi" }).hasAttribute("data-badge")).toBe(false));
    expect(getState().notifications.some((n) => n.audience === "resident" && !n.read)).toBe(true);
  });

  test("W1: notifikasi pembeli yang belum dibaca tidak memunculkan titik bel warga", async () => {
    asResident();
    setState((s) => ({ ...s, notifications: s.notifications.map((n) => (n.audience === "resident" ? { ...n, read: true } : n)) }));
    mount("/app/warga");
    await screen.findByText("Rumah aman");
    expect(screen.getByRole("link", { name: "Notifikasi" }).hasAttribute("data-badge")).toBe(false);
  });
});

test("STATE_VERSION 3: state v2 tersimpan (tanpa audience/jam demo) diganti fixture baru", () => {
  expect(STATE_VERSION).toBe(3);
  const v2 = { ...buildInitialState(NOW), version: 2, mode: "resident" };
  v2.notifications = v2.notifications.map(({ audience, ...n }) => n);
  const storage = { getItem: (k) => (k === STORAGE_KEY ? JSON.stringify(v2) : null), setItem: () => {} };
  __initStoreForTest({ storage, now: () => NOW });
  expect(getState().version).toBe(3);
  expect(getState().mode).toBe("buyer");
  expect(getState().notifications.every((n) => n.audience)).toBe(true);
  expect(getState().session.demoClock).toBe("anchored");
});
