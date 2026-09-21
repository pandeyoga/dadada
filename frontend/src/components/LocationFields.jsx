/**
 * LocationFields — alamat bertingkat ala e-commerce (2026-09):
 * Negara → Provinsi → Kota/Kabupaten → Kecamatan → Kode pos, semua dari registry resmi
 * (/api/wilayah). Kode pos hanya bisa dipilih dari kode pos kecamatan terpilih; mengetik
 * kode pos 5 angka di kolom cepat mengisi provinsi/kota/kecamatan otomatis.
 *
 * value  : { country, country_code, province, province_code, city, city_code, district, district_code, postal_code }
 * onChange(patch) — patch berisi kunci di atas (gabungkan ke state form).
 */
import { useEffect, useMemo, useState } from "react";
import axios, { API } from "../services/apiClient";
import KNSelect from "./KNSelect";

const EMPTY = { province: "", province_code: "", city: "", city_code: "", district: "", district_code: "", postal_code: "" };
const cache = {};
async function fetchCached(url) {
  if (!cache[url]) cache[url] = axios.get(url).then((r) => r.data).catch(() => { delete cache[url]; return []; });
  return cache[url];
}

export function locationSummary(v = {}) {
  return [v.district, v.city, v.province, v.postal_code].filter(Boolean).join(", ") || v.city || "";
}

export function locationIncomplete(v = {}) {
  if ((v.country_code || "ID") !== "ID") return !v.postal_code ? "Kode pos wajib diisi." : "";
  if (!v.province_code) return "Pilih provinsi.";
  if (!v.city_code) return "Pilih kota/kabupaten.";
  if (!v.postal_code) return "Pilih kode pos.";
  return "";
}

