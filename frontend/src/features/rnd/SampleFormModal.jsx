/**
 * SampleFormModal — buat permintaan Labdip / Handfeel / Proofing.
 * 1 sample = 1 SPESIFIKASI (wajib; menggantikan tab Spesifikasi terpisah) — selalu dibuat baru bersama sample:
 *   1) Spesifikasi produk target (WAJIB, ikut jenis) · 2) Brief untuk supplier (+ pesanan) · 3) Kapan dibutuhkan.
 * Uji bertahap di kain yang sama → tambah JENIS ke permintaan yang sama (tombol "Tambah jenis" di rincian), bukan permintaan baru.
 */
import { useEffect, useState } from "react";
import { Beaker, CalendarClock, FlaskConical, Package } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import KNDatePicker from "../../components/KNDatePicker";
import useCatalogMasters from "../../hooks/useCatalogMasters";
import axios, { API } from "../../services/apiClient";
import { createSample, listColors, listDesigns, sampleTypes } from "./rndApi";
import { errMsg, typeTone } from "./rndMeta";
import SampleSpecFields, { EMPTY_SPEC, buildSpecPayload, specProblems } from "./SampleSpecFields";
import { typeLabel, typeMeta } from "./sampleTypeMeta";

const listOrders = (params) => axios.get(`${API}/sales-orders`, { params }).then((r) => r.data);

