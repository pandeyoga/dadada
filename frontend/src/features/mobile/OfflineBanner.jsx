import { useEffect, useState } from "react";
import { WifiOff, RefreshCw, CheckCircle2, XCircle, CloudUpload } from "lucide-react";
import { pending, results, subscribe, syncQueue, clearResults } from "../../utils/offlineQueue";

/** Banner status offline/antrean di HP: jumlah aksi menunggu, tombol sinkron, hasil sinkron terakhir. */
export default function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);
  const [q, setQ] = useState(pending());
  const [rs, setRs] = useState(results());
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const refresh = () => { setQ(pending()); setRs(results()); };
    const un = subscribe(refresh);
    const on = () => { setOnline(true); refresh(); }; const off = () => setOnline(false);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    if (navigator.onLine && pending().length) syncQueue();
    return () => { un(); window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  const sync = async () => { setBusy(true); try { await syncQueue(); } finally { setBusy(false); } };
  if (online && !q.length && !rs.length) return null;
  return (
    <div className={`mx-3 mt-2 rounded-xl border p-3 text-sm ${online ? "border-[#0058CC]/30 bg-[#EAF2FF]" : "border-[#B23B14]/40 bg-[#FDECEC]"}`} data-testid="mw-offline-banner">
      <div className="flex items-center gap-2 font-semibold">
        {online ? <CloudUpload size={16} /> : <WifiOff size={16} />}
        <span data-testid="mw-offline-status">{online ? (q.length ? `${q.length} aksi menunggu sinkron` : "Sinkron selesai") : `Offline · ${q.length} aksi tersimpan di HP`}</span>
        {online && q.length > 0 && <button className="ml-auto secondary-button px-3 py-1 text-xs" disabled={busy} onClick={sync} data-testid="mw-offline-sync"><RefreshCw size={12} className={busy ? "animate-spin" : ""} /> Sinkron</button>}
        {!q.length && rs.length > 0 && <button className="ml-auto text-xs underline" onClick={clearResults} data-testid="mw-offline-clear">Tutup</button>}
      </div>
      {!online && <p className="mt-1 text-xs text-[#3C3C43]">Aksi & pindai tetap bisa dilakukan; akan dikirim otomatis saat sinyal kembali, tanpa dobel.</p>}
      {rs.length > 0 && (
        <ul className="mt-2 space-y-1" data-testid="mw-offline-results">
          {rs.slice(0, 5).map((r) => (
            <li key={r.key + r.at} className="flex items-start gap-1.5 text-xs" data-testid={`mw-offline-result-${r.ok ? "ok" : "fail"}`}>
              {r.ok ? <CheckCircle2 size={13} className="text-[#1B7F4B] mt-0.5" /> : <XCircle size={13} className="text-[#B23B14] mt-0.5" />}
              <span><b>{r.label}</b> — {r.ok ? (r.replay ? "sudah tercatat sebelumnya (tidak dobel)" : "berhasil") : `ditolak (${r.status}): ${r.detail}`}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
