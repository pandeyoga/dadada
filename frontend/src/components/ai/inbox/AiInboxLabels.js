import React, { useEffect, useMemo, useState } from "react";
import { Bot, FileEdit, UserRound } from "lucide-react";
import { getInboxLabels } from "../aiApi";

const MAP = {
  auto_replied: { text: "Dibalas otomatis", cls: "bg-[#E3F2EA] text-[#14532D]", Icon: Bot },
  draft_ready: { text: "Draf AI siap", cls: "bg-[#E1F0F6] text-[#00454D]", Icon: FileEdit },
  needs_sales: { text: "Butuh sales", cls: "bg-[#FFF4E5] text-[#7A3E00]", Icon: UserRound },
};
const ALIAS = {
  auto_sent: "auto_replied", auto: "auto_replied", dibalas_otomatis: "auto_replied",
  ready: "draft_ready", draft: "draft_ready", draf_ai_siap: "draft_ready",
  handoff: "needs_sales", butuh_sales: "needs_sales",
};

/** Terima string atau {status|key|label, detail|reason, score}. */
export function labelInfo(label) {
  if (!label) return null;
  const raw = typeof label === "string" ? label : (label.status || label.key || label.label || "");
  const key = ALIAS[raw] || raw;
  const base = MAP[key];
  if (!base) return null;
  const obj = typeof label === "object" ? label : {};
  return { ...base, key, detail: obj.detail || obj.reason || obj.category_label || "", score: obj.score };
}

export function AiLabelPill({ label }) {
  const info = labelInfo(label);
  if (!info) return null;
  const { Icon } = info;
  return (
    <span data-testid="ai-label" data-label={info.key}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${info.cls}`}>
      <Icon className="h-3 w-3" aria-hidden="true" />
      {info.text}{info.detail ? ` · ${info.detail}` : ""}
      {info.score != null ? <span className="ml-1 font-normal">Skor {info.score}</span> : null}
    </span>
  );
}

/** Ambil label AI untuk daftar percakapan; gagal/404 = tanpa label (tidak mengganggu Inbox). */
export function useAiLabels(ids, enabled) {
  const [map, setMap] = useState({});
  const key = useMemo(() => (ids || []).join(","), [ids]);
  useEffect(() => {
    if (!enabled || !key) { setMap({}); return undefined; }
    let alive = true;
    getInboxLabels(key.split(",")).then((r) => { if (alive) setMap(r?.labels || r || {}); })
      .catch(() => { if (alive) setMap({}); });
    return () => { alive = false; };
  }, [key, enabled]);
  return map;
}
