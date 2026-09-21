import { useEffect, useState } from "react";
import { Plus, ArrowLeft, UserPlus, Phone } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { formatCurrency } from "../../../utils/formatters";
import KNSelect from "../../../components/KNSelect";
import { offlinePost } from "../../../utils/offlineQueue";
import { askConfirm } from "../../../services/confirmService";

const STAGES = [["new", "Baru"], ["contacted", "Dihubungi"], ["qualified", "Potensial"], ["proposal", "Penawaran"], ["negotiation", "Negosiasi"]];
const SOURCES = [["walk_in", "Datang langsung"], ["referral", "Referensi"], ["whatsapp", "WhatsApp"], ["instagram", "Instagram"], ["exhibition", "Pameran"], ["other", "Lainnya"]];
const errText = (e, fb) => { const d = e.response?.data?.detail; return (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || fb; };

/** Pipeline prospek versi HP: kartu per tahap, catat prospek baru, geser tahap, ubah jadi pelanggan. */
export default function MobileLeads() {
  const [rows, setRows] = useState(null);
  const [create, setCreate] = useState(false);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState("");
  const load = () => axios.get(`${API}/crm/leads`).then((r) => setRows((Array.isArray(r.data) ? r.data : r.data.items || []).filter((l) => !["won", "lost", "converted"].includes(l.stage)))).catch((e) => { setRows([]); setMsg({ ok: false, text: errText(e, "Gagal memuat prospek.") }); });
  useEffect(() => { load(); }, []);
  const move = async (l, stage) => { setBusy(l.id); try { await axios.patch(`${API}/crm/leads/${l.id}`, { stage }); load(); } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal mengubah tahap.") }); } finally { setBusy(""); } };
  const convert = async (l) => {
    if (!(await askConfirm({ title: `Jadikan "${l.name}" pelanggan?`, message: "Pelanggan baru dibuat dari data prospek ini (nama, telepon, perusahaan)." }))) return;
    setBusy(l.id); setMsg(null);
    try { const r = await axios.post(`${API}/crm/leads/${l.id}/convert`, {}); setMsg({ ok: true, text: `Prospek "${l.name}" kini pelanggan${r.data?.customer_id ? ` (${r.data.customer_id})` : ""}. Buka menu Pelanggan (CRM) untuk melengkapi alamat.` }); load(); }
    catch (e) { setMsg({ ok: false, text: errText(e, "Gagal mengubah jadi pelanggan.") }); } finally { setBusy(""); }
  };
  if (create) {
    return <MobileLeadCreate onBack={() => setCreate(false)} onDone={() => { setCreate(false); load(); }} />;
  }
  return (
    <div className="space-y-2 p-3" data-testid="m-leads">
      <button className="primary-button w-full py-3 flex items-center justify-center gap-2" onClick={() => setCreate(true)} data-testid="m-lead-new"><Plus size={16} /> Catat prospek baru</button>
      {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"} text-xs`} data-testid="m-leads-msg">{msg.text}</div>}
      {rows === null && <p className="text-xs m-muted" data-testid="m-leads-loading">Memuat prospek…</p>}
      {rows && rows.length === 0 && <p className="text-xs m-muted" data-testid="m-leads-empty">Belum ada prospek aktif.</p>}
      {STAGES.map(([id, label]) => { const items = (rows || []).filter((l) => (l.stage || "new") === id); if (!items.length) return null; return (
        <div key={id} data-testid={`m-leads-stage-${id}`}>
          <p className="px-1 pt-1 text-[11px] font-bold text-[#6B6B73] uppercase tracking-wide">{label} · {items.length}</p>
          {items.map((l) => (
            <div key={l.id} className="m-card p-3 mt-1" data-testid={`m-lead-${l.id}`}>
              <div className="flex items-center gap-2"><div className="flex-1 min-w-0"><p className="truncate text-[13px] font-bold">{l.name}</p><p className="truncate text-[11px] m-muted">{l.company || "-"} · <Phone size={10} className="inline" /> {l.phone || "-"}{l.est_value ? ` · ${formatCurrency(l.est_value)}` : ""}</p></div></div>
              <div className="mt-2 flex gap-2">
                <KNSelect value={l.stage || "new"} onValueChange={(v) => move(l, v)} options={STAGES.map(([v, t]) => ({ value: v, label: t }))} testId={`m-lead-stage-${l.id}`} />
                <button className="primary-button px-3 py-2 flex items-center gap-1 text-xs" disabled={busy === l.id} onClick={() => convert(l)} data-testid={`m-lead-convert-${l.id}`}><UserPlus size={13} /> Jadi pelanggan</button>
              </div>
            </div>
          ))}
        </div>); })}
    </div>
  );
}

function MobileLeadCreate({ onBack, onDone }) {
  const [f, setF] = useState({ name: "", company: "", phone: "", source: "walk_in", est_value: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await offlinePost(`${API}/crm/leads`, { ...f, est_value: Number(f.est_value || 0), stage: "new" }, { label: `Prospek ${f.name}` });
      if (r.queued) { setMsg({ ok: true, text: "Offline — prospek tersimpan di HP, dikirim saat sinyal kembali." }); return; }
      setMsg({ ok: true, text: `Prospek ${f.name} tercatat.` }); setTimeout(onDone, 700);
    } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal menyimpan prospek.") }); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-2 p-3" data-testid="m-lead-create">
      <button className="m-subpage-back" onClick={onBack} data-testid="m-lead-back"><ArrowLeft size={17} /> Prospek</button>
      <div className="m-card p-3 space-y-2">
        <input className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Nama kontak *" value={f.name} onChange={set("name")} data-testid="m-lead-name" />
        <input className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Toko / perusahaan" value={f.company} onChange={set("company")} data-testid="m-lead-company" />
        <input className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Telepon / WhatsApp" inputMode="tel" value={f.phone} onChange={set("phone")} data-testid="m-lead-phone" />
        <KNSelect value={f.source} onValueChange={set("source")} options={SOURCES.map(([v, t]) => ({ value: v, label: t }))} testId="m-lead-source" />
        <input type="number" inputMode="decimal" className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Perkiraan nilai (Rp)" value={f.est_value} onChange={set("est_value")} data-testid="m-lead-value" />
        <textarea className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" rows={2} placeholder="Catatan (kebutuhan kain, jadwal follow-up)" value={f.notes} onChange={set("notes")} data-testid="m-lead-notes" />
        {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"} text-xs`} data-testid="m-lead-msg">{msg.text}</div>}
        <button className="primary-button w-full py-3" disabled={busy || !f.name.trim()} onClick={submit} data-testid="m-lead-submit">{busy ? "Menyimpan…" : "Simpan prospek"}</button>
      </div>
    </div>
  );
}
