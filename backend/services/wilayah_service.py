"""Wilayah (2026-09) — registry wilayah Indonesia (Kepmendagri 300.2.2-2138/2025 + kode pos) dan
validasi alamat ala e-commerce: negara → provinsi → kota/kabupaten → kecamatan → kode pos harus
saling konsisten. Data: backend/data/wilayah_id.json (38 provinsi, 514 kab/kota, 7.265 kecamatan,
83.345 kelurahan berkode pos).

Dua mode pada penulisan dokumen (customers/addresses/suppliers/makloons/entities):
  * STRICT  — payload membawa province/postal_code/…_code (klien sadar-lokasi, mis. UI baru):
              semua jenjang wajib valid & konsisten, kalau tidak → 400 yang menuntun.
  * LENIENT — hanya `city` (skrip/API lama): nama kota dipetakan ke kab/kota bila bisa
              (alias Solo→Kota Surakarta), sisanya ditandai `location_status` partial/unverified.
"""
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wilayah_id.json")
COUNTRIES: List[Dict[str, str]] = [
    {"code": "ID", "name": "Indonesia"}, {"code": "MY", "name": "Malaysia"}, {"code": "SG", "name": "Singapura"},
    {"code": "TH", "name": "Thailand"}, {"code": "VN", "name": "Vietnam"}, {"code": "CN", "name": "Tiongkok"},
    {"code": "IN", "name": "India"}, {"code": "PK", "name": "Pakistan"}, {"code": "BD", "name": "Bangladesh"},
    {"code": "JP", "name": "Jepang"}, {"code": "KR", "name": "Korea Selatan"}, {"code": "TW", "name": "Taiwan"},
    {"code": "HK", "name": "Hong Kong"}, {"code": "AE", "name": "Uni Emirat Arab"}, {"code": "TR", "name": "Turki"},
    {"code": "IT", "name": "Italia"}, {"code": "DE", "name": "Jerman"}, {"code": "GB", "name": "Inggris"},
    {"code": "US", "name": "Amerika Serikat"}, {"code": "AU", "name": "Australia"}, {"code": "OTHER", "name": "Lainnya"},
]
CITY_ALIASES = {"solo": "Kota Surakarta", "jogja": "Kota Yogyakarta", "yogya": "Kota Yogyakarta", "yogyakarta": "Kota Yogyakarta",
                "bandung": "Kota Bandung", "surabaya": "Kota Surabaya", "semarang": "Kota Semarang", "medan": "Kota Medan",
                "makassar": "Kota Makassar", "denpasar": "Kota Denpasar", "cimahi": "Kota Cimahi", "bekasi": "Kota Bekasi",
                "tangerang": "Kota Tangerang", "depok": "Kota Depok", "bogor": "Kota Bogor", "palembang": "Kota Palembang",
                "pekalongan": "Kota Pekalongan", "cirebon": "Kota Cirebon", "malang": "Kota Malang"}
LOCATION_KEYS = ("country", "country_code", "province", "province_code", "city", "city_code",
                 "district", "district_code", "postal_code")


