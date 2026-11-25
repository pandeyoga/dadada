import { useEffect, useState, useSyncExternalStore } from "react";
import { getState, subscribe, now } from "./store";

export function useProto(selector) {
  return useSyncExternalStore(subscribe, () => selector(getState()));
}

export function useNow(intervalMs = 1000) {
  const [t, setT] = useState(() => now());
  useEffect(() => {
    const id = setInterval(() => setT(now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return t;
}
