import React from "react";
import Photo from "../../../components/Photo";
import { StageIllustration } from "../../../components/Illustrations";

// Foto contoh lokal untuk laporan (foto lokal; SVG sebagai cadangan).
export const PHOTO_OPTIONS = [
  { id: "progress/atap", label: "Atap dan plafon" },
  { id: "progress/dinding", label: "Dinding" },
  { id: "progress/kusen", label: "Pintu dan jendela" },
  { id: "progress/plester", label: "Cat dan plester" },
];

export default function TicketPhoto({ img, className = "", tag = true }) {
  const label = (PHOTO_OPTIONS.find((p) => p.id === img) || { label: "Foto laporan" }).label;
  const alt = `Foto contoh: ${label}`;
  return (
    <Photo photoKey={img} alt={alt} className={className} tag={tag}
      fallback={<StageIllustration img={img === "ticket/bocor-dapur" ? "progress/atap" : img} label={alt} className={className} photo={false} />} />
  );
}
