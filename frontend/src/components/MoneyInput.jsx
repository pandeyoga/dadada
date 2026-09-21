import DecimalInput from "./DecimalInput";
import { parseDecimal } from "../utils/decimalInput";
import { formatCurrency } from "../utils/formatters";

/**
 * MoneyInput — isian rupiah seragam: awalan "Rp", keypad desimal, dan pratinjau
 * terformat ("Rp 1.250.000") di bawah kotak supaya nol-nya tidak salah hitung.
 */
export default function MoneyInput({ value, onChange, className = "field", testId, hint, ...rest }) {
  const n = parseDecimal(value === null || value === undefined ? "" : String(value));
  const preview = value !== "" && value !== null && value !== undefined && !Number.isNaN(n) ? formatCurrency(n) : "";
  return (
    <div className="grid gap-0.5">
      <div className="relative">
        <DecimalInput {...rest} data-testid={testId} className={className} value={value} min={0}
          onChange={onChange} style={{ paddingLeft: 34 }} />
        <span className="pointer-events-none absolute left-2.5 top-1/2 z-10 -translate-y-1/2 text-[11px] font-semibold text-[#8E8E93]">Rp</span>
      </div>
      {(preview || hint) && (
        <p className="text-[10px] tabular-nums text-[#8E8E93]" data-testid={testId ? `${testId}-preview` : undefined}>
          {preview}{preview && hint ? " · " : ""}{hint || ""}
        </p>
      )}
    </div>
  );
}
