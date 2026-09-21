import { useEffect, useRef, useState } from "react";
import { ClipboardList, ScanLine, Tags, PackageCheck, AlertTriangle, CheckCircle2, Loader2, Scissors, Printer, Camera } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import MobileShell from "./MobileShell";
import { printSampleLabel, printInboundRollLabels, reprintRollLabel } from "./MobileTaskActions";
import { isNetworkError, queueScan } from "../../utils/offlineQueue";
import PrinterStatusWidget from "../../components/PrinterStatusWidget";
import OfflineBanner from "./OfflineBanner";
import { InboundActions, OutboundActions, SampleCutActions } from "./MobileTaskActions";

const STATUS_ID = { pending: "Menunggu", receiving: "Menerima", qc_check: "Cek QC", put_away: "Simpan", picking: "Ambil", packing: "Kemas", escalated: "Eskalasi", completed: "Selesai", shipped: "Terkirim" };

function TaskList({ type, focusTaskId, onFocused }) {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(focusTaskId || "");
  const [lastCut, setLastCut] = useState(null);
  const [lastInbound, setLastInbound] = useState(null);
  const [fromCache, setFromCache] = useState(false);
  const load = () => axios.get(`${API}/wms/tasks`).then((r) => { setFromCache(r.headers?.["x-from-cache"] === "true"); setRows((Array.isArray(r.data) ? r.data : r.data.items || r.data.tasks || []).filter((t) => (type === "sample_cut" ? t.task_subtype === "sample_cut" : ((t.flow_type || t.type) === type && t.task_subtype !== "sample_cut")) && !["completed", "shipped", "cancelled", "done", "dispatched"].includes(t.status))); })
    .catch((e) => setErr(e.response?.data?.detail || "Gagal memuat tugas."));
  useEffect(() => { load(); }, [type]); // eslint-disable-line
  // Pindai → aksi: kartu tugas hasil pindai dibuka & digulir ke layar, lalu fokus dilepas.
  useEffect(() => {
    if (!focusTaskId || rows === null) return;
    setOpen(focusTaskId);
    document.querySelector(`[data-testid="mw-task-${focusTaskId}"]`)?.scrollIntoView({ block: "center" });
    onFocused?.();
  }, [focusTaskId, rows]); // eslint-disable-line
  if (err) return <div className="notice-bar danger m-4" data-testid="mw-task-error">{String(err)}</div>;
  if (rows === null) return <div className="p-6 text-center text-sm"><Loader2 className="animate-spin inline" size={16} /> Memuat…</div>;
  const label = { inbound: "barang masuk", outbound: "barang keluar", sample_cut: "potong sampel" }[type] || type;
  if (!rows.length) return <div className="p-8 text-center text-sm text-[#6E6E73]" data-testid="mw-task-empty">Tidak ada tugas {label} yang terbuka.</div>;
  const Actions = { inbound: InboundActions, outbound: OutboundActions, sample_cut: SampleCutActions }[type];
  return (
    <div className="space-y-2 p-3" data-testid={`mw-task-list-${type}`}>
      {fromCache && <div className="notice-bar warning text-xs" data-testid="mw-task-from-cache">Offline — menampilkan daftar tugas terakhir yang tersimpan di HP. Aksi akan diantrekan.</div>}
      {lastInbound && (
        <div className="m-card p-3 bg-[#E6F6EC] space-y-2" data-testid={`mw-inbound-done-${lastInbound.task.id}`}>
          <div className="notice-bar success" data-testid={`mw-action-msg-${lastInbound.task.id}`}>SELESAI · {lastInbound.task.product_name} · {lastInbound.rolls.length} roll baru masuk stok{lastInbound.rolls.length ? `: ${lastInbound.rolls.map((r) => r.roll_no).join(", ")}` : ""}</div>
          {lastInbound.rolls.length > 0 && <button className="primary-button w-full py-3 flex items-center justify-center gap-2" onClick={() => printInboundRollLabels(lastInbound.task, lastInbound.rolls)} data-testid={`mw-inbound-print-${lastInbound.task.id}`}><Printer size={16} /> Cetak label {lastInbound.rolls.length} roll</button>}
          <button className="secondary-button w-full py-2" onClick={() => setLastInbound(null)} data-testid={`mw-inbound-done-close-${lastInbound.task.id}`}>Tutup</button>
        </div>
      )}
      {lastCut && (
        <div className="m-card p-3 bg-[#E6F6EC] space-y-2" data-testid={`mw-sample-done-${lastCut.taskId}`}>
          <div className="notice-bar success" data-testid={`mw-action-msg-${lastCut.taskId}`}>DIPOTONG · {lastCut.res.cut_roll_no} → <b>{lastCut.res.child_roll_no}</b> · {lastCut.res.length} {lastCut.res.unit} · {lastCut.res.sales_order_number} — lanjut Berangkatkan di kartu tugas</div>
          <button className="primary-button w-full py-3 flex items-center justify-center gap-2" onClick={() => printSampleLabel(lastCut.res)} data-testid={`mw-sample-print-${lastCut.taskId}`}><Printer size={16} /> Cetak label potongan</button>
          <button className="secondary-button w-full py-2" onClick={() => setLastCut(null)} data-testid={`mw-sample-done-close-${lastCut.taskId}`}>Tutup</button>
        </div>
      )}
      {rows.map((t) => (
        <div key={t.id} className={`m-card p-3 ${focusTaskId === t.id ? "ring-2 ring-[#0058CC]" : ""}`} data-testid={`mw-task-${t.id}`} onClick={() => setOpen(open === t.id ? "" : t.id)}>
          <div className="flex items-center justify-between"><b className="text-[15px]">{t.product_name || t.product_id}</b>
            <span className={`status-pill ${t.status === "escalated" ? "pill-danger" : "pill-warning"}`}>{STATUS_ID[t.status] || t.status}</span></div>
          <div className="text-xs text-[#6E6E73] mt-1">{t.warehouse_name || t.warehouse_id} · qty <b className="tabular-nums">{t.quantity}</b> {t.unit || ""}{t.order_number ? ` · ${t.order_number}` : ""}{t.po_number ? ` · ${t.po_number}` : ""}{t.task_subtype === "sample_cut" ? " · SAMPEL" : ""}</div>
          {open === t.id && Actions && <div onClick={(e) => e.stopPropagation()}><Actions task={t} onDone={load} onCut={(res) => { setLastCut({ taskId: t.id, res }); load(); }} onCompleted={(res) => { setLastInbound(res); load(); }} /></div>}
        </div>
      ))}
    </div>
  );
}

