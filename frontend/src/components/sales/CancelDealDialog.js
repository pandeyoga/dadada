import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Ban } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";
import { DEAL_CANCEL } from "@/constants/testIds";

const MODES = [
  { value: "full", id: DEAL_CANCEL.modeFull, label: "Refund penuh", hint: "Seluruh booking fee dikembalikan ke pembeli." },
  { value: "partial", id: DEAL_CANCEL.modePartial, label: "Refund sebagian", hint: "Sebagian dikembalikan, sisanya hangus (pendapatan lain-lain)." },
  { value: "forfeit", id: DEAL_CANCEL.modeForfeit, label: "Hangus", hint: "Booking fee tidak dikembalikan — dibukukan sebagai pendapatan lain-lain." },
];

/**
 * CancelDealDialog — batalkan reservasi/booking SATU langkah dari profil lead.
 * Sales boleh membatalkan bila booking fee belum dibayar; bila sudah dibayar wajib admin
 * dan memilih perlakuan uang (refund penuh / sebagian / hangus).
 */
export default function CancelDealDialog({ deal, open, onOpenChange, onDone }) {
  const [pv, setPv] = useState(null);
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState("full");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("bank");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !deal?.id) return;
    setPv(null); setReason(""); setMode("full"); setAmount("");
    api.get(`/deals/${deal.id}/cancel-preview`).then((r) => setPv(r.data.data))
      .catch((e) => setPv({ can_cancel: false, blocked_reason: e?.response?.data?.detail || "Gagal memuat pratinjau." }));
  }, [open, deal?.id]);

  const refundable = pv?.booking_fee?.refundable || 0;
  const needMode = refundable > 0;
  const partialBad = mode === "partial" && (Number(amount) <= 0 || Number(amount) >= refundable);
  const valid = pv?.can_cancel && reason.trim().length >= 5 && (!needMode || !partialBad);

  const submit = async () => {
    setBusy(true);
    try {
      const res = await api.post(`/deals/${deal.id}/cancel`, {
        reason: reason.trim(),
        refund_mode: needMode ? mode : null,
        refund_amount: mode === "partial" ? Number(amount) : null,
        method: method === "kas" ? "cash" : "transfer",
      });
      toast.success(res.data.message || "Reservasi dibatalkan.");
      onOpenChange(false); onDone?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal membatalkan reservasi.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={DEAL_CANCEL.dialog} className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Ban className="h-4 w-4 text-rose-600" /> Batalkan Reservasi Unit {deal?.unit_code || ""}
          </DialogTitle>
          <DialogDescription>
            Unit langsung kembali ke stok (tersedia), tagihan yang belum dibayar ditutup, dan tahap lead
            mundur ke Nurturing. Aksi ini tercatat di audit.
          </DialogDescription>
        </DialogHeader>

        {!pv ? <p className="text-sm text-muted-foreground">Memeriksa reservasi…</p> : (
          <div className="space-y-3">
            <div data-testid={DEAL_CANCEL.summary} className="grid grid-cols-2 gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
              <span className="text-muted-foreground">Status deal</span><span className="text-right font-medium">{pv.deal_status}</span>
              <span className="text-muted-foreground">Booking fee</span>
              <span className="text-right font-medium">{pv.booking_fee?.invoice_no ? formatIDR(pv.booking_fee.amount) : "—"}</span>
              <span className="text-muted-foreground">Sudah dibayar</span>
              <span className={`text-right font-medium ${pv.booking_fee?.paid ? "text-emerald-700" : ""}`}>
                {formatIDR(pv.booking_fee?.paid || 0)}
              </span>
              {pv.contract ? (<><span className="text-muted-foreground">Kontrak</span>
                <span className="text-right font-medium">{pv.contract.no} · {pv.contract.state} → dibatalkan</span></>) : null}
            </div>

            {!pv.can_cancel ? (
              <div data-testid={DEAL_CANCEL.blocked} className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{pv.blocked_reason}</span>
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="dc-reason">Alasan pembatalan</Label>
                  <Textarea id="dc-reason" data-testid={DEAL_CANCEL.reason} rows={2} value={reason}
                    placeholder="Mis. pembeli mundur, ganti unit, KPR ditolak…"
                    onChange={(e) => setReason(e.target.value)} />
                </div>
                {needMode ? (
                  <div className="space-y-2 rounded-lg border p-3">
                    <p className="text-sm font-medium">Perlakuan booking fee yang sudah dibayar ({formatIDR(refundable)})</p>
                    <RadioGroup value={mode} onValueChange={setMode} className="gap-2">
                      {MODES.map((m) => (
                        <label key={m.value} htmlFor={m.id} className="flex cursor-pointer items-start gap-2 rounded-md border p-2 hover:bg-muted/40">
                          <RadioGroupItem id={m.id} data-testid={m.id} value={m.value} className="mt-0.5" />
                          <span><span className="text-sm font-medium">{m.label}</span>
                            <span className="block text-xs text-muted-foreground">{m.hint}</span></span>
                        </label>
                      ))}
                    </RadioGroup>
                    {mode === "partial" ? (
                      <div className="space-y-1.5">
                        <Label htmlFor="dc-amount">Nominal dikembalikan (Rp)</Label>
                        <RupiahInput id="dc-amount" data-testid={DEAL_CANCEL.amount} value={amount}
                          onChange={(e) => setAmount(e.target.value)} placeholder="0" />
                        {partialBad && amount ? (
                          <p className="text-xs text-rose-700">Harus lebih dari 0 dan kurang dari {formatIDR(refundable)}.</p>
                        ) : null}
                      </div>
                    ) : null}
                    {mode !== "forfeit" ? (
                      <div className="space-y-1.5">
                        <Label>Sumber kas refund</Label>
                        <ReferenceSelect group="cash_source" value={method} onChange={setMethod} testId={DEAL_CANCEL.method} />
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Tutup</Button>
          <Button data-testid={DEAL_CANCEL.submit} variant="destructive" disabled={!valid || busy} onClick={submit}>
            {busy ? "Memproses…" : "Batalkan Reservasi"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
