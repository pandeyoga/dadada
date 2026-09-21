import { useState } from "react";
import { Scissors, Printer } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { apiErrorText } from "../../utils/apiError";
import { notifySuccess } from "../../utils/feedback";
import { formatQty } from "../../utils/formatters";
import { printSampleLabel } from "../../utils/rollLabels";

/** §3-C — panel gudang: potong sampel dari roll induk yang dipindai (RFID/QR/nomor roll), catat panjang aktual. */
export default function SampleCutPanel({ task, onCut }) {
  const [code, setCode] = useState("");
  const [length, setLength] = useState(String(task.quantity ?? ""));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  const cut = async (useSuggested) => {
    setBusy(true); setErr("");
    try {
      const body = useSuggested ? { roll_id: task.suggested_roll_id, actual_length: Number(length) || undefined }
        : { epc: code.trim(), actual_length: Number(length) || undefined, reason };
      const { data } = await axios.post(`${API}/outbound/tasks/${task.id}/cut-sample`, body);
      setDone(data.cut);
      notifySuccess("Sampel dipotong", `${data.cut.cut_roll_no} → ${data.cut.child_roll_no} · ${formatQty(data.cut.length)} ${data.cut.unit}. Lanjut kirim.`);
      onCut?.(data.task);
    } catch (e) { setErr(apiErrorText(e, "Potong gagal.")); }
    finally { setBusy(false); }
  };
  if (done) {
    return (
      <div data-testid={`sample-cut-done-${task.id}`} className="rounded-lg border border-[#BFE6CC] bg-[#F1FBF4] p-2.5 text-[11px] space-y-2">
        <p className="font-semibold text-[#126E2C]">Dipotong: {done.cut_roll_no} → <b>{done.child_roll_no}</b> · {formatQty(done.length)} {done.unit} · sisa induk {formatQty(done.parent_remaining)} {done.unit}</p>
        <button className="secondary-button w-full" onClick={() => printSampleLabel(done)} data-testid={`sample-cut-print-${task.id}`}><Printer size={13} /> Cetak label potongan</button>
      </div>
    );
  }
  return (
    <div data-testid={`sample-cut-panel-${task.id}`} className="rounded-lg border border-[#F3D9A4] bg-[#FFF9EC] p-2.5 space-y-2 text-[11px]">
      <p className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[#9A5B00]"><Scissors size={11} /> Permintaan potong sampel</p>
      <p className="text-[#3C3C43]">Untuk <b>{task.customer_name}</b> · diminta <b>{formatQty(task.quantity)} {task.unit}</b> · saran FIFO: <b data-testid={`sample-cut-suggested-${task.id}`}>{task.suggested_roll_no || "tidak ada"}</b>. Cari roll dengan handheld RFID, potong, lalu catat panjang aktual — sisa yard roll induk & stok diperbarui otomatis.</p>
      <div>
        <label className="block text-[10px] font-semibold text-[#6B6B73] mb-1">Panjang aktual dipotong ({task.unit})</label>
        <input data-testid={`sample-cut-length-${task.id}`} type="number" step="0.1" min="0" value={length} onChange={(e) => setLength(e.target.value)} className="w-full border border-[#E5E5EA] rounded-lg px-2 py-1.5 text-sm" />
      </div>
      {task.suggested_roll_id && (
        <button data-testid={`sample-cut-use-suggested-${task.id}`} disabled={busy} onClick={() => cut(true)} className="w-full bg-[#FF9500] hover:bg-[#CC7700] text-white rounded-lg px-3 py-2 text-[12px] font-semibold disabled:opacity-50">
          Potong roll saran ({task.suggested_roll_no})
        </button>
      )}
      <div className="rounded-lg border border-[#E5E5EA] bg-white p-2 space-y-1.5">
        <label className="block text-[10px] font-semibold text-[#6B6B73]">Roll lain — pindai EPC / QR atau ketik nomor roll{task.suggested_roll_id ? " (wajib alasan)" : ""}</label>
        <input data-testid={`sample-cut-code-${task.id}`} value={code} onChange={(e) => setCode(e.target.value)} placeholder="EPC tag / nomor roll" className="w-full border border-[#E5E5EA] rounded-lg px-2 py-1.5 text-sm" />
        <input data-testid={`sample-cut-reason-${task.id}`} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Alasan (mis. roll saran tidak ditemukan)" className="w-full border border-[#E5E5EA] rounded-lg px-2 py-1.5 text-sm" />
        <button data-testid={`sample-cut-other-${task.id}`} disabled={busy || !code.trim()} onClick={() => cut(false)} className="w-full border border-[#FF9500] text-[#CC7700] rounded-lg px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50">Potong roll ini</button>
      </div>
      {err && <p data-testid={`sample-cut-error-${task.id}`} className="text-[#B23B14] font-medium">{err}</p>}
    </div>
  );
}
