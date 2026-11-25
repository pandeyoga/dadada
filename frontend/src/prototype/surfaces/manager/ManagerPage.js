import React from "react";
import DesktopShell from "../../components/DesktopShell";
import Screen from "../../components/Screen";
import { FrostCard } from "../../components/GlassCard";
import Loading from "../../components/Loading";

export const FIELD = "mt-1 block min-h-[44px] w-full rounded-xl border border-[color:var(--rdg-line)] bg-white px-3 text-[15px] text-rdg-ink900";
export const TH = "px-3 py-2.5 text-left text-[12.5px] font-bold uppercase tracking-wide text-[color:var(--rdg-muted)]";
export const TD = "px-3 py-2.5 align-middle text-[14px]";
export const SMALL_BTN = "!min-h-[36px] !px-3.5 !text-[13px]";

/** Kerangka layar pengelola: sidebar + judul halaman. `id` = K1–K7. */
export default function ManagerPage({ id, title, subtitle, children }) {
  return (
    <Screen id={id}>
      <DesktopShell active={id}>
        <header className="mb-5">
          <h1 className="text-[26px] font-extrabold leading-tight text-rdg-ink900">{title}</h1>
          {subtitle && <p className="mt-1 text-[14.5px] text-[color:var(--rdg-muted)]">{subtitle}</p>}
        </header>
        <div className="space-y-5">{children}</div>
      </DesktopShell>
    </Screen>
  );
}

/** Kartu konten putih dengan judul bagian. */
export function Panel({ title, right, children, className = "", ...rest }) {
  return (
    <FrostCard className={`!p-5 ${className}`} {...rest}>
      {(title || right) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-[17px] font-extrabold">{title}</h2>}
          {right}
        </div>
      )}
      {children}
    </FrostCard>
  );
}

export const Table = ({ label, children }) => (
  <div className="relative overflow-x-auto">
    <table aria-label={label} className="w-full border-collapse">{children}</table>
  </div>
);

export { Loading };
