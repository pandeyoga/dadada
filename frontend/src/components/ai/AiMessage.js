import React, { useMemo } from "react";
import { FileText } from "lucide-react";
import AiSteps from "./AiSteps";
import AiActionCard from "./AiActionCard";
import { renderMarkdown } from "./aiMarkdown";

export const AiLogo = ({ size = 30 }) => (
  <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" style={{ flex: "none" }}>
    <rect width="28" height="28" rx="8" fill="#006284" />
    <path d="M8 18c0-6 5-10 12-10-1 7-5 11-12 10Z" fill="#49AE42" />
  </svg>
);

export default function AiMessage({ message, onOpenArtifact }) {
  const html = useMemo(() => renderMarkdown(message.text), [message.text]);
  if (message.role === "user") {
    return (
      <div className="max-w-[85%] self-end whitespace-pre-wrap rounded-2xl bg-[#E6EFEC] px-4 py-3 text-[15px] leading-[1.55] text-[#12312F]"
        data-testid="ai-user-msg">
        {message.text}
      </div>
    );
  }
  return (
    <div className="flex gap-3.5" data-testid="ai-assistant-msg">
      <AiLogo />
      <div className="flex min-w-0 flex-1 flex-col gap-3.5 text-[15px] leading-[1.6] text-[#12312F]">
        <AiSteps steps={message.steps} streaming={message.streaming && !message.text} />
        {message.text ? (
          <div className="ai-md space-y-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-1 [&_code]:rounded [&_code]:bg-[#EEF3F1] [&_code]:px-1"
            dangerouslySetInnerHTML={{ __html: html }} />
        ) : null}
        {message.streaming && !message.text && !message.steps?.length ? (
          <p className="m-0 text-sm text-[#3E5653]" role="status">Estora AI sedang berpikir…</p>
        ) : null}
        {(message.actions || []).map((a) => <AiActionCard key={a.id} action={a} />)}
        {(message.artifacts || []).map((a) => (
          <button key={a.id} type="button" onClick={() => onOpenArtifact?.(a)}
            className="inline-flex min-h-[44px] w-fit items-center gap-2 rounded-[10px] border border-[#B9CFC8] bg-white px-3 text-sm font-semibold text-[#006284] hover:text-[#00454D]">
            <FileText className="h-4 w-4" aria-hidden="true" /> Buka laporan: {a.title || "Laporan"}
          </button>
        ))}
        {message.error ? (
          <p role="alert" className="m-0 rounded-lg border border-[#E8C4C0] bg-[#FDF2F1] px-3 py-2 text-sm text-[#9B1C1C]">
            {message.error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
