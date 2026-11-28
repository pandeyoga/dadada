// Klien JSON untuk asisten pembeli "Tanya Estora" (/api/portal/ai/*). Memakai klien portal
// (token pembeli), bukan klien staf.
import portalApi from "@/services/portalClient";

const unwrap = (res) => {
  const d = res?.data;
  return d && typeof d === "object" && !Array.isArray(d) && "data" in d ? d.data : d;
};

/** Pesan galat ramah; 404/5xx = backend belum siap. */
export function portalAiError(e, fallback = "Terjadi masalah. Coba lagi.") {
  const st = e?.response?.status;
  if (!e?.response) return "Tidak bisa terhubung ke server.";
  if ([404, 501, 502, 503].includes(st)) return "Asisten belum tersedia.";
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
}

export const getStatus = async () => unwrap(await portalApi.get("/portal/ai/status"));
export const ackNotice = async () => unwrap(await portalApi.post("/portal/ai/notice/ack", {}));
export const stopAssistant = async () => unwrap(await portalApi.post("/portal/ai/stop", {}));
export const resumeAssistant = async () => unwrap(await portalApi.post("/portal/ai/resume", {}));
export const listConversations = async () => unwrap(await portalApi.get("/portal/ai/conversations"));
export const createConversation = async () => unwrap(await portalApi.post("/portal/ai/conversations", {}));
export const getConversation = async (id) => unwrap(await portalApi.get(`/portal/ai/conversations/${id}`));
export const deleteAllConversations = async () => unwrap(await portalApi.delete("/portal/ai/conversations"));
export const confirmAction = async (id) => unwrap(await portalApi.post(`/portal/ai/actions/${id}/confirm`, {}));
export const cancelAction = async (id) => unwrap(await portalApi.post(`/portal/ai/actions/${id}/cancel`, {}));
