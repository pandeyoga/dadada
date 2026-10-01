import React, { useState } from "react";
import { toast } from "sonner";
import { ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";

const STATE = {
  pending: { label: "Potongan menunggu persetujuan", cls: "text-amber-800 bg-amber-50 border-amber-200", Icon: ShieldAlert },
  approved: { label: "Potongan disetujui", cls: "text-emerald-800 bg-emerald-50 border-emerald-200", Icon: ShieldCheck },
  rejected: { label: "Potongan ditolak", cls: "text-rose-800 bg-rose-50 border-rose-200", Icon: ShieldX },
};

/** Lencana persetujuan potongan pada reservasi (jalur SPR) + keputusan manajer (`pricing:approve`). */
export default function PricingApprovalBadge({ deal, onChanged }) {
  const { can, user } = useAuth();
  const [open, setOpen] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const pa = deal?.pricing_approval;
  if (!pa?.state) return null;
  const meta = STATE[pa.state] || STATE.pending;
  const mayDecide = pa.state === "pending" && can("pricing", "approve") && pa.requested_by !== user?.email;

  const decide = async () => {
    setBusy(true);
    try {
      const res = await api.post(`/deals/${deal.id}/pricing-approval`, { approve: open === "approve", reason });
      toast.success(res.data.message || "Keputusan tersimpan.");
      setOpen(null); setReason("");
      onChanged && onChanged(res.data.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan keputusan.");
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="deal-pricing-approval" data-state={pa.state} data-deal-id={deal.id}
      className={`mt-1 inline-flex flex-wrap items-center gap-1.5 rounded-md border px-2 py-1 text-xs ${meta.cls}`}>
      <meta.Icon className="h-3.5 w-3.5" /> {meta.label}
      {pa.decision_reason ? <span className="text-muted-foreground">· {pa.decision_reason}</span> : null}
      {mayDecide ? (
        <>
          <Button data-testid="deal-pricing-approve-btn" size="sm" variant="secondary" className="h-6 px-2"
            onClick={() => setOpen("approve")}>Setujui</Button>
          <Button data-testid="deal-pricing-reject-btn" size="sm" variant="ghost" className="h-6 px-2"
            onClick={() => setOpen("reject")}>Tolak</Button>
        </>
      ) : null}
      <Dialog open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <DialogContent className="max-w-md" data-testid="deal-pricing-decision-dialog">
          <DialogHeader>
            <DialogTitle>{open === "approve" ? "Setujui" : "Tolak"} potongan reservasi unit {deal.unit_code}</DialogTitle>
            <DialogDescription>
              {(pa.reasons || []).map((r, i) => <span key={i} className="block">• {r.label}</span>)}
              {pa.reason ? <span className="block mt-1">Alasan sales: {pa.reason}</span> : null}
            </DialogDescription>
          </DialogHeader>
          <Textarea data-testid="deal-pricing-decision-reason" rows={3} value={reason}
            placeholder="Alasan keputusan (min. 5 huruf)" onChange={(e) => setReason(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(null)}>Batal</Button>
            <Button data-testid="deal-pricing-decision-submit" variant={open === "approve" ? "default" : "destructive"}
              disabled={busy || reason.trim().length < 5} onClick={decide}>
              {open === "approve" ? "Setujui" : "Tolak"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
