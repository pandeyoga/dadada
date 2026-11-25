import React from "react";
import { CircleCheck, Clock, TriangleAlert, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import renderIcon from "./renderIcon";

const ICONS = { ok: CircleCheck, warn: Clock, danger: TriangleAlert, info: Info, neutral: null };

/** Status = warna + ikon + kata. `icon={null}` menyembunyikan ikon bawaan nada. */
export default function StatusChip({ tone = "neutral", icon, className, children }) {
  const t = tone in ICONS ? tone : "neutral";
  const I = icon === undefined ? ICONS[t] : icon;
  return (
    <span className={cn("rdg-chip", `rdg-chip--${t}`, className)}>
      {renderIcon(I, { size: 14, strokeWidth: 2.4 })}
      {children}
    </span>
  );
}
