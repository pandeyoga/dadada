import { useEffect, useState } from "react";
import { Clock, Trash2, RefreshCw } from "lucide-react";
import { pending, subscribe, syncQueue, removePending } from "../../../utils/offlineQueue";
import { askConfirm } from "../../../services/confirmService";

/** Aksi/pesanan yang masih antre di HP (belum terkirim) — bisa dibatalkan sebelum sinkron. */
export default function MobilePendingQueue() {
  const [q, setQ] = useState(pending());
  const [busy, setBusy] = useState(false);
  useEffect(() => subscribe(() => setQ(pending())), []);
  if (!q.length) return null;
  return (
    <div className="m-card p-3 space-y-2" data-testid="m-pending-queue">
      <div className="flex items-center gap-2 text-[12.5px] font-bold"><Clock size={14} className="text-[#B25E00]" /> {q.length} aksi menunggu dikirim
        <button className="ml-auto secondary-button px-2 py-1 text-[11px]" disabled={busy || !navigator.onLine} onClick={async () => { setBusy(true); try { await syncQueue(); } finally { setBusy(false); } }} data-testid="m-pending-sync"><RefreshCw size={11} className={busy ? "animate-spin" : ""} /> Kirim sekarang</button>
      </div>
      {q.map((it) => (
        <div key={it.key} className="flex items-center gap-2 rounded-lg border border-[#EFF0F2] p-2 text-[12px]" data-testid={`m-pending-${it.key}`}>
          <div className="flex-1 min-w-0"><b className="truncate block">{it.label || it.url}</b><span className="text-[10.5px] m-muted">disimpan {new Date(it.queued_at).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span></div>
          <button className="text-[#C0392B]" onClick={async () => { if (await askConfirm({ title: `Batalkan "${it.label || "aksi ini"}"?`, message: "Aksi tidak akan dikirim ke server.", danger: true })) removePending(it.key); }} data-testid={`m-pending-cancel-${it.key}`} aria-label="Batalkan"><Trash2 size={15} /></button>
        </div>
      ))}
    </div>
  );
}
