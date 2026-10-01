import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import PhoneInput from "@/components/patterns/PhoneInput";
import api from "@/services/apiClient";
import { CONTACT_EDIT as T } from "@/constants/testIds";

export default function EditConvContactDialog({ conversation, open, onOpenChange, onDone }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open && conversation) { setName(conversation.contact_name || ""); setPhone(conversation.contact_phone || ""); }
  }, [open, conversation]);

  const submit = async () => {
    if (!phone) { toast.error("Nomor WhatsApp wajib diisi."); return; }
    setBusy(true);
    try {
      await api.put(`/inbox/${conversation.id}/contact`, { contact_name: name, contact_phone: phone });
      toast.success("Kontak percakapan diperbarui.");
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan kontak.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={T.inboxDialog} className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Kontak Percakapan</DialogTitle>
          <DialogDescription>
            Mengubah nama/nomor di Inbox. Data lead tertaut diubah lewat profil lead.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="cc-n">Nama kontak</Label>
            <Input id="cc-n" data-testid={T.inboxName} value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cc-p">No. WhatsApp</Label>
            <PhoneInput id="cc-p" value={phone} onChange={setPhone} testId={T.inboxPhone} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={T.inboxSubmit} onClick={submit} disabled={busy}>{busy ? "Menyimpan…" : "Simpan"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
