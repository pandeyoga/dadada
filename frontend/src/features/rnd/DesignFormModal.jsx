/**
 * DesignFormModal — Desain Baru / Ubah Desain (revisi klien 17 Sep 2026).
 * Kode OTOMATIS: inisial desainer · Kategori Pattern · Kategori Design · urut (mis. SRI-SLR-AO-001).
 * Tanpa "jenis desain", tanpa palet warna, tanpa peruntukan produk (itu ditetapkan penilai saat ACC).
 */
import { useEffect, useState } from "react";
import { Layers, Save, Settings2, X } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { createDesign, patchDesign, studioCategories, studioNextCode } from "./rndApi";
import { errMsg } from "./rndMeta";
import TagInput from "./design/TagInput";
import CategoryManagerModal from "./design/CategoryManagerModal";

export default function DesignFormModal({ mode = "create", design, canManageMaster = false, onClose, onSaved }) {
  const [f, setF] = useState({
    title: design?.title || "",
    category_code: design?.category_code || "",
    design_category_code: design?.design_category_code || "",
    repeat_cm: design?.repeat_cm ?? "",
    screen_count: design?.screen_count ?? "",
    story: design?.story || "",
    tags: design?.tags || [],
  });
  const [patternCats, setPatternCats] = useState([]);
  const [designCats, setDesignCats] = useState([]);
  const [preview, setPreview] = useState(null);
  const [catModal, setCatModal] = useState(null); // axis: pattern | design
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const isEdit = mode === "edit";

  const loadCats = () => {
    studioCategories({ design_type: "pattern" }).then(setPatternCats).catch(() => setPatternCats([]));
    studioCategories({ design_type: "design" }).then(setDesignCats).catch(() => setDesignCats([]));
  };
  useEffect(() => { loadCats(); }, []);
  useEffect(() => {
    if (isEdit) return;
    studioNextCode({ category_code: f.category_code, design_category_code: f.design_category_code })
      .then(setPreview).catch(() => setPreview(null));
  }, [f.category_code, f.design_category_code, isEdit]);

  const num = (v) => (v === "" || v === null ? null : Number(String(v).replace(",", ".")));

  const save = async () => {
    setErr("");
    if (!f.title.trim()) { setErr("Judul desain wajib diisi."); return; }
    if (!f.category_code) { setErr("Pilih Kategori Pattern (salur, batik, bunga, …)."); return; }
    if (!f.design_category_code) { setErr("Pilih Kategori Design (allover / pinggiran)."); return; }
    setSaving(true);
    try {
      const body = {
        title: f.title, category_code: f.category_code, design_category_code: f.design_category_code,
        repeat_cm: num(f.repeat_cm), screen_count: num(f.screen_count), story: f.story, tags: f.tags,
      };
      const res = isEdit ? await patchDesign(design.id, body) : await createDesign(body);
      onSaved?.(res);
    } catch (e) {
      setErr(errMsg(e, "Desain gagal disimpan."));
      setSaving(false);
    }
  };

  const opts = (rows) => rows.map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` }));
  const manageBtn = (axis) => canManageMaster && (
    <button type="button" className="inline-flex items-center gap-1 text-[10px] text-[#6B219A] hover:underline"
      data-testid={`design-manage-categories-${axis}`} onClick={() => setCatModal(axis)}>
      <Settings2 size={10} /> kelola
    </button>
  );

  return (
    <div data-testid="design-form-modal"
      className="fixed inset-0 z-[172] flex items-center justify-center bg-black/50 p-4"
      {...overlayDismiss(onClose)}>
      <div className="flex max-h-[92vh] w-full max-w-[680px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-[#EFF0F2] px-4 py-3">
          <h2 className="flex items-center gap-2 text-[15px] font-bold">
            <Layers size={16} className="text-[#6B219A]" />
            {isEdit ? "Ubah Desain" : "Desain Baru"}
          </h2>
          <button className="icon-button" onClick={onClose} data-testid="design-form-close"><X size={18} /></button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {err && (
            <div className="rounded-lg bg-[#FDEDE7] px-3 py-2 text-[11.5px] text-[#C0392B]" data-testid="design-form-error">{err}</div>
          )}

          <div className="grid gap-2.5 md:grid-cols-2">
            <Field label="Judul desain *">
              <input className="field" data-testid="design-title-input" value={f.title}
                onChange={(e) => set("title", e.target.value)} placeholder="mis. Salur Pelangi Senja" />
            </Field>
            <Field label={isEdit ? "Kode desain" : "Kode desain (otomatis)"}>
              <div className="field flex items-center justify-between bg-[#FAFBFC] font-mono text-[12.5px] font-bold text-[#1C1C1E]"
                data-testid="design-code-preview">
                <span>{isEdit ? design?.code : (preview?.code || "…")}</span>
                {!isEdit && preview && (
                  <span className="text-[9.5px] font-normal text-[#8E8E93]" title={`Pola: ${preview.pattern}`}>
                    {preview.designer_code} · {preview.parts?.CAT || "—"} · {preview.parts?.DCAT || "—"}
                  </span>
                )}
              </div>
            </Field>
          </div>

          <div className="grid gap-2.5 md:grid-cols-2">
            <Field label={<span className="flex items-center justify-between">Kategori Pattern * {manageBtn("pattern")}</span>}>
              <KNSelect data-testid="design-category-select" className="field" value={f.category_code}
                options={opts(patternCats)} placeholder="salur / batik / bunga / polkadot…" onValueChange={(v) => set("category_code", v)} searchable />
            </Field>
            <Field label={<span className="flex items-center justify-between">Kategori Design * {manageBtn("design")}</span>}>
              <KNSelect data-testid="design-dcategory-select" className="field" value={f.design_category_code}
                options={opts(designCats)} placeholder="allover / pinggiran" onValueChange={(v) => set("design_category_code", v)} searchable />
            </Field>
          </div>

          <div className="grid gap-2.5 md:grid-cols-2">
            <Field label="Repeat (cm)">
              <input className="field" data-testid="design-repeat-input" value={f.repeat_cm}
                onChange={(e) => set("repeat_cm", e.target.value)} placeholder="32" />
            </Field>
            <Field label="Jumlah screen">
              <input className="field" data-testid="design-screens-input" value={f.screen_count}
                onChange={(e) => set("screen_count", e.target.value)} placeholder="4" />
            </Field>
          </div>

          <Field label="Cerita / catatan desain">
            <textarea className="field" rows={2} data-testid="design-story-input" value={f.story}
              onChange={(e) => set("story", e.target.value)} placeholder="mis. inspirasi salur pelangi untuk koleksi lebaran" />
          </Field>
          <Field label="Tag (tersimpan — ketik sedikit lalu pilih)">
            <TagInput value={f.tags} onChange={(v) => set("tags", v)} testId="design-tags" />
          </Field>
          {!isEdit && (
            <p className="rounded-lg bg-[#F2F7FF] px-3 py-2 text-[11px] text-[#004099]" data-testid="design-form-hint">
              Setelah disimpan: unggah berkas desain (boleh 1–7 file sekaligus) → <b>Ajukan</b>. Peruntukan produk ditentukan
              penilai saat ACC; setelah ACC Anda wajib mengunggah varian warna + mockup.
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-[#EFF0F2] px-4 py-3">
          <button className="secondary-button" onClick={onClose} data-testid="design-form-cancel">Batal</button>
          <button className="primary-button" onClick={save} disabled={saving} data-testid="design-form-save">
            <Save size={13} /> {saving ? "Menyimpan…" : "Simpan"}
          </button>
        </div>
      </div>
      {catModal && (
        <CategoryManagerModal designType={catModal} onClose={() => { setCatModal(null); loadCats(); }} />
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">{label}</span>
      {children}
    </label>
  );
}
