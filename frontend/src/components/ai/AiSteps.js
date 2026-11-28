import React from "react";
import { ChevronRight, Loader2, AlertTriangle } from "lucide-react";

/** Blok langkah: <details> "N langkah selesai · X detik" (mockup layar 1). */
export default function AiSteps({ steps = [], streaming = false }) {
  if (!steps.length) return null;
  const running = steps.some((s) => s.status === "running");
  const done = steps.filter((s) => s.status !== "running").length;
  const totalMs = steps.reduce((a, s) => a + (Number(s.ms) || 0), 0);
  const secs = Math.max(1, Math.round(totalMs / 1000));
  const title = running || streaming
    ? `Sedang bekerja · ${done} dari ${steps.length} langkah`
    : `${steps.length} langkah selesai · ${secs} detik`;
  return (
    <details open={running || streaming} data-testid="ai-steps"
      className="group rounded-xl border border-[#DDE7E3] bg-white">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-2.5 text-[13px] font-semibold text-[#3E5653]">
        <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden="true" />
        {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
        {title}
      </summary>
      <ol className="m-0 flex flex-col gap-1.5 px-3.5 pb-3 pl-9 text-[13px] text-[#2B4744]">
        {steps.map((s) => (
          <li key={s.id}>
            {s.label || s.tool}
            {s.status === "failed" ? (
              <span className="ml-1 inline-flex items-center gap-1 text-[#9B1C1C]">
                <AlertTriangle className="h-3 w-3" aria-hidden="true" /> gagal
              </span>
            ) : null}
            {s.summary ? <span className="text-[#3E5653]"> · {s.summary}</span> : null}
          </li>
        ))}
      </ol>
    </details>
  );
}
