import React from "react";
import { cn } from "@/lib/utils";

/**
 * Area atas gelap bergradasi (ink → forest) dengan sudut bawah membulat.
 * `height` = tinggi minimum (angka px atau string CSS). Konten tidak dipotong,
 * jadi kartu berikutnya boleh menumpang dengan margin negatif.
 */
export default function Hero({ height, className, children }) {
  return (
    <section className={cn("rdg-hero relative", className)} style={height ? { minHeight: height } : undefined}>
      <div className="relative px-5 pt-[calc(env(safe-area-inset-top)+14px)] pb-6">{children}</div>
    </section>
  );
}
