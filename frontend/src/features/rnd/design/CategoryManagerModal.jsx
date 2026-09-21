/** CategoryManagerModal — master Kategori Pattern & Kategori Design (admin & manager bisa menambah pilihan sendiri). */
import { useEffect, useState } from "react";
import { Plus, Tags, X } from "lucide-react";
import { createCategory, patchCategory, studioCategories } from "../rndApi";
import { errMsg } from "../rndMeta";

const TYPES = [["pattern", "Kategori Pattern"], ["design", "Kategori Design"]];

export default function CategoryManagerModal({ designType = "pattern", onClose }) {
  const [type, setType] = useState(designType);
  const [rows, setRows] = useState([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => studioCategories({ design_type: type, status: "all" }).then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, [type]); // eslint-disable-line react-hooks/exhaustive-deps

  const add = async () => {
    setErr(""); setBusy(true);
    try {
      await createCategory({ design_type: type, code, name });
      setCode(""); setName(""); await load();
    } catch (e) { setErr(errMsg(e, "Kategori gagal ditambah.")); } finally { setBusy(false); }
  };
  const toggle = async (r) => {
    setErr("");
    try { await patchCategory(r.id, { status: r.status === "active" ? "inactive" : "active" }); await load(); }
    catch (e) { setErr(errMsg(e, "Gagal mengubah status.")); }
  };

  return (
    <div className="fixed inset-0 z-[180] flex items-center justify-center bg-black/50 p-4" data-testid="category-manager-modal"
      onClick={onClose}>
      <div className="flex max-h-[85vh] w-full max-w-[520px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-[#EFF0F2] px-4 py-3">
          <h2 className="flex items-center gap-2 text-[14px] font-bold"><Tags size={15} className="text-[#6B219A]" /> Master Kategori Desain</h2>
          <button className="icon-button" onClick={onClose} data-testid="category-manager-close"><X size={16} /></button>
        </div>
        <div className="space-y-3 overflow-y-auto p-4">
          <p className="text-[10.5px] text-[#6B6B73]">Pilihan di sini muncul di form desainer. Tambah kode + nama untuk memperluas pilihan; nonaktifkan bila tidak dipakai lagi.</p>
          <div className="flex gap-1.5">
            {TYPES.map(([k, l]) => (
              <button key={k} onClick={() => setType(k)} data-testid={`category-type-${k}`}
                className={`rounded-full border px-3 py-1 text-[11px] font-medium ${type === k ? "border-[#6B219A] bg-[#6B219A] text-white" : "border-[#E5E5EA] bg-white"}`}>{l}</button>
            ))}
          </div>
          {err && <div className="rounded-lg bg-[#FDEDE7] px-3 py-2 text-[11.5px] text-[#C0392B]" data-testid="category-error">{err}</div>}
          <div className="flex gap-2">
            <input className="field !w-24 uppercase" placeholder="KODE" value={code} maxLength={6} data-testid="category-code-input"
              onChange={(e) => setCode(e.target.value.toUpperCase())} />
            <input className="field flex-1" placeholder="Nama kategori" value={name} data-testid="category-name-input"
              onChange={(e) => setName(e.target.value)} />
            <button className="primary-button" disabled={busy || code.length < 2 || !name.trim()} onClick={add} data-testid="category-add-button">
              <Plus size={13} /> Tambah
            </button>
          </div>
          <div className="divide-y divide-[#F0F0F2] rounded-lg border border-[#EFF0F2]">
            {rows.map((r) => (
              <div key={r.id} className="flex items-center justify-between px-3 py-1.5 text-[12px]" data-testid={`category-row-${r.code}`}>
                <span><b className="font-mono">{r.code}</b> <span className="ml-2">{r.name}</span></span>
                <button className={`text-[10.5px] ${r.status === "active" ? "text-[#1A7A3A]" : "text-[#9A9BA3]"}`}
                  onClick={() => toggle(r)} data-testid={`category-toggle-${r.code}`}>
                  {r.status === "active" ? "aktif · nonaktifkan" : "nonaktif · aktifkan"}
                </button>
              </div>
            ))}
            {rows.length === 0 && <p className="px-3 py-3 text-[11px] text-[#9A9BA3]">Belum ada kategori.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
