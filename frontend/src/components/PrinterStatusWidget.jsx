import { useEffect, useState } from "react";
import { Printer, AlertTriangle, CheckCircle2 } from "lucide-react";
import axios, { API } from "../services/apiClient";

const ago = (iso) => { if (!iso) return "—"; const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000); return m < 1 ? "baru saja" : m < 60 ? `${m} mnt lalu` : m < 1440 ? `${Math.round(m / 60)} jam lalu` : `${Math.round(m / 1440)} hari lalu`; };

/** Status printer label per gudang: online/offline, label menunggu, job tertua. compact = versi HP. */
export default function PrinterStatusWidget({ warehouseId, compact = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/rfid/printer-status`, { params: warehouseId ? { warehouse_id: warehouseId } : {} })
      .then((r) => setData(r.data)).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat status printer."))
      .finally(() => setLoading(false));
  }, [warehouseId]);
  if (err) return <div className="notice-bar danger text-xs" data-testid="printer-status-error">{String(err)}</div>;
  if (loading || !data) return <div className="text-xs text-[#6B6B73]" data-testid="printer-status-loading">Memuat status printer…</div>;
  if (!data.warehouses.length) return <div className="text-xs text-[#6B6B73]" data-testid="printer-status-empty">Belum ada printer label / antrean.</div>;
  return (
    <div className={compact ? "space-y-1.5" : "grid gap-2 sm:grid-cols-2 lg:grid-cols-3"} data-testid="printer-status">
      {data.warehouses.map((w) => (
        <div key={w.warehouse_id || "-"} className={`rounded-xl border p-3 ${w.stuck ? "border-[#B23B14]/50 bg-[#FDECEC]" : "border-[#EFF0F2] bg-white"}`} data-testid={`printer-status-wh-${w.warehouse_id}`}>
          <div className="flex items-center gap-2 text-sm font-bold">
            <Printer size={15} /> {w.warehouse_name || w.warehouse_id}
            {w.stuck ? <span className="ml-auto flex items-center gap-1 text-[11px] text-[#B23B14]" data-testid={`printer-stuck-${w.warehouse_id}`}><AlertTriangle size={12} /> label tertahan</span>
              : <span className="ml-auto flex items-center gap-1 text-[11px] text-[#1B7F4B]"><CheckCircle2 size={12} /> {w.online_printers}/{w.printers.length} printer online</span>}
          </div>
          <div className="mt-1 text-xs text-[#3C3C43]" data-testid={`printer-queue-${w.warehouse_id}`}>
            <b>{w.queued_labels}</b> label menunggu · {w.queued_jobs} job{w.oldest_queued_at ? ` · tertua ${ago(w.oldest_queued_at)}` : ""}
          </div>
          {!compact && w.printers.map((p) => (
            <div key={p.id} className="mt-1 flex items-center gap-1.5 text-[11px]" data-testid={`printer-dev-${p.id}`}>
              <span className={`inline-block h-2 w-2 rounded-full ${p.online ? "bg-[#1B7F4B]" : "bg-[#B23B14]"}`} />
              {p.name || p.code} · {p.online ? "online" : "offline"} · terlihat {ago(p.last_heartbeat)}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
