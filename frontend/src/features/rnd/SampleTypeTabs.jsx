/**
 * SampleTypeTabs — **tab terpisah per JENIS** (Labdip · Handfeel · Proofing) pada rincian
 * permintaan sample. Tiap tab: perbandingan supplier untuk jenis itu + timeline round-nya.
 * Jenis yang belum diminta tetap punya tab (abu-abu) dengan tombol "tambahkan ke permintaan".
 */
import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import SampleRoundList from "./SampleRoundList";
import SampleProofGallery from "./SampleProofGallery";
import { ROUND_RESULT_META, typeTone } from "./rndMeta";
import { FALLBACK_TYPE_CODES, roundTypeOf, sampleTypesOf, typeLabel, typeMeta } from "./sampleTypeMeta";

function TypeCompare({ sample, code }) {
  const rows = (sample.participants || []).map((p) => {
    const rs = (sample.rounds || []).filter((r) => r.supplier_id === p.supplier_id && roundTypeOf(r, sample) === code);
    if (rs.length === 0) return null;
    const last = rs[rs.length - 1] || {};
    const rm = ROUND_RESULT_META[last.result || ""] || ROUND_RESULT_META[""];
    const cost = rs.reduce((a, r) => a + Number(r.cost || 0), 0);
    const best = rs.reduce((a, r) => (r.score != null ? Math.max(a ?? 0, Number(r.score)) : a), null);
    return { p, rs, rm, cost, best };
  }).filter(Boolean);
  if (rows.length < 2) return null;
  return (
    <div className="rounded-lg border border-[#EFF0F2]" data-testid={`sample-compare-type-${code}`}>
      <p className="border-b border-[#EFF0F2] bg-[#FAFBFC] px-3 py-1.5 text-[10.5px] font-bold uppercase text-[#8E8E93]">Perbandingan supplier</p>
      <div className="grid grid-cols-[1.4fr_70px_90px_1fr_110px] px-3 py-1 text-[9.5px] font-bold uppercase text-[#8E8E93]">
        <span>Supplier</span><span>Round</span><span>Skor terbaik</span><span>Hasil terakhir</span><span className="text-right">Biaya</span>
      </div>
      <div className="divide-y divide-[#F4F5F7]">
        {rows.map(({ p, rs, rm, cost, best }) => (
          <div key={p.supplier_id} data-testid={`sample-compare-row-${code}-${p.supplier_id}`}
            className="grid grid-cols-[1.4fr_70px_90px_1fr_110px] items-center px-3 py-1.5 text-[11.5px]">
            <span className="truncate font-semibold">{p.supplier_name}</span>
            <span className="tabular-nums">{rs.length}</span>
            <span className="tabular-nums font-bold">{best == null ? "—" : best}</span>
            <span className="font-semibold" style={{ color: rm.tone }}>{rm.label}</span>
            <span className="text-right tabular-nums">{formatCurrency(cost)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SampleTypeTabs({ sample, types, measurements, busy, loading, highlightRoundId, initialType = "",
  canSubmit, canAssess, canAddType, onAddType, onUpload, onSubmit, onAssess, onOpenRound }) {
  const onSample = useMemo(() => sampleTypesOf(sample), [sample]);
  const tabs = useMemo(() => {
    const master = (types || []).length ? types.map((t) => t.value) : FALLBACK_TYPE_CODES;
    const all = [...master];
    onSample.forEach((c) => { if (!all.includes(c)) all.push(c); });
    return all;
  }, [types, onSample]);

  const focusType = (highlightRoundId
    ? roundTypeOf((sample.rounds || []).find((r) => r.id === highlightRoundId), sample) : "") || initialType;
  const [active, setActive] = useState(focusType || onSample[0] || tabs[0] || "");
  useEffect(() => {
    if (!tabs.includes(active)) setActive(focusType || onSample[0] || tabs[0] || "");
  }, [tabs.join(","), onSample.join(",")]);

  const countOf = (code) => (sample.rounds || []).filter((r) => roundTypeOf(r, sample) === code).length;
  const accOf = (code) => (sample.rounds || []).some((r) => roundTypeOf(r, sample) === code && r.result === "acc");
  const requested = onSample.includes(active);
  const meta = typeMeta(active, types);
  const tone = typeTone(active);

  return (
    <div className="section-card !p-0 overflow-hidden" data-testid="sample-type-tabs">
      <div className="flex flex-wrap items-end gap-1 border-b border-[#EFF0F2] bg-[#FAFBFC] px-2 pt-2" role="tablist">
        {tabs.map((code) => {
          const on = code === active;
          const has = onSample.includes(code);
          const t = typeTone(code);
          return (
            <button key={code} type="button" role="tab" aria-selected={on} data-testid={`sample-tab-${code}`}
              onClick={() => setActive(code)}
              className={`-mb-px flex items-center gap-1.5 rounded-t-lg border border-b-0 px-3 py-1.5 text-[11.5px] font-semibold transition-[background-color,color] ${on
                ? "border-[#EFF0F2] bg-white" : "border-transparent hover:bg-white/70"} ${has ? "" : "opacity-60"}`}
              style={{ color: on ? t.fg : "#6B6B73" }}>
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: has ? t.fg : "#D1D1D6" }} />
              {typeLabel(code, types).split(" (")[0]}
              {has && (
                <span className="rounded-full bg-[#F2F2F5] px-1.5 text-[9.5px] tabular-nums text-[#6B6B73]" data-testid={`sample-tab-count-${code}`}>
                  {countOf(code)} rnd{accOf(code) ? " · ACC" : ""}
                </span>
              )}
              {!has && <span className="text-[9.5px] font-normal text-[#9A9BA3]">tidak diminta</span>}
            </button>
          );
        })}
      </div>

      <div className="grid gap-2.5 p-3" data-testid={`sample-tab-panel-${active}`}>
        {meta.notes && (
          <p className="rounded-lg px-3 py-2 text-[11px]" style={{ background: tone.bg, color: tone.fg }} data-testid="sample-tab-notes">
            {meta.notes}
            {(meta.measurement_fields || []).length > 0 && <> Hasil ukur: <b>{meta.measurement_fields.join(", ")}</b>.</>}
          </p>
        )}
        {!requested ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[#D9D9DE] px-3 py-8 text-center" data-testid={`sample-tab-empty-${active}`}>
            <p className="text-[12px] font-semibold text-[#1C1C1E]">{typeLabel(active, types)} tidak termasuk dalam permintaan ini</p>
            <p className="max-w-sm text-[11px] text-[#8E8E93]">Setiap jenis punya rangkaian round & kuota revisi sendiri. Tambahkan bila supplier juga harus mengerjakan jenis ini.</p>
            {canAddType && (
              <button type="button" className="secondary-button" disabled={busy} data-testid={`sample-tab-add-${active}`}
                onClick={() => onAddType?.(active)}>
                <Plus size={13} /> Tambahkan {typeLabel(active, types).split(" (")[0]} ke permintaan
              </button>
            )}
          </div>
        ) : (
          <>
            <TypeCompare sample={sample} code={active} />
            <SampleProofGallery sample={sample} code={active} />
            <SampleRoundList sample={sample} types={types} measurements={measurements} onlyType={active}
              busy={busy} loading={loading} highlightRoundId={highlightRoundId}
              canSubmit={canSubmit} canAssess={canAssess}
              onUpload={onUpload} onSubmit={onSubmit} onAssess={onAssess} onOpenRound={onOpenRound} />
          </>
        )}
      </div>
    </div>
  );
}
