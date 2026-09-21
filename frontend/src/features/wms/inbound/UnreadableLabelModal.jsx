/** UnreadableLabelModal — fallback label rusak: barang DIPILIH dari item PO, hanya nomor roll & ukuran label diketik. */
import { useEffect, useState } from "react";
import useUomConversions from "../../../hooks/useUomConversions";   // INV-UOM-02 — satuan dari master
import { FileQuestion } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import FormModal from "../../../components/FormModal";
import KNSelect from "../../../components/KNSelect";

const REASONS = [
  { value: "label_unreadable", label: "Barcode/QR tidak terbaca scanner" },
  { value: "label_damaged", label: "Label rusak / sobek / luntur" },
  { value: "no_barcode", label: "Label tanpa barcode (teks saja)" },
  { value: "other", label: "Lainnya" },
];

export default function UnreadableLabelModal({ task, supplierId, busy, onClose, onSubmit }) {
  const { unitOptions: _uomOpts } = useUomConversions();   // INV-UOM-02
  const uomLengthOptions = _uomOpts("length");
  const [items, setItems] = useState([]);
  const [f, setF] = useState({ supplier_item_id: "", supplier_roll_no: "", declared_length: "", length_unit: task.unit === "meter" ? "meter" : "yard",
    declared_weight_kg: "", lot: "", color_code: "", reason: "label_unreadable", reason_note: "" });
  const [err, setErr] = useState("");

  useEffect(() => {
    const p = new URLSearchParams({ product_id: task.product_id });
    if (supplierId) p.set("supplier_id", supplierId);
    axios.get(`${API}/supplier-items?${p}`).then((r) => {
      const rows = Array.isArray(r.data) ? r.data : (r.data?.items || []);
      setItems(rows);
      if (rows.length === 1) setF((x) => ({ ...x, supplier_item_id: rows[0].id }));
    }).catch(() => setItems([]));
  }, [task.product_id, supplierId]);

  const submit = () => {
    if (!f.supplier_roll_no.trim()) { setErr("Nomor roll supplier wajib (baca dari label fisik)."); return; }
    if (!(Number(f.declared_length) > 0) && !(Number(f.declared_weight_kg) > 0)) { setErr("Isi panjang atau berat dari label."); return; }
    setErr("");
    onSubmit({ ...f, declared_length: Number(f.declared_length) || 0, declared_weight_kg: Number(f.declared_weight_kg) || 0 });
  };

  return (
    <FormModal open onClose={onClose} title="Label tidak terbaca" icon={FileQuestion}
      subtitle={`Barang dari PO ${task.po_number}: ${task.product_name}`} size="md" testId="unreadable-label-modal"
      onSubmit={submit} submitLabel={busy ? "Menyimpan…" : "Catat roll (manual override)"}
      submitTestId="unreadable-label-submit" cancelTestId="unreadable-label-cancel" error={err}>
      <div className="space-y-2.5 text-[11px]">
        <div className="rounded-md border border-[#E5F0FF] bg-[#F5F9FF] px-2 py-1.5 text-[10.5px] text-[#0058CC]">
          Produk KN: <b>{task.sku}</b> — {task.product_name}. Kejadian ini dicatat sebagai <b>manual override</b> untuk laporan % label tidak terbaca per supplier.
        </div>
        {items.length > 1 && (
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Barang versi supplier (dari item PO)</span>
            <KNSelect data-testid="unreadable-supplier-item-select" value={f.supplier_item_id}
              onValueChange={(v) => setF({ ...f, supplier_item_id: v })} className="field" placeholder="Pilih barang supplier"
              options={items.map((i) => ({ value: i.id, label: `${i.supplier_sku} — ${i.supplier_item_name || i.sku}` }))} />
          </label>
        )}
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Nomor roll supplier *</span>
            <input data-testid="unreadable-roll-no-input" value={f.supplier_roll_no} autoFocus
              onChange={(e) => setF({ ...f, supplier_roll_no: e.target.value })} className="field font-mono" placeholder="mis. R-00123" />
          </label>
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Lot / dye lot supplier</span>
            <input data-testid="unreadable-lot-input" value={f.lot}
              onChange={(e) => setF({ ...f, lot: e.target.value })} className="field font-mono" placeholder="mis. DL-2407" />
          </label>
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Panjang di label</span>
            <div className="flex gap-1">
              <input type="number" step="0.01" data-testid="unreadable-length-input" value={f.declared_length}
                onChange={(e) => setF({ ...f, declared_length: e.target.value })} className="field flex-1 tabular-nums" placeholder="120" />
              <KNSelect data-testid="unreadable-length-unit" value={f.length_unit} onValueChange={(v) => setF({ ...f, length_unit: v })}
                className="field !w-20" options={uomLengthOptions} />
            </div>
          </label>
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Berat di label (kg)</span>
            <input type="number" step="0.001" data-testid="unreadable-weight-input" value={f.declared_weight_kg}
              onChange={(e) => setF({ ...f, declared_weight_kg: e.target.value })} className="field tabular-nums" placeholder="opsional" />
          </label>
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Kode warna supplier</span>
            <input data-testid="unreadable-color-input" value={f.color_code}
              onChange={(e) => setF({ ...f, color_code: e.target.value })} className="field font-mono" placeholder="opsional" />
          </label>
          <label className="block">
            <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Alasan *</span>
            <KNSelect data-testid="unreadable-reason-select" value={f.reason} onValueChange={(v) => setF({ ...f, reason: v })}
              className="field" options={REASONS} />
          </label>
        </div>
        <label className="block">
          <span className="mb-0.5 block text-[10px] font-semibold text-[#6B6B73]">Catatan</span>
          <input data-testid="unreadable-note-input" value={f.reason_note}
            onChange={(e) => setF({ ...f, reason_note: e.target.value })} className="field" placeholder="mis. label basah terkena hujan" />
        </label>
      </div>
    </FormModal>
  );
}
