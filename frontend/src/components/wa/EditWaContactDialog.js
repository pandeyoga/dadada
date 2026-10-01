import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import PhoneInput from "@/components/patterns/PhoneInput";
import api from "@/services/apiClient";
import { CONTACT_EDIT as T } from "@/constants/testIds";

const fromContact = (c) => ({
  name: c?.name || "", phone: c?.phone || "", email: c?.email || "",
  first_message: c?.first_message || "", notes: c?.notes || "", opt_out: !!c?.opt_out,
});

export default function EditWaContactDialog({ contact, onOpenChange, onDone }) {
  const [form, setForm] = useState(fromContact(contact));
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => { if (contact) setForm(fromContact(contact)); }, [contact]);

  const submit = async () => {
    if (!form.phone) { toast.error("Nomor HP wajib diisi."); return; }
    setBusy(true);
    try {
      await api.put(`/wa/contacts/${contact.id}`, form);
      toast.success("Kontak WA diperbarui.");
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan kontak.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={!!contact} onOpenChange={onOpenChange}>
      <DialogContent data-testid={T.waDialog}>
        <DialogHeader>
          <DialogTitle>Edit Kontak WA</DialogTitle>
          <DialogDescription>Nomor baru dicek ulang terhadap lead &amp; pelanggan yang sudah ada.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="wc-n">Nama</Label>
            <Input id="wc-n" data-testid={T.waName} value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="wc-p">No. WhatsApp</Label>
            <PhoneInput id="wc-p" value={form.phone} onChange={(v) => set("phone", v)} testId={T.waPhone} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="wc-e">Email</Label>
            <Input id="wc-e" data-testid={T.waEmail} value={form.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="wc-m">Pesan pertama</Label>
            <Textarea id="wc-m" data-testid={T.waMessage} rows={2} value={form.first_message}
              onChange={(e) => set("first_message", e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="wc-nt">Catatan</Label>
            <Textarea id="wc-nt" data-testid={T.waNotes} rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
          <label className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm sm:col-span-2">
            <span>
              <span className="font-medium">Opt-out</span>
              <span className="block text-xs text-muted-foreground">Kontak menolak menerima pesan WhatsApp.</span>
            </span>
            <Switch data-testid={T.waOptOut} checked={form.opt_out} onCheckedChange={(v) => set("opt_out", v)} />
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={T.waSubmit} onClick={submit} disabled={busy}>{busy ? "Menyimpan…" : "Simpan Perubahan"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
