import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import QuotationBreakdown from "@/components/quotations/QuotationBreakdown";
import PricingFields, { EMPTY_PRICING, pricingPayload } from "@/components/pricing/PricingFields";
import { allinPayload } from "@/components/pricing/AllinSchemeField";
import { formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";
import { QUOTE, QUOTE_PRICING } from "@/constants/testIds";

const EMPTY = { unit_id: "", discount_reason: "", valid_days: "", note: "", booking_fee: "", ...EMPTY_PRICING };
const IDS = { ...QUOTE, ...QUOTE_PRICING };

/**
 * QuotationForm — buat/revisi penawaran dengan SIMULASI dulu.
 *
 * Form ini IDENTIK dengan dialog Buat Reservasi (PricingFields + skema all-in + booking fee):
 * komponen pembayaran yang dijanjikan di penawaran = yang dibawa ke reservasi saat konversi.
 */
export default function QuotationForm({ open, onOpenChange, leadId, source, onDone }) {
  const [form, setForm] = useState(EMPTY);
  const [units, setUnits] = useState([]);
  const [schemes, setSchemes] = useState([]);
  const [addonMaster, setAddonMaster] = useState([]);
  const [calc, setCalc] = useState(null);
  const [stale, setStale] = useState(false);
  const [simBusy, setSimBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setError(""); setCalc(null); setStale(false);
    setForm(source ? {
      ...EMPTY,
      unit_id: source.unit_id || "", scheme_id: source.scheme?.id || "",
      discount_scheme_id: source.discount_scheme?.rule_id || "",
      promo_id: source.promo?.rule_id || "", coupon_code: source.coupon_code || "",
      discount_reason: source.discount_reason || "", valid_days: source.valid_days || "",
      note: source.note || "",
      booking_fee: source.booking_fee_gross ?? source.booking_fee ?? "",
      allin: { scheme_id: source.allin_scheme_id || source.costs?.scheme_id || "", manual: false, items: [], reason: "" },
      kpr: {
        tenor_months: source.kpr?.tenor_months || "",
        annual_rate_pct: source.kpr?.annual_rate_pct || "",
        dp_pct: source.kpr?.dp_pct || "",
      },
      addons: (source.addons || []).map((a) => ({ code: a.code, qty: a.qty || 1, name: a.name })),
    } : EMPTY);
    (async () => {
      try {
        const o = await api.get("/quotations/options");
        const d = o.data.data || {};
        const list = d.units || [];
        setUnits(source?.unit_id && !list.some((x) => x.id === source.unit_id)
          ? [{ id: source.unit_id, code: source.unit_code, price: source.base_price }, ...list]
          : list);
        setSchemes(d.schemes || []);
        setAddonMaster(d.addons || []);
        if (!source) {
          const fee = await api.get("/settings/effective", { params: { keys: "booking_fee.default_amount" } }).catch(() => null);
          const v = fee?.data?.data?.["booking_fee.default_amount"];
          if (v != null) setForm((f) => ({ ...f, booking_fee: String(v) }));
        }
      } catch (e) {
        setError(e?.response?.data?.detail || "Gagal memuat data master.");
      }
    })();
  }, [open, source]);

  const unitPrice = Number((units.find((u) => u.id === form.unit_id) || {}).price) || calc?.net_price || 0;
  const allinPreview = form.allin?.preview;

  const payload = () => ({
    unit_id: form.unit_id, lead_id: leadId, ...pricingPayload(form), ...allinPayload(form.allin),
    booking_fee: form.booking_fee === "" || form.booking_fee == null ? null : Number(form.booking_fee) || 0,
  });

  const simulate = async () => {
    if (!form.unit_id) { setError("Pilih unit lebih dulu."); return; }
    setSimBusy(true); setError("");
    try {
      const res = await api.post("/quotations/simulate", payload());
      setCalc(res.data.data); setStale(false);
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal menghitung simulasi.");
    } finally { setSimBusy(false); }
  };

  const save = async () => {
    if (!form.unit_id) { setError("Pilih unit lebih dulu."); return; }
    setBusy(true); setError("");
    try {
      const body = {
        ...payload(),
        valid_days: form.valid_days === "" ? null : Number(form.valid_days),
        note: form.note.trim() || null,
        discount_reason: form.discount_reason.trim() || null,
      };
      const res = source?.id
        ? await api.post(`/quotations/${source.id}/revise`, body)
        : await api.post("/quotations", body);
      toast.success(res.data.message || "Penawaran tersimpan.");
      onOpenChange(false);
      onDone?.(res.data.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal menyimpan penawaran.");
    } finally { setBusy(false); }
  };

  const set = (patch) => {
    setForm((f) => ({ ...f, ...patch }));
    if (patch.allin && Object.keys(patch).length === 1) { setStale(!!calc); return; }
    setCalc(null); setStale(false);
  };
  const setKpr = (patch) => { setForm((f) => ({ ...f, kpr: { ...f.kpr, ...patch } })); setCalc(null); };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={QUOTE.dialog} className="max-h-[94vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>
            {source?.id ? `Revisi penawaran ${source.no}` : "Buat penawaran harga"}
          </DialogTitle>
          <DialogDescription>
            Form ini sama dengan Buat Reservasi: harga, add-on, skema all-in, potongan, booking fee,
            termin, dan simulasi KPR dihitung SERVER dari master yang sama dengan tagihan.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Unit yang ditawarkan</Label>
              <Select value={form.unit_id} onValueChange={(v) => set({ unit_id: v })}>
                <SelectTrigger data-testid={QUOTE.unitSelect} aria-label="Unit yang ditawarkan">
                  <SelectValue placeholder="Pilih unit tersedia" />
                </SelectTrigger>
                <SelectContent>
                  {units.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.code}{u.type ? ` · ${u.type}` : ""}{u.price ? ` · ${formatIDR(u.price)}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <PricingFields form={form} set={set} setKpr={setKpr} unitId={form.unit_id}
              leadId={leadId} schemes={schemes} addonMaster={addonMaster} ids={IDS}
              showCosts price={unitPrice} />

            <div className="space-y-1.5">
              <Label htmlFor="q-fee">Booking fee / tanda jadi (Rp)</Label>
              <RupiahInput id="q-fee" data-testid="quotation-booking-fee" value={form.booking_fee}
                onChange={(e) => set({ booking_fee: e.target.value })} />
              <p className="text-xs text-muted-foreground">Dibayar saat keep unit; dialihkan ke termin saat SPR sah — bukan potongan harga.</p>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="q-valid">Masa berlaku (hari)</Label>
                <Input id="q-valid" type="number" value={form.valid_days} placeholder="7"
                  onChange={(e) => set({ valid_days: e.target.value })} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="q-disc-reason">Alasan diskon (wajib bila perlu persetujuan)</Label>
              <Textarea id="q-disc-reason" rows={2} data-testid={QUOTE.discountReason}
                value={form.discount_reason}
                placeholder="Mis. pembeli membandingkan dengan kompetitor; margin masih sehat."
                onChange={(e) => set({ discount_reason: e.target.value })} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="q-note">Catatan untuk pembeli</Label>
              <Textarea id="q-note" rows={2} value={form.note}
                onChange={(e) => set({ note: e.target.value })} />
            </div>
          </div>

          <div className="space-y-3 lg:sticky lg:top-0 lg:self-start">
            <Button type="button" variant="secondary" className="w-full"
              data-testid={QUOTE.simulateBtn} disabled={simBusy} onClick={simulate}>
              <RefreshCw className={`mr-1.5 h-4 w-4 ${simBusy ? "animate-spin" : ""}`} />
              Hitung simulasi
            </Button>
            {error ? (
              <p data-testid="quotation-error" className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
            ) : null}
            {calc ? (
              <div data-testid="quotation-breakdown-wrap">
                {stale ? (
                  <p data-testid="quotation-recalc-hint" className="mb-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-900">
                    Skema biaya berubah — tekan <b>Hitung simulasi</b> lagi agar ringkasan biaya ikut diperbarui.
                  </p>
                ) : null}
                <QuotationBreakdown calc={calc} stale={stale} />
                {!calc.costs && allinPreview?.components?.length ? (
                  <div data-testid="quotation-costs-summary" className="mt-2 rounded-lg border border-dashed bg-card p-3 text-sm">
                    <div className="flex justify-between"><span>Pratinjau biaya · {allinPreview.scheme_name}</span>
                      <strong>{formatIDR(allinPreview.components.filter((c) => c.treatment !== "developer_borne").reduce((t, c) => t + (c.amount || 0), 0))}</strong></div>
                    <p className="mt-1 text-[11px] text-amber-800">Belum termasuk potongan promo — tekan <b>Hitung simulasi</b> untuk angka resmi.</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed bg-card p-4 text-sm text-muted-foreground">
                Tekan “Hitung simulasi” untuk melihat rincian harga, add-on, biaya all-in, potongan,
                termin, dan angsuran KPR sebelum penawaran disimpan.
              </p>
            )}
            {calc?.needs_discount_approval ? (
              <div data-testid="quotation-approval-box" className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <p>Potongan ini memerlukan persetujuan manajer — penawaran akan berstatus <b>menunggu persetujuan</b> dan alasan diskon wajib diisi.</p>
                <ul className="mt-1 list-disc pl-4 text-xs">
                  {(calc.approval_reasons || []).map((r, i) => <li key={i}>{r.label}</li>)}
                </ul>
              </div>
            ) : null}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Batal</Button>
          <Button data-testid={QUOTE.submitBtn} disabled={busy} onClick={save}>
            {busy ? "Menyimpan…" : (source?.id ? "Simpan revisi" : "Simpan penawaran")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
