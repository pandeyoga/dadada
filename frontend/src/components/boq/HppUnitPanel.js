import React, { useCallback, useEffect, useState } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/patterns/MetricCard";
import { LoadingCards } from "@/components/patterns/StateViews";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";

/** HPP RAB per unit vs biaya yang dikontrakkan / terverifikasi / ditagih (WIP terealisasi) + saldo akrual HPP. */
export default function HppUnitPanel({ projectId, reloadKey }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const load = useCallback(async () => {
    if (!projectId) return;
    try { setD((await api.get(`/finance/hpp-unit?project_id=${projectId}`)).data.data); setErr(""); }
    catch (e) { setErr(e?.response?.data?.detail || "Gagal memuat HPP per unit."); }
  }, [projectId]);
  useEffect(() => { load(); }, [load, reloadKey]);
  if (err) return <p className="text-sm text-rose-700">{err}</p>;
  if (!d) return <LoadingCards count={4} />;
  const t = d.totals || {};
  return (
    <div data-testid="hpp-unit-panel" className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <MetricCard label="HPP RAB (Σ unit)" value={t.hpp} format="idr" />
        <MetricCard label="Dikontrakkan (SPK unit)" value={t.contracted} format="idr" tone={d.units_over_rab ? "rose" : undefined}
          hint={d.units_over_rab ? `${d.units_over_rab} unit melebihi RAB` : "dalam RAB"} />
        <MetricCard label="Terverifikasi" value={t.verified} format="idr" />
        <MetricCard label="Ditagih (WIP terealisasi)" value={t.billed} format="idr" tone="amber" hint={`sisa RAB ${formatIDR(t.variance)}`} />
        <MetricCard label="Saldo WIP 1-1600 (GL)" value={d.gl_wip} format="idr" hint="seluruh organisasi" />
        <MetricCard label="Akrual HPP 2-1700 (GL)" value={d.gl_accrual} format="idr" tone={d.gl_accrual ? "amber" : undefined}
          hint={d.gl_accrual ? "HPP diakui saat BAST > WIP — akan dilunasi tagihan berikutnya" : "tidak ada akrual"} />
      </div>
      <p className="text-xs text-muted-foreground" data-testid="hpp-unit-note">
        Biaya proyek yang tidak melekat pada unit (SPK borongan tanpa lingkup, PO material, fasum): {formatIDR(d.project_ap_unallocated)} dari {formatIDR(d.project_ap_total)} tagihan AP proyek. {d.note}
      </p>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Unit</TableHead><TableHead>Tipe</TableHead>
              <TableHead className="text-right">HPP RAB</TableHead>
              <TableHead className="text-right">Dikontrakkan</TableHead>
              <TableHead className="text-right">Terverifikasi</TableHead>
              <TableHead className="text-right">Ditagih</TableHead>
              <TableHead className="text-right">Sisa RAB</TableHead>
              <TableHead className="text-right">Realisasi</TableHead>
              <TableHead>BAST / HPP diakui</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {d.rows.map((r) => (
              <TableRow key={r.unit_id} data-testid={`hpp-unit-row-${r.unit_code}`}>
                <TableCell className="font-medium">{r.unit_code}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{r.unit_type_code || r.type || "-"}</TableCell>
                <TableCell className="text-right tabular-nums">{formatIDR(r.hpp)}</TableCell>
                <TableCell className={`text-right tabular-nums ${r.over_rab ? "font-semibold text-rose-700" : ""}`}>{formatIDR(r.contracted)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatIDR(r.verified)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatIDR(r.billed)}</TableCell>
                <TableCell className={`text-right tabular-nums ${r.variance < 0 ? "text-rose-700" : ""}`}>{formatIDR(r.variance)}</TableCell>
                <TableCell className="text-right tabular-nums">{r.realized_pct == null ? "-" : `${r.realized_pct}%`}</TableCell>
                <TableCell>
                  {r.recognized
                    ? <Badge variant="outline" className="text-xs">HPP {formatIDR(r.recognized_cogs)} · {r.cogs_source === "rab" ? "dari RAB" : r.cogs_source === "manual" ? "manual" : "estimasi 70%"}</Badge>
                    : <span className="text-xs text-muted-foreground">belum BAST</span>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
