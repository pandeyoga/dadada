import React, { useRef, useState } from "react";
import { toast } from "sonner";
import { Download, FileSpreadsheet, Upload } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import api from "@/services/apiClient";
import { LEADS } from "@/constants/testIds";

const ACCEPT = ".xlsx,.xlsm,.csv";

export default function ImportLeadsDialog({ open, onOpenChange, onDone }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const reset = () => { setFile(null); setPreview(null); };
  const close = (v) => { if (!v) reset(); onOpenChange(v); };

  const send = async (f, dryRun) => {
    const fd = new FormData();
    fd.append("file", f);
    fd.append("dry_run", dryRun ? "true" : "false");
    const res = await api.post("/leads/import-file", fd, { headers: { "Content-Type": "multipart/form-data" } });
    return res.data.data;
  };

  const pick = async (f) => {
    if (!f) return;
    setFile(f); setPreview(null); setBusy(true);
    try { setPreview(await send(f, true)); }
    catch (e) { toast.error(e?.response?.data?.detail || "Berkas tidak bisa dibaca."); setFile(null); }
    finally { setBusy(false); }
  };

  const commit = async () => {
    setBusy(true);
    try {
      const r = await send(file, false);
      toast.success(`${r.insert} lead baru, ${r.update} diperbarui.`);
      onDone?.(); close(false);
    } catch (e) { toast.error(e?.response?.data?.detail || "Impor gagal."); }
    finally { setBusy(false); }
  };

  const downloadTemplate = async () => {
    try {
      const res = await api.get("/leads/import-template.xlsx", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = Object.assign(document.createElement("a"), { href: url, download: "SIPRO_Template_Leads.xlsx" });
      a.click(); URL.revokeObjectURL(url);
    } catch { toast.error("Template tidak bisa diunduh."); }
  };

  const errRows = (preview?.rows || []).filter((r) => r.errors?.length);
  const warnRows = (preview?.rows || []).filter((r) => !r.errors?.length && r.warnings?.length);

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent data-testid={LEADS.importDialog} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Impor Lead dari Excel</DialogTitle>
          <DialogDescription>
            Minimal kolom <b>Nama</b> dan <b>No. HP</b>. Nomor yang sudah ada diperbarui, bukan digandakan.
            Lead baru masuk tahap Akuisisi.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Button data-testid={LEADS.importTemplateBtn} variant="link" size="sm" className="h-auto p-0"
            onClick={downloadTemplate}>
            <Download className="mr-1.5 h-4 w-4" /> Unduh template Excel
          </Button>

          <input ref={inputRef} type="file" accept={ACCEPT} className="hidden"
            data-testid={LEADS.importFileInput}
            onChange={(e) => pick(e.target.files?.[0])} />
          <button type="button" data-testid={LEADS.importDropzone}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files?.[0]); }}
            className="flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-sm transition-colors hover:border-primary hover:bg-primary/5">
            <FileSpreadsheet className="h-8 w-8 text-muted-foreground" />
            {file ? <span className="font-medium">{file.name}</span>
              : <span className="text-muted-foreground">Klik atau seret berkas .xlsx / .csv ke sini</span>}
          </button>

          {busy && !preview ? <p className="text-sm text-muted-foreground">Memeriksa berkas…</p> : null}

          {preview ? (
            <div data-testid={LEADS.importPreview} className="space-y-2 rounded-lg border bg-secondary/40 p-3 text-sm">
              <div className="grid grid-cols-4 gap-2 text-center">
                <Stat label="Baris" value={preview.total} testId={LEADS.importStatTotal} />
                <Stat label="Baru" value={preview.insert} tone="text-emerald-600" testId={LEADS.importStatInsert} />
                <Stat label="Diperbarui" value={preview.update} tone="text-sky-600" testId={LEADS.importStatUpdate} />
                <Stat label="Error" value={preview.error} tone={preview.error ? "text-destructive" : ""} testId={LEADS.importStatError} />
              </div>
              {errRows.length ? (
                <ul className="max-h-32 space-y-1 overflow-auto text-xs text-destructive">
                  {errRows.slice(0, 20).map((r) => (
                    <li key={r.row}>Baris {r.row}: {r.errors.join(" ")}</li>
                  ))}
                </ul>
              ) : null}
              {warnRows.length ? (
                <p className="text-xs text-amber-700">{warnRows.length} baris dengan peringatan (tetap diimpor).</p>
              ) : null}
              {preview.error ? (
                <p className="text-xs text-muted-foreground">Baris error dilewati; baris lain tetap diimpor.</p>
              ) : null}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => close(false)} disabled={busy}>Batal</Button>
          <Button data-testid={LEADS.importSubmit} onClick={commit}
            disabled={busy || !preview || !(preview.insert + preview.update)}>
            <Upload className="mr-1.5 h-4 w-4" />
            {busy && preview ? "Mengimpor…" : `Impor ${preview ? preview.insert + preview.update : ""} lead`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Stat({ label, value, tone = "", testId }) {
  return (
    <div data-testid={testId} className="rounded-md bg-card p-2">
      <p className={`text-lg font-semibold tabular-nums ${tone}`}>{value ?? 0}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}
