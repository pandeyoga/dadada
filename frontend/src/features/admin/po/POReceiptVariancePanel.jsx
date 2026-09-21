import { Scale } from "lucide-react";

const fmt = (n) => new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(Number(n || 0));

/** Ringkasan satu baris untuk badge (baris PO, papan PO, form tagihan). */
export function receiptVarianceSummary(variances) {
  const list = Array.isArray(variances) ? variances : [];
  if (!list.length) return null;
  const diffQty = list.reduce((s, v) => s + Number(v.diff_qty || 0), 0);
  const flagged = list.reduce((s, v) => s + (v.label_variance_rolls || []).length, 0);
  const unit = list[list.length - 1]?.unit || "";
  const parts = [];
  if (Math.abs(diffQty) > 1e-6) parts.push(`${diffQty > 0 ? "+" : "−"}${fmt(Math.abs(diffQty))} ${unit}`.trim());
  if (flagged) parts.push(`${flagged} roll label≠aktual`);
  return { count: list.length, diffQty, flagged, label: parts.join(" · ") || "ada selisih" };
}

/**
 * POReceiptVariancePanel — catatan selisih penerimaan vs PO (FASE SL) yang ditulis
 * gudang saat GR selesai (qty/roll kurang-lebih, roll ber-flag label vs aktual).
 * Dibaca purchasing (detail PO) dan finance (form Vendor Bill) sebelum menagih.
 */
export default function POReceiptVariancePanel({ variances, testId = "po-receipt-variances", compact = false }) {
  const list = Array.isArray(variances) ? variances : [];
  if (!list.length) return null;
  return (
    <div data-testid={testId} className="rounded-md border border-[#F5D9A8] bg-[#FFFBF3] px-2.5 py-2 text-[11px] text-[#8A5A00]">
      <div className="flex items-center gap-1.5 font-bold mb-1">
        <Scale size={13} /> Selisih Penerimaan vs PO ({list.length} catatan gudang)
      </div>
      <div className="space-y-1">
        {list.map((v, i) => (
          <div key={i} data-testid={`${testId}-item-${i}`} className="rounded border border-[#F1E3C4] bg-white/70 px-2 py-1">
            <p className="font-semibold">{v.note || "ada selisih"}</p>
            {!compact && (
              <p className="text-[10px] text-[#9A7A3A] tabular-nums">
                PO {fmt(v.expected_qty)} {v.unit} → diterima {fmt(v.received_qty)} {v.unit}
                {v.diff_pct != null ? ` (${v.diff_pct > 0 ? "+" : ""}${v.diff_pct}%)` : ""}
                {v.expected_rolls != null ? ` · roll ${v.received_rolls}/${v.expected_rolls}` : ""}
                {(v.label_variance_rolls || []).length ? ` · flag QC: ${v.label_variance_rolls.join(", ")}` : ""}
                {v.recorded_by ? ` · ${v.recorded_by}` : ""}
                {v.recorded_at ? ` · ${String(v.recorded_at).slice(0, 10)}` : ""}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
