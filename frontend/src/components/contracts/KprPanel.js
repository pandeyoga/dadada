import React, { useEffect, useState } from "react";
import { AlertTriangle, Banknote, CheckCircle2, Circle, XCircle } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import EvidenceUploader from "@/components/patterns/EvidenceUploader";
import ReferenceSelect from "@/components/patterns/ReferenceSelect";
import DatePickerField from "@/components/patterns/DatePickerField";
import KprTermsPicker, { monthlyInstallment } from "@/components/patterns/KprTermsPicker";
import KprDisbursementBox from "@/components/contracts/KprDisbursementBox";
import { KprAmendTermsDialog, KprAmendmentHistory, KprScheduleBox, KPR_AMEND_TESTIDS } from "@/components/contracts/KprAmendTerms";
import CashAccountSelect from "@/components/cashBank/CashAccountSelect";
import { useAuth } from "@/context/AuthContext";
import { formatDateWIB, formatIDR } from "@/utils/formatters";
import api from "@/services/apiClient";
import { P53, P75 } from "@/constants/testIds";

/**
 * KprPanel — sub-alur KPR: berkas → bank → appraisal → **SP3K** → **AKAD KREDIT** → pencairan.
 *
 * Sebelum Fase 53 tidak ada tempat menyimpan SP3K/akad/pencairan, sehingga “sudah akad atau
 * belum” hanya ada di kepala orang. Dua gerbang bukti yang dipaksakan server dan dijelaskan
 * di layar ini: **SP3K wajib berkas + plafon yang DISETUJUI bank**, dan **akad kredit wajib
 * SP3K sah serta kelebihan tanah sudah lunas** (ketentuan SPKT milik owner).
 */
const NEEDS = {
  sp3k: ["number", "plafon", "tenor_months", "rate", "valid_until", "file"],
  akad_kredit: ["date", "notary", "place", "file"],
  pencairan: ["date", "amount", "file"],
  appraisal: ["date", "amount", "note"],
  diajukan_ke_bank: ["bank", "note"],
  berkas_lengkap: ["note"],
};

