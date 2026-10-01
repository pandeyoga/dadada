import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import CashAccountSelect from "@/components/cashBank/CashAccountSelect";
import { formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";
import { FUNDREQ } from "@/constants/testIds";

/** Finance mencairkan pengajuan yang sudah disetujui (jurnal Dr beban/1-1500 / Cr kas). */
export function FundRequestDisburseDialog({ req, onClose, onSaved }) {
  const [amount, setAmount] = useState("");
  const [source, setSource] = useState("bank");
  const [cashAccountId, setCashAccountId] = useState("");
  const [refNo, setRefNo] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (req) { setAmount(String(req.approved_amount || req.amount || "")); setSource("bank"); setRefNo(""); setNote(""); setErr(""); }
  }, [req]);
  if (!req) return null;
  const cap = Number(req.approved_amount || req.amount || 0);
  const over = Number(amount) > cap;

  const submit = async () => {
    setSaving(true); setErr("");
    try {
      await api.post(`/fund-requests/${req.id}/disburse`, {
        amount: Number(amount), source, cash_account_id: cashAccountId || null,
        reference_no: refNo || null, note: note || null,
      });
      toast.success(`Pengajuan ${req.no} dicairkan ${formatIDR(Number(amount))}.`);
      onClose(); onSaved?.();
    } catch (e) { setErr(e?.response?.data?.detail || "Gagal mencairkan."); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent data-testid={FUNDREQ.disburseDialog} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Cairkan {req.no}</DialogTitle>
          <DialogDescription>
            {req.title} · disetujui {formatIDR(cap)}.
            {req.payee_name ? ` Penerima: ${req.payee_name}${req.payee_bank ? ` (${req.payee_bank} ${req.payee_account || ""})` : ""}.` : ""}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="fr-dis-amount">Nominal dicairkan (Rp)</Label>
            <RupiahInput id="fr-dis-amount" data-testid={FUNDREQ.disburseAmount} value={amount} onChange={(e) => setAmount(e.target.value)} />
            {over ? <p className="rounded-md bg-rose-50 p-2 text-xs text-rose-700">Melebihi nominal disetujui ({formatIDR(cap)}).</p> : null}
          </div>
          <div className="space-y-1.5">
            <Label>Sumber kas</Label>
            <ReferenceSelect group="cash_source" value={source} onChange={setSource} testId={FUNDREQ.disburseSource} />
          </div>
          <CashAccountSelect value={cashAccountId} onChange={setCashAccountId}
            kind={["kas", "cash", "tunai"].includes(source) ? "cash" : "bank"} label="Dari rekening / kas" testId="fr-dis-cash-account" />
          <div className="space-y-1.5">
            <Label htmlFor="fr-dis-ref">No. referensi transfer (opsional)</Label>
            <Input id="fr-dis-ref" data-testid={FUNDREQ.disburseRef} value={refNo} onChange={(e) => setRefNo(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="fr-dis-note">Catatan</Label>
            <Textarea id="fr-dis-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          {err ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-700">{err}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button data-testid={FUNDREQ.disburseSubmit} onClick={submit} disabled={saving || over || !(Number(amount) > 0)}>
            {saving ? "Memproses…" : "Cairkan"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const blank = () => ({ key: Math.random().toString(36).slice(2), category: "transport", description: "", amount: "" });

/** Pertanggungjawaban kas bon (jenis `advance`): rincian realisasi per kategori + bukti. */
export function FundRequestSettleDialog({ req, onClose, onSaved }) {
  const [items, setItems] = useState([blank()]);
  const [files, setFiles] = useState([]);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { if (req) { setItems([blank()]); setFiles([]); setNote(""); setErr(""); } }, [req]);
  if (!req) return null;

  const disbursed = Number(req.disbursed_amount || 0);
  const total = items.reduce((s, it) => s + (Number(it.amount) || 0), 0);
  const upd = (key, patch) => setItems((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const valid = items.every((it) => it.description.trim().length >= 2 && Number(it.amount) > 0);

  const submit = async () => {
    setSaving(true); setErr("");
    try {
      await api.post(`/fund-requests/${req.id}/settle`, {
        items: items.map((it) => ({ category: it.category, description: it.description.trim(), amount: Number(it.amount) })),
        attachment_ids: files, note: note || null,
      });
      toast.success(`Kas bon ${req.no} dipertanggungjawabkan.`);
      onClose(); onSaved?.();
    } catch (e) { setErr(e?.response?.data?.detail || "Gagal menyimpan pertanggungjawaban."); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent data-testid={FUNDREQ.settleDialog} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Pertanggungjawaban {req.no}</DialogTitle>
          <DialogDescription>Dicairkan {formatIDR(disbursed)}. Isi realisasi pengeluaran; sisa/kekurangan dihitung otomatis.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {items.map((it, i) => (
            <div key={it.key} className="grid grid-cols-12 items-end gap-2 rounded-lg border p-2">
              <div className="col-span-4 space-y-1"><Label className="text-xs">Kategori</Label>
                <ReferenceSelect group="cashbon_category" value={it.category} onChange={(v) => upd(it.key, { category: v })} testId={`fr-settle-cat-${i}`} /></div>
              <div className="col-span-4 space-y-1"><Label className="text-xs">Keterangan</Label>
                <Input data-testid={`fr-settle-desc-${i}`} value={it.description} onChange={(e) => upd(it.key, { description: e.target.value })} /></div>
              <div className="col-span-3 space-y-1"><Label className="text-xs">Nominal</Label>
                <RupiahInput data-testid={`fr-settle-amt-${i}`} value={it.amount} onChange={(e) => upd(it.key, { amount: e.target.value })} /></div>
              <Button size="icon" variant="ghost" className="col-span-1" disabled={items.length === 1}
                onClick={() => setItems((rows) => rows.filter((r) => r.key !== it.key))}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
          <Button size="sm" variant="outline" data-testid={FUNDREQ.settleAddItem} onClick={() => setItems((r) => [...r, blank()])}>
            <Plus className="mr-1 h-3.5 w-3.5" /> Tambah baris
          </Button>
          <div className="grid grid-cols-3 gap-2 rounded-lg bg-muted/40 p-3 text-sm">
            <div><p className="text-xs text-muted-foreground">Total realisasi</p><p className="font-semibold">{formatIDR(total)}</p></div>
            <div><p className="text-xs text-muted-foreground">Sisa dikembalikan</p><p className="font-semibold text-emerald-700">{formatIDR(Math.max(0, disbursed - total))}</p></div>
            <div><p className="text-xs text-muted-foreground">Kekurangan (diganti)</p><p className="font-semibold text-amber-700">{formatIDR(Math.max(0, total - disbursed))}</p></div>
          </div>
          <EvidenceUploader value={files} onChange={setFiles} ownerType="fund_request" ownerId={req.id} max={5}
            testId="fr-settle-attachments" label="Lampirkan nota / struk" />
          <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Catatan" />
          {err ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-700">{err}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button data-testid={FUNDREQ.settleSubmit} onClick={submit} disabled={saving || !valid || total <= 0}>
            {saving ? "Menyimpan…" : "Simpan Pertanggungjawaban"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
