/**
 * OrderFeedbackPanel — feedback/komplain pelanggan per SO: daftar + catat baru + tindak lanjut
 * (status · penanggung jawab · tenggat · penyelesaian). API: /api/customer-feedback.
 */
import { useCallback, useEffect, useState } from "react";
import { MessageSquareWarning, Plus, UserCheck, CalendarClock } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import FeedbackFormModal from "./FeedbackFormModal";

const STATUS_TONE = {
  open: "bg-[#FFF3D6] text-[#8C4A00] border-[#F5C26B]",
  in_progress: "bg-[#E3EEFF] text-[#0058CC] border-[#CBDFFF]",
  resolved: "bg-[#E8F7EC] text-[#1A7A3A] border-[#BFE6CB]",
  closed: "bg-[#F2F2F5] text-[#6B6B73] border-[#E5E5EA]",
};
const SEV_TONE = { tinggi: "text-[#C62828]", sedang: "text-[#B26A00]", rendah: "text-[#6B6B73]" };

export default function OrderFeedbackPanel({ order, canEdit = true }) {
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [modal, setModal] = useState(null); // {mode:"create"} | {mode:"update", row}
  const [err, setErr] = useState("");
  const today = new Date().toISOString().slice(0, 10);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/customer-feedback`, { params: { order_id: order.id } });
      setRows(r.data.items || []); setErr("");
    } catch (e) { setErr(e.response?.data?.detail || "Gagal memuat feedback."); }
  }, [order.id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    axios.get(`${API}/customer-feedback/meta`).then((r) => setMeta(r.data)).catch(() => setMeta(null));
  }, []);

  const label = (kind, v) => (meta?.[kind] || []).find((x) => x.value === v)?.label || v;
  const openCount = rows.filter((r) => ["open", "in_progress"].includes(r.status)).length;

  return (
    <div data-testid="order-feedback-panel" className="rounded-md border border-[#EFF0F2] overflow-hidden">
      <div className="flex items-center justify-between px-2.5 py-1.5 bg-[#FAFBFC] border-b border-[#EFF0F2]">
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-[#6B6B73]">
          <MessageSquareWarning size={12} className={openCount ? "text-[#C62828]" : "text-[#8E8E93]"} />
          Feedback pelanggan
          <span data-testid="order-feedback-count" className={`rounded px-1.5 py-0.5 text-[9.5px] ${openCount ? "bg-[#FDECEC] text-[#C62828]" : "bg-[#F2F2F5] text-[#6B6B73]"}`}>
            {openCount} terbuka · {rows.length} total
          </span>
        </span>
        {canEdit && (
          <button data-testid="order-feedback-add" onClick={() => setModal({ mode: "create" })}
            className="flex items-center gap-1 rounded border border-[#CBDFFF] bg-[#F2F7FF] px-1.5 py-0.5 text-[10px] font-semibold text-[#0058CC] hover:bg-[#E3EEFF]">
            <Plus size={10} /> Catat feedback
          </button>
        )}
      </div>
      {err && <p className="px-2.5 py-1.5 text-[10.5px] text-[#C62828]" data-testid="order-feedback-error">{err}</p>}
      {rows.length === 0 && !err && (
        <p className="px-2.5 py-3 text-center text-[10.5px] text-[#9A9BA3]" data-testid="order-feedback-empty">Belum ada feedback/komplain untuk pesanan ini.</p>
      )}
      {rows.map((r) => {
        const late = ["open", "in_progress"].includes(r.status) && r.due_date && r.due_date < today;
        return (
          <button key={r.id} type="button" data-testid={`order-feedback-row-${r.id}`}
            onClick={() => canEdit && setModal({ mode: "update", row: r })}
            className="block w-full border-b border-[#F4F5F7] px-2.5 py-2 text-left last:border-0 hover:bg-[#FAFBFC]">
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate text-[11px] font-semibold text-[#1C1C1E]">
                <span className="text-[#6B6B73]">{r.number}</span> · {r.title}
              </span>
              <span data-testid={`order-feedback-status-${r.id}`}
                className={`shrink-0 rounded border px-1.5 py-0.5 text-[9.5px] font-bold ${STATUS_TONE[r.status] || STATUS_TONE.closed}`}>
                {label("statuses", r.status)}
              </span>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[10px] text-[#6B6B73]">
              <span>{label("categories", r.category)}</span>
              <span className={`font-semibold ${SEV_TONE[r.severity] || ""}`}>{r.severity}</span>
              <span className="flex items-center gap-0.5" data-testid={`order-feedback-assignee-${r.id}`}>
                <UserCheck size={10} /> {r.assignee_name || "belum ada penanggung jawab"}
              </span>
              {r.due_date && (
                <span className={`flex items-center gap-0.5 ${late ? "font-bold text-[#C62828]" : ""}`}>
                  <CalendarClock size={10} /> {r.due_date}{late ? " · lewat" : ""}
                </span>
              )}
            </div>
          </button>
        );
      })}
      {modal && (
        <FeedbackFormModal order={order} meta={meta} row={modal.row}
          onClose={() => setModal(null)} onDone={() => { setModal(null); load(); }} />
      )}
    </div>
  );
}
