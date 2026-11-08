import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import { formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";

const OPEN = ["menunggu_pemetaan", "menunggu_konfirmasi"];
const MODE_LABEL = {
  manual_keuangan: "Manual oleh Keuangan", urut_termin_tertua: "Urut termin tertua (hitungan sistem)",
  proporsional: "Proporsional (hitungan sistem)",
};

/** Galat pemetaan (cermin `scheme_change_alloc.normalize`; server tetap yang menentukan). */
function mappingErrors(req, rows) {
  const errs = [];
  const used = {};
  (req.receipts || []).forEach((r) => {
    const list = rows[r.id] || [];
    const sum = list.reduce((a, x) => a + (Number(x.amount) || 0), 0);
    if (sum !== r.applied) errs.push(`Kuitansi ${r.receipt_no}: jumlah ${formatIDR(sum)} harus tepat ${formatIDR(r.applied)}.`);
    list.forEach((x) => { used[x.no] = (used[x.no] || 0) + (Number(x.amount) || 0); });
  });
  (req.preview || []).forEach((p) => {
    if ((used[p.no] || 0) > p.amount) errs.push(`Termin ${p.no} '${p.label}' kelebihan alokasi ${formatIDR(used[p.no] - p.amount)}.`);
  });
  return errs;
}

/**
 * Pemetaan alokasi kuitansi → termin baru untuk penggantian skema yang DITAHAN karena sudah ada pembayaran (W1-B #9, IN-14).
 * Mode manual: Keuangan mengisi alokasi tiap kuitansi; mode hitungan sistem: pratinjau + konfirmasi. Alasan wajib, tercatat.
 */
export default function SchemeChangePanel({ dealId, onChanged }) {
  const { can } = useAuth();
  const mayApply = can("finance", "approve");
  const [req, setReq] = useState(null);
  const [rows, setRows] = useState({});
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/finance/scheme-changes", { params: { deal_id: dealId } });
      const open = (res.data.data || []).find((x) => OPEN.includes(x.status)) || null;
      setReq(open);
      if (open) {
        setRows(Object.fromEntries((open.receipts || []).map((r) => [r.id, [{ no: 1, amount: r.applied }]])));
      }
    } catch { setReq(null); }
  }, [dealId]);
  useEffect(() => { load(); }, [load]);

  const manual = req?.mode === "manual_keuangan";
  const errs = useMemo(() => (req && manual ? mappingErrors(req, rows) : []), [req, rows, manual]);
  if (!req) return null;

  const patch = (rid, i, p) => setRows((r) => ({ ...r, [rid]: r[rid].map((x, j) => (j === i ? { ...x, ...p } : x)) }));
  const add = (rid) => setRows((r) => ({ ...r, [rid]: [...r[rid], { no: 1, amount: 0 }] }));
  const del = (rid, i) => setRows((r) => ({ ...r, [rid]: r[rid].filter((_, j) => j !== i) }));

  const submit = async (cancel = false) => {
    setBusy(true);
    try {
      if (cancel) {
        await api.post(`/finance/scheme-changes/${req.id}/cancel`, { reason });
        toast.success("Permintaan ganti skema dibatalkan; jadwal lama tetap berlaku.");
      } else {
        const body = { reason, confirm: !manual };
        if (manual) {
          body.mapping = (req.receipts || []).map((r) => ({
            receipt_id: r.id, allocations: (rows[r.id] || []).filter((x) => Number(x.amount) > 0)
              .map((x) => ({ no: Number(x.no), amount: Number(x.amount) })) }));
        }
        await api.post(`/finance/scheme-changes/${req.id}/apply`, body);
        toast.success("Skema diganti dan alokasi kuitansi dipetakan ke termin baru.");
      }
      setReason(""); await load(); onChanged && onChanged();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal memproses permintaan.");
    } finally { setBusy(false); }
  };

  const proposal = Object.fromEntries((req.proposal || []).map((p) => [p.receipt_id, p.allocations]));
  const reasonOk = reason.trim().length >= 10;
  return (
    <div data-testid="scheme-change-panel" className="space-y-3 rounded-lg border border-amber-400 bg-amber-50/60 p-3 dark:bg-amber-950/20">
      <div>
        <h4 className="font-heading text-sm font-semibold">Ganti skema ditahan — menunggu pemetaan alokasi</h4>
        <p className="text-xs text-muted-foreground">
          Skema baru <b>{req.target_scheme_label}</b> belum berlaku karena sudah ada pembayaran {formatIDR(req.paid_total)}.
          Mode: {MODE_LABEL[req.mode] || req.mode}. Jadwal dan kuitansi lama tetap berlaku sampai ini selesai; mengubah alokasi tidak mengubah kas atau jurnal.
        </p>
      </div>
      <div className="grid gap-1 text-xs">
        <p className="font-medium">Termin skema baru</p>
        {(req.preview || []).map((p) => (
          <div key={p.no} className="flex justify-between"><span>{p.no}. {p.label}{p.payer === "bank" ? " (porsi bank)" : ""}</span><span className="tabular-nums">{formatIDR(p.amount)}</span></div>
        ))}
      </div>
      <div className="space-y-2">
        {(req.receipts || []).map((r) => (
          <div key={r.id} data-testid="scheme-change-receipt" className="rounded-md border bg-card p-2 text-xs">
            <div className="flex justify-between font-medium"><span>{r.receipt_no} · {r.method}</span><span className="tabular-nums">{formatIDR(r.applied)}</span></div>
            <div className="text-muted-foreground">Alokasi lama: {(r.allocations || []).map((a) => `${a.label} ${formatIDR(a.amount)}`).join(", ") || "-"}</div>
            {manual ? (
              <div className="mt-1 space-y-1">
                {(rows[r.id] || []).map((x, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Select value={String(x.no)} onValueChange={(v) => patch(r.id, i, { no: Number(v) })}>
                      <SelectTrigger data-testid="scheme-change-term" className="h-8 flex-1"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {(req.preview || []).map((p) => <SelectItem key={p.no} value={String(p.no)}>{p.no}. {p.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <RupiahInput data-testid="scheme-change-amount" className="h-8 w-40" value={x.amount}
                      onChange={(e) => patch(r.id, i, { amount: e.target.value === "" ? 0 : Number(e.target.value) })} />
                    <Button size="icon" variant="ghost" disabled={(rows[r.id] || []).length <= 1} onClick={() => del(r.id, i)} aria-label="Hapus baris">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
                <Button size="sm" variant="secondary" onClick={() => add(r.id)}><Plus className="mr-1 h-3 w-3" /> Tambah baris</Button>
              </div>
            ) : (
              <div className="mt-1 text-muted-foreground">
                Hitungan sistem: {(proposal[r.id] || []).map((a) => `termin ${a.no} ${formatIDR(a.amount)}`).join(", ")}
              </div>
            )}
          </div>
        ))}
      </div>
      {errs.length ? <ul data-testid="scheme-change-errors" className="list-disc pl-5 text-xs text-destructive">{errs.map((e) => <li key={e}>{e}</li>)}</ul> : null}
      {mayApply ? (
        <div className="space-y-2">
          <Textarea data-testid="scheme-change-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
            placeholder="Alasan (wajib, min. 10 karakter) — dicatat pada permintaan dan kuitansi" />
          <div className="flex gap-2">
            <Button data-testid="scheme-change-apply" disabled={busy || !reasonOk || errs.length > 0} onClick={() => submit(false)}>
              {manual ? "Terapkan pemetaan" : "Konfirmasi hitungan sistem"}
            </Button>
            <Button data-testid="scheme-change-cancel" variant="outline" disabled={busy || !reasonOk} onClick={() => submit(true)}>
              Batalkan permintaan
            </Button>
          </div>
        </div>
      ) : <p className="text-xs text-muted-foreground">Hanya Keuangan yang berwenang (finance:approve) yang dapat menerapkan atau membatalkannya.</p>}
    </div>
  );
}
