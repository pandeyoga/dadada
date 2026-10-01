import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Landmark } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import { formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";
import { FINANCE } from "@/constants/testIds";
import CashAccountSelect from "@/components/cashBank/CashAccountSelect";

const openOf = (it) => Number(it.amount || 0) - Number(it.paid_amount || 0);
const isBank = (it) => it.payer === "bank" && !it.kpr_excluded;

/**
 * Terima pembayaran pembeli.
 *
 * Fase 26 (kebenaran uang): metode pembayaran diambil dari SSOT `/api/reference`
 * (dulu daftar lokal memuat nilai "other" yang tidak dikenal backend), dan bila jumlah
 * melebihi sisa tagihan, kasir HARUS menyetujui secara sadar bahwa kelebihannya dicatat
 * sebagai **titipan pelanggan** (akun 2-1450). Sebelumnya kelebihan bayar hilang tanpa jejak.
 *
 * Porsi BANK (termin yang dilunasi pencairan KPR) TIDAK diterima di sini: nominal bawaan =
 * termin pembeli yang jatuh tempo berikutnya, bukan seluruh sisa piutang. Pembeli yang memang
 * melunasi porsi KPR-nya sendiri → centang eksplisit (`allow_bank_portion`).
 *
 * deal: { deal_id, unit_code, outstanding }
 */
export default function ReceiptDialog({ open, onOpenChange, deal, onDone }) {
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("transfer");
  const [cashAccountId, setCashAccountId] = useState("");
  const [note, setNote] = useState("");
  const [allowOverpay, setAllowOverpay] = useState(false);
  const [allowBank, setAllowBank] = useState(false);
  const [proofFiles, setProofFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState([]);
  const [alloc, setAlloc] = useState({});

  const payable = items.filter((it) => allowBank || !isBank(it));
  const bankItems = items.filter(isBank);
  const bankOutstanding = bankItems.reduce((a, it) => a + openOf(it), 0);
  const outstanding = payable.reduce((a, it) => a + openOf(it), 0);

  const fifo = (total, list) => {
    let sisa = Number(total) || 0; const out = {};
    [...list].sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || ""))).forEach((it) => {
      const open = openOf(it);
      if (open <= 0 || sisa <= 0) return;
      const pay = Math.min(open, sisa); out[it.id] = pay; sisa -= pay;
    });
    return out;
  };

  useEffect(() => {
    if (open && deal?.deal_id) {
      setAllowBank(false);
      api.get(`/finance/ar/${deal.deal_id}`).then((r) => {
        const list = (r.data?.data?.items || []).filter((it) => openOf(it) > 0);
        setItems(list);
        // Bawaan = termin PEMBELI yang jatuh tempo paling awal, bukan seluruh sisa piutang.
        const buyer = list.filter((it) => !isBank(it))
          .sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || "")));
        const first = buyer[0] ? openOf(buyer[0]) : 0;
        setAmount(first ? String(first) : "");
        setAlloc(fifo(first, buyer));
      }).catch(() => { setItems([]); setAlloc({}); setAmount(""); });
    }
  }, [open, deal]);

  useEffect(() => {
    if (open) {
      setMethod("transfer");
      setNote("");
      setAllowOverpay(false);
      setProofFiles([]);
    }
  }, [open, deal]);

  const amt = Number(amount) || 0;
  const excess = Math.max(0, amt - outstanding);
  const blocked = excess > 0 && !allowOverpay;
  const allocSum = Object.values(alloc).reduce((a, v) => a + (Number(v) || 0), 0);
  const allocMismatch = payable.length > 0 && allocSum !== Math.min(amt, outstanding);
  const setAmountFifo = (v) => { setAmount(v); setAlloc(fifo(Math.min(Number(v) || 0, outstanding), payable)); };
  const toggleBank = (v) => {
    const on = !!v; setAllowBank(on);
    const list = items.filter((it) => on || !isBank(it));
    const total = list.reduce((a, it) => a + openOf(it), 0);
    setAlloc(fifo(Math.min(amt, total), list));
  };

  const submit = async () => {
    if (!deal?.deal_id) return;
    if (!amt || amt <= 0) { toast.error("Masukkan jumlah pembayaran yang valid."); return; }
    if (allocMismatch) { toast.error("Alokasi per termin harus sama dengan jumlah yang dibayar (di luar kelebihan)."); return; }
    if (!proofFiles.length) { toast.error("Bukti pembayaran wajib dilampirkan."); return; }
    setBusy(true);
    try {
      const res = await api.post("/finance/ar/receipts", {
        deal_id: deal.deal_id, amount: amt, method, note: note || null,
        allow_overpay: allowOverpay, allow_bank_portion: allowBank, cash_account_id: cashAccountId || null,
        proof_file_ids: proofFiles,
        allocations: Object.entries(alloc).filter(([, v]) => Number(v) > 0).map(([item_id, v]) => ({ item_id, amount: Number(v) })),
      });
      const rec = res.data?.data?.receipt || {};
      const dep = Number(rec.deposit_amount || 0);
      toast.success(
        dep > 0
          ? `Pembayaran diterima — ${formatIDR(dep)} dicatat sebagai titipan pelanggan.`
          : res.data?.data?.paid_off
            ? "Pembayaran diterima — AR LUNAS. Menunggu BAST."
            : "Pembayaran diterima & dialokasikan ke termin.");
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal mencatat pembayaran.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Terima Pembayaran</DialogTitle>
          <DialogDescription data-testid="ar-receipt-summary">
            {deal ? `Unit ${deal.unit_code || "-"} · Sisa porsi pembeli ${formatIDR(outstanding)}` : ""}
            {bankOutstanding > 0 && !allowBank ? ` · porsi bank ${formatIDR(bankOutstanding)} menunggu pencairan KPR` : ""}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="amt">Jumlah (Rp)</Label>
            <RupiahInput id="amt" value={amount} data-testid="ar-receipt-amount"
              onChange={(e) => setAmountFifo(e.target.value)} placeholder="0" />
            <p className="text-[11px] text-muted-foreground">
              Bawaan = termin pembeli yang jatuh tempo berikutnya. Ubah bebas; boleh sebagian, tidak harus lunas semua.
            </p>
          </div>
          {payable.length ? (
            <div data-testid="ar-receipt-allocation" className="space-y-1.5 rounded-lg border p-2.5">
              <div className="flex items-center justify-between">
                <Label className="text-[12px]">Dialokasikan ke termin</Label>
                <button type="button" data-testid="ar-receipt-alloc-fifo" className="text-[11px] text-primary hover:underline"
                  onClick={() => setAlloc(fifo(Math.min(amt, outstanding), payable))}>Isi otomatis (jatuh tempo terlama dulu)</button>
              </div>
              {payable.map((it) => {
                const open = openOf(it);
                return (
                  <div key={it.id} data-testid="ar-receipt-alloc-row" data-item-id={it.id} data-payer={it.payer || "buyer"}
                    className="grid grid-cols-[1fr_9rem] items-center gap-2 text-[12px]">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{it.label}
                        {isBank(it) ? <span className="ml-1 rounded-full bg-sky-100 px-1.5 text-[10px] font-normal text-sky-800">porsi bank</span> : null}
                      </p>
                      <p className="text-[11px] text-muted-foreground">jatuh tempo {String(it.due_date || "").slice(0, 10)} · sisa {formatIDR(open)}</p>
                    </div>
                    <RupiahInput data-testid="ar-receipt-alloc-amount" aria-label={`Alokasi ${it.label}`} className="h-8"
                      value={alloc[it.id] ?? ""} placeholder="0"
                      onChange={(e) => setAlloc((a) => ({ ...a, [it.id]: Math.min(open, Number(e.target.value) || 0) }))} />
                  </div>
                );
              })}
              <p data-testid="ar-receipt-alloc-sum" className={`text-[11px] ${allocMismatch ? "text-rose-600" : "text-muted-foreground"}`}>
                Total alokasi {formatIDR(allocSum)} dari {formatIDR(Math.min(amt, outstanding))}{allocMismatch ? " — belum sama, sesuaikan." : " ✓"}
              </p>
            </div>
          ) : null}
          {bankItems.length ? (
            <div data-testid="ar-receipt-bank-portion"
              className="space-y-1.5 rounded-lg border border-sky-200 bg-sky-50 p-2.5 text-[12px] text-sky-900">
              <p className="flex items-start gap-1.5 font-medium">
                <Landmark className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Porsi bank {formatIDR(bankOutstanding)} — dilunasi lewat <b>Pencairan KPR</b> (menu KPR pelanggan), bukan di sini.
              </p>
              <ul className="ml-5 list-disc text-[11px]">
                {bankItems.map((it) => <li key={it.id}>{it.label} · sisa {formatIDR(openOf(it))}</li>)}
              </ul>
              <label className="flex items-start gap-2 text-[11px]">
                <Checkbox data-testid="ar-receipt-allow-bank" checked={allowBank} onCheckedChange={toggleBank} className="mt-0.5" />
                <span>Pembeli melunasi porsi KPR ini <b>sendiri</b> (bank tidak mencairkan) — buka termin bank untuk dialokasikan.</span>
              </label>
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label>Metode</Label>
            <ReferenceSelect group="payment_method" value={method} onChange={setMethod}
              testId="ar-receipt-method" />
          </div>
          <CashAccountSelect value={cashAccountId} onChange={setCashAccountId}
            kind={method === "cash" || method === "tunai" ? "cash" : "bank"}
            label="Masuk ke rekening / kas" testId="ar-receipt-cash-account" />
          <div className="space-y-1.5">
            <Label htmlFor="note">Catatan (opsional)</Label>
            <Textarea id="note" value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="mis. DP 20%, cicilan termin I" rows={2} />
          </div>
          <div className="space-y-1.5">
            <Label>Bukti bayar (wajib)</Label>
            <EvidenceUploader value={proofFiles} onChange={setProofFiles} ownerType="receipt_proof" required
              ownerId={deal?.deal_id} testId="ar-receipt-proof-input" label="Bukti bayar"
              hint="wajib untuk setiap pembayaran; tampil di kuitansi & semua laporan pembayaran." />
          </div>

          {excess > 0 ? (
            <div data-testid="ar-receipt-overpay-warning"
              className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="flex items-start gap-2 font-medium">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                Jumlah melebihi sisa tagihan porsi pembeli {formatIDR(outstanding)}.
              </p>
              <p className="text-[12px] leading-relaxed">
                Kelebihan <span className="font-semibold tabular-nums">{formatIDR(excess)}</span> akan
                dicatat sebagai <span className="font-semibold">Titipan Pelanggan</span> (akun 2-1450),
                bukan pendapatan — nanti bisa dipakai untuk termin berikutnya atau dikembalikan.
                {bankOutstanding > 0 && !allowBank ? " Bila uang ini untuk melunasi porsi KPR, centang opsi porsi bank di atas." : ""}
              </p>
              <label className="flex items-start gap-2 text-[12px] font-medium">
                <Checkbox data-testid="ar-receipt-allow-overpay" checked={allowOverpay}
                  onCheckedChange={(v) => setAllowOverpay(!!v)} className="mt-0.5" />
                <span>Ya, saya memang menerima kelebihan ini dan mencatatnya sebagai titipan.</span>
              </label>
            </div>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={FINANCE.receiptSubmit} onClick={submit} disabled={busy || blocked || allocMismatch || !proofFiles.length}>
            {busy ? "Memproses…" : blocked ? "Centang persetujuan dulu" : "Simpan Pembayaran"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
