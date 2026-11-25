import React from "react";

// Kolom tengah maks 430 px; nav menyusul di Task 3.
export default function MobileShell({ children, nav = null }) {
  return (
    <div className="rdg-page min-h-screen flex justify-center">
      <div className="rdg-shell w-full max-w-[430px] min-h-screen relative" data-nav={nav || undefined}>
        {children}
      </div>
    </div>
  );
}
