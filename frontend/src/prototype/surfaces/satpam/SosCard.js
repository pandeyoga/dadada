import React from "react";
import { Link } from "react-router-dom";
import { Siren, ChevronRight } from "lucide-react";
import { sosLabel } from "../../services/api/sos";
import { jam } from "../../lib/format";

/** Kartu merah laporan SOS aktif → layar S2. Berkedip ringan hanya saat baru masuk (sent). */
export default function SosCard({ event }) {
  const waiting = event.status === "sent";
  return (
    <Link to="/app/satpam/sos" className={`rdg-sos-card ${waiting ? "is-new" : ""}`}>
      <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-white text-[color:var(--rdg-sos-ink)]"><Siren size={28} aria-hidden="true" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-[13px] font-semibold">{waiting ? "Menunggu diterima" : "Sedang ditangani"}</span>
        <span className="block text-[19px] font-extrabold leading-tight">{`Laporan darurat ${sosLabel(event.type)}`}</span>
        <span className="block text-[14px]">{`Blok ${event.unit} · ${jam(event.createdAt)} WIB`}</span>
      </span>
      <ChevronRight size={22} aria-hidden="true" className="flex-none" />
    </Link>
  );
}
