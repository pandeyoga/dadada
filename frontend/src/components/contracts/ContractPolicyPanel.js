import React, { useCallback, useEffect, useState } from "react";
import { History, Lock, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { formatDateWIB, formatIDR } from "@/utils/formatters";

const MIN_REASON = 10;
const T = (id) => `w2b-policy-${id}`;

/** Nilai ringkas untuk satu kunci: enum → label opsi, persen → "50%", lainnya apa adanya. */
const show = (row, value) => {
  if (value === null || value === undefined) return "-";
  if (row.type === "enum") return (row.option_labels || {})[value]?.split(" — ")[0] || value;
  if (row.type === "pct") return `${value}%`;
  return String(value);
};

/**
 * ContractPolicyPanel — KEBIJAKAN TINGKAT KONTRAK (W2-B): nilai yang berlaku untuk kontrak ini + asalnya, ubah khusus kontrak ini
 * (alasan wajib), atau kembali mengikuti pengaturan proyek/organisasi. Server yang memutuskan boleh/tidaknya (uang sudah bergerak,
 * kontrak batal, izin) — pesan penolakannya ditampilkan apa adanya sebagai toast, dan alasan terkunci tampil di baris kuncinya.
 * Endpoint: GET /contracts/{id}/policy · PUT|DELETE /contracts/{id}/policy/{key}.
 */
export default function ContractPolicyPanel({ contract, onChanged }) {
  const { can } = useAuth();
  const [data, setData] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [dlg, setDlg] = useState(null);   // {row, mode: "set" | "clear"}
  const [form, setForm] = useState({ value: "", reason: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/contracts/${contract.id}/policy`);
      setData(r.data.data);
      setLoadErr("");
    } catch (e) {
      setLoadErr(e?.response?.data?.detail || "Kebijakan kontrak tidak dapat dimuat.");
    }
  }, [contract.id]);
  useEffect(() => { load(); }, [load, contract.updated_at]);

  if (loadErr) {
    return (
      <section data-testid={T("error")} className="rounded-lg border bg-card p-4 text-sm text-destructive shadow-[var(--shadow-card)]">
        {loadErr} <Button size="sm" variant="outline" className="ml-2" onClick={load}>Muat ulang</Button>
      </section>
    );
  }
  if (!data || !(data.keys || []).length) return null;

  const mayWrite = (row) => can("contracts", "update") && can(row.writer[0], row.writer[1]);
  const open = (row, mode) => {
    setForm({ value: mode === "set" ? String(row.value ?? "") : "", reason: "" });
    setDlg({ row, mode });
  };
  const reasonOk = form.reason.trim().length >= MIN_REASON;

  const submit = async () => {
    const { row, mode } = dlg;
    setBusy(true);
    try {
      let res;
      if (mode === "set") {
        const value = row.type === "pct" ? Number(form.value) : form.value;
        res = await api.put(`/contracts/${contract.id}/policy/${row.key}`, { value, reason: form.reason.trim() });
      } else {
        res = await api.delete(`/contracts/${contract.id}/policy/${row.key}`, { params: { reason: form.reason.trim() } });
      }
      const after = res.data?.data?.after;
      toast.success(mode === "set" ? "Kebijakan kontrak diperbarui." : "Kembali mengikuti pengaturan proyek/organisasi.");
      if (after?.error) toast.warning(after.error);
      else if (after?.voided) toast.info(`Invoice biaya yang belum dibayar dibatalkan (${after.voided})${after.reissued ? ` dan diterbitkan ulang: ${after.reissued}` : "; tidak ada lagi biaya yang ditagih ke pembeli"}.`);
      setDlg(null);
      await load();
      onChanged && onChanged();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan kebijakan kontrak.");   // 400 server tampil terbaca
    } finally {
      setBusy(false);
    }
  };

  const bphtb = (data.summary || {}).bphtb;
  return (
    <section data-testid={T("panel")} className="space-y-3 rounded-lg border bg-card p-4 shadow-[var(--shadow-card)]">
      <div>
        <h3 className="flex items-center gap-2 font-heading text-base font-semibold">
          <SlidersHorizontal className="h-4 w-4" /> Kebijakan kontrak
        </h3>
        <p className="text-xs text-muted-foreground">
          Nilai yang berlaku untuk kontrak ini dibekukan saat kontrak dibuat — mengganti pengaturan proyek/organisasi kemudian tidak
          mengubahnya. Ubah di sini hanya untuk kontrak ini.
        </p>
      </div>

      {bphtb ? (
        <p data-testid={T("summary")} className="rounded-md border bg-background p-2.5 text-sm">
          BPHTB <strong>{formatIDR(bphtb.total)}</strong> → pembeli <strong data-testid={T("summary-buyer")}>{formatIDR(bphtb.buyer)}</strong>
          {" "}· developer <strong data-testid={T("summary-dev")}>{formatIDR(bphtb.developer)}</strong>
          {bphtb.discount ? <span className="text-muted-foreground"> (setelah potongan promo {formatIDR(bphtb.discount)})</span> : null}
        </p>
      ) : null}

      <div className="space-y-2">
        {data.keys.map((row) => (
          <div key={row.key} data-testid={T(`row-${row.key}`)} data-value={String(row.value)} data-origin={row.origin}
            className="space-y-1.5 rounded-lg border bg-background p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium">{row.label}</p>
                <p className="text-xs text-muted-foreground">
                  <span data-testid={T(`value-${row.key}`)} className="font-medium text-foreground">{show(row, row.value)}</span>
                  {" · "}<span data-testid={T(`origin-${row.key}`)}>{row.origin_label}</span>
                  {row.override ? ` · diubah ${row.override.by} (${formatDateWIB(row.override.at)})` : ""}
                </p>
                {row.override?.reason ? <p className="text-[11px] text-muted-foreground">Alasan: {row.override.reason}</p> : null}
                {row.inherited && String(row.inherited.value) !== String(row.value) ? (
                  <p className="text-[11px] text-muted-foreground">
                    Pengaturan proyek/organisasi sekarang: {show(row, row.inherited.value)} (tidak mengubah kontrak ini).
                  </p>
                ) : null}
              </div>
              {mayWrite(row) ? (
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Button data-testid={T(`edit-${row.key}`)} size="sm" variant="outline" disabled={!row.editable} onClick={() => open(row, "set")}>
                    Ubah untuk kontrak ini
                  </Button>
                  {row.override ? (
                    <Button data-testid={T(`clear-${row.key}`)} size="sm" variant="ghost" disabled={!row.editable} onClick={() => open(row, "clear")}>
                      Ikuti proyek/organisasi
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
            {!row.editable && row.locked_reason ? (
              <p data-testid={T(`locked-${row.key}`)} className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
                <Lock className="mt-0.5 h-3 w-3 shrink-0" /> {row.locked_reason}
              </p>
            ) : null}
          </div>
        ))}
      </div>

      {(data.history || []).length ? (
        <details data-testid={T("history")} className="text-xs">
          <summary className="flex cursor-pointer items-center gap-1.5 text-muted-foreground"><History className="h-3 w-3" /> Riwayat perubahan ({data.history.length})</summary>
          <ul className="mt-1.5 space-y-1">
            {data.history.map((h, i) => {
              const row = data.keys.find((k) => k.key === h.key) || { type: "enum", option_labels: {} };
              return (
                <li key={`${h.at}-${i}`} data-testid={T("history-row")} className="text-muted-foreground">
                  {formatDateWIB(h.at)} · {h.by}: {row.label || h.key} {show(row, h.from)} → {show(row, h.to)}
                  {h.action === "clear" ? " (mengikuti proyek/organisasi)" : ""}{h.reason ? ` — ${h.reason}` : ""}
                </li>
              );
            })}
          </ul>
        </details>
      ) : null}

      <Dialog open={!!dlg} onOpenChange={(o) => { if (!o) setDlg(null); }}>
        <DialogContent data-testid={T("dialog")} className="max-w-md bg-background">
          {dlg ? (
            <>
              <DialogHeader>
                <DialogTitle>{dlg.mode === "set" ? "Ubah" : "Ikuti proyek/organisasi"}: {dlg.row.label}</DialogTitle>
                <DialogDescription>
                  {dlg.mode === "set"
                    ? "Berlaku hanya untuk kontrak ini. Bila ini mengubah tagihan, invoice biaya yang belum dibayar dibatalkan dan diterbitkan ulang; ditolak bila uangnya sudah bergerak."
                    : `Penimpaan dicabut dan kontrak memakai pengaturan proyek/organisasi SEKARANG (${show(dlg.row, dlg.row.inherited.value)}).`}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                {dlg.mode === "set" && dlg.row.type === "enum" ? (
                  <>
                    <Label>Pilihan</Label>
                    <Select value={form.value} onValueChange={(v) => setForm((f) => ({ ...f, value: v }))}>
                      <SelectTrigger data-testid={T("value")} className="bg-background"><SelectValue placeholder="Pilih" /></SelectTrigger>
                      <SelectContent>
                        {dlg.row.options.map((o) => (
                          <SelectItem key={o} value={o} disabled={!!dlg.row.unavailable[o]}>
                            {(dlg.row.option_labels || {})[o] || o}{dlg.row.unavailable[o] ? " (belum tersedia)" : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </>
                ) : null}
                {dlg.mode === "set" && dlg.row.type === "pct" ? (
                  <>
                    <Label htmlFor="w2b-pct">Persen ({dlg.row.min ?? 0}–{dlg.row.max ?? 100})</Label>
                    <Input id="w2b-pct" data-testid={T("share")} type="number" min={dlg.row.min ?? 0} max={dlg.row.max ?? 100} step="0.01"
                      className="bg-background" value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} />
                  </>
                ) : null}
                <Label htmlFor="w2b-reason">Alasan (minimal {MIN_REASON} karakter)</Label>
                <Textarea id="w2b-reason" data-testid={T("reason")} rows={3} className="bg-background" value={form.reason}
                  onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDlg(null)}>Batal</Button>
                <Button data-testid={T("submit")} disabled={busy || !reasonOk || (dlg.mode === "set" && form.value === "")} onClick={submit}>
                  {dlg.mode === "set" ? "Simpan" : "Cabut penimpaan"}
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </section>
  );
}
