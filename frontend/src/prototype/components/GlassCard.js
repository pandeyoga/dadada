import React from "react";
import { cn } from "@/lib/utils";

/** Kartu kaca: HANYA di atas latar hero gelap (teks putih). */
export function GlassCard({ as: Tag = "div", className, children, ...rest }) {
  return <Tag className={cn("rdg-glass relative p-4", className)} {...rest}>{children}</Tag>;
}

/** Kartu konten putih buram 82 % dengan teks gelap — untuk area terang. */
export function FrostCard({ as: Tag = "div", className, children, ...rest }) {
  return <Tag className={cn("rdg-frost relative p-4", className)} {...rest}>{children}</Tag>;
}

export default GlassCard;
