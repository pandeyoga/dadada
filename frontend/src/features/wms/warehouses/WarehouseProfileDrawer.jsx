/**
 * WarehouseProfileDrawer (FASE R0) — konfigurasi profil GEDUNG:
 * lokasi (site), peran (roles), rules penyimpanan (kategori/grade), gate fisik.
 * Semua configurable oleh user (keputusan pemilik: fungsi gudang bisa berubah).
 */
import { useState } from "react";
import { X, Save, MapPin, Shield, DoorOpen, Layers } from "lucide-react";
import KNSelect from "../../../components/KNSelect";
import { errText, patchWarehouse, WH_ROLES } from "./warehouseApi";

const GRADES = ["A", "B", "C", "BS"];
const RULE_MODES = [
  { value: "none", label: "Tanpa aturan (semua barang boleh)" },
  { value: "category", label: "Per kategori kain (master ERP)" },
  { value: "grade", label: "Per grade (mis. gedung retur)" },
];

export default function WarehouseProfileDrawer({ warehouse, sites = [], categories = [], onClose, onSaved }) {
  const [siteId, setSiteId] = useState(warehouse.site_id || "");
  const [roles, setRoles] = useState(warehouse.roles || []);
  const rules0 = warehouse.storage_rules || {};
  const [ruleMode, setRuleMode] = useState(rules0.mode || "none");
  const [cats, setCats] = useState(rules0.categories || []);
  const [grades, setGrades] = useState(rules0.grades || []);
  const [physicalGate, setPhysicalGate] = useState(!!(warehouse.gate_config || {}).physical_gate);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggle = (list, setList, val) =>
    setList(list.includes(val) ? list.filter((x) => x !== val) : [...list, val]);

  const save = async () => {
    setSaving(true); setError("");
    try {
      await patchWarehouse(warehouse.id, {
        site_id: siteId,
        roles,
        storage_rules: { mode: ruleMode, categories: cats, grades },
        gate_config: { physical_gate: physicalGate },
      });
      onSaved(`Profil ${warehouse.name} tersimpan.`);
    } catch (e) { setError(errText(e, "Gagal menyimpan profil gudang.")); }
    finally { setSaving(false); }
  };

  const siteOpts = [{ value: "", label: "— Tanpa lokasi —" },
    ...sites.map((s) => ({ value: s.id, label: `${s.name}${s.city ? ` (${s.city})` : ""}` }))];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" data-testid="wh-profile-drawer">
      <div className="h-full w-full max-w-md overflow-y-auto bg-white p-4 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Profil Gedung</p>
            <h3 className="text-[15px] font-bold">{warehouse.name}</h3>
          </div>
          <button data-testid="wh-profile-close" className="icon-button" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <p data-testid="wh-profile-error" className="mb-2 rounded bg-[#FBE9E7] px-2 py-1.5 text-[11.5px] text-[#C0341D]">{error}</p>}

        <div className="space-y-4">
          <section>
            <p className="mb-1 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]"><MapPin size={12} /> Lokasi (Site)</p>
            <KNSelect data-testid="wh-profile-site" value={siteId} onValueChange={setSiteId}
              options={siteOpts} className="field text-[12px]" placeholder="Pilih lokasi" />
          </section>

          <section>
            <p className="mb-1 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]"><Layers size={12} /> Peran Gedung (boleh lebih dari satu)</p>
            <div className="grid grid-cols-2 gap-1.5">
              {WH_ROLES.map((r) => (
                <button key={r.key} type="button" data-testid={`wh-profile-role-${r.key}`}
                  onClick={() => toggle(roles, setRoles, r.key)}
                  className={`rounded-md border px-2 py-1.5 text-left text-[12px] font-semibold ${
                    roles.includes(r.key) ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`}>
                  {r.label}
                </button>
              ))}
            </div>
          </section>

          <section>
            <p className="mb-1 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]"><Shield size={12} /> Aturan Penyimpanan</p>
            <KNSelect data-testid="wh-profile-rulemode" value={ruleMode} onValueChange={setRuleMode}
              options={RULE_MODES} className="field text-[12px]" />
            {ruleMode === "category" && (
              <div className="mt-2 grid grid-cols-2 gap-1" data-testid="wh-profile-categories">
                {categories.map((c) => (
                  <label key={c.id} className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[12px] hover:bg-[#F5F5F7]">
                    <input type="checkbox" checked={cats.includes(c.name)}
                      data-testid={`wh-profile-cat-${c.id}`}
                      onChange={() => toggle(cats, setCats, c.name)} />
                    {c.name}
                  </label>
                ))}
                <p className="col-span-2 text-[10.5px] text-[#8E8E93]">Kosong = semua kategori boleh. Centang untuk membatasi.</p>
              </div>
            )}
            {ruleMode === "grade" && (
              <div className="mt-2 flex gap-1.5" data-testid="wh-profile-grades">
                {GRADES.map((g) => (
                  <button key={g} type="button" data-testid={`wh-profile-grade-${g}`}
                    onClick={() => toggle(grades, setGrades, g)}
                    className={`rounded-md border px-3 py-1.5 text-[12px] font-bold ${
                      grades.includes(g) ? "border-[#6B219A] bg-[#F3E9FA] text-[#6B219A]" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`}>
                    {g}
                  </button>
                ))}
              </div>
            )}
          </section>

          <section>
            <p className="mb-1 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]"><DoorOpen size={12} /> Gate RFID Fisik</p>
            <button type="button" data-testid="wh-profile-gate-toggle"
              onClick={() => setPhysicalGate((v) => !v)}
              className={`w-full rounded-md border px-3 py-2 text-left text-[12px] ${
                physicalGate ? "border-[#1B7F4B] bg-[#E6F6EC]" : "border-[#E5E5EA] bg-white"}`}>
              <span className="block font-bold">{physicalGate ? "Ada gate fisik (in & out)" : "Tanpa gate fisik — handheld saja"}</span>
              <span className="block text-[10.5px] text-[#6B6B73]">
                {physicalGate ? "Validasi keluar-masuk lewat RFID gate + monitor." : "Validasi keluar-masuk lewat scan handheld (mis. Gudang Jakarta)."}
              </span>
            </button>
          </section>
        </div>

        <button data-testid="wh-profile-save" className="primary-button mt-4 w-full justify-center"
          onClick={save} disabled={saving}>
          <Save size={14} /> {saving ? "Menyimpan…" : "Simpan Profil"}
        </button>
      </div>
    </div>
  );
}
