import { buildInitialState } from "./initialState";

export const STORAGE_KEY = "rdg_proto_state";
export const STATE_VERSION = 1;

let storage = null;
let nowFn = () => Date.now();
let state = null;
const listeners = new Set();

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

function load() {
  try {
    const raw = storage ? storage.getItem(STORAGE_KEY) : null;
    if (raw) {
      const saved = parse(raw);
      if (saved) return saved;
    }
  } catch (e) {
    /* storage tidak terbaca: pakai state awal */
  }
  return buildInitialState(nowFn());
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

export const now = () => nowFn();

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
  state = buildInitialState(nowFn());
  persist();
  notify();
}

export function __initStoreForTest(opts = {}) {
  storage = "storage" in opts ? opts.storage : null;
  nowFn = opts.now || (() => Date.now());
  state = load();
  listeners.clear();
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key !== STORAGE_KEY) return;
    const next = e.newValue ? parse(e.newValue) : null;
    state = next || buildInitialState(nowFn());
    notify();
  });
}
