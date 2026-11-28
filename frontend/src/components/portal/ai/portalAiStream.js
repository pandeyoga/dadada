// Pembaca SSE untuk POST /api/portal/ai/conversations/{id}/messages (token pembeli).
import { API } from "@/services/apiClient";
import { PORTAL_TOKEN_KEY } from "@/services/portalClient";

/** Parser SSE yang aman terhadap potongan terputus di tengah event / baris. */
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

/** Kirim pesan pembeli dan alirkan event ke `onEvent`. Melempar Error berbahasa Indonesia. */
export async function streamPortalMessage(convId, text, { onEvent, signal }) {
  let res;
  try {
    res = await fetch(`${API}/portal/ai/conversations/${convId}/messages`, {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        Authorization: `Bearer ${localStorage.getItem(PORTAL_TOKEN_KEY) || ""}`,
      },
      body: JSON.stringify({ text }),
    });
  } catch (e) {
    if (e?.name === "AbortError") return;
    throw new Error("Tidak bisa terhubung ke server.");
  }
  if (!res.ok || !res.body) {
    if ([404, 501, 502, 503].includes(res.status)) throw new Error("Asisten belum tersedia.");
    if (res.status === 403) throw new Error("Asisten sedang tidak aktif.");
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

/** Terapkan satu event ke pesan asisten (murni). */
export function applyPortalEvent(msg, ev) {
  const m = { ...msg, steps: [...(msg.steps || [])], actions: [...(msg.actions || [])] };
  switch (ev.type) {
    case "step_started":
      m.steps.push({ id: ev.id, label: ev.label || ev.tool, status: "running" });
      break;
    case "step_done":
      m.steps = m.steps.map((s) => (s.id === ev.id ? { ...s, status: ev.ok === false ? "failed" : "done" } : s));
      break;
    case "text_delta": m.text = (m.text || "") + (ev.text || ""); break;
    case "action_proposed": if (ev.action) m.actions.push(ev.action); break;
    case "handoff": if (ev.ticket) m.ticket = ev.ticket; break;
    case "done": m.id = ev.message_id || m.id; m.streaming = false; break;
    case "error": m.error = ev.message || "Terjadi kesalahan."; m.streaming = false; break;
    default: break;
  }
  return m;
}
