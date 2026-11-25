import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { Siren } from "lucide-react";
import { cn } from "@/lib/utils";
import renderIcon from "./renderIcon";

const TICK = 100;
const R = 92;
const C = 2 * Math.PI * R;

/**
 * Tekan-tahan untuk konfirmasi (SOS). Pointer atau tombol Space/Enter ditahan
 * selama `durationMs`; dilepas lebih awal = batal. `onConfirm` dipanggil sekali
 * per tahanan penuh.
 */
export default function HoldToConfirm({ durationMs = 3000, onConfirm, label, icon = Siren, disabled = false }) {
  const [elapsed, setElapsed] = useState(0);
  const [holding, setHolding] = useState(false);
  const timer = useRef(null);
  const ticker = useRef(null);
  const confirmRef = useRef(onConfirm);
  const hintId = useId();
  confirmRef.current = onConfirm;

  const stop = useCallback(() => {
    clearTimeout(timer.current);
    clearInterval(ticker.current);
    timer.current = null;
    setHolding(false);
    setElapsed(0);
  }, []);

  const start = () => {
    if (disabled || timer.current) return;
    setHolding(true);
    setElapsed(0);
    ticker.current = setInterval(() => setElapsed((e) => Math.min(durationMs, e + TICK)), TICK);
    timer.current = setTimeout(() => {
      stop();
      try { navigator.vibrate?.(200); } catch (e) { /* tidak didukung */ }
      confirmRef.current?.();
    }, durationMs);
  };

  useEffect(() => () => {
    clearTimeout(timer.current);
    clearInterval(ticker.current);
  }, []);
  useEffect(() => {
    if (disabled) stop();
  }, [disabled, stop]);

  const isHoldKey = (e) => e.key === " " || e.key === "Enter";
  const onKeyDown = (e) => {
    if (!isHoldKey(e)) return;
    e.preventDefault();
    if (!e.repeat) start();
  };
  const onKeyUp = (e) => {
    if (!isHoldKey(e)) return;
    e.preventDefault();
    stop();
  };
  const onPointerDown = (e) => {
    if (e.button != null && e.button > 0) return;
    try { e.currentTarget.setPointerCapture?.(e.pointerId); } catch (err) { /* jsdom */ }
    start();
  };

  const secs = Math.ceil(durationMs / 1000);
  const remaining = Math.max(1, Math.ceil((durationMs - elapsed) / 1000));
  return (
    <div className={cn("rdg-hold", holding && "is-holding")}>
      <button
        type="button"
        className={cn("rdg-hold-btn", holding && "is-holding")}
        disabled={disabled}
        aria-describedby={hintId}
        onPointerDown={onPointerDown}
        onPointerUp={stop}
        onPointerCancel={stop}
        onLostPointerCapture={stop}
        onKeyDown={onKeyDown}
        onKeyUp={onKeyUp}
        onBlur={stop}
        onContextMenu={(e) => e.preventDefault()}
      >
        <svg className="rdg-hold-ring" viewBox="0 0 196 196" aria-hidden="true">
          <circle className="track" cx="98" cy="98" r={R} />
          <circle className="bar" cx="98" cy="98" r={R} strokeDasharray={C} strokeDashoffset={C * (1 - elapsed / durationMs)} />
        </svg>
        <span className="rdg-hold-core">
          {renderIcon(icon, { size: 40, strokeWidth: 2.2 })}
          <span className="rdg-hold-label">{label}</span>
          <span className="rdg-hold-hint" id={hintId} aria-live="polite">
            {holding ? `${remaining} detik lagi…` : `Tahan ${secs} detik`}
          </span>
        </span>
      </button>
    </div>
  );
}
