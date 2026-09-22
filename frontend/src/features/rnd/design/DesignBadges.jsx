/** DesignBadges — label HOLD & label proofing R&D yang seragam di kartu daftar dan halaman detail. */
import { FlaskConical, PauseCircle, PackageCheck } from "lucide-react";
import { PROOFING_STATE_META } from "../rndMeta";

export function HoldBadge({ design, testId, size = "sm" }) {
  if (!design?.on_hold) return null;
  const pad = size === "lg" ? "px-2.5 py-1 text-[11px]" : "px-1.5 py-0.5 text-[9.5px]";
  return (
    <span data-testid={testId} title={`Ditahan oleh ${design.hold?.by || "—"} · ${design.hold?.reason || ""}`}
      className={`inline-flex shrink-0 items-center gap-1 rounded font-bold uppercase tracking-wide ${pad} bg-[#FFF1E6] text-[#B24A00] ring-1 ring-[#F2B48A]`}>
      <PauseCircle size={size === "lg" ? 12 : 10} /> Ditahan
    </span>
  );
}

export function ProofingBadge({ design, testId, size = "sm", showDetail = false }) {
  const p = design?.proofing || { state: "none" };
  const m = PROOFING_STATE_META[p.state] || PROOFING_STATE_META.none;
  const pad = size === "lg" ? "px-2.5 py-1 text-[11px]" : "px-1.5 py-0.5 text-[9.5px]";
  const Icon = p.state === "master" ? PackageCheck : FlaskConical;
  return (
    <span data-testid={testId} title={p.detail || m.label} style={{ background: m.bg, color: m.fg }}
      className={`inline-flex max-w-full shrink-0 items-center gap-1 truncate rounded font-semibold ${pad}`}>
      <Icon size={size === "lg" ? 12 : 10} className="shrink-0" />
      <span className="truncate">{m.label}{showDetail && p.state !== "none" ? ` · ${p.detail}` : ""}</span>
    </span>
  );
}
