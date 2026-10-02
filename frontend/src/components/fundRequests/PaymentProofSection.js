import React, { useState } from "react";
import { toast } from "sonner";
import { FileText, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import { fileUrl } from "@/utils/photoSrc";
import api from "@/services/apiClient";
import { FUNDREQ } from "@/constants/testIds";

const isImage = (f) => (f.content_type || "").startsWith("image/");

/** Bukti pembayaran dari approver — terlihat oleh pemohon; approver bisa menambah bila belum ada. */
export default function PaymentProofSection({ req, canApprove, onUpdated }) {
  const [ids, setIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const proofs = req.payment_proofs || [];
  const paid = Boolean(req.disbursed_at);
  if (!paid) return null;

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.post(`/fund-requests/${req.id}/payment-proof`, { proof_ids: ids });
      toast.success("Bukti pembayaran disimpan.");
      setIds([]);
      onUpdated?.(res.data.data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan bukti."); }
    finally { setSaving(false); }
  };

  return (
    <div data-testid={FUNDREQ.proofSection} className="rounded-xl border bg-card p-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Receipt className="h-3.5 w-3.5" /> Bukti pembayaran
      </p>
      {proofs.length ? (
        <div className="grid grid-cols-3 gap-2">
          {proofs.map((f) => (
            <a key={f.id} data-testid={FUNDREQ.proofItem} href={fileUrl(f.id)} target="_blank" rel="noreferrer"
              className="group block overflow-hidden rounded-lg border bg-muted/30" title={f.filename}>
              {isImage(f) ? (
                <img src={fileUrl(f.id)} alt={f.filename || "Bukti bayar"}
                  className="h-24 w-full object-cover transition-transform group-hover:scale-105" />
              ) : (
                <div className="flex h-24 flex-col items-center justify-center gap-1 p-2 text-xs text-primary">
                  <FileText className="h-6 w-6" /><span className="line-clamp-2 text-center">{f.filename}</span>
                </div>
              )}
            </a>
          ))}
        </div>
      ) : (
        <p data-testid={FUNDREQ.proofEmpty} className="text-sm text-muted-foreground">
          Belum ada foto bukti pembayaran dari approver.
        </p>
      )}
      {canApprove ? (
        <div className="mt-3 space-y-2 border-t pt-3">
          <EvidenceUploader value={ids} onChange={setIds} ownerType="fund_request_payment" ownerId={req.id} max={3}
            accept="image/*,application/pdf" testId={FUNDREQ.proofAddInput} label="Tambah foto bukti pembayaran" />
          <Button size="sm" data-testid={FUNDREQ.proofAddSubmit} disabled={!ids.length || saving} onClick={save}>
            {saving ? "Menyimpan…" : "Simpan bukti"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
