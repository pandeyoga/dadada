import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, RefreshCw } from "lucide-react";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";

/** Lampu tie-out subledger ↔ buku besar: merah bila ada akun kendali yang selisih. */
export default function GlReconcileBanner() {
  const [d, setD] = useState(null);
  const [openList, setOpenList] = useState(false);
  const load = useCallback(async () => {
    try { setD((await api.get("/finance/reconcile")).data.data); } catch { setD(null); }
  }, []);
  useEffect(() => { load(); }, [load]);
  // GL-09: proses ulang event pembukuan yang gagal (hanya peran berizin; server menolak selain itu).
  const retryFailed = async () => {
    try {
      const r = (await api.post("/finance/events/retry-failed")).data;
      toast[r.still_failed ? "warning" : "success"](r.still_failed
        ? `${r.still_failed} dari ${r.total} jurnal masih gagal — periksa alasannya di Rincian.`
        : `${r.total} jurnal otomatis berhasil diposting ulang.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal memproses ulang jurnal.");
    }
    load();
  };
  if (!d) return null;
  const bad = d.checks.filter((c) => !c.ok && !c.indicator);   // `indicator` = peringatan, tidak menggagalkan lampu
  const ok = d.ok;
  return (
    <div data-testid="gl-reconcile-banner" data-state={ok ? "ok" : "mismatch"}
      className={`rounded-lg border p-3 text-sm ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-300 bg-rose-50 text-rose-900"}`}>
      <div className="flex flex-wrap items-center gap-2">
        {ok ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertTriangle className="h-4 w-4 text-rose-600" />}
        <span className="font-medium">
          {ok ? "Subledger AR/AP sama dengan buku besar." : `${bad.length} akun kendali SELISIH dengan subledger — angka laporan tidak bisa dipercaya sebelum dibetulkan.`}
        </span>
        {d.indicators_off ? <span data-testid="gl-reconcile-indicators" className="rounded bg-amber-100 px-1.5 text-xs text-amber-900">{d.indicators_off} indikator menyimpang (peringatan) — lihat Rincian</span> : null}
        {d.events_failed ? <span className="rounded bg-rose-200 px-1.5 text-xs">{d.events_failed} jurnal otomatis GAGAL diposting</span> : null}
        {d.events_failed && d.can_retry_events ? (
          <Button size="sm" variant="outline" data-testid="gl-reconcile-retry" onClick={retryFailed}>Proses ulang</Button>
        ) : null}
        {d.events_retrying ? <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-900">{d.events_retrying} jurnal dicoba ulang otomatis</span> : null}
        {d.events_pending ? <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-900">{d.events_pending} jurnal menunggu diposting</span> : null}
        <span className="ml-auto flex items-center gap-1">
          <Button size="sm" variant="ghost" data-testid="gl-reconcile-toggle" onClick={() => setOpenList((v) => !v)}>
            Rincian <ChevronDown className={`h-3.5 w-3.5 transition-transform ${openList ? "rotate-180" : ""}`} />
          </Button>
          <Button size="sm" variant="ghost" data-testid="gl-reconcile-refresh" onClick={load}><RefreshCw className="h-3.5 w-3.5" /></Button>
        </span>
      </div>
      {openList && (d.failed_events || []).length ? (
        <ul className="mt-2 space-y-1" data-testid="gl-failed-events">
          {d.failed_events.map((ev) => (
            <li key={ev.id} className="rounded border border-rose-300 bg-white/70 px-2 py-1 text-xs">
              <span className="font-mono font-semibold">{ev.type}</span> · {ev.last_error || "gagal"}
            </li>
          ))}
        </ul>
      ) : null}
      {openList ? (
        <ul className="mt-2 grid gap-1 md:grid-cols-2">
          {d.checks.map((c) => (
            <li key={c.code} data-testid={`gl-reconcile-row-${c.code}`} data-ok={c.ok}
              className={`flex items-start justify-between gap-2 rounded border bg-white/70 px-2 py-1 text-xs ${c.ok ? "border-emerald-100" : c.indicator ? "border-amber-300" : "border-rose-300"}`}>
              <span>
                <span className="font-mono font-semibold">{c.code}</span> · {c.label}
                {!c.ok ? <span className={`block ${c.indicator ? "text-amber-800" : "text-rose-700"}`}>{c.indicator ? "Indikator (tidak menggagalkan lampu): " : ""}{c.hint}</span> : null}
              </span>
              <span className="whitespace-nowrap text-right tabular-nums">
                GL {formatIDR(c.gl)}<br />sub {formatIDR(c.subledger)}
                {!c.ok ? <span className="block font-semibold text-rose-700">Δ {formatIDR(c.diff)}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
