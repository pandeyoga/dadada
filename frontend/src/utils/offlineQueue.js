import axios from "axios";
import { API } from "../services/apiClient";

/**
 * Antrean offline HP gudang — aksi disimpan lokal saat sinyal hilang, disinkron FIFO saat online.
 * Setiap aksi membawa Idempotency-Key unik → server menolak dobel walau dikirim ulang.
 */
const Q_KEY = "kn_offline_queue";
const R_KEY = "kn_offline_results";
const listeners = new Set();

const read = (k) => { try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch (_) { return []; } };
const write = (k, v) => { localStorage.setItem(k, JSON.stringify(v)); listeners.forEach((fn) => fn()); };
export const newKey = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `k-${Date.now()}-${Math.random().toString(16).slice(2)}`);
export const isNetworkError = (e) => !e?.response || e.code === "ERR_NETWORK";
export const pending = () => read(Q_KEY);
export const results = () => read(R_KEY);
export const subscribe = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
export const clearResults = () => write(R_KEY, []);
export const removePending = (key) => write(Q_KEY, read(Q_KEY).filter((it) => it.key !== key));

export function enqueue(item) {
  const q = read(Q_KEY);
  q.push({ ...item, queued_at: new Date().toISOString() });
  write(Q_KEY, q);
  return item.key;
}

function pushResult(r) {
  const rs = read(R_KEY);
  rs.unshift({ ...r, at: new Date().toISOString() });
  write(R_KEY, rs.slice(0, 20));
}

let syncing = false;
/** Kirim antrean berurutan. Berhenti di aksi pertama yang masih gagal jaringan. */
export async function syncQueue() {
  if (syncing || !navigator.onLine) return { sent: 0 };
  syncing = true;
  let sent = 0;
  try {
    let q = read(Q_KEY);
    while (q.length) {
      const it = q[0];
      try {
        const res = await axios({ method: it.method || "post", url: it.url, data: it.data, params: it.params, headers: { "Idempotency-Key": it.key } });
        pushResult({ ok: true, label: it.label, key: it.key, status: res.status, replay: res.headers?.["x-idempotent-replay"] === "true", detail: res.data?.message || "" });
      } catch (e) {
        if (isNetworkError(e)) break;                          // masih offline → coba lagi nanti
        const d = e.response?.data?.detail;
        pushResult({ ok: false, label: it.label, key: it.key, status: e.response?.status, detail: (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || "Ditolak server." });
      }
      q = q.slice(1); write(Q_KEY, q); sent += 1;
    }
  } finally { syncing = false; }
  return { sent };
}

/** POST dengan Idempotency-Key; bila jaringan putus → masuk antrean, kembalikan {queued:true}. */
export async function offlinePost(url, data, { params, label } = {}) {
  const key = newKey();
  try {
    const res = await axios.post(url, data, { params, headers: { "Idempotency-Key": key } });
    return { queued: false, data: res.data, status: res.status };
  } catch (e) {
    if (!isNetworkError(e)) throw e;
    enqueue({ key, method: "post", url, data, params, label });
    return { queued: true, key };
  }
}

/** Jejak pindai saat offline: dicatat ke server begitu online (POST /rfid/roll-scans). */
export const queueScan = (code, extra = {}) => enqueue({ key: newKey(), method: "post", url: `${API}/rfid/roll-scans`, data: { code, ...extra, scanned_at: new Date().toISOString() }, label: `Pindai ${code}` });

if (typeof window !== "undefined") {
  window.addEventListener("online", () => { syncQueue(); });
}
