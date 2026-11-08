import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import DataTable from "@/components/patterns/DataTable";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import api from "@/services/apiClient";
import { useReference } from "@/context/ReferenceContext";
import { formatIDR } from "@/utils/formatters";
import CostMasterDiffPanel from "@/components/config/CostMasterDiffPanel";
import { CONFIG, W2C } from "@/constants/testIds";

const CALC = { nominal_tetap: "Nominal tetap", persen_harga: "% × harga", rumus_bphtb: "Rumus BPHTB (% × (harga − NPOPTKP))" };
const BILL = { customer_pass_through: "Ditagih ke pembeli (titipan)", developer_borne: "Ditalangi developer (beban)" };

/**
 * Katalog komponen biaya (keputusan owner D12: tiap tipe pembayaran punya komponen berbeda). W2-C #16: katalog ini adalah SUMBER
 * master komponen biaya; baris bermuatan biaya membawa blok `cost` (cara hitung, ditagih/ditalangi, akun GL) yang pada mode
 * "katalog sebagai sumber" dipakai tagihan & jurnal. Pada mode bayangan tagihan masih dari Biaya All-in — lihat panel selisih.
 */
export default function PriceComponentPanel() {
  const { labelOf } = useReference();
  const [matrix, setMatrix] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState({ q: "", sort: "code", direction: "asc", skip: 0, limit: 50 });
  const [form, setForm] = useState(null);
  const [mode, setMode] = useState("bayangan");
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [m, list, eff] = await Promise.all([
        api.get("/catalog/price-components/matrix"),
        api.get("/catalog/price-components"),
        api.get("/settings/effective", { params: { keys: "cost.master_mode" } }).catch(() => ({ data: { data: {} } })),
      ]);
      setMatrix(m.data.data);
      setRows(list.data.data || []);
      setMode(eff.data.data?.["cost.master_mode"] || "bayangan");
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal memuat komponen biaya.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setCost = (k, v) => setForm((f) => ({ ...f, cost: { ...f.cost, [k]: v } }));
  const submit = async () => {
    try {
      // Baris bermuatan biaya: kolom lama (nilai bawaan, akun GL, skema) DITURUNKAN server dari blok biaya — tidak dikirim.
      const body = form.cost ? {
        label: form.label, note: form.note || null, active: form.active !== false,
        cost: { ...form.cost, amount: Number(form.cost.amount) || 0, pct: Number(form.cost.pct) || 0 },
      } : {
        label: form.label, value: Number(form.value) || 0,
        finance_treatment: form.finance_treatment, gl_account: form.gl_account || null,
        applies_schemes: form.applies_schemes || [], note: form.note || null,
      };
      await api.put(`/catalog/price-components/${form.id}`, body);
      toast.success("Komponen biaya diperbarui.");
      setForm(null); load(); setReloadKey((k) => k + 1);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan.");
    }
  };

  const schemes = matrix?.schemes || [];
  const toggleScheme = (value) => setForm((f) => {
    const set = new Set(f.applies_schemes || []);
    if (set.has(value)) set.delete(value); else set.add(value);
    return { ...f, applies_schemes: [...set] };
  });

  const columns = [
    { key: "code", header: "Kode", sortable: true,
      render: (r) => <span className="font-mono text-xs">{r.code}</span> },
    { key: "label", header: "Komponen", sortable: true,
      render: (r) => (
        <div>
          <div className="font-medium">{r.label}</div>
          {r.note ? <div className="text-xs text-muted-foreground">{r.note}</div> : null}
        </div>
      ) },
    { key: "group", header: "Kelompok", sortable: true,
      render: (r) => labelOf("price_component_group", r.group) },
    { key: "finance_treatment", header: "Perlakuan keuangan", sortable: true,
      render: (r) => (
        <div>
          <div>{labelOf("finance_treatment", r.finance_treatment)}</div>
          {r.cost ? <div className="text-[11px]" data-testid="w2c-cost-bill">{BILL[r.cost.default_treatment]} · {CALC[r.cost.calc_method]}
            {r.cost.calc_method === "nominal_tetap" ? ` · ${formatIDR(r.cost.amount)}` : ` · ${r.cost.pct}%`}</div> : null}
          <div className="font-mono text-[10px] text-muted-foreground">
            {r.cost ? `${r.cost.gl_expense} / ${r.cost.gl_liability} / ${r.cost.gl_ap}` : (r.gl_account || "-")}
          </div>
        </div>
      ),
      exportValue: (r) => r.finance_treatment },
    { key: "value", header: "Nilai bawaan", align: "right",
      render: (r) => (r.value ? formatIDR(r.value) : "—"), exportValue: (r) => r.value },
    ...schemes.map((s) => ({
      key: `scheme_${s.value}`, header: s.label,
      render: (r) => {
        const on = !(r.applies_schemes || []).length || (r.applies_schemes || []).includes(s.value);
        return <span className={on ? "font-medium text-primary" : "text-muted-foreground"}>
          {on ? "Ya" : "–"}
        </span>;
      },
      exportValue: (r) => ((!(r.applies_schemes || []).length
        || (r.applies_schemes || []).includes(s.value)) ? "ya" : "tidak"),
    })),
    { key: "actions", header: "Aksi", align: "right", sticky: true, sticky: true,
      render: (r) => (
        <Button data-testid={CONFIG.priceEdit} size="sm" variant="ghost"
          onClick={() => setForm({ ...r })}>
          <Pencil className="h-3.5 w-3.5" />
        </Button>
      ), exportValue: () => "" },
  ];

  return (
    <div data-testid={CONFIG.pricePanel} className="space-y-3">
      <div data-testid={W2C.banner} data-mode={mode} className="rounded-md border bg-secondary p-3 text-sm">
        {mode === "katalog_sumber" ? (
          <>
            <strong>Katalog adalah SUMBER master komponen biaya.</strong> Baris bermuatan biaya (BPHTB, notaris, bank, asuransi, …) di bawah
            ini DIPAKAI tagihan & jurnal untuk reservasi, penawaran, dan amandemen BARU; mengubahnya langsung berlaku ke depan (snapshot
            yang sudah terbit tidak berubah). Tab <strong>Biaya All-in</strong> hanya menentukan komponen mana yang berlaku di tiap skema.
            Baris harga/pajak/potongan lain hanya referensi.
          </>
        ) : (
          <>
            <strong>Mode bayangan — penyatuan master komponen biaya sedang disiapkan.</strong> Tagihan & jurnal biaya transaksi MASIH
            dihitung dari master di tab <strong>Biaya All-in</strong>; katalog ini dibandingkan dengannya dan selisihnya dilaporkan di
            bawah (belum mengubah tagihan maupun jurnal). Baris bermuatan biaya akan menjadi sumber bila opsi
            “Katalog sebagai sumber” dipilih di Aturan Bisnis (hanya bila selisih 0). Baris harga/pajak/potongan lain hanya referensi.
          </>
        )}
      </div>
      <CostMasterDiffPanel key={reloadKey} onChanged={load} />
      <DataTable
        testId="config-price-table"
        testIds={{ search: "config-price-search", row: CONFIG.priceRow,
          export: "config-price-export", columns: "config-price-columns" }}
        columns={columns} rows={rows} total={rows.length} query={query}
        onQueryChange={(p) => setQuery((q) => ({ ...q, ...p }))}
        loading={loading} error={error} onRefresh={load}
        searchPlaceholder="Cari komponen biaya…" exportName="komponen-biaya"
        emptyTitle="Belum ada komponen biaya" />

      <Dialog open={!!form} onOpenChange={(o) => { if (!o) setForm(null); }}>
        <DialogContent className="max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ubah komponen biaya</DialogTitle>
            <DialogDescription>{form?.code}</DialogDescription>
          </DialogHeader>
          {form ? (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="pc-label">Nama komponen</Label>
                <Input id="pc-label" value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })} />
              </div>
              {form.cost ? (
                <div className="space-y-3" data-testid="w2c-cost-form">
                  <p className="rounded-md border bg-secondary p-2 text-xs">
                    Komponen biaya: akun GL, nilai bawaan, dan skema berlaku <strong>diturunkan</strong> dari blok biaya di bawah (tidak bisa
                    saling bertentangan).{mode === "katalog_sumber" ? " Perubahan langsung dipakai tagihan baru." : " Pada mode bayangan perubahan di sini belum dipakai tagihan."}
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1.5"><Label>Cara hitung</Label>
                      <Select value={form.cost.calc_method} disabled={form.code === "BOOKING"} onValueChange={(v) => setCost("calc_method", v)}>
                        <SelectTrigger data-testid="w2c-cost-calc"><SelectValue /></SelectTrigger>
                        <SelectContent>{Object.entries(CALC).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                      </Select></div>
                    <div className="space-y-1.5"><Label>{form.cost.calc_method === "nominal_tetap" ? "Nominal (Rp)" : "Persen (%)"}</Label>
                      {form.cost.calc_method === "nominal_tetap"
                        ? <RupiahInput data-testid="w2c-cost-amount" disabled={form.code === "BOOKING"} value={form.cost.amount || 0} onChange={(e) => setCost("amount", e.target.value)} />
                        : <Input type="number" data-testid="w2c-cost-pct" disabled={form.code === "BOOKING"} value={form.cost.pct} onChange={(e) => setCost("pct", e.target.value)} />}</div>
                  </div>
                  <div className="space-y-1.5"><Label>Ditagih / ditalangi (bawaan)</Label>
                    <Select value={form.cost.default_treatment} onValueChange={(v) => setCost("default_treatment", v)}>
                      <SelectTrigger data-testid="w2c-cost-treatment"><SelectValue /></SelectTrigger>
                      <SelectContent>{Object.entries(BILL).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">Skema All-in tetap boleh menimpa per skema (aturan).</p></div>
                  <div className="grid gap-3 sm:grid-cols-3" data-testid={W2C.costFormGl}>
                    <div className="space-y-1.5"><Label>GL beban</Label><ReferenceSelect group="gl_account" value={form.cost.gl_expense || ""} onChange={(v) => setCost("gl_expense", v)} testId="w2c-gl-expense" /></div>
                    <div className="space-y-1.5"><Label>GL titipan</Label><ReferenceSelect group="gl_account" value={form.cost.gl_liability || ""} onChange={(v) => setCost("gl_liability", v)} testId="w2c-gl-liability" /></div>
                    <div className="space-y-1.5"><Label>GL utang (AP)</Label><ReferenceSelect group="gl_account" value={form.cost.gl_ap || ""} onChange={(v) => setCost("gl_ap", v)} testId="w2c-gl-ap" /></div>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <label className="flex items-center gap-2"><Switch checked={!!form.cost.kpr_only} onCheckedChange={(v) => setCost("kpr_only", v)} /> Hanya KPR</label>
                    <label className="flex items-center gap-2"><Switch checked={form.active !== false} onCheckedChange={(v) => setForm({ ...form, active: v })} /> Aktif</label>
                  </div>
                </div>
              ) : (<>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="pc-value">Nilai bawaan (Rp)</Label>
                  <RupiahInput id="pc-value" data-testid={CONFIG.priceFormValue}
                    value={form.value || 0}
                    onChange={(e) => setForm({ ...form, value: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Akun GL</Label>
                  <ReferenceSelect group="gl_account" value={form.gl_account || ""}
                    testId={CONFIG.priceFormAccount} placeholder="Pilih akun dari bagan akun…"
                    onChange={(v) => setForm({ ...form, gl_account: v })} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Perlakuan keuangan</Label>
                <ReferenceSelect group="finance_treatment" value={form.finance_treatment}
                  testId={CONFIG.priceFormTreatment}
                  onChange={(v) => setForm({ ...form, finance_treatment: v })} />
              </div>
              <div className="space-y-1.5">
                <Label>Berlaku pada skema bayar</Label>
                <div className="flex flex-wrap gap-3 rounded-md border bg-secondary p-2">
                  {schemes.map((sc) => (
                    <label key={sc.value} className="flex items-center gap-2 text-sm">
                      <input type="checkbox"
                        checked={(form.applies_schemes || []).includes(sc.value)}
                        onChange={() => toggleScheme(sc.value)} />
                      {sc.label}
                    </label>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Kosongkan semua = berlaku untuk semua skema.
                </p>
              </div>
              </>)}
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setForm(null)}>Batal</Button>
            <Button data-testid={CONFIG.priceSubmit} onClick={submit}>Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
