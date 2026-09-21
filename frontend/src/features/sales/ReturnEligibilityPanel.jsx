/**
 * ReturnEligibilityPanel — KELAYAKAN RETUR TAMPAK (2026-06).
 * Sebelum menyetujui, pemutus perlu tahu: masih di dalam jendela retur atau tidak,
 * sisa harinya, jenis retur yang diizinkan kebijakan, dan biaya restocking.
 * Sumber: `GET /sales-return-policies/eligibility` — mesin yang SAMA dengan yang
 * menjaga pembuatan retur (R0), jadi angkanya tidak mungkin berselisih.
 * Batas QTY per produk tetap dijaga server saat retur dibuat (assert_return_within_limits).
 */
import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { AlertTriangle, CalendarClock, CheckCircle2, ShieldAlert } from "lucide-react";
import { fmtDate } from "./ReturnShared";

const ACTIVE = ["draft", "pending_approval", "approved", "inspecting", "inspected"];

export default function ReturnEligibilityPanel({ ret }) {
  const [el, setEl] = useState(null);
  useEffect(() => {
    let on = true;
    if (!ret?.order_id || !ACTIVE.includes(ret?.status)) { setEl(null); return undefined; }
    axios.get(`${API}/sales-return-policies/eligibility`,
      { params: { order_id: ret.order_id, return_type: ret.return_type || "" } })
      .then((r) => { if (on) setEl(r.data); })
      .catch(() => { if (on) setEl(null); });
    return () => { on = false; };
  }, [ret?.order_id, ret?.return_type, ret?.status]);

  if (!el || !ACTIVE.includes(ret?.status)) return null;

  const late = el.deadline && !el.within_window;
  const tone = el.eligible && !late
    ? { cls: "border-[#BFE3CC] bg-[#F2FBF5] text-[#1B7F4B]", Icon: CheckCircle2, label: "Dalam jendela retur" }
    : el.blocked
      ? { cls: "border-[#F3C1C1] bg-[#FDF0F0] text-[#C62828]", Icon: ShieldAlert, label: "Di luar jendela — kebijakan MEMBLOKIR" }
      : { cls: "border-[#F5E0C3] bg-[#FDF6EC] text-[#B45309]", Icon: AlertTriangle, label: "Perlu perhatian kebijakan" };
  const { Icon } = tone;

  return (
    <div className={`mb-3 rounded-lg border px-3 py-2 ${tone.cls}`} data-testid="return-eligibility-panel">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] font-semibold">
        <span className="inline-flex items-center gap-1.5"><Icon size={13} /> {tone.label}</span>
        {el.deadline && (
          <span className="inline-flex items-center gap-1 font-normal" data-testid="return-eligibility-deadline">
            <CalendarClock size={12} /> Jendela {el.window_days} hari · deadline <b>{fmtDate(el.deadline)}</b>
            {el.days_remaining != null && (
              <b className="tabular-nums">
                {el.days_remaining >= 0 ? ` (sisa ${el.days_remaining} hari)` : ` (lewat ${Math.abs(el.days_remaining)} hari)`}
              </b>
            )}
          </span>
        )}
        {el.restocking_fee_pct > 0 && (
          <span className="font-normal">Biaya restocking <b>{el.restocking_fee_pct}%</b></span>
        )}
        {(el.allowed_return_types || []).length > 0 && (
          <span className="font-normal">Tipe diizinkan: <b>{el.allowed_return_types.join(", ")}</b></span>
        )}
      </div>
      {(el.warnings || []).map((w, i) => (
        <p key={i} className="mt-1 text-[11px] font-normal" data-testid={`return-eligibility-warning-${i}`}>• {w}</p>
      ))}
    </div>
  );
}
