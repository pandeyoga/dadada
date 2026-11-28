import React, { useCallback, useEffect, useRef, useState } from "react";
import { X, Send, MoreVertical, Headset } from "lucide-react";
import PortalAiMessage from "./PortalAiMessage";
import { streamPortalMessage, applyPortalEvent } from "./portalAiStream";
import {
  getStatus, ackNotice, stopAssistant, resumeAssistant, listConversations, createConversation,
  getConversation, deleteAllConversations, portalAiError,
} from "./portalAiApi";

const toUi = (m) => ({
  id: m.id, role: m.role === "user" ? "user" : "assistant",
  text: m.text ?? m.content ?? "", steps: m.steps || [], actions: m.actions || [], ticket: m.ticket || null,
});

/** Panel chat "Tanya Estora": layar penuh di < 640 px, kartu 380 px di layar lebar. */
export default function PortalAiPanel({ onClose }) {
  const [status, setStatus] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const [info, setInfo] = useState("");
  const abortRef = useRef(null);
  const endRef = useRef(null);

  const refreshStatus = useCallback(async () => {
    try { setStatus(await getStatus()); setLoadErr(""); } catch (e) {
      setStatus({ enabled: false }); setLoadErr(portalAiError(e));
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      let st;
      try { st = await getStatus(); } catch (e) { if (alive) { setStatus({ enabled: false }); setLoadErr(portalAiError(e)); } return; }
      if (!alive) return;
      setStatus(st);
      if (!st?.enabled) return;
      try {
        const list = await listConversations();
        const first = Array.isArray(list) ? list[0] : (list?.items || [])[0];
        if (first?.id) {
          const conv = await getConversation(first.id);
          if (!alive) return;
          setConvId(first.id);
          setMessages((conv?.messages || []).map(toUi));
        }
      } catch { /* riwayat gagal dimuat: mulai percakapan baru saat kirim */ }
    })();
    return () => { alive = false; abortRef.current?.abort(); };
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "end" }); }, [messages]);

  const send = async (raw) => {
    const t = (raw ?? text).trim();
    if (!t || busy) return;
    setText(""); setBusy(true); setInfo("");
    const aid = `a-${Date.now()}`;
    setMessages((ms) => [...ms, { id: `u-${Date.now()}`, role: "user", text: t },
      { id: aid, role: "assistant", text: "", streaming: true, steps: [], actions: [] }]);
    const patch = (fn) => setMessages((ms) => ms.map((m) => (m.id === aid ? fn(m) : m)));
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      let id = convId;
      if (!id) {
        const c = await createConversation();
        id = c?.id || c?.conversation?.id;
        if (!id) throw new Error("Asisten belum tersedia.");
        setConvId(id);
      }
      await streamPortalMessage(id, t, {
        signal: ctrl.signal,
        onEvent: (ev) => patch((m) => applyPortalEvent(m, ev)),
      });
      patch((m) => ({ ...m, streaming: false }));
      refreshStatus();
    } catch (e) {
      patch((m) => ({ ...m, streaming: false, error: e?.message || portalAiError(e) }));
    } finally { setBusy(false); }
  };

  const ack = async () => {
    try { await ackNotice(); } catch { /* tetap tutup pemberitahuan di layar */ }
    setStatus((s) => ({ ...s, noticed: true }));
  };
  const stop = async () => {
    setMenu(false);
    try { await stopAssistant(); await refreshStatus(); } catch (e) { setInfo(portalAiError(e)); }
  };
  const resume = async () => {
    try { await resumeAssistant(); await refreshStatus(); } catch (e) { setInfo(portalAiError(e)); }
  };
  const wipe = async () => {
    setMenu(false);
    if (typeof window !== "undefined" && window.confirm && !window.confirm("Hapus semua riwayat chat Anda dengan asisten?")) return;
    try { await deleteAllConversations(); setMessages([]); setConvId(null); setInfo("Riwayat chat dihapus."); } catch (e) { setInfo(portalAiError(e)); }
  };

  const quota = status?.quota;
  const remaining = quota ? Math.max(0, (quota.limit ?? 0) - (quota.used ?? 0)) : null;
  const unavailable = status && status.enabled === false;
  const showNotice = status?.enabled && status.noticed === false && !status.stopped;
  const stopped = status?.enabled && status.stopped;

  return (
    <section role="dialog" aria-label="Tanya Estora" data-testid="portal-ai-panel"
      className="fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:bottom-4 sm:right-4 sm:h-[600px] sm:max-h-[calc(100vh-2rem)] sm:w-[380px] sm:rounded-2xl sm:border sm:shadow-2xl">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="m-0 font-heading text-sm font-semibold">Tanya Estora</p>
          {remaining !== null && !unavailable ? (
            <p className="m-0 text-xs text-slate-500" data-testid="portal-ai-quota">Sisa {remaining}/{quota.limit} pesan hari ini</p>
          ) : null}
        </div>
        <div className="relative flex items-center gap-1">
          {status?.enabled ? (
            <button type="button" aria-label="Menu" aria-expanded={menu} onClick={() => setMenu((v) => !v)}
              className="grid h-10 w-10 place-items-center rounded-lg hover:bg-slate-100"><MoreVertical className="h-4 w-4" /></button>
          ) : null}
          <button type="button" aria-label="Tutup" onClick={onClose}
            className="grid h-10 w-10 place-items-center rounded-lg hover:bg-slate-100"><X className="h-4 w-4" /></button>
          {menu ? (
            <div role="menu" className="absolute right-0 top-11 z-10 w-56 rounded-xl border bg-white p-1 text-sm shadow-lg">
              <button type="button" role="menuitem" onClick={stop} className="block min-h-[40px] w-full rounded-lg px-3 text-left hover:bg-slate-100">Berhenti pakai asisten</button>
              <button type="button" role="menuitem" onClick={wipe} className="block min-h-[40px] w-full rounded-lg px-3 text-left hover:bg-slate-100">Hapus riwayat chat</button>
            </div>
          ) : null}
        </div>
      </header>

      {status && status.enabled && status.effective_mode && status.effective_mode !== "live" ? (
        <p role="status" className="m-0 bg-amber-50 px-4 py-1.5 text-xs text-amber-800"><b>Mode simulasi.</b> Jawaban belum dari asisten sungguhan.</p>
      ) : null}

      {!status ? (
        <p className="m-0 flex-1 p-4 text-sm text-slate-500">Memuat…</p>
      ) : unavailable ? (
        <div className="flex-1 p-4 text-sm text-slate-600">
          <p className="m-0 font-semibold">Asisten belum tersedia</p>
          <p className="m-0 mt-1">{status.notice_text || loadErr || "Silakan hubungi CS kami lewat tab Komplain."}</p>
        </div>
      ) : showNotice ? (
        <div className="flex flex-1 flex-col gap-3 p-4 text-sm text-slate-700" data-testid="portal-ai-notice">
          <p className="m-0 whitespace-pre-wrap">{status.notice_text || "Tanya Estora adalah asisten AI. Jawabannya bisa keliru; untuk hal penting, hubungi CS kami."}</p>
          <button type="button" onClick={ack} className="min-h-[44px] self-start rounded-lg bg-indigo-600 px-5 font-semibold text-white hover:bg-indigo-700">Mengerti</button>
        </div>
      ) : stopped ? (
        <div className="flex flex-1 flex-col gap-3 p-4 text-sm text-slate-700">
          <p className="m-0">Anda berhenti memakai asisten. Riwayat tetap tersimpan sampai Anda menghapusnya.</p>
          <button type="button" onClick={resume} className="min-h-[44px] self-start rounded-lg border px-5 font-semibold hover:bg-slate-100">Pakai asisten lagi</button>
        </div>
      ) : (
        <>
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
            {messages.length === 0 ? (
              <p className="m-0 text-sm text-slate-500">Halo! Tanyakan tagihan, progres rumah, dokumen, atau komplain Anda.</p>
            ) : null}
            {messages.map((m) => <PortalAiMessage key={m.id} message={m} />)}
            {info ? <p role="status" className="m-0 text-xs text-slate-500">{info}</p> : null}
            <div ref={endRef} />
          </div>
          <div className="border-t p-3">
            <button type="button" disabled={busy} onClick={() => send("Bicara dengan CS")}
              className="mb-2 inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-3 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-60">
              <Headset className="h-3.5 w-3.5" aria-hidden="true" /> Bicara dengan CS
            </button>
            <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2">
              <input value={text} onChange={(e) => setText(e.target.value)} aria-label="Tulis pesan" maxLength={2000}
                placeholder="Tulis pertanyaan Anda…" data-testid="portal-ai-input"
                className="min-h-[44px] min-w-0 flex-1 rounded-lg border px-3 text-sm" />
              <button type="submit" disabled={busy || !text.trim()} aria-label="Kirim pesan"
                className="grid h-11 w-11 place-items-center rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"><Send className="h-4 w-4" /></button>
            </form>
          </div>
        </>
      )}
    </section>
  );
}
