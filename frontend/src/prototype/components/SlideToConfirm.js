import React, { useEffect, useId, useRef, useState } from "react";
import { LockOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import renderIcon from "./renderIcon";

const PAD = 4; // = padding .rdg-slide
const THRESHOLD = 0.9;

/**
 * Geser untuk konfirmasi (mis. buka kunci). Konfirmasi bila kenop digeser
 * ≥ 90 % lintasan; ketukan saja tidak cukup. Keyboard: fokus + Enter.
 * `variant`: 'dark' (bawaan, di atas hero) atau 'light' (kartu terang).
 */
export default function SlideToConfirm({ onConfirm, label, icon = LockOpen, variant = "dark", disabled = false }) {
  const [x, setX] = useState(0);
  const [max, setMax] = useState(1); // lintasan terakhir yang diukur (untuk pudar label)
  const [dragging, setDragging] = useState(false);
  const track = useRef(null);
  const knob = useRef(null);
  const drag = useRef(null); // { startX, max, x }
  const resetTimer = useRef(null);
  const hintId = useId();

  useEffect(() => () => clearTimeout(resetTimer.current), []);

  const maxTravel = () => {
    const t = track.current?.getBoundingClientRect().width || 0;
    const k = knob.current?.getBoundingClientRect().width || 0;
    return Math.max(0, t - k - PAD * 2);
  };

  const confirm = (travel) => {
    setMax(travel || 1);
    setX(travel);
    onConfirm?.();
    clearTimeout(resetTimer.current);
    resetTimer.current = setTimeout(() => setX(0), 700);
  };

  const onPointerDown = (e) => {
    if (disabled) return;
    try { e.currentTarget.setPointerCapture?.(e.pointerId); } catch (err) { /* jsdom */ }
    drag.current = { startX: e.clientX - x, max: maxTravel(), x };
    setMax(drag.current.max || 1);
    setDragging(true);
  };
  const onPointerMove = (e) => {
    const d = drag.current;
    if (!d) return;
    d.x = Math.max(0, Math.min(d.max, e.clientX - d.startX));
    setX(d.x);
  };
  const onPointerUp = () => {
    const d = drag.current;
    if (!d) return;
    drag.current = null;
    setDragging(false);
    if (d.max > 0 && d.x / d.max >= THRESHOLD) confirm(d.max);
    else setX(0);
  };
  const onKeyDown = (e) => {
    if (disabled || e.key !== "Enter") return;
    e.preventDefault();
    confirm(maxTravel());
  };

  const pct = Math.min(1, x / max);
  return (
    <div
      ref={track}
      data-slide-track=""
      className={cn("rdg-slide", variant === "light" && "rdg-slide--light", dragging && "is-dragging", disabled && "opacity-60")}
    >
      <span className="rdg-slide-fill" style={{ width: x + 60 }} aria-hidden="true" />
      <span className="rdg-slide-label" style={{ opacity: Math.max(0, 1 - pct * 1.6) }} aria-hidden="true">
        {label}
      </span>
      <span
        ref={knob}
        data-slide-knob=""
        role="slider"
        tabIndex={disabled ? -1 : 0}
        aria-label={label}
        aria-describedby={hintId}
        aria-disabled={disabled || undefined}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pct * 100)}
        className="rdg-slide-knob"
        style={{ transform: `translateX(${x}px)` }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={onKeyDown}
      >
        {renderIcon(icon, { size: 22, strokeWidth: 2.3 })}
      </span>
      <span id={hintId} className="sr-only">Geser ke kanan sampai ujung, atau tekan Enter.</span>
    </div>
  );
}
