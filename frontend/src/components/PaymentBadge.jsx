// PaymentBadge — SATU kamus status bayar untuk daftar, panel ringkas, dan detail SO.
// Tiga keadaan: Lunas · Bayar Sebagian (opsional dengan sisa) · Belum bayar.
// Dulu `partial` jatuh ke "Belum bayar" (bohong) atau tampil mentah "partial" (Inggris).
import { Check } from "lucide-react";
import { formatCurrency } from "../utils/formatters";

export default function PaymentBadge({ order, showRemaining = false, className = "", testId = "payment-badge" }) {
  const ps = String(order?.payment_status || "").toLowerCase();
  const paid = Number(order?.paid_total || 0);
  const grand = Number(order?.grand_total ?? order?.total_amount ?? 0);
  const partial = ps === "partial" || (ps !== "paid" && paid > 0);
  const remaining = Math.max(grand - paid, 0);

  if (ps === "paid") {
    return (
      <span data-testid={testId}
            className={`inline-flex items-center gap-0.5 rounded-full border border-[#BFE6CE] bg-[#E6F6EC] px-1.5 py-0.5 text-[9.5px] font-bold text-[#1B7F4B] ${className}`}>
        <Check size={10} /> Lunas
      </span>
    );
  }
  if (partial) {
    return (
      <span data-testid={testId}
            className={`inline-flex items-center gap-0.5 rounded-full border border-[#F5D9A8] bg-[#FFF4E5] px-1.5 py-0.5 text-[9.5px] font-bold text-[#8A5300] ${className}`}>
        Bayar Sebagian{showRemaining && remaining > 0 ? ` · sisa ${formatCurrency(remaining)}` : ""}
      </span>
    );
  }
  return (
    <span data-testid={testId}
          className={`inline-flex items-center rounded-full border border-[#E2E2E7] bg-[#F2F2F5] px-1.5 py-0.5 text-[9.5px] font-bold text-[#6E6E73] ${className}`}>
      Belum bayar
    </span>
  );
}
