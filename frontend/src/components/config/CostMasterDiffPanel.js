import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { GitCompare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { W2C } from "@/constants/testIds";

const STATUS = {
  sama: ["Sama", "bg-emerald-100 text-emerald-900"],
  beda: ["Berselisih", "bg-red-100 text-red-900"],
  belum_dimigrasi: ["Belum dimigrasi", "bg-amber-100 text-amber-900"],
  hanya_aturan: ["Hanya di aturan All-in", "bg-amber-100 text-amber-900"],
  hanya_katalog_biaya: ["Hanya di katalog (belum didaftarkan)", "bg-slate-100 text-slate-800"],
  hanya_katalog: ["Bukan komponen biaya", "bg-slate-100 text-slate-700"],
  rujukan_putus: ["Rujukan skema putus", "bg-red-100 text-red-900"],
};

const show = (v) => {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "semua skema";
  if (typeof v === "boolean") return v ? "ya" : "tidak";
  return String(v);
};

/**
 * Laporan selisih "katalog vs aturan" (W2-C #16 / FN-01): katalog `price_components` = SUMBER, kebijakan Biaya All-in = ATURAN.
 * Pada mode bayangan tagihan tetap dari master All-in — panel ini hanya MELAPORKAN selisih dan menyediakan migrasi/penyelarasan.
 */
export default function CostMasterDiffPanel({ onChanged }) {
  const { can } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [syncOpen, setSyncOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [showAll, setShowAll] = useState(false);
  const mayManage = can("finance", "manage");

  const load = useCallback(async () => {
    try {
      const r = await api.get("/cost-master/diff");
      setData(r.data.data); setError("");
    } catch (e) { setError(e?.response?.data?.detail || "Gagal memuat laporan selisih."); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const migrate = async () => {
    setBusy(true);
    try {
      const r = await api.post("/cost-master/migrate");
      const d = r.data.data;
      toast.success(d.sudah_selaras ? "Sudah termigrasi — tidak ada perubahan."
        : `Migrasi selesai: ${d.katalog_dibuat} baris katalog dibuat, ${d.blok_biaya_diisi} blok biaya diisi, ${d.rujukan_dipasang} rujukan dipasang.`);
      await load(); onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Migrasi gagal."); } finally { setBusy(false); }
  };
  const sync = async () => {
    setBusy(true);
    try {
      const r = await api.post("/cost-master/sync", { reason, direction: "katalog_ikut_aturan" });
      toast.success(`Katalog diselaraskan: ${r.data.data.diselaraskan} komponen. Tagihan tidak berubah.`);
      setSyncOpen(false); setReason(""); await load(); onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Penyelarasan gagal."); } finally { setBusy(false); }
  };

  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (!data) return <p className="text-sm text-muted-foreground">Memuat laporan selisih…</p>;
  const s = data.summary;
  const quiet = (r) => r.status === "sama" || r.status === "hanya_katalog";   // tidak bermasalah / bukan komponen biaya
  const rows = data.rows.filter((r) => showAll || !quiet(r));
  const nQuiet = data.rows.filter(quiet).length;
  const mode = data.mode.value;

  return (
    <section data-testid={W2C.diffPanel} className="space-y-3 rounded-lg border bg-card p-3 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="section-title flex items-center gap-1.5"><GitCompare className="h-4 w-4" /> Selisih katalog vs aturan All-in</h3>
          <p className="text-xs text-muted-foreground">
            Mode sumber master: <strong data-testid={W2C.mode} data-mode={mode}>{mode === "katalog_sumber" ? "Katalog sebagai sumber" : "Bayangan (tagihan tetap dari Biaya All-in)"}</strong>
            {" "}— diatur di Aturan Bisnis › kunci <code>cost.master_mode</code>.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button data-testid={W2C.migrateBtn} size="sm" variant="outline" disabled={!mayManage || busy} onClick={migrate}
            title={mayManage ? "Buat baris katalog & rujukan yang belum ada (tidak mengubah tagihan)" : "Butuh izin finance:manage"}>
            Migrasi ke katalog
          </Button>
          <Button data-testid={W2C.syncBtn} size="sm" disabled={!mayManage || busy || s.nol} onClick={() => setSyncOpen(true)}
            title={mayManage ? "Samakan katalog dengan aturan All-in yang berjalan (tagihan tidak berubah)" : "Butuh izin finance:manage"}>
            Selaraskan katalog
          </Button>
        </div>
      </div>

      <p data-testid={W2C.diffSummary} data-zero={s.nol ? "1" : "0"} data-rows={s.baris_selisih}
        className={`rounded-md border p-2 text-sm ${s.nol ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
        {s.nol
          ? <>Tidak ada selisih: {s.komponen_aturan} komponen aturan All-in sama dengan katalog.</>
          : <><strong>{s.baris_selisih} komponen berselisih</strong> ({s.selisih} butir) dari {s.komponen_aturan} komponen aturan All-in.</>}
      </p>
      <p data-testid={W2C.katalogSumber} data-available={data.katalog_sumber.tersedia ? "1" : "0"} className="text-xs text-muted-foreground">
        Opsi <em>Katalog sebagai sumber</em>: {data.katalog_sumber.tersedia
          ? "tersedia — selisih 0 (uji ekuivalensi hitung-ulang skema dijalankan saat opsi dipilih)."
          : <>belum tersedia — {data.katalog_sumber.alasan}</>}
      </p>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-secondary/60 text-xs uppercase text-muted-foreground">
            <tr><th className="px-3 py-2 text-left">Kode</th><th className="px-3 py-2 text-left">Status</th><th className="px-3 py-2 text-left">Selisih (katalog → aturan)</th></tr>
          </thead>
          <tbody className="divide-y">
            {rows.length === 0 ? <tr><td colSpan={3} className="px-3 py-3 text-xs text-muted-foreground">Semua komponen biaya sama antara katalog dan aturan All-in.</td></tr> : null}
            {rows.map((r) => {
              const [label, cls] = STATUS[r.status] || [r.status, ""];
              return (
                <tr key={`${r.code}-${r.status}-${r.name}`} data-testid={W2C.diffRow} data-code={r.code} data-status={r.status}>
                  <td className="px-3 py-2 align-top"><span className="font-mono text-xs">{r.code}</span><div className="text-xs text-muted-foreground">{r.name}</div></td>
                  <td className="px-3 py-2 align-top"><span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}>{label}</span></td>
                  <td className="px-3 py-2 align-top text-xs">
                    {r.diffs.length ? (
                      <ul className="space-y-0.5">
                        {r.diffs.map((d) => (
                          <li key={d.field} data-testid={W2C.diffField} data-field={d.field}>
                            <span className="font-medium">{d.label}</span>: <span className="text-red-700">{show(d.katalog)}</span> → <span className="text-emerald-700">{show(d.aturan)}</span>
                            {d.kind === "kolom_lama" ? <span className="ml-1 text-muted-foreground">(kolom lama katalog)</span> : null}
                          </li>
                        ))}
                      </ul>
                    ) : <span className="text-muted-foreground">{r.catatan || "—"}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input type="checkbox" data-testid="w2c-diff-show-all" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Tampilkan juga {nQuiet} baris yang sudah sama atau bukan komponen biaya
      </label>

      <details className="text-xs">
        <summary className="cursor-pointer font-medium">Peta field kedua master</summary>
        <table data-testid={W2C.fieldMap} className="mt-2 w-full text-xs">
          <thead className="text-muted-foreground"><tr><th className="py-1 text-left">Katalog</th><th className="py-1 text-left">Aturan All-in</th><th className="py-1 text-left">Pembawa</th><th className="py-1 text-left">Catatan</th></tr></thead>
          <tbody className="divide-y">
            {data.field_map.map((f) => (
              <tr key={f.katalog + f.aturan}><td className="py-1 pr-2 font-mono">{f.katalog}</td><td className="py-1 pr-2 font-mono">{f.aturan}</td><td className="py-1 pr-2">{f.pembawa}</td><td className="py-1">{f.catatan}</td></tr>
            ))}
          </tbody>
        </table>
      </details>

      <Dialog open={syncOpen} onOpenChange={setSyncOpen}>
        <DialogContent className="max-w-md bg-background">
          <DialogHeader>
            <DialogTitle>Selaraskan katalog dengan aturan All-in</DialogTitle>
            <DialogDescription>
              Katalog disamakan dengan komponen All-in yang sedang berjalan ({s.baris_selisih} komponen). Tagihan dan jurnal TIDAK berubah; nilai katalog lama
              dicatat di log penyelarasan.
            </DialogDescription>
          </DialogHeader>
          <Label htmlFor="w2c-sync-reason">Alasan (min. 10 huruf)</Label>
          <Textarea id="w2c-sync-reason" data-testid={W2C.syncReason} rows={3} className="bg-background" value={reason} onChange={(e) => setReason(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncOpen(false)}>Batal</Button>
            <Button data-testid={W2C.syncConfirm} disabled={busy || reason.trim().length < 10} onClick={sync}>Selaraskan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
