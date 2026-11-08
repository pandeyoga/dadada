import React, { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/services/apiClient";
import { revocable } from "@/components/config/WebhookChannelTable";
import { webhookError } from "@/components/config/WebhookSecretDialog";
import { WEBHOOK_SEC } from "@/constants/testIds";

/**
 * Cabut rahasia tersimpan satu kanal — SELALU lewat konfirmasi. Yang bisa dicabut hanya nilai yang tersimpan di sistem;
 * nilai dari ENV server tidak tersentuh. Bila hanya satu butir yang bisa dicabut, ia langsung terpilih.
 */
export default function WebhookClearDialog({ channel, onClose, onSaved }) {
  const rv = revocable(channel);
  const [pick, setPick] = useState({ secret: rv.secret && !rv.verify, verify: rv.verify && !rv.secret });
  const [busy, setBusy] = useState(false);
  const chosen = (pick.secret && rv.secret) || (pick.verify && rv.verify);
  const envFallback = channel.secret_source === "db" && (channel.env_secret || []).length > 0;

  const confirm = async () => {
    const body = {};
    if (pick.secret && rv.secret) body.secret = "__clear__";
    if (pick.verify && rv.verify) body.verify_token = "__clear__";
    setBusy(true);
    try {
      const r = await api.put(`/webhooks/secrets/${channel.channel}`, body);
      toast.success(`Rahasia ${channel.label} dicabut.`);
      onSaved(r.data?.data);
    } catch (e) {
      toast.error(webhookError(e, "Gagal mencabut rahasia webhook."));
    } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o && !busy) onClose(); }}>
      <DialogContent data-testid={WEBHOOK_SEC.clearDialog} className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-600" /> Cabut rahasia {channel.label}?
          </DialogTitle>
          <DialogDescription>
            Setelah dicabut, kanal ini kembali menerima permintaan dari siapa pun (mode simulasi) sampai rahasia
            diisi lagi{envFallback ? ", kecuali nilai dari ENV server masih terpasang (ENV dipakai sebagai cadangan)" : ""}.
            Pastikan penyedia tidak lagi mengandalkan tanda tangan ini.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 text-sm">
          {rv.secret ? (
            <label className="flex items-center gap-2">
              <Checkbox data-testid={WEBHOOK_SEC.clearPickSecret} checked={pick.secret}
                onCheckedChange={(v) => setPick((p) => ({ ...p, secret: !!v }))} />
              Rahasia / App Secret
            </label>
          ) : null}
          {rv.verify ? (
            <label className="flex items-center gap-2">
              <Checkbox data-testid={WEBHOOK_SEC.clearPickVerify} checked={pick.verify}
                onCheckedChange={(v) => setPick((p) => ({ ...p, verify: !!v }))} />
              Verify token
            </label>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="outline" data-testid={WEBHOOK_SEC.clearCancel} disabled={busy} onClick={onClose}>Batal</Button>
          <Button variant="destructive" data-testid={WEBHOOK_SEC.clearConfirm} disabled={busy || !chosen} onClick={confirm}>
            {busy ? "Mencabut…" : "Cabut rahasia"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
