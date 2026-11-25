import React from "react";
import useActiveSos from "./useActiveSos";
import SosCard from "./SosCard";

/** Peringatan merah di layar satpam lain (S3–S5) saat ada SOS baru yang belum diterima. */
export default function SosBanner() {
  const event = useActiveSos();
  return event && event.status === "sent" ? <SosCard event={event} /> : null;
}
