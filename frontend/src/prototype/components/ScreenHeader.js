import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import renderIcon from "./renderIcon";

/**
 * Tombol ikon header (44 px). `variant` mengikuti latar: 'dark' = kaca di atas
 * hero, 'light' = putih di latar terang. `to` → tautan, selain itu tombol.
 */
export function HeaderButton({ icon, label, to, onClick, badge = false, variant = "dark" }) {
  const props = {
    className: variant === "light" ? "rdg-icon-btn rdg-icon-btn--light" : "rdg-icon-btn",
    "aria-label": label,
    "data-badge": badge ? "" : undefined,
  };
  const ic = renderIcon(icon, { size: 21, strokeWidth: 2.1 });
  if (to) return <Link to={to} {...props}>{ic}</Link>;
  return <button type="button" onClick={onClick} {...props}>{ic}</button>;
}

/**
 * Judul layar dengan tombol kembali dan slot kanan.
 * `back`: true → kembali satu langkah; string → ke rute itu.
 * `variant`: 'dark' (bawaan, di dalam `Hero`) atau 'light' (di latar terang,
 * sudah termasuk padding layar).
 */
export default function ScreenHeader({ title, back, right, variant = "dark" }) {
  const navigate = useNavigate();
  const light = variant === "light";
  const goBack = () => (typeof back === "string" ? navigate(back) : navigate(-1));
  return (
    <header className={light ? "rdg-header rdg-header--light" : "rdg-header"}>
      <div>{back && <HeaderButton icon={ChevronLeft} label="Kembali" onClick={goBack} variant={variant} />}</div>
      <h1 className="m-0 truncate text-center text-[18px] font-bold tracking-[-0.01em]">{title}</h1>
      <div className="flex justify-end gap-2">{right}</div>
    </header>
  );
}
