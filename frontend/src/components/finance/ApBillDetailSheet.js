import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ExternalLink } from "lucide-react";

import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import StatusPill from "@/components/patterns/StatusPill";
import { LoadingCards, ErrorState } from "@/components/patterns/StateViews";
import api from "@/services/apiClient";
import { formatIDR, formatDateWIB } from "@/utils/formatters";

function Stat({ label, value, tone }) {
  return (
    <div className="rounded-lg border bg-card p-2.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className={`text-sm font-semibold tabular-nums ${tone || ""}`}>{formatIDR(value || 0)}</p>
    </div>
  );
}

function Section({ title, count, children, testId }) {
  return (
    <section data-testid={testId} className="space-y-2">
      <h4 className="font-heading text-sm font-semibold">
        {title}{count != null ? <span className="ml-1.5 text-xs font-normal text-muted-foreground">({count})</span> : null}
      </h4>
      {children}
    </section>
  );
}

const Empty = ({ text }) => <p className="text-xs text-muted-foreground">{text}</p>;

/** Detail satu tagihan AP: ringkasan, sumber (termin/PO/pengajuan), pembayaran, retensi, jurnal. */
export default function ApBillDetailSheet({ billId, open, onOpenChange }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!billId) return;
    setError("");
    try { setD((await api.get(`/finance/ap/bills/${billId}`)).data.data); }
    catch (e) { setError(e?.response?.data?.detail || "Gagal memuat detail tagihan."); }
  }, [billId]);
  useEffect(() => { if (open) { setD(null); load(); } }, [open, load]);

  const b = d?.bill;
  const s = d?.summary || {};
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent data-testid="ap-bill-detail" className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Detail Tagihan AP</SheetTitle>
          <SheetDescription data-testid="ap-bill-detail-vendor">
            {b ? `${b.vendor}${d.project ? ` · ${d.project.name}` : ""}${b.note ? ` · ${b.note}` : ""}` : "Memuat…"}
          </SheetDescription>
        </SheetHeader>
        {error ? <ErrorState message={error} onRetry={load} /> : !d ? <LoadingCards count={3} /> : (
          <div className="mt-4 space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill status={b.status} group="ap_status" />
              {b.bill_kind === "retention_release" ? <Badge variant="outline">Pencairan retensi</Badge> : null}
              {b.retention_released ? <Badge variant="outline">Retensi sudah cair</Badge> : null}
              <span className="text-xs text-muted-foreground">Dibuat {formatDateWIB(b.created_at)} oleh {b.created_by || "-"}
                {b.approved_at ? ` · disetujui ${formatDateWIB(b.approved_at)} oleh ${b.approved_by}` : ""}
                {b.due_date ? ` · jatuh tempo ${formatDateWIB(b.due_date)}` : ""}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="ap-bill-detail-summary">
              <Stat label="Nilai klaim" value={s.claimed} />
              <Stat label="Retensi ditahan" value={s.retention_held} />
              <Stat label="Potongan termin" value={s.deduction_total} />
              <Stat label="Net terutang" value={s.net} />
              <Stat label="Dibayar" value={s.paid_recorded} tone="text-emerald-700" />
              <Stat label="Sisa" value={s.outstanding} tone={s.outstanding > 0 ? "text-amber-700" : ""} />
            </div>
            {!s.paid_consistent ? (
              <p data-testid="ap-bill-detail-inconsistent" className="flex items-center gap-1.5 rounded-md bg-rose-50 p-2 text-xs text-rose-800">
                <AlertTriangle className="h-3.5 w-3.5" /> Σ pembayaran tercatat {formatIDR(s.paid)} ≠ nilai dibayar pada tagihan {formatIDR(s.paid_recorded)}.
              </p>
            ) : null}

            <Section title="Sumber tagihan" testId="ap-bill-detail-source">
              {d.claim ? (
                <div className="rounded-lg border p-2.5 text-xs">
                  <p className="font-medium">Termin {d.claim.claim_number} · SPK {d.spk?.spk_number || d.claim.spk_number}</p>
                  <p className="text-muted-foreground">{d.claim.period} · {d.claim.basis === "items" ? `${(d.claim.lines || []).filter((l) => l.included).length} pekerjaan terverifikasi` : `${d.claim.prev_pct}% → ${d.claim.effective_pct}%`} · disetujui {formatDateWIB(d.claim.approved_at)} oleh {d.claim.approved_by}</p>
                  {d.spk ? <p className="text-muted-foreground">Nilai kontrak {formatIDR(d.spk.contract_value)} · progres {d.spk.progress_pct}% · {d.spk.title}</p> : null}
                  {(d.claim.deductions || []).length ? (
                    <ul className="mt-1 list-disc pl-4">
                      {d.claim.deductions.map((x) => <li key={x.deduction_id}>{x.kind}: {formatIDR(x.amount)} — {x.reason}</li>)}
                    </ul>
                  ) : null}
                </div>
              ) : d.po ? (
                <div className="rounded-lg border p-2.5 text-xs">
                  <p className="font-medium">PO {d.po.po_number} · {d.po.po_type}</p>
                  <p className="text-muted-foreground">{d.po.vendor} · total PO {formatIDR(d.po.total)}</p>
                </div>
              ) : d.source_retention ? (
                <div className="rounded-lg border p-2.5 text-xs">
                  <p className="font-medium">Pencairan retensi {d.source_retention.retention_number} atas termin {d.source_retention.claim_number}</p>
                  <p className="text-muted-foreground">SPK {d.source_retention.spk_number} · dicairkan {formatDateWIB(d.source_retention.released_at)} oleh {d.source_retention.released_by}</p>
                </div>
              ) : <Empty text="Tagihan manual (tanpa termin/PO)." />}
              {d.fund_requests?.length ? (
                <ul className="space-y-1 text-xs" data-testid="ap-bill-detail-fundreqs">
                  {d.fund_requests.map((f) => (
                    <li key={f.id} className="flex items-center justify-between rounded border px-2 py-1">
                      <span>Pengajuan {f.no} · {f.requested_by}</span>
                      <span className="flex items-center gap-2"><StatusPill status={f.status} group="fund_request_status" /> {formatIDR(f.disbursed_amount || f.amount)}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </Section>

            <Section title="Riwayat pembayaran" count={d.payments.length} testId="ap-bill-detail-payments">
              {!d.payments.length ? <Empty text="Belum ada pembayaran." /> : (
                <table className="w-full text-xs">
                  <thead className="text-left text-muted-foreground"><tr><th className="py-1">Tanggal</th><th>Rekening</th><th className="text-right">Jumlah</th><th className="text-right">PPh dipotong</th><th className="text-right">Kas keluar</th><th>Oleh</th></tr></thead>
                  <tbody>
                    {d.payments.map((p) => (
                      <tr key={p.id} className="border-t" data-testid="ap-bill-detail-payment-row">
                        <td className="py-1">{formatDateWIB(p.created_at)}</td>
                        <td className="text-muted-foreground">{p.cash_account_name || p.cash_account_code || "-"}</td>
                        <td className="text-right tabular-nums">{formatIDR(p.amount)}</td>
                        <td className="text-right tabular-nums text-muted-foreground">{p.withheld_amount ? formatIDR(p.withheld_amount) : "-"}</td>
                        <td className="text-right tabular-nums">{formatIDR(p.cash_out ?? p.amount)}</td>
                        <td className="text-muted-foreground">{p.actor}{p.note ? ` · ${p.note}` : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {d.withholding?.length ? (
                <p className="text-xs text-muted-foreground">Bukti potong: {d.withholding.map((w) => w.number || w.doc_number || w.id).join(", ")}</p>
              ) : null}
            </Section>

            <Section title="Retensi" testId="ap-bill-detail-retention">
              {d.retention ? (
                <div className="rounded-lg border p-2.5 text-xs">
                  <p className="font-medium">{d.retention.retention_number} · {formatIDR(d.retention.amount)} ({d.retention.retention_pct}%) · <StatusPill status={d.retention.state} group="retention_state" /></p>
                  <p className="text-muted-foreground">Masa pemeliharaan {d.retention.maintenance_days} hari s/d {d.retention.maintenance_until}
                    {d.retention.released_at ? ` · dicairkan ${formatDateWIB(d.retention.released_at)} oleh ${d.retention.released_by}` : ""}</p>
                  {d.release_bill ? <p className="text-muted-foreground">Tagihan pencairan: {formatIDR(d.release_bill.net)} · <StatusPill status={d.release_bill.status} group="ap_status" /></p> : null}
                </div>
              ) : s.retention_held > 0 ? <Empty text={`Retensi ${formatIDR(s.retention_held)} ditahan (tagihan manual — tanpa daftar retensi SPK).`} />
                : <Empty text="Tidak ada retensi." />}
            </Section>

            <Section title="Jurnal buku besar" count={d.journals.length} testId="ap-bill-detail-journals">
              {!d.journals.length ? <Empty text="Belum ada jurnal (tagihan belum disetujui)." /> : d.journals.map((j) => (
                <div key={j.id} className="rounded-lg border p-2.5 text-xs" data-testid="ap-bill-detail-journal">
                  <p className="flex items-center justify-between font-medium">
                    <span>{j.entry_no} · {formatDateWIB(j.date)}</span>
                    <a className="inline-flex items-center gap-1 text-primary" href={`/accounting?tab=journals&q=${encodeURIComponent(j.entry_no)}`}>
                      buku besar <ExternalLink className="h-3 w-3" />
                    </a>
                  </p>
                  <p className="text-muted-foreground">{j.memo}</p>
                  <table className="mt-1 w-full">
                    <tbody>
                      {j.lines.map((l, i) => (
                        <tr key={i}>
                          <td className={`py-0.5 ${l.credit ? "pl-4" : ""}`}><span className="font-mono">{l.account_code}</span> {l.account_name}</td>
                          <td className="text-right tabular-nums">{l.debit ? formatIDR(l.debit) : ""}</td>
                          <td className="text-right tabular-nums">{l.credit ? formatIDR(l.credit) : ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </Section>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
