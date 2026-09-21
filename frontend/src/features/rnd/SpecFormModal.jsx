/**
 * SpecFormModal (FASE F · PS-12/PS-13/PS-14) — buat spesifikasi produk R&D.
 *
 * Warna WAJIB dari Pustaka Warna (bukan teks bebas). "Butuh desain" TIDAK lagi
 * ditebak layar dengan `if jenis == "proofing"`: sejak FASE S ia dibaca dari baris
 * master jenis sampling (`requires_design`), sama seperti form permintaan sample —
 * jadi jenis printing yang DITAMBAH pemilik ikut menuntut desain tanpa satu baris
 * kode pun berubah.
 */
import { useEffect, useMemo, useState } from "react";
import { FlaskConical, Save, X } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import BaseFabricPicker from "../../components/BaseFabricPicker";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { createSpec, designFileUrl, listColors, listDesigns } from "./rndApi";
import { errMsg } from "./rndMeta";
import { typeLabel, typeMeta, typeOptions } from "./sampleTypeMeta";
import { SpecVariantFields } from "../catalog/SpecVariantFields";
import useCatalogMasters from "../../hooks/useCatalogMasters";

const STAGE_OPTS = [
  { value: "finished", label: "Finished (kain jadi)" },
  { value: "grey", label: "Grey (kain mentah)" },
  { value: "pfd", label: "PFD (siap celup)" },
  { value: "pfp", label: "PFP (siap cetak)" },
  { value: "yarn", label: "Benang (yarn)" },
];
// MD-01 — pilihan khas benang (selaras `domain_registry` YARN_*).
const YARN_SYSTEM_OPTS = ["Ne", "Nm", "Denier", "Tex"].map((v) => ({ value: v, label: v }));
const YARN_MATERIAL_OPTS = [
  { value: "katun", label: "Katun" }, { value: "poliester", label: "Poliester" }, { value: "rayon", label: "Rayon / viskosa" },
  { value: "campuran", label: "Campuran (blend)" }, { value: "sutra", label: "Sutra" }, { value: "linen", label: "Linen" },
  { value: "nilon", label: "Nilon" }, { value: "lainnya", label: "Lainnya" },
];
const YARN_TWIST_OPTS = [{ value: "S", label: "S (kiri)" }, { value: "Z", label: "Z (kanan)" }, { value: "SZ", label: "S/Z (gintir ganda)" }];
const YARN_DYE_OPTS = [
  { value: "raw", label: "Mentah / greige" }, { value: "bleached", label: "Putih (bleached)" },
  { value: "dyed", label: "Celup (dyed)" }, { value: "melange", label: "Melange" },
];
const FABRIC_OPTS = [
  { value: "woven", label: "Woven (tenun)" },
  { value: "knit", label: "Knit (rajut)" },
];
const GRADE_OPTS = [
  { value: "", label: "— tidak ditentukan —" },
  { value: "A", label: "A — mutu terbaik" },
  { value: "A1", label: "A1" }, { value: "A2", label: "A2" }, { value: "B", label: "B" },
];

