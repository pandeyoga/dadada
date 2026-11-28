import { useCallback, useEffect, useState } from "react";
import { getInboxAi } from "../aiApi";

/** Data AI untuk satu percakapan inbox: {draft,label,insights,channel,verified}. Gagal/404 = null. */
export default function useAiInbox(convId, enabled) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    if (!enabled || !convId) { setData(null); return; }
    try { setData((await getInboxAi(convId)) || null); } catch { setData(null); }
  }, [convId, enabled]);
  useEffect(() => { load(); }, [load]);
  return [data, load];
}

export const CHANNEL_TEXT = {
  coexistence: "Coexistence (resmi)", cloud: "Cloud API (resmi)", official: "WhatsApp resmi",
  unofficial: "Gateway tidak resmi (risiko blokir)",
};
export const channelText = (c) => {
  const v = typeof c === "string" ? c : c?.mode || c?.type || c?.label;
  return CHANNEL_TEXT[v] || (typeof c === "object" ? c?.label : v) || "";
};
