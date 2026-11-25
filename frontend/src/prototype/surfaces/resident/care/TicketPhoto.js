import React from "react";
import { StageIllustration } from "../../../components/Illustrations";

// Foto contoh lokal untuk laporan (ilustrasi SVG, tanpa berkas gambar).
export const PHOTO_OPTIONS = [
  { id: "progress/atap", label: "Atap dan plafon" },
  { id: "progress/dinding", label: "Dinding" },
  { id: "progress/kusen", label: "Pintu dan jendela" },
  { id: "progress/plester", label: "Cat dan plester" },
];
const ALIAS = { "ticket/bocor-dapur": "progress/atap" };

export default function TicketPhoto({ img, className = "" }) {
  const key = ALIAS[img] || img;
  const label = (PHOTO_OPTIONS.find((p) => p.id === key) || { label: "Foto laporan" }).label;
  return <StageIllustration img={key} label={`Foto contoh: ${label}`} className={className} />;
}
