/**
 * CreateSpecialOrderForm — INTAKE pesanan khusus (Special Order) terstruktur.
 * Pelanggan minta produk custom: referensi fisik/pattern/warna/handfeel → tipe permintaan menentukan routing
 * otomatis saat disetujui (printing → Desainer + R&D proofing; labdip/handfeel → R&D) dengan spesifikasi diwarisi.
 */
import { useEffect, useState } from "react";
import useUomConversions from "../../hooks/useUomConversions";   // INV-UOM-02 — satuan dari master
import { Palette, Sparkles } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNDatePicker from "../../components/KNDatePicker";
import KNSelect from "../../components/KNSelect";
import axios, { API } from "../../services/apiClient";
import { listColors } from "../rnd/rndApi";
import { Field, Hint } from "../rnd/RndField";

const TYPES = [
  { value: "printing", label: "Kain printing (ada desain / pattern)", hint: "→ Desainer membuat desain, lalu R&D proofing" },
  { value: "labdip", label: "Warna khusus (labdip)", hint: "→ R&D mencocokkan warna ke supplier" },
  { value: "handfeel", label: "Pegangan / konstruksi khusus (handfeel)", hint: "→ R&D uji konstruksi & pegangan" },
];

export default function CreateSpecialOrderForm({ token, onCreated, onCancel }) {
  const { unitOptions: _uomOpts } = useUomConversions();   // INV-UOM-02
  const uomAllOptions = _uomOpts();
  const [customers, setCustomers] = useState([]);
  const [colors, setColors] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [cats, setCats] = useState({ pattern: [], design: [] });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({
    customer_id: "", title: "", request_types: [], detail_level: "reference", reference_notes: "",
    template_id: "", fabric_type: "woven", gramasi: "", lebar: "", color_id: "", color_new_note: "", sku_hint: "", spec_notes: "",
    quantity: "", unit: "meter", target_price: "", expected_delivery: "", notes: "", submit: true,
    pattern_category_code: "", design_category_code: "",
  });
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const toggleType = (v) => set("request_types", f.request_types.includes(v) ? f.request_types.filter((x) => x !== v) : [...f.request_types, v]);

  useEffect(() => {
    const H = token ? { headers: { Authorization: `Bearer ${token}` } } : {};
    axios.get(`${API}/customers`, { params: { limit: 500 }, ...H }).then((r) => setCustomers(Array.isArray(r.data) ? r.data : r.data?.items || [])).catch(() => {});
    listColors().then((c) => setColors(Array.isArray(c) ? c : c?.items || [])).catch(() => {});
    axios.get(`${API}/product-templates`, H).then((r) => setTemplates(Array.isArray(r.data) ? r.data : r.data?.items || [])).catch(() => {});
    axios.get(`${API}/design-requests/meta`, H).then((r) => setCats({ pattern: r.data?.categories?.pattern || [], design: r.data?.categories?.design || [] })).catch(() => {});
  }, [token]);

  const full = f.detail_level === "full";
  const problems = [];
  if (!f.customer_id) problems.push("pelanggan");
  if (!f.title.trim()) problems.push("judul");
  if (f.request_types.length === 0) problems.push("tipe permintaan");
  if (!f.quantity || Number(f.quantity) <= 0) problems.push("jumlah");
  if (!f.expected_delivery) problems.push("tenggat");
  if (f.request_types.includes("labdip") && full && !f.color_id && !f.color_new_note.trim()) problems.push("warna target atau catatan warna baru");

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const payload = {
        customer_id: f.customer_id, title: f.title, request_types: f.request_types, detail_level: f.detail_level, reference_notes: f.reference_notes,
        spec: full ? { template_id: f.template_id, fabric_type: f.fabric_type, gramasi: f.gramasi === "" ? null : Number(f.gramasi), lebar: f.lebar === "" ? null : Number(f.lebar),
          color_id: f.color_id, color_new_note: f.color_new_note, sku_hint: f.sku_hint, notes: f.spec_notes }
          : { color_id: f.color_id, color_new_note: f.color_new_note },
        custom_item: { description: f.title, specifications: {}, quantity: Number(f.quantity), unit: f.unit, target_price: Number(f.target_price || 0), notes: f.notes },
        expected_delivery: f.expected_delivery, notes: f.notes, submit_for_approval: f.submit,
        pattern_category_code: f.pattern_category_code, design_category_code: f.design_category_code,
      };
      const res = await axios.post(`${API}/special-orders`, payload, token ? { headers: { Authorization: `Bearer ${token}` } } : undefined);
      onCreated(res.data);
    } catch (e) { setErr(e.response?.data?.detail || e.message); setBusy(false); }
  };

  return (
    <FormModal open onClose={onCancel} size="lg" testId="special-order-form" icon={Sparkles} error={err}
      title="Pesanan Khusus Baru" subtitle="Permintaan produk custom dari pelanggan — diteruskan otomatis ke Desainer / R&D setelah disetujui"
      onSubmit={submit} submitLabel="Simpan pesanan khusus" busy={busy} submitDisabled={problems.length > 0} submitTestId="special-order-save">
      <div className="grid gap-3">
        <Step n={1} title="Pelanggan & permintaan">
          <div className="grid gap-2.5 sm:grid-cols-2">
            <Field label="Pelanggan *">
              <KNSelect data-testid="od-customer" className="field" value={f.customer_id} searchable
                options={[{ value: "", label: "— pilih pelanggan —" }, ...customers.map((c) => ({ value: c.id, label: `${c.name}${c.code ? ` · ${c.code}` : ""}` }))]}
                onValueChange={(v) => set("customer_id", v)} />
            </Field>
            <Field label="Judul permintaan *"><input className="field" data-testid="od-title" value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="mis. Kain seragam navy motif kawung" /></Field>
          </div>
          <div className="mt-2.5">
            <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Tipe permintaan * (boleh lebih dari satu) — menentukan siapa yang mengerjakan</span>
            <div className="grid gap-1.5 sm:grid-cols-3" data-testid="od-request-types">
              {TYPES.map((t) => {
                const on = f.request_types.includes(t.value);
                return (
                  <button key={t.value} type="button" data-testid={`od-type-${t.value}`} onClick={() => toggleType(t.value)}
                    className={`rounded-lg border px-3 py-2 text-left transition-colors ${on ? "border-[#0058CC] bg-[#EFF4FF]" : "border-[#E5E5EA] bg-white hover:border-[#0058CC]"}`}>
                    <p className="text-[11.5px] font-bold text-[#1C1C1E]">{t.label}</p>
                    <p className="text-[10px] text-[#6B6B73]">{t.hint}</p>
                  </button>
                );
              })}
            </div>
          </div>
          {f.request_types.includes("printing") && (
            <div className="mt-2.5 grid gap-2.5 sm:grid-cols-2" data-testid="od-design-categories">
              <Field label="Kategori Pattern (desain)">
                <KNSelect data-testid="od-pattern-category" className="field" value={f.pattern_category_code}
                  options={[{ value: "", label: "— otomatis (kategori pertama aktif) —" }, ...cats.pattern.map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))]}
                  onValueChange={(v) => set("pattern_category_code", v)} />
              </Field>
              <Field label="Kategori Design">
                <KNSelect data-testid="od-design-category" className="field" value={f.design_category_code}
                  options={[{ value: "", label: "— otomatis (kategori pertama aktif) —" }, ...cats.design.map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))]}
                  onValueChange={(v) => set("design_category_code", v)} />
              </Field>
            </div>
          )}
        </Step>

        <Step n={2} title="Referensi pelanggan">
          <div className="grid gap-2.5 sm:grid-cols-[200px_1fr]">
            <Field label="Tingkat detail">
              <KNSelect data-testid="od-detail-level" className="field" value={f.detail_level}
                options={[{ value: "reference", label: "Hanya referensi (foto / kain fisik)" }, { value: "full", label: "Spesifikasi lengkap" }]} onValueChange={(v) => set("detail_level", v)} />
            </Field>
            <Field label="Catatan referensi fisik / pattern / warna / pegangan">
              <input className="field" data-testid="od-reference-notes" value={f.reference_notes} onChange={(e) => set("reference_notes", e.target.value)} placeholder="mis. Pelanggan kirim swatch navy & contoh motif, diterima 19 Sep" />
            </Field>
          </div>
          <Hint>Foto swatch / pattern / kain fisik diunggah di rincian pesanan setelah disimpan (bisa banyak) — otomatis ikut ke Desainer &amp; R&amp;D.</Hint>
        </Step>

        <Step n={3} title={full ? "Spesifikasi produk (lengkap)" : "Spesifikasi produk (ringkas — sisanya diisi R&D)"}>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {full && (
              <>
                <Field label="Induk produk basis (opsional)">
                  <KNSelect data-testid="od-template" className="field" value={f.template_id} searchable
                    options={[{ value: "", label: "— produk benar-benar baru —" }, ...templates.map((t) => ({ value: t.id, label: t.name }))]} onValueChange={(v) => set("template_id", v)} />
                </Field>
                <Field label="Jenis kain"><KNSelect data-testid="od-fabric" className="field" value={f.fabric_type} options={[{ value: "woven", label: "Woven (tenun)" }, { value: "knit", label: "Knit (rajut)" }]} onValueChange={(v) => set("fabric_type", v)} /></Field>
                <Field label="Gramasi (gsm)"><input className="field" type="number" data-testid="od-gramasi" value={f.gramasi} onChange={(e) => set("gramasi", e.target.value)} /></Field>
                <Field label="Lebar (cm)"><input className="field" type="number" data-testid="od-lebar" value={f.lebar} onChange={(e) => set("lebar", e.target.value)} /></Field>
                <Field label="SKU usulan"><input className="field" data-testid="od-sku" value={f.sku_hint} onChange={(e) => set("sku_hint", e.target.value.toUpperCase())} /></Field>
              </>
            )}
            <Field label={`Warna target dari Pustaka Warna${f.request_types.includes("labdip") ? " (labdip)" : ""}`}>
              <KNSelect data-testid="od-color" className="field" value={f.color_id} searchable
                options={[{ value: "", label: "— belum ada / warna baru —" }, ...colors.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` }))]} onValueChange={(v) => set("color_id", v)} />
            </Field>
            <Field label="Bila warna baru: catatan dari swatch pelanggan">
              <input className="field" data-testid="od-color-new" value={f.color_new_note} onChange={(e) => set("color_new_note", e.target.value)} placeholder="mis. navy kebiruan, lebih gelap dari KN-BLU-01" />
            </Field>
            {full && <Field label="Catatan spesifikasi"><input className="field" data-testid="od-spec-notes" value={f.spec_notes} onChange={(e) => set("spec_notes", e.target.value)} /></Field>}
          </div>
        </Step>

        <Step n={4} title="Jumlah, harga & tenggat">
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Jumlah *"><input className="field" type="number" min="0" data-testid="od-qty" value={f.quantity} onChange={(e) => set("quantity", e.target.value)} /></Field>
            <Field label="Satuan"><KNSelect data-testid="od-unit" className="field" value={f.unit} options={uomAllOptions} onValueChange={(v) => set("unit", v)} /></Field>
            <Field label="Target harga / satuan (Rp)"><input className="field" type="number" min="0" data-testid="od-price" value={f.target_price} onChange={(e) => set("target_price", e.target.value)} /></Field>
            <Field label="Tenggat kirim *"><KNDatePicker data-testid="od-delivery" value={f.expected_delivery} onChange={(v) => set("expected_delivery", v)} /></Field>
            <Field label="Catatan pesanan"><input className="field" data-testid="od-notes" value={f.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
          </div>
          <label className="mt-2 flex items-center gap-2 text-[11.5px]">
            <input type="checkbox" checked={f.submit} onChange={(e) => set("submit", e.target.checked)} data-testid="od-submit-approval" /> Langsung ajukan untuk persetujuan Manajer
          </label>
          {problems.length > 0 && <p className="mt-1 text-[11px] text-[#A8221A]" data-testid="od-problems">Belum lengkap: <b>{problems.join(", ")}</b>.</p>}
        </Step>
      </div>
    </FormModal>
  );
}

function Step({ n, title, children }) {
  return (
    <section className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-3">
      <p className="mb-2 flex items-center gap-2 text-[12px] font-bold text-[#1C1C1E]">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#0058CC] text-[10px] text-white">{n}</span>{title}
      </p>
      {children}
    </section>
  );
}
