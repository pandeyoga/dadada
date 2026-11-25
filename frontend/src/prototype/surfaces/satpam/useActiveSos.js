import { useMemo } from "react";
import { useProto } from "../../services/useStore";

/** SOS yang sedang berjalan (sent/accepted) — ikut berubah saat tab lain mengirim/membatalkan. */
export default function useActiveSos() {
  const sos = useProto((s) => s.security.sos);
  return useMemo(() => sos.find((e) => e.status === "sent" || e.status === "accepted") || null, [sos]);
}
