import React, { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import "./theme/rdg.css";
import "./theme/rdg-components.css";
import "./theme/rdg-controls.css";
import "./theme/rdg-security.css";
import screens from "./screens.json";
import { isPrototypeHost } from "./lib/host";
import { scrollToTop } from "./lib/scrollTop";
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
import SecurityHome from "./surfaces/resident/security/SecurityHome";
import DoorLock from "./surfaces/resident/security/DoorLock";
import HomeCctv from "./surfaces/resident/security/HomeCctv";
import AreaSecurity from "./surfaces/resident/security/AreaSecurity";
import Gate from "./surfaces/resident/security/Gate";
import Guests from "./surfaces/resident/security/Guests";
import Sos from "./surfaces/resident/security/Sos";
import SosContacts from "./surfaces/resident/security/SosContacts";
import Bills from "./surfaces/resident/bills/Bills";
import BillHistory from "./surfaces/resident/bills/BillHistory";
import CashReport from "./surfaces/resident/bills/CashReport";
import TopUp from "./surfaces/resident/bills/TopUp";
import Community from "./surfaces/resident/community/Community";
import EventDetail from "./surfaces/resident/community/EventDetail";
import Groups from "./surfaces/resident/community/Groups";
import Polls from "./surfaces/resident/community/Polls";
import Market from "./surfaces/resident/community/Market";
import HomeServices from "./surfaces/resident/community/HomeServices";
import AllServices from "./surfaces/resident/care/AllServices";
import ReportIssue from "./surfaces/resident/care/ReportIssue";
import Warranty from "./surfaces/resident/care/Warranty";
import HomeDocuments from "./surfaces/resident/care/HomeDocuments";
import Renovation from "./surfaces/resident/care/Renovation";
import Facilities from "./surfaces/resident/care/Facilities";
import Energy from "./surfaces/resident/care/Energy";
import Notifications from "./surfaces/resident/Notifications";
import ResidentAccount from "./surfaces/resident/ResidentAccount";
import GuardHome from "./surfaces/satpam/GuardHome";
import SosAlert from "./surfaces/satpam/SosAlert";
import GuestScan from "./surfaces/satpam/GuestScan";
import GuardCctv from "./surfaces/satpam/GuardCctv";
import Patrol from "./surfaces/satpam/Patrol";
import { getState, resetState } from "./services/store";
import { createGuestPass } from "./services/api/security";
import { sendSos, acceptSos, resolveSos } from "./services/api/sos";
import { setPersona, simulateBast, setLocation, homePathFor } from "./services/api/session";

// Satu tempat pemetaan id layar -> komponen. Task berikutnya mengganti Placeholder.
const COMPONENTS = {
  U1: Launcher, U2: Login,
  P1: BuyerHome, P2: Progress, P3: PlotMap, P4: Payments, P5: PayItem, P6: Kpr,
  P7: Cancellation, P8: Documents, P9: BuyerAccount, P10: Referral, P11: Promo,
  T1: Welcome, W1: ResidentHome,
  W2: SecurityHome, W3: DoorLock, W4: HomeCctv, W5: AreaSecurity, W6: Gate, W7: Guests, W8: Sos, W9: SosContacts,
  W10: Bills, W11: BillHistory, W12: CashReport, W13: TopUp,
  W14: Community, W15: EventDetail, W16: Groups, W17: Polls, W18: Market, W19: HomeServices,
  W20: AllServices, W21: ReportIssue, W22: Warranty, W23: HomeDocuments, W24: Renovation, W25: Facilities, W26: Energy,
  W27: Notifications, W28: ResidentAccount,
  S1: GuardHome, S2: SosAlert, S3: GuestScan, S4: GuardCctv, S5: Patrol,
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
  const { pathname } = useLocation();
  // Pindah layar → mulai dari atas.
  useEffect(() => { scrollToTop(); }, [pathname]);
  // Tuas untuk presenter/uji; hanya dipasang bila host diizinkan.
  useEffect(() => {
    if (!allowed) return undefined;
    const api = { reset: resetState, setPersona, simulateBast, setLocation, sendSos, createGuestPass, acceptSos, resolveSos };
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
