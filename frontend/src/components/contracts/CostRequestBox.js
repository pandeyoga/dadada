import React, { useCallback, useEffect, useState } from "react";
import { History, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";
import { W2C } from "@/constants/testIds";

const val = (f, v) => (v === null || v === undefined ? "belum diisi" : (f === "dp_percent" ? `${v}%` : formatIDR(v)));
const STATUS = { approved: "Disetujui", rejected: "Ditolak", cancelled: "Dibatalkan" };

/**
 * Permohonan isian bebas biaya kontrak (W2-C #6): menurut model biaya kontrak, isian BPHTB/notaris/bank/asuransi/PPh dapat DITAHAN
 * sampai pemegang izin persetujuan Keuangan (orang lain dari pemohon) menyetujuinya. Angka lama tetap berlaku selama menunggu.
 */
export default function CostRequestBox({ contract, onChanged }) {
  const { user, can } = useAuth();
  const [list, setList] = useState([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get(`/contracts/${contract.id}/cost-requests`).then((r) => setList(r.data.data || [])).catch(() => setList([]));
  }, [contract.id]);
  useEffect(() => { load(); }, [load, contract.updated_at, contract.costs_updated_at]);

  const pending = list.find((r) => r.status === "pending");
  const history = list.filter((r) => r.status !== "pending");
  if (!pending && !history.length) return null;
  const mine = pending && pending.requested_by === user?.email;
  const mayDecide = pending && !mine && can("finance", "approve");

  const act = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); setNote(""); load(); onChanged && onChanged(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal memproses permohonan."); } finally { setBusy(false); }
  };

  return (
    <div data-testid={W2C.reqBox} className="space-y-2 rounded-lg border bg-background p-3">
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <ShieldCheck className="h-3.5 w-3.5" /> Permohonan isian biaya kontrak
      </p>
      {pending ? (
        <div data-testid={W2C.reqRow} data-status="pending" className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
          <p><b>Menunggu persetujuan Keuangan</b> — diajukan {pending.requested_by}. Angka lama tetap berlaku sampai disetujui.</p>
          <ul className="list-disc pl-4">
            {pending.changes.map((c) => <li key={c.field}>{c.label}: {val(c.field, c.dari)} → <b>{c.ke === null ? "dikosongkan" : val(c.field, c.ke)}</b></li>)}
          </ul>
          {pending.note ? <p>Catatan: {pending.note}</p> : null}
          {mayDecide ? (
            <div className="space-y-1">
              <Textarea data-testid={W2C.reqNote} rows={2} className="bg-background" placeholder="Catatan keputusan (wajib bila menolak)"
                value={note} onChange={(e) => setNote(e.target.value)} />
              <div className="flex gap-2">
                <Button data-testid={W2C.reqApprove} size="sm" disabled={busy}
                  onClick={() => act(() => api.post(`/cost-requests/${pending.id}/decide`, { approve: true, note }), "Disetujui — isian biaya berlaku.")}>Setujui</Button>
                <Button data-testid={W2C.reqReject} size="sm" variant="outline" disabled={busy}
                  onClick={() => act(() => api.post(`/cost-requests/${pending.id}/decide`, { approve: false, note }), "Permohonan ditolak.")}>Tolak</Button>
              </div>
            </div>
          ) : null}
          {mine ? (
            <Button data-testid={W2C.reqCancel} size="sm" variant="outline" disabled={busy}
              onClick={() => act(() => api.post(`/cost-requests/${pending.id}/cancel`), "Permohonan dibatalkan.")}>Batalkan permohonan</Button>
          ) : null}
          {!mine && !mayDecide ? <p className="text-[11px]">Keputusan ada pada pemegang izin persetujuan Keuangan (bukan pemohon).</p> : null}
        </div>
      ) : null}
      {history.length ? (
        <ul className="space-y-1 text-xs">
          {history.slice(0, 5).map((r) => (
            <li key={r.id} data-testid={W2C.reqRow} data-status={r.status} className="flex items-start gap-1.5 text-muted-foreground">
              <History className="mt-0.5 h-3 w-3 shrink-0" />
              <span>{STATUS[r.status] || r.status} {String(r.decided_at || r.requested_at).slice(0, 10)}{r.decided_by ? ` oleh ${r.decided_by}` : ""}:
                {" "}{r.changes.map((c) => `${c.label} ${c.ke === null ? "dikosongkan" : val(c.field, c.ke)}`).join(", ")}{r.decision_note ? ` · ${r.decision_note}` : ""}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
