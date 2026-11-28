import React, { useState } from "react";
import { Sparkles } from "lucide-react";
import PortalAiPanel from "./PortalAiPanel";

/** Tombol mengambang "Tanya Estora" (kanan bawah) + panel chat. */
export default function PortalAiButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      {open ? <PortalAiPanel onClose={() => setOpen(false)} /> : null}
      {!open ? (
        <button type="button" data-testid="portal-ai-button" onClick={() => setOpen(true)}
          className="fixed bottom-4 right-4 z-40 inline-flex min-h-[48px] items-center gap-2 rounded-full bg-indigo-600 px-4 text-sm font-semibold text-white shadow-lg hover:bg-indigo-700">
          <Sparkles className="h-4 w-4" aria-hidden="true" /> Tanya Estora
        </button>
      ) : null}
    </>
  );
}
