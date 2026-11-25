import { buildInitialState, STATE_VERSION } from "./initialState";
import { clockMode, offsetFor } from "./clock";

export const STORAGE_KEY = "rdg_proto_state";
export { STATE_VERSION };

let storage = null;
let nowFn = () => Date.now();
// Uji menyuntik jam lewat __initStoreForTest; jam itu tidak diganti oleh mode jam demo.
let clockInjected = false;
let state = null;
const listeners = new Set();

/** Pasang jam untuk mode 'anchored' (tanggal demo, jam sungguhan) atau 'real'; selisih dihitung sekali. */
function applyClock(mode) {
  if (clockInjected) return;
  const offset = offsetFor(mode, Date.now());
  nowFn = () => Date.now() + offset;
}

const clockOf = (s) => clockMode(s && s.session && s.session.demoClock);

function defaultStorage() {
  try {
    return typeof window !== "undefined" ? window.localStorage || null : null;
  } catch (e) {
    return null;
  }
}

function parse(raw) {
  try {
    const obj = JSON.parse(raw);
    return obj && obj.version === STATE_VERSION ? obj : null;
  } catch (e) {
    return null;
  }
}

function readSaved() {
  try {
    const raw = storage ? storage.getItem(STORAGE_KEY) : null;
    return raw ? parse(raw) : null;
  } catch (e) {
    return null; /* storage tidak terbaca: pakai state awal */
  }
}

function load() {
  const saved = readSaved();
  applyClock(clockOf(saved));
  return saved || buildInitialState(nowFn(), { demoClock: clockOf(saved) });
}

function persist() {
  try {
    if (storage) storage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    /* penuh/diblokir: tetap di memori */
  }
}

function notify() {
  listeners.forEach((fn) => fn());
}

/** Jam prototipe (epoch ms). Semua pembaca waktu memakai ini atau useNow(), bukan Date.now(). */
export const now = () => {
  if (!state) getState();
  return nowFn();
};

export function getState() {
  if (!state) {
    storage = defaultStorage();
    state = load();
  }
  return state;
}

export function setState(updater) {
  state = updater(getState());
  persist();
  notify();
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function resetState() {
  state = buildInitialState(nowFn(), { demoClock: clockOf(getState()) });
  persist();
  notify();
}

/** Ganti mode jam ('anchored' | 'real') lalu bangun ulang data contoh terhadap jam yang baru. */
export function setDemoClock(mode) {
  const m = clockMode(mode);
  getState();
  applyClock(m);
  state = buildInitialState(nowFn(), { demoClock: m });
  persist();
  notify();
}

export function __initStoreForTest(opts = {}) {
  storage = "storage" in opts ? opts.storage : null;
  clockInjected = true;
  nowFn = opts.now || (() => Date.now());
  state = load();
  listeners.clear();
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key !== STORAGE_KEY) return;
    if (!state) getState(); // pasang storage dan jam lebih dulu
    const next = e.newValue ? parse(e.newValue) : null;
    const mode = next ? clockOf(next) : clockOf(state);
    if (mode !== clockOf(state)) applyClock(mode); // tab lain mengganti mode jam
    state = next || buildInitialState(nowFn(), { demoClock: mode });
    notify();
  });
}
