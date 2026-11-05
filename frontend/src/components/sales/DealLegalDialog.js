import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ScrollText, CheckCircle2, Landmark, Circle, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import StatusPill from "@/components/patterns/StatusPill";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { formatIDR, formatDateWIB } from "@/utils/formatters";
import api from "@/services/apiClient";
import { DEALS as T } from "@/constants/testIds";

const STEPS = [
  { key: "reserved", label: "Reservasi" },
  { key: "booked", label: "Booking" },
  { key: "ppjb", label: "PPJB" },
  { key: "ajb", label: "AJB / Lunas" },
];

function stepIndex(legal) {
  const { status, legal_stage } = legal || {};
  if (legal_stage === "ajb" || status === "completed") return 3;
  if (legal_stage === "ppjb") return 2;
  if (status === "booked") return 1;
  return 0;
}

/**
 * DealLegalDialog — status legal sebuah deal (HANYA BACA).
 *
 * Audit KT-01: dulu dialog ini punya tombol "Tandatangani PPJB/AJB" yang memanggil jalur
 * legal lama dan bisa menjadikan unit SOLD tanpa DP/pelunasan/BAST. Tahap legal sekarang
 * hanya dicatat di Kontrak & Legal pembeli (gerbang bukti + wewenang manajer berlaku di
 * sana), jadi dialog ini menampilkan status dan mengarahkan ke kontrak.
 */
export default function DealLegalDialog({ deal, open, onOpenChange }) {
  const navigate = useNavigate();
  const [legal, setLegal] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!deal?.id || !open) return;
    setLoading(true);
    try {
      const res = await api.get(`/deals/${deal.id}/legal`);
      setLegal(res.data.data);
    } catch (e) { toast.error("Gagal memuat status legal."); }
    finally { setLoading(false); }
  }, [deal, open]);

  useEffect(() => { load(); }, [load]);

  const idx = stepIndex(legal);
  const pay = legal?.payment || {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={T.legalDialog} className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-primary" /> Legal & Serah Terima
          </DialogTitle>
          <DialogDescription>
            {legal?.unit_code} · {legal?.lead_name}
          </DialogDescription>
        </DialogHeader>

        {loading ? <p className="text-sm text-muted-foreground">Memuat...</p> : (
          <div className="space-y-4">
            {/* Stepper */}
            <div className="flex items-center justify-between">
              {STEPS.map((s, i) => (
                <React.Fragment key={s.key}>
                  <div className="flex flex-col items-center gap-1">
                    {i <= idx ? (
                      <CheckCircle2 className={`h-6 w-6 ${i === idx ? "text-primary" : "text-emerald-500"}`} />
                    ) : <Circle className="h-6 w-6 text-muted-foreground/40" />}
                    <span className={`text-[11px] ${i <= idx ? "font-medium" : "text-muted-foreground"}`}>{s.label}</span>
                  </div>
                  {i < STEPS.length - 1 ? (
                    <div className={`mx-1 h-0.5 flex-1 ${i < idx ? "bg-emerald-400" : "bg-muted"}`} />
                  ) : null}
                </React.Fragment>
              ))}
            </div>

            {/* Payment */}
            <div className="rounded-xl border bg-card p-3 shadow-[var(--shadow-card)]">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Pembayaran</span>
                <span className="tabular-nums font-medium">{formatIDR(pay.paid)} / {formatIDR(pay.total)}</span>
              </div>
              <Progress value={pay.paid_pct || 0} className="h-2" />
              <p className="mt-1 text-[11px] text-muted-foreground">
                Terbayar {pay.paid_pct || 0}% · Sisa {formatIDR(pay.outstanding)}
              </p>
            </div>

            {/* Financing */}
            {legal?.financing ? (
              <div className="flex items-center gap-2 rounded-xl border bg-card p-3 text-sm shadow-[var(--shadow-card)]">
                <Landmark className="h-4 w-4 text-primary" />
                <span>KPR {legal.financing.bank} · plafon {formatIDR(legal.financing.plafon)}</span>
                <span className="ml-auto"><StatusPill status={legal.financing.status} group="financing_status" /></span>
              </div>
            ) : null}

            {/* PPJB / AJB records */}
            {legal?.ppjb ? (
              <div className="rounded-lg border bg-card p-2.5 text-sm shadow-[var(--shadow-card)]">
                <div className="flex items-center justify-between">
                  <span className="font-medium">PPJB {legal.ppjb.number}</span>
                  <span className="text-xs text-muted-foreground">{formatDateWIB(legal.ppjb.signed_date)}</span>
                </div>
                {legal.ppjb.dp_pct != null ? (
                  <p className="text-[11px] text-muted-foreground">DP saat PPJB: {legal.ppjb.dp_pct}%</p>
                ) : null}
              </div>
            ) : null}
            {legal?.ajb ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-emerald-800">AJB {legal.ajb.number}</span>
                  <span className="text-xs text-emerald-700">{formatDateWIB(legal.ajb.signed_date)}</span>
                </div>
                {legal.ajb.notary ? <p className="text-[11px] text-emerald-700">Notaris: {legal.ajb.notary}</p> : null}
              </div>
            ) : null}

            {/* Tahap legal dicatat di kontrak pembeli, bukan di sini */}
            {legal?.legal_stage === "ajb" ? (
              <span className="flex w-fit items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> Unit terjual (SOLD)
              </span>
            ) : null}
            <div data-testid={T.legalContractNote}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              PPJB, akad kredit, pelunasan, BAST, dan AJB dicatat di <b>Kontrak &amp; Legal</b> pembeli,
              oleh manajer, setelah syaratnya terpenuhi (DP terbayar, pelunasan, BAST). Layar ini hanya
              menampilkan status.
            </div>
            {legal?.contract_id && legal?.customer_id ? (
              <Button data-testid={T.legalOpenContractBtn} size="sm"
                onClick={() => { onOpenChange?.(false); navigate(`/customers/${legal.customer_id}?tab=kontrak53`); }}>
                <ExternalLink className="mr-1.5 h-4 w-4" /> Buka Kontrak &amp; Legal
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">
                Deal ini belum menjadi pembeli, jadi belum ada kontrak. Klik <b>Jadikan Pembeli</b> di
                daftar deal lebih dulu.
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
