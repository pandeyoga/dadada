import React from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

const asText = (v) => {
  if (v == null) return "";
  if (Array.isArray(v)) return v.map(asText).filter(Boolean).join(" · ");
  if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k.replace(/_/g, " ")} ${asText(x)}`).join(" · ");
  return String(v);
};

/** Ringkasan AI: insights = {score, stage, known, intent, objections[], next_step, next_step_prompt?}. */
export default function AiInsightsPanel({ insights, channel }) {
  const navigate = useNavigate();
  if (!insights) return null;
  const known = asText(insights.known);
  const intent = [asText(insights.intent), asText(insights.objections)].filter(Boolean).join(" · ");
  return (
    <aside aria-label="Ringkasan lead" data-testid="ai-insights"
      className="flex flex-col gap-3 rounded-xl border border-[#D5E0DC] bg-white p-4 shadow-[var(--shadow-card)]">
      <h2 className="m-0 flex items-center gap-1.5 font-['Space_Grotesk',Inter,sans-serif] text-base">
        <Sparkles className="h-4 w-4 text-[#006284]" aria-hidden="true" /> Ringkasan AI
      </h2>
      {insights.score != null || insights.stage ? (
        <div className="grid grid-cols-2 gap-2 text-[13px]">
          {insights.score != null ? <div className="rounded-lg bg-[#F4F7F6] p-2"><span className="text-[#3E5653]">Skor lead</span><br /><b className="text-lg">{insights.score}</b></div> : null}
          {insights.stage ? <div className="rounded-lg bg-[#F4F7F6] p-2"><span className="text-[#3E5653]">Tahap</span><br /><b>{insights.stage}</b></div> : null}
        </div>
      ) : null}
      {known ? <Row title="Yang diketahui" text={known} /> : null}
      {intent ? <Row title="Niat & keberatan" text={intent} /> : null}
      {insights.next_step ? (
        <div className="flex flex-col gap-1.5 text-[13px]">
          <span className="font-semibold text-[#3E5653]">Langkah berikutnya</span>
          <span className="text-[#12312F]">{insights.next_step}</span>
          <button type="button" onClick={() => navigate("/ai", { state: { prompt: insights.next_step_prompt || `Bantu saya: ${insights.next_step}` } })}
            className="min-h-[40px] w-fit rounded-lg border border-[#B9CFC8] bg-white px-3 text-[13px] font-semibold text-[#006284] hover:text-[#00454D]">
            Minta Estora AI menyiapkan
          </button>
        </div>
      ) : null}
      <p className="m-0 text-xs text-[#3E5653]">Riwayat lengkap tersimpan dari chat pertama sampai akad.{channel ? ` Kanal: ${channel}.` : ""}</p>
    </aside>
  );
}

const Row = ({ title, text }) => (
  <div className="flex flex-col gap-0.5 text-[13px]">
    <span className="font-semibold text-[#3E5653]">{title}</span>
    <span className="text-[#12312F]">{text}</span>
  </div>
);
