import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";
import { CUSTOMERS } from "@/constants/testIds";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import ReferenceItems from "@/components/patterns/ReferenceItems";
import KprTermsPicker from "@/components/patterns/KprTermsPicker";
import CashAccountSelect from "@/components/cashBank/CashAccountSelect";
import { useAuth } from "@/context/AuthContext";

/** Info skema pencairan (Pusat Konfigurasi › Pencairan KPR) untuk bank yang dipilih. */
function DisbursementSchemeHint({ bank }) {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    if (!bank) { setInfo(null); return; }
    api.get("/kpr-disbursement-schemes", { params: { bank } })
      .then((r) => setInfo(r.data)).catch(() => setInfo(null));
  }, [bank]);
  if (!bank || !info) return null;
  const rows = info.data || [];
  const dflt = rows.find((s) => s.id === info.default_id);
  return (
    <div data-testid="financing-disb-scheme-hint" className="rounded-lg border bg-secondary/60 p-2.5 text-[12px] sm:col-span-2">
      <p className="font-medium">Skema pencairan bank {bank}</p>
      {dflt ? (
        <p>Otomatis dipasang saat SP3K: <b>{dflt.name}</b> · {(dflt.tranches || []).length} tahap
          {" "}({(dflt.tranches || []).map((t) => `${t.code} ${t.amount ? formatIDR(t.amount) : `${t.pct}%`}`).join(", ")}) · toleransi ±{dflt.tolerance_pct}%.</p>
      ) : rows.length ? (
        <p>{rows.length} skema cocok ({rows.map((s) => s.name).join(", ")}) — dipilih manual di kontrak saat SP3K/pencairan.</p>
      ) : (
        <p className="text-rose-700">Belum ada skema pencairan aktif untuk bank ini — tambahkan di Pusat Konfigurasi › Pencairan KPR.</p>
      )}
    </div>
  );
}

