import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import api from "@/services/apiClient";
import { FUNDREQ } from "@/constants/testIds";

const TYPE_HINT = {
  expense: "Biaya operasional yang akan dibayar perusahaan (dibebankan saat cair).",
  reimbursement: "Anda sudah membayar dengan uang pribadi — WAJIB lampirkan nota/struk.",
  purchase: "Pembelian barang/jasa; isi rincian item bila ada.",
  vendor_payment: "Pembayaran tagihan vendor/subkon; isi data rekening penerima.",
  advance: "Uang muka (kas bon) — dicatat sebagai piutang karyawan 1-1500 dan wajib dipertanggungjawabkan.",
};

const EMPTY = { type: "expense", title: "", amount: "", category: "lainnya", urgency: "normal",
  projectId: "", neededDate: "", payeeName: "", payeeBank: "", payeeAccount: "", note: "", apBillId: "" };

/** Form pengajuan keuangan (biaya, reimbursement, pembelian, vendor, kas bon). */
export default function FundRequestDialog({ open, onOpenChange, onSaved }) {
  const [f, setF] = useState(EMPTY);
  const [files, setFiles] = useState([]);
  const [projects, setProjects] = useState([]);
  const [bills, setBills] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const setE = (k) => (e) => set(k)(e.target.value);

  const loadProjects = useCallback(async () => {
    try { setProjects((await api.get("/projects?limit=100")).data.data || []); } catch { setProjects([]); }
  }, []);
  const loadBills = useCallback(async () => {
    try {
      const [a, p] = await Promise.all([api.get("/finance/ap/bills?status=approved&limit=200"), api.get("/finance/ap/bills?status=partial&limit=200")]);
      setBills([...(a.data.data || []), ...(p.data.data || [])]);
    } catch { setBills([]); }
  }, []);
  useEffect(() => { if (open) { loadProjects(); setErr(""); setF(EMPTY); setFiles([]); } }, [open, loadProjects]);
  useEffect(() => { if (open && f.type === "vendor_payment") loadBills(); }, [open, f.type, loadBills]);

  const pickBill = (id) => {
    if (id === "__none__") { setF((s) => ({ ...s, apBillId: "" })); return; }
    const b = bills.find((x) => x.id === id);
    if (!b) return;
    const sisa = Number(b.net || 0) - Number(b.paid || 0);
    setF((s) => ({ ...s, apBillId: id, payeeName: b.vendor || s.payeeName, amount: String(sisa),
      projectId: b.project_id || s.projectId, title: s.title || `Pembayaran tagihan ${b.vendor}${b.note ? ` — ${b.note}` : ""}`.slice(0, 200) }));
  };
  const bill = bills.find((x) => x.id === f.apBillId);
  const billOutstanding = bill ? Number(bill.net || 0) - Number(bill.paid || 0) : null;

  const isPayee = ["vendor_payment", "purchase"].includes(f.type);
  const valid = f.title.trim().length >= 3 && Number(f.amount) > 0
    && (f.type !== "reimbursement" || files.length > 0)
    && (billOutstanding == null || Number(f.amount) <= billOutstanding);

  const submit = async () => {
    setSaving(true); setErr("");
    try {
      await api.post("/fund-requests", {
        type: f.type, title: f.title.trim(), amount: Number(f.amount), category: f.category,
        urgency: f.urgency, project_id: f.projectId || null,
        needed_date: f.neededDate ? new Date(f.neededDate).toISOString() : null,
        payee_name: f.payeeName || null, payee_bank: f.payeeBank || null,
        payee_account: f.payeeAccount || null, attachment_ids: files, note: f.note || null,
        ap_bill_id: f.type === "vendor_payment" && f.apBillId ? f.apBillId : null,
      });
      toast.success("Pengajuan terkirim ke finance.");
      onOpenChange(false); onSaved?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Gagal mengirim pengajuan.");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={FUNDREQ.dialog} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Buat Pengajuan Keuangan</DialogTitle>
          <DialogDescription>{TYPE_HINT[f.type]}</DialogDescription>
        </DialogHeader>
        <div className="max-h-[65vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Jenis pengajuan</Label>
              <ReferenceSelect group="fund_request_type" value={f.type} onChange={set("type")} testId={FUNDREQ.type} />
            </div>
            <div className="space-y-1.5">
              <Label>Urgensi</Label>
              <ReferenceSelect group="fund_request_urgency" value={f.urgency} onChange={set("urgency")} testId={FUNDREQ.urgency} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="fr-title">Keperluan / judul</Label>
            <Input id="fr-title" data-testid={FUNDREQ.title} value={f.title} onChange={setE("title")}
              placeholder="Mis. pembayaran listrik kantor pemasaran Agustus" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="fr-amount">Nominal (Rp)</Label>
              <RupiahInput id="fr-amount" data-testid={FUNDREQ.amount} value={f.amount} onChange={setE("amount")} placeholder="0" />
            </div>
            <div className="space-y-1.5">
              <Label>Kategori beban</Label>
              <ReferenceSelect group="cashbon_category" value={f.category} onChange={set("category")} testId={FUNDREQ.category} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Proyek (opsional)</Label>
              <Select value={f.projectId || "__none__"} onValueChange={(v) => set("projectId")(v === "__none__" ? "" : v)}>
                <SelectTrigger data-testid={FUNDREQ.project}><SelectValue placeholder="Tanpa proyek" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Tanpa proyek</SelectItem>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="fr-date">Tanggal dibutuhkan</Label>
              <Input id="fr-date" data-testid={FUNDREQ.date} type="date" value={f.neededDate} onChange={setE("neededDate")} />
            </div>
          </div>
          {f.type === "vendor_payment" ? (
            <div className="space-y-1.5 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
              <Label>Tagihan AP yang dibayar (agar tidak dibebankan dua kali)</Label>
              <Select value={f.apBillId || "__none__"} onValueChange={pickBill}>
                <SelectTrigger data-testid="fund-request-ap-bill"><SelectValue placeholder="Pilih tagihan AP disetujui" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Tanpa tagihan AP (pembayaran langsung — dibebankan saat cair)</SelectItem>
                  {bills.map((b) => (
                    <SelectItem key={b.id} value={b.id} data-testid={`fund-request-ap-bill-${b.id}`}>
                      {b.vendor} · sisa Rp {(Number(b.net || 0) - Number(b.paid || 0)).toLocaleString("id-ID")}{b.note ? ` · ${String(b.note).slice(0, 40)}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {bill ? (
                <p className="text-xs text-amber-900" data-testid="fund-request-ap-bill-hint">
                  Pencairan akan melunasi Utang Usaha 2-1100 (bukan beban baru). Sisa tagihan Rp {billOutstanding.toLocaleString("id-ID")}
                  {Number(f.amount) > billOutstanding ? " — nominal melebihi sisa tagihan." : "."}
                </p>
              ) : null}
            </div>
          ) : null}
          {isPayee ? (
            <div className="grid grid-cols-3 gap-3 rounded-lg border p-3">
              <div className="space-y-1.5 col-span-3 sm:col-span-1">
                <Label htmlFor="fr-payee">Nama penerima</Label>
                <Input id="fr-payee" data-testid={FUNDREQ.payeeName} value={f.payeeName} onChange={setE("payeeName")} placeholder="PT / Toko / Nama" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="fr-bank">Bank</Label>
                <Input id="fr-bank" data-testid={FUNDREQ.payeeBank} value={f.payeeBank} onChange={setE("payeeBank")} placeholder="BCA" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="fr-acc">No. rekening</Label>
                <Input id="fr-acc" data-testid={FUNDREQ.payeeAccount} value={f.payeeAccount} onChange={setE("payeeAccount")} placeholder="1234567890" />
              </div>
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label>{f.type === "reimbursement" ? "Bukti pembayaran (wajib)" : "Lampiran (opsional)"}</Label>
            <EvidenceUploader value={files} onChange={setFiles} ownerType="fund_request" max={5}
              testId="fund-request-attachments" label="Lampirkan nota / penawaran / tagihan" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="fr-note">Catatan</Label>
            <Textarea id="fr-note" data-testid={FUNDREQ.note} rows={2} value={f.note} onChange={setE("note")}
              placeholder="Rincian singkat / alasan" />
          </div>
          {err ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-700">{err}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Batal</Button>
          <Button data-testid={FUNDREQ.submit} disabled={!valid || saving} onClick={submit}>
            {saving ? "Mengirim…" : "Kirim Pengajuan"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
