import { getState, setState, subscribe, resetState, __initStoreForTest, STORAGE_KEY } from "@/prototype/services/store";
import { buildInitialState } from "@/prototype/services/initialState";
import { setLatency, wait } from "@/prototype/services/latency";

const NOW = new Date("2026-11-25T09:00:00+07:00").getTime();
const memStorage = (seed = {}) => {
  const data = { ...seed };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
  };
};

beforeEach(() => {
  setLatency(0);
  __initStoreForTest({ storage: memStorage(), now: () => NOW });
});

test("state awal memuat nilai dunia demo", () => {
  const s = buildInitialState(NOW);
  expect(s.world.unit.price).toBe(166000000);
  expect(s.buyer.installments.filter((i) => i.amount === 1000000)).toHaveLength(5);
  expect(s.buyer.kpr.monthly).toBe(1062500);
  expect(s.bills.ipl[0].amount).toBe(150000);
  expect(s.buyer.journey.progress).toBe(72);
  expect(s.buyer.journey.steps).toHaveLength(6);
  expect(s.world.neighbors).toHaveLength(20);
  expect(s.manager.units).toHaveLength(20);
  expect(s.buyer.installments.find((i) => i.id === "dp-3").status).toBe("unpaid");
  expect(new Set(s.notifications.map((n) => n.tier))).toEqual(new Set(["darurat", "keamanan", "info"]));
});

test("setState memicu pelanggan dan menyimpan JSON", () => {
  const storage = memStorage();
  __initStoreForTest({ storage, now: () => NOW });
  const fn = jest.fn();
  const off = subscribe(fn);
  setState((s) => ({ ...s, mode: "resident" }));
  expect(fn).toHaveBeenCalledTimes(1);
  expect(JSON.parse(storage.data[STORAGE_KEY]).mode).toBe("resident");
  off();
  setState((s) => s);
  expect(fn).toHaveBeenCalledTimes(1);
});

test("storage rusak -> state awal tanpa melempar", () => {
  __initStoreForTest({ storage: memStorage({ [STORAGE_KEY]: "{rusak" }), now: () => NOW });
  expect(getState().version).toBe(1);
});

test("versi lama diganti state awal", () => {
  __initStoreForTest({ storage: memStorage({ [STORAGE_KEY]: JSON.stringify({ version: 0, mode: "x" }) }), now: () => NOW });
  expect(getState().version).toBe(1);
  expect(getState().mode).toBe("buyer");
});

test("tanpa storage tetap jalan di memori", () => {
  __initStoreForTest({ storage: null, now: () => NOW });
  setState((s) => ({ ...s, mode: "resident" }));
  expect(getState().mode).toBe("resident");
});

test("event storage dari tab lain memperbarui state", () => {
  const fn = jest.fn();
  subscribe(fn);
  const other = { ...buildInitialState(NOW), mode: "resident" };
  window.dispatchEvent(new StorageEvent("storage", { key: STORAGE_KEY, newValue: JSON.stringify(other) }));
  expect(getState().mode).toBe("resident");
  expect(fn).toHaveBeenCalled();
});

test("resetState mengembalikan IPL belum dibayar", () => {
  setState((s) => ({ ...s, bills: { ...s.bills, ipl: s.bills.ipl.map((b, i) => (i === 0 ? { ...b, status: "paid" } : b)) } }));
  expect(getState().bills.ipl[0].status).toBe("paid");
  resetState();
  expect(getState().bills.ipl[0].status).toBe("unpaid");
});

test("wait selesai cepat saat latensi 0", async () => {
  await expect(wait()).resolves.toBeUndefined();
});
