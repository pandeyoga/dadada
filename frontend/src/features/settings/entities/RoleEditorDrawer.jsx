/**
 * RoleEditorDrawer — buat / ubah peran & tingkat aksesnya per modul.
 * 3 tingkat per modul, template "salin dari peran", pratinjau menu, dan
 * ringkasan perubahan sebelum disimpan.
 */
import { useMemo, useState } from "react";
import { X, Save, Loader2, ShieldCheck, Copy, Trash2, RotateCcw, Info, Lock } from "lucide-react";

import KNSelect from "../../../components/KNSelect";
import RoleModuleRow, { LEVELS, levelLabel } from "./RoleModuleRow";
import RoleMenuPreview from "./RoleMenuPreview";
import RoleAccountsList from "./RoleAccountsList";
import RoleDangerDialog from "./RoleDangerDialog";
import RoleNotifPreview from "./RoleNotifPreview";
import RoleAdvancedPanel from "./RoleAdvancedPanel";
import { applyLevel, levelOf, moduleActionsChanged, setResource, toggleAction } from "./roleAccessUtil";
import { createAccessRole, patchAccessRole, deleteAccessRole, resetAccessRole, errText } from "./entityApi";

const permsOf = (src) => {
  const out = {};
  Object.entries(src?.permissions || {}).forEach(([r, acts]) => { if (acts?.length) out[r] = [...acts]; });
  return out;
};
const levelsFromPerms = (perms, modules) => Object.fromEntries(modules.map((m) => [m.id, levelOf(perms, m)]));

