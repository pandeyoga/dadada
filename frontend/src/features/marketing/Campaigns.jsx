/** Campaigns — kampanye/tema konten (periode, platform, target) + ringkasan post & performa. */
import { useEffect, useState } from "react";
import { Flag, Plus, Pencil } from "lucide-react";
import FormModal from "../../components/FormModal";
import { Field } from "../rnd/RndField";
import { mktApi, PLATFORM_STYLE, fmtN, STATUS_STYLE } from "./marketingShared";

const COLORS = ["#0058CC", "#C13584", "#1B7F4B", "#B45309", "#6D28D9", "#C0392B", "#0F766E"];

export default function Campaigns({ currentUser }) {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const canEdit = ["admin", "manager", "designer", "sales", "sales_admin"].includes(currentUser?.role);
  const load = () => mktApi.campaigns().then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div className="grid gap-3" data-testid="mkt-campaigns">
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-[#6B6B73]">Kampanye mengelompokkan konten dalam satu tema & periode (mis. "Lebaran 2027", "Launching Koleksi Navy").</p>
        {canEdit && <button type="button" className="primary-button !py-1.5 text-[11px]" onClick={() => setEditing({})} data-testid="mkt-new-campaign"><Plus size={13} /> Kampanye baru</button>}
      </div>
      {rows.length === 0 && <p className="rounded-xl border border-dashed border-[#D9D9DE] p-6 text-center text-[12px] text-[#9A9BA3]" data-testid="mkt-campaigns-empty">Belum ada kampanye.</p>}
      <div className="grid gap-2 md:grid-cols-2">
        {rows.map((c) => (
          <div key={c.id} className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid={`mkt-campaign-${c.id}`} style={{ borderLeft: `4px solid ${c.color || "#0058CC"}` }}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-[13px] font-bold">{c.name} {c.status === "archived" && <span className="ml-1 rounded-full bg-[#F2F2F7] px-2 py-px text-[10px] text-[#6B6B73]">arsip</span>}</p>
                <p className="text-[11px] text-[#6B6B73]">{c.theme}{c.start_date ? ` · ${c.start_date} → ${c.end_date || "…"}` : ""}</p>
              </div>
              {canEdit && <button type="button" className="secondary-button !py-0.5 text-[10.5px]" onClick={() => setEditing(c)} data-testid={`mkt-campaign-edit-${c.id}`}><Pencil size={11} /> Ubah</button>}
            </div>
            {c.goal && <p className="mt-1 text-[11px]"><b>Tujuan:</b> {c.goal}</p>}
            <div className="mt-1 flex flex-wrap gap-1">{(c.platforms || []).map((p) => <span key={p} className="rounded-full px-1.5 py-px text-[9.5px] font-bold" style={{ background: PLATFORM_STYLE[p]?.bg, color: PLATFORM_STYLE[p]?.fg }}>{PLATFORM_STYLE[p]?.label || p}</span>)}</div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
              <Stat label="Konten" value={c.posts_total} sub={Object.entries(c.post_counts || {}).map(([k, v]) => `${STATUS_STYLE[k]?.label || k} ${v}`).join(" · ")} />
              <Stat label="Jangkauan" value={fmtN(c.reach_total)} />
              <Stat label="Engagement" value={fmtN(c.engagement_total)} sub={c.budget ? `anggaran Rp ${fmtN(c.budget)}` : ""} />
            </div>
          </div>
        ))}
      </div>
      {editing && <CampaignForm campaign={editing.id ? editing : null} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function Stat({ label, value, sub }) {
  return <div className="rounded-lg bg-[#FAFBFC] p-1.5"><p className="text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p><p className="text-[13px] font-bold">{value ?? 0}</p>{sub && <p className="truncate text-[9.5px] text-[#8E8E93]" title={sub}>{sub}</p>}</div>;
}

function CampaignForm({ campaign, onClose, onSaved }) {
  const [f, setF] = useState({ name: campaign?.name || "", theme: campaign?.theme || "", goal: campaign?.goal || "", start_date: campaign?.start_date || "", end_date: campaign?.end_date || "", platforms: campaign?.platforms || [], budget: campaign?.budget || "", color: campaign?.color || COLORS[0], status: campaign?.status || "active", notes: campaign?.notes || "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const submit = async () => {
    setBusy(true); setErr("");
    try { if (campaign) await mktApi.updateCampaign(campaign.id, { ...f, budget: Number(f.budget || 0) }); else await mktApi.createCampaign({ ...f, budget: Number(f.budget || 0) }); onSaved(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan kampanye."); } finally { setBusy(false); }
  };
  return (
    <FormModal open title={campaign ? "Ubah kampanye" : "Kampanye baru"} icon={Flag} onClose={onClose} onSubmit={submit} busy={busy} error={err} testId="mkt-campaign-form" submitTestId="mkt-campaign-submit">
      <div className="grid gap-3">
        <Field label="Nama kampanye *"><input className="field w-full" value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="mis. Lebaran 2027" data-testid="mkt-c-name" /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tema"><input className="field w-full" value={f.theme} onChange={(e) => set("theme", e.target.value)} placeholder="Koleksi warna hangat & motif klasik" data-testid="mkt-c-theme" /></Field>
          <Field label="Tujuan"><input className="field w-full" value={f.goal} onChange={(e) => set("goal", e.target.value)} placeholder="+500 pengikut, 50 prospek DM" data-testid="mkt-c-goal" /></Field>
          <Field label="Mulai"><input type="date" className="field w-full" value={f.start_date} onChange={(e) => set("start_date", e.target.value)} data-testid="mkt-c-start" /></Field>
          <Field label="Selesai"><input type="date" className="field w-full" value={f.end_date} onChange={(e) => set("end_date", e.target.value)} data-testid="mkt-c-end" /></Field>
          <Field label="Anggaran (Rp)"><input type="number" min="0" className="field w-full" value={f.budget} onChange={(e) => set("budget", e.target.value)} data-testid="mkt-c-budget" /></Field>
          <Field label="Status"><select className="field w-full" value={f.status} onChange={(e) => set("status", e.target.value)} data-testid="mkt-c-status"><option value="active">Aktif</option><option value="archived">Arsip</option></select></Field>
        </div>
        <Field label="Platform">
          <div className="flex flex-wrap gap-1.5">{Object.entries(PLATFORM_STYLE).map(([c, p]) => <button key={c} type="button" data-testid={`mkt-c-platform-${c}`} onClick={() => set("platforms", f.platforms.includes(c) ? f.platforms.filter((x) => x !== c) : [...f.platforms, c])} className={`rounded-full border px-3 py-1 text-[11px] font-bold ${f.platforms.includes(c) ? "border-transparent" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`} style={f.platforms.includes(c) ? { background: p.bg, color: p.fg } : undefined}>{p.label}</button>)}</div>
        </Field>
        <Field label="Warna penanda"><div className="flex gap-1.5">{COLORS.map((c) => <button key={c} type="button" onClick={() => set("color", c)} className={`h-6 w-6 rounded-full border-2 ${f.color === c ? "border-[#111]" : "border-transparent"}`} style={{ background: c }} data-testid={`mkt-c-color-${c.slice(1)}`} />)}</div></Field>
        <Field label="Catatan"><input className="field w-full" value={f.notes} onChange={(e) => set("notes", e.target.value)} data-testid="mkt-c-notes" /></Field>
      </div>
    </FormModal>
  );
}
