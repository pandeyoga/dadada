import { useEffect, useRef, useState } from "react";
import { useProto } from "../services/useStore";

const DEFAULT_SLICES = ["buyer", "bills", "care"];

/**
 * Muat data layanan; muat ulang bila salah satu slice state yang dipantau berubah.
 * `fetcher` harus fungsi stabil (module-level atau useCallback).
 * `slices` = daftar kunci tingkat atas state (bawaan buyer/bills/care).
 */
export default function useLoad(fetcher, slices = DEFAULT_SLICES) {
  const root = useProto((s) => s);
  const seen = useRef({ vals: [], n: 0 });
  if (slices.some((k, i) => seen.current.vals[i] !== root[k])) {
    seen.current = { vals: slices.map((k) => root[k]), n: seen.current.n + 1 };
  }
  const tick = seen.current.n;
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    fetcher().then(
      (d) => { if (alive) { setData(d); setError(""); } },
      (e) => alive && setError((e && e.message) || "Gagal memuat")
    );
    return () => { alive = false; };
  }, [fetcher, tick]);
  return { data, error };
}
