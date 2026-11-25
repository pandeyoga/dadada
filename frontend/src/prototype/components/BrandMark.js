import React from "react";
import { cn } from "@/lib/utils";

const MARK = `${process.env.PUBLIC_URL || ""}/rdg/mark.png`;

/**
 * Ikon Estora + teks "Rumah Dalam Genggaman". `variant` mengikuti latar:
 * 'light' = latar terang (teks ink), 'dark' = latar gelap (teks putih,
 * ikon di atas ubin putih agar gradasi hijaunya tetap terbaca).
 */
export default function BrandMark({ variant = "light", withText = true, className }) {
  const dark = variant === "dark";
  const img = (
    <img
      src={MARK}
      alt={withText ? "" : "Rumah Dalam Genggaman"}
      width={dark ? 26 : 34}
      height={dark ? 26 : 34}
      className="rdg-brand-mark"
    />
  );
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      {dark ? <span className="rdg-brand-tile h-10 w-10">{img}</span> : img}
      {withText && (
        <span className={cn("text-[15px] font-extrabold leading-[1.15] tracking-[-0.01em]", dark ? "text-white" : "text-rdg-ink")}>
          Rumah Dalam
          <br />
          Genggaman
        </span>
      )}
    </span>
  );
}
