/** RoleAccountsList — daftar akun yang memakai sebuah peran + pindah akun massal ke peran lain. */
import { useEffect, useState } from "react";
import { Users, ArrowRightLeft, Loader2 } from "lucide-react";

import KNSelect from "../../../components/KNSelect";
import RoleDangerDialog from "./RoleDangerDialog";
import { accessRole, moveAccessRoleUsers, errText } from "./entityApi";

export default function RoleAccountsList({ role, roles, canMove, onMoved, onError }) {
  const [accounts, setAccounts] = useState(null);
  const [target, setTarget] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const count = role.users;

  useEffect(() => {
    let alive = true;
    accessRole(role.id).then((r) => { if (alive) setAccounts(r.accounts || []); }).catch(() => { if (alive) setAccounts([]); });
    return () => { alive = false; };
  }, [role.id, count]);

  const targetLabel = roles.find((r) => r.id === target)?.label || "";
  const move = async () => {
    setBusy(true);
    try {
      const res = await moveAccessRoleUsers(role.id, target);
      setConfirm(false); setTarget("");
      onMoved?.(`${res.moved} akun dipindahkan dari “${role.label}” ke “${res.to_role_label}”.`);
    } catch (e) { setConfirm(false); onError?.(errText(e, "Gagal memindahkan akun.")); }
    finally { setBusy(false); }
  };

  return (
    <details className="mt-1.5" data-testid="role-editor-accounts" open={count > 0 && count <= 5}>
      <summary className="inline-flex cursor-pointer items-center gap-1 text-[10.5px] font-semibold text-[#3A3A3C]" data-testid="role-editor-users">
        <Users size={10} /> {count} akun memakai peran ini
      </summary>
      {accounts === null && <p className="mt-1 pl-3 text-[10px] text-[#8E8E93]">Memuat akun…</p>}
      {accounts && accounts.length === 0 && (
        <p className="mt-1 pl-3 text-[10px] text-[#8E8E93]" data-testid="role-editor-accounts-empty">
          Belum ada akun. Berikan lewat tab Akun & Akses.
        </p>
      )}
      {accounts && accounts.length > 0 && (
        <ul className="mt-1 max-h-40 space-y-1 overflow-auto pl-3">
          {accounts.map((a) => (
            <li key={a.id} className="text-[10px] leading-tight" data-testid={`role-editor-account-${a.id}`}>
              <span className="font-semibold text-[#1C1C1E]">{a.name}</span>
              {a.status !== "active" && <span className="ml-1 rounded-full bg-[#F2F2F7] px-1.5 text-[9px] text-[#6B6B73]">nonaktif</span>}
              <br />
              <span className="text-[#6B6B73]">{a.email}{a.entity_name ? ` · ${a.entity_name}` : ""}</span>
            </li>
          ))}
        </ul>
      )}
      {canMove && accounts && accounts.length > 0 && (
        <div className="mt-2 rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2" data-testid="role-editor-move">
          <p className="mb-1 text-[10px] font-semibold text-[#3A3A3C]">Pindahkan semua akun ke peran lain</p>
          <div className="flex items-center gap-1.5">
            <div className="min-w-0 flex-1">
              <KNSelect className="field !py-1 text-[11px]" data-testid="role-editor-move-target" value={target} placeholder="pilih peran tujuan…"
                        onValueChange={setTarget}
                        options={roles.filter((r) => r.id !== role.id && r.id !== "admin").map((r) => ({ value: r.id, label: r.label }))} />
            </div>
            <button type="button" className="secondary-button !py-1 text-[10.5px]" data-testid="role-editor-move-button"
                    disabled={!target || busy} onClick={() => setConfirm(true)}>
              {busy ? <Loader2 size={12} className="animate-spin" /> : <ArrowRightLeft size={12} />} Pindahkan {accounts.length}
            </button>
          </div>
        </div>
      )}
      {confirm && (
        <RoleDangerDialog kind="move" roleLabel={role.label} extra={{ count: accounts?.length || 0, targetLabel }} busy={busy}
                          onCancel={() => setConfirm(false)} onConfirm={move} />
      )}
    </details>
  );
}
