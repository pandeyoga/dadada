import React from "react";
import { Link } from "react-router-dom";
import renderIcon from "./renderIcon";

const TONES = ["leaf", "teal", "deep", "forest"];

/** Grid layanan 4 kolom, ikon di atas ubin bergradasi. `tone` opsional per item. */
export default function ServiceGrid({ items }) {
  return (
    <ul className="grid grid-cols-4 gap-x-1.5 gap-y-4">
      {items.map((it, i) => (
        <li key={`${it.to}-${it.label}`}>
          <Link to={it.to} className="rdg-service">
            <span className={`rdg-service-tile rdg-tone-${it.tone || TONES[i % TONES.length]}`}>
              {renderIcon(it.icon, { size: 25, strokeWidth: 2 })}
            </span>
            <span className="rdg-service-label">{it.label}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
