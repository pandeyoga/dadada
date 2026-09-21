/** ColorwaysPanel — alternatif kombinasi warna (colorway); warna WAJIB dari master. */
import { useState } from "react";
import { Plus, Star, Trash2, Upload } from "lucide-react";
import { addColorway, deleteColorway, designFileUrl, updateColorway, uploadDesignKindFile } from "../rndApi";
import { errMsg } from "../rndMeta";
import ColorPicker from "./ColorPicker";

export default function ColorwaysPanel({ design, canEdit, onDone, onError }) {
  const [form, setForm] = useState(null); // { id?, name, note, colors }
  const [busy, setBusy] = useState(false);
  const cws = design.colorways || [];
  const fileById = Object.fromEntries((design.files || []).map((f) => [f.id, f]));

  const save = async () => {
    if (!form.colors.length) { onError?.("Pilih minimal 1 warna dari master."); return; }
    setBusy(true);
    try {
      const body = { name: form.name, note: form.note, colors: form.colors.map((c) => ({ color_id: c.color_id, role: c.role || "" })) };
      if (form.id) await updateColorway(design.id, form.id, body); else await addColorway(design.id, body);
      setForm(null); onDone?.("Alternatif warna tersimpan.");
    } catch (e) { onError?.(errMsg(e, "Alternatif warna gagal disimpan.")); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-2" data-testid="design-colorways-panel">
      <div className="rounded-lg border border-[#EFF0F2] bg-white p-3" data-testid="design-palette-main">
        <p className="mb-1 text-[10.5px] font-bold uppercase text-[#8E8E93]">Palet utama · {(design.colors || []).length} warna</p>
        <Swatches colors={design.colors || []} />
      </div>
      {cws.map((cw) => (
        <div key={cw.id} className="rounded-lg border border-[#EFF0F2] bg-white p-3" data-testid={`design-colorway-${cw.id}`}>
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[12px] font-bold">{cw.name} <span className="ml-1 font-mono text-[10px] text-[#6B6B73]">{cw.code}</span>
                {cw.is_default && <span className="ml-1 rounded bg-[#F5A623] px-1 text-[9px] text-white">UTAMA</span>}</p>
              {cw.note && <p className="text-[10.5px] text-[#6B6B73]">{cw.note}</p>}
            </div>
            {canEdit && (
              <div className="flex gap-1">
                <button className="icon-button" title="Jadikan utama" data-testid={`design-colorway-default-${cw.id}`}
                  onClick={() => updateColorway(design.id, cw.id, { is_default: true }).then(() => onDone?.()).catch((e) => onError?.(errMsg(e)))}>
                  <Star size={12} /></button>
                <label className="icon-button cursor-pointer" title="Unggah mockup colorway ini">
                  <Upload size={12} />
                  <input type="file" className="hidden" accept="image/*" data-testid={`design-colorway-upload-${cw.id}`}
                    onChange={(e) => { const file = e.target.files?.[0]; if (file) uploadDesignKindFile(design.id, "mockup", file, { colorway_id: cw.id }).then(() => onDone?.("Mockup terunggah.")).catch((er) => onError?.(errMsg(er))); e.target.value = ""; }} />
                </label>
                <button className="icon-button" data-testid={`design-colorway-edit-${cw.id}`}
                  onClick={() => setForm({ id: cw.id, name: cw.name, note: cw.note || "", colors: cw.colors || [] })}>Ubah</button>
                <button className="icon-button text-red-400" data-testid={`design-colorway-delete-${cw.id}`}
                  onClick={() => deleteColorway(design.id, cw.id).then(() => onDone?.("Alternatif dihapus.")).catch((e) => onError?.(errMsg(e)))}>
                  <Trash2 size={12} /></button>
              </div>
            )}
          </div>
          <div className="mt-2"><Swatches colors={cw.colors || []} /></div>
          {(cw.file_ids || []).length > 0 && (
            <div className="mt-2 flex gap-1.5">
              {cw.file_ids.map((fid) => fileById[fid] && (
                <a key={fid} href={designFileUrl(design.id, fid)} target="_blank" rel="noreferrer" className="h-14 w-14 overflow-hidden rounded border">
                  <img src={designFileUrl(design.id, fid)} alt="mockup" className="h-full w-full object-cover" />
                </a>
              ))}
            </div>
          )}
        </div>
      ))}
      {cws.length === 0 && <p className="text-[11px] text-[#9A9BA3]" data-testid="design-colorways-empty">Belum ada alternatif warna.</p>}

      {canEdit && !form && (
        <button className="secondary-button text-[11.5px]" onClick={() => setForm({ name: "", note: "", colors: [] })} data-testid="design-colorway-add">
          <Plus size={13} /> Tambah alternatif warna
        </button>
      )}
      {form && (
        <div className="space-y-2 rounded-lg border border-[#6B219A] bg-[#FBF8FE] p-3" data-testid="design-colorway-form">
          <div className="grid gap-2 md:grid-cols-2">
            <input className="field" placeholder="Nama alternatif (mis. Navy–Emas)" value={form.name} data-testid="design-colorway-name"
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <input className="field" placeholder="Catatan (opsional)" value={form.note} data-testid="design-colorway-note"
              onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </div>
          <ColorPicker value={form.colors} onChange={(v) => setForm({ ...form, colors: v })} testId="design-colorway-colors" />
          <div className="flex justify-end gap-2">
            <button className="secondary-button !py-1 text-[11px]" onClick={() => setForm(null)}>Batal</button>
            <button className="primary-button !py-1 text-[11px]" disabled={busy} onClick={save} data-testid="design-colorway-save">Simpan</button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Swatches({ colors, size = 28 }) {
  if (!colors.length) return <span className="text-[10.5px] text-[#9A9BA3]">belum ada warna</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {colors.map((c) => (
        <div key={c.color_id} className="flex items-center gap-1.5 rounded-full border border-[#E5E5EA] bg-white py-0.5 pl-0.5 pr-2 text-[10.5px]" title={c.hex}>
          <span className="rounded-full border border-black/10" style={{ background: c.hex, width: size * 0.7, height: size * 0.7 }} />
          <span><b className="font-mono">{c.code}</b> {c.name}{c.role && <span className="text-[#8E8E93]"> · {c.role}</span>}</span>
        </div>
      ))}
    </div>
  );
}
