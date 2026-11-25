import React, { useEffect } from "react";
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
import Login from "./surfaces/demo/Login";
import { getState, resetState } from "./services/store";
import { setPersona, simulateBast, setLocation, homePathFor } from "./services/api/session";

// Satu tempat pemetaan id layar -> komponen. Task berikutnya mengganti Placeholder.
const COMPONENTS = { U1: Launcher, U2: Login };

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
  const allowed = isPrototypeHost(hostname);
  // Tuas untuk presenter/uji; hanya dipasang bila host diizinkan.
  useEffect(() => {
    if (!allowed) return undefined;
    const api = { reset: resetState, setPersona, simulateBast, setLocation };
    window.__rdgDemo = Object.assign(window.__rdgDemo || {}, api);
    return () => { delete window.__rdgDemo; };
  }, [allowed]);
  if (!allowed) return <Navigate to="/" replace />;
  return (
    <div className="rdg font-rdg">
      <Routes>
        {screens.map((s) => (
          <Route key={s.id} path={rel(DYNAMIC[s.id] || s.path)} element={renderScreen(s)} />
        ))}
        {/* /app (indeks) -> beranda menurut persona; belum masuk -> peluncur */}
        <Route path="/" element={<Navigate to={homePathFor(getState())} replace />} />
        <Route path="*" element={<Navigate to="/app/demo" replace />} />
      </Routes>
    </div>
  );
}
