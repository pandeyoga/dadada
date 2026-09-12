import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { FileSignature, Plus, Check, X, HandCoins, ClipboardList, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import MetricCard from "@/components/patterns/MetricCard";
import StatusPill from "@/components/patterns/StatusPill";
import EmptyState from "@/components/patterns/EmptyState";
import RefLabel from "@/components/patterns/RefLabel";
import { LoadingCards, ErrorState } from "@/components/patterns/StateViews";
import FundRequestDialog from "@/components/fundRequests/FundRequestDialog";
import FundRequestDetailSheet from "@/components/fundRequests/FundRequestDetailSheet";
import { FundRequestDisburseDialog, FundRequestSettleDialog } from "@/components/fundRequests/FundRequestActionDialogs";
import { useAuth } from "@/context/AuthContext";
import { useReference } from "@/context/ReferenceContext";
import { formatIDR, formatDateWIB } from "@/utils/formatters";
import api from "@/services/apiClient";
import { FUNDREQ } from "@/constants/testIds";

const STATUSES = ["submitted", "approved", "disbursed", "settled", "rejected", "cancelled"];

/**
 * Pengajuan Keuangan — satu pintu: biaya operasional, reimbursement, pembelian, pembayaran
 * vendor, dan kas bon. Alur satu tahap: diajukan → disetujui finance → dicairkan (kas bon → dipertanggungjawabkan).
 */
export default function FundRequestsPage() {
  const { user } = useAuth();
  const { labelOf, options } = useReference();
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [canApprove, setCanApprove] = useState(false);
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openNew, setOpenNew] = useState(false);
  const [disburse, setDisburse] = useState(null);
  const [settle, setSettle] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const params = {};
      if (status) params.status = status;
      if (type) params.type = type;
      if (q) params.q = q;
      const [list, sum] = await Promise.all([
        api.get("/fund-requests", { params }), api.get("/fund-requests/summary"),
      ]);
      setRows(list.data.data || []); setCanApprove(Boolean(list.data.can_approve));
      setSummary(sum.data.data || null);
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal memuat pengajuan.");
    } finally { setLoading(false); }
  }, [status, type, q]);
  useEffect(() => { load(); }, [load]);

  const act = async (row, action) => {
    setBusy(row.id);
    try {
      if (action === "approve") await api.post(`/fund-requests/${row.id}/approve`, { note: null });
      else if (action === "reject") {
        const reason = window.prompt("Alasan penolakan:") || "";
        if (!reason.trim()) { setBusy(""); return; }
        await api.post(`/fund-requests/${row.id}/reject`, { note: reason.trim() });
      } else await api.post(`/fund-requests/${row.id}/cancel`);
      toast.success(`Pengajuan ${row.no} ${action === "approve" ? "disetujui" : action === "reject" ? "ditolak" : "dibatalkan"}.`);
      await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Aksi gagal diproses."); }
    finally { setBusy(""); }
  };
  const isMine = (r) => r.requested_by === user?.email;

  return (
    <div data-testid={FUNDREQ.page} className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileSignature className="h-5 w-5 text-primary" />
          <div>
            <h1 className="page-title">Pengajuan Keuangan</h1>
            <p className="text-xs text-muted-foreground">
              Biaya operasional, reimbursement, pembelian, pembayaran vendor, dan kas bon — disetujui & dicairkan finance.
            </p>
          </div>
        </div>
        <Button data-testid={FUNDREQ.newBtn} onClick={() => setOpenNew(true)}>
          <Plus className="mr-1.5 h-4 w-4" /> Buat Pengajuan
        </Button>
      </div>

      {loading && !summary ? <LoadingCards count={4} /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <>
          <div data-testid={FUNDREQ.summary} className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard label="Menunggu Persetujuan" value={summary?.waiting_approval_amount || 0} tone="amber" format="idr"
              hint={`${summary?.waiting_approval || 0} pengajuan`} />
            <MetricCard label="Siap Dicairkan" value={summary?.ready_to_disburse_amount || 0} tone="primary" format="idr"
              hint={`${summary?.ready_to_disburse || 0} disetujui`} />
            <MetricCard label="Kas Bon Berjalan" value={summary?.advance_outstanding_amount || 0} tone="indigo" format="idr"
              hint={`${summary?.advance_outstanding || 0} belum dipertanggungjawabkan`} />
            <MetricCard label="Total Dicairkan" value={summary?.disbursed_total || 0} tone="emerald" format="idr" hint="Semua jenis pengajuan" />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Input data-testid="fund-requests-search" className="w-56" placeholder="Cari no / judul / pemohon"
              value={q} onChange={(e) => setQ(e.target.value)} />
            <Select value={status || "__all__"} onValueChange={(v) => setStatus(v === "__all__" ? "" : v)}>
              <SelectTrigger data-testid={FUNDREQ.filterStatus} className="w-48"><SelectValue placeholder="Semua status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Semua status</SelectItem>
                {STATUSES.map((s) => <SelectItem key={s} value={s}>{labelOf("fund_request_status", s)}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={type || "__all__"} onValueChange={(v) => setType(v === "__all__" ? "" : v)}>
              <SelectTrigger data-testid={FUNDREQ.filterType} className="w-64"><SelectValue placeholder="Semua jenis" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Semua jenis</SelectItem>
                {options("fund_request_type").map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {!rows.length ? (
            <div data-testid={FUNDREQ.empty}>
              <EmptyState icon={FileSignature} title="Belum ada pengajuan"
                description="Ajukan biaya, reimbursement, pembelian, pembayaran vendor, atau kas bon; finance akan menyetujui lalu mencairkannya."
                actionLabel="Buat Pengajuan" onAction={() => setOpenNew(true)} />
            </div>
          ) : (
            <div data-testid={FUNDREQ.table} className="overflow-hidden rounded-xl border bg-card shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>No.</TableHead><TableHead>Keperluan</TableHead><TableHead>Jenis</TableHead>
                    <TableHead>Pemohon</TableHead><TableHead className="text-right">Diajukan</TableHead>
                    <TableHead className="text-right">Dicairkan</TableHead><TableHead>Status</TableHead>
                    <TableHead className="col-actions-head text-right">Aksi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.id} data-testid={FUNDREQ.row} data-status={r.status} data-type={r.type}>
                      <TableCell className="font-medium">{r.no}
                        {r.urgency === "urgent" ? <span className="ml-1 rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">MENDESAK</span> : null}
                      </TableCell>
                      <TableCell className="max-w-[260px]">
                        <p className="truncate" title={r.title}>{r.title}</p>
                        <p className="text-[11px] text-muted-foreground">{r.project_name || "Tanpa proyek"} · {formatDateWIB(r.created_at)}</p>
                      </TableCell>
                      <TableCell className="text-sm"><RefLabel group="fund_request_type" value={r.type} /></TableCell>
                      <TableCell className="text-sm">{r.requester_name || r.requested_by}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatIDR(r.amount)}
                        {r.approved_amount && r.approved_amount !== r.amount ? <p className="text-[11px] text-muted-foreground">disetujui {formatIDR(r.approved_amount)}</p> : null}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{r.disbursed_amount ? formatIDR(r.disbursed_amount) : "—"}</TableCell>
                      <TableCell><StatusPill status={r.status} group="fund_request_status" /></TableCell>
                      <TableCell className="col-actions">
                        <div className="flex flex-wrap justify-end gap-1.5">
                          <Button size="sm" variant="ghost" data-testid={FUNDREQ.detailBtn} onClick={() => setDetail(r)}>Detail</Button>
                          {canApprove && r.status === "submitted" ? (<>
                            <Button size="sm" data-testid={FUNDREQ.approveBtn} disabled={busy === r.id || isMine(r)}
                              title={isMine(r) ? "Pemohon tidak boleh menyetujui pengajuannya sendiri" : undefined}
                              onClick={() => act(r, "approve")}><Check className="mr-1 h-3.5 w-3.5" /> Setujui</Button>
                            <Button size="sm" variant="outline" data-testid={FUNDREQ.rejectBtn} disabled={busy === r.id}
                              onClick={() => act(r, "reject")}><X className="mr-1 h-3.5 w-3.5" /> Tolak</Button>
                          </>) : null}
                          {canApprove && r.status === "approved" ? (
                            <Button size="sm" data-testid={FUNDREQ.disburseBtn} onClick={() => setDisburse(r)}>
                              <HandCoins className="mr-1 h-3.5 w-3.5" /> Cairkan</Button>
                          ) : null}
                          {r.type === "advance" && r.status === "disbursed" && (isMine(r) || canApprove) ? (
                            <Button size="sm" data-testid={FUNDREQ.settleBtn} onClick={() => setSettle(r)}>
                              <ClipboardList className="mr-1 h-3.5 w-3.5" /> Pertanggungjawaban</Button>
                          ) : null}
                          {["submitted", "approved"].includes(r.status) && (isMine(r) || canApprove) ? (
                            <Button size="sm" variant="outline" data-testid={FUNDREQ.cancelBtn} disabled={busy === r.id}
                              onClick={() => act(r, "cancel")}><Ban className="mr-1 h-3.5 w-3.5" /> Batalkan</Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </>
      )}

      <FundRequestDialog open={openNew} onOpenChange={setOpenNew} onSaved={load} />
      <FundRequestDisburseDialog req={disburse} onClose={() => setDisburse(null)} onSaved={load} />
      <FundRequestSettleDialog req={settle} onClose={() => setSettle(null)} onSaved={load} />
      <FundRequestDetailSheet req={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
