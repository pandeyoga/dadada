/** SocialAccounts — master Akun Sosmed per badan usaha (boleh banyak akun per PT). */
import { useEffect, useState } from "react";
import { AtSign, Plus, Pencil } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import FormModal from "../../components/FormModal";
import { Field } from "../rnd/RndField";
import { PLATFORM_STYLE, PlatformChip, fmtN } from "./marketingShared";

const api = {
  list: (params) => axios.get(`${API}/marketing/accounts`, { params }).then((r) => r.data),
  create: (b) => axios.post(`${API}/marketing/accounts`, b).then((r) => r.data),
  update: (id, b) => axios.patch(`${API}/marketing/accounts/${id}`, b).then((r) => r.data),
};

export default function SocialAccounts({ currentUser, selectedEntity = "all" }) {
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [editing, setEditing] = useState(null);
  const canEdit = ["admin", "manager", "designer", "sales", "sales_admin"].includes(currentUser?.role);
  const load = () => api.list(selectedEntity && selectedEntity !== "all" ? { entity_id: selectedEntity } : { entity_id: "all" }).then(setRows).catch(() => {});
  useEffect(() => { load(); }, [selectedEntity]); // eslint-disable-line
  useEffect(() => { axios.get(`${API}/marketing/meta`).then((r) => setMeta(r.data)).catch(() => {}); }, []);
  const byEntity = rows.reduce((m, r) => { (m[r.entity_name] ||= []).push(r); return m; }, {});
  return (
    <div className="grid gap-3" data-testid="mkt-accounts">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-[#6B6B73]">Akun sosial media resmi tiap badan usaha. Akun baru dibuat untuk <b>{meta?.active_entity_name || "badan usaha aktif"}</b>.</p>
        {canEdit && <button type="button" className="primary-button !py-1.5 text-[11px]" onClick={() => setEditing({})} data-testid="mkt-new-account"><Plus size={13} /> Akun baru</button>}
      </div>
      {rows.length === 0 && <p className="rounded-xl border border-dashed border-[#D9D9DE] p-6 text-center text-[12px] text-[#9A9BA3]" data-testid="mkt-accounts-empty">Belum ada akun sosmed terdaftar.</p>}
      {Object.entries(byEntity).map(([ent, list]) => (
        <section key={ent} className="rounded-xl border border-[#EFF0F2] bg-white p-3" data-testid={`mkt-accounts-entity-${ent}`}>
          <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{ent} · {list.length} akun</p>
          <div className="grid gap-1.5 md:grid-cols-2">
            {list.map((a) => (
              <div key={a.id} className={`flex items-center gap-2 rounded-lg border border-[#EFF0F2] px-2.5 py-2 text-[12px] ${a.active ? "" : "opacity-50"}`} data-testid={`mkt-account-${a.id}`}>
                <PlatformChip code={a.platform} />
                <span className="font-bold">@{a.handle}</span>
                {a.label && <span className="text-[#6B6B73]">· {a.label}</span>}
                {a.url && <a href={a.url} target="_blank" rel="noreferrer" className="text-[10.5px] text-[#0058CC] underline">buka</a>}
                <span className="ml-auto text-[10.5px] text-[#8E8E93]">{a.followers ? `${fmtN(a.followers)} pengikut · ` : ""}{a.posts_total} konten{a.active ? "" : " · nonaktif"}</span>
                {canEdit && <button type="button" className="secondary-button !py-0.5 text-[10.5px]" onClick={() => setEditing(a)} data-testid={`mkt-account-edit-${a.id}`}><Pencil size={11} /></button>}
              </div>
            ))}
          </div>
        </section>
      ))}
      {editing && <AccountForm account={editing.id ? editing : null} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function AccountForm({ account, onClose, onSaved }) {
  const [f, setF] = useState({ platform: account?.platform || "instagram", handle: account?.handle || "", url: account?.url || "", label: account?.label || "", followers: account?.followers || "", active: account?.active ?? true, notes: account?.notes || "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const submit = async () => {
    setBusy(true); setErr("");
    try { const body = { ...f, followers: Number(f.followers || 0) }; if (account) { delete body.platform; await api.update(account.id, body); } else await api.create(body); onSaved(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan akun."); } finally { setBusy(false); }
  };
  return (
    <FormModal open title={account ? `Ubah @${account.handle}` : "Akun sosmed baru"} icon={AtSign} onClose={onClose} onSubmit={submit} busy={busy} error={err} testId="mkt-account-form" submitTestId="mkt-account-submit">
      <div className="grid gap-3">
        {!account && <Field label="Platform *"><div className="flex flex-wrap gap-1.5">{Object.entries(PLATFORM_STYLE).map(([c, p]) => <button key={c} type="button" data-testid={`mkt-a-platform-${c}`} onClick={() => set("platform", c)} className={`rounded-full border px-3 py-1 text-[11px] font-bold ${f.platform === c ? "border-transparent" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`} style={f.platform === c ? { background: p.bg, color: p.fg } : undefined}>{p.label}</button>)}</div></Field>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Handle / nama akun *"><input className="field w-full" value={f.handle} onChange={(e) => set("handle", e.target.value)} placeholder="kainnusantara.id" data-testid="mkt-a-handle" /></Field>
          <Field label="Label"><input className="field w-full" value={f.label} onChange={(e) => set("label", e.target.value)} placeholder="Akun utama / Akun grosir" data-testid="mkt-a-label" /></Field>
          <Field label="URL profil"><input className="field w-full" value={f.url} onChange={(e) => set("url", e.target.value)} placeholder="https://instagram.com/…" data-testid="mkt-a-url" /></Field>
          <Field label="Pengikut saat ini"><input type="number" min="0" className="field w-full" value={f.followers} onChange={(e) => set("followers", e.target.value)} data-testid="mkt-a-followers" /></Field>
        </div>
        {account && <label className="flex items-center gap-2 text-[12px]"><input type="checkbox" checked={f.active} onChange={(e) => set("active", e.target.checked)} data-testid="mkt-a-active" /> Akun aktif</label>}
        <Field label="Catatan"><input className="field w-full" value={f.notes} onChange={(e) => set("notes", e.target.value)} data-testid="mkt-a-notes" /></Field>
      </div>
    </FormModal>
  );
}