function Section({ step, icon: Icon, title, hint, children, testId, required }) {
  return (
    <section className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-3" data-testid={testId}>
      <div className="mb-2.5 flex items-start gap-2">
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#0058CC] text-[10px] font-bold text-white">{step}</span>
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-[12px] font-bold text-[#1C1C1E]">
            <Icon size={13} className="text-[#6B6B73]" /> {title}
            {required && <span className="rounded bg-[#FDECEC] px-1.5 py-px text-[9px] font-bold uppercase text-[#C0392B]">wajib</span>}
          </p>
          {hint && <p className="text-[10.5px] text-[#6B6B73]">{hint}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function SampleFormModal({ selectedEntity, prefill, lockType = "", onClose, onSaved }) {
  const [colors, setColors] = useState([]);
  const [designs, setDesigns] = useState([]);
  const [orders, setOrders] = useState([]);
  const [types, setTypes] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({
    sample_types: prefill?.sample_types || (prefill?.sample_type ? [prefill.sample_type] : (lockType ? [lockType] : [])),
    title: "", brief: "",
    color_id: prefill?.color_id || "", design_id: prefill?.design_id || "",
    so_id: prefill?.so_id || "", line_code: prefill?.line_code || "",
    target_date: "", qty_requested: "3", unit: "meter",
  });
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const masters = useCatalogMasters({ current: { base_unit: f.unit } });
  const [catalog, setCatalog] = useState({});
  const [sp, setSp] = useState(EMPTY_SPEC);

  useEffect(() => {
    const params = selectedEntity && selectedEntity !== "all" ? { entity_id: selectedEntity } : {};
    listColors().then((c) => setColors(Array.isArray(c) ? c : c?.items || [])).catch(() => {});
    listDesigns().then((d) => setDesigns(Array.isArray(d) ? d : d?.items || [])).catch(() => {});
    listOrders({ ...params, limit: 200 }).then((r) => setOrders(Array.isArray(r) ? r : r?.items || [])).catch(() => {});
  }, [selectedEntity]);

  useEffect(() => {
    const p = {};
    if (selectedEntity && selectedEntity !== "all") p.entity_id = selectedEntity;
    if (f.line_code) p.line = f.line_code;
    sampleTypes(p).then((rows) => setTypes(Array.isArray(rows) ? rows : [])).catch(() => {});
  }, [selectedEntity, f.line_code]);

  useEffect(() => {
    if (f.sample_types.length || types.length === 0) return;
    if (prefill?.need_design !== undefined) {
      const hit = types.find((t) => Boolean(t.requires_design) === Boolean(prefill.need_design));
      if (hit) set("sample_types", [hit.value]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [types]);

  const toggleType = (code) => setF((p) => ({
    ...p, sample_types: p.sample_types.includes(code) ? p.sample_types.filter((x) => x !== code) : [...p.sample_types, code],
  }));

  const needDesign = f.sample_types.some((c) => typeMeta(c, types).requires_design);
  const problems = specProblems({ sp, catalog, f, sampleTypes: f.sample_types, types });
  const titleOk = f.title.trim().length > 0;
  const typesOk = f.sample_types.length > 0;
  const canSave = titleOk && typesOk && problems.length === 0;

  const submit = async () => {
    setErr(""); setSaving(true);
    try {
      const created = await createSample({
        sample_types: f.sample_types, title: f.title, brief: f.brief,
        color_target: f.color_id ? { color_id: f.color_id } : {},
        design_id: f.design_id, so_id: f.so_id, line_code: f.line_code,
        target_date: f.target_date, qty_requested: f.qty_requested || 0, unit: f.unit,
        spec: buildSpecPayload({ sp, catalog, f, sampleTypes: f.sample_types }),
      });
      onSaved?.(created);
    } catch (e) {
      setErr(errMsg(e, "Gagal membuat permintaan sample."));
      setSaving(false);
    }
  };

  const lockLabel = lockType ? typeLabel(lockType, types).split(" (")[0] : "";
  const autoTitle = () => {
    if (f.title.trim()) return;
    const parts = [f.sample_types.map((c) => typeLabel(c, types).split(" (")[0]).join("+"), catalog.template_name || sp.base_fabric_name,
      sp.gramasi && `${sp.gramasi} gsm`, colors.find((c) => c.id === f.color_id)?.name].filter(Boolean);
    if (parts.length > 1) set("title", parts.join(" — "));
  };

  return (
    <FormModal open onClose={onClose} title={lockType ? `Sampel ${lockLabel} Baru` : "Permintaan Sample Baru"}
      subtitle="Setiap permintaan lahir bersama SPESIFIKASI produk target-nya — saat ACC, spesifikasi ikut ACC dan SKU lahir di master."
      icon={Beaker} size="lg" testId="sample-form-modal"
      onSubmit={submit} submitLabel="Simpan Permintaan + Spesifikasi" busy={saving} error={err}
      submitDisabled={!canSave} submitTestId="sample-form-save">
      <div className="grid gap-3">
        {prefill?.source_label && (
          <div className="rounded-lg bg-[#F2F7FF] px-3 py-2 text-[11.5px] text-[#004099]" data-testid="sample-form-prefill">
            Diisi otomatis dari <b>{prefill.source_label}</b>.
          </div>
        )}

        <Section step={1} icon={Package} title="Spesifikasi produk target" required testId="sample-section-spec"
          hint="Isinya menyesuaikan jenis: labdip → warna target · proofing → desain ACC · handfeel → konstruksi kain. Pilih lebih dari satu jenis bila kain yang sama diuji bertahap — spesifikasinya tetap satu.">
          <div className="mb-3">
            <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Jenis sampling * (boleh lebih dari satu)</span>
            <div className="flex flex-wrap gap-1.5" data-testid="sample-type-picker">
              {types.length === 0 && <span className="text-[11.5px] text-[#8C4A00]" data-testid="sample-type-empty">Belum ada jenis sampling aktif. Tambahkan di Pengaturan → Master → Jenis Sampling.</span>}
              {types.map((t) => {
                const on = f.sample_types.includes(t.value);
                const tone = typeTone(t.value);
                const locked = lockType && t.value === lockType;
                return (
                  <button key={t.value} type="button" data-testid={`sample-type-${t.value}`} onClick={() => { if (!locked) toggleType(t.value); }}
                    title={locked ? "Jenis utama tab ini — tidak bisa dilepas" : (t.notes || "")}
                    className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-[background-color,border-color,color] ${locked ? "cursor-default" : ""}`}
                    style={on ? { background: tone.fg, borderColor: tone.fg, color: "#fff" } : { background: "#fff", borderColor: "#E5E5EA", color: "#3C3C43" }}>
                    {t.label}{t.requires_design ? " · wajib desain" : ""}{locked ? " · utama" : ""}
                  </button>
                );
              })}
            </div>
            {typesOk && (
              <p className="mt-1 text-[10.5px] text-[#6B6B73]" data-testid="sample-type-summary">
                Hasil ukur: {f.sample_types.map((c) => `${typeLabel(c, types).split(" (")[0]} → ${(typeMeta(c, types).measurement_fields || []).join(", ") || "foto + catatan"}`).join(" · ")}
              </p>
            )}
          </div>

          <SampleSpecFields sp={sp} setSp={setSp} catalog={catalog} setCatalog={setCatalog} f={f} set={set}
            sampleTypes={f.sample_types} types={types} colors={colors} designs={designs} />
          {problems.length > 0 && typesOk && (
            <p className="mt-2 text-[11px] text-[#A8221A]" data-testid="sample-spec-problems">Belum lengkap: <b>{problems.join(", ")}</b>.</p>
          )}
        </Section>

        <Section step={2} icon={FlaskConical} title="Brief untuk supplier" testId="sample-section-what"
          hint="Judul terisi otomatis dari spesifikasi bila dikosongkan lalu diklik di luar kolom.">
          <div className="grid gap-2.5 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Judul permintaan *</span>
              <input className="field" data-testid="sample-title-input" value={f.title} onChange={(e) => set("title", e.target.value)} onBlur={autoTitle}
                placeholder="mis. Labdip Katun Combed 150 gsm — biru dongker" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Jumlah diminta</span>
              <input className="field" type="number" min="0" step="any" inputMode="decimal" data-testid="sample-qty-input" value={f.qty_requested}
                onChange={(e) => set("qty_requested", e.target.value)} placeholder="3" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Satuan</span>
              <KNSelect data-testid="sample-unit-input" className="field" value={f.unit} options={masters.unitOptions} onValueChange={(v) => set("unit", v)} />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Untuk pesanan pelanggan (opsional)</span>
              <KNSelect data-testid="sample-so" className="field" value={f.so_id} searchable
                options={[{ value: "", label: "— bukan dari pesanan tertentu —" },
                  ...orders.map((o) => ({ value: o.id, label: `${o.order_number || o.number || o.id}${o.customer_name ? ` · ${o.customer_name}` : ""}` }))]}
                onValueChange={(v) => set("so_id", v)} />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Brief untuk supplier</span>
              <textarea className="field" rows={3} data-testid="sample-brief-input" value={f.brief} onChange={(e) => set("brief", e.target.value)}
                placeholder="mis. Cocokkan warna target maksimal ΔE 1.5, kirim swatch 3 meter" />
            </label>
          </div>
        </Section>

        <Section step={3} icon={CalendarClock} title="Kapan dibutuhkan" hint="Tenggat tiap round mengikuti SLA bila dikosongkan." testId="sample-section-when">
          <label className="block sm:w-1/2">
            <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Target tanggal selesai</span>
            <KNDatePicker data-testid="sample-target-date" value={f.target_date} onChange={(v) => set("target_date", v)} placeholder="Pilih tanggal" />
          </label>
        </Section>
      </div>
    </FormModal>
  );
}