function ScanPanel({ onOpenTask }) {
  const [epc, setEpc] = useState("");
  const [res, setRes] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [busy, setBusy] = useState(false);
  const [cam, setCam] = useState(false);
  const [myBin, setMyBin] = useState(() => localStorage.getItem("kn_my_bin") || "");
  const setBin = (v) => { setMyBin(v); localStorage.setItem("kn_my_bin", v); };
  const videoRef = useRef(null);
  const canCamera = typeof window !== "undefined" && "BarcodeDetector" in window && !!navigator.mediaDevices;
  const fmtScan = (s) => s ? `${new Date(s.at).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })} · ${s.by || "-"}${s.warehouse_id ? ` · ${s.warehouse_id}` : ""}${s.bin_id ? ` · bin ${s.bin_id}` : ""}` : "";
  const lookup = async (code) => {
    if (!code.trim()) return;
    setBusy(true); setRes(null); setTasks([]);
    try {
      const { data } = await axios.get(`${API}/rfid/lookup`, { params: { code: code.trim(), bin_id: myBin || undefined } });
      const r = data.roll || {};
      const held = ["reserved", "committed", "picked", "packed"].includes(r.status);
      setRes({ kind: held ? "warn" : "ok", title: held ? "TERIKAT PESANAN" : "COCOK", roll: r, productName: data.product_name, lastScan: data.last_scan,
        text: `${r.roll_no} · ${data.product_name || r.product_id || ""} · status ${r.status || "-"} · ${r.warehouse_id || ""} · sisa ${r.length_remaining ?? "-"} ${r.unit || ""} · ${data.via === "rfid" ? "via tag RFID" : "via label QR"}${data.tagged ? "" : " · roll belum bertag"}` });
      // Pindai → aksi: tugas terbuka yang menyentuh roll ini (dari backend) langsung ditawarkan.
      setTasks(data.open_tasks || []);
    } catch (e) {
      if (isNetworkError(e)) {
        // Offline: jejak pindai disimpan di HP, dikirim saat online. Data roll tak bisa ditampilkan tanpa server.
        queueScan(code.trim(), { bin_id: myBin || undefined });
        setRes({ kind: "warn", title: "OFFLINE — PINDAI TERSIMPAN", text: `${code.trim()} akan tercatat saat sinyal kembali${myBin ? ` (bin ${myBin})` : ""}. Data roll tidak bisa ditampilkan saat offline.` });
      } else { const d = e.response?.data?.detail; setRes({ kind: "bad", title: e.response?.status === 404 ? "KODE TIDAK DIKENAL" : "GAGAL", text: (d && (d.message || d)) || "Pindai gagal, coba lagi." }); }
    }
    finally { setBusy(false); }
  };
  const reprint = () => res?.roll && reprintRollLabel(res.roll, res.productName);
  const TAB_OF = { inbound: "inbound", outbound: "outbound", sample_cut: "sample" };
  const LABEL_OF = { inbound: "Terima", outbound: "Ambil", sample_cut: "Potong" };
  // Kamera HP → BarcodeDetector (QR label berisi nomor roll). Fallback: ketik / pemindai fisik.
  useEffect(() => {
    if (!cam || !canCamera) return undefined;
    let stream; let timer; let stop = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
        const det = new window.BarcodeDetector({ formats: ["qr_code", "code_128"] });
        const tick = async () => {
          if (stop) return;
          try { const codes = await det.detect(videoRef.current); if (codes.length) { const v = codes[0].rawValue; setEpc(v); setCam(false); lookup(v); return; } } catch (_) { /* frame belum siap */ }
          timer = setTimeout(tick, 350);
        };
        tick();
      } catch (_) { setCam(false); setRes({ kind: "bad", title: "KAMERA TIDAK TERSEDIA", text: "Izinkan kamera atau ketik nomor roll / EPC." }); }
    })();
    return () => { stop = true; clearTimeout(timer); if (stream) stream.getTracks().forEach((t) => t.stop()); };
  }, [cam]); // eslint-disable-line
  const Icon = res?.kind === "ok" ? CheckCircle2 : AlertTriangle;
  return (
    <div className="p-4 space-y-3" data-testid="mw-scan">
      <p className="text-sm text-[#6E6E73]">Pindai QR label (nomor roll) atau tag EPC. Hasil ditampilkan besar: ikon + teks, bukan warna saja.</p>
      <input className="w-full rounded-xl border-2 border-[#E5E5EA] p-4 text-lg" placeholder="Nomor roll / EPC tag…" value={epc} onChange={(e) => setEpc(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") lookup(epc); }} data-testid="mw-scan-input" autoFocus />
      <input className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Bin / lokasi saya (opsional, diingat di HP)" value={myBin} onChange={(e) => setBin(e.target.value)} data-testid="mw-scan-bin" />
      <div className="flex gap-2">
        <button className="primary-button flex-1 py-4 text-lg" disabled={busy} onClick={() => lookup(epc)} data-testid="mw-scan-btn">{busy ? "Mencari…" : "Pindai"}</button>
        {canCamera && <button className="secondary-button px-4" onClick={() => setCam((c) => !c)} data-testid="mw-scan-camera-btn" aria-label="Kamera"><Camera size={20} /></button>}
      </div>
      {cam && <video ref={videoRef} className="w-full rounded-xl bg-black" muted playsInline data-testid="mw-scan-video" />}
      {res && (
        <div className={`rounded-2xl p-5 text-center ${res.kind === "ok" ? "bg-[#E6F6EC]" : res.kind === "warn" ? "bg-[#FFF4E5]" : "bg-[#FDECEC]"}`} data-testid={`mw-scan-result-${res.kind}`}>
          <Icon size={44} className="mx-auto" />
          <div className="text-xl font-bold mt-2">{res.title}</div>
          <div className="text-sm mt-1">{res.text}</div>
          {res.roll && (
            <div className="mt-3 space-y-2 text-left">
              <div className="text-xs text-[#3C3C43]" data-testid="mw-scan-last">Pindai ini tercatat{myBin ? ` di bin ${myBin}` : ""}. Terakhir sebelumnya: <b>{res.lastScan ? fmtScan(res.lastScan) : "belum pernah"}</b></div>
              <button className="secondary-button w-full py-3 flex items-center justify-center gap-2" onClick={reprint} data-testid="mw-scan-reprint"><Printer size={16} /> Cetak ulang label QR</button>
              {tasks.length > 0 && <div className="text-xs font-semibold text-[#3C3C43]" data-testid="mw-scan-tasks">Tugas terbuka untuk roll ini:</div>}
              {tasks.map((t) => (
                <button key={t.id} className="primary-button w-full py-3 flex items-center justify-between px-3" onClick={() => onOpenTask?.(t.task_subtype === "sample_cut" ? "sample" : (TAB_OF[t.flow_type] || "inbound"), t.id)} data-testid={`mw-scan-task-${t.id}`}>
                  <span>{t.task_subtype === "sample_cut" ? "Potong" : (LABEL_OF[t.flow_type] || t.flow_type)} · {t.product_name || t.product_id}{t.task_subtype === "sample_cut" && t.customer_name ? ` · ${t.customer_name}` : ""}</span><span className="text-xs opacity-80">{t.order_number || t.po_number || STATUS_ID[t.status] || t.status}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="pt-2" data-testid="mw-printer-status"><div className="text-xs font-semibold text-[#3C3C43] mb-1">Printer label gudang</div><PrinterStatusWidget compact /></div>
    </div>
  );
}

function UntaggedPanel() {
  const [rows, setRows] = useState(null);
  useEffect(() => { axios.get(`${API}/rfid/untagged-rolls`).then((r) => setRows(Array.isArray(r.data) ? r.data : r.data.rolls || r.data.items || [])).catch(() => setRows([])); }, []);
  if (rows === null) return <div className="p-6 text-center text-sm">Memuat…</div>;
  if (!rows.length) return <div className="p-8 text-center text-sm text-[#6E6E73]" data-testid="mw-untagged-empty">Semua roll sudah bertag.</div>;
  return (
    <div className="space-y-2 p-3" data-testid="mw-untagged-list">
      <div className="text-xs text-[#6E6E73] px-1">{rows.length} roll belum bertag (termasuk potongan baru — P-1).</div>
      {rows.map((r) => (
        <div key={r.id} className="m-card p-3 flex items-center justify-between" data-testid={`mw-untagged-${r.id}`}>
          <div><b>{r.roll_no}</b><div className="text-xs text-[#6E6E73]">{r.product_name || r.product_id} · {r.warehouse_id} · sisa {r.length_remaining} {r.unit || ""}</div></div>
          <Tags size={18} />
        </div>
      ))}
    </div>
  );
}

export default function MobileWarehouseApp(props) {
  const [focus, setFocus] = useState(null);
  const list = (type) => <TaskList type={type} focusTaskId={focus?.type === type ? focus.taskId : ""} onFocused={() => setFocus(null)} />;
  const tabs = [
    { id: "inbound", label: "Masuk", icon: PackageCheck, render: () => list("inbound") },
    { id: "outbound", label: "Keluar", icon: ClipboardList, render: () => list("outbound") },
    { id: "sample", label: "Sampel", icon: Scissors, render: () => list("sample_cut") },
    { id: "scan", label: "Pindai", icon: ScanLine, render: ({ setTab }) => <ScanPanel onOpenTask={(tab, taskId) => { setFocus({ type: { inbound: "inbound", outbound: "outbound", sample: "sample_cut" }[tab], taskId }); setTab(tab); }} /> },
    { id: "untagged", label: "Belum Tag", icon: Tags, render: () => <UntaggedPanel /> },
  ];
  return <MobileShell {...props} tabs={tabs} testId="mobile-warehouse-app" topSlot={<OfflineBanner />} />;
}
