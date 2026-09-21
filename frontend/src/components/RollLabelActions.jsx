import { useState } from "react";
import { Printer, ListOrdered } from "lucide-react";
import axios, { API } from "../services/apiClient";
import { printRollLabelsBulk } from "../utils/rollLabels";

/** Dua jalur cetak label QR roll: popup browser ATAU antrean printer gudang (job kind=qr_label). */
export default function RollLabelActions({ rolls, ctx = {}, source = "", testPrefix = "roll-labels", compact = false }) {
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState("");
  const n = (rolls || []).length;
  if (!n) return null;
  const popup = async () => { await printRollLabelsBulk(rolls.map((r) => ({ ...r, product_name: r.product_name || ctx.product_name })), ctx); };
  const queue = async () => {
    setBusy(true); setInfo("");
    try {
      const { data } = await axios.post(`${API}/rfid/print-jobs`, { roll_ids: rolls.map((r) => r.id), kind: "qr_label", source });
      setInfo(`Antrean ${data.job_number} · ${data.item_count} label menunggu printer gudang.`);
    } catch (e) { const d = e.response?.data?.detail; setInfo((d && (d.message || d)) || "Gagal mengantrekan label."); }
    finally { setBusy(false); }
  };
  const cls = compact ? "btn-secondary !px-2 !py-1 !text-[10.5px]" : "secondary-button text-[11px]";
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5" data-testid={`${testPrefix}-actions`}>
      <button type="button" className={cls} onClick={popup} data-testid={`${testPrefix}-popup`} title="Cetak dari browser (popup)">
        <span className="flex items-center gap-1"><Printer size={11} /> Cetak label {n} roll</span>
      </button>
      <button type="button" className={cls} disabled={busy} onClick={queue} data-testid={`${testPrefix}-queue`} title="Kirim ke antrean printer label gudang">
        <span className="flex items-center gap-1"><ListOrdered size={11} /> {busy ? "Mengantrekan…" : "Kirim ke antrean printer"}</span>
      </button>
      {info && <span className="text-[10.5px] text-[#6B6B73]" data-testid={`${testPrefix}-info`}>{info}</span>}
    </div>
  );
}
