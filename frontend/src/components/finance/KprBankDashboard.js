import React, { useCallback, useEffect, useState } from "react";
import { Landmark, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import MoneyText from "@/components/patterns/MoneyText";
import { ErrorState, LoadingCards } from "@/components/patterns/StateViews";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";

const T = {
  panel: "kpr-bank-dashboard",
  totals: "kpr-bank-totals",
  bankRow: "kpr-bank-row",
  heldRow: "kpr-bank-held-row",
  noSchemeRow: "kpr-bank-noscheme-row",
  filter: "kpr-bank-filter",
  refresh: "kpr-bank-refresh",
};

const COND = { akad: "Akad kredit", serah_terima: "Serah terima", sertifikat: "Sertifikat" };

function BankCard({ b, active, onClick }) {
  const pct = b.plafon ? Math.round((b.disbursed / b.plafon) * 100) : 0;
  return (
    <button type="button" data-testid={T.bankRow} data-bank={b.bank} onClick={onClick}
      className={`rounded-xl border bg-card p-3 text-left shadow-[var(--shadow-card)] transition-colors hover:border-primary/60 ${active ? "border-primary bg-primary/5" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 font-medium"><Landmark className="h-4 w-4" /> {b.bank}</p>
        <span className="text-[11px] text-muted-foreground">{b.apps} pengajuan{b.done ? ` · ${b.done} lunas` : ""}</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[12px]">
        <span className="text-muted-foreground">Plafon</span><span className="text-right tabular-nums"><MoneyText value={b.plafon} /></span>
        <span className="text-muted-foreground">Sudah cair ({pct}%)</span><span className="text-right tabular-nums"><MoneyText value={b.disbursed} /></span>
        <span className="text-muted-foreground">Belum cair</span><span className="text-right font-semibold tabular-nums"><MoneyText value={b.outstanding} /></span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-secondary">
        <div className="h-full bg-primary" style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
        <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-amber-900">{b.ready} siap cair · {formatIDR(b.ready_amount)}</span>
        <span className="rounded-full bg-secondary px-2 py-0.5">{b.waiting} menunggu syarat · {formatIDR(b.waiting_amount)}</span>
        {b.no_scheme ? <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-rose-800">{b.no_scheme} tanpa skema</span> : null}
      </div>
    </button>
  );
}

/** Dashboard pencairan KPR per bank: plafon vs cair, tahap tertahan (siap cair vs menunggu syarat). */
export default function KprBankDashboard() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [bank, setBank] = useState("");
  const load = useCallback(() => {
    api.get("/kpr/disbursement-summary").then((r) => { setData(r.data.data); setErr(""); })
      .catch((e) => setErr(e?.response?.data?.detail || "Ringkasan pencairan KPR tidak dapat dimuat."));
  }, []);
  useEffect(() => { load(); }, [load]);

  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!data) return <LoadingCards count={3} />;
  const tot = data.totals || {};
  const held = (data.held || []).filter((h) => !bank || h.bank === bank);
  const noScheme = (data.no_scheme || []).filter((h) => !bank || h.bank === bank);

  return (
    <section data-testid={T.panel} className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="section-title">Pencairan KPR per bank</h3>
          <p className="text-[12px] text-muted-foreground">
            Tahap dari skema pencairan (Pusat Konfigurasi › Pencairan KPR). <b>Siap cair</b> = syarat tahap terpenuhi tetapi
            bank belum mencairkan — tagih bank. <b>Menunggu syarat</b> = retensi yang menanti serah terima / sertifikat.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {bank ? <Button data-testid={T.filter} size="sm" variant="outline" onClick={() => setBank("")}>Semua bank</Button> : null}
          <Button data-testid={T.refresh} size="sm" variant="ghost" onClick={load}><RefreshCw className="mr-1 h-3.5 w-3.5" /> Muat ulang</Button>
        </div>
      </div>

      <div data-testid={T.totals} className="grid gap-2 sm:grid-cols-5">
        {[["Plafon aktif", tot.plafon], ["Sudah cair", tot.disbursed], ["Belum cair", (tot.plafon || 0) - (tot.disbursed || 0)],
          [`Siap cair · ${tot.ready || 0} tahap`, tot.ready_amount], [`Menunggu syarat · ${tot.waiting || 0} tahap`, tot.waiting_amount]].map(([label, val]) => (
          <div key={label} className="rounded-lg border bg-secondary/40 px-2.5 py-1.5">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="font-semibold tabular-nums"><MoneyText value={val || 0} /></p>
          </div>
        ))}
      </div>

      {!(data.banks || []).length ? (
        <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">Belum ada pengajuan KPR dengan plafon SP3K.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.banks.map((b) => <BankCard key={b.bank} b={b} active={bank === b.bank} onClick={() => setBank(bank === b.bank ? "" : b.bank)} />)}
        </div>
      )}

      <div className="space-y-1.5">
        <p className="text-[13px] font-medium">Tahap tertahan{bank ? ` · ${bank}` : ""} ({held.length})</p>
        {!held.length ? (
          <p className="text-[12px] text-muted-foreground">Tidak ada tahap yang tertahan.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border bg-card shadow-[var(--shadow-card)]">
            <table className="w-full text-[13px]">
              <thead className="bg-secondary/60 text-left text-[12px] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Bank</th><th className="px-3 py-2">Pelanggan · Unit</th><th className="px-3 py-2">Tahap</th>
                  <th className="px-3 py-2">Syarat</th><th className="px-3 py-2 text-right">Nilai</th><th className="px-3 py-2">Sejak akad</th><th className="px-3 py-2">Keadaan</th>
                </tr>
              </thead>
              <tbody>
                {held.map((h) => (
                  <tr key={`${h.app_id}-${h.tranche_code}`} data-testid={T.heldRow} data-ready={h.ready} className="border-t">
                    <td className="px-3 py-2">{h.bank}</td>
                    <td className="px-3 py-2">
                      <Link to={`/customers/${h.customer_id}?tab=kpr`} className="font-medium text-primary hover:underline">{h.customer_name || "Pelanggan"}</Link>
                      <span className="text-muted-foreground"> · {h.unit_code || "-"} · {h.contract_no || "-"}</span>
                    </td>
                    <td className="px-3 py-2">{h.tranche_code} · {h.tranche_name}</td>
                    <td className="px-3 py-2 text-muted-foreground">{COND[h.condition] || h.condition}</td>
                    <td className="px-3 py-2 text-right tabular-nums"><MoneyText value={h.amount} /></td>
                    <td className="px-3 py-2 text-muted-foreground">{h.days_since_akad == null ? "belum akad" : `${h.days_since_akad} hari`}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${h.ready ? "border-amber-200 bg-amber-50 text-amber-900" : "border-slate-200 bg-slate-100 text-slate-700"}`}>
                        {h.ready ? "Siap cair — tagih bank" : "Menunggu syarat"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {noScheme.length ? (
        <div className="space-y-1.5">
          <p className="text-[13px] font-medium text-rose-800">Plafon tercatat tanpa skema pencairan ({noScheme.length})</p>
          <ul className="divide-y rounded-lg border text-[12px]">
            {noScheme.map((h) => (
              <li key={h.app_id} data-testid={T.noSchemeRow} className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1.5">
                <span>{h.bank} · <Link to={`/customers/${h.customer_id}?tab=kpr`} className="font-medium text-primary hover:underline">{h.customer_name || "Pelanggan"}</Link> · {h.unit_code || "-"}</span>
                <span className="tabular-nums"><MoneyText value={h.plafon} /> · pilih skema di kartu KPR</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