/** Peringatan plafon SP3K vs porsi bank pada jadwal tagihan (pratinjau server). */
function PlafonCheckBox({ check, dueDate, onDueDate }) {
  if (!check || check.kind === "no_ar") return null;
  if (check.kind === "no_bank_items") {
    return (
      <p data-testid="kpr-plafon-check" data-kind={check.kind} className="rounded-md border bg-secondary/40 px-2.5 py-1.5 text-xs text-muted-foreground">
        Skema pembayaran kontrak ini tidak menandai porsi bank — plafon dicatat tanpa penyesuaian termin.
      </p>
    );
  }
  if (check.kind === "match") {
    return (
      <p data-testid="kpr-plafon-check" data-kind={check.kind} className="flex items-center gap-1.5 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs text-emerald-900">
        <CheckCircle2 className="h-3.5 w-3.5" /> Plafon sama dengan porsi bank {formatIDR(check.bank_portion)} pada jadwal tagihan.
      </p>
    );
  }
  if (check.kind === "shortfall") {
    return (
      <div data-testid="kpr-plafon-check" data-kind={check.kind} className="space-y-2 rounded-md border border-amber-300 bg-amber-50 px-2.5 py-2 text-xs text-amber-900">
        <p className="flex items-start gap-1.5">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Plafon <b>{formatIDR(check.plafon)}</b> lebih kecil dari porsi bank <b>{formatIDR(check.bank_portion)}</b>.
            Selisih <b data-testid="kpr-plafon-shortfall">{formatIDR(check.shortfall)}</b> menjadi <b>kewajiban pembeli</b>: termin baru
            “Selisih Plafon KPR” lahir di jadwal tagihan (piutang pembeli naik, porsi bank turun; total piutang tetap).
          </span>
        </p>
        <div className="space-y-1">
          <Label htmlFor="kpr-shortfall-due" className="text-xs">Jatuh tempo selisih plafon (wajib)</Label>
          <DatePickerField id="kpr-shortfall-due" testId="kpr-shortfall-due" value={dueDate} onChange={onDueDate} />
        </div>
      </div>
    );
  }
  return (
    <p data-testid="kpr-plafon-check" data-kind={check.kind}
      className={`flex items-start gap-1.5 rounded-md border px-2.5 py-1.5 text-xs ${check.excess_ok ? "border-sky-200 bg-sky-50 text-sky-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        Plafon <b>{formatIDR(check.plafon)}</b> lebih besar dari porsi bank <b>{formatIDR(check.bank_portion)}</b> sebesar <b>{formatIDR(check.excess)}</b>.
        {check.excess_ok
          ? " Porsi bank akan dinaikkan dan termin pembeli yang belum dibayar dikurangi sebesar itu."
          : ` Termin pembeli yang masih bisa dialihkan hanya ${formatIDR(check.buyer_reducible)} — turunkan plafon atau periksa jadwal tagihan.`}
      </span>
    </p>
  );
}

/** Ringkasan penyesuaian AR yang sudah terjadi saat SP3K dicatat. */
function PlafonReconcileNote({ rec }) {
  if (!rec || !rec.applied || rec.kind === "match") return null;
  const short = rec.kind === "shortfall";
  return (
    <div data-testid="kpr-plafon-reconcile" data-kind={rec.kind}
      className={`rounded-lg border p-3 text-sm ${short ? "border-amber-200 bg-amber-50 text-amber-900" : "border-sky-200 bg-sky-50 text-sky-900"}`}>
      <p className="font-medium">
        {short ? `Selisih plafon ${formatIDR(rec.shortfall)} ditagih ke pembeli` : `Porsi bank dinaikkan ${formatIDR(rec.excess)}`}
      </p>
      <p className="mt-0.5 text-xs">
        Plafon SP3K {formatIDR(rec.plafon)} vs porsi bank semula {formatIDR(rec.bank_portion)} → porsi bank kini {formatIDR(rec.bank_portion_after)}.
        {short ? ` Termin “Selisih Plafon KPR” jatuh tempo ${rec.due_date ? formatDateWIB(rec.due_date) : "-"} — tampil di Rencana Bayar & Piutang.` : " Termin pembeli yang belum dibayar berkurang sebesar itu."}
      </p>
    </div>
  );
}

export default function KprPanel({ contract, onChanged }) {
  const { can, user } = useAuth();
  const mayUpdate = can("financing", "update");
  const kpr = contract?.kpr || {};
  const app = kpr.application || {};
  const [stage, setStage] = useState(null);
  const [reject, setReject] = useState(false);
  const [amend, setAmend] = useState(false);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  const [plafonCheck, setPlafonCheck] = useState(null);

  useEffect(() => {
    if (stage !== "sp3k" || !contract?.id) { setPlafonCheck(null); return undefined; }
    const plafon = Number(form.plafon) || 0;
    if (plafon <= 0) { setPlafonCheck(null); return undefined; }
    const t = setTimeout(() => {
      api.get(`/contracts/${contract.id}/kpr/plafon-check`, { params: { plafon } })
        .then((r) => setPlafonCheck(r.data.data)).catch(() => setPlafonCheck(null));
    }, 350);
    return () => clearTimeout(t);
  }, [stage, form.plafon, contract?.id]);

  if (!kpr.applicable) return null;

  const openStage = (s) => { setForm({}); setStage(s); };
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const shortfallNeedsDate = plafonCheck?.kind === "shortfall" && !form.shortfall_due_date;
  const excessBlocked = plafonCheck?.kind === "excess" && !plafonCheck.excess_ok;

  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/contracts/${contract.id}/kpr/stage/${stage}`, {
        number: form.number || undefined,
        date: form.date || undefined,
        plafon: form.plafon ? Number(form.plafon) : undefined,
        shortfall_due_date: form.shortfall_due_date || undefined,
        tenor_months: form.tenor_months ? Number(form.tenor_months) : undefined,
        rate: form.rate ? Number(form.rate) : undefined,
        kpr_product_id: form.product_id || undefined,
        kpr_product_name: form.product_name || undefined,
        valid_until: form.valid_until || undefined,
        bank: form.bank || undefined,
        amount: form.amount ? Number(form.amount) : undefined,
        cash_account_id: form.cash_account_id || undefined,
        notary: form.notary || undefined,
        place: form.place || undefined,
        file_id: form.file_id || undefined,
        note: form.note || undefined,
        tranche_code: form.tranche_code || undefined,
      });
      toast.success("Tahap KPR diperbarui.");
      setStage(null);
      onChanged && onChanged();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal memajukan tahap KPR.");
    } finally { setBusy(false); }
  };

  const doReject = async () => {
    setBusy(true);
    try {
      const res = await api.post(`/contracts/${contract.id}/kpr/reject`, {
        reason: form.reason || "", file_id: form.file_id || undefined,
      });
      const r = res.data.data?.rejection || {};
      toast.success(`Penolakan bank dicatat. Usul refund booking fee ${r.refund_pct}% `
        + `(${formatIDR(r.refund_amount)}).`);
      setReject(false);
      onChanged && onChanged();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal mencatat penolakan bank.");
    } finally { setBusy(false); }
  };

  const fields = NEEDS[stage] || ["note"];

  return (
    <section data-testid={P53.kprPanel} className="space-y-3 rounded-lg border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 font-heading text-base font-semibold">
            <Banknote className="h-4 w-4" /> Pengajuan KPR
          </h3>
          <p className="text-xs text-muted-foreground">
            Bank {app.bank_name || "belum diisi"}
            {app.approved_plafon ? ` · plafon disetujui ${formatIDR(app.approved_plafon)}` : ""}
            {app.tenor_months ? ` · tenor ${app.tenor_months} bulan` : ""}
          </p>
          {app.kpr_product_name || app.interest_rate_pct ? (
            <p data-testid="kpr-header-terms" className="text-xs text-muted-foreground">
              Produk {app.kpr_product_name || "—"}
              {app.interest_rate_pct ? ` · bunga ${app.interest_rate_pct}%/th` : ""}
              {app.approved_plafon && app.tenor_months && app.interest_rate_pct
                ? ` · est. angsuran ${formatIDR(monthlyInstallment(app.approved_plafon, app.interest_rate_pct, app.tenor_months))}/bln` : ""}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {mayUpdate && app.sp3k?.file_id && app.kpr_stage !== "ditolak" ? (
            <Button data-testid={KPR_AMEND_TESTIDS.amendBtn} size="sm" variant="outline" onClick={() => setAmend(true)}>
              Ubah tenor/bunga
            </Button>
          ) : null}
          {mayUpdate && app.kpr_stage !== "ditolak" ? (
            <Button data-testid={P53.kprRejectBtn} size="sm" variant="outline"
              onClick={() => { setForm({}); setReject(true); }}>
              <XCircle className="mr-1.5 h-3.5 w-3.5" /> Bank menolak
            </Button>
          ) : null}
        </div>
      </div>

      {app.kpr_stage === "ditolak" ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">
          <p className="font-medium">KPR ditolak bank</p>
          <p className="mt-0.5 text-xs">{app.rejection?.note}</p>
          <p className="mt-1 text-xs">
            Usulan refund booking fee {app.rejection?.refund_pct}% ={" "}
            {formatIDR(app.rejection?.refund_amount)} — sesuai ketentuan SPR.
          </p>
        </div>
      ) : null}

      {app.disbursement?.amount ? (
        <div data-testid="kpr-disbursement-accounting" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <p className="font-medium">Pencairan bank {formatIDR(app.disbursed_total || app.disbursement.amount)} · terakhir {app.disbursement.date}</p>
          <p className="mt-0.5 text-xs">
            {app.disbursement.receipt_no
              ? <>Dibukukan sebagai kuitansi <strong>{app.disbursement.receipt_no}</strong> (metode KPR) → melunasi termin piutang pembeli & tercatat di buku besar (kas masuk, piutang berkurang).{app.disbursement.deposit_excess ? ` Kelebihan ${formatIDR(app.disbursement.deposit_excess)} jadi titipan.` : ""}</>
              : <span className="text-amber-800">Pencairan lama tanpa kuitansi — belum mengurangi piutang. Catat ulang lewat Pembiayaan › Pencairan bila perlu.</span>}
          </p>
        </div>
      ) : null}

      <PlafonReconcileNote rec={app.plafon_reconcile} />

      <KprDisbursementBox contract={contract} app={app} mayUpdate={mayUpdate}
        onChanged={onChanged} onRecord={() => openStage("pencairan")} />
      <KprAmendmentHistory items={app.terms_amendments} />
      <KprScheduleBox contract={contract} nonce={`${app.tenor_months}-${app.interest_rate_pct}-${app.approved_plafon}-${(app.terms_amendments || []).length}`} />

      <ol className="space-y-2">
        {(kpr.stages || []).map((s) => (
          <li key={s.stage} data-testid={P53.kprStage} data-stage={s.stage}
            data-done={s.done}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-background p-3">
            <p className="flex items-center gap-2 text-sm">
              {s.done ? <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                : <Circle className="h-4 w-4 text-muted-foreground" />}
              <span className={s.current ? "font-medium" : ""}>{s.label}</span>
              {s.current ? (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  tahap sekarang
                </span>
              ) : null}
            </p>
            {mayUpdate && !s.done && kpr.next_stage === s.stage ? (
              <Button data-testid={`${P53.kprBtn}-${s.stage}`} size="sm" variant="outline"
                onClick={() => openStage(s.stage)}>Catat {s.label}</Button>
            ) : null}
          </li>
        ))}
      </ol>
      {app.sp3k?.file_id ? (
        <p className="text-xs text-muted-foreground">
          SP3K {app.sp3k.number || ""} · {app.sp3k.date ? formatDateWIB(app.sp3k.date) : ""}
          {" "}· berkas bukti tersimpan.
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          Akad kredit membutuhkan SP3K bank beserta BERKASnya — tanpa itu tahap akad tidak
          bisa dimajukan (dan itu memang aturannya, bukan tombol yang rusak).
        </p>
      )}

      {/* dialog tahap */}
      <Dialog open={!!stage} onOpenChange={(v) => !v && setStage(null)}>
        <DialogContent data-testid={P53.kprDialog}
          className="max-h-[85vh] max-w-md overflow-y-auto bg-background">
          <DialogHeader>
            <DialogTitle>Catat tahap KPR</DialogTitle>
            <DialogDescription>
              Isi bukti yang diminta tahap ini. Server menolak tahap tanpa bukti — supaya
              “sudah SP3K” dan “sudah akad” tidak pernah hanya klaim.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {fields.includes("bank") ? (
              <div className="space-y-1.5">
                {/* Bank dipilih dari Kamus Data (`financing_bank`), BUKAN diketik bebas.
                    Temuan gate `audit_forms_deep`: satu-satunya field relasi di Fase 53
                    yang masih input bebas. Akibat nyata bila dibiarkan — "BTN", "btn",
                    "Bank BTN", "BTN " menjadi empat bank berbeda, sehingga rekap KPR per
                    bank (dan pencocokan SP3K) memecah satu bank menjadi banyak baris.
                    Grup ini `dynamic`, jadi bank yang belum terdaftar tetap bisa
                    ditambahkan lewat "Nilai baru…" — tanpa membuka pintu salah ketik massal. */}
                <Label htmlFor="kpr-bank">Bank</Label>
                <ReferenceSelect group="financing_bank" testId="kpr-bank"
                  value={form.bank || ""} onChange={(v) => set("bank", v)}
                  placeholder="Pilih bank penyalur KPR…" />
              </div>
            ) : null}
            {fields.includes("number") ? (
              <div className="space-y-1.5">
                <Label htmlFor="kpr-num">Nomor SP3K</Label>
                <Input id="kpr-num" className="bg-background" value={form.number || ""}
                  onChange={(e) => set("number", e.target.value)} />
              </div>
            ) : null}
            {fields.includes("plafon") ? (
              <div className="space-y-1.5">
                <Label htmlFor="kpr-plafon">Plafon DISETUJUI bank (wajib)</Label>
                <RupiahInput id="kpr-plafon" data-testid="kpr-sp3k-plafon" className="bg-background"
                  value={form.plafon || ""} onChange={(e) => set("plafon", e.target.value)} />
                <PlafonCheckBox check={plafonCheck} dueDate={form.shortfall_due_date || ""}
                  onDueDate={(v) => set("shortfall_due_date", v)} />
              </div>
            ) : null}
            {fields.includes("tenor_months") ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <KprTermsPicker bankName={form.bank || app.bank || app.bank_name || ""} testIdPrefix="kpr-sp3k-terms" plafon={form.plafon}
                  value={{ product_id: form.product_id || "", product_name: form.product_name || "", tenor_months: form.tenor_months || "", interest_rate_pct: form.rate || "" }}
                  onChange={(v) => setForm((f) => ({ ...f, product_id: v.product_id, product_name: v.product_name, tenor_months: v.tenor_months, rate: v.interest_rate_pct }))} />
              </div>
            ) : null}
            {fields.includes("amount") ? (
              <div className="space-y-1.5">
                {stage === "pencairan" && (app.tranches || []).length ? (
                  <>
                    <Label>Tahap pencairan (dari skema {app.disbursement_scheme_name})</Label>
                    <Select value={form.tranche_code || ""} onValueChange={(code) => {
                      const t = (app.tranches || []).find((x) => x.code === code);
                      setForm((f) => ({ ...f, tranche_code: code, amount: t ? String(t.amount) : f.amount }));
                    }}>
                      <SelectTrigger data-testid={P75.kprTrancheSelect} className="bg-background"><SelectValue placeholder="Pilih tahap" /></SelectTrigger>
                      <SelectContent>
                        {(app.tranches || []).filter((t) => t.status !== "dicairkan").map((t) => (
                          <SelectItem key={t.code} value={t.code}>{t.name} · {formatIDR(t.amount)} · syarat {t.condition}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </>
                ) : null}
                <Label htmlFor="kpr-amt">{stage === "pencairan" ? "Nominal dicairkan bank (Rp)" : "Nilai (Rp)"}</Label>
                <Input id="kpr-amt" inputMode="numeric" className="bg-background" data-testid="kpr-stage-amount"
                  value={form.amount || ""} onChange={(e) => set("amount", e.target.value)}
                  disabled={stage === "pencairan" && (app.tranches || []).length > 0 && !can("finance", "manage")} />
                {stage === "pencairan" ? (
                  <p className="text-xs text-muted-foreground">
                    {(app.tranches || []).length
                      ? `Nominal terisi dari tahapan; koreksi hanya finance manager dalam toleransi ±${app.disbursement_tolerance_pct ?? 1}%.`
                      : "Belum ada skema pencairan — pilih skema di kotak Pencairan bertahap agar nominal tidak diketik bebas."}
                    {" "}Dibukukan sebagai kuitansi (metode KPR) → piutang berkurang. Pencairan yang melebihi sisa piutang DITOLAK.
                  </p>
                ) : null}
              </div>
            ) : null}
            {stage === "pencairan" ? (
              <CashAccountSelect value={form.cash_account_id || ""} onChange={(v) => set("cash_account_id", v)}
                kind="bank" label="Dana KPR masuk ke rekening" testId="kpr-disburse-cash-account"
                hint="Rekening penerima pencairan dari bank KPR — biasanya rekening escrow/operasional pengembang." />
            ) : null}
            {fields.includes("date") || fields.includes("valid_until") ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="kpr-date">Tanggal</Label>
                  <DatePickerField id="kpr-date" testId={P75.kprDate} value={form.date || ""}
                    onChange={(v) => set("date", v)} />
                </div>
                {fields.includes("valid_until") ? (
                  <div className="space-y-1.5">
                    <Label htmlFor="kpr-valid">Berlaku sampai</Label>
                    <DatePickerField id="kpr-valid" testId={`${P75.kprDate}-valid`} value={form.valid_until || ""}
                      onChange={(v) => set("valid_until", v)} />
                  </div>
                ) : null}
              </div>
            ) : null}
            {fields.includes("notary") ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="kpr-notary">Notaris</Label>
                  <Input id="kpr-notary" className="bg-background" value={form.notary || ""}
                    onChange={(e) => set("notary", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="kpr-place">Tempat akad</Label>
                  <Input id="kpr-place" className="bg-background" value={form.place || ""}
                    onChange={(e) => set("place", e.target.value)} />
                </div>
              </div>
            ) : null}
            {fields.includes("file") ? (
              <div className="space-y-1.5">
                <Label>Berkas bukti {stage === "sp3k" || stage === "disburse" ? "(WAJIB)" : ""}</Label>
                <EvidenceUploader ownerType="contract" ownerId={contract.id} max={1}
                  required={stage === "sp3k" || stage === "disburse"}
                  value={form.files || []}
                  onChange={(ids) => setForm((f) => ({ ...f, files: ids,
                    file_id: ids[0] || undefined }))} />
                {form.file_id ? (
                  <p className="text-xs text-emerald-700">Berkas terunggah.</p>
                ) : null}
              </div>
            ) : null}
            <div className="space-y-1.5">
              <Label htmlFor="kpr-note">Catatan</Label>
              <Textarea id="kpr-note" rows={2} className="bg-background" value={form.note || ""}
                onChange={(e) => set("note", e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStage(null)}>Batal</Button>
            <Button data-testid={P53.kprSubmit} onClick={submit} disabled={busy || shortfallNeedsDate || excessBlocked}>
              {busy ? "Menyimpan…" : "Simpan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* dialog amandemen tenor/bunga sesudah SP3K */}
      <KprAmendTermsDialog contract={contract} app={app} open={amend} onOpenChange={setAmend} onChanged={onChanged} />

      {/* dialog penolakan bank */}
      <Dialog open={reject} onOpenChange={setReject}>
        <DialogContent className="max-w-md bg-background">
          <DialogHeader>
            <DialogTitle>Bank menolak pengajuan KPR</DialogTitle>
            <DialogDescription>
              Alasan minimal 10 huruf — dibaca pembeli & tim saat memutuskan langkah berikut
              (ganti bank, ganti skema, atau lepas unit).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Textarea rows={3} className="bg-background" value={form.reason || ""}
              placeholder="mis. penghasilan tidak memenuhi rasio angsuran menurut bank"
              onChange={(e) => set("reason", e.target.value)} />
            <EvidenceUploader ownerType="contract" ownerId={contract.id} max={1}
              label="Lampirkan surat penolakan (opsional)" value={form.files || []}
              onChange={(ids) => setForm((f) => ({ ...f, files: ids,
                file_id: ids[0] || undefined }))} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReject(false)}>Batal</Button>
            <Button onClick={doReject} disabled={busy || (form.reason || "").trim().length < 10}>
              {busy ? "Menyimpan…" : "Catat penolakan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
