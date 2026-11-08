import React from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import MoneyText from "@/components/patterns/MoneyText";
import { P56, W1C } from "@/constants/testIds";

export const COST_NOTE_MIN = 10;   // sama dengan aturan server (`cancel_costs.assert_ack`)

/** Pengakuan biaya sudah memenuhi syarat? (tanpa titipan/invoice biaya menggantung, atau kebijakan menanganinya = tidak diperlukan). */
export function costAckOk(holds, ack) {
  return !holds?.has_holds || !!holds?.handled_by_policy || (ack.on && ack.note.trim().length >= COST_NOTE_MIN);
}

/** W1-C #12 — kebijakan `cancel.cost_deposit.policy` menangani titipan/invoice biaya: tidak perlu pengakuan, hanya pemberitahuan. */
function PolicyNotice({ holds }) {
  const hangus = holds.policy === "hangus_sebagian";
  return (
    <div data-testid={W1C.costPolicy} data-policy={holds.policy} className="space-y-1 rounded-lg border border-sky-300 bg-sky-50 p-3 text-xs text-sky-950">
      <p>Masih ada titipan biaya <MoneyText value={holds.titipan_balance} /> dan
        invoice biaya terbuka <MoneyText value={holds.open_invoice_total} />.
        Kebijakan pembatalan menanganinya, jadi tidak perlu pengakuan di sini:</p>
      <ul className="list-disc pl-4">
        <li>{hangus
          ? "sebagian titipan ditahan developer (persentase di Pusat Konfigurasi), sisanya menjadi utang refund ke pembeli;"
          : "titipan biaya (setelah dikurangi biaya yang sudah disalurkan ke notaris/BPN) menjadi utang refund ke pembeli;"}</li>
        <li>invoice biaya yang masih terbuka dibatalkan;</li>
        <li>keduanya baru berlaku setelah disetujui Keuangan (bila diwajibkan) — lihat Keuangan › Pembatalan &amp; Refund.</li>
      </ul>
    </div>
  );
}

/**
 * FN-03 — titipan/invoice biaya yang masih menggantung harus DIAKUI penyetuju sebelum pembatalan disetujui
 * (perlakuan uangnya keputusan pemilik, tidak dijurnal otomatis). Tombol setujui menunggu pengakuan ini lengkap;
 * menolak tidak memerlukannya. Dipakai juga oleh batal reservasi satu-klik (`CancelDealDialog`).
 */
export default function CancellationCostAck({ holds, ack, onChange, verb = "menyetujui", rejectNote = true }) {
  if (!holds?.has_holds) return null;
  if (holds.handled_by_policy) return <PolicyNotice holds={holds} />;
  const ok = costAckOk(holds, ack);
  return (
    <div data-testid={P56.costHold} data-ack-ok={String(ok)} className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs">
      <p>Masih ada titipan biaya <MoneyText value={holds.titipan_balance} /> dan
        invoice biaya terbuka <MoneyText value={holds.open_invoice_total} />.
        Perlakuannya keputusan pemilik dan TIDAK dijurnal otomatis oleh pembatalan.</p>
      <label className="flex items-center gap-2">
        <Checkbox data-testid={P56.costAckCheck} checked={ack.on} onCheckedChange={(v) => onChange({ ...ack, on: !!v })} />
        Saya mengakui dan akan menanganinya terpisah
      </label>
      {ack.on ? (
        <Input data-testid={P56.costAckNote} aria-label="Catatan penanganan biaya" value={ack.note}
          placeholder={`Catatan penanganan biaya (min. ${COST_NOTE_MIN} huruf)`}
          onChange={(e) => onChange({ ...ack, note: e.target.value })} />
      ) : null}
      {!ok ? (
        <p data-testid={P56.costAckHint} className="text-amber-900">
          Untuk {verb}: centang pengakuan lalu isi catatan penanganan (min. {COST_NOTE_MIN} huruf).{rejectNote ? " Menolak tidak memerlukannya." : ""}
        </p>
      ) : null}
    </div>
  );
}
