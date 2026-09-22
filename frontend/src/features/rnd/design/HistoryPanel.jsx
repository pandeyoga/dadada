/** HistoryPanel — riwayat lengkap desain: saring per kelompok peristiwa, tampilkan aktor · waktu · detail (sebelum → sesudah). */
import { useMemo, useState } from "react";
import { DESIGN_EVENT_LABEL, DESIGN_HISTORY_GROUPS, DESIGN_STATUS_META, fmtScore } from "../rndMeta";

const fmtAt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "");
const TONE = {
  approve: "#1A7A3A", activate: "#0F6E4A", request_revision: "#C62828", archive: "#6B6B73",
  scored: "#B26A00", feedback: "#0058CC", new_version: "#6B219A", submit: "#0058CC",
  hold: "#B24A00", release_hold: "#1A7A3A", file_deleted: "#C62828", updated: "#6B219A",
  proofing_requested: "#6B219A", proofing_finished: "#1A7A3A", proofing_decided: "#1A7A3A",
  master_product_created: "#0058CC", master_product_released: "#0058CC", spec_linked: "#0058CC",
};
const groupOf = (ev) => DESIGN_HISTORY_GROUPS.find((g) => g.events?.includes(ev))?.key || "lifecycle";
const fmtVal = (v) => {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (typeof v === "boolean") return v ? "ya" : "tidak";
  return String(v);
};

export default function HistoryPanel({ design }) {
  const [group, setGroup] = useState("");
  const [q, setQ] = useState("");
  const rows = useMemo(() => {
    const all = [...(design.timeline || [])].sort((a, b) => (a.at < b.at ? 1 : -1));
    const term = q.trim().toLowerCase();
    return all.filter((e) => (!group || groupOf(e.event) === group)
      && (!term || [DESIGN_EVENT_LABEL[e.event], e.note, e.by, e.sample_number, e.product_sku].some((v) => (v || "").toLowerCase().includes(term))));
  }, [design.timeline, group, q]);
  const counts = useMemo(() => {
    const c = {};
    (design.timeline || []).forEach((e) => { const g = groupOf(e.event); c[g] = (c[g] || 0) + 1; });
    return c;
  }, [design.timeline]);

  return (
    <div data-testid="design-history-panel" className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {DESIGN_HISTORY_GROUPS.map((g) => (
          <button key={g.key || "all"} type="button" onClick={() => setGroup(g.key)} data-testid={`design-history-filter-${g.key || "all"}`}
            className={`rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${group === g.key ? "border-[#6B219A] bg-[#F1E9F7] text-[#6B219A]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#6B219A]"}`}>
            {g.label} <span className="opacity-60">{g.key ? counts[g.key] || 0 : (design.timeline || []).length}</span>
          </button>
        ))}
        <input className="field ml-auto !w-48 !py-1 text-[11px]" placeholder="cari di riwayat…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="design-history-search" />
      </div>
      {!rows.length ? (
        <p className="text-[11.5px] text-[#9A9BA3]" data-testid="design-history-empty">Tidak ada riwayat untuk saringan ini.</p>
      ) : (
        <ol className="relative ml-2 border-l border-[#E5E5EA]" data-testid="design-history-list">
          {rows.map((e) => <HistoryRow key={e.id} e={e} />)}
        </ol>
      )}
    </div>
  );
}

function HistoryRow({ e }) {
  const tone = TONE[e.event] || "#8E8E93";
  return (
    <li className="relative mb-3 pl-4" data-testid={`design-history-${e.event}`}>
      <span className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white" style={{ background: tone }} />
      <p className="text-[11.5px]">
        <b style={{ color: tone }}>{DESIGN_EVENT_LABEL[e.event] || e.event}</b>
        {e.version && <span className="ml-1 rounded bg-[#F5F5F7] px-1 text-[9.5px] font-bold text-[#6B6B73]">v{e.version}</span>}
        {["approve", "scored"].includes(e.event) && e.score !== null && e.score !== undefined && <span className="ml-1 text-[10.5px] font-semibold">nilai akhir {fmtScore(e.score)}</span>}
        {e.to_status && e.from_status && e.from_status !== e.to_status && (
          <span className="ml-1 text-[10px] text-[#8E8E93]">
            {DESIGN_STATUS_META[e.from_status]?.label || e.from_status} → {DESIGN_STATUS_META[e.to_status]?.label || e.to_status}
          </span>
        )}
        {e.file_kind && <span className="ml-1 rounded bg-[#F5F5F7] px-1 text-[9.5px] text-[#6B6B73]">{e.file_kind}</span>}
        {e.sample_number && <span className="ml-1 rounded bg-[#F1E9F7] px-1 text-[9.5px] font-bold text-[#6B219A]">{e.sample_number}</span>}
        {e.product_sku && <span className="ml-1 rounded bg-[#E3F0FF] px-1 font-mono text-[9.5px] font-bold text-[#0058CC]">{e.product_sku}</span>}
      </p>
      {e.note && <p className="text-[11px] text-[#3C3C43]">{e.note}</p>}
      {e.event === "release_hold" && e.hold_reason && (
        <p className="text-[10px] text-[#8E8E93]">ditahan sejak {fmtAt(e.held_since)} — alasan: {e.hold_reason}</p>
      )}
      {Array.isArray(e.changes) && e.changes.length > 0 && (
        <ul className="mt-1 space-y-0.5 rounded-lg bg-[#FAFBFC] px-2 py-1.5" data-testid="design-history-changes">
          {e.changes.map((c) => (
            <li key={c.field} className="text-[10.5px]">
              <b>{c.label}</b>: <span className="text-[#C62828] line-through">{fmtVal(c.from)}</span> → <span className="text-[#1A7A3A]">{fmtVal(c.to)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-[9.5px] text-[#9A9BA3]">{e.by || "sistem"}{e.role && ` (${e.role})`} · {fmtAt(e.at)}</p>
    </li>
  );
}
