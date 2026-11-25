import { useEffect, useState } from "react";
import { useProto } from "../../services/useStore";

/** Muat data layanan; muat ulang tiap slice `buyer`/`bills`/`care` berubah. */
export default function useLoad(fetcher) {
  const buyer = useProto((s) => s.buyer);
  const bills = useProto((s) => s.bills);
  const care = useProto((s) => s.care);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    fetcher().then((d) => alive && setData(d), (e) => alive && setError(e.message || "Gagal memuat"));
    return () => { alive = false; };
  }, [fetcher, buyer, bills, care]);
  return { data, error };
}
