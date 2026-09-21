/**
 * SampleSpecFields — bagian SPESIFIKASI PRODUK TARGET (WAJIB) yang menyatu di form Labdip/Handfeel/Proofing.
 * Isinya menyesuaikan jenis: labdip → warna target wajib; proofing → desain ACC wajib; handfeel → konstruksi kain.
 * Dipakai oleh SampleFormModal (buat) dan SampleSpecPanel (lengkapi spesifikasi sample lama).
 */
import { useMemo } from "react";
import BaseFabricPicker from "../../components/BaseFabricPicker";
import KNSelect from "../../components/KNSelect";
import { SpecVariantFields } from "../catalog/SpecVariantFields";
import { typeMeta } from "./sampleTypeMeta";

export const EMPTY_SPEC = {
  fabric_type: "woven", gramasi: "", lebar: "", sku_hint: "", target_price: "", notes: "",
  base_fabric_template_id: "", base_fabric_name: "",
  yarn_count: "", yarn_count_system: "", epi: "", ppi: "", composition: "", finishing: "", handfeel_target: "",
};

/** Bentuk payload SpecInput dari state form. */
export function buildSpecPayload({ sp, catalog, f, sampleTypes }) {
  const num = (v) => (v === "" || v == null ? null : v);
  const handfeelNotes = [sp.composition && `Komposisi: ${sp.composition}`, sp.finishing && `Finishing: ${sp.finishing}`,
    sp.handfeel_target && `Target pegangan: ${sp.handfeel_target}`, sp.notes].filter(Boolean).join(" · ");
  return {
    title: f.title, base_unit: f.unit, line_code: f.line_code,
    template_id: catalog.template_id || "", target_product_id: catalog.target_product_id || "",
    variant_attrs: catalog.variant_attrs || {}, variant_options: catalog.variant_options || {},
    base_fabric_template_id: sp.base_fabric_template_id || "",
    sku_hint: sp.sku_hint, sample_type_hint: sampleTypes[0] || "labdip",
    target: { fabric_type: sp.fabric_type, gramasi: num(sp.gramasi), lebar: num(sp.lebar),
      yarn_count: sp.yarn_count, yarn_count_system: sp.yarn_count_system, epi: num(sp.epi), ppi: num(sp.ppi) },
    color_target: catalog.color_target || (f.color_id ? { color_id: f.color_id } : {}),
    design_id: f.design_id, so_id: f.so_id, target_price: sp.target_price || 0, notes: handfeelNotes,
  };
}

/** Syarat minimal per jenis — dipakai untuk menonaktifkan tombol simpan + pesan. */
export function specProblems({ sp, catalog, f, sampleTypes, types }) {
  const out = [];
  if (!sp.fabric_type) out.push("jenis kain");
  if (catalog.invalid) out.push("kombinasi varian tidak valid");
  if (sampleTypes.includes("labdip") && !f.color_id) out.push("warna target (labdip)");
  if (sampleTypes.some((c) => typeMeta(c, types).requires_design) && !f.design_id) out.push("desain/pattern (proofing)");
  return out;
}

// Didefinisikan di luar komponen: bila dibuat ulang tiap render, React me-remount input di dalamnya → fokus hilang tiap 1 karakter.
function L({ label, children, span }) {
  return (
    <label className={`block ${span ? "sm:col-span-2" : ""}`}>
      <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">{label}</span>{children}
    </label>
  );
}

