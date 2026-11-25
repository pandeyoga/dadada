import React from "react";
import { Link } from "react-router-dom";
import { LayoutDashboard, ReceiptText, Wrench, Megaphone, Wallet, ShieldCheck, Store } from "lucide-react";
import { cn } from "@/lib/utils";
import BrandMark from "./BrandMark";

export const MANAGER_NAV = [
  { id: "K1", label: "Ringkasan", to: "/app/pengelola", icon: LayoutDashboard },
  { id: "K2", label: "Tagihan IPL", to: "/app/pengelola/ipl", icon: ReceiptText },
  { id: "K3", label: "Tiket & keluhan", to: "/app/pengelola/tiket", icon: Wrench },
  { id: "K4", label: "Pengumuman & agenda", to: "/app/pengelola/pengumuman", icon: Megaphone },
  { id: "K5", label: "Laporan kas", to: "/app/pengelola/kas", icon: Wallet },
  { id: "K6", label: "Keamanan", to: "/app/pengelola/keamanan", icon: ShieldCheck },
  { id: "K7", label: "Mitra layanan & pasar", to: "/app/pengelola/mitra", icon: Store },
];

/** Kerangka dasbor pengelola: sidebar gelap (≥1024 px) atau bilah atas (tablet). `active` = id layar K1–K7. */
export default function DesktopShell({ active, children }) {
  return (
    <div className="min-h-screen bg-[#f2faf6] lg:flex">
      <aside style={{ borderRadius: 0 }} className="rdg-hero px-4 py-4 lg:sticky lg:top-0 lg:h-screen lg:w-[264px] lg:flex-none lg:px-5 lg:py-7">
        <div className="flex items-center justify-between gap-4 lg:block">
          <BrandMark variant="dark" />
          <p className="text-[12.5px] font-semibold text-white/85 lg:mt-3">Pengelola · Estora Residence</p>
        </div>
        <nav aria-label="Menu pengelola" className="mt-4 lg:mt-8">
          <ul className="-mx-1 flex gap-1 overflow-x-auto pb-1 lg:mx-0 lg:block lg:space-y-1 lg:overflow-visible">
            {MANAGER_NAV.map(({ id, label, to, icon: Icon }) => {
              const on = id === active;
              return (
                <li key={id} className="flex-none">
                  <Link
                    to={to}
                    aria-current={on ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 whitespace-nowrap rounded-2xl px-3.5 py-2.5 text-[14px] font-semibold no-underline transition-colors",
                      on ? "bg-white text-rdg-forest shadow-[0_6px_16px_rgba(0,31,36,0.25)]" : "text-white/90 hover:bg-white/10"
                    )}
                  >
                    <Icon aria-hidden="true" size={19} strokeWidth={on ? 2.4 : 2} />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>
      <main className="min-w-0 flex-1 px-5 py-6 lg:px-10 lg:py-8">{children}</main>
    </div>
  );
}
