import { useState } from "react";
import { Loader2, Printer } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { printSampleLabel, printInboundRollLabels, reprintRollLabel } from "../../utils/rollLabels";
import { offlinePost } from "../../utils/offlineQueue";

export { printSampleLabel, printInboundRollLabels, reprintRollLabel };

const errText = (e, fb) => { const d = e.response?.data?.detail; return (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || fb; };

/** Tombol cetak ulang label QR untuk roll yang sudah terikat ke tugas (label rusak/hilang). */
export function ReprintRollButton({ task }) {
  const [busy, setBusy] = useState(false);
  if (!task?.roll_id) return null;
  const go = async (e) => {
    e.stopPropagation(); setBusy(true);
    try { const { data } = await axios.get(`${API}/rfid/lookup`, { params: { code: task.roll_id } }); if (data?.roll) await reprintRollLabel(data.roll, data.product_name || task.product_name); }
    catch (_) { /* roll belum ada / tidak ditemukan */ } finally { setBusy(false); }
  };
  return <button className="secondary-button w-full py-2 flex items-center justify-center gap-2" disabled={busy} onClick={go} data-testid={`mw-reprint-${task.id}`}><Printer size={14} /> Cetak ulang label QR roll</button>;
}

/** Aksi tugas gudang di mobile (Tahap 2): satu tombol besar per langkah, hasil = ikon + teks. */

export function InboundActions({ task, onDone, onCompleted }) {
  const [qty, setQty] = useState(String(task.expected_qty ?? task.quantity ?? ""));
  const [lot, setLot] = useState(""); const [dye, setDye] = useState("");
  const [msg, setMsg] = useState(null); const [busy, setBusy] = useState(false);
  const run = async (fn, ok) => { setBusy(true); setMsg(null); try { const r = await fn(); setMsg(r?.queued ? { ok: true, text: "Offline — tersimpan di HP, akan dikirim saat sinyal kembali (tanpa dobel)." } : { ok: true, text: ok }); if (!r?.queued) onDone?.(); } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal.") }); } finally { setBusy(false); } };
  const receive = () => run(() => offlinePost(`${API}/inbound/tasks/${task.id}/scan-receive`, { product_id: task.product_id, actual_qty: parseFloat(qty) || 0 }, { label: `Terima ${task.product_name || task.id} ${qty}` }), "Diterima. Lanjut Selesai bila semua sudah dihitung.");
  const complete = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await offlinePost(`${API}/inbound/tasks/${task.id}/complete`, { supplier_lot: lot, dye_lot: dye }, { label: `Selesai barang masuk ${task.product_name || task.id}` });
      if (r.queued) { setMsg({ ok: true, text: "Offline — penyelesaian tersimpan di HP; label roll bisa dicetak setelah sinkron." }); return; }
      // Hasil + tombol cetak label diangkat ke induk (bertahan setelah kartu hilang dari daftar).
      onCompleted?.({ task, rolls: r.data.created_rolls || [] });
    } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal.") }); } finally { setBusy(false); }
  };
  return (
    <div className="mt-2 space-y-2" data-testid={`mw-inbound-actions-${task.id}`}>
      {["pending", "receiving", "in_progress"].includes(task.status) && (
        <div className="flex gap-2">
          <input type="number" className="flex-1 rounded-lg border p-3 text-lg" value={qty} onChange={(e) => setQty(e.target.value)} data-testid={`mw-receive-qty-${task.id}`} />
          <button className="primary-button px-4" disabled={busy} onClick={receive} data-testid={`mw-receive-btn-${task.id}`}>Terima</button>
        </div>
      )}
      {["receiving", "qc_check", "in_progress"].includes(task.status) && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input className="rounded-lg border p-2" placeholder="Lot supplier" value={lot} onChange={(e) => setLot(e.target.value)} data-testid={`mw-lot-${task.id}`} />
            <input className="rounded-lg border p-2" placeholder="Dye lot" value={dye} onChange={(e) => setDye(e.target.value)} data-testid={`mw-dye-${task.id}`} />
          </div>
          <button className="secondary-button w-full py-3" disabled={busy} onClick={complete} data-testid={`mw-complete-btn-${task.id}`}>{busy ? <Loader2 size={14} className="animate-spin inline" /> : null} Selesai (masuk stok)</button>
        </div>
      )}
      <ReprintRollButton task={task} />
      {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"}`} data-testid={`mw-action-msg-${task.id}`}>{msg.text}</div>}
    </div>
  );
}

