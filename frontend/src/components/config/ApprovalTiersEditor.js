import React, { useEffect, useState } from "react";
import { Plus, SlidersHorizontal, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { RupiahInput } from "@/components/ui/rupiah-input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

/** Urutan kewenangan naik — SAMA dengan `discount_approval.RANK` di backend. */
export const TIER_ROLES = [
  { value: "sales_manager", label: "Manajer Penjualan" },
  { value: "finance_manager", label: "Manajer Keuangan" },
  { value: "owner", label: "Owner" },
];
const RANK = { sales_manager: 1, finance_manager: 2, owner: 3 };
const LABEL = Object.fromEntries(TIER_ROLES.map((r) => [r.value, r.label]));
const rp = (v) => `Rp ${Number(v).toLocaleString("id-ID")}`;
const isBlank = (v) => v === null || v === undefined || v === "";

/** Cermin `discount_approval.validate` (server tetap yang menentukan). Mengembalikan daftar pesan galat. */
export function validateTiers(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return ["Tabel tingkat tidak boleh kosong."];
  const errs = [];
  let prevMax = 0;
  let prevRank = 0;
  rows.forEach((t, i) => {
    const n = i + 1;
    const last = i === rows.length - 1;
    if (!RANK[t.role]) errs.push(`Tingkat ${n}: pilih peran penyetuju.`);
    else if (RANK[t.role] < prevRank) errs.push(`Tingkat ${n}: peran lebih rendah daripada tingkat sebelumnya.`);
    if (last) {
      if (!isBlank(t.max_amount)) errs.push(`Tingkat terakhir harus tak terbatas (celah di atas ${rp(t.max_amount)}).`);
    } else if (isBlank(t.max_amount) || !(Number(t.max_amount) > 0)) {
      errs.push(`Tingkat ${n}: batas nominal harus lebih dari 0.`);
    } else if (Number(t.max_amount) <= prevMax) {
      errs.push(`Tingkat ${n}: batas ${rp(t.max_amount)} harus lebih besar dari tingkat sebelumnya (${rp(prevMax)}) — tidak boleh tumpang tindih.`);
    }
    if (!isBlank(t.max_amount) && Number(t.max_amount) > 0) prevMax = Number(t.max_amount);
    if (RANK[t.role]) prevRank = RANK[t.role];
  });
  return errs;
}

/** Ringkasan satu baris, mis. "≤ Rp 10.000.000 Manajer Penjualan · lebih besar Owner". */
export function summarizeTiers(rows) {
  if (!Array.isArray(rows) || !rows.length) return "(kosong)";
  return rows.map((t, i) => (isBlank(t.max_amount)
    ? `${i ? "di atas itu" : "semua nilai"} ${LABEL[t.role] || t.role}`
    : `≤ ${rp(t.max_amount)} ${LABEL[t.role] || t.role}`)).join(" · ");
}

const normalize = (rows) => rows.map((t, i) => ({
  max_amount: i === rows.length - 1 || isBlank(t.max_amount) ? null : Number(t.max_amount), role: t.role,
}));

/**
 * Editor tabel tingkat persetujuan diskon (`discount.approval_tiers`): nominal + peran, tambah/hapus baris,
 * validasi sisi klien yang meniru server. Dibuka dari sel "Nilai berlaku" Pusat Konfigurasi; hasilnya masuk draf
 * baris itu dan disimpan lewat tombol Simpan biasa (alasan wajib karena sensitif).
 */
export default function ApprovalTiersEditor({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(normalize(Array.isArray(value) ? value : []));
  useEffect(() => { if (open) setRows(normalize(Array.isArray(value) ? value : [])); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const errs = validateTiers(rows);

  const patch = (i, p) => setRows((rs) => rs.map((t, j) => (j === i ? { ...t, ...p } : t)));
  const add = () => setRows((rs) => {
    const prev = rs.length > 1 ? Number(rs[rs.length - 2].max_amount) || 0 : 0;
    const top = rs[rs.length - 1];
    const fresh = { max_amount: prev ? prev * 2 : 10000000, role: top ? top.role : "sales_manager" };
    return [...rs.slice(0, -1), fresh, top].filter(Boolean);
  });
  const remove = (i) => setRows((rs) => normalize(rs.filter((_, j) => j !== i)));
  const apply = () => { onChange(normalize(rows)); setOpen(false); };

  return (
    <div data-testid="approval-tiers-editor" className="space-y-1.5">
      <div data-testid="approval-tiers-summary" className="text-xs">{summarizeTiers(value)}</div>
      <Button data-testid="approval-tiers-open" size="sm" variant="outline" onClick={() => setOpen(true)}>
        <SlidersHorizontal className="mr-1 h-3.5 w-3.5" /> Atur tingkat
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Tingkat persetujuan diskon</DialogTitle>
            <DialogDescription>
              Total potongan disetujui oleh peran pada tingkat pertama yang batasnya mencukupi. Peran yang lebih tinggi
              boleh memutuskan tingkat di bawahnya; pemohon tidak boleh menyetujui permohonannya sendiri.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            {rows.map((t, i) => {
              const last = i === rows.length - 1;
              const from = i === 0 ? 0 : Number(rows[i - 1].max_amount) || 0;
              return (
                <div key={i} data-testid="approval-tier-row" className="grid grid-cols-[auto_1fr_1fr_auto] items-center gap-2 text-sm">
                  <span className="w-16 text-xs text-muted-foreground">Tingkat {i + 1}<br />dari {rp(from)}</span>
                  {last ? (
                    <div data-testid="approval-tier-max" className="rounded-md border bg-secondary/40 px-3 py-2 text-xs text-muted-foreground">
                      sampai tak terbatas
                    </div>
                  ) : (
                    <RupiahInput data-testid="approval-tier-max" aria-label={`Batas tingkat ${i + 1}`} value={t.max_amount ?? ""}
                      onChange={(e) => patch(i, { max_amount: e.target.value === "" ? "" : Number(e.target.value) })} />
                  )}
                  <Select value={t.role} onValueChange={(v) => patch(i, { role: v })}>
                    <SelectTrigger data-testid="approval-tier-role" aria-label={`Peran tingkat ${i + 1}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIER_ROLES.map((r) => <SelectItem key={r.value} value={r.value} data-testid={`approval-tier-role-${r.value}`}>{r.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button data-testid="approval-tier-remove" size="icon" variant="ghost" disabled={rows.length <= 1}
                    aria-label={`Hapus tingkat ${i + 1}`} onClick={() => remove(i)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              );
            })}
            <Button data-testid="approval-tier-add" size="sm" variant="secondary" onClick={add}>
              <Plus className="mr-1 h-3.5 w-3.5" /> Tambah tingkat
            </Button>
            {errs.length ? (
              <ul data-testid="approval-tier-errors" className="list-disc space-y-0.5 pl-5 text-xs text-destructive">
                {errs.map((e) => <li key={e}>{e}</li>)}
              </ul>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Batal</Button>
            <Button data-testid="approval-tier-apply" disabled={errs.length > 0} onClick={apply}>Terapkan ke draf</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
