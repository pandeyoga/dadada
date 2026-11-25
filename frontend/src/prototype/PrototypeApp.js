import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import "./theme/rdg.css";
import "./theme/rdg-components.css";
import "./theme/rdg-controls.css";
import screens from "./screens.json";
import { isPrototypeHost } from "./lib/host";
import Placeholder from "./surfaces/Placeholder";
import Launcher from "./surfaces/demo/Launcher";

// Satu tempat pemetaan id layar -> komponen. Task berikutnya mengganti Placeholder.
const COMPONENTS = { U1: Launcher };

// Rute dinamis (menggantikan path statis contoh di screens.json).
const DYNAMIC = {
  P5: "/app/pembeli/bayar/:itemId",
  P11: "/app/pembeli/promo/:id",
  W15: "/app/warga/komunitas/event/:id",
};

// Routes bersarang dicocokkan relatif terhadap induk "/app/*".
const rel = (p) => p.replace(/^\/app/, "") || "/";

function renderScreen(s) {
  const C = COMPONENTS[s.id];
  return C ? <C /> : <Placeholder id={s.id} title={s.title} />;
}

export default function PrototypeApp({ hostname = window.location.hostname }) {
  if (!isPrototypeHost(hostname)) return <Navigate to="/" replace />;
  return (
    <div className="rdg font-rdg">
      <Routes>
        {screens.map((s) => (
          <Route key={s.id} path={rel(DYNAMIC[s.id] || s.path)} element={renderScreen(s)} />
        ))}
        {/* /app (indeks) -> menurut session.persona (Task 4); sementara ke peluncur */}
        <Route path="/" element={<Navigate to="/app/demo" replace />} />
        <Route path="*" element={<Navigate to="/app/demo" replace />} />
      </Routes>
    </div>
  );
}
