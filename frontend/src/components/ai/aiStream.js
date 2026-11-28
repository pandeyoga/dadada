// Pembaca SSE untuk POST /api/ai/conversations/{id}/messages.
// `createSseParser` aman terhadap potongan yang terputus di tengah event / di tengah baris.
import { API, TOKEN_KEY, renewSession } from "@/services/apiClient";

export function createSseParser(onEvent) {
  let buf = "";
  const emit = (block) => {
    const data = block.split("\n")
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.slice(5).replace(/^ /, ""))
      .join("\n");
    if (!data) return;
    try { onEvent(JSON.parse(data)); } catch { /* event rusak diabaikan */ }
  };
  return {
    push(chunk) {
      buf += chunk.replace(/\r\n/g, "\n");
      let i = buf.indexOf("\n\n");
      while (i !== -1) {
        emit(buf.slice(0, i));
        buf = buf.slice(i + 2);
        i = buf.indexOf("\n\n");
      }
    },
    flush() { if (buf.trim()) emit(buf); buf = ""; },
  };
}

async function open(url, body, signal) {
  const doFetch = () => fetch(url, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) || ""}`,
    },
    body: JSON.stringify(body),
  });
  let res = await doFetch();
  if (res.status === 401) {
    try { await renewSession(); res = await doFetch(); } catch { /* biarkan 401 */ }
  }
  return res;
}

/** Kirim pesan dan alirkan event ke `onEvent`. Melempar Error berbahasa Indonesia bila gagal. */
export async function streamMessage(convId, body, { onEvent, signal }) {
  let res;
  try {
    res = await open(`${API}/ai/conversations/${convId}/messages`, body, signal);
  } catch (e) {
    if (e?.name === "AbortError") return;
    throw new Error("Tidak bisa terhubung ke server.");
  }
  if (!res.ok || !res.body) {
    if ([404, 501, 502, 503].includes(res.status)) throw new Error("Fitur AI belum tersedia di server ini.");
    if (res.status === 403) throw new Error("Anda tidak punya izin memakai Estora AI.");
    throw new Error("Pesan gagal dikirim. Coba lagi.");
  }
  const parser = createSseParser(onEvent);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.push(dec.decode(value, { stream: true }));
    }
    parser.push(dec.decode());
    parser.flush();
  } catch (e) {
    if (e?.name !== "AbortError") throw new Error("Koneksi terputus saat menerima jawaban.");
  }
}

/** Terapkan satu event ke pesan asisten (murni, mudah diuji). */
export function applyEvent(msg, ev) {
  const m = {
    ...msg,
    steps: [...(msg.steps || [])],
    actions: [...(msg.actions || [])],
    artifacts: [...(msg.artifacts || [])],
  };
  switch (ev.type) {
    case "step_started":
      m.steps.push({ id: ev.id, tool: ev.tool, label: ev.label, status: "running" });
      break;
    case "step_done":
      m.steps = m.steps.map((s) => (s.id === ev.id
        ? { ...s, status: ev.ok === false ? "failed" : "done", summary: ev.summary, ms: ev.ms } : s));
      break;
    case "text_delta": m.text = (m.text || "") + (ev.text || ""); break;
    case "action_proposed": if (ev.action) m.actions.push(ev.action); break;
    case "artifact": if (ev.artifact) m.artifacts.push(ev.artifact); break;
    case "done": m.id = ev.message_id || m.id; m.streaming = false; break;
    case "error": m.error = ev.message || "Terjadi kesalahan."; m.streaming = false; break;
    default: break;
  }
  return m;
}
