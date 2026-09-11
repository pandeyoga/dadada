import React from "react";
import { Paperclip } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import StatusPill from "@/components/patterns/StatusPill";
import RefLabel from "@/components/patterns/RefLabel";
import { formatIDR, formatDateTimeWIB } from "@/utils/formatters";
import { fileUrl } from "@/utils/photoSrc";
import { FUNDREQ } from "@/constants/testIds";

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b py-2 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-right text-sm font-medium">{value}</span>
    </div>
  );
}

const ACTION_LABEL = { submitted: "Diajukan", approved: "Disetujui", rejected: "Ditolak",
  cancelled: "Dibatalkan", disbursed: "Dicairkan", settled: "Dipertanggungjawabkan" };

/** Detail pengajuan + jejak persetujuan/pencairan + lampiran + realisasi kas bon. */
export default function FundRequestDetailSheet({ req, onClose }) {
  if (!req) return null;
  const r = req;
  const files = [...(r.attachments || []), ...(r.settle_attachments || [])];
  return (
    <Sheet open onOpenChange={(v) => { if (!v) onClose(); }}>
      <SheetContent data-testid={FUNDREQ.detailSheet} className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            {r.no} <StatusPill status={r.status} group="fund_request_status" />
          </SheetTitle>
          <SheetDescription>{r.title}</SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-4">
          <div className="rounded-xl border bg-card p-3 shadow-[var(--shadow-card)]">
            <Row label="Jenis" value={<RefLabel group="fund_request_type" value={r.type} />} />
            <Row label="Pemohon" value={r.requester_name || r.requested_by} />
            <Row label="Kategori beban" value={<RefLabel group="cashbon_category" value={r.category} />} />
            <Row label="Urgensi" value={<RefLabel group="fund_request_urgency" value={r.urgency} />} />
            <Row label="Proyek" value={r.project_name || "—"} />
            <Row label="Nominal diajukan" value={formatIDR(r.amount)} />
            {r.approved_amount ? <Row label="Nominal disetujui" value={formatIDR(r.approved_amount)} /> : null}
            {r.disbursed_amount ? <Row label="Dicairkan" value={`${formatIDR(r.disbursed_amount)} · ${r.cash_account_name || r.source || ""}`} /> : null}
            {r.ap_bill_id ? <Row label="Tagihan AP" value={`${r.ap_bill_note || r.ap_bill_id} · sisa saat diajukan Rp ${Number(r.ap_bill_outstanding || 0).toLocaleString("id-ID")}${r.ap_bill_status ? ` · status kini ${r.ap_bill_status}` : ""}`} /> : null}
            {r.payee_name ? <Row label="Penerima" value={`${r.payee_name}${r.payee_bank ? ` · ${r.payee_bank} ${r.payee_account || ""}` : ""}`} /> : null}
            <Row label="Tanggal dibutuhkan" value={r.needed_date ? formatDateTimeWIB(r.needed_date) : "—"} />
            <Row label="Catatan" value={r.note || "—"} />
            {r.reject_reason ? <Row label="Alasan ditolak" value={<span className="text-rose-700">{r.reject_reason}</span>} /> : null}
          </div>
          {files.length ? (
            <div className="rounded-xl border bg-card p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Lampiran</p>
              <ul className="space-y-1">
                {files.map((f) => (
                  <li key={f.id}>
                    <a className="inline-flex items-center gap-1 text-sm text-primary hover:underline" href={fileUrl(f.id)} target="_blank" rel="noreferrer">
                      <Paperclip className="h-3.5 w-3.5" /> {f.filename || f.id}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {r.expenses?.length ? (
            <div className="rounded-xl border bg-card p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Realisasi pertanggungjawaban</p>
              {r.expenses.map((e) => (
                <Row key={e.id} label={<><RefLabel group="cashbon_category" value={e.category} /> · {e.description}</>} value={formatIDR(e.amount)} />
              ))}
              <Row label="Total realisasi" value={formatIDR(r.expense_total)} />
              {r.returned_amount ? <Row label="Sisa dikembalikan" value={formatIDR(r.returned_amount)} /> : null}
              {r.reimburse_amount ? <Row label="Kekurangan diganti" value={formatIDR(r.reimburse_amount)} /> : null}
            </div>
          ) : null}
          <div className="rounded-xl border bg-card p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Riwayat</p>
            {(r.history || []).map((h, i) => (
              <Row key={i} label={`${ACTION_LABEL[h.action] || h.action} · ${h.actor}`}
                value={<span className="text-xs">{formatDateTimeWIB(h.at)}{h.note ? ` — ${h.note}` : ""}</span>} />
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