export default function SampleSpecFields({ sp, setSp, catalog, setCatalog, f, set, sampleTypes, types, colors, designs, locked = false, testPrefix = "sample-spec" }) {
  const setSpec = (k, v) => setSp((p) => ({ ...p, [k]: v }));
  const isLabdip = sampleTypes.includes("labdip");
  const isHandfeel = sampleTypes.includes("handfeel");
  const needDesign = useMemo(() => sampleTypes.some((c) => typeMeta(c, types).requires_design), [sampleTypes, types]);

  return (
    <div className={`grid gap-3 ${locked ? "pointer-events-none opacity-60" : ""}`} data-testid={`${testPrefix}-fields`}>
      <div className="rounded-lg border border-[#EFF0F2] bg-white p-2.5">
        <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Induk produk &amp; kombinasi varian</p>
        <SpecVariantFields onChange={setCatalog} onInherit={(patch) => setSp((p) => ({ ...p, ...patch }))} />
        {catalog.invalid && <p className="mt-1 text-[11px] text-[#A8221A]" data-testid={`${testPrefix}-combination-error`}>{catalog.invalid}</p>}
        <p className="mt-1 text-[10px] text-[#8E8E93]">Pilih induk → SKU lahir sebagai <b>varian</b> induk itu saat ACC. Tanpa induk → produk konsep mandiri.</p>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        <L label="Jenis kain *">
          <KNSelect data-testid={`${testPrefix}-fabric`} className="field" value={sp.fabric_type}
            options={[{ value: "woven", label: "Woven (tenun)" }, { value: "knit", label: "Knit (rajut)" }]} onValueChange={(v) => setSpec("fabric_type", v)} />
        </L>
        <L label="Gramasi (gsm)"><input className="field" type="number" min="0" step="any" data-testid={`${testPrefix}-gramasi`} value={sp.gramasi} onChange={(e) => setSpec("gramasi", e.target.value)} placeholder="150" /></L>
        <L label="Lebar (cm)"><input className="field" type="number" min="0" step="any" data-testid={`${testPrefix}-lebar`} value={sp.lebar} onChange={(e) => setSpec("lebar", e.target.value)} placeholder="150" /></L>
        <L label="Usulan kode SKU"><input className="field" data-testid={`${testPrefix}-sku`} value={sp.sku_hint} onChange={(e) => setSpec("sku_hint", e.target.value.toUpperCase())} placeholder="KTN-150-NAVY" /></L>
      </div>

      {(isLabdip || needDesign) && (
        <div className="rounded-lg border border-[#EFF0F2] bg-white p-2.5">
          <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">
            {isLabdip && needDesign ? "Warna target & desain" : isLabdip ? "Warna target (labdip)" : "Desain / pattern (proofing)"}
          </p>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {isLabdip && (
              <L label="Warna target dari Pustaka Warna *">
                <KNSelect data-testid="sample-color" className="field" value={f.color_id} searchable
                  options={[{ value: "", label: "— pilih warna —" }, ...colors.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` }))]}
                  onValueChange={(v) => set("color_id", v)} />
              </L>
            )}
            {!isLabdip && (
              <L label="Warna target (opsional)">
                <KNSelect data-testid="sample-color" className="field" value={f.color_id} searchable
                  options={[{ value: "", label: "— tanpa warna —" }, ...colors.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` }))]}
                  onValueChange={(v) => set("color_id", v)} />
              </L>
            )}
            <L label={`Desain / pattern${needDesign ? " * (ACC)" : " (opsional)"}`}>
              <KNSelect data-testid="sample-design" className="field" value={f.design_id} searchable
                options={[{ value: "", label: needDesign ? "— pilih desain ACC —" : "— tanpa desain —" },
                  ...designs.map((d) => ({ value: d.id, label: `${d.code || "tanpa kode"} · ${d.title} (v${d.version || 1})${d.on_hold ? " — ⛔ HOLD" : ""}` }))]}
                onValueChange={(v) => set("design_id", v)} />
            </L>
            <L label="Kain dasar (dari master data)" span>
              <BaseFabricPicker testId={`${testPrefix}-base-fabric`} value={sp.base_fabric_template_id} valueName={sp.base_fabric_name}
                onChange={(id, name) => setSp((p) => ({ ...p, base_fabric_template_id: id || "", base_fabric_name: name || "" }))} />
            </L>
          </div>
        </div>
      )}
      {!isLabdip && !needDesign && (
        <L label="Desain / pattern (opsional)">
          <KNSelect data-testid="sample-design" className="field" value={f.design_id} searchable
            options={[{ value: "", label: "— tanpa desain —" }, ...designs.map((d) => ({ value: d.id, label: `${d.code || "tanpa kode"} · ${d.title} (v${d.version || 1})` }))]}
            onValueChange={(v) => set("design_id", v)} />
        </L>
      )}

      {isHandfeel && (
        <div className="rounded-lg border border-[#EFF0F2] bg-white p-2.5" data-testid={`${testPrefix}-handfeel`}>
          <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Konstruksi kain (handfeel)</p>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            <L label="Nomor benang"><input className="field" data-testid={`${testPrefix}-yarn`} value={sp.yarn_count} onChange={(e) => setSpec("yarn_count", e.target.value)} placeholder="30s / 40s" /></L>
            <L label="Sistem benang">
              <KNSelect data-testid={`${testPrefix}-yarn-system`} className="field" value={sp.yarn_count_system}
                options={[{ value: "", label: "—" }, { value: "Ne", label: "Ne (English cotton)" }, { value: "Nm", label: "Nm (metric)" }, { value: "denier", label: "Denier" }, { value: "tex", label: "Tex" }]}
                onValueChange={(v) => setSpec("yarn_count_system", v)} />
            </L>
            <L label="EPI (helai/inch lusi)"><input className="field" type="number" min="0" data-testid={`${testPrefix}-epi`} value={sp.epi} onChange={(e) => setSpec("epi", e.target.value)} placeholder="120" /></L>
            <L label="PPI (helai/inch pakan)"><input className="field" type="number" min="0" data-testid={`${testPrefix}-ppi`} value={sp.ppi} onChange={(e) => setSpec("ppi", e.target.value)} placeholder="80" /></L>
            <L label="Komposisi"><input className="field" data-testid={`${testPrefix}-composition`} value={sp.composition} onChange={(e) => setSpec("composition", e.target.value)} placeholder="100% katun" /></L>
            <L label="Finishing"><input className="field" data-testid={`${testPrefix}-finishing`} value={sp.finishing} onChange={(e) => setSpec("finishing", e.target.value)} placeholder="soft, anti-pilling" /></L>
            <L label="Target pegangan" span><input className="field" data-testid={`${testPrefix}-handfeel-target`} value={sp.handfeel_target} onChange={(e) => setSpec("handfeel_target", e.target.value)} placeholder="lembut, jatuh, tidak kaku" /></L>
          </div>
        </div>
      )}

      <div className="grid gap-2.5 sm:grid-cols-2">
        <L label="Target harga (Rp / satuan)"><input className="field" type="number" min="0" data-testid={`${testPrefix}-price`} value={sp.target_price} onChange={(e) => setSpec("target_price", e.target.value)} placeholder="45000" /></L>
        <L label="Catatan spesifikasi"><input className="field" data-testid={`${testPrefix}-notes`} value={sp.notes} onChange={(e) => setSpec("notes", e.target.value)} placeholder="mis. toleransi gramasi ±5%" /></L>
      </div>
    </div>
  );
}
