import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import { useAuth } from "@/context/AuthContext";
import { useReference } from "@/context/ReferenceContext";
import api from "@/services/apiClient";
import { FINANCE } from "@/constants/testIds";

const MODE_HINT = {
  eksklusif: "Harga BELUM termasuk PPN: DPP = harga; PPN dicatat sebagai kewajiban pajak & Faktur Pajak, tidak ditambahkan ke tagihan pembeli (perilaku bawaan).",
  inklusif: "Harga SUDAH termasuk PPN: DPP = harga ÷ (1 + tarif); PPN = harga − DPP. Tagihan pembeli tetap = harga.",
  bebas_ppn: "Tarif efektif 0% (mis. rumah subsidi): tanpa catatan PPN dan tanpa Faktur Pajak.",
};

/**
 * MASTER PAJAK (W2-A, keputusan #15 + #1): satu sumber tarif/dasar pajak + mode PPN, boleh ditimpa per proyek.
 * Layar ini = lapisan kompatibilitas `/finance/config/tax` (menulis kunci `tax.*` Pusat Konfigurasi). Hanya pemegang
 * `finance:manage` (Manajer Keuangan, owner) yang boleh mengubah; peran lain melihat nilai efektif saja.
 */
export default function TaxMasterSection() {
  const { can } = useAuth();
  const { labelOf } = useReference();
  const mayTax = can("finance", "manage");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [tax, setTax] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/projects").then((r) => setProjects((r.data.data || []).map((p) => ({ id: p.id, name: p.name })))).catch(() => setProjects([]));
  }, []);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/finance/config/tax", { params: { project_id: projectId || undefined } });
      setTax(r.data.data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal memuat konfigurasi pajak."); }
  }, [projectId]);
  useEffect(() => { load(); }, [load]);

  const setT = (k, v) => setTax((prev) => ({ ...prev, [k]: v }));
  const origin = (field) => {
    const o = tax?.origins?.[field];
    return o ? <span className="text-[10px] text-muted-foreground">{labelOf("setting_origin", o)}</span> : null;
  };

  const save = async () => {
    if (projectId && reason.trim().length < 10) { toast.error("Menimpa pajak di tingkat proyek wajib beralasan (minimal 10 karakter)."); return; }
    setBusy(true);
    try {
      const res = await api.put("/finance/config/tax", {
        ppn_rate: Number(tax.ppn_rate) || 0, ppn_mode: tax.ppn_mode, bphtb_rate: Number(tax.bphtb_rate) || 0,
        pph_rate: Number(tax.pph_rate) || 0, npoptkp: Number(tax.npoptkp) || 0,
        njop_per_m2: Number(tax.njop_per_m2) || 0, bank_fee_pct_of_plafon: Number(tax.bank_fee_pct_of_plafon) || 0,
        reason: reason.trim() || undefined, project_id: projectId || undefined,
      });
      setTax(res.data.data);
      setReason("");
      toast.success(projectId ? "Konfigurasi pajak proyek disimpan." : "Konfigurasi pajak disimpan.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan pajak."); }
    finally { setBusy(false); }
  };

  if (!tax) return null;
  return (
    <section data-testid="finance-tax-section" className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-heading text-sm font-semibold">Konfigurasi Pajak (Master Pajak)</h3>
          <p className="text-[11px] text-muted-foreground">
            Nilai acuan — wajib dikonfirmasi penasihat pajak saat go-live. Satu sumber untuk penawaran, tagihan, komponen biaya BPHTB/BANK_FEE,
            catatan pajak, dan Faktur Pajak; boleh ditimpa per proyek. Perubahan berlaku untuk transaksi BARU — penawaran, deal, dan tagihan yang
            sudah ada tidak dihitung ulang.{mayTax ? "" : " Hanya Manajer Keuangan atau owner yang boleh mengubahnya."}
          </p>
        </div>
        <Select value={projectId || "__org__"} onValueChange={(v) => setProjectId(v === "__org__" ? "" : v)}>
          <SelectTrigger data-testid="tax-project" className="h-9 w-[240px]" aria-label="Tingkat pengaturan pajak"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__org__">Seluruh organisasi</SelectItem>
            {projects.map((p) => <SelectItem key={p.id} value={p.id}>Khusus proyek: {p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="space-y-1.5">
          <Label htmlFor="ppn">PPN (%)</Label>
          <Input id="ppn" type="number" value={tax.ppn_rate ?? ""} data-testid="tax-ppn" disabled={!mayTax}
            onChange={(e) => setT("ppn_rate", e.target.value)} />{origin("ppn_rate")}
        </div>
        <div className="space-y-1.5 md:col-span-2">
          <Label>Perlakuan harga terhadap PPN</Label>
          <ReferenceSelect group="ppn_mode" value={tax.ppn_mode || "eksklusif"} onChange={(v) => setT("ppn_mode", v)}
            disabled={!mayTax} testId="tax-ppn-mode" />{origin("ppn_mode")}
          <p data-testid="tax-ppn-mode-hint" className="text-[10px] text-muted-foreground">{MODE_HINT[tax.ppn_mode || "eksklusif"]}</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bphtb">BPHTB (%)</Label>
          <Input id="bphtb" type="number" value={tax.bphtb_rate ?? ""} data-testid="tax-bphtb" disabled={!mayTax}
            onChange={(e) => setT("bphtb_rate", e.target.value)} />{origin("bphtb_rate")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pph">PPh Final (%)</Label>
          <Input id="pph" type="number" value={tax.pph_rate ?? ""} data-testid="tax-pph" disabled={!mayTax}
            onChange={(e) => setT("pph_rate", e.target.value)} />{origin("pph_final_rate")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="npoptkp">NPOPTKP (Rp)</Label>
          <RupiahInput id="npoptkp" value={tax.npoptkp ?? ""} data-testid="tax-npoptkp" disabled={!mayTax}
            onChange={(e) => setT("npoptkp", e.target.value)} />{origin("npoptkp")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="njop">NJOP tanah per m² (Rp; 0 = tidak dipakai)</Label>
          <RupiahInput id="njop" value={tax.njop_per_m2 ?? ""} data-testid="tax-njop" disabled={!mayTax}
            onChange={(e) => setT("njop_per_m2", e.target.value)} />{origin("njop_per_m2")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bankfee">Biaya bank % plafon KPR (0 = tidak dipakai)</Label>
          <Input id="bankfee" type="number" value={tax.bank_fee_pct_of_plafon ?? ""} data-testid="tax-bankfee" disabled={!mayTax}
            onChange={(e) => setT("bank_fee_pct_of_plafon", e.target.value)} />{origin("bank_fee_pct_of_plafon")}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        <Input data-testid="tax-reason" className="max-w-xs" aria-label="Alasan perubahan pajak" disabled={!mayTax}
          placeholder={projectId ? "Alasan penimpaan proyek (wajib)" : "Alasan perubahan (dicatat di riwayat)"}
          value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button data-testid={FINANCE.taxSubmit} onClick={save} disabled={busy || !mayTax}>
          {busy ? "Menyimpan…" : projectId ? "Simpan Pajak Proyek" : "Simpan Pajak"}
        </Button>
      </div>
    </section>
  );
}
