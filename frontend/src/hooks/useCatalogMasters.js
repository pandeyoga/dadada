import { useEffect, useState } from "react";
import axios, { API } from "../services/apiClient";
import useUomConversions from "./useUomConversions";
import { uomSelectOptions } from "../utils/uomCatalog";

let _cache = null;
const load = () => _cache || (_cache = Promise.all([
  axios.get(`${API}/product-categories`).then((r) => r.data).catch(() => []),
  axios.get(`${API}/product-motifs`).then((r) => r.data.items || []).catch(() => []),
  axios.get(`${API}/suppliers`).then((r) => (Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => []),
]).then(([categories, motifs, suppliers]) => ({ categories, motifs, suppliers })));

/** Pilihan master untuk form produk — kategori, motif, pemasok, satuan — tanpa ketik bebas. */
export default function useCatalogMasters({ current = {} } = {}) {
  const [m, setM] = useState({ categories: [], motifs: [], suppliers: [] });
  useUomConversions();
  useEffect(() => { let live = true; load().then((d) => { if (live) setM(d); }); return () => { live = false; }; }, []);
  const withCurrent = (opts, cur) => (cur && !opts.some((o) => o.value === cur) ? [{ value: cur, label: `${cur} (nilai lama)` }, ...opts] : opts);
  return {
    categoryOptions: withCurrent(m.categories.filter((c) => (c.status || "active") === "active").map((c) => ({ value: c.name, label: c.name })), current.category),
    motifOptions: withCurrent(m.motifs.map((x) => ({ value: x.value, label: x.label })), current.motif),
    supplierOptions: withCurrent([{ value: "Internal", label: "Internal (produksi sendiri)" }, ...m.suppliers.filter((s) => (s.status || "active") === "active").map((s) => ({ value: s.name, label: `${s.name}${s.code ? ` · ${s.code}` : ""}` }))], current.supplier),
    unitOptions: uomSelectOptions({ dimensions: ["length", "weight", "count"], extra: [current.base_unit].filter(Boolean) }),
  };
}
export const refreshCatalogMasters = () => { _cache = null; };
