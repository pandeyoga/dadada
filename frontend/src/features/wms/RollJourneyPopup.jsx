/**
 * RollJourneyPopup — JEJAK BARANG: timeline satu roll lintas semua dokumen
 * (PO→GR→tag→print→verify→PA/BTG→SO→gate→loading check). Data dari
 * GET /inventory/rolls/{id}/journey-timeline (read-only, SSOT tersebar disatukan).
 */
import { useEffect, useState } from "react";
import { X, Route } from "lucide-react";
import axios, { API } from "../../services/apiClient";

const KIND_COLOR = {
  acquired: "#0058CC", tag: "#6B219A", print: "#6B219A", verify: "#6B219A",
  putaway: "#1B7F4B", movement: "#8E8E93", gate: "#B23B14", so: "#FF9500", loading: "#4B3B9E", scan: "#0A84FF",
};

export const RollJourneyPopup = ({ rollId, onClose }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get(`${API}/inventory/rolls/${rollId}/journey-timeline`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || e.message));
  }, [rollId]);

  const fmt = (iso) => (iso ? new Date(iso).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4" data-testid="roll-journey-popup"
      onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-2 flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-[13px] font-bold"><Route size={15} className="text-[#0058CC]" /> Jejak Barang</p>
          <button data-testid="roll-journey-close" className="icon-button" onClick={onClose}><X size={15} /></button>
        </div>
        {error && <p className="rounded bg-[#FBE9E7] px-2 py-1.5 text-[11.5px] text-[#C0341D]">{error}</p>}
        {!data && !error && <div className="h-24 animate-pulse rounded bg-[#F5F5F7]" />}
        {data && (
          <>
            <div className="mb-3 rounded-lg bg-[#FAFBFC] p-2.5 text-[11.5px]" data-testid="roll-journey-head">
              <p className="font-bold text-[12.5px]">{data.roll.roll_no} <span className="font-normal text-[#6B6B73]">· grade {data.roll.grade || "—"} · {data.roll.qty} {data.roll.unit}</span></p>
              <p className="text-[#6B6B73]">Gudang: <b>{data.roll.warehouse_name || "—"}</b> · Status stok: {data.roll.status}</p>
              <p className="text-[#6B6B73]">Journey: <b>{data.roll.journey_stage_label}</b>
                {data.roll.routing === "cross_dock" && <span className="ml-1 rounded bg-[#F3E9FA] px-1 text-[10px] font-bold text-[#6B219A]">CROSS-DOCK</span>}
              </p>
              {data.roll.epc && <p className="font-mono text-[10px] text-[#8E8E93]">EPC {data.roll.epc}</p>}
              <p className="text-[#6B6B73]" data-testid="roll-journey-last-scan">Terakhir dipindai HP: <b>{data.roll.last_scan ? `${fmt(data.roll.last_scan.at)} · ${data.roll.last_scan.by || "—"} · ${data.roll.last_scan.warehouse_id || ""}${data.roll.last_scan.bin_id ? ` · bin ${data.roll.last_scan.bin_id}` : ""}` : "belum pernah"}</b></p>
            </div>
            <ol className="relative ml-2 space-y-0 border-l border-[#E5E5EA]" data-testid="roll-journey-events">
              {data.events.length === 0 && <p className="pl-3 text-[11.5px] text-[#8E8E93]">Belum ada jejak.</p>}
              {data.events.map((e, i) => (
                <li key={i} className="relative pb-3 pl-4" data-testid={`roll-journey-ev-${i}`}>
                  <span className="absolute -left-[5px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white"
                    style={{ background: KIND_COLOR[e.kind] || "#8E8E93" }} />
                  <p className="text-[11.5px] leading-snug">{e.label}</p>
                  <p className="text-[10px] text-[#9A9BA3]">{fmt(e.at)}</p>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
    </div>
  );
};

export default RollJourneyPopup;
