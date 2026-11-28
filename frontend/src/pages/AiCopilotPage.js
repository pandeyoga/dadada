import React, { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle, FlaskConical } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import AiSidebar from "@/components/ai/AiSidebar";
import AiChat from "@/components/ai/AiChat";
import AiArtifactPanel from "@/components/ai/AiArtifactPanel";
import {
  getStatus, listConversations, createConversation, deleteConversation, friendlyError,
} from "@/components/ai/aiApi";

export function AiBanners({ status }) {
  if (!status) return null;
  const b = status.budget || {};
  return (
    <div className="flex flex-col gap-2 px-7 pt-3" data-testid="ai-banners">
      {status.effective_mode && status.effective_mode !== "live" ? (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-[#F2D7A6] bg-[#FFF4E5] px-3 py-2 text-[13px] text-[#7A3E00]">
          <FlaskConical className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          <span><b>Mode simulasi.</b> Jawaban dibuat dari data contoh, bukan dari Claude sungguhan. Pasang kunci API di Pengaturan AI untuk mode live.</span>
        </div>
      ) : null}
      {b.state === "warn" ? (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-[#F2D7A6] bg-[#FFF4E5] px-3 py-2 text-[13px] text-[#7A3E00]">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          <span>Pemakaian AI bulan ini sudah {Math.round((b.pct || 0) * (b.pct <= 1 ? 100 : 1))}% dari batas. Agen otomatis akan berhenti di 100%.</span>
        </div>
      ) : null}
      {b.state === "stop" ? (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-[#E8C4C0] bg-[#FDF2F1] px-3 py-2 text-[13px] text-[#9B1C1C]">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          <span>Batas biaya AI bulan ini tercapai. Agen otomatis dihentikan; Copilot hanya tersedia untuk pemilik/admin.</span>
        </div>
      ) : null}
    </div>
  );
}

export default function AiCopilotPage() {
  const { user, can } = useAuth();
  const location = useLocation();
  const [status, setStatus] = useState(null);
  const [statusErr, setStatusErr] = useState("");
  const [convs, setConvs] = useState([]);
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState(null);
  const [artifact, setArtifact] = useState(null);
  const [role, setRole] = useState("copilot");
  const [web, setWeb] = useState(false);
  const [prefill, setPrefill] = useState(location.state?.prompt || "");
  const [chatKey, setChatKey] = useState(0);
  const roleRef = useRef(role);
  roleRef.current = role;

  const loadConvs = useCallback(async (q) => {
    try { setConvs((await listConversations(q)) || []); } catch { setConvs([]); }
  }, []);

  useEffect(() => {
    getStatus().then(setStatus).catch((e) => setStatusErr(friendlyError(e)));
  }, []);
  useEffect(() => {
    const t = setTimeout(() => loadConvs(query), 250);
    return () => clearTimeout(t);
  }, [query, loadConvs]);

  const ensure = async () => {
    if (activeId) return activeId;
    const c = await createConversation(roleRef.current);
    setActiveId(c.id);
    return c.id;
  };

  const del = async (c) => {
    if (!window.confirm(`Hapus percakapan "${c.title || "tanpa judul"}"?`)) return;
    try {
      await deleteConversation(c.id);
      if (c.id === activeId) { setActiveId(null); setArtifact(null); }
      loadConvs(query);
    } catch (e) { toast.error(friendlyError(e, "Gagal menghapus percakapan.")); }
  };

  const active = convs.find((c) => c.id === activeId);
  const askAgent = (text) => { setPrefill(text); setChatKey((k) => k + 1); };

  return (
    <div className="-m-4 flex min-h-[calc(100vh-4rem)] flex-wrap bg-[#F4F7F6] font-[Inter,system-ui,sans-serif] text-[#12312F] md:-m-6"
      data-testid="ai-copilot-page">
      <AiSidebar conversations={convs} activeId={activeId} query={query} onQuery={setQuery}
        onSelect={(id) => { setActiveId(id); setArtifact(null); }}
        onNew={() => { setActiveId(null); setArtifact(null); setPrefill(""); setChatKey((k) => k + 1); }}
        onDelete={del} user={user} canSettings={can("ai_settings", "manage")} />
      <main className="flex min-w-0 flex-[999_1_560px] flex-col bg-[#FAFCFB]">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E1EAE7] px-7 py-3.5">
          <h1 className="m-0 text-base font-semibold">{active?.title || "Percakapan baru"}</h1>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E3F2EA] px-2.5 py-1 text-xs font-semibold text-[#14532D]">
            <span className="h-2 w-2 rounded-full bg-[#209F59]" aria-hidden="true" /> Copilot · didukung Claude
          </span>
        </header>
        {statusErr ? <p role="alert" className="mx-7 mt-3 rounded-lg bg-[#FFF4E5] px-3 py-2 text-[13px] text-[#7A3E00]">{statusErr}</p> : null}
        <AiBanners status={status} />
        <AiChat key={chatKey} conversationId={activeId} ensureConversation={ensure} status={status}
          role={role} onRole={setRole} web={web} onWeb={setWeb} initialPrompt={prefill}
          onArtifact={setArtifact} onActivity={() => loadConvs(query)} />
      </main>
      {artifact ? <AiArtifactPanel artifact={artifact} onClose={() => setArtifact(null)} onAskAgent={askAgent} /> : null}
    </div>
  );
}
