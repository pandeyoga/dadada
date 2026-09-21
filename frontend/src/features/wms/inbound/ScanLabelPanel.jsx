/**
 * ScanLabelPanel — FASE SL: "Scan – Konfirmasi – Tempel – Simpan bin".
 * Identitas roll (nomor, lot, kode barang, warna) datang dari label supplier + master;
 * manusia hanya mengonfirmasi ukuran aktual & grade.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Camera, CameraOff, ScanLine, FileQuestion, ShieldAlert } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { apiErrorText } from "../../../utils/apiError";
import { notifySuccess } from "../../../utils/feedback";
import { formatQty } from "../../../utils/formatters";
import ScannedRollRow from "./ScannedRollRow";
import UnreadableLabelModal from "./UnreadableLabelModal";
import RollLabelActions from "../../../components/RollLabelActions";
import { Radio } from "lucide-react";

const errDetail = (e) => {
  const d = e?.response?.data?.detail;
  if (d && typeof d === "object") return { code: d.code || "", message: d.message || JSON.stringify(d) };
  return { code: "", message: apiErrorText(e, "Scan gagal.") };
};

export default function ScanLabelPanel({ task, onTaskUpdated, onEscalate }) {
  const [rolls, setRolls] = useState([]);
  const [meta, setMeta] = useState({ tolerance_pct: 2, bins: [], supplier_name: "", supplier_id: "" });
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [lastOk, setLastOk] = useState(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const inputRef = useRef(null);
  const lastCam = useRef({ text: "", at: 0 });
  const readerRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/inbound/tasks/${task.id}/scanned-rolls`);
      setRolls(r.data.rolls || []);
      setMeta(r.data);
    } catch (e) { setErr(errDetail(e)); }
  }, [task.id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => () => stopCamera(), []); // eslint-disable-line

  const applyResult = (data, title) => {
    setRolls((prev) => [data.roll, ...prev.filter((x) => x.id !== data.roll.id)]);
    onTaskUpdated?.(data.task);
    setLastOk(data.roll);
    setErr(null);
    notifySuccess(title, `${data.roll.roll_no} ← ${data.roll.supplier_roll_no} · ${formatQty(data.roll.length_m)} m ≈ ${formatQty(data.roll.length_yd)} yd`);
  };

  const submitRaw = async (text) => {
    const v = (text || "").trim();
    if (!v || busy) return;
    setBusy(true);
    try {
      const r = await axios.post(`${API}/inbound/tasks/${task.id}/scan-label`, { raw: v });
      applyResult(r.data, "Roll diterima dari label");
      setRaw("");
    } catch (e) { setErr(errDetail(e)); }
    finally { setBusy(false); inputRef.current?.focus(); }
  };

  const submitManual = async (manual) => {
    setBusy(true);
    try {
      const r = await axios.post(`${API}/inbound/tasks/${task.id}/scan-label`, { raw: "", manual });
      applyResult(r.data, "Roll dicatat (label tidak terbaca)");
      setShowManual(false);
    } catch (e) { setErr(errDetail(e)); }
    finally { setBusy(false); }
  };

  const startCamera = async () => {
    try {
      const { BrowserMultiFormatReader } = await import("@zxing/browser");
      const reader = new BrowserMultiFormatReader();
      readerRef.current = reader;
      const el = document.getElementById("scan-label-video");
      if (!el) return;
      await reader.decodeFromVideoDevice(null, el, (result) => {
        if (!result) return;
        const text = result.getText();
        const now = Date.now();
        if (text === lastCam.current.text && now - lastCam.current.at < 4000) return;
        lastCam.current = { text, at: now };
        submitRaw(text);
      });
      setCameraActive(true);
    } catch { setErr({ code: "", message: "Kamera tidak bisa dibuka. Beri izin kamera, atau pakai scanner HID / tombol 'Label tidak terbaca'." }); }
  };

  const stopCamera = () => {
    const el = document.getElementById("scan-label-video");
    if (el?.srcObject) { el.srcObject.getTracks().forEach((t) => t.stop()); el.srcObject = null; }
    setCameraActive(false);
  };

  const onRollChanged = (data) => {
    setRolls((prev) => prev.map((x) => (x.id === data.roll.id ? data.roll : x)));
    if (data.task) onTaskUpdated?.(data.task);
  };

  const onRollRemoved = (rollId, taskAfter) => {
    setRolls((prev) => prev.filter((x) => x.id !== rollId));
    if (taskAfter) onTaskUpdated?.(taskAfter);
  };

  const sumTask = rolls.reduce((a, r) => a + Number(r.measure_confirmed ? (r.actual_task_qty ?? r.declared_task_qty) : r.declared_task_qty || 0), 0);
  const flagged = rolls.filter((r) => r.label_variance?.flagged).length;
  const unconfirmed = rolls.filter((r) => !r.measure_confirmed).length;
  const untagged = rolls.filter((r) => !r.rfid_epc && r.status === "receiving");
  const closed = ["completed", "qc_pending", "escalated", "cancelled"].includes(task.status);

  const tagAll = async () => {
    setBusy(true);
    let ok = 0;
    for (const r of untagged) {
      try { const res = await axios.post(`${API}/inbound/rolls/${r.id}/tag`, { epc: "" }); onRollChanged({ roll: res.data.roll }); ok += 1; }
      catch (e) { setErr(errDetail(e)); }
    }
    setBusy(false);
    if (ok) notifySuccess("Tag RFID dibuat", `${ok} roll mendapat EPC.`);
  };
  const labelRolls = rolls.map((r) => ({ ...r, length: r.length_initial, product_name: meta.product_name || task.product_name }));

  return (
    <div data-testid="scan-label-panel" className="space-y-2.5">
      {/* Ringkasan diharapkan vs di-scan */}
      <div className="grid grid-cols-3 gap-2 rounded-lg border border-[#E5F0FF] bg-[#F5F9FF] p-2 text-[10.5px]">
        <div>
          <p className="font-semibold uppercase text-[#6B6B73]">Diharapkan</p>
          <p data-testid="scan-label-expected" className="text-[12px] font-bold text-[#1C1C1E]">
            {task.expected_rolls ? `${task.expected_rolls} roll · ` : ""}{formatQty(task.expected_qty)} {task.unit}
          </p>
        </div>
        <div>
          <p className="font-semibold uppercase text-[#6B6B73]">Di-scan</p>
          <p data-testid="scan-label-scanned" className="text-[12px] font-bold text-[#0058CC]">
            {rolls.length} roll · {formatQty(sumTask)} {task.unit}
          </p>
        </div>
        <div>
          <p className="font-semibold uppercase text-[#6B6B73]">Status</p>
          <p className="text-[11px] font-semibold">
            {unconfirmed > 0 && <span className="text-amber-700">{unconfirmed} belum dikonfirmasi</span>}
            {flagged > 0 && <span className="ml-1 text-red-700">· {flagged} selisih &gt;{meta.tolerance_pct}%</span>}
            {unconfirmed === 0 && flagged === 0 && rolls.length > 0 && <span className="text-emerald-700">semua dikonfirmasi</span>}
            {rolls.length === 0 && <span className="text-[#8E8E93]">belum ada scan</span>}
          </p>
        </div>
      </div>

      {!closed && (
        <>
          {/* Input scanner HID + kamera */}
          <div className="flex items-stretch gap-2">
            <div className="relative flex-1">
              <ScanLine size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#0058CC]" />
              <input ref={inputRef} autoFocus value={raw} onChange={(e) => setRaw(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); submitRaw(raw); } }}
                data-testid="scan-label-input" disabled={busy}
                placeholder="Arahkan scanner ke label supplier (GS1 / QR / teks) lalu Enter…"
                className="w-full rounded-lg border-2 border-[#0058CC]/40 bg-white py-2 pl-8 pr-3 font-mono text-[12px] focus:border-[#0058CC] focus:outline-none" />
            </div>
            <button type="button" onClick={() => submitRaw(raw)} disabled={busy || !raw.trim()}
              data-testid="scan-label-submit"
              className="rounded-lg bg-[#0058CC] px-3 text-[11.5px] font-semibold text-white disabled:opacity-40">
              Scan
            </button>
            <button type="button" onClick={cameraActive ? stopCamera : startCamera}
              data-testid="scan-label-camera-toggle"
              className={`flex items-center gap-1 rounded-lg px-2.5 text-[11px] font-medium ${cameraActive ? "bg-red-500 text-white" : "border border-[#007AFF]/30 bg-[#F5F7FF] text-[#007AFF]"}`}>
              {cameraActive ? <><CameraOff size={12} /> Stop</> : <><Camera size={12} /> Kamera</>}
            </button>
          </div>
          <video id="scan-label-video" className={`w-full rounded-lg border border-[#007AFF]/30 ${cameraActive ? "block" : "hidden"}`} style={{ maxHeight: 180 }} />

          <div className="flex items-center justify-between">
            <button type="button" onClick={() => setShowManual(true)} data-testid="scan-label-unreadable-btn"
              className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[10.5px] font-semibold text-amber-800 hover:bg-amber-100">
              <FileQuestion size={12} /> Label tidak terbaca
            </button>
            <span className="text-[10px] text-[#8E8E93]">
              Supplier: {meta.supplier_name || task.supplier_name || "-"} · toleransi selisih {meta.tolerance_pct}%
              {(meta.item_label_patterns || []).length > 0 && (
                <span data-testid="scan-label-item-patterns" className="ml-1 rounded border border-[#CFE3FF] bg-[#F0F6FF] px-1 py-0.5 font-semibold text-[#0058CC]">
                  pola barang: {meta.item_label_patterns.map((p) => `${p.supplier_sku} (${p.format})`).join(", ")}
                </span>
              )}
            </span>
          </div>
        </>
      )}

      {/* Galat scan — layar merah */}
      {err && (
        <div data-testid="scan-label-error" role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-2.5 text-[11px] text-red-800">
          <div className="flex items-start gap-2">
            <ShieldAlert size={14} className="mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="font-bold">{err.code === "UNMAPPED" ? "Barang tidak ada di PO / belum dipetakan" : err.code === "DUPLICATE" ? "Roll sudah diterima" : err.code === "NOT_IN_TASK" ? "Bukan barang tugas ini" : "Scan ditolak"}</p>
              <p>{err.message}</p>
              <div className="mt-1.5 flex gap-2">
                {["UNMAPPED", "NOT_IN_TASK", "OVER_PO"].includes(err.code) && onEscalate && (
                  <button type="button" onClick={onEscalate} data-testid="scan-label-escalate-btn"
                    className="inline-flex items-center gap-1 rounded-md bg-orange-500 px-2 py-1 text-[10.5px] font-semibold text-white">
                    <AlertTriangle size={11} /> Eskalasi ke purchasing
                  </button>
                )}
                {["UNDECODABLE", "NO_ROLL_NO", "NO_QTY"].includes(err.code) && (
                  <button type="button" onClick={() => setShowManual(true)} data-testid="scan-label-error-manual-btn"
                    className="rounded-md bg-amber-500 px-2 py-1 text-[10.5px] font-semibold text-white">Isi dari label fisik</button>
                )}
                <button type="button" onClick={() => setErr(null)} data-testid="scan-label-error-dismiss"
                  className="rounded-md border border-red-300 px-2 py-1 text-[10.5px] font-semibold">Tutup</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Daftar roll hasil scan */}
      <div className="overflow-hidden rounded-lg border border-[#EFF0F2]">
        <div className="flex items-center justify-between bg-[#FAFBFC] px-2.5 py-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Roll hasil scan ({rolls.length})</span>
          <div className="flex items-center gap-1.5">
            {!closed && untagged.length > 0 && (
              <button type="button" onClick={tagAll} disabled={busy} data-testid="scan-label-tag-all"
                className="inline-flex items-center gap-1 rounded-md bg-[#1B7F4B] px-2 py-0.5 text-[10px] font-semibold text-white disabled:opacity-50">
                <Radio size={10} /> Tag RFID {untagged.length} roll
              </button>
            )}
            <span className="text-[9.5px] text-[#8E8E93]">hanya kolom aktual & grade yang bisa diubah</span>
          </div>
        </div>
        {rolls.length > 0 && (
          <div className="border-b border-[#EFF0F2] px-2.5 pb-1.5">
            <RollLabelActions rolls={labelRolls} ctx={{ product_name: meta.product_name || task.product_name, po_number: task.po_number, warehouse_id: task.warehouse_id }}
              source={`inbound_scan:${task.id}`} testPrefix="scan-label-print" compact />
          </div>
        )}
        {rolls.length === 0 ? (
          <p className="py-6 text-center text-[11px] text-[#8E8E93]">Belum ada roll. Scan label supplier untuk mulai.</p>
        ) : (
          <div className="divide-y divide-[#EFF0F2]">
            {rolls.map((r) => (
              <ScannedRollRow key={r.id} roll={r} taskUnit={task.unit} bins={meta.bins || []}
                tolerance={meta.tolerance_pct} readOnly={closed} highlight={lastOk?.id === r.id}
                productName={meta.product_name || task.product_name}
                onChanged={onRollChanged} onRemoved={onRollRemoved} />
            ))}
          </div>
        )}
      </div>

      {showManual && (
        <UnreadableLabelModal task={task} supplierId={meta.supplier_id} busy={busy}
          onClose={() => setShowManual(false)} onSubmit={submitManual} />
      )}
    </div>
  );
}
