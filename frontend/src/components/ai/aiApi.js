// Klien JSON untuk endpoint Estora AI (Task 7/9/10). Satu pintu supaya komponen tidak
// menebak bentuk respons: `unwrap` menerima `{data: ...}` maupun badan polos.
import api from "@/services/apiClient";

export const unwrap = (res) => {
  const d = res?.data;
  return d && typeof d === "object" && !Array.isArray(d) && "data" in d ? d.data : d;
};

/** Pesan galat ramah untuk pengguna (404/5xx = backend belum siap). */
export function friendlyError(e, fallback = "Terjadi masalah. Coba lagi.") {
  const st = e?.response?.status;
  if (!e?.response) return "Tidak bisa terhubung ke server.";
  if (st === 404 || st === 501 || st === 502 || st === 503) return "Fitur AI belum tersedia di server ini.";
  if (st === 403) return "Anda tidak punya izin untuk tindakan ini.";
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
}

const get = async (url, params) => unwrap(await api.get(url, { params }));
const post = async (url, body) => unwrap(await api.post(url, body ?? {}));
const put = async (url, body) => unwrap(await api.put(url, body ?? {}));

// ---- Copilot (Task 7)
export const getStatus = () => get("/ai/status");
export const listConversations = (q) => get("/ai/conversations", q ? { q } : undefined);
export const createConversation = (role) => post("/ai/conversations", { role });
export const renameConversation = async (id, title) =>
  unwrap(await api.patch(`/ai/conversations/${id}`, { title }));
export const deleteConversation = async (id) => unwrap(await api.delete(`/ai/conversations/${id}`));
export const getConversation = (id) => get(`/ai/conversations/${id}`);
export const approveAction = (id, edits) => post(`/ai/actions/${id}/approve`, edits ? { edits } : {});
export const rejectAction = (id, reason) => post(`/ai/actions/${id}/reject`, { reason: reason || "" });
export const uploadAttachment = async (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return unwrap(await api.post("/ai/files", fd, { headers: { "Content-Type": "multipart/form-data" } }));
};
export async function downloadArtifact(artifact, kind) {
  const res = await api.get(`/ai/artifacts/${artifact.id}/${kind}`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(artifact.title || "laporan").replace(/[^\w\- ]+/g, "")}.${kind}`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
/** Jalur unduhan (dipakai tombol & diuji). */
export const artifactPath = (artifact, kind) => `/ai/artifacts/${artifact.id}/${kind}`;

// ---- Pengaturan & kanal (Task 7/9/10)
export const getSettings = () => get("/ai/settings");
export const saveSettings = (patch) => put("/ai/settings", patch);
export const saveApiKey = (key) => put("/ai/settings/api-key", { key });
export const testConnection = () => post("/ai/settings/test");
export const getUsage = (month) => get("/ai/usage", month ? { month } : undefined);
export const getAccuracy = () => get("/ai/accuracy");
export const setCategoryMode = (cat, mode) => put(`/ai/categories/${encodeURIComponent(cat)}`, { mode });
export const getChannels = () => get("/ai/channels");
export const saveChannels = (body) => put("/ai/channels", body);
export const disableUnofficial = () => post("/ai/channels/unofficial/disable");

// ---- Inbox AI (Task 10)
export const getInboxAi = (convId) => get(`/ai/inbox/conversations/${convId}`);
export const getInboxLabels = (ids) => get("/ai/inbox/labels", { ids: ids.join(",") });
export const sendDraft = (id, text) => post(`/ai/inbox/drafts/${id}/send`, text != null ? { text } : {});
export const rewriteDraft = (id, instruction) => post(`/ai/inbox/drafts/${id}/rewrite`, { instruction });
export const discardDraft = (id) => post(`/ai/inbox/drafts/${id}/discard`);
export const reviewSample = (id, verdict) => post(`/ai/inbox/samples/${id}/review`, { verdict });
export const requestUnofficialOptin = (convId) => post(`/ai/inbox/conversations/${convId}/optin-unofficial`);