export default function SpecFormModal({ selectedEntity, types = [], onClose, onSaved, initial }) {
  const [catalog, setCatalog] = useState({ invalid: initial?.templateId ? "Memuat kombinasi induk…" : "" });
  const [colors, setColors] = useState([]);
  const [designs, setDesigns] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({
    title: "", category: "", base_unit: "meter", sku_hint: "",
    sample_type_hint: "labdip", stage: "finished", fabric_type: "woven",
    gramasi: "", lebar: "", grade: "", epi: "", ppi: "",
    yarn_count: "", yarn_count_system: "", yarn_material: "", yarn_ply: "", yarn_twist: "", yarn_dye_status: "",
    color_id: "", design_id: "", target_price: "", notes: "",
    base_fabric_template_id: "", base_fabric_name: "",
  });
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const masters = useCatalogMasters({ current: { category: f.category, base_unit: f.base_unit } });
  const isYarn = f.stage === "yarn";   // MD-01 — isian khas benang, bukan gramasi/lebar
  const selColor = useMemo(() => colors.find((c) => c.id === f.color_id), [colors, f.color_id]);
  const selDesign = useMemo(() => designs.find((d) => d.id === f.design_id), [designs, f.design_id]);

  useEffect(() => {
    listColors().then((c) => setColors(Array.isArray(c) ? c : c?.items || [])).catch(() => {});
    listDesigns().then((d) => setDesigns(Array.isArray(d) ? d : d?.items || [])).catch(() => {});
  }, []);

  // FASE S — pilihan "rencana sample" datang dari MASTER `sample_types` (diteruskan
  // layar Spesifikasi lewat `/api/rnd/meta`). Daftar cadangan hanya dipakai bila
  // master belum termuat, supaya form tak pernah kosong.
  const typeOpts = useMemo(() => typeOptions(types), [types]);

  // Kalau jenis bawaan (`labdip`) TIDAK ada di master badan usaha ini — mis. pemilik
  // menonaktifkannya — pilihannya digeser ke jenis pertama yang sah. Menyimpan
  // jenis yang sudah mati akan membuat form permintaan sample menolaknya nanti.
  useEffect(() => {
    if (typeOpts.length === 0) return;
    if (!typeOpts.some((o) => o.value === f.sample_type_hint)) {
      set("sample_type_hint", typeOpts[0].value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeOpts]);

  const hintRequiresDesign = useMemo(
    () => Boolean(typeMeta(f.sample_type_hint, types).requires_design),
    [f.sample_type_hint, types]);

  const submit = async () => {
    setErr("");
    if (!f.title.trim()) { setErr("Judul spesifikasi wajib diisi."); return; }
    if (catalog.invalid) { setErr(catalog.invalid); return; }
    setSaving(true);
    try {
      const created = await createSpec({
        title: f.title, category: f.category, base_unit: f.base_unit,
        template_id: catalog.template_id || "", target_product_id: catalog.target_product_id || "",
        variant_attrs: catalog.variant_attrs || {}, variant_options: catalog.variant_options || {},
        line_code: f.line_code || "",
        base_fabric_template_id: f.base_fabric_template_id || "",
        sku_hint: f.sku_hint, sample_type_hint: f.sample_type_hint,
        target: {
          stage: f.stage, fabric_type: f.fabric_type,
          gramasi: isYarn || f.gramasi === "" ? null : f.gramasi,
          lebar: isYarn || f.lebar === "" ? null : f.lebar,
          grade: f.grade, epi: isYarn || f.epi === "" ? null : f.epi, ppi: isYarn || f.ppi === "" ? null : f.ppi,
          ...(isYarn ? { yarn_count: f.yarn_count, yarn_count_system: f.yarn_count_system,
            yarn_material: f.yarn_material, yarn_ply: f.yarn_ply, yarn_twist: f.yarn_twist,
            yarn_dye_status: f.yarn_dye_status } : {}),
        },
        color_target: catalog.color_target || (f.color_id ? { color_id: f.color_id } : {}),
        design_id: f.design_id, target_price: f.target_price || 0, notes: f.notes,
        entity_id: selectedEntity && selectedEntity !== "all" ? selectedEntity : "",
      });
      onSaved?.(created);
    } catch (e) {
      setErr(errMsg(e, "Gagal menyimpan spesifikasi."));
      setSaving(false);
    }
  };

  return (
    <div data-testid="spec-form-modal"
      className="fixed inset-0 z-[170] flex items-center justify-center bg-black/50 p-4"
      {...overlayDismiss(onClose)}>
      <div className="flex max-h-[94vh] w-full max-w-[820px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-[#EFF0F2] px-4 py-3">
          <h2 className="flex items-center gap-2 text-[15px] font-bold">
            <FlaskConical size={16} className="text-[#0058CC]" /> Spesifikasi Produk Baru (R&D)
          </h2>
          <button className="icon-button" onClick={onClose} data-testid="spec-form-close">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {err && (
            <div className="rounded-lg bg-[#FDEDE7] px-3 py-2 text-[11.5px] text-[#C0392B]"
              data-testid="spec-form-error">{err}</div>
          )}
          <p className="rounded-lg bg-[#F2F7FF] px-3 py-2 text-[11.5px] text-[#004099]">
            Produk baru <b>tidak langsung bisa dijual</b>. Setelah spesifikasi disetujui,
            produk lahir dengan tahap <b>“Disetujui”</b>; barang baru boleh dipesan/dijual
            setelah <b>dirilis ke produksi</b>.
          </p>

          <Field label="Judul spesifikasi *">
            <input className="field" data-testid="spec-title-input" value={f.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="mis. Katun Premium 135gsm warna khusus pelanggan" />
          </Field>
          <SpecVariantFields initial={initial} onChange={setCatalog} onInherit={patch => setF(prev => ({ ...prev, ...patch }))} />
          {catalog.invalid && <p data-testid="spec-combination-error" className="text-xs text-red-700">{catalog.invalid}</p>}

          <div className="grid gap-2.5 md:grid-cols-3">
            <Field label="Jenis sample yang direncanakan">
              <KNSelect data-testid="spec-sample-type" className="field" value={f.sample_type_hint}
                options={typeOpts} onValueChange={(v) => set("sample_type_hint", v)} />
              {hintRequiresDesign && (
                <span className="mt-0.5 block text-[10px] text-[#B26A00]"
                  data-testid="spec-sample-type-needs-design">
                  Jenis <b>{typeLabel(f.sample_type_hint, types)}</b> menuntut kode desain
                  — pilih desain/pattern di bawah.
                </span>
              )}
            </Field>
            <Field label="Tahap bahan">
              <KNSelect data-testid="spec-stage" className="field" value={f.stage}
                options={STAGE_OPTS} onValueChange={(v) => set("stage", v)} />
            </Field>
            <Field label={isYarn ? "Untuk kain (woven/knit) *" : "Jenis kain *"}>
              <KNSelect data-testid="spec-fabric" className="field" value={f.fabric_type}
                options={FABRIC_OPTS} onValueChange={(v) => set("fabric_type", v)} />
            </Field>
          </div>

          <div className="block">
            <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Kain dasar dari master data (mis. kain polos woven yang menjadi bahan labdip/printing)</span>
            <BaseFabricPicker testId="spec-base-fabric" value={f.base_fabric_template_id} valueName={f.base_fabric_name}
              onChange={(tpl) => setF((prev) => ({
                ...prev, base_fabric_template_id: tpl?.id || "", base_fabric_name: tpl?.name || "",
                ...(tpl ? {
                  fabric_type: tpl.fabric_type || prev.fabric_type,
                  gramasi: prev.gramasi || (tpl.gramasi ? String(tpl.gramasi) : ""),
                  lebar: prev.lebar || (tpl.lebar ? String(Math.round(Number(tpl.lebar) * 100)) : ""),
                } : {}),
              }))} />
            {f.base_fabric_template_id && (
              <span className="mt-0.5 block text-[10px] text-[#0058CC]" data-testid="spec-base-fabric-hint">
                Jenis kain, gramasi & lebar yang masih kosong diisi dari kain dasar — ubah bila berbeda.
              </span>
            )}
          </div>

          {isYarn ? (
            <div className="rounded-md border border-[#DCE7F7] bg-[#F7FAFF] p-2.5" data-testid="spec-yarn-fields">
              <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]">Isian khas benang — bukan gramasi/lebar</p>
              <div className="grid gap-2.5 md:grid-cols-3">
                <Field label="Nomor benang *">
                  <input className="field" data-testid="spec-yarn-count-input" value={f.yarn_count}
                    onChange={(e) => set("yarn_count", e.target.value)} placeholder="30s / 150D" />
                </Field>
                <Field label="Sistem nomor">
                  <KNSelect data-testid="spec-yarn-count-system" className="field" value={f.yarn_count_system}
                    options={[{ value: "", label: "—" }, ...YARN_SYSTEM_OPTS]} onValueChange={(v) => set("yarn_count_system", v)} />
                </Field>
                <Field label="Bahan benang">
                  <KNSelect data-testid="spec-yarn-material" className="field" value={f.yarn_material}
                    options={[{ value: "", label: "—" }, ...YARN_MATERIAL_OPTS]} onValueChange={(v) => set("yarn_material", v)} />
                </Field>
                <Field label="Ply">
                  <input className="field" data-testid="spec-yarn-ply-input" value={f.yarn_ply}
                    onChange={(e) => set("yarn_ply", e.target.value)} placeholder="1 / 2" />
                </Field>
                <Field label="Arah puntiran">
                  <KNSelect data-testid="spec-yarn-twist" className="field" value={f.yarn_twist}
                    options={[{ value: "", label: "—" }, ...YARN_TWIST_OPTS]} onValueChange={(v) => set("yarn_twist", v)} />
                </Field>
                <Field label="Status celup">
                  <KNSelect data-testid="spec-yarn-dye" className="field" value={f.yarn_dye_status}
                    options={[{ value: "", label: "—" }, ...YARN_DYE_OPTS]} onValueChange={(v) => set("yarn_dye_status", v)} />
                </Field>
              </div>
            </div>
          ) : (
          <div className="grid gap-2.5 md:grid-cols-4">
            <Field label="Gramasi (gsm)">
              <input className="field" type="number" min="0" step="any" inputMode="decimal" data-testid="spec-gramasi-input" value={f.gramasi}
                onChange={(e) => set("gramasi", e.target.value)} placeholder="135" />
            </Field>
            <Field label="Lebar (cm)">
              <input className="field" type="number" min="0" step="any" inputMode="decimal" data-testid="spec-lebar-input" value={f.lebar}
                onChange={(e) => set("lebar", e.target.value)} placeholder="115" />
            </Field>
            <Field label="EPI (benang lusi/inci)">
              <input className="field" type="number" min="0" step="any" inputMode="decimal" data-testid="spec-epi-input" value={f.epi}
                onChange={(e) => set("epi", e.target.value)} placeholder="60" />
            </Field>
            <Field label="PPI (benang pakan/inci)">
              <input className="field" type="number" min="0" step="any" inputMode="decimal" data-testid="spec-ppi-input" value={f.ppi}
                onChange={(e) => set("ppi", e.target.value)} placeholder="58" />
            </Field>
          </div>
          )}

          <div className="grid gap-2.5 md:grid-cols-2">
            <Field label="Warna target (wajib dari Pustaka Warna)">
              {/* MD-03 — kotak warna ikut tampil di daftar & ringkasan, bukan hanya kode. */}
              <KNSelect data-testid="spec-color" className="field" value={f.color_id}
                disabled={!!catalog.color_target}
                options={[{ value: "", label: "— belum ditentukan —" },
                  ...colors.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}${c.factory_name ? ` (${c.factory_name})` : ""}`,
                    render: (
                      <span className="inline-flex min-w-0 items-center gap-2" data-testid={`spec-color-swatch-${c.id}`}>
                        <span className="h-4 w-4 shrink-0 rounded border border-[#E5E5EA]" style={{ backgroundColor: c.hex }} />
                        <span className="truncate">{c.code} · {c.name}{c.factory_name ? <span className="text-[#9A9BA3]"> · pabrik: {c.factory_name}</span> : null}</span>
                      </span>) }))]}
                onValueChange={(v) => set("color_id", v)} />
              {selColor && (
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-[#3C3C43]" data-testid="spec-color-preview">
                  <span className="h-8 w-8 rounded-md border border-[#E5E5EA]" style={{ backgroundColor: selColor.hex }} />
                  <span>{selColor.code} · {selColor.name} <span className="font-mono text-[#9A9BA3]">{selColor.hex}</span></span>
                </div>
              )}
              {catalog.color_target && <p data-testid="spec-inherited-color" className="mt-1.5 text-xs text-[#0058CC]">Warna varian: {catalog.variant_attrs?.color || catalog.color_target.code} · {catalog.color_target.code}</p>}
            </Field>
            <Field label={`Desain / pattern${hintRequiresDesign ? " (wajib untuk jenis ini)" : ""}`}>
              <KNSelect data-testid="spec-design" className="field" value={f.design_id}
                options={[{ value: "", label: "— tanpa desain —" },
                  ...designs.map((d) => {
                    const cover = (d.files || [])[0];
                    return { value: d.id,
                      label: `${d.code || "tanpa kode"} · ${d.title} (v${d.version || 1})`,
                      render: (
                        <span className="inline-flex min-w-0 items-center gap-2" data-testid={`spec-design-thumb-${d.id}`}>
                          {cover
                            ? <img src={designFileUrl(d.id, cover.id)} alt="" className="h-6 w-6 shrink-0 rounded object-cover border border-[#E5E5EA]" />
                            : <span className="h-6 w-6 shrink-0 rounded bg-[#F5F5F7] border border-[#E5E5EA]" />}
                          <span className="truncate">{d.code || "tanpa kode"} · {d.title} (v{d.version || 1})</span>
                        </span>) };
                  })]}
                onValueChange={(v) => set("design_id", v)} />
              {selDesign && (
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-[#3C3C43]" data-testid="spec-design-preview">
                  {(selDesign.files || [])[0]
                    ? <img src={designFileUrl(selDesign.id, selDesign.files[0].id)} alt={selDesign.title} className="h-14 w-14 rounded-md object-cover border border-[#E5E5EA]" />
                    : <span className="flex h-14 w-14 items-center justify-center rounded-md bg-[#F5F5F7] text-[9px] text-[#9A9BA3]">tanpa artwork</span>}
                  <span>{selDesign.code || "tanpa kode"} · {selDesign.title} <span className="text-[#9A9BA3]">v{selDesign.version || 1}</span></span>
                </div>
              )}
            </Field>
          </div>

          <div className="grid gap-2.5 md:grid-cols-4">
            <Field label="Kode SKU usulan (huruf/angka)">
              <input className="field" data-testid="spec-sku-input" value={f.sku_hint}
                onChange={(e) => set("sku_hint", e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, ""))} placeholder="KTN-PRM-135" />
            </Field>
            <Field label="Kategori (Master Kategori)">
              <KNSelect data-testid="spec-category-input" className="field" searchable value={f.category}
                options={[{ value: "", label: "— pilih kategori —" }, ...masters.categoryOptions]} onValueChange={(v) => set("category", v)} />
            </Field>
            <Field label="Satuan dasar (Master Satuan)">
              <KNSelect data-testid="spec-unit-input" className="field" value={f.base_unit}
                options={masters.unitOptions} onValueChange={(v) => set("base_unit", v)} />
            </Field>
            <Field label="Grade diharapkan">
              <KNSelect data-testid="spec-grade" className="field" value={f.grade}
                options={GRADE_OPTS} onValueChange={(v) => set("grade", v)} />
            </Field>
          </div>

          {/* MD-04 — kolom target harga jual DIHAPUS dari formulir (harga jual ditetapkan di
              daftar harga per PT / harga langganan). Data lama tetap tersimpan, hanya tak diisi di sini. */}
          <div className="grid gap-2.5">
            <Field label="Catatan">
              <input className="field" data-testid="spec-notes-input" value={f.notes}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="Permintaan pelanggan / referensi" />
            </Field>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-[#EFF0F2] px-4 py-3">
          <button className="secondary-button" data-testid="spec-form-cancel" onClick={onClose}>Batal</button>
          <button className="primary-button" onClick={submit} disabled={saving || !!catalog.invalid}
            data-testid="spec-form-save">
            <Save size={13} /> {saving ? "Menyimpan…" : "Simpan Draft"}
          </button>
        </div>
      </div>
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