export function OutboundActions({ task, onDone }) {
  const [qty, setQty] = useState(String(task.quantity ?? ""));
  const [msg, setMsg] = useState(null); const [busy, setBusy] = useState(false);
  const run = async (fn, ok) => { setBusy(true); setMsg(null); try { const r = await fn(); setMsg(r?.queued ? { ok: true, text: "Offline — tersimpan di HP, akan dikirim saat sinyal kembali (tanpa dobel)." } : { ok: true, text: ok }); if (!r?.queued) onDone?.(); } catch (e) { setMsg({ ok: false, text: errText(e, "Gagal.") }); } finally { setBusy(false); } };
  const pick = () => run(() => offlinePost(`${API}/outbound/tasks/${task.id}/scan-pick`, null, { params: { actual_qty: parseFloat(qty) || 0 }, label: `Ambil ${task.product_name || task.id} ${qty}` }), "Diambil. Lanjut Berangkatkan bila sudah dikemas.");
  const dispatch = () => run(() => offlinePost(`${API}/outbound/tasks/${task.id}/dispatch`, null, { label: `Berangkatkan ${task.order_number || task.id}` }), "Diberangkatkan — surat jalan dibuat.");
  return (
    <div className="mt-2 space-y-2" data-testid={`mw-outbound-actions-${task.id}`}>
      {["pending", "created", "picking", "in_progress", "released"].includes(task.status) && (
        <div className="flex gap-2">
          <input type="number" className="flex-1 rounded-lg border p-3 text-lg" value={qty} onChange={(e) => setQty(e.target.value)} data-testid={`mw-pick-qty-${task.id}`} />
          <button className="primary-button px-4" disabled={busy} onClick={pick} data-testid={`mw-pick-btn-${task.id}`}>Ambil</button>
        </div>
      )}
      {["picked", "packing", "packed", "ready"].includes(task.status) && (
        <button className="secondary-button w-full py-3" disabled={busy} onClick={dispatch} data-testid={`mw-dispatch-btn-${task.id}`}>Berangkatkan</button>
      )}
      <ReprintRollButton task={task} />
      {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"}`} data-testid={`mw-action-msg-${task.id}`}>{msg.text}</div>}
    </div>
  );
}

export function SampleCutActions({ task, onCut, onDone }) {
  const [epc, setEpc] = useState(""); const [reason, setReason] = useState(""); const [length, setLength] = useState(String(task.quantity ?? ""));
  const [msg, setMsg] = useState(null); const [busy, setBusy] = useState(false);
  // Sudah dipotong (picked_qty > 0) → sisa langkahnya identik barang keluar (berangkatkan).
  if (Number(task.picked_qty || 0) > 0 || !["pending", "created", "picking"].includes(task.status)) {
    return (
      <div className="mt-2 space-y-2" data-testid={`mw-sample-actions-${task.id}`}>
        <div className="text-xs text-[#126E2C] font-semibold">Dipotong dari {task.parent_roll_no} → {task.child_roll_no} · {task.picked_qty} {task.unit}</div>
        <OutboundActions task={task} onDone={onDone} />
      </div>
    );
  }
  const cut = async (useSuggested) => {
    setBusy(true); setMsg(null);
    try {
      const body = useSuggested ? { roll_id: task.suggested_roll_id, actual_length: parseFloat(length) || undefined } : { epc, actual_length: parseFloat(length) || undefined, reason };
      const r = await offlinePost(`${API}/outbound/tasks/${task.id}/cut-sample`, body, { label: `Potong sampel ${task.order_number || task.id}` });
      if (r.queued) { setMsg({ ok: true, text: "Offline — potongan tersimpan di HP; label bisa dicetak setelah sinkron." }); return; }
      // Hasil + tombol cetak diangkat ke induk (TaskList) supaya tetap tampil setelah kartu tugas hilang dari daftar.
      onCut?.(r.data.cut);
    } catch (e) { setMsg({ ok: false, text: errText(e, "Potong gagal.") }); } finally { setBusy(false); }
  };
  return (
    <div className="mt-2 space-y-2" data-testid={`mw-sample-actions-${task.id}`}>
      <div className="text-xs text-[#6E6E73]">Untuk {task.customer_name} · diminta {task.quantity} {task.unit} · saran FIFO: <b>{task.suggested_roll_no || "tidak ada"}</b></div>
      <label className="block text-xs">Panjang aktual dipotong ({task.unit})
        <input type="number" step="0.1" className="w-full rounded-lg border p-3 text-lg" value={length} onChange={(e) => setLength(e.target.value)} data-testid={`mw-sample-length-${task.id}`} /></label>
      {task.suggested_roll_id && <button className="primary-button w-full py-3" disabled={busy} onClick={() => cut(true)} data-testid={`mw-sample-cut-suggested-${task.id}`}>Potong roll saran ({task.suggested_roll_no})</button>}
      <div className="rounded-lg border p-2 space-y-2">
        <div className="text-xs">Roll lain (pindai EPC / QR atau ketik nomor roll) — wajib alasan bila bukan saran:</div>
        <input className="w-full rounded-lg border p-2" placeholder="EPC tag / nomor roll" value={epc} onChange={(e) => setEpc(e.target.value)} data-testid={`mw-sample-epc-${task.id}`} />
        <input className="w-full rounded-lg border p-2" placeholder="Alasan (mis. roll saran tidak ditemukan)" value={reason} onChange={(e) => setReason(e.target.value)} data-testid={`mw-sample-reason-${task.id}`} />
        <button className="secondary-button w-full py-2" disabled={busy || !epc} onClick={() => cut(false)} data-testid={`mw-sample-cut-other-${task.id}`}>Potong roll ini</button>
      </div>
      {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"}`} data-testid={`mw-action-msg-${task.id}`}>{msg.text}</div>}
    </div>
  );
}
