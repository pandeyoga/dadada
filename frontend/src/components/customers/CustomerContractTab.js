import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle, CheckCircle2, ExternalLink, Receipt, ScrollText, Wallet,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import EmptyState from "@/components/patterns/EmptyState";
import MoneyText from "@/components/patterns/MoneyText";
import StatusPill from "@/components/patterns/StatusPill";
import { LoadingCards, ErrorState } from "@/components/patterns/StateViews";
import CostsDialog from "@/components/contracts/CostsDialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { formatDateWIB, formatIDR } from "@/utils/formatters";
import { CHUB } from "@/constants/testIds";

/**
 * Tab “Kontrak & Harga” — SATU kartu per transaksi pembeli, dirangkai server
 * (`GET /customers/{id}/contract-pricing`): skema yang DIPILIH saat reservasi, rincian
 * harga, termin, kontrak (komponen biaya yang bisa diisi), ringkasan AR, dan pemeriksaan
 * sinkron skema deal ↔ kontrak ↔ AR.
 */
export default function CustomerContractTab({ customer }) {
  const { can } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [costsFor, setCostsFor] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await api.get(`/customers/${customer.id}/contract-pricing`);
      setRows(res.data.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal memuat kontrak & harga pelanggan.");
    } finally { setLoading(false); }
  }, [customer.id]);

  useEffect(() => { load(); }, [load]);

  const openCosts = async (contractId) => {
    try {
      const res = await api.get(`/contracts/${contractId}`);
      setCostsFor(res.data.data);
    } catch (e) { setError(e?.response?.data?.detail || "Gagal membuka kontrak."); }
  };

  if (loading) return <LoadingCards count={2} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!rows.length) {
    return (
      <div data-testid={CHUB.cpEmpty}>
        <EmptyState icon={ScrollText} title="Belum ada transaksi"
          description="Kontrak & harga muncul setelah pembeli ini punya reservasi unit." />
      </div>
    );
  }

  return (
    <div data-testid={CHUB.cpTab} className="space-y-5">
      {rows.map((r) => (
        <DealCard key={r.deal.id} row={r} customerId={customer.id}
          mayEditCosts={can("contracts", "update")} onCosts={openCosts} />
      ))}
      {costsFor ? (
        <CostsDialog contract={costsFor} open onOpenChange={(v) => !v && setCostsFor(null)}
          onSaved={() => { setCostsFor(null); load(); }} />
      ) : null}
    </div>
  );
}

function Stat({ label, value, strong = false }) {
  return (
    <div className="rounded-lg border bg-secondary/40 px-2.5 py-1.5">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`tabular-nums ${strong ? "text-base font-semibold" : "font-medium"}`}>
        {value === null || value === undefined ? <span className="text-xs italic text-muted-foreground">belum ada data</span> : value}
      </p>
    </div>
  );
}

