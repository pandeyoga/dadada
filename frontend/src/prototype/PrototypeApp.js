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
import BuyerHome from "./surfaces/buyer/BuyerHome";
import Progress from "./surfaces/buyer/Progress";
import PlotMap from "./surfaces/buyer/PlotMap";
import Payments from "./surfaces/buyer/Payments";
import PayItem from "./surfaces/buyer/PayItem";
import Kpr from "./surfaces/buyer/Kpr";
import Cancellation from "./surfaces/buyer/Cancellation";
import Documents from "./surfaces/buyer/Documents";
import BuyerAccount from "./surfaces/buyer/BuyerAccount";
import Referral from "./surfaces/buyer/Referral";
import Promo from "./surfaces/buyer/Promo";
import Welcome from "./surfaces/transition/Welcome";
import ResidentHome from "./surfaces/resident/ResidentHome";
import { getState, resetState } from "./services/store";
import { setPersona, simulateBast, setLocation, homePathFor } from "./services/api/session";

// Satu tempat pemetaan id layar -> komponen. Task berikutnya mengganti Placeholder.
const COMPONENTS = {
  U1: Launcher, U2: Login,
  P1: BuyerHome, P2: Progress, P3: PlotMap, P4: Payments, P5: PayItem, P6: Kpr,
  P7: Cancellation, P8: Documents, P9: BuyerAccount, P10: Referral, P11: Promo,
  T1: Welcome, W1: ResidentHome,
};

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
