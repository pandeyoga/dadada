import React, { useState } from "react";
import { Lock } from "lucide-react";
import { setCategoryMode, friendlyError } from "../aiApi";

const MODES = [["auto", "Otomatis"], ["draft", "Draf"], ["off", "Mati"]];
export const THRESHOLDS = [0.9, 0.95, 0.98];
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`);
const humanize = (k) => String(k || "").replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/** Normalisasi `GET /ai/accuracy` (array, `{categories:[]}`, atau objek per kategori). */
export function normalizeCategories(data) {
  const raw = Array.isArray(data) ? data : data?.categories || data?.items
    || Object.entries(data || {}).map(([category, v]) => ({ category, ...v }));
  return raw.map((r) => ({
    key: r.category || r.key || r.id,
    label: r.label || humanize(r.category || r.key),
    description: r.description || "",
    accuracy: r.accuracy ?? null,
    samples: r.samples ?? 0,
    mode: r.mode || "draft",
    locked: !!r.locked || r.mode === "handoff",
    canAuto: r.can_enable_auto !== false,
    reason: r.reason || r.auto_reason || "",
  }));
}

export default function AutonomyTable({ categories, threshold, onThreshold, onChanged }) {
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const rows = categories;

  const change = async (row, mode) => {
    setBusy(row.key); setErr("");
    try { await setCategoryMode(row.key, mode); onChanged?.(row.key, mode); }
    catch (e) { setErr(friendlyError(e, "Mode tidak dapat diubah.")); }
    finally { setBusy(""); }
  };

  return (
    <section id="otonomi" aria-labelledby="h-otonomi" className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="h-otonomi" className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">Kemandirian agen per jenis pesan</h2>
          <p className="m-0 mt-1 text-sm text-[#3E5653]">Mulai dari Draf. Naikkan ke Otomatis bila akurasi 30 hari terakhir sudah memenuhi ambang.</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#2B4744]">
          Ambang akurasi
          <select value={String(threshold)} onChange={(e) => onThreshold(Number(e.target.value))}
            className="min-h-[40px] rounded-lg border border-[#C9D8D3] bg-white px-2 text-sm font-semibold text-[#12312F]">
            {THRESHOLDS.map((t) => <option key={t} value={t}>{Math.round(t * 100)}%</option>)}
          </select>
        </label>
      </div>
      {!rows.length ? <p className="text-sm text-[#3E5653]">Belum ada data kategori pesan.</p> : null}
      <div role="table" aria-label="Kemandirian per kategori" className="flex flex-col">
        {rows.map((r) => (
          <div role="row" key={r.key} data-testid={`cat-${r.key}`}
            className="grid items-center gap-3 border-t border-[#EEF3F1] py-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,2fr)]">
            <span role="cell" className="text-sm">
              <b>{r.label}</b>
              {r.description ? <><br /><span className="text-[#3E5653]">{r.description}</span></> : null}
            </span>
            {r.locked ? (
              <>
                <span role="cell" className="text-sm text-[#3E5653]">—</span>
                <span role="cell" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#2B4744]">
                  <Lock className="h-4 w-4" aria-hidden="true" /> Dikunci: Butuh sales
                </span>
              </>
            ) : (
              <>
                <span role="cell" className="text-sm">
                  <b>{pct(r.accuracy)}</b>{" "}
                  <span className="text-[#3E5653]">· {r.samples} pesan{!r.canAuto && r.accuracy != null && r.accuracy < threshold ? ", di bawah ambang" : ""}</span>
                </span>
                <fieldset role="cell" className="m-0 flex min-w-0 flex-wrap gap-x-4 gap-y-1 border-0 p-0">
                  <legend className="sr-only">Mode {r.label}</legend>
                  {MODES.map(([v, l]) => {
                    const disabled = busy === r.key || (v === "auto" && !r.canAuto);
                    return (
                      <label key={v} className={`inline-flex min-h-[32px] items-center gap-1.5 text-sm ${disabled ? "text-[#5B6F6B]" : "text-[#12312F]"}`}>
                        <input type="radio" name={`mode-${r.key}`} value={v} checked={r.mode === v}
                          disabled={disabled} onChange={() => change(r, v)} />
                        {l}
                      </label>
                    );
                  })}
                  {!r.canAuto ? (
                    <span className="basis-full text-xs text-[#7A3E00]" data-testid={`reason-${r.key}`}>
                      Otomatis belum bisa dipilih: {r.reason || "belum memenuhi ambang akurasi."}
                    </span>
                  ) : null}
                </fieldset>
              </>
            )}
          </div>
        ))}
      </div>
      {err ? <p role="alert" className="mt-2 text-[13px] text-[#9B1C1C]">{err}</p> : null}
    </section>
  );
}
