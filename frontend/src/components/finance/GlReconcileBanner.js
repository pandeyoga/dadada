import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, RefreshCw } from "lucide-react";

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
  if (!d) return null;
  const bad = d.checks.filter((c) => !c.ok);
  const ok = d.ok;
  return (
    <div data-testid="gl-reconcile-banner" data-state={ok ? "ok" : "mismatch"}
      className={`rounded-lg border p-3 text-sm ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-300 bg-rose-50 text-rose-900"}`}>
      <div className="flex flex-wrap items-center gap-2">
        {ok ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertTriangle className="h-4 w-4 text-rose-600" />}
        <span className="font-medium">
          {ok ? "Subledger AR/AP sama dengan buku besar." : `${bad.length} akun kendali SELISIH dengan subledger — angka laporan tidak bisa dipercaya sebelum dibetulkan.`}
        </span>
        {d.events_failed ? <span className="rounded bg-rose-200 px-1.5 text-xs">{d.events_failed} jurnal otomatis GAGAL diposting</span> : null}
        {d.events_pending ? <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-900">{d.events_pending} jurnal menunggu diposting</span> : null}
        <span className="ml-auto flex items-center gap-1">
          <Button size="sm" variant="ghost" data-testid="gl-reconcile-toggle" onClick={() => setOpenList((v) => !v)}>
            Rincian <ChevronDown className={`h-3.5 w-3.5 transition-transform ${openList ? "rotate-180" : ""}`} />
          </Button>
          <Button size="sm" variant="ghost" data-testid="gl-reconcile-refresh" onClick={load}><RefreshCw className="h-3.5 w-3.5" /></Button>
        </span>
      </div>
      {openList ? (
        <ul className="mt-2 grid gap-1 md:grid-cols-2">
          {d.checks.map((c) => (
            <li key={c.code} data-testid={`gl-reconcile-row-${c.code}`} data-ok={c.ok}
              className={`flex items-start justify-between gap-2 rounded border bg-white/70 px-2 py-1 text-xs ${c.ok ? "border-emerald-100" : "border-rose-300"}`}>
              <span>
                <span className="font-mono font-semibold">{c.code}</span> · {c.label}
                {!c.ok ? <span className="block text-rose-700">{c.hint}</span> : null}
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
