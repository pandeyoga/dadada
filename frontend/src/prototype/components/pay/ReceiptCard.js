import React from "react";
import { methodLabel } from "../../services/api/payments";
import { rupiah, tanggal, jam } from "../../lib/format";
import StatusChip from "../StatusChip";

/** Rincian kuitansi (dipakai PayFlow; bisa dipakai ulang di riwayat bayar). */
export default function ReceiptCard({ receipt }) {
  const rows = [
    ["No. kuitansi", receipt.id.toUpperCase()],
    ["Untuk", receipt.title],
    ["Nominal", rupiah(receipt.amount)],
    ["Metode", methodLabel(receipt.method)],
    ["Waktu bayar", `${tanggal(receipt.paidAt)}, ${jam(receipt.paidAt)} WIB`],
  ];
  return (
    <dl className="rdg-receipt">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd className="[overflow-wrap:anywhere]">{v}</dd>
        </div>
      ))}
      <div>
        <dt>Status</dt>
        <dd><StatusChip tone="ok">Lunas</StatusChip></dd>
      </div>
    </dl>
  );
}