// --- Add KPR / Financing application ---
export function AddFinancingDialog({ open, onOpenChange, customer, onDone }) {
  const [deals, setDeals] = useState([]);
  const [form, setForm] = useState({ deal_id: "", bank_name: "", plafon: "", dp_amount: "", tenor_months: "", interest_rate_pct: "", product_id: "", product_name: "" });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!open) return;
    setForm({ deal_id: "", bank_name: "", plafon: "", dp_amount: "", tenor_months: "", interest_rate_pct: "", product_id: "", product_name: "" });
    (async () => {
      try {
        const res = await api.get("/deals");
        const all = res.data?.data || [];
        const mine = customer?.lead_id ? all.filter((d) => d.lead_id === customer.lead_id) : [];
        setDeals(mine.length ? mine : all);
      } catch { setDeals([]); }
    })();
  }, [open, customer]);

  const submit = async () => {
    if (!form.deal_id) { toast.error("Pilih deal/unit terlebih dahulu."); return; }
    if (!form.bank_name || !form.plafon) { toast.error("Bank & plafon wajib diisi."); return; }
    if (!form.tenor_months || !form.interest_rate_pct) { toast.error("Tenor & bunga wajib dipilih (dari Produk KPR bank)."); return; }
    setBusy(true);
    try {
      const res = await api.post("/financing", {
        deal_id: form.deal_id, customer_id: customer?.id,
        bank_name: form.bank_name, plafon: Number(form.plafon),
        dp_amount: Number(form.dp_amount || 0), tenor_months: Number(form.tenor_months || 0),
        interest_rate_pct: Number(form.interest_rate_pct || 0),
        kpr_product_id: form.product_id || null, kpr_product_name: form.product_name || null,
      });
      // Fase 30a: hasil pra-skrining SLIK lead ikut menempel; bila tidak lolos, petugas
      // langsung diberi tahu (bukan menemukannya nanti saat bank menolak).
      const warn = res.data?.prescreen_warning;
      const pre = res.data?.prescreen;
      if (warn) toast.warning(warn);
      else if (pre) toast.success(`Pengajuan KPR dibuat · pra-skrining lead: ${pre.label}.`);
      else toast.success("Pengajuan KPR dibuat.");
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal membuat pengajuan KPR.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ajukan KPR</DialogTitle>
          <DialogDescription>Pengajuan pembiayaan terkait deal/unit pembeli.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Deal / Unit</Label>
            <Select value={form.deal_id} onValueChange={(v) => set("deal_id", v)}>
              <SelectTrigger data-testid="financing-deal-select"><SelectValue placeholder="Pilih deal" /></SelectTrigger>
              <SelectContent>
                {deals.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {(d.lead_name || "Deal")} · {formatIDR(d.price)} · {String(d.id).slice(0, 6)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label htmlFor="bk">Bank</Label>
            <ReferenceSelect group="financing_bank" value={form.bank_name}
              onChange={(v) => setForm((f) => ({ ...f, bank_name: v, product_id: "", product_name: "", tenor_months: "", interest_rate_pct: "" }))} testId="financing-bank-select"
              placeholder="Pilih bank…" /></div>
          <div className="space-y-1.5"><Label htmlFor="pl">Plafon (Rp)</Label>
            <RupiahInput id="pl" value={form.plafon} onChange={(e) => set("plafon", e.target.value)} /></div>
          <div className="space-y-1.5"><Label htmlFor="dp">DP (Rp)</Label>
            <RupiahInput id="dp" value={form.dp_amount} onChange={(e) => set("dp_amount", e.target.value)} /></div>
          <KprTermsPicker bankName={form.bank_name} testIdPrefix="financing-terms" plafon={form.plafon}
            value={{ product_id: form.product_id, product_name: form.product_name, tenor_months: form.tenor_months, interest_rate_pct: form.interest_rate_pct }}
            onChange={(v) => setForm((f) => ({ ...f, ...v }))} />
          <DisbursementSchemeHint bank={form.bank_name} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={CUSTOMERS.financingAddSubmit} onClick={submit} disabled={busy}>
            {busy ? "Menyimpan…" : "Ajukan KPR"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- SLIK / BI check result ---
export function SlikDialog({ open, onOpenChange, financing, onDone }) {
  const [status, setStatus] = useState("clear");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  // Fase 30a: hasil PRA-SKRINING lead ikut menempel pada pengajuan. Dipakai sebagai
  // nilai awal form supaya petugas tidak mengetik ulang — tetapi hasil RESMI bank tetap
  // harus dikonfirmasi manusia (pra-skrining tidak pernah otomatis jadi hasil resmi).
  const pre = financing?.slik_prescreen || null;
  useEffect(() => {
    if (!open) return;
    setStatus(pre?.status && pre.status !== "pending" ? pre.status : "clear");
    setNote(pre ? `Mengacu pra-skrining lead (${pre.label || pre.status})${pre.note ? `: ${pre.note}` : ""}` : "");
  }, [open, financing]);   // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!financing?.id) return;
    setBusy(true);
    try {
      await api.post(`/financing/${financing.id}/slik`, { slik_status: status, note: note || null });
      toast.success(`Hasil SLIK: ${status}.`);
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal memperbarui SLIK.");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Hasil BI / SLIK Check</DialogTitle>
          <DialogDescription>{financing ? `${financing.bank_name} · ${formatIDR(financing.plafon)}` : ""}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {pre ? (
            <div data-testid="financing-slik-prescreen"
              className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900">
              <p className="font-semibold">
                Pra-skrining lead: {pre.label || pre.status} (SIMULASI)
              </p>
              <p>
                {(pre.evidence || []).length
                  ? `${pre.evidence.length} bukti iDeb dilampirkan`
                  : "tanpa lampiran"} · diperiksa {pre.checked_by || "-"}
                {pre.checked_at ? ` · ${String(pre.checked_at).slice(0, 10)}` : ""}
              </p>
              <p className="mt-1">
                Ini BUKAN hasil resmi bank — konfirmasi hasil resmi di bawah agar status KPR
                berubah.
              </p>
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger data-testid="financing-slik-status"><SelectValue /></SelectTrigger>
              <SelectContent>
                <ReferenceItems group="slik_status" />
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label htmlFor="sn">Catatan</Label>
            <Textarea id="sn" rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={CUSTOMERS.slikSubmit} onClick={submit} disabled={busy}>
            {busy ? "Menyimpan…" : "Simpan Hasil SLIK"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Staged disbursement: tahap dari SKEMA PENCAIRAN bank (Pusat Konfigurasi › Pencairan KPR) ---
const condMet = (contract, app, c) => {
  const legal = contract?.legal || {};
  if (c === "akad") return !!(app?.akad?.date || legal.akad_kredit);
  if (c === "serah_terima") return !!legal.bast;
  return !!legal.sertifikat;
};

export function DisburseDialog({ open, onOpenChange, financing, onDone }) {
  const { can } = useAuth();
  const [form, setForm] = useState({ tranche_code: "", amount: "", date: "", note: "", cash_account_id: "" });
  const [ctx, setCtx] = useState({ loading: true, contract: null, app: null, schemes: [], defaultId: null });
  const [pick, setPick] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const mayCorrect = can("finance", "manage");

  const load = async () => {
    if (!financing?.deal_id) { setCtx({ loading: false, contract: null, app: null, schemes: [], defaultId: null }); return; }
    setCtx((c) => ({ ...c, loading: true }));
    try {
      const cr = await api.get("/contracts", { params: { deal_id: financing.deal_id, limit: 5 } });
      const contract = (cr.data?.data || []).find((c) => c.deal_id === financing.deal_id) || null;
      let app = null;
      if (contract) {
        const kv = await api.get(`/contracts/${contract.id}/kpr`).then((r) => r.data?.data).catch(() => null);
        app = kv?.application || null;
      }
      const sr = await api.get("/kpr-disbursement-schemes", { params: { bank: app?.bank_name || financing.bank_name || "" } })
        .then((r) => r.data).catch(() => ({ data: [] }));
      setCtx({ loading: false, contract, app, schemes: sr.data || [], defaultId: sr.default_id || null });
      setPick(sr.default_id || "");
    } catch { setCtx({ loading: false, contract: null, app: null, schemes: [], defaultId: null }); }
  };

  useEffect(() => {
    if (!open) return;
    setForm({ tranche_code: "", amount: "", date: "", note: "", cash_account_id: "" });
    load();
  }, [open, financing]);   // eslint-disable-line react-hooks/exhaustive-deps

  const { contract, app } = ctx;
  const tranches = app?.tranches || [];
  const openTranches = tranches.filter((t) => t.status !== "dicairkan");
  const hasAkad = !!(app?.akad?.date);
  const plafon = Number(app?.approved_plafon || app?.plafon || financing?.plafon || 0);
  const remaining = plafon - Number(app?.disbursed_total || financing?.disbursed_total || 0);
  const chosen = tranches.find((t) => t.code === form.tranche_code);
  const tol = Number(app?.disbursement_tolerance_pct ?? 0);

  const assignScheme = async () => {
    if (!contract || !pick) return;
    setBusy(true);
    try {
      await api.post(`/contracts/${contract.id}/kpr/disbursement-scheme`, { scheme_id: pick });
      toast.success("Skema pencairan dipasang — tahapan tergenerasi dari plafon.");
      await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal memasang skema pencairan."); } finally { setBusy(false); }
  };

  const submit = async () => {
    if (!financing?.id) return;
    if (!form.tranche_code) { toast.error("Pilih tahap pencairan dari skema."); return; }
    setBusy(true);
    try {
      const res = await api.post(`/financing/${financing.id}/disburse`, {
        tranche_code: form.tranche_code,
        amount: form.amount ? Number(form.amount) : undefined,
        date: form.date || undefined, note: form.note || undefined,
        cash_account_id: form.cash_account_id || undefined,
      });
      const bk = res.data?.ar_booking || {};
      toast.success(`Pencairan ${bk.tranche || "tahap"} tercatat → kuitansi ${bk.receipt_no || "-"}: piutang berkurang ${formatIDR(bk.applied || 0)}`
        + (bk.deposit_amount ? `, ${formatIDR(bk.deposit_amount)} jadi titipan.` : "."));
      onOpenChange(false);
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal mencatat pencairan.");
    } finally { setBusy(false); }
  };

  const blocker = ctx.loading ? null
    : !contract ? "Kontrak unit ini belum terbentuk — aktifkan kontrak / konfirmasi booking dulu."
      : !app ? "Pengajuan KPR belum tertaut ke kontrak."
        : !hasAkad ? "Akad kredit belum tercatat — catat tahap AKAD KREDIT di tab Kontrak & Legal › KPR sebelum bank mencairkan."
          : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Pencairan KPR (Bertahap)</DialogTitle>
          <DialogDescription>
            {financing ? `${financing.bank_name || ""} · plafon ${formatIDR(plafon)} · sisa ${formatIDR(remaining)}` : ""}
            {app?.disbursement_scheme_name ? ` · skema ${app.disbursement_scheme_name}` : ""}
          </DialogDescription>
        </DialogHeader>
        {ctx.loading ? <p className="text-sm text-muted-foreground">Memuat skema pencairan…</p> : null}
        {blocker ? (
          <p data-testid="financing-disburse-blocker" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[12px] text-amber-900">{blocker}</p>
        ) : null}

        {!ctx.loading && contract && app && !tranches.length ? (
          <div data-testid="financing-disburse-scheme-pick" className="space-y-2 rounded-lg border p-3">
            <p className="text-sm font-medium">Skema pencairan belum dipasang</p>
            <p className="text-[12px] text-muted-foreground">
              Pilih skema dari Pusat Konfigurasi › Pencairan KPR yang cocok untuk bank {app.bank_name || financing?.bank_name || "-"}.
              Tahapan dibuat dari plafon {formatIDR(plafon)}.
            </p>
            {!ctx.schemes.length ? (
              <p className="text-[12px] text-rose-700">Belum ada skema aktif untuk bank ini — tambahkan di Pusat Konfigurasi › Pencairan KPR.</p>
            ) : (
              <div className="flex gap-2">
                <Select value={pick} onValueChange={setPick}>
                  <SelectTrigger data-testid="financing-disburse-scheme-select"><SelectValue placeholder="Pilih skema pencairan" /></SelectTrigger>
                  <SelectContent>
                    {ctx.schemes.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}{s.bank ? ` · ${s.bank}` : " · semua bank"} ({(s.tranches || []).length} tahap)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button data-testid="financing-disburse-scheme-assign" size="sm" disabled={!pick || busy || plafon <= 0} onClick={assignScheme}>Pakai</Button>
              </div>
            )}
            {plafon <= 0 ? <p className="text-[12px] text-rose-700">Plafon SP3K belum tercatat — skema butuh plafon sebagai dasar tahapan.</p> : null}
          </div>
        ) : null}

        {tranches.length ? (
          <ul data-testid="financing-disburse-tranches" className="divide-y rounded-lg border text-[12px]">
            {tranches.map((t) => {
              const met = condMet(contract, app, t.condition);
              return (
                <li key={t.code} data-tranche={t.code} data-status={t.status} className="flex items-center justify-between px-2.5 py-1.5">
                  <span>{t.code} · {t.name} <span className="text-muted-foreground">· syarat {t.condition}{t.status !== "dicairkan" ? (met ? " ✓" : " (belum)") : ""}</span></span>
                  <span className="flex items-center gap-2 tabular-nums">{formatIDR(t.amount)}
                    <span className={`rounded-full px-2 py-0.5 text-[10px] ${t.status === "dicairkan" ? "bg-emerald-100 text-emerald-800" : "bg-secondary"}`}>{t.status}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        ) : null}

        {!blocker && tranches.length ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Tahap pencairan</Label>
              <Select value={form.tranche_code} onValueChange={(code) => {
                const t = tranches.find((x) => x.code === code);
                setForm((f) => ({ ...f, tranche_code: code, amount: t ? String(t.amount) : "" }));
              }}>
                <SelectTrigger data-testid="financing-disburse-tranche-select"><SelectValue placeholder={openTranches.length ? "Pilih tahap" : "Semua tahap sudah dicairkan"} /></SelectTrigger>
                <SelectContent>
                  {openTranches.map((t) => (
                    <SelectItem key={t.code} value={t.code} disabled={!condMet(contract, app, t.condition)}>
                      {t.code} · {t.name} · {formatIDR(t.amount)} · syarat {t.condition}{condMet(contract, app, t.condition) ? "" : " (belum terpenuhi)"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label htmlFor="am">Nominal (Rp)</Label>
              <RupiahInput id="am" data-testid="financing-disburse-amount" value={form.amount}
                onChange={(e) => set("amount", e.target.value)} disabled={!mayCorrect || !chosen} />
              <p className="text-[11px] text-muted-foreground">
                {chosen ? `Nominal tahap ${formatIDR(chosen.amount)}; koreksi hanya finance manager dalam toleransi ±${tol}%.` : "Terisi dari tahap yang dipilih."}
              </p>
            </div>
            <div className="space-y-1.5"><Label htmlFor="dd">Tanggal cair</Label>
              <Input id="dd" type="date" data-testid="financing-disburse-date" value={form.date} onChange={(e) => set("date", e.target.value)} /></div>
            <div className="sm:col-span-2">
              <CashAccountSelect value={form.cash_account_id} onChange={(v) => set("cash_account_id", v)}
                kind="bank" label="Dana KPR masuk ke rekening" testId="financing-disburse-cash-account"
                hint="Rekening penerima pencairan dari bank KPR." />
            </div>
            <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="dn">Catatan</Label>
              <Textarea id="dn" rows={2} value={form.note} onChange={(e) => set("note", e.target.value)} /></div>
          </div>
        ) : null}
        <div data-testid="financing-book-to-ar-note" className="rounded-lg border bg-secondary p-3 text-[12px]">
          <span className="font-medium">Nominal mengikuti tahapan skema pencairan bank</span> — bukan angka bebas. Dana yang
          cair dibukukan sebagai kuitansi (metode KPR): piutang unit berkurang dan jurnal kas terbentuk. Pencairan
          yang melebihi sisa piutang DITOLAK; setiap tahap hanya bisa dicatat sekali.
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Batal</Button>
          <Button data-testid={CUSTOMERS.disburseSubmit} onClick={submit} disabled={busy || !!blocker || !form.tranche_code}>
            {busy ? "Memproses…" : "Catat Pencairan"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