def _key(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


@lru_cache(maxsize=1)
def _db() -> Dict[str, Any]:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    prov = {p["code"]: p for p in raw["provinces"]}
    reg = {r["code"]: r for r in raw["regencies"]}
    dist = {d["code"]: d for d in raw["districts"]}
    reg_pos: Dict[str, set] = {}
    for d in raw["districts"]:
        reg_pos.setdefault(d["regency_code"], set()).update(d["postal_codes"])
    pos_index: Dict[str, List[Dict[str, Any]]] = {}
    for v in raw["villages"]:
        if v["postal_code"]:
            pos_index.setdefault(v["postal_code"], []).append(v)
    reg_by_name: Dict[str, List[str]] = {}
    for r in raw["regencies"]:
        reg_by_name.setdefault(_key(r["name"]), []).append(r["code"])
        bare = _key(re.sub(r"^(Kota|Kabupaten|Kab\.)\s+", "", r["name"], flags=re.I))
        reg_by_name.setdefault(bare, []).append(r["code"])
    prov_by_name = {_key(p["name"]): p["code"] for p in raw["provinces"]}
    prov_by_name["jakarta"] = prov_by_name["dki jakarta"] = "31"   # alias umum
    return {"prov": prov, "reg": reg, "dist": dist, "reg_pos": reg_pos, "pos_index": pos_index,
            "reg_by_name": reg_by_name, "prov_by_name": prov_by_name, "raw": raw}


# ── Pencarian untuk UI ─────────────────────────────────────────────────────────
def provinces() -> List[Dict[str, str]]:
    return list(_db()["prov"].values())


def regencies(province_code: str) -> List[Dict[str, str]]:
    return [r for r in _db()["reg"].values() if r["province_code"] == province_code]


def districts(regency_code: str) -> List[Dict[str, Any]]:
    return [d for d in _db()["dist"].values() if d["regency_code"] == regency_code]


def villages(district_code: str) -> List[Dict[str, Any]]:
    return [v for v in _db()["raw"]["villages"] if v["code"].startswith(district_code + ".")]


def by_postal_code(code: str) -> List[Dict[str, Any]]:
    """Kode pos → daftar {province, city, district} — isi otomatis ala e-commerce."""
    db = _db()
    out, seen = [], set()
    for v in db["pos_index"].get(str(code).strip(), []):
        dc = v["code"][:8]
        if dc in seen:
            continue
        seen.add(dc)
        d, r = db["dist"][dc], db["reg"][dc[:5]]
        out.append({"postal_code": code, "province_code": dc[:2], "province": db["prov"][dc[:2]]["name"],
                    "city_code": dc[:5], "city": r["name"], "district_code": dc, "district": d["name"]})
    return out


def search(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    k = _key(q)
    if len(k) < 2:
        return []
    db = _db()
    out = [{"level": "city", "code": r["code"], "name": r["name"], "province": db["prov"][r["province_code"]]["name"]}
           for r in db["reg"].values() if k in _key(r["name"])]
    if len(out) < limit:
        out += [{"level": "district", "code": d["code"], "name": f"{d['name']}, {db['reg'][d['regency_code']]['name']}",
                 "province": db["prov"][d["code"][:2]]["name"]} for d in db["dist"].values() if k in _key(d["name"])][: limit - len(out)]
    return out[:limit]


# ── Validasi dokumen ───────────────────────────────────────────────────────────
def _resolve_city_name(name: str) -> Optional[str]:
    db = _db()
    k = _key(CITY_ALIASES.get(_key(name), name))
    codes = db["reg_by_name"].get(k) or []
    if len(codes) == 1:
        return codes[0]
    kota = [c for c in codes if db["reg"][c]["name"].lower().startswith("kota")]
    return kota[0] if len(kota) == 1 else None


def _bad(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)


def normalize_location(data: Dict[str, Any], *, require: bool = False) -> Dict[str, Any]:
    """Field lokasi yang sudah dinormalisasi. Raise 400 bila STRICT dan tidak konsisten.
    `require=True` → provinsi, kota/kabupaten, kode pos WAJIB (alamat baru dari UI)."""
    db = _db()
    country_code = str(data.get("country_code") or "").strip().upper()
    country = str(data.get("country") or "").strip()
    if not country_code:
        country_code = next((c["code"] for c in COUNTRIES if _key(c["name"]) == _key(country)), "ID" if not country else "OTHER")
    country = next((c["name"] for c in COUNTRIES if c["code"] == country_code), country or "Indonesia")
    out: Dict[str, Any] = {"country": country, "country_code": country_code}
    postal = re.sub(r"\s", "", str(data.get("postal_code") or ""))
    g = lambda k: str(data.get(k) or "").strip()  # noqa: E731
    if country_code != "ID":
        if require and not postal:
            raise _bad("Kode pos wajib diisi untuk alamat luar negeri.")
        out.update({"province": g("province"), "province_code": "", "city": g("city"), "city_code": "",
                    "district": g("district"), "district_code": "", "postal_code": postal, "location_status": "foreign"})
        return out

    strict = require or any(g(k) for k in ("province", "province_code", "city_code", "district", "district_code", "postal_code"))
    pcode, ccode, dcode = g("province_code"), g("city_code"), g("district_code")
    city_name, prov_name = g("city"), g("province")

    if not pcode and prov_name:
        pcode = db["prov_by_name"].get(_key(prov_name), "")
        if strict and not pcode:
            raise _bad(f"Provinsi '{prov_name}' tidak dikenal. Pilih dari daftar provinsi.")
    if not ccode and city_name:
        ccode = _resolve_city_name(city_name) or ""
        if not ccode and not pcode and _key(city_name) in db["prov_by_name"]:
            pcode = db["prov_by_name"][_key(city_name)]      # "Jakarta" → provinsi DKI Jakarta
        elif strict and not ccode:
            raise _bad(f"Kota/Kabupaten '{city_name}' tidak dikenal. Pilih dari daftar kota/kabupaten.")
    if ccode and ccode not in db["reg"]:
        raise _bad("Kode kota/kabupaten tidak dikenal.")
    if ccode and not pcode:
        pcode = ccode[:2]
    if pcode and pcode not in db["prov"]:
        raise _bad("Kode provinsi tidak dikenal.")
    if ccode and pcode and ccode[:2] != pcode:
        raise _bad(f"{db['reg'][ccode]['name']} tidak berada di provinsi {db['prov'][pcode]['name']}.")
    if dcode:
        if dcode not in db["dist"]:
            raise _bad("Kode kecamatan tidak dikenal.")
        if ccode and dcode[:5] != ccode:
            raise _bad(f"Kecamatan {db['dist'][dcode]['name']} tidak berada di {db['reg'][ccode]['name']}.")
        ccode, pcode = ccode or dcode[:5], pcode or dcode[:2]
    if postal:
        if not re.fullmatch(r"\d{5}", postal):
            raise _bad("Kode pos Indonesia harus 5 angka.")
        if postal not in db["pos_index"]:
            raise _bad(f"Kode pos {postal} tidak ditemukan di daftar kode pos Indonesia.")
        if dcode and postal not in db["dist"][dcode]["postal_codes"]:
            raise _bad(f"Kode pos {postal} bukan kode pos kecamatan {db['dist'][dcode]['name']} "
                       f"(yang sah: {', '.join(db['dist'][dcode]['postal_codes'])}).")
        if ccode and postal not in db["reg_pos"].get(ccode, set()):
            raise _bad(f"Kode pos {postal} bukan kode pos wilayah {db['reg'][ccode]['name']}.")
        if not ccode:
            hits = by_postal_code(postal)
            ccode, pcode = hits[0]["city_code"], hits[0]["province_code"]
            if len(hits) == 1:
                dcode = hits[0]["district_code"]
    if require:
        missing = [n for n, v in (("provinsi", pcode), ("kota/kabupaten", ccode), ("kode pos", postal)) if not v]
        if missing:
            raise _bad(f"Alamat belum lengkap: {', '.join(missing)} wajib diisi & valid.")
    out.update({
        "province": db["prov"][pcode]["name"] if pcode else prov_name,
        "province_code": pcode,
        "city": db["reg"][ccode]["name"] if ccode else city_name,
        "city_code": ccode,
        "district": db["dist"][dcode]["name"] if dcode else g("district"),
        "district_code": dcode,
        "postal_code": postal,
        "location_status": "verified" if (pcode and ccode and postal) else ("partial" if (pcode or ccode) else "unverified"),
    })
    return out


def apply_location(doc: Dict[str, Any], *, require: bool = False) -> Dict[str, Any]:
    """Isi/normalisasi field lokasi pada dict (in-place) bila ada field lokasi apa pun."""
    if any(k in doc for k in LOCATION_KEYS):
        doc.update(normalize_location(doc, require=require))
    return doc