export default function LocationFields({ value = {}, onChange, testId = "loc", required = true, compact = false }) {
  const [countries, setCountries] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [regencies, setRegencies] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [quick, setQuick] = useState("");
  const [quickMsg, setQuickMsg] = useState("");
  const cc = value.country_code || "ID";

  useEffect(() => { fetchCached(`${API}/wilayah/countries`).then(setCountries); fetchCached(`${API}/wilayah/provinces`).then(setProvinces); }, []);
  useEffect(() => { if (value.province_code) fetchCached(`${API}/wilayah/regencies?province_code=${value.province_code}`).then(setRegencies); else setRegencies([]); }, [value.province_code]);
  useEffect(() => { if (value.city_code) fetchCached(`${API}/wilayah/districts?regency_code=${value.city_code}`).then(setDistricts); else setDistricts([]); }, [value.city_code]);

  const postalOptions = useMemo(() => {
    const d = districts.find((x) => x.code === value.district_code);
    const codes = d ? d.postal_codes : [...new Set(districts.flatMap((x) => x.postal_codes))].sort();
    return codes.map((c) => ({ value: c, label: c }));
  }, [districts, value.district_code]);

  const setCountry = (code) => {
    const c = countries.find((x) => x.code === code);
    onChange({ ...EMPTY, country_code: code, country: c?.name || code });
  };
  const setProvince = (code) => onChange({ ...EMPTY, province_code: code, province: provinces.find((p) => p.code === code)?.name || "" });
  const setCity = (code) => onChange({ city_code: code, city: regencies.find((r) => r.code === code)?.name || "", district: "", district_code: "", postal_code: "" });
  const setDistrict = (code) => {
    const d = districts.find((x) => x.code === code);
    onChange({ district_code: code, district: d?.name || "", postal_code: d && d.postal_codes.length === 1 ? d.postal_codes[0] : "" });
  };

  const applyQuick = async (raw) => {
    const code = raw.replace(/\D/g, "").slice(0, 5);
    setQuick(code); setQuickMsg("");
    if (code.length !== 5) return;
    const hits = await axios.get(`${API}/wilayah/postal-code/${code}`).then((r) => r.data).catch(() => []);
    if (!hits.length) { setQuickMsg(`Kode pos ${code} tidak ditemukan.`); return; }
    const h = hits[0];
    onChange({ country_code: "ID", country: "Indonesia", province: h.province, province_code: h.province_code, city: h.city, city_code: h.city_code,
      district: hits.length === 1 ? h.district : "", district_code: hits.length === 1 ? h.district_code : "", postal_code: code });
    setQuickMsg(hits.length === 1 ? `${h.district}, ${h.city}, ${h.province}` : `${h.city}, ${h.province} — pilih kecamatan (${hits.length} kecamatan memakai kode ini).`);
  };

  const err = required ? locationIncomplete(value) : "";
  const grid = compact ? "grid gap-2 sm:grid-cols-2" : "grid grid-cols-2 gap-3";
  const L = ({ children }) => <label className="text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">{children}</label>;

  return (
    <div data-testid={`${testId}-fields`} className="space-y-2 col-span-2">
      <div className={grid}>
        <div><L>Negara</L>
          <KNSelect data-testid={`${testId}-country`} className="field" value={cc} onValueChange={setCountry}
            options={countries.map((c) => ({ value: c.code, label: c.name }))} placeholder="Negara" /></div>
        {cc === "ID" ? (
          <div><L>Isi cepat dari kode pos</L>
            <input data-testid={`${testId}-postal-quick`} className="field" inputMode="numeric" placeholder="Ketik 5 angka kode pos…" value={quick} onChange={(e) => applyQuick(e.target.value)} />
            {quickMsg && <p data-testid={`${testId}-postal-quick-msg`} className="mt-0.5 text-[10.5px] text-[#6B6B73]">{quickMsg}</p>}
          </div>
        ) : (
          <div><L>Kode pos</L><input data-testid={`${testId}-postal-foreign`} className="field" value={value.postal_code || ""} onChange={(e) => onChange({ postal_code: e.target.value })} placeholder="Kode pos" /></div>
        )}
      </div>
      {cc === "ID" ? (
        <div className={grid}>
          <div><L>Provinsi</L>
            <KNSelect data-testid={`${testId}-province`} className="field" searchable value={value.province_code || ""} onValueChange={setProvince}
              options={provinces.map((p) => ({ value: p.code, label: p.name }))} placeholder="Pilih provinsi" /></div>
          <div><L>Kota / Kabupaten</L>
            <KNSelect data-testid={`${testId}-city`} className="field" searchable disabled={!value.province_code} value={value.city_code || ""} onValueChange={setCity}
              options={regencies.map((r) => ({ value: r.code, label: r.name }))} placeholder={value.province_code ? "Pilih kota/kabupaten" : "Pilih provinsi dahulu"} /></div>
          <div><L>Kecamatan</L>
            <KNSelect data-testid={`${testId}-district`} className="field" searchable disabled={!value.city_code} value={value.district_code || ""} onValueChange={setDistrict}
              options={districts.map((d) => ({ value: d.code, label: d.name }))} placeholder={value.city_code ? "Pilih kecamatan" : "Pilih kota dahulu"} /></div>
          <div><L>Kode pos</L>
            <KNSelect data-testid={`${testId}-postal`} className="field" searchable disabled={!value.city_code} value={value.postal_code || ""} onValueChange={(v) => onChange({ postal_code: v })}
              options={postalOptions} placeholder={value.city_code ? "Pilih kode pos" : "Pilih kota dahulu"} /></div>
        </div>
      ) : (
        <div className={grid}>
          <div><L>Provinsi / Negara bagian</L><input data-testid={`${testId}-province-foreign`} className="field" value={value.province || ""} onChange={(e) => onChange({ province: e.target.value })} /></div>
          <div><L>Kota</L><input data-testid={`${testId}-city-foreign`} className="field" value={value.city || ""} onChange={(e) => onChange({ city: e.target.value })} /></div>
        </div>
      )}
      {err && <p data-testid={`${testId}-error`} className="text-[11px] text-[#C0392B]">{err}</p>}
    </div>
  );
}
