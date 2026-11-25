import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import renderIcon from "./renderIcon";

/**
 * Baris daftar. `to` → tautan, `onClick` → tombol, selain itu teks biasa.
 * `right` menggantikan panah bawaan. Pembatas antarbaris diatur pembungkus
 * (mis. `divide-y divide-[color:var(--rdg-line)]`).
 */
export default function ListRow({ icon, title, subtitle, right, to, onClick }) {
  const body = (
    <>
      {icon && <span className="rdg-row-icon">{renderIcon(icon, { size: 20, strokeWidth: 2.1 })}</span>}
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-semibold leading-snug text-rdg-ink900">{title}</span>
        {subtitle && <span className="mt-0.5 block text-[13px] leading-snug text-[color:var(--rdg-muted)]">{subtitle}</span>}
      </span>
      {right}
      {(to || onClick) && !right && <ChevronRight size={18} aria-hidden="true" className="flex-none text-[color:var(--rdg-muted)]" />}
    </>
  );
  if (to) return <Link to={to} className="rdg-row">{body}</Link>;
  if (onClick) return <button type="button" onClick={onClick} className="rdg-row">{body}</button>;
  return <div className="rdg-row">{body}</div>;
}
