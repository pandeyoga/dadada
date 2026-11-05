import React from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Hari ini menurut WIB (YYYY-MM-DD) — batas atas tanggal bayar. */
export const todayWIB = () => new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Jakarta" });

/**
 * Tanggal bayar nyata (opsional). Kosong = dibukukan hari ini. Server menolak tanggal masa depan dan
 * tanggal di periode yang sudah ditutup/dikunci (GL-15), jadi pesan galatnya muncul saat simpan.
 */
export default function PaymentDateField({ value, onChange, id = "payment-date", testId }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>Tanggal bayar (opsional)</Label>
      <Input id={id} type="date" data-testid={testId} value={value} max={todayWIB()}
        onChange={(e) => onChange(e.target.value)} />
      <p className="text-[11px] text-muted-foreground">
        Isi bila uang sebenarnya masuk/keluar di tanggal lain. Kosong = hari ini.
      </p>
    </div>
  );
}
