/**
 * RoleAccessPanel — tab "Peran & Hak Akses": daftar peran (bawaan + kustom),
 * jumlah akun, ringkasan tingkat akses, dan pintu ke editor.
 */
import { useCallback, useEffect, useState } from "react";
import { Plus, ShieldCheck, Lock, Users, Sparkles, Pencil, Copy } from "lucide-react";

import RoleEditorDrawer from "./RoleEditorDrawer";
import { accessModules, accessRoles, errText } from "./entityApi";

function RoleCard({ role, onOpen, onDuplicate }) {
  const lv = Object.values(role.levels || {});
  const n = (k) => lv.filter((x) => x.level === k).length;
  return (
    <div role="button" tabIndex={0} data-testid={`role-card-${role.id}`} onClick={() => onOpen(role)}
         onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(role); } }}
         className="flex cursor-pointer flex-col gap-1.5 rounded-xl border border-[#EFF0F2] bg-white p-3 text-left transition-colors hover:border-[#0058CC]/50">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[12.5px] font-bold text-[#1C1C1E]" data-testid={`role-card-label-${role.id}`}>{role.label}</p>
          <p className="line-clamp-2 text-[10.5px] text-[#6B6B73]">{role.description || "—"}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9.5px] font-semibold ${
          role.custom ? "bg-[#F3E9FA] text-[#6B219A]" : "bg-[#F2F2F7] text-[#6B6B73]"}`}
              data-testid={`role-card-kind-${role.id}`}>
          {role.custom ? "Kustom" : "Bawaan"}
        </span>
        {onDuplicate && (
          <button type="button" className="icon-button shrink-0" title="Duplikat peran ini" aria-label={`Duplikat ${role.label}`}
                  data-testid={`role-card-duplicate-${role.id}`}
                  onClick={(e) => { e.stopPropagation(); onDuplicate(role); }}>
            <Copy size={12} />
          </button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
        <span className="inline-flex items-center gap-1 rounded-full border border-[#E5E5EA] px-2 py-0.5 font-semibold text-[#3A3A3C]" data-testid={`role-card-users-${role.id}`}>
          <Users size={10} /> {role.users} akun
        </span>
        <span className="rounded-full bg-[#EEF9F1] px-2 py-0.5 font-semibold text-[#1B7F4B]">{n("manage")} kelola</span>
        <span className="rounded-full bg-[#EAF2FF] px-2 py-0.5 font-semibold text-[#0058CC]">{n("view")} lihat</span>
        <span className="rounded-full bg-[#F2F2F7] px-2 py-0.5 font-semibold text-[#6B6B73]">{n("none")} tidak ada</span>
        {role.locked && <span className="inline-flex items-center gap-0.5 rounded-full bg-[#FCEBEA] px-2 py-0.5 font-semibold text-[#A8221A]"><Lock size={9} /> dikunci</span>}
        {role.modified && <span className="inline-flex items-center gap-0.5 rounded-full bg-[#FEF7EC] px-2 py-0.5 font-semibold text-[#8C4A00]" data-testid={`role-card-modified-${role.id}`}><Pencil size={9} /> diubah dari bawaan</span>}
        {role.base_role_label && <span className="text-[#8E8E93]">acuan: {role.base_role_label}</span>}
      </div>
    </div>
  );
}

export default function RoleAccessPanel({ canManage, onChanged, onError }) {
  const [roles, setRoles] = useState([]);
  const [modules, setModules] = useState([]);
  const [labels, setLabels] = useState({});
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState(null);   // null | {} (baru) | {template} (duplikat) | role

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, m] = await Promise.all([accessRoles(), accessModules()]);
      setRoles(r); setModules(m.modules || []);
      setLabels({ resource_labels: m.resource_labels || {}, action_labels: m.action_labels || {} });
      return r;
    } catch (e) { onError?.(errText(e, "Gagal memuat daftar peran.")); return null; }
    finally { setLoading(false); }
  }, [onError]);

  useEffect(() => { load(); }, [load]);

  const duplicate = canManage ? (r) => setEditor({ template: r }) : null;
  const refreshEditor = async (msg) => {
    onChanged?.(msg);
    const list = await load();
    const cur = list?.find((x) => x.id === editor?.id);
    setEditor(cur || null);
  };

  const customs = roles.filter((r) => r.custom);
  const builtins = roles.filter((r) => !r.custom);

  return (
    <div data-testid="role-access-panel">
      <div className="mb-3 flex flex-wrap items-start gap-2 rounded-md border border-[#C9DBF7] bg-[#F2F7FF] px-3 py-2">
        <ShieldCheck size={14} className="mt-0.5 text-[#0058CC]" />
        <div className="min-w-0 flex-1">
          <p className="text-[11.5px] font-bold text-[#1C1C1E]">Peran menentukan modul mana yang boleh dilihat dan dikelola.</p>
          <p className="text-[10.5px] text-[#6B6B73]">
            Tiga tingkat per modul: <b>Tidak ada</b> (menu tersembunyi) · <b>Lihat saja</b> (baca tanpa tombol ubah) · <b>Kelola penuh</b>.
            Notifikasi mengikuti pengaturan ini — pengguna hanya menerima pemberitahuan untuk layar yang boleh dibukanya.
            Buat peran kustom bila peran bawaan tidak pas — misalnya "Staf Penagihan" yang hanya butuh piutang & pelanggan.
          </p>
        </div>
        {canManage && (
          <button type="button" className="primary-button" data-testid="role-create-button" onClick={() => setEditor({})}>
            <Plus size={14} /> Buat Peran Baru
          </button>
        )}
      </div>

      {loading && <p className="text-[11px] text-[#8E8E93]" data-testid="role-access-loading">Memuat peran…</p>}

      {!loading && (
        <>
          <div className="mb-1.5 flex items-center gap-1.5">
            <Sparkles size={12} className="text-[#6B219A]" />
            <p className="kicker !mb-0">Peran kustom ({customs.length})</p>
          </div>
          {customs.length === 0 ? (
            <div className="mb-4 rounded-xl border border-dashed border-[#E5E5EA] bg-[#FAFBFC] px-4 py-5 text-center" data-testid="role-custom-empty">
              <p className="text-[11.5px] font-semibold text-[#1C1C1E]">Belum ada peran kustom.</p>
              <p className="text-[10.5px] text-[#8E8E93]">Klik "Buat Peran Baru", salin dari peran bawaan yang paling mirip, lalu sesuaikan modulnya.</p>
            </div>
          ) : (
            <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="role-custom-grid">
              {customs.map((r) => <RoleCard key={r.id} role={r} onOpen={setEditor} onDuplicate={duplicate} />)}
            </div>
          )}
          <p className="kicker mb-1.5">Peran bawaan sistem ({builtins.length}) — hak aksesnya bisa disesuaikan</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="role-builtin-grid">
            {builtins.map((r) => <RoleCard key={r.id} role={r} onOpen={setEditor} onDuplicate={r.locked ? null : duplicate} />)}
          </div>
        </>
      )}

      {editor && (
        <RoleEditorDrawer key={editor.id || editor.template?.id || "new"}
                          role={editor.id ? editor : null} template={editor.template || null} roles={roles} modules={modules} labels={labels}
                          onClose={() => setEditor(null)}
                          onSaved={(msg) => { setEditor(null); onChanged?.(msg); load(); }}
                          onRefresh={refreshEditor}
                          onError={onError} />
      )}
    </div>
  );
}
