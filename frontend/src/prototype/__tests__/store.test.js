import screens from "@/prototype/screens.json";
import { getState, setState, subscribe, resetState, __initStoreForTest, STORAGE_KEY, STATE_VERSION } from "@/prototype/services/store";
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
  expect(getState().version).toBe(STATE_VERSION);
});

test("versi lama diganti state awal", () => {
  __initStoreForTest({ storage: memStorage({ [STORAGE_KEY]: JSON.stringify({ version: 0, mode: "x" }) }), now: () => NOW });
  expect(getState().version).toBe(STATE_VERSION);
  expect(getState().mode).toBe("buyer");
});

test("state v1 tersimpan (bentuk lama) diganti fixture baru", () => {
  expect(STATE_VERSION).toBe(3);
  const v1 = { ...buildInitialState(NOW), version: 1, mode: "resident" };
  v1.security = { ...v1.security, energy: { kwh: 142, lastKwh: 131 } };
  __initStoreForTest({ storage: memStorage({ [STORAGE_KEY]: JSON.stringify(v1) }), now: () => NOW });
  expect(getState().version).toBe(3);
  expect(getState().mode).toBe("buyer");
  expect(getState().security.energy.months.length).toBeGreaterThan(0);
});

test("state awal baru tersimpan dengan versi yang sama dan bertahan saat dimuat ulang", () => {
  const storage = memStorage();
  __initStoreForTest({ storage, now: () => NOW });
  setState((s) => ({ ...s, mode: "resident" }));
  expect(JSON.parse(storage.data[STORAGE_KEY]).version).toBe(STATE_VERSION);
  __initStoreForTest({ storage, now: () => NOW });
  expect(getState().mode).toBe("resident");
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

test("manager tidak menyimpan salinan tiket (dibaca dari care.tickets)", () => {
  expect(buildInitialState(NOW).manager.tickets).toBeUndefined();
});

test("semua link fixture adalah rute di screens.json", () => {
  const paths = new Set(screens.map((s) => s.path));
  const links = [];
  const walk = (v) => {
    if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === "object") {
      Object.entries(v).forEach(([k, x]) => {
        if ((k === "link" || k === "to") && typeof x === "string") links.push(x);
        else walk(x);
      });
    }
  };
  walk(buildInitialState(Date.now()));
  expect(links.length).toBeGreaterThan(0);
  links.forEach((l) => expect(paths.has(l)).toBe(true));
});

describe("jam demo (tanpa jam suntikan)", () => {
  const WIB = (s) => Date.parse(`${s}+07:00`);
  // Modul store segar: jalur produksi (localStorage jsdom, jam bawaan), bukan __initStoreForTest.
  const freshStore = () => {
    let mod;
    jest.isolateModules(() => { mod = require("@/prototype/services/store"); });
    return mod;
  };
  let real;
  beforeEach(() => {
    window.localStorage.clear();
    real = WIB("2026-12-15T10:30:00");
    jest.spyOn(Date, "now").mockImplementation(() => real);
  });
  afterEach(() => {
    jest.restoreAllMocks();
    window.localStorage.clear();
  });

  test("anchoredOffset: jam WIB hari ini dipindah ke Rabu, 25 Nov 2026 (juga dekat tengah malam)", () => {
    const { anchoredOffset, DEMO_DATE } = require("@/prototype/services/clock");
    expect(DEMO_DATE).toBe("2026-11-25");
    const at = (s) => WIB(s) + anchoredOffset(WIB(s));
    expect(at("2026-12-15T10:30:00")).toBe(WIB("2026-11-25T10:30:00"));
    expect(at("2026-12-15T23:59:30")).toBe(WIB("2026-11-25T23:59:30"));
    expect(at("2026-12-16T00:00:10")).toBe(WIB("2026-11-25T00:00:10"));
    expect(at("2026-11-25T09:41:00")).toBe(WIB("2026-11-25T09:41:00"));
  });

  test("bawaan 'anchored': tanggal demo 25 Nov, jam tetap berjalan", () => {
    const store = freshStore();
    expect(store.getState().session.demoClock).toBe("anchored");
    expect(store.now()).toBe(WIB("2026-11-25T10:30:00"));
    real += 5000;
    expect(store.now()).toBe(WIB("2026-11-25T10:30:05"));
    expect(store.getState().buyer.installments.find((i) => i.id === "dp-3").dueDate).toBe("2026-12-10");
  });

  test("setDemoClock('real') memakai tanggal hari ini, membangun ulang data, dan bertahan saat dimuat ulang", () => {
    const store = freshStore();
    store.setState((s) => ({ ...s, session: { ...s.session, persona: "resident", loggedIn: true } }));
    store.setDemoClock("real");
    expect(store.now()).toBe(real);
    expect(store.getState().session).toMatchObject({ demoClock: "real", loggedIn: false });
    expect(Date.parse(store.getState().security.door.changedAt)).toBe(real - 2 * 3600000);
    const again = freshStore();
    expect(again.getState().session.demoClock).toBe("real");
    expect(again.now()).toBe(real);
    again.setDemoClock("anchored");
    expect(again.now()).toBe(WIB("2026-11-25T10:30:00"));
    again.resetState();
    expect(again.getState().session.demoClock).toBe("anchored");
  });

  test("tab lain mengganti mode jam lewat event storage", () => {
    const store = freshStore();
    expect(store.now()).toBe(WIB("2026-11-25T10:30:00"));
    const other = buildInitialState(real, { demoClock: "real" });
    window.dispatchEvent(new StorageEvent("storage", { key: store.STORAGE_KEY, newValue: JSON.stringify(other) }));
    expect(store.now()).toBe(real);
  });
});
