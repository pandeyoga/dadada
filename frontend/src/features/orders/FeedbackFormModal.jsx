/**
 * FeedbackFormModal — catat feedback baru (mode create) atau tindak lanjut (mode update:
 * penanggung jawab, tenggat, status, penyelesaian, catatan). Penanggung jawab dipilih dari
 * GET /api/users (bila diizinkan) atau diketik bebas.
 */
import KNDatePicker from "@/components/KNDatePicker";
import { useEffect, useState } from "react";
import { MessageSquareWarning, X } from "lucide-react";
import { overlayDismiss } from "../../utils/overlayDismiss";
import axios, { API } from "../../services/apiClient";
import KNSelect from "../../components/KNSelect";

export default function FeedbackFormModal({ order, meta, row, onClose, onDone }) {
  const isEdit = !!row;
  const [f, setF] = useState({
    title: row?.title || "", category: row?.category || "kualitas", severity: row?.severity || "sedang",
    description: row?.description || "", assignee_id: row?.assignee_id || "", assignee_name: row?.assignee_name || "",
    due_date: row?.due_date || "", status: row?.status || "open", resolution: row?.resolution || "", note: "",
  });
  const [users, setUsers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  useEffect(() => {
    axios.get(`${API}/users`, { params: order.entity_id ? { entity_id: order.entity_id } : {} })
      .then((r) => setUsers((Array.isArray(r.data) ? r.data : r.data.items || []).filter((u) => u.active !== false)))
      .catch(() => setUsers([]));
  }, [order.entity_id]);

  const pickUser = (id) => {
    const u = users.find((x) => x.id === id);
    setF((p) => ({ ...p, assignee_id: id, assignee_name: u ? u.name : p.assignee_name }));
  };

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      if (isEdit) {
        const body = { assignee_id: f.assignee_id, assignee_name: f.assignee_name, due_date: f.due_date,
          severity: f.severity, note: f.note };
        if (f.status !== row.status) body.status = f.status;
        if (["resolved", "closed"].includes(f.status)) body.resolution = f.resolution;
        await axios.patch(`${API}/customer-feedback/${row.id}`, body);
      } else {
        await axios.post(`${API}/customer-feedback`, { order_id: order.id, title: f.title, category: f.category,
          severity: f.severity, description: f.description, assignee_id: f.assignee_id,
          assignee_name: f.assignee_name, due_date: f.due_date });
      }
      onDone?.();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan feedback."); }
    finally { setBusy(false); }
  };

  const opts = (k) => (meta?.[k] || []).map((x) => ({ value: x.value, label: x.label }));
  const needResolution = isEdit && ["resolved", "closed"].includes(f.status) && f.resolution.trim().length < 5;
  const canSave = !busy && (isEdit ? !needResolution : f.title.trim().length >= 5);

  return (
    <div className="modal-overlay" style={{ zIndex: 190 }} data-testid="feedback-form-modal" {...overlayDismiss(onClose)}>
      <div className="modal-card" style={{ maxWidth: 600 }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="modal-title flex items-center gap-2"><MessageSquareWarning size={15} className="text-[#C62828]" />
              {isEdit ? `Tindak lanjut ${row.number}` : "Catat Feedback / Komplain Pelanggan"}</p>
            <p className="modal-subtitle">{order.number} · {order.customer_name}{isEdit ? ` · ${row.title}` : ""}</p>
          </div>
          <button className="icon-button" onClick={onClose} data-testid="feedback-form-close"><X size={16} /></button>
        </div>
        {err && <div className="notice-bar danger mt-2" data-testid="feedback-form-error"><span>{err}</span></div>}
        <div className="mt-3 grid gap-3">
          {!isEdit && (
            <>
              <div className="grid gap-1.5">
                <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Judul singkat *</label>
                <input className="form-input" value={f.title} onChange={(e) => set("title", e.target.value)}
                  data-testid="feedback-title-input" placeholder="Mis. warna roll ke-2 lebih gelap dari sampel" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="grid gap-1.5">
                  <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Kategori</label>
                  <KNSelect data-testid="feedback-category" className="form-input" value={f.category} options={opts("categories")} onValueChange={(v) => set("category", v)} />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Tingkat</label>
                  <KNSelect data-testid="feedback-severity" className="form-input" value={f.severity} options={opts("severities")} onValueChange={(v) => set("severity", v)} />
                </div>
              </div>
              <div className="grid gap-1.5">
                <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Uraian dari pelanggan</label>
                <textarea className="form-input" rows="2" value={f.description} onChange={(e) => set("description", e.target.value)} data-testid="feedback-description" />
              </div>
            </>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1.5">
              <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Penanggung jawab</label>
              {users.length > 0 ? (
                <KNSelect data-testid="feedback-assignee" className="form-input" value={f.assignee_id} placeholder="— pilih orang —"
                  options={[{ value: "", label: "— belum ditentukan —" }, ...users.map((u) => ({ value: u.id, label: `${u.name} · ${u.role}` }))]}
                  onValueChange={pickUser} />
              ) : (
                <input className="form-input" value={f.assignee_name} onChange={(e) => set("assignee_name", e.target.value)} data-testid="feedback-assignee-name" placeholder="Nama penanggung jawab" />
              )}
            </div>
            <div className="grid gap-1.5">
              <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Tenggat tindak lanjut</label>
              <KNDatePicker value={f.due_date} onChange={(v) => set("due_date", v)} data-testid="feedback-due-date" />
            </div>
          </div>
          {isEdit && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div className="grid gap-1.5">
                  <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Status</label>
                  <KNSelect data-testid="feedback-status" className="form-input" value={f.status} options={opts("statuses")} onValueChange={(v) => set("status", v)} />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Tingkat</label>
                  <KNSelect data-testid="feedback-severity" className="form-input" value={f.severity} options={opts("severities")} onValueChange={(v) => set("severity", v)} />
                </div>
              </div>
              {["resolved", "closed"].includes(f.status) && (
                <div className="grid gap-1.5">
                  <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Penyelesaian * (min. 5 huruf)</label>
                  <textarea className="form-input" rows="2" value={f.resolution} onChange={(e) => set("resolution", e.target.value)} data-testid="feedback-resolution" />
                </div>
              )}
              <div className="grid gap-1.5">
                <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Catatan tindak lanjut</label>
                <textarea className="form-input" rows="2" value={f.note} onChange={(e) => set("note", e.target.value)} data-testid="feedback-note" />
              </div>
              {(row.timeline || []).length > 0 && (
                <div className="max-h-28 overflow-y-auto rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2 text-[10.5px]" data-testid="feedback-timeline">
                  {[...row.timeline].reverse().map((t, i) => (
                    <p key={i} className="text-[#3C3C43]"><span className="text-[#8E8E93]">{String(t.at || "").slice(0, 16).replace("T", " ")}</span> · <b>{t.actor}</b> — {t.label}{t.note ? ` (${t.note})` : ""}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} data-testid="feedback-form-cancel">Batal</button>
          <button className="btn-primary" onClick={submit} disabled={!canSave} data-testid="feedback-form-submit">{busy ? "Menyimpan…" : isEdit ? "Simpan tindak lanjut" : "Catat feedback"}</button>
        </div>
      </div>
    </div>
  );
}
