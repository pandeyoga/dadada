import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  House, HardHat, Wallet, FileText, CircleUser, ShieldCheck, Siren, ReceiptText, Users,
  ShieldHalf, ScanQrCode, Cctv, Route, Building2, UserPlus, Coins,
} from "lucide-react";

// `also`: rute lain (di luar prefiks `to`) yang juga menyalakan tab ini.
// `end`: hanya aktif di rute persis (beranda); tab lain ikut aktif di subhalamannya.
export const NAV_ITEMS = {
  buyer: [
    { label: "Beranda", to: "/app/pembeli", icon: House, end: true },
    { label: "Progres", to: "/app/pembeli/progres", icon: HardHat },
    { label: "Bayar", to: "/app/pembeli/bayar", icon: Wallet },
    { label: "Dokumen", to: "/app/pembeli/dokumen", icon: FileText },
    { label: "Akun", to: "/app/pembeli/akun", icon: CircleUser },
  ],
  resident: [
    { label: "Beranda", to: "/app/warga", icon: House, end: true },
    { label: "Keamanan", to: "/app/warga/keamanan", icon: ShieldCheck },
    { label: "SOS", to: "/app/warga/sos", icon: Siren, sos: true, aria: "SOS darurat" },
    { label: "Tagihan", to: "/app/warga/tagihan", icon: ReceiptText, also: ["/app/warga/isi-ulang"] },
    { label: "Komunitas", to: "/app/warga/komunitas", icon: Users, also: ["/app/warga/pasar", "/app/warga/jasa"] },
  ],
  satpam: [
    { label: "Pos", to: "/app/satpam", icon: ShieldHalf, end: true },
    { label: "Tamu", to: "/app/satpam/tamu", icon: ScanQrCode },
    { label: "CCTV", to: "/app/satpam/cctv", icon: Cctv },
    { label: "Patroli", to: "/app/satpam/patroli", icon: Route },
  ],
  partner: [
    { label: "Beranda", to: "/app/mitra", icon: House, end: true },
    { label: "Katalog", to: "/app/mitra/katalog", icon: Building2 },
    { label: "Rujukan", to: "/app/mitra/rujukan", icon: UserPlus },
    { label: "Komisi", to: "/app/mitra/komisi", icon: Coins },
  ],
};

/** Menu bawah melayang (kaca putih). Varian resident punya SOS bulat merah di tengah. */
export default function BottomNav({ variant }) {
  const items = NAV_ITEMS[variant];
  const { pathname } = useLocation();
  if (!items) return null;
  return (
    <nav className="rdg-nav" aria-label="Menu utama">
      <ul className="rdg-nav-bar" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
        {items.map(({ label, to, icon: Icon, end, sos, aria, also }) => {
          const extra = (also || []).some((p) => pathname === p || pathname.startsWith(`${p}/`));
          return (
          <li key={to} className="flex justify-center">
            <NavLink
              to={to}
              end={end}
              aria-label={aria}
              className={({ isActive }) =>
                ["rdg-nav-link w-full", sos && "rdg-nav-link--sos", (isActive || extra) && "is-active"].filter(Boolean).join(" ")
              }
            >
              {({ isActive: on }) => {
                const isActive = on || extra;
                return (
                <>
                  <span className={sos ? "rdg-nav-sos" : "rdg-nav-icon"}>
                    <Icon aria-hidden="true" size={sos ? 28 : 23} strokeWidth={isActive || sos ? 2.4 : 2} />
                  </span>
                  <span>{label}</span>
                </>
                );
              }}
            </NavLink>
          </li>
          );
        })}
      </ul>
    </nav>
  );
}