function DealCard({ row, customerId, mayEditCosts, onCosts }) {
  const { deal, scheme, pricing, contract, ar, sync } = row;
  const bd = contract?.breakdown || {};
  const terms = ar?.items?.length ? ar.items : (pricing.terms || []);
  const termSource = ar?.items?.length ? "tagihan AR (nyata)" : "rencana saat reservasi";

  return (
    <div data-testid={CHUB.cpDealCard} data-deal={deal.id}
      className="space-y-4 rounded-xl border bg-card p-4 shadow-[var(--shadow-card)]">
      {/* ---------- kepala ---------- */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            <Link data-testid={CHUB.cpOpenUnit} to={`/units/${deal.unit_id}`}
              className="text-primary hover:underline">Unit {deal.unit_code}</Link>
            <StatusPill group="deal_status" status={deal.status} />
            {contract ? <StatusPill group="contract_legal_stage" status={contract.legal_stage} /> : null}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Reservasi {deal.reserved_at ? formatDateWIB(deal.reserved_at) : "—"}
            {deal.booked_at ? ` · booking ${formatDateWIB(deal.booked_at)}` : ""}
            {deal.assigned_to ? ` · sales ${deal.assigned_to}` : ""}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Skema pembayaran (dipilih saat reservasi)</p>
          {scheme ? (
            <p data-testid={CHUB.cpSchemeBadge} className="text-sm font-semibold">
              {scheme.name}
              {scheme.kind_label ? (
                <span className="ml-1.5 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">{scheme.kind_label}</span>
              ) : null}
            </p>
          ) : (
            <p data-testid={CHUB.cpSchemeBadge} className="text-xs italic text-amber-700">
              tidak dipilih saat reservasi — memakai skema bawaan
            </p>
          )}
        </div>
      </div>

      {/* ---------- sinkron ---------- */}
      {sync.ok ? (
        <p data-testid={CHUB.cpSyncOk}
          className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Skema reservasi, kontrak, dan tagihan AR SINKRON{contract ? ` (${contract.payment_scheme_name || contract.scheme_label})` : ""}.
        </p>
      ) : (
        <div data-testid={CHUB.cpSyncIssue}
          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
          <p className="flex items-center gap-1.5 font-medium"><AlertTriangle className="h-3.5 w-3.5" /> Skema TIDAK sinkron</p>
          <ul className="mt-1 list-disc pl-5">{sync.issues.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}

      {/* ---------- harga ---------- */}
      <section className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Rincian harga</h4>
        <div data-testid={CHUB.cpPriceGrid} className="grid gap-2 sm:grid-cols-5">
          <Stat label="Harga unit" value={<MoneyText value={pricing.base_price} />} />
          <Stat label="Add-on" value={<MoneyText value={pricing.addon_total ?? 0} />} />
          <Stat label="Diskon / promo" value={<MoneyText value={pricing.discount_amount ?? 0} />} />
          <Stat label="Harga neto" value={<MoneyText value={pricing.net_price} />} strong />
          <Stat label="Booking fee" value={<MoneyText value={deal.booking_fee} />} />
        </div>
        {(pricing.addon_lines || []).length ? (
          <ul className="text-xs text-muted-foreground">
            {pricing.addon_lines.map((a, i) => (
              <li key={a.code || i} data-testid={CHUB.cpAddonRow} className="flex justify-between border-t py-1">
                <span>+ {a.name || a.code}{a.qty ? ` · ${a.qty} ${a.uom || ""}` : ""}</span>
                <span className="tabular-nums">{formatIDR(a.amount ?? a.total ?? a.subtotal ?? 0)}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {(pricing.discount_lines || []).length ? (
          <ul className="text-xs text-muted-foreground">
            {pricing.discount_lines.map((d, i) => (
              <li key={i} data-testid={CHUB.cpDiscountRow} className="flex justify-between border-t py-1">
                <span>− {d.label || d.name || d.kind}{d.pct ? ` (${d.pct}%)` : ""}</span>
                <span className="tabular-nums">{formatIDR(d.amount || 0)}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {/* ---------- termin ---------- */}
      <section className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Termin pembayaran <span className="font-normal normal-case">· sumber: {termSource}</span>
        </h4>
        {terms.length ? (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-[13px]">
              <thead className="bg-secondary/60 text-left text-[12px] text-muted-foreground">
                <tr><th className="px-3 py-1.5">#</th><th className="px-3 py-1.5">Termin</th>
                  <th className="px-3 py-1.5">Jatuh tempo</th><th className="px-3 py-1.5 text-right">Nilai</th>
                  <th className="px-3 py-1.5 text-right">Terbayar</th><th className="px-3 py-1.5">Status</th></tr>
              </thead>
              <tbody>
                {terms.map((t, i) => (
                  <tr key={t.id || i} data-testid={CHUB.cpTermRow} className="border-t">
                    <td className="px-3 py-1.5 text-muted-foreground">{i + 1}</td>
                    <td className="px-3 py-1.5 font-medium">{t.label}{t.value && t.basis === "percent" && !/%/.test(t.label || "") ? ` (${t.value}%)` : ""}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">
                      {t.due_date ? formatDateWIB(t.due_date) : (t.due_rule || "mengikuti peristiwa")}
                    </td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{formatIDR(t.amount || 0)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{formatIDR(t.paid_amount || 0)}</td>
                    <td className="px-3 py-1.5"><StatusPill group="ar_status" status={t.status || "unpaid"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Termin belum terbentuk untuk transaksi ini.</p>
        )}
      </section>

      {/* ---------- kontrak & komponen biaya ---------- */}
      <section data-testid={CHUB.cpContractBox} className="space-y-2 rounded-lg border bg-background p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="flex items-center gap-1.5 text-sm font-semibold"><ScrollText className="h-4 w-4" /> Kontrak</h4>
            {contract ? (
              <p className="text-xs text-muted-foreground">
                <span className="font-mono">{contract.number}</span> · <StatusPill group="contract_state" status={contract.state} />
                {" "}· skema kontrak <b>{contract.payment_scheme_name || contract.scheme_label}</b>
                {contract.activated_at ? ` · aktif sejak ${formatDateWIB(contract.activated_at)}` : ""}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Belum ada kontrak — lahir saat lead dijadikan PEMBELI setelah booking dikonfirmasi.
              </p>
            )}
          </div>
          {contract ? (
            <div className="flex items-center gap-2">
              {mayEditCosts ? (
                <Button data-testid={CHUB.cpCostsBtn} size="sm" variant="outline" onClick={() => onCosts(contract.id)}>
                  <Wallet className="mr-1.5 h-3.5 w-3.5" /> Isi komponen biaya
                </Button>
              ) : null}
              <Link data-testid={CHUB.cpOpenContract} to={`/customers/${customerId}?tab=kontrak53`}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                Kontrak & Legal <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          ) : null}
        </div>
        {contract ? (
          <>
            <table className="w-full text-[13px]">
              <tbody>
                {(bd.rows || []).map((c) => (
                  <tr key={c.code} data-testid={CHUB.cpCostRow} data-code={c.code} data-state={c.state} className="border-t">
                    <td className="py-1.5">
                      <span className="font-medium">{c.label}</span>
                      {c.note ? <span className="ml-1 text-[11px] text-muted-foreground">{c.note}</span> : null}
                    </td>
                    <td className="py-1.5 text-xs text-muted-foreground">{c.finance_treatment}</td>
                    <td className="py-1.5 text-right tabular-nums">
                      {c.amount === null || c.amount === undefined
                        ? <span className="text-xs italic text-amber-700">{c.state_label || "belum diisi"}</span>
                        : formatIDR(c.amount)}
                    </td>
                  </tr>
                ))}
                <tr className="border-t font-semibold">
                  <td className="py-1.5" colSpan={2}>Total ditagihkan
                    {bd.total_is_provisional ? <span className="ml-1.5 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-900">SEMENTARA</span> : null}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">{formatIDR(bd.total_bill || 0)}</td>
                </tr>
              </tbody>
            </table>
            {bd.total_is_provisional ? (
              <p className="text-[11px] text-amber-700">
                Belum diisi: {(bd.costs_incomplete_labels || bd.costs_incomplete || []).join(", ")}.
              </p>
            ) : null}
          </>
        ) : null}
      </section>

      {/* ---------- AR ---------- */}
      <section data-testid={CHUB.cpArBox} className="rounded-lg border bg-background p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h4 className="flex items-center gap-1.5 text-sm font-semibold"><Receipt className="h-4 w-4" /> Piutang (AR)</h4>
          {ar ? (
            <Link data-testid={CHUB.cpArOpen} to={`/finance?tab=ar&deal_id=${deal.id}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              Buka di Finance <ExternalLink className="h-3 w-3" />
            </Link>
          ) : null}
        </div>
        {ar ? (
          <div className="mt-2 grid gap-2 sm:grid-cols-4">
            <Stat label="Total tagihan" value={<MoneyText value={ar.total} />} />
            <Stat label="Terbayar" value={<MoneyText value={ar.paid} />} />
            <Stat label="Sisa" value={<MoneyText value={ar.outstanding} />} strong />
            <Stat label="Jatuh tempo berikutnya" value={ar.next_due
              ? `${ar.next_due.label} · ${ar.next_due.due_date ? formatDateWIB(ar.next_due.due_date) : "peristiwa"}`
              : "semua lunas"} />
          </div>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">
            Tagihan AR belum terbit — terbentuk saat kontrak diaktifkan (termin mengikuti skema kontrak).
          </p>
        )}
      </section>
    </div>
  );
}
