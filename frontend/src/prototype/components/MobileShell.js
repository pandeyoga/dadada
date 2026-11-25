import React from "react";
import BottomNav from "./BottomNav";

/**
 * Kolom tengah maks 430 px; latar halaman bergradasi di layar lebar.
 * `nav` ('buyer'|'resident'|'satpam'|'partner') menampilkan menu bawah dan
 * menyisakan ruang di bawah layar (lihat `.rdg-shell[data-nav]`).
 */
export default function MobileShell({ children, nav = null }) {
  return (
    <div className="rdg-page min-h-screen flex justify-center">
      <div className="rdg-shell w-full max-w-[430px] min-h-screen relative" data-nav={nav || undefined}>
        {children}
        {nav && <BottomNav variant={nav} />}
      </div>
    </div>
  );
}
