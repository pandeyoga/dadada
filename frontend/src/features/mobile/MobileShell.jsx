import { useState } from "react";
import { Layers, Bell, Monitor, LogOut } from "lucide-react";
import { entityShortById } from "../../utils/entityLabel";

/**
 * §3-A — SATU cangkang mobile bersama untuk semua peran (bottom-nav per peran).
 * Sasaran sentuh besar, satu tugas per layar; `tabs` = [{id,label,icon,render}].
 */
export default function MobileShell({ user, tabs, entities = [], selectedEntity, unreadCount = 0, onLogout, onForceDesktop, testId = "mobile-shell", initialTab, topSlot = null }) {
  const [tab, setTab] = useState(initialTab || tabs[0]?.id);
  const active = tabs.find((t) => t.id === tab) || tabs[0];
  return (
    <div className="m-shell" data-testid={testId}>
      <header className="m-appbar">
        <div className="m-brand-mark"><Layers size={16} /></div>
        <div className="m-title">
          <span className="t1">Halo, {(user?.name || "").split(" ")[0]}</span>
          <span className="t2">{entityShortById(entities, selectedEntity) || user?.role}</span>
        </div>
        <button className="m-act" data-testid="mobile-force-desktop" onClick={onForceDesktop} aria-label="Tampilan desktop"><Monitor size={18} /></button>
        <button className="m-act" data-testid="mobile-logout" onClick={onLogout} aria-label="Keluar"><LogOut size={18} /></button>
        {unreadCount > 0 && <span className="m-badge" data-testid="mobile-unread"><Bell size={10} /> {unreadCount}</span>}
      </header>
      <main className="m-main" data-testid={`mobile-view-${active?.id}`}>{topSlot}{active?.render?.({ setTab })}</main>
      <nav className="m-tabbar" data-testid="mobile-tabbar">
        {tabs.map((t) => {
          const Icon = t.icon; const on = t.id === tab;
          return (
            <button key={t.id} data-testid={`mobile-tab-btn-${t.id}`} className={`m-tab ${on ? "active" : ""}`} onClick={() => setTab(t.id)} aria-current={on}>
              <span className="m-tab-ico"><Icon size={21} strokeWidth={on ? 2.4 : 2} /></span>{t.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
