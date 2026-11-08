import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Coins } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import CashAccountSelect from "@/components/cashBank/CashAccountSelect";
import MoneyText from "@/components/patterns/MoneyText";
import StatusPill from "@/components/patterns/StatusPill";
import { ErrorState } from "@/components/patterns/StateViews";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { W1C } from "@/constants/testIds";
import { formatDateTimeWIB } from "@/utils/formatters";

const NOTE_MIN = 10;   // sama dengan aturan server (`cancel_cost_settlement.MIN_NOTE`)

/**
 * CostSettlementsPanel (Keuangan → "Pembatalan & Refund") — W1-C #12.
 *
 * Daftar PERMOHONAN refund titipan biaya (2-1470) + pembatalan invoice biaya terbuka pada deal batal. Lahir otomatis dari
 * pembatalan menurut kebijakan `cancel.cost_deposit.*`; disetujui Manajer Keuangan (orang lain dari pemohon) lalu refund
 * dibayar lewat jalur uang keluar yang digerbang dana. Tombol hanya muncul bila server mungkin mengizinkannya.
 */
export default function CostSettlementsPanel() {
  const { user, can } = useAuth();
  const mayView = can("cancellation", "view");
  const [data, setData] = useState({ rows: [], counts: {}, outstanding: 0 });
  const [state, setState] = useState({ loading: true, error: "" });
  const [decide, setDecide] = useState(null);       // { row, approved }
  const [note, setNote] = useState("");
  const [pay, setPay] = useState(null);             // row
  const [form, setForm] = useState({ method: "transfer", amount: "", cash_account_id: "" });
  const [busy, setBusy] = useState(false);
  const payRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/cancel-cost-settlements", { params: { limit: 100 } });
      setData({ rows: res.data.data || [], counts: res.data.counts || {}, outstanding: res.data.outstanding || 0 });
      setState({ loading: false, error: "" });
    } catch (e) {
      setState({ loading: false, error: e?.response?.data?.detail || "Gagal memuat permohonan refund titipan biaya." });
    }
  }, []);
  useEffect(() => { if (mayView) load(); }, [mayView, load]);

  if (!mayView || state.loading) return null;
  if (state.error) return <ErrorState message={state.error} onRetry={load} />;
  if (!data.rows.length) {
    return (
      <p data-testid={W1C.empty} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        Belum ada permohonan refund titipan biaya. Permohonan lahir otomatis saat deal dibatalkan dengan titipan biaya
        atau invoice biaya terbuka (kebijakan: Pusat Konfigurasi › Aturan Bisnis › Kebijakan).
      </p>
    );
  }

  const mayDecide = can("cancellation", "approve");
  const mayPay = can("cancellation", "update");
  const waiting = data.counts.diajukan || 0;

  const submitDecision = async () => {
    setBusy(true);
    try {
      await api.post(`/cancel-cost-settlements/${decide.row.id}/decision`, { approved: decide.approved, note: note.trim() });
      toast.success(decide.approved
        ? "Disetujui — titipan biaya menjadi utang refund dan invoice biaya terbuka dibatalkan."
        : "Permohonan ditolak — titipan & invoice biaya ditangani manual.");
      setDecide(null); setNote("");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan putusan.");
      load();   // 409/400: muat ulang supaya tombol yang sudah basi hilang
    } finally { setBusy(false); }
  };

  const openPay = (row) => {
    payRef.current = `ctb-${row.id}-${Date.now()}`;   // penanda sekali-pakai: klik ganda bukan pembayaran kedua
    setForm({ method: "transfer", amount: "", cash_account_id: "" });
    setPay(row);
  };
  const submitPay = async () => {
    setBusy(true);
    try {
      await api.post(`/cancel-cost-settlements/${pay.id}/refund`, {
        method: form.method, cash_account_id: form.cash_account_id || undefined,
        amount: form.amount ? Number(String(form.amount).replace(/[^\d]/g, "")) : undefined,
        client_ref: payRef.current,
      });
      toast.success("Refund titipan biaya dibayar & dibukukan.");
      setPay(null);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal membayar refund.");
      load();
    } finally { setBusy(false); }
  };

  return (
    <div data-testid={W1C.panel} className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Coins className="h-4 w-4" /> Refund titipan biaya pada deal batal
        <span data-testid={W1C.summary} className="text-xs font-normal text-muted-foreground">
          {waiting} menunggu persetujuan · sisa refund belum dibayar <MoneyText value={data.outstanding} />
        </span>
      </div>
      <div className="overflow-hidden rounded-lg border bg-card shadow-[var(--shadow-card)]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nomor</TableHead>
              <TableHead>Pembeli / unit</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Titipan</TableHead>
              <TableHead className="text-right">Refund</TableHead>
              <TableHead className="text-right">Hangus</TableHead>
              <TableHead className="text-right">Sisa refund</TableHead>
              <TableHead className="col-actions-head" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((r) => {
              const st = r.settlement;
              const mine = r.requested_by === user?.email;
              return (
                <TableRow key={r.id} data-testid={W1C.row} data-state={r.state}>
                  <TableCell className="font-mono text-xs">
                    {r.number}
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDateTimeWIB(r.requested_at)}</p>
                  </TableCell>
                  <TableCell className="text-sm">
                    {r.customer_name || "—"}
                    <p className="text-[11px] text-muted-foreground">unit {r.unit_code || "—"} · {r.source} · {r.policy_label}</p>
                  </TableCell>
                  <TableCell><StatusPill status={r.state} group="cost_settlement_state" /></TableCell>
                  <TableCell className="text-right"><MoneyText value={st ? st.titipan_balance : r.snapshot?.titipan_balance} /></TableCell>
                  <TableCell className="text-right">{st ? <MoneyText value={st.refund_amount} /> : <span className="text-xs text-muted-foreground">belum ditetapkan</span>}</TableCell>
                  <TableCell className="text-right">{st ? <MoneyText value={st.forfeit_amount} /> : "—"}</TableCell>
                  <TableCell className="text-right"><MoneyText value={r.refund_outstanding} /></TableCell>
                  <TableCell className="col-actions space-x-1 text-right">
                    {r.state === "diajukan" && mayDecide ? (
                      mine ? (
                        <span className="text-[11px] text-muted-foreground">Diajukan Anda — minta Keuangan lain menyetujui</span>
                      ) : (
                        <>
                          <Button size="sm" data-testid={W1C.approveBtn} onClick={() => { setNote(""); setDecide({ row: r, approved: true }); }}>Setujui</Button>
                          <Button size="sm" variant="outline" data-testid={W1C.rejectBtn} onClick={() => { setNote(""); setDecide({ row: r, approved: false }); }}>Tolak</Button>
                        </>
                      )
                    ) : null}
                    {r.can_pay_refund && mayPay ? (
                      <Button size="sm" data-testid={W1C.payBtn} onClick={() => openPay(r)}>Bayar refund</Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!decide} onOpenChange={(o) => { if (!o) setDecide(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{decide?.approved ? "Setujui" : "Tolak"} {decide?.row?.number}</DialogTitle>
            <DialogDescription>
              {decide?.approved
                ? "Saldo titipan biaya (setelah dikurangi yang sudah disalurkan ke pihak ketiga) menjadi utang refund pembeli dan invoice biaya yang masih terbuka dibatalkan. Dijurnal sekarang."
                : "Titipan dan invoice biaya dibiarkan apa adanya dan ditangani manual oleh Keuangan. Alasan wajib dicatat."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="ctb-note">Catatan{decide?.approved ? " (opsional)" : ` (minimal ${NOTE_MIN} huruf)`}</Label>
            <Textarea id="ctb-note" data-testid={W1C.decideNote} rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDecide(null)}>Batal</Button>
            <Button data-testid={W1C.decideConfirm} disabled={busy || (!decide?.approved && note.trim().length < NOTE_MIN)} onClick={submitDecision}>
              {decide?.approved ? "Setujui" : "Tolak"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!pay} onOpenChange={(o) => { if (!o) setPay(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bayar refund {pay?.number}</DialogTitle>
            <DialogDescription>
              Sisa utang refund <MoneyText value={pay?.refund_outstanding} />. Uang keluar dijaga saldo rekening; kosongkan nominal untuk melunasi sisa.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <CashAccountSelect value={form.cash_account_id || ""} kind="bank" label="Dari rekening / kas"
              testId="cost-settlement-cash-account" onChange={(v) => setForm((f) => ({ ...f, cash_account_id: v }))} />
            <div className="space-y-1.5">
              <Label htmlFor="ctb-amount">Nominal (Rp)</Label>
              <Input id="ctb-amount" data-testid={W1C.payAmount} inputMode="numeric" value={form.amount} placeholder="Sisa penuh"
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPay(null)}>Batal</Button>
            <Button data-testid={W1C.payConfirm} disabled={busy} onClick={submitPay}>Bayar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
