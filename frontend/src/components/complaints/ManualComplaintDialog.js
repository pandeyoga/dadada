import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Search } from "lucide-react";

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { CHUB } from "@/constants/testIds";

const CHANNELS = [
  ["whatsapp", "WhatsApp"], ["telepon", "Telepon"], ["walk_in", "Datang langsung"],
  ["email", "Email"], ["lainnya", "Lainnya"],
];
const NONE = "__none__";
const EMPTY = { unit_id: "", channel: "whatsapp", category: "lainnya", priority: "medium",
  subject: "", message: "", assigned_to: "", notify_customer: true };

/**
 * ManualComplaintDialog — staf mencatat komplain ATAS NAMA pembeli (WA/telepon/datang
 * langsung). Bila `customer` diberikan, pembeli sudah terkunci; bila tidak, cari dahulu.
 */
export default function ManualComplaintDialog({ open, onOpenChange, customer = null, onDone }) {
  const { can } = useAuth();
  const [cust, setCust] = useState(customer);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState([]);
  const [units, setUnits] = useState([]);
  const [owners, setOwners] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const mayAssign = can("complaints", "assign");

  useEffect(() => {
    if (!open) return;
    setCust(customer); setQ(""); setHits([]); setForm(EMPTY); setError("");
    if (mayAssign) api.get("/leads/assignees").then((r) => setOwners(r.data.data || [])).catch(() => setOwners([]));
  }, [open, customer, mayAssign]);

  useEffect(() => {
    if (!cust?.id) { setUnits([]); return; }
    api.get(`/customers/${cust.id}/units-construction`)
      .then((r) => setUnits((r.data.data || []).map((x) => x.unit)))
      .catch(() => setUnits([]));
  }, [cust]);

  useEffect(() => {
    if (customer || q.trim().length < 2) { setHits([]); return; }
    const t = setTimeout(() => {
      api.get("/customers", { params: { q: q.trim(), limit: 8 } })
        .then((r) => setHits(r.data.data || [])).catch(() => setHits([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, customer]);

  const submit = async () => {
    if (!cust?.id) { setError("Pilih pembeli terlebih dahulu."); return; }
    if (!form.subject.trim() || !form.message.trim()) { setError("Subjek dan isi komplain wajib diisi."); return; }
    setBusy(true); setError("");
    try {
      await api.post("/complaints", {
        customer_id: cust.id, unit_id: form.unit_id || null, channel: form.channel,
        category: form.category, priority: form.priority, subject: form.subject.trim(),
        message: form.message.trim(), assigned_to: form.assigned_to || null,
        notify_customer: form.notify_customer,
      });
      toast.success("Komplain dicatat — tugas SLA 48 jam dibuat untuk PIC.");
      onDone?.();
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal mencatat komplain.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={CHUB.mcDialog} className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Catat komplain pembeli</DialogTitle>
          <DialogDescription>
            Untuk pembeli yang menyampaikan keluhan lewat WA, telepon, atau datang langsung —
            alurnya sama dengan komplain portal (SLA 48 jam, tugas untuk PIC).
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Pembeli</Label>
            {cust ? (
              <div className="flex items-center justify-between rounded-md border bg-secondary/40 px-3 py-2 text-sm">
                <span><b>{cust.name}</b>{cust.phone ? ` · ${cust.phone}` : ""}</span>
                {!customer ? <Button size="sm" variant="ghost" onClick={() => setCust(null)}>Ganti</Button> : null}
              </div>
            ) : (
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input data-testid={CHUB.mcCustomerSearch} className="pl-8" placeholder="Cari nama / telepon / NIK pembeli…"
                  value={q} onChange={(e) => setQ(e.target.value)} />
                {hits.length ? (
                  <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border bg-popover shadow-md">
                    {hits.map((h) => (
                      <li key={h.id}>
                        <button type="button" data-testid={CHUB.mcCustomerOption}
                          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-secondary"
                          onClick={() => { setCust(h); setHits([]); }}>
                          <span>{h.name}</span><span className="text-xs text-muted-foreground">{h.phone}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Unit</Label>
            <Select value={form.unit_id || NONE} onValueChange={(v) => set("unit_id", v === NONE ? "" : v)} disabled={!cust}>
              <SelectTrigger data-testid={CHUB.mcUnit} aria-label="Unit"><SelectValue placeholder="Pilih unit" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>{units.length ? "Unit pertama pembeli" : "Tanpa unit"}</SelectItem>
                {units.map((u) => <SelectItem key={u.id} value={u.id}>{u.code} · {u.type}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Kanal masuk</Label>
            <Select value={form.channel} onValueChange={(v) => set("channel", v)}>
              <SelectTrigger data-testid={CHUB.mcChannel} aria-label="Kanal"><SelectValue /></SelectTrigger>
              <SelectContent>{CHANNELS.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Kategori</Label>
            <ReferenceSelect group="complaint_category" value={form.category}
              onChange={(v) => set("category", v)} testId={CHUB.mcCategory} />
          </div>
          <div className="space-y-1.5">
            <Label>Prioritas</Label>
            <ReferenceSelect group="priority" value={form.priority}
              onChange={(v) => set("priority", v)} testId={CHUB.mcPriority} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="mc-subject">Subjek</Label>
            <Input id="mc-subject" data-testid={CHUB.mcSubject} value={form.subject}
              onChange={(e) => set("subject", e.target.value)} placeholder="mis. Atap bocor di kamar utama" />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="mc-message">Isi komplain (sesuai ucapan pembeli)</Label>
            <Textarea id="mc-message" data-testid={CHUB.mcMessage} rows={4} value={form.message}
              onChange={(e) => set("message", e.target.value)} />
          </div>
          {mayAssign ? (
            <div className="space-y-1.5">
              <Label>PIC penanganan</Label>
              <Select value={form.assigned_to || NONE} onValueChange={(v) => set("assigned_to", v === NONE ? "" : v)}>
                <SelectTrigger data-testid={CHUB.mcAssignee} aria-label="PIC"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>Otomatis (sales pemegang deal)</SelectItem>
                  {owners.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <div className="flex items-center gap-2 pt-6">
            <Switch id="mc-notify" data-testid={CHUB.mcNotify} checked={form.notify_customer}
              onCheckedChange={(v) => set("notify_customer", v)} />
            <Label htmlFor="mc-notify" className="text-sm">Kirim WA konfirmasi ke pembeli</Label>
          </div>
        </div>
        {error ? (
          <p data-testid={CHUB.mcError} className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={CHUB.mcSubmit} onClick={submit} disabled={busy}>
            {busy ? "Menyimpan…" : "Catat komplain"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
