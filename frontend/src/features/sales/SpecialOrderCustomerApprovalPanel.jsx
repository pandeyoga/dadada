/** Fase 2 OD — blok "Persetujuan Pelanggan" atas sample: ACC / minta revisi / tolak + catatan, tanggal, bukti, riwayat. */
import { useState } from "react";
import { Check, FileText, Image as ImageIcon, Loader2, RotateCcw, Upload, UserCheck, X } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { useProofBlob } from "../rnd/ProofImage";
import { fmtDate } from "./SpecialOrderShared";

const DEC = {
  acc: { label: "ACC", cls: "bg-[#E9F7EF] text-[#1B7F4B] border-[#CDE9D6]", icon: Check },
  revisi: { label: "Minta revisi", cls: "bg-[#FFF4E5] text-[#B45309] border-[#FCE1B6]", icon: RotateCcw },
  tolak: { label: "Tolak", cls: "bg-[#FDECEC] text-[#C0392B] border-[#F5C6C6]", icon: X },
};

export default function SpecialOrderCustomerApprovalPanel({ order, canEdit, onUpdated }) {
  const ch = order.chain || {};
  const review = ch.review || {};
  const history = order.customer_decisions || [];
  const locked = !!(order.pricing || {}).locked;
  const cancelled = order.status === "cancelled";
  const canDecide = canEdit && review.ready && !locked && !cancelled && order.customer_decision !== "acc";
  const [mode, setMode] = useState("");
  const [note, setNote] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [contact, setContact] = useState("");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const r = await axios.post(`${API}/special-orders/${order.id}/customer-decision`, { decision: mode, note, decided_at: date, contact_name: contact });
      const decId = r.data.decision?.id;
      let latest = r.data.special_order;
      for (const f of files) {
        const fd = new FormData(); fd.append("file", f); fd.append("decision_id", decId);
        const up = await axios.post(`${API}/special-orders/${order.id}/customer-decision/evidence`, fd);
        latest = up.data.special_order;
      }
      onUpdated?.(latest); setMode(""); setNote(""); setFiles([]); setContact("");
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan keputusan pelanggan."); } finally { setBusy(false); }
  };

  const uploadMore = async (decId, fs) => {
    setBusy(true); setErr("");
    try {
      let latest = null;
      for (const f of fs) { const fd = new FormData(); fd.append("file", f); fd.append("decision_id", decId); latest = (await axios.post(`${API}/special-orders/${order.id}/customer-decision/evidence`, fd)).data.special_order; }
      if (latest) onUpdated?.(latest);
    } catch (e) { setErr(e.response?.data?.detail || "Unggah bukti gagal."); } finally { setBusy(false); }
  };

  const basis = review.sample ? `sample ${review.sample.number}${review.sample.decision?.supplier_name ? ` · pemenang ${review.sample.decision.supplier_name}` : ""}` : review.design ? `desain ${review.design.code} (ACC)` : "";

  return (
    <section className="section-card !p-3" data-testid="od-customer-approval">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]"><UserCheck size={12} /> Persetujuan pelanggan atas sample</p>
        {order.customer_decision === "acc" && <span className={`rounded-full border px-2 py-0.5 text-[10.5px] font-bold ${DEC.acc.cls}`} data-testid="od-customer-status-acc">Pelanggan ACC · {order.customer_decision_at}</span>}
      </div>
      {!review.ready ? (
        <p className="rounded-lg border border-dashed border-[#D9D9DE] px-3 py-3 text-[11px] text-[#9A9BA3]" data-testid="od-customer-not-ready">
          Belum ada sample yang diputus pemenang (atau desain ACC). Blok ini aktif setelah R&amp;D menutup sampling.
        </p>
      ) : (
        <p className="text-[11px] text-[#3C3C43]" data-testid="od-customer-basis">Dasar keputusan: <b>{basis}</b></p>
      )}

      {canDecide && !mode && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(DEC).map(([k, m]) => { const I = m.icon; return (
            <button key={k} type="button" className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-[11px] font-bold ${m.cls}`} data-testid={`od-customer-${k}-button`} onClick={() => setMode(k)}><I size={12} /> {m.label}</button>
          ); })}
        </div>
      )}
      {mode && (
        <div className="mt-2 grid gap-2 rounded-lg border border-[#EDEEF1] bg-[#FAFBFC] p-2.5" data-testid="od-customer-form">
          <p className="text-[11px] font-bold">Catat keputusan pelanggan: <span className={`rounded-full border px-2 py-px ${DEC[mode].cls}`}>{DEC[mode].label}</span></p>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="text-[10.5px] font-semibold text-[#6B6B73]">Tanggal keputusan<input type="date" className="input mt-0.5 w-full" value={date} onChange={(e) => setDate(e.target.value)} data-testid="od-customer-date" /></label>
            <label className="text-[10.5px] font-semibold text-[#6B6B73]">Nama kontak pelanggan<input className="input mt-0.5 w-full" value={contact} onChange={(e) => setContact(e.target.value)} placeholder="mis. Ibu Rina (purchasing)" data-testid="od-customer-contact" /></label>
          </div>
          <label className="text-[10.5px] font-semibold text-[#6B6B73]">Catatan {mode !== "acc" && <span className="text-[#C0392B]">*wajib</span>}
            <textarea className="textarea mt-0.5 w-full" rows={2} value={note} onChange={(e) => setNote(e.target.value)} data-testid="od-customer-note"
              placeholder={mode === "acc" ? "mis. disetujui via WA, warna & handfeel sesuai" : mode === "revisi" ? "apa yang harus diperbaiki (warna terlalu gelap, handfeel kurang lembut…)" : "alasan penolakan"} />
          </label>
          <label className="secondary-button w-fit cursor-pointer !py-1 text-[11px]" data-testid="od-customer-evidence-label">
            <Upload size={12} /> Bukti (foto / screenshot WA / PDF) {files.length ? `· ${files.length} berkas` : ""}
            <input type="file" multiple accept="image/*,.pdf" className="hidden" data-testid="od-customer-evidence" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
          </label>
          {mode === "revisi" && <p className="text-[10.5px] text-[#B45309]">Sample R&amp;D baru akan dibuat otomatis (spesifikasi diwarisi) dan OD kembali ke fase Sampling.</p>}
          {mode === "tolak" && <p className="text-[10.5px] text-[#C0392B]">OD akan dibatalkan.</p>}
          {err && <p className="text-[11px] text-[#C0392B]" data-testid="od-customer-error">{err}</p>}
          <div className="flex gap-2">
            <button type="button" className="primary-button !py-1 text-[11px]" disabled={busy || (mode !== "acc" && !note.trim())} onClick={submit} data-testid="od-customer-submit">{busy ? <Loader2 size={12} className="spin" /> : <Check size={12} />} Simpan keputusan</button>
            <button type="button" className="secondary-button !py-1 text-[11px]" disabled={busy} onClick={() => { setMode(""); setErr(""); }} data-testid="od-customer-cancel">Batal</button>
          </div>
        </div>
      )}
      {!mode && err && <p className="mt-1 text-[11px] text-[#C0392B]">{err}</p>}

      <div className="mt-3">
        <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Riwayat keputusan pelanggan · {history.length}</p>
        {history.length === 0 ? <p className="text-[11px] text-[#9A9BA3]" data-testid="od-customer-history-empty">belum ada keputusan tercatat</p> : (
          <ol className="grid gap-1.5" data-testid="od-customer-history">
            {[...history].reverse().map((d) => { const m = DEC[d.decision] || DEC.acc; return (
              <li key={d.id} className="rounded-lg border border-[#EFF0F2] p-2 text-[11px]" data-testid={`od-customer-decision-${d.id}`}>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className={`rounded-full border px-2 py-px text-[10px] font-bold ${m.cls}`}>{m.label}</span>
                  <b>{d.decided_at}</b>
                  {d.contact_name && <span className="text-[#6B6B73]">· {d.contact_name}</span>}
                  <span className="text-[#9A9BA3]">· dicatat {d.recorded_by} {fmtDate(d.recorded_at)}</span>
                  {d.sample_number && <span className="font-mono text-[#6B6B73]">· {d.sample_number}</span>}
                  {d.design_code && <span className="font-mono text-[#6B6B73]">· {d.design_code}</span>}
                  {d.revision_sample_number && <span className="rounded-full bg-[#FFF4E5] px-2 py-px text-[10px] font-bold text-[#B45309]">→ sample baru {d.revision_sample_number}</span>}
                </div>
                {d.note && <p className="mt-1 text-[#3C3C43]">{d.note}</p>}
                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                  {(d.evidence || []).map((f) => <Evidence key={f.id} url={`${API}/special-orders/${order.id}/customer-decision/evidence/${f.id}`} meta={f} />)}
                  {canEdit && !locked && (
                    <label className="cursor-pointer rounded-md border border-dashed border-[#D9D9DE] px-2 py-1 text-[10px] text-[#6B6B73] hover:border-[#0058CC]" data-testid={`od-customer-evidence-add-${d.id}`}>
                      <Upload size={10} className="inline" /> tambah bukti
                      <input type="file" multiple accept="image/*,.pdf" className="hidden" onChange={(e) => { const fs = Array.from(e.target.files || []); if (fs.length) uploadMore(d.id, fs); e.target.value = ""; }} />
                    </label>
                  )}
                </div>
              </li>
            ); })}
          </ol>
        )}
      </div>
    </section>
  );
}

function Evidence({ url, meta }) {
  const isImg = meta.content_type?.startsWith("image/");
  const { src, status } = useProofBlob(url, isImg);
  return (
    <a href={url} target="_blank" rel="noreferrer" title={meta.caption || meta.filename} className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-md border border-[#E5E5EA] bg-[#F5F5F7]" data-testid={`od-customer-evidence-${meta.id}`}>
      {isImg ? (status === "ok" && src ? <img src={src} alt={meta.filename} className="h-full w-full object-cover" /> : <ImageIcon size={14} className="text-[#B5B5BC]" />) : <FileText size={14} className="text-[#6B6B73]" />}
    </a>
  );
}
