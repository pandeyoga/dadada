import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import PhoneInput from "@/components/patterns/PhoneInput";
import api from "@/services/apiClient";
import { CONTACT_EDIT as T } from "@/constants/testIds";

const fromLead = (l) => ({
  name: l?.name || "", phone: l?.phone || "", email: l?.email || "", source: l?.source || "manual",
  partner_id: l?.partner_id || "", interest_unit_type: l?.interest_unit_type || "", notes: l?.notes || "",
});

export default function EditLeadDialog({ lead, open, onOpenChange, onDone }) {
  const [form, setForm] = useState(fromLead(lead));
  const [partners, setPartners] = useState([]);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!open) return;
    setForm(fromLead(lead));
    api.get("/partners", { params: { status: "active", limit: 200 } })
      .then((r) => setPartners(r.data.data || [])).catch(() => setPartners([]));
  }, [open, lead]);

  const submit = async () => {
    if (!form.name.trim() || !form.phone) { toast.error("Nama & telepon wajib diisi."); return; }
    if (form.source === "partner" && !form.partner_id) { toast.error("Lead dari mitra wajib memilih mitranya."); return; }
    setBusy(true);
    try {
      const payload = { ...form, name: form.name.trim() };
      if (!payload.interest_unit_type) delete payload.interest_unit_type;
      if (!payload.partner_id) delete payload.partner_id;
      await api.put(`/leads/${lead.id}`, payload);
      toast.success("Data lead diperbarui.");
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan lead.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={T.leadDialog}>
        <DialogHeader>
          <DialogTitle>Edit Kontak Lead</DialogTitle>
          <DialogDescription>Perubahan nama ikut disamakan ke agenda, tagihan, dan percakapan WA.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="el-n">Nama</Label>
            <Input id="el-n" data-testid={T.leadName} value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="el-p">No. Telepon (WA)</Label>
            <PhoneInput id="el-p" value={form.phone} onChange={(v) => set("phone", v)} testId={T.leadPhone} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="el-e">Email</Label>
            <Input id="el-e" data-testid={T.leadEmail} value={form.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Sumber</Label>
            <ReferenceSelect group="lead_source" value={form.source} onChange={(v) => set("source", v)} testId={T.leadSource} />
          </div>
          {form.source === "partner" ? (
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Mitra pengirim lead (wajib)</Label>
              <Select value={form.partner_id} onValueChange={(v) => set("partner_id", v)}>
                <SelectTrigger data-testid={T.leadPartner} aria-label="Mitra pengirim lead">
                  <SelectValue placeholder="Pilih mitra" />
                </SelectTrigger>
                <SelectContent>
                  {partners.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Minat Unit</Label>
            <ReferenceSelect group="unit_type" value={form.interest_unit_type}
              onChange={(v) => set("interest_unit_type", v)} testId={T.leadUnitType}
              placeholder="Pilih tipe unit yang diminati" />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="el-nt">Catatan</Label>
            <Textarea id="el-nt" data-testid={T.leadNotes} rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={T.leadSubmit} onClick={submit} disabled={busy}>{busy ? "Menyimpan…" : "Simpan Perubahan"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