export default function RoleEditorDrawer({ role, template, roles, modules, labels, onClose, onSaved, onRefresh, onError }) {
  const editing = Boolean(role?.id);
  const locked = Boolean(role?.locked);
  const custom = editing ? Boolean(role.custom) : true;
  const originalPerms = useMemo(() => permsOf(role || template), [role, template]);
  const original = useMemo(() => Object.fromEntries(Object.entries(levelsFromPerms(originalPerms, modules)).map(([k, v]) => [k, v.level])), [originalPerms, modules]);
  const [label, setLabel] = useState(role?.label || (template ? `${template.label} (salinan)` : ""));
  const [description, setDescription] = useState(role?.description || template?.description || "");
  const [baseRole, setBaseRole] = useState(role?.base_role || (template ? (template.custom ? template.base_role : template.id) : ""));
  const [perms, setPerms] = useState(originalPerms);
  const [advanced, setAdvanced] = useState({});   // moduleId → true (panel lanjutan terbuka)
  const [confirm, setConfirm] = useState(false);
  const [danger, setDanger] = useState(null);   // null | "delete" | "reset"
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const levelInfo = useMemo(() => levelsFromPerms(perms, modules), [perms, modules]);
  const levels = useMemo(() => Object.fromEntries(Object.entries(levelInfo).map(([k, v]) => [k, v.level])), [levelInfo]);

  const groups = useMemo(() => {
    const out = [];
    for (const m of modules) {
      let g = out.find((x) => x.name === m.group);
      if (!g) { g = { name: m.group, items: [] }; out.push(g); }
      g.items.push(m);
    }
    return out;
  }, [modules]);

  const changes = modules.filter((m) => moduleActionsChanged(perms, originalPerms, m));
  const counts = LEVELS.map((l) => ({ ...l, n: modules.filter((m) => levels[m.id] === l.id).length }));
  const nameError = custom && label.trim().length < 2 ? "Nama peran minimal 2 karakter." : "";
  const nothingOn = modules.every((m) => levels[m.id] === "none");
  const canSave = !locked && !nameError && (changes.length > 0 || (!editing) || label !== role?.label || description !== (role?.description || ""));

  const copyFrom = (rid) => {
    const src = roles.find((r) => r.id === rid);
    if (!src) return;
    setBaseRole(editing ? baseRole : rid);
    setPerms(permsOf(src));
  };
  const setAll = (lvl) => setPerms((p) => modules.reduce((acc, m) => applyLevel(acc, m, lvl), p));
  const setModuleLevel = (m, lvl) => setPerms((p) => applyLevel(p, m, lvl));
  const onToggleAction = (m) => (res, act) => setPerms((p) => toggleAction(p, m, res, act));
  const onSetResource = (m) => (res, all) => setPerms((p) => setResource(p, m, res, all));

  const submit = async () => {
    setBusy(true); setError("");
    try {
      let res;
      if (editing) {
        res = await patchAccessRole(role.id, {
          ...(custom ? { label: label.trim(), description: description.trim() } : {}),
          permissions: perms,
        });
        onSaved?.(`Hak akses peran “${res.label}” disimpan. ${res.users} akun terpengaruh — berlaku otomatis dalam ≤1 menit.`);
      } else {
        res = await createAccessRole({ label: label.trim(), description: description.trim(), base_role: baseRole, permissions: perms });
        onSaved?.(`Peran “${res.label}” dibuat. Berikan ke akun lewat tab Akun & Akses.`);
      }
    } catch (e) {
      setError(errText(e, "Gagal menyimpan peran.")); onError?.(errText(e, "Gagal menyimpan peran.")); setConfirm(false);
    } finally { setBusy(false); }
  };

  const remove = async () => {
    setBusy(true);
    try { await deleteAccessRole(role.id); onSaved?.(`Peran “${role.label}” dihapus.`); }
    catch (e) { setError(errText(e, "Gagal menghapus peran.")); setDanger(null); }
    finally { setBusy(false); }
  };

  const reset = async () => {
    setBusy(true);
    try { await resetAccessRole(role.id); onSaved?.(`Hak akses “${role.label}” dikembalikan ke bawaan sistem.`); }
    catch (e) { setError(errText(e, "Gagal mengembalikan bawaan.")); setDanger(null); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-overlay" data-testid="role-editor-drawer"
         onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose?.(); }}>
      <div className="modal-card" style={{ maxWidth: 1080, width: "96vw" }}>
        <div className="flex items-start gap-2 border-b border-[#EFF0F2] px-4 py-3">
          <ShieldCheck size={16} className="mt-0.5 text-[#0058CC]" />
          <div className="min-w-0 flex-1">
            <h3 className="text-[13.5px] font-bold" data-testid="role-editor-title">
              {editing ? `Hak Akses · ${role.label}` : (template ? `Duplikat Peran · ${template.label}` : "Buat Peran Baru")}
              {editing && !custom && <span className="ml-2 rounded-full bg-[#F2F2F7] px-2 py-0.5 text-[9.5px] font-semibold text-[#6B6B73]">bawaan sistem</span>}
              {locked && <span className="ml-1 inline-flex items-center gap-0.5 rounded-full bg-[#FCEBEA] px-2 py-0.5 text-[9.5px] font-semibold text-[#A8221A]"><Lock size={9} /> dikunci</span>}
            </h3>
            <p className="text-[11px] text-[#6B6B73]">
              Pilih tingkat akses tiap modul. Perubahan berlaku untuk semua akun dengan peran ini.
            </p>
          </div>
          <button type="button" className="icon-button" aria-label="Tutup" data-testid="role-editor-close" onClick={onClose}><X size={14} /></button>
        </div>

        <div className="grid gap-3 p-4 lg:grid-cols-[1fr_300px]" style={{ maxHeight: "68vh", overflowY: "auto" }}>
          <div className="space-y-2.5">
            {custom ? (
              <div className="grid gap-2.5 sm:grid-cols-2">
                <div className="grid gap-1">
                  <label className="kicker">Nama peran</label>
                  <input className="field" data-testid="role-editor-label" value={label} placeholder="mis. Staf Penagihan"
                         onChange={(e) => setLabel(e.target.value)} />
                </div>
                <div className="grid gap-1">
                  <label className="kicker">Keterangan singkat (opsional)</label>
                  <input className="field" data-testid="role-editor-description" value={description} placeholder="Untuk siapa peran ini?"
                         onChange={(e) => setDescription(e.target.value)} />
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-[#6B6B73]" data-testid="role-editor-builtin-note">{role.description}</p>
            )}

            {!locked && (
              <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-2" data-testid="role-editor-tools">
                <Copy size={12} className="text-[#0058CC]" />
                <span className="text-[10.5px] font-semibold text-[#3A3A3C]">Salin dari peran:</span>
                <div className="min-w-[200px]">
                  <KNSelect className="field !py-1 text-[11px]" data-testid="role-editor-copy-from" value="" placeholder="pilih peran acuan…"
                            onValueChange={copyFrom}
                            options={roles.filter((r) => r.id !== role?.id && r.id !== "admin").map((r) => ({ value: r.id, label: r.label }))} />
                </div>
                <span className="mx-1 text-[#D1D1D6]">|</span>
                <span className="text-[10.5px] font-semibold text-[#3A3A3C]">Semua modul:</span>
                {LEVELS.map((l) => (
                  <button key={l.id} type="button" data-testid={`role-editor-all-${l.id}`} onClick={() => setAll(l.id)}
                          className="rounded-full border border-[#E5E5EA] bg-white px-2 py-0.5 text-[10px] font-semibold text-[#6B6B73] hover:border-[#1C1C1E]/40">
                    {l.label}
                  </button>
                ))}
              </div>
            )}

            {locked && (
              <div className="flex items-start gap-1.5 rounded-md border border-[#F0B5AE] bg-[#FCEBEA] p-2.5" data-testid="role-editor-locked">
                <Lock size={13} className="mt-0.5 shrink-0 text-[#A8221A]" />
                <p className="text-[11px] text-[#3C3C43]">Peran Admin selalu punya semua akses dan tidak bisa diubah, supaya tidak ada yang terkunci keluar dari sistem.</p>
              </div>
            )}

            {groups.map((g) => (
              <div key={g.name} data-testid={`role-editor-group-${g.name}`}>
                <p className="kicker mb-1 mt-1">{g.name}</p>
                <div className="space-y-1.5">
                  {g.items.map((m) => (
                    <RoleModuleRow key={m.id} module={m} value={levels[m.id]} original={original[m.id]}
                                   partial={levelInfo[m.id]?.partial} disabled={locked || busy}
                                   onChange={(v) => setModuleLevel(m, v)}
                                   advanced={!!advanced[m.id]}
                                   onToggleAdvanced={locked ? null : () => setAdvanced((s) => ({ ...s, [m.id]: !s[m.id] }))}>
                      <RoleAdvancedPanel module={m} perms={perms} original={originalPerms} labels={labels} disabled={locked || busy}
                                         onToggle={onToggleAction(m)} onSetResource={onSetResource(m)} />
                    </RoleModuleRow>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2.5">
            <div className="rounded-md border border-[#EFF0F2] bg-white p-2.5" data-testid="role-editor-summary">
              <p className="kicker mb-1">Ringkasan</p>
              <div className="flex flex-wrap gap-1.5">
                {counts.map((c) => (
                  <span key={c.id} data-testid={`role-editor-count-${c.id}`} className={`rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${c.on}`}>
                    {c.n} {c.label}
                  </span>
                ))}
              </div>
              {editing && <RoleAccountsList role={role} roles={roles} canMove={!locked} onMoved={onRefresh} onError={onError} />}
              {!locked && (
                <RoleNotifPreview roleId={editing ? role.id : ""} baseRole={baseRole} permissions={perms} saved={(editing ? role.turn_alerts : template?.turn_alerts) || []} />
              )}
              {baseRole && !editing && <p className="mt-1 text-[10.5px] text-[#6B6B73]">Menu dasar mengikuti peran acuan: <b>{roles.find((r) => r.id === baseRole)?.label}</b>.</p>}
              {nothingOn && <p className="mt-1 text-[10.5px] text-[#A8221A]" data-testid="role-editor-nothing">Belum ada modul yang dinyalakan.</p>}
            </div>
            <RoleMenuPreview modules={modules} levels={levels} baseRole={editing ? role.base_role : baseRole} />
            <div className="flex items-start gap-1.5 rounded-md border border-[#C9DBF7] bg-[#F2F7FF] p-2.5">
              <Info size={12} className="mt-0.5 shrink-0 text-[#0058CC]" />
              <p className="text-[10.5px] text-[#3C3C43]">Perubahan berlaku otomatis untuk yang sedang masuk (paling lama 1 menit atau saat muat ulang) — tidak perlu keluar-masuk lagi. <b>Notifikasi ikut menyesuaikan</b>: hanya layar yang boleh dibuka yang muncul di lonceng, dan "giliran Anda" dikirim ke peran yang memegang wewenangnya.</p>
            </div>
          </div>
        </div>

        {error && <div className="notice-bar danger !py-1.5 mx-4 mb-2" data-testid="role-editor-error"><span className="text-[11.5px]">{error}</span></div>}

        <div className="flex flex-wrap items-center gap-2 border-t border-[#EFF0F2] px-4 py-3">
          {editing && custom && (
            <button type="button" className="secondary-button !text-[#A8221A]" data-testid="role-editor-delete" disabled={busy || !role.deletable}
                    title={role.deletable ? "" : "Masih dipakai akun — pindahkan akunnya dulu."} onClick={() => setDanger("delete")}>
              <Trash2 size={13} /> Hapus peran
            </button>
          )}
          {editing && !custom && !locked && role.modified && (
            <button type="button" className="secondary-button" data-testid="role-editor-reset" disabled={busy} onClick={() => setDanger("reset")}>
              <RotateCcw size={13} /> Kembalikan ke bawaan
            </button>
          )}
          <div className="ml-auto flex gap-2">
            <button type="button" className="secondary-button" data-testid="role-editor-cancel" onClick={onClose}>Batal</button>
            <button type="button" className="primary-button" data-testid="role-editor-save" disabled={busy || !canSave} onClick={() => setConfirm(true)}>
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              {editing ? "Simpan Perubahan" : "Buat Peran"}
            </button>
          </div>
        </div>

        {danger && (
          <RoleDangerDialog kind={danger} roleLabel={role.label} busy={busy}
                            onCancel={() => setDanger(null)} onConfirm={danger === "delete" ? remove : reset} />
        )}

        {confirm && (
          <div className="modal-overlay" data-testid="role-editor-confirm" onClick={(e) => { if (e.target === e.currentTarget) setConfirm(false); }}>
            <div className="modal-card" style={{ maxWidth: 520, width: "92vw" }}>
              <div className="border-b border-[#EFF0F2] px-4 py-3">
                <h4 className="text-[13px] font-bold">Periksa sebelum menyimpan</h4>
                <p className="text-[11px] text-[#6B6B73]">
                  {editing ? `${role.users} akun berperan “${role.label}” akan langsung mengikuti hak baru.` : `Peran “${label.trim()}” akan dibuat dengan akses berikut.`}
                </p>
              </div>
              <div className="max-h-64 overflow-auto p-4">
                {editing && changes.length === 0 && <p className="text-[11px] text-[#6B6B73]">Hanya nama/keterangan yang berubah.</p>}
                <ul className="space-y-1">
                  {(editing ? changes : modules.filter((m) => levels[m.id] !== "none")).map((m) => (
                    <li key={m.id} className="text-[11px] text-[#1C1C1E]" data-testid={`role-editor-confirm-${m.id}`}>
                      <b>{m.label}</b>: {editing ? `${levelLabel(original[m.id])} → ` : ""}<span className="font-semibold text-[#0058CC]">{levelLabel(levels[m.id])}{levelInfo[m.id]?.partial ? " (sebagian aksi)" : ""}</span>
                      {editing && original[m.id] === levels[m.id] && <span className="ml-1 text-[10px] text-[#8C4A00]">· aksi rinci berubah</span>}
                    </li>
                  ))}
                </ul>
                {changes.some((m) => m.sensitive && levels[m.id] !== "none") && (
                  <p className="mt-2 text-[10.5px] font-semibold text-[#B45309]" data-testid="role-editor-confirm-sensitive">
                    Perhatian: modul sensitif dinyalakan — peran ini bisa mengubah pengaturan/akun orang lain.
                  </p>
                )}
              </div>
              <div className="flex justify-end gap-2 border-t border-[#EFF0F2] px-4 py-3">
                <button type="button" className="secondary-button" data-testid="role-editor-confirm-cancel" onClick={() => setConfirm(false)}>Periksa lagi</button>
                <button type="button" className="primary-button" data-testid="role-editor-confirm-save" disabled={busy} onClick={submit}>
                  {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Ya, simpan
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
