/**
 * LabdipHistoryModal (MD-06) — riwayat labdip per WARNA pustaka / BARANG lintas
 * permintaan: tanggal butuh per putaran, hasil, skor, mitra — klik baris membuka
 * rincian putaran (deep-link `openRnd`).
 */
import { useEffect, useState } from "react";
import { CalendarClock, ExternalLink, History, X } from "lucide-react";
import { labdipHistory } from "./rndApi";
import { errMsg, ROUND_RESULT_META } from "./rndMeta";
import { openRnd } from "./rndDeepLink";
import { overlayDismiss } from "../../utils/overlayDismiss";

export default function LabdipHistoryModal({ colorId = "", productId = "", label = "", entityId, onClose }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const params = { color_id: colorId, product_id: productId };
    if (entityId && entityId !== "all") params.entity_id = entityId;
    labdipHistory(params).then(setData).catch((e) => setErr(errMsg(e, "Gagal memuat riwayat labdip.")));
  }, [colorId, productId, entityId]);

  const rows = data?.items || [];
  const s = data?.summary || {};
  const go = (r) => { openRnd({ view: "rnd-samples", sampleId: r.sample_id, roundId: r.round_id }); onClose?.(); };

  return (
    <div className="modal-overlay" style={{ zIndex: 170 }} data-testid="labdip-history-modal" {...overlayDismiss(onClose)}>
      <div className="modal-card" style={{ maxWidth: 820 }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="modal-title flex items-center gap-2"><History size={15} className="text-[#0058CC]" /> Riwayat Labdip</p>
            <p className="modal-subtitle" data-testid="labdip-history-label">{label || "—"}</p>
          </div>
          <button className="icon-button" onClick={onClose} data-testid="labdip-history-close"><X size={16} /></button>
        </div>
        {err && <div className="notice-bar danger mt-2" data-testid="labdip-history-error"><span>{err}</span></div>}
        {data && (
          <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6 text-[11px]" data-testid="labdip-history-summary">
            <Kpi label="Permintaan" value={s.samples || 0} />
            <Kpi label="Putaran" value={s.rounds || 0} />
            <Kpi label="ACC" value={s.acc || 0} tone="#1A7A3A" />
            <Kpi label="Revisi" value={s.revisi || 0} tone="#B26A00" />
            <Kpi label="Tolak" value={s.tolak || 0} tone="#C62828" />
            <Kpi label="Skor terbaik" value={s.best_score ?? "—"} />
          </div>
        )}
        <div className="mt-3 max-h-[52vh] overflow-y-auto rounded-md border border-[#EFF0F2]">
          <div className="grid grid-cols-[1.3fr_1fr_60px_110px_110px_90px] bg-[#FAFBFC] px-3 py-1.5 text-[10px] font-bold uppercase text-[#6B6B73]">
            <span>Permintaan</span><span>Mitra</span><span>Rnd</span><span>Tgl butuh</span><span>Diterima</span><span className="text-right">Hasil</span>
          </div>
          {!data && !err && <p className="px-3 py-4 text-center text-[12px] text-[#9A9BA3]" data-testid="labdip-history-loading">Memuat riwayat…</p>}
          {data && rows.length === 0 && (
            <p className="px-3 py-5 text-center text-[12px] text-[#9A9BA3]" data-testid="labdip-history-empty">
              Belum ada putaran labdip untuk {label || "objek ini"}.
            </p>
          )}
          {rows.map((r) => {
            const rm = ROUND_RESULT_META[r.result || ""] || ROUND_RESULT_META[""];
            return (
              <button key={r.round_id} type="button" onClick={() => go(r)} data-testid={`labdip-history-row-${r.round_id}`}
                className="grid w-full grid-cols-[1.3fr_1fr_60px_110px_110px_90px] items-center border-t border-[#F4F5F7] px-3 py-2 text-left text-[11.5px] hover:bg-[#F7F9FC]">
                <span className="min-w-0">
                  <span className="flex items-center gap-1 font-semibold text-[#0058CC]">{r.sample_number} <ExternalLink size={10} /></span>
                  <span className="block truncate text-[10.5px] text-[#6B6B73]">{r.sample_title}</span>
                </span>
                <span className="truncate">{r.supplier_name || "—"}</span>
                <span className="tabular-nums">rnd {r.round_no}</span>
                <span className="flex items-center gap-1 tabular-nums" data-testid={`labdip-history-due-${r.round_id}`}>
                  <CalendarClock size={11} className={r.overdue ? "text-[#C0392B]" : "text-[#8E8E93]"} />
                  {r.due_date || "—"}
                </span>
                <span className="tabular-nums text-[#6B6B73]">{(r.received_at || "").slice(0, 10) || "—"}</span>
                <span className="text-right font-bold" style={{ color: rm.tone }}>{rm.label}{r.score != null ? ` · ${r.score}` : ""}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, tone = "#1C1C1E" }) {
  return (
    <div className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2">
      <p className="text-[9.5px] font-bold uppercase text-[#8E8E93]">{label}</p>
      <p className="text-[13px] font-bold tabular-nums leading-tight" style={{ color: tone }}>{value}</p>
    </div>
  );
}
