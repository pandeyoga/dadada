import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import {
  requestOtp, verifyOtp, setPersona, logout, simulateBast, setLocation, homePathFor,
} from "@/prototype/services/api/session";

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
});
afterAll(() => setLatency(null));

test("requestOtp menolak nomor kurang dari 10 digit", async () => {
  await expect(requestOtp("0812")).rejects.toThrow("Nomor WhatsApp belum lengkap");
});

test("requestOtp menerima format bebas dan menyimpan nomor", async () => {
  const r = await requestOtp("0812-3456-7890");
  expect(r.sentTo).toContain("7890");
  expect(getState().session.phone).toBe("081234567890");
  await expect(requestOtp("+62 812 3456 789")).resolves.toBeDefined();
});

test("verifyOtp menerima 6 digit dan menolak selain itu", async () => {
  await expect(verifyOtp("12345")).rejects.toThrow("Kode harus 6 angka");
  await expect(verifyOtp("12345a")).rejects.toThrow("Kode harus 6 angka");
  expect(getState().session.loggedIn).toBe(false);
  await verifyOtp("123456");
  expect(getState().session.loggedIn).toBe(true);
});

test("homePathFor menurut persona", () => {
  expect(homePathFor(getState())).toBe("/app/demo");
  setPersona("buyer");
  expect(homePathFor(getState())).toBe("/app/pembeli");
  setPersona("resident");
  expect(getState().mode).toBe("resident");
  expect(getState().onboarding.done).toBe(true);
  expect(homePathFor(getState())).toBe("/app/warga");
  setPersona("satpam");
  expect(homePathFor(getState())).toBe("/app/satpam");
  setPersona("pengelola");
  expect(homePathFor(getState())).toBe("/app/pengelola");
  setPersona("mitra");
  expect(homePathFor(getState())).toBe("/app/mitra");
});

test("simulateBast: warga baru ke onboarding, perjalanan selesai, ada notifikasi", () => {
  setPersona("buyer");
  const before = getState().notifications.length;
  simulateBast();
  const s = getState();
  expect(s.mode).toBe("resident");
  expect(s.onboarding.done).toBe(false);
  expect(s.buyer.journey.current).toBe(5);
  expect(s.buyer.journey.progress).toBe(100);
  expect(s.notifications.length).toBe(before + 1);
  expect(s.notifications[0]).toMatchObject({ tier: "info", read: false });
  expect(s.notifications[0].title).toBe("Selamat, rumah Anda resmi diserahterimakan");
  expect(homePathFor(s)).toBe("/app/selamat-datang");
});

test("logout dan setLocation", () => {
  setPersona("resident");
  logout();
  expect(getState().session.loggedIn).toBe(false);
  expect(homePathFor(getState())).toBe("/app/demo");
  setLocation("outside");
  expect(getState().location).toBe("outside");
});
