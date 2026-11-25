import React from "react";
import { Inbox } from "lucide-react";
import renderIcon from "./renderIcon";

/** Keadaan kosong. `children` (opsional) = tombol aksi di bawahnya. */
export default function EmptyState({ icon = Inbox, title, body, children }) {
  return (
    <div className="flex flex-col items-center text-center px-6 py-10">
      <span className="rdg-empty-icon">{renderIcon(icon, { size: 30, strokeWidth: 2 })}</span>
      <p className="mt-4 text-[16px] font-bold text-rdg-ink900">{title}</p>
      {body && <p className="mt-1 max-w-[290px] text-[14px] leading-relaxed text-[color:var(--rdg-muted)]">{body}</p>}
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}
