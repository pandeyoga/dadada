import React, { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RupiahInput } from "@/components/ui/rupiah-input";
import api from "@/services/apiClient";

const KEYS = "quotation.discount_max_pct_sales,pricing.approval_min_amount";

/** Ambang GLOBAL persetujuan manajer — satu aturan untuk penawaran & reservasi/SPR. */
export default function PricingApprovalSettings() {
  const [pct, setPct] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/settings/effective", { params: { keys: KEYS } }).then((r) => {
    const d = r.data.data || {};
    setPct(String(d["quotation.discount_max_pct_sales"] ?? ""));
    setAmount(String(d["pricing.approval_min_amount"] ?? 0));
  }).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/settings/quotation.discount_max_pct_sales", { value: Number(pct) || 0 });
      await api.put("/settings/pricing.approval_min_amount", { value: Number(amount) || 0 });
      toast.success("Ambang persetujuan tersimpan — berlaku untuk penawaran & SPR berikutnya.");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan ambang persetujuan.");
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="pricing-approval-settings" className="rounded-lg border bg-card p-3 space-y-2">
      <p className="flex items-center gap-1.5 text-sm font-medium"><ShieldCheck className="h-4 w-4" /> Ambang global persetujuan manajer</p>
      <p className="text-xs text-muted-foreground">
        Aturan bermode <b>ikut ambang organisasi</b> dijumlahkan lalu dibandingkan dengan dua ambang ini.
        Mode <b>selalu</b> / <b>tidak pernah</b> pada tiap skema diskon, promo, dan kupon menimpanya.
        Berlaku sama untuk penawaran maupun reservasi langsung (SPR menunggu persetujuan).
      </p>
      <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div className="space-y-1">
          <Label htmlFor="appr-pct">Batas potongan harga tanpa persetujuan (%)</Label>
          <Input id="appr-pct" data-testid="pricing-approval-pct" type="number" step="0.1" min="0" max="100"
            value={pct} onChange={(e) => setPct(e.target.value)} />
        </div>
        <div className="space-y-1">
          <Label htmlFor="appr-amount">Ambang nominal total potongan (Rp, 0 = mati)</Label>
          <RupiahInput id="appr-amount" data-testid="pricing-approval-amount" value={amount}
            onChange={(e) => setAmount(e.target.value)} />
        </div>
        <Button data-testid="pricing-approval-save" size="sm" disabled={busy} onClick={save}>Simpan</Button>
      </div>
    </div>
  );
}
