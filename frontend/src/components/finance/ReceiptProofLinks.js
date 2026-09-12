import React, { useState } from "react";
import { Paperclip, Plus } from "lucide-react";
import { toast } from "sonner";

import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/services/apiClient";
import { photoSrc } from "@/utils/photoSrc";

/**
 * ReceiptProofLinks — tautan BUKTI BAYAR sebuah kuitansi (struk transfer/foto) yang tampil
 * di semua laporan pembayaran (staf & portal). `canAttach` (finance:update) menambahkan
 * tombol lampirkan untuk kuitansi lama yang belum berbukti (PATCH /finance/ar/receipts/{id}/proof).
 */
export default function ReceiptProofLinks({ receipt, portal = false, canAttach = false, onChanged, size = "xs" }) {
  const ids = receipt?.proof_file_ids || [];
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!files.length) { toast.error("Pilih berkas bukti dulu."); return; }
    setBusy(true);
    try {
      await api.patch(`/finance/ar/receipts/${receipt.id}/proof`, { proof_file_ids: files });
      toast.success("Bukti bayar dilampirkan ke kuitansi.");
      setOpen(false); setFiles([]);
      onChanged && onChanged();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal melampirkan bukti.");
    } finally { setBusy(false); }
  };

  const cls = size === "xs" ? "text-[11px]" : "text-xs";
  return (
    <span data-testid="receipt-proof" data-receipt-id={receipt?.id} data-count={ids.length}
      className={`inline-flex flex-wrap items-center gap-1 ${cls}`}>
      {ids.length ? ids.map((id, i) => (
        <a key={id} href={photoSrc({ file_id: id }, { portal })} target="_blank" rel="noreferrer"
          data-testid="receipt-proof-link"
          className="inline-flex items-center gap-0.5 rounded-full border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 font-medium text-emerald-800 hover:bg-emerald-100">
          <Paperclip className="h-3 w-3" /> Bukti {ids.length > 1 ? i + 1 : ""}
        </a>
      )) : (
        <span data-testid="receipt-proof-none" className="text-muted-foreground">tanpa bukti</span>
      )}
      {canAttach ? (
        <>
          <button type="button" data-testid="receipt-proof-attach" onClick={() => setOpen(true)}
            className="inline-flex items-center gap-0.5 text-primary hover:underline">
            <Plus className="h-3 w-3" /> lampirkan
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent className="max-w-md bg-background" data-testid="receipt-proof-dialog">
              <DialogHeader>
                <DialogTitle>Lampirkan bukti bayar</DialogTitle>
                <DialogDescription>
                  Kuitansi {receipt?.receipt_no || ""} · bukti disimpan utuh dan tampil di semua laporan pembayaran.
                </DialogDescription>
              </DialogHeader>
              <EvidenceUploader value={files} onChange={setFiles} ownerType="receipt_proof"
                ownerId={receipt?.id} testId="receipt-proof-input" label="Bukti bayar" />
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Batal</Button>
                <Button data-testid="receipt-proof-save" onClick={save} disabled={busy || !files.length}>
                  {busy ? "Menyimpan…" : "Simpan bukti"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      ) : null}
    </span>
  );
}
