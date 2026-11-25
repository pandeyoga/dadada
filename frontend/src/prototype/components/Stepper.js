import React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Tahapan horizontal (mis. 6 tahap perjalanan pembeli). `current` berbasis 0.
 * `progress` (0–100) menampilkan bilah progres tahap berjalan.
 * `variant`: 'light' (bawaan, kartu terang) atau 'dark' (kartu kaca di hero).
 */
export default function Stepper({ steps, current, progress, variant = "light" }) {
  const now = steps[current];
  return (
    <div className={cn("rdg-stepper", variant === "dark" && "rdg-stepper--dark")}>
      <ol className="rdg-stepper-list" aria-label="Tahapan" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((s, i) => {
          const state = i < current ? "done" : i === current ? "current" : "todo";
          return (
            <li key={s} className={`rdg-step is-${state}`} aria-current={state === "current" ? "step" : undefined}>
              <span className="rdg-step-dot" aria-hidden="true">
                {state === "done" ? <Check size={15} strokeWidth={3} /> : i + 1}
              </span>
              <span className="rdg-step-label">{s}</span>
              {state === "done" && <span className="sr-only">(selesai)</span>}
            </li>
          );
        })}
      </ol>
      {progress != null && now && (
        <div className="mt-4">
          <div className="mb-1.5 flex items-baseline justify-between text-[13px] font-semibold">
            <span>Tahap {current + 1} dari {steps.length} · {now}</span>
            <span className="text-[15px] font-extrabold">{progress} %</span>
          </div>
          <div
            className="rdg-progress"
            role="progressbar"
            aria-label={`Progres ${now}`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <span style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}
