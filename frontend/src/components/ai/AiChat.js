import React, { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import AiMessage from "./AiMessage";
import AiComposer from "./AiComposer";
import { getConversation, friendlyError } from "./aiApi";
import { streamMessage, applyEvent } from "./aiStream";

const textOf = (m) => {
  if (typeof m.text === "string") return m.text;
  if (typeof m.content === "string") return m.content;
  if (Array.isArray(m.content)) return m.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  return "";
};
export const normalizeMessage = (m) => ({
  id: m.id, role: m.role === "user" ? "user" : "assistant", text: textOf(m),
  steps: m.steps || [], actions: m.actions || [], artifacts: m.artifacts || [],
});

const SUGGESTIONS = [
  "Buatkan laporan funnel penjualan bulan ini per sumber lead",
  "Siapa lead panas yang belum dijadwalkan survei?",
  "Tunggakan pembeli yang jatuh tempo minggu ini",
];

/**
 * Kolom chat. `ensureConversation()` membuat percakapan bila belum ada dan mengembalikan id-nya.
 */
export default function AiChat({
  conversationId, ensureConversation, status, role, onRole, web, onWeb,
  onArtifact, onActivity, initialPrompt,
}) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadErr, setLoadErr] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef(null);
  const skipLoad = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (!conversationId) { setMessages([]); setLoadErr(""); return undefined; }
    if (skipLoad.current === conversationId) { skipLoad.current = null; return undefined; }
    let alive = true;
    setLoading(true); setLoadErr("");
    getConversation(conversationId).then((c) => {
      if (!alive) return;
      const msgs = (c?.messages || []).map(normalizeMessage);
      setMessages(msgs);
      const last = [...msgs].reverse().flatMap((m) => m.artifacts || [])[0];
      if (last) onArtifact?.(last);
    }).catch((e) => { if (alive) { setMessages([]); setLoadErr(friendlyError(e, "Gagal memuat percakapan.")); } })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "end" }); }, [messages]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const patchLast = useCallback((fn) => setMessages((ms) => {
    const copy = [...ms];
    copy[copy.length - 1] = fn(copy[copy.length - 1]);
    return copy;
  }), []);

  const send = async ({ text, attachments }) => {
    let id;
    try {
      const had = !!conversationId;
      id = await ensureConversation();
      if (!had) skipLoad.current = id;
    } catch (e) {
      setMessages((ms) => [...ms, { role: "assistant", text: "", error: friendlyError(e, "Gagal membuat percakapan.") }]);
      return;
    }
    setMessages((ms) => [...ms,
      { id: `u${Date.now()}`, role: "user", text },
      { id: `a${Date.now()}`, role: "assistant", text: "", steps: [], actions: [], artifacts: [], streaming: true }]);
    const ctl = new AbortController();
    abortRef.current = ctl;
    setStreaming(true);
    try {
      await streamMessage(id, { text, role, web_research: !!web, attachments }, {
        signal: ctl.signal,
        onEvent: (ev) => {
          patchLast((m) => applyEvent(m, ev));
          if (ev.type === "artifact") onArtifact?.(ev.artifact);
        },
      });
    } catch (e) {
      patchLast((m) => ({ ...m, error: e.message, streaming: false }));
    } finally {
      patchLast((m) => ({ ...m, streaming: false }));
      setStreaming(false);
      abortRef.current = null;
      onActivity?.(id);
    }
  };

  const stop = () => abortRef.current?.abort();
  const budgetStop = status?.budget?.state === "stop";

  return (
    <>
      <div className="flex-1 overflow-auto px-7 pb-2 pt-7" aria-live="polite">
        <div className="mx-auto flex max-w-[760px] flex-col gap-[22px]">
          {loading ? <p className="text-sm text-[#3E5653]">Memuat percakapan…</p> : null}
          {loadErr ? <p role="alert" className="text-sm text-[#9B1C1C]">{loadErr}</p> : null}
          {!loading && !loadErr && !messages.length ? (
            <div className="mt-10 flex flex-col items-center gap-4 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#006284] text-white"><Sparkles className="h-6 w-6" aria-hidden="true" /></span>
              <h2 className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-2xl text-[#12312F]">Apa yang ingin Anda kerjakan?</h2>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" onClick={() => send({ text: s, attachments: [] })}
                    className="min-h-[44px] rounded-[10px] border border-[#B9CFC8] bg-white px-3 text-left text-[13px] font-semibold text-[#12312F] hover:bg-[#EEF6F3]">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          {messages.map((m, i) => <AiMessage key={m.id || i} message={m} onOpenArtifact={onArtifact} />)}
          <div ref={endRef} />
        </div>
      </div>
      <AiComposer onSend={send} onStop={stop} streaming={streaming}
        disabled={budgetStop && !status?.budget?.exempt}
        disabledReason="Anggaran AI bulan ini habis."
        webResearchAvailable={!!status?.web_research_enabled}
        role={role} onRole={onRole} web={web} onWeb={onWeb} initialText={initialPrompt || ""} />
    </>
  );
}
