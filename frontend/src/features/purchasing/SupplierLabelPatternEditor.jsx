/** SupplierLabelPatternEditor — pola label supplier (GS1 / QR JSON / teks berpemisah / regex) + uji scan contoh. */
import { useState } from "react";
import useUomConversions from "../../hooks/useUomConversions";   // INV-UOM-02 — satuan dari master
import { ScanLine } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import KNSelect from "../../components/KNSelect";

export const DEFAULT_LABEL_PATTERN = {
  format: "auto", length_unit: "yard", delimiter: "|",
  fields: ["supplier_sku", "lot", "roll_no", "length", "weight_kg", "color_code"],
  regex: "", json_keys: {}, gs1_ai_map: {},
};

const FORMATS = [
  { value: "auto", label: "Otomatis (deteksi JSON → GS1 → teks)" },
  { value: "gs1", label: "GS1-128 / GS1 DataMatrix (AI 01·10·21·240·3230·3103)" },
  { value: "qr_json", label: "QR berisi JSON" },
  { value: "delimited", label: "Teks berpemisah (mis. SKU|LOT|ROLL|LEN|WT)" },
  { value: "regex", label: "Regex (grup bernama)" },
];
const GS1_FIELDS = [
  { key: "supplier_sku", label: "Kode barang", def: "240" }, { key: "lot", label: "Lot / dye lot", def: "10" },
  { key: "roll_no", label: "Nomor roll", def: "21" }, { key: "length_yd", label: "Panjang (yard)", def: "323" },
  { key: "length_m", label: "Panjang (meter)", def: "311" }, { key: "weight_kg", label: "Berat (kg)", def: "310" },
  { key: "color_code", label: "Kode warna", def: "91" },
];
const LABELS = { supplier_sku: "Kode barang", gtin: "GTIN", lot: "Lot", roll_no: "No. roll", length: "Panjang", length_unit: "Satuan", weight_kg: "Berat kg", color_code: "Warna", count: "Jumlah", format: "Format" };

export default function SupplierLabelPatternEditor({ value, onChange }) {
  const { unitOptions: _uomOpts } = useUomConversions();   // INV-UOM-02
  const uomLengthOptions = _uomOpts("length");
  const p = { ...DEFAULT_LABEL_PATTERN, ...(value || {}) };
  const set = (patch) => onChange({ ...p, ...patch });
  const [sample, setSample] = useState("");
  const [result, setResult] = useState(null);
  const aiFor = (f) => Object.entries(p.gs1_ai_map || {}).find(([, v]) => v === f.key)?.[0] ?? f.def;
  const setAi = (f, ai) => {
    const m = Object.fromEntries(Object.entries(p.gs1_ai_map || {}).filter(([, v]) => v !== f.key));
    if (ai.trim() && ai.trim() !== f.def) m[ai.trim()] = f.key;
    set({ gs1_ai_map: m });
  };

  const test = async () => {
    try {
      const r = await axios.post(`${API}/suppliers/label-pattern/test`, { raw: sample, pattern: p });
      setResult(r.data);
    } catch (e) { setResult({ ok: false, error: e.response?.data?.detail || "Uji gagal." }); }
  };

  return (
    <div data-testid="supplier-label-pattern" className="rounded-lg border border-[#E5E5EA] p-3 space-y-2.5">
      <div className="flex items-center gap-2">
        <ScanLine size={13} className="text-[#0058CC]" />
        <p className="text-[11.5px] font-bold text-[#1C1C1E]">Pola Label Roll Supplier</p>
        <span className="text-[10px] text-[#8E8E93]">— cara membaca barcode/QR di label pabrik saat penerimaan</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Format label</span>
          <KNSelect data-testid="label-pattern-format" value={p.format} onValueChange={(v) => set({ format: v })} className="field" options={FORMATS} />
        </label>
        <label className="block">
          <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Satuan panjang di label (bila tak tersurat)</span>
          <KNSelect data-testid="label-pattern-unit" value={p.length_unit} onValueChange={(v) => set({ length_unit: v })} className="field"
            options={uomLengthOptions} />
        </label>
        {(p.format === "delimited" || p.format === "auto") && (
          <>
            <label className="block">
              <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Pemisah</span>
              <input data-testid="label-pattern-delimiter" value={p.delimiter} onChange={(e) => set({ delimiter: e.target.value })} className="field font-mono" maxLength={3} />
            </label>
            <label className="block">
              <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Urutan kolom (pisahkan koma)</span>
              <input data-testid="label-pattern-fields" value={(p.fields || []).join(",")}
                onChange={(e) => set({ fields: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                className="field font-mono text-[10.5px]" placeholder="supplier_sku,lot,roll_no,length,weight_kg,kode_warna" />
            </label>
          </>
        )}
        {p.format === "regex" && (
          <label className="col-span-2 block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Regex dengan grup bernama (?P&lt;supplier_sku&gt;…) (?P&lt;lot&gt;…) (?P&lt;roll_no&gt;…) (?P&lt;length&gt;…)</span>
            <input data-testid="label-pattern-regex" value={p.regex} onChange={(e) => set({ regex: e.target.value })} className="field font-mono text-[10.5px]" />
          </label>
        )}
      </div>
      {(p.format === "gs1" || p.format === "auto") && (
        <div>
          <p className="mb-1 text-[10px] font-semibold text-[#6B6B73]">Peta AI GS1 (kosongkan = baku)</p>
          <div className="grid grid-cols-4 gap-1.5">
            {GS1_FIELDS.map((f) => (
              <label key={f.key} className="block">
                <span className="block text-[9px] text-[#8E8E93]">{f.label}</span>
                <input data-testid={`label-pattern-ai-${f.key}`} value={aiFor(f)} onChange={(e) => setAi(f, e.target.value)}
                  className="field font-mono !py-1 text-[10.5px]" placeholder={f.def} />
              </label>
            ))}
          </div>
        </div>
      )}
      <div className="rounded-md bg-[#FAFBFC] p-2">
        <p className="mb-1 text-[10px] font-semibold text-[#6B6B73]">Uji dengan scan contoh (tidak menyimpan apa pun)</p>
        <div className="flex gap-1.5">
          <input data-testid="label-pattern-sample" value={sample} onChange={(e) => setSample(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); test(); } }}
            className="field flex-1 font-mono text-[10.5px]" placeholder='(240)ABC-01(10)DL77(21)R0001(3230)00012000  atau  {"sku":"ABC-01","lot":"DL77","roll":"R1","yd":120}' />
          <button type="button" onClick={test} disabled={!sample.trim()} data-testid="label-pattern-test-btn"
            className="rounded-md bg-[#0058CC] px-3 text-[11px] font-semibold text-white disabled:opacity-40">Uji</button>
        </div>
        {result && (
          <div data-testid="label-pattern-test-result" className={`mt-1.5 rounded-md border p-2 text-[10.5px] ${result.ok ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50 text-red-800"}`}>
            {result.ok ? (
              <div className="grid grid-cols-3 gap-x-3 gap-y-0.5">
                {Object.entries(result.decoded).filter(([k]) => k !== "raw").map(([k, v]) => (
                  <span key={k}><span className="text-[#6B6B73]">{LABELS[k] || k}:</span> <b className="font-mono">{v === null || v === "" ? "—" : String(v)}</b></span>
                ))}
              </div>
            ) : <span>{String(result.error)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
