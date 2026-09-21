/** ScannedRollRow — satu roll hasil scan label: alias supplier + dua satuan + konfirmasi aktual + bin. */
import { useState } from "react";
import { Check, MapPin, Trash2, AlertTriangle, PenLine, Radio, Printer } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { apiErrorText } from "../../../utils/apiError";
import { formatQty } from "../../../utils/formatters";
import { reprintRollLabel } from "../../../utils/rollLabels";
import { GRADE_OPTIONS } from "../InboundScanForm";
import KNSelect from "../../../components/KNSelect";

const num = (v) => (v === "" || v === null || v === undefined ? "" : String(v));

export default function ScannedRollRow({ roll, taskUnit, bins = [], tolerance, readOnly, highlight, onChanged, onRemoved, productName = "" }) {
  const [len, setLen] = useState(num(roll.length_initial));
  const [wt, setWt] = useState(num(roll.weight_kg || ""));
  const [grade, setGrade] = useState(roll.grade || "A");
  const [bin, setBin] = useState(roll.bin_code || "");
  const [epc, setEpc] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const v = roll.label_variance;

  const tagRfid = async () => {
    setBusy(true); setErr("");
    try {
      const r = await axios.post(`${API}/inbound/rolls/${roll.id}/tag`, { epc: epc.trim() });
      onChanged?.({ roll: r.data.roll });
      setEpc("");
    } catch (e) { setErr(apiErrorText(e, "Tag RFID gagal.")); }
    finally { setBusy(false); }
  };

  const confirm = async () => {
    setBusy(true); setErr("");
    try {
      const r = await axios.post(`${API}/inbound/rolls/${roll.id}/confirm-measure`, {
        actual_length: len === "" ? null : Number(len),
        actual_weight_kg: wt === "" ? null : Number(wt),
        grade,
      });
      onChanged?.(r.data);
    } catch (e) { setErr(apiErrorText(e, "Konfirmasi gagal.")); }
    finally { setBusy(false); }
  };

  const putaway = async () => {
    if (!bin.trim()) return;
    setBusy(true); setErr("");
    try {
      const r = await axios.post(`${API}/inbound/rolls/${roll.id}/putaway`, { bin_code: bin.trim() });
      onChanged?.({ roll: r.data.roll });
    } catch (e) { setErr(apiErrorText(e, "Bin tidak dikenal.")); }
    finally { setBusy(false); }
  };

  const undo = async () => {
    setBusy(true); setErr("");
    try {
      const r = await axios.delete(`${API}/inbound/rolls/${roll.id}/scan`);
      onRemoved?.(roll.id, r.data.task);
    } catch (e) { setErr(apiErrorText(e, "Tidak bisa dibatalkan.")); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid={`scanned-roll-${roll.id}`}
      className={`px-2.5 py-2 text-[11px] ${highlight ? "bg-[#F0FFF4]" : v?.flagged ? "bg-red-50/60" : "bg-white"}`}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-bold text-[#007AFF]" data-testid={`scanned-roll-no-${roll.id}`}>{roll.roll_no}</span>
        <span className="text-[#6B6B73]">← supplier <b className="font-mono text-[#1C1C1E]">{roll.supplier_roll_no}</b></span>
        {roll.supplier_lot && (
          <span data-testid={`scanned-roll-lot-${roll.id}`}
            className="rounded bg-[#F3E8FF] px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[#6B219A]">lot {roll.supplier_lot}</span>
        )}
        {roll.supplier_color_code && (
          <span className="rounded bg-[#FFF4E5] px-1.5 py-0.5 font-mono text-[10px] text-[#B26A00]">warna {roll.supplier_color_code}</span>
        )}
        {roll.manual_override && (
          <span title={roll.manual_override.reason} className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 text-[9.5px] font-semibold text-amber-800">
            <PenLine size={9} /> manual
          </span>
        )}
        {roll.measure_confirmed && !v?.flagged && (
          <span className="inline-flex items-center gap-0.5 rounded bg-emerald-100 px-1.5 py-0.5 text-[9.5px] font-semibold text-emerald-700"><Check size={9} /> dikonfirmasi</span>
        )}
        {v?.flagged && (
          <span data-testid={`scanned-roll-variance-${roll.id}`} title={v.message}
            className="inline-flex items-center gap-0.5 rounded bg-red-100 px-1.5 py-0.5 text-[9.5px] font-semibold text-red-700">
            <AlertTriangle size={9} /> selisih label vs aktual → QC
          </span>
        )}
        {roll.bin_code && (
          <span className="inline-flex items-center gap-0.5 rounded bg-[#EEF2FF] px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[#4338CA]"><MapPin size={9} /> {roll.bin_code}</span>
        )}
        {roll.rfid_epc ? (
          <span data-testid={`scanned-roll-epc-${roll.id}`} title="EPC RFID tertaut"
            className="ml-auto inline-flex items-center gap-0.5 rounded bg-[#E6F7F1] px-1.5 py-0.5 font-mono text-[9.5px] font-semibold text-[#1B7F4B]"><Radio size={9} /> {roll.rfid_epc}</span>
        ) : (
          <span data-testid={`scanned-roll-notag-${roll.id}`} className="ml-auto rounded bg-gray-100 px-1.5 py-0.5 text-[9.5px] text-[#6B6B73]">tanpa tag RFID</span>
        )}
        <button type="button" onClick={() => reprintRollLabel({ ...roll, length: roll.length_initial }, productName)}
          data-testid={`scanned-roll-print-${roll.id}`} title="Cetak label KN roll ini"
          className="inline-flex items-center gap-0.5 rounded border border-[#CFE0F5] bg-white px-1.5 py-0.5 text-[9.5px] font-semibold text-[#0058CC] hover:bg-[#F0F6FF]"><Printer size={9} /> Label</button>
      </div>
      <p className="mt-0.5 text-[10px] text-[#6B6B73]">
        <span className="font-semibold text-[#0058CC]">{roll.supplier_sku || "-"}</span>
        {roll.supplier_item_name ? ` — ${roll.supplier_item_name}` : ""}
        <span className="ml-2">label: <b>{formatQty(roll.declared_length_label ?? roll.declared_length)} {roll.declared_length_unit || roll.unit}</b>
          {" "}≈ {formatQty(roll.length_m)} m ≈ {formatQty(roll.length_yd)} yd{roll.declared_weight_kg ? ` · ${formatQty(roll.declared_weight_kg)} kg` : ""}</span>
      </p>

      {!readOnly && roll.status === "receiving" && (
        <div className="mt-1.5 grid grid-cols-[1fr_1fr_1fr_auto_1fr_auto_auto] items-end gap-1.5">
          <label className="block">
            <span className="text-[9px] font-semibold uppercase text-[#6B6B73]">Aktual ({roll.unit})</span>
            <input type="number" step="0.01" value={len} onChange={(e) => setLen(e.target.value)}
              data-testid={`scanned-roll-length-${roll.id}`}
              className="w-full rounded-md border border-[#D6D7DC] px-1.5 py-1 text-[11px] tabular-nums" />
          </label>
          <label className="block">
            <span className="text-[9px] font-semibold uppercase text-[#6B6B73]">Aktual kg</span>
            <input type="number" step="0.001" value={wt} onChange={(e) => setWt(e.target.value)}
              data-testid={`scanned-roll-weight-${roll.id}`} placeholder="timbang"
              className="w-full rounded-md border border-[#D6D7DC] px-1.5 py-1 text-[11px] tabular-nums" />
          </label>
          <label className="block">
            <span className="text-[9px] font-semibold uppercase text-[#6B6B73]">Grade</span>
            <KNSelect value={grade} onValueChange={setGrade} data-testid={`scanned-roll-grade-${roll.id}`}
              className="w-full rounded-md border border-[#D6D7DC] px-1 py-1 text-[11px]"
              options={GRADE_OPTIONS.map((g) => ({ value: g.value, label: g.value }))} />
          </label>
          <button type="button" onClick={confirm} disabled={busy} data-testid={`scanned-roll-confirm-${roll.id}`}
            className="rounded-md bg-[#34C759] px-2 py-1.5 text-[10.5px] font-semibold text-white disabled:opacity-50">
            {roll.measure_confirmed ? "Koreksi" : "Konfirmasi"}
          </button>
          <label className="block">
            <span className="text-[9px] font-semibold uppercase text-[#6B6B73]">Scan bin</span>
            <input list={`bins-${roll.id}`} value={bin} onChange={(e) => setBin(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); putaway(); } }}
              data-testid={`scanned-roll-bin-${roll.id}`} placeholder="A1-01"
              className="w-full rounded-md border border-[#D6D7DC] px-1.5 py-1 font-mono text-[11px]" />
            <datalist id={`bins-${roll.id}`}>{bins.map((b) => <option key={b.id} value={b.code}>{b.zone} / {b.rack}</option>)}</datalist>
          </label>
          <button type="button" onClick={putaway} disabled={busy || !bin.trim()} data-testid={`scanned-roll-putaway-${roll.id}`}
            className="rounded-md bg-[#4338CA] px-2 py-1.5 text-[10.5px] font-semibold text-white disabled:opacity-40"><MapPin size={11} /></button>
          <button type="button" onClick={undo} disabled={busy} title="Batalkan scan ini" data-testid={`scanned-roll-undo-${roll.id}`}
            className="rounded-md border border-red-200 px-2 py-1.5 text-red-600 hover:bg-red-50 disabled:opacity-40"><Trash2 size={11} /></button>
        </div>
      )}
      {!readOnly && roll.status === "receiving" && !roll.rfid_epc && (
        <div className="mt-1.5 flex items-center gap-1.5">
          <input value={epc} onChange={(e) => setEpc(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); tagRfid(); } }}
            data-testid={`scanned-roll-epc-input-${roll.id}`} placeholder="EPC dari handheld (kosongkan = EPC sistem)"
            className="flex-1 rounded-md border border-[#D6D7DC] px-1.5 py-1 font-mono text-[10.5px]" />
          <button type="button" onClick={tagRfid} disabled={busy} data-testid={`scanned-roll-tag-${roll.id}`}
            className="inline-flex items-center gap-1 rounded-md bg-[#1B7F4B] px-2 py-1 text-[10.5px] font-semibold text-white disabled:opacity-50">
            <Radio size={11} /> Tag RFID
          </button>
        </div>
      )}
      {v && (
        <p className={`mt-1 text-[9.5px] ${v.flagged ? "text-red-700" : "text-emerald-700"}`}>
          {v.length_pct != null ? `panjang ${v.length_declared} → ${v.length_actual} (${v.length_pct}%)` : ""}
          {v.weight_pct != null && v.weight_declared > 0 ? ` · berat ${v.weight_declared} → ${v.weight_actual} kg (${v.weight_pct}%)` : ""}
          {" "}· toleransi {v.tolerance_pct ?? tolerance}%
        </p>
      )}
      {err && <p data-testid={`scanned-roll-error-${roll.id}`} className="mt-1 text-[10px] font-semibold text-red-700">{err}</p>}
    </div>
  );
}
