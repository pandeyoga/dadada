/** RoleDangerDialog — konfirmasi in-app untuk hapus peran / kembalikan ke bawaan / pindah akun massal. */
import { Loader2, Trash2, RotateCcw, ArrowRightLeft, AlertTriangle } from "lucide-react";

const META = {
  delete: {
    icon: Trash2, tone: "text-[#A8221A]", btn: "!bg-[#A8221A]", confirm: "Ya, hapus peran",
    title: (l) => `Hapus peran “${l}”?`,
    body: () => "Peran beserta pengaturan hak aksesnya dihapus permanen. Tindakan ini tidak bisa dibatalkan.",
  },
  reset: {
    icon: RotateCcw, tone: "text-[#B45309]", btn: "", confirm: "Ya, kembalikan",
    title: (l) => `Kembalikan “${l}” ke bawaan?`,
    body: () => "Semua tingkat akses yang Anda ubah pada peran ini dikembalikan ke bawaan sistem. Akun yang memakainya langsung mengikuti.",
  },
  move: {
    icon: ArrowRightLeft, tone: "text-[#B45309]", btn: "", confirm: "Ya, pindahkan",
    title: (l, x) => `Pindahkan ${x?.count ?? ""} akun dari “${l}”?`,
    body: (x) => `Semua akun berperan ini akan berpindah ke peran “${x?.targetLabel || "—"}” dan langsung mengikuti hak aksesnya (paling lama 1 menit). Peran asal menjadi kosong dan bisa dihapus.`,
  },
};

export default function RoleDangerDialog({ kind, roleLabel, extra, busy, onCancel, onConfirm }) {
  const m = META[kind] || META.delete;
  const Icon = m.icon;
  return (
    <div className="modal-overlay" data-testid="role-editor-danger" onClick={(e) => { if (e.target === e.currentTarget && !busy) onCancel(); }}>
      <div className="modal-card" style={{ maxWidth: 440, width: "92vw" }}>
        <div className="flex items-start gap-2 border-b border-[#EFF0F2] px-4 py-3">
          <AlertTriangle size={15} className={`mt-0.5 shrink-0 ${m.tone}`} />
          <div>
            <h4 className="text-[13px] font-bold" data-testid="role-editor-danger-title">{m.title(roleLabel, extra)}</h4>
            <p className="mt-0.5 text-[11px] text-[#6B6B73]">{m.body(extra)}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3">
          <button type="button" className="secondary-button" data-testid="role-editor-danger-cancel" disabled={busy} onClick={onCancel}>Batal</button>
          <button type="button" className={`primary-button ${m.btn}`} data-testid="role-editor-danger-confirm" disabled={busy} onClick={onConfirm}>
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Icon size={13} />} {m.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
