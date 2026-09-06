import React, { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import api from "@/services/apiClient";
import { formatIDR } from "@/utils/formatters";
import RabTemplateTools from "./RabTemplateTools";
import RabVersionHistory from "./RabVersionHistory";
import { P80, P81 } from "@/constants/testIds";

const EMPTY_ROW = { code: "", description: "", category: "struktur", uom: "unit", qty: "1", unit_price: "", step_code: "" };
const total = (rows) => rows.reduce((s, r) => s + Math.round((Number(r.qty) || 0) * (Number(r.unit_price) || 0)), 0);
const toRows = (items) => (items || []).map((it) => ({ ...it, qty: String(it.qty), unit_price: String(it.unit_price), step_code: it.step_code || "" }));

/** Editor RAB tertempel pada TIPE unit atau ADD-ON (kind: unit_type | addon). */
export default function RabTemplateDialog({ kind, target, candidates, open, onOpenChange, onDone }) {
  const [rows, setRows] = useState([]);
  const [steps, setSteps] = useState([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [preview, setPreview] = useState("");
  const [histKey, setHistKey] = useState(0);
  const setRow = (i, patch) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const loadCurrent = () => api.get(`/rab/templates/${kind}/${encodeURIComponent(target.ref_code)}`)
    .then((r) => setRows(toRows(r.data.data.items))).catch(() => setRows([]));

  useEffect(() => {
    if (!open || !target) return;
    setNote(""); setPreview("");
    loadCurrent();
    if (kind === "unit_type") {
      api.get("/build/templates").then((r) => setSteps((r.data.data || []).map((t) => ({
        code: t.code, name: t.name, unit_types: t.unit_types || [],
        steps: (t.steps || []).map((s) => ({ code: s.code, label: `${s.code} · ${s.name}` })),
      })))).catch(() => setSteps([]));
    }
  }, [open, kind, target]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/rab/templates/${kind}/${encodeURIComponent(target.ref_code)}`, {
        note: note || null,
        items: rows.map((r) => ({ ...r, qty: Number(r.qty) || 0, unit_price: Math.round(Number(r.unit_price) || 0), step_code: r.step_code || null })),
      });
      toast.success("RAB tersimpan."); onOpenChange(false); onDone && onDone();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan RAB."); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={P80.tplDialog} className="max-h-[88vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>RAB {kind === "unit_type" ? "tipe" : "add-on"} {target?.ref_code} — {target?.name}</DialogTitle>
          <DialogDescription>
            {kind === "unit_type"
              ? "Biaya membangun SATU unit tipe ini. Proyek mengalikan dengan jumlah unit; SPK unit mengambil baris ini. Kolom langkah menautkan baris ke jadwal pembangunan (acuan harga borongan)."
              : "Biaya (HPP) menyediakan satu add-on ini — dipakai SPK add-on & margin add-on."}
          </DialogDescription>
        </DialogHeader>
        <RabTemplateTools kind={kind} target={target} candidates={candidates}
          onLoadRows={(rs, msg) => { setRows(rs); setPreview(msg); }} />
        {preview ? <p data-testid={P81.previewBanner} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">{preview} <button type="button" className="underline" onClick={() => { loadCurrent(); setPreview(""); }}>Batalkan, muat RAB tersimpan</button></p> : null}
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} data-testid={P80.tplRow} className="grid grid-cols-12 items-center gap-2 rounded-lg border bg-secondary/40 p-2">
              <Input className="col-span-2 h-8 text-xs" placeholder="Kode" value={r.code} onChange={(e) => setRow(i, { code: e.target.value })} />
              <Input data-testid={P80.tplDesc} className="col-span-3 h-8 text-xs" placeholder="Uraian pekerjaan" value={r.description} onChange={(e) => setRow(i, { description: e.target.value })} />
              <div className="col-span-2"><ReferenceSelect group="work_category" value={r.category} onChange={(v) => setRow(i, { category: v })} /></div>
              <Input data-testid={P80.tplQty} className="col-span-1 h-8 text-xs" type="number" step="0.01" placeholder="Vol" value={r.qty} onChange={(e) => setRow(i, { qty: e.target.value })} />
              <RupiahInput data-testid={P80.tplPrice} className="col-span-3 h-8 text-xs" placeholder="Harga satuan" value={r.unit_price} onChange={(e) => setRow(i, { unit_price: e.target.value })} />
              <Button variant="ghost" size="icon" className="col-span-1 h-8 w-8 text-rose-600" aria-label="Hapus baris" onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
              {kind === "unit_type" ? (
                <select data-testid={P80.tplStep} className="col-span-6 h-8 rounded-md border bg-background px-2 text-xs" value={r.step_code} onChange={(e) => setRow(i, { step_code: e.target.value })}>
                  <option value="">— tanpa tautan langkah jadwal —</option>
                  {r.step_code && !steps.some((t) => t.steps.some((s) => s.code === r.step_code) && (t.unit_types.includes(target?.name) || !steps.some((x) => x.unit_types.includes(target?.name))))
                    ? <option value={r.step_code} label={`${r.step_code} — bukan langkah jadwal tipe ini (tidak akan masuk lingkup)`}>{`${r.step_code} — bukan langkah jadwal tipe ini (tidak akan masuk lingkup)`}</option> : null}
                  {(steps.some((t) => t.unit_types.includes(target?.name)) ? steps.filter((t) => t.unit_types.includes(target?.name)) : steps).map((t) => (
                    <optgroup key={t.code} label={`${t.code} — ${t.name}`}>
                      {t.steps.map((s) => <option key={s.code} value={s.code} label={s.label}>{s.label}</option>)}
                    </optgroup>
                  ))}
                </select>
              ) : null}
              <p className="col-span-6 text-right text-xs tabular-nums text-muted-foreground">= {formatIDR(Math.round((Number(r.qty) || 0) * (Number(r.unit_price) || 0)))}</p>
            </div>
          ))}
          <Button data-testid={P80.tplAddRow} size="sm" variant="outline" onClick={() => setRows((rs) => [...rs, { ...EMPTY_ROW }])}><Plus className="mr-1 h-3.5 w-3.5" /> Tambah baris</Button>
        </div>
        <div data-testid={P80.tplTotal} className="rounded-lg bg-secondary p-3 text-sm">Total RAB per {kind === "unit_type" ? "unit" : "add-on"}: <b className="tabular-nums">{formatIDR(total(rows))}</b>
          {target?.base_price || target?.unit_price ? <span className="ml-2 text-xs text-muted-foreground">· harga jual {formatIDR(target.base_price || target.unit_price)} → margin {formatIDR((target.base_price || target.unit_price) - total(rows))}</span> : null}</div>
        <Input data-testid={P81.tplNote} className="h-8 text-xs" placeholder="Catatan perubahan (opsional, tampil di riwayat versi)" value={note} onChange={(e) => setNote(e.target.value)} />
        <RabVersionHistory kind={kind} target={open ? target : null} reloadKey={histKey}
          onRestored={() => { loadCurrent(); setPreview(""); setHistKey((k) => k + 1); onDone && onDone(); }} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Batal</Button>
          <Button data-testid={P80.tplSave} disabled={busy} onClick={save}>Simpan RAB</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
